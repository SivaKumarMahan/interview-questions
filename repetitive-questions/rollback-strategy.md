# Repetitive Interview Questions

## What rollback strategy do you follow if an issue occurs?

### Detailed answer

In my project, rollback is a **planned recovery workflow**, not an improvised command after a failure. Every Production release has an immutable application version, deployment record, previous known-good version, health gates, rollback owner and tested recovery procedure.

Our normal application delivery path is:

```text
Git commit
-> tested Java artifact
-> immutable Docker image in Azure Container Registry
-> versioned Helm release in Azure Kubernetes Service
-> smoke tests and observability gates
-> promote, pause or roll back
```

If an issue occurs, my first actions are to **stop further promotion, limit user impact and preserve evidence**. I then decide whether rollback is safer than a forward-fix. I do not automatically roll back every incident because a previous application version might be incompatible with a completed database migration, changed configuration, rotated secret or external dependency.

### 1. Detect the problem

The deployment pipeline and monitoring platform watch both technical and business signals:

- Kubernetes rollout status and unavailable replicas.
- Readiness, startup and liveness probe failures.
- HTTP error rate and failed requests.
- Response latency and timeouts.
- CPU, memory, throttling, restarts and `OOMKilled` containers.
- JVM health, garbage collection and thread behavior.
- Application exceptions and dependency failures.
- Failed smoke, API, integration or synthetic tests.
- Business signals such as login, payment or transaction success rate.
- Azure Monitor, Log Analytics, Application Insights, Prometheus and Grafana alerts.

We compare these signals with the deployment timestamp, Git commit, ACR image digest, Helm revision, configuration version and recent platform changes. This helps establish whether the release caused the issue rather than reacting to an unrelated dependency or traffic event.

### 2. Stop the blast radius

When a release breaches an agreed threshold:

1. Pause the current deployment or promotion.
2. Prevent the same artifact from moving to another environment.
3. Stop increasing canary traffic or shift traffic away from the unhealthy version.
4. Keep healthy replicas or the previous environment serving users.
5. Notify the application owner, release owner and incident channel.
6. Capture Pod status, Events, logs, metrics, traces and deployment metadata.

I avoid repeatedly restarting Pods or rerunning the pipeline before collecting evidence. Those actions can temporarily hide the symptom and destroy useful troubleshooting information.

### 3. Decide between rollback and forward-fix

I use the following decision model:

| Situation | Preferred response |
| --- | --- |
| New application version causes errors and is backward compatible | Roll back to the previous image/Helm revision |
| Canary fails before most users receive traffic | Stop the canary and route all traffic to the stable version |
| Blue-green deployment fails before cutover | Keep traffic on the blue/old environment |
| Incorrect non-secret configuration caused the issue | Restore the previous reviewed configuration and redeploy |
| Secret is expired or revoked | Rotate/fix the secret and verify consumers; do not restore a compromised value |
| External service is temporarily unavailable | Apply the dependency runbook, timeout/circuit-breaker controls or traffic mitigation |
| Database migration is backward compatible | Roll back application code while keeping the compatible schema |
| Destructive database migration has completed | Do not blindly roll back the application; use the database recovery plan or a compatible forward-fix |
| Infrastructure change created the fault | Revert the IaC change in Git, review a new plan and apply the corrective change |
| Security vulnerability is actively exploitable | Remove traffic or disable the affected feature, rotate exposed credentials and deploy a remediated artifact |

The decision considers user impact, recovery time, data compatibility, security exposure and confidence in the previous release. During a major incident, one person coordinates the response so application, platform and database teams do not execute conflicting changes.

### 4. Application rollback in AKS

Our preferred rollback unit is the **immutable ACR image digest and versioned Helm release**. We retain the previous known-good image and Helm revision according to the release-retention policy.

Before Production deployment, the pipeline records:

```text
new Git commit
new ACR image digest
new Helm chart and release revision
previous known-good image digest
previous Helm revision
configuration version
database migration compatibility
```

If the application is managed by Helm, I inspect the release history and roll back through Helm:

