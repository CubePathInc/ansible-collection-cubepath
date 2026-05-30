#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: network_route
short_description: Manage routes on a CubePath Cloud private network
description:
    - Create or delete static routes on a CubePath Cloud private network.
    - For idempotency on create, the module fetches existing routes via
      C(GET /networks/{network_id}/routes) and matches by I(destination) and
      I(next_hop_target); it will not recreate a route that already exists.
    - For I(state=absent), provide I(route_id) directly or supply I(destination)
      plus I(next_hop_target) to look it up automatically.
version_added: "1.3.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the route.
        type: str
        default: present
        choices: [present, absent]
    network_id:
        description: ID of the private network this route belongs to.
        type: int
        required: true
    destination:
        description:
            - Destination CIDR prefix (e.g. C(10.0.0.0/24)).
            - Required when I(state=present).
        type: str
    next_hop_type:
        description:
            - Type of the next hop.
            - Required when I(state=present).
        type: str
        choices: [ip, vps, baremetal]
    next_hop_target:
        description:
            - >-
              Target for the next hop. Meaning depends on I(next_hop_type) -
              an IP address string for C(ip), or a resource ID/UUID for C(vps) or C(baremetal).
            - Required when I(state=present).
        type: str
    description:
        description: Optional human-readable description for the route.
        type: str
    route_id:
        description:
            - ID of the route.
            - Required for I(state=absent) when I(destination) and I(next_hop_target)
              are not provided.
        type: str
'''

EXAMPLES = r'''
- name: Add a static route via IP next hop
  cubepathinc.cloud.network_route:
    api_token: "{{ cubepath_token }}"
    network_id: 42
    destination: 10.1.0.0/16
    next_hop_type: ip
    next_hop_target: "192.168.1.1"
    description: Route to remote office
    state: present
  register: route

- name: Add a route via a VPS next hop
  cubepathinc.cloud.network_route:
    api_token: "{{ cubepath_token }}"
    network_id: 42
    destination: 10.2.0.0/24
    next_hop_type: vps
    next_hop_target: "456"
    state: present

- name: Delete a route by ID
  cubepathinc.cloud.network_route:
    api_token: "{{ cubepath_token }}"
    network_id: 42
    route_id: "def-789"
    state: absent

- name: Delete a route by destination lookup
  cubepathinc.cloud.network_route:
    api_token: "{{ cubepath_token }}"
    network_id: 42
    destination: 10.1.0.0/16
    next_hop_target: "192.168.1.1"
    state: absent
'''

RETURN = r'''
route:
    description: Route details.
    type: dict
    returned: on success when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def find_route(api, network_id, destination, next_hop_target):
    routes = api.get('/networks/%d/routes' % network_id)
    if isinstance(routes, list):
        for r in routes:
            if r.get('destination') == destination and r.get('next_hop_target') == next_hop_target:
                return r
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        network_id=dict(type='int', required=True),
        destination=dict(type='str'),
        next_hop_type=dict(type='str', choices=['ip', 'vps', 'baremetal']),
        next_hop_target=dict(type='str'),
        description=dict(type='str'),
        route_id=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['destination', 'next_hop_type', 'next_hop_target'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    network_id = module.params['network_id']

    if state == 'present':
        destination = module.params['destination']
        next_hop_target = module.params['next_hop_target']

        existing = find_route(api, network_id, destination, next_hop_target)
        if existing:
            module.exit_json(changed=False, route=existing)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'destination': destination,
            'next_hop_type': module.params['next_hop_type'],
            'next_hop_target': next_hop_target,
        }
        if module.params.get('description') is not None:
            data['description'] = module.params['description']

        result = api.post('/networks/%d/routes' % network_id, data)
        module.exit_json(changed=True, route=result)

    elif state == 'absent':
        route_id = module.params.get('route_id')
        if not route_id:
            destination = module.params.get('destination')
            next_hop_target = module.params.get('next_hop_target')
            if destination and next_hop_target:
                existing = find_route(api, network_id, destination, next_hop_target)
                if existing:
                    route_id = existing.get('id') or existing.get('uuid')
        if not route_id:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/networks/%d/routes/%s' % (network_id, route_id))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
