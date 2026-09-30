#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_backup_info
short_description: List VPS backups on CubePath Cloud
description:
    - Retrieve the manual and automatic backups of a VPS, newest first, and its automatic backup settings.
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
- name: Backups of a VPS
  cubepathinc.cloud.vps_backup_info:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
  register: backups
'''

RETURN = r'''
backups:
    description: Backups (C(id), C(backup_type), C(status), C(size_gb), C(notes), C(created_at)...).
    type: list
    elements: dict
    returned: always
settings:
    description: Automatic backup settings.
    type: dict
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
    vps_id = module.params['vps_id']

    backups = []
    offset = 0
    while True:
        page = api.get('/vps/%d/backups' % vps_id, params={'limit': 100, 'offset': offset})
        items = as_list(page, 'backups')
        backups.extend(items)
        offset += len(items)
        if not items or offset >= (page or {}).get('total', 0):
            break

    module.exit_json(changed=False, backups=backups, settings=api.get('/vps/%d/backup/settings' % vps_id))


if __name__ == '__main__':
    main()
