# Ops: Site Reliability Engineering

> SRE principles and error budgets, SLO-driven delivery, toil and self-healing, resilience and chaos engineering, incident management and post-mortems, and disaster recovery.

## Interview Questions

<details><summary>Q1. [Intermediate] SRE principles and implementing error budgets <em>(asked in interview round)</em></summary>

- **SRE** applies software-engineering thinking to operations. You measure reliability with **SLIs** (like latency or availability), set a target called an **SLO** (say, 99.9%), and the gap between that and 100% is your **error budget** — the amount of unreliability you're allowed to spend.
- **Error budget policy:** if the budget is healthy, ship features fast. If it's used up, freeze risky releases and put the focus on reliability until it recovers. This ties feature velocity to reliability in an objective way, instead of an argument.
- **Other principles:** remove repetitive manual work through automation, run blameless postmortems, keep that manual work under roughly half of everyone's time, and watch the **four golden signals** — latency, traffic, errors, and saturation (how close a resource is to running out of capacity).

</details>

<details><summary>Q2. [Intermediate] How do you implement SRE practices in DevOps pipelines? <em>(scenario)</em></summary>

**Answer:** Define SLOs and error budgets, add monitoring checks into the pipeline, and block deployments if the error budget is exceeded.

**Detailed interview approach:**
I instrument the pipeline itself — queue time, stage duration, failure and retry rate, deployment frequency, lead time, change-failure rate, and recovery time — and tag each deployment on the application dashboards.

Post-deploy gates check health, error rate, latency, saturation, and a real business transaction, rather than just trusting that a command ran successfully.

Alerts include the environment, commit, artifact, which stage failed, links to dashboards, and a runbook, then get routed by severity with deduplication so chat doesn't get noisy. I use trends to fix the slow or flaky stage, and make sure any automatic rollback or fix stays limited, logged, and doesn't just hide a recurring root cause.

</details>

<details><summary>Q3. [Advanced] How do you implement SLO-driven deployments in CI/CD? <em>(scenario)</em></summary>

**Answer:** Define SLOs and error budgets, add pipeline gates that check recent SLO metrics after a canary or blue-green rollout, block the full rollout or trigger a rollback if the error budget is blown, and notify the SRE team.

Mini-case: during a canary, the pipeline queried Prometheus for the 5-minute error rate. It crossed the threshold, so the pipeline halted and automatically rolled back to the previous version.

**Detailed interview approach:**
I deploy a fixed artifact (its contents never change once built) using a strategy that matches the risk: rolling for routine stateless changes, canary when I want to check metrics on a small slice of traffic, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or zero-traffic target, runs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and the SLO/error budget.

If any threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record what happened, and improve whatever test or guard should have caught the problem earlier.

</details>

<details><summary>Q4. [Intermediate] How do you reduce toil in on-call DevOps support? <em>(scenario)</em></summary>

**Answer:** Automate the runbooks you use often, add self-healing for common incidents, rotate on-call fairly, and make alerts richer with logs and graphs. Mini-case: we automated disk cleanup for build agents. Instead of three night-time alerts a week, the script just fixed it on its own.

**Detailed interview approach:**
I measure repeated tickets and pages by how often they happen, how long they take, how risky they are, and their root cause, then go after the highest-value toil first.

First I make the alert actionable and link it to a tested runbook. Then I automate the diagnostics that are predictable. Only after that do I automate a limited fix — with preconditions, rate limits, audit logs, and a kill switch.

Anything dangerous or unclear still needs a human to approve it. Every self-healing action leaves evidence and a follow-up, so the automation doesn't just quietly paper over a real problem.

I track pages, minutes of manual work, false-positive rate, and whether the issue keeps coming back. I prefer fixing the actual product or config over maintaining permanent cleanup scripts forever, and game days make sure responders can still handle the failures automation can't.

</details>

<details><summary>Q5. [Intermediate] How do you implement automatic fixes for common infra issues? <em>(scenario)</em></summary>

