# System Design: Secure Monolithic Application on Azure

> A network-isolated design for a VM-based monolithic application on Azure: Application Gateway with WAF as the only public entry, separate frontend and backend subnets with NSGs and ASGs, an internal load balancer, private endpoints for Key Vault, SQL Database, and Storage, Azure Firewall for egress, and Terraform for the whole build.

## Key Concepts

### Architecture

```text
Internet
   |
   v
Public IP
   |
   v
Application Gateway v2 + WAF (snet-appgw)
   |  Listener (HTTPS 443, certificate from Key Vault)
   |  Routing rule -> backend pool
   v
Frontend VMs / VMSS (snet-frontend, ASG: asg-web)
   |
   v
Internal Load Balancer (Standard, private IP)
   |
   v
Backend VMs / VMSS (snet-backend, ASG: asg-app)
   |
   |  Private endpoints (snet-private-endpoints)
   |-----> Azure SQL Database   (privatelink.database.windows.net)
   |-----> Azure Key Vault      (privatelink.vaultcore.azure.net)
   '-----> Storage Account      (privatelink.blob.core.windows.net)

Outbound internet (updates, external APIs)
   VM subnets --UDR 0.0.0.0/0--> Azure Firewall (AzureFirewallSubnet) --> Internet

Admin access: Azure Bastion (AzureBastionSubnet) -> VMs over private IP
```

Only the Application Gateway has a public IP for application traffic. Everything else is private and stays inside the VNet.

### Subnet plan

| Subnet | Example range | Contains | Notes |
| --- | --- | --- | --- |
| `snet-appgw` | 10.0.0.0/24 | Application Gateway v2 | Dedicated subnet, nothing else in it |
| `snet-frontend` | 10.0.1.0/24 | Web tier VMs or VMSS | NSG + `asg-web` |
| `snet-backend` | 10.0.2.0/24 | App tier VMs or VMSS, internal load balancer | NSG + `asg-app` |
| `snet-private-endpoints` | 10.0.3.0/24 | Private endpoints for SQL, Key Vault, Storage | Network policies enabled so NSGs apply |
| `AzureFirewallSubnet` | 10.0.4.0/26 | Azure Firewall | Exact name required, at least /26 |
| `AzureBastionSubnet` | 10.0.5.0/26 | Azure Bastion | Exact name required, at least /26 |

### Traffic flows

1. **Inbound:** user → Public IP → Application Gateway listener (TLS) → WAF inspection (OWASP rules, bot protection) → routing rule → frontend backend pool, checked by a health probe.
2. **Frontend to backend:** frontend VMs → internal load balancer private IP → backend VMs. The load balancer health probe takes unhealthy VMs out of rotation.
3. **Backend to data:** backend VMs → private endpoint IPs for SQL, Key Vault, and Storage. Private DNS zones linked to the VNet make the normal hostnames resolve to private IPs. Public network access on these services is disabled.
4. **Outbound:** a route table on the VM subnets sends `0.0.0.0/0` to the Azure Firewall private IP. Firewall application rules allow only the FQDNs the app needs (OS updates, specific external APIs).
5. **Admin:** engineers connect through Azure Bastion. No VM has a public IP, and no NSG allows 22 or 3389 from the internet.

### NSG and ASG rules

Application security groups (ASGs) group VMs by role, so NSG rules use `asg-web` and `asg-app` instead of IP addresses. New VMs get the right rules as soon as their NIC joins the ASG.

| NSG | Priority | Source | Destination | Port | Action |
| --- | --- | --- | --- | --- | --- |
| nsg-frontend | 100 | `snet-appgw` | `asg-web` | 443 (or 80 behind TLS offload) | Allow |
| nsg-frontend | 110 | `AzureBastionSubnet` | `asg-web` | 22 / 3389 | Allow |
| nsg-frontend | 4000 | Any | Any | Any | Deny |
| nsg-backend | 100 | `asg-web` | `asg-app` | 8080 | Allow |
| nsg-backend | 110 | `AzureLoadBalancer` | `asg-app` | 8080 | Allow (health probe) |
| nsg-backend | 120 | `AzureBastionSubnet` | `asg-app` | 22 / 3389 | Allow |
| nsg-backend | 4000 | Any | Any | Any | Deny |
| nsg-private-endpoints | 100 | `asg-app` | private endpoint subnet | 1433, 443 | Allow |

The Application Gateway subnet needs its own NSG rules for the gateway's infrastructure ports (65200–65535 from `GatewayManager`) and for `AzureLoadBalancer`, or the gateway will not work.

