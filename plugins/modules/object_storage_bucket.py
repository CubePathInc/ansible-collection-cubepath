#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_bucket
short_description: Manage Object Storage buckets on CubePath Cloud
description:
    - Create, update or delete S3 compatible Object Storage buckets on CubePath Cloud.
    - Bucket names are unique across all CubePath customers, so the module finds an existing
      bucket by I(name).
    - Buckets are created asynchronously; by default the module waits until the bucket is
      C(active), or gone when I(state=absent).
    - Object Lock (WORM) can only be turned on when the bucket is created, with I(object_lock).
      Its default retention I(object_lock_default) can be changed later.
    - Buckets are private. To serve one publicly, add it as an origin of a CDN zone with
      M(cubepathinc.cloud.cdn_origin) and I(object_storage_bucket_uuid).
version_added: "1.4.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the bucket.
        type: str
        default: present
        choices: [present, absent]
    name:
        description:
            - Bucket name, 3 to 63 lowercase letters, numbers and hyphens.
        type: str
        required: true
    tier:
        description:
            - Storage tier slug or UUID, for example C(infrequent_access).
            - Required when the bucket has to be created.
        type: str
    project_id:
        description:
            - Project the bucket belongs to. Defaults to the organization's first project.
            - Only used when creating the bucket.
        type: int
    versioning:
        description:
            - Object versioning.
            - C(off) is only valid while versioning was never enabled; once enabled it can
              only be C(suspended).
            - A bucket with Object Lock always keeps versioning C(enabled).
        type: str
        choices: [enabled, suspended, 'off']
    protected:
        description: Deletion protection. A protected bucket cannot be deleted.
        type: bool
    tags:
        description:
            - Bucket tags as a dictionary of key and value, to organize and filter buckets.
            - "At most 50 tags; keys 1 to 128 and values 0 to 256 characters of letters, numbers,
              spaces and C(_ . : / = + - @). Keys cannot contain C(=), start or end with a space,
              or start with C(aws:), C(cp:) or C(cubepath:)."
            - When omitted the tags are left unchanged.
            - Bucket tags are not visible through S3 bucket tagging calls, which answer 403.
              Object tags are standard S3 object tagging.
        type: dict
        version_added: "1.6.0"
    purge_tags:
        description:
            - With C(true), tags not listed in I(tags) are removed. With C(false), I(tags) is
              merged with the current tags.
            - Has no effect when I(tags) is omitted.
        type: bool
        default: true
        version_added: "1.6.0"
    object_lock:
        description:
            - Create the bucket with Object Lock, so object versions can be protected from
              deletion and overwrite (WORM) for a retention period.
            - Only used when creating the bucket; it cannot be turned on or off later, and the
              module fails if an existing bucket does not match.
            - A bucket with Object Lock is created with versioning C(enabled) and deletion
              protection on. Requires I(accept_object_lock_terms=true).
        type: bool
        version_added: "1.6.0"
    object_lock_default:
        description:
            - Default retention applied to object versions that have no retention of their own.
              Only for buckets with Object Lock.
            - Give I(mode) and exactly one of I(days) or I(years). Use C({}) to remove the
              default retention. When omitted the current rule is left unchanged.
            - A C(compliance) rule cannot be removed or shortened, not even by CubePath.
            - The module changes the rule when it differs from the bucket's.
        type: dict
        version_added: "1.6.0"
        suboptions:
            mode:
                description:
                    - C(governance) versions can still be deleted by access keys created with
                      I(bypass_governance). C(compliance) versions cannot be deleted by anyone
                      until the retention ends; it must be enabled for the organization by support.
                type: str
                choices: [governance, compliance]
            days:
                description: Retention in days.
                type: int
            years:
                description: Retention in years.
                type: int
    accept_object_lock_terms:
        description:
            - Accept the Object Lock terms. Required to create a bucket with Object Lock, and to
              turn on or lengthen a C(compliance) default retention.
        type: bool
        default: false
        version_added: "1.6.0"
    force:
        description:
            - With I(state=absent), delete the bucket even if it still has objects (they are
              deleted too). Without it, a bucket with objects is not deleted.
            - On a bucket with Object Lock, versions still under retention or legal hold are kept;
              the bucket stays with C(locked_content_kept) and the module fails. Delete it again
              when their retention ends.
        type: bool
        default: false
    bypass_governance:
        description:
            - With I(state=absent) and I(force=true) on a bucket with Object Lock, also delete the
              versions under C(governance) retention. C(compliance) versions are always kept.
        type: bool
        default: false
        version_added: "1.6.0"
    wait:
        description: Wait until the bucket is C(active), or deleted when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 600
