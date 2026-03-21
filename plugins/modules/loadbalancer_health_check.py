#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer_health_check
short_description: Configure load balancer health checks on CubePath Cloud
description:
    - Configure or remove health checks on CubePath Cloud load balancer listeners.
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
    listener_uuid:
        description: Listener UUID.
        type: str
        required: true
    protocol:
        description: Health check protocol.
        type: str
        default: http
        choices: [http, https, tcp]
    path:
        description: Health check path.
        type: str
        default: /
    interval:
        description: Check interval in seconds (5-300).
        type: int
        default: 30
    timeout:
        description: Timeout in seconds (1-60).
        type: int
        default: 5
    healthy_threshold:
        description: Healthy threshold (1-10).
        type: int
        default: 2
    unhealthy_threshold:
        description: Unhealthy threshold (1-10).
        type: int
        default: 3
    expected_codes:
        description: Expected HTTP status codes.
        type: str
        default: "200-399"
'''

EXAMPLES = r'''
- name: Configure health check
  cubepathinc.cloud.loadbalancer_health_check:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    listener_uuid: "def-456"
    protocol: http
    path: /health
    interval: 30
    state: present

- name: Remove health check
  cubepathinc.cloud.loadbalancer_health_check:
    api_token: "{{ cubepath_token }}"
    lb_uuid: "abc-123"
    listener_uuid: "def-456"
    state: absent
'''

RETURN = r'''
health_check:
    description: Health check configuration.
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
        listener_uuid=dict(type='str', required=True),
        protocol=dict(type='str', default='http', choices=['http', 'https', 'tcp']),
        path=dict(type='str', default='/'),
        interval=dict(type='int', default=30),
        timeout=dict(type='int', default=5),
        healthy_threshold=dict(type='int', default=2),
        unhealthy_threshold=dict(type='int', default=3),
        expected_codes=dict(type='str', default='200-399'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    state = module.params['state']
    endpoint = '/loadbalancer/%s/listeners/%s/health-check' % (
        module.params['lb_uuid'], module.params['listener_uuid'])

    if state == 'present':
        if module.check_mode:
            module.exit_json(changed=True)
        data = {
            'protocol': module.params['protocol'],
            'path': module.params['path'],
            'interval_seconds': module.params['interval'],
            'timeout_seconds': module.params['timeout'],
            'healthy_threshold': module.params['healthy_threshold'],
            'unhealthy_threshold': module.params['unhealthy_threshold'],
            'expected_codes': module.params['expected_codes'],
        }
        result = api.put(endpoint, data)
        module.exit_json(changed=True, health_check=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete(endpoint)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
