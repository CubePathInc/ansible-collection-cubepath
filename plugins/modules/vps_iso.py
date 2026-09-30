#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: vps_iso
short_description: Mount or unmount ISO images on a CubePath VPS
description:
    - Attach an ISO image to the virtual CD drive of a VPS, or detach it. A VPS has one drive.
    - List the available ISOs with M(cubepathinc.cloud.vps_iso_info).
    - The change runs in the background; boot from the ISO from the VPS console.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: C(present) mounts I(iso), C(absent) unmounts whatever is mounted.
        type: str
        default: present
        choices: [present, absent]
    vps_id:
        description: ID of the VPS.
        type: int
        required: true
    iso:
        description: Name or ID of the ISO to mount. Required when I(state=present).
        type: str
'''

EXAMPLES = r'''
- name: Mount a rescue ISO
  cubepathinc.cloud.vps_iso:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
    iso: SystemRescue 11

- name: Unmount it
  cubepathinc.cloud.vps_iso:
    api_token: "{{ cubepath_token }}"
    vps_id: 456
    state: absent
'''

RETURN = r'''
result:
    description: API response.
    type: dict
    returned: when something changed
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        vps_id=dict(type='int', required=True),
        iso=dict(type='str'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['iso'])],
        supports_check_mode=True,
    )
    api = CubePathAPI(module)
    vps_id = module.params['vps_id']

    catalog = api.get('/vps/%d/isos' % vps_id)
    mounted = (catalog or {}).get('mounted_iso_id')

    if module.params['state'] == 'absent':
        if not mounted:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        module.exit_json(changed=True, result=api.delete('/vps/%d/iso' % vps_id))

    ref = module.params['iso']
    iso = next((i for i in as_list(catalog, 'items') if ref in (i.get('id'), i.get('name'), i.get('filename'))), None)
    if iso is None:
        module.fail_json(msg='ISO %s not found' % ref)
    if mounted == iso['id']:
        module.exit_json(changed=False)
    if module.check_mode:
        module.exit_json(changed=True)
    module.exit_json(changed=True, result=api.post('/vps/%d/iso' % vps_id, {'iso_id': iso['id']}))


if __name__ == '__main__':
    main()
