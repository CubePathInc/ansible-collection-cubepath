# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.cubepathinc.cloud.plugins.modules import floating_ip


class ExitJson(Exception):
    pass


class FailJson(Exception):
    pass


def _exit_json(self, **kwargs):
    raise ExitJson(kwargs)


def _fail_json(self, **kwargs):
    raise FailJson(kwargs)


class FakeAPI(object):
    calls = []

    def __init__(self, module):
        pass

    def post(self, endpoint, data=None, params=None):
        FakeAPI.calls.append(('POST', endpoint, data, params))
        return {'ip_address': '203.0.113.7'}


@pytest.fixture(autouse=True)
def patched(monkeypatch):
    FakeAPI.calls = []
    monkeypatch.setattr(basic.AnsibleModule, 'exit_json', _exit_json)
    monkeypatch.setattr(basic.AnsibleModule, 'fail_json', _fail_json)
    monkeypatch.setattr(floating_ip, 'CubePathAPI', FakeAPI)


def run(args):
    args = dict(args, api_token='t')
    basic._ANSIBLE_ARGS = to_bytes(json.dumps({'ANSIBLE_MODULE_ARGS': args}))
    with pytest.raises((ExitJson, FailJson)) as exc:
        floating_ip.main()
    return exc


def test_acquire_sends_query_params():
    run({'state': 'acquired', 'location': 'eu-bcn-1'})
    assert FakeAPI.calls == [('POST', '/floating_ips/acquire', None, {'ip_type': 'IPv4', 'location_name': 'eu-bcn-1'})]


def test_release_puts_the_address_in_the_path():
    run({'state': 'released', 'address': '203.0.113.7'})
    assert FakeAPI.calls == [('POST', '/floating_ips/release/203.0.113.7', None, None)]


def test_assign_vps_sends_the_address_as_query():
    run({'state': 'assigned', 'address': '203.0.113.7', 'vps_id': 42})
    assert FakeAPI.calls == [('POST', '/floating_ips/assign/vps/42', None, {'address': '203.0.113.7'})]


def test_assign_baremetal():
    run({'state': 'assigned', 'address': '203.0.113.7', 'baremetal_id': 9})
    assert FakeAPI.calls == [('POST', '/floating_ips/assign/baremetal/9', None, {'address': '203.0.113.7'})]


def test_assign_needs_a_target():
    exc = run({'state': 'assigned', 'address': '203.0.113.7'})
    assert exc.type is FailJson
    assert FakeAPI.calls == []


def test_unassign_by_address():
    run({'state': 'unassigned', 'address': '203.0.113.7'})
    assert FakeAPI.calls == [('POST', '/floating_ips/unassign/203.0.113.7', None, None)]
