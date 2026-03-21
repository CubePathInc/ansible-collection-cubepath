#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_zone_info
short_description: List DNS zones on CubePath Cloud
description:
    - Retrieve DNS zones from CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    domain:
        description: Filter by domain name.
        type: str
    project_id:
        description: Filter by project ID.
        type: int
    zone_uuid:
        description: Get a specific zone by UUID.
        type: str
'''

EXAMPLES = r'''
- name: List all DNS zones
  cubepathinc.cloud.dns_zone_info:
    api_token: "{{ cubepath_token }}"
  register: zones
'''

RETURN = r'''
zones:
    description: List of DNS zones.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        domain=dict(type='str'),
        project_id=dict(type='int'),
        zone_uuid=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    zone_uuid = module.params.get('zone_uuid')
    if zone_uuid:
        result = api.get('/dns/zones/%s' % zone_uuid)
        module.exit_json(changed=False, zones=[result])

    params = {}
    if module.params.get('project_id'):
        params['project_id'] = module.params['project_id']

    zones = api.get('/dns/zones', params=params or None)
    if not isinstance(zones, list):
        zones = []

    domain = module.params.get('domain')
    if domain:
        zones = [z for z in zones if z.get('domain') == domain]

    module.exit_json(changed=False, zones=zones)


if __name__ == '__main__':
    main()
