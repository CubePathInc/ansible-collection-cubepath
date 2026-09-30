# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import (
    managed_database, managed_database_action, managed_database_db, managed_database_user,
)

PLANS = [
    {'location_name': 'eu-bcn-1', 'plans': [{'uuid': 'p-bcn', 'name': 'mysql.micro', 'engine': 'mysql'}]},
    {'location_name': 'us-mia-1', 'plans': [{'uuid': 'p-mia', 'name': 'mysql.micro', 'engine': 'mysql'}]},
]
ACTIVE = {'uuid': 'md-1', 'name': 'app-db', 'engine': 'mysql', 'status': 'active', 'replicas': 3,
          'protected': False, 'label': None, 'plan': {'uuid': 'p-bcn'}, 'backup_enabled': False,
          'backup_schedule_cron': None, 'backup_retention_days': 7}


def test_create_resolves_the_plan_of_the_location(run):
    status, result, api = run(managed_database, {
        'name': 'app-db', 'project_id': 882, 'engine': 'mysql', 'version': '8.0.39', 'plan': 'mysql.micro',
        'location': 'eu-bcn-1', 'replicas': 3, 'backup_schedule': '0 3 * * *', 'wait': False,
    }, {
        ('GET', '/managed-databases/'): ([], [{'uuid': 'md-1', 'name': 'app-db'}]),
        ('GET', '/managed-database-plans/'): PLANS,
        ('GET', '/managed-databases/md-1'): dict(ACTIVE, status='provisioning', backup_enabled=True, backup_schedule_cron='0 3 * * *'),
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/managed-databases/', {
        'project_id': 882, 'name': 'app-db', 'engine': 'mysql', 'version': '8.0.39', 'plan_uuid': 'p-bcn',
        'replicas': 3, 'backup': {'schedule_cron': '0 3 * * *'},
    }, None)]


def test_ambiguous_plan_name_fails(run):
    status, result, api = run(managed_database, {
        'name': 'app-db', 'project_id': 882, 'engine': 'mysql', 'version': '8.0.39', 'plan': 'mysql.micro',
    }, {('GET', '/managed-databases/'): [], ('GET', '/managed-database-plans/'): PLANS})
    assert status == 'fail' and 'several locations' in result['msg']
    assert api.writes() == []


def test_existing_database_is_left_alone(run):
    status, result, api = run(managed_database, {'name': 'app-db', 'replicas': 3, 'plan': 'p-bcn'}, {
        ('GET', '/managed-databases/'): [{'uuid': 'md-1', 'name': 'app-db'}],
        ('GET', '/managed-database-plans/'): PLANS,
        ('GET', '/managed-databases/md-1'): ACTIVE,
    })
    assert status == 'exit' and not result['changed']
    assert api.writes() == []


def test_scale_and_protect(run):
    status, result, api = run(managed_database, {'name': 'app-db', 'replicas': 5, 'protected': True, 'label': 'prod'}, {
        ('GET', '/managed-databases/'): [{'uuid': 'md-1', 'name': 'app-db'}],
        ('GET', '/managed-databases/md-1'): ACTIVE,
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [
        ('PATCH', '/managed-databases/md-1', {'label': 'prod'}, None),
        ('POST', '/managed-databases/md-1/protection', {'enabled': True}, None),
        ('POST', '/managed-databases/md-1/scale', {'replicas': 5}, None),
    ]


def test_delete_waits_out_provisioning_and_unprotects(run):
    status, result, api = run(managed_database, {'name': 'app-db', 'state': 'absent', 'protected': False}, {
        ('GET', '/managed-databases/'): ([{'uuid': 'md-1', 'name': 'app-db'}],) * 4 + ([],),
        ('GET', '/managed-databases/md-1'): (dict(ACTIVE, status='provisioning'), dict(ACTIVE, protected=True)),
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [
        ('POST', '/managed-databases/md-1/protection', {'enabled': False}, None),
        ('DELETE', '/managed-databases/md-1', None, None),
    ]


def test_user_password_is_returned_once(run):
    status, result, api = run(managed_database_user, {'managed_database': 'app-db', 'username': 'app', 'wait': False}, {
        ('GET', '/managed-databases/'): [{'uuid': 'md-1', 'name': 'app-db'}],
        ('GET', '/managed-databases/md-1/users'): ([], [{'uuid': 'u-1', 'username': 'app', 'status': 'pending'}]),
        ('POST', '/managed-databases/md-1/users'): {'uuid': 'u-1', 'password': 'generated-secret'},
    })
    assert status == 'exit' and result['changed'] and result['password'] == 'generated-secret'
    assert api.writes() == [('POST', '/managed-databases/md-1/users', {'username': 'app'}, None)]


def test_logical_database_absent(run):
    status, result, api = run(managed_database_db, {'managed_database': 'md-1', 'name': 'appdb', 'state': 'absent'}, {
        ('GET', '/managed-databases/'): [{'uuid': 'md-1', 'name': 'app-db'}],
        ('GET', '/managed-databases/md-1/databases'): ([{'uuid': 'd-1', 'name': 'appdb', 'status': 'active'}], []),
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('DELETE', '/managed-databases/md-1/databases/d-1', None, None)]


def test_configure_sends_params(run):
    status, result, api = run(managed_database_action, {
        'managed_database': 'app-db', 'action': 'configure', 'parameters': {'max_connections': 500}, 'wait': False,
    }, {('GET', '/managed-databases/'): [{'uuid': 'md-1', 'name': 'app-db'}]})
    assert status == 'exit'
    assert api.writes() == [('PATCH', '/managed-databases/md-1/config', {'params': {'max_connections': 500}}, None)]
