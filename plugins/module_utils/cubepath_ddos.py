# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def normalize_network(value):
    """CIDR form the API stores entries in: a bare IP becomes /32 (IPv4) or /128 (IPv6)."""
    value = value.strip().lower()
    if '/' in value:
        return value
    return '%s/%s' % (value, 128 if ':' in value else 32)


def list_prefix_lists(api):
    return as_list(api.get('/ddos-mitigation/prefix-lists'), 'prefix_lists')


def find_prefix_list(api, ref, own_only=False):
    for pl in list_prefix_lists(api):
        if own_only and pl.get('is_global'):
            continue
        if ref in (pl.get('uuid'), pl.get('name')):
            return pl
    return None
