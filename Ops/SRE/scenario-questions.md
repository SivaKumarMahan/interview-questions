## 1. How do you reduce toil in on-call DevOps support?

**Answer:** Automate the runbooks you use often, add self-healing for common incidents, rotate on-call fairly, and make alerts richer with logs and graphs. Mini-case: we automated disk cleanup for build agents. Instead of three night-time alerts a week, the script just fixed it on its own.

**Detailed interview approach:**
I measure repeated tickets and pages by how often they happen, how long they take, how risky they are, and their root cause, then go after the highest-value toil first.

First I make the alert actionable and link it to a tested runbook. Then I automate the diagnostics that are predictable. Only after that do I automate a limited fix — with preconditions, rate limits, audit logs, and a kill switch.

Anything dangerous or unclear still needs a human to approve it. Every self-healing action leaves evidence and a follow-up, so the automation doesn't just quietly paper over a real problem.

I track pages, minutes of manual work, false-positive rate, and whether the issue keeps coming back. I prefer fixing the actual product or config over maintaining permanent cleanup scripts forever, and game days make sure responders can still handle the failures automation can't.

## 2. How do you apply chaos engineering safely in production?

**Answer:** Start with small-impact experiments, run them in non-critical namespaces, use circuit breakers and feature flags, schedule experiments for low-traffic windows, and roll back automatically if metrics get worse.

Mini-case: a controlled pod-kill experiment in staging validated the autoscaler and retry logic. Running the same experiment in production, narrowly scoped, improved resilience with no impact on users.

**Detailed interview approach:**
I write a hypothesis tied to an SLO — something like "losing one pod causes no user-visible errors" — and confirm monitoring, rollback, an owner, and abort thresholds are all in place first.

I run the experiment in staging, then in production at the smallest possible scope: one service or pod, a low-traffic window, a short duration, and nothing else risky happening at the same time.

Tools like Chaos Mesh can inject pod, network, or resource faults, but access to them is tightly controlled. A controller watches error rate, latency, saturation, and data integrity, and stops the experiment the moment a threshold is crossed.

I compare what actually happened to the hypothesis, note any gaps, fix probes, capacity, retries, or runbooks as needed, and rerun it. Chaos engineering is never just letting failures happen at random.

## 3. How do you implement cross-team incident playbooks and runbooks?

**Answer:** Keep versioned runbooks in a shared repo, automate the diagnostic steps as scripts triggered from alerts, assign clear roles during an incident, and run regular drills to make sure the playbooks still work. Wire the runbooks into PagerDuty or your alerting tool.

Mini-case: during an outage, the runbook told the responder to check the autoscaler logs and run an automated fix script. Recovery time dropped from 45 minutes to 12.

**Detailed interview approach:**
I declare severity and an incident commander, assign operations, communications, and scribe roles, open a channel to track the timeline, and focus first on user impact and safe containment.

Responders preserve alerts, logs, traces, audit events, deployments, and decisions while following the versioned runbooks. Any risky change has an owner and a rollback plan.

Stakeholders get factual updates on a schedule. Once things recover, I verify service and data integrity, watch it through a stability window, and write a blameless review covering the trigger, contributing factors, detection, response, and recovery.

Every action gets an owner and a date, and I prioritize systemic fixes — tests, guardrails, capacity, or design changes — over quick patches. Regular drills confirm the contacts, permissions, commands, and dependencies in the runbook still actually work.

## 4. How do you implement automatic fixes for common infra issues?

**Answer:** Hook alerts up to runbooks or automation (Cloud Functions, Lambdas, Runbooks) that perform a safe fix — restart a service, scale up — with manual approval as a fallback for anything risky. Log every automated step.

Mini-case: a CPU spike alert triggered an automated scale-up script that added nodes and notified the team. The script logged its actions and opened a follow-up ticket.

**Detailed interview approach:**
I only automate a condition that's well understood, happens often, and has a safe, predictable response. The automation checks its preconditions and the current state, limits its own scope and frequency, uses an identity with only the access it needs, logs every action, and backs off safely if the evidence is unclear.

For example, it might recycle one unhealthy stateless instance after confirming health checks and capacity — but it should never restart the whole fleet. Success is verified against the original metric plus a real business check. If it fails, it pages a person along with diagnostics.

A kill switch, a dry-run mode, a timeout, safe-to-repeat behavior, and manual approval for anything stateful or destructive all keep the risk contained. Even a fix that runs automatically should still open a ticket so someone removes the root cause.

## 5. How do you implement SLO-driven deployments in CI/CD?

**Answer:** Define SLOs and error budgets, add pipeline gates that check recent SLO metrics after a canary or blue-green rollout, block the full rollout or trigger a rollback if the error budget is blown, and notify the SRE team.

