# Azure DevOps Scenario Questions

---

### 1. How do you troubleshoot Azure DevOps "401 Unauthorized" errors?

**Answer:** Check service connection → Rotate PAT/SPN credentials → Validate RBAC.

**Detailed interview approach:**

I start from the exact pipeline error and execution context.

For authentication failures I inspect the service connection type, tenant/subscription, federated credential or secret/certificate expiry, endpoint scope, and target RBAC; for queued/agent failures I inspect pool demand/capability matching, agent online status, parallel-job quota, and agent diagnostics.

I reproduce using the same identity/agent without printing tokens, compare Azure activity and Entra sign-in logs, and make the smallest RBAC or configuration correction.

I prefer workload identity federation/managed identity over long-lived PATs, scope service connections to approved pipelines, rotate exposed credentials, and verify a real read/deploy operation plus audit logs after the fix.

---

### 2. How do you troubleshoot Azure DevOps pipeline stuck at "queued"?

**Answer:** No available agents → Check agent pool → Scale agents → Verify concurrency limits.

**Detailed interview approach:**

I inspect the queue reason, executor usage, node labels, offline status, and controller/agent logs. A job can wait because no agent matches its label, all executors are busy, a node is disconnected, a throttle/concurrency rule applies, or cloud-agent provisioning has failed.

I check `Manage Nodes`, queue/build metrics, agent pod/VM events, network and credentials, then restore or scale the correct agent pool. I do not add controller executors as a shortcut.

Preventive measures include ephemeral autoscaled agents, capacity and queue-time alerts, sensible labels/quotas, agent image health checks, timeouts, and separating long or privileged workloads.

---

### 3. How do you enforce least privilege (only the permissions needed) access in GCP/Azure pipelines?

**Answer:** Use service accounts with minimum roles → Rotate keys regularly → Audit pipeline IAM policies.

**Detailed interview approach:**

I identify the exact principal, resource, action, scope, and denied condition from the error and cloud audit logs. I inspect effective IAM/RBAC including inherited roles, deny policies, conditional bindings, tenant/project/subscription, and token audience/expiry.

I reproduce a harmless call with the same identity, then grant the narrow predefined/custom role at the smallest scope—never owner/admin just to make the pipeline pass. Workload identity or managed identity replaces static service-account keys.

For a leaked key I disable/revoke it immediately, review its use and resources changed, rotate related secrets, and rebuild the workload identity path. Access reviews, expiry, policy tests, and audit alerts prevent role sprawl.

---

### 4. How do you troubleshoot Azure DevOps pipeline agent errors?

**Answer:** Check agent logs → Verify network connectivity → Restart agent service → Re register agent if required.

**Detailed interview approach:**

I inspect the queue reason, executor usage, node labels, offline status, and controller/agent logs. A job can wait because no agent matches its label, all executors are busy, a node is disconnected, a throttle/concurrency rule applies, or cloud-agent provisioning has failed.

I check `Manage Nodes`, queue/build metrics, agent pod/VM events, network and credentials, then restore or scale the correct agent pool. I do not add controller executors as a shortcut.

Preventive measures include ephemeral autoscaled agents, capacity and queue-time alerts, sensible labels/quotas, agent image health checks, timeouts, and separating long or privileged workloads.

---

### 5. How do you implement canary release in Azure DevOps?

**Answer:** Use Azure Traffic Manager/App Gateway → Route small % of traffic to new version → Gradually increase if stable.

**Detailed interview approach:**

I deploy an immutable (not changed after creation) artifact through a strategy matched to risk: rolling for routine stateless changes, canary for metric-based exposure, or blue-green for fast traffic switching.

The pipeline runs prechecks, deploys to a small/no-traffic target, performs readiness and business smoke tests, then advances while watching error rate, latency, saturation (how close a resource is to its limit), and SLO/error budget.

If thresholds fail it stops traffic and rolls back to the previous artifact/config; database changes use expand-and-contract because application rollback cannot undo destructive schema changes. I verify recovery, record the result, and improve the test or guard that should have caught the failure earlier.

---

### 6. How do you implement blue-green deployment in Azure DevOps?

**Answer:** Use deployment slots (App Service) → Route traffic between slots → Rollback to blue if green fails.

**Detailed interview approach:**

I deploy an immutable (not changed after creation) artifact through a strategy matched to risk: rolling for routine stateless changes, canary for metric-based exposure, or blue-green for fast traffic switching.

The pipeline runs prechecks, deploys to a small/no-traffic target, performs readiness and business smoke tests, then advances while watching error rate, latency, saturation (how close a resource is to its limit), and SLO/error budget.

If thresholds fail it stops traffic and rolls back to the previous artifact/config; database changes use expand-and-contract because application rollback cannot undo destructive schema changes. I verify recovery, record the result, and improve the test or guard that should have caught the failure earlier.

---

### 7. How do you troubleshoot a failed GCP Cloud Build or Azure DevOps pipeline?

**Answer:** Check build logs → Validate service account permissions → Verify YAML pipeline definition → Retry with verbose logs.

**Detailed interview approach:**

I start from the exact pipeline error and execution context.

For authentication failures I inspect the service connection type, tenant/subscription, federated credential or secret/certificate expiry, endpoint scope, and target RBAC; for queued/agent failures I inspect pool demand/capability matching, agent online status, parallel-job quota, and agent diagnostics.

I reproduce using the same identity/agent without printing tokens, compare Azure activity and Entra sign-in logs, and make the smallest RBAC or configuration correction.

I prefer workload identity federation/managed identity over long-lived PATs, scope service connections to approved pipelines, rotate exposed credentials, and verify a real read/deploy operation plus audit logs after the fix.
