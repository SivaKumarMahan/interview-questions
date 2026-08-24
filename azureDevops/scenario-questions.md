# Azure DevOps Scenario Questions

---

### 1. How do you troubleshoot Azure DevOps "401 Unauthorized" errors?

**Answer:** Check the service connection, rotate the PAT or service-principal credentials, then validate RBAC.

**Detailed interview approach:**

I start from the exact pipeline error and the context it failed in.

For authentication failures, I check the service connection type, the tenant and subscription, whether the federated credential or secret has expired, the endpoint's scope, and the target's RBAC. For a job stuck queued or an agent failure, I check pool demand and capability matching, whether the agent is online, the parallel-job quota, and the agent's own diagnostics.

I reproduce the problem using the same identity and agent, without ever printing tokens, and compare Azure activity logs against Entra sign-in logs to find the smallest fix.

I prefer workload identity federation or managed identity over long-lived PATs, scope each service connection to only the pipelines that need it, rotate any credential that's been exposed, and after the fix, confirm a real read or deploy actually works and check the audit logs.

---

### 2. How do you troubleshoot Azure DevOps pipeline stuck at "queued"?

**Answer:** No available agents. Check the agent pool, scale up agents, and verify concurrency limits.

**Detailed interview approach:**

I look at the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can sit waiting because no agent matches its labels, every executor is busy, a node has disconnected, a throttle or concurrency rule is in effect, or a cloud agent failed to provision.

I check **Manage Nodes**, queue and build metrics, agent pod or VM events, network and credentials, then restore or scale the right agent pool. I don't just add more executors to the controller as a shortcut.

To prevent this going forward: use ephemeral, autoscaled agents, set up capacity and queue-time alerts, use sensible labels and quotas, check agent image health, set timeouts, and keep long or privileged jobs separate from the rest.

---

### 3. How do you enforce least privilege access in GCP or Azure pipelines?

**Answer:** Use service accounts with the minimum roles they need, rotate keys regularly, and audit pipeline IAM policies.

**Detailed interview approach:**

I start from the exact principal, resource, action, scope, and denial from the error and the cloud's audit logs. I check the effective IAM or RBAC, including inherited roles, deny policies, conditional bindings, the tenant/project/subscription, and the token's audience and expiry.

I reproduce with a harmless call using the same identity, then grant the narrowest predefined or custom role at the smallest possible scope — never Owner or Admin just to make the pipeline pass. Workload identity or managed identity replaces static service-account keys wherever it can.

If a key has leaked, I disable or revoke it right away, check what it was used for and what it changed, rotate anything related, and rebuild the identity path properly using workload identity. Regular access reviews, expiry dates, policy tests, and audit alerts keep roles from creeping wider over time.

---

### 4. How do you troubleshoot Azure DevOps pipeline agent errors?

**Answer:** Check the agent logs, verify network connectivity, restart the agent service, and re-register the agent if needed.

**Detailed interview approach:**

I look at the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can sit waiting because no agent matches its labels, every executor is busy, a node has disconnected, a throttle or concurrency rule is in effect, or a cloud agent failed to provision.

I check **Manage Nodes**, queue and build metrics, agent pod or VM events, network and credentials, then restore or scale the right agent pool. I don't just add more executors to the controller as a shortcut.

To prevent this going forward: use ephemeral, autoscaled agents, set up capacity and queue-time alerts, use sensible labels and quotas, check agent image health, set timeouts, and keep long or privileged jobs separate from the rest.

---

### 5. How do you implement canary release in Azure DevOps?

**Answer:** Use Azure Traffic Manager or Application Gateway, route a small percentage of traffic to the new version, and increase it gradually if it's stable.

**Detailed interview approach:**

I deploy one artifact that never changes once built, using a rollout strategy matched to the risk: rolling for routine stateless changes, canary when I want to watch metrics before going further, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or no-traffic target, runs readiness and business smoke tests, then gradually sends more traffic while watching error rate, latency, how close resources are to their limits, and the service's error budget.

If any threshold fails, it stops sending traffic and rolls back to the previous version. Database changes use expand-and-contract instead, since rolling back the application can't undo a destructive schema change. After recovery, I confirm things actually work again, record what happened, and improve whatever test or guard should have caught the problem sooner.

---

### 6. How do you implement blue-green deployment in Azure DevOps?

**Answer:** Use App Service deployment slots, route traffic between them, and roll back to the old slot if the new one fails.

**Detailed interview approach:**

I deploy one artifact that never changes once built, using a rollout strategy matched to the risk: rolling for routine stateless changes, canary when I want to watch metrics before going further, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or no-traffic target, runs readiness and business smoke tests, then gradually sends more traffic while watching error rate, latency, how close resources are to their limits, and the service's error budget.

If any threshold fails, it stops sending traffic and rolls back to the previous version. Database changes use expand-and-contract instead, since rolling back the application can't undo a destructive schema change. After recovery, I confirm things actually work again, record what happened, and improve whatever test or guard should have caught the problem sooner.

---

### 7. How do you troubleshoot a failed GCP Cloud Build or Azure DevOps pipeline?

**Answer:** Check the build logs, validate the service account's permissions, verify the YAML pipeline definition, and retry with verbose logging.

**Detailed interview approach:**

I start from the exact pipeline error and the context it failed in.

For authentication failures, I check the service connection type, the tenant and subscription, whether the federated credential or secret has expired, the endpoint's scope, and the target's RBAC. For a job stuck queued or an agent failure, I check pool demand and capability matching, whether the agent is online, the parallel-job quota, and the agent's own diagnostics.

I reproduce the problem using the same identity and agent, without ever printing tokens, and compare Azure activity logs against Entra sign-in logs to find the smallest fix.

I prefer workload identity federation or managed identity over long-lived PATs, scope each service connection to only the pipelines that need it, rotate any credential that's been exposed, and after the fix, confirm a real read or deploy actually works and check the audit logs.
