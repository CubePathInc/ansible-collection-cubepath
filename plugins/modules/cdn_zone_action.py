#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_zone_action
short_description: One-shot actions on CDN zones on CubePath Cloud
description:
    - Perform non-CRUD operations on an existing CDN zone — currently re-trigger
      automatic SSL issuance after fixing a DNS misconfiguration, and move
      a zone between projects within the same organization.
version_added: "1.2.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description: Action to perform.
        type: str
        required: true
        choices: [request_ssl, move_project]
    zone_uuid:
        description: UUID of the CDN zone.
        type: str
        required: true
    project_id:
        description: Target project ID. Required when I(action=move_project).
        type: int
'''

EXAMPLES = r'''
- name: Retry SSL issuance after fixing CNAME
  cubepathinc.cloud.cdn_zone_action:
    api_token: "{{ cubepath_token }}"
    action: request_ssl
    zone_uuid: 9ffd2652-a68c-4cc3-a2b9-06c88e892482

- name: Move a CDN zone to another project
  cubepathinc.cloud.cdn_zone_action:
    api_token: "{{ cubepath_token }}"
    action: move_project
    zone_uuid: 9ffd2652-a68c-4cc3-a2b9-06c88e892482
    project_id: 42
'''

RETURN = r'''
result:
    description: Raw API response body.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath import CubePathAPI


def main():
    argument_spec = dict(
        action=dict(type='str', required=True, choices=['request_ssl', 'move_project']),
        zone_uuid=dict(type='str', required=True),
        project_id=dict(type='int'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('action', 'move_project', ['project_id'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    zone_uuid = module.params['zone_uuid']

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s on zone %s' % (action, zone_uuid))

    if action == 'request_ssl':
        result = api.post('/cdn/zones/%s/request-ssl' % zone_uuid)
    elif action == 'move_project':
        result = api.post(
            '/cdn/zones/%s/move-project' % zone_uuid,
            {'project_id': module.params['project_id']},
        )

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
