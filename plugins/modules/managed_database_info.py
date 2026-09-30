#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: managed_database_info
short_description: Get Managed Database information from CubePath Cloud
description:
    - List managed databases and the plan catalog, or read one database in detail with its logical
      databases, users, configuration, connection credentials and metrics.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    managed_database:
        description:
            - Name or UUID of one managed database, returned in detail as RV(managed_database).
            - Required for every I(gather) item except C(plans).
        type: str
    gather:
        description:
            - Extra information to return.
            - C(credentials) returns the admin user and password, and is only available while the database
              is active.
        type: list
        elements: str
        default: []
        choices: [plans, databases, users, config, credentials, metrics]
    engine:
        description: Only plans of this engine.
        type: str
        choices: [mysql, postgresql, valkey]
    metrics:
        description: Metrics to return with C(metrics) in I(gather). All of them by default.
        type: list
        elements: str
        choices: [connections, cpu, memory, replication_lag]
    time_range:
        description: Time range of the metrics, for example C(1h), C(24h), C(7d) or C(30d).
        type: str
        default: 1h
'''

EXAMPLES = r'''
- name: List managed databases and MySQL plans
  cubepathinc.cloud.managed_database_info:
    api_token: "{{ cubepath_token }}"
    gather: [plans]
    engine: mysql
  register: dbs

- name: Connection details of one database
  cubepathinc.cloud.managed_database_info:
    api_token: "{{ cubepath_token }}"
    managed_database: app-db
    gather: [credentials, databases, users]
  register: app_db
  no_log: true
'''

RETURN = r'''
managed_databases:
    description: Managed databases of the organization.
    type: list
    elements: dict
    returned: always
managed_database:
    description: Detail of the database given in I(managed_database).
    type: dict
    returned: when I(managed_database) is set
plans:
    description: Plans grouped by location, each with its per-node size and hourly price.
    type: list
    elements: dict
    returned: when C(plans) is in I(gather)
databases:
    description: Logical databases of the managed database.
    type: list
    elements: dict
    returned: when C(databases) is in I(gather)
users:
    description: Database users of the managed database (passwords are never listed).
    type: list
    elements: dict
    returned: when C(users) is in I(gather)
config:
    description: Tunable configuration parameters of the engine with their type, bounds and default.
    type: dict
    returned: when C(config) is in I(gather)
credentials:
    description: Admin connection details (C(host), C(port), C(username), C(password), C(uri)).
    type: dict
    returned: when C(credentials) is in I(gather)
metrics:
    description: Time series as lists of C([timestamp, value]) pairs, with C(start) and C(end).
    type: dict
    returned: when C(metrics) is in I(gather)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_managed_database import list_instances, list_plans


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        managed_database=dict(type='str'),
        gather=dict(type='list', elements='str', default=[],
                    choices=['plans', 'databases', 'users', 'config', 'credentials', 'metrics']),
        engine=dict(type='str', choices=['mysql', 'postgresql', 'valkey']),
        metrics=dict(type='list', elements='str', choices=['connections', 'cpu', 'memory', 'replication_lag']),
        time_range=dict(type='str', default='1h'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    gather = module.params['gather']
    instances = list_instances(api)
    result = {'changed': False, 'managed_databases': instances}

    if 'plans' in gather:
        result['plans'] = list_plans(api, module.params.get('engine'))

    ref = module.params.get('managed_database')
    per_instance = [g for g in gather if g != 'plans']
    if per_instance and not ref:
        module.fail_json(msg='managed_database is required to gather %s' % ', '.join(per_instance))
    if ref:
        match = next((m for m in instances if ref in (m.get('name'), m.get('uuid'))), None)
        if match is None:
            module.fail_json(msg='Managed database %s not found' % ref)
        base = '/managed-databases/%s' % match['uuid']
        result['managed_database'] = api.get(base)
        if 'databases' in gather:
            result['databases'] = api.get('%s/databases' % base)
        if 'users' in gather:
            result['users'] = api.get('%s/users' % base)
        if 'config' in gather:
            result['config'] = api.get('%s/config' % base)
        if 'credentials' in gather:
            result['credentials'] = api.get('%s/credentials' % base)
        if 'metrics' in gather:
            params = {'time_range': module.params['time_range']}
            if module.params.get('metrics'):
                params['metrics'] = ','.join(module.params['metrics'])
            result['metrics'] = api.get('%s/metrics' % base, params=params)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
