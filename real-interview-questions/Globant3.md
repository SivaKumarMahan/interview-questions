# Globant - Interview Questions (Part 3)

Real interview questions with simple, easy-to-read answers.

> Answers about your own experience (Q1, Q14, Q20-Q22, Q36) are written as project-style samples. Change the details to match what you really did, because interviewers ask follow-up questions.

---

<details><summary>Q1. What is the most challenging issue you faced in production or other environments, and how did you fix it?</summary>

Answer with **STAR**: Situation, Task, Action, Result. Pick one real story and go deep.

### Sample story: a private AKS cluster behind Azure Firewall

**Situation:** we were building AKS in a **spoke VNet**. A **UDR** sent all outbound traffic (`0.0.0.0/0`) to **Azure Firewall** in the hub, and the cluster API server was **private**. Nothing worked on the first deployment.

**Action:** I fixed it one layer at a time.

| Blocker | Symptom | Root cause | Fix |
| --- | --- | --- | --- |
| Firewall egress | Nodes `NotReady`, pods in `ImagePullBackOff` | Firewall blocked MCR, ACR and the AKS required endpoints | Added the `AzureKubernetesService` FQDN tag, MCR/ACR rules and required ports (443, 9000, 1194); confirmed in firewall logs |
| Private DNS | Private endpoints and API server resolved to public IPs, or not at all | Private DNS zones were not linked to the hub and spoke VNets | Linked `privatelink.<region>.azmk8s.io`, `privatelink.azurecr.io` and `privatelink.vaultcore.azure.net`; custom DNS forwards to `168.63.129.16`; checked with `nslookup` |
| Pipeline access | `kubectl` deploy from Azure DevOps failed | Microsoft-hosted agents cannot reach a private API server | Self-hosted agent inside the VNet, and `az aks command invoke` for emergencies |
| NSG / UDR | Intermittent timeouts | NSG rule, and asymmetric routing through the firewall | Network Watcher (IP flow verify, next hop) and NSG flow logs; corrected rules and routes |
| Subnet IPs | Scale-up failed | Azure CNI gives every pod a VNet IP; the subnet was too small | Re-planned the subnet size; moved to Azure CNI Overlay |

**Order I troubleshot in:** DNS first, then routes and firewall logs, then NSGs, then identity and permissions.

**Prevention:** firewall rules, DNS zone links and NSG/UDR config all moved into Terraform; alerts on firewall denies and node `NotReady`.

**Result:** the cluster became stable, and the same pattern was reused for the other environments without the same failures.

### Interview-ready answer

> "The hardest one was building a private AKS cluster in a spoke VNet where all egress went through Azure Firewall. Nodes stayed NotReady and images would not pull. I worked layer by layer: I allowed the AKS FQDN tag and the MCR and ACR endpoints on the firewall, linked the private DNS zones for AKS, ACR and Key Vault to the hub and spoke VNets, moved deployments to a self-hosted agent inside the VNet, fixed an asymmetric route found with Network Watcher, and resized the subnet. Then I put all of it in Terraform with alerts, so the next environments came up cleanly."

</details>

<details><summary>Q2. You set up a private endpoint, but the App Service still gets a 403 Forbidden when it reads a Key Vault secret. What might have gone wrong?</summary>

A **403** means the request **reached Key Vault and was rejected**. First read the error text: it tells you if it is a **network** problem or a **permission** problem.

| Error text | Type |
| --- | --- |
| `ForbiddenByFirewall`, "Client address is not authorized" | Network / DNS: the call did not come through the private endpoint |
| `ForbiddenByRbac`, `ForbiddenByPolicy`, "does not have secrets get permission" | Identity / permission |

### 1. Network path

- **No VNet integration** on the App Service. A private endpoint only helps **inbound to Key Vault**; the app's **outbound** calls need VNet integration, or they go over the internet and hit the vault firewall.
- **DNS returns the public IP:** the `privatelink.vaultcore.azure.net` zone is missing, not linked to the VNet the app uses, or has no A record. With custom DNS (hub-and-spoke), it must forward to `168.63.129.16` or a DNS Private Resolver.
- **Route All is off** (`vnetRouteAllEnabled` / `WEBSITE_VNET_ROUTE_ALL`), so some traffic does not use the VNet. Or an NSG, UDR or firewall blocks 443 to the private endpoint subnet.
- **Key Vault references** (`@Microsoft.KeyVault(...)`) resolve through the VNet only when the app's outbound traffic is routed through the VNet.
- The private endpoint connection is still **Pending**, not **Approved**.

### 2. Identity and permissions

- **Managed identity not enabled**, or the wrong one. A user-assigned identity must be set as `keyVaultReferenceIdentity`.
- **No role or access policy**: RBAC needs **Key Vault Secrets User**; the access policy model needs **Get** on secrets.
- **Permission model mismatch** (very common): the vault uses **Azure RBAC**, but someone added an **access policy**, or the other way round.
- Role assigned at the wrong scope, or RBAC has not propagated yet (a few minutes).

### 3. Other causes

The secret is disabled or expired, the reference syntax is wrong, or an Azure Policy or cross-tenant setting blocks access.

### How I troubleshoot

```bash
# From the Kudu / SSH console of the App Service
nslookup kv-prod.vault.azure.net        # must return a private IP like 10.x.x.x
tcpping kv-prod.vault.azure.net:443     # (Windows Kudu) or: curl -v https://kv-prod.vault.azure.net
```

```kusto
// Key Vault diagnostic logs: who called, from where, with what result
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where httpStatusCode_d == 403
| project TimeGenerated, OperationName, CallerIPAddress, identity_claim_oid_g, ResultSignature, ResultDescription
| order by TimeGenerated desc
```

- If `CallerIPAddress` is a **public IP**, it is a network/DNS problem.
- If it is a **private IP**, it is an identity/permission problem.
- In the App Service **Environment variables** blade, each Key Vault reference shows its status and error.

### Interview-ready answer

> "A 403 means Key Vault received the call and rejected it, so I read the error first. ForbiddenByFirewall means the traffic did not come through the private endpoint: usually VNet integration is missing on the App Service, Route All is off, or the privatelink.vaultcore.azure.net zone is not linked, so DNS returns the public IP. ForbiddenByRbac means the identity is wrong: managed identity not enabled, no Key Vault Secrets User role, or the vault uses RBAC while someone set an access policy. I check nslookup from Kudu and the caller IP in the Key Vault logs to tell the two apart quickly."

</details>

<details><summary>Q3. Apart from configuring the Storage Account with GRS, do we have to do anything ourselves to access the data in a regional outage?</summary>

**Yes.** GRS only **keeps a copy** of the data in the paired region. By default:

- the secondary copy is **not readable**, and
- the account **does not fail over automatically**.

### What you need to do

| Action | Why |
| --- | --- |
| Use **RA-GRS** or **RA-GZRS** if the app must **read** during an outage | Gives a read-only secondary endpoint: `<account>-secondary.blob.core.windows.net` |
| **Change the app** to use the secondary endpoint | Endpoints and connection strings do not switch by themselves; SDKs can retry reads against a secondary location |
| **Start the failover yourself** for write access | **Customer-managed failover** (portal, CLI, PowerShell). Microsoft-managed failover happens only in extreme cases |
| Check **Last Sync Time** first | Replication is asynchronous, so writes after the last sync can be lost (RPO is usually under 15 minutes, not guaranteed) |
| **Re-enable geo-redundancy** after an unplanned failover | After failover the account is **LRS** in the new primary; you must turn GRS on again (re-sync can take time). A *planned* failover keeps geo-redundancy |
| Prepare **networking** in the secondary region | Private endpoints, private DNS records and firewall rules for the secondary region, or the app cannot reach it |
| Check **access** | SAS tokens, keys and managed identity roles still work after failover |
| **Test it** | Run a failover drill in non-prod and measure RTO and RPO |

```bash
# See replication status
az storage account show -n stappprod -g rg-app --expand geoReplicationStats \
  --query geoReplicationStats

# Customer-managed (unplanned) failover
az storage account failover -n stappprod -g rg-app
```

### Interview-ready answer

> "Yes. GRS only keeps a copy in the paired region; the secondary is not readable and there is no automatic failover. If the app needs to read during an outage I use RA-GRS or RA-GZRS and code the app to use the secondary endpoint. For writes I trigger a customer-managed failover myself, after checking Last Sync Time because replication is asynchronous. After an unplanned failover the account becomes LRS, so I re-enable GRS. I also prepare private endpoints and DNS in the secondary region and test the failover in a drill."

</details>

<details><summary>Q4. Have you worked with Azure Front Door and Traffic Manager?</summary>

Yes. Both send users to the right region, but they work at **different layers**.

- **Traffic Manager** is a **DNS-based** load balancer. It only answers the DNS query; the client then connects **directly** to the endpoint.
- **Front Door** is a **global layer-7 (HTTP/HTTPS) reverse proxy** at Microsoft's edge. Traffic actually flows **through** it.

| | Traffic Manager | Azure Front Door |
| --- | --- | --- |
| Layer | DNS | HTTP/HTTPS proxy at the edge |
| Protocols | Any (HTTP, TCP, UDP, …) | HTTP/HTTPS only |
| Failover speed | Depends on DNS **TTL** and client caching | Fast, health-probe based, no DNS wait |
| WAF | No | **Yes** (Premium has managed rule sets and bot protection) |
| TLS offload, caching, compression | No | Yes |
| URL path routing, rewrite | No | Yes |
| Private origins | No | **Private Link** to origins (Premium) |
| Routing methods | Priority, weighted, performance, geographic, multivalue, subnet | Latency-based, priority, weighted, session affinity |

