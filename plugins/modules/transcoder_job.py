#!/usr/bin/python
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: transcoder_job
short_description: Submit or cancel Video Transcoder jobs on CubePath Cloud
description:
    - Submit a video transcoding job that reads a video from a URL or an S3 compatible bucket and writes
      the requested renditions to an S3 compatible bucket, or cancel a job.
    - Set I(idempotency_key) to make the task idempotent. A job created with the same key is returned
      instead of creating a new one. Without a key every run submits a new job.
    - Jobs are billed by processed length.
version_added: "1.5.0"
author: CubePath (@cubepath)
extends_documentation_fragment:
    - cubepathinc.cloud.cubepath
options:
    state:
        description: C(present) submits the job, C(absent) cancels the job given in I(job_uuid).
        type: str
        default: present
        choices: [present, absent]
    job_uuid:
        description: UUID of the job to cancel. Required when I(state=absent).
        type: str
    input_url:
        description: Public http(s) URL of the source video. Mutually exclusive with I(input_s3).
        type: str
    input_s3:
        description: Bucket and object key of the source video. Mutually exclusive with I(input_url).
        type: dict
        suboptions:
            endpoint:
                description: S3 endpoint URL. Omit for AWS.
                type: str
            region:
                description: Region of the bucket.
                type: str
            bucket:
                description: Bucket name.
                type: str
                required: true
            path:
                description: Object key of the source video.
                type: str
                default: ''
            access_key:
                description: Access key ID.
                type: str
            secret_key:
                description: Secret access key. Never returned by the API.
                type: str
    output_s3:
        description: Bucket and prefix the renditions are written to. Required when I(state=present).
        type: dict
        suboptions:
            endpoint:
                description: S3 endpoint URL. Omit for AWS.
                type: str
            region:
                description: Region of the bucket.
                type: str
            bucket:
                description: Bucket name.
                type: str
                required: true
            path:
                description: Prefix the outputs are written under.
                type: str
                default: ''
            access_key:
                description: Access key ID.
                type: str
            secret_key:
                description: Secret access key. Never returned by the API.
                type: str
    outputs:
        description:
            - Renditions to produce (1 to 20). Each item has a C(type) (C(file), C(hls), C(thumbnails) or C(gif))
              plus the parameters of that type, for example C(codec), C(height), C(container) or C(crf).
            - Required when I(state=present).
        type: list
        elements: dict
    webhook_url:
        description: URL called when the job finishes.
        type: str
    idempotency_key:
        description: Client key that makes the submission idempotent (up to 255 characters).
        type: str
    wait:
        description: Wait until the job is C(completed), C(failed) or C(canceled).
        type: bool
        default: false
    wait_timeout:
        description: Seconds to wait when I(wait=true).
        type: int
        default: 3600
'''

EXAMPLES = r'''
- name: Transcode a video to 720p H.265 and HLS
  cubepathinc.cloud.transcoder_job:
    api_token: "{{ cubepath_token }}"
    input_url: https://example.com/source.mp4
    output_s3:
      endpoint: https://eu.cubestorage.io
      bucket: my-videos
      path: renditions/clip-1/
      access_key: "{{ s3_access_key }}"
      secret_key: "{{ s3_secret_key }}"
    outputs:
      - type: file
        codec: h265
        height: 720
        container: mp4
      - type: hls
    idempotency_key: clip-1
    wait: true
  register: job

- name: Cancel a job
  cubepathinc.cloud.transcoder_job:
    api_token: "{{ cubepath_token }}"
    job_uuid: "{{ job.job.uuid }}"
    state: absent
'''

RETURN = r'''
job:
    description: The job (C(uuid), C(status), C(progress), C(outputs), C(error)...). S3 secret keys are never returned.
    type: dict
    returned: when I(state=present)
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_api import CubePathAPI, cubepath_argument_spec
from ansible_collections.cubepathinc.cloud.plugins.module_utils.cubepath_common import wait_for

FINAL = ('completed', 'failed', 'canceled')


def s3_spec():
    return dict(
        endpoint=dict(type='str'),
        region=dict(type='str'),
        bucket=dict(type='str', required=True),
        path=dict(type='str', default=''),
        access_key=dict(type='str', no_log=False),
        secret_key=dict(type='str', no_log=True),
    )


def s3_body(value):
    return dict((k, v) for k, v in value.items() if v is not None)


def main():
    argument_spec = cubepath_argument_spec()
    argument_spec.update(
        state=dict(type='str', default='present', choices=['present', 'absent']),
        job_uuid=dict(type='str'),
        input_url=dict(type='str'),
        input_s3=dict(type='dict', options=s3_spec()),
        output_s3=dict(type='dict', options=s3_spec()),
        outputs=dict(type='list', elements='dict'),
        webhook_url=dict(type='str'),
        idempotency_key=dict(type='str', no_log=False),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(type='int', default=3600),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'absent', ['job_uuid']),
            ('state', 'present', ['output_s3', 'outputs']),
            ('state', 'present', ['input_url', 'input_s3'], True),
        ],
        mutually_exclusive=[('input_url', 'input_s3')],
        supports_check_mode=True,
    )

    api = CubePathAPI(module)
    p = module.params

    if p['state'] == 'absent':
        job = api.get('/transcoder/jobs/%s' % p['job_uuid'])
        if job.get('status') in FINAL:
            module.exit_json(changed=False, job=job)
        if module.check_mode:
            module.exit_json(changed=True)
        api.delete('/transcoder/jobs/%s' % p['job_uuid'])
        module.exit_json(changed=True)

    if module.check_mode:
        module.exit_json(changed=True)

    if p.get('input_url'):
        job_input = {'source': 'url', 'url': p['input_url']}
    else:
        job_input = {'source': 's3', 's3': s3_body(p['input_s3'])}
    data = {
        'input': job_input,
        'output': {'s3': s3_body(p['output_s3'])},
        'outputs': p['outputs'],
    }
    if p.get('webhook_url'):
        data['webhook_url'] = p['webhook_url']
    if p.get('idempotency_key'):
        data['idempotency_key'] = p['idempotency_key']

    before = None
    if p.get('idempotency_key'):
        # The API answers a replay with the original job, so look at the job list to tell a replay apart.
        before = set(j.get('uuid') for j in (api.get('/transcoder/jobs', params={'limit': 500}) or {}).get('jobs', []))
    job = api.post('/transcoder/jobs', data)
    changed = before is None or job.get('uuid') not in before

    if p['wait'] and job.get('status') not in FINAL:
        job = wait_for(module, lambda: api.get('/transcoder/jobs/%s' % job['uuid']),
                       lambda j: j.get('status') in FINAL, p['wait_timeout'], interval=10)
        if job.get('status') == 'failed':
            module.fail_json(msg='The transcoding job failed: %s' % (job.get('error') or 'unknown error'), job=job)
    module.exit_json(changed=changed, job=job)


if __name__ == '__main__':
    main()
