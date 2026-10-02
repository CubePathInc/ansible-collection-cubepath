#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_replication
short_description: Manage the replication of an Object Storage bucket on CubePath Cloud
description:
    - Replicate the new objects of a bucket, asynchronously, to another CubePath bucket of the same
      tier or to an external S3 compatible bucket over HTTPS (port 443 only).
    - A bucket replicates to one destination at most, so the replication is found by
      I(source_bucket). Versioning must be enabled on the source bucket (and on a CubePath
      destination). Buckets with Object Lock cannot be replication sources.
    - A CubePath destination lives on the same cluster as the source, so it is not a disaster
      recovery copy. Use an external destination for an off site copy.
    - Replicating to an external destination is billed as egress of the source bucket.
    - A bucket of another organization can only be used as destination with a grant token
      created by its owner (M(cubepathinc.cloud.object_storage_replication_grant)), and is given
      by its UUID.
    - The module is idempotent. It compares the rules and I(enabled) with the replication's and
      only changes what differs. The destination cannot be changed; the module fails when it
      differs, remove the replication (I(state=absent)) and create it again.
    - The external secret access key is never returned by the API, so it is sent only when the
      replication is created, when I(destination.access_key_id) differs from the stored one, or
      when I(update_credentials=true).
version_added: "1.7.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the replication.
        type: str
        default: present
        choices: [present, absent]
    source_bucket:
        description: Name or UUID of the source bucket.
        type: str
        required: true
    destination:
        description: Where to replicate. Required with I(state=present).
        type: dict
        suboptions:
            type:
                description: C(cubepath) for a CubePath bucket, C(external) for another S3 compatible provider.
                type: str
                required: true
                choices: [cubepath, external]
            bucket:
                description:
                    - C(cubepath), name or UUID of the destination bucket (UUID for a bucket of another organization).
                    - C(external), name of the destination bucket at the provider.
                type: str
                required: true
            grant_token:
                description: C(cubepath), grant token of the destination owner when the bucket belongs to another organization.
                type: str
            provider:
                description: C(external), the provider (informative).
                type: str
                choices: [aws, wasabi, other]
            endpoint:
                description: C(external), public HTTPS host of the provider, without scheme, for example C(s3.eu-west-1.amazonaws.com).
                type: str
            region:
                description: C(external), region of the destination bucket.
                type: str
            path_style:
                description: C(external), path style addressing.
                type: str
                default: auto
                choices: [auto, 'on', 'off']
            access_key_id:
                description: C(external), access key ID with write access to the destination bucket.
                type: str
            secret_access_key:
                description: C(external), secret of I(destination.access_key_id). Never returned.
                type: str
    prefix:
        description: Only replicate the objects under this prefix. Not together with I(tags).
        type: str
    tags:
        description: Only replicate the objects that carry all these tags (at most 10). Not together with I(prefix).
        type: dict
    delete_marker_replication:
        description: Replicate delete markers. Not together with I(tags).
        type: bool
        default: false
    delete_replication:
        description: Replicate the deletion of a specific object version.
        type: bool
        default: false
    existing_objects:
        description: Copy the objects the bucket already holds when the replication is created.
        type: bool
        default: true
    enabled:
        description: C(false) pauses the replication, C(true) resumes it.
        type: bool
        default: true
    update_credentials:
        description:
            - Send I(destination.access_key_id) and I(destination.secret_access_key) again, to rotate
              the secret of an external destination. The task then reports a change on every run.
        type: bool
        default: false
    wait:
        description: Wait until the replication is configured (C(active)), or removed when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 600
'''

EXAMPLES = r'''
- name: Replicate a bucket to another bucket of the organization
  cubepathinc.cloud.object_storage_replication:
    api_token: "{{ cubepath_token }}"
    source_bucket: photos
    destination:
      type: cubepath
      bucket: photos-replica

- name: Off site copy to an external provider
  cubepathinc.cloud.object_storage_replication:
    api_token: "{{ cubepath_token }}"
    source_bucket: photos
    destination:
      type: external
      provider: aws
      endpoint: s3.eu-west-1.amazonaws.com
      region: eu-west-1
      bucket: acme-photos-backup
      access_key_id: "{{ aws_key }}"
      secret_access_key: "{{ aws_secret }}"
    prefix: img/
  no_log: true

- name: Replicate into a bucket of another organization with its owner's grant
  cubepathinc.cloud.object_storage_replication:
    api_token: "{{ cubepath_token }}"
    source_bucket: photos
    destination:
      type: cubepath
      bucket: 7a0c9a52-0b6e-4bd8-9f8e-0f3c2d1b4a77
      grant_token: "{{ partner_grant }}"
  no_log: true

- name: Pause it
  cubepathinc.cloud.object_storage_replication:
    api_token: "{{ cubepath_token }}"
    source_bucket: photos
    destination:
      type: cubepath
      bucket: photos-replica
    enabled: false

