## 1. How do you optimize infrastructure cost without impacting performance or reliability?

**Answer:**

I start by getting the evidence right: I break down cost by account, service, environment, owner, region, tag, SKU, and a real unit like cost per request or per customer. Then I compare that billing data against utilization, latency, errors, capacity forecasts, and SLOs.

That comparison is what tells waste apart from legitimate growth, so I'm not just cutting an arbitrary percentage across the board.

From there, typical actions include deleting confirmed orphaned non-production resources, scheduling resources to shut off when idle, right-sizing based on real usage percentiles and load tests, autoscaling with a safe minimum, storage lifecycle and tiering, controlling log retention and how many unique label combinations get tracked, more efficient data transfer, the right managed-service tier, and reserved or savings commitments for stable baseline load.

Spot capacity only goes to workloads that can tolerate being interrupted.

Often, improving the architecture or the application's own efficiency saves more than just shrinking instance sizes.

Every change has clear performance and rollback criteria, and I canary it where I can. Budgets, anomaly alerts, ownership tags, cost estimates during IaC review, quotas, showback reporting, and regular reviews keep the optimization work going instead of it being a one-time push.

After every change, I check that cost per unit actually improved and that SLOs are still being met.

## 2. Your cloud bill increases by 40% overnight. How do you investigate it?

**Answer:**

I compare the affected day or hour against the normal baseline, broken down by service, account, region, SKU, usage type, tag, and resource ID.

I check for recent deployments, autoscaling events, new resources, a pricing or commitment change, data egress, NAT traffic, log or metrics ingestion, snapshots, database I/O, serverless invocations, and marketplace charges.

A sudden jump in compute or API usage is also a signal to check for leaked credentials or crypto-mining.

I only shut down what I've confirmed is waste or a compromise: disable a leaked identity, cap runaway autoscaling or logging, stop non-production resources I own, or block a job that's clearly misbehaving. I never terminate an unfamiliar stateful production resource just because a cost dashboard flagged it.

Cloud audit logs and the owner/tag metadata tell me who created or last changed the resource.

Once it's fixed, I confirm application SLOs are healthy and billing has actually come back down. Then I add budget and anomaly alerts, require ownership tags, set quotas and scaling limits, tighten log retention policy, and add cost review to IaC changes.

Finally, I write down whether the spike was waste, an attack, expected traffic growth, or just a tagging/allocation error.
