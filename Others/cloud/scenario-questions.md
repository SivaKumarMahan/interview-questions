# Cloud Scenario Questions

### 1. How do you ensure data encryption in GCP/Azure storage?

**Answer:** Turn on default encryption with KMS-managed keys, and for extra security, use customer-managed encryption keys (CMEK).

**Detailed interview approach:**

Cloud storage already encrypts data at rest, but I still confirm the compliance requirement: provider-managed or customer-managed keys, rotation, region, separation of duties, and audit retention.

For CMEK, I place the key in the approved KMS/Key Vault, give only the storage service identity encrypt/decrypt permission, turn on rotation and deletion protection, and keep key administration separate from data administration.

I also enforce TLS and private endpoints for data in transit, disable public access, and log every object and key operation. I test upload and download with the application's identity and with a denied identity, then set alerts for public access, key disablement, and unusual reads.

Backups need to use keys that are just as well protected.

---

### 2. How do you handle GCP IAM service account key leaks?

**Answer:** Immediately disable and rotate the compromised key, audit access logs, redeploy workloads with the new key, and give the new identity only the access it needs.

**Detailed interview approach:**

Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store — never in Git, YAML, images, command arguments, or artifacts. Jobs get a short-lived identity and fetch only the secret they need for that stage. Masking is a backup control, since an encoded or transformed value can still leak.

Rotation works with an overlap: issue the new value, update consumers, verify it works, revoke the old value, and audit for failures. If a scan finds a committed secret, I revoke it right away, check how it was used, remove it from active history where appropriate, and rotate anything downstream that trusted it — just deleting the line isn't enough.

Pre-commit and server-side scans, protected logs, minimal access, expiry, and rotation tests all help prevent it from happening again.

---

### 3. How do you migrate workloads from GCP to Azure with minimal downtime?

**Answer:** Use containerization, abstract infrastructure with Terraform modules, run both clouds side by side temporarily, sync data continuously, and shift traffic over gradually. Mini-case: we ran GCP and Azure clusters side by side for a week. Once data sync was stable, a DNS cutover moved traffic fully to Azure.
**Detailed interview approach:**

I inventory the application, data, network, identity, DNS, compliance, and managed-service dependencies, and define the RTO/RPO and acceptance tests up front. I build the target environment with separate provider-specific Terraform modules and private connectivity, migrate one low-risk service first, and keep data replicating continuously.

While both environments run in parallel, I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic or DNS with a tested rollback window, and write ownership is carefully controlled so two sides don't both think they own the data.

Once things are stable, I bring Terraform state back in line with reality, revoke any temporary cross-cloud access, archive the evidence, and only decommission the source resources after retention requirements and business approval are met.

---

### 4. How do you manage CI/CD for hybrid cloud (on-prem + cloud)?

**Answer:** Use self-hosted Jenkins or Azure DevOps agents, connect to on-prem over VPN, and manage infrastructure with Terraform/Ansible.

**Detailed interview approach:**

I inventory the application, data, network, identity, DNS, compliance, and managed-service dependencies, and define the RTO/RPO and acceptance tests up front. I build the target environment with separate provider-specific Terraform modules and private connectivity, migrate one low-risk service first, and keep data replicating continuously.

While both environments run in parallel, I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic or DNS with a tested rollback window, and write ownership is carefully controlled so two sides don't both think they own the data.

Once things are stable, I bring Terraform state back in line with reality, revoke any temporary cross-cloud access, archive the evidence, and only decommission the source resources after retention requirements and business approval are met.

---

### 5. How do you handle GCP IAM role sprawl?

**Answer:** Audit IAM bindings, merge duplicate roles, use custom roles, and give every identity only the access it needs.

**Detailed interview approach:**

I pin down the exact principal, resource, action, scope, and denied condition from the error and the cloud audit logs. I check the effective IAM/RBAC picture, including inherited roles, deny policies, conditional bindings, the tenant/project/subscription, and token audience and expiry.

I reproduce a harmless call with the same identity, then grant a narrow predefined or custom role at the smallest scope that works — never owner or admin just to unblock the pipeline. Workload identity or managed identity replaces static service-account keys.

