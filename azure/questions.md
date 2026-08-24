## 1. What is Microsoft Azure?

**Answer:**

Microsoft Azure is a cloud platform that offers compute, networking, storage, databases, identity, integration, security, monitoring, analytics, and DevOps services. It supports public cloud, hybrid, and multi-cloud setups through services like Azure Arc.

A simple application flow looks like this: users hit Azure Front Door, traffic goes to App Service or AKS, the workload uses managed identity to read Key Vault and reach Azure SQL, and monitoring data flows to Azure Monitor and Application Insights.

Azure organizes things using tenants for identity, management groups and subscriptions for governance and billing, resource groups for grouping resources by lifecycle, and regions or availability zones for where things physically run.

In an interview, I try to describe the actual services, the availability target, the security model, day-to-day operations, and cost controls — not just say "Azure hosts applications."

## 2. What is the difference between IaaS, PaaS, and serverless in Azure?

**Answer:**

- **IaaS:** Azure manages the physical hardware and virtualization; I manage the VM's OS, patches, middleware, application, and data. Example: Azure Virtual Machines.
- **PaaS:** Azure also manages the OS and runtime; I focus on the application, its configuration, identity, and data. Examples: App Service and Azure SQL Database.
- **Serverless:** Code or workflows run in response to events and scale based on demand. Examples: Azure Functions and Logic Apps.

I pick IaaS for legacy software or when I need OS-level control, PaaS for managed web and database platforms, and Functions for event-driven tasks.

I weigh compliance, how much runtime control I need, scaling, latency and cold start, how long execution can run, networking, operational effort, and steady-state cost. "Serverless" doesn't mean there are no servers — it just means Azure runs them instead of you.

## 3. How do you manage infrastructure with Terraform in Azure?

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

## 4. How do you deploy applications to Azure Kubernetes Service?

**Answer:**

My delivery flow:

1. Build and test the application.
2. Create a minimal container image, generate an SBOM (a list of everything that went into the image), and scan it.
3. Push a digest — a fixed reference to that exact image — to Azure Container Registry.
4. Deploy to AKS using Helm, plain manifests, or GitOps with Flux or Argo CD.
5. Use workload identity and the Key Vault CSI driver for Azure access and secrets.
6. Set requests and limits, probes, Pod security, NetworkPolicy, horizontal autoscaling, and a PodDisruptionBudget.
7. Wait for the rollout, run smoke tests, and watch for errors and latency.

If a rollout fails, I check `kubectl describe`, the events, current and previous logs, whether the image pulled, configuration, probes, scheduling, and dependencies. If user impact is growing, I roll back the traffic or the release, keep the evidence, fix it in a lower environment, then redeploy a fresh, unchanged version.

## 5. How do you design a secure Azure landing zone?

**Answer:**

A landing zone is the governed foundation that workloads get deployed into. I start by gathering the regulatory, identity, connectivity, availability, ownership, and cost requirements, then design:

- Management-group hierarchy and subscription boundaries
- Entra ID groups, RBAC scoped to only what's needed, Privileged Identity Management, and break-glass access
- Azure Policy initiatives for regions, tags, diagnostics, encryption, and public access
- Hub-spoke or Virtual WAN connectivity, private DNS, Firewall, and DDoS controls
- Central logging or SIEM, Defender for Cloud, budgets, naming conventions, and tagging
- Infrastructure-as-code modules and a subscription-vending process

I test policies in audit mode first, check that allowed and denied deployments actually behave as expected, verify private connectivity and DNS, and document any exceptions. A landing zone has to let teams work safely — policies so strict they block necessary work aren't mature governance, they're just an obstacle.

## 6. How do you use managed identity in Azure?

**Answer:**

Managed identity gives an Azure workload its own Entra ID identity, with no password to store. A system-assigned identity lives and dies with one resource; a user-assigned identity is a separate resource you can reuse elsewhere.

