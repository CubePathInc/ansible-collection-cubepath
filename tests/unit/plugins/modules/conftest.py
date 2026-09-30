# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

import pytest

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes

from ansible_collections.cubepathinc.cloud.plugins.module_utils import cubepath_common


class ExitJson(Exception):
    pass


class FailJson(Exception):
    pass


def _exit_json(self, **kwargs):
    raise ExitJson(kwargs)


def _fail_json(self, **kwargs):
    raise FailJson(kwargs)


class Router(object):
    """Stands in for CubePathAPI: answers from a route table and records every call.

    A route value is the response, a tuple of responses served one per call (the last one repeats,
    for a resource that changes between reads), or a callable taking (data, params).
    """

    def __init__(self, routes):
        self.routes = dict(routes)
        self.calls = []

    def _answer(self, method, endpoint, data=None, params=None):
        self.calls.append((method, endpoint, data, params))
        key = (method, endpoint)
        if key not in self.routes:
            return {}
        value = self.routes[key]
        if callable(value):
            return value(data, params)
        if isinstance(value, tuple):
            if len(value) > 1:
                self.routes[key] = value[1:]
            return value[0]
        return value

    def get(self, endpoint, params=None):
        return self._answer('GET', endpoint, params=params)

    def get_raw(self, endpoint, params=None):
        return self._answer('GET', endpoint, params=params)

    def post(self, endpoint, data=None, params=None, busy_timeout=0):
        return self._answer('POST', endpoint, data, params)

    def put(self, endpoint, data=None, params=None):
        return self._answer('PUT', endpoint, data, params)

    def patch(self, endpoint, data=None):
        return self._answer('PATCH', endpoint, data)

    def delete(self, endpoint, data=None, params=None):
        return self._answer('DELETE', endpoint, data, params)

    def writes(self):
        return [c for c in self.calls if c[0] != 'GET']


@pytest.fixture
def run(monkeypatch):
    monkeypatch.setattr(basic.AnsibleModule, 'exit_json', _exit_json)
    monkeypatch.setattr(basic.AnsibleModule, 'fail_json', _fail_json)
    monkeypatch.setattr(cubepath_common.time, 'sleep', lambda s: None)

    def _run(module, args, routes):
        router = Router(routes)
        monkeypatch.setattr(module, 'CubePathAPI', lambda m: router)
        args = dict(args, api_token='t')
        basic._ANSIBLE_ARGS = to_bytes(json.dumps({'ANSIBLE_MODULE_ARGS': args}))
        try:
            module.main()
        except ExitJson as e:
            return 'exit', e.args[0], router
        except FailJson as e:
            return 'fail', e.args[0], router
        raise AssertionError('module did not exit')

    return _run
