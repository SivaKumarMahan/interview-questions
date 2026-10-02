# Azure: Identity, Security, and Governance

> Entra ID and RBAC, managed identity, Key Vault and secrets, Defender, landing zones, Azure Policy, tags, and resource groups.

## Key Concepts

### Entra ID, RBAC, and scope

Microsoft Entra ID authenticates users, groups, service principals, and managed identities — it confirms who someone is. Azure RBAC authorizes what they can do to Azure resources.

Entra directory roles like Global Administrator govern directory-wide capabilities. Azure roles like Owner, Contributor, and Reader govern access to resources. These are two different permission systems, not one.

Azure resource scope inherits downward:

```text
management group -> subscription -> resource group -> resource
```

Apply the rule **right principal, right role, right scope**. Prefer groups and managed identities over individual assignments. Use least privilege, time-bound privileged access, separation of duties, access reviews, and diagnostic logs.

`Owner` can also assign roles to others. `Contributor` manages resources but can't grant RBAC access by default. `Reader` is view-only. Avoid broad, permanent assignments when a narrower resource-group or resource scope would do the job.

### Key Vault: Management Plane vs. Data Plane

A subscription Owner does not automatically receive permission to read or change secrets, keys, and certificates in every Key Vault.

- **Management plane:** Create or delete the vault, configure networking, and manage resource settings and role assignments.
- **Data plane:** Read, create, update, or delete the keys, secrets, and certificates stored inside the vault.

The Owner role provides broad management-plane permissions, including the ability to assign access, but it is not itself a Key Vault data-plane role.

#### When using Azure RBAC

Assign a suitable data-plane role at the narrowest practical scope:

| Role | Typical access |
| --- | --- |
| Key Vault Administrator | Manage keys, secrets, and certificates; does not manage RBAC assignments |
| Key Vault Crypto Officer | Create and manage keys |
| Key Vault Secrets Officer | Create and manage secrets |
| Key Vault Certificates Officer | Create and manage certificates |
| Key Vault Secrets User | Read secret values |

#### When using vault access policies

Add an access policy that explicitly grants the required key, secret, or certificate operations.

Check the configured model under **Key Vault > Settings > Access configuration**. Apply least privilege, and prefer managed identities for applications.

### Defender for Containers

Microsoft Defender for Containers adds security capabilities for supported container registries and Kubernetes environments.

What it actually gives you depends on which Defender plan, extensions, and connectivity you've enabled — it can cover vulnerability scanning for the registry and running images, security-posture recommendations, and runtime threat detection.

In an Azure delivery flow:

1. CI scans the exact image digest and blocks findings according to policy.
2. The approved digest is stored in Azure Container Registry.
3. AKS deploys the same digest using managed identity with narrowly scoped `AcrPull`.
4. Defender for Containers continuously reassesses supported registry and running images and produces security findings.
5. Defender alerts flow to the security operations process; Azure Monitor verifies application health.

Defender doesn't automatically stop an Azure DevOps run by itself — it's not a pipeline task. To actually enforce a deployment policy, use a CI scan that fails the build, an admission policy, or an Azure DevOps environment check that queries an approved external decision source.

Plan out the Defender components and private-cluster connectivity you need, then test that alerts actually route where they should and get fixed.

### Landing Zone design areas

An Azure Landing Zone is a governed platform blueprint. It's more than just a collection of VNets and subnets.

Its design covers tenant and resource organization, identity and access, network topology and hybrid connectivity, security and governance, management and monitoring, business continuity, cost, and platform automation.

Management groups and subscriptions set the policy, ownership, billing, and blast-radius boundaries. Shared platform subscriptions can host connectivity, identity, and management capabilities, while each application team owns its own workload subscription.

### Azure Policy governance

Azure Policy checks resources against your organization's rules. Depending on the effect you choose, it can audit, deny, modify supported properties, deploy required configuration, or just flag something as non-compliant.

