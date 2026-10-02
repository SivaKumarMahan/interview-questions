# Azure Services: Identity, Secrets, and Governance

> Microsoft Entra ID, managed identity, Key Vault and secret rotation for AKS, and Azure Policy.

## Key Concepts

### Azure Key Vault Secret Rotation for AKS

My preferred design: use the Azure Key Vault provider for the Secrets Store CSI Driver, paired with AKS workload identity. The Pod mounts values straight from Key Vault, and the driver can poll for a new secret version on its own.

This keeps Terraform or a CI pipeline from becoming the long-term owner of rotating secret values — that job stays with Key Vault and the driver.

A few things matter here:

- Give the Kubernetes ServiceAccount and workload identity access to only the specific Key Vault objects they need, nothing broader.
- Use private Key Vault connectivity and DNS where that's required.
- Decide up front whether the application rereads the mounted file on its own, or needs a controlled Pod restart to pick up the change.
- Watch for mount and rotation errors, and actually test a rotation with both the old and new application connections still active.
- If you also sync the value into a Kubernetes Secret, remember that's another stored copy of the data. It needs its own encryption, RBAC, audit trail, and rotation handling.

An event-driven alternative: a Key Vault rotation event goes through Event Grid to an Azure Function or automation workflow, which updates the approved target and kicks off a safe rollout.

Whatever runs that workflow needs to be safe to run more than once, scoped to only the access it needs, logged, retried with dead-letter handling for failures, and verified afterward. A scheduled pipeline is simpler to build, but it can leave stale values sitting around until the next run — so don't rely on "runs every three months" as your only answer for a secret that might need to rotate early.

One more thing: Argo CD won't notice a Key Vault version change on its own. Something else — an external-secrets process, or an encrypted desired-state update — has to bring that change into Git or Kubernetes before Argo CD can act on it.

## Interview Questions

### 1. What is Microsoft Entra ID?

**Answer:**

Microsoft Entra ID is Microsoft's cloud identity service. It handles users, groups, applications and service principals, managed identities, devices, authentication, Conditional Access, and tokens.

It's a different system from Azure RBAC: Entra ID authenticates who someone is, while Azure RBAC decides what they're allowed to do to Azure resources.

I use groups instead of assigning access to individual users, turn on MFA and Conditional Access, use Privileged Identity Management for privileged roles, prefer workload identity over stored secrets, run access reviews, keep break-glass accounts ready, and watch sign-in and audit logs.

When authentication fails, I check the tenant, the identity's state, credentials or federation, Conditional Access rules, the token's audience and scopes, consent, and the sign-in logs. Once authentication is confirmed, authorization failures point me to roles and policies instead.

### 2. What is Azure Managed Identity?

**Answer:**

Managed Identity gives an Azure resource its own Entra identity. A system-assigned identity lives and dies with that one resource; a user-assigned identity is independent and can be reused across resources. Azure manages the credentials behind the scenes, and the workload just requests short-lived tokens.

For example: a Function has a user-assigned identity that's been granted Blob Data Reader on one container and Key Vault Secrets User on one vault. The code uses `DefaultAzureCredential`, and there's no client secret sitting in configuration anywhere.

I scope roles as narrowly as I can, and I use separate identities when workloads need different levels of access. When access fails, I check which identity is attached, whether the right principal or client ID was selected, the token's audience, the RBAC role and its scope, whether the assignment has propagated, and any network restrictions.

### 3. What is Azure Key Vault?

**Answer:**

Key Vault stores secrets, cryptographic keys, and certificates. Management-plane permissions control the vault's configuration; data-plane permissions control access to what's stored inside it. A subscription Owner doesn't automatically get to read secrets — those are two separate permission systems.

Applications use managed identity with a narrow role, like Key Vault Secrets User. I turn on soft delete and purge protection, enable logging, assign clear ownership for rotation and expiry, and use private networking where it's needed. I never let a secret's value get printed out through a pipeline or an infrastructure-as-code run.

When troubleshooting, I check the identity making the request, whether the vault uses RBAC or the older access-policy model, the role and its scope, whether the role assignment has actually propagated yet, the object's version and state, the token's audience, firewall and private DNS settings, and the audit logs. I test rotation with the actual consumers of the secret, not just in isolation.

### 4. How do you use Key Vault with App Service or Functions?

**Answer:**

I turn on managed identity, grant it a narrow Key Vault data role, set up network access and private DNS, then use a Key Vault reference in app settings, or access it directly through the SDK with `DefaultAzureCredential`.

The app setting holds a reference URI, not the actual secret value. I plan out how refresh and rotation should behave, and I avoid pinning to a specific secret version if I want rotation to happen automatically, unless controlled versioning is actually the goal.

I test startup and rotation, both allowed and denied identities, slot-specific identity and settings, and how the app behaves on failure. When troubleshooting, I check the reference's status, which identity got selected, the role and its scope, whether RBAC has propagated, the vault's network settings, DNS, the secret's expiry and state, and the logs.

No secret value ever gets printed in diagnostics.

### 5. What is Azure Policy?

**Answer:**

Azure Policy checks resource configuration against rules at whatever scope you assign it. Depending on the policy's effect, it can audit, deny, modify, append to, or deploy required settings. Initiatives group related policies together, and exemptions document any approved exceptions.

For example: audit storage accounts for public access, deploy diagnostic settings automatically, then deny new insecure storage accounts once the existing ones are fixed. I roll out audit mode first, look at false positives and the impact on existing resources, fix what needs fixing, then switch to enforcement. Policies and their assignments are version-controlled like code.

I test both compliant and non-compliant deployments, watch the compliance trend, and require exceptions to have an owner, a justification, and an expiry date. Policy is about governance — RBAC is what actually controls who can act.
