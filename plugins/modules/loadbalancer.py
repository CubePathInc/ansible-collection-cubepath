#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: loadbalancer
short_description: Manage load balancers on CubePath Cloud
description:
    - Create, update, resize, or delete load balancers on CubePath Cloud.
    - The module finds an existing load balancer by I(name). On an existing one it updates I(label) and
      I(protected), resizes it to I(resize_plan), and moves it to I(project_id) when it is in another project.
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
        description:
            - Project ID.
            - An existing load balancer in another project is moved to this one.
        type: int
    label:
        description: Optional label.
        type: str
    lb_uuid:
        description: LB UUID for deletion or updates.
        type: str
    network_id:
        description: Private network ID to attach the load balancer to.
        type: int
    resize_plan:
        description:
            - When set on an existing load balancer on another plan, resize it to this plan.
            - Has no effect when creating a new load balancer.
        type: str
        version_added: "1.5.0"
    protected:
        description:
            - Deletion protection. A protected load balancer cannot be deleted.
            - With I(state=absent), C(false) disables protection before deleting.
        type: bool
        version_added: "1.5.0"
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


def update_existing(module, api, existing):
    """Apply label, protection, plan and project changes to an existing load balancer."""
    p = module.params
    uuid = existing.get('uuid')
    calls = []
    if p.get('label') and existing.get('label') != p['label']:
        calls.append(('patch', '/loadbalancer/%s' % uuid, {'label': p['label']}))
    if p.get('protected') is not None and p['protected'] != bool(existing.get('protected')):
        calls.append(('post', '/loadbalancer/%s/protection' % uuid, {'enabled': p['protected']}))
    # Only resize to a different plan: the API rejects a resize to the current one.
    if p.get('resize_plan') and p['resize_plan'] != existing.get('plan_name'):
        calls.append(('post', '/loadbalancer/%s/resize' % uuid, {'plan_name': p['resize_plan']}))
    if p.get('project_id') and p['project_id'] != existing.get('project_id'):
        calls.append(('post', '/loadbalancer/%s/move-project' % uuid, {'project_id': p['project_id']}))
    if not calls:
        return dict(changed=False, loadbalancer=existing)
    if module.check_mode:
        return dict(changed=True, loadbalancer=existing)
    for method, path, data in calls:
        getattr(api, method)(path, data)
    return dict(changed=True, loadbalancer=find_lb(api, p['name']))


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
        network_id=dict(type='int'),
        resize_plan=dict(type='str'),
        protected=dict(type='bool'),
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
            module.exit_json(**update_existing(module, api, existing))
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
        if module.params.get('network_id') is not None:
            data['network_id'] = module.params['network_id']

        result = api.post('/loadbalancer/', data)
        if module.params.get('protected'):
            api.post('/loadbalancer/%s/protection' % result['uuid'], {'enabled': True})
        module.exit_json(changed=True, loadbalancer=result)

    elif state == 'absent':
        uuid = module.params.get('lb_uuid')
        if existing:
            uuid = existing.get('uuid')
        if not uuid:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if existing and module.params.get('protected') is False and existing.get('protected'):
            api.post('/loadbalancer/%s/protection' % uuid, {'enabled': False})
        api.delete('/loadbalancer/%s' % uuid)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
