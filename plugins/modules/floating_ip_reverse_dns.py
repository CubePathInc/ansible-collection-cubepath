#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: floating_ip_reverse_dns
short_description: Manage the reverse DNS of CubePath floating IPs
description:
    - Set or remove the PTR record of a floating IP of the organization.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: C(present) sets I(hostname), C(absent) removes the PTR record.
        type: str
        default: present
        choices: [present, absent]
    address:
        description: Floating IP address.
        type: str
        required: true
    hostname:
        description: Host name the address resolves to, for example C(mail.example.com). Required when I(state=present).
        type: str
'''

EXAMPLES = r'''
- name: PTR for a mail server
  cubepathinc.cloud.floating_ip_reverse_dns:
    api_token: "{{ cubepath_token }}"
    address: 203.0.113.10
    hostname: mail.example.com
'''

RETURN = r'''
reverse_dns:
    description: PTR host name of the address, or null.
    type: str
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def current_ptr(api, address):
    result = api.get('/floating_ips/organization')
    for ip in (result or {}).get('single_ips', []):
        if ip.get('address') == address:
            return True, ip.get('reverse_dns')
    for subnet in (result or {}).get('subnets', []):
        for ip in subnet.get('ip_addresses') or subnet.get('ips') or []:
            if ip.get('address') == address:
                return True, ip.get('reverse_dns')
    return False, None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        address=dict(type='str', required=True),
        hostname=dict(type='str'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['hostname'])],
        supports_check_mode=True,
    )
    api = CubePathAPI(module)
    address = module.params['address']

    found, ptr = current_ptr(api, address)
    if not found:
        module.fail_json(msg='Floating IP %s not found in the organization' % address)
    wanted = module.params['hostname'] if module.params['state'] == 'present' else None
    if (ptr or '').rstrip('.') == (wanted or '').rstrip('.'):
        module.exit_json(changed=False, reverse_dns=ptr)
    if module.check_mode:
        module.exit_json(changed=True, reverse_dns=wanted)
    api.post('/floating_ips/reverse_dns/configure', params={'ip': address, 'reverse_dns': wanted or ''})
    module.exit_json(changed=True, reverse_dns=wanted)


if __name__ == '__main__':
    main()
