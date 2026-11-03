# Globant - Interview Questions (Part 2)

Real interview questions with simple, easy-to-read answers.

---

<details><summary>Q1. How do you use <code>for_each</code> in Terraform?</summary>

`for_each` creates **one resource (or module) per item** in a map or a set of strings. Each instance is identified by its **key**, not by a number.

Inside the block you use:

- `each.key`: the map key (or the set value)
- `each.value`: the map value (for a set, the same as `each.key`)

### Example 1: a set of strings

```hcl
resource "azurerm_resource_group" "rg" {
  for_each = toset(["dev", "test", "prod"])

  name     = "rg-app-${each.key}"
  location = "eastus"
}
```

This creates `azurerm_resource_group.rg["dev"]`, `rg["test"]` and `rg["prod"]`.

### Example 2: a map of objects (most common in real projects)

```hcl
variable "subnets" {
  type = map(object({
    address_prefix = string
  }))
  default = {
    web = { address_prefix = "10.0.1.0/24" }
    app = { address_prefix = "10.0.2.0/24" }
    db  = { address_prefix = "10.0.3.0/24" }
  }
}

resource "azurerm_subnet" "subnet" {
  for_each = var.subnets

  name                 = "snet-${each.key}"
  resource_group_name  = azurerm_resource_group.rg["dev"].name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [each.value.address_prefix]
}

output "subnet_ids" {
  value = { for name, subnet in azurerm_subnet.subnet : name => subnet.id }
}
```

### `for_each` vs `count`

| | `count` | `for_each` |
| --- | --- | --- |
| Input | A number | A map or a set of strings |
| Instance address | `rg[0]`, `rg[1]` | `rg["dev"]`, `rg["prod"]` |
| Removing an item in the middle | Shifts the indexes, so Terraform may destroy and recreate other resources | Only that one item is destroyed |
| Best for | N identical copies, or on/off (`count = var.enabled ? 1 : 0`) | Resources that differ by name or settings |

**Rules to remember:**

- `for_each` does not accept a plain list. Convert it with `toset()`.
- The keys must be known at plan time. You cannot use a value that is only known after apply (such as a generated ID) as a key.
- You cannot use `count` and `for_each` in the same block.

### Interview-ready answer

> "`for_each` creates one instance of a resource or module for each item in a map or set. I use `each.key` and `each.value` inside the block. For example, I keep subnets in a map variable and create all of them with one `azurerm_subnet` block. I prefer `for_each` over `count` because instances are tracked by key, so removing one item does not shift indexes and recreate the others. I use `count` only for simple on/off resources."

</details>

<details><summary>Q2. What is <code>TF_LOG</code> in Terraform?</summary>

`TF_LOG` is an **environment variable that turns on detailed Terraform logs**. It is used to debug problems such as provider errors, authentication failures, API calls that fail, or a plan that hangs.

### Log levels (most detailed first)

| Level | What you see |
| --- | --- |
| `TRACE` | Everything, including every API request and response |
| `DEBUG` | Detailed internal and provider messages |
| `INFO` | General information |
| `WARN` | Warnings |
| `ERROR` | Errors only |
| `JSON` | Same as `TRACE`, in JSON format |

### Related variables

| Variable | Use |
| --- | --- |
| `TF_LOG_PATH` | Writes the logs to a file instead of the console |
| `TF_LOG_CORE` | Log level for Terraform core only |
| `TF_LOG_PROVIDER` | Log level for providers only (for example `azurerm`) |

### Examples

```bash
# Linux / macOS
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform-debug.log
terraform plan

# Only provider logs, to see the Azure API calls
export TF_LOG_PROVIDER=TRACE
terraform apply

# Turn logging off again
unset TF_LOG TF_LOG_PATH TF_LOG_PROVIDER
```

```powershell
# Windows PowerShell
$env:TF_LOG = "DEBUG"
$env:TF_LOG_PATH = "terraform-debug.log"
terraform plan
```

In an Azure DevOps pipeline:

```yaml
- script: terraform plan -out=tfplan
  env:
    TF_LOG: DEBUG
    TF_LOG_PATH: $(Build.ArtifactStagingDirectory)/terraform-debug.log
```

**Careful:** `TRACE` and `DEBUG` logs can contain tokens and secrets. Do not publish them as public pipeline artifacts, and turn logging off after debugging.

### Interview-ready answer

> "`TF_LOG` is an environment variable that enables Terraform's detailed logging. The levels are TRACE, DEBUG, INFO, WARN and ERROR. I set `TF_LOG=DEBUG` or `TRACE` with `TF_LOG_PATH` to write the logs to a file when I need to debug a provider or authentication error, and `TF_LOG_PROVIDER` when I only want the provider's API calls. I turn it off afterwards because the logs can contain sensitive data."

</details>

<details><summary>Q3. What is the difference between a list and a map in Terraform?</summary>

| | List | Map |
| --- | --- | --- |
| What it is | An **ordered** collection of values | A collection of **key = value** pairs |
| Accessed by | Index: `var.locations[0]` | Key: `var.tags["environment"]` |
| Order | Order matters | Accessed by key, not by position |
| Duplicates | Allowed | Keys must be unique |
| Works with `for_each` | Only after `toset()` | Yes, directly |
| Typical use | Address spaces, DNS servers, zones | Tags, per-environment settings, VM sizes per environment |

### List example

```hcl
variable "address_space" {
  type    = list(string)
  default = ["10.0.0.0/16", "10.1.0.0/16"]
}

resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-app"
  address_space       = var.address_space
  location            = "eastus"
  resource_group_name = "rg-app"
}

# First item: var.address_space[0]
```

### Map example

```hcl
variable "vm_size" {
  type = map(string)
  default = {
    dev  = "Standard_B2s"
    prod = "Standard_D4s_v5"
  }
}

variable "tags" {
  type = map(string)
  default = {
    environment = "dev"
    owner       = "platform-team"
  }
}

# VM size for the current environment
# size = var.vm_size[var.environment]
# tags = var.tags
```

There are also `set` (unordered, unique values) and `object` (fixed attributes with different types, for example `object({ name = string, size = number })`).

### Interview-ready answer

> "A list is an ordered collection accessed by index, like `var.zones[0]`. A map is a set of key-value pairs accessed by key, like `var.tags["environment"]`. I use lists for things like address spaces and zones, and maps for tags and per-environment settings, for example a map of VM sizes keyed by environment. Maps also work directly with `for_each`, while a list needs `toset()` first."

