# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type


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
