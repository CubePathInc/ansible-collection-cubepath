# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import object_storage_bucket_lifecycle as lifecycle

BUCKETS = [{'uuid': 'b1', 'name': 'logs'}]
PATH = '/object-storage/buckets/b1/lifecycle'
STORED = {
    'id': 'logs-30d', 'enabled': True,
    'filter': {'prefix': 'logs/', 'tags': None, 'object_size_greater_than': None, 'object_size_less_than': None},
    'expiration': {'days': 30, 'date': None, 'expired_object_delete_marker': None},
    'noncurrent_version_expiration': None, 'abort_incomplete_multipart_upload': None,
}


def state(rules, generation=2, applied=2, status='active'):
    return {'bucket_uuid': 'b1', 'status': status, 'rules': rules, 'generation': generation, 'applied_generation': applied}


def test_unchanged_rules_write_nothing(run):
    result, out, router = run(lifecycle, {'bucket': 'logs', 'rules': [{'id': 'logs-30d', 'filter': {'prefix': '/logs/'}, 'expiration': {'days': 30}}]},
                              {('GET', '/object-storage/buckets'): BUCKETS, ('GET', PATH): state([STORED])})
    assert result == 'exit' and out['changed'] is False
    assert router.writes() == []


def test_new_rules_are_put_normalized_and_waited_for(run):
    rules = [{'id': 'tmp', 'filter': {'tags': [{'key': 'b', 'value': '2'}, {'key': 'a', 'value': '1'}]}, 'expiration': {'days': 1}}]
    result, out, router = run(lifecycle, {'bucket': 'logs', 'rules': rules}, {
        ('GET', '/object-storage/buckets'): BUCKETS,
        ('GET', PATH): (state([STORED]), state([STORED], 3, 2, 'pending'), state([STORED], 3, 3)),
        ('PUT', PATH): {'detail': 'Lifecycle rules are being applied', 'generation': 3},
    })
    assert result == 'exit' and out['changed'] is True and out['lifecycle']['applied_generation'] == 3
    (method, endpoint, data, _params), = router.writes()
    assert (method, endpoint) == ('PUT', PATH)
    assert data['rules'][0]['filter']['tags'] == [{'key': 'a', 'value': '1'}, {'key': 'b', 'value': '2'}]
    assert data['rules'][0]['enabled'] is True


def test_check_mode_changes_nothing(run):
    result, out, router = run(lifecycle, {'bucket': 'logs', 'rules': [{'id': 'x', 'expiration': {'days': 9}}], '_ansible_check_mode': True},
                              {('GET', '/object-storage/buckets'): BUCKETS, ('GET', PATH): state([STORED])})
    assert result == 'exit' and out['changed'] is True and router.writes() == []


def test_failed_apply_fails_the_task(run):
    result, out, _router = run(lifecycle, {'bucket': 'logs', 'rules': [{'id': 'x', 'expiration': {'days': 9}}]}, {
        ('GET', '/object-storage/buckets'): BUCKETS,
        ('GET', PATH): (state([STORED]), dict(state([STORED], 3, 2, 'error'), error='The storage service rejected the rules')),
        ('PUT', PATH): {'generation': 3},
    })
    assert result == 'fail' and 'rejected' in out['msg']


def test_absent(run):
    result, out, router = run(lifecycle, {'bucket': 'logs', 'state': 'absent', 'wait': False}, {
        ('GET', '/object-storage/buckets'): BUCKETS, ('GET', PATH): state([STORED]), ('DELETE', PATH): {'generation': 3},
    })
    assert result == 'exit' and out['changed'] is True and router.writes()[0][:2] == ('DELETE', PATH)
    result, out, router = run(lifecycle, {'bucket': 'logs', 'state': 'absent'},
                              {('GET', '/object-storage/buckets'): BUCKETS, ('GET', PATH): state([], 0, 0, 'none')})
    assert result == 'exit' and out['changed'] is False and router.writes() == []


def test_unknown_bucket(run):
    result, out, _router = run(lifecycle, {'bucket': 'nope', 'state': 'absent'}, {('GET', '/object-storage/buckets'): BUCKETS})
    assert result == 'fail' and 'not found' in out['msg']
