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
