# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""References to a baremetal server: the number or the uuid, as the API accepts both on its routes."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re

_NUMBER = re.compile(r'^[0-9]+$')
_UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def normalize_baremetal_ref(value):
    """Return the reference as route text (digits as given, a uuid in lower case) or None when invalid."""
    if value is None:
        return None
    text = str(value).strip()
    if _NUMBER.match(text):
        return text
    text = text.lower()
    if _UUID.match(text):
        return text
    return None


def baremetal_ref_param(module, name='baremetal_id'):
    """Validate the module parameter before any request. Return the reference text, or None when unset."""
    value = module.params.get(name)
    if value is None:
        return None
    ref = normalize_baremetal_ref(value)
    if ref is None:
        module.fail_json(msg='%s must be the baremetal number or its uuid, got %r' % (name, value))
    return ref


def baremetal_matches(server, ref):
    """True when a server of a listing (/projects/) is the one the reference names."""
    if str(server.get('id')) == ref:
        return True
    uuid = server.get('uuid')
    return bool(uuid) and str(uuid).lower() == ref
