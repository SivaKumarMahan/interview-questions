# Ops: Site Reliability Engineering

> SRE principles and error budgets, SLO-driven delivery, toil and self-healing, resilience and chaos engineering, incident management and post-mortems, and disaster recovery.

## Interview Questions

### 1. SRE principles and implementing error budgets *(asked in interview round)*

- **SRE** applies software-engineering thinking to operations. You measure reliability with **SLIs** (like latency or availability), set a target called an **SLO** (say, 99.9%), and the gap between that and 100% is your **error budget** — the amount of unreliability you're allowed to spend.
- **Error budget policy:** if the budget is healthy, ship features fast. If it's used up, freeze risky releases and put the focus on reliability until it recovers. This ties feature velocity to reliability in an objective way, instead of an argument.
- **Other principles:** remove repetitive manual work through automation, run blameless postmortems, keep that manual work under roughly half of everyone's time, and watch the **four golden signals** — latency, traffic, errors, and saturation (how close a resource is to running out of capacity).

### 2. How do you implement SRE practices in DevOps pipelines? *(scenario)*

**Answer:** Define SLOs and error budgets, add monitoring checks into the pipeline, and block deployments if the error budget is exceeded.

**Detailed interview approach:**
I instrument the pipeline itself — queue time, stage duration, failure and retry rate, deployment frequency, lead time, change-failure rate, and recovery time — and tag each deployment on the application dashboards.

Post-deploy gates check health, error rate, latency, saturation, and a real business transaction, rather than just trusting that a command ran successfully.

Alerts include the environment, commit, artifact, which stage failed, links to dashboards, and a runbook, then get routed by severity with deduplication so chat doesn't get noisy. I use trends to fix the slow or flaky stage, and make sure any automatic rollback or fix stays limited, logged, and doesn't just hide a recurring root cause.

### 3. How do you implement SLO-driven deployments in CI/CD? *(scenario)*

**Answer:** Define SLOs and error budgets, add pipeline gates that check recent SLO metrics after a canary or blue-green rollout, block the full rollout or trigger a rollback if the error budget is blown, and notify the SRE team.

Mini-case: during a canary, the pipeline queried Prometheus for the 5-minute error rate. It crossed the threshold, so the pipeline halted and automatically rolled back to the previous version.

**Detailed interview approach:**
I deploy a fixed artifact (its contents never change once built) using a strategy that matches the risk: rolling for routine stateless changes, canary when I want to check metrics on a small slice of traffic, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or zero-traffic target, runs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and the SLO/error budget.

If any threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record what happened, and improve whatever test or guard should have caught the problem earlier.

### 4. How do you reduce toil in on-call DevOps support? *(scenario)*

**Answer:** Automate the runbooks you use often, add self-healing for common incidents, rotate on-call fairly, and make alerts richer with logs and graphs. Mini-case: we automated disk cleanup for build agents. Instead of three night-time alerts a week, the script just fixed it on its own.

**Detailed interview approach:**
I measure repeated tickets and pages by how often they happen, how long they take, how risky they are, and their root cause, then go after the highest-value toil first.

First I make the alert actionable and link it to a tested runbook. Then I automate the diagnostics that are predictable. Only after that do I automate a limited fix — with preconditions, rate limits, audit logs, and a kill switch.

Anything dangerous or unclear still needs a human to approve it. Every self-healing action leaves evidence and a follow-up, so the automation doesn't just quietly paper over a real problem.

I track pages, minutes of manual work, false-positive rate, and whether the issue keeps coming back. I prefer fixing the actual product or config over maintaining permanent cleanup scripts forever, and game days make sure responders can still handle the failures automation can't.

### 5. How do you implement automatic fixes for common infra issues? *(scenario)*

**Answer:** Hook alerts up to runbooks or automation (Cloud Functions, Lambdas, Runbooks) that perform a safe fix — restart a service, scale up — with manual approval as a fallback for anything risky. Log every automated step.

Mini-case: a CPU spike alert triggered an automated scale-up script that added nodes and notified the team. The script logged its actions and opened a follow-up ticket.

**Detailed interview approach:**
I only automate a condition that's well understood, happens often, and has a safe, predictable response. The automation checks its preconditions and the current state, limits its own scope and frequency, uses an identity with only the access it needs, logs every action, and backs off safely if the evidence is unclear.

For example, it might recycle one unhealthy stateless instance after confirming health checks and capacity — but it should never restart the whole fleet. Success is verified against the original metric plus a real business check. If it fails, it pages a person along with diagnostics.

