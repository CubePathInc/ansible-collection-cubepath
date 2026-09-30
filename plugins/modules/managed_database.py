#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: managed_database
short_description: Manage Managed Databases on CubePath Cloud
description:
    - Create, update, scale or delete fully managed MySQL, PostgreSQL and Valkey databases on CubePath Cloud.
    - The module finds an existing database by I(name), which is unique in the organization.
    - Provisioning and scaling are asynchronous. By default the module waits until the database is
      C(active), or gone when I(state=absent).
    - On an existing database, I(label), the backup policy and I(protected) are updated in place, and a
      different I(replicas) or I(plan) scales it (one change at a time, waiting in between).
      I(engine), I(version) and I(topology) cannot be changed after creation.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the managed database.
        type: str
        default: present
        choices: [present, absent]
    name:
        description:
            - Name of the managed database, 2 to 60 lowercase letters, numbers and hyphens.
        type: str
        required: true
    project_id:
        description: Project the database is created in. Required to create it.
        type: int
    engine:
        description: Database engine. Required to create the database.
        type: str
        choices: [mysql, postgresql, valkey]
    version:
        description:
            - Engine version, for example C(8.0.39) for MySQL. Required to create the database.
            - The available versions are listed in the error returned for an unknown version.
        type: str
    plan:
        description:
            - Plan name (for example C(mysql.micro)) or UUID. Required to create the database.
            - The plan sets the size of every node and the location the database is deployed in.
            - On an existing database, a different plan scales it vertically.
        type: str
    location:
        description:
            - Location of the plan, for example C(eu-bcn-1).
            - Only needed when the plan name exists in more than one location.
        type: str
    replicas:
        description:
            - Number of nodes. Defaults to the API default (3) on create.
            - MySQL needs at least 3, PostgreSQL and Valkey at least 2, and the plan sets the maximum.
            - On an existing database, a different value scales it horizontally.
        type: int
    topology:
        description: Cluster topology. Defaults per engine (C(mgr) for MySQL, C(replication) otherwise).
        type: str
    label:
        description: Free-form label.
        type: str
    backup_enabled:
        description: Enable or disable automatic backups.
        type: bool
    backup_schedule:
        description: Backup schedule as a 5-field cron expression, for example C(0 3 * * *).
        type: str
    backup_retention_days:
        description: Days to keep backups (1-365).
        type: int
    protected:
        description:
            - Deletion protection. A protected database cannot be deleted.
            - With I(state=absent), C(false) disables protection before deleting.
        type: bool
    wait:
        description: Wait until the database is C(active), or deleted when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 3600
notes:
    - The organization can run up to 5 managed databases and create one at a time. With I(wait=true) a
      create that finds the platform busy is retried until I(wait_timeout); with I(wait=false) it fails.
'''

EXAMPLES = r'''
- name: Create a 3 node MySQL database
  cubepathinc.cloud.managed_database:
    api_token: "{{ cubepath_token }}"
    name: app-db
    project_id: 12
    engine: mysql
    version: "8.0.39"
    plan: mysql.micro
    location: eu-bcn-1
    replicas: 3
    backup_schedule: "0 3 * * *"
    protected: true
  register: db

- name: Scale it to 5 nodes
  cubepathinc.cloud.managed_database:
    api_token: "{{ cubepath_token }}"
    name: app-db
    replicas: 5

- name: Delete it
  cubepathinc.cloud.managed_database:
    api_token: "{{ cubepath_token }}"
    name: app-db
    protected: false
    state: absent
