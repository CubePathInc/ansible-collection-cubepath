#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: network_bgp_peer
short_description: Manage BGP peers of a CubePath Cloud private network
description:
    - Create, update or delete eBGP sessions (Dynamic Routes) between the router of a private network and a
      server or IP inside it, so the server can announce its own prefixes to the network.
    - The module finds an existing peer of the network by I(peer_target). On an existing peer it updates
      I(max_prefix), I(description) and I(enabled). I(peer_type) and I(remote_asn) cannot be changed; delete
      the peer and create it again.
    - A network can have up to 8 peers.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the peer.
        type: str
        default: present
        choices: [present, absent]
    network_id:
        description: ID of the private network.
        type: int
        required: true
    peer_type:
        description: Kind of neighbor. Required to create the peer.
        type: str
        choices: [ip, vps, baremetal]
    peer_target:
        description: IP address inside the network, or ID of the VPS or baremetal server attached to it.
        type: str
        required: true
    remote_asn:
        description: AS number of the neighbor (any but 64512, the network side). Required to create the peer.
        type: int
    max_prefix:
        description: Maximum number of prefixes accepted from the neighbor (1 to 1000, 100 by default).
        type: int
    description:
        description: Free-form description.
        type: str
    enabled:
        description: Whether the session is configured on the router.
        type: bool
'''

EXAMPLES = r'''
- name: Let a VPN appliance announce the office networks
  cubepathinc.cloud.network_bgp_peer:
    api_token: "{{ cubepath_token }}"
    network_id: 42
    peer_type: vps
    peer_target: "123"
    remote_asn: 65010
    max_prefix: 50
    description: Office VPN
'''

RETURN = r'''
peer:
    description: Peer details (C(id), C(peer_type), C(peer_target), C(remote_asn), C(resolved_peer_ip), C(last_state)...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        network_id=dict(type='int', required=True),
        peer_type=dict(type='str', choices=['ip', 'vps', 'baremetal']),
        peer_target=dict(type='str', required=True),
        remote_asn=dict(type='int'),
        max_prefix=dict(type='int'),
        description=dict(type='str'),
        enabled=dict(type='bool'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params
    base = '/networks/%d/bgp-peers' % p['network_id']

    def fetch():
        return next((b for b in as_list(api.get(base)) if str(b.get('peer_target')) == p['peer_target']), None)

    peer = fetch()

    if p['state'] == 'absent':
        if peer is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s/%s' % (base, peer['id']))
        module.exit_json(changed=True)

    if peer is None:
        if not p.get('peer_type') or p.get('remote_asn') is None:
            module.fail_json(msg='peer_type and remote_asn are required to create a BGP peer')
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'peer_type': p['peer_type'], 'peer_target': p['peer_target'], 'remote_asn': p['remote_asn']}
        for k in ('max_prefix', 'description'):
            if p.get(k) is not None:
                data[k] = p[k]
        created = api.post(base, data)
        if p.get('enabled') is False:
            api.patch('%s/%s' % (base, created['peer_id']), {'enabled': False})
        module.exit_json(changed=True, peer=fetch())

    for k in ('peer_type', 'remote_asn'):
        if p.get(k) is not None and p[k] != peer.get(k):
            module.fail_json(msg='%s of the BGP peer to %s is %s and cannot be changed' % (k, p['peer_target'], peer.get(k)))
    update = dict((k, p[k]) for k in ('max_prefix', 'description', 'enabled') if p.get(k) is not None and p[k] != peer.get(k))
    if not update:
        module.exit_json(changed=False, peer=peer)
    if module.check_mode:
        module.exit_json(changed=True, peer=peer)
    api.patch('%s/%s' % (base, peer['id']), update)
    module.exit_json(changed=True, peer=fetch())


if __name__ == '__main__':
    main()
