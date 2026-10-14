# Ops: FinOps

> Reducing cloud cost without hurting reliability, investigating bill spikes, and building cost awareness into Terraform, CI/CD and observability retention.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you optimize infrastructure cost without impacting performance or reliability?</summary>

**Answer:**

I start by getting the evidence right: I break down cost by account, service, environment, owner, region, tag, SKU, and a real unit like cost per request or per customer. Then I compare that billing data against utilization, latency, errors, capacity forecasts, and SLOs.

That comparison is what tells waste apart from legitimate growth, so I'm not just cutting an arbitrary percentage across the board.

From there, typical actions include deleting confirmed orphaned non-production resources, scheduling resources to shut off when idle, right-sizing based on real usage percentiles and load tests, autoscaling with a safe minimum, storage lifecycle and tiering, controlling log retention and how many unique label combinations get tracked, more efficient data transfer, the right managed-service tier, and reserved or savings commitments for stable baseline load.

Spot capacity only goes to workloads that can tolerate being interrupted.

Often, improving the architecture or the application's own efficiency saves more than just shrinking instance sizes.

Every change has clear performance and rollback criteria, and I canary it where I can. Budgets, anomaly alerts, ownership tags, cost estimates during IaC review, quotas, showback reporting, and regular reviews keep the optimization work going instead of it being a one-time push.

After every change, I check that cost per unit actually improved and that SLOs are still being met.

</details>

<details><summary>Q2. [Intermediate] How would you identify and reduce cloud infrastructure costs without sacrificing performance or reliability? <em>(scenario)</em></summary>

**Answer:** Use tagging and Cost Explorer to find spending patterns, right-size EC2 from CloudWatch data plus autoscaling, use the Cluster Autoscaler and HPA on EKS, use spot instances for non-critical workloads, apply S3 lifecycle rules and DynamoDB autoscaling, and schedule off-hours scaling alongside Reserved Instances or Savings Plans.

**Detailed interview approach:**
I start with thorough tagging and AWS Cost Explorer to see spending patterns by team, application, and environment.

For EC2, I look at CloudWatch metrics to find oversized instances and set up autoscaling with instance types that actually match the workload.

For EKS clusters, I use the Kubernetes Cluster Autoscaler to adjust node counts based on pod demand, and the Horizontal Pod Autoscaler to scale deployments based on CPU and memory use. I use spot instances for non-critical workloads, spreading across instance types to avoid disruption.

For storage, I use S3 lifecycle policies to move infrequently accessed data to cheaper tiers, and set up DynamoDB autoscaling to match actual throughput.

Scheduled scaling through Terraform reduces resources during off-hours in non-production environments, and I regularly review Reserved Instance coverage and Savings Plans to keep discounts working for predictable workloads.

This approach has cut costs by around 43% in practice while keeping the same performance targets.

</details>

<details><summary>Q3. [Advanced] Your cloud bill increases by 40% overnight. How do you investigate it?</summary>

**Answer:**

I compare the affected day or hour against the normal baseline, broken down by service, account, region, SKU, usage type, tag, and resource ID.

I check for recent deployments, autoscaling events, new resources, a pricing or commitment change, data egress, NAT traffic, log or metrics ingestion, snapshots, database I/O, serverless invocations, and marketplace charges.

A sudden jump in compute or API usage is also a signal to check for leaked credentials or crypto-mining.

I only shut down what I've confirmed is waste or a compromise: disable a leaked identity, cap runaway autoscaling or logging, stop non-production resources I own, or block a job that's clearly misbehaving. I never terminate an unfamiliar stateful production resource just because a cost dashboard flagged it.

Cloud audit logs and the owner/tag metadata tell me who created or last changed the resource.

Once it's fixed, I confirm application SLOs are healthy and billing has actually come back down. Then I add budget and anomaly alerts, require ownership tags, set quotas and scaling limits, tighten log retention policy, and add cost review to IaC changes.

Finally, I write down whether the spike was waste, an attack, expected traffic growth, or just a tagging/allocation error.

</details>

