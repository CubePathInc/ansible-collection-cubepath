#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer_target
short_description: Manage load balancer targets on CubePath Cloud
description:
    - Add, update, remove, or drain targets on CubePath Cloud load balancers.
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
'''

RETURN = r'''
target:
    description: Target details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


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
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'absent', ['target_uuid']),
            ('state', 'draining', ['target_uuid']),
        ],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    lb_uuid = module.params['lb_uuid']
    listener_uuid = module.params['listener_uuid']
    target_uuid = module.params.get('target_uuid')
    base = '/loadbalancer/%s/listeners/%s/targets' % (lb_uuid, listener_uuid)

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