If a key leaked, I disable or revoke it right away, check what it was used for and what it touched, rotate related secrets, and rebuild the workload identity path. Regular access reviews, expiry, policy tests, and audit alerts keep roles from sprawling over time.

---

### 6. How do you troubleshoot Azure VM not starting?

**Answer:** Check Azure Activity Logs, verify quota limits, validate boot diagnostics, and recreate the VM if it's corrupted.

**Detailed interview approach:**

I start with the Azure Activity Log and the VM's instance/power state, then check subscription quota, locks/policy, disk attachment, networking, extensions, and the Boot Diagnostics screenshot or serial log.

A control-plane start failure is different from an OS boot failure: a quota or allocation issue needs more capacity or a different size/zone, while a filesystem, fstab, kernel, or extension problem needs rescue access instead.

I protect the OS disk with a snapshot first, then use Serial Console or attach a copy to a recovery VM, fix the specific boot problem, and reattach and start it. Recreating the VM entirely is a last resort, using the existing protected disks or an image/IaC definition.

I verify the OS, extensions, network, and application are healthy, then add backup and monitoring so it's easier to catch next time.

---

### 7. How do you troubleshoot GCP Cloud Build quota exceeded error?

**Answer:** Check quotas in the GCP console, optimize build concurrency, request a quota increase, and split builds up.

**Detailed interview approach:**

I identify the exact quota metric, project/region, current usage, concurrency, and which builds are consuming it, using Cloud Build logs and the quota dashboards. I stop any retry storms, cancel obsolete duplicate builds, and either reduce concurrency or route approved work to another pool while protecting urgent releases.

For a permanent fix, I look at batching stages, caching artifacts, right-sizing worker pools, path-based triggers, and requesting a quota increase backed by real growth data. I also check service-account/API quotas and regional capacity, since the error message can point in the wrong direction.

Alerts on queue time and quota usage catch it before exhaustion, and making pipeline stages safe to rerun means a delayed retry doesn't cause a mess.

---

### 8. How do you troubleshoot a failing GCP Cloud Function deployment in CI/CD?

**Answer:** Check the logs in Cloud Build, validate IAM permissions, make sure environment variables are configured, and rebuild with the correct runtime.

**Detailed interview approach:**

I check the deployment stage and Cloud Build logs for source or packaging errors, an unsupported runtime, the entry point, a dependency lock issue, service-account permissions, API enablement, region/quota, environment limits, and network configuration.

I compare the artifact and command against a known-good release, and test the handler locally or in a lower environment.

If the deployment succeeds but the health check fails, I look at cold-start and runtime logs, memory and timeout settings, secret access, the VPC connector, and downstream calls. I fix the code or IaC, redeploy the exact same artifact through approval, then run a real test and watch error rate and latency.

Pinned runtimes and dependencies, packaging tests, quota alerts, and staged traffic all help prevent this from recurring.

---

### 9. How do you implement centralized secrets management in multi-cloud (GCP + Azure)?

**Answer:** Use HashiCorp Vault, or integrate GCP Secret Manager and Azure Key Vault with CI/CD, and fetch secrets at runtime.

**Detailed interview approach:**

I use either one primary enterprise Vault, or a controlled setup with Azure Key Vault and GCP Secret Manager each kept close to their own workloads. Applications and pipelines authenticate with managed/workload identity and fetch secrets at runtime — no static cross-cloud credentials ever go into Git or images.

Naming, ownership, access policy, rotation, expiry, audit, replication, and break-glass recovery are all standardized, while the actual secret values stay scoped to their environment. Rotation overlaps the old and new values, verifies every consumer picked up the change, then revokes the old access.

I test what happens during a provider outage and how caching behaves, without letting stale credentials linger indefinitely. A central inventory and audit trail gives good governance, while regional stores and short-lived dynamic credentials keep latency low and the blast radius small.

---

### 10. How do you troubleshoot GCP IAM permission denied errors?

**Answer:** Check the service account's roles, use `gcloud projects get-iam-policy`, grant the minimal role actually needed, and retry the operation.

**Detailed interview approach:**

I pin down the exact principal, resource, action, scope, and denied condition from the error and the cloud audit logs. I check the effective IAM/RBAC picture, including inherited roles, deny policies, conditional bindings, the tenant/project/subscription, and token audience and expiry.

