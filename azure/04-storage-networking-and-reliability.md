# Azure: Storage, Networking, and Reliability

> Storage accounts, Blob Storage and Azure SQL Database, static websites and storage security, network basics, Availability Zones and multi-region resilience, backup, and disaster recovery.

## Key Concepts

### Hosting a Static Website in Azure Storage

Azure Storage can host static HTML, CSS, JavaScript, and media files without a web server or VM.

**Setup**

1. Create a general-purpose v2 storage account.
2. Open **Storage account > Data management > Static website**.
3. Enable the feature.
4. Configure an index document such as `index.html` and an error document such as `error.html`.
5. Upload website files to the automatically created `$web` container.
6. Test the primary web endpoint and a missing path to verify error handling.
7. Monitor storage metrics and logs as required.

**Benefits**

- No web server administration
- Low-cost hosting for static content
- Simple deployment
- Integration with Azure Front Door for custom domains, edge delivery, security, and global performance

**Limitations:** Storage static websites do not execute server-side application code. Use an API or Functions for dynamic behavior.

### Azure Front Door with a Storage Static Website

Azure Front Door is a global entry point. It routes users through Microsoft's edge network, which improves performance and availability. Depending on how it's configured and which tier you use, it can also add caching, TLS termination, custom domains, health probes, and a Web Application Firewall.

**Typical setup**

1. Enable static website hosting and upload the site.
2. Create an Azure Front Door profile and endpoint.
3. Add the Storage static website endpoint as an origin.
4. Configure the origin group, route, caching, and custom domain.
5. Test both the origin URL and the Front Door URL from a few different locations.
6. Review latency, cache behavior, and health metrics.

Register the required resource provider first if the subscription hasn't used this service before. Test performance from more than one location — a single browser request isn't enough to prove a real improvement.

### Securing Azure Storage Accounts

Use defense in depth rather than relying on one setting.

1. **Prevent anonymous blob access** unless the workload explicitly requires public content.
2. **Restrict public network access** to selected networks, or disable it when private access is sufficient.
3. **Use private endpoints** to give a storage service a private IP address in a VNet.
4. **Use service endpoints when appropriate** to restrict the public storage endpoint to selected subnets. Unlike a private endpoint, the service still uses its public endpoint.
5. **Enforce secure transfer** so clients use HTTPS or supported secure protocols.
6. **Prefer Microsoft Entra ID and managed identities** over account keys.
7. **Use SAS tokens carefully**: grant minimal permissions, use short expiry times, require HTTPS, and prefer user-delegation SAS for Blob Storage when possible.
8. **Protect account keys** and rotate them if they must be used.
9. **Use encryption at rest** with Microsoft-managed keys or customer-managed keys where required.
10. **Consider infrastructure encryption** when compliance requires an additional encryption layer.
11. **Use Defender for Storage** for threat detection where the risk and cost justify it.
12. **Enable diagnostic settings, logging, soft delete, versioning, and recovery features** according to the workload's protection requirements.

### VNet, Subnet, and Application Delivery Patterns

An Azure VNet is a private address space and routing boundary. Subnets divide it up by trust zone or role — for example ingress, web, application, data, private endpoints, and management.

Plan non-overlapping address ranges with room to grow, then attach resources through network interfaces or private integration.

NSGs filter traffic by source, destination, protocol, and port at the subnet or NIC level. User-defined routes control where traffic goes. Peering connects VNets to each other. A VPN Gateway or ExpressRoute handles hybrid connectivity. Private endpoints give supported PaaS services their own private addresses, which needs matching private DNS design.

Don't call an Azure subnet inherently "public" or "private" — how exposed it actually is depends on public IPs, load-balancer or application-gateway frontends, routes, NAT, NSGs, firewall policy, and the service running there.

### Azure Application Gateway request flow

```text
client -> frontend IP -> listener -> routing rule
       -> HTTP settings and health probe -> backend pool
```

Application Gateway is a regional Layer-7 load balancer for HTTP/HTTPS. Listeners receive traffic, rules pick a backend by host or path, backend settings define the protocol, port, TLS, and session behavior, and health probes remove any target that isn't healthy.