The flow: enable or attach the identity → grant it a narrow RBAC or data role → the application requests a token from Azure's identity endpoint through an SDK credential chain → the target service validates that token.

For example, an App Service gets `Key Vault Secrets User` on one vault, and reads a secret through `DefaultAzureCredential`. I don't grant subscription Contributor just so an app can read one secret.

I test both allowed and denied operations, check sign-in and resource logs, and give role assignments time to propagate. If access fails, I check the principal ID, the token's audience, the role and its scope, network rules and private DNS, and whether the service uses RBAC or the older access-policy model.

## 7. How do you manage secrets in Azure?

**Answer:**

I store secrets, keys, and certificates in Key Vault and access them through managed identity. Applications only get the specific data-plane role they need.

Vaults use soft delete and purge protection, logging, rotation, and private endpoints or firewall controls when necessary.

My preferred setup avoids ever copying a secret into a pipeline variable. The workload fetches it at runtime, or uses a Key Vault reference or the CSI driver.

I track who owns each secret, who consumes it, when it expires, and how it gets rotated. I test rotation so applications pick up the new value without an outage.

If access fails, I check whether it's a management-plane or data-plane issue, the RBAC or access-policy mode, the scope, the identity, the secret's version and status, network restrictions, and the logs. If a secret is ever exposed, I rotate or revoke it first, investigate who accessed it, and only then clean up the leaked value from code, logs, and artifacts.

## 8. How do you monitor Azure resources?

**Answer:**

I use Azure Monitor as the common platform: metrics for numeric time series, diagnostic settings for platform and resource logs, Log Analytics with KQL for querying, Application Insights for application and dependency traces, alerts with action groups, and workbooks or dashboards on top.

I define what to watch based on what actually matters: availability, latency, errors, traffic, how close resources are to their limits, queue depth, failed dependencies, and capacity. Every alert needs to be actionable, routed to an owner, and tied to a runbook.

During an incident, I pin down the time and scope, compare recent deployments and Activity Log changes, trace the problem from the user's symptom down through the application to its dependencies to the infrastructure, and confirm the fix with the original query or transaction. I also tune out noisy alerts and actually test that notifications get routed correctly, rather than just assuming the configuration works.

## 9. How do you control Azure costs?

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

## 10. How do you enforce governance in Azure?

**Answer:**

I use management groups for hierarchy, subscriptions as boundaries, Entra groups with RBAC and Privileged Identity Management for access, Azure Policy for audit, deny, or deploy rules, resource locks to prevent accidental deletion of critical resources, and infrastructure-as-code or pipeline controls to standardize how things get deployed.

Policies cover things like allowed regions or SKUs, mandatory tags, diagnostic settings, encryption, private connectivity, and security configuration. I roll them out as audit-only first, understand what's already non-compliant, fix it, and only then switch selected rules to deny.

Exceptions always need a business justification, an owner, a scope, and an expiry date.

I watch compliance trends, failed deployments, how many people hold privileged roles, and how policies are actually behaving. Governance is working when it produces consistent evidence and lets people self-serve safely — not when its only effect is adding another manual approval.

## 11. How do you approach Azure disaster recovery?

**Answer:**

I start with a business impact analysis and define the recovery time objective, recovery point objective, how much data loss is tolerable, what a regional failure would mean, dependencies, and who owns the recovery decision.

Then I pick patterns per component: zones for a datacenter failure, multi-region capacity for the application, database replication, geo-redundant storage where it fits, Azure Backup, Site Recovery for supported VM workloads, and Front Door, Traffic Manager, or DNS-based failover.

A runbook needs to cover detection, who has authority to decide, data consistency, the order of failover, whether secrets and DNS are actually available during the failover, smoke tests, communication, and failing back afterward. Backups are kept isolated and protected from deletion.

