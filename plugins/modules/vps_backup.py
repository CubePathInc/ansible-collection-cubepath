#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_backup
short_description: Create, restore or delete VPS backups on CubePath Cloud
description:
    - Take a manual backup of a VPS, restore a VPS from a backup, or delete a backup.
    - Automatic backups are configured with M(cubepathinc.cloud.vps_backup_settings) and listed with
      M(cubepathinc.cloud.vps_backup_info).
    - With I(state=present) and I(notes), a completed or running backup with the same notes counts as
      already taken, which makes the task idempotent. Without I(notes) every run takes a new backup.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description:
            - C(present) takes a manual backup, C(absent) deletes I(backup_id), C(restored) restores the VPS
              from I(backup_id), overwriting its disk.
        type: str
        default: present
        choices: [present, absent, restored]
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
    backup_id:
        description: ID of the backup. Required when I(state=absent) or I(state=restored).
        type: int
    notes:
        description: Notes of a new backup (up to 500 characters).
        type: str
    wait:
        description: Wait until a new backup is completed.
        type: bool
        default: false
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 3600
'''

EXAMPLES = r'''
- name: Backup before the upgrade
  cubepathinc.cloud.vps_backup:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
    notes: before-upgrade-2026-10
    wait: true
  register: backup

- name: Roll back
  cubepathinc.cloud.vps_backup:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
    backup_id: "{{ backup.backup.id }}"
    state: restored
'''

RETURN = r'''
backup:
    description: Backup details (C(id), C(status), C(progress), C(size_gb), C(notes)...).
    type: dict
    returned: when I(state=present)
result:
    description: API response.
    type: dict
    returned: when I(state=restored)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, wait_for


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent', 'restored']),
        vps_id=dict(type='int', required=True),
        backup_id=dict(type='int'),
        notes=dict(type='str'),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(type='int', default=3600),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'absent', ['backup_id']), ('state', 'restored', ['backup_id'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    p = module.params
    base = '/vps/%d/backups' % p['vps_id']

    def backups():
        return as_list(api.get(base, params={'limit': 500}), 'backups')

    def fetch(backup_id):
        return next((b for b in backups() if b.get('id') == backup_id), None)

    if p['state'] == 'absent':
        if fetch(p['backup_id']) is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s/%d' % (base, p['backup_id']))
        module.exit_json(changed=True)

    if p['state'] == 'restored':
        if fetch(p['backup_id']) is None:
            module.fail_json(msg='Backup %d of VPS %d not found' % (p['backup_id'], p['vps_id']))
        if module.check_mode:
            module.exit_json(changed=True)
        result = api.post('%s/%d/restore' % (base, p['backup_id']), {'confirm': True})
        module.exit_json(changed=True, result=result)

    backup = None
    if p.get('notes'):
        backup = next((b for b in backups() if b.get('notes') == p['notes'] and b.get('status') != 'failed'), None)
    changed = backup is None
    if backup is None:
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'notes': p['notes']} if p.get('notes') else {}
        backup = api.post(base, data)
    if p['wait'] and backup.get('status') in ('pending', 'in_progress'):
        backup = wait_for(module, lambda: fetch(backup['id']), lambda b: b is not None and b.get('status') not in ('pending', 'in_progress'),
                          p['wait_timeout'], interval=15)
        if backup.get('status') == 'failed':
            module.fail_json(msg='The backup failed: %s' % (backup.get('error_message') or 'unknown error'), backup=backup)
    module.exit_json(changed=changed, backup=backup)


if __name__ == '__main__':
    main()
