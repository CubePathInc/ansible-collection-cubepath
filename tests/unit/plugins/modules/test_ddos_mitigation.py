# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import (
    ddos_attack_info, ddos_firewall_rule, ddos_prefix_list, ddos_protection_profile,
)

LISTS = {'prefix_lists': [{'uuid': 'pl-1', 'name': 'trusted', 'is_global': False},
                          {'uuid': 'pl-g', 'name': 'scanners', 'is_global': True}]}


def test_prefix_list_created_then_entries_synced(run):
    status, result, api = run(ddos_prefix_list, {'name': 'new', 'entries': ['192.0.2.7', '10.0.0.0/24']}, {
        ('GET', '/ddos-mitigation/prefix-lists'): ({'prefix_lists': []}, {'prefix_lists': [{'uuid': 'pl-2', 'name': 'new'}]}),
        ('GET', '/ddos-mitigation/prefix-lists/pl-2/entries'): ([], [{'network': '192.0.2.7/32'}, {'network': '10.0.0.0/24'}]),
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [
        ('POST', '/ddos-mitigation/prefix-lists', {'name': 'new'}, None),
        ('POST', '/ddos-mitigation/prefix-lists/pl-2/entries', {'network': '192.0.2.7/32'}, None),
        ('POST', '/ddos-mitigation/prefix-lists/pl-2/entries', {'network': '10.0.0.0/24'}, None),
    ]


def test_prefix_list_purges_extra_entries_keeping_the_slash(run):
    status, result, api = run(ddos_prefix_list, {'name': 'trusted', 'entries': ['192.0.2.7/32']}, {
        ('GET', '/ddos-mitigation/prefix-lists'): LISTS,
        ('GET', '/ddos-mitigation/prefix-lists/pl-1/entries'): [{'network': '192.0.2.7/32'}, {'network': '10.0.0.0/24'}],
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('DELETE', '/ddos-mitigation/prefix-lists/pl-1/entries/10.0.0.0/24', None, None)]


def test_global_list_is_never_deleted(run):
    status, result, api = run(ddos_prefix_list, {'name': 'scanners', 'state': 'absent'}, {
        ('GET', '/ddos-mitigation/prefix-lists'): LISTS,
    })
    assert status == 'exit' and not result['changed']
    assert api.writes() == []


def test_firewall_rule_with_other_action_is_recreated(run):
    rule = {'id': 7, 'protocol': 6, 'dst_port': 443, 'action': 0, 'tcp_syn': 0, 'tcp_ack': 0, 'tcp_synack': 0,
            'tcp_rst': 0, 'tcp_fin': 0, 'tcp_all': 0, 'udp': 0, 'icmp': 0}
    status, result, api = run(ddos_firewall_rule, {
        'network': '203.0.113.10', 'protocol': 6, 'dst_port': 443, 'rule_action': 60, 'rate_limits': {'tcp_syn': 1000},
    }, {('GET', '/ddos-mitigation/firewall-rules/203.0.113.10'): {'rules': [rule]}})
    assert status == 'exit' and result['changed']
    writes = api.writes()
    assert writes[0] == ('DELETE', '/ddos-mitigation/firewall-rules/7', None, None)
    assert writes[1][:2] == ('POST', '/ddos-mitigation/firewall-rules')
    assert writes[1][2]['action'] == 60 and writes[1][2]['tcp_syn'] == 1000 and writes[1][2]['udp'] == 0


def test_firewall_rule_subnet_absent_uses_bulk(run):
    status, result, api = run(ddos_firewall_rule, {
        'network': '203.0.113.0/28', 'protocol': 17, 'dst_port': 0, 'state': 'absent',
    }, {})
    assert status == 'exit'
    assert api.writes() == [('DELETE', '/ddos-mitigation/firewall-rules/bulk', None,
                             {'network': '203.0.113.0/28', 'protocol': 17, 'dst_port': 0})]


def test_profile_keeps_unset_settings_and_syncs_countries(run):
    profile = dict((k, 1) for k in ddos_protection_profile.SETTINGS)
    status, result, api = run(ddos_protection_profile, {
        'network': '203.0.113.10', 'settings': {'udp_validation_level': 3}, 'countries': ['es', 'pt'],
    }, {
        ('GET', '/ddos-mitigation/profiles/203.0.113.10'): profile,
        ('GET', '/ddos-mitigation/ips'): {'single_ips': [{'network': '203.0.113.10', 'has_profile': True}]},
        ('GET', '/ddos-mitigation/profiles/203.0.113.10/countries'): {'countries': [{'iso_code': 'FR'}]},
        ('GET', '/ddos-mitigation/profiles/203.0.113.10/asns'): {'asns': []},
        ('GET', '/ddos-mitigation/profiles/203.0.113.10/prefix-lists'): {'prefix_lists': []},
    })
    assert status == 'exit' and result['changed']
    writes = api.writes()
    assert writes[0][:2] == ('PUT', '/ddos-mitigation/profiles/203.0.113.10')
    assert writes[0][2]['udp_validation_level'] == 3 and writes[0][2]['tcp_validation_level'] == 1
    assert writes[1] == ('PUT', '/ddos-mitigation/profiles/203.0.113.10/countries', {'iso_codes': ['ES', 'PT']}, None)
    assert len(writes) == 2


def test_profile_rejects_unknown_settings(run):
    status, result, api = run(ddos_protection_profile, {'network': '203.0.113.10', 'settings': {'bogus': 1}}, {})
    assert status == 'fail' and 'bogus' in result['msg']


def test_attack_details(run):
    status, result, api = run(ddos_attack_info, {'attack_id': 4211}, {
        ('GET', '/ddos-attacks/attacks'): [{'attack_id': 4211}],
        ('GET', '/ddos-attacks/attacks/4211/details'): {'vectors': []},
        ('GET', '/ddos-attacks/attacks/4211/traffic-graph'): {'data': []},
    })
    assert status == 'exit' and result['details'] == {'vectors': []} and result['traffic_graph'] == {'data': []}
