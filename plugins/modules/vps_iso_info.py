#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_iso_info
short_description: List the ISO images available to a CubePath VPS
description:
    - Retrieve the ISO images that can be mounted on a VPS and which one is mounted.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
'''

EXAMPLES = r'''
- name: ISOs of a VPS
  cubepathinc.cloud.vps_iso_info:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
  register: isos
'''

RETURN = r'''
isos:
    description: ISO images (C(id), C(name), C(filename), C(file_size), C(is_mounted)).
    type: list
    elements: dict
    returned: always
mounted_iso_id:
    description: ID of the mounted ISO, or null.
    type: str
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(vps_id=dict(type='int', required=True))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    result = api.get('/vps/%d/isos' % module.params['vps_id'])
    module.exit_json(changed=False, isos=as_list(result, 'items'), mounted_iso_id=(result or {}).get('mounted_iso_id'))


if __name__ == '__main__':
    main()
