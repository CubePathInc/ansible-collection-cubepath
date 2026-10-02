#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_bucket_lifecycle
short_description: Manage the lifecycle rules of an Object Storage bucket on CubePath Cloud
description:
    - Set or remove every lifecycle rule of an Object Storage bucket. The rules given replace
      all the rules of the bucket.
    - Rules delete objects in the background, permanently. Objects are removed within 48 hours
      of their due date.
    - In a versioned bucket an expiration only adds a delete marker; add a
      C(noncurrent_version_expiration) rule to free the space.
    - Rules are applied asynchronously (seconds, up to 10 minutes after a previous change of the
      same bucket); by default the module waits until they are applied.
    - The module is idempotent. It compares the normalized rules with the bucket's and only
      writes when they differ.
version_added: "1.6.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: C(present) sets the rules, C(absent) removes every rule.
        type: str
        default: present
        choices: [present, absent]
    bucket:
        description: Bucket name (or UUID).
        type: str
        required: true
    rules:
        description:
            - Lifecycle rules, 1 to 100, in the API format. Required with I(state=present).
            - Each rule has C(id) (1 to 64 letters, numbers, dots, hyphens and underscores, not
              starting with C(cubepath-)), C(enabled) (default true), an optional C(filter)
              (C(prefix), C(tags) as a list of C(key)/C(value), C(object_size_greater_than),
              C(object_size_less_than)) and at least one action, C(expiration) (C(days), C(date)
              as YYYY-MM-DD after today, or C(expired_object_delete_marker)),
              C(noncurrent_version_expiration) (C(noncurrent_days), C(newer_noncurrent_versions))
              or C(abort_incomplete_multipart_upload) (C(days_after_initiation), 1 to 7).
        type: list
        elements: dict
    wait:
        description: Wait until the rules are applied.
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 900
'''

EXAMPLES = r'''
- name: Delete logs after 30 days and old versions after 7
  cubepathinc.cloud.object_storage_bucket_lifecycle:
    api_token: "{{ cubepath_token }}"
    bucket: my-logs
    rules:
      - id: logs-30d
        filter:
          prefix: logs/
        expiration:
          days: 30
      - id: old-versions
        noncurrent_version_expiration:
          noncurrent_days: 7
          newer_noncurrent_versions: 3

- name: Remove every lifecycle rule
  cubepathinc.cloud.object_storage_bucket_lifecycle:
    api_token: "{{ cubepath_token }}"
    bucket: my-logs
    state: absent
'''

RETURN = r'''
lifecycle:
    description: The bucket's lifecycle (status, rules, generation, applied_generation, notes).
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import list_buckets, wait_for


def _none_if_empty(value):
    return value if value not in ('', [], {}) else None


def normalize_rule(rule):
    """The rule in the API's stored form: every key present, absent values as None, a prefix
    without leading slashes (the API strips them) and tags sorted by key."""
    rule = rule or {}
    flt = rule.get('filter') or {}
    prefix = flt.get('prefix')
    prefix = prefix.lstrip('/') if isinstance(prefix, str) else prefix
    tags = flt.get('tags') or []
    if isinstance(tags, dict):
        tags = [{'key': k, 'value': v} for k, v in tags.items()]
    tags = sorted(({'key': str(t.get('key')), 'value': str(t.get('value', ''))} for t in tags), key=lambda t: t['key'])
    exp = rule.get('expiration') or {}
    expiration = None
    if exp.get('days') is not None or exp.get('date') or exp.get('expired_object_delete_marker'):
        expiration = {
            'days': exp.get('days'),
            'date': exp.get('date') or None,
            'expired_object_delete_marker': True if exp.get('expired_object_delete_marker') else None,
        }
    nve = rule.get('noncurrent_version_expiration') or {}
    noncurrent = None
    if nve.get('noncurrent_days') is not None:
        noncurrent = {'noncurrent_days': nve.get('noncurrent_days'), 'newer_noncurrent_versions': nve.get('newer_noncurrent_versions')}
    abort = rule.get('abort_incomplete_multipart_upload') or {}
    return {
        'id': rule.get('id'),
        'enabled': rule.get('enabled', True) is not False,
        'filter': {
            'prefix': _none_if_empty(prefix),
            'tags': _none_if_empty(tags),
            'object_size_greater_than': flt.get('object_size_greater_than'),
            'object_size_less_than': flt.get('object_size_less_than'),
        },
        'expiration': expiration,
        'noncurrent_version_expiration': noncurrent,
        'abort_incomplete_multipart_upload': (
            {'days_after_initiation': abort.get('days_after_initiation')} if abort.get('days_after_initiation') is not None else None
        ),
    }


def find_bucket_uuid(api, ref):
    for bucket in list_buckets(api):
        if bucket.get('name') == ref:
            return bucket['uuid']
    for bucket in list_buckets(api):
        if bucket.get('uuid') == ref:
            return bucket['uuid']
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        bucket=dict(type='str', required=True),
        rules=dict(type='list', elements='dict'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=900),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['rules'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    uuid = find_bucket_uuid(api, module.params['bucket'])
    if uuid is None:
        module.fail_json(msg='Bucket %s not found' % module.params['bucket'])
    path = '/object-storage/buckets/%s/lifecycle' % uuid
    current = api.get(path)
    current_rules = [normalize_rule(r) for r in (current or {}).get('rules') or []]

    if module.params['state'] == 'absent':
        if not current_rules:
            module.exit_json(changed=False, lifecycle=current)
        if module.check_mode:
            module.exit_json(changed=True, lifecycle=current)
        answer = api.delete(path) or {}
    else:
        desired = [normalize_rule(r) for r in module.params['rules']]
        if not desired:
            module.fail_json(msg='rules needs at least one rule; use state=absent to remove every rule')
        if desired == current_rules and (current or {}).get('status') != 'error':
            module.exit_json(changed=False, lifecycle=current)
        if module.check_mode:
            module.exit_json(changed=True, lifecycle=current)
        answer = api.put(path, {'rules': desired}) or {}

    lifecycle = api.get(path)
    generation = answer.get('generation')
    if module.params['wait'] and generation is not None:
        lifecycle = wait_for(
            module,
            lambda: api.get(path),
            lambda lc: lc is not None and (lc.get('applied_generation', 0) >= generation or lc.get('generation', 0) > generation),
            module.params['wait_timeout'],
        )
    module.exit_json(changed=True, lifecycle=lifecycle)


if __name__ == '__main__':
    main()
