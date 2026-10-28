#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_access_key
short_description: Manage Object Storage access keys on CubePath Cloud
description:
    - Create, update or revoke S3 access keys for CubePath Object Storage.
    - Keys are found by I(name) (within I(project_id) and I(tier) when given). An existing
      key is updated in place, keeping its access key ID and secret, when I(permission),
      I(buckets), I(all_buckets) or I(bypass_governance) are given and differ. Options you leave out
      are not managed on an existing key. I(tier), I(project_id) and I(expires_at) are fixed
      when the key is created.
    - The secret access key is returned only by the task that creates the key. Running the
      task again returns the key without its secret, so store it the first time (for example
      in a vault) and run the task with C(no_log=true).
version_added: "1.4.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the key.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Key name.
        type: str
        required: true
    tier:
        description:
            - Storage tier slug or UUID, for example C(infrequent_access).
            - Required when the key has to be created.
        type: str
    project_id:
        description: Project of the key. Defaults to the organization's first project.
        type: int
    permission:
        description:
            - What the key can do.
            - When the key is created it defaults to C(read_write). On an existing key, if you leave it
              out the permission is not changed.
        type: str
        choices: [read_write, read_only]
    buckets:
        description:
            - Limit the key to these buckets (names or UUIDs) of the same project and tier.
            - Omit it to give the key access to every bucket of the project in the tier,
              present and future, when the key is created. On an existing key, if you leave it out
              the buckets are not changed; use I(all_buckets) to give it every bucket.
            - Cannot be an empty list on an existing key (use I(all_buckets)). At most 20 buckets.
        type: list
        elements: str
    all_buckets:
        description:
            - Give the key access to every bucket of the project in the tier, present and future.
            - On an existing key limited to some buckets, this widens it to all of them.
            - On creation it is the same as leaving I(buckets) out.
        type: bool
        version_added: "1.7.0"
    expires_at:
        description: Expiry time in UTC (ISO 8601). The key stops working at that time.
        type: str
    bypass_governance:
        description:
            - Let the key delete or overwrite object versions under C(governance) retention in
              buckets with Object Lock, by sending the C(x-amz-bypass-governance-retention) header.
              C(compliance) versions can never be deleted before their date.
            - Only for C(read_write) keys. Turning a key with the bypass to C(read_only) needs
              I(bypass_governance=false) in the same task.
            - Defaults to C(false) when the key is created. On an existing key, if you leave it out
              the setting is not changed.
        type: bool
        version_added: "1.6.0"
    wait:
        description: Wait until the key is usable (C(active)), or revoked when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 300
'''

EXAMPLES = r'''
- name: Create a read only key for one bucket
  cubepathinc.cloud.object_storage_access_key:
    api_token: "{{ cubepath_token }}"
    name: web-reader
    tier: infrequent_access
    project_id: 12
    permission: read_only
    buckets:
      - my-assets
  register: key
  no_log: true

- name: Create a key that can remove governance locked versions
  cubepathinc.cloud.object_storage_access_key:
    api_token: "{{ cubepath_token }}"
    name: backup-admin
    tier: infrequent_access
    permission: read_write
    bypass_governance: true
  register: admin_key
  no_log: true

- name: Limit an existing key to two buckets and make it read only
  cubepathinc.cloud.object_storage_access_key:
    api_token: "{{ cubepath_token }}"
    name: web-reader
    project_id: 12
    permission: read_only
    buckets:
      - my-assets
      - my-logs
  no_log: true

- name: Give an existing key access to every bucket of its project in the tier
  cubepathinc.cloud.object_storage_access_key:
    api_token: "{{ cubepath_token }}"
    name: web-reader
    project_id: 12
    all_buckets: true
  no_log: true

- name: Revoke a key
  cubepathinc.cloud.object_storage_access_key:
    api_token: "{{ cubepath_token }}"
    name: web-reader
    project_id: 12
    state: absent
'''

RETURN = r'''
access_key:
    description:
        - Key details (access key ID, permission, bucket_scope, endpoint, region, status,
          bypass_governance). After an update it is read again, so it has the new values
          (RustFS enforces them a few seconds later).
        - Includes C(secret_access_key) only when this task created the key.
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import find_bucket, find_key, list_keys, wait_for


def resolve_bucket_uuids(module, api, refs):
    uuids = []
    for ref in refs:
        bucket = find_bucket(api, ref)
        if bucket is None:
            bucket = next((b for b in api.get('/object-storage/buckets') or [] if b.get('uuid') == ref), None)
        if bucket is None:
            module.fail_json(msg='Bucket %s not found' % ref)
        uuids.append(bucket['uuid'])
    return uuids


