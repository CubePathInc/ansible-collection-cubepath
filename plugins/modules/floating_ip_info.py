#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: floating_ip_info
short_description: List floating IPs on CubePath Cloud
description:
    - Retrieve floating IPs from CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    ip_type:
        description: Filter by IP type.
        type: str
        choices: [IPv4, IPv6]
    location:
        description: Filter by location.
        type: str
'''

EXAMPLES = r'''
- name: List all floating IPs
  cubepathinc.cloud.floating_ip_info:
    api_token: "{{ cubepath_token }}"
  register: ips
'''

RETURN = r'''
single_ips:
    description: List of single floating IPs.
    type: list
    returned: always
    elements: dict
subnets:
    description: List of floating IP subnets.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        ip_type=dict(type='str', choices=['IPv4', 'IPv6']),
        location=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    result = api.get('/floating_ips/organization')
    single_ips = result.get('single_ips', [])
    subnets = result.get('subnets', [])

    ip_type = module.params.get('ip_type')
    location = module.params.get('location')

    if ip_type:
        single_ips = [ip for ip in single_ips if ip.get('type') == ip_type]
    if location:
        single_ips = [ip for ip in single_ips if ip.get('location') == location]
        subnets = [s for s in subnets if s.get('location') == location]

    module.exit_json(changed=False, single_ips=single_ips, subnets=subnets)


if __name__ == '__main__':
    main()
