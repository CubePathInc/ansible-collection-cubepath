#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: network
short_description: Manage private networks on CubePath Cloud
description:
    - Create or delete private networks on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the network.
        type: str
        required: true
    project_id:
        description: Project ID. Required when I(state=present).
        type: int
    location:
        description: Location. Required when I(state=present).
        type: str
    ip_range:
        description: IP range (e.g. 10.0.0.0). Required when I(state=present).
        type: str
    prefix:
        description: Network prefix (8-24). Required when I(state=present).
        type: int
    label:
        description: Network label.
        type: str
    network_id:
        description: Network ID. Used for I(state=absent).
        type: int
'''

EXAMPLES = r'''
- name: Create private network
  cubepathinc.cloud.network:
    api_token: "{{ cubepath_token }}"
    name: prod-network
    project_id: 1
    location: eu-bcn-1
    ip_range: "10.0.0.0"
    prefix: 24
    state: present
'''

RETURN = r'''
network:
    description: Network details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import find_resource_in_projects


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        project_id=dict(type='int'),
        location=dict(type='str'),
        ip_range=dict(type='str'),
        prefix=dict(type='int'),
        label=dict(type='str'),
        network_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['project_id', 'location', 'ip_range', 'prefix'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params['name']

    existing = find_resource_in_projects(api, 'networks', 'name', name)

    if state == 'present':
        if existing:
            module.exit_json(changed=False, network=existing)
        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': name,
            'project_id': module.params['project_id'],
            'location_name': module.params['location'],
            'ip_range': module.params['ip_range'],
            'prefix': module.params['prefix'],
        }
        if module.params.get('label'):
            data['label'] = module.params['label']

        result = api.post('/networks/create_network', data)
        module.exit_json(changed=True, network=result)

    elif state == 'absent':
        network_id = module.params.get('network_id')
        if existing:
            network_id = existing.get('id')
        if not network_id:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/networks/%d' % network_id)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
