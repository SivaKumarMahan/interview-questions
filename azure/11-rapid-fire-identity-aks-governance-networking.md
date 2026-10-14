# Azure: Rapid-Fire Questions on Identity, AKS, Governance and Networking

> Fifty short-answer Azure questions for DevOps interviews, from basics to advanced: Entra ID and managed identities, AKS and containers, RBAC and Azure Policy governance, and networking. Use it for quick revision; the other Azure files explain each topic in depth.

## Key Concepts

### Corrections to common study notes

Several popular question sheets repeat outdated or wrong statements. Use these instead:

| Common claim | Correct answer |
| --- | --- |
| "An NSG is stateless" | NSGs are **stateful**: return traffic for an allowed flow is allowed automatically |
| "The AKS control plane is always free" | Free only on the **Free** tier. The **Standard** tier (uptime SLA, recommended for production) and **Premium** tier charge per cluster hour |
| "Use Azure Blueprints for repeatable environments" | Blueprints are deprecated (retirement July 2026). Use **Template Specs**, **Deployment Stacks**, Azure Policy and landing-zone IaC (Bicep or Terraform) |
| "ACR has built-in vulnerability scanning" | Scanning comes from **Microsoft Defender for Containers** (paid). Geo-replication needs the **Premium** SKU |
| "Application Gateway has a WAF, Front Door does not" | Both support **Azure WAF**: Front Door at the global edge, Application Gateway regionally |
| "Kubenet is a normal choice for new clusters" | Kubenet is being retired (March 2028). Use **Azure CNI Overlay** for new clusters |
| "AAD Pod Identity for Pod access to Azure" | Deprecated. Use **Microsoft Entra Workload ID** |

### Scope hierarchy

```text
Microsoft Entra tenant
└── Management groups (up to 6 levels below the root)
    └── Subscriptions (billing and access boundary)
        └── Resource groups (lifecycle boundary)
            └── Resources
```

RBAC role assignments and Policy assignments at a higher scope are **inherited** by everything below.

## Interview Questions

### Level 1: Core Azure and identity

<details><summary>Q1. [Basic] What is Microsoft Entra ID (formerly Azure Active Directory), and how does it relate to access to Azure resources?</summary>

**Answer:**

Microsoft Entra ID is Microsoft's cloud identity and access management service. It holds identities (users, groups, service principals, managed identities) and **authenticates** them (sign-in, MFA, Conditional Access). Azure RBAC then **authorizes** those identities: it decides what they can do on which Azure resources. Entra ID is also the identity platform for Microsoft 365 and for apps that use OAuth 2.0 and OpenID Connect.

</details>

<details><summary>Q2. [Basic] What is the difference between Azure RBAC and Azure Policy?</summary>

**Answer:**

- **Azure RBAC** controls **who** can do **what** at which scope. Example: give the app team Contributor on their resource group.
- **Azure Policy** controls **what resources may look like**, whoever creates them. Example: storage accounts must disable public access; only approved regions and VM SKUs are allowed.

RBAC answers "may this person act?"; Policy answers "is this resource compliant?". You need both: an Owner can still be blocked by a Deny policy.

</details>

<details><summary>Q3. [Basic] What is a service principal?</summary>

**Answer:**

A service principal is the identity of an application or automation tool in an Entra tenant, used for machine-to-machine access instead of a human account. It is created from an **app registration**, and it authenticates with a client secret, a certificate, or, best of all, **workload identity federation** (OIDC) from GitHub Actions, Azure DevOps or Kubernetes, which needs no stored secret. It is roughly the Azure equivalent of an AWS IAM role used by a workload.

</details>

<details><summary>Q4. [Basic] What is a managed identity, and how is it better than a service principal with a stored secret?</summary>

**Answer:**

A managed identity is an identity that Azure creates and manages for a resource such as a VM, App Service, Function App or AKS. The application gets tokens from the local identity endpoint, and Azure handles and rotates the credentials. There is **no secret** to store, leak or rotate by hand, which removes the most common credential leaks. Grant it the minimum RBAC role needed, for example "Key Vault Secrets User" on a single vault.

