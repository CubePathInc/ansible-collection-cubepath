# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import wait_for  # noqa: F401 pylint: disable=unused-import


def tag_filter(tags):
    """Turn a tags dict into the API's repeated tag filter: key=value, or just key for a None value."""
    if not tags:
        return None
    return ['%s' % k if v is None else '%s=%s' % (k, v) for k, v in sorted(tags.items())]


def desired_tags(current, tags, purge):
    """The tag set to send: tags alone with purge, otherwise merged over the current ones."""
    wanted = dict((str(k), '' if v is None else str(v)) for k, v in (tags or {}).items())
    if purge:
        return wanted
    merged = dict(current or {})
    merged.update(wanted)
    return merged


def lock_retention(rule):
    """A default retention as the API takes it ({mode, days} or {mode, years}), or None for no rule."""
    if not rule or not rule.get('mode'):
        return None
    if rule.get('days') is not None:
        return {'mode': rule['mode'], 'days': int(rule['days'])}
    if rule.get('years') is not None:
        return {'mode': rule['mode'], 'years': int(rule['years'])}
    return None


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