<details><summary>Q4. [Intermediate] How do you implement infrastructure cost optimization in Terraform? <em>(scenario)</em></summary>

**Answer:** Use variables for instance sizes, add auto-scaling groups, apply resource tags, and use lifecycle policies to clean up unused resources.

**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

</details>

<details><summary>Q5. [Intermediate] How do you set up cost-aware CI/CD pipelines to prevent runaway spend? <em>(scenario)</em></summary>

**Answer:** Add cost estimation to the pipeline so it estimates the infra cost of each change, set budget checks and alerts, use autoscaling and spot instances where they fit, and block a merge if the estimated cost goes over a threshold.

Mini-case: a pipeline flagged that a proposed infra change would triple the monthly cost. That required manager approval before it could go through, which prevented an accidental large spend.
**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

</details>

<details><summary>Q6. [Intermediate] How do you integrate cost monitoring into DevOps pipelines? <em>(scenario)</em></summary>

**Answer:** Pull data from the GCP Billing API or Azure Cost Management, add cost checks into the pipeline, and alert when the estimated cost goes over budget.

**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

</details>

<details><summary>Q7. [Advanced] How do you scale observability storage and retention cost-effectively? <em>(scenario)</em></summary>

**Answer:** Aggregate and downsample older metrics (Prometheus remote write to Thanos/Cortex), use tiered log retention (hot/warm/cold), and set retention policies that match compliance requirements.

Mini-case: we moved 30-day detailed metrics to Thanos with 90-day downsampled retention. That cut monitoring costs by 60% while keeping the accuracy we needed for alerts.
**Detailed interview approach:**
I compare cost by service, account, region, tag, SKU, and usage metric against the normal baseline and any recent deployments. I check whether the rise is from real traffic growth, runaway autoscaling, orphaned resources, log or egress volume, a pricing/commitment change, or compromised compute.

I only contain what I've confirmed: budgets, scaling caps, quotas, or stopping non-production waste I own — I don't delete stateful production resources without being sure. Terraform plans get cost estimates, and changes above a threshold need policy approval.

Required tags, anomaly alerts, right-sizing, schedules, lifecycle retention, reserved vs. spot choices, and owner-level cost visibility keep the optimization ongoing. I always check performance and SLOs after making a cost change.

</details>

<details><summary>Q8. [Intermediate] A client says the cloud cost has increased. How do you optimise it? <em>(asked in interview round)</em></summary>

**Answer:**

First I find **what** increased and **why**, using cost analysis grouped by service, resource, tag and region. Then I apply quick wins (delete waste), right-size, use commitment discounts, and add governance (budgets, tags, policies) so it does not happen again.

**Steps:**

1. **Analyse:** Azure Cost Management / AWS Cost Explorer; compare this month with last month, group by service, resource group, tag and region.
2. **Find the spike:** a new resource, scale-out, data transfer/egress, log ingestion, storage growth, or a pricing change.
3. **Remove waste:** unattached disks, old snapshots, idle public IPs, unused load balancers, stopped-but-allocated VMs, forgotten test environments.
4. **Right-size:** use Azure Advisor / AWS Compute Optimizer recommendations based on CPU and memory usage.
5. **Schedule non-production:** shut down dev/test VMs and clusters at night and on weekends.
6. **Commitment discounts:** Reservations and Savings Plans for steady workloads; Spot VMs for interruptible workloads.
7. **Storage tiering:** lifecycle policies to move data to cool/archive tiers.
8. **Reduce logging and egress costs:** lower retention, filter noisy logs, use private endpoints/CDN where it helps.
9. **Govern:** mandatory tags, budgets with alerts, anomaly alerts, policies limiting expensive SKUs, monthly cost reviews.

**Flow:**

```text
Cost spike reported
      |
      v
Cost analysis (by service / tag / region, month-over-month)
      |
      v
Root cause (new resource? scale-out? egress? logs?)
      |
      v
Quick wins: delete idle resources -> right-size -> schedule non-prod
      |
      v
Commitments (Reservations / Savings Plans) + storage tiers
      |
      v
Governance: tags, budgets, anomaly alerts, policy, monthly review
```

