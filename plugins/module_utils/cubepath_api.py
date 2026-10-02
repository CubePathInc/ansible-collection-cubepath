# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import time

from ansible.module_utils.urls import open_url
from ansible.module_utils.basic import env_fallback
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.six.moves.urllib.parse import quote, urlencode


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


def _query_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return value


def path_quote(value):
    """Quote a value for a URL path segment. A CIDR keeps its slash, which the API expects literally."""
    return quote(str(value), safe='/:')


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

    def _request(self, method, endpoint, data=None, params=None, raw=False, busy_timeout=0):
        """Call the API and return the decoded answer.

        `busy_timeout` keeps retrying a 409 (the platform is busy with another operation of the
        resource) for up to that many seconds, for operations the API documents as retryable.
        """
        url = '%s%s' % (self.api_url, endpoint)
        if params:
            # A list value is sent as a repeated parameter (tag=a&tag=b).
            pairs = []
            for k, v in params.items():
                if isinstance(v, (list, tuple)):
                    pairs.extend((k, _query_value(item)) for item in v if item is not None)
                elif v is not None:
                    pairs.append((k, _query_value(v)))
            query = urlencode(pairs)
            if query:
                url = '%s?%s' % (url, query)

        # An empty list is a valid body (for example "detach every key"), only None means no body.
        body = json.dumps(data) if data is not None else None
        retries = 3
        attempt = 0
        deadline = time.time() + busy_timeout

        while True:
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
                content = response.read()
                if raw:
                    return content.decode('utf-8') if isinstance(content, bytes) else content
                if not content:
                    return {}
                return json.loads(content)
            except HTTPError as e:
                status = e.code if hasattr(e, 'code') else 0
                if status in (429, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    attempt += 1
                    continue
                if status == 409 and time.time() < deadline:
                    time.sleep(15)
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
                    attempt += 1
                    continue
                self.module.fail_json(msg='API connection error: %s' % str(e))
            except Exception as e:
                self.module.fail_json(msg='Unexpected error: %s' % str(e))

    def get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params)

    def get_raw(self, endpoint, params=None):
        """GET an endpoint that answers plain text (for example a kubeconfig YAML)."""
        return self._request('GET', endpoint, params=params, raw=True)

    def post(self, endpoint, data=None, params=None, busy_timeout=0):
        return self._request('POST', endpoint, data, params=params, busy_timeout=busy_timeout)

    def put(self, endpoint, data=None, params=None):
        return self._request('PUT', endpoint, data, params=params)

    def patch(self, endpoint, data=None):
        return self._request('PATCH', endpoint, data)

    def delete(self, endpoint, data=None, params=None):
        return self._request('DELETE', endpoint, data, params=params)