</details>

<details><summary>Q5. [Basic] What is the difference between a system-assigned and a user-assigned managed identity?</summary>

**Answer:**

| | System-assigned | User-assigned |
| --- | --- | --- |
| Created as | Part of one resource | A standalone Azure resource |
| Lifecycle | Deleted with the resource | Independent; survives resource deletion |
| Sharing | One resource only | Can be attached to many resources |
| Good for | One app with its own permissions | Several instances (VMSS, slots, AKS workloads) that need the same access; pre-creating permissions before the resource exists |

</details>

<details><summary>Q6. [Basic] What is Azure Resource Manager (ARM)?</summary>

**Answer:**

ARM is the deployment and management layer of Azure. Every request from the portal, Azure CLI, PowerShell, SDKs, Terraform or Bicep goes to the ARM API, which authenticates the caller with Entra ID, checks RBAC, evaluates Azure Policy, applies locks, and then sends the request to the resource provider. That is why access control, policy, tags and the Activity Log work the same way for every resource type.

</details>

<details><summary>Q7. [Basic] What is a resource group?</summary>

**Answer:**

A resource group is a logical container for resources that share a lifecycle, such as all resources of one application in one environment. It is a scope for RBAC, policy, tags, locks and cost reports. Deleting a resource group deletes everything in it, so production groups often get a `CanNotDelete` lock. A resource belongs to exactly one resource group, and resources in a group can be in different regions.

</details>

<details><summary>Q8. [Basic] What is the difference between a subscription and a management group?</summary>

**Answer:**

A **subscription** is a billing and access boundary that contains resource groups, with its own quotas. A **management group** sits above subscriptions and groups them, for example Platform, Landing Zones/Corp, Landing Zones/Online, Sandbox. Policies and RBAC assigned to a management group apply to every subscription under it, so governance is set once instead of per subscription.

</details>

<details><summary>Q9. [Basic] What is Azure Key Vault used for?</summary>

**Answer:**

Key Vault stores and controls access to **secrets** (passwords, connection strings), **keys** (encryption keys, including HSM-backed) and **certificates** (with automatic renewal). Applications read secrets at runtime using a managed identity, so nothing is hard-coded. Use the **Azure RBAC** permission model (recommended over legacy access policies), enable soft delete and purge protection, use a private endpoint, and send diagnostic logs to Log Analytics for auditing.

</details>

<details><summary>Q10. [Basic] What is the difference between a Network Security Group and an Application Security Group?</summary>

**Answer:**

An **NSG** is a stateful firewall of allow and deny rules (source, destination, port, protocol, priority), attached to a subnet or a network interface. An **ASG** is a label for a group of network interfaces, for example `asg-web` or `asg-db`, that you use as source or destination inside NSG rules. Rules like "allow `asg-web` to `asg-db` on 1433" keep working as VMs are added or removed, without editing IP addresses.

</details>

<details><summary>Q11. [Basic] What is a Virtual Network, and how does it compare to an AWS VPC?</summary>

**Answer:**

A VNet is a private, isolated network in one Azure region and subscription, with its own address space divided into subnets. It is the Azure equivalent of an AWS VPC. Differences to mention: Azure subnets span all availability zones of the region (AWS subnets belong to one AZ), and Azure provides default routing and outbound connectivity rules that differ from AWS. VNets connect to each other with peering and to on-premises with VPN Gateway or ExpressRoute.

</details>

<details><summary>Q12. [Basic] What is Azure Monitor, and what does it provide?</summary>

**Answer:**

Azure Monitor is the platform for collecting and acting on telemetry from Azure, on-premises and other clouds:

- **Metrics** (numeric time series) and **Logs** in Log Analytics workspaces, queried with KQL.
- **Application Insights** for application performance monitoring and distributed tracing.
- **Container Insights** and **managed Prometheus** with **Azure Managed Grafana** for AKS.
- **Alerts** with **action groups** (email, SMS, webhook, Logic App, runbook), plus workbooks and dashboards.

