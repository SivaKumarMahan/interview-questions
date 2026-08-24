# Multi-Cloud Networking Scenario Questions

### 1. How do you implement policy-based routing in multi-cloud CI/CD?

**Answer:** Use traffic managers (Azure Traffic Manager, GCP Load Balancing), enforce routing rules per region, monitor latency, and shift traffic automatically on failures.

**Mini-case:** Our hybrid GCP-Azure app used geo-routing; during an Azure region outage, traffic auto-shifted to GCP with under 2 minutes of downtime.

**Detailed interview approach:**

I inventory the application, data, network, identity, DNS, compliance, and managed-service dependencies, and set clear RTO/RPO targets and acceptance tests. I build the target environment using separate, provider-specific Terraform modules and private connectivity, migrate one low-risk service first, and keep data replicating continuously.

While both environments run in parallel, I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic or DNS, with a tested rollback window, and I keep tight control over which side owns writes so I don't end up with split brain.

Once things are stable, I reconcile Terraform and its state, revoke any temporary cross-cloud access, archive the evidence, and only decommission the source resources once retention requirements and business approval are both satisfied.

---

### 2. How do you secure cross-cloud network connectivity (GCP ↔ Azure)?

**Answer:** Use encrypted VPN tunnels or cloud interconnects, enforce firewall/security groups on both sides, use mutually authenticated service endpoints, and centralize monitoring/audit of cross-cloud flows.

Grant only the network access that's actually needed, and use private endpoints.

**Mini-case:** We connected GCP and Azure via IPsec tunnels. Route filtering and firewall rules allowed only the required service ports, which stopped an attacker from moving laterally in case of a compromise.

**Detailed interview approach:**

I inventory the application, data, network, identity, DNS, compliance, and managed-service dependencies, and set clear RTO/RPO targets and acceptance tests. I build the target environment using separate, provider-specific Terraform modules and private connectivity, migrate one low-risk service first, and keep data replicating continuously.

While both environments run in parallel, I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic or DNS, with a tested rollback window, and I keep tight control over which side owns writes so I don't end up with split brain.

Once things are stable, I reconcile Terraform and its state (so the tracked state matches what's actually deployed), revoke any temporary cross-cloud access, archive the evidence, and only decommission the source resources once retention requirements and business approval are both satisfied.
