#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_record
short_description: Manage DNS records on CubePath Cloud
description:
    - Create, update, or delete DNS records on CubePath Cloud.
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
        description: DNS zone UUID.
        type: str
        required: true
    name:
        description: Record name (@ for apex). Required when I(state=present).
        type: str
    record_type:
        description: Record type. Required when I(state=present).
        type: str
        choices: [A, AAAA, CNAME, MX, TXT, SRV, NS, CAA, PTR]
    content:
        description: Record content. Required when I(state=present).
        type: str
    ttl:
        description: TTL in seconds.
        type: int
        default: 3600
    priority:
        description: Priority for MX/SRV records.
        type: int
    weight:
        description: Weight for SRV records.
        type: int
    port:
        description: Port for SRV records.
        type: int
    comment:
        description: Optional comment.
        type: str
    record_uuid:
        description: Record UUID. Required for I(state=absent) or updates.
        type: str
'''

EXAMPLES = r'''
- name: Create A record
  cubepathinc.cloud.dns_record:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    name: "@"
    record_type: A
    content: "1.2.3.4"
    state: present

- name: Delete record
  cubepathinc.cloud.dns_record:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    record_uuid: "def-456"
    state: absent
'''

RETURN = r'''
record:
    description: DNS record details.
    type: dict
    returned: on success
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def find_record(api, zone_uuid, name, record_type, content):
    records = api.get('/dns/zones/%s/records' % zone_uuid)
    if isinstance(records, list):
        for r in records:
            if (r.get('name') == name and
                    r.get('record_type') == record_type and
                    r.get('content') == content):
                return r
    return None


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        zone_uuid=dict(type='str', required=True),
        name=dict(type='str'),
        record_type=dict(type='str', choices=['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'NS', 'CAA', 'PTR']),
        content=dict(type='str'),
        ttl=dict(type='int', default=3600),
        priority=dict(type='int'),
        weight=dict(type='int'),
        port=dict(type='int'),
        comment=dict(type='str'),
        record_uuid=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[('state', 'present', ['name', 'record_type', 'content'])],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    state = module.params['state']
    zone_uuid = module.params['zone_uuid']

    if state == 'present':
        name = module.params['name']
        record_type = module.params['record_type']
        content = module.params['content']
        record_uuid = module.params.get('record_uuid')

        existing = find_record(api, zone_uuid, name, record_type, content)

        if existing and not record_uuid:
            desired_ttl = module.params['ttl']
            if existing.get('ttl') == desired_ttl:
                module.exit_json(changed=False, record=existing)
            record_uuid = existing.get('uuid')

        if record_uuid:
            data = {}
            if module.params.get('content'):
                data['content'] = module.params['content']
            if module.params.get('ttl'):
                data['ttl'] = module.params['ttl']
            if module.params.get('priority') is not None:
                data['priority'] = module.params['priority']
            if module.params.get('weight') is not None:
                data['weight'] = module.params['weight']
            if module.params.get('port') is not None:
                data['port'] = module.params['port']
            if module.params.get('comment') is not None:
                data['comment'] = module.params['comment']
            if module.check_mode:
                module.exit_json(changed=True)
            result = api.put('/dns/zones/%s/records/%s' % (zone_uuid, record_uuid), data)
            module.exit_json(changed=True, record=result)

        if module.check_mode:
            module.exit_json(changed=True)

        data = {
            'name': name,
            'record_type': record_type,
            'content': content,
            'ttl': module.params['ttl'],
        }
        if module.params.get('priority') is not None:
            data['priority'] = module.params['priority']
        if module.params.get('weight') is not None:
            data['weight'] = module.params['weight']
        if module.params.get('port') is not None:
            data['port'] = module.params['port']
        if module.params.get('comment') is not None:
            data['comment'] = module.params['comment']

        result = api.post('/dns/zones/%s/records' % zone_uuid, data)
        module.exit_json(changed=True, record=result)

    elif state == 'absent':
        record_uuid = module.params.get('record_uuid')
        if not record_uuid:
            name = module.params.get('name')
            record_type = module.params.get('record_type')
            content = module.params.get('content')
            if name and record_type and content:
                existing = find_record(api, zone_uuid, name, record_type, content)
                if existing:
                    record_uuid = existing.get('uuid')
        if not record_uuid:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/dns/zones/%s/records/%s' % (zone_uuid, record_uuid))
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
