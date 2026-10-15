# My Projects: Consumption Logic App Reading a Firewall-Protected Storage Account

> A hands-on scenario: how to lock a Storage account down with its firewall (selected networks only) and still let a Consumption Logic App read blobs from it, using a system-assigned managed identity and a resource instance rule. Includes a STAR draft and likely follow-up questions.

## Key Concepts

This scenario comes from my own hands-on notes and a working test setup. It is not a resume bullet. Use it as a "tell me about a tricky problem you solved" story only if you did this in a real project, and replace each `[Confirm: …]` with the real detail first.

### The problem in simple words

- Security teams want Storage accounts closed to the internet, so we set **Public network access** to **Enabled from selected networks** (or disable it).
- A **Consumption** Logic App runs in Microsoft's shared, multi-tenant environment. It has **no VNet integration** and **no fixed private IP**, so you cannot just "add the Logic App's network" to the Storage firewall.
- Allowing the Logic App's outbound IP addresses is also unreliable: the list is long and shared with other customers, and when the Logic App and the Storage account are in the **same region**, Azure sends the traffic over private IPs, so IP firewall rules do not match at all.
- Result: as soon as the firewall is on, the Logic App's blob trigger and "Get blob content" action fail with **403 (AuthorizationFailure / This request is not authorized to perform this operation)**.

### The solution in one line

Give the Logic App a **managed identity**, give that identity a **data role** on the Storage account, and add a **resource instance rule** on the Storage firewall that allows **that specific Logic App** in.

### Key terms

| Term | Simple meaning |
| --- | --- |
| System-assigned managed identity | An identity Azure creates for the Logic App. No password or key to store. |
| Storage Blob Data Contributor | An RBAC role that lets an identity read, write, and delete blobs (data plane). Use **Storage Blob Data Reader** if the Logic App only reads. |
| Selected networks | The Storage firewall mode that blocks everything except the VNets, IPs, and resource instances you list. |
| Resource instance rule | A firewall rule that allows one specific Azure resource (identified by its system-assigned managed identity) through the Storage firewall, even though it is not in your VNet. |
| Trusted Microsoft services exception | A checkbox that lets a fixed list of Azure services bypass the firewall. Broader than a resource instance rule. |

### Step-by-step setup

**Step 1: Create the Logic App and turn on its system-assigned managed identity.**

Logic App > **Settings > Identity > System assigned > Status: On > Save**. Azure creates an identity and shows its **Object (principal) ID**.

```bash
az logic workflow identity assign -g rg-int -n la-blob-reader --system-assigned   # needs the "logic" CLI extension
```

**Step 2: Create the Storage account and give the Logic App's identity a data role.**

Storage account > **Access Control (IAM) > Add role assignment > Storage Blob Data Contributor** > Members: **Managed identity** > pick the Logic App.

```bash
az role assignment create \
  --assignee-object-id <logic-app-principal-id> \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope $(az storage account show -g rg-int -n stintdemo --query id -o tsv)
```

**Step 3: Configure Storage networking.** Storage account > **Networking > Public network access**:

1. **Public network access:** Enable.
2. **Public network access scope:** Enable from selected networks.
3. **Virtual networks:** add the VNet and subnet of any *other* clients that need access (for example VMs or a Logic App Standard). This uses service endpoints. It does not help the Consumption Logic App itself.
4. **Resource instances:** Resource type = `Microsoft.Logic/workflows`.
5. **Instance name:** select your Logic App (or all Logic Apps in a resource group or subscription, if that fits your use case; one specific instance is the safest).
6. **Exceptions:** **untick** "Allow trusted Microsoft services to access this resource", so only the resources you named can get in.

```bash
az storage account update -g rg-int -n stintdemo --default-action Deny --public-network-access Enabled

az storage account network-rule add -g rg-int --account-name stintdemo \
  --resource-id /subscriptions/<sub-id>/resourceGroups/rg-int/providers/Microsoft.Logic/workflows/la-blob-reader \
  --tenant-id <tenant-id>
```

