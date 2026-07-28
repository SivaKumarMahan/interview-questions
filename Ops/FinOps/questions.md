## 1. How do you optimize infrastructure cost without impacting performance or reliability?

**Answer:**

I start with allocation and evidence: cost by account/subscription, service, environment, owner, region, tag, SKU, and unit such as cost per request/customer. I compare billing with utilization, latency, errors, capacity forecasts, and SLOs.

This distinguishes waste from legitimate growth and prevents arbitrary percentage cuts.

Actions include deleting confirmed orphaned nonproduction resources, schedules, rightsizing from percentiles and load tests, autoscaling with safe minimums, storage lifecycle/tiering, log retention and cardinality (number of unique label combinations) control, efficient data transfer, appropriate managed-service tiers, and reserved/savings commitments for stable baselines.

Spot capacity is used only for interruption-tolerant workloads.

Architecture and application efficiency often save more than instance downsizing.

Each change has performance and rollback criteria and is canaried where possible. Budgets, anomaly alerts, ownership tags, cost estimates in IaC review, quotas, showback, and regular reviews keep optimization continuous.

I verify cost per unit and SLOs after every change.

## 2. Your cloud bill increases by 40% overnight. How do you investigate it?

**Answer:**

I compare the affected day/hour with the normal baseline by service, account, region, SKU, usage type, tag, and resource ID.

I check recent deployments, autoscaling, new resources, commitment or pricing changes, data egress, NAT, logs/metrics ingestion, snapshots, database I/O, serverless invocation, and marketplace charges.

A sudden compute or API increase also triggers a security check for leaked credentials or crypto-mining.

I contain only confirmed waste or compromise: disable leaked identity, cap runaway scaling or logging, stop owned nonproduction resources, or block an erroneous job. I do not terminate unknown stateful production resources from a cost dashboard.

Cloud audit logs and owner/tag data identify who created or changed the resource.

After correction I verify application SLOs and billing/usage decline, then add budget/anomaly alerts, required ownership tags, quotas, scaling bounds, log retention/cardinality (number of unique label combinations) policy, and IaC cost review.

I document whether the increase was waste, attack, expected traffic, or allocation error.
