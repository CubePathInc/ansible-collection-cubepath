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
    - Purge cached content from every edge location, rotate the Token Auth secret, or sign a URL for a zone
      with Token Auth.
version_added: "1.2.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    action:
        description: Action to perform.
        type: str
        required: true
        choices: [request_ssl, move_project, purge_cache, rotate_token_secret, sign_url]
    zone_uuid:
        description: UUID of the CDN zone.
        type: str
        required: true
    project_id:
        description: Target project ID. Required when I(action=move_project).
        type: int
    paths:
        description:
            - Paths to purge with I(action=purge_cache), up to 100. C(/assets/app.css) purges that path,
              C(/images/*) everything under C(/images/).
            - When omitted, the whole cache of the zone is purged.
        type: list
        elements: str
        version_added: "1.5.0"
    wait:
        description: With I(action=purge_cache), wait until every edge location has purged.
        type: bool
        default: false
        version_added: "1.5.0"
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 300
        version_added: "1.5.0"
    path:
        description: Path or URL to sign. Required when I(action=sign_url).
        type: str
        version_added: "1.5.0"
    expires_in:
        description: Seconds the signed URL is valid (60 to 604800).
        type: int
        default: 3600
        version_added: "1.5.0"
    client_ip:
        description: IP the signed URL is bound to, required when the zone binds tokens to the client IP.
        type: str
        version_added: "1.5.0"
notes:
    - I(action=rotate_token_secret) enables Token Auth and returns the new secret in C(result.token_auth_secret).
      It is shown only once.
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

- name: Purge the stylesheets after a deploy
  cubepathinc.cloud.cdn_zone_action:
    api_token: "{{ cubepath_token }}"
    action: purge_cache
    zone_uuid: 9ffd2652-a68c-4cc3-a2b9-06c88e892482
    paths:
      - /assets/*
    wait: true

- name: Signed link valid for one day
  cubepathinc.cloud.cdn_zone_action:
    api_token: "{{ cubepath_token }}"
    action: sign_url
    zone_uuid: 9ffd2652-a68c-4cc3-a2b9-06c88e892482
    path: /videos/clip.mp4
    expires_in: 86400
  register: signed
'''

RETURN = r'''
result:
    description: Raw API response body.
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, wait_for


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        action=dict(type='str', required=True, choices=['request_ssl', 'move_project', 'purge_cache', 'rotate_token_secret', 'sign_url']),
        zone_uuid=dict(type='str', required=True),
        project_id=dict(type='int'),
        paths=dict(type='list', elements='str'),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(type='int', default=300),
        path=dict(type='str'),
        expires_in=dict(type='int', default=3600),
        client_ip=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('action', 'move_project', ['project_id']), ('action', 'sign_url', ['path'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    action = module.params['action']
    zone_uuid = module.params['zone_uuid']

    if action == 'sign_url':
        # Signing only computes a token; nothing changes on the zone.
        data = {'path': module.params['path'], 'expires_in': module.params['expires_in']}
        if module.params.get('client_ip'):
            data['client_ip'] = module.params['client_ip']
        module.exit_json(changed=False, result=api.post('/cdn/zones/%s/token-auth/sign-url' % zone_uuid, data))

    if module.check_mode:
        module.exit_json(changed=True, msg='Would %s on zone %s' % (action, zone_uuid))

    if action == 'request_ssl':
        result = api.post('/cdn/zones/%s/request-ssl' % zone_uuid)
    elif action == 'move_project':
        result = api.post(
            '/cdn/zones/%s/move-project' % zone_uuid,
            {'project_id': module.params['project_id']},
        )
    elif action == 'rotate_token_secret':
        result = api.post('/cdn/zones/%s/token-auth/rotate-secret' % zone_uuid)
    elif action == 'purge_cache':
        paths = module.params.get('paths')
        result = api.post('/cdn/zones/%s/purge-cache' % zone_uuid, {'paths': paths} if paths else {'everything': True})
        if module.params['wait']:
            purge_uuid = result.get('purge_uuid')

            def fetch():
                return next((x for x in as_list(api.get('/cdn/zones/%s/purge-cache' % zone_uuid)) if x.get('purge_uuid') == purge_uuid), None)
            purge = wait_for(module, fetch, lambda x: x is not None and x.get('status') not in ('pending', 'in_progress'),
                             module.params['wait_timeout'])
            if purge.get('status') != 'completed':
                module.fail_json(msg='The purge ended as %s' % purge.get('status'), result=purge)
            result['purge'] = purge

    module.exit_json(changed=True, result=result)


if __name__ == '__main__':
    main()
