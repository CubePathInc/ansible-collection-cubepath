# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest import mock

from ansible_collections.cubepathinc.cloud.plugins.inventory import cubepath
from ansible_collections.cubepathinc.cloud.plugins.module_utils import cubepath_api


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
    assert headers['User-Agent'] == cubepath_api.USER_AGENT
    assert headers['User-Agent'].startswith('CubePathAnsible/1.')
