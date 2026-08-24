# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## SRE, Reliability & Incident Management

### 10.1 SRE principles and implementing error budgets

- **SRE** applies software-engineering thinking to operations. You measure reliability with **SLIs** (like latency or availability), set a target called an **SLO** (say, 99.9%), and the gap between that and 100% is your **error budget** — the amount of unreliability you're allowed to spend.
- **Error budget policy:** if the budget is healthy, ship features fast. If it's used up, freeze risky releases and put the focus on reliability until it recovers. This ties feature velocity to reliability in an objective way, instead of an argument.
- **Other principles:** remove repetitive manual work through automation, run blameless postmortems, keep that manual work under roughly half of everyone's time, and watch the **four golden signals** — latency, traffic, errors, and saturation (how close a resource is to running out of capacity).

### 10.2 Post-mortem / effective incident review process

- **Blameless:** focus on the systems and contributing factors, not on blaming a person.
- **Structure:** a timeline of events, the impact (users affected, duration, SLO impact), how it was detected, the root cause (found through something like the 5 Whys), what went well and what didn't, and concrete follow-ups with an owner and a due date.
- **Process:** any significant incident triggers one, write it up promptly, review it with stakeholders, track the follow-ups to completion, and share it across the org so others learn from it. The goal is fixing the system, not just this one incident.

### 10.3 Lead a team through a critical production issue (behavioral — STAR)

Use the **STAR** format: Situation (a severe outage), Task (your role, say incident commander), Action (declared the incident, opened a war room, assigned roles for communication/operations/scribe, mitigated first through rollback or failover, kept stakeholders updated regularly), Result (restored service, met the recovery target, ran a blameless postmortem, and drove the follow-up fixes).

Emphasize staying calm, communicating clearly, fixing the immediate problem before digging into the cause, and following through afterward.

### 10.4 Handle complex/varying-traffic scaling scenarios for Kubernetes

- Combine the **Horizontal Pod Autoscaler** (per service, on CPU, requests per second, or custom metrics through Prometheus Adapter, or **KEDA** for event/queue-driven scaling), the **Vertical Pod Autoscaler** for right-sizing, and the **Cluster Autoscaler** or **Karpenter** for adding nodes.
- For **predictable peaks**, use scheduled scaling to pre-warm capacity. For **spiky traffic**, buffer it with queues (SQS/Kafka) plus KEDA. For **sudden node demand**, Karpenter provisions fast and cost-consciously, combined with spot instances.
- Set real resource requests and limits, PodDisruptionBudgets, topology spread, and readiness probes, then load-test to confirm it all works, and keep an eye on cost. Different services need different scaling policies based on how their traffic actually behaves.

### 10.5 Experience managing large-scale environments — challenges (behavioral)

Talk about the actual scale you worked with (how many clusters, services, or regions) and the real challenges: config drift and standardizing things (solved with IaC and GitOps), observability at scale (too many unique label combinations, and the cost that comes with it — solved with tools like Thanos or sampling), coordinating across teams and rolling out changes safely (progressive delivery), cost optimization, reducing on-call load, and staying reliable through upgrades and migrations.

For each challenge, be ready to say specifically what you did about it.
---
