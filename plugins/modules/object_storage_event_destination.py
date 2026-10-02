#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_event_destination
short_description: Manage Object Storage event destinations on CubePath Cloud
description:
    - Create, update or delete a destination for Object Storage event notifications, a signed
      webhook or a Slack or Discord channel of Cloud Alerts. Bucket events reach it through
      M(cubepathinc.cloud.object_storage_event_rule).
    - Destinations are found by I(name).
    - The signing secret of a webhook is returned only by the task that creates the destination
      (or by I(rotate_secret=true)). Store it the first time, for example in a vault, and run the
      task with C(no_log=true).
    - Every webhook delivery carries C(CubePath-Timestamp) and C(CubePath-Signature), one or more
      C(v1=<hex>) values, each the HMAC-SHA256 of C(timestamp + "." + raw body) with the secret.
      Reject deliveries whose timestamp is more than 5 minutes away.
version_added: "1.7.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description:
            - Desired state of the destination.
            - A destination can only be deleted once no rule uses it.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Destination name (1 to 64 characters).
        type: str
        required: true
    type:
        description:
            - C(webhook) (with I(url)) or C(notificator), a Cloud Alerts channel (with I(notificator_id)).
            - Required when the destination has to be created. It cannot change later.
        type: str
        choices: [webhook, notificator]
    url:
        description:
            - Webhook URL, https on port 443 or 8443, resolving to a public address.
            - The API never returns it in clear, so it is only sent on create, or on every run
              with I(update_url=always).
        type: str
    update_url:
        description: C(always) sends I(url) on every run (reporting a change); C(on_create) only when the destination is created.
        type: str
        default: on_create
        choices: [always, on_create]
    notificator_id:
        description: ID of a Slack or Discord channel of Cloud Alerts (M(cubepathinc.cloud.cloud_alert_channel)).
        type: str
    payload_format:
        description: C(cubepath), or C(s3) for C({"Records":[...]}) in the AWS shape.
        type: str
        default: cubepath
        choices: [cubepath, s3]
    enabled:
        description:
            - Whether events are delivered. A destination disabled by CubePath after repeated
              failures is enabled again when this is true.
        type: bool
        default: true
    rotate_secret:
        description:
            - Issue a new signing secret and return it. The previous secret keeps signing for 24 hours.
            - Always reports a change.
        type: bool
        default: false
'''

EXAMPLES = r'''
- name: Webhook destination
  cubepathinc.cloud.object_storage_event_destination:
    api_token: "{{ cubepath_token }}"
    name: uploads-hook
    type: webhook
    url: https://example.com/hooks/storage
  register: hook
  no_log: true

- name: Keep the signing secret (only returned on create)
  ansible.builtin.copy:
    content: "{{ hook.signing_secret }}"
    dest: /etc/myapp/storage-events.secret
    mode: "0600"
  when: hook.signing_secret is not none
  no_log: true

- name: Slack channel destination
  cubepathinc.cloud.object_storage_event_destination:
    api_token: "{{ cubepath_token }}"
    name: ops
    type: notificator
    notificator_id: "{{ slack_channel.channel.id }}"

- name: Delete a destination
  cubepathinc.cloud.object_storage_event_destination:
    api_token: "{{ cubepath_token }}"
    name: uploads-hook
    state: absent
'''

RETURN = r'''
destination:
    description: The destination (uuid, name, type, url_masked, notificator, payload_format, status, disabled_reason, rules_count).
    type: dict
    returned: when I(state=present)
signing_secret:
    description: The signing secret (C(whsec_...)), only when this task created a webhook destination or rotated its secret.
    type: str
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import find_event_destination

PATH = '/object-storage/event-destinations'


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        type=dict(type='str', choices=['webhook', 'notificator']),
        url=dict(type='str', no_log=True),
        update_url=dict(type='str', default='on_create', choices=['always', 'on_create']),
        notificator_id=dict(type='str'),
        payload_format=dict(type='str', default='cubepath', choices=['cubepath', 's3']),
        enabled=dict(type='bool', default=True),
        rotate_secret=dict(type='bool', default=False, no_log=False),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True,
                           mutually_exclusive=[('url', 'notificator_id')])

    api = CubePathAPI(module)
    p = module.params
    dest = find_event_destination(api, p['name'])

    if p['state'] == 'absent':
        if dest is None:
            module.exit_json(changed=False)
        if not module.check_mode:
            api.delete('%s/%s' % (PATH, dest['uuid']))
        module.exit_json(changed=True)

    if dest is None:
        if not p['type']:
            module.fail_json(msg='type is required to create an event destination')
        if p['type'] == 'webhook' and not p['url']:
            module.fail_json(msg='url is required for a webhook destination')
        if p['type'] == 'notificator' and not p['notificator_id']:
            module.fail_json(msg='notificator_id is required for a notificator destination')
        if module.check_mode:
            module.exit_json(changed=True, signing_secret=None)
        data = {'name': p['name'], 'type': p['type'], 'payload_format': p['payload_format']}
        if p['type'] == 'webhook':
            data['url'] = p['url']
        else:
            data['notificator_id'] = p['notificator_id']
        created = api.post(PATH, data)
        dest = created.get('destination') or {}
        if not p['enabled'] and dest.get('uuid'):
            dest = api.patch('%s/%s' % (PATH, dest['uuid']), {'enabled': False}) or dest
        module.exit_json(changed=True, destination=dest, signing_secret=created.get('signing_secret'))

    if p['type'] and p['type'] != dest.get('type'):
        module.fail_json(msg='The destination %s is a %s; delete it to change its type' % (p['name'], dest.get('type')))
    if p['notificator_id'] and p['notificator_id'] != (dest.get('notificator') or {}).get('id'):
        module.fail_json(msg='The channel of a destination cannot change; delete it and create it again')

    changes = {}
    if p['payload_format'] != dest.get('payload_format'):
        changes['payload_format'] = p['payload_format']
    if p['enabled'] != (dest.get('status') == 'active'):
        changes['enabled'] = p['enabled']
    if p['url'] and p['update_url'] == 'always' and dest.get('type') == 'webhook':
        changes['url'] = p['url']

    if module.check_mode:
        module.exit_json(changed=bool(changes) or p['rotate_secret'], destination=dest, signing_secret=None)
    if changes:
        dest = api.patch('%s/%s' % (PATH, dest['uuid']), changes) or dest
    secret = None
    if p['rotate_secret']:
        rotated = api.post('%s/%s/rotate-secret' % (PATH, dest['uuid']))
        dest = rotated.get('destination') or dest
        secret = rotated.get('signing_secret')
    module.exit_json(changed=bool(changes) or p['rotate_secret'], destination=dest, signing_secret=secret)


if __name__ == '__main__':
    main()