</details>

<details><summary>Q4. Are App Service deployment slots blue/green, canary, or both?</summary>

**Both.**

- **Blue/green:** deploy the new version to the `staging` slot, test it, then **swap** it with `production`. All traffic moves to the new version at once, and the old version is now in the staging slot, so you can swap back to roll back.
- **Canary:** use **Traffic % routing** (called "testing in production"). Send a small percentage of production traffic, for example 10%, to the staging slot, watch errors and performance, then increase it or swap.

### Blue/green with a swap

```bash
# Deploy to the staging slot
az webapp deploy -g rg-app -n app-prod --slot staging --src-path app.zip

# Test https://app-prod-staging.azurewebsites.net, then swap
az webapp deployment slot swap -g rg-app -n app-prod --slot staging --target-slot production

# Rollback = swap again
az webapp deployment slot swap -g rg-app -n app-prod --slot staging --target-slot production
```

### Canary with traffic routing

```bash
# Send 10% of production traffic to the staging slot
az webapp traffic-routing set -g rg-app -n app-prod --distribution staging=10

# Everything looks good: send all traffic by swapping, then clear the routing
az webapp deployment slot swap -g rg-app -n app-prod --slot staging --target-slot production
az webapp traffic-routing clear -g rg-app -n app-prod
```

A user who is routed to a slot stays on it through the `x-ms-routing-name` cookie, so they do not jump between versions.

### Interview-ready answer

> "Deployment slots support both. The swap is a blue/green deployment: I deploy to the staging slot, warm it up and test it, then swap it with production, and rolling back is just swapping again. For canary, I use Traffic % routing to send a small share of production traffic, like 10%, to the staging slot, monitor it in Application Insights, and then swap when it is healthy."

</details>

<details><summary>Q5. If the PAT used to set up a self-hosted agent expires, will the agent show as online or offline?</summary>

**It stays online.**

The PAT is used **only once, while registering the agent** (`config.sh` / `config.cmd`). During registration, the agent gets its own credentials (a key pair and an OAuth token issued for that agent). After that, the agent uses those credentials to talk to Azure DevOps, not the PAT.

So when the PAT expires or is revoked:

- The agent stays **online** and keeps running jobs.
- You need a **new PAT** only when you **reconfigure** or **remove** the agent (`config.sh remove`), or register a new one.

### When does an agent go offline?

| Cause | What to do |
| --- | --- |
| The agent service or VM is stopped | Start the service (`sudo ./svc.sh start`) or the VM |
| No outbound network access to Azure DevOps (firewall, proxy, DNS) | Allow outbound HTTPS 443 to the Azure DevOps URLs |
| The agent was deleted from the pool in the portal | Register it again with a new PAT |
| The VM was reimaged, or the agent folder was deleted | Register it again |
| A very old agent version that cannot update itself | Upgrade the agent |

```bash
# Check the agent service on Linux
sudo ./svc.sh status

# Remove and re-register (this step needs a valid PAT)
./config.sh remove --auth pat --token <new-pat>
./config.sh --unattended --url https://dev.azure.com/<org> --auth pat --token <new-pat> \
  --pool Linux-SelfHosted --agent build-agent-01 --acceptTeeEula
sudo ./svc.sh install && sudo ./svc.sh start
```

**Good practice:** give the registration PAT only the **Agent Pools (Read & manage)** scope and a short expiry, because it is not needed after registration.

### Interview-ready answer

> "The agent stays online. The PAT is only used to register the agent. During registration the agent gets its own credentials, and it uses those afterwards. An expired PAT only matters when I want to reconfigure, remove or add an agent. If an agent shows offline, I check the agent service, the VM, and outbound network access to Azure DevOps."

</details>

<details><summary>Q6. Give a use case where you would use self-hosted agents.</summary>

Microsoft-hosted agents are easy (a clean VM for every job, no maintenance), but they run on Microsoft's network and you cannot change them much. I use **self-hosted agents** when:

1. **The pipeline must reach private resources.** For example, deploying to a **private AKS cluster**, a Key Vault or Storage Account with **private endpoints only**, an internal database, or on-premises servers. A Microsoft-hosted agent cannot reach them.
2. **Special tools or licences** are needed: a specific SDK, a licensed tool, GPU, or a particular OS version.
3. **Speed:** Docker layers, Maven `.m2`, npm and NuGet caches stay on the agent between runs, so builds are faster.
4. **Compliance:** the build must run inside the company network or a specific region, with company-approved images.
5. **Long or heavy jobs:** jobs that need more CPU, memory or disk, or run longer than the Microsoft-hosted time limit.
6. **Cost:** many build minutes a month can be cheaper on your own VMs or a VM Scale Set.

### Real-time example

> Our production AKS cluster was **private** and Key Vault was behind a **private endpoint**. Microsoft-hosted agents could not reach them, so we created self-hosted Linux agents in a VM Scale Set **inside a subnet peered with the AKS VNet**. The deploy stages ran on that pool, so `kubectl`, `helm` and Key Vault calls stayed inside the private network.

```yaml
stages:
  - stage: Build
    pool:
      vmImage: ubuntu-latest        # Microsoft-hosted is fine for the build
    jobs:
      - job: Build
        steps:
          - script: docker build -t myapp:$(Build.BuildId) .

  - stage: DeployProd
    pool:
      name: Linux-SelfHosted-Private   # self-hosted agents inside the VNet
    jobs:
      - deployment: Deploy
        environment: prod
        strategy:
          runOnce:
            deploy:
              steps:
                - script: helm upgrade --install myapp ./chart -n myapp
```

**Tip:** Azure Virtual Machine Scale Set agents (or Managed DevOps Pools) give you self-hosted agents that scale automatically and can be reset to a clean state after each job.

### Interview-ready answer

> "I use self-hosted agents when the pipeline needs to reach private resources. In my project the production AKS cluster was private and Key Vault had only a private endpoint, so Microsoft-hosted agents could not reach them. We ran self-hosted agents in a VM Scale Set inside a peered VNet and used that pool for the deployment stages. Other reasons are custom tools, caching for faster builds, compliance, and long-running jobs."

</details>

<details><summary>Q7. Terraform says a resource already exists. What do you do?</summary>

The error usually looks like this (with the `azurerm` provider it normally appears during **apply**):

