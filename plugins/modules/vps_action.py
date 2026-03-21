#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_action
short_description: Perform actions on VPS instances on CubePath Cloud
description:
    - Resize, reinstall, change password, or update a VPS on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description: Action to perform.
        type: str
        required: true
        choices: [resize, reinstall, change_password, update]
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
'''

EXAMPLES = r'''
- name: Resize VPS
  cubepathinc.cloud.vps_action:
    api_token: "{{ cubepath_token }}"
    action: resize
    vps_id: 123
    plan: gp.starter
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
        action=dict(type='str', required=True, choices=['resize', 'reinstall', 'change_password', 'update']),
        vps_id=dict(type='int', required=True),
        plan=dict(type='str'),
        template=dict(type='str'),
        password=dict(type='str', no_log=True),
        label=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('action', 'resize', ['plan']),
            ('action', 'reinstall', ['template']),
            ('action', 'change_password', ['password']),
        ],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    vps_id = module.params['vps_id']

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s VPS %d' % (action, vps_id))

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

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