**Answer:** Hook alerts up to runbooks or automation (Cloud Functions, Lambdas, Runbooks) that perform a safe fix — restart a service, scale up — with manual approval as a fallback for anything risky. Log every automated step.

Mini-case: a CPU spike alert triggered an automated scale-up script that added nodes and notified the team. The script logged its actions and opened a follow-up ticket.

**Detailed interview approach:**
I only automate a condition that's well understood, happens often, and has a safe, predictable response. The automation checks its preconditions and the current state, limits its own scope and frequency, uses an identity with only the access it needs, logs every action, and backs off safely if the evidence is unclear.

For example, it might recycle one unhealthy stateless instance after confirming health checks and capacity — but it should never restart the whole fleet. Success is verified against the original metric plus a real business check. If it fails, it pages a person along with diagnostics.

A kill switch, a dry-run mode, a timeout, safe-to-repeat behavior, and manual approval for anything stateful or destructive all keep the risk contained. Even a fix that runs automatically should still open a ticket so someone removes the root cause.

</details>

<details><summary>Q6. [Advanced] How would you design a self-healing platform for critical production services?</summary>

**Answer:**

I build self-healing around known failure modes, using actions that are safe and limited in scope.

Redundant instances spread across separate failure domains (groups of resources that could fail together), health and readiness checks, the orchestrator continuously reconciling state, autoscaling, queue-based buffering, timeouts on dependencies, and automatically pulling bad instances out of traffic — these handle most common component failures.

Data services are different: they need quorum, replication, backups, and fencing, because blindly restarting a failed database can cause corruption or a split-brain situation.

Detection relies on SLIs that reflect what users actually see, plus evidence from individual components. Every automated action has clear prerequisites, a rate limit, a cooldown period, a maximum number of attempts, an audit log, and a path to escalate to a human.

Examples: replacing an unhealthy instance with a fresh, unmodified one, restarting a stateless process that's confirmed to be deadlocked, scaling based on queue age, or failing traffic over to a healthy region. Automation should never delete state, grant broad access, or loop forever.

I test this by injecting controlled failures, to confirm detection works, the fix works, customer impact is limited, and it correctly falls back to a human when it should. Dashboards track whether actions succeeded and whether the same issue keeps recurring.

Self-healing shortens recovery time. It doesn't replace root-cause analysis, capacity planning, or a tested disaster-recovery plan.

</details>

<details><summary>Q7. [Advanced] How do you handle cascading failures across multiple microservices?</summary>

**Answer:**

First I stabilize demand and protect the dependencies that are still healthy: stop risky releases, rate-limit at the edge, drop non-critical work, open circuit breakers, cap retries with jittered backoff (a growing, slightly randomized wait between retries) and a retry budget, bound queue sizes, and only scale where the dependency can actually absorb more load.

Unlimited retries and timeouts that all fire at once are what turn a small failure into a full cascade.

Using traces, the service topology, saturation levels (how close each resource is to its limit), queue age, and the timing of errors, I find the earliest shared dependency that actually failed, rather than treating every downstream 5xx as its own separate incident.

Bulkheads, separate resource pools, per-tenant quotas, idempotency (so retries are always safe), deadlines that propagate across calls, fallbacks, and cached or degraded responses all keep the blast radius small.

Once things recover, I safely replay any buffered work, confirm data correctness and that SLOs have recovered, and load-test the new limits. The post-incident review updates dependency ownership, capacity assumptions, retry and timeout standards, alerts, and failure-mode exercises.

</details>

<details><summary>Q8. [Basic] Can strict use of the Single Responsibility Principle increase complexity in a distributed system? (True or False)</summary>

**Answer:**

True. A good responsibility boundary improves ownership and makes changes safer to isolate, but applying the principle too mechanically can leave you with far too many tiny services.

Every service boundary adds a network call, a new way to partially fail, its own deployment and versioning, observability, security, data-consistency concerns, testing, and coordination between teams. "Single responsibility" should describe one cohesive business capability with clear ownership — not one class or function per service.

