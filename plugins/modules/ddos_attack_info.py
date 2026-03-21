#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_attack_info
short_description: List DDoS attacks on CubePath Cloud
description:
    - Retrieve DDoS attack history from CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options: {}
'''

EXAMPLES = r'''
- name: List DDoS attacks
  cubepathinc.cloud.ddos_attack_info:
    api_token: "{{ cubepath_token }}"
  register: attacks
'''

RETURN = r'''
attacks:
    description: List of DDoS attacks.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    result = api.get('/ddos-attacks/attacks')
    attacks = result if isinstance(result, list) else result.get('attacks', []) if isinstance(result, dict) else []

    module.exit_json(changed=False, attacks=attacks)


if __name__ == '__main__':
    main()
