#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: baremetal_info
short_description: List baremetal servers on CubePath Cloud
description:
    - Retrieve information about baremetal servers on CubePath Cloud.
    - Optionally list the server models on sale, and for one server the operating systems it can be
      reinstalled with and its KVM console access.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    hostname:
        description: Filter by hostname.
        type: str
    baremetal_id:
        description: Filter by baremetal ID.
        type: int
    project_id:
        description: Filter by project ID.
        type: int
    gather:
        description:
            - Extra information to return.
            - C(models) lists the server models per location with price and stock.
            - C(os) lists the operating systems and disk layouts I(baremetal_id) can be reinstalled with.
            - C(kvm) returns the KVM console URL and credentials of I(baremetal_id).
        type: list
        elements: str
        default: []
        choices: [models, os, kvm]
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: List all baremetals
  cubepathinc.cloud.baremetal_info:
    api_token: "{{ cubepath_token }}"
  register: servers

- name: Operating systems a server can be reinstalled with
  cubepathinc.cloud.baremetal_info:
    api_token: "{{ cubepath_token }}"
    baremetal_id: 10
    gather: [os]
  register: bm
'''

RETURN = r'''
servers:
    description: List of baremetal servers.
    type: list
    returned: always
    elements: dict
models:
    description: Server models on sale per location.
    type: list
    returned: when C(models) is in I(gather)
    elements: dict
    version_added: "1.5.0"
os:
    description: Operating systems and compatible disk layouts for I(baremetal_id).
    type: list
    returned: when C(os) is in I(gather)
    elements: dict
    version_added: "1.5.0"
kvm:
    description: KVM console C(url), C(username) and C(password) of I(baremetal_id).
    type: dict
    returned: when C(kvm) is in I(gather)
    version_added: "1.5.0"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import collect_resources_from_projects


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        hostname=dict(type='str'),
        baremetal_id=dict(type='int'),
        project_id=dict(type='int'),
        gather=dict(type='list', elements='str', default=[], choices=['models', 'os', 'kvm']),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    filters = {}
    if module.params.get('project_id'):
        filters['project_id'] = module.params['project_id']

    servers = collect_resources_from_projects(api, 'baremetals', filters or None)

    hostname = module.params.get('hostname')
    baremetal_id = module.params.get('baremetal_id')
    if hostname:
        servers = [s for s in servers if s.get('hostname') == hostname]
    if baremetal_id:
        servers = [s for s in servers if s.get('id') == baremetal_id]

    result = {'changed': False, 'servers': servers}
    gather = module.params['gather']
    if ('os' in gather or 'kvm' in gather) and not baremetal_id:
        module.fail_json(msg='baremetal_id is required to gather os or kvm')
    if 'models' in gather:
        result['models'] = (api.get('/baremetal/models') or {}).get('locations', [])
    if 'os' in gather:
        os_list = api.get('/baremetal/os/%d' % baremetal_id)
        result['os'] = os_list if isinstance(os_list, list) else []
    if 'kvm' in gather:
        result['kvm'] = api.get('/baremetal/%d/kvm' % baremetal_id)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
