#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: transcoder_job_info
short_description: Get Video Transcoder jobs from CubePath Cloud
description:
    - List transcoding jobs, newest first, or read one job with the files it produced.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    job_uuid:
        description: UUID of one job, returned in detail as RV(job) with its RV(outputs).
        type: str
    batch_id:
        description: Only jobs of this bulk submission.
        type: str
    limit:
        description: Maximum number of jobs to list (1 to 500).
        type: int
        default: 100
    offset:
        description: Number of jobs to skip, for paging.
        type: int
        default: 0
'''

EXAMPLES = r'''
- name: Latest jobs
  cubepathinc.cloud.transcoder_job_info:
    api_token: "{{ cubepath_token }}"
    limit: 20
  register: jobs

- name: Files produced by a job
  cubepathinc.cloud.transcoder_job_info:
    api_token: "{{ cubepath_token }}"
    job_uuid: b93468bd-4a89-4863-864b-6890cb27a104
  register: job
'''

RETURN = r'''
jobs:
    description: Jobs, newest first. S3 secret keys are never returned.
    type: list
    elements: dict
    returned: when I(job_uuid) is not set
job:
    description: Detail of the job given in I(job_uuid).
    type: dict
    returned: when I(job_uuid) is set
outputs:
    description: C(outputs) (produced objects with C(type), C(bucket) and C(key)) and C(destination) of the job given in I(job_uuid).
    type: dict
    returned: when I(job_uuid) is set
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import as_list


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        job_uuid=dict(type='str'),
        batch_id=dict(type='str'),
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    api = CubePathAPI(module)

    job_uuid = module.params.get('job_uuid')
    if job_uuid:
        module.exit_json(
            changed=False,
            job=api.get('/transcoder/jobs/%s' % job_uuid),
            outputs=api.get('/transcoder/jobs/%s/outputs' % job_uuid),
        )

    params = {'batch_id': module.params.get('batch_id'), 'limit': module.params['limit'], 'offset': module.params['offset']}
    module.exit_json(changed=False, jobs=as_list(api.get('/transcoder/jobs', params=params), 'jobs'))


if __name__ == '__main__':
    main()
