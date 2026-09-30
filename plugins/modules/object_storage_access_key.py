#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_access_key
short_description: Manage Object Storage access keys on CubePath Cloud
description:
    - Create or revoke S3 access keys for CubePath Object Storage.
    - Keys are found by I(name) (within I(project_id) and I(tier) when given). An existing
      key is never changed; revoke it and create a new one to change its permission or buckets.
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
        description: What the key can do.
        type: str
        default: read_write
        choices: [read_write, read_only]
    buckets:
        description:
            - Limit the key to these buckets (names or UUIDs) of the same project and tier.
            - Omit it to give the key access to every bucket of the project in the tier,
              present and future.
        type: list
        elements: str
    expires_at:
        description: Expiry time in UTC (ISO 8601). The key stops working at that time.
        type: str
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
        - Key details (access key ID, permission, buckets, endpoint, region, status).
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


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        tier=dict(type='str'),
        project_id=dict(type='int'),
        permission=dict(type='str', default='read_write', choices=['read_write', 'read_only']),
        buckets=dict(type='list', elements='str'),
        expires_at=dict(type='str'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=300),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

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
        module.exit_json(changed=False, access_key=key)

    if not tier:
        module.fail_json(msg='tier is required to create an access key')
    if module.check_mode:
        module.exit_json(changed=True)

    data = {'name': name, 'tier': tier, 'permission': module.params['permission']}
    if project_id is not None:
        data['project_id'] = project_id
    if module.params.get('buckets'):
        data['bucket_uuids'] = resolve_bucket_uuids(module, api, module.params['buckets'])
    if module.params.get('expires_at'):
        data['expires_at'] = module.params['expires_at']
    created = api.post('/object-storage/keys', data)

    if module.params['wait'] and created.get('uuid'):
        current = wait_for(module, fetch_by_uuid(created['uuid']), lambda k: k is not None and k.get('status') != 'pending', timeout)
        created.update(current)
    created.pop('detail', None)
    module.exit_json(changed=True, access_key=created)


if __name__ == '__main__':
    main()
