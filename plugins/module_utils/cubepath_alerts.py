# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list

# The trailing slashes matter: without them /triggers/notificators is read as an alert id.
ALERTS = '/triggers/'
CHANNELS = '/triggers/notificators/'


def list_channels(api):
    return as_list(api.get(CHANNELS))


def find_channel(api, ref):
    for ch in list_channels(api):
        if ref in (ch.get('id'), ch.get('name')):
            return ch
    return None


def list_alerts(api, project_id=None, status=None):
    return as_list(api.get(ALERTS, params={'project_id': project_id, 'status': status}))


def find_alert(api, ref):
    for alert in list_alerts(api):
        if ref in (alert.get('id'), alert.get('name')):
            return alert
    return None
