#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_replication_grant
short_description: Manage replication grants of an Object Storage bucket on CubePath Cloud
description:
    - A replication grant lets another organization replicate one of its buckets into I(bucket).
      Inside the same organization no grant is needed.
    - A grant is used once, expires (1 to 30 days) and can be revoked until it is used. At most
      5 grants of a bucket can be open at the same time. Versioning must be enabled on the bucket.
    - The token is returned only by the task that creates the grant. Running the task again
      returns the grant without its token, so hand it over (or store it in a vault) the first
      time and run the task with C(no_log=true).
    - With I(state=present) an open grant with the same I(note) is reused; without I(note) every
      run creates a new grant.
    - With I(state=absent) the open grants given by I(uuid) or I(note) are revoked. Grants that
      were used, expired or were already revoked are left as they are.
version_added: "1.7.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the grant.
        type: str
        default: present
        choices: [present, absent]
    bucket:
        description: Name or UUID of the destination bucket the grant authorizes.
        type: str
        required: true
    note:
        description: Free text to recognize the grant, for example who it is for (at most 255 characters).
        type: str
    expires_in_days:
        description: Days until the grant expires if it is not used.
        type: int
        default: 7
    uuid:
        description: UUID of the grant to revoke with I(state=absent).
        type: str
'''

EXAMPLES = r'''
- name: Let a partner replicate into our bucket
  cubepathinc.cloud.object_storage_replication_grant:
    api_token: "{{ cubepath_token }}"
    bucket: partner-inbox
    note: for Acme
    expires_in_days: 3
  register: grant
  no_log: true

- name: Revoke it if it was not used
  cubepathinc.cloud.object_storage_replication_grant:
    api_token: "{{ cubepath_token }}"
    bucket: partner-inbox
    note: for Acme
    state: absent
'''

RETURN = r'''
grant:
    description:
        - The grant (uuid, token_prefix, note, status, expires_at, used_at, revoked_at, created_at).
        - Includes C(token) only when this task created the grant.
    type: dict
    returned: when I(state=present)
revoked:
    description: UUIDs of the grants revoked by this task.
    type: list
    elements: str
    returned: when I(state=absent)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import find_bucket_ref


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        bucket=dict(type='str', required=True),
        note=dict(type='str'),
        expires_in_days=dict(type='int', default=7),
        uuid=dict(type='str'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'absent', ['uuid', 'note'], True)],
        supports_check_mode=True,
    )
    p = module.params

    api = CubePathAPI(module)
    bucket = find_bucket_ref(api, p['bucket'])
    if bucket is None:
        module.fail_json(msg='Bucket %s not found' % p['bucket'])
    path = '/object-storage/buckets/%s/replication-grants' % bucket['uuid']
    grants = api.get(path)
    grants = grants if isinstance(grants, list) else []

    if p['state'] == 'absent':
        targets = [g for g in grants if g.get('status') == 'open'
                   and (p.get('uuid') is None or g.get('uuid') == p['uuid'])
                   and (p.get('note') is None or g.get('note') == p['note'])]
        if not targets:
            module.exit_json(changed=False, revoked=[])
        uuids = [g['uuid'] for g in targets]
        if not module.check_mode:
            for uuid in uuids:
                api.delete('/object-storage/replication-grants/%s' % uuid)
        module.exit_json(changed=True, revoked=uuids)

    if not 1 <= p['expires_in_days'] <= 30:
        module.fail_json(msg='expires_in_days must be between 1 and 30')
    if p.get('note') is not None:
        existing = next((g for g in grants if g.get('status') == 'open' and g.get('note') == p['note']), None)
        if existing is not None:
            module.exit_json(changed=False, grant=existing)
    if module.check_mode:
        module.exit_json(changed=True)

    data = {'expires_in_days': p['expires_in_days']}
    if p.get('note') is not None:
        data['note'] = p['note']
    created = api.post(path, data)
    created.pop('detail', None)
    created.setdefault('status', 'open')
    module.exit_json(changed=True, grant=created)


if __name__ == '__main__':
    main()
