# Azure: Automation, Monitoring, and Cost

> Repeatable delivery with Terraform, monitoring Azure resources, and controlling cost.

## Key Concepts

### Azure three-tier blueprint and automation

A typical Azure three-tier design uses Front Door for global entry, Application Gateway or WAF for regional routing, and App Service, VM Scale Sets, containers, or AKS for the presentation tier.

The application tier runs on its own separately secured service or compute boundary, and can use an internal load balancer, Service Bus, and Redis to decouple work and cut down latency.

Azure SQL, Cosmos DB, or Storage services make up the data tier, reached through private connectivity, managed identity, encryption, backup, and tested recovery.

Terraform modules, the Azure CLI where it fits, Git-based review, and CI/CD keep Dev, Test, and Production repeatable. Environment separation also needs to cover state, identity, approval, policy, and network boundaries — not just separate variable files.

### Monitoring and Operations

Use monitoring at both the component and workflow level:

- **Azure Monitor:** common platform for metrics, logs, alerts, and dashboards.
- **Log Analytics workspace:** query and analyze collected logs with KQL.
- **Application Insights:** application performance monitoring, requests, dependencies, exceptions, traces, and distributed transaction views.
- **Network Watcher:** network topology, diagnostics, connection monitoring, packet capture, and flow-related analysis.
- **Service-specific monitoring:** Data Factory pipeline runs, Function executions, Storage metrics, and Front Door health/caching metrics.

Operationally mature systems should include structured logs, correlation IDs, useful alerts, retry visibility, dashboards, runbooks, and tested incident procedures.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you manage infrastructure with Terraform in Azure?</summary>

**Answer:**

I use the `azurerm` provider, reusable modules, separate state files for separate boundaries, and an Azure Storage backend. CI authenticates using workload identity federation rather than a stored client secret.

```hcl
terraform {
  backend "azurerm" {}
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

provider "azurerm" { features {} }
```

The flow goes `fmt` → `validate` → lint, security, and policy checks → plan → peer review → production approval → apply the saved plan → smoke tests. State storage uses encryption, versioning, lease-based locking, private access where required, and access scoped to only what's needed.

When something fails, I check the Terraform state, the provider's error, the Azure Activity Log, policy, quota, IAM, and networking. I never just rerun it blindly, and I never edit state without a backup and a plan to bring things back in sync.

</details>

<details><summary>Q2. [Intermediate] How do you monitor Azure resources?</summary>

**Answer:**

I use Azure Monitor as the common platform: metrics for numeric time series, diagnostic settings for platform and resource logs, Log Analytics with KQL for querying, Application Insights for application and dependency traces, alerts with action groups, and workbooks or dashboards on top.

I define what to watch based on what actually matters: availability, latency, errors, traffic, how close resources are to their limits, queue depth, failed dependencies, and capacity. Every alert needs to be actionable, routed to an owner, and tied to a runbook.

During an incident, I pin down the time and scope, compare recent deployments and Activity Log changes, trace the problem from the user's symptom down through the application to its dependencies to the infrastructure, and confirm the fix with the original query or transaction. I also tune out noisy alerts and actually test that notifications get routed correctly, rather than just assuming the configuration works.

</details>

<details><summary>Q3. [Intermediate] How do you monitor Azure services?</summary>

**Answer:**

I turn on platform metrics, diagnostic settings pointed at Log Analytics, Event Hub, or Storage as needed, Application Insights or OpenTelemetry for application traces, alerts with action groups, workbooks, and whatever health signals the service itself provides.

Monitoring is driven by what actually matters to the business: availability, latency, errors, traffic, how close resources are to their limits, dependency failures, queue age, capacity, and security-relevant changes. Every alert has an owner, a runbook, and gets tested.

When investigating an issue, I pin down the time window and scope, compare the Activity Log and recent deployments against the metrics, follow a request through its dependencies using a correlation or trace ID, fix the immediate problem, then confirm the original user-facing transaction actually works again.

Retention, access control, sampling, how many unique label combinations get tracked, and ingestion cost all get designed deliberately — not left at whatever the defaults happen to be.

</details>

<details><summary>Q4. [Intermediate] How do you control Azure costs?</summary>

**Answer:**

I combine four things: allocation, prevention, optimization, and review.

- Clear ownership at the management-group, subscription, and resource-group level, with required tags
- Budgets, forecasts, anomaly alerts, and cost exports
- Right-sizing based on actual utilization and Advisor recommendations
- Autoscaling and schedules for non-production environments
- Reservations or savings plans for compute that's genuinely predictable, once you've measured it
- Spot capacity for workloads that can tolerate interruption
- Storage tiering, lifecycle policies, and cleaning up unattached resources
- Reviewing network egress and managed-service tiers at the architecture level

If costs spike, I compare spend by service, resource, tag, and day, check it against recent deployments and usage, safely stop anything that's clearly waste, and loop in the resource owner. I always check that savings don't come at the cost of reliability or performance — deleting something that looks idle without confirming ownership and a recovery plan is risky.

</details>
