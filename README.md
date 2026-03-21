# CubePath Cloud Ansible Collection

Ansible collection for managing CubePath Cloud infrastructure resources including VPS, baremetal servers, networks, DNS, load balancers, CDN, and more.

## Installation

```bash
ansible-galaxy collection install cubepathinc.cloud
```

Or install from source:

```bash
ansible-galaxy collection install git+https://github.com/CubePathInc/cubepath.ansible.git
```

## Authentication

All modules require a CubePath API token. You can provide it via:

- Module parameter: `api_token`
- Environment variable: `CUBEPATH_API_TOKEN`

## Modules

### Compute
- `cubepathinc.cloud.vps` - Create/destroy VPS instances
- `cubepathinc.cloud.vps_info` - List VPS instances
- `cubepathinc.cloud.vps_power` - Manage VPS power state
- `cubepathinc.cloud.vps_action` - Resize, reinstall, change password, update VPS
- `cubepathinc.cloud.baremetal` - Deploy baremetal servers
- `cubepathinc.cloud.baremetal_info` - List baremetal servers
- `cubepathinc.cloud.baremetal_power` - Manage baremetal power state
- `cubepathinc.cloud.baremetal_action` - Reinstall, rescue, reset BMC, update baremetal

### Networking
- `cubepathinc.cloud.network` - Manage private networks
- `cubepathinc.cloud.network_info` - List networks
- `cubepathinc.cloud.floating_ip` - Manage floating IP lifecycle and assignments
- `cubepathinc.cloud.floating_ip_info` - List floating IPs

### DNS
- `cubepathinc.cloud.dns_zone` - Manage DNS zones
- `cubepathinc.cloud.dns_zone_info` - List DNS zones
- `cubepathinc.cloud.dns_record` - Manage DNS records
- `cubepathinc.cloud.dns_record_info` - List DNS records

### Load Balancer
- `cubepathinc.cloud.loadbalancer` - Manage load balancers
- `cubepathinc.cloud.loadbalancer_info` - List load balancers
- `cubepathinc.cloud.loadbalancer_listener` - Manage listeners
- `cubepathinc.cloud.loadbalancer_target` - Manage targets
- `cubepathinc.cloud.loadbalancer_health_check` - Configure health checks

### CDN
- `cubepathinc.cloud.cdn_zone` - Manage CDN zones
- `cubepathinc.cloud.cdn_zone_info` - List CDN zones
- `cubepathinc.cloud.cdn_origin` - Manage CDN origins
- `cubepathinc.cloud.cdn_rule` - Manage CDN edge rules
- `cubepathinc.cloud.cdn_waf_rule` - Manage CDN WAF rules

### Account
- `cubepathinc.cloud.project` - Manage projects
- `cubepathinc.cloud.project_info` - List projects
- `cubepathinc.cloud.ssh_key` - Manage SSH keys
- `cubepathinc.cloud.ssh_key_info` - List SSH keys

### Reference
- `cubepathinc.cloud.plan_info` - List VPS plans
- `cubepathinc.cloud.template_info` - List OS templates
- `cubepathinc.cloud.location_info` - List locations
- `cubepathinc.cloud.ddos_attack_info` - List DDoS attacks

### Inventory
- `cubepathinc.cloud.cubepath` - Dynamic inventory plugin

## Example

```yaml
- name: Deploy infrastructure
  hosts: localhost
  tasks:
    - name: Create project
      cubepathinc.cloud.project:
        api_token: "{{ cubepath_token }}"
        name: production
        state: present
      register: project

    - name: Create VPS
      cubepathinc.cloud.vps:
        api_token: "{{ cubepath_token }}"
        name: web-01
        project_id: "{{ project.project.id }}"
        plan: gp.nano
        template: debian-13
        location: eu-bcn-1
        ssh_keys:
          - deploy-key
        state: present
```

## License

GPL-3.0-or-later
