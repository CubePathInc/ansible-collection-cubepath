#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: ddos_traffic_info
short_description: Query DDoS Mitigation traffic captures on CubePath Cloud
description:
    - Read the sampled packets seen by the DDoS scrubbing platform for an IP with Premium protection, or the
      passed and dropped totals over time.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    query:
        description: C(packets) returns the captured packets of I(destination_ip), C(stats) the pass and drop totals per interval.
        type: str
        default: stats
        choices: [packets, stats]
    start_time:
        description: Start of the window, as an ISO 8601 date and time (UTC), for example C(2026-09-30T10:00:00).
        type: str
        required: true
    end_time:
        description: End of the window, as an ISO 8601 date and time (UTC).
        type: str
        required: true
    destination_ip:
        description: IP or subnet of the organization. Required when I(query=packets).
        type: str
    destination_ips:
        description: IPs for I(query=stats). All the organization's Premium IPs by default.
        type: list
        elements: str
    interval:
        description: Bucket size for I(query=stats).
        type: str
        default: 1m
        choices: [10s, 30s, 1m, 5m, 15m, 1h]
    filters:
        description:
            - Extra filters for I(query=packets), passed as they are. For example C(include_protocols),
              C(exclude_src_ips), C(include_dst_ports), C(include_actions), C(has_payload) or C(limit)
              (1 to 100000, 20000 by default).
        type: dict
'''

EXAMPLES = r'''
- name: Dropped packets to a game server in the last attack window
  cubepathinc.cloud.ddos_traffic_info:
    api_token: "{{ cubepath_token }}"
    query: packets
    destination_ip: 203.0.113.10
    start_time: "2026-09-30T10:00:00"
    end_time: "2026-09-30T10:15:00"
    filters:
      include_actions: [DROP]
      limit: 1000
  register: capture
'''

RETURN = r'''
traffic:
    description:
        - For C(packets), C(total_logs) and C(logs) with one entry per sampled packet.
        - For C(stats), C(total_pass), C(total_drop) and C(buckets) with counts, bytes and packets per second.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        query=dict(type='str', default='stats', choices=['packets', 'stats']),
        start_time=dict(type='str', required=True),
        end_time=dict(type='str', required=True),
        destination_ip=dict(type='str'),
        destination_ips=dict(type='list', elements='str'),
        interval=dict(type='str', default='1m', choices=['10s', '30s', '1m', '5m', '15m', '1h']),
        filters=dict(type='dict'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('query', 'packets', ['destination_ip'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    p = module.params
    window = {'start_time': p['start_time'], 'end_time': p['end_time']}

    if p['query'] == 'packets':
        data = dict(p.get('filters') or {}, destination_ip=p['destination_ip'], **window)
        traffic = api.post('/ddos-mitigation/traffic-capture', data)
    else:
        data = dict(window, destination_ips=p.get('destination_ips') or [], interval=p['interval'])
        traffic = api.post('/ddos-mitigation/traffic-capture/stats', data)

    module.exit_json(changed=False, traffic=traffic)


if __name__ == '__main__':
    main()