```text
Error: A resource with the ID "/subscriptions/.../resourceGroups/rg-app" already exists -
to be managed via Terraform this resource needs to be imported into the State.
```

It means the resource **exists in Azure but not in the Terraform state**, so Terraform tries to create it again. Common causes: someone created it manually in the portal, a previous apply failed after creating it, or you are using the **wrong state file** (wrong backend key or workspace).

### Step 1: check you are on the right state

```bash
terraform workspace show
terraform state list | grep rg-app
```

If the backend key or workspace is wrong, fix that first. Then the resource is already in the state and there is nothing to import.

### Step 2: decide if Terraform should manage it

**Yes, Terraform should manage it: import it.**

Option A, the `import` block (Terraform 1.5+, reviewed in the plan, good for pipelines):

```hcl
import {
  to = azurerm_resource_group.rg
  id = "/subscriptions/<subscription-id>/resourceGroups/rg-app"
}
```

```bash
terraform plan    # shows "1 to import"
terraform apply
```

Option B, the CLI command:

```bash
terraform import azurerm_resource_group.rg /subscriptions/<subscription-id>/resourceGroups/rg-app
```

**No, it is a different resource with the same name:** give the Terraform resource a different name.

### Step 3: make the code match

After the import, run `terraform plan`. If it shows changes, update the code to match the real settings (or accept the changes on purpose). The goal is **"No changes"**.

**Do not** delete the Azure resource just to make the error go away. It may hold data or be used by other systems.

### Interview-ready answer

> "That error means the resource exists in Azure but not in Terraform's state. First I check I am using the right backend and workspace, because a wrong state file causes the same error. If the resource should be managed by Terraform, I import it, preferably with an `import` block so the import shows up in the plan, or with `terraform import`. Then I run plan again and adjust the code until it shows no changes. I never delete the existing resource just to get past the error."

</details>

<details><summary>Q8. Give a particular use case where you would use HPA.</summary>

The **Horizontal Pod Autoscaler (HPA)** adds or removes **pod replicas** based on a metric, usually CPU or memory.

### Use case

> We had an **order API** on AKS. Traffic was low at night and very high during sales and in the evenings. With a fixed 3 replicas, pods hit high CPU and response times went up at peak, and at night we paid for capacity we did not use. We added an HPA: **minimum 3, maximum 15 pods, target 70% CPU**. At peak it scaled out automatically; at night it scaled back to 3. The **Cluster Autoscaler** added nodes when the new pods did not fit.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-api
  minReplicas: 3
  maxReplicas: 15
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # wait 5 minutes before scaling down
```

### Requirements

- **metrics-server** must be running (it is built into AKS).
- The containers must have **CPU and memory requests**, because utilization is calculated against the request.
- The app should be **stateless** so any pod can serve any request.

```bash
kubectl get hpa order-api -w
kubectl describe hpa order-api
```

**When HPA is not the right tool:**

- Scaling on **queue length** or events (Service Bus, Kafka): use **KEDA**.
- Pods need **more CPU per pod**, not more pods: use **VPA**.
- There is **no room for more pods** on the nodes: the **Cluster Autoscaler** adds nodes.

### Interview-ready answer

> "I use HPA for stateless services with changing traffic. For example, our order API on AKS had big peaks in the evening. I configured an HPA with minimum 3, maximum 15 replicas and a 70% CPU target, with CPU requests set on the containers. It scaled out at peak and back down at night, and the Cluster Autoscaler added nodes when needed. For queue-based workloads I use KEDA instead."

</details>

<details><summary>Q9. What is the difference between a Deployment and a DaemonSet?</summary>

| | Deployment | DaemonSet |
| --- | --- | --- |
| Purpose | Run **N replicas** of an application | Run **one pod on every node** (or on selected nodes) |
| Number of pods | You set `replicas` (or HPA does) | Equal to the number of matching nodes |
| Placement | The scheduler places pods on any suitable nodes | One pod per node, automatically |
| New node joins | Nothing changes | A pod is started on the new node automatically |
| Scaling | `kubectl scale`, HPA | No `replicas` field; it follows the nodes |
| Typical use | Web apps, APIs, microservices | Log agents (Fluent Bit), monitoring agents (node-exporter), network/CNI and storage/CSI plugins, security agents |

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-api
  template:
    metadata:
      labels:
        app: web-api
    spec:
      containers:
        - name: web-api
          image: myacr.azurecr.io/web-api:1.4.0
```

### DaemonSet

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      tolerations:
        - operator: Exists          # also run on tainted nodes
      containers:
        - name: node-exporter
          image: quay.io/prometheus/node-exporter:v1.8.2
```

### Interview-ready answer

> "A Deployment runs a set number of replicas of an application, and the scheduler decides which nodes they go on. I use it for web apps and APIs, and scale it with HPA. A DaemonSet runs exactly one pod on every node, or on nodes that match a selector, and automatically adds a pod when a new node joins. I use DaemonSets for node-level agents like Fluent Bit for logs and node-exporter for metrics."

</details>

<details><summary>Q10. The same port is defined in <code>values.yaml</code> and <code>dev-values.yaml</code>. Which one is used?</summary>

**The value from `dev-values.yaml` is used** (assuming you pass it with `-f`).

Helm merges values in this order, and **later values override earlier ones**:

1. The chart's own `values.yaml` (always loaded, even if you do not pass it)
2. Files passed with `-f` / `--values`, **from left to right**
3. `--set` and `--set-string` (highest priority)

```yaml
# values.yaml
service:
  port: 80
  type: ClusterIP
```

```yaml
# dev-values.yaml
service:
  port: 8080
```

```bash
helm upgrade --install myapp ./myapp -f values.yaml -f dev-values.yaml
# Result: service.port = 8080, service.type = ClusterIP (kept from values.yaml)

