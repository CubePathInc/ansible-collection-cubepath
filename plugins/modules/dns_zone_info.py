#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_zone_info
short_description: List DNS zones on CubePath Cloud
description:
    - Retrieve DNS zones from CubePath Cloud.
    - Optionally return the GeoDNS regions, and the SOA settings and record health checks of I(zone_uuid).
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    domain:
        description: Filter by domain name.
        type: str
    project_id:
        description: Filter by project ID.
        type: int
    zone_uuid:
        description: Get a specific zone by UUID.
        type: str
    gather:
        description:
            - Extra information to return. C(soa) and C(health_checks) need I(zone_uuid).
        type: list
        elements: str
        default: []
        choices: [regions, soa, health_checks]
        version_added: "1.5.0"
'''

EXAMPLES = r'''
- name: List all DNS zones
  cubepathinc.cloud.dns_zone_info:
    api_token: "{{ cubepath_token }}"
  register: zones

- name: SOA and health checks of a zone
  cubepathinc.cloud.dns_zone_info:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    gather: [soa, health_checks]
  register: zone
'''

RETURN = r'''
zones:
    description: List of DNS zones.
    type: list
    returned: always
    elements: dict
regions:
    description: GeoDNS regions (C(code), C(name)).
    type: list
    returned: when C(regions) is in I(gather)
    elements: dict
    version_added: "1.5.0"
soa:
    description: SOA settings of I(zone_uuid).
    type: dict
    returned: when C(soa) is in I(gather)
    version_added: "1.5.0"
health_checks:
    description: Health checks of the records of I(zone_uuid).
    type: list
    returned: when C(health_checks) is in I(gather)
    elements: dict
    version_added: "1.5.0"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        domain=dict(type='str'),
        project_id=dict(type='int'),
        zone_uuid=dict(type='str'),
        gather=dict(type='list', elements='str', default=[], choices=['regions', 'soa', 'health_checks']),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    zone_uuid = module.params.get('zone_uuid')
    gather = module.params['gather']
    extra = {}
    if ('soa' in gather or 'health_checks' in gather) and not zone_uuid:
        module.fail_json(msg='zone_uuid is required to gather soa or health_checks')
    if 'regions' in gather:
        regions = api.get('/dns/regions')
        extra['regions'] = regions if isinstance(regions, list) else []
    if 'soa' in gather:
        extra['soa'] = api.get('/dns/zones/%s/soa' % zone_uuid)
    if 'health_checks' in gather:
        checks = api.get('/dns/zones/%s/health-checks' % zone_uuid)
        extra['health_checks'] = checks if isinstance(checks, list) else []

    if zone_uuid:
        result = api.get('/dns/zones/%s' % zone_uuid)
        module.exit_json(changed=False, zones=[result], **extra)

    params = {}
    if module.params.get('project_id'):
        params['project_id'] = module.params['project_id']

    zones = api.get('/dns/zones', params=params or None)
    if not isinstance(zones, list):
        zones = []

    domain = module.params.get('domain')
    if domain:
        zones = [z for z in zones if z.get('domain') == domain]

    module.exit_json(changed=False, zones=zones, **extra)


if __name__ == '__main__':
    main()
