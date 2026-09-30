#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_firewall_groups
short_description: Assign firewall groups to a VPS on CubePath Cloud
description:
    - Set the exact list of firewall groups applied to a VPS. Groups not in I(firewall_groups) are unassigned.
    - Groups are managed with M(cubepathinc.cloud.firewall_group) and must be in the project of the VPS.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
    firewall_groups:
        description:
            - Names or IDs of the groups to apply (up to 10). An empty list removes every group.
        type: list
        elements: str
        required: true
'''

EXAMPLES = r'''
- name: Apply the web and ssh groups to a VPS
  cubepathinc.cloud.vps_firewall_groups:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
    firewall_groups: [web, ssh]
'''

RETURN = r'''
firewall_group_ids:
    description: IDs of the groups applied to the VPS.
    type: list
    elements: int
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        vps_id=dict(type='int', required=True),
        firewall_groups=dict(type='list', elements='str', required=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    vps_id = module.params['vps_id']

    vps = next((v for v in as_list(api.get('/vps/')) if v.get('id') == vps_id), None)
    if vps is None:
        module.fail_json(msg='VPS %d not found' % vps_id)
    project_id = (vps.get('project') or {}).get('id')

    groups = as_list(api.get('/firewall/groups'))
    wanted = []
    for ref in module.params['firewall_groups']:
        match = next((g for g in groups if g.get('project_id') == project_id and ref in (str(g.get('id')), g.get('name'))), None)
        if match is None:
            module.fail_json(msg='Firewall group %s not found in the project of VPS %d' % (ref, vps_id))
        if match['id'] not in wanted:
            wanted.append(match['id'])

    current = [g.get('id') for g in vps.get('firewall_groups') or []]
    if sorted(current) == sorted(wanted):
        module.exit_json(changed=False, firewall_group_ids=current)
    if module.check_mode:
        module.exit_json(changed=True, firewall_group_ids=wanted)
    api.put('/firewall/vps/%d/groups' % vps_id, {'firewall_group_ids': wanted})
    module.exit_json(changed=True, firewall_group_ids=wanted)


if __name__ == '__main__':
    main()
