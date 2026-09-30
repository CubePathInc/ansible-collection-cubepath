#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: kubernetes_info
short_description: Get Kubernetes information from CubePath Cloud
description:
    - List managed Kubernetes clusters, versions, worker plans and the addon catalog, or read one cluster
      in detail with its node pools, addons, load balancers, kubeconfig and metrics.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    cluster:
        description:
            - Name or UUID of one cluster, returned in detail as RV(cluster).
            - Required for C(node_pools), C(addons), C(loadbalancers), C(kubeconfig), C(metrics) and C(node_metrics).
        type: str
    gather:
        description:
            - Extra information to return.
            - C(catalog) is the addon catalog, C(addons) the addons installed on I(cluster).
            - C(kubeconfig) returns the admin kubeconfig of I(cluster) as a YAML string.
            - C(node_metrics) needs I(node_name).
        type: list
        elements: str
        default: []
        choices: [versions, plans, catalog, node_pools, addons, loadbalancers, kubeconfig, metrics, node_metrics]
    version:
        description: Kubernetes version the C(plans) must meet the minimums of. Defaults to the platform default.
        type: str
    category:
        description: Only C(catalog) addons of this category.
        type: str
        choices: [ingress, monitoring, cicd, storage, security, networking]
    node_name:
        description: Kubernetes node name of the worker for C(node_metrics).
        type: str
    time_range:
        description: Time range of the metrics.
        type: str
        default: 1h
        choices: [1h, 3h, 6h, 12h, 24h, 3d, 7d, 30d]
'''

EXAMPLES = r'''
- name: Versions and worker plans
  cubepathinc.cloud.kubernetes_info:
    api_token: "{{ cubepath_token }}"
    gather: [versions, plans]
  register: k8s

- name: Write the kubeconfig of a cluster
  cubepathinc.cloud.kubernetes_info:
    api_token: "{{ cubepath_token }}"
    cluster: prod
    gather: [kubeconfig]
  register: prod
  no_log: true

- name: Save it
  ansible.builtin.copy:
    content: "{{ prod.kubeconfig }}"
    dest: ~/.kube/prod.yaml
    mode: "0600"
'''

RETURN = r'''
clusters:
    description: Clusters of the organization.
    type: list
    elements: dict
    returned: always
cluster:
    description: Detail of the cluster given in I(cluster), with node pools, workers and the latest health.
    type: dict
    returned: when I(cluster) is set
versions:
    description: Available Kubernetes versions and their minimum worker size.
    type: list
    elements: dict
    returned: when C(versions) is in I(gather)
plans:
    description: Worker plans that meet the version minimums.
    type: list
    elements: dict
    returned: when C(plans) is in I(gather)
catalog:
    description: Addons that can be installed.
    type: list
    elements: dict
    returned: when C(catalog) is in I(gather)
node_pools:
    description: Node pools of the cluster with their workers.
    type: list
    elements: dict
    returned: when C(node_pools) is in I(gather)
addons:
    description: Addons installed on the cluster.
    type: list
    elements: dict
    returned: when C(addons) is in I(gather)
loadbalancers:
    description: Load balancers that target the cluster's node pools.
    type: list
    elements: dict
    returned: when C(loadbalancers) is in I(gather)
kubeconfig:
    description: Admin kubeconfig of the cluster (YAML).
    type: str
    returned: when C(kubeconfig) is in I(gather)
metrics:
    description: Cluster health series (ready nodes, pods, API latency) as C([timestamp, value]) pairs.
    type: dict
    returned: when C(metrics) is in I(gather)
node_metrics:
    description: Kubelet and VPS series of the worker given in I(node_name).
    type: dict
    returned: when C(node_metrics) is in I(gather)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec, path_quote
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_kubernetes import list_clusters

PER_CLUSTER = ('node_pools', 'addons', 'loadbalancers', 'kubeconfig', 'metrics', 'node_metrics')


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        cluster=dict(type='str'),
        gather=dict(type='list', elements='str', default=[],
                    choices=['versions', 'plans', 'catalog'] + list(PER_CLUSTER)),
        version=dict(type='str'),
        category=dict(type='str', choices=['ingress', 'monitoring', 'cicd', 'storage', 'security', 'networking']),
        node_name=dict(type='str'),
        time_range=dict(type='str', default='1h', choices=['1h', '3h', '6h', '12h', '24h', '3d', '7d', '30d']),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    gather = module.params['gather']
    clusters = list_clusters(api)
    result = {'changed': False, 'clusters': clusters}

    if 'versions' in gather:
        result['versions'] = as_list(api.get('/kubernetes/versions'))
    if 'plans' in gather:
        result['plans'] = as_list(api.get('/kubernetes/plans', params={'version': module.params.get('version')}))
    if 'catalog' in gather:
        result['catalog'] = as_list(api.get('/kubernetes/addons', params={'category': module.params.get('category')}))

    ref = module.params.get('cluster')
    wanted = [g for g in gather if g in PER_CLUSTER]
    if wanted and not ref:
        module.fail_json(msg='cluster is required to gather %s' % ', '.join(wanted))
    if 'node_metrics' in gather and not module.params.get('node_name'):
        module.fail_json(msg='node_name is required to gather node_metrics')
    if ref:
        match = next((c for c in clusters if ref in (c.get('uuid'), c.get('name'))), None)
        if match is None:
            module.fail_json(msg='Kubernetes cluster %s not found' % ref)
        base = '/kubernetes/%s' % match['uuid']
        metrics_params = {'time_range': module.params['time_range']}
        result['cluster'] = api.get(base)
        if 'node_pools' in gather:
            result['node_pools'] = as_list(api.get('%s/node-pools/' % base))
        if 'addons' in gather:
            result['addons'] = as_list(api.get('%s/addons' % base))
        if 'loadbalancers' in gather:
            result['loadbalancers'] = as_list(api.get('%s/loadbalancers' % base), 'loadbalancers')
        if 'kubeconfig' in gather:
            result['kubeconfig'] = api.get_raw('%s/kubeconfig' % base)
        if 'metrics' in gather:
            result['metrics'] = api.get('%s/metrics' % base, params=metrics_params)
        if 'node_metrics' in gather:
            result['node_metrics'] = api.get('%s/nodes/%s/metrics' % (base, path_quote(module.params['node_name'])), params=metrics_params)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