### Where I used them

- **Front Door Premium with WAF** in front of two regional App Services (or Application Gateways), with health probes, for a multi-region web app. Origins locked down so they only accept traffic from Front Door (`AzureFrontDoor.Backend` service tag + `X-Azure-FDID` header check, or Private Link).
- **Traffic Manager** for a **non-HTTP** workload, and as a simple DNS failover between two regions.

**Note:** Front Door is **global**, Application Gateway is **regional**. They are often used together: Front Door at the edge, Application Gateway inside each region.

### Interview-ready answer

> "Yes. Traffic Manager is DNS-based: it returns the healthy endpoint's address and the client connects directly, so it supports any protocol but failover depends on DNS TTL. Front Door is a global HTTP/S reverse proxy at the Microsoft edge with WAF, TLS offload, caching, path routing and fast health-probe failover. I used Front Door Premium with WAF in front of App Services in two regions, locked the origins to Front Door, and used Traffic Manager for a non-HTTP workload."

</details>

<details><summary>Q5. My app is behind Application Gateway with WAF and the default Microsoft rules. One default rule blocks my app. How do you unblock the application?</summary>

**Do not turn WAF off**, and do not switch the whole policy to Detection permanently. Find the exact rule, confirm it is a **false positive**, and make the **smallest** change.

### Steps

**1. Find the rule in the firewall logs** (diagnostic settings → Log Analytics):

```kusto
AzureDiagnostics
| where Category == "ApplicationGatewayFirewallLog"
| where action_s in ("Blocked", "Matched")
| project TimeGenerated, clientIp_s, requestUri_s, ruleId_s, Message,
          details_message_s, details_data_s
| order by TimeGenerated desc
```

This gives the **rule ID** (for example `942130`, a SQL injection rule) and the **matched variable** (for example the post argument `comment`).

**2. Confirm it is a false positive:** the request is legitimate (for example a JSON field with special characters). Test in non-prod if needed.

**3. Fix it, narrowest option first:**

| Option | What it does | When |
| --- | --- | --- |
| **Exclusion** (preferred) | Skips inspection of **one request field** (header, cookie, query arg, post arg) **for that rule only**. The rule still checks everything else | A specific field triggers the rule |
| **Disable the single rule** (rule override) | Turns off that **one rule ID** in the managed rule set, or changes its action to **Log** | The rule is wrong for the whole app |
| **Custom allow rule** | Allows a trusted path or source IP before managed rules run | Rarely; very wide |
| Per-site / per-URI WAF policy | A separate policy for one listener or path | Only that app or path needs the change |

### Example in Terraform

```hcl
resource "azurerm_web_application_firewall_policy" "waf" {
  name                = "waf-app-prod"
  resource_group_name = "rg-network"
  location            = "eastus"

  policy_settings {
    mode    = "Prevention"
    enabled = true
  }

  managed_rules {
    # Option 1: exclusion - don't inspect the "comment" field for rule 942130 only
    exclusion {
      match_variable          = "RequestArgNames"
      selector_match_operator = "Equals"
      selector                = "comment"
      excluded_rule_set {
        type    = "Microsoft_DefaultRuleSet"
        version = "2.1"
        rule_group {
          rule_group_name = "SQLI"
          excluded_rules  = ["942130"]
        }
      }
    }

    managed_rule_set {
      type    = "Microsoft_DefaultRuleSet"
      version = "2.1"

      # Option 2: override - disable one rule
      rule_group_override {
        rule_group_name = "SQLI"
        rule {
          id      = "942130"
          enabled = false
        }
      }
    }
  }
}
```

**4. Test and monitor:** retest the app, and watch the logs for new blocks.

**5. Govern:** keep the exclusion in IaC, record the rule ID and reason, get security approval, and review it regularly.

### Interview-ready answer

> "I would not disable WAF. I check the ApplicationGatewayFirewallLog in Log Analytics to get the rule ID and the matched field, and confirm it is a false positive. Then I make the narrowest change: preferably a WAF policy exclusion for just that field, scoped to that rule, so the rule still protects everything else. If that is not enough, I override and disable only that one rule ID in the managed rule set. I do it in Terraform, document why, get security sign-off and keep monitoring the logs."

</details>

<details><summary>Q6. Have you worked with Azure Monitor? Have you written any workbooks?</summary>

Yes. I used Azure Monitor **metrics, Log Analytics, Application Insights and alerts** for App Service, AKS and Key Vault, and built **workbooks** with KQL so the team had one view instead of many portal blades.

**Workbook** = an interactive report in the portal: parameters, KQL queries, charts, grids and text in one page.

### Workbooks I built

| Workbook | What it showed | Data source |
| --- | --- | --- |
| App Service health | Requests, failures, p95 response time, 4xx/5xx trend | Application Insights |
| Key Vault access | 401/403 counts, top callers, operations by identity | Key Vault diagnostic logs |
| AKS and infrastructure | Node CPU/memory, pod restarts, disk usage with threshold colours | Container Insights, VM metrics |
| SLO report | Availability and error budget left per service | Application Insights |

### Example KQL (App Service failures and latency)

```kusto
requests
| where timestamp > ago(24h)
| summarize Total = count(),
            Failed = countif(success == false),
            P95ms = percentile(duration, 95)
          by bin(timestamp, 15m), cloud_RoleName
| extend FailurePct = round(100.0 * Failed / Total, 2)
```

### Good practices

- **Parameters** at the top (subscription, resource group, time range) so one workbook serves every environment.
- **Conditional formatting** (green/amber/red) on thresholds.
- Workbook stored as **ARM/Bicep/Terraform** (`azurerm_application_insights_workbook`) so it is deployed the same way everywhere.
- **Alerts** with action groups are for notification; the workbook is for investigation. Each alert links to the workbook.

### Interview-ready answer

> "Yes. I used Azure Monitor metrics, Log Analytics, Application Insights and alerts with action groups. I built workbooks with KQL, for example an App Service health workbook with failures and p95 latency, a Key Vault access workbook showing 403s by caller, and an SLO report. I add parameters for subscription and time range so one workbook works for all environments, and I deploy them as code. Alerts notify us, and the alert links to the workbook for investigation."

</details>

<details><summary>Q7. Have you worked on SRE topics like SLOs, SLIs and error budgets? How do you calculate the error budget?</summary>

Yes. Short definitions (more in Q15):

- **SLI**: what you measure, for example % of successful requests.
- **SLO**: the target for the SLI, for example 99.9% over 30 days.
- **Error budget**: how much failure the SLO still allows.

### Formula

```text
Error budget = 100% - SLO
```

### Time-based example: 99.9% availability over 30 days

- Minutes in 30 days = 30 × 24 × 60 = **43,200**
- Error budget = 0.1% × 43,200 = **43.2 minutes** of allowed downtime
- An incident causes 30 minutes of downtime → used 30 / 43.2 ≈ **69%**, about **13.2 minutes left**

| SLO (30 days) | Error budget | Allowed downtime |
| --- | --- | --- |
| 99% | 1% | 7.2 hours |
| 99.9% | 0.1% | 43.2 minutes |
| 99.95% | 0.05% | 21.6 minutes |
| 99.99% | 0.01% | 4.32 minutes |

### Request-based example

SLO 99.9% success, 10,000,000 requests in a month → budget = **10,000 failed requests**. If 7,500 have failed, **75%** of the budget is used.

### Burn rate

```text
Burn rate = actual error rate / allowed error rate
```

- Burn rate **1** uses exactly the whole budget by the end of the window.
- Burn rate **10** empties it in one tenth of the window (3 days of a 30-day window) → page the on-call.
- Common practice: **fast-burn** alert (high burn rate over 1 hour) pages; **slow-burn** alert (over 6-24 hours) creates a ticket.

### Interview-ready answer

> "Yes. The error budget is 100% minus the SLO. For 99.9% availability over 30 days, that is 0.1% of 43,200 minutes, so 43.2 minutes of downtime. If an incident takes 30 minutes, we have used about 69% of the budget. For request-based SLOs, 99.9% of 10 million requests gives 10,000 allowed failures. I alert on burn rate: a fast burn pages the on-call, a slow burn creates a ticket, and when the budget is used up we pause risky releases and focus on reliability."

</details>

<details><summary>Q8. A pipeline variable and a variable group variable have the same name. If both are used in the same pipeline, which one does the pipeline use?</summary>

It depends on the **pipeline type** and **where** each is defined.

### YAML pipelines

Variables are processed **in the order they are listed** under `variables:`. At the same scope, **the one defined last wins**.

```yaml
variables:
  - group: my-variable-group    # defines env = dev
  - name: env
    value: prod                 # listed later -> env = prod

# Reverse the order and the variable group value wins
```

Other YAML rules:

- A **narrower scope wins**: job-level > stage-level > pipeline (root) level.
- Variables in the YAML file **override** variables set in the pipeline **UI** (Edit → Variables) with the same name.
- A value set at **queue time** (only if "Let users override this value when running this pipeline" is ticked) overrides the UI value.
- A script with `##vso[task.setvariable variable=env]value` changes it for the **later steps**.

### Classic pipelines

A variable defined **directly in the pipeline** takes precedence over a variable with the same name from a **linked variable group**. In Classic release pipelines, **stage-scoped** variables beat **release-scoped** ones.

### In the question

Both have the **same name and the same value**, so the result is the same either way. But it is still bad practice: if one value changes later, it becomes confusing which one is used.

**What I do:** keep each variable in **one place**. Shared and secret values in a variable group (linked to Key Vault); pipeline-only values in the pipeline.

### Interview-ready answer

