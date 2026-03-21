#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer_info
short_description: List load balancers on CubePath Cloud
description:
    - Retrieve load balancers from CubePath Cloud.
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
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        lb_uuid=dict(type='str'),
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

    module.exit_json(changed=False, loadbalancers=lbs)


if __name__ == '__main__':
    main()
