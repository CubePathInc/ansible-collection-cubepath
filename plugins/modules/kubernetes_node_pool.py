#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: kubernetes_node_pool
short_description: Manage node pools of CubePath Kubernetes clusters
description:
    - Create, scale, update or delete a node pool of a managed Kubernetes cluster, or remove specific workers.
    - The module finds an existing pool of the cluster by I(name). On an existing pool it updates the
      number of workers, the autoscaling bounds, the labels and the taints that differ. The plan of a pool
      cannot be changed.
    - By default the module waits until every worker of the pool is ready, or the pool is gone when
      I(state=absent).
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the node pool.
        type: str
        default: present
        choices: [present, absent]
    cluster:
        description: Name or UUID of the cluster.
        type: str
        required: true
    name:
        description: Name of the pool, lowercase letters, numbers and hyphens.
        type: str
        required: true
    plan:
        description: VPS plan of the workers, for example C(gp.small). Required to create the pool.
        type: str
    count:
        description: Desired number of workers (1 to 100).
        type: int
    min_nodes:
        description: Lower bound for the autoscaler.
        type: int
    max_nodes:
        description: Upper bound for the autoscaler.
        type: int
    auto_scale:
        description: Let the cluster autoscaler change the number of workers.
        type: bool
    labels:
        description: Kubernetes labels of the workers. Replaces the current labels.
        type: dict
    taints:
        description: Kubernetes taints of the workers. Replaces the current taints.
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
    remove_nodes:
        description:
            - VPS IDs of workers of this pool to destroy. The pool shrinks by one for each removed worker.
            - Workers that are not in the pool are ignored.
        type: list
        elements: int
    wait:
        description: Wait until every worker of the pool is ready, or the pool is deleted when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 1800
'''

EXAMPLES = r'''
- name: Add a pool for batch jobs
  cubepathinc.cloud.kubernetes_node_pool:
    api_token: "{{ cubepath_token }}"
    cluster: prod
    name: batch
    plan: gp.medium
    count: 2
    auto_scale: false
    labels:
      workload: batch
    taints:
      - key: dedicated
        value: batch
        effect: NoSchedule

- name: Scale it to 4 workers
  cubepathinc.cloud.kubernetes_node_pool:
    api_token: "{{ cubepath_token }}"
    cluster: prod
    name: batch
    count: 4
'''

RETURN = r'''
node_pool:
    description: Pool details with its workers (C(nodes)).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, wait_for
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_kubernetes import TAINT_SPEC, pool_body, pool_ready, require_cluster


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        cluster=dict(type='str', required=True),
        name=dict(type='str', required=True),
        plan=dict(type='str'),
        count=dict(type='int'),
        min_nodes=dict(type='int'),
        max_nodes=dict(type='int'),
        auto_scale=dict(type='bool'),
        labels=dict(type='dict'),
        taints=dict(type='list', elements='dict', options=TAINT_SPEC),
        remove_nodes=dict(type='list', elements='int'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=1800),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params
    cluster = require_cluster(module, api, p['cluster'])
    base = '/kubernetes/%s/node-pools/' % cluster['uuid']

    def fetch():
        return next((pool for pool in as_list(api.get(base)) if pool.get('name') == p['name']), None)

    def wait(done):
        return wait_for(module, fetch, done, p['wait_timeout'], interval=15)

    pool = fetch()

    if p['state'] == 'absent':
        if pool is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s%s' % (base, pool['uuid']))
        if p['wait']:
            wait(lambda x: x is None)
        module.exit_json(changed=True)

    changed = False
    if pool is None:
        if not p.get('plan'):
            module.fail_json(msg='plan is required to create a node pool')
        if module.check_mode:
            module.exit_json(changed=True)
        api.post(base, pool_body(dict(p, count=p.get('count') or 1)))
        changed = True
        pool = fetch()
    elif p.get('plan') and p['plan'] != (pool.get('plan') or {}).get('name'):
        module.fail_json(msg='The plan of node pool %s is %s and cannot be changed' % (p['name'], (pool.get('plan') or {}).get('name')))

    update = {}
    for opt, field in (('count', 'desired_nodes'), ('min_nodes', 'min_nodes'), ('max_nodes', 'max_nodes'), ('auto_scale', 'auto_scale')):
        if p.get(opt) is not None and p[opt] != pool.get(field):
            update[field] = p[opt]
    if p.get('labels') is not None and p['labels'] != (pool.get('labels') or {}):
        update['labels'] = p['labels']
    if p.get('taints') is not None:
        taints = [dict(t) for t in p['taints']]
        if taints != (pool.get('taints') or []):
            update['taints'] = taints
    if update:
        if module.check_mode:
            module.exit_json(changed=True, node_pool=pool)
        api.patch('%s%s' % (base, pool['uuid']), update)
        changed = True

    present_ids = [n.get('vps_id') for n in pool.get('nodes') or []]
    for vps_id in p.get('remove_nodes') or []:
        if vps_id not in present_ids:
            continue
        if module.check_mode:
            module.exit_json(changed=True, node_pool=pool)
        api.delete('%s%s/nodes/%d' % (base, pool['uuid'], vps_id))
        changed = True

    pool = fetch()
    if p['wait'] and not pool_ready(pool):
        pool = wait(lambda x: x is not None and pool_ready(x))
    module.exit_json(changed=changed, node_pool=pool)


if __name__ == '__main__':
    main()