helm upgrade --install myapp ./myapp -f dev-values.yaml --set service.port=9090
# Result: service.port = 9090 (--set wins)
```

Things to know:

- **Maps are merged deeply**, so `service.type` is kept from `values.yaml` while only `service.port` changes.
- **Lists are replaced, not merged.** If both files define a list, the later list replaces the earlier one completely.
- If you pass the files the other way round (`-f dev-values.yaml -f values.yaml`), `values.yaml` wins. The order on the command line matters.

Check the final values before deploying:

```bash
helm template myapp ./myapp -f values.yaml -f dev-values.yaml | grep -A5 "kind: Service"
helm get values myapp -n dev          # values used by an installed release
```

### Interview-ready answer

> "The port from `dev-values.yaml` is used. Helm starts with the chart's `values.yaml`, then applies each `-f` file from left to right, and `--set` overrides everything. Maps are deep-merged, so only the port is overridden and other keys stay from `values.yaml`, but lists are replaced completely. I check the final result with `helm template` before deploying."

</details>

<details><summary>Q11. How do you give new joiners access to a storage account?</summary>

I give access through **Microsoft Entra ID groups and Azure RBAC**, never by sharing the storage account keys.

### Steps

1. **Add the new joiner to an Entra ID group**, for example `grp-storage-app-readers`. Access is given to the group, not to each person, so onboarding and offboarding is just group membership.
2. **Assign a data role to the group** at the smallest scope that works (the container or file share, not the whole subscription):

| Need | Role |
| --- | --- |
| Read blobs | **Storage Blob Data Reader** |
| Upload and change blobs | **Storage Blob Data Contributor** |
| Read Azure Files shares | **Storage File Data SMB Share Reader** |
| Read and write Azure Files shares | **Storage File Data SMB Share Contributor** |
| Read queue messages | **Storage Queue Data Reader** |

```bash
SCOPE=$(az storage account show -n stappdata -g rg-app --query id -o tsv)
GROUP_ID=$(az ad group show --group grp-storage-app-readers --query id -o tsv)

az role assignment create \
  --assignee-object-id "$GROUP_ID" --assignee-principal-type Group \
  --role "Storage Blob Data Reader" \
  --scope "$SCOPE/blobServices/default/containers/reports"
```

3. **Disable shared key access** (`allowSharedKeyAccess = false`) so everyone must use Entra ID, and every access is logged with the user's identity.
4. **Network:** if the account uses private endpoints or firewall rules, the user must connect through the VPN or corporate network.
5. **Elevated access** (for example Contributor on production) goes through **PIM**: eligible, time-limited and approved.
6. **Temporary access** for one file or an external user: a **user delegation SAS** with a short expiry, not an account key SAS.
7. Run **access reviews** every quarter, and remove the user from the group when they leave or change team.

**Important:** **Reader** or **Contributor** on the storage account is **control-plane** access (manage the account settings). They do **not** let users read data with Entra ID. For data you need the **Storage Blob Data** roles.

The user then signs in with their own account, for example in Azure Storage Explorer or with `az storage blob list --auth-mode login`.

### Interview-ready answer

> "I add the new joiner to an Entra ID group and give the group a data-plane role like Storage Blob Data Reader, scoped to the container they need. I keep shared key access disabled, so access always goes through Entra ID and is audited. Higher access goes through PIM, temporary access uses a short user delegation SAS, and access reviews remove people who no longer need it. I never share account keys."

</details>

<details><summary>Q12. What are Function Apps and App Service used for?</summary>

Both run on the same App Service platform, but they are used for different kinds of work.

| | App Service (Web App) | Function App (Azure Functions) |
| --- | --- | --- |
| Model | Always-on web hosting | **Serverless**, event-driven code |
| Runs when | Always, waiting for HTTP requests | When a **trigger** fires: HTTP, timer, queue, Service Bus, Event Grid, Blob |
| Typical use | Websites, REST APIs, backends for mobile and frontend apps | Small background tasks: process a queue message, resize an uploaded image, nightly cleanup, webhooks |
| Scaling | Manual or autoscale rules on the App Service plan | Automatic, per event, down to zero on the Consumption / Flex Consumption plans |
| Billing | Pay for the App Service plan all the time | On Consumption: pay per execution and resources used |
| Long tasks | Fine | Consumption plan has an execution time limit (5 minutes by default, 10 at most); use Premium, Dedicated or Durable Functions for longer work |
| Deployment slots | Yes | Yes (with limits on some plans) |

### Real-time example

> Our customer portal and its REST API ran on **App Service** with deployment slots. When a user uploaded an invoice to Blob Storage, a **Function App** with a Blob/Event Grid trigger read the file, generated a PDF summary and wrote the result to another container. A **timer-triggered function** cleaned up old files every night.

```csharp
// A timer-triggered function: runs every day at 01:00
[Function("NightlyCleanup")]
public void Run([TimerTrigger("0 0 1 * * *")] TimerInfo timer) { /* delete old blobs */ }
```

### Interview-ready answer

> "App Service is for always-on web apps and APIs, like our customer portal and its REST API. Function Apps are serverless and event-driven: code runs when a trigger fires, like an HTTP call, a timer, a queue message or a new blob. I use Functions for small background jobs such as processing uploaded files or nightly cleanup, because they scale automatically and on the Consumption plan you pay only when they run. For long-running work I use a Premium plan or Durable Functions."

</details>

<details><summary>Q13. Write a sample KQL query to list the resources in a resource group.</summary>

Use **Azure Resource Graph**, which you can query with KQL from the **Resource Graph Explorer** in the portal, the Azure CLI or PowerShell.

### List the resources

```kusto
Resources
| where resourceGroup =~ 'rg-app-prod'
| project name, type, location, resourceGroup, subscriptionId
| order by type asc, name asc
```

`=~` is a case-insensitive comparison. Resource group names are stored in lowercase in Resource Graph, so `=~` avoids missing them.

### More useful queries

```kusto
// Count the resources by type
Resources
| where resourceGroup =~ 'rg-app-prod'
| summarize count() by type
| order by count_ desc

// Resources missing an "owner" tag
Resources
| where resourceGroup =~ 'rg-app-prod'
| where isnull(tags.owner) or tostring(tags.owner) == ''
| project name, type

// VMs and their power state
Resources
| where type =~ 'microsoft.compute/virtualmachines'
| where resourceGroup =~ 'rg-app-prod'
| project name, powerState = tostring(properties.extended.instanceView.powerState.code)
```

### Run it from the CLI

```bash
az extension add --name resource-graph
az graph query -q "Resources | where resourceGroup =~ 'rg-app-prod' | project name, type, location" -o table

