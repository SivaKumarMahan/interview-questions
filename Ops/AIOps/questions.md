## 1. What is AIOps, and how is it related to observability?

**Answer:**

AIOps means using analytics and machine learning to improve IT operations. Observability is what collects and connects the raw evidence — metrics, logs, traces, topology, and changes. AIOps takes that evidence and uses it for anomaly detection, grouping related events, ranking impact, helping find the probable cause, forecasting, and safely automating a fix.

For example, instead of paging separately for pod CPU throttling, API latency, and HPA saturation, AIOps can group all three into one incident, line up the start time with a recent deployment, and recommend restoring the known-good CPU requests. The team still checks that evidence before acting on it.

Without good monitoring data, clear ownership, and real runbooks, AIOps just ends up automating noisy guesses.

## 2. Describe an end-to-end AIOps incident flow.

**Answer:**

Collectors bring in normalized monitoring data and change events, tagged with service, environment, region, and ownership. Correlation groups the symptoms together by time, topology, and dependency.

Anomaly and SLO logic detects real impact, and the system ranks the likely causes, backed by traces, logs, metrics, and recent changes. It recommends a runbook — a low-risk, pre-approved action might run automatically, while anything riskier needs a human's approval.

The platform then checks the real user transaction and SLO, rolls back if it needs to, records every decision, and learns from the confirmed outcome.

When rolling this out, I start with one high-volume, well-understood type of incident and evaluate it against historical data, comparing it to existing rules and what a human would have decided, before I let it run automation on its own.

## 3. How do you make an AIOps fix safe?

**Answer:**

I require a specific, confidently detected condition, a fresh check of the current state, an identity with only the access it needs, resource and rate limits, a cap on attempts, a timeout, dry-run evidence, a kill switch, rollback, and audit logs that can't be altered after the fact.

Anything involving stateful deletion, broad access changes, data recovery, or a security incident stays under human control.

After every action, I run the original synthetic or business transaction and check errors, latency, saturation, and dependencies. If that check fails, the automation stops and escalates — it doesn't just keep looping.

I track false correlations and any action that turned out unsafe or ineffective, and I expire old approvals whenever the architecture changes.

## 4. An AIOps tool reports an anomaly but users see no problem. What do you do?

**Answer:**

I don't act on the anomaly score alone. I look at the underlying feature and its baseline, seasonality, any deployment or traffic changes, missing data, changes to labels or topology, and whether the real user-facing SLIs are still healthy.

It might be an early capacity warning, a legitimate new pattern, or the model itself drifting.

I keep the event as non-paging evidence, only tune the segmentation or time window after actually analyzing it, and measure the impact of false positives. If it does point to a real future risk, I open a capacity ticket or a lower-severity forecast alert instead of paging anyone.

I judge the model against confirmed incidents — not by how many anomalies it happens to flag.
