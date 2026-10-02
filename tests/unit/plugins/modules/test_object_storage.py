# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import desired_tags, lock_retention, tag_filter
from ansible_collections.cubepathinc.cloud.plugins.modules import object_storage_access_key, object_storage_bucket, object_storage_info

BUCKET = {'uuid': 'b1', 'name': 'photos', 'status': 'active', 'versioning': 'off', 'protected': False,
          'tags': {'env': 'prod', 'team': 'web'}}
LIST = ('GET', '/object-storage/buckets')
DETAIL = ('GET', '/object-storage/buckets/b1')


def test_desired_tags():
    assert desired_tags({'a': '1'}, {'b': 2}, True) == {'b': '2'}
    assert desired_tags({'a': '1'}, {'b': 2}, False) == {'a': '1', 'b': '2'}
    assert desired_tags({'a': '1'}, {'a': None}, False) == {'a': ''}
    assert desired_tags({'a': '1'}, {}, True) == {}


def test_tag_filter():
    assert tag_filter(None) is None
    assert tag_filter({'team': None, 'env': 'prod', 'note': ''}) == ['env=prod', 'note=', 'team']


def test_create_sends_tags(run):
    created = dict(BUCKET, tags={'env': 'prod'})
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tier': 'infrequent_access', 'tags': {'env': 'prod'},
    }, {LIST: ([], [created]), DETAIL: created})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/object-storage/buckets', {
        'name': 'photos', 'tier': 'infrequent_access', 'versioning': False, 'tags': {'env': 'prod'},
    }, None)]


def test_equal_tags_are_not_changed(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tags': {'team': 'web', 'env': 'prod'},
    }, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and not result['changed']
    assert api.writes() == []


def test_omitted_tags_are_left_alone(run):
    status, result, api = run(object_storage_bucket, {'name': 'photos'}, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_purge_replaces_every_tag(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tags': {'env': 'dev'},
    }, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/object-storage/buckets/b1', {'tags': {'env': 'dev'}}, None)]


def test_no_purge_merges_with_the_current_tags(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tags': {'owner': 'ops'}, 'purge_tags': False,
    }, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/object-storage/buckets/b1',
                             {'tags': {'env': 'prod', 'team': 'web', 'owner': 'ops'}}, None)]


def test_no_purge_with_tags_already_present_is_unchanged(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tags': {'env': 'prod'}, 'purge_tags': False,
    }, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_empty_tags_clear_them(run):
    status, result, api = run(object_storage_bucket, {'name': 'photos', 'tags': {}}, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/object-storage/buckets/b1', {'tags': {}}, None)]


def test_check_mode_does_not_patch_tags(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tags': {'env': 'dev'}, '_ansible_check_mode': True,
    }, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'exit' and result['changed'] and api.writes() == []


def test_info_tag_filter_applies_to_buckets_and_usage_only(run):
    status, result, api = run(object_storage_info, {
        'gather': ['buckets', 'access_keys', 'usage'], 'tags': {'env': 'prod', 'team': None},
    }, {LIST: [BUCKET], ('GET', '/object-storage/keys'): [], ('GET', '/object-storage/usage'): {}})
    assert status == 'exit' and result['buckets'][0]['tags'] == BUCKET['tags']
    params = dict((c[1], c[3]) for c in api.calls)
    assert params['/object-storage/buckets']['tag'] == ['env=prod', 'team']
    assert params['/object-storage/usage']['tag'] == ['env=prod', 'team']
    assert 'tag' not in params['/object-storage/keys']


LOCKED = dict(BUCKET, versioning='enabled', protected=True,
              object_lock={'enabled': True, 'default_retention': {'mode': 'governance', 'days': 30, 'years': None}})
LOCK_PUT = ('PUT', '/object-storage/buckets/b1/object-lock')


def test_lock_retention():
    assert lock_retention(None) is None
    assert lock_retention({'mode': None, 'days': None, 'years': None}) is None
    assert lock_retention({'mode': 'governance', 'days': 30, 'years': None}) == {'mode': 'governance', 'days': 30}
    assert lock_retention({'mode': 'compliance', 'days': None, 'years': 7}) == {'mode': 'compliance', 'years': 7}


def test_create_with_object_lock(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tier': 'infrequent_access', 'object_lock': True,
        'object_lock_default': {'mode': 'governance', 'days': 30}, 'accept_object_lock_terms': True,
    }, {LIST: ([], [LOCKED]), DETAIL: LOCKED})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/object-storage/buckets', {
        'name': 'photos', 'tier': 'infrequent_access', 'versioning': True, 'object_lock': True,
        'object_lock_default': {'mode': 'governance', 'days': 30}, 'accept_object_lock_terms': True,
    }, None)]


