#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: cloud_alert_channel
short_description: Manage Cloud Alerts notification channels on CubePath Cloud
description:
    - Create, update or delete the Slack, Discord or email channels that Cloud Alerts notify
      (see M(cubepathinc.cloud.cloud_alert)).
    - The module finds an existing channel by I(name). The type of a channel cannot be changed.
    - The API only shows the host and the last 4 characters of a webhook URL, so a new URL with the same
      host and ending is not detected as a change.
    - A channel that an alert still uses cannot be deleted.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the channel.
        type: str
        default: present
        choices: [present, absent]
    name:
        description: Name of the channel (1 to 64 characters), unique in the organization.
        type: str
        required: true
    type:
        description:
            - Channel type. Required to create the channel.
            - C(email) notifies the organization's alert recipients and takes no I(webhook_url).
        type: str
        choices: [slack, discord, email]
    webhook_url:
        description: Incoming webhook URL (https) of a C(slack) or C(discord) channel.
        type: str
    enabled:
        description: Whether the channel sends notifications.
        type: bool
'''

EXAMPLES = r'''
- name: Slack channel for alerts
  cubepathinc.cloud.cloud_alert_channel:
    api_token: "{{ cubepath_token }}"
    name: ops-slack
    type: slack
    webhook_url: "{{ slack_webhook_url }}"
'''

RETURN = r'''
channel:
    description: Channel details (C(id), C(name), C(type), C(config), C(enabled)).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six.moves.urllib.parse import urlsplit
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_alerts import CHANNELS, find_channel


def masked(url):
    """The form the API shows a webhook URL in: scheme://host/***last4."""
    parts = urlsplit(url)
    return '%s://%s/***%s' % (parts.scheme, parts.netloc, url[-4:])


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        name=dict(type='str', required=True),
        type=dict(type='str', choices=['slack', 'discord', 'email']),
        webhook_url=dict(type='str', no_log=True),
        enabled=dict(type='bool'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params
    existing = find_channel(api, p['name'])

    if p['state'] == 'absent':
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('%s%s' % (CHANNELS, existing['id']))
        module.exit_json(changed=True)

    if existing is None:
        if not p.get('type'):
            module.fail_json(msg='type is required to create a channel')
        if p['type'] != 'email' and not p.get('webhook_url'):
            module.fail_json(msg='webhook_url is required for a %s channel' % p['type'])
        if module.check_mode:
            module.exit_json(changed=True)
        data = {'name': p['name'], 'type': p['type'], 'config': {}}
        if p['type'] != 'email':
            data['config'] = {'webhook_url': p['webhook_url']}
        if p.get('enabled') is not None:
            data['enabled'] = p['enabled']
        api.post(CHANNELS, data)
        module.exit_json(changed=True, channel=find_channel(api, p['name']))

    if p.get('type') and p['type'] != existing.get('type'):
        module.fail_json(msg='The type of channel %s is %s and cannot be changed' % (p['name'], existing.get('type')))
    update = {}
    if p.get('enabled') is not None and p['enabled'] != existing.get('enabled'):
        update['enabled'] = p['enabled']
    url = p.get('webhook_url')
    if url and existing.get('type') != 'email' and masked(url) != (existing.get('config') or {}).get('webhook_url'):
        update['config'] = {'webhook_url': url}
    if not update:
        module.exit_json(changed=False, channel=existing)
    if module.check_mode:
        module.exit_json(changed=True, channel=existing)
    api.put('%s%s' % (CHANNELS, existing['id']), update)
    module.exit_json(changed=True, channel=find_channel(api, p['name']))


if __name__ == '__main__':
    main()