I look at coupling, how often each part changes independently, scaling needs, who owns the data, latency, transaction requirements, team ownership, and how mature the team's operations are. A well-structured modular monolith can genuinely be safer than splitting into microservices too early.

I only pull out a separate service when the boundary gives measurable independent value and the team can actually operate it — and I revisit that decision as usage changes.

</details>

<details><summary>Q9. [Advanced] How do you apply chaos engineering safely in production? <em>(scenario)</em></summary>

**Answer:** Start with small-impact experiments, run them in non-critical namespaces, use circuit breakers and feature flags, schedule experiments for low-traffic windows, and roll back automatically if metrics get worse.

Mini-case: a controlled pod-kill experiment in staging validated the autoscaler and retry logic. Running the same experiment in production, narrowly scoped, improved resilience with no impact on users.

**Detailed interview approach:**
I write a hypothesis tied to an SLO — something like "losing one pod causes no user-visible errors" — and confirm monitoring, rollback, an owner, and abort thresholds are all in place first.

I run the experiment in staging, then in production at the smallest possible scope: one service or pod, a low-traffic window, a short duration, and nothing else risky happening at the same time.

Tools like Chaos Mesh can inject pod, network, or resource faults, but access to them is tightly controlled. A controller watches error rate, latency, saturation, and data integrity, and stops the experiment the moment a threshold is crossed.

I compare what actually happened to the hypothesis, note any gaps, fix probes, capacity, retries, or runbooks as needed, and rerun it. Chaos engineering is never just letting failures happen at random.

</details>

<details><summary>Q10. [Advanced] Handle complex/varying-traffic scaling scenarios for Kubernetes <em>(asked in interview round)</em></summary>

- Combine the **Horizontal Pod Autoscaler** (per service, on CPU, requests per second, or custom metrics through Prometheus Adapter, or **KEDA** for event/queue-driven scaling), the **Vertical Pod Autoscaler** for right-sizing, and the **Cluster Autoscaler** or **Karpenter** for adding nodes.
- For **predictable peaks**, use scheduled scaling to pre-warm capacity. For **spiky traffic**, buffer it with queues (SQS/Kafka) plus KEDA. For **sudden node demand**, Karpenter provisions fast and cost-consciously, combined with spot instances.
- Set real resource requests and limits, PodDisruptionBudgets, topology spread, and readiness probes, then load-test to confirm it all works, and keep an eye on cost. Different services need different scaling policies based on how their traffic actually behaves.

</details>

<details><summary>Q11. [Intermediate] Experience managing large-scale environments — challenges (behavioral) <em>(asked in interview round)</em></summary>

Talk about the actual scale you worked with (how many clusters, services, or regions) and the real challenges: config drift and standardizing things (solved with IaC and GitOps), observability at scale (too many unique label combinations, and the cost that comes with it — solved with tools like Thanos or sampling), coordinating across teams and rolling out changes safely (progressive delivery), cost optimization, reducing on-call load, and staying reliable through upgrades and migrations.

For each challenge, be ready to say specifically what you did about it.

</details>

<details><summary>Q12. [Intermediate] Explain your production incident-management process.</summary>

**Answer:**

I assess impact and severity, declare a single incident, assign an incident commander plus technical leads, communications, and a scribe, and open a timestamped channel to track the timeline.

The team protects safety, security, and data integrity first, then stabilizes users through rollback, a traffic shift, disabling a feature, scaling, or isolating the problem.

We preserve evidence and build testable hypotheses from metrics, logs, traces, deploys, and audit changes, instead of making several random changes at once and hoping one works.

Stakeholders get regular updates covering impact, what's being done, who owns it, and when the next update will come. Every action has an expected result and a rollback plan.

Recovery means confirming real customer and business transactions work, plus SLOs and backlog — not just that infrastructure shows green. Any temporary access or workaround gets removed or explicitly tracked.