'''

RETURN = r'''
managed_database:
    description: Managed database details (engine, version, status, endpoint, plan, location, backup policy...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import wait_for
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_managed_database import find_instance, resolve_plan

# Statuses in which the database accepts day-2 operations.
OPERABLE = ('active', 'degraded')
# Statuses that settle by themselves; the module waits them out before acting.
TRANSIENT = ('provisioning', 'updating', 'scaling', 'backing_up', 'restoring')


class Runner(object):
    def __init__(self, module, api):
        self.module = module
        self.api = api
        self.p = module.params
        self.timeout = module.params['wait_timeout']

    def fetch(self):
        md = find_instance(self.api, self.p['name'])
        if md is None:
            return None
        return self.api.get('/managed-databases/%s' % md['uuid'])

    def wait(self, done):
        return wait_for(self.module, self.fetch, done, self.timeout, interval=15)

    def settle(self, md):
        if md and md.get('status') in TRANSIENT:
            return self.wait(lambda m: m is None or m.get('status') not in TRANSIENT)
        return md

    def absent(self, md):
        module, p = self.module, self.p
        if md is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if p['wait']:
            md = self.settle(self.fetch()) or md
        if p.get('protected') is False and md.get('protected'):
            self.api.post('/managed-databases/%s/protection' % md['uuid'], {'enabled': False})
        if md.get('status') != 'deleting':
            self.api.delete('/managed-databases/%s' % md['uuid'])
        if p['wait']:
            self.wait(lambda m: m is None)
        module.exit_json(changed=True)

    def create(self):
        module, p = self.module, self.p
        missing = [k for k in ('project_id', 'engine', 'version', 'plan') if p.get(k) is None]
        if missing:
            module.fail_json(msg='%s required to create the managed database' % ', '.join(missing))
        if module.check_mode:
            module.exit_json(changed=True)
        plan = resolve_plan(module, self.api, p['plan'], p['engine'], p.get('location'))
        data = {
            'project_id': p['project_id'],
            'name': p['name'],
            'engine': p['engine'],
            'version': p['version'],
            'plan_uuid': plan['uuid'],
        }
        if p.get('replicas') is not None:
            data['replicas'] = p['replicas']
        if p.get('topology'):
            data['topology'] = p['topology']
        if p.get('backup_schedule') and p.get('backup_enabled') is not False:
            data['backup'] = {'schedule_cron': p['backup_schedule']}
            if p.get('backup_retention_days') is not None:
                data['backup']['retention_days'] = p['backup_retention_days']
        # The platform builds one database per organization at a time and answers 409 meanwhile;
        # with wait=true keep retrying until the other creation is done.
        self.api.post('/managed-databases/', data, busy_timeout=self.timeout if p['wait'] else 0)

    def update(self, current):
        """Label, backup policy and protection. Returns True when something changed."""
        module, p = self.module, self.p
        changed = False
        update = {}
        if p.get('label') is not None and p['label'] != current.get('label'):
            update['label'] = p['label']
        backup = {}
        if p.get('backup_enabled') is not None and p['backup_enabled'] != bool(current.get('backup_enabled')):
            backup['enabled'] = p['backup_enabled']
        if p.get('backup_schedule') and p['backup_schedule'] != current.get('backup_schedule_cron'):
            backup['schedule_cron'] = p['backup_schedule']
        if p.get('backup_retention_days') is not None and p['backup_retention_days'] != current.get('backup_retention_days'):
            backup['retention_days'] = p['backup_retention_days']
        if backup:
            update['backup'] = backup
        if update:
            if module.check_mode:
                module.exit_json(changed=True, managed_database=current)
            self.api.patch('/managed-databases/%s' % current['uuid'], update)
            changed = True
        if p.get('protected') is not None and p['protected'] != bool(current.get('protected')):
            if module.check_mode:
                module.exit_json(changed=True, managed_database=current)
            self.api.post('/managed-databases/%s/protection' % current['uuid'], {'enabled': p['protected']})
            changed = True
        return changed

    def scale(self, current):
        """The API takes exactly one of plan or replicas per request, so they go one after the other."""
        module, p = self.module, self.p
        scales = []
        if p.get('plan'):
            plan = resolve_plan(module, self.api, p['plan'], current.get('engine'), p.get('location'))
            if plan['uuid'] != (current.get('plan') or {}).get('uuid'):
                scales.append({'plan_uuid': plan['uuid']})
        if p.get('replicas') is not None and p['replicas'] != current.get('replicas'):
            scales.append({'replicas': p['replicas']})
        for i, scale in enumerate(scales):
            if module.check_mode:
                module.exit_json(changed=True, managed_database=current)
            if current.get('status') not in OPERABLE:
                module.fail_json(msg='The managed database must be active to scale it (status: %s)' % current.get('status'),
                                 managed_database=current)
            self.api.post('/managed-databases/%s/scale' % current['uuid'], scale)
            if p['wait'] or i < len(scales) - 1:
                current = self.wait(lambda m: m is not None and m.get('status') in OPERABLE + ('error',))
        return bool(scales)


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        project_id=dict(type='int'),
        engine=dict(type='str', choices=['mysql', 'postgresql', 'valkey']),
        version=dict(type='str'),
        plan=dict(type='str'),
        location=dict(type='str'),
        replicas=dict(type='int'),
        topology=dict(type='str'),
        label=dict(type='str'),
        backup_enabled=dict(type='bool'),
        backup_schedule=dict(type='str'),
        backup_retention_days=dict(type='int'),
        protected=dict(type='bool'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=3600),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    runner = Runner(module, CubePathAPI(module))

    md = find_instance(runner.api, module.params['name'])
    if module.params['state'] == 'absent':
        runner.absent(md)

    changed = False
    if md is None:
        runner.create()
        changed = True

    current = runner.fetch()
    if module.params['wait']:
        current = runner.settle(current)
        if current and current.get('status') == 'error':
            module.fail_json(msg='The managed database ended in error', managed_database=current)

    changed = runner.update(current) or changed
    changed = runner.scale(current) or changed
    module.exit_json(changed=changed, managed_database=runner.fetch())


if __name__ == '__main__':
    main()