'''

EXAMPLES = r'''
- name: Create a bucket
  cubepathinc.cloud.object_storage_bucket:
    api_token: "{{ cubepath_token }}"
    name: my-backups
    tier: infrequent_access
    project_id: 12
    versioning: enabled
    protected: true
    tags:
      env: prod
      team: data
  register: bucket

- name: Add a tag and keep the others
  cubepathinc.cloud.object_storage_bucket:
    api_token: "{{ cubepath_token }}"
    name: my-backups
    tags:
      owner: backups-team
    purge_tags: false

- name: Remove every tag
  cubepathinc.cloud.object_storage_bucket:
    api_token: "{{ cubepath_token }}"
    name: my-backups
    tags: {}

- name: Create a bucket with Object Lock for immutable backups
  cubepathinc.cloud.object_storage_bucket:
    api_token: "{{ cubepath_token }}"
    name: veeam-immutable
    tier: infrequent_access
    object_lock: true
    object_lock_default:
      mode: governance
      days: 30
    accept_object_lock_terms: true

- name: Remove the default retention of a bucket with Object Lock
  cubepathinc.cloud.object_storage_bucket:
    api_token: "{{ cubepath_token }}"
    name: veeam-immutable
    object_lock_default: {}

- name: Delete a bucket and everything in it
  cubepathinc.cloud.object_storage_bucket:
    api_token: "{{ cubepath_token }}"
    name: my-old-bucket
    protected: false
    force: true
    state: absent
