#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_rule
short_description: Manage CDN edge rules on CubePath Cloud
description:
    - Create, update, or delete CDN edge rules on CubePath Cloud.
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
        description: Rule name. Required when I(state=present).
        type: str
    rule_type:
        description: Rule type. Required when I(state=present).
        type: str
        choices: [cache, cache_bypass, redirect, header_request, header_response]
    priority:
        description: Priority (1-10000).
        type: int
        default: 100
    action_config:
        description: Action configuration (dict).
        type: dict
        required: false
    match_conditions:
        description: Match conditions (dict).
        type: dict
    enabled:
        description: Enable or disable rule.
        type: bool
        default: true
    rule_uuid:
        description: Rule UUID for updates or deletion.
        type: str
'''

EXAMPLES = r'''
- name: Create cache rule
  cubepathinc.cloud.cdn_rule:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    name: cache-static
    rule_type: cache
    action_config:
      cache_ttl: 86400
    match_conditions:
      path_pattern: "*.css,*.js,*.png"
    state: present

- name: Delete rule
  cubepathinc.cloud.cdn_rule:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    rule_uuid: "def-456"
    state: absent
'''

RETURN = r'''
rule:
    description: Edge rule details.
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
        rule_type=dict(type='str', choices=['cache', 'cache_bypass', 'redirect', 'header_request', 'header_response']),
        priority=dict(type='int', default=100),
        action_config=dict(type='dict'),
        match_conditions=dict(type='dict'),
        enabled=dict(type='bool', default=True),
        rule_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'present', ['name', 'rule_type', 'action_config']),
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
            for field in ('name', 'priority', 'action_config', 'match_conditions', 'enabled'):
                if module.params.get(field) is not None:
                    data[field] = module.params[field]
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.patch('/cdn/zones/%s/rules/%s' % (zone_uuid, rule_uuid), data)
            module.exit_json(changed=True, rule=result)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': module.params['name'],
            'rule_type': module.params['rule_type'],
            'priority': module.params['priority'],
            'action_config': module.params['action_config'],
            'enabled': module.params['enabled'],
        }
        if module.params.get('match_conditions'):
            data['match_conditions'] = module.params['match_conditions']

        result = api.post('/cdn/zones/%s/rules' % zone_uuid, data)
        module.exit_json(changed=True, rule=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/cdn/zones/%s/rules/%s' % (zone_uuid, rule_uuid))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
