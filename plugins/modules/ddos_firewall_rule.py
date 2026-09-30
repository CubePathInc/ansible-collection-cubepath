#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_firewall_rule
short_description: Manage DDoS Mitigation firewall rules on CubePath Cloud
description:
    - Create or delete a firewall rule of the DDoS scrubbing platform for one of the organization's IPs.
    - A rule matches a protocol and destination port on the IP and applies an action. There is one rule per
      IP, protocol and port, found by those three values.
    - The API cannot update a rule, so a rule whose action or limits differ is deleted and created again.
    - Up to 20 rules per IP.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the rule.
        type: str
        default: present
        choices: [present, absent]
    network:
        description:
            - IP address the rule applies to.
            - With I(state=absent) an IPv4 subnet (up to C(/24)) of the organization is also accepted and
              deletes the rule for I(protocol) and I(dst_port) on every address in it.
        type: str
        required: true
    protocol:
        description: IP protocol number. C(0) any, C(1) ICMP, C(6) TCP, C(17) UDP.
        type: int
        required: true
    dst_port:
        description: Destination port, C(0) for any.
        type: int
        required: true
    rule_action:
        description:
            - Action of the rule. Required when I(state=present).
            - C(0) drop, C(1) accept, C(2) filter.
            - FiveM TCP C(10) monitor, C(11) auth, C(12) auth and rate limit. FiveM UDP C(15) monitor,
              C(16) auth, C(17) self-auth.
            - C(20) RDP TCP full auth, C(21) RDP UDP auth.
            - C(30) DNS UDP header validation, C(31) DNS TCP header and length validation.
            - C(40) Minecraft Java (TCP), C(50) TLS validation (TCP).
            - C(60) rate limit per source IP in packets per second, C(61) in megabits per second, with the
              limits in I(rate_limits).
        type: int
        choices: [0, 1, 2, 10, 11, 12, 15, 16, 17, 20, 21, 30, 31, 40, 50, 60, 61]
    rate_limits:
        description:
            - Per source limits for I(rule_action=60) or C(61), as a map of C(tcp_syn), C(tcp_ack), C(tcp_synack),
              C(tcp_rst), C(tcp_fin), C(tcp_all), C(udp) and C(icmp) to a number. Unset limits are C(0).
        type: dict
'''

EXAMPLES = r'''
- name: Protect a FiveM server
  cubepathinc.cloud.ddos_firewall_rule:
    api_token: "{{ cubepath_token }}"
    network: 203.0.113.10
    protocol: 17
    dst_port: 30120
    rule_action: 16

- name: Limit every source to 1000 SYN per second on port 443
  cubepathinc.cloud.ddos_firewall_rule:
    api_token: "{{ cubepath_token }}"
    network: 203.0.113.10
    protocol: 6
    dst_port: 443
    rule_action: 60
    rate_limits:
      tcp_syn: 1000

- name: Remove it
  cubepathinc.cloud.ddos_firewall_rule:
    api_token: "{{ cubepath_token }}"
    network: 203.0.113.10
    protocol: 6
    dst_port: 443
    state: absent
'''

RETURN = r'''
rule:
    description: The rule (C(id), C(action), C(action_label), limits...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec, path_quote
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list

LIMITS = ('tcp_syn', 'tcp_ack', 'tcp_synack', 'tcp_rst', 'tcp_fin', 'tcp_all', 'udp', 'icmp')


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        network=dict(type='str', required=True),
        protocol=dict(type='int', required=True),
        dst_port=dict(type='int', required=True),
        rule_action=dict(type='int', choices=[0, 1, 2, 10, 11, 12, 15, 16, 17, 20, 21, 30, 31, 40, 50, 60, 61]),
        rate_limits=dict(type='dict'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['rule_action'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    p = module.params
    network = p['network']

    if p['state'] == 'absent' and '/' in network and not network.endswith(('/32', '/128')):
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/ddos-mitigation/firewall-rules/bulk',
                   params={'network': network, 'protocol': p['protocol'], 'dst_port': p['dst_port']})
        module.exit_json(changed=True)

    rules = as_list(api.get('/ddos-mitigation/firewall-rules/%s' % path_quote(network)), 'rules')
    existing = next((r for r in rules if r.get('protocol') == p['protocol'] and r.get('dst_port') == p['dst_port']), None)

    if p['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/ddos-mitigation/firewall-rules/%d' % existing['id'])
        module.exit_json(changed=True)

    limits = p.get('rate_limits') or {}
    unknown = sorted(k for k in limits if k not in LIMITS)
    if unknown:
        module.fail_json(msg='Unknown rate limits: %s. Valid limits: %s' % (', '.join(unknown), ', '.join(LIMITS)))
    wanted = dict((k, int(limits.get(k) or 0)) for k in LIMITS)
    wanted['action'] = p['rule_action']

    if existing is not None and all(existing.get(k) == v for k, v in wanted.items()):
        module.exit_json(changed=False, rule=existing)
    if module.check_mode:
        module.exit_json(changed=True)
    if existing is not None:
        api.delete('/ddos-mitigation/firewall-rules/%d' % existing['id'])
    data = dict(wanted, network=network, protocol=p['protocol'], dst_port=p['dst_port'])
    api.post('/ddos-mitigation/firewall-rules', data)
    rules = as_list(api.get('/ddos-mitigation/firewall-rules/%s' % path_quote(network)), 'rules')
    rule = next((r for r in rules if r.get('protocol') == p['protocol'] and r.get('dst_port') == p['dst_port']), None)
    module.exit_json(changed=True, rule=rule)


if __name__ == '__main__':
    main()
