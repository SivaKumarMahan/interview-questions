# Azure Cost Optimization

**Question:** How have you reduced cloud cost in Azure? Give a few examples.

For an Azure DevOps interview, give practical cost-saving examples and explain **what you changed, why, and how you measured it**.

## 1. Right-size VMs

> "I reviewed VM CPU and memory utilization using Azure Monitor. If a VM was consistently underutilized, for example using only 10-20% CPU, I recommended moving it to a smaller SKU."

Example:

```text
Before:
D4s_v5 -> 4 vCPU / 16 GB

After:
D2s_v5 -> 2 vCPU / 8 GB
```

I would validate the workload before downsizing and monitor it after the change.

**Cost saving:** lower compute cost without affecting application performance.

## 2. Stop non-production resources after working hours

For Dev/Test environments, resources don't need to run 24/7.

```text
Dev VM
 |
Stop at 8 PM
 |
Start at 8 AM
```

I can automate this with Azure Automation, Logic Apps, Functions, or scheduled Azure DevOps jobs.

```bash
az vm deallocate \
  --resource-group dev-rg \
  --name dev-vm
```

**Important:** `deallocate` is different from simply shutting down the OS, because deallocation releases the VM compute allocation.

**Cost saving:** avoid paying for compute during unused hours.

### Follow-up: how do you implement VM auto-shutdown?

**Interviewer:** How do you set up auto-shutdown for a VM?

**Candidate:** For one Dev VM, I use the built-in **Auto-shutdown** setting. For many VMs, I use a tag-based schedule.

**Option 1 - one VM:** Portal -> VM -> Operations -> Auto-shutdown -> set time, time zone and an optional email notification. Or with the CLI:

```bash
# Time is HHMM in UTC (1430 UTC = 8 PM IST)
az vm auto-shutdown \
  --resource-group dev-rg \
  --name dev-vm \
  --time 1430 \
  --email "devops-team@company.com"
```

Auto-shutdown only stops the VM. It does not start it again in the morning.

**Option 2 - many VMs:** tag the VMs and run a schedule.

```text
Tags: Environment=Dev, AutoShutdown=Yes
        |
Azure Automation runbook / Logic App / Start/Stop VMs v2
        |
8 PM -> deallocate tagged VMs
8 AM -> start tagged VMs
```

A small runbook that uses the Automation account's managed identity:

```powershell
Connect-AzAccount -Identity

Get-AzVM -Status |
  Where-Object { $_.Tags['AutoShutdown'] -eq 'Yes' -and $_.PowerState -eq 'VM running' } |
  ForEach-Object { Stop-AzVM -ResourceGroupName $_.ResourceGroupName -Name $_.Name -Force -NoWait }
```

**Stop vs deallocate:**

| Action | Compute billed? |
| --- | --- |
| Shutdown from inside the OS, or `az vm stop` | Yes - the VM is still allocated |
| `az vm deallocate`, `Stop-AzVM`, portal **Stop**, Auto-shutdown | No |

Remember:

- Disks and static public IPs are still billed when the VM is deallocated.
- I do not schedule shutdown for Production unless the business asks for it.
- Microsoft's ready-made option is **Start/Stop VMs v2** (the older v1 solution is retired).

## 3. AKS node optimization

I would monitor:

- CPU utilization
- Memory utilization
- Pod density
- Node utilization
- Cluster autoscaler behaviour

If nodes are consistently underutilized, I can reduce the node count or use a smaller VM SKU.

```text
Before:
5 x D4s_v5 nodes

After:
3 x D4s_v5 nodes
```

I can also use the Cluster Autoscaler so AKS adds and removes nodes based on pending workload.

```text
Low workload
     |
Fewer nodes

High workload
     |
More nodes
```

Other AKS savings:

