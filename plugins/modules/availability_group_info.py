#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: availability_group_info
short_description: List VPS availability groups on CubePath Cloud
description:
    - Retrieve availability groups with their VPS, from one project or from every project of the organization.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    project_id:
        description: Only groups of this project.
        type: int
    location:
        description: Only groups of this location.
        type: str
    name:
        description: Filter by name.
        type: str
    uuid:
        description: Filter by UUID.
        type: str
'''

EXAMPLES = r'''
- name: Availability groups of a project
  cubepathinc.cloud.availability_group_info:
    api_token: "{{ cubepath_token }}"
    project_id: 12
  register: groups
'''

RETURN = r'''
availability_groups:
    description: Availability groups with their VPS (C(vps_list)).
    type: list
    elements: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, get_projects


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        project_id=dict(type='int'),
        location=dict(type='str'),
        name=dict(type='str'),
        uuid=dict(type='str'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    p = module.params

    if p.get('project_id') is not None:
        project_ids = [p['project_id']]
    else:
        project_ids = [(proj.get('project') or {}).get('id') for proj in get_projects(api)]

    groups = []
    for project_id in project_ids:
        if project_id is None:
            continue
        result = api.get('/vps/availability-groups/project/%d' % project_id, params={'location_name': p.get('location')})
        groups.extend(as_list(result, 'groups'))
    if p.get('name'):
        groups = [g for g in groups if g.get('name') == p['name']]
    if p.get('uuid'):
        groups = [g for g in groups if g.get('uuid') == p['uuid']]

    module.exit_json(changed=False, availability_groups=groups)


if __name__ == '__main__':
    main()
