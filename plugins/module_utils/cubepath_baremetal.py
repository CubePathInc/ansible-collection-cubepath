# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""References to a baremetal server: its uuid, which is also the id the API returns."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re

_UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def normalize_baremetal_ref(value):
    """Return the uuid in lower case, or None when the value is not a uuid (a server number included)."""
    if not isinstance(value, str):
        return None
    text = value.lower()
    if _UUID.match(text):
        return text
    return None


def baremetal_ref_param(module, name='baremetal_id'):
    """Validate the module parameter before any request. Return the uuid in lower case, or None when unset."""
    value = module.params.get(name)
    if value is None:
        return None
    ref = normalize_baremetal_ref(value)
    if ref is None:
        module.fail_json(msg='%s must be the baremetal server uuid (baremetal reference must be a uuid), got %r'
                         % (name, value))
    return ref


def baremetal_target_param(module, type_name, target_name):
    """The target parameter, validated as a uuid when the type parameter is baremetal.

    The module parameter is replaced by the lower-cased uuid, so later comparisons with what the API returns
    match. Targets of other types are left as given.
    """
    if module.params.get(type_name) != 'baremetal':
        return module.params.get(target_name)
    ref = baremetal_ref_param(module, target_name)
    module.params[target_name] = ref
    return ref


def baremetal_matches(server, ref):
    """True when a server of a listing (/projects/) is the one the uuid names."""
    server_id = server.get('id')
    return isinstance(server_id, str) and server_id.lower() == ref
