# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import desired_tags, tag_filter
from ansible_collections.cubepathinc.cloud.plugins.modules import object_storage_bucket, object_storage_info

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
