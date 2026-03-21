#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: baremetal
short_description: Deploy baremetal servers on CubePath Cloud
description:
    - Deploy baremetal servers on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    project_id:
        description: Project ID.
        type: int
        required: true
    location:
        description: Location for deployment.
        type: str
        required: true
    model:
        description: Server model name.
        type: str
        required: true
    hostname:
        description: Hostname for the server.
        type: str
        required: true
    password:
        description: Root password.
        type: str
        required: true
    os:
        description: Operating system name.
        type: str
    disk_layout:
        description: Disk layout name.
        type: str
    ssh_key:
        description: SSH key name.
        type: str
    label:
        description: Server label. Defaults to hostname.
        type: str
    user:
        description: Username.
        type: str
        default: root
'''

EXAMPLES = r'''
- name: Deploy baremetal
  cubepathinc.cloud.baremetal:
    api_token: "{{ cubepath_token }}"
    project_id: 1
    location: eu-bcn-1
    model: AMDRyzen75800X-128GB-2x1TB
    hostname: db-01
    password: "{{ vault_password }}"
    os: Debian 13
    ssh_key: deploy-key
'''

RETURN = r'''
baremetal:
    description: Baremetal server details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import find_resource_in_projects


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        project_id=dict(type='int', required=True),
        location=dict(type='str', required=True),
        model=dict(type='str', required=True),
        hostname=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        os=dict(type='str'),
        disk_layout=dict(type='str'),
        ssh_key=dict(type='str', no_log=False),
        label=dict(type='str'),
        user=dict(type='str', default='root'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    project_id = module.params['project_id']
    hostname = module.params['hostname']

    existing = find_resource_in_projects(api, 'baremetals', 'hostname', hostname, project_id)
    if existing:
        module.exit_json(changed=False, baremetal=existing)
    if module.check_mode:
        module.exit_json(changed=True)

    data = {
        'location_name': module.params['location'],
        'model_name': module.params['model'],
        'hostname': hostname,
        'user': module.params['user'],
        'password': module.params['password'],
        'label': module.params.get('label') or hostname,
    }
    if module.params.get('os'):
        data['os_name'] = module.params['os']
    if module.params.get('disk_layout'):
        data['disk_layout_name'] = module.params['disk_layout']
    if module.params.get('ssh_key'):
        data['ssh_key_name'] = module.params['ssh_key']

    result = api.post('/baremetal/deploy/%d' % project_id, data)
    module.exit_json(changed=True, baremetal=result)


if __name__ == '__main__':
    main()