- **Spot node pools** for work that can be interrupted, such as batch jobs or test runs. Spot nodes can be evicted at any time, so I never put critical system pods or stateful workloads on them.
- **Stop the whole Dev cluster** at night with `az aks stop` / `az aks start`.
- Set correct **resource requests** on pods. Requests that are too high waste node capacity, because the scheduler reserves what is requested, not what is used.

## 4. Use Azure Reservations / Savings Plan

For workloads that are predictable and continuously running, such as production VMs, I would evaluate:

- Azure Reservations
- Azure Savings Plan for Compute

instead of paying the full pay-as-you-go rate for stable workloads.

```text
Production VM
Runs 24 x 7
        |
Analyze historical usage
        |
Commit appropriate capacity
        |
Lower compute cost
```

I wouldn't use a long-term commitment for highly variable or temporary workloads.

## 5. Remove unused resources

This is one of the easiest cost optimizations.

I regularly look for unused:

- Managed disks
- Snapshots
- Public IPs
- Load balancers
- Old VM resources
- Unused NICs
- Old container images
- Unused App Service plans
- Old backups

For example, a VM may be deleted but its managed disk remains.

```text
VM deleted
   |
Disk still exists
   |
Still generating cost
```

I can use Azure Resource Graph or Azure CLI to identify orphaned resources and clean them up after validation.

## 6. Storage lifecycle management

For storage accounts, I can move old data to cheaper tiers.

```text
Hot
 |
Cool
 |
Archive
```

For logs or backups that are rarely accessed:

```text
Recent logs -> Hot
Older logs  -> Cool
Old backups -> Archive
```

I would configure lifecycle management rules rather than manually moving files.

## 7. Optimize Azure DevOps build agents

If we're using self-hosted agents, I can clean up:

- Old Docker images
- Containers
- Build artifacts
- Temporary files
- Workspace files

For Microsoft-hosted agents, I avoid unnecessary work by improving pipeline efficiency:

- Dependency caching
- Parallel jobs
- Incremental builds
- Docker layer caching

This doesn't just reduce Azure infrastructure cost - it reduces pipeline execution time and compute consumption.

## 8. Container image optimization

For Docker workloads, I use:

- Multi-stage builds
- Smaller base images
- `.dockerignore`
- Layer caching

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

Instead of putting Node.js, npm, source code and build dependencies into the production image, the final image only contains Nginx and the built application.

This reduces:

- ACR storage
- Image transfer time
- AKS pull time
- Container storage usage

## 9. Log retention optimization

Logs can become surprisingly expensive.

I review:

```text
Log Analytics
     |
Retention
     |
Ingestion volume
     |
Cost
```

I avoid sending unnecessary verbose/debug logs to Log Analytics in production.

```text
DEBUG -> Don't collect in production unless required
INFO  -> Keep where useful
ERROR -> Always retain
```

I also configure appropriate retention and archive older data where required.

## 10. Resource tagging and cost analysis

I use consistent tags:

```text
Environment = Production
Application = Payments
Owner       = DevOps
CostCenter  = 1234
```

Then Azure Cost Management can help identify which application, team or environment is consuming money.

```text
Application A -> ₹80,000/month
Application B -> ₹25,000/month
Unused Dev    -> ₹15,000/month
```

Then I investigate the biggest unexpected spend first.

## 11. App Service plan right-sizing and autoscale

**Interviewer:** Which App Service plan do you use, and how does it affect cost?

**Candidate:** The **App Service plan** is the compute that the Web App runs on. I pay for the plan instances, not for each app. So the plan tier and the instance count drive the cost.

| Tier | Where I use it |
| --- | --- |
| Free / Shared | Learning only |
| Basic (B1-B3) | Dev and QA - dedicated compute, manual scale only |
| Standard (S1-S3) | Smaller production apps - autoscale and deployment slots |
| Premium v3 (P0v3, P1v3...) | Most production apps - more slots, better VNet integration, faster scaling |
| Isolated v2 (App Service Environment) | Apps that need full network isolation |

How I keep it cheap:

