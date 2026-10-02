# Azure DevOps: Troubleshooting

> Diagnosing failed pipelines, 401 errors, jobs stuck in the queue, and agent problems.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you troubleshoot a failed Azure Pipeline?</summary>

**Answer:**

I find the first task or stage that actually failed and figure out what kind of failure it is: YAML compilation, a trigger, a queued or agent problem, checkout, a tool command, a service connection, a variable, an artifact, or the deployment itself.

I look at the logs, the timeline, any recent changes to YAML, templates, or tasks, agent demands and capabilities, disk, network, and DNS, permissions, variable scope, artifact paths, and the status of any external service involved. For a deployment failure, I also check the Azure Activity Log, AKS events, policy, quota, and the target's health.

I reproduce it with the same tool image and parameters in a safe environment, fix the actual cause, rerun only the stage that's safe to repeat, and confirm the output downstream looks right. To prevent it happening again, I might pin a version, add an earlier check, add a timeout or more capacity, or make the error message clearer.

</details>

<details><summary>Q2. [Intermediate] How do you troubleshoot a failed GCP Cloud Build or Azure DevOps pipeline? <em>(scenario)</em></summary>

**Answer:** Check the build logs, validate the service account's permissions, verify the YAML pipeline definition, and retry with verbose logging.

**Detailed interview approach:**

I start from the exact pipeline error and the context it failed in.

For authentication failures, I check the service connection type, the tenant and subscription, whether the federated credential or secret has expired, the endpoint's scope, and the target's RBAC. For a job stuck queued or an agent failure, I check pool demand and capability matching, whether the agent is online, the parallel-job quota, and the agent's own diagnostics.

I reproduce the problem using the same identity and agent, without ever printing tokens, and compare Azure activity logs against Entra sign-in logs to find the smallest fix.

I prefer workload identity federation or managed identity over long-lived PATs, scope each service connection to only the pipelines that need it, rotate any credential that's been exposed, and after the fix, confirm a real read or deploy actually works and check the audit logs.

</details>

<details><summary>Q3. [Intermediate] How do you troubleshoot Azure DevOps "401 Unauthorized" errors? <em>(scenario)</em></summary>

**Answer:** Check the service connection, rotate the PAT or service-principal credentials, then validate RBAC.

**Detailed interview approach:**

I start from the exact pipeline error and the context it failed in.

For authentication failures, I check the service connection type, the tenant and subscription, whether the federated credential or secret has expired, the endpoint's scope, and the target's RBAC. For a job stuck queued or an agent failure, I check pool demand and capability matching, whether the agent is online, the parallel-job quota, and the agent's own diagnostics.

I reproduce the problem using the same identity and agent, without ever printing tokens, and compare Azure activity logs against Entra sign-in logs to find the smallest fix.

I prefer workload identity federation or managed identity over long-lived PATs, scope each service connection to only the pipelines that need it, rotate any credential that's been exposed, and after the fix, confirm a real read or deploy actually works and check the audit logs.

</details>

<details><summary>Q4. [Intermediate] How do you troubleshoot Azure DevOps pipeline stuck at "queued"? <em>(scenario)</em></summary>

**Answer:** No available agents. Check the agent pool, scale up agents, and verify concurrency limits.

**Detailed interview approach:**

I look at the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can sit waiting because no agent matches its labels, every executor is busy, a node has disconnected, a throttle or concurrency rule is in effect, or a cloud agent failed to provision.

I check **Manage Nodes**, queue and build metrics, agent pod or VM events, network and credentials, then restore or scale the right agent pool. I don't just add more executors to the controller as a shortcut.

To prevent this going forward: use ephemeral, autoscaled agents, set up capacity and queue-time alerts, use sensible labels and quotas, check agent image health, set timeouts, and keep long or privileged jobs separate from the rest.

</details>

<details><summary>Q5. [Intermediate] How do you troubleshoot Azure DevOps pipeline agent errors? <em>(scenario)</em></summary>

**Answer:** Check the agent logs, verify network connectivity, restart the agent service, and re-register the agent if needed.

**Detailed interview approach:**

I look at the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can sit waiting because no agent matches its labels, every executor is busy, a node has disconnected, a throttle or concurrency rule is in effect, or a cloud agent failed to provision.

I check **Manage Nodes**, queue and build metrics, agent pod or VM events, network and credentials, then restore or scale the right agent pool. I don't just add more executors to the controller as a shortcut.

To prevent this going forward: use ephemeral, autoscaled agents, set up capacity and queue-time alerts, use sensible labels and quotas, check agent image health, set timeouts, and keep long or privileged jobs separate from the rest.

</details>

<details><summary>Q6. [Intermediate] Azure DevOps Pipeline Not Triggering for Feature Branches</summary>

#### The YAML

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - script: echo "Build started"
```

A developer pushes to `feature/payment-api`, but the pipeline doesn't run.

#### Is this expected?

**Yes.** The `trigger` section explicitly lists only `main`, so Azure DevOps only creates a CI run automatically for pushes to `main`. Pushing to any other branch, including `feature/payment-api`, simply doesn't match the trigger and is correctly skipped — this isn't a bug.

#### Fix — trigger on both `main` and `feature/*`

```yaml
trigger:
  branches:
    include:
      - main
      - feature/*

pool:
  vmImage: ubuntu-latest

steps:
  - script: echo "Build started"
```

Using `branches: include:` (instead of the short list form) is required once you need wildcard patterns like `feature/*`.

#### Short interview answer

"Yes, this is expected — the trigger only lists `main`, so pushes to any other branch, including `feature/payment-api`, are correctly ignored by design, not a bug. To make it trigger for both, I'd rewrite the trigger using the `branches: include:` form with both `main` and `feature/*` listed, since wildcard patterns require that expanded syntax instead of the short list form."

</details>