**Example commands:**

```bash
# Azure: unattached managed disks
az disk list --query "[?diskState=='Unattached'].{name:name, rg:resourceGroup, sizeGb:diskSizeGb}" -o table

# Azure: VMs that are stopped but still allocated (still billed for compute)
az vm list -d --query "[?powerState=='VM stopped'].{name:name, rg:resourceGroup}" -o table

# AWS: unattached EBS volumes
aws ec2 describe-volumes --filters Name=status,Values=available \
  --query "Volumes[].{id:VolumeId,size:Size}" --output table
```

**Important points:**

- In Azure, "Stopped" from inside the OS still bills compute; use "Stop (deallocate)".
- Do not buy reservations before right-sizing, or you commit to the wrong size.
- Tagging (owner, environment, cost centre) is what makes cost analysis possible.
- Optimisation is continuous (FinOps), not a one-time clean-up.

See also: [Azure cost optimization](../repetitive-questions/azure-cost-optimization.md), [FinOps](../ops/04-finops.md).

**Interview-ready answer:**

> "First I find out exactly what increased by using Cost Management or Cost Explorer, comparing month over month and grouping by service, resource group, tag and region. Once I know the cause, I remove waste like unattached disks, old snapshots, idle public IPs and forgotten test resources. Then I right-size VMs using Advisor recommendations and schedule non-production environments to shut down outside working hours. For steady workloads I use Reservations or Savings Plans, and Spot instances for interruptible jobs, and I move old data to cheaper storage tiers. Finally I add governance with mandatory tags, budgets and anomaly alerts, so the client sees any new spike early."

</details>

<details><summary>Q9. [Basic] Which AWS tool compares this month's billing with last month's? <em>(asked in interview round)</em></summary>

**Answer:**

The main tool is **AWS Cost Explorer**, part of **AWS Billing and Cost Management**.

**Tools and when to use them:**

| Tool | Use |
| --- | --- |
| **Cost Explorer** | Monthly granularity, last 2 months, group by Service / Account / Usage type / Tag; up to 12+ months of history and forecasts |
| **Cost Explorer cost comparison** | Select two months and see the total change and the top cost drivers (by service, account, Region, usage type) |
| **Bills page** (Billing and Cost Management) | Invoice-level charges per service and Region for a month; switch months to compare |
| **AWS Budgets** | Alert when actual or forecasted spend exceeds a threshold |
| **Cost Anomaly Detection** | ML-based alerts for unusual spend, with root cause (service, account, usage type) |
| **CUR 2.0 via Data Exports + Athena / QuickSight** | Line-item detail for deep analysis and custom month-over-month reports |
| **Cost Optimization Hub / Compute Optimizer / Trusted Advisor** | Recommendations to reduce the cost once you know the driver |

**Example: month-over-month by service from the CLI:**

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-10-01 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "ResultsByTime[].{month:TimePeriod.Start, services:Groups[].[Keys[0], Metrics.UnblendedCost.Amount]}"
```

The `End` date is exclusive, so this returns August and September.

**Example: Athena query on CUR data:**

```sql
SELECT line_item_product_code,
       date_format(line_item_usage_start_date, '%Y-%m') AS month,
       round(sum(line_item_unblended_cost), 2)          AS cost
FROM   cur_db.cur_table
WHERE  line_item_usage_start_date >= date '2026-08-01'
  AND  line_item_usage_start_date <  date '2026-10-01'
