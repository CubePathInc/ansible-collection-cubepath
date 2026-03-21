# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import time

from ansible.module_utils.urls import open_url
from ansible.module_utils.basic import env_fallback
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError


DEFAULT_API_URL = 'https://api.cubepath.com'


def cubepath_argument_spec():
    return dict(
        api_token=dict(
            type='str',
            required=True,
            no_log=True,
            fallback=(env_fallback, ['CUBEPATH_API_TOKEN']),
        ),
        api_url=dict(type='str', default=DEFAULT_API_URL),
        api_timeout=dict(type='int', default=60),
        validate_certs=dict(type='bool', default=True),
    )


class CubePathAPI:
    def __init__(self, module):
        self.module = module
        self.api_token = module.params['api_token']
        self.api_url = module.params['api_url'].rstrip('/')
        self.timeout = module.params.get('api_timeout', 60)
        self.validate_certs = module.params.get('validate_certs', True)
        self.headers = {
            'Authorization': 'Bearer %s' % self.api_token,
            'Content-Type': 'application/json',
            'User-Agent': 'CubePathAnsible/1.1',
            'X-Requested-With': 'XMLHttpRequest',
        }

    def _request(self, method, endpoint, data=None, params=None):
        url = '%s%s' % (self.api_url, endpoint)
        if params:
            query = '&'.join('%s=%s' % (k, v) for k, v in params.items() if v is not None)
            if query:
                url = '%s?%s' % (url, query)

        body = json.dumps(data) if data else None
        retries = 3

        for attempt in range(retries):
            try:
                response = open_url(
                    url,
                    method=method,
                    headers=self.headers,
                    data=body,
                    timeout=self.timeout,
                    validate_certs=self.validate_certs,
                )
                status_code = response.getcode()
                if status_code == 204:
                    return {}
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw)
            except HTTPError as e:
                status = e.code if hasattr(e, 'code') else 0
                if status in (429, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                try:
                    error_body = json.loads(e.read())
                    msg = error_body.get('detail', str(e))
                except Exception:
                    msg = str(e)
                self.module.fail_json(msg='API request failed: %s %s - %s' % (method, url, msg))
            except URLError as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                self.module.fail_json(msg='API connection error: %s' % str(e))
            except Exception as e:
                self.module.fail_json(msg='Unexpected error: %s' % str(e))

    def get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint, data=None, params=None):
        return self._request('POST', endpoint, data, params=params)

    def put(self, endpoint, data=None):
        return self._request('PUT', endpoint, data)

    def patch(self, endpoint, data=None):
        return self._request('PATCH', endpoint, data)

    def delete(self, endpoint, data=None):
        return self._request('DELETE', endpoint, data)