# The simple non-KQL way
az resource list -g rg-app-prod -o table
```

### Interview-ready answer

> "I use Azure Resource Graph with KQL: `Resources | where resourceGroup =~ 'rg-app-prod' | project name, type, location`. I run it in Resource Graph Explorer or with `az graph query`. I also use `summarize count() by type` to see what is in a resource group, and filter on tags to find resources without an owner. Resource Graph is fast and can query across all subscriptions at once."

</details>

<details><summary>Q14. Which Azure-native security tool scans code for vulnerabilities?</summary>

**GitHub Advanced Security for Azure DevOps (GHAzDO)**, with the results also visible in **Microsoft Defender for Cloud**.

| Tool | What it scans |
| --- | --- |
| **GitHub Advanced Security for Azure DevOps** | **Code scanning** with **CodeQL** (SQL injection, XSS, insecure code in C#, Java, JavaScript, Python and more), **secret scanning** (with push protection to block secrets before they are pushed), and **dependency scanning** (vulnerable open-source packages) |
| **Microsoft Defender for Cloud: DevOps security** | Connects Azure DevOps, GitHub and GitLab, and shows code, secret, dependency and IaC findings in one place, linked to the cloud resources they deploy |
| **Microsoft Security DevOps extension** | Runs scanners in the pipeline (for example Checkov, Trivy and Template Analyzer) and sends the results to Defender for Cloud |
| **Defender for Containers** | Vulnerability scanning of container images in Azure Container Registry |

For code in **GitHub**, the same features are part of **GitHub Advanced Security** (CodeQL, secret scanning, Dependabot).

### Pipeline example with GitHub Advanced Security for Azure DevOps

```yaml
steps:
  - task: AdvancedSecurity-Codeql-Init@1
    inputs:
      languages: 'csharp'
  - task: DotNetCoreCLI@2
    inputs:
      command: build
  - task: AdvancedSecurity-Dependency-Scanning@1
  - task: AdvancedSecurity-Codeql-Analyze@1
