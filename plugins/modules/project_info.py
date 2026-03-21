#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: project_info
short_description: List projects on CubePath Cloud
description:
    - Retrieve information about projects on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by project name.
        type: str
    project_id:
        description: Filter by project ID.
        type: int
'''

EXAMPLES = r'''
- name: List all projects
  cubepathinc.cloud.project_info:
    api_token: "{{ cubepath_token }}"
  register: projects
'''

RETURN = r'''
projects:
    description: List of projects.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import get_projects


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        project_id=dict(type='int'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    projects = []
    for item in get_projects(api):
        p = item.get('project', item)
        p['vps_count'] = len(item.get('vps', []))
        p['network_count'] = len(item.get('networks', []))
        p['baremetal_count'] = len(item.get('baremetals', []))
        projects.append(p)

    name = module.params.get('name')
    project_id = module.params.get('project_id')
    if name:
        projects = [p for p in projects if p.get('name') == name]
    if project_id:
        projects = [p for p in projects if p.get('id') == project_id]

    module.exit_json(changed=False, projects=projects)


if __name__ == '__main__':
    main()
