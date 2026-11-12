# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_baremetal import normalize_baremetal_ref
from ansible_collections.cubepathinc.cloud.plugins.modules import (
    baremetal_action, baremetal_info, baremetal_power, cloud_alert, floating_ip, loadbalancer_target,
    network_bgp_peer, network_route,
)

UUID = '6f1c2a9e-3b7d-4e58-9a10-5c2d8e4f7b31'
UPPER = UUID.upper()


@pytest.mark.parametrize('value,expected', [
    (UUID, UUID), (UPPER, UUID),
    (10, None), ('10', None), ('007', None), (' %s ' % UUID, None),
    ('', None), ('abc', None), ('10a', None), ('-1', None), ('1.5', None), (UUID[:-1], None),
    ('../etc', None), ('10/power', None), (None, None), (UUID + '\n', None),
])
def test_normalize(value, expected):
    assert normalize_baremetal_ref(value) == expected


@pytest.mark.parametrize('ref', [UUID, UPPER])
def test_action_routes_take_the_uuid(run, ref):
    status, result, api = run(baremetal_action, {'action': 'protect', 'baremetal_id': ref}, {})
    assert status == 'exit'
    assert api.writes() == [('POST', '/baremetal/%s/protection' % UUID, {'enabled': True}, None)]


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
@pytest.mark.parametrize('bad', ['10', '007', 'abc', '10/power', '12-34'])
def test_a_number_or_anything_else_fails_before_any_request(run, module, args, bad):
    status, result, api = run(module, dict(args, baremetal_id=bad), {})
    assert status == 'fail'
    assert 'baremetal_id' in result['msg'] and 'must be a uuid' in result['msg']
    assert api.calls == []


def test_check_mode_message_uses_the_uuid(run):
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


PROJECTS = [{'baremetals': [{'id': UUID, 'uuid': UUID, 'hostname': 'a'},
                            {'id': 'aaaaaaaa-0000-4000-8000-000000000000', 'hostname': 'b'}]}]


@pytest.mark.parametrize('ref,expected', [
    (UUID, ['a']),
    (UPPER, ['a']),
    ('bbbbbbbb-0000-4000-8000-000000000000', []),
])
def test_info_matches_the_uuid(run, ref, expected):
    status, result, api = run(baremetal_info, {'baremetal_id': ref}, {('GET', '/projects/'): PROJECTS})
    assert status == 'exit'
    assert [s['hostname'] for s in result['servers']] == expected


def test_info_gather_kvm_and_os_with_uuid(run):
    routes = {('GET', '/projects/'): PROJECTS}
    status, result, api = run(baremetal_info, {'baremetal_id': UUID, 'gather': ['os', 'kvm']}, routes)
    gets = [c[1] for c in api.calls]
    assert '/baremetal/os/%s' % UUID in gets and '/baremetal/%s/kvm' % UUID in gets


def test_info_gather_needs_the_reference(run):
    status, result, api = run(baremetal_info, {'gather': ['kvm']}, {('GET', '/projects/'): PROJECTS})
    assert status == 'fail'


def test_route_to_a_baremetal_takes_the_uuid_and_is_idempotent(run):
    args = {'network_id': 4, 'destination': '10.1.0.0/24', 'next_hop_type': 'baremetal', 'next_hop_target': UPPER}
    status, result, api = run(network_route, args, {('GET', '/networks/4/routes'): [], ('POST', '/networks/4/routes'): {}})
    assert api.writes() == [('POST', '/networks/4/routes',
                             {'destination': '10.1.0.0/24', 'next_hop_type': 'baremetal', 'next_hop_target': UUID}, None)]
    existing = [{'id': 'r1', 'destination': '10.1.0.0/24', 'next_hop_type': 'baremetal', 'next_hop_target': UUID}]
    status, result, api = run(network_route, args, {('GET', '/networks/4/routes'): existing})
    assert status == 'exit' and not result['changed'] and api.writes() == []


def test_bgp_peer_to_a_baremetal_takes_the_uuid(run):
    args = {'network_id': 4, 'peer_type': 'baremetal', 'peer_target': UPPER, 'remote_asn': 65010}
    routes = {('GET', '/networks/4/bgp-peers'): [], ('POST', '/networks/4/bgp-peers'): {'peer_id': 'bp'}}
    status, result, api = run(network_bgp_peer, args, routes)
    assert api.writes()[0] == ('POST', '/networks/4/bgp-peers',
                               {'peer_type': 'baremetal', 'peer_target': UUID, 'remote_asn': 65010}, None)


def test_lb_targets_of_a_baremetal_take_the_uuid(run):
    lbs = [{'uuid': 'lb', 'listeners': [{'uuid': 'l', 'targets': [{'target_type': 'baremetal', 'target_uuid': UUID}]}]}]
    routes = {('GET', '/loadbalancer/'): lbs, ('POST', '/loadbalancer/lb/listeners/l/targets/batch'): {'targets': []}}
    status, result, api = run(loadbalancer_target, {'lb_uuid': 'lb', 'listener_uuid': 'l', 'targets': [
        {'target_type': 'baremetal', 'target_uuid': UPPER}]}, routes)
    assert status == 'exit' and not result['changed'] and api.writes() == []
    status, result, api = run(loadbalancer_target, {
        'lb_uuid': 'lb', 'listener_uuid': 'l', 'target_type': 'baremetal', 'target_uuid': UPPER}, {})
    assert api.writes() == [('POST', '/loadbalancer/lb/listeners/l/targets',
                             {'target_type': 'baremetal', 'target_uuid': UUID, 'weight': 100}, None)]


def test_alert_on_a_baremetal_takes_the_uuid(run):
    routes = {('GET', '/triggers/'): [], ('GET', '/triggers/notificators/'): [{'id': 'n1', 'name': 'ops'}],
              ('POST', '/triggers/'): {'id': 'a1'}}
    status, result, api = run(cloud_alert, {
        'name': 'bm', 'project_id': 1, 'target_type': 'baremetal', 'target_id': UPPER, 'metric': 'network_in',
        'operator': 'gt', 'threshold': 1, 'channels': ['ops']}, routes)
    assert status == 'exit'
    assert api.writes()[0][2]['target_id'] == UUID


@pytest.mark.parametrize('module,args', [
    (network_route, {'network_id': 4, 'destination': '10.1.0.0/24', 'next_hop_type': 'baremetal',
                     'next_hop_target': '12'}),
    (network_bgp_peer, {'network_id': 4, 'peer_type': 'baremetal', 'peer_target': '12', 'remote_asn': 65010}),
    (loadbalancer_target, {'lb_uuid': 'lb', 'listener_uuid': 'l', 'target_type': 'baremetal', 'target_uuid': '12'}),
    (loadbalancer_target, {'lb_uuid': 'lb', 'listener_uuid': 'l', 'targets': [
        {'target_type': 'baremetal', 'target_uuid': '12'}]}),
    (cloud_alert, {'name': 'bm', 'target_type': 'baremetal', 'target_id': '12'}),
])
def test_a_baremetal_target_number_fails_before_any_write(run, module, args):
    routes = {('GET', '/loadbalancer/'): [], ('GET', '/triggers/'): []}
    status, result, api = run(module, args, routes)
    assert status == 'fail'
    assert 'must be a uuid' in result['msg']
    assert api.writes() == []