Backend pools can include VMs, scale sets, App Service, AKS, or plain IP/FQDN targets, depending on what's supported. WAF adds managed or custom rules against common web attacks. TLS can either terminate at the gateway or be re-encrypted on the way to the backend.

Cookie-based affinity can keep a client pinned to the same backend when an application needs session stickiness, but a stateless application is easier to scale and recover. Current v2 SKUs support autoscaling and zone redundancy in regions that have Availability Zones.

For centralized certificate management, Application Gateway can pull TLS certificates from Key Vault using a managed identity that has only the access it needs.

Send access, performance, firewall, and health data through diagnostic settings to Azure Monitor/Log Analytics, and alert on unhealthy backends, failed requests, latency, capacity, and WAF events.

To troubleshoot: check the resolved frontend address, listener/SNI and certificate, WAF logs, rule priority, any rewrite/redirect behavior, backend health, probe host/path/status, the NSG/UDR/firewall path, backend TLS trust, and application logs. A healthy gateway doesn't mean the backend is healthy too.

### Load Balancer and secure administration

Azure Load Balancer distributes Layer-4 TCP/UDP traffic using a frontend, a rule, a backend pool, and a health probe. A common path looks like: internet -> public frontend -> load-balancing rule -> healthy VM backend.

Use an internal load balancer for private, tier-to-tier traffic.

A jump VM is a hardened VM used as a stepping stone for admin access — but it still needs patching, identity controls, logging, and network protection like any other VM. Azure Bastion is a managed alternative: it gives RDP or SSH access to private VMs without giving each one a public IP.

Typically a user starts the session through the Azure portal over HTTPS, and Bastion then reaches the VM over its private address — so inbound TCP 22 or 3389 never has to be exposed to the public internet.