### Security controls

- **WAF in Prevention mode** with the managed OWASP rule set, tuned with exclusions in Detection mode first.
- **TLS certificate in Key Vault**, read by the Application Gateway through a user-assigned managed identity.
- **Managed identities** on the VMs to read Key Vault secrets and access Storage, so no credentials are stored on disk.
- **SQL Database** with Entra ID authentication, public access disabled, and auditing enabled.
- **Azure Firewall** for egress with an FQDN allow-list and threat intelligence; logs sent to Log Analytics.
- **Defender for Cloud** for VM vulnerability assessment and recommendations.

### High availability

- Frontend and backend as **VM Scale Sets across availability zones**, behind zone-redundant Application Gateway v2 and a Standard internal load balancer.
- Zone-redundant SQL Database and ZRS storage.
- Health probes on both the Application Gateway and the internal load balancer.

### Infrastructure as Code

Everything is built with Terraform: one module per building block (network, NSG/ASG, Application Gateway, load balancer, compute, private endpoints, firewall, Bastion), environment folders for Dev, QA, and Prod, remote state, and a pipeline with plan, security scan, and approval before apply. See [handson/05](../handson/05-terraform-landing-zone-nested-maps.md) for a modular Terraform example.

### Monitoring

Diagnostic settings on the Application Gateway (access and WAF logs), firewall, load balancer, SQL, and Key Vault send logs to a Log Analytics workspace. Azure Monitor alerts cover backend health, WAF blocks spikes, VM CPU and memory, and SQL DTU or vCore usage.

## Interview Questions

<details><summary>Q1. [Intermediate] Walk me through how a request reaches the database in this design.</summary>

**Answer:**

The user's request reaches the Application Gateway's public IP. The HTTPS listener terminates TLS, the WAF inspects the request, and the routing rule sends it to a healthy frontend VM. The frontend calls the backend through the internal load balancer's private IP, which forwards to a healthy backend VM. The backend connects to SQL Database using its normal hostname; private DNS resolves it to the private endpoint IP, so the traffic never leaves the VNet.

</details>

<details><summary>Q2. [Intermediate] Why use application security groups instead of IP-based NSG rules?</summary>

**Answer:**

ASGs group NICs by role, such as web and app. NSG rules then say "allow `asg-web` to `asg-app` on 8080" instead of listing IP ranges. When a scale set adds a VM, its NIC is already in the ASG, so the rules apply without any change. It also makes the rules readable and keeps them correct when IPs change.

</details>

<details><summary>Q3. [Intermediate] Why put an internal load balancer between the frontend and backend tiers?</summary>

**Answer:**

It gives the frontend one stable private IP for the backend, spreads traffic across backend VMs, and removes unhealthy VMs using health probes. The backend can scale or be patched without the frontend knowing individual VM addresses. It works at Layer 4, so it is simple and adds very little latency.

</details>

<details><summary>Q4. [Advanced] How do you make sure nothing is publicly exposed except the Application Gateway?</summary>

**Answer:**

- No public IPs on VMs; Azure Policy denies public IPs on NICs in these subnets.
- Public network access disabled on SQL, Key Vault, and Storage, reached only through private endpoints.
- NSGs deny all inbound by default and allow only the specific tier-to-tier flows.
- Admin access only through Bastion.
- Outbound only through Azure Firewall with an allow-list.
- I verify it with Defender for Cloud recommendations, Azure Resource Graph queries for public IPs, and an external port scan.

</details>

<details><summary>Q5. [Advanced] Why route egress through Azure Firewall, and what should not get that route?</summary>

**Answer:**

Without it, VMs could reach any internet address, which allows data exfiltration and malware downloads. A route table sends `0.0.0.0/0` to the firewall, which allows only the FQDNs the application needs and logs everything. The default route should not be applied to the Application Gateway subnet (it needs direct internet for its own management traffic) or to `AzureBastionSubnet`.

</details>

<details><summary>Q6. [Advanced] How would you evolve this monolith design as traffic grows?</summary>

**Answer:**

First scale out: VM Scale Sets with autoscale on both tiers and zone redundancy. Then add caching (Azure Cache for Redis) and read replicas or a higher SQL tier. For global users, put Azure Front Door with WAF in front of regional Application Gateways and add a second region for DR. Longer term, split the busiest parts of the monolith into services, often moving them to App Service or AKS, while keeping the same private networking and egress controls.

</details>