'''

RETURN = r'''
bucket:
    description: Bucket details (endpoint, region, status, versioning, tags, object_lock, encryption, size...).
    type: dict
    returned: when I(state=present)
    contains:
        encryption:
            description:
                - Encryption at rest of the bucket's objects (SSE-S3, always on, nothing to configure).
                - Null until the bucket default is applied. C(scope) is C(all_objects), or C(new_objects)
                  while objects uploaded before the default may still be stored unencrypted (they are
                  re-encrypted in the background).
            type: dict
            returned: always
            sample: {"algorithm": "AES256", "scope": "all_objects"}
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import (
    desired_tags, find_bucket, lock_retention, wait_for,
)


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        tier=dict(type='str'),
        project_id=dict(type='int'),
        versioning=dict(type='str', choices=['enabled', 'suspended', 'off']),
        protected=dict(type='bool'),
        tags=dict(type='dict'),
        purge_tags=dict(type='bool', default=True),
        object_lock=dict(type='bool'),
        object_lock_default=dict(type='dict', options=dict(
            mode=dict(type='str', choices=['governance', 'compliance']),
            days=dict(type='int'),
            years=dict(type='int'),
        )),
        accept_object_lock_terms=dict(type='bool', default=False),
        force=dict(type='bool', default=False),
        bypass_governance=dict(type='bool', default=False),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=600),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    name = module.params['name']
    state = module.params['state']
    timeout = module.params['wait_timeout']
    bucket = find_bucket(api, name)
    params = module.params
    lock_default_given = params.get('object_lock_default') is not None
    wanted_rule = None
    if lock_default_given:
        rule = params['object_lock_default']
        if rule.get('mode') is None:
            if rule.get('days') is not None or rule.get('years') is not None:
                module.fail_json(msg='object_lock_default needs a mode with days or years')
        elif (rule.get('days') is None) == (rule.get('years') is None):
            module.fail_json(msg='object_lock_default needs exactly one of days or years')
        else:
            wanted_rule = lock_retention(rule)

    def fetch():
        return find_bucket(api, name)

    if state == 'absent':
        if bucket is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if module.params.get('protected') is False and bucket.get('protected'):
            api.patch('/object-storage/buckets/%s' % bucket['uuid'], {'protected': False})
        if params['bypass_governance'] and not params['force']:
            module.fail_json(msg='bypass_governance can only be used together with force')
        if bucket.get('status') != 'deleting':
            query = None
            if params['force']:
                query = {'force': 'true'}
                if params['bypass_governance']:
                    query['bypass_governance'] = 'true'
            api.delete('/object-storage/buckets/%s' % bucket['uuid'], params=query)
        if module.params['wait']:
            # A bucket that could not be emptied goes back to active with an error message.
            final = wait_for(module, fetch, lambda b: b is None or b.get('status') != 'deleting', timeout)
            if final is not None:
                module.fail_json(msg=final.get('error_message') or 'The bucket was not deleted', bucket=final)
        module.exit_json(changed=True)

    changed = False
    if bucket is None:
        if not module.params.get('tier'):
            module.fail_json(msg='tier is required to create a bucket')
        if params.get('object_lock'):
            if params.get('versioning') not in (None, 'enabled'):
                module.fail_json(msg='A bucket with Object Lock needs versioning enabled')
            if not params['accept_object_lock_terms']:
                module.fail_json(msg='accept_object_lock_terms must be true to create a bucket with Object Lock')
        elif lock_default_given:
            module.fail_json(msg='object_lock_default can only be set on a bucket with object_lock')
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'name': name, 'tier': module.params['tier'], 'versioning': module.params.get('versioning') == 'enabled'}
        if module.params.get('project_id') is not None:
            data['project_id'] = module.params['project_id']
        if module.params.get('tags'):
            data['tags'] = desired_tags(None, module.params['tags'], True)
        if params.get('object_lock'):
            data['versioning'] = True
            data['object_lock'] = True
            data['object_lock_default'] = wanted_rule
            data['accept_object_lock_terms'] = True
        api.post('/object-storage/buckets', data)
        changed = True
        bucket = fetch()

    if module.params['wait'] and bucket and bucket.get('status') == 'pending':
        bucket = wait_for(module, fetch, lambda b: b is not None and b.get('status') != 'pending', timeout)

    lock = bucket.get('object_lock') or {}
    lock_enabled = bool(lock.get('enabled'))
    if params.get('object_lock') is not None and params['object_lock'] != lock_enabled:
        module.fail_json(msg='Object Lock can only be chosen when the bucket is created; bucket %s has it %s'
                         % (name, 'on' if lock_enabled else 'off'), bucket=bucket)
    if lock_default_given and not lock_enabled:
        module.fail_json(msg='object_lock_default can only be set on a bucket with object_lock', bucket=bucket)
    if lock_default_given and not changed and wanted_rule != lock_retention(lock.get('default_retention')):
        if module.check_mode:
            module.exit_json(changed=True, bucket=bucket)
        api.put('/object-storage/buckets/%s/object-lock' % bucket['uuid'], {
            'default_retention': wanted_rule,
            'accept_object_lock_terms': params['accept_object_lock_terms'],
        })
        changed = True
        bucket = fetch()

    update = {}
    versioning = module.params.get('versioning')
    if versioning and versioning != bucket.get('versioning') and not (versioning == 'enabled' and changed):
        update['versioning'] = versioning
    protected = module.params.get('protected')
    if protected is not None and protected != bool(bucket.get('protected')):
        update['protected'] = protected
    if module.params.get('tags') is not None:
        current = bucket.get('tags') or {}
        wanted = desired_tags(current, module.params['tags'], module.params['purge_tags'])
        if wanted != current:
            update['tags'] = wanted
    if update:
        if module.check_mode:
            module.exit_json(changed=True, bucket=bucket)
        api.patch('/object-storage/buckets/%s' % bucket['uuid'], update)
        changed = True
        if module.params['wait'] and 'versioning' in update:
            bucket = wait_for(module, fetch, lambda b: b is not None and b.get('versioning') == versioning and b.get('status') == 'active', timeout)
        else:
            bucket = fetch()

    if bucket and bucket.get('uuid'):
        detail = api.get('/object-storage/buckets/%s' % bucket['uuid'])
        if isinstance(detail, dict) and detail.get('uuid'):
            bucket = detail
    module.exit_json(changed=changed, bucket=bucket)


if __name__ == '__main__':
    main()
