#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cloud_alert
short_description: Manage Cloud Alerts on CubePath Cloud
description:
    - Create, update or delete an alert that watches a metric of a VPS, a baremetal server, an
      availability group, an Object Storage bucket or the Object Storage usage of the organization, and
      notifies channels when it crosses a threshold.
    - The module finds an existing alert by I(name), which is unique in the organization, and updates the
      fields that differ.
    - Channels are managed with M(cubepathinc.cloud.cloud_alert_channel).
    - Monthly metrics (C(storage_cost_month) and C(storage_egress_gb_month)) notify once per month as soon
      as the threshold is crossed and reset on the 1st (UTC). They only accept the C(gt) and C(gte)
      operators and ignore I(duration_seconds) and I(cooldown_seconds).
    - An organization can have up to 50 alerts.
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
        description:
            - Kind of resource watched. Required to create the alert.
            - C(organization) watches the Object Storage usage of the whole organization.
        type: str
        choices: [vps, baremetal, availability_group, object_storage_bucket, organization]
    target_id:
        description:
            - ID of the VPS or baremetal server, UUID of the availability group or of the bucket, or the
              organization ID when I(target_type=organization). Required to create the alert.
            - A bucket alert must be created in the bucket's project. An organization alert still needs a
              I(project_id); it is listed under that project and deleted with it.
        type: str
    metric:
        description:
            - Metric watched. Required to create the alert.
            - Servers and availability groups use C(cpu), C(ram), C(disk), C(network_in) and C(network_out).
              Baremetal servers only support C(network_in) and C(network_out).
            - Buckets use C(storage_size_gb) (GiB), C(storage_egress_gb_month) (GiB this month, before the free
              tier), C(storage_error_rate_5xx) and C(storage_error_rate_403) (percent of requests over the last
              5 minutes, needs at least 20 requests).
            - Organizations use C(storage_cost_month) (USD billed so far this month, about an hour behind
              billing) and C(storage_egress_gb_month).
        type: str
        choices: [cpu, ram, disk, network_in, network_out, storage_size_gb, storage_egress_gb_month,
                  storage_error_rate_5xx, storage_error_rate_403, storage_cost_month]
    operator:
        description:
            - Comparison with I(threshold). Required to create the alert.
            - Monthly metrics only accept C(gt) and C(gte).
        type: str
        choices: [gt, gte, lt, lte, eq]
    threshold:
        description:
            - Threshold value. Required to create the alert.
            - 0 to 1000000 for server metrics (percent for C(cpu), C(ram) and C(disk)).
            - Object Storage metrics need a value above 0 and at most 1048576 for C(storage_size_gb), 100 for
              the error rates and 1000000 for C(storage_egress_gb_month) and C(storage_cost_month).
        type: float
    duration_seconds:
        description:
            - Seconds the condition must hold before the alert fires (60 to 3600, 300 by default).
            - Ignored by monthly metrics; leave it unset for them.
        type: int
    cooldown_seconds:
        description:
            - Minimum seconds between two notifications (60 to 86400, 600 by default).
            - Ignored by monthly metrics.
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

- name: Monthly Object Storage budget, notified once when 50 USD have been billed this month
  cubepathinc.cloud.cloud_alert:
    api_token: "{{ cubepath_token }}"
    name: object storage budget
    project_id: 12
    target_type: organization
    target_id: "{{ organization_id | string }}"
    metric: storage_cost_month
    operator: gte
    threshold: 50
    channels: [ops-email]

- name: Alert when a bucket grows above 500 GiB
  cubepathinc.cloud.cloud_alert:
    api_token: "{{ cubepath_token }}"
    name: assets bucket size
    project_id: 12
    target_type: object_storage_bucket
    target_id: 6f1c1a8e-0d6b-4f0e-9a43-2b7f3c1d9e10
    metric: storage_size_gb
    operator: gt
    threshold: 500
    channels: [ops-slack]
'''

RETURN = r'''
alert:
    description: Alert details, with its C(actions) and C(target_name) (the bucket name, or null).
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
        target_type=dict(type='str', choices=['vps', 'baremetal', 'availability_group', 'object_storage_bucket',
                                              'organization']),
        target_id=dict(type='str'),
        metric=dict(type='str', choices=['cpu', 'ram', 'disk', 'network_in', 'network_out', 'storage_size_gb',
                                         'storage_egress_gb_month', 'storage_error_rate_5xx',
                                         'storage_error_rate_403', 'storage_cost_month']),
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
