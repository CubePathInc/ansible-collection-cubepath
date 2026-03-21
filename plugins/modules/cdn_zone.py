#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_zone
short_description: Manage CDN zones on CubePath Cloud
description:
    - Create, update, or delete CDN zones on CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Zone name (3-32 chars).
        type: str
        required: true
    plan:
        description: CDN plan name. Required when I(state=present).
        type: str
    custom_domain:
        description: Custom domain.
        type: str
    ssl_type:
        description: SSL type.
        type: str
        choices: [automatic, custom]
    certificate_uuid:
        description: Custom SSL certificate UUID.
        type: str
    project_id:
        description: Project ID.
        type: int
    zone_uuid:
        description: Zone UUID for deletion or updates.
        type: str
'''

EXAMPLES = r'''
- name: Create CDN zone
  cubepathinc.cloud.cdn_zone:
    api_token: "{{ cubepath_token }}"
    name: my-cdn
    plan: cdn.starter
    state: present

- name: Delete CDN zone
  cubepathinc.cloud.cdn_zone:
    api_token: "{{ cubepath_token }}"
    name: my-cdn
    state: absent
'''

RETURN = r'''
zone:
    description: CDN zone details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def find_cdn_zone(api, name):
    zones = api.get('/cdn/zones')
    if isinstance(zones, list):
        for z in zones:
            if z.get('name') == name:
                return z
    elif isinstance(zones, dict):
        for z in zones.get('zones', []):
            if z.get('name') == name:
                return z
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        plan=dict(type='str'),
        custom_domain=dict(type='str'),
        ssl_type=dict(type='str', choices=['automatic', 'custom']),
        certificate_uuid=dict(type='str'),
        project_id=dict(type='int'),
        zone_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['plan'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params['name']

    existing = find_cdn_zone(api, name)

    if state == 'present':
        if existing:
            uuid = existing.get('uuid')
            update_data = {}
            for field, api_field in [('custom_domain', 'custom_domain'), ('ssl_type', 'ssl_type'), ('certificate_uuid', 'certificate_uuid')]:
                val = module.params.get(field)
                if val and existing.get(api_field) != val:
                    update_data[api_field] = val
            if update_data:
                if module.check_mode:
                    module.exit_json(changed=True)
                result = api.patch('/cdn/zones/%s' % uuid, update_data)
                module.exit_json(changed=True, zone=result)
            module.exit_json(changed=False, zone=existing)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {'name': name, 'plan_name': module.params['plan']}
        if module.params.get('custom_domain'):
            data['custom_domain'] = module.params['custom_domain']
        if module.params.get('project_id'):
            data['project_id'] = module.params['project_id']

        result = api.post('/cdn/zones', data)
        module.exit_json(changed=True, zone=result)

    elif state == 'absent':
        uuid = module.params.get('zone_uuid')
        if existing:
            uuid = existing.get('uuid')
        if not uuid:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/cdn/zones/%s' % uuid)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