```bash
helm history <release> -n <namespace>
helm rollback <release> <known-good-revision> \
  -n <namespace> \
  --wait \
  --timeout <approved-timeout>
```

I use the deployment mechanism that owns the resource. I do not run `kubectl rollout undo` against a Helm-managed Deployment and leave Helm believing a different revision is active. For a Deployment managed directly through Kubernetes manifests, the controlled alternative can be:

```bash
kubectl rollout history deployment/<name> -n <namespace>
kubectl rollout undo deployment/<name> -n <namespace> \
  --to-revision=<known-good-revision>
kubectl rollout status deployment/<name> -n <namespace> \
  --timeout=<approved-timeout>
```

The rollback uses the exact known-good digest, not `latest`. Kubernetes performs a controlled rollout, and readiness probes prevent the restored Pods from receiving traffic until they are ready.

### 5. Rollback by deployment strategy

#### Rolling deployment

I stop the current rollout and restore the previous image/Helm revision. Multiple replicas, readiness probes, PodDisruptionBudgets, sufficient surge capacity and graceful termination help keep healthy Pods available during recovery.

#### Canary deployment

Only a small percentage of traffic reaches the new version initially. If errors, latency or business metrics breach the threshold, I stop promotion, return canary traffic to zero and keep the stable version serving users. This limits the blast radius and is usually faster than replacing the entire workload.

#### Blue-green deployment

The old blue environment remains available while green is validated. If green fails before cutover, traffic stays on blue. If failure appears shortly after cutover, traffic can be shifted back to blue, provided database and external side effects remain compatible. Blue is removed only after the agreed observation window.

### 6. Configuration rollback

Application configuration is version-controlled separately from the container image. If a ConfigMap, Helm value, feature flag or routing rule causes the problem:

1. Identify the exact configuration difference.
2. Revert it through a pull request.
3. Run validation and policy checks.
4. Deploy the reviewed configuration through the pipeline.
5. Restart or reload only the workloads that require it.
6. Verify the application transaction and monitoring signals.

I do not make an undocumented console or `kubectl edit` change and leave it in Production. If an emergency manual change is necessary, it is time-bound, recorded and immediately reconciled back into Git to prevent configuration drift.

### 7. Secret and certificate failures

Secrets and certificates require a different recovery approach:

- If a secret version is incorrect but not compromised, restore or activate a known valid Key Vault version according to policy and verify the application reload behavior.
- If a secret is exposed or suspected to be compromised, revoke and rotate it. Never roll back to the exposed credential.
- Use an overlap period where supported so producers and consumers can transition safely.
- Confirm that managed identity, Key Vault RBAC, private connectivity and the CSI/external-secret integration are healthy.
- Check that logs, pipeline output and Kubernetes resources do not expose secret values.

The rollback pipeline references secret identifiers or versions; it never stores secret values in Git, Helm values, artifacts or logs.

### 8. Database rollback strategy

Database changes are the main reason application rollback can become unsafe. We use backward-compatible **expand, migrate and contract** changes:

1. **Expand:** Add new tables, columns or indexes without breaking the old application.
2. **Migrate:** Deploy compatible application code and migrate/backfill data safely.
3. **Contract:** Remove old schema only after all consumers have moved and the rollback window has closed.

With this pattern, the previous application version can normally run against the expanded schema. Destructive actions such as dropping or renaming a required column are not combined with the initial application rollout.

If data has been corrupted, I stop writes where appropriate, involve the database owner, define the recovery point and use the approved Azure Database for PostgreSQL backup/point-in-time recovery procedure. Restoring a database is a business and data-recovery decision, not a routine pipeline rollback, because it can discard valid transactions created after the recovery point.

### 9. Infrastructure rollback

Terraform state is not an infrastructure backup, and I do not copy an old state file over the current one to roll back Azure resources.

For an infrastructure problem:

1. Identify the offending Git commit and actual Azure state.
2. Revert or correct the Terraform/Bicep code through a pull request.
3. Run formatting, validation, security/policy checks and a fresh plan.
4. Review replacement, deletion, networking, identity and data impact.
5. Obtain the required environment approval.
6. Apply the corrective plan with a protected identity.
7. Verify network paths, RBAC, AKS, ACR, Key Vault, monitoring and the real application flow.

