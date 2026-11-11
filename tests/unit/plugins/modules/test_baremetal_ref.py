# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_baremetal import normalize_baremetal_ref
from ansible_collections.cubepathinc.cloud.plugins.modules import (
    baremetal_action, baremetal_info, baremetal_power, floating_ip,
)

UUID = '6f1c2a9e-3b7d-4e58-9a10-5c2d8e4f7b31'
UPPER = UUID.upper()


@pytest.mark.parametrize('value,expected', [
    (10, '10'), ('10', '10'), (UUID, UUID), (UPPER, UUID), (' %s ' % UPPER, UUID),
    ('', None), ('abc', None), ('10a', None), ('-1', None), ('1.5', None), (UUID[:-1], None),
    ('../etc', None), ('10/power', None), (None, None),
])
def test_normalize(value, expected):
    assert normalize_baremetal_ref(value) == expected


@pytest.mark.parametrize('ref,expected', [(10, '10'), ('10', '10'), (UUID, UUID), (UPPER, UUID)])
def test_action_routes_take_number_or_uuid(run, ref, expected):
    status, result, api = run(baremetal_action, {'action': 'protect', 'baremetal_id': ref}, {})
    assert status == 'exit'
    assert api.writes() == [('POST', '/baremetal/%s/protection' % expected, {'enabled': True}, None)]


def test_action_update_and_ssh_key_routes(run):
    status, result, api = run(baremetal_action, {'action': 'update', 'baremetal_id': UUID, 'hostname': 'h'}, {})
    assert api.writes()[0][1] == '/baremetal/update/%s' % UUID
    status, result, api = run(baremetal_action, {'action': 'remove_ssh_key', 'baremetal_id': UUID, 'ssh_key_ids': [4]}, {})
    assert api.writes()[0][1] == '/baremetal/%s/ssh-keys/4' % UUID


@pytest.mark.parametrize('module,args', [
    (baremetal_action, {'action': 'protect'}),
    (baremetal_power, {'state': 'started'}),
    (baremetal_info, {}),
    (floating_ip, {'state': 'assigned', 'address': '203.0.113.7'}),
])
@pytest.mark.parametrize('bad', ['abc', '10/power', '12-34'])
def test_invalid_reference_fails_before_any_request(run, module, args, bad):
    status, result, api = run(module, dict(args, baremetal_id=bad), {})
    assert status == 'fail'
    assert 'baremetal_id' in result['msg']
    assert api.calls == []


def test_check_mode_message_uses_the_reference(run):
    status, result, api = run(baremetal_action, {'action': 'rescue', 'baremetal_id': UPPER, '_ansible_check_mode': True}, {})
    assert status == 'exit'
    assert result['msg'] == 'Would rescue baremetal %s' % UUID


def test_power_with_uuid(run):
    status, result, api = run(baremetal_power, {'baremetal_id': UPPER, 'state': 'restarted'}, {})
    assert api.writes()[0][:2] == ('POST', '/baremetal/%s/power/%s' % (UUID, baremetal_power.POWER_MAP['restarted']))
    assert result['msg'].startswith('Baremetal %s power action' % UUID)


def test_floating_ip_assign_with_uuid(run):
    status, result, api = run(floating_ip, {'state': 'assigned', 'address': '203.0.113.7', 'baremetal_id': UPPER}, {})
    assert api.writes() == [('POST', '/floating_ips/assign/baremetal/%s' % UUID, None, {'address': '203.0.113.7'})]


PROJECTS_OLD = [{'baremetals': [{'id': 7, 'hostname': 'a'}, {'id': 17, 'hostname': 'b'}]}]
PROJECTS_NEW = [{'baremetals': [{'id': '7', 'uuid': UUID, 'hostname': 'a'}, {'id': 17, 'uuid': 'x', 'hostname': 'b'}]}]


@pytest.mark.parametrize('projects,ref,expected', [
    (PROJECTS_OLD, 7, ['a']),
    (PROJECTS_OLD, '17', ['b']),
    (PROJECTS_NEW, 7, ['a']),
    (PROJECTS_NEW, UUID, ['a']),
    (PROJECTS_NEW, UPPER, ['a']),
    (PROJECTS_OLD, UUID, []),
])
def test_info_matches_id_or_uuid(run, projects, ref, expected):
    status, result, api = run(baremetal_info, {'baremetal_id': ref}, {('GET', '/projects/'): projects})
    assert status == 'exit'
    assert [s['hostname'] for s in result['servers']] == expected


def test_info_gather_kvm_and_os_with_uuid(run):
    routes = {('GET', '/projects/'): PROJECTS_NEW}
    status, result, api = run(baremetal_info, {'baremetal_id': UUID, 'gather': ['os', 'kvm']}, routes)
    gets = [c[1] for c in api.calls]
    assert '/baremetal/os/%s' % UUID in gets and '/baremetal/%s/kvm' % UUID in gets


def test_info_gather_needs_the_reference(run):
    status, result, api = run(baremetal_info, {'gather': ['kvm']}, {('GET', '/projects/'): PROJECTS_OLD})
    assert status == 'fail'
