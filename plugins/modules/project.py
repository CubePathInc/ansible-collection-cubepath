#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: project
short_description: Manage projects on CubePath Cloud
description:
    - Create, update, or delete projects on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the project.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the project.
        type: str
        required: true
    description:
        description: Description of the project.
        type: str
    project_id:
        description: ID of the project. Required when I(state=absent).
        type: int
'''

EXAMPLES = r'''
- name: Create project
  cubepathinc.cloud.project:
    api_token: "{{ cubepath_token }}"
    name: production
    description: "Production environment"
    state: present

- name: Delete project
  cubepathinc.cloud.project:
    api_token: "{{ cubepath_token }}"
    name: old-project
    project_id: 123
    state: absent
'''

RETURN = r'''
project:
    description: Project details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import get_projects


def find_project(api, name):
    for item in get_projects(api):
        p = item.get('project', item)
        if p.get('name') == name:
            return p
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        description=dict(type='str'),
        project_id=dict(type='int'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params['name']

    existing = find_project(api, name)

    if state == 'present':
        if existing:
            desc = module.params.get('description')
            if desc and existing.get('description') != desc:
                if module.check_mode:
                    module.exit_json(changed=True)
                pid = existing.get('id')
                result = api.put('/projects/%d' % pid, {'name': name, 'description': desc})
                module.exit_json(changed=True, project=result)
            module.exit_json(changed=False, project=existing)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {'name': name}
        if module.params.get('description'):
            data['description'] = module.params['description']

        result = api.post('/projects/', data)
        module.exit_json(changed=True, project=result)

    elif state == 'absent':
        project_id = module.params.get('project_id')
        if existing:
            project_id = existing.get('id')
        if not project_id:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/projects/%d' % project_id)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
