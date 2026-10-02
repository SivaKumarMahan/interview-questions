# Ops: FinOps

> Reducing cloud cost without hurting reliability, investigating bill spikes, and building cost awareness into Terraform, CI/CD and observability retention.

## Interview Questions

### 1. How do you optimize infrastructure cost without impacting performance or reliability?

**Answer:**

I start by getting the evidence right: I break down cost by account, service, environment, owner, region, tag, SKU, and a real unit like cost per request or per customer. Then I compare that billing data against utilization, latency, errors, capacity forecasts, and SLOs.

That comparison is what tells waste apart from legitimate growth, so I'm not just cutting an arbitrary percentage across the board.

From there, typical actions include deleting confirmed orphaned non-production resources, scheduling resources to shut off when idle, right-sizing based on real usage percentiles and load tests, autoscaling with a safe minimum, storage lifecycle and tiering, controlling log retention and how many unique label combinations get tracked, more efficient data transfer, the right managed-service tier, and reserved or savings commitments for stable baseline load.

Spot capacity only goes to workloads that can tolerate being interrupted.

Often, improving the architecture or the application's own efficiency saves more than just shrinking instance sizes.

Every change has clear performance and rollback criteria, and I canary it where I can. Budgets, anomaly alerts, ownership tags, cost estimates during IaC review, quotas, showback reporting, and regular reviews keep the optimization work going instead of it being a one-time push.

After every change, I check that cost per unit actually improved and that SLOs are still being met.

### 2. How would you identify and reduce cloud infrastructure costs without sacrificing performance or reliability? *(scenario)*

**Answer:** Use tagging and Cost Explorer to find spending patterns, right-size EC2 from CloudWatch data plus autoscaling, use the Cluster Autoscaler and HPA on EKS, use spot instances for non-critical workloads, apply S3 lifecycle rules and DynamoDB autoscaling, and schedule off-hours scaling alongside Reserved Instances or Savings Plans.

**Detailed interview approach:**
I start with thorough tagging and AWS Cost Explorer to see spending patterns by team, application, and environment.

For EC2, I look at CloudWatch metrics to find oversized instances and set up autoscaling with instance types that actually match the workload.

For EKS clusters, I use the Kubernetes Cluster Autoscaler to adjust node counts based on pod demand, and the Horizontal Pod Autoscaler to scale deployments based on CPU and memory use. I use spot instances for non-critical workloads, spreading across instance types to avoid disruption.

For storage, I use S3 lifecycle policies to move infrequently accessed data to cheaper tiers, and set up DynamoDB autoscaling to match actual throughput.

Scheduled scaling through Terraform reduces resources during off-hours in non-production environments, and I regularly review Reserved Instance coverage and Savings Plans to keep discounts working for predictable workloads.

This approach has cut costs by around 43% in practice while keeping the same performance targets.

### 3. Your cloud bill increases by 40% overnight. How do you investigate it?

**Answer:**

I compare the affected day or hour against the normal baseline, broken down by service, account, region, SKU, usage type, tag, and resource ID.

I check for recent deployments, autoscaling events, new resources, a pricing or commitment change, data egress, NAT traffic, log or metrics ingestion, snapshots, database I/O, serverless invocations, and marketplace charges.

A sudden jump in compute or API usage is also a signal to check for leaked credentials or crypto-mining.

I only shut down what I've confirmed is waste or a compromise: disable a leaked identity, cap runaway autoscaling or logging, stop non-production resources I own, or block a job that's clearly misbehaving. I never terminate an unfamiliar stateful production resource just because a cost dashboard flagged it.

Cloud audit logs and the owner/tag metadata tell me who created or last changed the resource.

Once it's fixed, I confirm application SLOs are healthy and billing has actually come back down. Then I add budget and anomaly alerts, require ownership tags, set quotas and scaling limits, tighten log retention policy, and add cost review to IaC changes.

Finally, I write down whether the spike was waste, an attack, expected traffic growth, or just a tagging/allocation error.

### 4. How do you implement infrastructure cost optimization in Terraform? *(scenario)*

**Answer:** Use variables for instance sizes, add auto-scaling groups, apply resource tags, and use lifecycle policies to clean up unused resources.

**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

### 5. How do you set up cost-aware CI/CD pipelines to prevent runaway spend? *(scenario)*

**Answer:** Add cost estimation to the pipeline so it estimates the infra cost of each change, set budget checks and alerts, use autoscaling and spot instances where they fit, and block a merge if the estimated cost goes over a threshold.

Mini-case: a pipeline flagged that a proposed infra change would triple the monthly cost. That required manager approval before it could go through, which prevented an accidental large spend.
**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

### 6. How do you integrate cost monitoring into DevOps pipelines? *(scenario)*

**Answer:** Pull data from the GCP Billing API or Azure Cost Management, add cost checks into the pipeline, and alert when the estimated cost goes over budget.

**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

### 7. How do you scale observability storage and retention cost-effectively? *(scenario)*

**Answer:** Aggregate and downsample older metrics (Prometheus remote write to Thanos/Cortex), use tiered log retention (hot/warm/cold), and set retention policies that match compliance requirements.

Mini-case: we moved 30-day detailed metrics to Thanos with 90-day downsampled retention. That cut monitoring costs by 60% while keeping the accuracy we needed for alerts.
**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.