A kill switch, a dry-run mode, a timeout, safe-to-repeat behavior, and manual approval for anything stateful or destructive all keep the risk contained. Even a fix that runs automatically should still open a ticket so someone removes the root cause.

### 6. How would you design a self-healing platform for critical production services?

**Answer:**

I build self-healing around known failure modes, using actions that are safe and limited in scope.

Redundant instances spread across separate failure domains (groups of resources that could fail together), health and readiness checks, the orchestrator continuously reconciling state, autoscaling, queue-based buffering, timeouts on dependencies, and automatically pulling bad instances out of traffic — these handle most common component failures.

Data services are different: they need quorum, replication, backups, and fencing, because blindly restarting a failed database can cause corruption or a split-brain situation.

Detection relies on SLIs that reflect what users actually see, plus evidence from individual components. Every automated action has clear prerequisites, a rate limit, a cooldown period, a maximum number of attempts, an audit log, and a path to escalate to a human.

Examples: replacing an unhealthy instance with a fresh, unmodified one, restarting a stateless process that's confirmed to be deadlocked, scaling based on queue age, or failing traffic over to a healthy region. Automation should never delete state, grant broad access, or loop forever.

I test this by injecting controlled failures, to confirm detection works, the fix works, customer impact is limited, and it correctly falls back to a human when it should. Dashboards track whether actions succeeded and whether the same issue keeps recurring.

Self-healing shortens recovery time. It doesn't replace root-cause analysis, capacity planning, or a tested disaster-recovery plan.

### 7. How do you handle cascading failures across multiple microservices?

**Answer:**

First I stabilize demand and protect the dependencies that are still healthy: stop risky releases, rate-limit at the edge, drop non-critical work, open circuit breakers, cap retries with jittered backoff (a growing, slightly randomized wait between retries) and a retry budget, bound queue sizes, and only scale where the dependency can actually absorb more load.

Unlimited retries and timeouts that all fire at once are what turn a small failure into a full cascade.

Using traces, the service topology, saturation levels (how close each resource is to its limit), queue age, and the timing of errors, I find the earliest shared dependency that actually failed, rather than treating every downstream 5xx as its own separate incident.

Bulkheads, separate resource pools, per-tenant quotas, idempotency (so retries are always safe), deadlines that propagate across calls, fallbacks, and cached or degraded responses all keep the blast radius small.

Once things recover, I safely replay any buffered work, confirm data correctness and that SLOs have recovered, and load-test the new limits. The post-incident review updates dependency ownership, capacity assumptions, retry and timeout standards, alerts, and failure-mode exercises.

### 8. Can strict use of the Single Responsibility Principle increase complexity in a distributed system? (True or False)

**Answer:**

True. A good responsibility boundary improves ownership and makes changes safer to isolate, but applying the principle too mechanically can leave you with far too many tiny services.

Every service boundary adds a network call, a new way to partially fail, its own deployment and versioning, observability, security, data-consistency concerns, testing, and coordination between teams. "Single responsibility" should describe one cohesive business capability with clear ownership — not one class or function per service.

I look at coupling, how often each part changes independently, scaling needs, who owns the data, latency, transaction requirements, team ownership, and how mature the team's operations are. A well-structured modular monolith can genuinely be safer than splitting into microservices too early.

I only pull out a separate service when the boundary gives measurable independent value and the team can actually operate it — and I revisit that decision as usage changes.

### 9. How do you apply chaos engineering safely in production? *(scenario)*

**Answer:** Start with small-impact experiments, run them in non-critical namespaces, use circuit breakers and feature flags, schedule experiments for low-traffic windows, and roll back automatically if metrics get worse.

Mini-case: a controlled pod-kill experiment in staging validated the autoscaler and retry logic. Running the same experiment in production, narrowly scoped, improved resilience with no impact on users.

**Detailed interview approach:**
I write a hypothesis tied to an SLO — something like "losing one pod causes no user-visible errors" — and confirm monitoring, rollback, an owner, and abort thresholds are all in place first.

I run the experiment in staging, then in production at the smallest possible scope: one service or pod, a low-traffic window, a short duration, and nothing else risky happening at the same time.

Tools like Chaos Mesh can inject pod, network, or resource faults, but access to them is tightly controlled. A controller watches error rate, latency, saturation, and data integrity, and stops the experiment the moment a threshold is crossed.

I compare what actually happened to the hypothesis, note any gaps, fix probes, capacity, retries, or runbooks as needed, and rerun it. Chaos engineering is never just letting failures happen at random.

### 10. Handle complex/varying-traffic scaling scenarios for Kubernetes *(asked in interview round)*

