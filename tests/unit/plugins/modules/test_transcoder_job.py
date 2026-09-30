# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.cubepathinc.cloud.plugins.modules import transcoder_job

ARGS = {
    'input_url': 'https://example.com/in.mp4',
    'output_s3': {'bucket': 'out', 'endpoint': 'https://eu.cubestorage.io', 'access_key': 'AK', 'secret_key': 'SK'},
    'outputs': [{'type': 'file', 'codec': 'h264', 'height': 360}],
    'idempotency_key': 'clip-1',
}


def test_submit_builds_the_job(run):
    status, result, api = run(transcoder_job, ARGS, {
        ('GET', '/transcoder/jobs'): {'jobs': []},
        ('POST', '/transcoder/jobs'): {'uuid': 'j-1', 'status': 'queued'},
    })
    assert status == 'exit' and result['changed']
    assert api.writes() == [('POST', '/transcoder/jobs', {
        'input': {'source': 'url', 'url': 'https://example.com/in.mp4'},
        'output': {'s3': {'bucket': 'out', 'endpoint': 'https://eu.cubestorage.io', 'path': '', 'access_key': 'AK', 'secret_key': 'SK'}},
        'outputs': [{'type': 'file', 'codec': 'h264', 'height': 360}],
        'idempotency_key': 'clip-1',
    }, None)]


def test_replay_of_the_same_key_is_unchanged(run):
    status, result, api = run(transcoder_job, ARGS, {
        ('GET', '/transcoder/jobs'): {'jobs': [{'uuid': 'j-1'}]},
        ('POST', '/transcoder/jobs'): {'uuid': 'j-1', 'status': 'completed'},
    })
    assert status == 'exit' and not result['changed']


def test_cancel_finished_job_is_a_no_op(run):
    status, result, api = run(transcoder_job, {'state': 'absent', 'job_uuid': 'j-1'}, {
        ('GET', '/transcoder/jobs/j-1'): {'uuid': 'j-1', 'status': 'completed'},
    })
    assert status == 'exit' and not result['changed']
    assert api.writes() == []
