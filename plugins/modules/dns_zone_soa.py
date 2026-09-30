#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_zone_soa
short_description: Manage the SOA record of a CubePath DNS zone
description:
    - Set the timers and the hostmaster address of the SOA record of a DNS zone. The serial is managed by
      the platform and increases on every change.
    - Values not given keep their current value.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    zone_uuid:
        description: DNS zone UUID.
        type: str
        required: true
    refresh:
        description: Refresh interval in seconds (300 to 86400).
        type: int
    retry:
        description: Retry interval in seconds (60 to 86400).
        type: int
    expire:
        description: Expire time in seconds (86400 to 2419200).
        type: int
    minimum:
        description: Negative caching TTL in seconds (60 to 86400).
        type: int
    hostmaster:
        description: Email address of the zone administrator, for example C(hostmaster@example.com).
        type: str
'''

EXAMPLES = r'''
- name: Shorter negative caching
  cubepathinc.cloud.dns_zone_soa:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    minimum: 60
    hostmaster: dns@example.com
'''

RETURN = r'''
soa:
    description: SOA settings (C(serial), C(refresh), C(retry), C(expire), C(minimum), C(primary_ns), C(hostmaster)).
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec

FIELDS = ('refresh', 'retry', 'expire', 'minimum', 'hostmaster')


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        zone_uuid=dict(type='str', required=True),
        refresh=dict(type='int'),
        retry=dict(type='int'),
        expire=dict(type='int'),
        minimum=dict(type='int'),
        hostmaster=dict(type='str'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    path = '/dns/zones/%s/soa' % module.params['zone_uuid']

    current = api.get(path)
    update = dict((k, module.params[k]) for k in FIELDS
                  if module.params.get(k) is not None and module.params[k] != current.get(k))
    if not update:
        module.exit_json(changed=False, soa=current)
    if module.check_mode:
        module.exit_json(changed=True, soa=dict(current, **update))
    module.exit_json(changed=True, soa=api.put(path, update))


if __name__ == '__main__':
    main()
