#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: availability_group
short_description: Manage VPS availability groups on CubePath Cloud
description:
    - Create or delete availability groups, which spread their VPS over different hypervisors, and manage
      which VPS belong to them.
    - The module finds an existing group by I(name) in the organization. When it is in another project than
      I(project_id), it is moved there.
    - Only an empty group can be deleted; with I(state=absent) the module first removes its VPS.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the group.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the group (up to 100 characters).
        type: str
        required: true
    project_id:
        description:
            - Project of the group. Required when I(state=present).
            - An existing group in another project is moved to this one.
        type: int
    location:
        description: Location of the group, for example C(eu-bcn-1). Required to create it.
        type: str
    description:
        description: Description, only used when the group is created.
        type: str
    vps_ids:
        description:
            - IDs of the VPS that must be in the group. VPS in the group but not in this list are removed
              when I(purge_vps=true).
            - When omitted, the members are left as they are.
        type: list
        elements: int
    purge_vps:
        description: Remove the VPS that are not in I(vps_ids).
        type: bool
        default: true
'''

EXAMPLES = r'''
- name: Spread the web servers
  cubepathinc.cloud.availability_group:
    api_token: "{{ cubepath_token }}"
    name: web
    project_id: 12
    location: eu-bcn-1
    vps_ids: [101, 102, 103]
  register: web_ag
'''

RETURN = r'''
availability_group:
    description: Group details (C(uuid), C(name), C(strategy), C(location_name), C(vps_list)...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, get_projects


def find_group(api, name):
    for proj in get_projects(api):
        project_id = (proj.get('project') or {}).get('id')
        if project_id is None:
            continue
        for group in as_list(api.get('/vps/availability-groups/project/%d' % project_id), 'groups'):
            if group.get('name') == name:
                return group
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        project_id=dict(type='int'),
        location=dict(type='str'),
        description=dict(type='str'),
        vps_ids=dict(type='list', elements='int'),
        purge_vps=dict(type='bool', default=True),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['project_id'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    p = module.params
    group = find_group(api, p['name'])

    if p['state'] == 'absent':
        if group is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        for vps in group.get('vps_list') or []:
            api.delete('/vps/availability-groups/%s/vps/%d' % (group['uuid'], vps['id']))
        api.delete('/vps/availability-groups/%s' % group['uuid'])
        module.exit_json(changed=True)

    changed = False
    if group is None:
        if not p.get('location'):
            module.fail_json(msg='location is required to create an availability group')
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'project_id': p['project_id'], 'name': p['name'], 'location_name': p['location']}
        if p.get('description') is not None:
            data['description'] = p['description']
        created = api.post('/vps/availability-groups/', data)
        group = api.get('/vps/availability-groups/%s' % created['uuid'])
        changed = True

    if group.get('project_id') != p['project_id']:
        if module.check_mode:
            module.exit_json(changed=True, availability_group=group)
        api.post('/vps/availability-groups/%s/move-project' % group['uuid'], {'project_id': p['project_id']})
        changed = True

    if p.get('vps_ids') is not None:
        members = [v.get('id') for v in group.get('vps_list') or []]
        to_add = [v for v in p['vps_ids'] if v not in members]
        to_remove = [v for v in members if v not in p['vps_ids']] if p['purge_vps'] else []
        if (to_add or to_remove) and module.check_mode:
            module.exit_json(changed=True, availability_group=group)
        for vps_id in to_remove:
            api.delete('/vps/availability-groups/%s/vps/%d' % (group['uuid'], vps_id))
        for vps_id in to_add:
            api.post('/vps/availability-groups/%s/vps/%d' % (group['uuid'], vps_id))
        changed = changed or bool(to_add or to_remove)

    module.exit_json(changed=changed, availability_group=api.get('/vps/availability-groups/%s' % group['uuid']))


if __name__ == '__main__':
    main()