```text
Dev / QA   -> Basic plan, 1 instance
Production -> Premium v3, autoscale min 2 / max 4
```

Example autoscale rule on the plan:

```text
CPU > 70% for 10 min -> add 1 instance (max 4)
CPU < 35% for 15 min -> remove 1 instance (min 2)
```

Remember:

- **Scale out** = more instances (autoscale). **Scale up** = bigger tier or size.
- Several small apps can share one plan to save money, but they share the same CPU and memory. A noisy app can slow the others.
- Delete empty plans. An App Service plan with no apps is still billed.
- Use different scale-out and scale-in thresholds so the plan does not keep flapping.

## 12. Budgets, alerts and Azure Advisor

Saving money once is not enough. I also put guardrails in place so cost does not creep back up.

```text
Azure Advisor        -> cost recommendations (idle VMs, right-size, reservations)
Budgets              -> monthly limit per subscription or resource group
Cost alerts          -> email / Action Group at 50%, 80%, 100% of budget
Anomaly alerts       -> Cost Management flags an unusual daily spike
Azure Policy         -> deny expensive VM SKUs in Dev, require cost tags
```

Example Azure Policy idea for Dev subscriptions:

```text
Allowed VM SKUs  -> B-series and D2s/D4s only
Required tags    -> Environment, Owner, CostCenter
```

## 13. Scenario: the Azure bill suddenly went up

**Interviewer:** You notice the Azure cost has increased a lot. What will you do?

**Candidate:** I follow **detect -> fix -> root cause -> prevent**.

```text
Cost Management -> Cost analysis
        |
Group by subscription -> resource group -> resource / meter
        |
Compare with last week / last month
        |
Find the cause:
  new resources, bigger SKUs, unexpected scale-out,
  storage growth, data transfer, Log Analytics ingestion,
  something left running after a test
        |
Activity Log -> who created or changed it, and when
        |
Fix: stop / resize / delete (after checking with the owner)
        |
Prevent: budgets + alerts, Azure Policy, tags, RBAC, scheduled shutdown
```

> "I would not just delete the expensive resource. I would confirm with the owner, find out from the Activity Log how it was created, and then add a budget alert, a policy and the right RBAC so the same thing cannot happen again."

## Strong interview answer

If they ask *"How have you reduced Azure cloud costs?"*, say:

> "I have approached cost optimization mainly through resource utilization and automation. First, I used Azure Monitor metrics to identify underutilized VMs and right-size them. For non-production environments, I automated VM shutdown and startup during non-working hours. For AKS, I monitored node and pod utilization and used appropriate node sizing and cluster autoscaling to avoid running unnecessary nodes.
>
> I also used Spot node pools for interruptible jobs, and kept Dev App Service plans on lower tiers with autoscale only in production. I cleaned up orphaned resources such as unattached managed disks, unused public IPs, snapshots and old container images. For storage, I used lifecycle policies to move older data from Hot to Cool or Archive tiers. For stable production workloads, I would evaluate Azure Reservations or Savings Plans based on historical usage.
>
> On the DevOps side, I optimized Docker images using multi-stage builds and cleaned up self-hosted agent resources. I also reviewed Log Analytics ingestion and retention so we weren't unnecessarily storing verbose logs. Finally, I used resource tagging and Azure Cost Management to identify which applications and environments were actually driving the cost, and I set budgets and cost alerts so we found any new spike early."

## If they ask "How did you prove the saving?"

Don't say *"I think it reduced the cost."*

Say:

> "I compared the Azure Cost Management data before and after the change, while controlling for workload changes. For example, after right-sizing or shutting down non-production resources, I compared the monthly compute cost and validated that application performance and availability remained within the required limits."

That's a much stronger DevOps interview answer.

## Related

A working PowerShell script for point 5 (finding unattached managed disks and exporting them to CSV for owner review) is in [automation-shell-and-python-examples.md](automation-shell-and-python-examples.md#azure-cost-optimization---find-unattached-managed-disks).