I run actual restore tests and regional exercises, measure the real recovery time and recovery point achieved, and fix whatever gaps show up. Replication is not a backup — corruption or deletion can replicate right along with the good data. I also test failing back, because recovery isn't finished until normal operations are safely restored.

## 12. How do you resize an Azure VM, and does it require a reboot?

**Answer:**

In the portal, select the VM, open **Size** under Availability + scale, pick a compatible size, and apply it — the same thing can be done through the CLI or infrastructure-as-code. A resize normally restarts the VM.

If the size you want isn't available on the current hardware cluster, Azure may need to stop and deallocate the VM first, which releases any dynamic public IP unless it's set up as static.

Before resizing, I check the application's maintenance windows, disk and network compatibility, availability-set or zone constraints, capacity, cost, backups, and how to roll back if needed.

## 13. Can an NSG be attached directly to a virtual network?

**Answer:**

No. A network security group attaches to a subnet or a network interface — not directly to the virtual network.

The effective rules are the combination of whatever's applied at the subnet and the NIC, evaluated by Azure's priority order. I check the effective security rules and use Network Watcher to confirm the real path traffic takes, rather than assuming a broad default allow rule is fine.

## 14. Can VMs in different subnets of the same VNet communicate?

**Answer:**

Yes — VNet routing allows communication between subnets by default. That can be restricted by network security groups, user-defined routes, Azure Firewall or NVAs, service endpoints, private endpoints, or the guest OS's own firewall.

I check the effective routes, the NSG flow, DNS, and the target listener before assuming a subnet boundary is doing any actual security work.

## 15. Can an OS disk be removed from an Azure VM?

**Answer:**

You can't just detach the OS disk from a running VM the way you'd detach an ordinary data disk. Azure supports an OS-disk swap for a stopped VM in supported scenarios, and you can build a replacement VM from a managed-disk snapshot or image.

I take an application-consistent backup first, confirm what the actual recovery goal is, and use the documented swap or rebuild process rather than attempting a destructive detach.

## 16. Must an Azure VM and its Recovery Services vault be in the same region for backup?

**Answer:**

Yes — Azure VM Backup requires the Recovery Services vault and the VM it protects to be in the same region. Redundancy settings affect how the backup data itself gets replicated, but they don't remove that same-region requirement.

I pick the vault's region deliberately, apply retention, immutability, and access controls, and actually run restore tests rather than just checking that backups report success.

## 17. Do Azure tags automatically flow to child resources?

**Answer:**

No — tags aren't inherited by child resources automatically.

Azure Policy with a `modify` effect, infrastructure-as-code modules, or automation can enforce or copy the tags you need. I require ownership, environment, cost-center, and data-classification tags at deployment time, monitor for compliance, and handle exceptions explicitly, so cost allocation and incident ownership stay reliable.

## 18. Can a resource belong to more than one Azure resource group?

**Answer:**

No — an Azure resource belongs to exactly one resource group at a time.

A resource group is a management and lifecycle boundary. The resources inside it can still live in different regions. I group resources by ownership, lifecycle, access, and cost — not by assuming a resource group is also a network boundary.

## 19. Why does an Azure resource group have a location?

**Answer:**

That location just stores the resource group's own management metadata — deployment history, tags, locks, and similar information. It doesn't force every resource inside the group into that same region.

I still choose it deliberately for governance and support reasons, while setting each individual resource's location based on what that workload actually needs for performance, data residency, and resilience.

## 20. Are you charged for an Azure VM that is stopped but not deallocated?

**Answer:**

Yes. A VM that's stopped from inside the guest OS, or that shows as **Stopped**, can still hold onto its compute allocation and keep incurring compute charges. **Stopped (deallocated)** actually releases that allocation and stops the compute charges — though managed disks, snapshots, public IPs, and other attached resources can still cost money.

I use scheduled deallocation for non-production workloads, and I check the actual power state and the cost of anything still attached, rather than assuming "stopped" means "not costing anything."
