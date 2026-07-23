## 1. What is Microsoft Azure?

**Answer:**

Microsoft Azure is a cloud platform that provides compute, networking, storage, databases, identity, integration, security, monitoring, analytics, and DevOps services. It supports public cloud, hybrid, and multi-cloud scenarios through services such as Azure Arc.

A simple application flow is: users reach Azure Front Door, traffic goes to App Service or AKS, the workload uses managed identity to read Key Vault and access Azure SQL, and telemetry goes to Azure Monitor/Application Insights.

Azure uses tenants for identity, management groups and subscriptions for governance/billing boundaries, resource groups for lifecycle grouping, and regions/availability zones for placement. In an interview I explain the actual services, availability target, security model, operations, and cost controls rather than saying only “Azure hosts applications.”

## 2. What is the difference between IaaS, PaaS, and serverless in Azure?

**Answer:**

- **IaaS:** Azure manages physical infrastructure and virtualization; I manage VM OS, patches, middleware, application, and data. Example: Azure Virtual Machines.
- **PaaS:** Azure also manages the OS/runtime platform; I focus on application, configuration, identity, and data. Examples: App Service and Azure SQL Database.
- **Serverless:** Code or workflows run in response to events and can scale based on demand. Examples: Azure Functions and Logic Apps.

I choose IaaS for legacy software or OS-level control, PaaS for managed web/database platforms, and Functions for event-driven tasks. I compare compliance, runtime control, scaling, latency/cold start, execution duration, networking, operational effort, and steady-state cost. “Serverless” does not mean no servers; it means the provider operates them.

## 3. How do you manage infrastructure with Terraform in Azure?

**Answer:**

I use the `azurerm` provider, reusable modules, separate state boundaries, and an Azure Storage backend. CI authenticates with workload identity federation rather than a stored client secret.

```hcl
terraform {
  backend "azurerm" {}
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

provider "azurerm" { features {} }
```

The flow is `fmt` → `validate` → lint/security/policy checks → plan → peer review → production approval → apply saved plan → smoke tests. State storage uses encryption, versioning, lease-based locking, private access where required, and least privilege.

For failure I inspect Terraform state, provider error, Azure Activity Log, policy, quota, IAM, and networking. I never rerun blindly or edit state without backup and reconciliation.

## 4. How do you deploy applications to Azure Kubernetes Service?

**Answer:**

My delivery flow is:

1. Build and test the application.
2. Create a minimal container image, generate an SBOM, and scan it.
3. Push an immutable tag/digest to Azure Container Registry.
4. Deploy to AKS using Helm/manifests or GitOps with Flux/Argo CD.
5. Use workload identity and Key Vault CSI for Azure access/secrets.
6. Configure requests/limits, probes, Pod security, NetworkPolicy, HPA, and PodDisruptionBudget.
7. Wait for rollout, run smoke tests, and monitor errors/latency.

For a failed rollout I check `kubectl describe`, events, current/previous logs, image pull, configuration, probes, scheduling, and dependencies. I roll back traffic/release if user impact is growing, preserve evidence, fix in lower environment, and redeploy an immutable version.

## 5. How do you design a secure Azure landing zone?

**Answer:**

A landing zone is the governed foundation into which workloads are deployed. I gather regulatory, identity, connectivity, availability, ownership, and cost requirements, then design:

- Management-group hierarchy and subscription boundaries
- Entra ID groups, least-privilege RBAC, PIM, and break-glass access
- Azure Policy initiatives for regions, tags, diagnostics, encryption, and public access
- Hub-spoke or Virtual WAN connectivity, private DNS, Firewall, and DDoS controls
- Central logs/SIEM, Defender for Cloud, budgets, naming, and tagging
- IaC modules and a subscription-vending process

I test policies in audit mode, validate allowed and denied deployments, test private connectivity and DNS, and document exceptions. A landing zone must enable teams safely; uncontrolled policies that block necessary work are not mature governance.

## 6. How do you use managed identity in Azure?

**Answer:**

Managed identity gives an Azure workload an Entra ID identity without storing a password. A system-assigned identity follows one resource’s lifecycle; a user-assigned identity is a separate reusable resource.

