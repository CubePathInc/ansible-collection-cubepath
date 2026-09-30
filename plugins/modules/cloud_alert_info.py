#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cloud_alert_info
short_description: Get Cloud Alerts information from CubePath Cloud
description:
    - List Cloud Alerts and notification channels, or read one alert with its actions and the log of
      the times it fired and recovered.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    alert:
        description: Name or ID of one alert, returned in detail as RV(alert) with its RV(history).
        type: str
    project_id:
        description: Only alerts of this project.
        type: int
    status:
        description: Only alerts in this status.
        type: str
        choices: [enabled, disabled, triggered, resolved]
    history_limit:
        description: Number of history events returned with I(alert) (1 to 200).
        type: int
        default: 50
'''

EXAMPLES = r'''
- name: List alerts and channels
  cubepathinc.cloud.cloud_alert_info:
    api_token: "{{ cubepath_token }}"
  register: alerts

- name: History of one alert
  cubepathinc.cloud.cloud_alert_info:
    api_token: "{{ cubepath_token }}"
    alert: web-01 cpu
  register: web_cpu
'''

RETURN = r'''
alerts:
    description: Alerts of the organization.
    type: list
    elements: dict
    returned: always
channels:
    description: Notification channels, with webhook URLs masked.
    type: list
    elements: dict
    returned: always
alert:
    description: Detail of the alert given in I(alert), with its actions.
    type: dict
    returned: when I(alert) is set
history:
    description: Events of the alert given in I(alert), newest first.
    type: list
    elements: dict
    returned: when I(alert) is set
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_alerts import ALERTS, find_alert, list_alerts, list_channels


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        alert=dict(type='str'),
        project_id=dict(type='int'),
        status=dict(type='str', choices=['enabled', 'disabled', 'triggered', 'resolved']),
        history_limit=dict(type='int', default=50),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    result = {
        'changed': False,
        'alerts': list_alerts(api, module.params.get('project_id'), module.params.get('status')),
        'channels': list_channels(api),
    }
    ref = module.params.get('alert')
    if ref:
        match = find_alert(api, ref)
        if match is None:
            module.fail_json(msg='Alert %s not found' % ref)
        result['alert'] = api.get('%s%s' % (ALERTS, match['id']))
        result['history'] = api.get('%s%s/history' % (ALERTS, match['id']), params={'limit': module.params['history_limit']})

    module.exit_json(**result)


if __name__ == '__main__':
    main()
