#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: plan_info
short_description: List VPS plans on CubePath Cloud
description:
    - Retrieve available VPS plans and pricing.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    location:
        description: Filter by location.
        type: str
'''

EXAMPLES = r'''
- name: List all plans
  cubepathinc.cloud.plan_info:
    api_token: "{{ cubepath_token }}"
  register: plans
'''

RETURN = r'''
plans:
    description: List of VPS plans.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(location=dict(type='str'))

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    result = api.get('/pricing')
    vps_data = result.get('vps', result)
    locations = vps_data.get('locations', [])

    location = module.params.get('location')
    if location:
        locations = [loc for loc in locations if loc.get('location_name') == location]

    plans = []
    for loc in locations:
        for cluster in loc.get('clusters', []):
            for plan in cluster.get('plans', []):
                plan['location'] = loc.get('location_name')
                plan['cluster'] = cluster.get('cluster_name')
                plans.append(plan)

    module.exit_json(changed=False, plans=plans)


if __name__ == '__main__':
    main()
