#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: managed_database_db
short_description: Manage logical databases inside a CubePath Managed Database
description:
    - Create or delete a logical database (a schema) inside a MySQL or PostgreSQL managed database.
    - The module finds an existing logical database by I(name).
    - Creation and deletion are asynchronous. By default the module waits until the database is
      C(active), or gone when I(state=absent).
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the logical database.
        type: str
        default: present
        choices: [present, absent]
    managed_database:
        description: Name or UUID of the managed database.
        type: str
        required: true
    name:
        description: Name of the logical database. It starts with a lowercase letter and holds lowercase letters, digits and underscores.
        type: str
        required: true
    wait:
        description: Wait until the logical database is C(active), or deleted when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 600
'''

EXAMPLES = r'''
- name: Create the application schema
  cubepathinc.cloud.managed_database_db:
    api_token: "{{ cubepath_token }}"
    managed_database: app-db
    name: appdb
'''

RETURN = r'''
database:
    description: Logical database (C(uuid), C(name), C(status), C(created_at)).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, wait_for
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_managed_database import require_instance


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        managed_database=dict(type='str', required=True),
        name=dict(type='str', required=True),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=600),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    name = module.params['name']
    timeout = module.params['wait_timeout']
    md = require_instance(module, api, module.params['managed_database'])
    base = '/managed-databases/%s/databases' % md['uuid']

    def fetch():
        return next((d for d in as_list(api.get(base)) if d.get('name') == name), None)

    existing = fetch()

    if module.params['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if existing.get('status') != 'deleting':
            api.delete('%s/%s' % (base, existing['uuid']))
        if module.params['wait']:
            wait_for(module, fetch, lambda d: d is None, timeout)
        module.exit_json(changed=True)

    changed = False
    if existing is None:
        if module.check_mode:
            module.exit_json(changed=True)
        api.post(base, {'name': name})
        changed = True
    database = fetch()
    if module.params['wait'] and database and database.get('status') == 'pending':
        database = wait_for(module, fetch, lambda d: d is not None and d.get('status') != 'pending', timeout)
    module.exit_json(changed=changed, database=database)


if __name__ == '__main__':
    main()
