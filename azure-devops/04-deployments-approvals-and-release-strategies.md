# Azure DevOps: Deployments, Approvals, and Release Strategies

> Approvals, gates, environments, deploying to AKS, and canary and blue-green releases.

## Key Concepts

### Approvals, Gates and Protected Resources

For YAML pipelines, configure **Approvals and checks** on the protected resource — usually an Azure DevOps environment, service connection, variable group, secure file, or agent pool.

The resource owner controls these checks outside the pipeline's YAML, so a contributor can't remove a production approval just by editing the pipeline file.

Useful checks include:

- Manual approval by the correct production owner
- Branch control requiring a protected release branch
- Required templates
- Business hours or change window
- Azure Monitor alert query
- Invoke Azure Function or REST API for an external policy decision
- Exclusive lock to prevent overlapping production deployments

Classic release pipelines still support pre-deployment approvals and gates, but new designs usually go with multistage YAML and protected environments instead. To actually enforce a Trivy scan result, make the scan stage fail on findings, publish the scan evidence, or expose an approved policy service through a supported check.

Running Trivy earlier in the pipeline doesn't automatically make it a gate on its own.

An approval is not a substitute for automated validation. The approver should be able to see the change, the exact artifact version, the test and scan results, which environment is affected, the deployment plan, health evidence, and how to roll back.

## Interview Questions

### 1. How do approvals and environments work in Azure Pipelines?

**Answer:**

An environment represents a deployment target and keeps a history of what's been deployed to it. Approvals and checks can require an authorized approver, a specific branch, business hours, an exclusive lock, an Azure Function or REST call for validation, or other gates before a deployment job is allowed to start.

I keep the critical checks outside the application's YAML, so a pull request can't quietly remove them. The approval screen should show the artifact's digest, what changed, the risk, test and scan evidence, and the rollback plan. Production identity is only made available to that specific protected deployment.

I test the approved, rejected, timed-out, and concurrent cases. Emergency bypass is tightly restricted and audited. Approval supports accountability, but it's not a substitute for automated health and policy checks.

### 2. How do you deploy to AKS from Azure Pipelines?

**Answer:**

The pipeline builds, tests, and scans an image, pushes its digest — a fixed reference that always points to that exact image — to ACR, then deploys it through Helm, plain manifests, or by updating a GitOps repository. Authentication uses workload identity or a service connection scoped to only what's needed.

```yaml
- task: HelmDeploy@0
  inputs:
    command: upgrade
    chartType: FilePath
    chartPath: chart
    releaseName: orders
    namespace: orders
    arguments: '--install --atomic --wait --set image.tag=$(Build.SourceVersion)'
```

I set up probes, resource requests, a security context, a PodDisruptionBudget, and NetworkPolicy. Secrets come from Key Vault through the CSI driver. After deployment I check the rollout, events, smoke tests, and error rate and latency. If something's wrong, it triggers a rollback of traffic or the release, and the evidence is kept.

### 3. How do you implement canary release in Azure DevOps? *(scenario)*

**Answer:** Use Azure Traffic Manager or Application Gateway, route a small percentage of traffic to the new version, and increase it gradually if it's stable.

**Detailed interview approach:**

I deploy one artifact that never changes once built, using a rollout strategy matched to the risk: rolling for routine stateless changes, canary when I want to watch metrics before going further, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or no-traffic target, runs readiness and business smoke tests, then gradually sends more traffic while watching error rate, latency, how close resources are to their limits, and the service's error budget.

If any threshold fails, it stops sending traffic and rolls back to the previous version. Database changes use expand-and-contract instead, since rolling back the application can't undo a destructive schema change. After recovery, I confirm things actually work again, record what happened, and improve whatever test or guard should have caught the problem sooner.

### 4. How do you implement blue-green deployment in Azure DevOps? *(scenario)*

**Answer:** Use App Service deployment slots, route traffic between them, and roll back to the old slot if the new one fails.

**Detailed interview approach:**

I deploy one artifact that never changes once built, using a rollout strategy matched to the risk: rolling for routine stateless changes, canary when I want to watch metrics before going further, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or no-traffic target, runs readiness and business smoke tests, then gradually sends more traffic while watching error rate, latency, how close resources are to their limits, and the service's error budget.

If any threshold fails, it stops sending traffic and rolls back to the previous version. Database changes use expand-and-contract instead, since rolling back the application can't undo a destructive schema change. After recovery, I confirm things actually work again, record what happened, and improve whatever test or guard should have caught the problem sooner.