- name: Remove it (the data already replicated stays in the destination)
  cubepathinc.cloud.object_storage_replication:
    api_token: "{{ cubepath_token }}"
    source_bucket: photos
    state: absent
'''

RETURN = r'''
replication:
    description:
        - The replication (status, pause reason, source, destination, rules, health, backfill and,
          once active, metrics). The external access key ID is masked and the secret is never returned.
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import (
    find_bucket_ref, find_outgoing_replication, list_replications, normalize_endpoint, replication_tags, wait_for,
)

CUBEPATH_ONLY = ('grant_token',)
EXTERNAL_ONLY = ('provider', 'endpoint', 'region', 'access_key_id', 'secret_access_key')


def check_destination_params(module, dest):
    if dest['type'] == 'cubepath':
        extra = [k for k in EXTERNAL_ONLY if dest.get(k) is not None]
        if extra:
            module.fail_json(msg='destination.%s does not apply to a cubepath destination' % extra[0])
    else:
        extra = [k for k in CUBEPATH_ONLY if dest.get(k) is not None]
        if extra:
            module.fail_json(msg='destination.%s does not apply to an external destination' % extra[0])
        missing = [k for k in ('endpoint', 'region', 'access_key_id', 'secret_access_key') if not dest.get(k)]
        if missing:
            module.fail_json(msg='destination.%s is required for an external destination' % missing[0])


def destination_body(module, api, dest):
    if dest['type'] == 'cubepath':
        bucket = find_bucket_ref(api, dest['bucket'])
        if bucket is None and not dest.get('grant_token'):
            module.fail_json(msg='Destination bucket %s not found (a bucket of another organization needs its UUID '
                                 'and destination.grant_token)' % dest['bucket'])
        body = {'type': 'cubepath', 'bucket_uuid': bucket['uuid'] if bucket else dest['bucket']}
        if dest.get('grant_token') and bucket is None:
            body['grant_token'] = dest['grant_token']
        return body
    body = {
        'type': 'external',
        'endpoint': dest['endpoint'],
        'region': dest['region'],
        'bucket': dest['bucket'],
        'path_style': dest.get('path_style') or 'auto',
        'access_key_id': dest['access_key_id'],
        'secret_access_key': dest['secret_access_key'],
    }
    if dest.get('provider'):
        body['provider'] = dest['provider']
    return body


def destination_differs(module, api, current, dest):
    """The name of the first destination field that differs from the replication's, or None."""
    cur = current.get('destination') or {}
    if cur.get('type') != dest['type']:
        return 'type'
    if dest['type'] == 'cubepath':
        bucket = find_bucket_ref(api, dest['bucket'])
        if bucket is not None:
            same = bucket['uuid'] == cur.get('bucket_uuid') or (cur.get('bucket_uuid') is None and bucket.get('name') == cur.get('bucket_name'))
        else:
            same = dest['bucket'] in (cur.get('bucket_uuid'), cur.get('bucket_name'))
        return None if same else 'bucket'
    if normalize_endpoint(dest['endpoint']) != normalize_endpoint(cur.get('endpoint')):
        return 'endpoint'
    for field in ('region', 'bucket'):
        if dest.get(field) != cur.get(field):
            return field
    if (dest.get('path_style') or 'auto') != (cur.get('path_style') or 'auto'):
        return 'path_style'
    return None


def key_id_differs(current, access_key_id):
    """The API returns the key ID masked (**** and its last 4 characters)."""
    masked = ((current.get('destination') or {}).get('access_key_id') or '')
    return not access_key_id or masked[-4:] != access_key_id[-4:]