**Step 4: Build the workflow and test it.**

- Trigger: **When a blob is added or modified (properties only) (V2)**.
- Action: **Get blob content (V2)**.
- Action: **Parse JSON** on the blob content.
- When creating the Azure Blob Storage connection, choose **Logic Apps Managed Identity** as the authentication type, **not** an access key or connection string.

Upload a JSON file to the container. The run history should show all three steps green, and Parse JSON should show the file's fields.

### Why each piece is needed

```text
Logic App (Consumption)
  | 1. gets a token for its system-assigned managed identity
  v
Storage firewall  ---- 2. resource instance rule: "this Logic App may pass" (network check)
  |
  v
Blob data plane   ---- 3. RBAC: Storage Blob Data Contributor (permission check)
```

- **Without the managed identity:** there is no identity for the firewall rule or RBAC to recognise.
- **Without the resource instance rule:** the network check fails, so you get **403 AuthorizationFailure** even though RBAC is correct.
- **Without the RBAC role:** the network check passes but the permission check fails, so you get **403 AuthorizationPermissionMismatch**.
- **With an access-key connection:** the connector does not use the managed identity, so the resource instance rule does not apply. Use managed identity authentication.

### Alternatives and when to use them

| Option | When to use it |
| --- | --- |
| Resource instance rule + managed identity (this scenario) | Consumption Logic App, quick and cheap, no extra networking |
| Logic App **Standard** with VNet integration + Storage **private endpoint** | Strict "no public endpoint at all" policies; higher cost, more networking work |
| Trusted Microsoft services exception | Only for services on Microsoft's trusted list; broader than you usually want |
| **Network Security Perimeter** ("Secured by perimeter") | Newer option to group PaaS resources inside one perimeter with shared inbound and outbound rules |
| IP allow-list of Logic App outbound IPs | Avoid: shared IPs, long list, and does not work in the same region |

### STAR draft

- **Situation:** Security required the Storage account to block public access. A Consumption Logic App that processed uploaded JSON files `[Confirm: what the files were and who used them]` started failing with 403 errors once the firewall was turned on.
- **Task:** Keep the Storage account locked down and make the Logic App work again, without moving to a more expensive plan or storing keys. `[Confirm: your role and the deadline]`
- **Action:** I turned on the Logic App's system-assigned managed identity, gave it the Storage Blob Data Contributor role on the account, switched the blob connection from access key to managed identity authentication, and added a resource instance rule for `Microsoft.Logic/workflows` limited to that one Logic App. I unticked the trusted services exception so only named resources could pass. I tested with a sample upload and checked the run history.
- **Result:** The Logic App worked again with the firewall on, no access keys were needed, and only that one Logic App plus the approved VNet could reach the account. `[Confirm: number of workflows fixed, time to fix, any audit finding closed]`
- **Lesson:** For multi-tenant PaaS services that cannot join a VNet, use identity-based network rules (resource instance rules) instead of chasing IP addresses.

## Interview Questions

<details><summary>Q1. [Basic] Give me a two-minute overview of this scenario.</summary>

**Answer:**

Our Storage account had to be closed to the public internet, so we set it to "selected networks". A Consumption Logic App read JSON files from that account using a blob trigger, and it immediately started failing with 403 errors, because a Consumption Logic App runs in Microsoft's shared environment and is not part of our VNet. I fixed it in four steps: turn on the Logic App's system-assigned managed identity, give it the Storage Blob Data Contributor role, add a resource instance rule on the Storage firewall for that exact Logic App, and switch the blob connection to managed identity authentication. Now the account stays locked down and the Logic App works without any access keys.

</details>

<details><summary>Q2. [Basic] Why can't you just add the Logic App's VNet to the Storage firewall?</summary>

**Answer:**

