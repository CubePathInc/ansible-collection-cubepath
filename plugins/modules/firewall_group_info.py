#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: firewall_group_info
short_description: List firewall groups on CubePath Cloud
description:
    - Retrieve the VPS firewall groups of the organization.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by name.
        type: str
    project_id:
        description: Filter by project.
        type: int
'''

EXAMPLES = r'''
- name: Firewall groups of a project
  cubepathinc.cloud.firewall_group_info:
    api_token: "{{ cubepath_token }}"
    project_id: 12
  register: groups
'''

RETURN = r'''
firewall_groups:
    description: Firewall groups with their rules and the number of VPS they are assigned to.
    type: list
    elements: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        project_id=dict(type='int'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    groups = as_list(api.get('/firewall/groups'))
    if module.params.get('name'):
        groups = [g for g in groups if g.get('name') == module.params['name']]
    if module.params.get('project_id') is not None:
        groups = [g for g in groups if g.get('project_id') == module.params['project_id']]

    module.exit_json(changed=False, firewall_groups=groups)


if __name__ == '__main__':
    main()
