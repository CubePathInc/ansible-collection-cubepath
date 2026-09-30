#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: nat_gateway
short_description: Manage NAT gateways on CubePath Cloud
description:
    - Create, update, resize, move or delete NAT gateways on CubePath Cloud.
    - For idempotency on create, the module lists existing gateways and matches by
      I(name) within the organisation; it will not recreate a gateway that already
      exists.
    - On an existing gateway the module updates I(label) and I(protected), and moves it to I(project_id) when
      it is in another project.
version_added: "1.3.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the NAT gateway.
        type: str
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the NAT gateway.
            - Required when I(state=present).
        type: str
    label:
        description: Optional display label.
        type: str
    plan_name:
        description:
            - Plan name for the NAT gateway (e.g. C(nat.small)).
            - Required when I(state=present).
        type: str
    network_id:
        description:
            - Private network ID the gateway is attached to.
            - Required when I(state=present).
        type: int
    project_id:
        description:
            - Project ID to associate the gateway with.
            - An existing gateway in another project is moved to this one.
        type: int
    nat_gateway_uuid:
        description:
            - UUID of an existing NAT gateway.
            - Used to target a specific gateway for I(state=absent) or I(resize_plan).
        type: str
    resize_plan:
        description:
            - When set on an existing gateway, resize it to this plan by calling
              C(POST /nat-gateway/{uuid}/resize).
            - Has no effect when creating a new gateway.
        type: str
    protected:
        description:
            - Deletion protection. A protected gateway cannot be deleted.
            - With I(state=absent), C(false) disables protection before deleting.
        type: bool
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: Create NAT gateway
  cubepathinc.cloud.nat_gateway:
    api_token: "{{ cubepath_token }}"
    name: my-nat-gw
    plan_name: nat.small
    network_id: 42
    project_id: 7
    state: present
  register: gw

- name: Resize NAT gateway
  cubepathinc.cloud.nat_gateway:
    api_token: "{{ cubepath_token }}"
    name: my-nat-gw
    plan_name: nat.small
    network_id: 42
    resize_plan: nat.medium
    state: present

- name: Delete NAT gateway by UUID
  cubepathinc.cloud.nat_gateway:
    api_token: "{{ cubepath_token }}"
    name: my-nat-gw
    nat_gateway_uuid: "abc-123"
    state: absent
'''

RETURN = r'''
nat_gateway:
    description: NAT gateway details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def find_gateway(api, name):
    gateways = api.get('/nat-gateway/')
    if isinstance(gateways, list):
        for gw in gateways:
            if gw.get('name') == name:
                return gw
    return None


def update_existing(module, api, existing):
    """Apply label, protection, plan and project changes to an existing gateway."""
    p = module.params
    uuid = existing.get('uuid')
    calls = []
    if p.get('label') is not None and p['label'] != existing.get('label'):
        calls.append(('patch', '/nat-gateway/%s' % uuid, {'label': p['label']}))
    if p.get('protected') is not None and p['protected'] != bool(existing.get('protected')):
        calls.append(('post', '/nat-gateway/%s/protection' % uuid, {'enabled': p['protected']}))
    # Only resize when the requested plan differs from the current one, otherwise the API rejects an
    # unchanged resize (400 "already on plan") and the task would no longer be idempotent.
    if p.get('resize_plan') and p['resize_plan'] != existing.get('plan_name'):
        calls.append(('post', '/nat-gateway/%s/resize' % uuid, {'plan_name': p['resize_plan']}))
    if p.get('project_id') is not None and p['project_id'] != existing.get('project_id'):
        calls.append(('post', '/nat-gateway/%s/move-to-project' % uuid, {'project_id': p['project_id']}))
    if not calls:
        return dict(changed=False, nat_gateway=existing)
    if module.check_mode:
        return dict(changed=True, nat_gateway=existing)
    for method, path, data in calls:
        getattr(api, method)(path, data)
    return dict(changed=True, nat_gateway=find_gateway(api, p['name']))


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str'),
        label=dict(type='str'),
        plan_name=dict(type='str'),
        network_id=dict(type='int'),
        project_id=dict(type='int'),
        nat_gateway_uuid=dict(type='str'),
        resize_plan=dict(type='str'),
        protected=dict(type='bool'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['name', 'plan_name', 'network_id'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params.get('name')

    if state == 'present':
        existing = find_gateway(api, name)

        if existing:
            module.exit_json(**update_existing(module, api, existing))

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': name,
            'plan_name': module.params['plan_name'],
            'network_id': module.params['network_id'],
        }
        if module.params.get('label'):
            data['label'] = module.params['label']
        if module.params.get('project_id') is not None:
            data['project_id'] = module.params['project_id']

        result = api.post('/nat-gateway/', data)
        if module.params.get('protected') and result.get('uuid'):
            api.post('/nat-gateway/%s/protection' % result['uuid'], {'enabled': True})
        module.exit_json(changed=True, nat_gateway=result)

    elif state == 'absent':
        uuid = module.params.get('nat_gateway_uuid')
        existing = None
        if name:
            existing = find_gateway(api, name)
        if not uuid and existing:
            uuid = existing.get('uuid')
        if not uuid:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if existing and existing.get('uuid') == uuid and module.params.get('protected') is False and existing.get('protected'):
            api.post('/nat-gateway/%s/protection' % uuid, {'enabled': False})
        api.delete('/nat-gateway/%s' % uuid)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
