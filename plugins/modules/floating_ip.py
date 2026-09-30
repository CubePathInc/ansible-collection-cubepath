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
        description: Location name (for example C(eu-bcn-1)). Required when I(state=acquired).
        type: str
    address:
        description:
            - Floating IP address.
            - Required when I(state=released), I(state=assigned) or I(state=unassigned).
        type: str
    vps_id:
        description: VPS ID to assign the address to. Used when I(state=assigned).
        type: int
    baremetal_id:
        description: Baremetal ID to assign the address to. Used when I(state=assigned).
        type: int
notes:
    - I(state=acquired) and I(state=released) are limited by the API to 3 per organization every 24 hours.
    - The address returned by I(state=acquired) is in C(result.ip_address).
'''

EXAMPLES = r'''
- name: Acquire floating IP
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: acquired
    ip_type: IPv4
    location: eu-bcn-1
  register: fip

- name: Assign it to a VPS
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: assigned
    address: "{{ fip.result.ip_address }}"
    vps_id: 123

- name: Unassign it
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: unassigned
    address: "{{ fip.result.ip_address }}"

- name: Release floating IP
  cubepathinc.cloud.floating_ip:
    api_token: "{{ cubepath_token }}"
    state: released
    address: "{{ fip.result.ip_address }}"
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
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'acquired', ['location']),
            ('state', 'released', ['address']),
            ('state', 'assigned', ['address']),
            ('state', 'assigned', ['vps_id', 'baremetal_id'], True),
            ('state', 'unassigned', ['address']),
        ],
        mutually_exclusive=[('vps_id', 'baremetal_id')],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    address = module.params['address']

    if module.check_mode:
        module.exit_json(changed=True)

    if state == 'acquired':
        params = {'ip_type': module.params['ip_type'], 'location_name': module.params['location']}
        result = api.post('/floating_ips/acquire', params=params)
        module.exit_json(changed=True, result=result)

    elif state == 'released':
        result = api.post('/floating_ips/release/%s' % address)
        module.exit_json(changed=True, result=result)

    elif state == 'assigned':
        if module.params.get('vps_id'):
            endpoint = '/floating_ips/assign/vps/%d' % module.params['vps_id']
        else:
            endpoint = '/floating_ips/assign/baremetal/%d' % module.params['baremetal_id']
        result = api.post(endpoint, params={'address': address})
        module.exit_json(changed=True, result=result)

    elif state == 'unassigned':
        result = api.post('/floating_ips/unassign/%s' % address)
        module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
