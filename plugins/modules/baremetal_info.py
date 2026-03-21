#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: baremetal_info
short_description: List baremetal servers on CubePath Cloud
description:
    - Retrieve information about baremetal servers on CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    hostname:
        description: Filter by hostname.
        type: str
    baremetal_id:
        description: Filter by baremetal ID.
        type: int
    project_id:
        description: Filter by project ID.
        type: int
'''

EXAMPLES = r'''
- name: List all baremetals
  cubepathinc.cloud.baremetal_info:
    api_token: "{{ cubepath_token }}"
  register: servers
'''

RETURN = r'''
servers:
    description: List of baremetal servers.
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
        hostname=dict(type='str'),
        baremetal_id=dict(type='int'),
        project_id=dict(type='int'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    filters = {}
    if module.params.get('project_id'):
        filters['project_id'] = module.params['project_id']

    servers = collect_resources_from_projects(api, 'baremetals', filters or None)

    hostname = module.params.get('hostname')
    baremetal_id = module.params.get('baremetal_id')
    if hostname:
        servers = [s for s in servers if s.get('hostname') == hostname]
    if baremetal_id:
        servers = [s for s in servers if s.get('id') == baremetal_id]

    module.exit_json(changed=False, servers=servers)


if __name__ == '__main__':
    main()
