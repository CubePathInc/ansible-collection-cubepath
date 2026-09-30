#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_protection_profile
short_description: Manage DDoS protection profiles on CubePath Cloud
description:
    - Tune the DDoS Mitigation profile of an IP with Premium protection, and the countries, ASNs and
      prefix lists it filters.
    - Settings not given in I(settings) keep their current value (the platform defaults for an IP without
      a profile). The module only writes when something differs.
    - I(state=absent) deletes the profile, which puts the IP back on the platform defaults.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the profile.
        type: str
        default: present
        choices: [present, absent]
    network:
        description:
            - Protected IP address, for example C(203.0.113.10).
            - With I(state=absent) an IPv4 subnet of the organization is also accepted and deletes the
              profile of every address in it.
        type: str
        required: true
    settings:
        description:
            - Profile settings to set, as a map of setting name to integer value.
            - Filter levels (0 to 10) C(tcp_validation_level), C(tcp_validation_sym_level),
              C(udp_validation_level), C(invalid_filter_level), C(fragmented_filter_level),
              C(amplification_udp_level), C(amplification_tcp_level), C(icmp_rate_limit_level),
              C(same_packet_size_level), C(stateful_firewall_level).
            - C(default_action) 0 filter, 1 accept, 2 drop.
            - C(country_mode), C(asn_mode) and C(prefix_list_mode) 0 off, 1 block the listed sources,
              2 allow only the listed sources.
            - Thresholds (at least 1) C(udp_threshold_pps), C(tcp_threshold_pps), C(tcp_syn_threshold_pps),
              C(tcp_ack_threshold_pps), C(icmp_threshold_pps), C(udp_threshold_mbps), C(tcp_threshold_mbps),
              C(tcp_syn_threshold_mbps), C(tcp_ack_threshold_mbps), C(icmp_threshold_mbps).
            - C(syn_flood_threshold) (0 to 10000) and C(syn_flood_block_secs) (0 to 86400).
            - C(always_on_mitigation) and C(symmetric_routing), 0 or 1.
        type: dict
    countries:
        description:
            - ISO 3166 country codes the profile filters (see I(settings.country_mode)).
            - An empty list clears them. When omitted, they are left as they are.
        type: list
        elements: str
    asns:
        description:
            - AS numbers the profile filters (see I(settings.asn_mode)).
            - An empty list clears them. When omitted, they are left as they are.
        type: list
        elements: int
    prefix_lists:
        description:
            - Names or UUIDs of prefix lists the profile filters (see I(settings.prefix_list_mode)).
            - An empty list clears them. When omitted, they are left as they are.
        type: list
        elements: str
'''

EXAMPLES = r'''
- name: Only accept traffic from Spain and Portugal on a game server
  cubepathinc.cloud.ddos_protection_profile:
    api_token: "{{ cubepath_token }}"
    network: 203.0.113.10
    settings:
      udp_validation_level: 3
      country_mode: 2
    countries: [ES, PT]

- name: Back to the platform defaults
  cubepathinc.cloud.ddos_protection_profile:
    api_token: "{{ cubepath_token }}"
    network: 203.0.113.10
    state: absent
'''

RETURN = r'''
profile:
    description: The profile settings after the changes.
    type: dict
    returned: when I(state=present)
countries:
    description: Country codes assigned to the profile.
    type: list
    elements: str
    returned: when I(state=present)
asns:
    description: AS numbers assigned to the profile.
    type: list
    elements: int
    returned: when I(state=present)
prefix_lists:
    description: UUIDs of the prefix lists assigned to the profile.
    type: list
    elements: str
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec, path_quote
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_ddos import list_prefix_lists

SETTINGS = (
    'tcp_validation_level', 'tcp_validation_sym_level', 'udp_validation_level', 'invalid_filter_level',
    'fragmented_filter_level', 'amplification_udp_level', 'amplification_tcp_level', 'icmp_rate_limit_level',
    'same_packet_size_level', 'stateful_firewall_level', 'default_action', 'country_mode', 'asn_mode',
    'prefix_list_mode', 'udp_threshold_pps', 'tcp_threshold_pps', 'tcp_syn_threshold_pps', 'tcp_ack_threshold_pps',
    'icmp_threshold_pps', 'udp_threshold_mbps', 'tcp_threshold_mbps', 'tcp_syn_threshold_mbps',
    'tcp_ack_threshold_mbps', 'icmp_threshold_mbps', 'syn_flood_threshold', 'syn_flood_block_secs',
    'always_on_mitigation', 'symmetric_routing',
)


