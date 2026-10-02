# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import cloud_alert, cloud_alert_channel

CHANNELS = [{'id': 'c-1', 'name': 'ops-slack', 'type': 'slack', 'enabled': True,
             'config': {'webhook_url': 'https://hooks.slack.com/***AbCd'}}]


def test_create_alert_with_channel_names(run):
    status, result, api = run(cloud_alert, {
        'name': 'cpu', 'project_id': 882, 'target_type': 'vps', 'target_id': '42', 'metric': 'cpu',
        'operator': 'gt', 'threshold': 90, 'channels': ['ops-slack'],
    }, {
        ('GET', '/triggers/'): [],
        ('GET', '/triggers/notificators/'): CHANNELS,
        ('POST', '/triggers/'): {'id': 't-1'},
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/triggers/', {
        'project_id': 882, 'name': 'cpu', 'target_type': 'vps', 'target_id': '42', 'metric_type': 'cpu',
        'operator': 'gt', 'threshold': 90.0,
        'actions': [{'action_type': 'notify', 'notificator_id': 'c-1', 'order': 0, 'enabled': True}],
    }, None)]


def test_create_organization_budget_alert(run):
    status, result, api = run(cloud_alert, {
        'name': 'budget', 'project_id': 882, 'target_type': 'organization', 'target_id': '7',
        'metric': 'storage_cost_month', 'operator': 'gte', 'threshold': 50, 'channels': ['ops-slack'],
    }, {
        ('GET', '/triggers/'): [],
        ('GET', '/triggers/notificators/'): CHANNELS,
        ('POST', '/triggers/'): {'id': 't-2', 'target_name': None},
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/triggers/', {
        'project_id': 882, 'name': 'budget', 'target_type': 'organization', 'target_id': '7',
        'metric_type': 'storage_cost_month', 'operator': 'gte', 'threshold': 50.0,
        'actions': [{'action_type': 'notify', 'notificator_id': 'c-1', 'order': 0, 'enabled': True}],
    }, None)]


def test_bucket_alert_is_unchanged_when_it_matches(run):
    current = {'id': 't-3', 'name': 'assets size', 'target_type': 'object_storage_bucket',
               'target_id': '6f1c1a8e-0d6b-4f0e-9a43-2b7f3c1d9e10', 'target_name': 'assets',
               'metric_type': 'storage_size_gb', 'operator': 'gt', 'threshold': 1048576.0, 'status': 'enabled',
               'actions': [{'action_type': 'notify', 'notificator_id': 'c-1'}]}
    status, result, api = run(cloud_alert, {
        'name': 'assets size', 'target_type': 'object_storage_bucket',
        'target_id': '6f1c1a8e-0d6b-4f0e-9a43-2b7f3c1d9e10', 'metric': 'storage_size_gb', 'operator': 'gt',
        'threshold': 1048576, 'channels': ['ops-slack'],
    }, {
        ('GET', '/triggers/'): [{'id': 't-3', 'name': 'assets size'}],
        ('GET', '/triggers/notificators/'): CHANNELS,
        ('GET', '/triggers/t-3'): current,
    })
    assert status == 'exit' and not result['changed']
    assert result['alert']['target_name'] == 'assets'
    assert api.writes() == []


def test_alert_update_only_sends_changes(run):
    current = {'id': 't-1', 'name': 'cpu', 'threshold': 90.0, 'status': 'triggered', 'metric_type': 'cpu',
               'actions': [{'action_type': 'notify', 'notificator_id': 'c-1'}]}
    status, result, api = run(cloud_alert, {'name': 'cpu', 'threshold': 80, 'enabled': True, 'channels': ['c-1']}, {
        ('GET', '/triggers/'): [{'id': 't-1', 'name': 'cpu'}],
        ('GET', '/triggers/notificators/'): CHANNELS,
        ('GET', '/triggers/t-1'): current,
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PUT', '/triggers/t-1', {'threshold': 80.0}, None)]


def test_channel_with_same_masked_webhook_is_unchanged(run):
    status, result, api = run(cloud_alert_channel, {
        'name': 'ops-slack', 'type': 'slack', 'webhook_url': 'https://hooks.slack.com/services/T0/B0/xyzAbCd',
    }, {('GET', '/triggers/notificators/'): CHANNELS})
    assert status == 'exit' and not result['changed']


def test_channel_type_cannot_change(run):
    status, result, api = run(cloud_alert_channel, {'name': 'ops-slack', 'type': 'email'}, {
        ('GET', '/triggers/notificators/'): CHANNELS,
    })
    assert status == 'fail'
    assert api.writes() == []
