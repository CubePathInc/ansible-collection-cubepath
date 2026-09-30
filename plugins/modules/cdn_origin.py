#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cdn_origin
short_description: Manage CDN origins on CubePath Cloud
description:
    - Create, update, or delete CDN origins on CubePath Cloud.
    - An origin can be an external server (I(origin_url) or I(address)) or one of your
      CubePath Object Storage buckets (I(object_storage_bucket_uuid)). For a bucket, the
      address, TLS, health check and read only credentials are set by CubePath, and deleting
      the origin stops serving the bucket.
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
        description: Origin name. Required when I(state=present).
        type: str
    origin_url:
        description: Origin URL (auto-parsed).
        type: str
    address:
        description: Origin IP or hostname.
        type: str
    port:
        description: Origin port.
        type: int
    protocol:
        description: Protocol.
        type: str
        choices: [http, https]
    weight:
        description: Load balancing weight (1-1000).
        type: int
        default: 100
    priority:
        description: Priority (1-100).
        type: int
        default: 1
    is_backup:
        description: Mark as backup origin.
        type: bool
        default: false
    health_check_enabled:
        description:
            - Enable health checks. Defaults to C(true) for external origins.
            - Not allowed with I(object_storage_bucket_uuid).
        type: bool
    health_check_path:
        description:
            - Health check path. Defaults to C(/health) for external origins.
            - Not allowed with I(object_storage_bucket_uuid).
        type: str
    verify_ssl:
        description:
            - Verify SSL certificates. Defaults to C(true) for external origins.
            - Not allowed with I(object_storage_bucket_uuid).
        type: bool
    host_header:
        description: Custom Host header.
        type: str
    base_path:
        description: Base path prefix.
        type: str
    enabled:
        description:
            - Enable or disable origin. Defaults to C(true) for external origins.
            - Not allowed with I(object_storage_bucket_uuid).
        type: bool
    origin_uuid:
        description: Origin UUID for updates or deletion.
        type: str
    object_storage_bucket_uuid:
        description:
            - Serve this Object Storage bucket of your organization through the zone.
            - Mutually exclusive with I(origin_url), I(address), I(port), I(protocol),
              I(host_header), I(base_path), I(verify_ssl), I(health_check_enabled),
              I(health_check_path) and I(enabled).
            - Idempotent, if the zone already has an origin for this bucket nothing changes.
            - With I(state=absent), removes the zone's origin for this bucket.
            - A bucket can be served by one origin at a time.
        type: str
        version_added: "1.4.0"
'''

EXAMPLES = r'''
- name: Create CDN origin
  cubepathinc.cloud.cdn_origin:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    name: primary-origin
    address: "1.2.3.4"
    port: 443
    protocol: https
    state: present

- name: Serve an Object Storage bucket through the CDN
  cubepathinc.cloud.cdn_origin:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    name: assets-bucket
    object_storage_bucket_uuid: "3f2b1c4d-0000-4000-8000-000000000000"
    state: present

- name: Stop serving the bucket
  cubepathinc.cloud.cdn_origin:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    object_storage_bucket_uuid: "3f2b1c4d-0000-4000-8000-000000000000"
    state: absent

- name: Delete CDN origin
  cubepathinc.cloud.cdn_origin:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    origin_uuid: "def-456"
    state: absent
'''

RETURN = r'''
origin:
    description: Origin details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec

# Set by CubePath for an Object Storage bucket origin; the API refuses them next to the bucket.
BUCKET_FIXED_FIELDS = (
    'origin_url', 'address', 'port', 'protocol', 'host_header', 'base_path',
    'verify_ssl', 'health_check_enabled', 'health_check_path', 'enabled',
)


def default(value, fallback):
    return fallback if value is None else value


def find_bucket_origin(api, zone_uuid, bucket_uuid):
    origins = api.get('/cdn/zones/%s/origins' % zone_uuid)
    for origin in origins if isinstance(origins, list) else []:
        if origin.get('object_storage_bucket_uuid') == bucket_uuid:
            return origin
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        zone_uuid=dict(type='str', required=True),
        name=dict(type='str'),
        origin_url=dict(type='str'),
        address=dict(type='str'),
        port=dict(type='int'),
        protocol=dict(type='str', choices=['http', 'https']),
        weight=dict(type='int', default=100),
        priority=dict(type='int', default=1),
        is_backup=dict(type='bool', default=False),
        health_check_enabled=dict(type='bool'),
        health_check_path=dict(type='str'),
        verify_ssl=dict(type='bool'),
        host_header=dict(type='str'),
        base_path=dict(type='str'),
        enabled=dict(type='bool'),
        origin_uuid=dict(type='str'),
        object_storage_bucket_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'present', ['name']),
            ('state', 'absent', ['origin_uuid', 'object_storage_bucket_uuid'], True),
        ],
        mutually_exclusive=[('object_storage_bucket_uuid', f) for f in BUCKET_FIXED_FIELDS],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    zone_uuid = module.params['zone_uuid']
    origin_uuid = module.params.get('origin_uuid')
    bucket_uuid = module.params.get('object_storage_bucket_uuid')

    if bucket_uuid and not origin_uuid:
        existing = find_bucket_origin(api, zone_uuid, bucket_uuid)
        if state == 'absent':
            if existing is None:
                module.exit_json(changed=False)
            origin_uuid = existing.get('uuid')
        elif existing is not None:
            module.exit_json(changed=False, origin=existing)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            data = {
                'name': module.params['name'],
                'object_storage_bucket_uuid': bucket_uuid,
                'weight': module.params['weight'],
                'priority': module.params['priority'],
                'is_backup': module.params['is_backup'],
            }
            result = api.post('/cdn/zones/%s/origins' % zone_uuid, data)
            module.exit_json(changed=True, origin=result)

    if state == 'present':
        if origin_uuid:
            data = {}
            for field in ('name', 'address', 'port', 'protocol', 'weight', 'priority', 'host_header', 'base_path'):
                if module.params.get(field) is not None:
                    data[field] = module.params[field]
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.patch('/cdn/zones/%s/origins/%s' % (zone_uuid, origin_uuid), data)
            module.exit_json(changed=True, origin=result)

        if not module.params.get('origin_url') and not module.params.get('address'):
            module.fail_json(msg='Either origin_url or address is required')

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': module.params['name'],
            'weight': module.params['weight'],
            'priority': module.params['priority'],
            'is_backup': module.params['is_backup'],
            'health_check_enabled': default(module.params['health_check_enabled'], True),
            'health_check_path': default(module.params['health_check_path'], '/health'),
            'verify_ssl': default(module.params['verify_ssl'], True),
            'enabled': default(module.params['enabled'], True),
        }
        if module.params.get('origin_url'):
            data['origin_url'] = module.params['origin_url']
        if module.params.get('address'):
            data['address'] = module.params['address']
        if module.params.get('port'):
            data['port'] = module.params['port']
        if module.params.get('protocol'):
            data['protocol'] = module.params['protocol']
        if module.params.get('host_header'):
            data['host_header'] = module.params['host_header']
        if module.params.get('base_path'):
            data['base_path'] = module.params['base_path']

        result = api.post('/cdn/zones/%s/origins' % zone_uuid, data)
        module.exit_json(changed=True, origin=result)

    elif state == 'absent':
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/cdn/zones/%s/origins/%s' % (zone_uuid, origin_uuid))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
