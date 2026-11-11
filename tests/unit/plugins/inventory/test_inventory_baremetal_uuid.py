# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest import mock

from ansible_collections.cubepathinc.cloud.plugins.inventory import cubepath


def _variables(data, host_type='baremetal'):
    plugin = cubepath.InventoryModule()
    plugin.inventory = mock.Mock()
    with mock.patch.object(plugin, 'get_option', return_value=False):
        plugin._add_host(data, host_type, 'proj')
    return {c.args[1]: c.args[2] for c in plugin.inventory.set_variable.call_args_list}


def test_baremetal_exposes_uuid_and_keeps_the_id():
    uuid = '6f1c2a9e-3b7d-4e58-9a10-5c2d8e4f7b31'
    variables = _variables({'id': 7, 'uuid': uuid, 'hostname': 'bm1', 'main_ip': '192.0.2.1'})
    assert variables['cubepath_id'] == 7
    assert variables['cubepath_uuid'] == uuid


def test_baremetal_without_uuid_gets_an_empty_one():
    variables = _variables({'id': 7, 'hostname': 'bm1', 'main_ip': '192.0.2.1'})
    assert variables['cubepath_id'] == 7
    assert variables['cubepath_uuid'] == ''


def test_vps_has_no_uuid_variable():
    variables = _variables({'id': 3, 'name': 'v1', 'main_ip': '192.0.2.2'}, 'vps')
    assert 'cubepath_uuid' not in variables