A **Consumption** Logic App has no VNet. It runs on shared, multi-tenant infrastructure and does not support VNet integration. Only **Logic App Standard** can integrate with a VNet. The VNet rule in this setup is for other clients (VMs, Standard Logic Apps, Function Apps) that really sit in that subnet.

</details>

<details><summary>Q3. [Basic] What is a resource instance rule on a Storage account?</summary>

**Answer:**

It is a Storage firewall rule that lets a **specific Azure resource** through, based on its **system-assigned managed identity**, even though the resource is not in your VNet and has no fixed IP. You choose the resource type (for example `Microsoft.Logic/workflows`) and the instance, resource group, or subscription. The resource still needs an RBAC role to actually read or write data; the rule only passes the network check.

</details>

<details><summary>Q4. [Intermediate] Why did you untick "Allow trusted Microsoft services to access this resource"?</summary>

**Answer:**

That exception lets a whole list of Azure services through the firewall, which is broader than needed. The resource instance rule already allows our one Logic App. Unticking the exception follows least privilege, and it also proves the access really comes from the resource instance rule and not from a broad bypass. If another service later needs that exception (for example Azure Backup or Event Grid in some setups), we add it back on purpose.

</details>

<details><summary>Q5. [Intermediate] Why Storage Blob Data Contributor and not Contributor?</summary>

**Answer:**

**Contributor** is a **control-plane** role: it can manage the Storage account (settings, keys) but does not by itself grant blob data access through Entra ID. **Storage Blob Data Contributor** is a **data-plane** role: it can read, write, and delete blobs. For a Logic App that only reads files, **Storage Blob Data Reader** is even better (least privilege). Assign it at the container scope if the Logic App needs only one container.

</details>

<details><summary>Q6. [Intermediate] You did all the steps, but the Logic App still gets 403. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

1. **Read the error code** in the run history:
   - `AuthorizationFailure` = blocked by the **network** rules. Check the resource instance rule points to the right Logic App and tenant.
   - `AuthorizationPermissionMismatch` = network passed but **RBAC** is missing. Check the role assignment and scope.
2. **Check the connection's authentication type.** If the blob connection uses an access key, the managed identity and resource instance rule are not used. Recreate it with **Logic Apps Managed Identity**.
3. **Check the identity type.** Resource instance rules work with the **system-assigned** identity.
4. **Wait for propagation.** New role assignments can take a few minutes to apply.
5. **Check other rules:** an Azure Policy that sets public network access to Disabled overrides the "selected networks" setting.

</details>

<details><summary>Q7. [Advanced] Security now wants no public endpoint at all on the Storage account. What do you change?</summary>

**Answer:**

With **Public network access: Disabled**, resource instance rules no longer apply, so a Consumption Logic App cannot reach the account. Options:

1. Move to **Logic App Standard**, turn on **VNet integration**, and create a **private endpoint** for the Storage account's `blob` sub-resource, with the `privatelink.blob.core.windows.net` Private DNS zone linked to the VNet. Use built-in (in-app) storage connectors with managed identity.
2. Or move the processing into an **Azure Function** with VNet integration and the same private endpoint setup.

Trade-off: more cost and networking work, but no public endpoint at all, which is what strict policies require.

</details>

<details><summary>Q8. [Advanced] How would you automate this setup instead of clicking in the portal?</summary>

**Answer:**

Define it in Bicep or Terraform:

- The Logic App with `identity: { type: 'SystemAssigned' }`.
- The role assignment on the Storage account (or container) to the Logic App's `principalId`.
- The Storage account `networkAcls`: `defaultAction: 'Deny'`, `bypass: 'None'`, and `resourceAccessRules` with the Logic App's resource ID and tenant ID.
- The API connection resource using managed identity authentication.

```bicep
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
      resourceAccessRules: [
        {
          tenantId: tenant().tenantId
          resourceId: logicApp.id
        }
      ]
    }
  }
}
```

Deploy it through a pipeline so every environment gets the same locked-down setup.

</details>
