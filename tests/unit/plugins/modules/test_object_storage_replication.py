# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import normalize_endpoint, replication_tags
from ansible_collections.cubepathinc.cloud.plugins.modules import (
    object_storage_info, object_storage_replication, object_storage_replication_grant,
)

SRC = {'uuid': 's1', 'name': 'photos', 'status': 'active'}
DST = {'uuid': 'd1', 'name': 'photos-replica', 'status': 'active'}
BUCKETS = ('GET', '/object-storage/buckets')
REPLS = ('GET', '/object-storage/replications')
DETAIL = ('GET', '/object-storage/replications/r1')
RULES = {'enabled': True, 'prefix': None, 'tags': [], 'delete_marker_replication': False,
         'delete_replication': False, 'existing_objects': True}
CP_REPL = {'uuid': 'r1', 'status': 'active', 'pause_reason': None, 'direction': 'outgoing',
           'source': {'bucket_uuid': 's1', 'bucket_name': 'photos'},
           'destination': {'type': 'cubepath', 'bucket_uuid': 'd1', 'bucket_name': 'photos-replica'},
           'rules': RULES}
EXT_REPL = dict(CP_REPL, destination={'type': 'external', 'provider': 'aws', 'endpoint': 's3.eu-west-1.amazonaws.com',
                                      'region': 'eu-west-1', 'bucket': 'acme-backup', 'path_style': 'auto',
                                      'access_key_id': '****WXYZ'})
EXT_DEST = {'type': 'external', 'bucket': 'acme-backup', 'provider': 'aws', 'endpoint': 's3.eu-west-1.amazonaws.com:443',
            'region': 'eu-west-1', 'access_key_id': 'AKIAWXYZ', 'secret_access_key': 'shh'}
CP_DEST = {'type': 'cubepath', 'bucket': 'photos-replica'}


def test_helpers():
    assert replication_tags({'b': 1, 'a': None}) == [{'key': 'a', 'value': ''}, {'key': 'b', 'value': '1'}]
    assert replication_tags(None) == []
    assert normalize_endpoint(' S3.Example.com:443 ') == 's3.example.com'


def test_create_cubepath(run):
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': CP_DEST}, {
        BUCKETS: [SRC, DST], REPLS: ([], [CP_REPL]),
        ('POST', '/object-storage/replications'): {'detail': 'x', 'uuid': 'r1', 'status': 'pending'},
        DETAIL: CP_REPL,
    })
    assert status == 'exit' and result['changed'] and result['replication'] == CP_REPL
    assert api.writes() == [('POST', '/object-storage/replications', {
        'source_bucket_uuid': 's1', 'destination': {'type': 'cubepath', 'bucket_uuid': 'd1'},
        'delete_marker_replication': False, 'delete_replication': False, 'existing_objects': True,
    }, None)]
    assert api.calls[1][3] == {'direction': 'outgoing', 'bucket_uuid': 's1'}


def test_create_with_grant_for_a_bucket_of_another_org(run):
    dest = {'type': 'cubepath', 'bucket': 'other-uuid', 'grant_token': 'cprg_x'}
    status, result, api = run(object_storage_replication, {'source_bucket': 's1', 'destination': dest, 'wait': False}, {
        BUCKETS: [SRC], REPLS: [],
        ('POST', '/object-storage/replications'): {'uuid': 'r1', 'status': 'pending'}, DETAIL: CP_REPL,
    })
    assert status == 'exit' and result['changed']
    assert api.writes()[0][2]['destination'] == {'type': 'cubepath', 'bucket_uuid': 'other-uuid', 'grant_token': 'cprg_x'}


def test_unknown_destination_without_grant_fails(run):
    dest = {'type': 'cubepath', 'bucket': 'nope'}
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': dest},
                              {BUCKETS: [SRC], REPLS: []})
    assert status == 'fail' and 'grant_token' in result['msg'] and api.writes() == []