Some cloud changes are not safely reversible—for example, data deletion, address-space changes or certain resource replacements. Those changes need backups, migration plans, `prevent_destroy`/resource locks where appropriate, staged rollout and a tested disaster-recovery procedure before implementation.

### 10. Verification after rollback

A successful rollback command does not prove that users have recovered. After rollback, I verify:

```bash
kubectl get pods -n <namespace>
kubectl get events -n <namespace> \
  --sort-by=.metadata.creationTimestamp
kubectl rollout status deployment/<name> \
  -n <namespace> \
  --timeout=<approved-timeout>
```

I then validate:

- All expected replicas are Ready and stable.
- The Service and ingress/Application Gateway route to healthy endpoints.
- Smoke and critical API tests pass.
- Error rate and latency return to baseline.
- Application Insights dependencies and traces are healthy.
- No new restart, memory, CPU or probe issue is appearing.
- A real business transaction succeeds.
- Data integrity and background processing are correct.

We monitor for a defined observation period before resolving the incident or resuming other releases.

### 11. CI/CD implementation

The same rollback principles apply whether the pipeline is implemented in Jenkins, Azure DevOps, GitHub Actions or GitLab CI:

- The deployment job records the new and previous immutable versions.
- The rollback job is parameterized but restricted to authorized users.
- Production uses a protected environment and least-privilege Azure identity.
- Only one deployment or rollback can modify an environment at a time.
- The job validates the target cluster, namespace, application and digest before acting.
- Approval is required when policy demands it, but emergency procedures remain fast and auditable.
- Logs and notifications contain identifiers and evidence links, not secrets.
- Rollback is tested periodically in a representative non-production environment.

The pipeline can automatically initiate rollback for clear application-health failures. For database, infrastructure, security or ambiguous incidents, it pauses and requires the responsible owner to choose the recovery action.

### 12. Post-rollback activities

After service is restored:

1. Confirm and communicate user recovery.
2. Preserve the failed artifact, logs, traces and deployment evidence.
3. Record the incident timeline and exact rollback action.
4. Determine the root cause rather than treating rollback as the final fix.
5. Correct the application, test, probe, configuration or pipeline control.
6. Add a regression test or monitoring signal that would detect the issue earlier.
7. Rebuild a new immutable artifact and run the complete promotion flow.
8. Review whether rollback time met the recovery objective.
9. Update the runbook and conduct a blameless RCA.

We do not redeploy the same failed digest without understanding why it failed.

### How this strategy protects Production

The strategy is safe because:

- The previous known-good artifact is immutable and retained.
- Progressive delivery limits how many users see a bad version.
- Health and business gates stop promotion early.
- Application, configuration, database and infrastructure recovery are treated differently.
- Database migrations remain backward compatible during the rollback window.
- Production rollback access is protected, serialized and audited.
- Recovery verifies the user transaction, not only Kubernetes resource status.
- Every rollback produces evidence and a preventive follow-up action.

### Concise interview version

If an issue occurs, my first step is to stop the rollout and prevent the artifact from moving to another environment. I correlate the deployment timestamp with AKS Events and logs, Application Insights traces, Azure Monitor metrics and business health checks. Then I decide whether rollback is safer than a forward-fix, because database, secret or infrastructure changes may not be safely reversible.

For a normal application failure, we roll back the Helm release to the previous known-good ACR image digest. With canary deployment, we stop the canary and return traffic to the stable version; with blue-green, we switch traffic back to blue. We then verify Pod readiness, smoke tests, error rate, latency and a real business transaction.

Configuration is reverted through Git, compromised secrets are rotated rather than restored, and infrastructure is corrected through a reviewed Terraform/Bicep plan—not by restoring an old state file. Database changes follow expand, migrate and contract so the previous application remains compatible during the rollback window. Finally, we monitor through an observation period, communicate recovery and complete RCA with preventive actions.
