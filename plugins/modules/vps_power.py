#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_power
short_description: Manage VPS power state on CubePath Cloud
description:
    - Start, stop, restart, or reset a VPS on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
    state:
        description: Desired power state.
        type: str
        required: true
        choices: [started, stopped, restarted, reset]
'''

EXAMPLES = r'''
- name: Start VPS
  cubepathinc.cloud.vps_power:
    api_token: "{{ cubepath_token }}"
    vps_id: 123
    state: started
'''

RETURN = r'''
msg:
    description: Result message.
    type: str
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec

POWER_MAP = {
    'started': 'start_vps',
    'stopped': 'stop_vps',
    'restarted': 'restart_vps',
    'reset': 'reset_vps',
}


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        vps_id=dict(type='int', required=True),
        state=dict(type='str', required=True, choices=['started', 'stopped', 'restarted', 'reset']),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    vps_id = module.params['vps_id']
    state = module.params['state']
    action = POWER_MAP[state]

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s VPS %d' % (action, vps_id))

    api.post('/vps/%d/power/%s' % (vps_id, action))
    module.exit_json(changed=True, msg='VPS %d power action %s executed' % (vps_id, action))


if __name__ == '__main__':
    main()
