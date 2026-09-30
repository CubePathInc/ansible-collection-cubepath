#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_action
short_description: Perform actions on VPS instances on CubePath Cloud
description:
    - Resize, reinstall, change password, or update a VPS on CubePath Cloud.
    - Enable or disable destruction protection, move the VPS to another project, attach or detach SSH keys,
      and attach or detach its private network.
    - SSH key changes only update the keys recorded for the VPS (used by reinstalls); they do not edit
      C(authorized_keys) on a running server. Network changes apply after a restart of the VPS.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description: Action to perform.
        type: str
        required: true
        choices: [resize, reinstall, change_password, update, protect, unprotect, move_project, add_ssh_keys,
                  remove_ssh_key, attach_network, detach_network]
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
    plan:
        description: New plan name. Required when I(action=resize).
        type: str
    template:
        description: New OS template. Required when I(action=reinstall).
        type: str
    password:
        description: New password. Required when I(action=change_password).
        type: str
    label:
        description: New label. Used when I(action=update).
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
        description: Private network ID. Required when I(action=attach_network).
        type: int
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: Resize VPS
  cubepathinc.cloud.vps_action:
    api_token: "{{ cubepath_token }}"
    action: resize
    vps_id: 123
    plan: gp.starter

- name: Protect a VPS against deletion
  cubepathinc.cloud.vps_action:
    api_token: "{{ cubepath_token }}"
    action: protect
    vps_id: 123

- name: Attach a private network
  cubepathinc.cloud.vps_action:
    api_token: "{{ cubepath_token }}"
    action: attach_network
    vps_id: 123
    network_id: 42
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
            'resize', 'reinstall', 'change_password', 'update', 'protect', 'unprotect', 'move_project',
            'add_ssh_keys', 'remove_ssh_key', 'attach_network', 'detach_network',
        ]),
        vps_id=dict(type='int', required=True),
        plan=dict(type='str'),
        template=dict(type='str'),
        password=dict(type='str', no_log=True),
        label=dict(type='str'),
        project_id=dict(type='int'),
        ssh_key_ids=dict(type='list', elements='int', no_log=False),
        network_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('action', 'resize', ['plan']),
            ('action', 'reinstall', ['template']),
            ('action', 'change_password', ['password']),
            ('action', 'move_project', ['project_id']),
            ('action', 'add_ssh_keys', ['ssh_key_ids']),
            ('action', 'remove_ssh_key', ['ssh_key_ids']),
            ('action', 'attach_network', ['network_id']),
        ],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    vps_id = module.params['vps_id']

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s VPS %d' % (action, vps_id))

    result = {}
    if action == 'resize':
        result = api.post('/vps/resize/vps_id/%d/resize_plan/%s' % (vps_id, module.params['plan']))
    elif action == 'reinstall':
        result = api.post('/vps/reinstall/%d' % vps_id, {'template_name': module.params['template']})
    elif action == 'change_password':
        result = api.post('/vps/%d/change-password' % vps_id, {'password': module.params['password']})
    elif action == 'update':
        data = {}
        if module.params.get('label') is not None:
            data['label'] = module.params['label']
        if not data:
            module.fail_json(msg='At least one field must be provided for update')
        result = api.patch('/vps/update/%d' % vps_id, data)
    elif action in ('protect', 'unprotect'):
        result = api.post('/vps/%d/protection' % vps_id, {'enabled': action == 'protect'})
    elif action == 'move_project':
        result = api.post('/vps/%d/move-project' % vps_id, {'project_id': module.params['project_id']})
    elif action == 'add_ssh_keys':
        result = api.post('/vps/%d/ssh-keys' % vps_id, module.params['ssh_key_ids'])
    elif action == 'remove_ssh_key':
        for key_id in module.params['ssh_key_ids']:
            result = api.delete('/vps/%d/ssh-keys/%d' % (vps_id, key_id))
    elif action == 'attach_network':
        result = api.post('/vps/%d/network' % vps_id, {'network_id': module.params['network_id']})
    elif action == 'detach_network':
        result = api.delete('/vps/%d/network' % vps_id)

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
