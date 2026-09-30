#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: kubernetes_cluster
short_description: Manage Kubernetes clusters on CubePath Cloud
description:
    - Create, update, move or delete managed Kubernetes clusters on CubePath Cloud.
    - The module finds an existing cluster by I(name). On an existing cluster it updates I(label) and
      I(protected), and moves it to I(project_id) when it is in another project. The other creation settings
      cannot be changed; node pools are managed with M(cubepathinc.cloud.kubernetes_node_pool).
    - Provisioning is asynchronous. By default the module waits until the cluster is C(active) and every
      worker is ready, or gone when I(state=absent).
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the cluster.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the cluster, 3 to 100 lowercase letters, numbers and hyphens.
        type: str
        required: true
    project_id:
        description:
            - Project of the cluster. Required to create it.
            - When an existing cluster is in another project, it is moved to this one with its load
              balancers and network.
        type: int
    location:
        description: Location, for example C(eu-bcn-1). Required to create the cluster.
        type: str
    version:
        description: Kubernetes version. Defaults to the platform default version.
        type: str
    ha_control_plane:
        description: Highly available control plane.
        type: bool
        default: false
    allocate_ipv4:
        description: Give every worker a public IPv4 address.
        type: bool
        default: true
    allocate_ipv6:
        description: Give every worker a public IPv6 address.
        type: bool
        default: true
    network_id:
        description: Existing private network for the workers. Mutually exclusive with I(node_cidr).
        type: int
    node_cidr:
        description: CIDR of a new private network created for the workers. Mutually exclusive with I(network_id).
        type: str
    pod_cidr:
        description: Pod CIDR. Defaults to C(10.42.0.0/16).
        type: str
    service_cidr:
        description: Service CIDR. Defaults to C(10.43.0.0/16).
        type: str
    node_pools:
        description: Node pools created with the cluster (1 to 10). Required to create the cluster.
        type: list
        elements: dict
        suboptions:
            name:
                description: Pool name.
                type: str
                default: default
            plan:
                description: VPS plan of the workers, for example C(gp.small).
                type: str
                required: true
            count:
                description: Number of workers (1 to 100).
                type: int
                default: 1
            auto_scale:
                description: Let the cluster autoscaler change the number of workers.
                type: bool
                default: true
            labels:
                description: Kubernetes labels of the workers.
                type: dict
            taints:
                description: Kubernetes taints of the workers.
                type: list
                elements: dict
                suboptions:
                    key:
                        description: Taint key.
                        type: str
                        required: true
                    value:
                        description: Taint value.
                        type: str
                        default: ''
                    effect:
                        description: Taint effect.
                        type: str
                        required: true
                        choices: [NoSchedule, PreferNoSchedule, NoExecute]
    label:
        description: Free-form label.
        type: str
    protected:
        description:
            - Deletion protection. A protected cluster cannot be deleted.
            - With I(state=absent), C(false) disables protection before deleting.
        type: bool
    wait:
        description: Wait until the cluster is C(active) with every worker ready, or deleted when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 1800
'''

EXAMPLES = r'''
- name: Create a cluster with 3 workers
  cubepathinc.cloud.kubernetes_cluster:
    api_token: "{{ cubepath_token }}"
    name: prod
    project_id: 12
    location: eu-bcn-1
    node_pools:
      - name: default
        plan: gp.small
        count: 3
        auto_scale: false
  register: cluster

- name: Delete it
  cubepathinc.cloud.kubernetes_cluster:
    api_token: "{{ cubepath_token }}"
    name: prod
    state: absent
