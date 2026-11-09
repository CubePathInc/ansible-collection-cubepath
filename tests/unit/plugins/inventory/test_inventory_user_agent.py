# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import re
from unittest import mock

from ansible_collections.cubepathinc.cloud.plugins.inventory import cubepath


def test_inventory_requests_send_the_collection_user_agent():
    plugin = cubepath.InventoryModule()
    options = {'api_token': 't', 'api_url': 'https://api.example.test'}
    response = mock.Mock()
    response.read.return_value = b'[]'
    with mock.patch.object(cubepath.BaseInventoryPlugin, 'parse'), \
            mock.patch.object(plugin, '_read_config_data'), \
            mock.patch.object(plugin, 'get_option', side_effect=lambda name: options.get(name)), \
            mock.patch.object(cubepath, 'open_url', return_value=response) as open_url:
        plugin.parse(mock.Mock(), mock.Mock(), 'x.cubepath.yml')
    headers = open_url.call_args.kwargs['headers']
    galaxy = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'galaxy.yml')
    with open(galaxy) as f:
        version = re.search(r'^version:\s*([0-9][^\s#]*)\s*$', f.read(), re.M).group(1)
    assert headers['User-Agent'] == 'CubePathAnsible/%s' % version
