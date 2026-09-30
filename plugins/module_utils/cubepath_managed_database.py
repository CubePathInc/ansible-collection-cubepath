# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def list_instances(api):
    return as_list(api.get('/managed-databases/'))


def find_instance(api, ref):
    """Find a managed database by name or UUID. Names are unique within the organization."""
    for md in list_instances(api):
        if ref in (md.get('name'), md.get('uuid')):
            return md
    return None


def require_instance(module, api, ref):
    md = find_instance(api, ref)
    if md is None:
        module.fail_json(msg='Managed database %s not found' % ref)
    return md


def list_plans(api, engine=None):
    params = {'engine': engine} if engine else None
    return as_list(api.get('/managed-database-plans/', params=params))


def resolve_plan(module, api, ref, engine=None, location=None):
    """Return the plan dict for a plan name or UUID. A name can exist in several locations."""
    matches = []
    for loc in list_plans(api, engine):
        if location and loc.get('location_name') != location:
            continue
        for plan in loc.get('plans', []):
            if ref in (plan.get('uuid'), plan.get('name')):
                matches.append(dict(plan, location_name=loc.get('location_name')))
    if not matches:
        module.fail_json(msg='Managed database plan %s not found%s' % (ref, ' in %s' % location if location else ''))
    if len({m['uuid'] for m in matches}) > 1:
        module.fail_json(msg='Plan %s exists in several locations (%s); set location' % (
            ref, ', '.join(sorted(m['location_name'] for m in matches))))
    return matches[0]
