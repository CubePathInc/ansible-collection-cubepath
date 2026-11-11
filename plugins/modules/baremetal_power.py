#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: baremetal_power
short_description: Manage baremetal power state on CubePath Cloud
description:
    - Start, stop, or restart a baremetal server on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    baremetal_id:
        description: Number or uuid of the baremetal server.
        type: str
        required: true
    state:
        description: Desired power state.
        type: str
        required: true
        choices: [started, stopped, restarted]
'''

EXAMPLES = r'''
- name: Start baremetal
  cubepathinc.cloud.baremetal_power:
    api_token: "{{ cubepath_token }}"
    baremetal_id: 10
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
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_baremetal import baremetal_ref_param

POWER_MAP = {
    'started': 'start_metal',
    'stopped': 'stop_metal',
    'restarted': 'restart_metal',
}


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        baremetal_id=dict(type='str', required=True),
        state=dict(type='str', required=True, choices=['started', 'stopped', 'restarted']),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    baremetal_id = baremetal_ref_param(module)
    state = module.params['state']
    action = POWER_MAP[state]

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s baremetal %s' % (action, baremetal_id))

    api.post('/baremetal/%s/power/%s' % (baremetal_id, action))
    module.exit_json(changed=True, msg='Baremetal %s power action %s executed' % (baremetal_id, action))


if __name__ == '__main__':
    main()
