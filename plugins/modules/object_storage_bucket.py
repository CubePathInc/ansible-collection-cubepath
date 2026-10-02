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
    force:
        description:
            - With I(state=absent), delete the bucket even if it still has objects (they are
              deleted too). Without it, a bucket with objects is not deleted.
        type: bool
        default: false
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
    description: Bucket details (endpoint, region, status, versioning, tags, size...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import desired_tags, find_bucket, wait_for


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
        force=dict(type='bool', default=False),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=600),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    name = module.params['name']
    state = module.params['state']
    timeout = module.params['wait_timeout']
    bucket = find_bucket(api, name)

    def fetch():
        return find_bucket(api, name)

    if state == 'absent':
        if bucket is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if module.params.get('protected') is False and bucket.get('protected'):
            api.patch('/object-storage/buckets/%s' % bucket['uuid'], {'protected': False})
        if bucket.get('status') != 'deleting':
            params = {'force': 'true'} if module.params['force'] else None
            api.delete('/object-storage/buckets/%s' % bucket['uuid'], params=params)
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
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'name': name, 'tier': module.params['tier'], 'versioning': module.params.get('versioning') == 'enabled'}
        if module.params.get('project_id') is not None:
            data['project_id'] = module.params['project_id']
        if module.params.get('tags'):
            data['tags'] = desired_tags(None, module.params['tags'], True)
        api.post('/object-storage/buckets', data)
        changed = True
        bucket = fetch()

    if module.params['wait'] and bucket and bucket.get('status') == 'pending':
        bucket = wait_for(module, fetch, lambda b: b is not None and b.get('status') != 'pending', timeout)

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
