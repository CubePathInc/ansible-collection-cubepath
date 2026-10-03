#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_event_rule
short_description: Manage Object Storage event rules on CubePath Cloud
description:
    - Send the events of a bucket (objects created, removed or tagged) whose key matches
      I(prefix) and I(suffix) to an event destination
      (M(cubepathinc.cloud.object_storage_event_destination)).
    - Rules are found by I(name) within the bucket and applied in the background.
version_added: "1.7.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the rule.
        type: str
        default: present
        choices: [present, absent]
    bucket:
        description: Bucket name or UUID.
        type: str
        required: true
    name:
        description: Rule name, 1 to 64 letters, digits, hyphens and spaces.
        type: str
        required: true
    destination:
        description:
            - Event destination name or UUID. It must be enabled.
            - Required when the rule has to be created.
        type: str
    events:
        description:
            - Event types, C(created), C(removed) and/or C(tagging) (C(object.created) and so on also work).
            - Required when the rule has to be created.
        type: list
        elements: str
    prefix:
        description: Only keys starting with this prefix (up to 1024 characters).
        type: str
        default: ''
    suffix:
        description: Only keys ending with this suffix (up to 1024 characters).
        type: str
        default: ''
    enabled:
        description: Whether the rule sends events.
        type: bool
        default: true
    wait:
        description: Wait until the rule is applied (C(active)), or gone when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 300
'''

EXAMPLES = r'''
- name: Send new photos to a webhook
  cubepathinc.cloud.object_storage_event_rule:
    api_token: "{{ cubepath_token }}"
    bucket: photos
    name: new-photos
    destination: uploads-hook
    events: [created]
    prefix: incoming/
    suffix: .jpg

- name: Remove the rule
  cubepathinc.cloud.object_storage_event_rule:
    api_token: "{{ cubepath_token }}"
    bucket: photos
    name: new-photos
    state: absent
'''

RETURN = r'''
rule:
    description: The rule (uuid, name, bucket_uuid, destination, events, prefix, suffix, enabled, status, error_message).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import (
    find_bucket_ref, find_event_destination, list_event_rules, normalize_events, wait_for,
)


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        bucket=dict(type='str', required=True),
        name=dict(type='str', required=True),
        destination=dict(type='str'),
        events=dict(type='list', elements='str'),
        prefix=dict(type='str', default=''),
        suffix=dict(type='str', default=''),
        enabled=dict(type='bool', default=True),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=300),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params
    bucket = find_bucket_ref(api, p['bucket'])
    if bucket is None:
        module.fail_json(msg='Bucket %s not found' % p['bucket'])
    path = '/object-storage/buckets/%s/event-rules' % bucket['uuid']

    def find_rule():
        return next((r for r in list_event_rules(api, bucket['uuid']) if r.get('name') == p['name'] and r.get('status') != 'deleted'), None)

    def fetch(uuid):
        return lambda: next((r for r in list_event_rules(api, bucket['uuid']) if r.get('uuid') == uuid and r.get('status') != 'deleted'), None)

    rule = find_rule()

    if p['state'] == 'absent':
        if rule is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s/%s' % (path, rule['uuid']))
        if p['wait']:
            wait_for(module, fetch(rule['uuid']), lambda r: r is None, p['wait_timeout'])
        module.exit_json(changed=True)

    events = None
    if p['events'] is not None:
        try:
            events = normalize_events(p['events'])
        except ValueError as e:
            module.fail_json(msg=str(e))
        if not events:
            module.fail_json(msg='events needs at least one of created, removed, tagging')
    dest_uuid = None
    if p['destination']:
        dest = find_event_destination(api, p['destination'])
        if dest is None:
            module.fail_json(msg='Event destination %s not found' % p['destination'])
        dest_uuid = dest['uuid']

    if rule is None:
        if dest_uuid is None or events is None:
            module.fail_json(msg='destination and events are required to create an event rule')
        if module.check_mode:
            module.exit_json(changed=True)
        rule = api.post(path, {
            'name': p['name'], 'destination_uuid': dest_uuid, 'events': events,
            'prefix': p['prefix'], 'suffix': p['suffix'], 'enabled': p['enabled'],
        })
        changed = True
    else:
        changes = {}
        if dest_uuid and dest_uuid != (rule.get('destination') or {}).get('uuid'):
            changes['destination_uuid'] = dest_uuid
        if events is not None and events != sorted(rule.get('events') or []):
            changes['events'] = events
        for field in ('prefix', 'suffix', 'enabled'):
            if p[field] != rule.get(field):
                changes[field] = p[field]
        if module.check_mode:
            module.exit_json(changed=bool(changes), rule=rule)
        if changes:
            rule = api.patch('%s/%s' % (path, rule['uuid']), changes) or rule
        changed = bool(changes)

    if p['wait'] and rule.get('uuid') and rule.get('status') != 'active':
        rule = wait_for(module, fetch(rule['uuid']), lambda r: r is not None and r.get('status') == 'active', p['wait_timeout'])
    module.exit_json(changed=changed, rule=rule)


if __name__ == '__main__':
    main()
