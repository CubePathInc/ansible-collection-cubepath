#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cloud_alert
short_description: Manage Cloud Alerts on CubePath Cloud
description:
    - Create, update or delete an alert that watches a metric of a VPS, a baremetal server or an
      availability group and notifies channels when it crosses a threshold.
    - The module finds an existing alert by I(name), which is unique in the organization, and updates the
      fields that differ.
    - Channels are managed with M(cubepathinc.cloud.cloud_alert_channel).
    - An organization can have up to 20 alerts.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the alert.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the alert (1 to 128 characters).
        type: str
        required: true
    project_id:
        description: Project of the alert. Required to create it.
        type: int
    description:
        description: Free-form description.
        type: str
    target_type:
        description: Kind of resource watched. Required to create the alert.
        type: str
        choices: [vps, baremetal, availability_group]
    target_id:
        description:
            - ID of the VPS or baremetal server, or UUID of the availability group. Required to create the alert.
        type: str
    metric:
        description:
            - Metric watched. Required to create the alert.
            - Baremetal servers only support C(network_in) and C(network_out).
        type: str
        choices: [cpu, ram, disk, network_in, network_out]
    operator:
        description: Comparison with I(threshold). Required to create the alert.
        type: str
        choices: [gt, gte, lt, lte, eq]
    threshold:
        description: Threshold value (0 to 1000000). Required to create the alert.
        type: float
    duration_seconds:
        description: Seconds the condition must hold before the alert fires (60 to 3600, 300 by default).
        type: int
    cooldown_seconds:
        description: Minimum seconds between two notifications (60 to 86400, 600 by default).
        type: int
    channels:
        description:
            - Names or IDs of the notification channels to notify (1 to 10). Required to create the alert.
            - When set on an existing alert, replaces its channels.
        type: list
        elements: str
    enabled:
        description: Whether the alert is evaluated.
        type: bool
'''

EXAMPLES = r'''
- name: Alert when a VPS stays above 90% CPU for 10 minutes
  cubepathinc.cloud.cloud_alert:
    api_token: "{{ cubepath_token }}"
    name: web-01 cpu
    project_id: 12
    target_type: vps
    target_id: "456"
    metric: cpu
    operator: gt
    threshold: 90
    duration_seconds: 600
    channels: [ops-slack]

- name: Pause it
  cubepathinc.cloud.cloud_alert:
    api_token: "{{ cubepath_token }}"
    name: web-01 cpu
    enabled: false
'''

RETURN = r'''
alert:
    description: Alert details, with its C(actions).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_alerts import ALERTS, find_alert, list_channels

FIELDS = (
    ('description', 'description'), ('target_type', 'target_type'), ('target_id', 'target_id'),
    ('metric', 'metric_type'), ('operator', 'operator'), ('threshold', 'threshold'),
    ('duration_seconds', 'duration_seconds'), ('cooldown_seconds', 'cooldown_seconds'),
)


def resolve_channels(module, api, refs):
    channels = list_channels(api)
    ids = []
    for ref in refs:
        match = next((c for c in channels if ref in (c.get('id'), c.get('name'))), None)
        if match is None:
            module.fail_json(msg='Notification channel %s not found' % ref)
        ids.append(match['id'])
    return ids


def notify_actions(ids):
    return [{'action_type': 'notify', 'notificator_id': cid, 'order': i, 'enabled': True} for i, cid in enumerate(ids)]


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        project_id=dict(type='int'),
        description=dict(type='str'),
        target_type=dict(type='str', choices=['vps', 'baremetal', 'availability_group']),
        target_id=dict(type='str'),
        metric=dict(type='str', choices=['cpu', 'ram', 'disk', 'network_in', 'network_out']),
        operator=dict(type='str', choices=['gt', 'gte', 'lt', 'lte', 'eq']),
        threshold=dict(type='float'),
        duration_seconds=dict(type='int'),
        cooldown_seconds=dict(type='int'),
        channels=dict(type='list', elements='str'),
        enabled=dict(type='bool'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params
    existing = find_alert(api, p['name'])

    if p['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s%s' % (ALERTS, existing['id']))
        module.exit_json(changed=True)

    channel_ids = resolve_channels(module, api, p['channels']) if p.get('channels') is not None else None

    if existing is None:
        missing = [k for k in ('project_id', 'target_type', 'target_id', 'metric', 'operator', 'threshold', 'channels')
                   if p.get(k) is None]
        if missing:
            module.fail_json(msg='%s required to create the alert' % ', '.join(missing))
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'project_id': p['project_id'], 'name': p['name'], 'actions': notify_actions(channel_ids)}
        for opt, field in FIELDS:
            if p.get(opt) is not None:
                data[field] = p[opt]
        alert = api.post(ALERTS, data)
        if p.get('enabled') is False:
            alert = api.put('%s%s' % (ALERTS, alert['id']), {'status': 'disabled'})
        module.exit_json(changed=True, alert=alert)

    current = api.get('%s%s' % (ALERTS, existing['id']))
    update = {}
    for opt, field in FIELDS:
        if p.get(opt) is not None and p[opt] != current.get(field):
            update[field] = p[opt]
    if p.get('enabled') is not None:
        # A firing alert is `triggered` or `resolved`; both count as enabled.
        is_enabled = current.get('status') != 'disabled'
        if p['enabled'] != is_enabled:
            update['status'] = 'enabled' if p['enabled'] else 'disabled'
    if channel_ids is not None:
        current_ids = [a.get('notificator_id') for a in current.get('actions') or [] if a.get('action_type') == 'notify']
        if sorted(current_ids) != sorted(channel_ids):
            update['actions'] = notify_actions(channel_ids)
    if not update:
        module.exit_json(changed=False, alert=current)
    if module.check_mode:
        module.exit_json(changed=True, alert=current)
    alert = api.put('%s%s' % (ALERTS, existing['id']), update)
    module.exit_json(changed=True, alert=alert)


if __name__ == '__main__':
    main()
