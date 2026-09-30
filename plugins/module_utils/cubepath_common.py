# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import time


def get_projects(api):
    result = api.get('/projects/')
    return result if isinstance(result, list) else []


def find_resource_in_projects(api, resource_key, match_field, match_value, project_id=None):
    for proj in get_projects(api):
        p = proj.get('project', {})
        if project_id is not None and p.get('id') != project_id:
            continue
        for item in proj.get(resource_key, []):
            if item.get(match_field) == match_value:
                return item
    return None


def collect_resources_from_projects(api, resource_key, filters=None):
    results = []
    for proj in get_projects(api):
        p = proj.get('project', {})
        for item in proj.get(resource_key, []):
            item['project_id'] = p.get('id')
            item['project_name'] = p.get('name')
            results.append(item)

    if filters:
        for field, value in filters.items():
            if value is not None:
                results = [r for r in results if r.get(field) == value]
    return results


def find_resource_with_project(api, resource_key, match_field, match_value):
    """Like find_resource_in_projects, but also returns the id of the project that holds the item."""
    for proj in get_projects(api):
        p = proj.get('project', {})
        for item in proj.get(resource_key, []):
            if item.get(match_field) == match_value:
                return item, p.get('id')
    return None, None


def as_list(result, key=None):
    """Return a list from an API answer that is either a bare list or an object wrapping one under `key`."""
    if isinstance(result, list):
        return result
    if key and isinstance(result, dict) and isinstance(result.get(key), list):
        return result[key]
    return []


def wait_for(module, fetch, done, timeout, interval=5):
    """Poll `fetch()` until `done(item)` is true. `fetch` returns None once the resource is gone."""
    deadline = time.time() + timeout
    item = fetch()
    while not done(item):
        if time.time() >= deadline:
            module.fail_json(msg='Timed out after %ss waiting for the resource' % timeout, resource=item)
        if item and item.get('status') in ('error', 'failed'):
            module.fail_json(msg='The resource ended in error: %s' % (item.get('error_message') or item.get('error') or 'unknown error'),
                             resource=item)
        time.sleep(interval)
        item = fetch()
    return item
