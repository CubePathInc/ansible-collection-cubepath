#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer
short_description: Manage load balancers on CubePath Cloud
description:
    - Create, update, resize, or delete load balancers on CubePath Cloud.
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
    name:
        description: Load balancer name.
        type: str
        required: true
    plan:
        description: Plan name (e.g. lb.small). Required when I(state=present).
        type: str
    location:
        description: Location. Required when I(state=present).
        type: str
    project_id:
        description: Project ID.
        type: int
    label:
        description: Optional label.
        type: str
    lb_uuid:
        description: LB UUID for deletion or updates.
        type: str
'''

EXAMPLES = r'''
- name: Create load balancer
  cubepathinc.cloud.loadbalancer:
    api_token: "{{ cubepath_token }}"
    name: web-lb
    plan: lb.small
    location: eu-bcn-1
    state: present

- name: Delete load balancer
  cubepathinc.cloud.loadbalancer:
    api_token: "{{ cubepath_token }}"
    name: web-lb
    state: absent
'''

RETURN = r'''
loadbalancer:
    description: Load balancer details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def find_lb(api, name):
    lbs = api.get('/loadbalancer/')
    if isinstance(lbs, list):
        for lb in lbs:
            if lb.get('name') == name:
                return lb
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        plan=dict(type='str'),
        location=dict(type='str'),
        project_id=dict(type='int'),
        label=dict(type='str'),
        lb_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['plan', 'location'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params['name']

    existing = find_lb(api, name)

    if state == 'present':
        if existing:
            changed = False
            uuid = existing.get('uuid')
            update_data = {}
            if module.params.get('label') and existing.get('label') != module.params['label']:
                update_data['label'] = module.params['label']
                changed = True
            if update_data:
                if module.check_mode:
                    module.exit_json(changed=True)
                result = api.patch('/loadbalancer/%s' % uuid, update_data)
                module.exit_json(changed=True, loadbalancer=result)
            module.exit_json(changed=False, loadbalancer=existing)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': name,
            'plan_name': module.params['plan'],
            'location_name': module.params['location'],
        }
        if module.params.get('project_id'):
            data['project_id'] = module.params['project_id']
        if module.params.get('label'):
            data['label'] = module.params['label']

        result = api.post('/loadbalancer/', data)
        module.exit_json(changed=True, loadbalancer=result)

    elif state == 'absent':
        uuid = module.params.get('lb_uuid')
        if existing:
            uuid = existing.get('uuid')
        if not uuid:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/loadbalancer/%s' % uuid)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
