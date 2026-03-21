#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: baremetal_action
short_description: Perform actions on baremetal servers on CubePath Cloud
description:
    - Reinstall, rescue, reset BMC, update, or manage monitoring on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description: Action to perform.
        type: str
        required: true
        choices: [reinstall, rescue, reset_bmc, update, monitoring_enable, monitoring_disable]
    baremetal_id:
        description: ID of the baremetal server.
        type: int
        required: true
    os:
        description: OS name. Required when I(action=reinstall).
        type: str
    hostname:
        description: Hostname. Required when I(action=reinstall).
        type: str
    user:
        description: Username for reinstall.
        type: str
        default: root
    password:
        description: Password. Required when I(action=reinstall).
        type: str
    disk_layout:
        description: Disk layout for reinstall.
        type: str
    tags:
        description: Tags for update.
        type: str
'''

EXAMPLES = r'''
- name: Reinstall OS
  cubepathinc.cloud.baremetal_action:
    api_token: "{{ cubepath_token }}"
    action: reinstall
    baremetal_id: 10
    os: "Debian 13"
    hostname: db-01
    password: "{{ vault_password }}"

- name: Enable rescue mode
  cubepathinc.cloud.baremetal_action:
    api_token: "{{ cubepath_token }}"
    action: rescue
    baremetal_id: 10
'''

RETURN = r'''
result:
    description: API response.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        action=dict(type='str', required=True, choices=[
            'reinstall', 'rescue', 'reset_bmc', 'update',
            'monitoring_enable', 'monitoring_disable',
        ]),
        baremetal_id=dict(type='int', required=True),
        os=dict(type='str'),
        hostname=dict(type='str'),
        user=dict(type='str', default='root'),
        password=dict(type='str', no_log=True),
        disk_layout=dict(type='str'),
        tags=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('action', 'reinstall', ['os', 'hostname', 'password'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    bid = module.params['baremetal_id']

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s baremetal %d' % (action, bid))

    if action == 'reinstall':
        data = {
            'os_name': module.params['os'],
            'hostname': module.params['hostname'],
            'user': module.params['user'],
            'password': module.params['password'],
        }
        if module.params.get('disk_layout'):
            data['disk_layout_name'] = module.params['disk_layout']
        result = api.post('/baremetal/%d/reinstall' % bid, data)
    elif action == 'rescue':
        result = api.post('/baremetal/%d/rescue' % bid)
    elif action == 'reset_bmc':
        result = api.post('/baremetal/%d/reset-bmc' % bid)
    elif action == 'update':
        data = {}
        if module.params.get('hostname'):
            data['hostname'] = module.params['hostname']
        if module.params.get('tags') is not None:
            data['tags'] = module.params['tags']
        if not data:
            module.fail_json(msg='At least one of hostname or tags required for update')
        result = api.patch('/baremetal/update/%d' % bid, data)
    elif action == 'monitoring_enable':
        result = api.put('/baremetal/%d/monitoring?enable=true' % bid)
    elif action == 'monitoring_disable':
        result = api.put('/baremetal/%d/monitoring?enable=false' % bid)

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