The blameless review looks at both technical and organizational contributing factors, gaps in detection, what worked well, and concrete actions with an owner and a date. We update tests, architecture, runbooks, alerts, capacity plans, and game days, then check later that those fixes actually worked.

</details>

<details><summary>Q13. [Intermediate] How do you perform incident response in DevOps? <em>(scenario)</em></summary>

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

</details>

<details><summary>Q14. [Advanced] How do you implement cross-team incident playbooks and runbooks? <em>(scenario)</em></summary>

**Answer:** Keep versioned runbooks in a shared repo, automate the diagnostic steps as scripts triggered from alerts, assign clear roles during an incident, and run regular drills to make sure the playbooks still work. Wire the runbooks into PagerDuty or your alerting tool.

Mini-case: during an outage, the runbook told the responder to check the autoscaler logs and run an automated fix script. Recovery time dropped from 45 minutes to 12.

**Detailed interview approach:**
I declare severity and an incident commander, assign operations, communications, and scribe roles, open a channel to track the timeline, and focus first on user impact and safe containment.

Responders preserve alerts, logs, traces, audit events, deployments, and decisions while following the versioned runbooks. Any risky change has an owner and a rollback plan.

Stakeholders get factual updates on a schedule. Once things recover, I verify service and data integrity, watch it through a stability window, and write a blameless review covering the trigger, contributing factors, detection, response, and recovery.

Every action gets an owner and a date, and I prioritize systemic fixes — tests, guardrails, capacity, or design changes — over quick patches. Regular drills confirm the contacts, permissions, commands, and dependencies in the runbook still actually work.

</details>

<details><summary>Q15. [Advanced] Lead a team through a critical production issue (behavioral — STAR) <em>(asked in interview round)</em></summary>

Use the **STAR** format: Situation (a severe outage), Task (your role, say incident commander), Action (declared the incident, opened a war room, assigned roles for communication/operations/scribe, mitigated first through rollback or failover, kept stakeholders updated regularly), Result (restored service, met the recovery target, ran a blameless postmortem, and drove the follow-up fixes).

Emphasize staying calm, communicating clearly, fixing the immediate problem before digging into the cause, and following through afterward.

</details>

<details><summary>Q16. [Intermediate] Post-mortem / effective incident review process <em>(asked in interview round)</em></summary>

- **Blameless:** focus on the systems and contributing factors, not on blaming a person.
- **Structure:** a timeline of events, the impact (users affected, duration, SLO impact), how it was detected, the root cause (found through something like the 5 Whys), what went well and what didn't, and concrete follow-ups with an owner and a due date.
- **Process:** any significant incident triggers one, write it up promptly, review it with stakeholders, track the follow-ups to completion, and share it across the org so others learn from it. The goal is fixing the system, not just this one incident.

</details>

<details><summary>Q17. [Advanced] A deployment succeeds, but latency rises from 80 ms to two seconds. How do you investigate it?</summary>

**Answer:**

A successful deployment only tells you the control plane did its job — it says nothing about performance. I compare the new and old versions under identical traffic, and break latency down by DNS, connection/TLS, gateway or queue time, application time, cache, database, and downstream calls, using traces and proxy/application metrics.

I line up the exact time of the change against configuration changes, feature flags, schema changes, the instance mix, garbage collection, CPU throttling, connection pools, query plans, cache hit rate, payload size, retries, and zone or region routing.

If the SLO impact is real, I pause the rollout or route traffic back to the last healthy version while preserving evidence. Comparing a canary against the baseline helps tell whether it's the new code, a shared dependency, or a traffic change.

I avoid the easy trap of just raising the timeout — that hides the latency problem and eats even more resources.

Once I've made the targeted fix, I load-test the real path, confirm p50/p95/p99 latency and error rates, saturation, dependency health, and business metrics, and add a regression test or deployment guard based on what actually caused it.

</details>

