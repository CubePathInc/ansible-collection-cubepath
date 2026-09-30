# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import kubernetes_addon, kubernetes_cluster, kubernetes_info, kubernetes_node_pool

READY_POOL = {'uuid': 'np-1', 'name': 'default', 'plan': {'name': 'gp.small'}, 'desired_nodes': 1, 'min_nodes': 1,
              'max_nodes': 2, 'auto_scale': False, 'labels': None, 'taints': None,
              'nodes': [{'vps_id': 9, 'k8s_status': 'ready'}]}


def test_cluster_create_body(run):
    status, result, api = run(kubernetes_cluster, {
        'name': 'prod', 'project_id': 882, 'location': 'eu-bcn-1', 'wait': False,
        'node_pools': [{'plan': 'gp.small', 'count': 1, 'auto_scale': False, 'taints': [{'key': 'k', 'effect': 'NoSchedule'}]}],
    }, {('GET', '/kubernetes/'): ([], [{'uuid': 'k-1', 'name': 'prod', 'project_id': 882}])})
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/kubernetes/', {
        'project_id': 882, 'name': 'prod', 'location_name': 'eu-bcn-1', 'ha_control_plane': False,
        'allocate_ipv4': True, 'allocate_ipv6': True,
        'node_pools': [{'name': 'default', 'plan': 'gp.small', 'count': 1, 'auto_scale': False,
                        'taints': [{'key': 'k', 'value': '', 'effect': 'NoSchedule'}]}],
    }, None)]


def test_cluster_is_moved_and_protected(run):
    status, result, api = run(kubernetes_cluster, {'name': 'prod', 'project_id': 7, 'protected': True}, {
        ('GET', '/kubernetes/'): [{'uuid': 'k-1', 'name': 'prod', 'project_id': 882, 'protected': False}],
        ('GET', '/kubernetes/k-1'): {'uuid': 'k-1', 'status': 'active', 'node_pools': [READY_POOL]},
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [
        ('POST', '/kubernetes/k-1/protection', {'enabled': True}, None),
        ('POST', '/kubernetes/k-1/move', {'project_id': 7}, None),
    ]


def test_node_pool_scale_patches_only_the_count(run):
    status, result, api = run(kubernetes_node_pool, {'cluster': 'prod', 'name': 'default', 'count': 3, 'plan': 'gp.small', 'wait': False}, {
        ('GET', '/kubernetes/'): [{'uuid': 'k-1', 'name': 'prod'}],
        ('GET', '/kubernetes/k-1/node-pools/'): [READY_POOL],
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('PATCH', '/kubernetes/k-1/node-pools/np-1', {'desired_nodes': 3}, None)]


def test_node_pool_plan_cannot_change(run):
    status, result, api = run(kubernetes_node_pool, {'cluster': 'prod', 'name': 'default', 'plan': 'gp.large'}, {
        ('GET', '/kubernetes/'): [{'uuid': 'k-1', 'name': 'prod'}],
        ('GET', '/kubernetes/k-1/node-pools/'): [READY_POOL],
    })
    assert status == 'fail'


def test_addon_uninstall_uses_the_catalog_uuid(run):
    status, result, api = run(kubernetes_addon, {'cluster': 'prod', 'slug': 'ingress-nginx', 'state': 'absent'}, {
        ('GET', '/kubernetes/'): [{'uuid': 'k-1', 'name': 'prod'}],
        ('GET', '/kubernetes/k-1/addons'): ([{'uuid': 'inst-1', 'status': 'active', 'addon': {'uuid': 'cat-1', 'slug': 'ingress-nginx'}}], []),
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('DELETE', '/kubernetes/k-1/addons/cat-1', None, None)]


def test_kubeconfig_is_read_as_text(run):
    status, result, api = run(kubernetes_info, {'cluster': 'prod', 'gather': ['kubeconfig']}, {
        ('GET', '/kubernetes/'): [{'uuid': 'k-1', 'name': 'prod'}],
        ('GET', '/kubernetes/k-1/kubeconfig'): 'apiVersion: v1\n',
    })
    assert status == 'exit' and result['kubeconfig'] == 'apiVersion: v1\n'
