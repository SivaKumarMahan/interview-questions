# Azure Cost Optimization

**Question:** How have you reduced cloud cost in Azure? Give a few examples.

For an Azure DevOps interview, give practical cost-saving examples and explain **what you changed, why, and how you measured it**.

## 1. Right-size VMs

> "I reviewed VM CPU and memory utilization using Azure Monitor. If a VM was consistently underutilized, for example using only 10-20% CPU, I recommended moving it to a smaller SKU."

Example:

```
Before:
D4s_v5 -> 4 vCPU / 16 GB

After:
D2s_v5 -> 2 vCPU / 8 GB
```

I would validate the workload before downsizing and monitor it after the change.

**Cost saving:** lower compute cost without affecting application performance.

## 2. Stop non-production resources after working hours

For Dev/Test environments, resources don't need to run 24/7.

```
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

## 3. AKS node optimization

I would monitor:

- CPU utilization
- Memory utilization
- Pod density
- Node utilization
- Cluster autoscaler behaviour

If nodes are consistently underutilized, I can reduce the node count or use a smaller VM SKU.

```
Before:
5 x D4s_v5 nodes

After:
3 x D4s_v5 nodes
```

I can also use the Cluster Autoscaler so AKS adds and removes nodes based on pending workload.

```
Low workload
     |
Fewer nodes

High workload
     |
More nodes
```

## 4. Use Azure Reservations / Savings Plan

For workloads that are predictable and continuously running, such as production VMs, I would evaluate:

- Azure Reservations
- Azure Savings Plan for Compute

instead of paying the full pay-as-you-go rate for stable workloads.

```
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

```
VM deleted
   |
Disk still exists
   |
Still generating cost
```

I can use Azure Resource Graph or Azure CLI to identify orphaned resources and clean them up after validation.

## 6. Storage lifecycle management

For storage accounts, I can move old data to cheaper tiers.

```
Hot
 |
Cool
 |
Archive
```

For logs or backups that are rarely accessed:

```
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

```
Log Analytics
     |
Retention
     |
Ingestion volume
     |
Cost
```

I avoid sending unnecessary verbose/debug logs to Log Analytics in production.

```
DEBUG -> Don't collect in production unless required
INFO  -> Keep where useful
ERROR -> Always retain
```

I also configure appropriate retention and archive older data where required.

## 10. Resource tagging and cost analysis

I use consistent tags:

```
Environment = Production
Application = Payments
Owner       = DevOps
CostCenter  = 1234
```

Then Azure Cost Management can help identify which application, team or environment is consuming money.

```
Application A -> ₹80,000/month
Application B -> ₹25,000/month
Unused Dev    -> ₹15,000/month
```

Then I investigate the biggest unexpected spend first.

## Strong interview answer

If they ask *"How have you reduced Azure cloud costs?"*, say:

> "I have approached cost optimization mainly through resource utilization and automation. First, I used Azure Monitor metrics to identify underutilized VMs and right-size them. For non-production environments, I automated VM shutdown and startup during non-working hours. For AKS, I monitored node and pod utilization and used appropriate node sizing and cluster autoscaling to avoid running unnecessary nodes.
>
> I also cleaned up orphaned resources such as unattached managed disks, unused public IPs, snapshots and old container images. For storage, I used lifecycle policies to move older data from Hot to Cool or Archive tiers. For stable production workloads, I would evaluate Azure Reservations or Savings Plans based on historical usage.
>
> On the DevOps side, I optimized Docker images using multi-stage builds and cleaned up self-hosted agent resources. I also reviewed Log Analytics ingestion and retention so we weren't unnecessarily storing verbose logs. Finally, I used resource tagging and Azure Cost Management to identify which applications and environments were actually driving the cost."

## If they ask "How did you prove the saving?"

Don't say *"I think it reduced the cost."*

Say:

> "I compared the Azure Cost Management data before and after the change, while controlling for workload changes. For example, after right-sizing or shutting down non-production resources, I compared the monthly compute cost and validated that application performance and availability remained within the required limits."

That's a much stronger DevOps interview answer.

## Related

A working PowerShell script for point 5 (finding unattached managed disks and exporting them to CSV for owner review) is in [automation-shell-and-python-examples.md](automation-shell-and-python-examples.md#azure-cost-optimization---find-unattached-managed-disks).
