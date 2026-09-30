# CubePath Cloud Ansible Collection

Ansible collection for managing CubePath Cloud infrastructure resources including VPS, baremetal servers, Kubernetes, managed databases, networks, DNS, load balancers, CDN, DDoS mitigation, and more.

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
- `cubepathinc.cloud.vps_action` - Resize, reinstall, change password, update, protect, move, SSH keys and private network of a VPS
- `cubepathinc.cloud.vps_backup` - Take, restore or delete VPS backups
- `cubepathinc.cloud.vps_backup_settings` - Configure automatic VPS backups
- `cubepathinc.cloud.vps_backup_info` - List VPS backups and backup settings
- `cubepathinc.cloud.vps_iso` - Mount or unmount an ISO on a VPS
- `cubepathinc.cloud.vps_iso_info` - List the ISOs available to a VPS
- `cubepathinc.cloud.vps_firewall_groups` - Assign firewall groups to a VPS
- `cubepathinc.cloud.availability_group` - Manage availability groups and their VPS
- `cubepathinc.cloud.availability_group_info` - List availability groups
- `cubepathinc.cloud.baremetal` - Deploy baremetal servers
- `cubepathinc.cloud.baremetal_info` - List baremetal servers, models, installable OS and KVM access
- `cubepathinc.cloud.baremetal_power` - Manage baremetal power state
- `cubepathinc.cloud.baremetal_action` - Reinstall, rescue, reset BMC, update, protect, move, SSH keys and private network of a baremetal server

### Kubernetes
- `cubepathinc.cloud.kubernetes_cluster` - Manage Kubernetes clusters
- `cubepathinc.cloud.kubernetes_node_pool` - Manage node pools
- `cubepathinc.cloud.kubernetes_addon` - Install or uninstall catalog addons
- `cubepathinc.cloud.kubernetes_info` - List clusters, versions, plans and addons; kubeconfig and metrics

### Managed Databases
- `cubepathinc.cloud.managed_database` - Manage MySQL, PostgreSQL and Valkey databases (create, scale, protect, delete)
- `cubepathinc.cloud.managed_database_db` - Manage logical databases
- `cubepathinc.cloud.managed_database_user` - Manage database users (the password is returned only on create)
- `cubepathinc.cloud.managed_database_action` - Rotate the admin password or change configuration parameters
- `cubepathinc.cloud.managed_database_info` - List databases and plans; credentials, config and metrics of one

### Networking
- `cubepathinc.cloud.network` - Manage private networks
- `cubepathinc.cloud.network_info` - List networks
- `cubepathinc.cloud.network_route` - Manage static routes on a private network
- `cubepathinc.cloud.network_bgp_peer` - Manage BGP peers (Dynamic Routes) on a private network
- `cubepathinc.cloud.floating_ip` - Manage floating IP lifecycle and assignments
- `cubepathinc.cloud.floating_ip_reverse_dns` - Manage the reverse DNS of a floating IP
- `cubepathinc.cloud.floating_ip_info` - List floating IPs
- `cubepathinc.cloud.nat_gateway` - Manage NAT gateways (create, update, resize, protect, move)
- `cubepathinc.cloud.nat_gateway_info` - List NAT gateways and available plans
- `cubepathinc.cloud.firewall_group` - Manage VPS firewall groups
- `cubepathinc.cloud.firewall_group_info` - List firewall groups

### DNS
- `cubepathinc.cloud.dns_zone` - Manage DNS zones
- `cubepathinc.cloud.dns_zone_info` - List DNS zones, GeoDNS regions, SOA and health checks
- `cubepathinc.cloud.dns_zone_soa` - Manage the SOA settings of a zone
- `cubepathinc.cloud.dns_record_health_check` - Manage health checks of DNS records
- `cubepathinc.cloud.dns_record` - Manage DNS records
- `cubepathinc.cloud.dns_record_info` - List DNS records

### Load Balancer
- `cubepathinc.cloud.loadbalancer` - Manage load balancers (create, update, resize, protect, move)
- `cubepathinc.cloud.loadbalancer_info` - List load balancers and plans
- `cubepathinc.cloud.loadbalancer_listener` - Manage listeners
- `cubepathinc.cloud.loadbalancer_target` - Manage targets, one at a time or in batches
- `cubepathinc.cloud.loadbalancer_health_check` - Configure health checks

### CDN
- `cubepathinc.cloud.cdn_zone` - Manage CDN zones
- `cubepathinc.cloud.cdn_zone_info` - List CDN zones and plans; origins, rules, WAF rules, purges, pricing and metrics of a zone
- `cubepathinc.cloud.cdn_zone_action` - Request SSL, move, purge cache, rotate the Token Auth secret, sign URLs
- `cubepathinc.cloud.cdn_origin` - Manage CDN origins
- `cubepathinc.cloud.cdn_rule` - Manage CDN edge rules
- `cubepathinc.cloud.cdn_waf_rule` - Manage CDN WAF rules

### Object Storage
- `cubepathinc.cloud.object_storage_bucket` - Manage S3 compatible buckets
- `cubepathinc.cloud.object_storage_access_key` - Manage S3 access keys (the secret is returned only on create)
- `cubepathinc.cloud.object_storage_info` - List tiers, buckets, keys, bucket detail and monthly usage

To serve a bucket publicly, add it to a CDN zone with `cubepathinc.cloud.cdn_origin` and
`object_storage_bucket_uuid`. Buckets are never public on their own.

### DDoS Mitigation
- `cubepathinc.cloud.ddos_protection_profile` - Tune the protection profile of a Premium IP (settings, countries, ASNs, prefix lists)
- `cubepathinc.cloud.ddos_firewall_rule` - Manage scrubbing firewall rules of an IP
- `cubepathinc.cloud.ddos_prefix_list` - Manage custom prefix lists and their entries
- `cubepathinc.cloud.ddos_mitigation_info` - List protected IPs, countries, ASNs, prefix lists, profiles and rules
- `cubepathinc.cloud.ddos_traffic_info` - Query captured packets and pass/drop statistics
- `cubepathinc.cloud.ddos_attack_info` - List DDoS attacks, with details and traffic graph of one

### Cloud Alerts
- `cubepathinc.cloud.cloud_alert` - Manage metric alerts on VPS, baremetal servers and availability groups
- `cubepathinc.cloud.cloud_alert_channel` - Manage Slack, Discord and email notification channels
- `cubepathinc.cloud.cloud_alert_info` - List alerts and channels, with the history of one alert

### Video Transcoder
- `cubepathinc.cloud.transcoder_job` - Submit or cancel transcoding jobs
- `cubepathinc.cloud.transcoder_job_info` - List jobs, or read one with its outputs

### Account
- `cubepathinc.cloud.project` - Manage projects
- `cubepathinc.cloud.project_info` - List projects
- `cubepathinc.cloud.ssh_key` - Manage and rename SSH keys
- `cubepathinc.cloud.ssh_key_info` - List SSH keys

### Reference
- `cubepathinc.cloud.plan_info` - List VPS plans
- `cubepathinc.cloud.template_info` - List OS templates
- `cubepathinc.cloud.location_info` - List locations

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