Mini-case: during a canary, the pipeline queried Prometheus for the 5-minute error rate. It crossed the threshold, so the pipeline halted and automatically rolled back to the previous version.

**Detailed interview approach:**
I deploy a fixed artifact (its contents never change once built) using a strategy that matches the risk: rolling for routine stateless changes, canary when I want to check metrics on a small slice of traffic, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or zero-traffic target, runs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and the SLO/error budget.

If any threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record what happened, and improve whatever test or guard should have caught the problem earlier.

## 6. How do you implement SRE practices in DevOps pipelines?

**Answer:** Define SLOs and error budgets, add monitoring checks into the pipeline, and block deployments if the error budget is exceeded.

**Detailed interview approach:**
I instrument the pipeline itself — queue time, stage duration, failure and retry rate, deployment frequency, lead time, change-failure rate, and recovery time — and tag each deployment on the application dashboards.

Post-deploy gates check health, error rate, latency, saturation, and a real business transaction, rather than just trusting that a command ran successfully.

Alerts include the environment, commit, artifact, which stage failed, links to dashboards, and a runbook, then get routed by severity with deduplication so chat doesn't get noisy. I use trends to fix the slow or flaky stage, and make sure any automatic rollback or fix stays limited, logged, and doesn't just hide a recurring root cause.

## 7. How do you automate backups in DevOps workflows?

**Answer:** Schedule backups with Velero for Kubernetes, automate database backups through scripts in the pipeline, and store backups in GCS or Azure Blob.

**Detailed interview approach:**
I start from a business-approved RTO and RPO, then map out data, configuration, identity, DNS/network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a separate failure domain (a group of resources that could fail together) or account.

I automate restoring into a clean environment and check integrity, application transactions, monitoring, and access before switching traffic over. A backup isn't considered good until a restore drill has proven it.

Regular exercises record the actual recovery time, any missing dependencies, and manual steps needed — and the runbook, capacity, DNS TTLs, contact paths, and retention policy get updated based on what they find.

## 8. How do you ensure disaster recovery in the cloud (GCP/Azure)?

**Answer:** Deploy across multiple zones, back up to remote regions, use Terraform to rebuild infrastructure quickly, and run DR drills regularly.

**Detailed interview approach:**
I start from a business-approved RTO and RPO, then map out data, configuration, identity, DNS/network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a separate failure domain (a group of resources that could fail together) or account.

I automate restoring into a clean environment and check integrity, application transactions, monitoring, and access before switching traffic over. A backup isn't considered good until a restore drill has proven it.

Regular exercises record the actual recovery time, any missing dependencies, and manual steps needed — and the runbook, capacity, DNS TTLs, contact paths, and retention policy get updated based on what they find.

## 9. How do you perform incident response in DevOps?

**Answer:**
- Detect it through monitoring and alerts.
- Run a root-cause analysis using logs, metrics, and events.
- Mitigate with a rollback or scaling.
- Document the incident and build automation to prevent it from happening again.

**Detailed interview approach:**
I declare severity and an incident commander, assign operations, communications, and scribe roles, open a channel to track the timeline, and focus first on user impact and safe containment.

Responders preserve alerts, logs, traces, audit events, deployments, and decisions while following the versioned runbooks. Any risky change has an owner and a rollback plan.

Stakeholders get factual updates on a schedule. Once things recover, I verify service and data integrity, watch it through a stability window, and write a blameless review covering the trigger, contributing factors, detection, response, and recovery.

Every action gets an owner and a date, and I prioritize systemic fixes — tests, guardrails, capacity, or design changes — over quick patches. Regular drills confirm the contacts, permissions, commands, and dependencies in the runbook still actually work.

## 10. How would you design and implement a disaster recovery strategy for a multi-region cloud infrastructure?

**Answer:** Multi-region AWS setup with us-east-1 as primary and us-west-2 for DR, Terraform with per-region state but shared modules, S3 cross-region replication plus DynamoDB global tables plus cross-region RDS snapshots, Argo CD GitOps per region, Route53 failover, and quarterly FIS drills validating RTO/RPO.

**Detailed interview approach:**
I build a full DR strategy on an AWS multi-region setup, with primary workloads in us-east-1 and DR components in us-west-2. Infrastructure is defined in Terraform, with separate state files per region but shared modules.

I use S3 cross-region replication for static assets and DynamoDB global tables for distributed data. For stateful applications, I set up automated RDS snapshots with point-in-time recovery, copied across regions.

EKS clusters use GitOps with Argo CD in each region, pulling from the same Git repository so configuration stays consistent.

Route53 health checks with failover routing automatically redirect traffic during a region failure. I run quarterly DR drills with AWS Fault Injection Simulator to confirm the actual recovery time (RTO) and recovery point (RPO) meet the targets.