def test_create_with_object_lock_needs_the_terms(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tier': 'infrequent_access', 'object_lock': True,
    }, {LIST: []})
    assert status == 'fail' and 'accept_object_lock_terms' in result['msg'] and api.writes() == []


def test_create_with_object_lock_refuses_versioning_off(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'tier': 'infrequent_access', 'object_lock': True, 'versioning': 'off',
        'accept_object_lock_terms': True,
    }, {LIST: []})
    assert status == 'fail' and api.writes() == []


def test_lock_default_needs_one_period(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'object_lock_default': {'mode': 'governance', 'days': 1, 'years': 1},
    }, {LIST: [LOCKED]})
    assert status == 'fail' and api.writes() == []


def test_object_lock_cannot_be_turned_on_later(run):
    status, result, api = run(object_storage_bucket, {'name': 'photos', 'object_lock': True},
                              {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'fail' and api.writes() == []


def test_same_lock_rule_is_not_changed(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'object_lock': True, 'object_lock_default': {'mode': 'governance', 'days': 30},
    }, {LIST: [LOCKED], DETAIL: LOCKED})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_different_lock_rule_is_put(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'object_lock_default': {'mode': 'compliance', 'years': 1}, 'accept_object_lock_terms': True,
    }, {LIST: [LOCKED], DETAIL: LOCKED})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PUT', '/object-storage/buckets/b1/object-lock', {
        'default_retention': {'mode': 'compliance', 'years': 1}, 'accept_object_lock_terms': True,
    }, None)]


def test_empty_lock_rule_removes_it(run):
    status, result, api = run(object_storage_bucket, {'name': 'photos', 'object_lock_default': {}},
                              {LIST: [LOCKED], DETAIL: LOCKED})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PUT', '/object-storage/buckets/b1/object-lock', {
        'default_retention': None, 'accept_object_lock_terms': False,
    }, None)]


def test_lock_rule_check_mode(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'object_lock_default': {}, '_ansible_check_mode': True,
    }, {LIST: [LOCKED], DETAIL: LOCKED})
    assert status == 'exit' and result['changed'] and api.writes() == []


def test_lock_rule_on_a_bucket_without_lock_fails(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'object_lock_default': {'mode': 'governance', 'days': 1},
    }, {LIST: [BUCKET], DETAIL: BUCKET})
    assert status == 'fail' and api.writes() == []


def test_delete_with_bypass_governance(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'state': 'absent', 'force': True, 'bypass_governance': True, 'wait': False,
    }, {LIST: [LOCKED]})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('DELETE', '/object-storage/buckets/b1', None,
                             {'force': 'true', 'bypass_governance': 'true'})]


def test_bypass_governance_needs_force(run):
    status, result, api = run(object_storage_bucket, {
        'name': 'photos', 'state': 'absent', 'bypass_governance': True,
    }, {LIST: [LOCKED]})
    assert status == 'fail' and api.writes() == []


def test_locked_content_kept_fails_the_delete(run):
    kept = dict(LOCKED, locked_content_kept=True, error_message='Some objects are still protected by Object Lock')
    status, result, api = run(object_storage_bucket, {'name': 'photos', 'state': 'absent', 'force': True},
                              {LIST: ([LOCKED], [kept])})
    assert status == 'fail' and 'Object Lock' in result['msg']


def test_key_with_bypass_governance(run):
    status, result, api = run(object_storage_access_key, {
        'name': 'veeam', 'tier': 'infrequent_access', 'bypass_governance': True, 'wait': False,
    }, {('GET', '/object-storage/keys'): [], ('POST', '/object-storage/keys'): {'uuid': 'k1'}})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/object-storage/keys', {
        'name': 'veeam', 'tier': 'infrequent_access', 'permission': 'read_write', 'bypass_governance': True,
    }, None)]


def test_read_only_key_cannot_bypass_governance(run):
    status, result, api = run(object_storage_access_key, {
        'name': 'veeam', 'tier': 'infrequent_access', 'permission': 'read_only', 'bypass_governance': True,
    }, {('GET', '/object-storage/keys'): []})
    assert status == 'fail' and api.writes() == []