def test_create_external_with_filter(run):
    status, result, api = run(object_storage_replication, {
        'source_bucket': 'photos', 'destination': EXT_DEST, 'tags': {'backup': 'yes'}, 'existing_objects': False,
    }, {BUCKETS: [SRC], REPLS: ([], [EXT_REPL]),
        ('POST', '/object-storage/replications'): {'uuid': 'r1', 'status': 'pending'}, DETAIL: EXT_REPL})
    assert status == 'exit' and result['changed']
    body = api.writes()[0][2]
    assert body['destination'] == {'type': 'external', 'endpoint': 's3.eu-west-1.amazonaws.com:443', 'region': 'eu-west-1',
                                   'bucket': 'acme-backup', 'path_style': 'auto', 'access_key_id': 'AKIAWXYZ',
                                   'secret_access_key': 'shh', 'provider': 'aws'}
    assert body['tags'] == [{'key': 'backup', 'value': 'yes'}] and body['existing_objects'] is False


def test_external_needs_credentials(run):
    dest = dict(EXT_DEST, secret_access_key=None)
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': dest},
                              {BUCKETS: [SRC], REPLS: []})
    assert status == 'fail' and 'secret_access_key' in result['msg']


def test_external_field_on_cubepath_destination_fails(run):
    dest = dict(CP_DEST, endpoint='s3.example.com')
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': dest},
                              {BUCKETS: [SRC, DST], REPLS: []})
    assert status == 'fail' and 'endpoint' in result['msg']


def test_create_paused_waits_then_pauses(run):
    pending = dict(CP_REPL, status='pending')
    status, result, api = run(object_storage_replication, {
        'source_bucket': 'photos', 'destination': CP_DEST, 'enabled': False, 'wait': False,
    }, {BUCKETS: [SRC, DST], REPLS: ([], [pending], [CP_REPL]),
        ('POST', '/object-storage/replications'): {'uuid': 'r1', 'status': 'pending'}, DETAIL: CP_REPL})
    assert status == 'exit' and result['changed']
    assert api.writes()[-1] == ('PATCH', '/object-storage/replications/r1', {'enabled': False}, None)


def test_same_rules_is_unchanged(run):
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': CP_DEST},
                              {BUCKETS: [SRC, DST], REPLS: [CP_REPL]})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_external_same_key_id_is_unchanged(run):
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': EXT_DEST},
                              {BUCKETS: [SRC], REPLS: [EXT_REPL]})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_rule_change_patches_only_the_difference(run):
    status, result, api = run(object_storage_replication, {
        'source_bucket': 'photos', 'destination': CP_DEST, 'tags': {'env': 'prod'}, 'delete_replication': True,
    }, {BUCKETS: [SRC, DST], REPLS: [dict(CP_REPL, rules=dict(RULES, prefix='img/'))], DETAIL: CP_REPL})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/object-storage/replications/r1', {
        'tags': [{'key': 'env', 'value': 'prod'}], 'prefix': None, 'delete_replication': True,
    }, None)]


def test_pause(run):
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': CP_DEST, 'enabled': False},
                              {BUCKETS: [SRC, DST], REPLS: [CP_REPL], DETAIL: CP_REPL})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/object-storage/replications/r1', {'enabled': False}, None)]


def test_paused_by_cubepath_is_not_resumed(run):
    paused = dict(CP_REPL, status='paused', pause_reason='org', rules=dict(RULES, enabled=False))
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': CP_DEST},
                              {BUCKETS: [SRC, DST], REPLS: [paused]})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_new_key_id_rotates_credentials(run):
    dest = dict(EXT_DEST, access_key_id='AKIANEW1', secret_access_key='new')
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'destination': dest},
                              {BUCKETS: [SRC], REPLS: [EXT_REPL], DETAIL: EXT_REPL})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/object-storage/replications/r1',
                             {'destination': {'access_key_id': 'AKIANEW1', 'secret_access_key': 'new'}}, None)]


def test_update_credentials_forces_rotation(run):
    status, result, api = run(object_storage_replication, {
        'source_bucket': 'photos', 'destination': EXT_DEST, 'update_credentials': True,
    }, {BUCKETS: [SRC], REPLS: [EXT_REPL], DETAIL: EXT_REPL})
    assert status == 'exit' and result['changed']
    assert api.writes()[0][2] == {'destination': {'access_key_id': 'AKIAWXYZ', 'secret_access_key': 'shh'}}