I reproduce a harmless call with the same identity, then grant a narrow predefined or custom role at the smallest scope that works — never owner or admin just to unblock the pipeline. Workload identity or managed identity replaces static service-account keys.

If a key leaked, I disable or revoke it right away, check what it was used for and what it touched, rotate related secrets, and rebuild the workload identity path. Regular access reviews, expiry, policy tests, and audit alerts keep roles from sprawling over time.

---

### 11. How do you rotate service account keys in GCP/Azure?

**Answer:** Automate it with GCP IAM key rotation or Azure Key Vault rotation policies, and update CI/CD pipelines to use the new keys.

**Detailed interview approach:**

Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store — never in Git, YAML, images, command arguments, or artifacts. Jobs get a short-lived identity and fetch only the secret they need for that stage. Masking is a backup control, since an encoded or transformed value can still leak.

Rotation works with an overlap: issue the new value, update consumers, verify it works, revoke the old value, and audit for failures. If a scan finds a committed secret, I revoke it right away, check how it was used, remove it from active history where appropriate, and rotate anything downstream that trusted it — just deleting the line isn't enough.

Pre-commit and server-side scans, protected logs, minimal access, expiry, and rotation tests all help prevent it from happening again.

---

### 12. How do you migrate workloads from GCP to Azure using Terraform?

**Answer:** Write separate Terraform provider configs for GCP and Azure, export state from GCP, import the resources into Azure, and test in a lower environment before production.

**Detailed interview approach:**

I inventory the application, data, network, identity, DNS, compliance, and managed-service dependencies, and define the RTO/RPO and acceptance tests up front. I build the target environment with separate provider-specific Terraform modules and private connectivity, migrate one low-risk service first, and keep data replicating continuously.

While both environments run in parallel, I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic or DNS with a tested rollback window, and write ownership is carefully controlled so two sides don't both think they own the data.

Once things are stable, I bring Terraform state back in line with reality, revoke any temporary cross-cloud access, archive the evidence, and only decommission the source resources after retention requirements and business approval are met.

---

### 13. What if your GCP/Azure costs suddenly spike?

**Answer:**

- Check billing reports.
- Look for unused resources — VMs, disks, load balancers.
- Set budgets and alerts.
- Use autoscaling and reserved instances.

**Detailed interview approach:**

I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

---

### 14. How do you manage multi-cloud deployments (GCP + Azure)?

**Answer:** Use Terraform with multiple providers, create a module for each cloud, and keep separate state files for GCP and Azure.

**Detailed interview approach:**

I inventory the application, data, network, identity, DNS, compliance, and managed-service dependencies, and define the RTO/RPO and acceptance tests up front. I build the target environment with separate provider-specific Terraform modules and private connectivity, migrate one low-risk service first, and keep data replicating continuously.

While both environments run in parallel, I compare correctness, latency, observability, backup, security, and cost. Cutover uses weighted traffic or DNS with a tested rollback window, and write ownership is carefully controlled so two sides don't both think they own the data.

Once things are stable, I bring Terraform state back in line with reality, revoke any temporary cross-cloud access, archive the evidence, and only decommission the source resources after retention requirements and business approval are met.

---

### 15. How do you automate infrastructure scaling in cloud?

**Answer:** Configure autoscaling groups in GCP (Instance Groups) or Azure (VM Scale Sets), and manage them through Terraform.

**Detailed interview approach:**

I pick the scaling signal based on the workload — request or queue depth, or latency, is usually a better signal than CPU alone. The application tier uses an autoscaling group, VM scale set, Kubernetes HPA, or serverless concurrency, with a tested minimum, maximum, cooldown period, health checks, and graceful scale-in.

Node or cluster autoscaling provides the underlying capacity, while databases and downstream quotas are scaled or protected separately. Terraform defines the policy and alarms, and the runtime controllers make the frequent moment-to-moment decisions.

I load-test both scale-up and failure behavior, confirm new instances are actually ready before they take traffic, make sure busy or stateful capacity never gets removed by mistake, and add cost and maximum-size alerts. I also document a manual override and rollback for when metrics go bad or scaling runs away.
