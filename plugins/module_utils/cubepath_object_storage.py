# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import wait_for  # noqa: F401 pylint: disable=unused-import


def list_buckets(api, project_id=None):
    params = {'project_id': project_id} if project_id is not None else None
    result = api.get('/object-storage/buckets', params=params)
    return result if isinstance(result, list) else []


def find_bucket(api, name):
    """Bucket names are unique across every customer, so a name identifies one bucket."""
    for bucket in list_buckets(api):
        if bucket.get('name') == name:
            return bucket
    return None


def list_keys(api, project_id=None):
    params = {'project_id': project_id} if project_id is not None else None
    result = api.get('/object-storage/keys', params=params)
    return result if isinstance(result, list) else []


def find_key(api, name, project_id=None, tier=None):
    for key in list_keys(api, project_id):
        if key.get('name') != name:
            continue
        if tier and tier not in ((key.get('tier') or {}).get('slug'), (key.get('tier') or {}).get('uuid')):
            continue
        return key
    return None