> "In YAML it depends on order: variables are processed top to bottom, so whichever is listed last at the same scope wins, and job-level beats stage-level beats root level. In Classic pipelines the pipeline's own variable takes precedence over the variable group. Here the values are the same, so the result is identical, but I would remove the duplicate and keep each variable in one place, because the day someone changes one of them, nobody will know which value is used."

</details>

<details><summary>Q9. Can I create Storage Accounts with the same name in two different subscriptions?</summary>

**No.** A storage account name must be **globally unique across all of Azure**, not just per subscription or tenant.

**Naming rules:**

- **3 to 24 characters**
- **Lowercase letters and numbers only** (no hyphens, no capitals)

If the name is already used by anyone, anywhere, creation fails with `StorageAccountAlreadyTaken` / "The storage account named X is already taken".

```bash
az storage account check-name --name stappprod001
# { "nameAvailable": false, "reason": "AlreadyExists", ... }
```

### Interview-ready answer

> "No. Storage account names are globally unique across all of Azure, not per subscription. They must be 3 to 24 characters, lowercase letters and numbers only. If someone else in any tenant already uses the name, the deployment fails, so I check availability with `az storage account check-name` and use a naming convention with a unique suffix."

</details>

<details><summary>Q10. Why must the Storage Account name be unique? Why doesn't this apply to other resources?</summary>

### Why storage names are unique

The name becomes part of a **public DNS hostname**:

```text
https://<name>.blob.core.windows.net
https://<name>.file.core.windows.net
https://<name>.queue.core.windows.net
https://<name>.table.core.windows.net
https://<name>.dfs.core.windows.net
```

DNS names must be unique worldwide, so the name must be too.

### Why most other resources are not

Most resources are identified by their **resource ID**, which already contains the subscription and resource group:

```text
/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Network/virtualNetworks/vnet-app
```

So two subscriptions (or two resource groups) can both have a VNet called `vnet-app`, because the full IDs are different and the VNet has no public DNS name.

### Resources that are also globally unique (same reason: public DNS)

| Resource | Hostname |
| --- | --- |
| App Service / Function App | `<name>.azurewebsites.net` (new apps can use a unique default hostname with a random hash) |
| Key Vault | `<name>.vault.azure.net` |
| Container Registry | `<name>.azurecr.io` |
| Azure SQL logical server | `<name>.database.windows.net` |
| Cosmos DB account | `<name>.documents.azure.com` |
| Service Bus / Event Hubs namespace | `<name>.servicebus.windows.net` |

**Tip:** naming convention like `st<app><env><region><suffix>` (for example `stpaymentsprodeus01`), and a random suffix in Terraform (`random_string`) for shared modules.

### Interview-ready answer

> "Because the storage account name becomes part of a public DNS name like name.blob.core.windows.net, and DNS names must be unique worldwide. Most other resources, like VNets or VMs, are identified by a resource ID that includes the subscription and resource group, so the same name can exist in different places. Any resource that gets a public hostname, such as Key Vault, ACR, App Service or SQL server, has the same global uniqueness rule."

</details>

<details><summary>Q11. The client's app depends on a Storage Account and must stay up even if the primary Azure region goes down. How would you design it?</summary>

First agree the **RTO** (how long we can be down) and **RPO** (how much data we can lose) with the client. They decide how much redundancy, and cost, is needed.

### Architecture

```text
                      Users
                        |
               Azure Front Door (WAF, health probes)
                 /                         \
     Region A (primary)                Region B (secondary / paired)
     App Service / AKS                 App Service / AKS (same IaC)
     Key Vault A                       Key Vault B
     Private endpoints + DNS           Private endpoints + DNS
            \                               /
             Storage account: RA-GZRS  -----> read-only secondary in Region B
             (zone-redundant in A,             (customer-managed failover for writes)
              async copy to B)
     Database: SQL failover group / Cosmos DB multi-region
```

### Storage layer

- **RA-GZRS**: zone-redundant in the primary region (survives a zone failure) **plus** a readable copy in the paired region. Use **RA-GRS** if the region has no zones.
- **Soft delete, versioning, point-in-time restore** for blobs: protect against deletion or corruption (replication copies mistakes too).
- **Object replication** to a separate account in region B if you need control over what is replicated, or a writable account in each region.

### Application layer

- App deployed in **two regions** from the **same IaC** (active-active or active-passive).
- **Azure Front Door** (HTTP) or **Traffic Manager** (DNS) with health probes routes users away from the failed region.
- App reads from the **secondary endpoint** when the primary fails (SDK retry with secondary location), or switches the storage endpoint by configuration after failover.

### Supporting services

- **Key Vault** in each region with the same secrets and roles.
- **Private endpoints and private DNS** in both regions.
- Database with geo-replication: **SQL auto-failover groups** or **Cosmos DB multi-region writes**.
- **Managed identities** and roles set up in both regions.

### Failover runbook

1. Front Door probes and Azure Monitor / Service Health alerts detect the outage.
2. Front Door moves traffic to region B automatically.
3. Storage: the app reads from the secondary; if writes are needed, we check **Last Sync Time** and start **customer-managed failover**.
4. After region A recovers: re-enable geo-redundancy, re-sync, and **fail back** in a maintenance window.

### Business continuity

- Written **DR runbook** with owners; **DR drills** at least twice a year, measuring real RTO/RPO.
- **Backups** outside the primary region; IaC to rebuild quickly.
- **Trade-off:** active-active is fastest but costs more; active-passive (warm standby) is cheaper with a longer RTO.

### Interview-ready answer

> "I would first agree RTO and RPO. Then I'd use RA-GZRS for the storage account, so it survives a zone failure and has a readable copy in the paired region, plus soft delete and versioning. The app runs in two regions from the same IaC, behind Front Door with health probes, so traffic moves automatically. The app reads from the secondary endpoint during an outage, and if we need writes I start a customer-managed failover after checking Last Sync Time. Key Vault, private endpoints and DNS exist in both regions, the database uses failover groups, and we test it all with regular DR drills."

</details>

<details><summary>Q12. The app team wants an application on a single VM, and users will access it through that VM. What are your next steps and action items?</summary>

First, **challenge the single VM**: it is a **single point of failure**. Then build it properly if the business accepts that risk.

### 1. Requirements

- Users: **internal or internet**? How many? Which ports and protocols?
- **OS**, app stack, CPU/memory/disk needs, licensing.
- **Availability** need: a single VM's SLA is **99.9%** only with Premium SSD/Ultra disks on all disks (lower with Standard disks). Is that enough? What are the RTO/RPO?
- Data: does the VM store data, or does it use a database / storage?
- Compliance, budget, environment (dev/test/prod).

### 2. Design and build (with IaC: Terraform/Bicep)

| Area | Action |
| --- | --- |
| **Networking** | VNet and subnet from the IP plan; **NSG** allowing only required ports; **no public IP on the VM** |
| **User access** | Internet: **Application Gateway with WAF** (or Front Door) in front, with TLS certificate and DNS name. Internal: Load Balancer or private DNS name |
| **Admin access** | **Azure Bastion** or JIT access; no open RDP/SSH to the internet |
| **Identity** | Entra ID login for the VM, **managed identity** for the app to reach Key Vault, storage or DB |
| **Secrets** | Key Vault, not in config files |
| **Disks and size** | Right VM size, Premium SSD, data on a separate data disk |
| **Security** | Hardened image, **encryption at host / disk encryption**, Defender for Servers, antimalware |
| **Patching** | **Azure Update Manager** schedule |
| **Backup** | **Azure Backup** policy, and test a restore |
| **Monitoring** | Azure Monitor Agent, **VM Insights**, Log Analytics, alerts on CPU, memory, disk, heartbeat; app health probe |
| **Governance** | Tags (owner, env, cost centre), naming, Azure Policy, budget alerts |
| **Deployment** | App deployed by pipeline (or VM extension / Ansible), not by hand |

### 3. Recommend a more resilient option

- **Two VMs** across **availability zones** behind a Load Balancer / App Gateway (**99.99%** SLA), or a **VM Scale Set**.
- Or move the app to **PaaS** (App Service, Container Apps) if it fits.
- At minimum: **Azure Site Recovery** to another region for DR.

### 4. Handover

Document the architecture, runbook, access, backup and restore steps; agree ownership and on-call.

### Interview-ready answer

> "First I'd gather requirements: internal or external users, ports, OS, sizing, data, and the RTO and RPO, and I'd point out that one VM is a single point of failure with a 99.9% SLA at best. Then I'd build it with Terraform: VNet and NSG, no public IP, an Application Gateway with WAF and TLS in front for users, Bastion for admin access, managed identity and Key Vault for secrets, disk encryption, Defender, Update Manager for patching, Azure Backup and VM Insights with alerts. I'd recommend two VMs across zones or a scale set, or at least Site Recovery for DR."

</details>

<details><summary>Q13. Have you worked with Classic pipelines? You need to run a Key Vault task against 10-20 Key Vaults. Build or Release pipeline, and how do you run it in parallel?</summary>

Yes. I would choose a **Release pipeline**. Build pipelines are for compiling code and producing artifacts; Release pipelines are made to run the **same work against many targets**, each with its own variables, service connection and approvals.

### Option 1: Classic Release with parallel stages

1. Create **one stage** with the task (Azure Key Vault task, or Azure CLI/PowerShell), using variables like `$(vaultName)`, not hard-coded names.
2. **Clone** the stage for each vault.
3. Set each stage's **trigger to "After release"** (not "After stage"), so **all stages start together**.
4. Use **stage-scoped variables**: `vaultName`, `resourceGroup`, and the service connection per stage.
5. Add **pre-deployment approvals** only on production vaults.

