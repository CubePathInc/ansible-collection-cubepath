#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_prefix_list
short_description: Manage DDoS Mitigation prefix lists on CubePath Cloud
description:
    - Create or delete custom prefix lists and manage their entries. A prefix list is a set of source
      networks that a DDoS protection profile can block or allow (see M(cubepathinc.cloud.ddos_protection_profile)).
    - The module finds an existing list of the organization by I(name). Platform-wide lists are read only.
    - An organization can own up to 3 lists of up to 100 entries each.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the prefix list.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the prefix list (1 to 64 characters).
        type: str
        required: true
    description:
        description:
            - Description of the list. Only used when the list is created; the API cannot change it later.
        type: str
    entries:
        description:
            - IP addresses or CIDR networks the list must contain. A bare IP is stored as C(/32) or C(/128).
            - Give networks without host bits (C(10.0.0.0/24), not C(10.0.0.5/24)); the API stores the network
              address, so a network with host bits would be added again on every run.
            - Entries not in this list are removed when I(purge_entries=true).
            - When omitted, the entries are left as they are.
        type: list
        elements: str
    purge_entries:
        description: Remove the entries that are not in I(entries).
        type: bool
        default: true
'''

EXAMPLES = r'''
- name: Trusted monitoring sources
  cubepathinc.cloud.ddos_prefix_list:
    api_token: "{{ cubepath_token }}"
    name: trusted-monitoring
    description: Uptime probes
    entries:
      - 192.0.2.0/24
      - 198.51.100.7

- name: Delete it
  cubepathinc.cloud.ddos_prefix_list:
    api_token: "{{ cubepath_token }}"
    name: trusted-monitoring
    state: absent
'''

RETURN = r'''
prefix_list:
    description: Prefix list (C(uuid), C(name), C(description), C(entries_count)...).
    type: dict
    returned: when I(state=present)
entries:
    description: Networks in the list after the changes.
    type: list
    elements: str
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec, path_quote
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_ddos import find_prefix_list, normalize_network


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        description=dict(type='str'),
        entries=dict(type='list', elements='str'),
        purge_entries=dict(type='bool', default=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    name = module.params['name']
    existing = find_prefix_list(api, name, own_only=True)

    if module.params['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/ddos-mitigation/prefix-lists/%s' % existing['uuid'])
        module.exit_json(changed=True)

    wanted = []
    for entry in module.params.get('entries') or []:
        network = normalize_network(entry)
        if network not in wanted:
            wanted.append(network)

    changed = False
    if existing is None:
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'name': name}
        if module.params.get('description') is not None:
            data['description'] = module.params['description']
        api.post('/ddos-mitigation/prefix-lists', data)
        changed = True
        existing = find_prefix_list(api, name, own_only=True)

    base = '/ddos-mitigation/prefix-lists/%s/entries' % existing['uuid']
    current = [e.get('network') for e in as_list(api.get(base), 'entries')]
    if module.params.get('entries') is not None:
        to_add = [e for e in wanted if e not in current]
        to_remove = [e for e in current if e not in wanted] if module.params['purge_entries'] else []
        if (to_add or to_remove) and module.check_mode:
            module.exit_json(changed=True, prefix_list=existing, entries=current)
        for network in to_remove:
            api.delete('%s/%s' % (base, path_quote(network)))
        for network in to_add:
            api.post(base, {'network': network})
        if to_add or to_remove:
            changed = True
            current = [e.get('network') for e in as_list(api.get(base), 'entries')]
            existing = find_prefix_list(api, name, own_only=True)

    module.exit_json(changed=changed, prefix_list=existing, entries=current)


if __name__ == '__main__':
    main()
