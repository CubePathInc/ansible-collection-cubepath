#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: location_info
short_description: List available locations on CubePath Cloud
description:
    - Retrieve available datacenter locations.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options: {}
'''

EXAMPLES = r'''
- name: List locations
  cubepathinc.cloud.location_info:
    api_token: "{{ cubepath_token }}"
  register: locations
'''

RETURN = r'''
locations:
    description: List of locations.
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

    result = api.get('/pricing')
    vps_data = result.get('vps', result)
    locations = [
        {'name': loc.get('location_name'), 'description': loc.get('description')}
        for loc in vps_data.get('locations', [])
    ]

    module.exit_json(changed=False, locations=locations)


if __name__ == '__main__':
    main()