def current_bucket_uuids(key):
    """The uuids a key is limited to, or None for every bucket (bucket_scope null)."""
    scope = key.get('bucket_scope')
    if scope is None:
        return None
    return set(b.get('uuid') if isinstance(b, dict) else b for b in scope)


def key_changes(module, api, key):
    """The PATCH body for the options the user set that differ from the key, {} when it is converged."""
    p = module.params
    if p.get('buckets') is not None and not p['buckets'] and not p.get('all_buckets'):
        module.fail_json(msg='buckets cannot be empty on an existing key: use all_buckets: true for every bucket')
    changes = {}
    if p.get('permission') and p['permission'] != key.get('permission'):
        changes['permission'] = p['permission']
    if p.get('bypass_governance') is not None and p['bypass_governance'] != bool(key.get('bypass_governance')):
        changes['bypass_governance'] = p['bypass_governance']
    if p.get('all_buckets'):
        if current_bucket_uuids(key) is not None:
            changes['bucket_uuids'] = None
    elif p.get('buckets'):
        wanted = resolve_bucket_uuids(module, api, p['buckets'])
        if current_bucket_uuids(key) != set(wanted):
            changes['bucket_uuids'] = wanted
    final_permission = changes.get('permission', key.get('permission'))
    final_bypass = changes.get('bypass_governance', bool(key.get('bypass_governance')))
    if changes and final_bypass and final_permission != 'read_write':
        module.fail_json(msg='bypass_governance can only be given to read_write keys: set bypass_governance: false '
                             'to make the key read_only')
    return changes


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        tier=dict(type='str'),
        project_id=dict(type='int'),
        permission=dict(type='str', choices=['read_write', 'read_only']),
        buckets=dict(type='list', elements='str'),
        all_buckets=dict(type='bool'),
        expires_at=dict(type='str'),
        bypass_governance=dict(type='bool'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=300),
    )
    module = AnsibleModule(argument_spec=argument_spec, mutually_exclusive=[('buckets', 'all_buckets')], supports_check_mode=True)

    api = CubePathAPI(module)
    name = module.params['name']
    project_id = module.params.get('project_id')
    tier = module.params.get('tier')
    timeout = module.params['wait_timeout']
    key = find_key(api, name, project_id, tier)

    def fetch_by_uuid(uuid):
        return lambda: next((k for k in list_keys(api) if k.get('uuid') == uuid), None)

    if module.params['state'] == 'absent':
        if key is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if key.get('status') != 'deleting':
            api.delete('/object-storage/keys/%s' % key['uuid'])
        if module.params['wait']:
            wait_for(module, fetch_by_uuid(key['uuid']), lambda k: k is None, timeout)
        module.exit_json(changed=True)

    if key is not None:
        if module.params['wait'] and key.get('status') == 'pending':
            key = wait_for(module, fetch_by_uuid(key['uuid']), lambda k: k is not None and k.get('status') != 'pending', timeout)
        changes = key_changes(module, api, key)
        if not changes:
            module.exit_json(changed=False, access_key=key)
        before = dict((f, key.get(f)) for f in ('permission', 'bypass_governance'))
        before['bucket_uuids'] = None if current_bucket_uuids(key) is None else sorted(current_bucket_uuids(key))
        diff = {'before': before, 'after': dict(before, **changes)}
        if module.check_mode:
            module.exit_json(changed=True, access_key=key, diff=diff)
        api.patch('/object-storage/keys/%s' % key['uuid'], changes)
        key = fetch_by_uuid(key['uuid'])() or key
        if module.params['wait'] and key.get('status') == 'pending':
            key = wait_for(module, fetch_by_uuid(key['uuid']), lambda k: k is not None and k.get('status') != 'pending', timeout)
        module.exit_json(changed=True, access_key=key, diff=diff)

    if not tier:
        module.fail_json(msg='tier is required to create an access key')
    permission = module.params['permission'] or 'read_write'
    if module.params['bypass_governance'] and permission != 'read_write':
        module.fail_json(msg='bypass_governance can only be given to read_write keys')
    if module.check_mode:
        module.exit_json(changed=True)

    data = {'name': name, 'tier': tier, 'permission': permission}
    if project_id is not None:
        data['project_id'] = project_id
    if module.params.get('buckets'):
        data['bucket_uuids'] = resolve_bucket_uuids(module, api, module.params['buckets'])
    if module.params.get('expires_at'):
        data['expires_at'] = module.params['expires_at']
    if module.params['bypass_governance']:
        data['bypass_governance'] = True
    created = api.post('/object-storage/keys', data)

    if module.params['wait'] and created.get('uuid'):
        current = wait_for(module, fetch_by_uuid(created['uuid']), lambda k: k is not None and k.get('status') != 'pending', timeout)
        created.update(current)
    created.pop('detail', None)
    module.exit_json(changed=True, access_key=created)


if __name__ == '__main__':
    main()
