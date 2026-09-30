#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_zone_info
short_description: List CDN zones on CubePath Cloud
description:
    - Retrieve CDN zones from CubePath Cloud.
    - Optionally return the CDN plans, and for I(zone_uuid) its origins, edge rules, WAF rules, cache purges,
      pricing and traffic metrics.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    name:
        description: Filter by zone name.
        type: str
    zone_uuid:
        description: Get a specific zone by UUID.
        type: str
    gather:
        description:
            - Extra information to return. Everything but C(plans) needs I(zone_uuid).
            - C(purges) lists the latest 20 cache purges with their progress per edge location.
        type: list
        elements: str
        default: []
        choices: [plans, origins, rules, waf_rules, purges, pricing]
        version_added: "1.5.0"
    rule_uuid:
        description: UUID of an edge rule of I(zone_uuid) to return as RV(rule).
        type: str
        version_added: "1.5.0"
    waf_rule_uuid:
        description: UUID of a WAF rule of I(zone_uuid) to return as RV(waf_rule).
        type: str
        version_added: "1.5.0"
    metrics:
        description: Traffic metrics of I(zone_uuid) to return in RV(metrics).
        type: list
        elements: str
        choices: [summary, requests, bandwidth, cache, status-codes, top-urls, top-countries, top-asn,
                  top-user-agents, blocked, pops, file-extensions]
        version_added: "1.5.0"
    metrics_minutes:
        description: Look-back window of the metrics in minutes.
        type: int
        default: 60
        version_added: "1.5.0"
    metrics_filters:
        description:
            - Filters applied to the metrics, passed as they are. For example C(country) (ISO codes, comma
              separated), C(status_range) (C(4xx)), C(cache_status) (C(HIT) or C(MISS)), C(path_prefix),
              C(interval_seconds) or C(limit).
        type: dict
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: List CDN zones
  cubepathinc.cloud.cdn_zone_info:
    api_token: "{{ cubepath_token }}"
  register: zones

- name: Rules and last hour traffic summary of a zone
  cubepathinc.cloud.cdn_zone_info:
    api_token: "{{ cubepath_token }}"
    zone_uuid: 9ffd2652-a68c-4cc3-a2b9-06c88e892482
    gather: [rules, waf_rules]
    metrics: [summary, top-urls]
  register: zone
'''

RETURN = r'''
zones:
    description: List of CDN zones.
    type: list
    returned: always
    elements: dict
plans:
    description: CDN plans with prices and limits.
    type: list
    returned: when C(plans) is in I(gather)
    elements: dict
    version_added: "1.5.0"
origins:
    description: Origins of I(zone_uuid).
    type: list
    returned: when C(origins) is in I(gather)
    elements: dict
    version_added: "1.5.0"
rules:
    description: Edge rules of I(zone_uuid).
    type: list
    returned: when C(rules) is in I(gather)
    elements: dict
    version_added: "1.5.0"
waf_rules:
    description: WAF rules of I(zone_uuid).
    type: list
    returned: when C(waf_rules) is in I(gather)
    elements: dict
    version_added: "1.5.0"
purges:
    description: Latest cache purges of I(zone_uuid).
    type: list
    returned: when C(purges) is in I(gather)
    elements: dict
    version_added: "1.5.0"
pricing:
    description: Pricing of I(zone_uuid) (plan, override and effective price per GB).
    type: dict
    returned: when C(pricing) is in I(gather)
    version_added: "1.5.0"
rule:
    description: The edge rule given in I(rule_uuid).
    type: dict
    returned: when I(rule_uuid) is set
    version_added: "1.5.0"
waf_rule:
    description: The WAF rule given in I(waf_rule_uuid).
    type: dict
    returned: when I(waf_rule_uuid) is set
    version_added: "1.5.0"
metrics:
    description: One entry per metric in I(metrics), keyed by metric name.
    type: dict
    returned: when I(metrics) is set
    version_added: "1.5.0"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def gather_extra(module, api, zone_uuid):
    gather = module.params['gather']
    per_zone = [g for g in gather if g != 'plans']
    for opt in ('rule_uuid', 'waf_rule_uuid', 'metrics'):
        if module.params.get(opt):
            per_zone.append(opt)
    if per_zone and not zone_uuid:
        module.fail_json(msg='zone_uuid is required for %s' % ', '.join(per_zone))
    extra = {}
    base = '/cdn/zones/%s' % zone_uuid
    if 'plans' in gather:
        extra['plans'] = as_list(api.get('/cdn/plans'))
    for key, sub in (('origins', 'origins'), ('rules', 'rules'), ('waf_rules', 'waf-rules'), ('purges', 'purge-cache')):
        if key in gather:
            extra[key] = as_list(api.get('%s/%s' % (base, sub)), key)
    if 'pricing' in gather:
        extra['pricing'] = api.get('%s/pricing' % base)
    if module.params.get('rule_uuid'):
        extra['rule'] = api.get('%s/rules/%s' % (base, module.params['rule_uuid']))
    if module.params.get('waf_rule_uuid'):
        extra['waf_rule'] = api.get('%s/waf-rules/%s' % (base, module.params['waf_rule_uuid']))
    if module.params.get('metrics'):
        params = dict(module.params.get('metrics_filters') or {}, minutes=module.params['metrics_minutes'])
        extra['metrics'] = dict((m, api.get('%s/metrics/%s' % (base, m), params=params)) for m in module.params['metrics'])
    return extra


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        zone_uuid=dict(type='str'),
        gather=dict(type='list', elements='str', default=[], choices=['plans', 'origins', 'rules', 'waf_rules', 'purges', 'pricing']),
        rule_uuid=dict(type='str'),
        waf_rule_uuid=dict(type='str'),
        metrics=dict(type='list', elements='str', choices=[
            'summary', 'requests', 'bandwidth', 'cache', 'status-codes', 'top-urls', 'top-countries', 'top-asn',
            'top-user-agents', 'blocked', 'pops', 'file-extensions',
        ]),
        metrics_minutes=dict(type='int', default=60),
        metrics_filters=dict(type='dict'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    zone_uuid = module.params.get('zone_uuid')
    extra = gather_extra(module, api, zone_uuid)
    if zone_uuid:
        result = api.get('/cdn/zones/%s' % zone_uuid)
        module.exit_json(changed=False, zones=[result], **extra)

    result = api.get('/cdn/zones')
    if isinstance(result, list):
        zones = result
    elif isinstance(result, dict):
        zones = result.get('zones', [])
    else:
        zones = []

    name = module.params.get('name')
    if name:
        zones = [z for z in zones if z.get('name') == name]

    module.exit_json(changed=False, zones=zones, **extra)


if __name__ == '__main__':
    main()
