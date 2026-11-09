# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import re

from ansible_collections.cubepathinc.cloud.plugins.module_utils import cubepath_api


GALAXY_YML = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'galaxy.yml')


def _galaxy_version():
    with open(GALAXY_YML) as f:
        match = re.search(r'^version:\s*([0-9][^\s#]*)\s*$', f.read(), re.M)
    assert match, 'no version in galaxy.yml'
    return match.group(1)


def test_collection_version_matches_galaxy():
    assert cubepath_api.COLLECTION_VERSION == _galaxy_version()


def test_user_agent_carries_the_collection_version():
    assert cubepath_api.USER_AGENT == 'CubePathAnsible/%s' % _galaxy_version()


class _Module(object):
    params = {'api_token': 't', 'api_url': 'https://api.example.test'}


def test_api_client_sends_the_user_agent():
    api = cubepath_api.CubePathAPI(_Module())
    assert api.headers['User-Agent'] == 'CubePathAnsible/%s' % _galaxy_version()