### Option 2: one stage, multi-configuration (less clicking)

In the agent job → **Execution plan → Parallelism → Multi-configuration**:

- **Multipliers:** `vaultName`
- Variable `vaultName` = `kv-app1,kv-app2,kv-app3,...`
- **Maximum number of agents:** for example 10

The job runs once per vault, on several agents at the same time.

### Option 3 (better long-term): multi-stage YAML with a list

```yaml
parameters:
  - name: vaults
    type: object
    default: [kv-app1, kv-app2, kv-app3]

stages:
  - stage: KeyVaultTasks
    jobs:
      - ${{ each vault in parameters.vaults }}:
          - job: kv_${{ replace(vault, '-', '_') }}
            pool:
              vmImage: ubuntu-latest
            steps:
              - task: AzureCLI@2
                inputs:
                  azureSubscription: sc-keyvault-ops
                  scriptType: bash
                  scriptLocation: inlineScript
                  inlineScript: |
                    echo "Running against ${{ vault }}"
                    az keyvault secret list --vault-name ${{ vault }} -o table
```

Jobs in one stage run **in parallel** by default. Adding a vault = adding one name to the list. (A `strategy: matrix` with `maxParallel` also works.)

### Prerequisites

- Enough **parallel jobs** in the organization / agents in the pool. With 1 parallel job, everything queues one after another.
- A service connection (preferably **workload identity federation**) with the right **RBAC role** on every vault.
- **Self-hosted agents** in the VNet if the vaults use private endpoints or firewalls.
- `continueOnError` or separate jobs, so one failing vault does not stop the others; check per-job logs.

### Interview-ready answer

> "I'd use a Release pipeline, because it's meant to run the same deployment against many targets with their own variables and approvals. In Classic I'd create one stage with variables for the vault name, clone it per vault and set every stage to trigger after release so they all run in parallel, or use a multi-configuration job with vaultName as the multiplier and a max agent count. Today I'd do it in YAML with an `each` loop over a list of vaults, which creates parallel jobs. Parallel job capacity, RBAC on each vault and self-hosted agents for private vaults are the prerequisites."

</details>

<details><summary>Q14. What common SRE issues have you handled?</summary>

| Area | Typical issues | How I fixed them |
| --- | --- | --- |
| **Availability** | 5xx spikes after a release, failed health probes | Roll back or swap slots back first, then root cause |
| **Resource exhaustion** | High CPU/memory, full disks, pods `OOMKilled` / `CrashLoopBackOff` | Right-sizing, requests/limits, HPA and cluster autoscaler, disk clean-up and alerts |
| **Networking and DNS** | Private endpoint and firewall problems, DNS resolving to public IPs, expired or wrong TLS certificates | DNS zone links, firewall rules, certificate automation and expiry alerts |
| **Identity and secrets** | 401/403 from Key Vault, expired client secrets | Managed identities, correct RBAC, expiry alerts and rotation |
| **Pipelines** | Failed deployments, agent capacity, wrong variables | Retries, approvals, parameterised templates, more agents |
| **Dependencies** | Slow database or third-party API | Timeouts, retries with backoff, circuit breakers, caching |
| **Alert noise** | Too many alerts, real ones ignored | Alert tuning, severity levels, dynamic thresholds, alert processing rules |
| **Cost** | Idle and oversized resources | Tagging, right-sizing, schedules, reservations |

**My incident loop:** detect → triage → **mitigate first** → find root cause → **blameless post-incident review** with action items.

### Interview-ready answer

> "I've handled 5xx spikes after releases, which I mitigate by rolling back or swapping slots first; resource problems like OOMKilled pods and full disks, fixed with right-sizing and autoscaling; networking and DNS issues with private endpoints and expired certificates; Key Vault 403s and expired secrets, fixed with managed identities and rotation; pipeline failures; and noisy alerts. For each I follow the same loop: mitigate first, find the root cause, then a blameless review with action items so it doesn't repeat."

</details>

<details><summary>Q15. Explain the SRE goals: SLI, SLO, SLA and error budget.</summary>

| Term | Meaning | Example |
| --- | --- | --- |
| **SLI** (Service Level Indicator) | A **measurement** of service health | % of successful requests; % of requests under 300 ms |
| **SLO** (Service Level Objective) | Our **internal target** for an SLI over a time window | 99.9% of requests succeed over 30 days |
| **SLA** (Service Level Agreement) | A **contract** with the customer, with penalties (for example service credits) if missed | 99.5% monthly availability |
| **Error budget** | Allowed unreliability = **100% − SLO** | 0.1% of requests may fail (43.2 min/month) |

### How they connect

```text
SLI (what we measure) --> compared with --> SLO (our target)  -->  tighter than  -->  SLA (customer promise)
                                              |
                                        Error budget = 100% - SLO
```

- The **SLO is stricter than the SLA**, so we get a warning before breaching the contract.
- The **error budget** turns reliability into a **decision tool** between speed and stability:
  - **Budget left:** ship features, take reasonable release risk.
  - **Budget nearly used:** freeze risky releases, focus on reliability work.
- **Burn-rate alerts** tell us how fast we are using the budget (calculation in Q7).

### Good SLIs

User-facing, measured where users feel it: **availability** (successful requests / total), **latency** (p95/p99), **error rate**, **freshness** for data pipelines.

### Interview-ready answer

> "An SLI is what we measure, like the percentage of successful requests. An SLO is our internal target for it, like 99.9% over 30 days. An SLA is the contract with the customer, with penalties, and it's always looser than the SLO so we get early warning. The error budget is 100% minus the SLO. It balances speed and reliability: while we have budget we ship, and when it's nearly used we pause risky changes and fix reliability."

</details>

<details><summary>Q16. How do you calculate MTTR?</summary>

**MTTR (Mean Time To Restore/Recover)** = the average time to restore service after an incident.

```text
MTTR = Total downtime across incidents / Number of incidents
```

Downtime is measured from when the incident **started (or was detected)** until service was **restored** for users, not until the root cause was fixed.

### Example

Three incidents lasted 30, 45 and 15 minutes.

- Total = 90 minutes
- MTTR = 90 / 3 = **30 minutes**

### Related metrics

| Metric | Meaning |
| --- | --- |
| **MTTD** (detect) | Start of the problem → alert/detection |
| **MTTA** (acknowledge) | Alert → an engineer acknowledges |
| **MTTR** (restore) | Start → service restored |
| **MTBF** (between failures) | Average uptime between incidents |

MTTR is also one of the four **DORA** metrics (as "failed deployment recovery time").

### Interview-ready answer

> "MTTR is total downtime divided by the number of incidents. If three incidents lasted 30, 45 and 15 minutes, that's 90 minutes over 3, so an MTTR of 30 minutes. I measure from when the impact started until users are restored, not until the root cause is fixed, and I also track MTTD and MTTA, because detection and acknowledgement are often the biggest part."

</details>

<details><summary>Q17. How do you reduce MTTR?</summary>

Reduce each part of the incident timeline: **detect → acknowledge → diagnose → mitigate**.

| Stage | How I reduced it |
| --- | --- |
| **Detect faster** | Alerts on **symptoms** users feel (error rate, latency, availability tests), with good thresholds |
| **Acknowledge faster** | Clear on-call rota, action groups to Teams/phone/PagerDuty, severity levels |
| **Diagnose faster** | **Runbooks** and dashboards/workbooks per service, distributed tracing (Application Insights), correlated logs, recent-change view |
| **Mitigate first, fix later** | **Rollback**, slot swap back, scale out, **feature flags**, failover, before root-cause analysis |
| **Automate** | Auto-restart, autoscaling, self-healing probes, automated rollback on failed smoke tests, runbook automation |
| **Learn** | Blameless **post-incident reviews** with tracked action items; game days to practise |

### Interview-ready answer

> "I reduce MTTR at every stage. We detect faster with alerts on user-facing symptoms and availability tests, acknowledge faster with a clear on-call rota and action groups, and diagnose faster with runbooks, workbooks and tracing. Most importantly, we mitigate first: roll back, swap slots, scale out or flip a feature flag, then find the root cause. Automation like self-healing probes and automatic rollback removes human delay, and post-incident reviews stop repeats."

</details>

<details><summary>Q18. How do alerts help reduce incident time and production downtime?</summary>

Detection and diagnosis are usually the **longest** parts of an incident. Good alerts shorten both.

- **Faster detection:** Azure Monitor alerts notify the on-call within minutes, **before users report it**.
- **Right people, right context:** **action groups** send email, Teams, SMS or paging; the alert includes the resource, the query and links to the **runbook** and **workbook**.
- **Less noise:** severity levels, **dynamic thresholds**, and **alert processing rules** (suppress during maintenance, route by team), so real alerts get attention.
- **Quicker diagnosis:** log alerts with KQL point to where the failure is: app, dependency or network.
- **Auto-remediation:** alerts trigger **Logic Apps, Automation runbooks or Functions** to restart, scale or clear disk.
- **Proactive:** alerts on trends (disk 80%, certificate expiry) prevent the outage completely.

### Example: alert on 5xx rate (log alert query)

```kusto
requests
| where timestamp > ago(5m)
| summarize Total = count(), Errors = countif(toint(resultCode) >= 500)
| extend ErrorPct = 100.0 * Errors / Total
| where ErrorPct > 5
```

### Interview-ready answer

> "Alerts cut the time to detect and diagnose, which is usually most of the downtime. Azure Monitor alerts reach the on-call engineer through action groups within minutes, with links to the runbook and workbook. I keep them actionable with severities, dynamic thresholds and alert processing rules, and some alerts trigger automation to restart or scale on their own. Trend alerts like disk at 80% or a certificate expiring in 30 days stop the incident before it happens."

