#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_zone
short_description: Manage DNS zones on CubePath Cloud
description:
    - Create, delete, or verify DNS zones on CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent, verified]
    domain:
        description: Domain name (e.g. example.com).
        type: str
        required: true
    project_id:
        description: Project ID. Required when I(state=present).
        type: int
    zone_uuid:
        description: Zone UUID. Required when I(state=absent) or I(state=verified) if domain lookup fails.
        type: str
'''

EXAMPLES = r'''
- name: Create DNS zone
  cubepathinc.cloud.dns_zone:
    api_token: "{{ cubepath_token }}"
    domain: example.com
    project_id: 1
    state: present

- name: Verify DNS zone
  cubepathinc.cloud.dns_zone:
    api_token: "{{ cubepath_token }}"
    domain: example.com
    state: verified

- name: Delete DNS zone
  cubepathinc.cloud.dns_zone:
    api_token: "{{ cubepath_token }}"
    domain: example.com
    state: absent
'''

RETURN = r'''
zone:
    description: DNS zone details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def find_zone(api, domain, project_id=None):
    params = {}
    if project_id:
        params['project_id'] = project_id
    zones = api.get('/dns/zones', params=params or None)
    if isinstance(zones, list):
        for z in zones:
            if z.get('domain') == domain:
                return z
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent', 'verified']),
        domain=dict(type='str', required=True),
        project_id=dict(type='int'),
        zone_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['project_id'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    domain = module.params['domain']

    existing = find_zone(api, domain, module.params.get('project_id'))

    if state == 'present':
        if existing:
            module.exit_json(changed=False, zone=existing)
        if module.check_mode:
            module.exit_json(changed=True)
        result = api.post('/dns/zones', {'domain': domain, 'project_id': module.params['project_id']})
        module.exit_json(changed=True, zone=result)

    elif state == 'absent':
        uuid = module.params.get('zone_uuid')
        if existing:
            uuid = existing.get('uuid')
        if not uuid:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/dns/zones/%s' % uuid)
        module.exit_json(changed=True)

    elif state == 'verified':
        uuid = module.params.get('zone_uuid')
        if existing:
            uuid = existing.get('uuid')
            if existing.get('verified_at'):
                module.exit_json(changed=False, zone=existing)
        if not uuid:
            module.fail_json(msg='Zone not found for domain %s' % domain)
        if module.check_mode:
            module.exit_json(changed=True)
        result = api.post('/dns/zones/%s/verify' % uuid)
        module.exit_json(changed=True, zone=result)


if __name__ == '__main__':
    main()
