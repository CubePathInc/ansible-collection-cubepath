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


EVENT_TYPES = ('object.created', 'object.removed', 'object.tagging')


def normalize_events(events):
    """Event types as the API takes them, sorted and without repeats: "created" or
    "object.created" both give object.created. Unknown names raise ValueError."""
    out = set()
    for event in events or []:
        name = str(event).strip().lower()
        full = name if name.startswith('object.') else 'object.' + name
        if full not in EVENT_TYPES:
            raise ValueError("Unknown event type '%s': use created, removed or tagging" % event)
        out.add(full)
    return sorted(out)


def list_event_destinations(api):
    result = api.get('/object-storage/event-destinations')
    return result if isinstance(result, list) else []


def find_event_destination(api, ref):
    """A destination by name, or by UUID when no destination has that name."""
    destinations = list_event_destinations(api)
    for dest in destinations:
        if dest.get('name') == ref:
            return dest
    for dest in destinations:
        if dest.get('uuid') == ref:
            return dest
    return None


def find_bucket_ref(api, ref):
    """A bucket by name, or by UUID when no bucket has that name."""
    buckets = list_buckets(api)
    for bucket in buckets:
        if bucket.get('name') == ref:
            return bucket
    for bucket in buckets:
        if bucket.get('uuid') == ref:
            return bucket
    return None


def list_replications(api, direction='all', bucket_uuid=None):
    params = {'direction': direction, 'bucket_uuid': bucket_uuid}
    result = api.get('/object-storage/replications', params=params)
    return result if isinstance(result, list) else []


def find_outgoing_replication(api, source_bucket_uuid):
    """The replication of a source bucket (a bucket replicates to one destination at most)."""
    for replication in list_replications(api, 'outgoing', source_bucket_uuid):
        if (replication.get('source') or {}).get('bucket_uuid') == source_bucket_uuid:
            return replication
    return None


def replication_tags(tags):
    """Tags as the API takes them, a list of key/value sorted by key, from a dict or a list."""
    if not tags:
        return []
    if isinstance(tags, dict):
        tags = [{'key': k, 'value': v} for k, v in tags.items()]
    return sorted(({'key': str(t.get('key')), 'value': '' if t.get('value') is None else str(t.get('value'))} for t in tags),
                  key=lambda t: t['key'])


def normalize_endpoint(endpoint):
    """An external endpoint as the API stores it: lowercase host, without :443."""
    endpoint = (endpoint or '').strip().lower()
    if endpoint.endswith(':443'):
        endpoint = endpoint[:-4]
    return endpoint


def list_event_rules(api, bucket_uuid):
    result = api.get('/object-storage/buckets/%s/event-rules' % bucket_uuid)
    return result if isinstance(result, list) else []