</details>

<details><summary>Q19. Explain proactive monitoring and automation. How do you prevent production downtime?</summary>

**Reactive** monitoring tells you something **broke**. **Proactive** monitoring tells you it is **about to break**, and automation fixes or prevents it.

### Proactive monitoring

- Alerts on **trends**, not just failures: disk > 80%, memory growth, queue backlog, node pressure, DB DTU/CPU.
- **Certificate and secret expiry** alerts (for example 30 days before).
- **Availability tests** (synthetic checks) from Application Insights from several regions.
- **Service Health** and **Resource Health** alerts for Azure platform issues and planned maintenance.
- **Capacity and quota** checks before big releases or events.
- **SLO burn-rate** alerts.

### Automation that prevents downtime

| Automation | Example |
| --- | --- |
| **Autoscaling** | HPA, cluster autoscaler, App Service autoscale, VMSS |
| **Self-healing** | Health probes, liveness/readiness probes, App Service auto-heal |
| **Safe deployments** | Slots, blue/green, canary, approval gates, **automatic rollback** on failed smoke tests |
| **Patching** | Azure Update Manager with maintenance windows |
| **Drift prevention** | IaC only, Azure Policy, scheduled `terraform plan` for drift |
| **Secret rotation** | Key Vault rotation, managed identities (no secrets) |
| **Resilience** | Availability zones, backups, DR drills, chaos tests (Azure Chaos Studio) |

### Interview-ready answer

> "Proactive monitoring means alerting on trends before failure: disk and memory growth, queue backlog, certificate expiry, availability tests and Service Health. Then automation prevents or fixes problems: autoscaling, self-healing probes, safe deployments with slots or canary and automatic rollback, patching with Update Manager, IaC with Azure Policy to stop drift, and secret rotation. Combined with zone redundancy and DR drills, most issues are caught before users notice."

</details>

<details><summary>Q20. Explain your EKS architecture and how you manage it.</summary>

We ran EKS in a **multi-AZ VPC** with **private worker nodes**. AWS manages the **control plane**; we manage nodes, networking, add-ons and deployments.

| Layer | Design |
| --- | --- |
| **Network** | VPC across 3 AZs: public subnets (load balancers, NAT gateways), private subnets (nodes); security groups; **VPC endpoints** for ECR, S3, STS |
| **Control plane** | Managed EKS, private or restricted public endpoint, control plane logs to CloudWatch |
| **Compute** | **Managed node groups**, plus **Karpenter** or Cluster Autoscaler; Spot for non-critical; Fargate for some workloads |
| **Ingress** | **AWS Load Balancer Controller** (ALB/NLB), ACM certificates, Route 53, AWS WAF |
| **Identity** | **IRSA** or **EKS Pod Identity** for pods; **EKS access entries** (or `aws-auth`) for users; Kubernetes RBAC |
| **Images** | **ECR** with image scanning |
| **Add-ons** | VPC CNI, CoreDNS, kube-proxy, EBS/EFS CSI drivers, metrics-server |
| **Secrets** | AWS Secrets Manager / SSM via Secrets Store CSI driver or External Secrets |
| **Observability** | CloudWatch Container Insights or Prometheus + Grafana; logs with Fluent Bit |

### How we managed it

- **IaC:** Terraform for VPC, EKS and node groups, with remote state in S3 and locking.
- **Deployments:** pipeline builds the image → pushes to ECR → deploys with **Helm** (or **Argo CD** GitOps).
- **Scaling:** HPA for pods, Karpenter for nodes.
- **Upgrades:** control plane first, then add-ons, then node groups (rolling), tested in a lower environment; **PodDisruptionBudgets** protect availability.
- **Security:** least-privilege IAM, network policies, image scanning, private endpoint.
- **Cost:** right-sizing, Spot, tagging.

### Interview-ready answer

> "Our EKS ran in a three-AZ VPC with nodes in private subnets, NAT in public subnets and VPC endpoints for ECR and S3. AWS manages the control plane; we used managed node groups with Karpenter, the AWS Load Balancer Controller for ALBs, IRSA for pod permissions and access entries for users. Everything was built with Terraform, apps were deployed with Helm through the pipeline, and upgrades went control plane, then add-ons, then nodes, tested in lower environments first with PodDisruptionBudgets in place."

</details>

<details><summary>Q21. What common issues have you faced in EKS, and how did you troubleshoot them?</summary>

| Issue | Likely cause | How I troubleshot and fixed it |
| --- | --- | --- |
| **Nodes not joining** | Wrong node IAM role, missing access entry / `aws-auth` mapping, no route to the API or ECR | Checked node role, access entries, subnet routes and security groups |
| **ImagePullBackOff** | No ECR permission, no route to ECR, wrong tag | `kubectl describe pod`; node role policy, VPC endpoints or NAT, image tag |
| **Pods Pending** | Not enough CPU/memory, taints, **no free IPs** (VPC CNI uses VPC IPs) | Events in `describe pod`; scaled nodes, fixed requests, tolerations; **prefix delegation** or bigger subnets for IP exhaustion |
| **CrashLoopBackOff / OOMKilled** | App error, bad config, memory limit too low | `kubectl logs --previous`; raised limits, fixed config and probes |
| **502/504 from the ALB** | Failing target health checks, security group blocks, wrong target type | Target group health, probe path and port, security group rules |
| **AccessDenied from pods (IRSA)** | Wrong trust policy, OIDC provider, or service account annotation | Verified OIDC provider, role trust policy, annotation |
| **DNS failures** | CoreDNS overloaded or misconfigured | CoreDNS pods and logs; scaled CoreDNS, tuned config, NodeLocal DNSCache |
| **Upgrade problems** | Deprecated APIs, add-on version mismatch | API deprecation check (for example `pluto` / EKS upgrade insights), add-ons upgraded in order, staging first |

### My approach

```bash
kubectl get events -A --sort-by=.lastTimestamp
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns> --previous
kubectl get nodes -o wide && kubectl describe node <node>
```

Then network (security groups, routes, DNS), then IAM. Each fix went into a **runbook** and an **alert**.

### Interview-ready answer

> "The common ones were nodes not joining because of IAM role or access entry mapping, ImagePullBackOff from missing ECR permissions or routes, Pending pods from IP exhaustion with the VPC CNI, which we fixed with prefix delegation, OOMKilled pods, 502s from failing ALB health checks, and IRSA AccessDenied from wrong trust policies. I always start with events and describe, then logs, then network and IAM, and each fix becomes a runbook entry and an alert."

</details>

<details><summary>Q22. What is Azure Container Apps, and what have you done with it?</summary>

**Azure Container Apps (ACA)** is a **serverless container platform**. It runs containers on managed infrastructure (built on **Kubernetes, KEDA, Dapr and Envoy**), without you managing a cluster, nodes or control plane.

### Key features

- **Scale to zero** and **event-driven autoscaling** with KEDA (HTTP, queue length, CPU, Service Bus, Kafka, …).
- **Revisions** with **traffic splitting** for blue/green and canary releases.
- Built-in **ingress** with HTTPS (external or internal), custom domains and certificates.
- **Managed identity**, Key Vault secret references.
- **Dapr** for service-to-service calls, pub/sub and state.
- **Container Apps jobs** for scheduled, event-driven or manual batch tasks.
- **Environments**: a boundary (shared VNet and Log Analytics) that holds several apps. Consumption or **workload profiles** (dedicated, including GPU).

### What I did (sample)

- Deployed containerised **APIs and background workers** into a Container Apps environment **inside a VNet**.
- Pulled images from **ACR with a managed identity** (no admin user).
- Read secrets from **Key Vault**; configured **scale rules** (HTTP concurrency for the API, Service Bus queue length for the worker, which scaled to zero at night).
- Used revisions to send 10% of traffic to a new version before shifting fully.
- Logs and metrics to Log Analytics with alerts.

### Interview-ready answer

> "Azure Container Apps is a serverless platform for containers, built on Kubernetes, KEDA and Dapr, but you don't manage the cluster. It gives scale to zero, event-driven autoscaling, revisions with traffic splitting and built-in HTTPS ingress. I deployed APIs and queue workers into a VNet-integrated environment, pulled from ACR with managed identity, used Key Vault secrets, scaled the worker on Service Bus queue length down to zero, and did canary releases with revision traffic splitting."

</details>

<details><summary>Q23. How do you deploy an application on Azure Container Apps end to end?</summary>

1. **Build the image:** Dockerfile, build and test locally.
2. **Push to a registry:** the pipeline builds and pushes to **ACR**, with image scanning.
3. **Create base resources (IaC):** resource group, Log Analytics workspace, VNet and subnet (if private), and the **Container Apps environment**.
4. **Identity and access:** a managed identity for the app with **AcrPull** on ACR and **Key Vault Secrets User** on the vault.
5. **Create the container app:** image, CPU/memory, target port, ingress (external/internal), environment variables and secrets (Key Vault references).
6. **Scaling and probes:** min/max replicas, scale rules (HTTP concurrency, queue length), liveness/readiness/startup probes.
7. **Release safely:** **multiple revision mode**; send a small % of traffic to the new revision, check health, then 100% (or roll back to the old revision).
8. **Networking and DNS:** custom domain and managed certificate; internal ingress or private endpoint where needed.
9. **Monitor:** Log Analytics queries, alerts on restarts, failures, latency and replica count.

