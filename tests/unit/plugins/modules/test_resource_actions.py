# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import (
    availability_group, baremetal_action, cdn_zone_action, dns_record_health_check, dns_zone_soa,
    floating_ip_reverse_dns, loadbalancer, loadbalancer_target, network_bgp_peer, ssh_key, vps_action,
    vps_backup_settings, vps_iso,
)


def test_vps_ssh_keys_body_is_a_bare_list(run):
    status, result, api = run(vps_action, {'action': 'add_ssh_keys', 'vps_id': 1, 'ssh_key_ids': [3, 4]}, {})
    assert api.writes() == [('POST', '/vps/1/ssh-keys', [3, 4], None)]


def test_baremetal_protect(run):
    status, result, api = run(baremetal_action, {'action': 'protect', 'baremetal_id': 9}, {})
    assert api.writes() == [('POST', '/baremetal/9/protection', {'enabled': True}, None)]


def test_cdn_purge_everything(run):
    status, result, api = run(cdn_zone_action, {'action': 'purge_cache', 'zone_uuid': 'z'}, {
        ('POST', '/cdn/zones/z/purge-cache'): {'purge_uuid': 'p', 'status': 'pending'},
    })
    assert api.writes() == [('POST', '/cdn/zones/z/purge-cache', {'everything': True}, None)]


def test_cdn_sign_url_changes_nothing(run):
    status, result, api = run(cdn_zone_action, {'action': 'sign_url', 'zone_uuid': 'z', 'path': '/a.mp4'}, {
        ('POST', '/cdn/zones/z/token-auth/sign-url'): {'signed_url': 'https://x/a.mp4?token=t'},
    })
    assert status == 'exit' and not result['changed']


def test_soa_only_sends_differences(run):
    status, result, api = run(dns_zone_soa, {'zone_uuid': 'z', 'minimum': 60, 'refresh': 3600}, {
        ('GET', '/dns/zones/z/soa'): {'refresh': 3600, 'minimum': 300},
    })
    assert api.writes() == [('PUT', '/dns/zones/z/soa', {'minimum': 60}, None)]


def test_health_check_unchanged(run):
    check = {'record_uuid': 'r', 'name': 'web', 'check_type': 'https', 'path': '/', 'enabled': True}
    status, result, api = run(dns_record_health_check, {'zone_uuid': 'z', 'record_uuid': 'r', 'check_type': 'https'}, {
        ('GET', '/dns/zones/z/health-checks'): [check],
    })
    assert status == 'exit' and not result['changed']


def test_reverse_dns_ignores_trailing_dot(run):
    status, result, api = run(floating_ip_reverse_dns, {'address': '203.0.113.1', 'hostname': 'mail.example.com.'}, {
        ('GET', '/floating_ips/organization'): {'single_ips': [{'address': '203.0.113.1', 'reverse_dns': 'mail.example.com'}]},
    })
    assert status == 'exit' and not result['changed']


def test_loadbalancer_resize_and_move(run):
    lb = {'uuid': 'lb', 'name': 'web', 'plan_name': 'lb.small', 'project_id': 1, 'protected': False}
    status, result, api = run(loadbalancer, {'name': 'web', 'plan': 'lb.small', 'location': 'eu-bcn-1',
                                             'resize_plan': 'lb.medium', 'project_id': 2}, {
        ('GET', '/loadbalancer/'): [lb],
    })
    assert api.writes() == [
        ('POST', '/loadbalancer/lb/resize', {'plan_name': 'lb.medium'}, None),
        ('POST', '/loadbalancer/lb/move-project', {'project_id': 2}, None),
    ]


def test_batch_targets_skip_existing(run):
    lbs = [{'uuid': 'lb', 'listeners': [{'uuid': 'l', 'targets': [{'target_type': 'vps', 'target_uuid': '1'}]}]}]
    status, result, api = run(loadbalancer_target, {'lb_uuid': 'lb', 'listener_uuid': 'l', 'targets': [
        {'target_type': 'vps', 'target_uuid': '1'}, {'target_type': 'vps', 'target_uuid': '2'},
    ]}, {('GET', '/loadbalancer/'): lbs, ('POST', '/loadbalancer/lb/listeners/l/targets/batch'): {'targets': []}})
    assert api.writes() == [('POST', '/loadbalancer/lb/listeners/l/targets/batch',
                             {'targets': [{'target_type': 'vps', 'target_uuid': '2', 'weight': 100}]}, None)]


def test_bgp_peer_update(run):
    peer = {'id': 'bp', 'peer_type': 'vps', 'peer_target': '12', 'remote_asn': 65010, 'max_prefix': 100, 'enabled': True}
    status, result, api = run(network_bgp_peer, {'network_id': 4, 'peer_target': '12', 'max_prefix': 50}, {
        ('GET', '/networks/4/bgp-peers'): [peer],
    })
    assert api.writes() == [('PATCH', '/networks/4/bgp-peers/bp', {'max_prefix': 50}, None)]


def test_ssh_key_rename(run):
    status, result, api = run(ssh_key, {'name': 'new-name', 'ssh_key_id': 64}, {
        ('GET', '/sshkey/user/sshkeys'): {'sshkeys': [{'id': 64, 'name': 'old'}]},
    })
    assert api.writes() == [('PUT', '/sshkey/64', {'name': 'new-name'}, None)]


def test_backup_settings_idempotent(run):
    current = {'enabled': True, 'schedule_hour': 3, 'retention_days': 7, 'max_backups': 7}
    status, result, api = run(vps_backup_settings, {'vps_id': 1, 'enabled': True, 'schedule_hour': 3}, {
        ('GET', '/vps/1/backup/settings'): current,
    })
    assert status == 'exit' and not result['changed']


def test_iso_mount_by_name(run):
    status, result, api = run(vps_iso, {'vps_id': 1, 'iso': 'Rescue'}, {
        ('GET', '/vps/1/isos'): {'mounted_iso_id': None, 'items': [{'id': 'iso-1', 'name': 'Rescue'}]},
    })
    assert api.writes() == [('POST', '/vps/1/iso', {'iso_id': 'iso-1'}, None)]


def test_availability_group_members(run):
    group = {'uuid': 'ag', 'name': 'web', 'project_id': 882, 'vps_list': [{'id': 1}, {'id': 2}]}
    status, result, api = run(availability_group, {'name': 'web', 'project_id': 882, 'vps_ids': [2, 3]}, {
        ('GET', '/projects/'): [{'project': {'id': 882}}],
        ('GET', '/vps/availability-groups/project/882'): {'groups': [group]},
        ('GET', '/vps/availability-groups/ag'): group,
    })
    assert api.writes() == [
        ('DELETE', '/vps/availability-groups/ag/vps/1', None, None),
        ('POST', '/vps/availability-groups/ag/vps/3', None, None),
    ]