```

The results appear in **Repos → Advanced Security**, and the team can block pull requests that add new high-severity alerts.

### Interview-ready answer

> "The Azure-native option is GitHub Advanced Security for Azure DevOps. It gives code scanning with CodeQL, secret scanning with push protection, and dependency scanning, all inside Azure Repos and Pipelines. Microsoft Defender for Cloud's DevOps security brings those findings together with IaC and container image findings, so we see everything in one place. Many teams also use SonarQube for code quality, but the native security tool is Advanced Security."

</details>

<details><summary>Q15. What type of vulnerabilities does Checkov report?</summary>

**Checkov** is an open-source **static analysis tool for infrastructure as code**. It reports **misconfigurations**: settings that make the infrastructure insecure or non-compliant, **before** it is deployed.

### What it scans

Terraform (and Terraform plan JSON), Bicep, ARM templates, CloudFormation, Kubernetes YAML, Helm charts, Kustomize, Dockerfiles, and CI/CD files such as GitHub Actions and Azure Pipelines.

### Types of issues it reports

| Category | Examples |
| --- | --- |
| Public exposure | Storage account allows public blob access; NSG allows SSH (22) or RDP (3389) from `0.0.0.0/0`; database open to the internet |
| Encryption | Encryption at rest disabled; HTTPS-only not enforced; minimum TLS version below 1.2 |
| Identity and access | Overly broad IAM/RBAC permissions; managed identity not used; AKS without Entra ID or with local accounts |
| Logging and monitoring | Diagnostic logs disabled; no log retention |
| Backup and resilience | Soft delete or purge protection disabled on Key Vault; no backup or geo-redundancy |
| Kubernetes and containers | Containers running as root or privileged; no CPU/memory limits; no readiness/liveness probes; image using the `latest` tag |
| Secrets | Hardcoded passwords, keys and tokens in the code |
| Supply chain (SCA) | Vulnerable open-source packages and container images (with the Prisma Cloud platform connected) |

Each finding has a check ID (for example `CKV_AZURE_...`, `CKV_K8S_...`), the file and line, and a link to the fix.

### Example

```bash
checkov -d ./terraform --framework terraform
checkov -f k8s/deployment.yaml
checkov -d . --soft-fail          # report only, do not fail the build
```

```hcl
resource "azurerm_storage_account" "logs" {
  # checkov:skip=<check-id>:Public access is required for the static website
  name                     = "stlogs001"
  resource_group_name      = "rg-app"
  location                 = "eastus"
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
```

Skips must have a reason, and the team reviews them.

**Note:** Checkov is **not** a code vulnerability scanner for application code (SQL injection, XSS). Use CodeQL or SonarQube for that, and Trivy or Defender for Containers for image CVEs.

### Interview-ready answer

> "Checkov scans infrastructure as code (Terraform, Bicep, ARM, Kubernetes manifests, Helm charts and Dockerfiles) for security misconfigurations before deployment. It reports things like public storage access, NSGs open to the internet on SSH or RDP, encryption or HTTPS-only not enforced, missing diagnostic logs, Key Vault without purge protection, containers running as root or without resource limits, and hardcoded secrets. I run it in the pipeline on every pull request, and any skip needs a documented reason."

</details>

<details><summary>Q16. Will I get Helm in the Azure Marketplace?</summary>

**Not as a product to buy or deploy.** Helm is a free, open-source **CLI tool**. You install it on your machine or agent; it is not something you deploy from the Azure Marketplace.

Where Helm is already available in Azure:

| Place | How |
| --- | --- |
| **Azure Cloud Shell** | Helm is preinstalled |
| **Microsoft-hosted pipeline agents** | Helm is preinstalled; the `HelmInstaller@1` task installs a specific version |
| **Azure DevOps** | Built-in **`HelmDeploy@0`** task to run `helm upgrade` against AKS |
| **Azure Container Registry** | Stores Helm charts as **OCI artifacts** (`helm push oci://myacr.azurecr.io/helm`) |
| **Azure Marketplace "Kubernetes apps"** | Third-party applications **packaged as Helm charts** that you install on AKS as cluster extensions. You get the application, not the Helm tool |

```bash
# Install Helm on a Linux VM or self-hosted agent
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

```yaml
- task: HelmInstaller@1
  inputs:
    helmVersionToInstall: 'latest'
- task: HelmDeploy@0
  inputs:
    connectionType: 'Azure Resource Manager'
    azureSubscription: 'sc-azure-prod'
    azureResourceGroup: 'rg-aks'
    kubernetesCluster: 'aks-prod'
    command: upgrade
    chartType: FilePath
    chartPath: './charts/myapp'
    releaseName: 'myapp'
    namespace: 'myapp'
```

### Interview-ready answer

> "Helm itself is an open-source CLI, so you install it rather than get it from the Marketplace. It is already in Cloud Shell and on Microsoft-hosted agents, Azure DevOps has the HelmInstaller and HelmDeploy tasks, and ACR can store Helm charts as OCI artifacts. What the Azure Marketplace does have is Kubernetes apps, which are third-party applications packaged as Helm charts that you install on AKS."

</details>

<details><summary>Q17. Explain maxSurge and maxUnavailable in a rolling update: 8 replicas, surge 4, unavailable 2. What are the percentages?</summary>

In a rolling update, Kubernetes replaces old pods with new ones in batches.

- **`maxSurge`**: how many **extra** pods can exist **above** the desired replica count during the update.
- **`maxUnavailable`**: how many pods can be **unavailable below** the desired replica count during the update.

### With 8 replicas, maxSurge 4, maxUnavailable 2

| | Number | Percentage of 8 |
| --- | --- | --- |
| maxSurge | 4 | **50%** (4 / 8) |
| maxUnavailable | 2 | **25%** (2 / 8) |

So during the update:

- **Maximum pods at any time:** 8 + 4 = **12**
- **Minimum available pods at any time:** 8 - 2 = **6**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
spec:
  replicas: 8
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 4           # or "50%"
      maxUnavailable: 2     # or "25%"
```

### What happens step by step

1. Kubernetes can start up to **4 new pods** at once (total 12) and stop up to **2 old pods** at once (6 still available).
2. When new pods become **Ready** (readiness probe passes), more old pods are removed and more new pods are started.
3. This repeats until all 8 pods run the new version.

### Rounding rules for percentages

- `maxSurge` percentage is **rounded up**.
- `maxUnavailable` percentage is **rounded down**.

For example, with 8 replicas and `maxUnavailable: 30%`: 8 × 0.3 = 2.4, rounded down to **2**.

**Zero-downtime setting:** `maxUnavailable: 0` with `maxSurge: 1` (or more) never drops below full capacity, but needs room for the extra pods.

### Interview-ready answer

> "maxSurge is how many extra pods can run above the desired count during a rolling update, and maxUnavailable is how many can be down below it. With 8 replicas, a surge of 4 is 50% and an unavailable of 2 is 25%, so the Deployment runs at most 12 pods and always keeps at least 6 available. New pods must pass their readiness probe before more old ones are removed. For zero downtime in production, I use maxUnavailable 0."

</details>

<details><summary>Q18. How do you use GitHub with Azure DevOps?</summary>

You can keep your code in **GitHub** and still use **Azure Pipelines** and **Azure Boards**.

### 1. Build and deploy GitHub code with Azure Pipelines

1. In Azure DevOps: **Pipelines → New pipeline → GitHub (YAML)**.
2. Authorize with the **Azure Pipelines GitHub App** (recommended), OAuth, or a PAT. This creates a **GitHub service connection**.
3. Select the repository. The pipeline YAML (`azure-pipelines.yml`) lives in the GitHub repo.
4. Pushes and pull requests in GitHub trigger the pipeline, and the result appears as a **status check** on the pull request.

```yaml
# azure-pipelines.yml in the GitHub repository
trigger:
  branches:
    include: [main]

pr:
  branches:
    include: [main]

pool:
  vmImage: ubuntu-latest

steps:
  - script: npm ci && npm test
    displayName: Build and test
```

In GitHub, make that check **required** with a branch protection rule, so pull requests cannot merge until the pipeline passes.

### 2. Use another GitHub repository in a pipeline (templates or multi-repo)

```yaml
resources:
  repositories:
    - repository: templates
      type: github
      name: my-org/pipeline-templates
      endpoint: github-connection      # the GitHub service connection
      ref: refs/heads/main

steps:
  - checkout: self
  - checkout: templates
```

### 3. Azure Boards with GitHub

Install the **Azure Boards app** for GitHub. Then write `AB#1234` in a commit message or pull request, and it links to work item 1234. `Fixes AB#1234` moves the work item to done when the pull request merges.

### Interview-ready answer

> "I connect the GitHub repository to Azure Pipelines through the Azure Pipelines GitHub App, which creates a service connection. The YAML file lives in the GitHub repo, pushes and pull requests trigger the pipeline, and the result shows as a status check that I make required with branch protection. I also use GitHub repos as template repositories through `resources.repositories`, and link commits to Azure Boards with `AB#` mentions."

</details>

<details><summary>Q19. What are slots in a Web App?</summary>

A **deployment slot** is a **separate live copy of your web app** with its own hostname, for example `app-prod-staging.azurewebsites.net`. The default slot is **production**; you add others like **staging** or **qa**.

### Why use them

- **Test before going live:** deploy to staging and test it with real settings.
- **Zero-downtime release:** the slot is **warmed up** before the swap, so users do not hit a cold start.
- **Instant rollback:** swap back, and the previous version is live again.
- **Canary:** send a percentage of traffic to a slot (see Q4).

### Key facts

| Point | Detail |
| --- | --- |
| Plan tier | **Standard** or higher (Standard: up to 5 slots, Premium and Isolated: up to 20) |
| Shared resources | All slots run on the **same App Service plan**, so they share its CPU and memory |
| Slot settings ("sticky") | Settings marked **Deployment slot setting** stay with the slot during a swap, for example a staging database connection string |
| Swap with preview | Applies the target slot's settings to the source first, so you can check it before finishing the swap |
| Auto swap | Swaps automatically after a successful deployment to the slot |
| Warm-up | Use `applicationInitialization` or health check paths so the app is ready before the swap |

```bash
az webapp deployment slot create -g rg-app -n app-prod --slot staging
az webapp config appsettings set -g rg-app -n app-prod --slot staging \
  --slot-settings ENVIRONMENT=staging
az webapp deployment slot swap -g rg-app -n app-prod --slot staging --target-slot production
```

```yaml
# Azure DevOps: deploy to staging, then swap
- task: AzureWebApp@1
  inputs:
    azureSubscription: sc-azure-prod
    appName: app-prod
    deployToSlotOrASE: true
    resourceGroupName: rg-app
    slotName: staging
    package: $(Pipeline.Workspace)/drop/*.zip
- task: AzureAppServiceManage@0
  inputs:
    azureSubscription: sc-azure-prod
    Action: Swap Slots
    WebAppName: app-prod
    ResourceGroupName: rg-app
    SourceSlot: staging
```

### Interview-ready answer

> "Slots are separate live environments of the same web app, each with its own URL, running on the same App Service plan. I deploy to the staging slot, test it, and swap it into production, so the release is zero downtime and rollback is just swapping back. I mark environment-specific settings as slot settings so they stay with the slot. Slots need the Standard tier or higher."

</details>

<details><summary>Q20. Explain Azure Front Door, VNet peering, private endpoints, IaaS and PaaS.</summary>

### Azure Front Door

A **global** entry point for web applications. It is a Layer 7 load balancer and CDN that runs at Microsoft's edge locations around the world. It sends users to the **nearest healthy backend**, handles TLS, caches static content and includes a **WAF**. Used for multi-region apps and failover between regions.

### VNet peering

Connects **two virtual networks** so resources in them talk using **private IPs** over the Microsoft backbone, with low latency. It works in the same region or across regions (global peering). Peering is **not transitive**: if A is peered with B and B with C, A cannot reach C unless you add peering or route through a hub firewall. Used in **hub-and-spoke** networks.

### Private endpoint

A **network interface with a private IP in your subnet** that connects to a PaaS service such as Storage, Key Vault, SQL or ACR. Traffic stays on the private network, and you can **disable public access** to the service. It needs **Private DNS zones** (for example `privatelink.blob.core.windows.net`) so the service name resolves to the private IP.

### IaaS (Infrastructure as a Service)

Azure gives you the infrastructure (**VMs, disks, networks**); **you manage the OS**, patching, runtime and application. Example: Azure Virtual Machines. Most control, most work.

### PaaS (Platform as a Service)

Azure manages the infrastructure **and the OS and runtime**; **you manage only your code and data**. Examples: App Service, Azure SQL Database, Azure Functions, AKS (partly). Less work, less control.

| | IaaS | PaaS | SaaS |
| --- | --- | --- | --- |
| You manage | OS, runtime, app, data | App and data | Only your data and users |
| Example | Azure VMs | App Service, Azure SQL | Microsoft 365 |

### How they fit together

```text
Users ──► Azure Front Door (global, WAF)
            ──► App Service (PaaS) in the spoke VNet
                  ──► Azure SQL / Key Vault through private endpoints
            Hub VNet (firewall, VPN) ◄── peering ──► spoke VNets
            Legacy app on VMs (IaaS) in another spoke
```

### Interview-ready answer

> "Front Door is a global Layer 7 entry point with WAF, caching and routing to the nearest healthy region. VNet peering connects two VNets over private IPs, and it is not transitive, so we use hub-and-spoke. A private endpoint gives a PaaS service a private IP inside my VNet, so I can turn off its public access, with Private DNS zones for name resolution. IaaS means I manage the OS, like with VMs, and PaaS means Azure manages the platform and I manage only my app and data, like with App Service and Azure SQL."

</details>

<details><summary>Q21. Explain the traffic flow from a user on the internet to an application in a container in a pod.</summary>

A typical AKS setup with an ingress controller:

```text
User's browser
  1. DNS: app.example.com ──► public IP (of Front Door / App Gateway / Load Balancer)
  2. Azure Front Door or Application Gateway (TLS, WAF)            [optional]
  3. Azure Load Balancer (public IP)  ──► AKS node
  4. Ingress controller Service (type LoadBalancer) ──► ingress pod (NGINX)
  5. Ingress rule: host + path ──► backend Service (ClusterIP)
  6. Service ──► one of the healthy pod IPs (Endpoints)
  7. Pod ──► container port (for example 8080) ──► application
```

### Step by step

1. **DNS:** the user types `app.example.com`. DNS returns the public IP of the entry point.
2. **Edge / WAF (optional):** Front Door or Application Gateway terminates TLS, checks the WAF rules, and forwards the request.
3. **Azure Load Balancer:** AKS creates it for any Service of type `LoadBalancer`. It sends the traffic to a node.
4. **Ingress controller:** the NGINX ingress controller pod receives the request.
5. **Ingress rules:** it matches the **host** and **path** (for example `/api` → `api-service`) and forwards to that **ClusterIP Service**.
6. **Service:** the Service has a stable virtual IP. **kube-proxy** (iptables/IPVS) or the CNI sends the request to one of the **ready** pod IPs.
7. **Pod and container:** the request reaches the pod IP on the `targetPort`, and the container's application handles it.

The response goes back the same way.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
spec:
  ingressClassName: nginx
  tls:
    - hosts: [app.example.com]
      secretName: app-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8080
```

**With the Application Gateway Ingress Controller (AGIC) or Application Gateway for Containers,** the gateway sends traffic **directly to the pod IPs**, so there is no in-cluster NGINX hop.

**Only ready pods get traffic:** a pod is added to the Service endpoints only when its **readiness probe** passes.

### Interview-ready answer

> "The user's DNS lookup returns the public IP of the entry point, usually Front Door or Application Gateway with WAF. From there the traffic reaches the Azure Load Balancer that AKS created for the ingress controller's LoadBalancer Service. The NGINX ingress controller matches the host and path in the Ingress rules and forwards to a ClusterIP Service. The Service, through kube-proxy, sends the request to one of the ready pod IPs on the target port, and the container handles it. With AGIC, Application Gateway sends traffic straight to the pod IPs."

</details>

<details><summary>Q22. What is Cloud NAT?</summary>

**Cloud NAT** is **Google Cloud's** managed NAT service. It lets **private resources without public IPs** (VMs, GKE nodes) make **outbound** connections to the internet, for example to download packages or call external APIs. It does **not** allow inbound connections from the internet.

The equivalents in other clouds:

| Cloud | Service |
| --- | --- |
| Google Cloud | **Cloud NAT** |
| Azure | **Azure NAT Gateway** |
| AWS | **NAT Gateway** |

### Why it is used

- **Security:** VMs and Kubernetes nodes stay private (no public IP), but can still reach the internet outbound.
- **Fixed outbound IP:** all outbound traffic uses the NAT's static public IP(s), so external partners can **allow-list** that IP.
- **Avoid SNAT port exhaustion:** a NAT gateway provides many more SNAT ports than default outbound access or a load balancer's outbound rules, so busy apps do not run out of outbound connections.

### Azure example: NAT Gateway on a subnet

```bash
az network public-ip create -g rg-net -n pip-nat --sku Standard
az network nat gateway create -g rg-net -n nat-app --public-ip-addresses pip-nat --idle-timeout 10
az network vnet subnet update -g rg-net --vnet-name vnet-app -n snet-aks --nat-gateway nat-app
```

For AKS you can use `--outbound-type managedNATGateway` or `userAssignedNATGateway`.

### Interview-ready answer

> "Cloud NAT is Google Cloud's managed NAT service. It lets private VMs and GKE nodes without public IPs make outbound internet connections, while blocking inbound connections. In Azure the equivalent is NAT Gateway, which I attach to a subnet. It gives a fixed outbound IP that partners can allow-list, keeps workloads private, and provides enough SNAT ports to avoid outbound connection failures."

</details>

<details><summary>Q23. What is the difference between a stage and a job in an Azure DevOps pipeline?</summary>

A pipeline is built like this: **Pipeline → Stages → Jobs → Steps**.

| | Stage | Job |
| --- | --- | --- |
| What it is | A **major phase** of the pipeline, for example Build, Deploy Dev, Deploy Prod | A **set of steps that runs on one agent** |
| Contains | One or more jobs | Steps (tasks and scripts) |
| Runs on | Not an agent itself; its jobs pick agents | **One agent** per job; each job gets a fresh agent |
| Order by default | Stages run **one after another** | Jobs in the same stage run **in parallel** (if agents are available) |
| Dependencies | `dependsOn` and `condition` between stages | `dependsOn` and `condition` between jobs |
| Approvals and checks | Yes, through **environments** (approvals, business hours, branch control) | No approvals on a job itself; a `deployment` job targets an environment |
| Sharing files | Through **pipeline artifacts** | Jobs do not share a file system; use artifacts or output variables |
| Rerun | You can rerun a failed stage | Rerun failed jobs within a stage |

### Example

```yaml
stages:
  - stage: Build
    jobs:
      - job: BuildApi
        pool:
          vmImage: ubuntu-latest
        steps:
          - script: dotnet build
          - publish: $(Build.ArtifactStagingDirectory)
            artifact: api

      - job: BuildWeb               # runs in parallel with BuildApi
        pool:
          vmImage: ubuntu-latest
        steps:
          - script: npm ci && npm run build

  - stage: DeployProd
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployApi
        environment: prod           # approval is configured on this environment
        strategy:
          runOnce:
            deploy:
              steps:
                - script: echo "deploying"
```

### Interview-ready answer

> "A stage is a major phase of the pipeline, like Build or Deploy to Prod, and a job is a group of steps that runs on one agent. A stage contains one or more jobs. By default stages run in order and jobs in the same stage run in parallel. Each job gets a fresh agent, so jobs share files through artifacts. Approvals and checks are applied at the stage level through environments, which is why I put each environment in its own stage."

</details>

<details><summary>Q24. Give a particular use case where you would use VPA.</summary>

The **Vertical Pod Autoscaler (VPA)** changes the **CPU and memory requests (and limits) of a pod**, not the number of pods. HPA scales **out** (more pods); VPA scales **up** (bigger pods).

### Use case (real-world example)

> We had a **nightly report/ETL worker** on AKS that ran as a **single replica**. It could not run as several copies because it processed one batch at a time. The team had guessed the requests: `cpu: 250m, memory: 512Mi`. As data grew, the pod got **OOMKilled** and was CPU-throttled, so the job ran for hours. Other services had the opposite problem: they requested `2 CPU / 4Gi` but used about 10% of it, so nodes looked "full" and we paid for capacity we did not use.
>
> We first deployed VPA in **`Off` (recommendation) mode** for a week to see real usage. Then we switched the worker to **`Auto`** with a `minAllowed` and `maxAllowed` range. VPA raised its memory to about 1.5Gi and the OOMKills stopped. For the over-sized services we used the recommendations to **right-size requests**, which let more pods fit per node and reduced the node count.

### Example manifest

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: report-worker-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: report-worker
  updatePolicy:
    updateMode: "Auto"        # Off = recommend only, Initial = only on pod creation, Recreate/Auto = evict and resize
  resourcePolicy:
    containerPolicies:
      - containerName: "*"
        minAllowed:
          cpu: 250m
          memory: 512Mi
        maxAllowed:
          cpu: "2"
          memory: 4Gi
        controlledResources: ["cpu", "memory"]
```

```bash
# On AKS, VPA is a managed add-on
az aks update -g rg-aks -n aks-prod --enable-vpa

kubectl get vpa
kubectl describe vpa report-worker-vpa   # shows Target, Lower Bound, Upper Bound recommendations
```

### Update modes

| Mode | What VPA does |
| --- | --- |
| `Off` | Only gives **recommendations**; changes nothing. Good for right-sizing. |
| `Initial` | Sets requests **only when a pod is created**; never evicts running pods. |
| `Recreate` / `Auto` | **Evicts** pods whose requests are far from the recommendation, and they restart with new values. (Newer Kubernetes versions can resize in place.) |

### When I would use VPA

- **Single-replica or stateful workloads** that cannot scale out: batch jobs, workers, some databases, legacy apps.
- **Right-sizing**: you do not know the correct requests, so you use `Off` mode to get recommendations.
- Workloads that keep getting **OOMKilled** or **CPU-throttled** because requests were guessed too low.
- **Cost saving**: over-requested pods waste node capacity.

### Things to be careful about

- **Do not use VPA and HPA on the same metric** (CPU or memory) for the same workload; they fight each other. You can combine them if HPA uses a custom or external metric (for example requests per second or queue length).
- In `Auto`/`Recreate` mode, pods are **restarted** to apply new values, so set a **PodDisruptionBudget** and run more than one replica where you can.
- Always set **`maxAllowed`**, or one memory leak can make VPA request a huge pod that no node can fit.
- VPA needs the **metrics server** and some days of history to give good recommendations.

| | HPA | VPA |
| --- | --- | --- |
| Changes | Number of pods | CPU/memory per pod |
| Best for | Stateless apps with changing traffic | Single-replica, stateful or unknown sizing |
| Restarts pods | No | Yes, in `Auto`/`Recreate` mode |

### Interview-ready answer

> "VPA adjusts the CPU and memory requests of pods instead of the number of pods. I use it for workloads that cannot scale out, like a single-replica batch worker. In one case our nightly report worker kept getting OOMKilled because its memory request was a guess. I ran VPA in Off mode for a week to get recommendations, then switched it to Auto with min and max limits, and the OOMKills stopped. I also use Off mode to right-size over-requested services and save node cost. I don't run VPA and HPA on the same CPU or memory metric, because they conflict."

</details>
