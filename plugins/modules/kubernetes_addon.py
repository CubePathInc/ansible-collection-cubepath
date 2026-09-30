#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: kubernetes_addon
short_description: Install or uninstall addons on CubePath Kubernetes clusters
description:
    - Install an addon of the CubePath catalog (a Helm chart such as an ingress controller or cert-manager)
      on a managed Kubernetes cluster, or uninstall it.
    - An addon that failed to install is installed again. The Helm values of an installed addon are not
      changed; uninstall and install it again to change them.
    - By default the module waits until the addon is C(active), or gone when I(state=absent).
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: Desired state of the addon.
        type: str
        default: present
        choices: [present, absent]
    cluster:
        description: Name or UUID of the cluster.
        type: str
        required: true
    slug:
        description: Catalog slug of the addon, for example C(ingress-nginx). List them with M(cubepathinc.cloud.kubernetes_info).
        type: str
        required: true
    custom_values:
        description: Helm value overrides used when installing (up to 10 KB).
        type: dict
    wait:
        description: Wait until the addon is C(active), or uninstalled when I(state=absent).
        type: bool
        default: true
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 900
'''

EXAMPLES = r'''
- name: Install the NGINX ingress controller with 2 replicas
  cubepathinc.cloud.kubernetes_addon:
    api_token: "{{ cubepath_token }}"
    cluster: prod
    slug: ingress-nginx
    custom_values:
      controller:
        replicaCount: 2
'''

RETURN = r'''
addon:
    description: Installed addon (C(status), C(installed_version), C(custom_values), C(addon) catalog entry...).
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list, wait_for
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_kubernetes import require_cluster


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        cluster=dict(type='str', required=True),
        slug=dict(type='str', required=True),
        custom_values=dict(type='dict'),
        wait=dict(type='bool', default=True),
        wait_timeout=dict(type='int', default=900),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    p = module.params
    cluster = require_cluster(module, api, p['cluster'])
    base = '/kubernetes/%s/addons' % cluster['uuid']

    def fetch():
        return next((a for a in as_list(api.get(base)) if (a.get('addon') or {}).get('slug') == p['slug']), None)

    def wait(done):
        return wait_for(module, fetch, done, p['wait_timeout'], interval=10)

    installed = fetch()

    if p['state'] == 'absent':
        if installed is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        if installed.get('status') != 'uninstalling':
            api.delete('%s/%s' % (base, installed['addon']['uuid']))
        if p['wait']:
            wait(lambda a: a is None)
        module.exit_json(changed=True)

    changed = False
    if installed is None or installed.get('status') == 'failed':
        if module.check_mode:
            module.exit_json(changed=True)
        body = {'custom_values': p['custom_values']} if p.get('custom_values') is not None else None
        api.post('%s/%s/install' % (base, p['slug']), body)
        changed = True
        installed = fetch()
    if p['wait'] and installed and installed.get('status') in ('pending', 'installing'):
        installed = wait(lambda a: a is not None and a.get('status') not in ('pending', 'installing'))
        if installed.get('status') == 'failed':
            module.fail_json(msg='Addon installation failed: %s' % (installed.get('error_message') or 'unknown error'), addon=installed)
    module.exit_json(changed=changed, addon=installed)


if __name__ == '__main__':
    main()