<details><summary>Q18. [Advanced] How do you design disaster recovery with an RTO under five minutes and a defined RPO?</summary>

**Answer:**

First I confirm the business cost actually justifies that target. An RTO (recovery time objective) under five minutes generally needs a pre-provisioned warm or active secondary environment, automated detection and traffic switching, independent identity, DNS, certificates, and observability, and enough spare capacity to absorb the failover.

Backups alone can't hit that RTO. The RPO (recovery point objective) is what decides whether you need synchronous or asynchronous replication, and how much data loss is acceptable in the worst case.

I map every dependency: compute, data, object storage, queues, secrets, DNS, third parties, CI/CD, and the people involved. Data replication needs fencing and clear write ownership to avoid split-brain.

Infrastructure and configuration are versioned, but the actual restore and failover steps are automated and safe to run more than once. Health checks use real transactions, not just whether a host is up.

Game days simulate region and dependency failures, and measure detection, decision-making, data promotion, scaling, traffic shift, and validation. I record the RTO and RPO actually achieved, replication lag, how data was reconciled, and how failback went.

If the tests can't hit five minutes, I report that gap honestly and either change the architecture or reset the expectation — I don't claim a target that hasn't been proven.

</details>

<details><summary>Q19. [Advanced] How would you design and implement a disaster recovery strategy for a multi-region cloud infrastructure? <em>(scenario)</em></summary>

**Answer:** Multi-region AWS setup with us-east-1 as primary and us-west-2 for DR, Terraform with per-region state but shared modules, S3 cross-region replication plus DynamoDB global tables plus cross-region RDS snapshots, Argo CD GitOps per region, Route53 failover, and quarterly FIS drills validating RTO/RPO.

**Detailed interview approach:**
I build a full DR strategy on an AWS multi-region setup, with primary workloads in us-east-1 and DR components in us-west-2. Infrastructure is defined in Terraform, with separate state files per region but shared modules.

I use S3 cross-region replication for static assets and DynamoDB global tables for distributed data. For stateful applications, I set up automated RDS snapshots with point-in-time recovery, copied across regions.

EKS clusters use GitOps with Argo CD in each region, pulling from the same Git repository so configuration stays consistent.

Route53 health checks with failover routing automatically redirect traffic during a region failure. I run quarterly DR drills with AWS Fault Injection Simulator to confirm the actual recovery time (RTO) and recovery point (RPO) meet the targets.

</details>

<details><summary>Q20. [Intermediate] How do you ensure disaster recovery in the cloud (GCP/Azure)? <em>(scenario)</em></summary>

**Answer:** Deploy across multiple zones, back up to remote regions, use Terraform to rebuild infrastructure quickly, and run DR drills regularly.

**Detailed interview approach:**
I start from a business-approved RTO and RPO, then map out data, configuration, identity, DNS/network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a separate failure domain (a group of resources that could fail together) or account.

I automate restoring into a clean environment and check integrity, application transactions, monitoring, and access before switching traffic over. A backup isn't considered good until a restore drill has proven it.

Regular exercises record the actual recovery time, any missing dependencies, and manual steps needed — and the runbook, capacity, DNS TTLs, contact paths, and retention policy get updated based on what they find.

</details>

<details><summary>Q21. [Intermediate] How do you automate backups in DevOps workflows? <em>(scenario)</em></summary>

**Answer:** Schedule backups with Velero for Kubernetes, automate database backups through scripts in the pipeline, and store backups in GCS or Azure Blob.

**Detailed interview approach:**
I start from a business-approved RTO and RPO, then map out data, configuration, identity, DNS/network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a separate failure domain (a group of resources that could fail together) or account.

I automate restoring into a clean environment and check integrity, application transactions, monitoring, and access before switching traffic over. A backup isn't considered good until a restore drill has proven it.

Regular exercises record the actual recovery time, any missing dependencies, and manual steps needed — and the runbook, capacity, DNS TTLs, contact paths, and retention policy get updated based on what they find.

