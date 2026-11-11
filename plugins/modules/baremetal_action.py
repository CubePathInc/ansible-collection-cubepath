#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: baremetal_action
short_description: Perform actions on baremetal servers on CubePath Cloud
description:
    - Reinstall, rescue, reset BMC, update, or manage monitoring on CubePath Cloud.
    - Cancel a reinstall, enable or disable destruction protection, move the server to another project,
      attach or detach SSH keys, and attach or detach its private network.
    - SSH key changes only update the keys recorded for the server (used by reinstalls). Network changes
      apply after a restart of the server.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description: Action to perform.
        type: str
        required: true
        choices: [reinstall, rescue, reset_bmc, update, monitoring_enable, monitoring_disable, cancel_reinstall,
                  protect, unprotect, move_project, add_ssh_keys, remove_ssh_key, attach_network, detach_network]
    baremetal_id:
        description: Number or uuid of the baremetal server.
        type: str
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
    project_id:
        description: Target project. Required when I(action=move_project).
        type: int
        version_added: "1.5.0"
    ssh_key_ids:
        description:
            - SSH key IDs. Required when I(action=add_ssh_keys) or I(action=remove_ssh_key)
              (C(remove_ssh_key) removes each of them).
        type: list
        elements: int
        version_added: "1.5.0"
    network_id:
        description: Private network ID in the location of the server. Required when I(action=attach_network).
        type: int
        version_added: "1.5.0"
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

- name: Move a server to another project
  cubepathinc.cloud.baremetal_action:
    api_token: "{{ cubepath_token }}"
    action: move_project
    baremetal_id: 10
    project_id: 7
'''

RETURN = r'''
result:
    description: API response.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_baremetal import baremetal_ref_param


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        action=dict(type='str', required=True, choices=[
            'reinstall', 'rescue', 'reset_bmc', 'update',
            'monitoring_enable', 'monitoring_disable', 'cancel_reinstall', 'protect', 'unprotect',
            'move_project', 'add_ssh_keys', 'remove_ssh_key', 'attach_network', 'detach_network',
        ]),
        baremetal_id=dict(type='str', required=True),
        os=dict(type='str'),
        hostname=dict(type='str'),
        user=dict(type='str', default='root'),
        password=dict(type='str', no_log=True),
        disk_layout=dict(type='str'),
        tags=dict(type='str'),
        project_id=dict(type='int'),
        ssh_key_ids=dict(type='list', elements='int', no_log=False),
        network_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('action', 'reinstall', ['os', 'hostname', 'password']),
            ('action', 'move_project', ['project_id']),
            ('action', 'add_ssh_keys', ['ssh_key_ids']),
            ('action', 'remove_ssh_key', ['ssh_key_ids']),
            ('action', 'attach_network', ['network_id']),
        ],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    bid = baremetal_ref_param(module)

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s baremetal %s' % (action, bid))

    result = {}
    if action == 'reinstall':
        data = {
            'os_name': module.params['os'],
            'hostname': module.params['hostname'],
            'user': module.params['user'],
            'password': module.params['password'],
        }
        if module.params.get('disk_layout'):
            data['disk_layout_name'] = module.params['disk_layout']
        result = api.post('/baremetal/%s/reinstall' % bid, data)
    elif action == 'rescue':
        result = api.post('/baremetal/%s/rescue' % bid)
    elif action == 'reset_bmc':
        result = api.post('/baremetal/%s/reset-bmc' % bid)
    elif action == 'update':
        data = {}
        if module.params.get('hostname'):
            data['hostname'] = module.params['hostname']
        if module.params.get('tags') is not None:
            data['tags'] = module.params['tags']
        if not data:
            module.fail_json(msg='At least one of hostname or tags required for update')
        result = api.patch('/baremetal/update/%s' % bid, data)
    elif action == 'monitoring_enable':
        result = api.put('/baremetal/%s/monitoring?enable=true' % bid)
    elif action == 'monitoring_disable':
        result = api.put('/baremetal/%s/monitoring?enable=false' % bid)
    elif action == 'cancel_reinstall':
        result = api.delete('/baremetal/%s/reinstall' % bid)
    elif action in ('protect', 'unprotect'):
        result = api.post('/baremetal/%s/protection' % bid, {'enabled': action == 'protect'})
    elif action == 'move_project':
        result = api.post('/baremetal/%s/move-project' % bid, {'project_id': module.params['project_id']})
    elif action == 'add_ssh_keys':
        result = api.post('/baremetal/%s/ssh-keys' % bid, module.params['ssh_key_ids'])
    elif action == 'remove_ssh_key':
        for key_id in module.params['ssh_key_ids']:
            result = api.delete('/baremetal/%s/ssh-keys/%d' % (bid, key_id))
    elif action == 'attach_network':
        result = api.post('/baremetal/%s/network' % bid, {'network_id': module.params['network_id']})
    elif action == 'detach_network':
        result = api.delete('/baremetal/%s/network' % bid)

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
