## 1. How do you control monitoring and logging cost without losing visibility?

**Answer:**

I allocate ingestion, active series, storage, query and egress by owner and signal. Then I remove duplicate collectors, fix unbounded labels, aggregate/downsample old metrics, use service-specific log retention and levels, archive required records, and sample normal traces while retaining errors and important transactions. Budgets and anomaly alerts catch regressions.

Before reducing data I ask which SLO, investigation, security or compliance decision it supports. Afterward I test dashboards, alerts and a representative incident query and confirm cost per service transaction decreases without creating a detection gap.

## 2. Observability cost rises 40% overnight. What do you investigate?

**Answer:**

I compare by account/workspace, service, data type, table/index, metric namespace, team and hour. I correlate deployments and configuration changes and check debug logging, duplicate forwarding, new diagnostic categories, cardinality explosion, trace sampling, retention, egress and real traffic. Security review checks whether unexpected workload or credential abuse produced telemetry.

I cap only the confirmed source safely, preserve required evidence, and notify the owner. The permanent fix adds bounded labels, reviewed collection policy, quotas/budgets, anomaly alerts and cost tests for telemetry configuration.
