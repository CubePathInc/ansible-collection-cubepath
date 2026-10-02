#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: object_storage_info
short_description: Get Object Storage information from CubePath Cloud
description:
    - List storage tiers, buckets, access keys and replications, get one bucket in detail (with
      its replication grants), or read the month's usage and cost.
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
        choices: [tiers, buckets, access_keys, usage, replications, replication_grants]
    bucket:
        description:
            - Name or UUID of a bucket to return in detail as RV(bucket).
            - Also limits RV(replications) to the ones of this bucket, and is required for
              C(replication_grants).
        type: str
    direction:
        description:
            - Which replications to return, C(outgoing) (from buckets of the organization),
              C(incoming) (into them) or C(all).
        type: str
        default: all
        choices: [outgoing, incoming, all]
        version_added: "1.7.0"
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

- name: Replications of a bucket and its grants
  cubepathinc.cloud.object_storage_info:
    api_token: "{{ cubepath_token }}"
    gather: [replications, replication_grants]
    bucket: photos
  register: replication

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
replications:
    description:
        - Replications of the organization, newest first, each with its C(direction), source,
          destination (external access key IDs masked), rules, health and backfill.
    type: list
    elements: dict
    returned: when C(replications) is in I(gather)
    version_added: "1.7.0"
replication_grants:
    description: Replication grants of the bucket given in I(bucket), without their tokens.
    type: list
    elements: dict
    returned: when C(replication_grants) is in I(gather)
    version_added: "1.7.0"
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
                    choices=['tiers', 'buckets', 'access_keys', 'usage', 'replications', 'replication_grants']),
        bucket=dict(type='str'),
        direction=dict(type='str', default='all', choices=['outgoing', 'incoming', 'all']),
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
    if 'replication_grants' in gather and not ref:
        module.fail_json(msg='bucket is required to gather replication_grants')
    if ref:
        # The lookup of a single bucket ignores the tag filter.
        if buckets is None or module.params.get('tags'):
            buckets = api.get('/object-storage/buckets', params=filters)
            buckets = buckets if isinstance(buckets, list) else []
        match = next((b for b in buckets if ref in (b.get('name'), b.get('uuid'))), None)
        if match is None:
            module.fail_json(msg='Bucket %s not found' % ref)
        result['bucket'] = api.get('/object-storage/buckets/%s' % match['uuid'])
        if 'replication_grants' in gather:
            grants = api.get('/object-storage/buckets/%s/replication-grants' % match['uuid'])
            result['replication_grants'] = grants if isinstance(grants, list) else []
    else:
        match = None

    if 'replications' in gather:
        params = {'direction': module.params['direction'], 'bucket_uuid': match['uuid'] if match else None}
        replications = api.get('/object-storage/replications', params=params)
        result['replications'] = replications if isinstance(replications, list) else []

    module.exit_json(**result)


if __name__ == '__main__':
    main()