See [Azure Monitor, KQL and alerting](09-azure-monitor-kql-and-alerting.md) for detail.

</details>

<details><summary>Q13. [Basic] What is the difference between Azure CLI and Azure PowerShell? Does it matter which you use?</summary>

**Answer:**

Both call the same ARM APIs and can do almost the same things. **Azure CLI** (`az`) has a short, Bash-friendly syntax and returns JSON, which suits Linux pipelines. **Azure PowerShell** (`Az` module) returns objects, which suits Windows-heavy teams and complex scripting. The choice mostly depends on the team's existing skills and pipeline agents; for repeatable infrastructure I prefer Bicep or Terraform over either.

</details>

### Level 2: AKS and containers

<details><summary>Q14. [Basic] What is AKS, and how does its control-plane pricing compare with EKS?</summary>

**Answer:**

AKS is Azure's managed Kubernetes service: Azure runs the control plane (API server, etcd, scheduler), and you manage node pools and workloads.

Pricing:

- **Free tier:** no charge for the control plane, no financially backed SLA. Good for dev and test.
- **Standard tier:** charged per cluster hour, includes the uptime SLA and higher scale limits. Recommended for production.
- **Premium tier:** adds long-term support for Kubernetes versions.

EKS charges an hourly fee for every cluster. In both, you also pay for nodes, disks, load balancers and egress.

</details>

<details><summary>Q15. [Intermediate] How does Entra ID integration work for signing in to an AKS cluster?</summary>

**Answer:**

With AKS-managed Entra ID integration, `kubectl` users sign in with their Entra account (through `kubelogin`), and Kubernetes receives their user and group identity. Access is then granted with Kubernetes RBAC bindings to Entra **groups**, or with Azure RBAC for Kubernetes. Disable **local accounts** (`--disable-local-accounts`) so nobody can bypass Entra with the static admin kubeconfig, and use Conditional Access and PIM for admin groups.

</details>

<details><summary>Q16. [Intermediate] What is Azure RBAC for Kubernetes authorization, and how is it different from native Kubernetes RBAC?</summary>

**Answer:**

Native Kubernetes RBAC uses `Role`, `ClusterRole`, `RoleBinding` and `ClusterRoleBinding` objects stored inside the cluster. **Azure RBAC for Kubernetes** lets you grant in-cluster permissions with Azure role assignments instead, for example "Azure Kubernetes Service RBAC Reader" on a namespace scope. Access to Azure resources and to the cluster is then managed, reviewed and audited in one place. Both can be used together: Azure RBAC is checked first, then Kubernetes RBAC.

</details>

<details><summary>Q17. [Basic] What is a node pool in AKS?</summary>

**Answer:**

A node pool is a group of nodes with the same configuration: VM size, OS (Linux or Windows), zones, labels, taints and autoscaler settings. One cluster can have several pools, for example general-purpose, memory-optimised, GPU or Spot pools, and you steer workloads to them with node selectors, affinity, taints and tolerations.

</details>

<details><summary>Q18. [Basic] What is the difference between a system node pool and a user node pool?</summary>

**Answer:**

The **system** node pool runs critical add-ons such as CoreDNS, metrics-server and konnectivity. Every cluster needs at least one, it must be Linux, and it should have at least three nodes for production. **User** node pools run application workloads and can be scaled, changed or even scaled to zero independently. Taint the system pool with `CriticalAddonsOnly=true:NoSchedule` so application Pods stay off it.

</details>

<details><summary>Q19. [Intermediate] How does networking work in AKS? What are the main network plugin options?</summary>

**Answer:**

| Option | Pod IPs | Notes |
| --- | --- | --- |
| Kubenet | From a private range, NAT to the node IP | Simple, but limited and being retired (March 2028) |
| Azure CNI (flat) | Real VNet IPs | Pods directly reachable from the VNet; uses many IPs |
| Azure CNI Overlay | Private overlay range, not from the VNet | Saves VNet IPs; recommended default for most new clusters |
| Azure CNI powered by Cilium | Overlay or VNet IPs, eBPF data plane | Better performance and network policy, observability |

