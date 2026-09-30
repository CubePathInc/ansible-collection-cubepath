# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list

# Settings shared by the node pool options of kubernetes_cluster and kubernetes_node_pool.
TAINT_SPEC = dict(
    key=dict(type='str', required=True, no_log=False),
    value=dict(type='str', default=''),
    effect=dict(type='str', required=True, choices=['NoSchedule', 'PreferNoSchedule', 'NoExecute']),
)


def list_clusters(api):
    return as_list(api.get('/kubernetes/'))


def find_cluster(api, ref):
    for cluster in list_clusters(api):
        if ref in (cluster.get('uuid'), cluster.get('name')):
            return cluster
    return None


def require_cluster(module, api, ref):
    cluster = find_cluster(api, ref)
    if cluster is None:
        module.fail_json(msg='Kubernetes cluster %s not found' % ref)
    return cluster


def pool_body(pool):
    """Request body of a node pool from the module options (unset values are left to the API defaults)."""
    body = dict((k, pool[k]) for k in ('name', 'plan', 'count', 'auto_scale', 'labels') if pool.get(k) is not None)
    if pool.get('taints') is not None:
        body['taints'] = [dict(t) for t in pool['taints']]
    return body


def pool_ready(pool):
    nodes = pool.get('nodes') or []
    return len(nodes) == pool.get('desired_nodes') and all(n.get('k8s_status') == 'ready' for n in nodes)