```bash
az containerapp env create -n cae-prod -g rg-app -l eastus \
  --logs-workspace-id <id> --logs-workspace-key <key>

az containerapp create -n ca-api -g rg-app --environment cae-prod \
  --image myacr.azurecr.io/api:1.0 --target-port 8080 --ingress external \
  --registry-server myacr.azurecr.io --registry-identity system \
  --min-replicas 1 --max-replicas 5

# New version from the pipeline
az containerapp update -n ca-api -g rg-app --image myacr.azurecr.io/api:1.1

# Canary: 90/10 split between revisions
az containerapp ingress traffic set -n ca-api -g rg-app \
  --revision-weight ca-api--v1=90 ca-api--v2=10
```

In Azure DevOps you can use the `AzureContainerApps@1` task; in GitHub Actions, `azure/container-apps-deploy-action`.

### Interview-ready answer

> "The pipeline builds the image, scans it and pushes it to ACR. Terraform creates the Log Analytics workspace, the VNet and the Container Apps environment. The app gets a managed identity with AcrPull and Key Vault Secrets User. I create the container app with the image, port, ingress, secrets, scale rules and probes. For each release the pipeline creates a new revision, sends a small share of traffic to it, checks health, then moves 100% or rolls back. Logs and alerts go to Log Analytics."

</details>

<details><summary>Q24. What are the prerequisites for deploying an application on Azure Container Apps?</summary>

- An **Azure subscription** with the **`Microsoft.App`** and **`Microsoft.OperationalInsights`** resource providers registered.
- A **resource group** and a **Log Analytics workspace** (for logs).
- A **Container Apps environment**. For a custom VNet, a **dedicated subnet**, delegated to `Microsoft.App/environments` for workload profiles. Minimum size: **/27** for workload-profiles environments, **/23** for consumption-only environments.
- A **container image** in a registry (ACR, Docker Hub, …), and **pull access**: managed identity with **AcrPull** (preferred) or registry credentials.
- The app listens on a **known port** (target port) and is a **Linux** container (linux/amd64).
- **RBAC** for the deployer (for example Contributor on the resource group) and a **service connection** for the pipeline.
- **Secrets and config** ready: Key Vault, environment variables.
- **DNS and certificates** if using a custom domain.
- **Azure CLI** with the `containerapp` extension, if deploying from the command line.

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az extension add --name containerapp --upgrade
```

### Interview-ready answer

> "I need a subscription with the Microsoft.App and Microsoft.OperationalInsights providers registered, a resource group, a Log Analytics workspace and a Container Apps environment, with a dedicated subnet of the right size if it's in my VNet. The image must be a Linux container in a registry like ACR, and the app needs a managed identity with AcrPull. I also need the target port, RBAC and a pipeline service connection, secrets in Key Vault, DNS and certificates for a custom domain, and the containerapp CLI extension."

</details>

<details><summary>Q25. What is the difference between AKS and Azure Container Apps?</summary>

| | AKS | Azure Container Apps |
| --- | --- | --- |
| Model | **Managed Kubernetes**: you manage node pools, upgrades, add-ons | **Serverless containers**: Azure manages the infrastructure |
| Kubernetes API | **Full** (`kubectl`, CRDs, operators, Helm) | **Not exposed** |
| Control and flexibility | Very high: custom networking, node pools, GPUs, service mesh, DaemonSets | Lower: simpler and opinionated |
| Scaling | HPA, cluster autoscaler, KEDA (you set them up) | **Built-in KEDA**, including **scale to zero** |
| Releases | Your choice of tools (Helm, Argo CD, Flagger) | Revisions with traffic splitting built in |
| Operational effort | **Higher**: patching, upgrades, security hardening | **Lower** |
| Cost | Pay for nodes **even when idle** | Pay per use (consumption); scale to zero saves cost |
| Best for | Complex microservices, platform teams, custom Kubernetes needs | Web APIs, microservices, event-driven workers, small teams |

### How I choose

- **Container Apps**: fast, low-ops microservices, APIs and event-driven jobs, when the team does not need Kubernetes itself.
- **AKS**: when we need full Kubernetes: operators, service mesh, custom networking, DaemonSets, GPU pools, strict compliance, or many teams on one platform.

### Interview-ready answer

> "AKS is managed Kubernetes: I get the full Kubernetes API, CRDs, operators and node pools, but I also own upgrades, patching and hardening, and I pay for nodes even when idle. Container Apps is serverless on top of Kubernetes: no cluster to manage, built-in KEDA scaling to zero, revisions with traffic splitting, but no kubectl access. I choose Container Apps for simple APIs and event-driven workers, and AKS when we need full Kubernetes control or complex networking and compliance."

</details>

<details><summary>Q26. What database services are available in Azure?</summary>

### Relational

| Service | What it is | HA / DR options |
| --- | --- | --- |
| **Azure SQL Database** | Fully managed SQL Server engine (PaaS), single database or elastic pool. Tiers: General Purpose, Business Critical, **Hyperscale**; DTU or vCore; **serverless** auto-pause | Zone redundancy, **active geo-replication**, **auto-failover groups**, automatic backups with point-in-time restore (PITR), long-term retention |
| **Azure SQL Managed Instance** | Near 100% SQL Server compatibility (SQL Agent, cross-database queries, CLR); good for lift-and-shift | Zone redundancy, failover groups, backups/PITR |
| **SQL Server on Azure VM** (IaaS) | Full control of OS and SQL Server | Always On availability groups, Site Recovery, Azure Backup |
| **Azure Database for PostgreSQL – Flexible Server** | Managed PostgreSQL | Zone-redundant HA (standby in another zone), read replicas, geo-redundant backup |
| **Azure Database for MySQL – Flexible Server** | Managed MySQL | Zone-redundant HA, read replicas, geo-redundant backup |

### Non-relational and others

| Service | What it is |
| --- | --- |
| **Azure Cosmos DB** | Globally distributed **NoSQL** database (APIs: NoSQL, MongoDB, Cassandra, Gremlin, Table; also **PostgreSQL** for distributed Postgres). Multi-region writes, 5 consistency levels, single-digit-ms latency |
| **Azure Cache for Redis / Azure Managed Redis** | In-memory cache and session store |
| **Azure Table Storage** | Simple, cheap key-value store in a storage account |
| **Azure Synapse / Microsoft Fabric / Azure Data Explorer** | Analytics and data warehouse (not OLTP) |
| **Azure Database Migration Service** | Migrate on-prem databases to Azure |

### How I choose

- Existing SQL Server app → **Azure SQL Database**; needs instance features → **SQL Managed Instance**; needs OS access or unsupported features → **SQL on VM**.
- Open-source stack → **PostgreSQL / MySQL Flexible Server**.
- Global, low-latency, flexible schema, huge scale → **Cosmos DB**.
- Caching, sessions → **Redis**.

### Interview-ready answer

> "For relational data Azure has Azure SQL Database, SQL Managed Instance for near-full SQL Server compatibility, SQL Server on VMs when we need OS control, and Flexible Server for PostgreSQL and MySQL. For NoSQL there's Cosmos DB, globally distributed with multi-region writes, plus Redis for caching and Table Storage for simple key-value data. For HA and DR I use zone redundancy, auto-failover groups or geo-replication for SQL, zone-redundant HA and read replicas for Flexible Server, and multi-region accounts for Cosmos DB."

</details>

<details><summary>Q27. Which authentication types do the different Azure databases support?</summary>

| Database | Authentication types |
| --- | --- |
| **Azure SQL Database / SQL Managed Instance** | **SQL authentication** (username + password); **Microsoft Entra ID**: users and groups (password, integrated, interactive with **MFA**), **service principals**, **managed identities**; option for **Microsoft Entra-only authentication** (SQL auth disabled). SQL MI also supports **Windows authentication** for Entra principals (Kerberos) |
| **SQL Server on Azure VM** | Windows authentication (AD domain), SQL authentication, Microsoft Entra authentication (SQL Server 2022+) |
| **PostgreSQL Flexible Server** | PostgreSQL authentication (password), **Microsoft Entra ID** (users, groups, service principals, managed identities), or both |
| **MySQL Flexible Server** | MySQL authentication (password), **Microsoft Entra ID**, or both |
| **Cosmos DB** | **Primary/secondary keys** (read-write and read-only), **resource tokens**, **Microsoft Entra ID with data-plane RBAC** (keys can be turned off with `disableLocalAuth`) |
| **Azure Cache for Redis** | Access keys, **Microsoft Entra ID** (access keys can be disabled) |
| **Table Storage** | Account keys, **SAS tokens**, Microsoft Entra ID |

### Best practice

- Use **Microsoft Entra ID with managed identities** for apps: no passwords in config, central control, MFA for humans, easy offboarding.
- **Disable local/key authentication** where possible (Entra-only for SQL, `disableLocalAuth` for Cosmos DB).
- If passwords or keys must be used, keep them in **Key Vault** and rotate them.
- Combine with **network security**: private endpoints, firewall rules, TLS.

### Example: app with managed identity on Azure SQL

```sql
-- Run as the Entra admin of the database
CREATE USER [app-orders-prod] FROM EXTERNAL PROVIDER;   -- the managed identity's name
ALTER ROLE db_datareader ADD MEMBER [app-orders-prod];
ALTER ROLE db_datawriter ADD MEMBER [app-orders-prod];
```

```text
Server=tcp:sql-prod.database.windows.net;Database=orders;Authentication=Active Directory Managed Identity;
```

### Interview-ready answer

> "Azure SQL and Managed Instance support SQL authentication and Microsoft Entra ID, including MFA, service principals and managed identities, and can be set to Entra-only. PostgreSQL and MySQL Flexible Server support their native passwords and Entra ID. Cosmos DB supports keys, resource tokens and Entra ID with data-plane RBAC, and Redis supports keys and Entra ID. My standard is managed identity with Entra ID for apps, local auth disabled where possible, and any remaining secrets in Key Vault with rotation."

</details>

<details><summary>Q28. What do you know about High Availability and Disaster Recovery plans?</summary>

### Key terms

| Term | Meaning |
| --- | --- |
| **RTO** (Recovery Time Objective) | Maximum acceptable **downtime** |
| **RPO** (Recovery Point Objective) | Maximum acceptable **data loss**, measured in time |
| **Availability zone** | Separate datacenter(s) in one region, with its own power, cooling, network |
| **Paired / secondary region** | Another region used for DR |

### HA plan (within a region)

- **Zone-redundant** services: ZRS/GZRS storage, zone-redundant App Service plans, AKS node pools across zones, zone-redundant SQL, Application Gateway v2 across zones.
- **No single instance**: at least 2 VMs/instances behind a load balancer, VM Scale Sets.
- **Health probes and auto-healing**, autoscaling.

### DR plan (another region)

| DR strategy | How it works | RTO | Cost |
| --- | --- | --- | --- |
| **Backup and restore** | Backups copied to another region; rebuild with IaC | Hours to days | Lowest |
| **Pilot light** | Data replicated; minimal core services running in DR | Hours | Low |
| **Warm standby** (active-passive) | Scaled-down full copy running in DR; scale up on failover | Minutes to an hour | Medium |
| **Active-active** | Both regions serve traffic | Near zero | Highest |

### Azure services for DR

- **Azure Site Recovery** (VM replication and failover), **Azure Backup** with cross-region restore.
- **SQL auto-failover groups**, Cosmos DB multi-region, **GRS/GZRS** storage.
- **Front Door / Traffic Manager** for traffic failover.
- **IaC** (Terraform/Bicep) to rebuild the same environment in the secondary region.

### The plan itself

1. **Business impact analysis**: list applications by criticality, set RTO/RPO for each tier.
2. Choose the strategy per tier (not everything needs active-active).
3. **Runbook**: who declares a disaster, failover steps, DNS changes, communication, failback.
4. **Test**: DR drills at least twice a year; measure real RTO/RPO; fix gaps.
5. **Review** after every architecture change.

### Interview-ready answer

> "I start with RTO and RPO per application, from a business impact analysis. For HA inside a region I use availability zones, multiple instances and health probes, so a zone or server failure doesn't cause an outage. For DR I pick a strategy per tier, from backup and restore up to warm standby or active-active, using Site Recovery, Azure Backup with cross-region restore, SQL failover groups, GZRS storage and Front Door. Everything is written in a runbook with clear owners and tested in regular DR drills."

</details>

<details><summary>Q29. What is the difference between the old and the new landing zone?</summary>

A **landing zone** is a pre-configured Azure environment (subscriptions, management groups, networking, identity, policies, monitoring) that application teams deploy into.

Clarify what the interviewer means by "old". It is usually one of these two comparisons:

### 1. Old (traditional, hand-built) vs new (Azure landing zone / CAF)

| | Old / traditional | New: Azure landing zone (Cloud Adoption Framework) |
| --- | --- | --- |
| Structure | Few large subscriptions, everything mixed; resource groups as the main boundary | **Management group hierarchy** with **subscriptions as the unit of scale** (one or more per app/environment) |
| Build | Manual, portal clicks, inconsistent | **IaC** (Bicep / Terraform accelerators), repeatable |
| Governance | Checked after the fact, by people | **Policy-driven guardrails** with **Azure Policy** at management-group level (deny public IPs, allowed regions, required tags, diagnostics) |
| Networking | Flat or ad hoc VNets | **Hub-and-spoke** or **Virtual WAN**, central firewall, private DNS |
| Platform services | Each team sets up its own | Central **platform** subscriptions: Connectivity, Identity, Management (Log Analytics, Defender) |
| New apps | Ticket and wait | **Subscription vending**: new app landing zone created automatically |

### 2. ALZ itself: older vs current implementation

- **Older**: "Enterprise-Scale" ARM templates, the **ALZ-Bicep** modules, and the Terraform `caf-enterprise-scale` module.
- **Current**: Azure landing zone **accelerators built on Azure Verified Modules (AVM)** for Bicep and Terraform, with updated policy assignments and a simpler, more modular design. The older modules are being retired in favour of AVM.

Typical management group layout (both versions):

```text
Tenant Root
└── Organisation
    ├── Platform        (Connectivity, Identity, Management)
    ├── Landing Zones   (Corp = private/connected, Online = internet-facing)
    ├── Sandbox
    └── Decommissioned
