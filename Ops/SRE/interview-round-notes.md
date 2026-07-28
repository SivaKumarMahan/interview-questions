# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## SRE, Reliability & Incident Management

### 10.1 SRE principles & implementing error budgets

- **SRE** applies software engineering to operations: measure reliability with **SLIs** (e.g. latency, availability), set **SLOs** (targets, e.g. 99.9%), and derive an **error budget** = `100% − SLO` (the allowed unreliability).
- **Error budget policy:** if the budget is healthy, ship features fast; if it's **exhausted**, freeze risky releases and shift focus to reliability until it recovers. This aligns dev velocity with reliability objectively.
- **Other principles:** eliminate toil via automation, embrace blameless postmortems, cap toil (~50%), and monitor the **four golden signals** (latency, traffic, errors, saturation (how close a resource is to its limit)).

### 10.2 Post-mortem / effective incident review process

- **Blameless:** focus on systems and contributing factors, not individuals.
- **Structure:** timeline of events, impact (users/duration/SLO), detection, root cause (5 Whys / contributing factors), what went well/poorly, and **actionable follow-ups with owners and due dates**.
- **Process:** trigger for any significant incident, write it promptly, review with stakeholders, track action items to completion, and share org-wide so others learn. The goal is systemic improvement and preventing recurrence.

### 10.3 Lead a team through a critical production issue (behavioral — STAR)

Frame with **STAR**: Situation (severe outage), Task (your role, e.g. incident commander), Action (declared incident, set up a war room/bridge, assigned roles — comms, ops, scribe — mitigated first (rollback/failover), communicated status to stakeholders regularly), Result (restored service, RTO met, ran a blameless postmortem, drove fixes).

Emphasize calm coordination, clear communication, mitigate-before-diagnose, and follow-through.

### 10.4 Handle complex/varying-traffic scaling scenarios for K8s

- Combine **HPA** (per-service, on CPU/RPS/custom metrics via Prometheus Adapter or **KEDA** for event-driven/queue-based scaling), **VPA** for right-sizing, and **Cluster Autoscaler/Karpenter** for nodes.
- **Predictable peaks:** scheduled scaling/pre-warming; **spiky:** buffer with queues (SQS/Kafka) and KEDA; **bursty node needs:** Karpenter for fast, cost-aware provisioning + spot instances.
- Set proper requests/limits, PDBs, topology spread, and readiness probes; load-test to validate; watch cost. Different services get different policies based on their traffic shape.

### 10.5 Experience managing large-scale environments — challenges (behavioral)

Talk about concrete scale (N clusters/services/regions) and challenges: config drift and standardization (solved with IaC + GitOps), observability at scale (cardinality (number of unique label combinations), cost — Thanos/sampling), multi-team coordination and safe rollouts (progressive delivery), cost optimization, on-call/toil reduction, and reliability during upgrades/migrations.

Pair each challenge with what you did about it.
---
