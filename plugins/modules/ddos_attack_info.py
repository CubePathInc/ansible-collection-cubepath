#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_attack_info
short_description: List DDoS attacks on CubePath Cloud
description:
    - Retrieve DDoS attack history from CubePath Cloud.
    - With I(attack_id), also return the detailed breakdown and the traffic graph of that attack.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    attack_id:
        description: ID of one attack (from RV(attacks)) to return in detail.
        type: int
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: List DDoS attacks
  cubepathinc.cloud.ddos_attack_info:
    api_token: "{{ cubepath_token }}"
  register: attacks

- name: Detail and traffic graph of one attack
  cubepathinc.cloud.ddos_attack_info:
    api_token: "{{ cubepath_token }}"
    attack_id: 4211
  register: attack
'''

RETURN = r'''
attacks:
    description: List of DDoS attacks.
    type: list
    returned: always
    elements: dict
details:
    description: Detailed breakdown of the attack given in I(attack_id), as reported by the mitigation platform.
    type: raw
    returned: when I(attack_id) is set
    version_added: "1.5.0"
traffic_graph:
    description: Traffic time series of the attack given in I(attack_id).
    type: raw
    returned: when I(attack_id) is set
    version_added: "1.5.0"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(attack_id=dict(type='int'))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    result = api.get('/ddos-attacks/attacks')
    attacks = result if isinstance(result, list) else result.get('attacks', []) if isinstance(result, dict) else []

    result = {'changed': False, 'attacks': attacks}
    attack_id = module.params.get('attack_id')
    if attack_id is not None:
        result['details'] = api.get('/ddos-attacks/attacks/%d/details' % attack_id)
        result['traffic_graph'] = api.get('/ddos-attacks/attacks/%d/traffic-graph' % attack_id)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
