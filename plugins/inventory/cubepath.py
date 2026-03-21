# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
name: cubepath
short_description: CubePath Cloud dynamic inventory
description:
    - Dynamically generate inventory from CubePath Cloud infrastructure.
    - Groups hosts by project, location, type (vps/baremetal), and status.
version_added: "1.1.0"
author: CubePath (@cubepath)
options:
    plugin:
        description: Token that ensures this is a source file for the plugin.
        required: true
        choices: ['cubepathinc.cloud.cubepath']
    api_token:
        description: CubePath API token.
        required: true
        env:
            - name: CUBEPATH_API_TOKEN
    api_url:
        description: CubePath API URL.
        default: https://api.cubepath.com
        env:
            - name: CUBEPATH_API_URL
    group_by_project:
        description: Create groups based on project name.
        type: bool
        default: true
    group_by_location:
        description: Create groups based on location.
        type: bool
        default: true
    group_by_type:
        description: Create groups for vps and baremetal.
        type: bool
        default: true
    group_by_status:
        description: Create groups based on status.
        type: bool
        default: false
'''

EXAMPLES = r'''
# cubepath.yml
plugin: cubepathinc.cloud.cubepath
api_token: "{{ lookup('env', 'CUBEPATH_API_TOKEN') }}"
group_by_project: true
group_by_location: true
group_by_type: true
'''

import json

from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError


class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'cubepathinc.cloud.cubepath'

    def verify_file(self, path):
        if super().verify_file(path):
            return path.endswith(('.cubepath.yml', '.cubepath.yaml'))
        return False

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)
        self._read_config_data(path)

        api_token = self.get_option('api_token')
        api_url = self.get_option('api_url').rstrip('/')

        headers = {
            'Authorization': 'Bearer %s' % api_token,
            'Content-Type': 'application/json',
            'User-Agent': 'CubePathAnsible/1.1',
            'X-Requested-With': 'XMLHttpRequest',
        }

        try:
            response = open_url('%s/projects/' % api_url, headers=headers, timeout=60)
            projects = json.loads(response.read())
        except (HTTPError, URLError) as e:
            raise Exception('Failed to fetch CubePath inventory: %s' % str(e))

        if not isinstance(projects, list):
            return

        for proj_data in projects:
            project = proj_data.get('project', {})
            project_name = self._sanitize(project.get('name', 'unknown'))

            if self.get_option('group_by_project'):
                self.inventory.add_group('project_%s' % project_name)

            for vps in proj_data.get('vps', []):
                self._add_host(vps, 'vps', project_name)

            for bm in proj_data.get('baremetals', []):
                self._add_host(bm, 'baremetal', project_name)

    def _add_host(self, data, host_type, project_name):
        if host_type == 'vps':
            hostname = data.get('name', '')
            ip = data.get('main_ip', '')
        else:
            hostname = data.get('hostname', '')
            ip = data.get('main_ip', data.get('primary_ip', ''))

        if not hostname or not ip:
            return

        self.inventory.add_host(hostname)
        self.inventory.set_variable(hostname, 'ansible_host', ip)
        self.inventory.set_variable(hostname, 'cubepath_id', data.get('id'))
        self.inventory.set_variable(hostname, 'cubepath_type', host_type)
        self.inventory.set_variable(hostname, 'cubepath_status', data.get('status', ''))
        self.inventory.set_variable(hostname, 'cubepath_location', data.get('location_name', ''))
        self.inventory.set_variable(hostname, 'cubepath_project', project_name)

        if data.get('ipv6'):
            self.inventory.set_variable(hostname, 'cubepath_ipv6', data['ipv6'])
        if data.get('plan_name'):
            self.inventory.set_variable(hostname, 'cubepath_plan', data['plan_name'])
        if data.get('label'):
            self.inventory.set_variable(hostname, 'cubepath_label', data['label'])

        if self.get_option('group_by_project'):
            self.inventory.add_child('project_%s' % project_name, hostname)

        if self.get_option('group_by_type'):
            self.inventory.add_group(host_type)
            self.inventory.add_child(host_type, hostname)

        location = self._sanitize(data.get('location_name', ''))
        if location and self.get_option('group_by_location'):
            group = 'location_%s' % location
            self.inventory.add_group(group)
            self.inventory.add_child(group, hostname)

        status = self._sanitize(data.get('status', ''))
        if status and self.get_option('group_by_status'):
            group = 'status_%s' % status
            self.inventory.add_group(group)
            self.inventory.add_child(group, hostname)

    @staticmethod
    def _sanitize(name):
        return name.lower().replace('-', '_').replace(' ', '_').replace('.', '_')
