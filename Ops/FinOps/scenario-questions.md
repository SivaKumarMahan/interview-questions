## 1. How do you scale observability storage and retention cost-effectively?
**Answer:** Use metric aggregations and downsampling for older data (Prometheus remote write to Thanos/Cortex), tiered log retention (hot/warm/cold), and set retention policies aligned to compliance requirements. Mini-case: We moved 30-day granular metrics to Thanos with 90-day downsampled retention, cutting monitoring costs by 60% while keeping required fidelity for alerts.

**Detailed interview approach:**
I compare cost by service, account/subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the rise comes from real traffic, runaway autoscaling, orphaned resources, log/egress volume, a pricing/commitment change, or compromised compute. I contain safely with budgets, scaling caps, quotas, or stopping confirmed non-production waste—without deleting stateful production resources blindly. Terraform plans receive cost estimates and policy/approval above thresholds. Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved/spot choices, and owner showback make optimization continuous, and I verify performance/SLOs after reducing cost.

## 2. How do you set up cost-aware CI/CD pipelines to prevent runaway spend?
**Answer:** Integrate cost estimation in pipelines (estimate infra cost for new changes), set budget checks and alerts, enforce autoscaling and spot instances where appropriate, and gate merges if estimated cost exceeds threshold. Mini-case: A pipeline reported a proposed infra change would increase monthly cost by 3x; it required a manager approval step, preventing accidental large spend.

**Detailed interview approach:**
I compare cost by service, account/subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the rise comes from real traffic, runaway autoscaling, orphaned resources, log/egress volume, a pricing/commitment change, or compromised compute. I contain safely with budgets, scaling caps, quotas, or stopping confirmed non-production waste—without deleting stateful production resources blindly. Terraform plans receive cost estimates and policy/approval above thresholds. Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved/spot choices, and owner showback make optimization continuous, and I verify performance/SLOs after reducing cost.

## 3. How do you integrate cost monitoring into DevOps pipelines?
**Answer:** Use GCP Billing API/Azure Cost Management → Add cost checks in pipelines → Alert if estimated cost exceeds budget.

**Detailed interview approach:**
I compare cost by service, account/subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the rise comes from real traffic, runaway autoscaling, orphaned resources, log/egress volume, a pricing/commitment change, or compromised compute. I contain safely with budgets, scaling caps, quotas, or stopping confirmed non-production waste—without deleting stateful production resources blindly. Terraform plans receive cost estimates and policy/approval above thresholds. Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved/spot choices, and owner showback make optimization continuous, and I verify performance/SLOs after reducing cost.

## 4. How do you implement Infrastructure Cost Optimization in Terraform?
**Answer:** Use variables for instance sizes → Add auto-scaling groups → Apply resource tags → Use lifecycle policies to delete unused resources.

**Detailed interview approach:**
I compare cost by service, account/subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the rise comes from real traffic, runaway autoscaling, orphaned resources, log/egress volume, a pricing/commitment change, or compromised compute. I contain safely with budgets, scaling caps, quotas, or stopping confirmed non-production waste—without deleting stateful production resources blindly. Terraform plans receive cost estimates and policy/approval above thresholds. Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved/spot choices, and owner showback make optimization continuous, and I verify performance/SLOs after reducing cost.


## 5. How would you identify and reduce cloud infrastructure costs without sacrificing performance or reliability?

**Answer:** Tagging + Cost Explorer to find spend patterns → right-size EC2 from CloudWatch + autoscaling → Cluster Autoscaler + HPA on EKS → Spot for non-critical workloads → S3 lifecycle + DynamoDB autoscaling → scheduled off-hours scaling + Reserved Instances/Savings Plans.

**Detailed interview approach:**
My approach to cloud cost optimization starts with comprehensive tagging and AWS Cost Explorer to identify spending patterns by team, application, and environment. For EC2 instances, I analyze CloudWatch metrics to identify oversized instances and implement auto-scaling with appropriate instance types based on workload patterns.

For EKS clusters, I use the Kubernetes Cluster Autoscaler to dynamically adjust node counts based on pod demand, and the Horizontal Pod Autoscaler to scale deployments based on CPU/memory utilization. I use Spot Instances for non-critical workloads with instance diversification to avoid disruptions.

For storage optimization, I use S3 lifecycle policies to transition infrequently accessed data to cheaper storage tiers and set up DynamoDB auto-scaling to match actual throughput needs. Scheduled scaling through Terraform reduces resources during off-hours for non-production environments, and regular reviews of Reserved Instance coverage and Savings Plans ensure long-term discounts for predictable workloads. This approach can achieve significant cost reduction (e.g., ~43%) while maintaining the same performance SLAs.
