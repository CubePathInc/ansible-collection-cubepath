#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ssh_key_info
short_description: List SSH keys on CubePath Cloud
description:
    - Retrieve SSH keys from CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options: {}
'''

EXAMPLES = r'''
- name: List SSH keys
  cubepathinc.cloud.ssh_key_info:
    api_token: "{{ cubepath_token }}"
  register: keys
'''

RETURN = r'''
ssh_keys:
    description: List of SSH keys.
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

    result = api.get('/sshkey/user/sshkeys')
    if isinstance(result, dict):
        keys = result.get('sshkeys', [])
    else:
        keys = result if isinstance(result, list) else []

    module.exit_json(changed=False, ssh_keys=keys)


if __name__ == '__main__':
    main()