Choose based on IP address availability, whether Pods must be directly reachable from on-premises, and network policy needs.

</details>

<details><summary>Q20. [Intermediate] What is Azure CNI Overlay, and which problem does it solve?</summary>

**Answer:**

With flat Azure CNI, every Pod uses an IP from the VNet subnet, so large clusters exhaust address space fast and need huge subnets planned up front. **Azure CNI Overlay** gives Pods IPs from a private overlay CIDR (for example `10.244.0.0/16`) that does not use VNet addresses; only nodes take subnet IPs. Traffic leaving the cluster is translated to the node IP. Trade-off: Pods are not directly addressable from outside the cluster, so inbound traffic goes through Services or Ingress.

</details>

<details><summary>Q21. [Intermediate] How do you securely give an AKS Pod access to Azure resources such as Key Vault or Storage?</summary>

**Answer:**

Use **Microsoft Entra Workload ID** (it replaced the deprecated AAD Pod Identity):

1. Enable the OIDC issuer and workload identity on the cluster.
2. Create a user-assigned managed identity and grant it a narrow role (for example "Storage Blob Data Reader" on one account).
3. Create a federated identity credential that trusts the cluster's issuer and the specific `namespace:serviceaccount`.
4. Annotate the Kubernetes service account with the identity's client ID and label the Pod `azure.workload.identity/use: "true"`.

The Pod exchanges its service account token for an Entra token. No secrets are stored and each workload gets only its own permissions.

</details>

<details><summary>Q22. [Basic] What is Azure Container Registry, and how does it integrate with AKS?</summary>

**Answer:**

ACR is a private registry for container images, Helm charts and other OCI artifacts. Features include ACR Tasks for builds, geo-replication and private endpoints (Premium SKU), content trust, and vulnerability scanning through Defender for Containers. AKS pulls images without image pull secrets when the kubelet identity has the **AcrPull** role:

```bash
az aks update -g rg-aks -n aks-prod --attach-acr myregistry
```

</details>

<details><summary>Q23. [Intermediate] How does the Cluster Autoscaler work in AKS?</summary>

**Answer:**

The Cluster Autoscaler watches for Pods that are **Pending** because no node has enough requested CPU or memory, and adds nodes to the matching node pool (each pool is backed by a VM Scale Set), within the pool's `min-count` and `max-count`. When nodes are under-used and their Pods can be safely moved, it drains and removes them. It works on resource **requests**, not actual usage, so correct requests are essential. HPA scales Pods; Cluster Autoscaler scales nodes. **Node auto-provisioning** (Karpenter-based) can also choose VM sizes automatically.

</details>

<details><summary>Q24. [Basic] What is a VM Scale Set, and how does it relate to AKS node pools?</summary>

**Answer:**

A VM Scale Set (VMSS) manages a group of identical VMs that can scale in and out. Each AKS node pool is backed by a VMSS in the node resource group (`MC_...`). AKS manages it for you, so you scale and upgrade through AKS (`az aks nodepool scale`), never by editing the VMSS directly. It plays the same role as an Auto Scaling Group behind an EKS managed node group.

</details>

<details><summary>Q25. [Intermediate] How do you upgrade an AKS cluster with minimal disruption?</summary>

**Answer:**

1. Check supported versions and deprecated APIs (`az aks get-upgrades`, kubent or pluto) and read the release notes.
2. Upgrade a non-production cluster first.
3. Upgrade the control plane, then node pools one at a time (system pool first).
4. Use **max surge** (for example `33%`) so new nodes are added before old ones are cordoned and drained.
5. Make sure applications have several replicas, **PodDisruptionBudgets**, readiness probes and graceful shutdown.
6. Use a planned maintenance window and auto-upgrade channels for patch versions and node images.
7. Watch errors and latency during the rollout; for high-risk changes, blue-green clusters are the safest option.

</details>

<details><summary>Q26. [Intermediate] What is the Azure Policy add-on for AKS?</summary>

**Answer:**

