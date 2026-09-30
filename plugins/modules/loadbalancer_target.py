#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer_target
short_description: Manage load balancer targets on CubePath Cloud
description:
    - Add, update, remove, or drain targets on CubePath Cloud load balancers.
    - With I(targets), add several targets in one call (up to 50). Targets already on the listener are
      skipped.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent, draining]
    lb_uuid:
        description: Load balancer UUID.
        type: str
        required: true
    listener_uuid:
        description: Listener UUID.
        type: str
        required: true
    target_type:
        description: Target type. Required when I(state=present) and creating.
        type: str
        choices: [vps, baremetal, availability_group]
    target_uuid:
        description: Target resource UUID. Required for I(state=absent) or I(state=draining).
        type: str
    port:
        description: Override target port.
        type: int
    weight:
        description: Target weight (1-100).
        type: int
        default: 100
    enabled:
        description: Enable or disable target.
        type: bool
    targets:
        description:
            - Targets to add in one call with I(state=present). Mutually exclusive with I(target_uuid).
        type: list
        elements: dict
        version_added: "1.5.0"
        suboptions:
            target_type:
                description: Target type.
                type: str
                required: true
                choices: [vps, baremetal, availability_group]
            target_uuid:
                description: Target resource ID or UUID.
                type: str
                required: true
            port:
                description: Override target port.
                type: int
            weight:
                description: Target weight (1-100).
                type: int
                default: 100
'''

EXAMPLES = r'''
- name: Add VPS target
  cubepathinc.cloud.loadbalancer_target:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    listener_uuid: "def-456"
    target_type: vps
    target_uuid: "ghi-789"
    weight: 100
    state: present

- name: Drain target
  cubepathinc.cloud.loadbalancer_target:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    listener_uuid: "def-456"
    target_uuid: "ghi-789"
    state: draining

- name: Add three VPS at once
  cubepathinc.cloud.loadbalancer_target:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    listener_uuid: "def-456"
    targets:
      - target_type: vps
        target_uuid: "101"
      - target_type: vps
        target_uuid: "102"
      - target_type: vps
        target_uuid: "103"
'''

RETURN = r'''
target:
    description: Target details.
    type: dict
    returned: on success
targets:
    description: Targets added by I(targets).
    type: list
    elements: dict
    returned: when I(targets) is set
    version_added: "1.5.0"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def add_batch(module, api, lb_uuid, listener_uuid, base):
    """Add the targets that are not on the listener yet, in one request."""
    current = set()
    for lb in api.get('/loadbalancer/') or []:
        if lb.get('uuid') != lb_uuid:
            continue
        for listener in lb.get('listeners') or []:
            if listener.get('uuid') == listener_uuid:
                current = set((t.get('target_type'), str(t.get('target_uuid'))) for t in listener.get('targets') or [])
    new = []
    for t in module.params['targets']:
        if (t['target_type'], str(t['target_uuid'])) in current:
            continue
        new.append(dict((k, v) for k, v in t.items() if v is not None))
    if not new:
        module.exit_json(changed=False, targets=[])
    if module.check_mode:
        module.exit_json(changed=True, targets=new)
    result = api.post('%s/batch' % base, {'targets': new})
    module.exit_json(changed=True, targets=result.get('targets', []))


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent', 'draining']),
        lb_uuid=dict(type='str', required=True),
        listener_uuid=dict(type='str', required=True),
        target_type=dict(type='str', choices=['vps', 'baremetal', 'availability_group']),
        target_uuid=dict(type='str'),
        port=dict(type='int'),
        weight=dict(type='int', default=100),
        enabled=dict(type='bool'),
        targets=dict(type='list', elements='dict', options=dict(
            target_type=dict(type='str', required=True, choices=['vps', 'baremetal', 'availability_group']),
            target_uuid=dict(type='str', required=True),
            port=dict(type='int'),
            weight=dict(type='int', default=100),
        )),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'absent', ['target_uuid']),
            ('state', 'draining', ['target_uuid']),
        ],
        mutually_exclusive=[('targets', 'target_uuid')],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    lb_uuid = module.params['lb_uuid']
    listener_uuid = module.params['listener_uuid']
    target_uuid = module.params.get('target_uuid')
    base = '/loadbalancer/%s/listeners/%s/targets' % (lb_uuid, listener_uuid)

    if state == 'present' and module.params.get('targets') is not None:
        add_batch(module, api, lb_uuid, listener_uuid, base)

    if state == 'present':
        if target_uuid and module.params.get('target_type') is None:
            data = {}
            if module.params.get('port') is not None:
                data['port'] = module.params['port']
            if module.params.get('weight') is not None:
                data['weight'] = module.params['weight']
            if module.params.get('enabled') is not None:
                data['enabled'] = module.params['enabled']
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.patch('%s/%s' % (base, target_uuid), data)
            module.exit_json(changed=True, target=result)

        if not module.params.get('target_type') or not target_uuid:
            module.fail_json(msg='target_type and target_uuid required when adding a target')

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'target_type': module.params['target_type'],
            'target_uuid': target_uuid,
            'weight': module.params['weight'],
        }
        if module.params.get('port') is not None:
            data['port'] = module.params['port']

        result = api.post(base, data)
        module.exit_json(changed=True, target=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s/%s' % (base, target_uuid))
        module.exit_json(changed=True)

    elif state == 'draining':
        if module.check_mode:
            module.exit_json(changed=True)
        result = api.post('%s/%s/drain' % (base, target_uuid))
        module.exit_json(changed=True, target=result)


if __name__ == '__main__':
    main()
