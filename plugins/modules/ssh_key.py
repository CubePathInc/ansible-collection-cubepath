#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ssh_key
short_description: Manage SSH keys on CubePath Cloud
description:
    - Create or delete SSH keys on CubePath Cloud.
version_added: "1.0.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the SSH key.
        type: str
        required: true
    public_key:
        description: Public key content. Required when I(state=present).
        type: str
    ssh_key_id:
        description: SSH key ID. Used for I(state=absent).
        type: int
'''

EXAMPLES = r'''
- name: Add SSH key
  cubepathinc.cloud.ssh_key:
    api_token: "{{ cubepath_token }}"
    name: my-key
    public_key: "ssh-ed25519 AAAA... user@host"
    state: present
'''

RETURN = r'''
ssh_key:
    description: SSH key details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def get_ssh_keys(api):
    result = api.get('/sshkey/user/sshkeys')
    if isinstance(result, dict):
        return result.get('sshkeys', [])
    return result if isinstance(result, list) else []


def find_ssh_key(api, name):
    for key in get_ssh_keys(api):
        if key.get('name') == name:
            return key
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        public_key=dict(type='str'),
        ssh_key_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['public_key'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    name = module.params['name']
    existing = find_ssh_key(api, name)

    if state == 'present':
        if existing:
            module.exit_json(changed=False, ssh_key=existing)
        if module.check_mode:
            module.exit_json(changed=True)
        result = api.post('/sshkey/create', {'name': name, 'ssh_key': module.params['public_key']})
        module.exit_json(changed=True, ssh_key=result)

    elif state == 'absent':
        key_id = module.params.get('ssh_key_id')
        if existing:
            key_id = existing.get('id')
        if not key_id:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/sshkey/%d' % key_id)
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