```

### Interview-ready answer

> "A landing zone is the ready-made foundation that applications deploy into. The old way was a few hand-built subscriptions with mixed workloads, manual networking and governance checked afterwards. The new Azure landing zone from the Cloud Adoption Framework uses a management group hierarchy, subscriptions per workload, hub-and-spoke or Virtual WAN networking, central platform subscriptions for connectivity, identity and management, Azure Policy guardrails and subscription vending, all deployed with IaC. The latest accelerators are built on Azure Verified Modules, replacing the older Enterprise-Scale and ALZ-Bicep modules."

</details>

<details><summary>Q30. What is the difference between authentication and authorization?</summary>

| | Authentication (AuthN) | Authorization (AuthZ) |
| --- | --- | --- |
| Question it answers | **Who are you?** | **What are you allowed to do?** |
| Happens | **First** | **After** authentication |
| Based on | Credentials: password, MFA, certificate, token, managed identity | Roles, permissions, policies |
| Azure example | Signing in to **Microsoft Entra ID**, getting a token | **Azure RBAC** role (Reader, Contributor, Key Vault Secrets User) on a scope |
| Protocol | **OpenID Connect** (identity), SAML | **OAuth 2.0** (access to an API/resource) |
| Failure | **401 Unauthorized** (actually "unauthenticated") | **403 Forbidden** |

### Example

A pipeline's service connection signs in to Entra ID with **workload identity federation** → **authentication**. It then tries to create a VM in a resource group where it only has the **Reader** role → **authorization** fails with 403.

### Interview-ready answer

> "Authentication proves who you are, for example signing in to Entra ID with a password and MFA, or a managed identity getting a token. Authorization decides what you can do after that, for example the RBAC role you have on a resource group. Authentication always comes first. A 401 usually means authentication failed, and a 403 means you are authenticated but not authorized."

</details>

<details><summary>Q31. What is the difference between DR and HA?</summary>

| | High Availability (HA) | Disaster Recovery (DR) |
| --- | --- | --- |
| Goal | **Keep running** with no or minimal interruption | **Recover** after a major failure |
| Protects against | Server, rack, disk or **zone** failure | **Whole region** outage, data corruption, ransomware, major human error |
| Scope | Usually **within one region** (availability zones, multiple instances) | **Another region** (or site) |
| Failover | **Automatic**, seconds | Often **planned / triggered**, minutes to hours |
| Data loss | Usually none (synchronous replication) | Possible, defined by **RPO** (asynchronous replication) |
| Measured by | Uptime % (SLA, for example 99.99%) | **RTO** and **RPO** |
| Azure examples | Availability zones, load balancer, VMSS, ZRS, zone-redundant SQL | Site Recovery, GRS/GZRS, SQL failover groups, backups with cross-region restore, Front Door failover |

**Simple way to say it:** HA stops small failures from becoming outages. DR gets you back when something big fails anyway. You need **both**: HA does not protect against a region outage or a corrupted database (corruption is replicated too), and DR alone means downtime for every small failure.

### Interview-ready answer

> "HA keeps the service running through component failures, like a VM or a zone going down, usually inside one region, with automatic failover and no data loss, measured as uptime. DR is recovering from a big event like a region outage or data corruption, usually in another region, measured by RTO and RPO. For example, zone-redundant App Service and SQL give HA, while a failover group and a second region behind Front Door give DR. We need both."

</details>

<details><summary>Q32. What is the difference between a system-assigned and a user-assigned managed identity?</summary>

A **managed identity** is an identity in **Microsoft Entra ID** that Azure manages for you. A resource uses it to get tokens for other services (Key Vault, Storage, SQL) **without any secret** in your code.

| | System-assigned | User-assigned |
| --- | --- | --- |
| Created | **Enabled on the resource** itself | Created as a **separate Azure resource** |
| Lifecycle | **Tied to the resource**: deleted when the resource is deleted | **Independent**: survives when resources are deleted |
| Sharing | **One resource only** | **Can be attached to many resources** |
| Per resource | One | Several user-assigned identities per resource |
| Role assignments | Must be redone for each new resource | Assign once, reuse across resources |
| Available before the resource exists | No | **Yes**: you can grant roles before deploying |
| Best for | Single resource with its own permissions; simple setups | Many resources needing the same access (VMSS, multiple apps, AKS workload identity); **blue/green or recreated resources**; pre-provisioned access |

### Examples

```bash
# System-assigned on a web app
az webapp identity assign -g rg-app -n app-orders

# User-assigned: create once, attach to several apps
az identity create -g rg-identity -n id-orders
az webapp identity assign -g rg-app -n app-orders     --identities <id-orders-resource-id>
az webapp identity assign -g rg-app -n app-orders-dr  --identities <id-orders-resource-id>
az role assignment create --assignee <principalId> \
  --role "Key Vault Secrets User" --scope <key-vault-id>