Initiatives group related policies into one baseline, and an assignment at management-group scope can inherit down across every subscription underneath it. Common controls include allowed regions or SKUs, mandatory tags, diagnostic settings, encryption, private networking, and security baselines.

Start a policy rollout with an inventory and audit-only mode. Look at exemptions and how much it would break, then move to enforcement through proper change control. Policy isn't a replacement for RBAC — RBAC decides who can act, while Policy decides which resource states are acceptable.

### Azure Policy: Restricting Snapshot SKUs

Azure Policy can enforce or report configuration rules at scale. For example, an organization can require managed-disk snapshots in Central India to use `Standard_LRS`.

- `deny` blocks a non-compliant create or update request.
- `audit` allows the request but marks the resource non-compliant.

Example policy rule:

```json
{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Compute/snapshots"
      },
      {
        "field": "location",
        "equals": "centralindia"
      },
      {
        "field": "Microsoft.Compute/snapshots/sku.name",
        "notEquals": "Standard_LRS"
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}
```

**Expected behavior**

- With `deny`, `Standard_LRS` passes and a disallowed SKU is rejected.
- With `audit`, a disallowed SKU can be created but appears as non-compliant.

Test policies in a non-production scope first. Review aliases, exemptions, existing resources, and fix requirements before broad assignment.

### Moving Resources Between Resource Groups

Azure can move many resource types between resource groups, but support and dependencies vary by service.

**What happens during a move**

- Azure validates that the resources and dependencies support the move.
- The source and destination resource groups are locked against write operations for part of the move.
- Existing workloads usually continue to run, but control-plane changes are temporarily blocked.
- Resource IDs change because the resource-group segment changes.

**Preparation checklist**

1. Confirm that every resource type supports the intended move.
2. Identify and include required dependent resources.
3. Check resource locks, policies, quotas, and destination permissions.
4. Save resource IDs and review anything that stores them explicitly, such as scripts, dashboards, or external automation.
5. Validate the move before execution.
6. Avoid simultaneous changes to either resource group.
7. Verify monitoring, permissions, automation, and application behavior afterward.

**Interview summary:** A resource-group move is primarily a control-plane operation and normally does not move the resource's physical region. Do not promise zero impact without checking the specific services and dependencies.

## Interview Questions

### 1. How do you use managed identity in Azure?

**Answer:**

Managed identity gives an Azure workload its own Entra ID identity, with no password to store. A system-assigned identity lives and dies with one resource; a user-assigned identity is a separate resource you can reuse elsewhere.

The flow: enable or attach the identity → grant it a narrow RBAC or data role → the application requests a token from Azure's identity endpoint through an SDK credential chain → the target service validates that token.

For example, an App Service gets `Key Vault Secrets User` on one vault, and reads a secret through `DefaultAzureCredential`. I don't grant subscription Contributor just so an app can read one secret.

I test both allowed and denied operations, check sign-in and resource logs, and give role assignments time to propagate. If access fails, I check the principal ID, the token's audience, the role and its scope, network rules and private DNS, and whether the service uses RBAC or the older access-policy model.

### 2. How do you manage secrets in Azure?

**Answer:**

I store secrets, keys, and certificates in Key Vault and access them through managed identity. Applications only get the specific data-plane role they need.

Vaults use soft delete and purge protection, logging, rotation, and private endpoints or firewall controls when necessary.

My preferred setup avoids ever copying a secret into a pipeline variable. The workload fetches it at runtime, or uses a Key Vault reference or the CSI driver.

I track who owns each secret, who consumes it, when it expires, and how it gets rotated. I test rotation so applications pick up the new value without an outage.

If access fails, I check whether it's a management-plane or data-plane issue, the RBAC or access-policy mode, the scope, the identity, the secret's version and status, network restrictions, and the logs. If a secret is ever exposed, I rotate or revoke it first, investigate who accessed it, and only then clean up the leaked value from code, logs, and artifacts.

