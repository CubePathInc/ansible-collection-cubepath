#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_backup_settings
short_description: Configure automatic VPS backups on CubePath Cloud
description:
    - Enable, disable or tune the automatic daily backups of a VPS.
    - Settings not given keep their current value.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
    enabled:
        description: Take automatic backups.
        type: bool
    schedule_hour:
        description: Hour of the day (0-23, UTC) the backup runs at.
        type: int
    retention_days:
        description: Days to keep automatic backups (1-7).
        type: int
    max_backups:
        description: Maximum number of automatic backups kept (1-10).
        type: int
'''

EXAMPLES = r'''
- name: Nightly backups at 02:00, keep a week
  cubepathinc.cloud.vps_backup_settings:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
    enabled: true
    schedule_hour: 2
    retention_days: 7
    max_backups: 7
'''

RETURN = r'''
settings:
    description: Backup settings of the VPS (C(enabled), C(schedule_hour), C(retention_days), C(max_backups)).
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec

FIELDS = ('enabled', 'schedule_hour', 'retention_days', 'max_backups')


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        vps_id=dict(type='int', required=True),
        enabled=dict(type='bool'),
        schedule_hour=dict(type='int'),
        retention_days=dict(type='int'),
        max_backups=dict(type='int'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    path = '/vps/%d/backup/settings' % module.params['vps_id']

    current = api.get(path)
    desired = dict((k, current.get(k)) for k in FIELDS)
    for k in FIELDS:
        if module.params.get(k) is not None:
            desired[k] = module.params[k]
    if all(desired[k] == current.get(k) for k in FIELDS):
        module.exit_json(changed=False, settings=current)
    if module.check_mode:
        module.exit_json(changed=True, settings=desired)
    module.exit_json(changed=True, settings=api.put(path, desired))


if __name__ == '__main__':
    main()
