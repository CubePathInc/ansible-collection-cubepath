# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import firewall_group, vps_firewall_groups

GROUP = {'id': 5, 'project_id': 882, 'name': 'web', 'enabled': True,
         'rules': [{'direction': 'in', 'protocol': 'tcp', 'port': '443', 'source': None, 'comment': None}]}


def test_group_is_created_with_the_project_as_query(run):
    status, result, api = run(firewall_group, {
        'name': 'web', 'project_id': 882, 'rules': [{'direction': 'in', 'protocol': 'tcp', 'port': '443'}],
    }, {('GET', '/firewall/groups'): []})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/firewall/groups', {
        'name': 'web', 'rules': [{'direction': 'in', 'protocol': 'tcp', 'port': '443'}],
    }, {'project_id': 882})]


def test_same_rules_are_unchanged(run):
    status, result, api = run(firewall_group, {
        'name': 'web', 'project_id': 882, 'rules': [{'direction': 'in', 'protocol': 'tcp', 'port': '443'}],
    }, {('GET', '/firewall/groups'): [GROUP]})
    assert status == 'exit' and not result['changed']


def test_vps_groups_by_name(run):
    status, result, api = run(vps_firewall_groups, {'vps_id': 42, 'firewall_groups': ['web']}, {
        ('GET', '/vps/'): [{'id': 42, 'project': {'id': 882}, 'firewall_groups': []}],
        ('GET', '/firewall/groups'): [GROUP],
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PUT', '/firewall/vps/42/groups', {'firewall_group_ids': [5]}, None)]
