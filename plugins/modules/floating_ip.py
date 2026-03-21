#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: floating_ip
short_description: Manage floating IPs on CubePath Cloud
description:
    - Acquire, release, assign, or unassign floating IPs on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        required: true
        choices: [acquired, released, assigned, unassigned]
    ip_type:
        description: IP type. Used when I(state=acquired).
        type: str
        default: IPv4
        choices: [IPv4, IPv6]
    location:
        description: Location. Required when I(state=acquired).
        type: str
    address:
        description: IP address. Required when I(state=released).
        type: str
    vps_id:
        description: VPS ID for assignment.
        type: int
    baremetal_id:
        description: Baremetal ID for assignment.
        type: int
    floating_ip_id:
        description: Floating IP ID for unassignment.
        type: int
'''

EXAMPLES = r'''
- name: Acquire floating IP
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: acquired
    ip_type: IPv4
    location: eu-bcn-1

- name: Assign to VPS
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: assigned
    vps_id: 123

- name: Release floating IP
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: released
    address: "1.2.3.4"
'''

RETURN = r'''
result:
    description: API response.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', required=True, choices=['acquired', 'released', 'assigned', 'unassigned']),
        ip_type=dict(type='str', default='IPv4', choices=['IPv4', 'IPv6']),
        location=dict(type='str'),
        address=dict(type='str'),
        vps_id=dict(type='int'),
        baremetal_id=dict(type='int'),
        floating_ip_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'acquired', ['location']),
            ('state', 'released', ['address']),
            ('state', 'unassigned', ['floating_ip_id']),
        ],
        mutually_exclusive=[('vps_id', 'baremetal_id')],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']

    if module.check_mode:
        module.exit_json(changed=True)

    if state == 'acquired':
        data = {
            'type': module.params['ip_type'],
            'location': module.params['location'],
        }
        result = api.post('/floating_ips/acquire', data)
        module.exit_json(changed=True, result=result)

    elif state == 'released':
        result = api.post('/floating_ips/release', {'address': module.params['address']})
        module.exit_json(changed=True, result=result)

    elif state == 'assigned':
        vps_id = module.params.get('vps_id')
        baremetal_id = module.params.get('baremetal_id')
        if not vps_id and not baremetal_id:
            module.fail_json(msg='Either vps_id or baremetal_id required when state=assigned')
        if vps_id:
            result = api.post('/floating_ips/assign/vps/%d' % vps_id)
        else:
            result = api.post('/floating_ips/assign/baremetal/%d' % baremetal_id)
        module.exit_json(changed=True, result=result)

    elif state == 'unassigned':
        result = api.post('/floating_ips/unassign/%d' % module.params['floating_ip_id'])
        module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