It extends Azure Policy into the cluster using OPA Gatekeeper. Built-in policies can audit or deny Kubernetes objects, for example: no privileged containers, CPU and memory limits required, images only from approved registries, no `hostPath` volumes. Compliance appears in the same Azure Policy dashboard as other resources, and policies can be assigned at management-group level to all clusters at once.

</details>

<details><summary>Q27. [Intermediate] How would you secure secrets for applications running on AKS?</summary>

**Answer:**

Keep secrets in **Azure Key Vault** and mount them into Pods with the **Secrets Store CSI Driver** and the Azure Key Vault provider, authenticating with **Workload Identity**. Secrets then never live in Git or the image. If you also sync them into Kubernetes Secrets (for environment variables), enable etcd encryption with a Key Vault key (KMS), and restrict who can read Secrets with RBAC. Enable rotation polling so updated secrets reach Pods.

</details>

<details><summary>Q28. [Intermediate] What is the difference between AKS and Azure Container Apps, and when do you choose each?</summary>

**Answer:**

| | AKS | Azure Container Apps |
| --- | --- | --- |
| Model | Full Kubernetes; you manage node pools, upgrades and add-ons | Serverless containers on managed Kubernetes with KEDA, Dapr and Envoy |
| Kubernetes API | Full access | None |
| Scaling | HPA, KEDA, Cluster Autoscaler | Built-in, including scale to zero |
| Best for | Large platforms, custom operators, service mesh, strict network control | Microservices, APIs, event-driven jobs without a platform team |

</details>

<details><summary>Q29. [Intermediate] How would you troubleshoot a Pod networking issue on AKS?</summary>

**Answer:**

1. Inside Kubernetes: Pod status and readiness, Service selector and `kubectl get endpoints`, NetworkPolicies, and CoreDNS (`nslookup` from a debug Pod).
2. Test from a debug Pod: `kubectl run tmp --rm -it --image=nicolaka/netshoot -- bash`, then `curl`, `dig` and `nc`.
3. Azure side: NSG rules on the node subnet, route tables (UDRs) and Azure Firewall rules for egress, private DNS zones for private endpoints.
4. Check the network plugin behaviour (Overlay or flat CNI, Cilium policy).
5. Use Container Insights, NSG or VNet flow logs and Network Watcher (connection troubleshoot, IP flow verify).

</details>

<details><summary>Q30. [Advanced] Describe a real production issue you faced running workloads on AKS and what you learned.</summary>

**Answer:**

Use the STAR format and be specific. Example:

> "After we added two services, new Pods stayed Pending with 'insufficient IP addresses'. The cluster used flat Azure CNI on a /24 subnet with max 30 Pods per node, so the subnet was exhausted. Short term, I added a node pool on a new, larger subnet and moved workloads with node selectors. Long term, we migrated to Azure CNI Overlay through a blue-green cluster, added an alert on subnet IP usage, and documented IP planning in our cluster module. No more IP-related outages after that."

Other good stories: a Workload Identity federated-credential mismatch that blocked Key Vault access, or a node pool that could not scale out because of VM quota.

</details>

### Level 3: RBAC and governance

<details><summary>Q31. [Basic] What are the built-in Owner, Contributor and Reader roles?</summary>

**Answer:**

- **Owner:** full access, including granting access to others (role assignments).
- **Contributor:** create and manage all resources, but cannot grant access or change role assignments (and cannot manage Blueprints or policy assignments).
- **Reader:** view only.

Also know **User Access Administrator** (only manages access) and **Role Based Access Control Administrator**, which can be limited with conditions to assign only certain roles. Prefer narrow service roles (for example "Key Vault Secrets User", "AcrPush") over Contributor.

</details>

<details><summary>Q32. [Basic] How does the scope of an Azure RBAC role assignment work?</summary>

**Answer:**

A role can be assigned at management group, subscription, resource group or single resource scope, and it is **inherited** by everything below. RBAC is **additive**: a user's effective permissions are the union of all their assignments, so a narrower assignment cannot take away a broader one. To block actions explicitly, use **deny assignments** (created by Deployment Stacks or managed apps) or Azure Policy.

