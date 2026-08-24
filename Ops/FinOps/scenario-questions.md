## 1. How do you scale observability storage and retention cost-effectively?

**Answer:** Aggregate and downsample older metrics (Prometheus remote write to Thanos/Cortex), use tiered log retention (hot/warm/cold), and set retention policies that match compliance requirements.

Mini-case: we moved 30-day detailed metrics to Thanos with 90-day downsampled retention. That cut monitoring costs by 60% while keeping the accuracy we needed for alerts.
**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

## 2. How do you set up cost-aware CI/CD pipelines to prevent runaway spend?

**Answer:** Add cost estimation to the pipeline so it estimates the infra cost of each change, set budget checks and alerts, use autoscaling and spot instances where they fit, and block a merge if the estimated cost goes over a threshold.

Mini-case: a pipeline flagged that a proposed infra change would triple the monthly cost. That required manager approval before it could go through, which prevented an accidental large spend.
**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

## 3. How do you integrate cost monitoring into DevOps pipelines?

**Answer:** Pull data from the GCP Billing API or Azure Cost Management, add cost checks into the pipeline, and alert when the estimated cost goes over budget.

**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

## 4. How do you implement infrastructure cost optimization in Terraform?

**Answer:** Use variables for instance sizes, add auto-scaling groups, apply resource tags, and use lifecycle policies to clean up unused resources.

**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.


## 5. How would you identify and reduce cloud infrastructure costs without sacrificing performance or reliability?

**Answer:** Use tagging and Cost Explorer to find spending patterns, right-size EC2 from CloudWatch data plus autoscaling, use the Cluster Autoscaler and HPA on EKS, use spot instances for non-critical workloads, apply S3 lifecycle rules and DynamoDB autoscaling, and schedule off-hours scaling alongside Reserved Instances or Savings Plans.

**Detailed interview approach:**
I start with thorough tagging and AWS Cost Explorer to see spending patterns by team, application, and environment.

For EC2, I look at CloudWatch metrics to find oversized instances and set up autoscaling with instance types that actually match the workload.

For EKS clusters, I use the Kubernetes Cluster Autoscaler to adjust node counts based on pod demand, and the Horizontal Pod Autoscaler to scale deployments based on CPU and memory use. I use spot instances for non-critical workloads, spreading across instance types to avoid disruption.

For storage, I use S3 lifecycle policies to move infrequently accessed data to cheaper tiers, and set up DynamoDB autoscaling to match actual throughput.

Scheduled scaling through Terraform reduces resources during off-hours in non-production environments, and I regularly review Reserved Instance coverage and Savings Plans to keep discounts working for predictable workloads.

This approach has cut costs by around 43% in practice while keeping the same performance targets.
