#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: template_info
short_description: List OS templates on CubePath Cloud
description:
    - Retrieve available OS templates.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options: {}
'''

EXAMPLES = r'''
- name: List OS templates
  cubepathinc.cloud.template_info:
    api_token: "{{ cubepath_token }}"
  register: templates
'''

RETURN = r'''
templates:
    description: List of OS templates.
    type: list
    returned: always
    elements: dict
applications:
    description: List of applications.
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

    result = api.get('/vps/os')
    module.exit_json(
        changed=False,
        templates=result.get('operating_systems', []),
        applications=result.get('applications', []),
    )


if __name__ == '__main__':
    main()