'''

RETURN = r'''
cluster:
    description: Cluster details (status, version, API endpoint, network, node pools with their workers...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import wait_for
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_kubernetes import TAINT_SPEC, find_cluster, pool_body, pool_ready


def cluster_ready(cluster):
    return (cluster is not None and cluster.get('status') in ('active', 'error')
            and (cluster.get('status') == 'error' or all(pool_ready(p) for p in cluster.get('node_pools') or [])))


def create_body(module):
    p = module.params
    missing = [k for k in ('project_id', 'location', 'node_pools') if not p.get(k)]
    if missing:
        module.fail_json(msg='%s required to create the cluster' % ', '.join(missing))
    body = {
        'project_id': p['project_id'],
        'name': p['name'],
        'location_name': p['location'],
        'ha_control_plane': p['ha_control_plane'],
        'allocate_ipv4': p['allocate_ipv4'],
        'allocate_ipv6': p['allocate_ipv6'],
        'node_pools': [pool_body(pool) for pool in p['node_pools']],
    }
    if p.get('version'):
        body['version'] = p['version']
    network = dict((k, p[k]) for k in ('network_id', 'node_cidr', 'pod_cidr', 'service_cidr') if p.get(k) is not None)
    if network:
        body['network'] = network
    return body


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        project_id=dict(type='int'),
        location=dict(type='str'),
        version=dict(type='str'),
        ha_control_plane=dict(type='bool', default=False),
        allocate_ipv4=dict(type='bool', default=True),
        allocate_ipv6=dict(type='bool', default=True),
        network_id=dict(type='int'),
        node_cidr=dict(type='str'),
        pod_cidr=dict(type='str'),
        service_cidr=dict(type='str'),
        node_pools=dict(type='list', elements='dict', options=dict(
            name=dict(type='str', default='default'),
            plan=dict(type='str', required=True),
            count=dict(type='int', default=1),
            auto_scale=dict(type='bool', default=True),
            labels=dict(type='dict'),
            taints=dict(type='list', elements='dict', options=TAINT_SPEC),
        )),
        label=dict(type='str'),
        protected=dict(type='bool'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=1800),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[('network_id', 'node_cidr')],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    p = module.params
    timeout = p['wait_timeout']

    def fetch():
        cluster = find_cluster(api, p['name'])
        return api.get('/kubernetes/%s' % cluster['uuid']) if cluster else None

    existing = find_cluster(api, p['name'])

    if p['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if p.get('protected') is False and existing.get('protected'):
            api.post('/kubernetes/%s/protection' % existing['uuid'], {'enabled': False})
        if existing.get('status') != 'deleting':
            api.delete('/kubernetes/%s' % existing['uuid'])
        if p['wait']:
            wait_for(module, fetch, lambda c: c is None, timeout, interval=15)
        module.exit_json(changed=True)

    changed = False
    if existing is None:
        body = create_body(module)
        if module.check_mode:
            module.exit_json(changed=True)
        api.post('/kubernetes/', body)
        changed = True
        existing = find_cluster(api, p['name'])

    uuid = existing['uuid']
    if p.get('label') is not None and p['label'] != existing.get('label'):
        if module.check_mode:
            module.exit_json(changed=True, cluster=existing)
        api.patch('/kubernetes/%s' % uuid, {'label': p['label']})
        changed = True
    if p.get('protected') is not None and p['protected'] != bool(existing.get('protected')):
        if module.check_mode:
            module.exit_json(changed=True, cluster=existing)
        api.post('/kubernetes/%s/protection' % uuid, {'enabled': p['protected']})
        changed = True
    if p.get('project_id') is not None and p['project_id'] != existing.get('project_id'):
        if module.check_mode:
            module.exit_json(changed=True, cluster=existing)
        api.post('/kubernetes/%s/move' % uuid, {'project_id': p['project_id']})
        changed = True

    cluster = fetch()
    if p['wait'] and not cluster_ready(cluster):
        cluster = wait_for(module, fetch, cluster_ready, timeout, interval=15)
    if cluster and cluster.get('status') == 'error':
        module.fail_json(msg='The Kubernetes cluster ended in error', cluster=cluster)
    module.exit_json(changed=changed, cluster=cluster)


if __name__ == '__main__':
    main()