</details>

<details><summary>Q22. [Intermediate] How do you perform Root Cause Analysis? <em>(asked in interview round)</em></summary>

**Answer:**

RCA is a structured, blameless process to find **why** an incident happened and what will **prevent it from happening again**. It starts after the service is stable, using evidence collected during the incident.

**Steps:**

1. **Stabilise first**: mitigation comes before analysis.
2. **Preserve evidence**: logs, metrics, traces, dumps, configuration and the timeline of actions taken.
3. **Build a timeline**: detection, impact start and end, every change and action, with timestamps.
4. **Identify the trigger and the contributing factors**: the change or event that started it, and the conditions that let it cause impact (missing test, weak alert, no rate limit).
5. **Ask "why" repeatedly** (5 Whys) or use a cause-and-effect diagram across people, process, technology and environment. Stop at causes you can act on.
6. **Validate**: reproduce in a lower environment or confirm with data.
7. **Define actions**: prevent, detect earlier, reduce impact, recover faster. Each with an owner and due date.
8. **Share the write-up** and track actions to completion.

**Example 5 Whys:**

```text
Checkout returned 5xx for 25 minutes
  Why? Orders service exhausted DB connections
  Why? A new query held connections for 30s
  Why? Missing index on a new column
  Why? Migration review did not include query plans
  Why? No performance test or index check in the pipeline
Actions: add index (fix), query-plan check in CI (prevent),
         alert on pool saturation (detect), connection timeouts (limit impact)
```

**Important points:**

- Blameless: "why did the system allow this?" rather than "who did this?".
- There is rarely a single root cause; list contributing factors.
- An RCA without tracked action items is just a story.

See also: [SRE](../ops/03-sre.md), [Observability and APM](../monitoring-tools/01-observability-and-apm.md), [Kubernetes observability, backup and DR](../kubernetes/09-observability-backup-dr.md)

**Interview-ready answer:**

> "I do RCA after the service is stable, and I make sure evidence is preserved during the incident. I build a detailed timeline of impact, changes and actions, then separate the trigger from the contributing factors that allowed it to cause impact. I use 5 Whys or a cause-and-effect diagram to keep asking why until I reach something we can act on, and I validate the cause with data or a reproduction. The output is a blameless write-up with actions to prevent, detect earlier, reduce impact and recover faster, each with an owner and date. I track those actions to completion, because the review only helps if the actions are done."

</details>

<details><summary>Q23. [Advanced] How do you define SLOs, alerts and actionable dashboards to reduce MTTR? <em>(asked in interview round)</em></summary>

**Answer:**

I define what "good" means from the user's perspective (SLIs and SLOs), alert on how fast we are consuming the error budget, and build dashboards that move from "is the user affected?" to "where is the problem?" in a few clicks. That shortens detection and diagnosis, which is most of MTTR.

**Definitions:**

- **SLI**: a measurement of good events over valid events, for example the ratio of successful requests faster than 300 ms.
- **SLO**: a target for the SLI over a window, for example 99.9% over 30 days.
- **Error budget**: `1 - SLO`, here 0.1%, about 43 minutes of full downtime per 30 days. If the budget is spent, reliability work takes priority over features.

**Steps:**

1. Pick critical user journeys (login, checkout, search).
2. Define SLIs for availability and latency at the edge closest to the user.
3. Set realistic SLOs with stakeholders, based on historical data.
4. Alert on **multi-window, multi-burn-rate** conditions rather than raw thresholds.
5. Every page has a runbook and an owner; cause-based alerts go to tickets.
6. Build dashboards in layers: SLO overview, service golden signals (RED/USE), dependencies, then per-instance detail, linked together and to traces and logs.
7. Review alerts after each incident: missed, noisy or unactionable alerts get fixed.

**Burn-rate alerting (99.9% SLO, 30-day window):**

