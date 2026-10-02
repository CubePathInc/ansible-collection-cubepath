# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import object_storage_event_destination as destination
from ansible_collections.cubepathinc.cloud.plugins.modules import object_storage_event_rule as rule_module

DESTS = '/object-storage/event-destinations'
HOOK = {'uuid': 'd1', 'name': 'hook', 'type': 'webhook', 'url_masked': 'https://example.com/***', 'payload_format': 'cubepath', 'status': 'active'}
BUCKETS = [{'uuid': 'b1', 'name': 'photos'}]
RULES = '/object-storage/buckets/b1/event-rules'
RULE = {'uuid': 'r1', 'name': 'new-photos', 'bucket_uuid': 'b1', 'destination': {'uuid': 'd1'}, 'events': ['object.created'],
        'prefix': 'incoming/', 'suffix': '', 'enabled': True, 'status': 'active'}


def test_create_webhook_returns_secret_once(run):
    result, out, router = run(destination, {'name': 'hook', 'type': 'webhook', 'url': 'https://example.com/h'}, {
        ('GET', DESTS): [],
        ('POST', DESTS): {'destination': HOOK, 'signing_secret': 'whsec_x'},
    })
    assert result == 'exit' and out['changed'] is True and out['signing_secret'] == 'whsec_x'
    (method, endpoint, data, _params), = router.writes()
    assert (method, endpoint) == ('POST', DESTS)
    assert data == {'name': 'hook', 'type': 'webhook', 'url': 'https://example.com/h', 'payload_format': 'cubepath'}


def test_existing_destination_is_idempotent_and_url_not_resent(run):
    result, out, router = run(destination, {'name': 'hook', 'type': 'webhook', 'url': 'https://example.com/h'}, {('GET', DESTS): [HOOK]})
    assert result == 'exit' and out['changed'] is False and out['signing_secret'] is None and router.writes() == []


def test_update_url_always_and_reenable(run):
    result, out, router = run(destination, {'name': 'hook', 'url': 'https://example.com/v2', 'update_url': 'always'}, {
        ('GET', DESTS): [dict(HOOK, status='auto_disabled', disabled_reason='failing')],
        ('PATCH', DESTS + '/d1'): HOOK,
    })
    assert result == 'exit' and out['changed'] is True
    (method, endpoint, data, _params), = router.writes()
    assert (method, endpoint) == ('PATCH', DESTS + '/d1') and data == {'enabled': True, 'url': 'https://example.com/v2'}


def test_rotate_secret(run):
    result, out, router = run(destination, {'name': 'hook', 'rotate_secret': True}, {
        ('GET', DESTS): [HOOK],
        ('POST', DESTS + '/d1/rotate-secret'): {'destination': HOOK, 'signing_secret': 'whsec_new'},
    })
    assert result == 'exit' and out['changed'] is True and out['signing_secret'] == 'whsec_new'


def test_type_cannot_change(run):
    result, out, _router = run(destination, {'name': 'hook', 'type': 'notificator', 'notificator_id': 'n1'}, {('GET', DESTS): [HOOK]})
    assert result == 'fail' and 'type' in out['msg']


def test_create_channel_disabled(run):
    chan = dict(HOOK, uuid='d2', name='ops', type='notificator', url_masked=None, notificator={'id': 'n1'})
    result, out, router = run(destination, {'name': 'ops', 'type': 'notificator', 'notificator_id': 'n1', 'enabled': False}, {
        ('GET', DESTS): [],
        ('POST', DESTS): {'destination': chan, 'signing_secret': None},
        ('PATCH', DESTS + '/d2'): dict(chan, status='disabled'),
    })
    assert result == 'exit' and out['destination']['status'] == 'disabled' and out['signing_secret'] is None
    assert [w[:2] for w in router.writes()] == [('POST', DESTS), ('PATCH', DESTS + '/d2')]
    assert router.writes()[0][2]['notificator_id'] == 'n1' and 'url' not in router.writes()[0][2]


def test_destination_absent(run):
    result, out, router = run(destination, {'name': 'hook', 'state': 'absent'}, {('GET', DESTS): [HOOK]})
    assert result == 'exit' and out['changed'] is True and router.writes()[0][:2] == ('DELETE', DESTS + '/d1')
    result, out, router = run(destination, {'name': 'hook', 'state': 'absent'}, {('GET', DESTS): []})
    assert result == 'exit' and out['changed'] is False and router.writes() == []


def test_rule_create_waits_until_active(run):
    pending = dict(RULE, status='pending')
    result, out, router = run(rule_module, {'bucket': 'photos', 'name': 'new-photos', 'destination': 'hook', 'events': ['created', 'object.created'],
                                            'prefix': 'incoming/'}, {
        ('GET', '/object-storage/buckets'): BUCKETS,
        ('GET', DESTS): [HOOK],
        ('GET', RULES): ([], [pending], [RULE]),
        ('POST', RULES): pending,
    })
    assert result == 'exit' and out['changed'] is True and out['rule']['status'] == 'active'
    (method, endpoint, data, _params), = router.writes()
    assert (method, endpoint) == ('POST', RULES)
    assert data == {'name': 'new-photos', 'destination_uuid': 'd1', 'events': ['object.created'], 'prefix': 'incoming/', 'suffix': '', 'enabled': True}


def test_rule_unchanged(run):
    result, out, router = run(rule_module, {'bucket': 'b1', 'name': 'new-photos', 'destination': 'd1', 'events': ['created'], 'prefix': 'incoming/'}, {
        ('GET', '/object-storage/buckets'): BUCKETS, ('GET', DESTS): [HOOK], ('GET', RULES): [RULE],
    })
    assert result == 'exit' and out['changed'] is False and router.writes() == []


def test_rule_update_sends_only_changes(run):
    result, out, router = run(rule_module, {'bucket': 'photos', 'name': 'new-photos', 'events': ['removed', 'created'], 'prefix': 'incoming/', 'wait': False}, {
        ('GET', '/object-storage/buckets'): BUCKETS, ('GET', RULES): [RULE], ('PATCH', RULES + '/r1'): dict(RULE, status='pending'),
    })
    assert result == 'exit' and out['changed'] is True
    (method, endpoint, data, _params), = router.writes()
    assert (method, endpoint) == ('PATCH', RULES + '/r1') and data == {'events': ['object.created', 'object.removed']}


def test_rule_rejects_unknown_event_and_missing_fields(run):
    routes = {('GET', '/object-storage/buckets'): BUCKETS, ('GET', DESTS): [HOOK], ('GET', RULES): []}
    result, out, _router = run(rule_module, {'bucket': 'photos', 'name': 'x', 'destination': 'hook', 'events': ['copied']}, routes)
    assert result == 'fail' and 'copied' in out['msg']
    result, out, _router = run(rule_module, {'bucket': 'photos', 'name': 'x', 'events': ['created']}, routes)
    assert result == 'fail' and 'required' in out['msg']


def test_rule_absent_and_unknown_bucket(run):
    result, out, router = run(rule_module, {'bucket': 'photos', 'name': 'new-photos', 'state': 'absent'}, {
        ('GET', '/object-storage/buckets'): BUCKETS, ('GET', RULES): ([RULE], []),
    })
    assert result == 'exit' and out['changed'] is True and router.writes()[0][:2] == ('DELETE', RULES + '/r1')
    result, out, _router = run(rule_module, {'bucket': 'nope', 'name': 'x', 'state': 'absent'}, {('GET', '/object-storage/buckets'): BUCKETS})
    assert result == 'fail' and 'not found' in out['msg']
