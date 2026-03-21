#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_origin
short_description: Manage CDN origins on CubePath Cloud
description:
    - Create, update, or delete CDN origins on CubePath Cloud.
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
    zone_uuid:
        description: CDN zone UUID.
        type: str
        required: true
    name:
        description: Origin name. Required when I(state=present).
        type: str
    origin_url:
        description: Origin URL (auto-parsed).
        type: str
    address:
        description: Origin IP or hostname.
        type: str
    port:
        description: Origin port.
        type: int
    protocol:
        description: Protocol.
        type: str
        choices: [http, https]
    weight:
        description: Load balancing weight (1-1000).
        type: int
        default: 100
    priority:
        description: Priority (1-100).
        type: int
        default: 1
    is_backup:
        description: Mark as backup origin.
        type: bool
        default: false
    health_check_enabled:
        description: Enable health checks.
        type: bool
        default: true
    health_check_path:
        description: Health check path.
        type: str
        default: /health
    verify_ssl:
        description: Verify SSL certificates.
        type: bool
        default: true
    host_header:
        description: Custom Host header.
        type: str
    base_path:
        description: Base path prefix.
        type: str
    enabled:
        description: Enable or disable origin.
        type: bool
        default: true
    origin_uuid:
        description: Origin UUID for updates or deletion.
        type: str
'''

EXAMPLES = r'''
- name: Create CDN origin
  cubepathinc.cloud.cdn_origin:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    name: primary-origin
    address: "1.2.3.4"
    port: 443
    protocol: https
    state: present

- name: Delete CDN origin
  cubepathinc.cloud.cdn_origin:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    origin_uuid: "def-456"
    state: absent
'''

RETURN = r'''
origin:
    description: Origin details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        zone_uuid=dict(type='str', required=True),
        name=dict(type='str'),
        origin_url=dict(type='str'),
        address=dict(type='str'),
        port=dict(type='int'),
        protocol=dict(type='str', choices=['http', 'https']),
        weight=dict(type='int', default=100),
        priority=dict(type='int', default=1),
        is_backup=dict(type='bool', default=False),
        health_check_enabled=dict(type='bool', default=True),
        health_check_path=dict(type='str', default='/health'),
        verify_ssl=dict(type='bool', default=True),
        host_header=dict(type='str'),
        base_path=dict(type='str'),
        enabled=dict(type='bool', default=True),
        origin_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['name']), ('state', 'absent', ['origin_uuid'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    zone_uuid = module.params['zone_uuid']
    origin_uuid = module.params.get('origin_uuid')

    if state == 'present':
        if origin_uuid:
            data = {}
            for field in ('name', 'address', 'port', 'protocol', 'weight', 'priority', 'host_header', 'base_path'):
                if module.params.get(field) is not None:
                    data[field] = module.params[field]
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.patch('/cdn/zones/%s/origins/%s' % (zone_uuid, origin_uuid), data)
            module.exit_json(changed=True, origin=result)

        if not module.params.get('origin_url') and not module.params.get('address'):
            module.fail_json(msg='Either origin_url or address is required')

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': module.params['name'],
            'weight': module.params['weight'],
            'priority': module.params['priority'],
            'is_backup': module.params['is_backup'],
            'health_check_enabled': module.params['health_check_enabled'],
            'health_check_path': module.params['health_check_path'],
            'verify_ssl': module.params['verify_ssl'],
            'enabled': module.params['enabled'],
        }
        if module.params.get('origin_url'):
            data['origin_url'] = module.params['origin_url']
        if module.params.get('address'):
            data['address'] = module.params['address']
        if module.params.get('port'):
            data['port'] = module.params['port']
        if module.params.get('protocol'):
            data['protocol'] = module.params['protocol']
        if module.params.get('host_header'):
            data['host_header'] = module.params['host_header']
        if module.params.get('base_path'):
            data['base_path'] = module.params['base_path']

        result = api.post('/cdn/zones/%s/origins' % zone_uuid, data)
        module.exit_json(changed=True, origin=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/cdn/zones/%s/origins/%s' % (zone_uuid, origin_uuid))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