The flow is: enable/attach identity → grant a narrow RBAC/data role → application requests a token from Azure’s identity endpoint through an SDK credential chain → target service validates the token.

For example, an App Service receives `Key Vault Secrets User` on one vault and reads a secret through `DefaultAzureCredential`. I do not grant subscription Contributor merely to read a secret.

I test allowed and denied operations, inspect sign-in/resource logs, and allow for RBAC propagation. If access fails, I verify the principal ID, token audience, role, scope, network rules/private DNS, and whether the service uses RBAC or an older access-policy model.

## 7. How do you manage secrets in Azure?

**Answer:**

I store secrets, keys, and certificates in Key Vault and access them with managed identity. Applications receive only the data-plane role they require. Vaults use soft delete and purge protection, logging, rotation, and private endpoints/firewall controls when necessary.

My preferred design avoids copying a secret into pipeline variables. The workload requests it at runtime or uses a Key Vault reference/CSI driver. I track owner, consumers, expiry, and rotation method. Rotation is tested so applications refresh without an outage.

If access fails, I distinguish management plane from data plane, check RBAC/access-policy mode, scope, identity, secret version/status, network restrictions, and logs. If exposure occurs, I rotate/revoke first, investigate access, and then remove leaked values from code, logs, and artifacts.

## 8. How do you monitor Azure resources?

**Answer:**

I use Azure Monitor as the common platform: metrics for numeric time series, diagnostic settings for platform/resource logs, Log Analytics with KQL, Application Insights for application/dependency traces, alerts with action groups, and workbooks/dashboards.

I define signals from service objectives: availability, latency, errors, traffic, saturation, queue depth, failed dependencies, and capacity. Alerts must be actionable, routed to an owner, and linked to a runbook.

During an incident I establish time and scope, correlate recent deployments and Activity Log changes, move from user symptom to application dependency to infrastructure, and validate the fix with the original query/transaction. I tune noisy alerts and test notification routing rather than assuming configuration works.

## 9. How do you control Azure costs?

**Answer:**

I combine allocation, prevention, optimization, and review:

- Management-group/subscription/resource-group ownership and required tags
- Budgets, forecasts, anomaly alerts, and cost exports
- Right-sizing from utilization and Advisor recommendations
- Autoscaling and schedules for non-production
- Reservations/savings plans for predictable compute after measurement
- Spot capacity for interruptible workloads
- Storage tier/lifecycle policies and cleanup of unattached resources
- Architecture review of network egress and managed-service tiers

For a spike I compare cost by service/resource/tag/day, correlate deployments and usage, stop clear waste safely, and contact the owner. I validate savings against reliability and performance; deleting idle-looking resources without ownership and recovery checks is unsafe.

## 10. How do you enforce governance in Azure?

**Answer:**

I use management groups for hierarchy, subscriptions for boundaries, Entra groups and RBAC/PIM for access, Azure Policy for audit/deny/deploy settings, resource locks for critical accidental deletion, and IaC/pipeline controls for standardized deployment.

Policies cover allowed regions/SKUs, mandatory tags, diagnostic settings, encryption, private connectivity, and security configuration. I roll them out as audit first, understand existing noncompliance, remediate, then move selected rules to deny. Exceptions have business justification, owner, scope, and expiry.

I monitor compliance trends, failed deployments, excessive privileged roles, and policy effects. Governance is successful when it produces consistent evidence and safe self-service, not when it only adds manual approval.

## 11. How do you approach Azure disaster recovery?

**Answer:**

I begin with business impact analysis and define RTO, RPO, data-loss tolerance, regional failure assumptions, dependencies, and recovery ownership. Then I select patterns per component: zones for datacenter failure, multi-region application capacity, database replication, geo-redundant storage where suitable, Azure Backup, Site Recovery for supported VM workloads, and Front Door/Traffic Manager/DNS failover.

A runbook covers detection, decision authority, data consistency, failover order, secret/DNS availability, smoke tests, communication, and failback. Backups are isolated and protected from deletion.

I run restore tests and regional exercises, measure actual RTO/RPO, and fix gaps. Replication is not a backup: corruption or deletion can replicate. I also test failback, because recovery is incomplete until normal operations are restored safely.