Whichever pattern you use, apply least privilege (give access only where it's needed), just-in-time access, session logging, restricted management sources, and a break-glass procedure for emergencies.

### NSG and Azure Firewall together

NSGs give you distributed, stateful Layer-3/4 filtering close to subnets and NICs. Azure Firewall gives you centralized inspection and policy — network/application rules, threat-intelligence features, DNAT/SNAT, and centralized logs, depending on the SKU and configuration.

In a hub-and-spoke design, use UDRs to steer the traffic that needs inspection through the firewall, and use NSGs to restrict each workload's boundary. Validate that routing is symmetric and check the effective rules — just deploying both products doesn't create defense in depth on its own; you need a deliberate traffic path.

### Azure Landing Zone Hub-and-Spoke Networking

The hub-and-spoke model keeps shared connectivity separate from application workloads:

- A connectivity subscription hosts the hub VNet and shared services: Azure Firewall, VPN or ExpressRoute Gateway, Bastion, private DNS resolver, private endpoints, Route Server, logging, and network monitoring.
- Workload subscriptions host their own spoke VNets and application subnets for VMs, AKS, App Service integration, and databases.
- VNet peering connects the hub to each spoke. User-defined routes in the spokes normally send outbound traffic through Azure Firewall; where needed, route propagation can use BGP and Azure Route Server.
- Internet traffic coming in can pass through Azure Front Door with WAF/DDoS controls before it reaches the regional application. Traffic from on-premises terminates in the hub, over ExpressRoute or a site-to-site VPN.
- Private endpoints give supported PaaS services private IP addresses. Private DNS zones and resolver/forwarding rules need to make the same name resolve correctly from both the spokes and on-premises.

Typical traffic paths are:

- **Spoke to internet:** workload → spoke route table → Azure Firewall/NAT policy → internet.
- **Internet to application:** Front Door/WAF → regional load balancer or application gateway/firewall → spoke application.
- **On-premises to spoke:** ExpressRoute/VPN → hub gateway → approved hub route → spoke.
- **Spoke to PaaS:** workload → private endpoint in the private address space, resolved through private DNS.

This design keeps governance, inspection, logging, and hybrid connectivity centralized, while each workload still owns its own spoke. Things worth validating: non-overlapping address ranges, both forward and return routes, gateway transit, firewall policy, DNS resolution, asymmetric routing, and what happens if a shared hub component fails.

The architecture isn't really done until routing, DNS, monitoring, and recovery have all been tested from the real source networks — not just assumed to work.

### Individual Public IP vs. Public IP Prefix

An **individual public IP address** is one public address assigned to a resource — a load balancer, firewall, application gateway, NAT gateway, or network interface.

A **public IP prefix** is a reserved, contiguous range of static public IP addresses (Standard SKU). You can create individual public IP resources out of that range.

| Feature | Individual public IP | Public IP prefix |
| --- | --- | --- |
| Scope | One address | Contiguous address range |
| Example | `52.160.10.15` | `52.160.10.0/28` |
| Management | Managed separately | Whole range reserved as one resource |
| Best fit | A few endpoints | Larger deployments that need predictable addresses |
| Main benefit | Simple setup | Consistent addresses, easier for partners to allow-list |

**Use an individual IP** for a small number of endpoints. **Use a prefix** when several resources need addresses from a known range — for example outbound NAT, load balancers, or firewalls that external partners need to allow-list.

### Azure Network Watcher VM Extension

Network Watcher is Azure's network monitoring and diagnostics service. Some of its VM-based checks — packet capture and certain connection-monitoring scenarios — need the Network Watcher Agent extension installed on the VM first.

If you start one of these diagnostics and the extension is missing, Azure may install the current version for you automatically. If your change-control process requires a specific version, install and validate it yourself before running the diagnostic.

```bash
az vm extension set \
  --resource-group <resource-group> \
  --vm-name <vm-name> \
  --name NetworkWatcherAgentWindows \
  --publisher Microsoft.Azure.NetworkWatcher \
  --version <desired-version>
```

To query the latest version available in a region:

```bash
az vm extension image list \
  --name NetworkWatcherAgentWindows \
  --publisher Microsoft.Azure.NetworkWatcher \
  --latest \
  --location centralindia
```

**Interview summary:** Network Watcher is the service itself. The VM extension is a small in-guest agent that specific diagnostic features need. They're related, but not the same resource.

### Secure Azure Database Connectivity

1. Pick the managed database and availability model — Azure SQL, PostgreSQL, MySQL, or Cosmos DB — based on backup needs, zone/region, RTO, RPO, and performance.
2. Provision it through reviewed IaC, with diagnostic settings on, deletion protection where it's supported, backup retention set, and a private endpoint.
3. Connect the application over VNet integration, private DNS, routes, and firewall rules scoped as narrowly as possible. Avoid exposing the database publicly unless there's a real, controlled reason to.
4. Prefer managed identity and Microsoft Entra authentication. If a password or connection secret is unavoidable, store it in Key Vault and pull it at runtime — never bake it into an image or a repository.
5. Require TLS certificate validation. Use connection pooling, limited timeouts, retry with backoff (waiting a bit longer between each retry), and safe locking during migrations.

Investigation flow for a failed connection:

```text
DNS/private endpoint → route/NSG/firewall → TCP port → TLS
→ identity/token audience and database user → database health/quota
→ pool exhaustion, timeout, query and application logs
```

I test from the real workload identity and subnet, and check both an allowed path and a path that should be denied. I compare Azure Activity/diagnostic logs, and watch connection failures, pool use, query latency, deadlocks, storage, and failover.

An administrator connecting successfully from the portal doesn't prove the application's own connection path works.

### Azure Reliability, Storage, and Operations Notes

Use Availability Zones to survive a single datacenter failing within a region. For a whole region going down, you need a multi-region setup, data replication, and failover that's actually been tested. Region pairs are just an Azure planning concept — they don't automatically mean every workload replicates or fails over on its own.

Recovery design starts with the application's recovery time and recovery point objectives, data consistency needs, and how much capacity the dependencies actually have.

Azure Blob Storage is object storage. Pick the access tier based on how the data is actually used: Hot for data accessed often, Cool for data accessed rarely (with tradeoffs around minimum retention and retrieval cost), and Archive for long-term data that needs to be brought back online before it can be used.

Azure Files gives you managed SMB or NFS file shares; managed disks give you block storage for VMs. Use private endpoints, encryption, RBAC, and backup or lifecycle policies wherever they're needed.

Azure Monitor collects metrics, logs, and alerts. Application Insights covers application-level request and dependency monitoring. Log Analytics stores and lets you query logs with KQL. Azure Service Health tells you about Azure's own incidents and planned maintenance.

Azure Advisor gives recommendations across reliability, security, performance, cost, and operational excellence — but each one still needs a workload-specific review before you act on it.

Network security groups are stateful allow/deny rules at Layer 3/4, applied to subnets or network interfaces. Azure Firewall is a centralized, managed firewall service.

Application Gateway is a Layer-7 HTTP(S) load balancer, and it can run a web application firewall policy too. Pick the right one for the traffic boundary you're actually protecting, and check the effective routes and rules directly — don't assume that stacking all three together automatically gives you a correct design.

### Resilient multi-region application

A multi-region Azure application can use Front Door as the global entry point, with a regional Application Gateway, WAF, or another regional ingress in each deployment.

Keep the web, application, data, and management boundaries separate. Use private endpoints, Key Vault, Firewall, Policy, Monitor, and tested backup and failover, based on what the workload actually needs.

The real recovery point and recovery time come down to how data replication and failover actually behave — deploying compute in two regions by itself is not disaster recovery. Regularly test regional traffic failover, dependency capacity, DNS and TLS, data recovery, and the operational runbooks themselves.

## Interview Questions

<details><summary>Q1. [Basic] What is an Azure Storage Account?</summary>

**Answer:**

A Storage Account is Azure's namespace, security, and configuration boundary for Blob, Files, Queue, and Table services, depending on the account type. It controls region, redundancy, performance tier, networking, encryption, identity and RBAC, lifecycle rules, and protection settings.

I pick general-purpose v2 in most cases, choose LRS, ZRS, or GRS based on what failure and recovery-point needs the workload actually has, turn off public or anonymous access unless it's genuinely required, prefer Entra ID and managed identity over keys, enforce HTTPS, use private endpoints or firewalls, and turn on logs, soft delete, versioning, or lifecycle rules depending on the workload.

I keep an eye on capacity, transactions, latency, availability, throttling, and data leaving the account. Recovery features and backup get chosen per service — replication by itself doesn't protect against every kind of deletion or corruption.

</details>

<details><summary>Q2. [Basic] What is Azure Blob Storage?</summary>

**Answer:**

Blob Storage is object storage for unstructured data — images, logs, backups, build artifacts, static content, data-lake files, that kind of thing. Containers hold block, append, or page blobs, and access tiers let you trade retrieval speed and cost against storage cost.

Applications use the SDK or REST API with managed identity and roles scoped to just the data they need. I use lifecycle rules to move data to cheaper tiers or delete it on a schedule, immutable storage (which can't be altered or deleted before its retention period ends) for regulated data that must be retained, and versioning or soft delete for recovery.

Large uploads go in blocks, with retries designed to be safe even if the same block gets uploaded twice.

I choose Blob over Azure Files when the workload fits object access over HTTP; Files is the better fit for SMB or NFS shares. Monitoring covers request errors, latency, capacity, throttling, and outbound data.

</details>

<details><summary>Q3. [Intermediate] How do you secure Azure Storage?</summary>

**Answer:**

I stack several layers of protection rather than relying on one setting. I turn off anonymous blob access, restrict or disable public network access, use private endpoints and private DNS, require HTTPS for all transfers, prefer Entra managed identities and data-level RBAC over account keys, protect and rotate any keys that are still in use, and issue SAS tokens that are short-lived and carry only the permissions they need.

Azure encrypts data at rest by default. I add customer-managed keys or infrastructure-level encryption when the requirement calls for it. I also turn on Defender and logging, use versioning, soft delete, or immutability where it makes sense, and apply policies that stop insecure settings from being created in the first place.

I test that allowed access actually works and denied access actually fails. If there's an exposure, I lock down access, revoke SAS tokens or rotate keys, keep the logs, check what was downloaded or changed, restore data if needed, and fix the underlying policy or architecture.

</details>

<details><summary>Q4. [Basic] What is Azure SQL Database?</summary>

**Answer:**

Azure SQL Database is a managed, SQL Server-compatible database. Azure handles platform patching, backups, and built-in availability; I manage schema, queries and indexes, users, data protection, performance tier, networking, recovery policy, and how resilient the application is to hiccups.

I use Entra authentication or managed identity, a firewall or private endpoint, TLS, auditing and Defender, access scoped to only what's needed, and monitoring. Point-in-time restore and geo-replication or failover groups get chosen based on how much data loss and downtime the business can actually tolerate.

When the database is slow, I look at query performance, wait stats, blocking, CPU and IO, the connection pool, indexes and query plans, and any recent changes. Scaling up can help in the moment, but it doesn't replace actually fixing the query or the root cause.

</details>

<details><summary>Q5. [Basic] Can an NSG be attached directly to a virtual network?</summary>

**Answer:**

No. A network security group attaches to a subnet or a network interface — not directly to the virtual network.

The effective rules are the combination of whatever's applied at the subnet and the NIC, evaluated by Azure's priority order. I check the effective security rules and use Network Watcher to confirm the real path traffic takes, rather than assuming a broad default allow rule is fine.

</details>

<details><summary>Q6. [Basic] Can VMs in different subnets of the same VNet communicate?</summary>

**Answer:**

Yes — VNet routing allows communication between subnets by default. That can be restricted by network security groups, user-defined routes, Azure Firewall or NVAs, service endpoints, private endpoints, or the guest OS's own firewall.

I check the effective routes, the NSG flow, DNS, and the target listener before assuming a subnet boundary is doing any actual security work.

</details>

<details><summary>Q7. [Advanced] How do you approach Azure disaster recovery?</summary>

**Answer:**

I start with a business impact analysis and define the recovery time objective, recovery point objective, how much data loss is tolerable, what a regional failure would mean, dependencies, and who owns the recovery decision.

Then I pick patterns per component: zones for a datacenter failure, multi-region capacity for the application, database replication, geo-redundant storage where it fits, Azure Backup, Site Recovery for supported VM workloads, and Front Door, Traffic Manager, or DNS-based failover.

A runbook needs to cover detection, who has authority to decide, data consistency, the order of failover, whether secrets and DNS are actually available during the failover, smoke tests, communication, and failing back afterward. Backups are kept isolated and protected from deletion.

I run actual restore tests and regional exercises, measure the real recovery time and recovery point achieved, and fix whatever gaps show up. Replication is not a backup — corruption or deletion can replicate right along with the good data. I also test failing back, because recovery isn't finished until normal operations are safely restored.

</details>

<details><summary>Q8. [Advanced] How do you design high availability in Azure?</summary>

Broader than just Kubernetes - applies across VMs, databases, and storage too:

- **Availability Zones**
- **Multiple VM instances / VMSS**
- **Multiple AKS nodes and Pod replicas**
- **Load Balancer / Application Gateway**
- **Autoscaling**
- **Highly available databases**
- **Storage redundancy**
- **Backup and disaster recovery**
- **Monitoring and alerting**

**Storage redundancy tiers:**

| Tier | Meaning |
| --- | --- |
| LRS | Locally Redundant Storage - copies within a single datacenter |
| ZRS | Zone Redundant Storage - copies across Availability Zones in one region |
| GRS | Geo Redundant Storage - copies to a secondary, paired region |
| GZRS | Geo-Zone Redundant Storage - zone redundancy in the primary region, plus geo-replication to a secondary region |

**For AKS specifically:** deploy node pools across Availability Zones, use multiple Pod replicas with readiness probes, HPA, Cluster Autoscaler, an Application Gateway (or other LB) in front, and a highly available database configuration behind it.

#### Short interview answer

Azure HA spans compute, data, and storage: Availability Zones and VMSS/multiple AKS nodes for compute, HA database configurations, and a storage redundancy tier chosen for the failure domain that actually matters - LRS for datacenter-local redundancy up through GZRS when both zone and region redundancy are required - backed by autoscaling, load balancing, backup/DR, and monitoring across all of it.

</details>

<details><summary>Q9. [Basic] Must an Azure VM and its Recovery Services vault be in the same region for backup?</summary>

**Answer:**

Yes — Azure VM Backup requires the Recovery Services vault and the VM it protects to be in the same region. Redundancy settings affect how the backup data itself gets replicated, but they don't remove that same-region requirement.

I pick the vault's region deliberately, apply retention, immutability, and access controls, and actually run restore tests rather than just checking that backups report success.

</details>

<details><summary>Q10. [Basic] What is Azure Virtual Network?</summary>

**Answer:**

A VNet is an isolated network in Azure, with its own address space and subnets. Resources inside it talk to each other and to the outside world through routes, NSGs, peering, gateways, private endpoints, load balancers, and DNS.

I plan non-overlapping address ranges with room to grow, keep workload and security tiers separate, control routing and egress, and connect on-premises networks through VPN or ExpressRoute. Peering gives connectivity between two VNets, but it isn't transitive by default — a third VNet peered to one of them isn't automatically reachable.

When something's broken, I check DNS, effective routes, effective NSG rules, any firewall/NVA, peering/gateway status, service firewalls, and the application port. Network Watcher's connection troubleshoot tool and flow logs help pinpoint exactly where traffic is being dropped.

After any IaC change, I confirm both the traffic that should get through and the traffic that should be blocked behave as expected.

</details>

<details><summary>Q11. [Basic] What is Azure Application Gateway?</summary>

**Answer:**

Application Gateway is a regional Layer-7 load balancer for HTTP/HTTPS. It handles host/path routing, TLS termination (or end-to-end TLS), health probes, session affinity, redirects, autoscaling, and can add a Web Application Firewall.

**Flow:** client → frontend IP/listener → routing rule → backend pool/HTTP setting → healthy backend. WAF policies inspect requests using managed or custom rules.

For a 502/503, I check the backend's health-check failure reason, DNS/IP, probe path/status, host header, certificate trust, port/protocol, NSG/routes, and whether the backend is actually ready. I compare access, performance, and firewall logs to narrow it down.

Once fixed, I test TLS, the routing paths, health checks, and latency, and confirm WAF is still doing its job — I don't disable protection broadly just to get things working again.

</details>

<details><summary>Q12. [Basic] What is Azure DNS?</summary>

**Answer:**

Azure DNS hosts public DNS zones and records. Azure Private DNS handles internal resolution for VNets and private endpoints. Hosting DNS for a domain doesn't register that domain for you.

I delegate public zones by pointing the registrar's NS records at Azure, manage records through IaC, use sensible TTLs, and lock down who can change records. Private zones get linked to the VNets that need them, with records or zone groups set up for private endpoints.

A hybrid setup, where on-premises and Azure both need to resolve the same names, may need Azure DNS Private Resolver or DNS forwarders.

To troubleshoot, I use `dig`/`nslookup`, confirm which server is actually authoritative, check the record type, TTL/cache, the VNet link, forwarding rules, and the client's resolver settings. I query from both an internal and an external client, since split-horizon DNS is often deliberately giving different answers to each.

</details>

<details><summary>Q13. [Intermediate] How do you connect Azure services privately?</summary>

**Answer:**

I use private endpoints to give supported PaaS services a private IP address inside a VNet, paired with private DNS that maps the service name to that IP. I then disable or restrict public network access, once I've confirmed everything still works.

App Service and Functions use VNet integration for outbound traffic; the private endpoint handles private inbound traffic where that's supported.

Service endpoints are a different, older option for some services and subnets — they still route to the service's public endpoint, so they aren't the same thing as Private Link.

I validate DNS resolution from the actual workload, the route, NSG/firewall rules, endpoint approval, the service's own configuration, and a real TCP/application connection. Hybrid clients also need DNS forwarding and a working VPN/ExpressRoute path. I test that public access is actually denied too, not just that private access works.

</details>

<details><summary>Q14. [Intermediate] How do you secure Azure networking?</summary>

**Answer:**

I start by mapping out the data flows and trust boundaries. From there, the usual controls are: subnet segmentation, NSGs, user-defined routes, Azure Firewall or an NVA where traffic needs deep inspection, private endpoints, private DNS, restricted egress, DDoS Protection for exposed critical workloads, a WAF for HTTP applications, and keeping public IPs to a minimum.

Connectivity to on-premises goes over VPN or ExpressRoute, built with redundancy in mind.

I test from the real source, working layer by layer: DNS resolution, routing, effective NSG rules, firewall logs, service firewalls, private endpoint approval, and the application port. Network Watcher's connection troubleshoot tool and flow logs help find exactly where a connection is being denied.

Changes go through IaC and peer review. I turn on diagnostics, alert on unexpected public exposure, review rules regularly, and check both an allowed flow and one that's meant to be denied.

</details>
