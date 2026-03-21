#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: network_info
short_description: List private networks on CubePath Cloud
description:
    - Retrieve information about private networks on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by network name.
        type: str
    network_id:
        description: Filter by network ID.
        type: int
    project_id:
        description: Filter by project ID.
        type: int
    location:
        description: Filter by location.
        type: str
'''

EXAMPLES = r'''
- name: List all networks
  cubepathinc.cloud.network_info:
    api_token: "{{ cubepath_token }}"
  register: networks
'''

RETURN = r'''
networks:
    description: List of networks.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import collect_resources_from_projects


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        network_id=dict(type='int'),
        project_id=dict(type='int'),
        location=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    filters = {}
    if module.params.get('project_id'):
        filters['project_id'] = module.params['project_id']
    if module.params.get('location'):
        filters['location_name'] = module.params['location']

    networks = collect_resources_from_projects(api, 'networks', filters or None)

    name = module.params.get('name')
    network_id = module.params.get('network_id')
    if name:
        networks = [n for n in networks if n.get('name') == name]
    if network_id:
        networks = [n for n in networks if n.get('id') == network_id]

    module.exit_json(changed=False, networks=networks)


if __name__ == '__main__':
    main()
