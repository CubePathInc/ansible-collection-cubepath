#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: managed_database_action
short_description: One-shot operations on a CubePath Managed Database
description:
    - Rotate the admin password or change engine configuration parameters of a managed database.
    - Both operations are asynchronous. By default the module waits until the database is C(active) again.
    - The API reports the engine defaults, not the applied values, so I(action=configure) cannot tell
      whether a value is already set and always reports a change.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description:
            - C(rotate_credentials) sets a new admin password. Read it afterwards with
              M(cubepathinc.cloud.managed_database_info) and C(credentials).
            - C(configure) changes the parameters in I(parameters). Some parameters need a brief rolling restart,
              listed in C(result.requires_restart).
        type: str
        required: true
        choices: [rotate_credentials, configure]
    managed_database:
        description: Name or UUID of the managed database.
        type: str
        required: true
    parameters:
        description:
            - Parameters to change, as a map of name to value. Required when I(action=configure).
            - The allowed names and bounds depend on the engine; list them with
              M(cubepathinc.cloud.managed_database_info) and C(config).
        type: dict
    wait:
        description: Wait until the database is C(active) again.
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 1800
'''

EXAMPLES = r'''
- name: Raise max_connections
  cubepathinc.cloud.managed_database_action:
    api_token: "{{ cubepath_token }}"
    managed_database: app-db
    action: configure
    parameters:
      max_connections: 500

- name: Rotate the admin password
  cubepathinc.cloud.managed_database_action:
    api_token: "{{ cubepath_token }}"
    managed_database: app-db
    action: rotate_credentials
'''

RETURN = r'''
result:
    description: API response.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import wait_for
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_managed_database import require_instance


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        action=dict(type='str', required=True, choices=['rotate_credentials', 'configure']),
        managed_database=dict(type='str', required=True),
        parameters=dict(type='dict'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=1800),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('action', 'configure', ['parameters'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    md = require_instance(module, api, module.params['managed_database'])
    base = '/managed-databases/%s' % md['uuid']

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s managed database %s' % (action, md['name']))

    if action == 'rotate_credentials':
        result = api.post('%s/credentials/rotate' % base)
    else:
        result = api.patch('%s/config' % base, {'params': module.params['parameters']})

    if module.params['wait']:
        wait_for(module, lambda: api.get(base), lambda m: m.get('status') in ('active', 'degraded'),
                 module.params['wait_timeout'], interval=10)

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