- Combine the **Horizontal Pod Autoscaler** (per service, on CPU, requests per second, or custom metrics through Prometheus Adapter, or **KEDA** for event/queue-driven scaling), the **Vertical Pod Autoscaler** for right-sizing, and the **Cluster Autoscaler** or **Karpenter** for adding nodes.
- For **predictable peaks**, use scheduled scaling to pre-warm capacity. For **spiky traffic**, buffer it with queues (SQS/Kafka) plus KEDA. For **sudden node demand**, Karpenter provisions fast and cost-consciously, combined with spot instances.
- Set real resource requests and limits, PodDisruptionBudgets, topology spread, and readiness probes, then load-test to confirm it all works, and keep an eye on cost. Different services need different scaling policies based on how their traffic actually behaves.

### 11. Experience managing large-scale environments — challenges (behavioral) *(asked in interview round)*

Talk about the actual scale you worked with (how many clusters, services, or regions) and the real challenges: config drift and standardizing things (solved with IaC and GitOps), observability at scale (too many unique label combinations, and the cost that comes with it — solved with tools like Thanos or sampling), coordinating across teams and rolling out changes safely (progressive delivery), cost optimization, reducing on-call load, and staying reliable through upgrades and migrations.

For each challenge, be ready to say specifically what you did about it.

### 12. Explain your production incident-management process.

**Answer:**

I assess impact and severity, declare a single incident, assign an incident commander plus technical leads, communications, and a scribe, and open a timestamped channel to track the timeline.

The team protects safety, security, and data integrity first, then stabilizes users through rollback, a traffic shift, disabling a feature, scaling, or isolating the problem.

We preserve evidence and build testable hypotheses from metrics, logs, traces, deploys, and audit changes, instead of making several random changes at once and hoping one works.

Stakeholders get regular updates covering impact, what's being done, who owns it, and when the next update will come. Every action has an expected result and a rollback plan.

Recovery means confirming real customer and business transactions work, plus SLOs and backlog — not just that infrastructure shows green. Any temporary access or workaround gets removed or explicitly tracked.

The blameless review looks at both technical and organizational contributing factors, gaps in detection, what worked well, and concrete actions with an owner and a date. We update tests, architecture, runbooks, alerts, capacity plans, and game days, then check later that those fixes actually worked.

### 13. How do you perform incident response in DevOps? *(scenario)*

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

### 14. How do you implement cross-team incident playbooks and runbooks? *(scenario)*

**Answer:** Keep versioned runbooks in a shared repo, automate the diagnostic steps as scripts triggered from alerts, assign clear roles during an incident, and run regular drills to make sure the playbooks still work. Wire the runbooks into PagerDuty or your alerting tool.

Mini-case: during an outage, the runbook told the responder to check the autoscaler logs and run an automated fix script. Recovery time dropped from 45 minutes to 12.

**Detailed interview approach:**
I declare severity and an incident commander, assign operations, communications, and scribe roles, open a channel to track the timeline, and focus first on user impact and safe containment.

Responders preserve alerts, logs, traces, audit events, deployments, and decisions while following the versioned runbooks. Any risky change has an owner and a rollback plan.

Stakeholders get factual updates on a schedule. Once things recover, I verify service and data integrity, watch it through a stability window, and write a blameless review covering the trigger, contributing factors, detection, response, and recovery.

Every action gets an owner and a date, and I prioritize systemic fixes — tests, guardrails, capacity, or design changes — over quick patches. Regular drills confirm the contacts, permissions, commands, and dependencies in the runbook still actually work.

### 15. Lead a team through a critical production issue (behavioral — STAR) *(asked in interview round)*

Use the **STAR** format: Situation (a severe outage), Task (your role, say incident commander), Action (declared the incident, opened a war room, assigned roles for communication/operations/scribe, mitigated first through rollback or failover, kept stakeholders updated regularly), Result (restored service, met the recovery target, ran a blameless postmortem, and drove the follow-up fixes).

Emphasize staying calm, communicating clearly, fixing the immediate problem before digging into the cause, and following through afterward.

### 16. Post-mortem / effective incident review process *(asked in interview round)*

- **Blameless:** focus on the systems and contributing factors, not on blaming a person.
- **Structure:** a timeline of events, the impact (users affected, duration, SLO impact), how it was detected, the root cause (found through something like the 5 Whys), what went well and what didn't, and concrete follow-ups with an owner and a due date.
- **Process:** any significant incident triggers one, write it up promptly, review it with stakeholders, track the follow-ups to completion, and share it across the org so others learn from it. The goal is fixing the system, not just this one incident.

### 17. A deployment succeeds, but latency rises from 80 ms to two seconds. How do you investigate it?

**Answer:**

