#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_info
short_description: List VPS instances on CubePath Cloud
description:
    - Retrieve information about VPS instances on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by VPS name.
        type: str
    vps_id:
        description: Filter by VPS ID.
        type: int
    project_id:
        description: Filter by project ID.
        type: int
'''

EXAMPLES = r'''
- name: List all VPS
  cubepathinc.cloud.vps_info:
    api_token: "{{ cubepath_token }}"
  register: servers
'''

RETURN = r'''
servers:
    description: List of VPS instances.
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
        vps_id=dict(type='int'),
        project_id=dict(type='int'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    filters = {}
    if module.params.get('project_id'):
        filters['project_id'] = module.params['project_id']

    servers = collect_resources_from_projects(api, 'vps', filters or None)

    name = module.params.get('name')
    vps_id = module.params.get('vps_id')
    if name:
        servers = [s for s in servers if s.get('name') == name]
    if vps_id:
        servers = [s for s in servers if s.get('id') == vps_id]

    module.exit_json(changed=False, servers=servers)


if __name__ == '__main__':
    main()