GROUP  BY 1, 2
ORDER  BY 1, 2;
```

**Important points:**

- Compare with the same cost metric (`UnblendedCost`, `AmortizedCost` or `NetAmortizedCost`); amortized is better when Savings Plans or RIs are involved.
- Activate cost allocation tags so you can compare by team or application.
- Cost Explorer data is not real time; it usually updates at least once every 24 hours.

See also: [Monitoring cost and FinOps](../monitoring-tools/10-monitoring-cost-finops.md).

**Interview-ready answer:**

> "I use AWS Cost Explorer in the Billing and Cost Management console. I set monthly granularity for the last two months and group by service, then drill into linked account, Region and usage type, and the cost comparison view shows the top drivers between the two months directly. For invoice-level detail I check the Bills page. For automated tracking I use AWS Budgets and Cost Anomaly Detection, and for detailed analysis I export CUR 2.0 data through Data Exports and query it with Athena. I make sure to compare amortized cost when Savings Plans or Reserved Instances are involved."

</details>

<details><summary>Q10. [Intermediate] This month's bill is 40% higher. How do you analyze it? <em>(asked in interview round)</em></summary>

**Answer:**

I approach it like an incident: **find which dimension changed, find the resource, find the cause, fix it, and stop it from happening again.** First I separate *real* usage growth from waste or a billing effect (for example, a Savings Plan expiring).

**Steps:**

1. **Confirm the change**: compare the same period (month-to-date vs the same days last month, not a full month vs a partial month) with the same cost metric (amortized).
2. **Top-down drill-down in Cost Explorer**: group by **Service** → **Linked account** → **Region** → **Usage type** → **Resource** (resource-level daily data for EC2 if enabled) or **Tag** (team, application).
3. **Use daily granularity** to find the date the cost jumped, then correlate with deployments, Terraform changes or CloudTrail events around that date.
4. **Check Cost Anomaly Detection** findings, which often name the account, service and usage type directly.
5. **Check commitment coverage**: Savings Plans / RI utilization and coverage reports; an expired commitment turns the same usage into On-Demand prices.
6. **Look at common culprits**:
   - New or oversized EC2/RDS/EKS nodes, autoscaling max raised, forgotten test environments.
   - Data transfer: NAT Gateway processing, cross-AZ traffic, internet egress.
   - Storage growth: S3 without lifecycle, EBS snapshots, unattached EBS volumes, idle load balancers, unused Elastic IPs (public IPv4 addresses are charged hourly).
   - Logging/monitoring: CloudWatch Logs ingestion from debug logging, high-cardinality custom metrics.
   - New services enabled (GuardDuty, Macie, Config recording in all Regions).
7. **Fix and verify**: right-size, delete idle resources, add lifecycle policies, VPC endpoints, buy or renew Savings Plans; check the daily trend returns to normal.
8. **Prevent**: budgets per account/team, anomaly alerts to the owning team, mandatory cost allocation tags, cost review in change management.

```text
Bill +40%
  -> Cost Explorer (amortized, daily): which service? which day?
      -> account / Region / usage type / tag
          -> resource + CloudTrail (who created/changed it, when)
              -> root cause: usage growth | waste | pricing change
                  -> fix -> verify daily trend -> budgets + anomaly alerts
```

**Example: daily cost by usage type for one service:**

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-10-01 \
  --granularity DAILY --metrics AmortizedCost \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Compute Cloud - Compute"]}}' \
  --group-by Type=DIMENSION,Key=USAGE_TYPE

# Who launched instances around the jump date
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RunInstances \
  --start-time 2026-09-14 --end-time 2026-09-16 \
  --query "Events[].[EventTime,Username]" --output text
```

**Important points:**

- Not every increase is bad: if traffic or customers grew 40%, compare cost per unit (per request, per customer).
- Data transfer and NAT charges are often missed because they appear under EC2 "Other" usage types.
- Communicate findings with numbers: "X increased by $Y because of Z, fixed on date D, expected saving $S per month".

See also: [Monitoring cost and FinOps](../monitoring-tools/10-monitoring-cost-finops.md).

**Interview-ready answer:**

> "I first confirm the increase with a like-for-like comparison using amortized cost, then drill down in Cost Explorer by service, account, Region, usage type and tags to find exactly which line grew. I switch to daily granularity to find the day it jumped and correlate that date with deployments, Terraform changes and CloudTrail events. I check Cost Anomaly Detection and Savings Plans coverage, because an expired commitment can raise the bill without any usage change. Typical causes are oversized or forgotten resources, NAT and cross-AZ data transfer, unmanaged S3 or log growth, and newly enabled services. After fixing it I verify the daily trend drops, and I add budgets, anomaly alerts and mandatory cost tags so the owning team gets alerted next time."

</details>