### 3. How do you secure Azure Key Vault?

- **Enable Soft Delete** - deleted secrets, keys, or certificates are retained and recoverable during the retention period, instead of being gone immediately.
- **Enable Purge Protection** - prevents a *permanent* purge during that retention period, so even someone with delete permissions can't irreversibly destroy a secret before the retention window ends.
- **Use Managed Identity** instead of storing credentials in application code to authenticate to the Vault.
- **Use Azure RBAC with least privilege** - scope access to exactly the secrets/keys a given identity needs.
- **Enable diagnostic logs and monitoring** - so access to secrets is auditable.
- **Restrict network access** using Private Endpoints or firewall rules, rather than leaving the Vault reachable from the public internet.

#### Short interview answer

I secure Key Vault with Soft Delete and Purge Protection so secrets can't be irrecoverably destroyed, Managed Identity instead of embedded credentials, least-privilege Azure RBAC, diagnostic logging for auditability, and private network access via Private Endpoints or firewall rules instead of public exposure.

### 4. How do you design a secure Azure landing zone?

**Answer:**

A landing zone is the governed foundation that workloads get deployed into. I start by gathering the regulatory, identity, connectivity, availability, ownership, and cost requirements, then design:

- Management-group hierarchy and subscription boundaries
- Entra ID groups, RBAC scoped to only what's needed, Privileged Identity Management, and break-glass access
- Azure Policy initiatives for regions, tags, diagnostics, encryption, and public access
- Hub-spoke or Virtual WAN connectivity, private DNS, Firewall, and DDoS controls
- Central logging or SIEM, Defender for Cloud, budgets, naming conventions, and tagging
- Infrastructure-as-code modules and a subscription-vending process

I test policies in audit mode first, check that allowed and denied deployments actually behave as expected, verify private connectivity and DNS, and document any exceptions. A landing zone has to let teams work safely — policies so strict they block necessary work aren't mature governance, they're just an obstacle.

### 5. How do you enforce governance in Azure?

**Answer:**

I use management groups for hierarchy, subscriptions as boundaries, Entra groups with RBAC and Privileged Identity Management for access, Azure Policy for audit, deny, or deploy rules, resource locks to prevent accidental deletion of critical resources, and infrastructure-as-code or pipeline controls to standardize how things get deployed.

Policies cover things like allowed regions or SKUs, mandatory tags, diagnostic settings, encryption, private connectivity, and security configuration. I roll them out as audit-only first, understand what's already non-compliant, fix it, and only then switch selected rules to deny.

Exceptions always need a business justification, an owner, a scope, and an expiry date.

I watch compliance trends, failed deployments, how many people hold privileged roles, and how policies are actually behaving. Governance is working when it produces consistent evidence and lets people self-serve safely — not when its only effect is adding another manual approval.

### 6. Do Azure tags automatically flow to child resources?

**Answer:**

No — tags aren't inherited by child resources automatically.

Azure Policy with a `modify` effect, infrastructure-as-code modules, or automation can enforce or copy the tags you need. I require ownership, environment, cost-center, and data-classification tags at deployment time, monitor for compliance, and handle exceptions explicitly, so cost allocation and incident ownership stay reliable.

### 7. Can a resource belong to more than one Azure resource group?

**Answer:**

No — an Azure resource belongs to exactly one resource group at a time.

A resource group is a management and lifecycle boundary. The resources inside it can still live in different regions. I group resources by ownership, lifecycle, access, and cost — not by assuming a resource group is also a network boundary.

### 8. Why does an Azure resource group have a location?

**Answer:**

That location just stores the resource group's own management metadata — deployment history, tags, locks, and similar information. It doesn't force every resource inside the group into that same region.

I still choose it deliberately for governance and support reasons, while setting each individual resource's location based on what that workload actually needs for performance, data residency, and resilience.
