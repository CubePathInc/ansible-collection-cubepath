#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer_listener
short_description: Manage load balancer listeners on CubePath Cloud
description:
    - Create, update, or delete listeners on CubePath Cloud load balancers.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent]
    lb_uuid:
        description: Load balancer UUID.
        type: str
        required: true
    name:
        description: Listener name. Required when I(state=present).
        type: str
    protocol:
        description: Protocol.
        type: str
        default: http
        choices: [http, https, tcp, tls]
    source_port:
        description: Port to listen on. Required when I(state=present).
        type: int
    target_port:
        description: Port to forward to. Required when I(state=present).
        type: int
    algorithm:
        description: Load balancing algorithm.
        type: str
        default: round_robin
        choices: [round_robin, least_conn, source]
    sticky_sessions:
        description: Enable sticky sessions.
        type: bool
        default: false
    enabled:
        description: Enable or disable.
        type: bool
    listener_uuid:
        description: Listener UUID. Required for I(state=absent) or updates.
        type: str
'''

EXAMPLES = r'''
- name: Create listener
  cubepathinc.cloud.loadbalancer_listener:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    name: http-listener
    protocol: http
    source_port: 80
    target_port: 8080
    state: present

- name: Delete listener
  cubepathinc.cloud.loadbalancer_listener:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    listener_uuid: "def-456"
    state: absent
'''

RETURN = r'''
listener:
    description: Listener details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        lb_uuid=dict(type='str', required=True),
        name=dict(type='str'),
        protocol=dict(type='str', default='http', choices=['http', 'https', 'tcp', 'tls']),
        source_port=dict(type='int'),
        target_port=dict(type='int'),
        algorithm=dict(type='str', default='round_robin', choices=['round_robin', 'least_conn', 'source']),
        sticky_sessions=dict(type='bool', default=False),
        enabled=dict(type='bool'),
        listener_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'present', ['name', 'source_port', 'target_port']),
            ('state', 'absent', ['listener_uuid']),
        ],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    lb_uuid = module.params['lb_uuid']
    listener_uuid = module.params.get('listener_uuid')

    if state == 'present':
        if listener_uuid:
            data = {}
            for field in ('name', 'target_port', 'algorithm', 'enabled'):
                if module.params.get(field) is not None:
                    data[field] = module.params[field]
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.patch('/loadbalancer/%s/listeners/%s' % (lb_uuid, listener_uuid), data)
            module.exit_json(changed=True, listener=result)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': module.params['name'],
            'protocol': module.params['protocol'],
            'source_port': module.params['source_port'],
            'target_port': module.params['target_port'],
            'algorithm': module.params['algorithm'],
            'sticky_sessions': module.params['sticky_sessions'],
        }
        result = api.post('/loadbalancer/%s/listeners' % lb_uuid, data)
        module.exit_json(changed=True, listener=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/loadbalancer/%s/listeners/%s' % (lb_uuid, listener_uuid))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
