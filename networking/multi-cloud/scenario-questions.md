# Multi-Cloud Networking Scenario Questions

### 1. How do you implement policy-based routing in multi-cloud CI/CD?

**Answer:** Use traffic managers (Azure Traffic Manager, GCP Load Balancing), enforce routing rules per region, monitor latency, and shift traffic automatically on failures. **Mini-case:** Our hybrid GCP-Azure app used geo-routing; during an Azure region outage, traffic auto-shifted to GCP with <2 min downtime.

**Detailed interview approach:**

I inventory application, data, network, identity, DNS, compliance, and managed-service dependencies and define RTO/RPO and acceptance tests. I build the target with separate provider-specific Terraform modules and private connectivity, migrate a low-risk service first, and continuously replicate data. During parallel operation I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic/DNS with a tested rollback window; write ownership is carefully controlled to avoid split brain. After stabilization I reconcile Terraform/state, revoke cross-cloud temporary access, archive evidence, and decommission source resources only after retention and business approval.

---

### 2. How do you secure cross-cloud network connectivity (GCP ↔ Azure)?

**Answer:** Use encrypted VPN tunnels or cloud interconnects, enforce firewall/security groups on both sides, use mutually authenticated service endpoints, and centralize monitoring/audit of cross-cloud flows. Use least-privilege network access and private endpoints. **Mini-case:** We connected GCP and Azure via IPsec tunnels; route filtering and firewall rules allowed only required service ports, preventing lateral movement in case of compromise.

**Detailed interview approach:**

I inventory application, data, network, identity, DNS, compliance, and managed-service dependencies and define RTO/RPO and acceptance tests. I build the target with separate provider-specific Terraform modules and private connectivity, migrate a low-risk service first, and continuously replicate data. During parallel operation I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic/DNS with a tested rollback window; write ownership is carefully controlled to avoid split brain. After stabilization I reconcile Terraform/state, revoke cross-cloud temporary access, archive evidence, and decommission source resources only after retention and business approval.
