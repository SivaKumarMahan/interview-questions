# Cloud Scenario Questions

### 1. How do you ensure data encryption in GCP/Azure storage?

**Answer:** Enable default encryption (KMS-managed keys) → For extra security, use customer-managed encryption keys (CMEK).

**Detailed interview approach:**

Cloud storage already encrypts data at rest, but I confirm the compliance requirement: provider-managed keys or customer-managed keys, rotation, region, separation of duties, and audit retention.

For CMEK I place the key in the approved KMS/Key Vault, give only the storage service identity encrypt/decrypt permission, enable rotation and deletion protection, and keep key administration separate from data administration.

I also enforce TLS and private endpoints for data in transit, disable public access, and log object and key operations. I test upload/download with the application identity and a denied identity, then alert on public access, key disablement, and unusual reads.

Backups must use equally protected keys.

---

### 2. How do you handle GCP IAM service account key leaks?

**Answer:** Immediately disable/rotate compromised key → Audit access logs → Re-deploy workloads with new key → Enforce least privilege (only the permissions needed).

**Detailed interview approach:**

Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak.

Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient.

Pre-commit/server-side scans, protected logs, least privilege (only the permissions needed), expiry, and rotation tests prevent recurrence.

---

### 3. How do you migrate workloads from GCP to Azure with minimal downtime?

**Answer:** Use containerization, abstract with Terraform modules, set up dual cloud deployments temporarily, sync data continuously, and cut traffic gradually. Mini-case: We ran dual GCP+Azure clusters for a week; once data sync stabilized, DNS cutover moved traffic fully to Azure.
**Detailed interview approach:**

I inventory application, data, network, identity, DNS, compliance, and managed-service dependencies and define RTO/RPO and acceptance tests. I build the target with separate provider-specific Terraform modules and private connectivity, migrate a low-risk service first, and continuously replicate data.

During parallel operation I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic/DNS with a tested rollback window; write ownership is carefully controlled to avoid split brain.

After stabilization I reconcile (make actual state match desired state) Terraform/state, revoke cross-cloud temporary access, archive evidence, and decommission source resources only after retention and business approval.

---

### 4. How do you manage CI/CD for hybrid cloud (on-prem + cloud)?

**Answer:** Use Jenkins/Azure DevOps self-hosted agents → Connect VPN to on-prem → Manage infra via Terraform/Ansible.

**Detailed interview approach:**

I inventory application, data, network, identity, DNS, compliance, and managed-service dependencies and define RTO/RPO and acceptance tests. I build the target with separate provider-specific Terraform modules and private connectivity, migrate a low-risk service first, and continuously replicate data.

During parallel operation I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic/DNS with a tested rollback window; write ownership is carefully controlled to avoid split brain.

After stabilization I reconcile (make actual state match desired state) Terraform/state, revoke cross-cloud temporary access, archive evidence, and decommission source resources only after retention and business approval.

---

### 5. How do you handle GCP IAM role sprawl?

**Answer:** Audit IAM bindings → Merge duplicate roles → Use custom roles → Apply principle of least privilege (only the permissions needed).

**Detailed interview approach:**

I identify the exact principal, resource, action, scope, and denied condition from the error and cloud audit logs. I inspect effective IAM/RBAC including inherited roles, deny policies, conditional bindings, tenant/project/subscription, and token audience/expiry.

I reproduce a harmless call with the same identity, then grant the narrow predefined/custom role at the smallest scope—never owner/admin just to make the pipeline pass. Workload identity or managed identity replaces static service-account keys.

For a leaked key I disable/revoke it immediately, review its use and resources changed, rotate related secrets, and rebuild the workload identity path. Access reviews, expiry, policy tests, and audit alerts prevent role sprawl.

---

### 6. How do you troubleshoot Azure VM not starting?

**Answer:** Check Azure Activity Logs → Verify quota limits → Validate boot diagnostics → Recreate VM if corrupted.

**Detailed interview approach:**

I begin with Azure Activity Log and the VM instance/power state, then inspect subscription quota, locks/policy, disk attachment, networking, extensions, and Boot Diagnostics screenshot/serial log.

A control-plane start failure differs from an OS boot failure: quota/allocation needs capacity or size/zone action, while filesystem, fstab, kernel, or extension issues need rescue access.

I preserve the OS disk through a snapshot, use Serial Console or attach a copy to a recovery VM, correct the specific boot problem, and reattach/start. Recreating the VM is a last step using existing protected disks or image/IaC.

I verify OS, extensions, network and application health and add backup/monitoring.

---

### 7. How do you troubleshoot GCP Cloud Build quota exceeded error?

**Answer:** Check quotas in GCP console → Optimize build concurrency → Request quota increase → Split builds.

**Detailed interview approach:**

I identify the exact quota metric, project/region, current usage, concurrency, and which builds consume it from Cloud Build logs and quota dashboards. I stop retry storms, cancel obsolete duplicate builds, and reduce concurrency or route approved work to another pool while protecting urgent releases.

Permanent changes include batching stages, caching artifacts, right-sizing worker pools, path-based triggers, and requesting a justified quota increase with growth evidence. I also check service-account/API quotas and regional capacity because the message can be indirect.

Queue time and quota utilization alerts trigger before exhaustion, and idempotent (safe to run more than once) pipeline stages make a delayed retry safe.

---

### 8. How do you troubleshoot a failing GCP Cloud Function deployment in CI/CD?

**Answer:** Check logs in Cloud Build → Validate IAM permissions → Ensure environment variables are configured → Rebuild with correct runtime.

**Detailed interview approach:**

I inspect the deployment stage and cloud build logs for source/package errors, unsupported runtime, entry point, dependency lock, service-account permission, API enablement, region/quota, environment limits, and network configuration.

