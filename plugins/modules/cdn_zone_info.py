#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_zone_info
short_description: List CDN zones on CubePath Cloud
description:
    - Retrieve CDN zones from CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by zone name.
        type: str
    zone_uuid:
        description: Get a specific zone by UUID.
        type: str
'''

EXAMPLES = r'''
- name: List CDN zones
  cubepathinc.cloud.cdn_zone_info:
    api_token: "{{ cubepath_token }}"
  register: zones
'''

RETURN = r'''
zones:
    description: List of CDN zones.
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
        zone_uuid=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    zone_uuid = module.params.get('zone_uuid')
    if zone_uuid:
        result = api.get('/cdn/zones/%s' % zone_uuid)
        module.exit_json(changed=False, zones=[result])

    result = api.get('/cdn/zones')
    if isinstance(result, list):
        zones = result
    elif isinstance(result, dict):
        zones = result.get('zones', [])
    else:
        zones = []

    name = module.params.get('name')
    if name:
        zones = [z for z in zones if z.get('name') == name]

    module.exit_json(changed=False, zones=zones)


if __name__ == '__main__':
    main()