def has_profile(api, network):
    ips = api.get('/ddos-mitigation/ips')
    for item in as_list(ips, 'single_ips'):
        if item.get('network') == network:
            return bool(item.get('has_profile'))
    for subnet in as_list(ips, 'subnets'):
        if subnet.get('network') == network or '%s/%s' % (subnet.get('network'), subnet.get('prefix')) == network:
            return True
        for addr in subnet.get('ip_addresses') or []:
            if addr.get('address') == network:
                return bool(addr.get('has_profile'))
    return False


def sync_assignment(module, api, network, kind, key, wanted, current, result):
    """PUT a full replacement of one assignment list when it differs. Returns True on change."""
    if wanted is None:
        result[kind] = current
        return False
    if sorted(wanted) == sorted(current):
        result[kind] = current
        return False
    if not module.check_mode:
        api.put('/ddos-mitigation/profiles/%s/%s' % (path_quote(network), kind), {key: wanted})
    result[kind] = wanted
    return True


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        network=dict(type='str', required=True),
        settings=dict(type='dict'),
        countries=dict(type='list', elements='str'),
        asns=dict(type='list', elements='int'),
        prefix_lists=dict(type='list', elements='str'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    network = module.params['network']
    path = '/ddos-mitigation/profiles/%s' % path_quote(network)

    if module.params['state'] == 'absent':
        if '/' not in network and not has_profile(api, network):
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete(path)
        module.exit_json(changed=True)

    settings = module.params.get('settings') or {}
    unknown = sorted(k for k in settings if k not in SETTINGS)
    if unknown:
        module.fail_json(msg='Unknown settings: %s. Valid settings: %s' % (', '.join(unknown), ', '.join(SETTINGS)))

    current = api.get(path)
    exists = has_profile(api, network)
    desired = dict((k, current.get(k)) for k in SETTINGS)
    for k, v in settings.items():
        desired[k] = int(v)

    changed = False
    # A profile must exist before countries, ASNs or prefix lists can be assigned to it.
    if not exists or any(desired[k] != current.get(k) for k in SETTINGS):
        if not module.check_mode:
            body = dict((k, v) for k, v in desired.items() if v is not None)
            api.put(path, body)
        changed = True

    result = {'profile': desired}
    if exists:
        countries = [c.get('iso_code') for c in as_list(api.get('%s/countries' % path), 'countries')]
        asns = [a.get('asn') for a in as_list(api.get('%s/asns' % path), 'asns')]
        lists = [pl.get('uuid') for pl in as_list(api.get('%s/prefix-lists' % path), 'prefix_lists')]
    else:
        countries, asns, lists = [], [], []

    wanted_countries = None
    if module.params.get('countries') is not None:
        wanted_countries = [c.upper() for c in module.params['countries']]
    wanted_lists = None
    if module.params.get('prefix_lists') is not None:
        wanted_lists = []
        all_lists = list_prefix_lists(api)
        for ref in module.params['prefix_lists']:
            match = next((pl for pl in all_lists if ref in (pl.get('uuid'), pl.get('name'))), None)
            if match is None:
                module.fail_json(msg='Prefix list %s not found' % ref)
            wanted_lists.append(match['uuid'])

    changed = sync_assignment(module, api, network, 'countries', 'iso_codes', wanted_countries, countries, result) or changed
    changed = sync_assignment(module, api, network, 'asns', 'asns', module.params.get('asns'), asns, result) or changed
    changed = sync_assignment(module, api, network, 'prefix-lists', 'uuids', wanted_lists, lists, result) or changed
    result['prefix_lists'] = result.pop('prefix-lists')

    module.exit_json(changed=changed, **result)


if __name__ == '__main__':
    main()
