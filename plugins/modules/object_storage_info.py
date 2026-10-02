#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_info
short_description: Get Object Storage information from CubePath Cloud
description:
    - List storage tiers, buckets and access keys, get one bucket in detail, or read the
      month's usage and cost.
    - Access key secrets are never returned.
version_added: "1.4.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    gather:
        description: What to return.
        type: list
        elements: str
        default: [tiers, buckets, access_keys]
        choices: [tiers, buckets, access_keys, usage]
    bucket:
        description: Name or UUID of a bucket to return in detail as RV(bucket).
        type: str
    project_id:
        description: Only buckets, keys and usage of this project.
        type: int
    tier:
        description: Only buckets, keys and usage of this tier (slug or UUID).
        type: str
    period:
        description: Month of the usage report (C(YYYY-MM)). Defaults to the current month.
        type: str
    tags:
        description:
            - Only buckets (and their usage) with every one of these tags.
            - A key with a value matches that exact value; a key with an empty (null) value
              matches any value. At most 10.
        type: dict
        version_added: "1.6.0"
'''

EXAMPLES = r'''
- name: List tiers, buckets and access keys
  cubepathinc.cloud.object_storage_info:
    api_token: "{{ cubepath_token }}"
  register: storage

- name: This month's usage and cost of a project
  cubepathinc.cloud.object_storage_info:
    api_token: "{{ cubepath_token }}"
    gather: [usage]
    project_id: 12
  register: usage

- name: Production buckets of the data team
  cubepathinc.cloud.object_storage_info:
    api_token: "{{ cubepath_token }}"
    gather: [buckets]
    tags:
      env: prod
      team:
  register: prod

- name: One bucket in detail
  cubepathinc.cloud.object_storage_info:
    api_token: "{{ cubepath_token }}"
    gather: []
    bucket: my-backups
  register: detail
'''

RETURN = r'''
tiers:
    description: Available storage tiers with endpoint, region, prices and free tier.
    type: list
    elements: dict
    returned: when C(tiers) is in I(gather)
buckets:
    description: Buckets of the organization, each with its C(tags).
    type: list
    elements: dict
    returned: when C(buckets) is in I(gather)
access_keys:
    description: Access keys of the organization, without secrets.
    type: list
    elements: dict
    returned: when C(access_keys) is in I(gather)
usage:
    description: Usage and cost of the month per tier and per bucket.
    type: dict
    returned: when C(usage) is in I(gather)
bucket:
    description: Detail of the bucket given in I(bucket), with connection details and month usage.
    type: dict
    returned: when I(bucket) is set
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_object_storage import tag_filter


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        gather=dict(type='list', elements='str', default=['tiers', 'buckets', 'access_keys'],
                    choices=['tiers', 'buckets', 'access_keys', 'usage']),
        bucket=dict(type='str'),
        project_id=dict(type='int'),
        tier=dict(type='str'),
        period=dict(type='str'),
        tags=dict(type='dict'),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    api = CubePathAPI(module)
    gather = module.params['gather']
    filters = {'project_id': module.params.get('project_id'), 'tier': module.params.get('tier')}
    bucket_filters = dict(filters, tag=tag_filter(module.params.get('tags')))
    result = {'changed': False}

    if 'tiers' in gather:
        tiers = api.get('/object-storage/tiers')
        result['tiers'] = tiers if isinstance(tiers, list) else []
    buckets = None
    if 'buckets' in gather:
        buckets = api.get('/object-storage/buckets', params=bucket_filters)
        buckets = buckets if isinstance(buckets, list) else []
        result['buckets'] = buckets
    if 'access_keys' in gather:
        keys = api.get('/object-storage/keys', params=filters)
        result['access_keys'] = keys if isinstance(keys, list) else []
    if 'usage' in gather:
        params = dict(bucket_filters, period=module.params.get('period'))
        result['usage'] = api.get('/object-storage/usage', params=params)

    ref = module.params.get('bucket')
    if ref:
        # The lookup of a single bucket ignores the tag filter.
        if buckets is None or module.params.get('tags'):
            buckets = api.get('/object-storage/buckets', params=filters)
            buckets = buckets if isinstance(buckets, list) else []
        match = next((b for b in buckets if ref in (b.get('name'), b.get('uuid'))), None)
        if match is None:
            module.fail_json(msg='Bucket %s not found' % ref)
        result['bucket'] = api.get('/object-storage/buckets/%s' % match['uuid'])

    module.exit_json(**result)


if __name__ == '__main__':
    main()
