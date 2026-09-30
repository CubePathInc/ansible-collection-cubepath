#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: firewall_group
short_description: Manage firewall groups on CubePath Cloud
description:
    - Create, update or delete VPS firewall groups on CubePath Cloud. A group is a set of rules applied to
      every VPS it is assigned to (see M(cubepathinc.cloud.vps_firewall_groups)).
    - The module finds an existing group by I(name) in I(project_id), or anywhere in the organization when
      I(project_id) is not set, and replaces its rules when they differ. Changes are synchronized to the
      assigned VPS.
    - A group assigned to a VPS cannot be deleted.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the group.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the group (up to 255 characters).
        type: str
        required: true
    project_id:
        description: Project of the group. Required to create it.
        type: int
    rules:
        description:
            - Rules of the group (up to 100). Required to create the group.
            - When set on an existing group, replaces its rules.
        type: list
        elements: dict
        suboptions:
            direction:
                description: Traffic direction.
                type: str
                required: true
                choices: [in, out]
            protocol:
                description: Protocol.
                type: str
                required: true
                choices: [tcp, udp, icmp, gre]
            port:
                description: Port for C(tcp) and C(udp), as a single port C(80), a range C(8000-8100) or a list C(80,443).
                type: str
            source:
                description: Source IP or CIDR the rule applies to. Any source when omitted.
                type: str
            comment:
                description: Free-form comment.
                type: str
    enabled:
        description: Whether the group's rules are applied.
        type: bool
'''

EXAMPLES = r'''
- name: Web server rules
  cubepathinc.cloud.firewall_group:
    api_token: "{{ cubepath_token }}"
    name: web
    project_id: 12
    rules:
      - direction: in
        protocol: tcp
        port: "80,443"
        comment: HTTP and HTTPS
      - direction: in
        protocol: tcp
        port: "22"
        source: 203.0.113.0/24
        comment: SSH from the office
  register: web_fw
'''

RETURN = r'''
firewall_group:
    description: Group details (C(id), C(project_id), C(name), C(rules), C(enabled), C(vps_count)).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list

RULE_FIELDS = ('direction', 'protocol', 'port', 'source', 'comment')


def normalize(rule):
    """Compare rules by value, treating a missing and an empty port, source or comment alike."""
    return tuple((rule.get(k) or None) for k in RULE_FIELDS)


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        project_id=dict(type='int'),
        rules=dict(type='list', elements='dict', options=dict(
            direction=dict(type='str', required=True, choices=['in', 'out']),
            protocol=dict(type='str', required=True, choices=['tcp', 'udp', 'icmp', 'gre']),
            port=dict(type='str'),
            source=dict(type='str'),
            comment=dict(type='str'),
        )),
        enabled=dict(type='bool'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params

    def fetch():
        for group in as_list(api.get('/firewall/groups')):
            if group.get('name') == p['name'] and (p.get('project_id') is None or group.get('project_id') == p['project_id']):
                return group
        return None

    existing = fetch()

    if p['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/firewall/groups/%d' % existing['id'])
        module.exit_json(changed=True)

    rules = None
    if p.get('rules') is not None:
        rules = [dict((k, r.get(k)) for k in RULE_FIELDS if r.get(k) is not None) for r in p['rules']]

    if existing is None:
        if p.get('project_id') is None or rules is None:
            module.fail_json(msg='project_id and rules are required to create a firewall group')
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'name': p['name'], 'rules': rules}
        if p.get('enabled') is not None:
            data['enabled'] = p['enabled']
        group = api.post('/firewall/groups', data, params={'project_id': p['project_id']})
        module.exit_json(changed=True, firewall_group=group)

    update = {}
    if rules is not None and [normalize(r) for r in rules] != [normalize(r) for r in existing.get('rules') or []]:
        update['rules'] = rules
    if p.get('enabled') is not None and p['enabled'] != existing.get('enabled'):
        update['enabled'] = p['enabled']
    if not update:
        module.exit_json(changed=False, firewall_group=existing)
    if module.check_mode:
        module.exit_json(changed=True, firewall_group=existing)
    group = api.put('/firewall/groups/%d' % existing['id'], update)
    module.exit_json(changed=True, firewall_group=group)


if __name__ == '__main__':
    main()
