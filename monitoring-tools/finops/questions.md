## 1. How do you control monitoring and logging cost without losing visibility?

**Answer:**

First I break down cost by owner and by signal type: ingestion, active series, storage, queries, and egress. That shows me where the money is actually going.

Then I cut waste. I remove duplicate collectors, fix labels that can produce unlimited values (a cardinality problem), downsample old metrics, and set log retention and log levels per service. I archive anything I'm required to keep, and I sample normal traces while keeping errors and important transactions in full.

Budgets and anomaly alerts catch any regression early.

Before I remove any data, I ask what SLO, investigation, security case, or compliance requirement depends on it. After a change, I test the dashboards, alerts, and a real incident query to confirm the cost per transaction actually dropped without creating a blind spot.

## 2. Observability cost rises 40% overnight. What do you investigate?

**Answer:**

I start by slicing the cost by account, service, data type, table or index, metric namespace, team, and hour. That usually points to where the spike started.

Then I look at recent deployments and config changes. Common causes are debug logging left on, duplicate log forwarding, new diagnostic categories, a spike in the number of unique label combinations (cardinality), a change in trace sampling, a retention change, extra egress, or just a real increase in traffic.

I also check security: an unexpected workload or a compromised credential can generate a flood of monitoring data too.

Once I've confirmed the actual source, I cap only that source safely, preserve any evidence I'm required to keep, and tell the owner what happened. For a permanent fix, I add label limits, a reviewed collection policy, quotas and budgets, anomaly alerts, and a cost test that runs whenever monitoring configuration changes.