A successful deployment only tells you the control plane did its job — it says nothing about performance. I compare the new and old versions under identical traffic, and break latency down by DNS, connection/TLS, gateway or queue time, application time, cache, database, and downstream calls, using traces and proxy/application metrics.

I line up the exact time of the change against configuration changes, feature flags, schema changes, the instance mix, garbage collection, CPU throttling, connection pools, query plans, cache hit rate, payload size, retries, and zone or region routing.

If the SLO impact is real, I pause the rollout or route traffic back to the last healthy version while preserving evidence. Comparing a canary against the baseline helps tell whether it's the new code, a shared dependency, or a traffic change.

I avoid the easy trap of just raising the timeout — that hides the latency problem and eats even more resources.

Once I've made the targeted fix, I load-test the real path, confirm p50/p95/p99 latency and error rates, saturation, dependency health, and business metrics, and add a regression test or deployment guard based on what actually caused it.

### 18. How do you design disaster recovery with an RTO under five minutes and a defined RPO?

**Answer:**

First I confirm the business cost actually justifies that target. An RTO (recovery time objective) under five minutes generally needs a pre-provisioned warm or active secondary environment, automated detection and traffic switching, independent identity, DNS, certificates, and observability, and enough spare capacity to absorb the failover.

Backups alone can't hit that RTO. The RPO (recovery point objective) is what decides whether you need synchronous or asynchronous replication, and how much data loss is acceptable in the worst case.

I map every dependency: compute, data, object storage, queues, secrets, DNS, third parties, CI/CD, and the people involved. Data replication needs fencing and clear write ownership to avoid split-brain.

Infrastructure and configuration are versioned, but the actual restore and failover steps are automated and safe to run more than once. Health checks use real transactions, not just whether a host is up.

Game days simulate region and dependency failures, and measure detection, decision-making, data promotion, scaling, traffic shift, and validation. I record the RTO and RPO actually achieved, replication lag, how data was reconciled, and how failback went.

If the tests can't hit five minutes, I report that gap honestly and either change the architecture or reset the expectation — I don't claim a target that hasn't been proven.

### 19. How would you design and implement a disaster recovery strategy for a multi-region cloud infrastructure? *(scenario)*

**Answer:** Multi-region AWS setup with us-east-1 as primary and us-west-2 for DR, Terraform with per-region state but shared modules, S3 cross-region replication plus DynamoDB global tables plus cross-region RDS snapshots, Argo CD GitOps per region, Route53 failover, and quarterly FIS drills validating RTO/RPO.

**Detailed interview approach:**
I build a full DR strategy on an AWS multi-region setup, with primary workloads in us-east-1 and DR components in us-west-2. Infrastructure is defined in Terraform, with separate state files per region but shared modules.

I use S3 cross-region replication for static assets and DynamoDB global tables for distributed data. For stateful applications, I set up automated RDS snapshots with point-in-time recovery, copied across regions.

EKS clusters use GitOps with Argo CD in each region, pulling from the same Git repository so configuration stays consistent.

Route53 health checks with failover routing automatically redirect traffic during a region failure. I run quarterly DR drills with AWS Fault Injection Simulator to confirm the actual recovery time (RTO) and recovery point (RPO) meet the targets.

### 20. How do you ensure disaster recovery in the cloud (GCP/Azure)? *(scenario)*

**Answer:** Deploy across multiple zones, back up to remote regions, use Terraform to rebuild infrastructure quickly, and run DR drills regularly.

**Detailed interview approach:**
I start from a business-approved RTO and RPO, then map out data, configuration, identity, DNS/network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a separate failure domain (a group of resources that could fail together) or account.

I automate restoring into a clean environment and check integrity, application transactions, monitoring, and access before switching traffic over. A backup isn't considered good until a restore drill has proven it.

Regular exercises record the actual recovery time, any missing dependencies, and manual steps needed — and the runbook, capacity, DNS TTLs, contact paths, and retention policy get updated based on what they find.

### 21. How do you automate backups in DevOps workflows? *(scenario)*

**Answer:** Schedule backups with Velero for Kubernetes, automate database backups through scripts in the pipeline, and store backups in GCS or Azure Blob.

**Detailed interview approach:**
I start from a business-approved RTO and RPO, then map out data, configuration, identity, DNS/network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a separate failure domain (a group of resources that could fail together) or account.

I automate restoring into a clean environment and check integrity, application transactions, monitoring, and access before switching traffic over. A backup isn't considered good until a restore drill has proven it.

Regular exercises record the actual recovery time, any missing dependencies, and manual steps needed — and the runbook, capacity, DNS TTLs, contact paths, and retention policy get updated based on what they find.