</details>

<details><summary>Q33. [Intermediate] What is a custom RBAC role, and when do you create one?</summary>

**Answer:**

A custom role is a JSON definition with `Actions`, `NotActions`, `DataActions` and `AssignableScopes`, used when no built-in role matches the least-privilege need. Example: an operator who can start, stop and restart VMs but not create or delete them:

```json
{
  "Name": "VM Operator",
  "Actions": [
    "Microsoft.Compute/virtualMachines/read",
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/restart/action",
    "Microsoft.Compute/virtualMachines/deallocate/action"
  ],
  "AssignableScopes": ["/subscriptions/<sub-id>"]
}
```

Note that `NotActions` is not a deny: another role can still grant the excluded action. (A built-in role, "Virtual Machine Contributor", is broader than this.)

</details>

<details><summary>Q34. [Intermediate] What is Azure Policy, and how does it enforce compliance?</summary>

**Answer:**

Azure Policy evaluates resource properties against rules when resources are created or changed, and on a regular compliance scan. Effects include:

- **Deny:** block a non-compliant deployment.
- **Audit:** allow it but mark it non-compliant.
- **Append / Modify:** add or change properties, for example tags.
- **DeployIfNotExists:** deploy a missing companion resource, for example diagnostic settings, through a remediation task with a managed identity.
- **AuditIfNotExists**, **Disabled**, and **DenyAction** (block specific actions such as delete).

Start with Audit to measure impact, then switch to Deny.

</details>

<details><summary>Q35. [Basic] What is the difference between a policy initiative and a single policy?</summary>

**Answer:**

A policy definition is one rule. An **initiative** (policy set) groups many definitions with shared parameters so they are assigned, tracked and reported as one unit, for example the Microsoft cloud security benchmark, CIS, ISO 27001, or your own "Corp landing zone baseline".

</details>

<details><summary>Q36. [Intermediate] What were Azure Blueprints used for, and what replaces them?</summary>

**Answer:**

Blueprints packaged ARM templates, role assignments and policy assignments so new subscriptions could be created already compliant. They are **deprecated** (retirement July 2026). Today the same goal is met with:

- **Template Specs** for versioned, shareable templates.
- **Deployment Stacks** to deploy and manage a group of resources together, with deny settings to protect them.
- **Azure landing zones** (Bicep or Terraform accelerators) plus **Azure Policy** initiatives at management-group level.
- Subscription vending through a pipeline.

</details>

<details><summary>Q37. [Intermediate] How do you audit who has access to a resource and what they can do?</summary>

**Answer:**

- Portal: the resource's **Access control (IAM)** → **Role assignments** and **Check access**, which include inherited assignments.
- CLI: `az role assignment list --scope <resource-id> --include-inherited --output table`.
- At scale: **Azure Resource Graph** queries over `authorizationresources` across all subscriptions.
- History: the **Activity Log** shows who created or removed assignments.
- Ongoing: **Entra access reviews** to re-certify access, and **PIM** for privileged roles.
- Remember data-plane access too: Key Vault, Storage and SQL can also have their own access settings.

</details>

<details><summary>Q38. [Intermediate] What is Privileged Identity Management (PIM), and which problem does it solve?</summary>

**Answer:**

PIM gives **just-in-time**, time-limited activation of privileged Entra and Azure roles instead of permanent assignments. Users are *eligible* and activate a role when needed, with MFA, a justification, optional approval and a maximum duration, and every activation is audited. It shrinks the attack surface of standing admin access and supports access reviews.

</details>

<details><summary>Q39. [Intermediate] How is the Azure Activity Log different from Azure Monitor Logs (Log Analytics)?</summary>

**Answer:**

The **Activity Log** is the platform record of subscription-level **control-plane** events: who created, changed or deleted which resource, plus service health events. It is similar to AWS CloudTrail and kept for 90 days by default. **Azure Monitor Logs** (Log Analytics) is a flexible store you configure for resource logs (diagnostic settings), application logs, agent data and the Activity Log itself, queried with KQL and kept for as long as you configure. Send the Activity Log to Log Analytics for longer retention and alerting.

