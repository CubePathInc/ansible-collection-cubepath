#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_waf_rule
short_description: Manage CDN WAF rules on CubePath Cloud
description:
    - Create, update, or delete CDN WAF rules on CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state.
        type: str
        default: present
        choices: [present, absent]
    zone_uuid:
        description: CDN zone UUID.
        type: str
        required: true
    name:
        description: WAF rule name. Required when I(state=present).
        type: str
    rule_type:
        description: WAF rule type. Required when I(state=present).
        type: str
        choices: [rate_limit, ip_block, geo_block, custom]
    action:
        description: Action when triggered.
        type: str
        choices: [block, challenge, log]
        default: block
    priority:
        description: Priority (1-10000).
        type: int
        default: 100
    config:
        description: Rule configuration (dict).
        type: dict
    match_conditions:
        description: Match conditions (dict).
        type: dict
    enabled:
        description: Enable or disable.
        type: bool
        default: true
    rule_uuid:
        description: WAF rule UUID for updates or deletion.
        type: str
'''

EXAMPLES = r'''
- name: Create rate limit WAF rule
  cubepathinc.cloud.cdn_waf_rule:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    name: api-rate-limit
    rule_type: rate_limit
    action: block
    config:
      requests_per_second: 100
      burst: 200
    state: present

- name: Delete WAF rule
  cubepathinc.cloud.cdn_waf_rule:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    rule_uuid: "def-456"
    state: absent
'''

RETURN = r'''
waf_rule:
    description: WAF rule details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        zone_uuid=dict(type='str', required=True),
        name=dict(type='str'),
        rule_type=dict(type='str', choices=['rate_limit', 'ip_block', 'geo_block', 'custom']),
        action=dict(type='str', default='block', choices=['block', 'challenge', 'log']),
        priority=dict(type='int', default=100),
        config=dict(type='dict'),
        match_conditions=dict(type='dict'),
        enabled=dict(type='bool', default=True),
        rule_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'present', ['name', 'rule_type']),
            ('state', 'absent', ['rule_uuid']),
        ],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    zone_uuid = module.params['zone_uuid']
    rule_uuid = module.params.get('rule_uuid')

    if state == 'present':
        if rule_uuid:
            data = {}
            for field in ('name', 'action', 'priority', 'config', 'match_conditions', 'enabled'):
                if module.params.get(field) is not None:
                    data[field] = module.params[field]
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.patch('/cdn/zones/%s/waf-rules/%s' % (zone_uuid, rule_uuid), data)
            module.exit_json(changed=True, waf_rule=result)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': module.params['name'],
            'rule_type': module.params['rule_type'],
            'action': module.params['action'],
            'priority': module.params['priority'],
            'enabled': module.params['enabled'],
        }
        if module.params.get('config'):
            data['config'] = module.params['config']
        if module.params.get('match_conditions'):
            data['match_conditions'] = module.params['match_conditions']

        result = api.post('/cdn/zones/%s/waf-rules' % zone_uuid, data)
        module.exit_json(changed=True, waf_rule=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/cdn/zones/%s/waf-rules/%s' % (zone_uuid, rule_uuid))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
