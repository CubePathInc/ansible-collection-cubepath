# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment:
    DOCUMENTATION = r'''
options:
    api_token:
        description:
            - CubePath API token for authentication.
            - Can be set via the C(CUBEPATH_API_TOKEN) environment variable.
        type: str
        required: true
    api_url:
        description:
            - URL of the CubePath API.
        type: str
        default: https://api.cubepath.com
    api_timeout:
        description:
            - Timeout for API requests in seconds.
        type: int
        default: 60
    validate_certs:
        description:
            - Whether to validate SSL certificates.
        type: bool
        default: true
'''