</details>

<details><summary>Q40. [Advanced] How would you design Azure governance for a large enterprise with many teams and environments?</summary>

**Answer:**

- **Hierarchy:** management groups following the Azure landing-zone model (Platform: identity, management, connectivity; Landing zones: Corp, Online; Sandbox; Decommissioned).
- **Subscriptions** per application and environment, created through subscription vending, for clear billing and a small blast radius.
- **Policy initiatives** at management-group level: allowed regions and SKUs, required tags, no public IPs in Corp, diagnostic settings, Defender for Cloud plans.
- **RBAC** through Entra groups, least privilege, PIM for Owner and admin roles, no permanent personal Owner assignments.
- **Networking:** hub-and-spoke or Virtual WAN with central firewall and DNS.
- **Cost:** budgets and alerts per subscription, tagging for chargeback.
- **Everything as code** (Terraform or Bicep) with pipeline approvals.

</details>

### Level 4: Networking and advanced scenarios

<details><summary>Q41. [Intermediate] What is VNet peering, and how is it different from connecting VNets with a VPN gateway?</summary>

**Answer:**

**VNet peering** connects two VNets (same or different regions) over the Microsoft backbone with low latency and high bandwidth, and no gateway in the path. Peering is non-transitive: in hub-and-spoke, spokes reach each other only through the hub firewall or with a route server. A **VPN gateway** builds an IPsec-encrypted tunnel; it is used mainly for on-premises connections, has lower throughput and adds gateway cost. Peering traffic stays private but is not encrypted by peering itself; enable **VNet encryption** when encryption in transit is required.

</details>

<details><summary>Q42. [Intermediate] What is ExpressRoute, and how does it compare to a site-to-site VPN?</summary>

**Answer:**

**ExpressRoute** is a private, dedicated circuit from on-premises to Microsoft through a connectivity provider, which does not cross the public internet. It gives predictable latency, high bandwidth (up to 100 Gbps with ExpressRoute Direct) and an SLA. It is not encrypted by default; add MACsec or IPsec over it if needed. A **site-to-site VPN** is an encrypted IPsec tunnel over the internet: cheaper and faster to set up, but with variable latency and lower throughput. Many companies use ExpressRoute as the primary path and VPN as the backup.

</details>

<details><summary>Q43. [Intermediate] What is Azure Front Door, and how is it different from Application Gateway?</summary>

**Answer:**

| | Azure Front Door | Application Gateway |
| --- | --- | --- |
| Scope | Global, at Microsoft edge locations | Regional, inside your VNet |
| Layer | 7 (HTTP/HTTPS) with CDN caching | 7 (HTTP/HTTPS) |
| Use | Multi-region failover, global acceleration, static content | Routing to private back ends in one region, AKS ingress (AGIC / Application Gateway for Containers) |
| WAF | Yes (Premium for managed rule sets and bot protection) | Yes (WAF_v2 SKU) |
| Private back ends | Through Private Link (Premium) | Directly in the VNet |

A common pattern is Front Door in front of regional Application Gateways.

</details>

<details><summary>Q44. [Basic] What is a private endpoint, and why use one?</summary>

**Answer:**

A private endpoint is a network interface with a private IP in your subnet that connects to one specific PaaS resource (Storage, SQL, Key Vault, ACR) through Azure Private Link. Traffic stays on the Microsoft network, and public access to the service can be disabled. It needs a **private DNS zone** (for example `privatelink.blob.core.windows.net`) linked to the VNet, so the normal hostname resolves to the private IP. See Q24 in [Epam2](../real-interview-questions/Epam2.md) for the full request flow.

</details>

<details><summary>Q45. [Intermediate] A VM in a private subnet cannot reach the internet. How do you troubleshoot?</summary>

**Answer:**

