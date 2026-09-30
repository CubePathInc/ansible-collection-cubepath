#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer_info
short_description: List load balancers on CubePath Cloud
description:
    - Retrieve load balancers from CubePath Cloud.
    - Optionally return the load balancer plans per location.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by name.
        type: str
    lb_uuid:
        description: Filter by UUID.
        type: str
    gather:
        description: Extra information to return.
        type: list
        elements: str
        default: []
        choices: [plans]
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: List load balancers
  cubepathinc.cloud.loadbalancer_info:
    api_token: "{{ cubepath_token }}"
  register: lbs
'''

RETURN = r'''
loadbalancers:
    description: List of load balancers.
    type: list
    returned: always
    elements: dict
plans:
    description: Load balancer plans grouped by location, with price and limits.
    type: list
    returned: when C(plans) is in I(gather)
    elements: dict
    version_added: "1.5.0"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        lb_uuid=dict(type='str'),
        gather=dict(type='list', elements='str', default=[], choices=['plans']),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    lbs = api.get('/loadbalancer/')
    if not isinstance(lbs, list):
        lbs = []

    name = module.params.get('name')
    lb_uuid = module.params.get('lb_uuid')
    if name:
        lbs = [lb for lb in lbs if lb.get('name') == name]
    if lb_uuid:
        lbs = [lb for lb in lbs if lb.get('uuid') == lb_uuid]

    result = {'changed': False, 'loadbalancers': lbs}
    if 'plans' in module.params['gather']:
        plans = api.get('/loadbalancer/plans')
        result['plans'] = plans if isinstance(plans, list) else []
    module.exit_json(**result)


if __name__ == '__main__':
    main()