def test_destination_change_fails(run):
    status, result, api = run(object_storage_replication, {
        'source_bucket': 'photos', 'destination': dict(EXT_DEST, bucket='other-bucket'),
    }, {BUCKETS: [SRC], REPLS: [EXT_REPL]})
    assert status == 'fail' and 'cannot be changed' in result['msg'] and api.writes() == []


def test_check_mode_does_not_write(run):
    status, result, api = run(object_storage_replication, {
        'source_bucket': 'photos', 'destination': CP_DEST, 'enabled': False, '_ansible_check_mode': True,
    }, {BUCKETS: [SRC, DST], REPLS: [CP_REPL]})
    assert status == 'exit' and result['changed'] and api.writes() == []


def test_absent(run):
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'state': 'absent'},
                              {BUCKETS: [SRC], REPLS: ([CP_REPL], [dict(CP_REPL, status='deleting')], [])})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('DELETE', '/object-storage/replications/r1', None, None)]


def test_absent_without_replication(run):
    status, result, api = run(object_storage_replication, {'source_bucket': 'photos', 'state': 'absent'},
                              {BUCKETS: [SRC], REPLS: []})
    assert status == 'exit' and not result['changed'] and api.writes() == []


GRANTS = ('GET', '/object-storage/buckets/d1/replication-grants')
GRANT = {'uuid': 'g1', 'token_prefix': 'cprg_AbCd', 'note': 'for Acme', 'status': 'open'}


def test_grant_create_returns_token(run):
    status, result, api = run(object_storage_replication_grant, {'bucket': 'photos-replica', 'note': 'for Acme'}, {
        BUCKETS: [DST], GRANTS: [],
        ('POST', '/object-storage/buckets/d1/replication-grants'): {'detail': 'x', 'uuid': 'g1', 'token': 'cprg_secret'},
    })
    assert status == 'exit' and result['changed'] and result['grant']['token'] == 'cprg_secret'
    assert 'detail' not in result['grant']
    assert api.writes() == [('POST', '/object-storage/buckets/d1/replication-grants',
                             {'expires_in_days': 7, 'note': 'for Acme'}, None)]


def test_grant_with_same_note_is_reused(run):
    status, result, api = run(object_storage_replication_grant, {'bucket': 'photos-replica', 'note': 'for Acme'},
                              {BUCKETS: [DST], GRANTS: [GRANT]})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_grant_absent_revokes_open_ones_only(run):
    used = dict(GRANT, uuid='g2', status='used')
    status, result, api = run(object_storage_replication_grant, {'bucket': 'd1', 'note': 'for Acme', 'state': 'absent'},
                              {BUCKETS: [DST], GRANTS: [GRANT, used]})
    assert status == 'exit' and result['changed'] and result['revoked'] == ['g1']
    assert api.writes() == [('DELETE', '/object-storage/replication-grants/g1', None, None)]


def test_grant_absent_needs_uuid_or_note(run):
    status, result, api = run(object_storage_replication_grant, {'bucket': 'd1', 'state': 'absent'}, {BUCKETS: [DST]})
    assert status == 'fail'


def test_info_replications_and_grants(run):
    status, result, api = run(object_storage_info, {
        'gather': ['replications', 'replication_grants'], 'bucket': 'photos', 'direction': 'outgoing',
    }, {BUCKETS: [SRC], ('GET', '/object-storage/buckets/s1'): SRC, REPLS: [CP_REPL],
        ('GET', '/object-storage/buckets/s1/replication-grants'): [GRANT]})
    assert status == 'exit' and result['replications'] == [CP_REPL] and result['replication_grants'] == [GRANT]
    params = dict((c[1], c[3]) for c in api.calls)
    assert params['/object-storage/replications'] == {'direction': 'outgoing', 'bucket_uuid': 's1'}


def test_info_grants_need_a_bucket(run):
    status, result, api = run(object_storage_info, {'gather': ['replication_grants']}, {})
    assert status == 'fail'
