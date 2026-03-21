#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps
short_description: Manage VPS instances on CubePath Cloud
description:
    - Create or destroy VPS instances on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the VPS.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the VPS.
        type: str
        required: true
    project_id:
        description: ID of the project. Required when I(state=present).
        type: int
    plan:
        description: Plan name (e.g. gp.nano). Required when I(state=present).
        type: str
    template:
        description: OS template (e.g. debian-13). Required when I(state=present).
        type: str
    location:
        description: Location (e.g. eu-bcn-1). Required when I(state=present).
        type: str
    ssh_keys:
        description: List of SSH key names to attach.
        type: list
        elements: str
    password:
        description: Root password for the server.
        type: str
    ipv4:
        description: Enable dedicated IPv4.
        type: bool
        default: true
    label:
        description: Label for the server. Defaults to name.
        type: str
    network_id:
        description: Private network ID to attach.
        type: int
    backups:
        description: Enable automatic backups.
        type: bool
        default: false
    firewall_id:
        description: Firewall group ID.
        type: int
    cloudinit:
        description: Cloud-init configuration.
        type: str
    vps_id:
        description: ID of the VPS. Used for I(state=absent).
        type: int
'''

EXAMPLES = r'''
- name: Create VPS
  cubepathinc.cloud.vps:
    api_token: "{{ cubepath_token }}"
    name: web-01
    project_id: 1
    plan: gp.nano
    template: debian-13
    location: eu-bcn-1
    ssh_keys:
      - deploy-key
    state: present

- name: Destroy VPS
  cubepathinc.cloud.vps:
    api_token: "{{ cubepath_token }}"
    name: web-01
    vps_id: 456
    state: absent
'''

RETURN = r'''
vps:
    description: VPS details.
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
        plan=dict(type='str'),
        template=dict(type='str'),
        location=dict(type='str'),
        ssh_keys=dict(type='list', elements='str', no_log=False),
        password=dict(type='str', no_log=True),
        ipv4=dict(type='bool', default=True),
        label=dict(type='str'),
        network_id=dict(type='int'),
        backups=dict(type='bool', default=False),
        firewall_id=dict(type='int'),
        cloudinit=dict(type='str'),
        vps_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['project_id', 'plan', 'template', 'location'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params['name']

    if state == 'present':
        project_id = module.params['project_id']
        existing = find_resource_in_projects(api, 'vps', 'name', name, project_id)

        if existing:
            module.exit_json(changed=False, vps=existing)
        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': name,
            'plan_name': module.params['plan'],
            'template_name': module.params['template'],
            'location_name': module.params['location'],
            'label': module.params.get('label') or name,
            'ipv4': module.params['ipv4'],
            'enable_backups': module.params['backups'],
        }
        if module.params.get('ssh_keys'):
            data['ssh_key_names'] = module.params['ssh_keys']
        if module.params.get('password'):
            data['password'] = module.params['password']
        if module.params.get('network_id') is not None:
            data['network_id'] = module.params['network_id']
        if module.params.get('firewall_id') is not None:
            data['firewall_group_ids'] = [module.params['firewall_id']]
        if module.params.get('cloudinit'):
            data['custom_cloudinit'] = module.params['cloudinit']

        result = api.post('/vps/create/%d' % project_id, data)
        module.exit_json(changed=True, vps=result)

    elif state == 'absent':
        vps_id = module.params.get('vps_id')
        existing = find_resource_in_projects(api, 'vps', 'name', name)
        if existing:
            vps_id = existing.get('id')
        if not vps_id:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.post('/vps/destroy/%d' % vps_id)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