1. **Outbound method:** private subnets need a **NAT Gateway**, Azure Firewall or a load balancer outbound rule. Default outbound access is being retired, so new VNets should not rely on it.
2. **Route table (UDR):** is `0.0.0.0/0` sent to the firewall or NVA, or to on-premises by forced tunnelling? Check **Effective routes** on the NIC.
3. **NSG:** check **Effective security rules** for outbound denies.
4. **Firewall rules:** application or network rules for the destination FQDN or port; check the firewall logs.
5. **DNS:** can the VM resolve names (custom DNS server reachable)?
6. Test with **Network Watcher** connection troubleshoot and IP flow verify, and from the VM with `curl -v`.

</details>

<details><summary>Q46. [Intermediate] What is Azure Firewall, and how does it differ from an NSG?</summary>

**Answer:**

An **NSG** is a free, distributed, **stateful** layer 3/4 filter on subnets or NICs, using IPs, ports, service tags and ASGs. **Azure Firewall** is a managed, centralised, highly available firewall service with FQDN filtering, application rules, threat-intelligence filtering, DNS proxy, central logging and, in the Premium SKU, TLS inspection and IDPS. Typical design: NSGs for micro-segmentation inside each spoke, and Azure Firewall in the hub to control traffic between spokes, to on-premises and to the internet.

</details>

<details><summary>Q47. [Basic] What is the difference between Azure Load Balancer and Application Gateway?</summary>

**Answer:**

**Azure Load Balancer** works at layer 4 (TCP/UDP): very fast, no knowledge of HTTP, used for VMs, VMSS, non-HTTP traffic and AKS `LoadBalancer` Services. Use the Standard SKU (Basic was retired). **Application Gateway** works at layer 7 (HTTP/HTTPS): TLS termination, path- and host-based routing, cookie affinity, rewrites, and WAF. It is the same split as AWS NLB versus ALB.

</details>

<details><summary>Q48. [Intermediate] How would you design network security for a multi-tier application in Azure?</summary>

**Answer:**

- Separate subnets per tier (web, app, data) in a spoke VNet peered to a hub.
- Internet traffic only through **Front Door or Application Gateway with WAF**; no public IPs on VMs.
- **NSGs** with ASGs: web accepts 443 only from the gateway subnet, app accepts only from web, data accepts only from app.
- **Private endpoints** for SQL, Storage and Key Vault, with public access disabled and private DNS zones.
- Outbound traffic through **Azure Firewall** (or NAT Gateway) with FQDN allow-lists.
- Admin access via **Azure Bastion** or just-in-time VM access.
- DDoS Protection on public endpoints, flow logs and Defender for Cloud for monitoring.

</details>

<details><summary>Q49. [Basic] What is Azure DevOps, and how does it compare with GitHub Actions?</summary>

**Answer:**

Azure DevOps is a suite: **Repos** (Git), **Pipelines** (YAML CI/CD with environments, approvals and checks), **Boards** (work tracking), **Artifacts** (package feeds) and **Test Plans**. GitHub Actions is GitHub's event-driven workflow engine, tightly integrated with GitHub repositories and pull requests, with a large marketplace of actions, and with GitHub Advanced Security for code scanning. Both support OIDC to Azure, self-hosted agents or runners, and multi-stage deployments. Microsoft's new investment is mostly in GitHub, but Azure DevOps remains common in enterprises for Boards and approvals.

</details>

<details><summary>Q50. [Advanced] Describe a production incident on Azure infrastructure that you resolved, and what changed afterwards.</summary>

**Answer:**

Use STAR and finish with a lasting improvement. Example:

> "After a network change, our API returned 502s through Application Gateway. The back-end health page showed the pool unhealthy, and IP flow verify showed that a new NSG rule on the app subnet denied traffic from the gateway subnet on 443. I added an allow rule from the gateway subnet with a higher priority, and the back ends were healthy within minutes, about 20 minutes of impact in total. Afterwards we moved NSG rules into Terraform with pull request review, added an alert on unhealthy back-end hosts, and added the gateway health check to the change checklist."

Other good examples: a managed identity that lost its Key Vault role assignment after a redeploy, or an AKS node pool that could not scale because of regional vCPU quota.

</details>