```

When a resource has a user-assigned identity, the code must say **which one** to use (its **client ID**), for example `AZURE_CLIENT_ID`, or `keyVaultReferenceIdentity` for App Service Key Vault references.

### Interview-ready answer

> "A system-assigned identity is enabled on one resource and lives and dies with it, so it can't be shared. A user-assigned identity is its own resource with an independent lifecycle and can be attached to many resources. I use system-assigned for a single app with its own permissions, and user-assigned when several resources need the same access, when resources get recreated, or when I want to grant roles before deploying, for example for AKS workload identity. With user-assigned, the app must specify the client ID."

</details>

<details><summary>Q33. How does a Classic release pipeline work with multiple stages and approvals?</summary>

A Classic **Release pipeline** takes an **artifact** (from a build pipeline) and deploys it through **stages**, for example Dev → QA → UAT → Prod. Each stage can have **approvals and gates** before and after it.

```text
Artifact (build) --> [Dev] --> [QA] --> (pre-approval: QA lead) [UAT] --> (pre-approval: CAB + gate) [Prod] --> (post-approval)
```

### Stage triggers

- **After release**: the stage starts as soon as a release is created (usually Dev).
- **After stage**: starts when a previous stage **succeeds** (can wait for several stages, or also run on partial success).
- **Manual only**: someone clicks Deploy.

### Approvals

| Setting | Meaning |
| --- | --- |
| **Pre-deployment approval** | Someone must approve **before** the stage deploys (for example a release manager before Prod) |
| **Post-deployment approval** | Someone must sign off **after** deployment before the release moves on (for example QA sign-off) |
| **Approvers** | Users or groups |
| **Approval order** | **Any one** user, **all in any order**, or **all in sequence** |
| **Timeout** | Release is rejected if not approved in time (for example 3 days) |
| **Policy** | "The user requesting a release should not approve it" |
| **Revalidate identity** | Approver must re-enter credentials |

### Gates

Automatic checks that must pass before or after a stage, re-evaluated on an interval: **Azure Monitor alerts** (no active alerts), **query work items** (no open Sev1 bugs), **invoke REST API / Azure Function** (for example ServiceNow change approved), **Azure Policy compliance**.

### Other settings

- **Stage variables** (different connection strings per stage) and **variable groups** scoped to stages.
- **Deployment queue settings**: deploy only the latest release, or all in sequence.
- **Redeploy / rollback** by redeploying an older release to a stage.

### YAML equivalent

In YAML, approvals and checks live on **Environments** (Pipelines → Environments → Approvals and checks), and a `deployment` job targeting that environment waits for them.

### Interview-ready answer

> "A Classic release pipeline takes the build artifact and deploys it stage by stage, like Dev, QA, UAT and Prod. Each stage has a trigger: after release, after a previous stage, or manual. I add pre-deployment approvals before UAT and Prod, with approver groups, an order like any-one or all, a timeout and the rule that the requester can't approve. Post-deployment approvals are for sign-off, and gates check things automatically, like no active Azure Monitor alerts or an approved change in ServiceNow. In YAML the same is done with approvals and checks on environments."

</details>

<details><summary>Q34. Have you used Azure Bicep and ARM templates? How do they compare with Terraform?</summary>

**ARM templates** are JSON files that describe Azure resources for **Azure Resource Manager**. **Bicep** is a simpler language **on top of ARM**: Bicep files are **compiled into ARM JSON**, so anything ARM can do, Bicep can do.

### The same storage account

**ARM (JSON):**

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "name": { "type": "string" }
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2023-05-01",
      "name": "[parameters('name')]",
      "location": "[resourceGroup().location]",
      "sku": { "name": "Standard_GZRS" },
      "kind": "StorageV2"
    }
  ]
}
```

**Bicep:**

```bicep
param name string
param location string = resourceGroup().location

resource st 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  sku: { name: 'Standard_GZRS' }
  kind: 'StorageV2'
}
```

```bash
az deployment group what-if -g rg-app -f main.bicep -p name=stappprod01   # preview
az deployment group create  -g rg-app -f main.bicep -p name=stappprod01
az bicep decompile --file template.json                                  # ARM -> Bicep
```

### Comparison

| | ARM templates | Bicep | Terraform |
| --- | --- | --- | --- |
| Language | Verbose JSON | Clean, concise DSL | HCL |
| Clouds | Azure only | Azure only | **Multi-cloud** and many other providers |
| State file | No (Azure is the state) | **No** | **Yes**: must be stored and locked securely |
| Preview | `what-if` | `what-if` | `plan` |
| New Azure features | Day one | **Day one** | When the provider adds them (`azapi` provider fills the gap) |
| Modules | Linked/nested templates | **Modules**, registries, Azure Verified Modules | Modules, registry |
| Deployment modes | Incremental / Complete | Incremental / Complete, **deployment stacks** | Desired state; also destroys removed resources |

### How I deploy IaC

1. Code and modules in Git with pull request reviews.
2. Pipeline runs lint/validation, then `terraform plan` or `az deployment ... what-if`.
3. Manual approval before production.
4. Parameter files per environment; secrets from Key Vault, never in code.
5. Azure Policy and tagging enforced; drift checked regularly.

### How I choose

**Bicep** for Azure-only work, **Terraform** when the setup is multi-cloud or the team already uses it, **raw ARM** only when maintaining existing templates (or decompile them to Bicep).

### Interview-ready answer

> "Yes. ARM templates are Azure's native JSON format; Bicep is a cleaner language that compiles to ARM, so it supports every Azure resource on day one, has modules and what-if, and needs no state file. Terraform is multi-cloud with plan and a large provider ecosystem, but I must manage its state file securely. I use Bicep for Azure-only work, Terraform for multi-cloud or where the team already uses it, and keep ARM only for legacy templates. All of it runs through a pipeline with what-if or plan, reviews and approval before production."

</details>

<details><summary>Q35. The App Service is in East US and the Key Vault is in a different region. What best practices would you follow?</summary>

Cross-region works, but plan for **latency, resilience and access**.

### Key Vault

- **Replication:** Key Vault contents are replicated within the region and to the **paired region**. During a Microsoft-managed failover the vault is **read-only**: you can read secrets but cannot create or rotate them until it recovers.
- **Soft delete** and **purge protection** on.
- **Azure RBAC** with least privilege, scoped to the vault (or secret).
- **Networking:** private endpoint (needs DNS working across regions/VNets), firewall, trusted services.
- **Monitoring:** diagnostic settings to Log Analytics; alerts on failures, throttling and near-expiry secrets/certificates.
- **Secret lifecycle:** rotation, expiry dates; reference secrets **without a pinned version** so rotation is picked up.
- **Throttling limits** and the right SKU (Standard, or Premium for HSM keys).

### App Service

- **Managed identity** with **Key Vault Secrets User**.
- **Key Vault references** (`@Microsoft.KeyVault(SecretUri=...)`) resolve correctly; they are cached and refreshed periodically, not fetched per request.
- **VNet integration**, routing and private DNS to reach the vault's private endpoint in the other region (VNet peering / hub).
- **Latency:** cross-region calls add delay, so **cache secrets** in the app; don't fetch on every request.
- **Resilience:** retry with backoff; app startup should not fail hard on a slow vault.
- **Slots:** slot-specific settings and a swap strategy.
- Monitoring with Application Insights (dependency calls to Key Vault).

### Recommendation

Put the vault **in the same region** as the app, and a **second vault in the DR region** (synced by IaC/pipeline), so one regional problem does not break secret access, and latency stays low.

### Interview-ready answer

> "It works, but I'd plan for latency and resilience. On Key Vault: soft delete and purge protection, RBAC, a private endpoint with DNS that resolves from the app's VNet, diagnostics and expiry alerts, and awareness that during a regional failover the vault is read-only. On App Service: a managed identity with Secrets User, Key Vault references without pinned versions, VNet integration, and caching with retries so we don't call across regions on every request. My recommendation is a vault in the same region as the app, plus one in the DR region."

</details>

<details><summary>Q36. Which tools have you worked with so far?</summary>

Only list tools you can answer follow-up questions on.

| Area | Tools | How I used them |
| --- | --- | --- |
| **Cloud** | Azure (App Service, VMs, AKS, Container Apps, Key Vault, VNet, Storage, Front Door, Application Gateway), AWS (EKS, ECR, VPC) | Built and ran production environments in hub-and-spoke networks |
| **CI/CD** | Azure DevOps (YAML and Classic), GitHub Actions, Jenkins | Build and release pipelines, templates, approvals, self-hosted agents |
| **IaC** | Terraform, Bicep, ARM templates | Repeatable environments with plan / what-if review |
| **Scripting** | PowerShell, Azure CLI, Bash, Python | Automation, Key Vault tasks, housekeeping scripts |
| **Containers** | Docker, Kubernetes (AKS, EKS), Helm, Azure Container Apps | Packaging, deployment and scaling |
| **Monitoring** | Azure Monitor, Log Analytics, Application Insights, workbooks, Prometheus, Grafana | Dashboards, alerts, KQL investigations, SLOs |
| **Source control** | Git, Azure Repos, GitHub | Branching strategy, pull requests, branch policies |
| **Security and quality** | Key Vault, Defender for Cloud, SonarQube, Trivy, Checkov, Azure Policy | Secrets, scanning, compliance |
| **Other** | Ansible, Jira, ServiceNow, Confluence | Configuration, tickets, change records, runbooks |

### Interview-ready answer

> "Mainly Azure: App Service, AKS, Container Apps, Key Vault, networking with Front Door and Application Gateway, and some AWS EKS. For CI/CD, Azure DevOps YAML and Classic plus GitHub Actions; for IaC, Terraform and Bicep; scripting in PowerShell, Bash, Azure CLI and Python. For containers, Docker, Kubernetes and Helm; for monitoring, Azure Monitor, Application Insights, workbooks, Prometheus and Grafana; and for security, Defender for Cloud, SonarQube, Trivy and Checkov, with ServiceNow and Jira for change and work tracking."

</details>
