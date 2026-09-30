#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: dns_record_health_check
short_description: Manage health checks of CubePath DNS records
description:
    - Create, update or delete the health check of a DNS record. A record whose check fails is left out of
      the answers while other records of the same name are healthy.
    - An enabled health check is billed monthly.
    - Settings not given keep their current value, or the API default on create.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the health check.
        type: str
        default: present
        choices: [present, absent]
    zone_uuid:
        description: DNS zone UUID.
        type: str
        required: true
    record_uuid:
        description: UUID of the record the check is attached to.
        type: str
        required: true
    name:
        description: Friendly name of the check. Required to create it.
        type: str
    check_type:
        description: Probe type. Required to create the check.
        type: str
        choices: [http, https, tcp, ping]
    target:
        description: Hostname or IP to probe. Defaults to the record's value.
        type: str
    port:
        description: Port to probe. Required for C(tcp).
        type: int
    path:
        description: Path requested by C(http) and C(https) checks, starting with C(/).
        type: str
    expected_status:
        description: HTTP status expected by C(http) and C(https) checks (200 by default).
        type: int
    interval_secs:
        description: Seconds between probes (10 to 3600, 60 by default).
        type: int
    timeout_secs:
        description: Probe timeout in seconds, lower than I(interval_secs) (5 by default).
        type: int
    healthy_threshold:
        description: Consecutive successes before the record is healthy (1 to 10, 2 by default).
        type: int
    unhealthy_threshold:
        description: Consecutive failures before the record is unhealthy (1 to 10, 3 by default).
        type: int
    enabled:
        description: Whether the check runs (and is billed).
        type: bool
'''

EXAMPLES = r'''
- name: Take the record out of rotation when the site is down
  cubepathinc.cloud.dns_record_health_check:
    api_token: "{{ cubepath_token }}"
    zone_uuid: "abc-123"
    record_uuid: "def-456"
    name: web-01 https
    check_type: https
    path: /healthz
'''

RETURN = r'''
health_check:
    description: Health check details, with C(last_status) and C(last_check_at).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list

FIELDS = ('name', 'check_type', 'target', 'port', 'path', 'expected_status', 'interval_secs', 'timeout_secs',
          'healthy_threshold', 'unhealthy_threshold', 'enabled')


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        zone_uuid=dict(type='str', required=True),
        record_uuid=dict(type='str', required=True),
        name=dict(type='str'),
        check_type=dict(type='str', choices=['http', 'https', 'tcp', 'ping']),
        target=dict(type='str'),
        port=dict(type='int'),
        path=dict(type='str'),
        expected_status=dict(type='int'),
        interval_secs=dict(type='int'),
        timeout_secs=dict(type='int'),
        healthy_threshold=dict(type='int'),
        unhealthy_threshold=dict(type='int'),
        enabled=dict(type='bool'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)
    p = module.params
    path = '/dns/zones/%s/records/%s/health-check' % (p['zone_uuid'], p['record_uuid'])

    checks = as_list(api.get('/dns/zones/%s/health-checks' % p['zone_uuid']))
    current = next((c for c in checks if c.get('record_uuid') == p['record_uuid']), None)

    if p['state'] == 'absent':
        if current is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete(path)
        module.exit_json(changed=True)

    if current is None and (not p.get('name') or not p.get('check_type')):
        module.fail_json(msg='name and check_type are required to create a health check')
    body = dict((k, (current or {}).get(k)) for k in FIELDS)
    for k in FIELDS:
        if p.get(k) is not None:
            body[k] = p[k]
    if current is not None and all(body[k] == current.get(k) for k in FIELDS):
        module.exit_json(changed=False, health_check=current)
    if module.check_mode:
        module.exit_json(changed=True, health_check=current)
    body = dict((k, v) for k, v in body.items() if v is not None)
    module.exit_json(changed=True, health_check=api.put(path, body))


if __name__ == '__main__':
    main()
