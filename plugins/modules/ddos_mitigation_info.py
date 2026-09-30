#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_mitigation_info
short_description: Get DDoS Mitigation information from CubePath Cloud
description:
    - List the organization's IPs with Premium DDoS protection, the country and ASN catalogs and the
      prefix lists, or read the protection profile and firewall rules of one IP.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    gather:
        description:
            - What to return.
            - C(profile) (with its countries, ASNs and prefix lists) and C(firewall_rules) need I(network).
            - C(capture_ips) lists the IPs whose traffic can be captured with M(cubepathinc.cloud.ddos_traffic_info).
        type: list
        elements: str
        default: [ips]
        choices: [ips, countries, asns, prefix_lists, profile, firewall_rules, capture_ips]
    network:
        description: Protected IP address for C(profile) and C(firewall_rules).
        type: str
    ip_type:
        description: Only C(ips) of this family.
        type: str
        choices: [IPv4, IPv6]
    location:
        description: Only C(ips) of this location.
        type: str
    asn_search:
        description: Only C(asns) whose number is this value or whose name contains it.
        type: str
    prefix_list:
        description: Name or UUID of a prefix list whose entries are returned as RV(prefix_list_entries).
        type: str
'''

EXAMPLES = r'''
- name: IPs with Premium protection
  cubepathinc.cloud.ddos_mitigation_info:
    api_token: "{{ cubepath_token }}"
  register: ddos

- name: Profile and firewall rules of one IP
  cubepathinc.cloud.ddos_mitigation_info:
    api_token: "{{ cubepath_token }}"
    gather: [profile, firewall_rules]
    network: 203.0.113.10
  register: ip

- name: Look up Cloudflare's ASN
  cubepathinc.cloud.ddos_mitigation_info:
    api_token: "{{ cubepath_token }}"
    gather: [asns]
    asn_search: cloudflare
'''

RETURN = r'''
ips:
    description: C(single_ips) and C(subnets) with Premium protection, their location and whether they have a profile.
    type: dict
    returned: when C(ips) is in I(gather)
countries:
    description: Countries available for geo-blocking (C(iso_code), C(name)).
    type: list
    elements: dict
    returned: when C(countries) is in I(gather)
asns:
    description: AS numbers available for filtering (C(asn), C(name)).
    type: list
    elements: dict
    returned: when C(asns) is in I(gather)
prefix_lists:
    description: Prefix lists of the organization and of the platform.
    type: list
    elements: dict
    returned: when C(prefix_lists) is in I(gather)
prefix_list_entries:
    description: Networks of the prefix list given in I(prefix_list).
    type: list
    elements: str
    returned: when I(prefix_list) is set
profile:
    description: Protection profile of I(network) (platform defaults when it has none), with C(countries), C(asns) and C(prefix_lists).
    type: dict
    returned: when C(profile) is in I(gather)
firewall_rules:
    description: Firewall rules of I(network).
    type: list
    elements: dict
    returned: when C(firewall_rules) is in I(gather)
capture_ips:
    description: IPs whose traffic can be captured.
    type: list
    elements: dict
    returned: when C(capture_ips) is in I(gather)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec, path_quote
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_ddos import find_prefix_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        gather=dict(type='list', elements='str', default=['ips'],
                    choices=['ips', 'countries', 'asns', 'prefix_lists', 'profile', 'firewall_rules', 'capture_ips']),
        network=dict(type='str'),
        ip_type=dict(type='str', choices=['IPv4', 'IPv6']),
        location=dict(type='str'),
        asn_search=dict(type='str'),
        prefix_list=dict(type='str'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    gather = module.params['gather']
    network = module.params.get('network')
    if not network and ('profile' in gather or 'firewall_rules' in gather):
        module.fail_json(msg='network is required to gather profile or firewall_rules')
    result = {'changed': False}

    if 'ips' in gather:
        result['ips'] = api.get('/ddos-mitigation/ips',
                                params={'ip_type': module.params.get('ip_type'), 'location': module.params.get('location')})
    if 'countries' in gather:
        result['countries'] = as_list(api.get('/ddos-mitigation/countries'), 'countries')
    if 'asns' in gather:
        result['asns'] = as_list(api.get('/ddos-mitigation/asns', params={'search': module.params.get('asn_search')}), 'asns')
    if 'prefix_lists' in gather:
        result['prefix_lists'] = as_list(api.get('/ddos-mitigation/prefix-lists'), 'prefix_lists')
    if module.params.get('prefix_list'):
        pl = find_prefix_list(api, module.params['prefix_list'])
        if pl is None:
            module.fail_json(msg='Prefix list %s not found' % module.params['prefix_list'])
        entries = as_list(api.get('/ddos-mitigation/prefix-lists/%s/entries' % pl['uuid']), 'entries')
        result['prefix_list_entries'] = [e.get('network') for e in entries]
    if 'profile' in gather:
        path = '/ddos-mitigation/profiles/%s' % path_quote(network)
        profile = api.get(path)
        profile['countries'] = as_list(api.get('%s/countries' % path), 'countries')
        profile['asns'] = as_list(api.get('%s/asns' % path), 'asns')
        profile['prefix_lists'] = as_list(api.get('%s/prefix-lists' % path), 'prefix_lists')
        result['profile'] = profile
    if 'firewall_rules' in gather:
        result['firewall_rules'] = as_list(api.get('/ddos-mitigation/firewall-rules/%s' % path_quote(network)), 'rules')
    if 'capture_ips' in gather:
        result['capture_ips'] = as_list(api.get('/ddos-mitigation/traffic-capture/protected-ips'), 'ips')

    module.exit_json(**result)


if __name__ == '__main__':
    main()