def rules_patch(params, rules):
    """The PATCH body that brings the rules to the desired ones (empty when they match)."""
    rules = rules or {}
    patch = {}
    prefix = params.get('prefix') or None
    if prefix != (rules.get('prefix') or None):
        patch['prefix'] = prefix
    tags = replication_tags(params.get('tags'))
    if tags != replication_tags(rules.get('tags')):
        patch['tags'] = tags or None
    for field in ('delete_marker_replication', 'delete_replication', 'existing_objects'):
        if bool(params[field]) != bool(rules.get(field)):
            patch[field] = bool(params[field])
    # A filter can switch from prefix to tags (or back) in one call: clear the other one too.
    if patch.get('tags') and rules.get('prefix') and 'prefix' not in patch:
        patch['prefix'] = None
    if patch.get('prefix') and rules.get('tags') and 'tags' not in patch:
        patch['tags'] = None
    return patch


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        source_bucket=dict(type='str', required=True),
        destination=dict(type='dict', options=dict(
            type=dict(type='str', required=True, choices=['cubepath', 'external']),
            bucket=dict(type='str', required=True),
            grant_token=dict(type='str', no_log=True),
            provider=dict(type='str', choices=['aws', 'wasabi', 'other']),
            endpoint=dict(type='str'),
            region=dict(type='str'),
            path_style=dict(type='str', default='auto', choices=['auto', 'on', 'off']),
            access_key_id=dict(type='str', no_log=False),
            secret_access_key=dict(type='str', no_log=True),
        )),
        prefix=dict(type='str'),
        tags=dict(type='dict'),
        delete_marker_replication=dict(type='bool', default=False),
        delete_replication=dict(type='bool', default=False),
        existing_objects=dict(type='bool', default=True),
        enabled=dict(type='bool', default=True),
        update_credentials=dict(type='bool', default=False),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=600),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['destination'])],
        mutually_exclusive=[('prefix', 'tags')],
        supports_check_mode=True,
    )
    p = module.params
    if p['tags'] and p['delete_marker_replication']:
        module.fail_json(msg='Delete markers cannot be replicated with a tag filter')

    api = CubePathAPI(module)
    source = find_bucket_ref(api, p['source_bucket'])
    if source is None:
        module.fail_json(msg='Bucket %s not found' % p['source_bucket'])
    timeout = p['wait_timeout']

    def fetch(uuid):
        return lambda: next((r for r in list_replications(api, 'outgoing', source['uuid']) if r.get('uuid') == uuid), None)

    def settled(uuid):
        return wait_for(module, fetch(uuid), lambda r: r is None or r.get('status') not in ('pending', 'deleting'), timeout)

    current = find_outgoing_replication(api, source['uuid'])

    if p['state'] == 'absent':
        if current is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if current.get('status') == 'pending':
            if not p['wait']:
                module.fail_json(msg='The replication is still being configured; run again with wait=true or later')
            current = settled(current['uuid'])
        if current is not None and current.get('status') != 'deleting':
            api.delete('/object-storage/replications/%s' % current['uuid'])
        if current is not None and p['wait']:
            wait_for(module, fetch(current['uuid']), lambda r: r is None, timeout)
        module.exit_json(changed=True)

    dest = p['destination']
    check_destination_params(module, dest)

    if current is not None and current.get('status') == 'deleting':
        if not p['wait']:
            module.fail_json(msg='The previous replication of bucket %s is still being removed' % source['name'])
        if not module.check_mode:
            wait_for(module, fetch(current['uuid']), lambda r: r is None, timeout)
        current = None

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True)
        body = {
            'source_bucket_uuid': source['uuid'],
            'destination': destination_body(module, api, dest),
            'delete_marker_replication': p['delete_marker_replication'],
            'delete_replication': p['delete_replication'],
            'existing_objects': p['existing_objects'],
        }
        if p.get('prefix'):
            body['prefix'] = p['prefix']
        if p.get('tags'):
            body['tags'] = replication_tags(p['tags'])
        created = api.post('/object-storage/replications', body)
        uuid = created.get('uuid')
        if uuid and (p['wait'] or not p['enabled']):
            # A pending replication cannot be changed: pausing it waits for the configuration.
            settled(uuid)
            if not p['enabled']:
                api.patch('/object-storage/replications/%s' % uuid, {'enabled': False})
        replication = api.get('/object-storage/replications/%s' % uuid) if uuid else created
        module.exit_json(changed=True, replication=replication)

    differs = destination_differs(module, api, current, dest)
    if differs:
        module.fail_json(msg='The destination %s of the replication of bucket %s cannot be changed; remove the '
                             'replication (state=absent) and create it again' % (differs, source['name']))

    if current.get('status') == 'pending':
        if not p['wait'] or module.check_mode:
            module.exit_json(changed=False, replication=current)
        current = settled(current['uuid'])
    if current.get('status') == 'error':
        module.fail_json(msg='The replication of bucket %s failed: %s. Remove it (state=absent) and create it again'
                             % (source['name'], current.get('error_message') or 'unknown error'), replication=current)

    patch = rules_patch(p, current.get('rules'))
    warnings = []
    is_enabled = (current.get('rules') or {}).get('enabled', current.get('status') == 'active')
    if p['enabled'] != bool(is_enabled):
        reason = current.get('pause_reason')
        if p['enabled'] and reason == 'dest_revoked':
            warnings.append('The destination owner revoked this replication; remove it and ask for a new grant')
        elif p['enabled'] and reason not in (None, 'customer'):
            warnings.append('This replication is paused by CubePath (%s); contact support' % reason)
        else:
            patch['enabled'] = p['enabled']
    if dest['type'] == 'external' and (p['update_credentials'] or key_id_differs(current, dest.get('access_key_id'))):
        patch['destination'] = {'access_key_id': dest['access_key_id'], 'secret_access_key': dest['secret_access_key']}

    for warning in warnings:
        module.warn(warning)
    if not patch:
        module.exit_json(changed=False, replication=current)
    if module.check_mode:
        module.exit_json(changed=True, replication=current)
    api.patch('/object-storage/replications/%s' % current['uuid'], patch)
    module.exit_json(changed=True, replication=api.get('/object-storage/replications/%s' % current['uuid']))


if __name__ == '__main__':
    main()