| Severity | Burn rate | Long window | Short window | Budget consumed |
| --- | --- | --- | --- | --- |
| Page | 14.4 | 1 hour | 5 minutes | 2% |
| Page | 6 | 6 hours | 30 minutes | 5% |
| Ticket | 1 | 3 days | 6 hours | 10% |

```promql
# Page: fast burn
(
  sum(rate(http_requests_total{job="checkout",code=~"5.."}[1h]))
  / sum(rate(http_requests_total{job="checkout"}[1h]))
) > (14.4 * 0.001)
and
(
  sum(rate(http_requests_total{job="checkout",code=~"5.."}[5m]))
  / sum(rate(http_requests_total{job="checkout"}[5m]))
) > (14.4 * 0.001)
```

The long window gives significance; the short window makes the alert reset quickly once the problem is fixed.

**Dashboard flow:**

```text
SLO overview (budget remaining, burn rate)
      |
      v
Service RED: rate, errors, duration (p50/p95/p99) per route
      |
      v
Dependencies: DB, cache, queues, third parties
      |
      v
Infrastructure USE: utilisation, saturation, errors per node/Pod
      |
      v
Exemplars --> traces --> logs (same trace ID)
```

**Important points:**

- 100% is never the right SLO; it leaves no room for change.
- Burn-rate alerts reduce noise and catch both fast outages and slow degradation.
- MTTR also improves with runbooks, recent-change annotations on dashboards and one-click rollback.

See also: [Observability and APM](../monitoring-tools/01-observability-and-apm.md), [Grafana and Alertmanager](../monitoring-tools/03-grafana-and-alertmanager.md), [Prometheus](../monitoring-tools/02-prometheus.md), [SRE](../ops/03-sre.md)

**Interview-ready answer:**

> "I start from critical user journeys and define SLIs at the edge, such as the percentage of successful checkout requests under 300 milliseconds, then agree SLOs like 99.9 percent over 30 days, which gives an error budget of about 43 minutes. Instead of static thresholds I use multi-window, multi-burn-rate alerts: for example page when the burn rate is above 14.4 over both one hour and five minutes, and open a ticket for slow burns over days. Every page has a runbook and an owner, and cause-level alerts go to tickets to avoid fatigue. Dashboards are layered from SLO overview to golden signals, dependencies and infrastructure, with deployment annotations and links from metrics to traces and logs. That reduces both detection time and diagnosis time, which is most of MTTR."

</details>

<details><summary>Q24. [Advanced] Chaos engineering — how would you use it in production? <em>(asked in interview round)</em></summary>

**Answer:**

Chaos engineering is controlled experimentation to prove the system tolerates failure, not random breakage.

1. Define steady state with SLO metrics (error rate, latency).
2. Form a hypothesis: "if one AZ's nodes are lost, error rate stays under 0.5 percent".
3. Start in staging, then production with a small blast radius, during business hours, with the team watching.
4. Inject the fault: Pod kill, node drain, latency, dependency outage.
5. Automatic abort conditions tied to alarms; a tested rollback.
6. Fix findings, then automate the experiment as a recurring game day.

Tools: AWS Fault Injection Service, Azure Chaos Studio, `LitmusChaos`, Chaos Mesh, Gremlin.

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata: { name: kill-one-orders-pod, namespace: chaos }
spec:
  action: pod-kill
  mode: one
  selector: { namespaces: [prod], labelSelectors: { app: orders } }
```

**Interview-ready answer:**

> I treat chaos engineering as a scientific experiment. I define steady state from SLO metrics, write a hypothesis, and run the fault first in staging, then in production with a small blast radius and stop conditions wired to alarms. Typical experiments are killing Pods, draining a node, adding latency to a dependency or failing an AZ, using AWS FIS, Azure Chaos Studio or Chaos Mesh. Every experiment ends with action items, and the useful ones become regular automated game days.

See also: [Chaos engineering safely in production](../ops/03-sre.md), [Chaos engineering in Kubernetes](../kubernetes/09-observability-backup-dr.md)

</details>
