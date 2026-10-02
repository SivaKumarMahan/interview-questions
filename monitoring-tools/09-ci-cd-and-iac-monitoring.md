# Monitoring Tools: CI/CD and Infrastructure-as-Code Monitoring

> Monitoring pipelines and deployments, observability-driven deployment gates, and monitoring Terraform-managed infrastructure, applies and drift.

## Key Concepts

### CI/CD Monitoring Overview

Pipeline monitoring should cover the full delivery path, not just whether a build passed.

### What to Track in Pipelines

| Area | Signals |
| --- | --- |
| Pipeline health | Queue time, stage duration, success/failure/retry rate, flaky tests |
| Agent capacity | Agent saturation — how close agents are to running out of capacity |
| Artifacts | Artifact size and transfer time |
| Delivery performance | Deployment frequency, lead time, change-failure rate, recovery time |

Jenkins can expose metrics through a maintained Prometheus integration. Azure DevOps has its own metrics and APIs that can feed whatever observability backend you use.

Grafana, or another dashboard tool, should show these trends broken down by pipeline, branch, agent pool, and environment.

### Deployment Tagging and Correlation

Tag application dashboards with the commit, artifact digest, and deployment time. This lets you trace a production issue back to the exact build that caused it.

### Deployment Gates

A post-deployment gate should check error rate, latency, saturation, and a real smoke or business transaction before allowing promotion to continue.

Automatic rollback must be:

- Limited in scope
- Authorized
- Recorded
- Verified afterward

A rollback that fires automatically should never hide a recurring root cause — someone still needs to investigate why it triggered.

### Pipeline Alerting

Alerts should identify the environment, commit, failed stage, owner, and runbook.

Page someone only for urgent production impact or a blocked critical delivery path. Ordinary build failures should just notify the responsible team, not wake up on-call.

### Pipeline Security Note

Never expose credentials in pipeline logs. Also avoid high-cardinality labels — labels with too many unique values, like raw usernames or request IDs, that make metrics expensive to store and slow to query.

### Infrastructure-as-Code Monitoring Overview

There are two separate things to monitor here: the infrastructure that Terraform creates, and the Terraform pipeline itself. Both need attention.

### Monitor the Infrastructure Terraform Creates

Provision monitoring alongside the infrastructure it watches, not as an afterthought added later. Diagnostic settings or log groups, metric and log alerts, dashboards, notification routing (action groups or topics), retention, and access controls should all live in the same Terraform, Bicep, or CloudFormation resources as the service they belong to — or be enforced through policy so nothing slips through unmonitored.

Reusable modules give every service a safe default. Service owners still decide what a meaningful signal looks like for their own service, and where its alerts should route.

### Monitor the Terraform Pipeline Itself

The delivery pipeline is its own thing to watch, separate from the infrastructure it manages:

- Plan and apply duration and result
- State lock wait time
- Provider and API errors
- Drift detection results
- Policy and security check failures
- Smoke checks run right after apply

Keep a reviewed, access-controlled plan and a full audit trail for every change. Terraform state and full plans can contain secrets, so their content should never be exported into ordinary logs or metrics.

Production applies should be serialized — one at a time — and alerts need to tell the difference between an active, legitimate lock and a stale one left behind by a failed run.

### Validate After Every Apply

An apply that finishes successfully, and creates an alert resource or a diagnostic setting, is not proof the monitoring actually works. Check three things afterward:

1. Monitoring data is actually arriving.
2. Alerts route to the right place.
3. The application transaction being monitored actually works.

### IaC Monitoring Quick Reference

| What to track | Where | Why it matters |
| --- | --- | --- |
| Format, validation, and policy results | PR pipeline | Catches problems before merge |
| Reviewed plan | PR pipeline, access-controlled | Audit trail, prevents surprise changes |
| Apply result and duration | Production pipeline | Confirms delivery worked |
| State-lock wait | Production pipeline | Flags contention or stuck runs |
| Provider/API failures | Production pipeline | Surfaces upstream issues early |
| Drift | Scheduled plans or platform drift detection | Flags out-of-band changes without silently reverting them |
| Post-apply smoke check | Production pipeline | Confirms the real service works, not just that resources exist |

## Interview Questions

### 1. How do you monitor Jenkins or Azure DevOps pipelines?

**Answer:**

I export whatever platform, plugin, or API metrics are available to Prometheus or the chosen backend. Then I graph queue time, stage duration, result, retries, flaky tests, agent capacity, artifact transfer time, deployment frequency, lead time, change-failure rate, and recovery time.

I keep labels limited. Commit hashes belong in deployment annotations or logs, not in long-lived metric labels.

An alert should include the pipeline, environment, failed stage, owner, and runbook. A normal build failure notifies the team; a production deployment failure, or a blocked critical path, may page someone.

I compare trends against agent image or tool changes, and fix the flaky or constrained stage instead of just adding more retries.

### 2. How do you integrate observability into deployment gates?

**Answer:**

I deploy one immutable artifact — meaning it's never changed after it's built — and annotate dashboards with its digest and commit. I route a controlled amount of traffic to it, then check error rate, latency, saturation (how close the system is to its limit), and a smoke or business transaction.

The gate uses a fixed observation window and a minimum amount of traffic, so an empty or thin sample can't pass silently.

If the thresholds fail, promotion stops. A controlled rollback or traffic shift runs, followed by the same verification. That action is authorized, limited in scope, and logged.

Teams can only override the gate through an audited approval path, because automated health checks can be wrong too.

### 3. How do you implement monitoring for Terraform-managed infrastructure?

**Answer:**

I build monitoring into the same Terraform modules as the service itself. Diagnostic settings or log groups, metric and log alerts, dashboards, notification routing, retention, and access controls all live next to the resource they watch, not bolted on afterward.

Service owners still decide what a meaningful signal looks like for their own service. I push back on generic CPU-only alerts, because they rarely tell you whether users are actually affected.

Policy can enforce a baseline level of logging across the org, so nothing ships unmonitored by accident.

CI validates the code and previews the plan before anything is applied. The apply itself runs with only the permissions it actually needs. Afterward, I generate a known test event or a smoke transaction to prove the whole pipeline works end to end — that data really arrives and a notification really fires.

I also monitor the monitoring resources themselves. That includes cardinality, the number of unique label combinations being produced, since it drives cost and retention just as much as raw data volume does.

### 4. How do you monitor Terraform changes and drift?

**Answer:**

The pull request pipeline records the results of format checks, validation, and policy checks, along with a reviewed and protected plan. Nothing gets applied without going through that review.

In production, I record whether the apply succeeded, how long it took, how long it waited on a state lock, and any provider or API failures. After the apply, I run infrastructure and application checks to confirm the change actually worked.

Scheduled plans, or the platform's own drift-detection feature, catch changes made outside of Terraform. When that happens, I open a ticket or alert for someone to review. I don't let automation silently overwrite an emergency change someone made by hand.

Terraform state and full plans can contain secrets, so I keep them encrypted and access-controlled rather than sending them to ordinary logs. When a run fails, I compare it against the cloud provider's audit logs, and I make sure the state matches the real resources — reconciling the two — before retrying.
