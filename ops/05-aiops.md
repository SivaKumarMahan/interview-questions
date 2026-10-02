# Ops: AIOps

> What AIOps is, how it uses observability data, an end-to-end incident flow, and how to keep automated fixes safe.

## Key Concepts

### AIOps Overview

**AIOps** applies analytics and machine learning to IT operations data. It helps teams spot unusual behavior, group related events together, prioritize what matters most, assist with diagnosis, forecast capacity, and safely automate repeatable responses.

**Observability** supplies the raw evidence: metrics, logs, traces, service relationships, deployment or configuration events, and who owns each service. AIOps uses those signals — it doesn't replace them.

It also doesn't replace instrumentation, SRE ownership, or having someone lead an incident.

```text
monitoring data and changes -> clean and add context -> group related events and detect unusual behavior
-> rank impact/probable causes -> recommend action
-> approval or bounded runbook -> verify -> learn
```

A useful result looks like real evidence: "latency began after version 42, it affects two regions, traces point to database pool exhaustion, and a rollback fixed this same pattern before." A vague anomaly score on its own isn't useful.

**What automation needs:**

- Confidence thresholds
- An identity with only the access it needs
- Preconditions before it acts
- Rate limits and a capped blast radius
- A dry-run mode
- Approval for anything risky
- A rollback path and a kill switch
- Audit evidence that can't be changed after the fact
- A check against the SLO after the action runs

**What to measure:** detection precision and recall, how much duplicate noise gets reduced, whether alerts are actually actionable, time to detect/acknowledge/restore, whether the top-ranked root cause is usually right, how often the fix actually works, and how often an action turns out to be unsafe.

Feedback has to tell a temporary workaround apart from a real fix — otherwise the system just learns to keep restarting a service instead of ever fixing the underlying leak.

### AIOps Incident Flow: Kubernetes CPU Throttling

AIOps means applying analytics and machine learning to IT operations. Its job is to improve monitoring and response, not to replace the whole software-delivery lifecycle. A practical CPU-throttling flow looks like this:

1. **Prometheus** collects container CPU usage and throttling counters.
2. **Alerting** detects sustained throttling and attaches context: the service, cluster, deployment, and any recent changes.
3. The **AIOps layer** checks the signal against recent deployments, config changes, traffic increases, node pressure, and similar past incidents.
4. It **recommends a limited action**, such as restoring known-good resource requests, scaling replicas, or rolling back a bad release.
5. An **approved runbook** applies the change, watches the rollout, and confirms that throttling, latency, and errors return to normal.
6. The platform **notifies the team** and stores the evidence, decision, action, and result for audit and future learning.

Automatic fixes need confidence thresholds, an identity with only the access it needs, limits on how big a change can be, human approval for risky actions, a rollback path, and a check afterward. Increasing CPU blindly can hide inefficient code or just push the pressure onto another dependency.

Tools like PagerDuty, Datadog, Dynatrace, ManageEngine, Prometheus, Grafana, and various automation platforms can all play a part, but AIOps is an approach to running operations, not one single product.

## Interview Questions

<details><summary>Q1. [Basic] What is AIOps, and how is it related to observability?</summary>

**Answer:**

AIOps means using analytics and machine learning to improve IT operations. Observability is what collects and connects the raw evidence — metrics, logs, traces, topology, and changes. AIOps takes that evidence and uses it for anomaly detection, grouping related events, ranking impact, helping find the probable cause, forecasting, and safely automating a fix.

For example, instead of paging separately for pod CPU throttling, API latency, and HPA saturation, AIOps can group all three into one incident, line up the start time with a recent deployment, and recommend restoring the known-good CPU requests. The team still checks that evidence before acting on it.

Without good monitoring data, clear ownership, and real runbooks, AIOps just ends up automating noisy guesses.

</details>

<details><summary>Q2. [Intermediate] Describe an end-to-end AIOps incident flow.</summary>

**Answer:**

Collectors bring in normalized monitoring data and change events, tagged with service, environment, region, and ownership. Correlation groups the symptoms together by time, topology, and dependency.

Anomaly and SLO logic detects real impact, and the system ranks the likely causes, backed by traces, logs, metrics, and recent changes. It recommends a runbook — a low-risk, pre-approved action might run automatically, while anything riskier needs a human's approval.

The platform then checks the real user transaction and SLO, rolls back if it needs to, records every decision, and learns from the confirmed outcome.

When rolling this out, I start with one high-volume, well-understood type of incident and evaluate it against historical data, comparing it to existing rules and what a human would have decided, before I let it run automation on its own.

</details>

<details><summary>Q3. [Advanced] How do you make an AIOps fix safe?</summary>

**Answer:**

I require a specific, confidently detected condition, a fresh check of the current state, an identity with only the access it needs, resource and rate limits, a cap on attempts, a timeout, dry-run evidence, a kill switch, rollback, and audit logs that can't be altered after the fact.

Anything involving stateful deletion, broad access changes, data recovery, or a security incident stays under human control.

After every action, I run the original synthetic or business transaction and check errors, latency, saturation, and dependencies. If that check fails, the automation stops and escalates — it doesn't just keep looping.

I track false correlations and any action that turned out unsafe or ineffective, and I expire old approvals whenever the architecture changes.

</details>

<details><summary>Q4. [Intermediate] An AIOps tool reports an anomaly but users see no problem. What do you do?</summary>

**Answer:**

I don't act on the anomaly score alone. I look at the underlying feature and its baseline, seasonality, any deployment or traffic changes, missing data, changes to labels or topology, and whether the real user-facing SLIs are still healthy.

It might be an early capacity warning, a legitimate new pattern, or the model itself drifting.

I keep the event as non-paging evidence, only tune the segmentation or time window after actually analyzing it, and measure the impact of false positives. If it does point to a real future risk, I open a capacity ticket or a lower-severity forecast alert instead of paging anyone.

I judge the model against confirmed incidents — not by how many anomalies it happens to flag.

</details>
