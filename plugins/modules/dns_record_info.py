#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_record_info
short_description: List DNS records on CubePath Cloud
description:
    - Retrieve DNS records from a zone on CubePath Cloud.
version_added: "1.1.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    zone_uuid:
        description: DNS zone UUID.
        type: str
        required: true
    record_type:
        description: Filter by record type.
        type: str
    name:
        description: Filter by record name.
        type: str
'''

EXAMPLES = r'''
- name: List all records in zone
  cubepathinc.cloud.dns_record_info:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
  register: records
'''

RETURN = r'''
records:
    description: List of DNS records.
    type: list
    returned: always
    elements: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        zone_uuid=dict(type='str', required=True),
        record_type=dict(type='str'),
        name=dict(type='str'),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    params = {}
    if module.params.get('record_type'):
        params['record_type'] = module.params['record_type'].upper()

    records = api.get('/dns/zones/%s/records' % module.params['zone_uuid'], params=params or None)
    if not isinstance(records, list):
        records = []

    name = module.params.get('name')
    if name:
        records = [r for r in records if r.get('name') == name]

    module.exit_json(changed=False, records=records)


if __name__ == '__main__':
    main()