I compare the produced artifact and command with a known-good release and test the handler locally or in a lower environment.

If deployment succeeds but health fails, I inspect cold-start/runtime logs, memory/timeout, secret access, VPC connector, and downstream calls. I correct code or IaC and redeploy the same immutable (not changed after creation) artifact through approval, then invoke a real test and monitor error/latency.

Pinned runtimes/dependencies, packaging tests, quota alerts, and staged traffic reduce recurrence.

---

### 9. How do you implement centralized secrets management in multi-cloud (GCP + Azure)?

**Answer:** Use HashiCorp Vault, or integrate GCP Secret Manager + Azure Key Vault with CI/CD → Fetch secrets at runtime.

**Detailed interview approach:**

I use a primary enterprise Vault or a controlled federation pattern with Azure Key Vault and GCP Secret Manager close to workloads. Applications and pipelines authenticate using managed/workload identity and fetch secrets at runtime; no static cross-cloud credentials are placed in Git or images.

Naming, ownership, access policy, rotation, expiry, audit, replication, and break-glass recovery are standardized, while secret values remain scoped to the environment. Rotation overlaps old/new values, verifies every consumer, then revokes old access.

I test provider outage and cache behavior without allowing indefinite stale credentials. Central inventory and audit give governance, but regional stores and short-lived dynamic credentials reduce latency and scope of impact.

---

### 10. How do you troubleshoot GCP IAM permission denied errors?

**Answer:** Check service account roles → Use `gcloud projects get-iam-policy` → Grant least privilege (only the permissions needed) role needed → Retry operation.

**Detailed interview approach:**

I identify the exact principal, resource, action, scope, and denied condition from the error and cloud audit logs. I inspect effective IAM/RBAC including inherited roles, deny policies, conditional bindings, tenant/project/subscription, and token audience/expiry.

I reproduce a harmless call with the same identity, then grant the narrow predefined/custom role at the smallest scope—never owner/admin just to make the pipeline pass. Workload identity or managed identity replaces static service-account keys.

For a leaked key I disable/revoke it immediately, review its use and resources changed, rotate related secrets, and rebuild the workload identity path. Access reviews, expiry, policy tests, and audit alerts prevent role sprawl.

---

### 11. How do you rotate service account keys in GCP/Azure?

**Answer:** Automate with GCP IAM key rotation or Azure Key Vault rotation policies → Update CI/CD pipelines to use new keys.

**Detailed interview approach:**

Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak.

Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient.

Pre-commit/server-side scans, protected logs, least privilege (only the permissions needed), expiry, and rotation tests prevent recurrence.

---

### 12. How do you migrate workloads from GCP to Azure using Terraform?

**Answer:** Write separate Terraform provider configs for GCP and Azure → Export state from GCP → Import resources in Azure → Test in lower env before prod.

**Detailed interview approach:**

I inventory application, data, network, identity, DNS, compliance, and managed-service dependencies and define RTO/RPO and acceptance tests. I build the target with separate provider-specific Terraform modules and private connectivity, migrate a low-risk service first, and continuously replicate data.

During parallel operation I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic/DNS with a tested rollback window; write ownership is carefully controlled to avoid split brain.

After stabilization I reconcile (make actual state match desired state) Terraform/state, revoke cross-cloud temporary access, archive evidence, and decommission source resources only after retention and business approval.

---

### 13. What if your GCP/Azure costs suddenly spike?

**Answer:**

- Check billing reports.
- Identify unused resources (VMs, disks, load balancers).
- Set budgets & alerts.
- Use autoscaling + reserved instances.

**Detailed interview approach:**

I compare cost by service, account/subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the rise comes from real traffic, runaway autoscaling, orphaned resources, log/egress volume, a pricing/commitment change, or compromised compute.

I contain safely with budgets, scaling caps, quotas, or stopping confirmed non-production waste—without deleting stateful production resources blindly. Terraform plans receive cost estimates and policy/approval above thresholds.

Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved/spot choices, and owner showback make optimization continuous, and I verify performance/SLOs after reducing cost.

---

### 14. How do you manage multi-cloud deployments (GCP + Azure)?

**Answer:** Use Terraform with multiple providers → Create modules for each cloud → Keep separate state files for GCP and Azure.

**Detailed interview approach:**

I inventory application, data, network, identity, DNS, compliance, and managed-service dependencies and define RTO/RPO and acceptance tests. I build the target with separate provider-specific Terraform modules and private connectivity, migrate a low-risk service first, and continuously replicate data.

During parallel operation I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic/DNS with a tested rollback window; write ownership is carefully controlled to avoid split brain.

After stabilization I reconcile (make actual state match desired state) Terraform/state, revoke cross-cloud temporary access, archive evidence, and decommission source resources only after retention and business approval.

---

### 15. How do you automate infrastructure scaling in cloud?

**Answer:** Configure Auto Scaling Groups in GCP (Instance Groups) or Azure (VM Scale Sets) → Integrate with Terraform for automation.

**Detailed interview approach:**

I select the scaling signal from the workload: request/queue depth or latency is often better than CPU alone. The application tier uses an autoscaling group, VM scale set, Kubernetes HPA, or serverless concurrency with tested minimum, maximum, cooldown/stabilization, health checks, and graceful scale-in.

Node/cluster autoscaling supplies underlying capacity; databases and downstream quotas are scaled or protected separately. Terraform defines the policy and alarms, while runtime controllers make frequent decisions.

I load-test scale-up and failure behavior, confirm new instances become Ready before traffic, prevent removal of busy/stateful capacity, and add cost/maximum alerts. Manual override and rollback are documented for bad metrics or runaway scaling.
