#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: nat_gateway_info
short_description: List NAT gateways on CubePath Cloud
description:
    - Retrieve information about NAT gateways on CubePath Cloud.
    - Can list all gateways, a single gateway by UUID, or available gateway plans.
version_added: "1.3.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    nat_gateway_uuid:
        description: UUID of a specific NAT gateway to retrieve.
        type: str
    plans:
        description:
            - When C(true), return available NAT gateway plans instead of gateway instances.
        type: bool
        default: false
'''

EXAMPLES = r'''
- name: List all NAT gateways
  cubepathinc.cloud.nat_gateway_info:
    api_token: "{{ cubepath_token }}"
  register: gateways

- name: Get a specific NAT gateway
  cubepathinc.cloud.nat_gateway_info:
    api_token: "{{ cubepath_token }}"
    nat_gateway_uuid: "abc-123"
  register: gw

- name: List available NAT gateway plans
  cubepathinc.cloud.nat_gateway_info:
    api_token: "{{ cubepath_token }}"
    plans: true
  register: gw_plans
'''

RETURN = r'''
nat_gateways:
    description: List of NAT gateways. Empty when I(plans=true).
    type: list
    returned: when I(plans=false)
    elements: dict
nat_gateway:
    description: Single NAT gateway details. Returned when I(nat_gateway_uuid) is provided.
    type: dict
    returned: when I(nat_gateway_uuid) is set
plans:
    description: List of available NAT gateway plans. Returned when I(plans=true).
    type: list
    returned: when I(plans=true)
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        nat_gateway_uuid=dict(type='str'),
        plans=dict(type='bool', default=False),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    if module.params['plans']:
        result = api.get('/nat-gateway/plans')
        plans = result if isinstance(result, list) else []
        module.exit_json(changed=False, plans=plans)

    nat_gateway_uuid = module.params.get('nat_gateway_uuid')
    if nat_gateway_uuid:
        result = api.get('/nat-gateway/%s' % nat_gateway_uuid)
        module.exit_json(changed=False, nat_gateway=result)

    result = api.get('/nat-gateway/')
    nat_gateways = result if isinstance(result, list) else []
    module.exit_json(changed=False, nat_gateways=nat_gateways)


if __name__ == '__main__':
    main()
