# EPAM - Interview Questions

## Shell scripting

## Q1. Write a shell script to ping a list of IPs

If you want to ping a list of IP addresses using shell scripting, a simple DevOps-friendly script is:

```bash
#!/bin/bash

for ip in 192.168.1.1 192.168.1.2 192.168.1.3
do
    if ping -c 2 -W 2 "$ip" > /dev/null 2>&1
    then
        echo "$ip is UP"
    else
        echo "$ip is DOWN"
    fi
done
```

### Better approach: IPs from a file

Create `ips.txt`:

```text
192.168.1.1
192.168.1.2
192.168.1.3
8.8.8.8
```

Script:

```bash
#!/bin/bash

while read -r ip
do
    if ping -c 2 -W 2 "$ip" > /dev/null 2>&1
    then
        echo "$ip is UP"
    else
        echo "$ip is DOWN"
    fi
done < ips.txt
```

### Interview explanation

> "I can maintain the list of IP addresses in a file and use a shell script to read each IP one by one. I use the ping command with a limited number of packets and a timeout. Based on the exit status of ping, I print whether the server is UP or DOWN."

Important options:

- `-c 2` → send 2 ping packets
- `-W 2` → wait up to 2 seconds for a response
- `$?` → exit status of the previous command
- `> /dev/null 2>&1` → suppress the ping output

### Interview-ready version: CSV report with IP, status and response time

For an interview, make it slightly more practical by generating a CSV with `IP`, `Status` and `Response_Time_ms`.

`check_ips.sh`:

```bash
#!/bin/bash

INPUT_FILE="ips.txt"
OUTPUT_FILE="ping_report.csv"

echo "IP,Status,Response_Time_ms" > "$OUTPUT_FILE"

while read -r ip
do
    # Skip empty lines
    [ -z "$ip" ] && continue

    # Get ping response time
    response=$(ping -c 1 -W 2 "$ip" 2>/dev/null)

    if echo "$response" | grep -q "time="
    then
        time=$(echo "$response" | grep -o "time=[0-9.]*" | cut -d= -f2)

        echo "$ip,UP,$time" >> "$OUTPUT_FILE"
    else
        echo "$ip,DOWN,N/A" >> "$OUTPUT_FILE"
    fi

done < "$INPUT_FILE"

echo "Ping report generated: $OUTPUT_FILE"
```

`ips.txt`:

```text
8.8.8.8
1.1.1.1
192.168.1.10
192.168.1.20
```

Run:

```bash
chmod +x check_ips.sh
./check_ips.sh
```

Generated `ping_report.csv`:

```text
IP,Status,Response_Time_ms
8.8.8.8,UP,18.4
1.1.1.1,UP,12.7
192.168.1.10,DOWN,N/A
192.168.1.20,UP,2.31
```

### Interview explanation

> "I have a list of IPs in a file. The script reads each IP using a while loop and performs one ping with a 2-second timeout. If the ping succeeds, I extract the response time from the ping output and mark the server as UP. Otherwise, I mark it as DOWN. Finally, I write the IP, status, and response time into a CSV report."

**Be careful:** a ping failure does not always mean the server is down. ICMP may be blocked by a firewall. In a real production check, I would also validate the required service port, such as 443 or 22.

---

## Q2. Write a shell script to check SSH login on all servers

Check SSH connectivity and login for a list of servers, and generate a CSV report.

`servers.txt`:

```text
192.168.1.10
192.168.1.11
192.168.1.12
10.10.10.20
```

`check_ssh.sh`:

```bash
#!/bin/bash

INPUT_FILE="servers.txt"
OUTPUT_FILE="ssh_report.csv"
SSH_USER="devops"

echo "Server,SSH_Status" > "$OUTPUT_FILE"

while read -r server
do
    [ -z "$server" ] && continue

    if ssh -n -o BatchMode=yes \
           -o ConnectTimeout=5 \
           -o StrictHostKeyChecking=no \
           "$SSH_USER@$server" "echo OK" > /dev/null 2>&1
    then
        echo "$server,LOGIN_SUCCESS" >> "$OUTPUT_FILE"
        echo "$server : SSH login successful"
    else
        echo "$server,LOGIN_FAILED" >> "$OUTPUT_FILE"
        echo "$server : SSH login failed"
    fi

done < "$INPUT_FILE"

echo "Report generated: $OUTPUT_FILE"
```

Output (`ssh_report.csv`):

```text
Server,SSH_Status
192.168.1.10,LOGIN_SUCCESS
192.168.1.11,LOGIN_FAILED
192.168.1.12,LOGIN_SUCCESS
10.10.10.20,LOGIN_SUCCESS
```

### Common mistake: `ssh` inside a `while read` loop

Without `-n`, `ssh` reads from standard input, which is the same input the loop is reading (`servers.txt`). After the **first successful login**, `ssh` swallows the remaining lines and the loop silently stops checking the other servers.

Fix it with either:

- `ssh -n ...` (redirects ssh's stdin from `/dev/null`), or
- `ssh ... < /dev/null`

Also use a variable such as `SSH_USER` rather than `USER`, so you don't overwrite the shell's built-in `$USER` variable.

### Interview answer

> "I keep the server IPs in a file and use a shell script to loop through them. For each server, I use SSH with BatchMode=yes so the script doesn't wait for a password prompt, and ConnectTimeout=5 to avoid hanging on unreachable servers. I execute a simple echo OK command. Based on the SSH exit status, I mark the server as login successful or failed and generate a CSV report. I also use ssh -n so ssh doesn't consume the loop's input."

### Important

- For automation, use **SSH keys, not passwords**. `BatchMode=yes` prevents the script from interactively asking for credentials.
- `StrictHostKeyChecking=no` is convenient for a lab, but in production prefer a managed `known_hosts` file, so you don't accept unknown host keys silently.
- To check 500+ servers, add **parallel execution** (for example `xargs -P` or GNU `parallel`) so you don't wait for each server one after another.

---

## Q3. Find missing tags in a JSON file with jq

If the requirement is to find JSON objects where a required tag or key is missing, `jq` is a good fit.

### Example `servers.json`

```json
[
  {
    "name": "server1",
    "environment": "prod",
    "owner": "devops"
  },
  {
    "name": "server2",
    "environment": "prod"
  },
  {
    "name": "server3",
    "owner": "devops"
  }
]
```

Suppose the required tags are:

- `name`
- `environment`
- `owner`

### Using jq: list the objects with a missing tag

```bash
jq '.[] | select(.name == null or .environment == null or .owner == null)' servers.json
```

Output:

```json
{
  "name": "server2",
  "environment": "prod"
}
{
  "name": "server3",
  "owner": "devops"
}
```

### Better approach: show exactly which tags are missing

```bash
jq '
.[] |
. as $obj |
{
  name: $obj.name,
  missing_tags: ["name", "environment", "owner"]
    | map(select($obj[.] == null))
}
| select(.missing_tags | length > 0)
' servers.json
```

Output:

```json
{
  "name": "server2",
  "missing_tags": [
    "owner"
  ]
}
{
  "name": "server3",
  "missing_tags": [
    "environment"
  ]
}
```

### Common mistake

Inside `map(...)`, `.` is the **tag name** (a string), not the server object. So this does **not** work:

```bash
# Wrong: fails with "Cannot index string with string"
jq '.[] | {name: .name, missing_tags: ["environment", "owner"] | map(select(. as $tag | .[$tag] == null))}' servers.json
```

That's why the working version saves the object first with `. as $obj` and then checks `$obj[.]`.

### Interview answer

> "I use jq to parse the JSON and check whether the required keys exist. I define the mandatory tags and use select() to identify objects where any required tag is missing. I can also return the resource name along with the exact missing tags, which makes it easier to fix the configuration."

For Azure-style resource JSON (for example from `az resource list`), the same technique can be adapted to check required tags such as `Environment`, `Owner`, `CostCenter` and `Application` across hundreds of resources.

---

## Q4. Write a shell script to check if a file exists (`/etc/config.js`)

```bash
#!/bin/bash

FILE="/etc/config.js"

if [ -f "$FILE" ]; then
    echo "$FILE exists"
else
    echo "$FILE does not exist"
fi
```

### To check any type of file or directory

```bash
if [ -e "/etc/config.js" ]; then
    echo "Path exists"
else
    echo "Path does not exist"
fi
```

### Difference

- `-f` → checks whether it is a **regular file**
- `-e` → checks whether the **path exists**, including files and directories

### Interview answer

> "I use the -f test operator to check whether /etc/config.js is a regular file. If the condition is true, I print that the file exists; otherwise, I handle the missing-file case."

---

## Q5. Write a shell script to delete logs older than N days

Use `find` for this. It is the standard approach in Linux.

### Delete logs older than 7 days

```bash
find /var/log -type f -name "*.log" -mtime +7 -delete
```

### Safer version: check before deleting

First, list the files:

```bash
find /var/log -type f -name "*.log" -mtime +7
```

If the output is correct, run:

```bash
find /var/log -type f -name "*.log" -mtime +7 -delete
```

### Shell script

```bash
#!/bin/bash

LOG_DIR="/var/log"
DAYS=7

find "$LOG_DIR" -type f -name "*.log" -mtime +"$DAYS" -delete

echo "Deleted logs older than $DAYS days"
```

### Interview answer

> "I use the find command with -mtime to identify log files older than the required number of days. I first verify the files using find without -delete, and once confirmed, I use -delete to remove them."

### Important

- `-mtime +7` matches files last modified **more than 7 full days ago**. `find` counts age in whole days and drops the fraction, so a file that is 7 days and 1 hour old is **not** matched; it must be at least 8 days old.
- For production cleanup, verify the target directory carefully before using `-delete`. For logs that a running service is still writing to, prefer `logrotate`.

---

## Q6. Write a shell script to check disk usage

To check disk usage in shell scripting, the basic command is `df`.

### Check disk usage

```bash
df -h
```

Example:

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   42G  8.0G  84% /
/dev/sdb1       100G   60G   40G  60% /data
```

### Check if disk usage is above 80%

```bash
df -h | awk 'NR>1 && $5+0 > 80 {print $0}'
```

This prints the filesystems where usage is greater than 80%.

### Shell script with alert

```bash
#!/bin/bash

THRESHOLD=80

df -P | awk 'NR>1 {print $5, $6}' | while read -r usage mount
do
    usage=${usage%\%}

    if [ "$usage" -gt "$THRESHOLD" ]; then
        echo "WARNING: $mount is ${usage}% full"
    fi
done
```

`df -P` (POSIX format) keeps each filesystem on one line, so the columns stay in the same place even for long device names.

### Check which directories are consuming space

```bash
du -sh /var/* 2>/dev/null | sort -h
```

For the largest directories:

```bash
du -sh /var/* 2>/dev/null | sort -hr | head -10
```

### Interview answer

> "I use df -h to check filesystem-level disk utilization. If usage crosses a threshold such as 80%, I generate an alert. Then I use du -sh to identify which directories are consuming the most space and investigate large logs, temporary files, or application data."

---

## Terraform

## Q7. Write a Terraform file to create a Resource Group

For Azure, you can create a Resource Group with a simple Terraform configuration.

`main.tf`:

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-devops-demo"
  location = "East US"

  tags = {
    Environment = "Dev"
    Owner       = "DevOps"
  }
}
```

### Commands

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

To delete it:

```bash
terraform destroy
```

### Interview explanation

> "I use the azurerm provider to interact with Azure. The azurerm_resource_group resource creates the Resource Group with a name and Azure region. I can also add tags for environment and ownership. I run terraform init, validate the configuration, review the plan, and then run terraform apply."

### Important points

- Terraform tracks the Resource Group in the **state file**. If you delete the Resource Group manually from Azure, Terraform detects the drift during the next `plan`.
- With **azurerm 4.x**, the provider needs a subscription ID. Set it in the provider block (`subscription_id = "<id>"`) or with the `ARM_SUBSCRIPTION_ID` environment variable, otherwise `terraform plan` fails.

---

## Azure

## Q8. Give a brief on Azure Batch, Microsoft Entra ID and Azure Monitor

### 1. Azure Batch

Azure Batch is a service used to run **large-scale parallel and high-performance computing (HPC)** workloads.

- Creates and manages a pool of VMs.
- Runs jobs across multiple VMs in parallel.
- Automatically scales compute resources based on the workload.
- Useful for batch processing, simulations, rendering, data processing and similar jobs.

**Interview answer:**

> "Azure Batch is a managed service for running large-scale parallel workloads. It automatically manages a pool of VMs and distributes jobs across them, which is useful when we need high compute capacity without manually managing individual VMs."

### 2. Microsoft Entra ID

Microsoft Entra ID, formerly **Azure Active Directory (Azure AD)**, is Microsoft's cloud-based **identity and access management** service.

- User and group management.
- Authentication and authorization.
- Single sign-on (SSO) for applications.
- Multi-factor authentication (MFA) and Conditional Access.
- Managed identities for Azure resources.
- Application and service authentication.

**Interview answer:**

> "Microsoft Entra ID is Microsoft's cloud identity and access management service. We use it for user authentication, authorization, SSO, MFA, and managing identities for applications and Azure resources."

**DevOps example:** an Azure DevOps pipeline can use a managed identity or service principal to securely access Azure resources without storing passwords in the pipeline.

### 3. Azure Monitor

Azure Monitor is Microsoft's **monitoring and observability** service for Azure resources and applications.

It collects and uses:

- **Metrics** → CPU, memory, requests, latency and so on.
- **Logs** → application and infrastructure logs (Log Analytics).
- **Alerts** → notify when a condition is triggered.
- **Application Insights** → application performance monitoring.

**Interview answer:**

> "Azure Monitor is used to monitor the health and performance of Azure resources and applications. We collect metrics and logs, create alerts based on thresholds, and use Application Insights and Log Analytics to troubleshoot application and infrastructure issues."

### Easy way to remember

| Service | Main purpose |
| --- | --- |
| Azure Batch | Run large-scale jobs |
| Microsoft Entra ID | Identity and access |
| Azure Monitor | Monitoring and alerts |

---

## Q9. Give a brief on Azure Container Apps and Azure Container Instances

### 1. Azure Container Apps

Azure Container Apps (ACA) is a **fully managed, serverless container platform** for running containerized applications without managing Kubernetes infrastructure.

- Supports containers, microservices, APIs and background jobs.
- Built-in autoscaling using KEDA.
- Supports revisions and traffic splitting.
- Supports internal and external ingress.
- Integrates with Azure services such as Container Registry, Managed Identity and Log Analytics.
- A good choice when you need container orchestration features but don't want to manage AKS.

**Interview answer:**

> "Azure Container Apps is a serverless container platform used to run microservices and APIs without managing the underlying Kubernetes infrastructure. It provides autoscaling, ingress, revisions and traffic management. I would choose Container Apps when I need containerized applications with less operational overhead than AKS."

### 2. Azure Container Instances (ACI)

Azure Container Instances is a service for **running individual containers directly in Azure** without managing VMs or Kubernetes.

- Very quick container startup.
- No VM management.
- Suitable for short-lived or simple workloads.
- Useful for development, testing, batch jobs and CI/CD tasks.
- Supports Linux and Windows containers.
- Does not provide the full orchestration capabilities of Kubernetes.

**Interview answer:**

> "Azure Container Instances allows us to run containers directly in Azure without managing virtual machines or a Kubernetes cluster. It is useful for simple, short-lived workloads, testing and batch jobs where we don't need Kubernetes orchestration."

### Container Apps vs. Container Instances

| Feature | Container Apps | Container Instances |
| --- | --- | --- |
| Main use | Microservices / APIs | Simple containers |
| Scaling | Built-in autoscaling | Basic / manual scaling |
| Kubernetes | Managed abstraction | No Kubernetes orchestration |
| Revisions | Yes | No |
| Traffic splitting | Yes | No |
| Best for | Production microservices | Simple / short-lived workloads |
| Operational effort | Low | Very low |

### Easy way to remember

- **ACI** = run a container.
- **Container Apps** = run and scale an application made of containers.

---

## Q10. Azure Functions: generate a PDF and store it in a Storage Account <em>(scenario)</em>

The question in the interview was short ("Azure Functions, create a PDF in a storage account"). A common full version of this scenario is:

> "A user uploads a document to Azure Storage. You need to generate a PDF from that document using Azure Functions and store the generated PDF back in the Storage Account. How would you design and implement this solution?"

### Architecture

```text
User
  |
  | Upload document
  v
Azure Blob Storage
  |
  | Blob Created event
  v
Event Grid
  |
  v
Azure Function
  |
  | Generate PDF
  v
Azure Blob Storage
  |
  v
Generated PDF
```

### How it works

1. The user uploads a file, such as `.docx` or `.html`, to a Blob Storage container.
2. Blob Storage raises a **Blob Created** event.
3. Event Grid triggers the Azure Function.
4. The Function reads the uploaded file from Blob Storage.
5. The Function uses a suitable PDF-generation library to convert the content into a PDF.
6. The generated PDF is uploaded to another container, for example:

```text
input/
    invoice123.docx

output/
    invoice123.pdf
```

7. The Function logs success or failure to Application Insights / Azure Monitor.

### How would you secure it?

I would **not** store the Storage Account key in the Function configuration. Instead:

```text
Azure Function
      |
      | Managed Identity
      v
Azure Storage Account
```

Assign the Function's managed identity the right RBAC role:

- **Storage Blob Data Reader** → read input files
- **Storage Blob Data Contributor** → read and write blobs

Store any other application secrets in Azure Key Vault.

### What if PDF generation fails?

I would implement:

- Exception handling in the Function.
- Application Insights logging.
- A retry mechanism.
- Dead-letter / error handling for events that keep failing.
- A separate `failed/` (or `error/`) container if the business needs failed files to be kept.

```text
input/
output/
failed/
```

### What if 10,000 files are uploaded at once?

This is an important follow-up.

> "I would avoid processing everything synchronously. Event Grid can trigger the Function for each blob event, and Azure Functions can scale out based on the workload. I would also make the function idempotent so that if the same event is delivered more than once, we don't generate duplicate PDFs."

For heavier or long-running PDF generation, I would put **Service Bus or a Storage Queue** in between:

```text
Blob Storage
     |
 Event Grid
     |
Service Bus / Queue
     |
Azure Function
     |
 Generate PDF
     |
Blob Storage
```

This gives better control over retries, throttling and workload spikes.

### Interview-ready answer

> "I would use Azure Blob Storage as the input and output storage. When a document is uploaded, a Blob Created event can be published through Event Grid and trigger an Azure Function. The Function reads the document, generates the PDF using a suitable library, and writes the PDF to an output container. I would use Managed Identity with Azure RBAC instead of storage account keys. For monitoring, I would use Application Insights and Azure Monitor. I would also implement retry and error handling. If the workload is high, I would put Service Bus or a Storage Queue between the event and the Function so that processing can be controlled and scaled safely."

### Likely follow-up questions

1. **Why an Azure Function instead of a VM?**
   "The workload is event-driven and may be intermittent, so Functions removes server management and scales automatically."
2. **Why Event Grid?**
   "Because the processing starts when a blob is created. Event Grid is designed for event-driven scenarios."
3. **How do you prevent duplicate PDF generation?**
   "I make the function idempotent. Before generating the PDF, I check whether the output blob already exists, or keep a processing record."
4. **How do you authenticate to Storage?**
   "Using the Function's Managed Identity with the right Storage Blob Data RBAC roles."
5. **How do you monitor failures?**
   "Application Insights and Azure Monitor alerts. I monitor function failures, execution duration, exceptions, and retry and dead-letter counts."
6. **What if PDF generation takes several minutes?**
   "I would use an asynchronous design with a queue, and pick a Functions hosting plan whose execution time limit fits. For very heavy processing, I would evaluate Container Apps Jobs or Azure Batch instead of forcing everything into a single Function execution."

---

## Q11. How do you reduce costs in Azure?

For a DevOps interview, answer this as a **practical process**, not just a list of Azure services.

### Interview-ready answer

> "I optimize Azure costs by first analyzing the current spending using Azure Cost Management and Advisor. I identify the resources with high utilization or unnecessary spending. Then I right-size VMs and AKS node pools, shut down non-production resources outside working hours, remove unused disks and public IPs, and use autoscaling where appropriate.
>
> For predictable workloads, I evaluate Azure Reservations or Savings Plans. For suitable workloads, I use Spot VMs. I also optimize storage by selecting the appropriate storage tier and lifecycle policies.
>
> At the governance level, I use resource tagging such as Environment, Application, Owner and CostCenter, and configure budgets and cost alerts. I regularly review the cost trends and remove orphaned or unused resources."

### Areas I would check

| Area | Cost optimization |
| --- | --- |
| VMs | Right-size, auto-shutdown Dev/QA, Reserved Instances / Savings Plans |
| AKS | Right-size node pools, autoscaling, Spot nodes for suitable workloads |
| Storage | Lifecycle policies, Hot/Cool/Archive tiers, remove unused disks and snapshots |
| Networking | Review unneeded NAT Gateways, public IPs, data transfer and load balancers |
| Database | Right-size the SKU, scale down non-prod, use the right service tier |
| Monitoring | Control excessive Log Analytics ingestion and retention |
| Unused resources | Remove unattached disks, IPs, NICs, old snapshots and test resources |
| Governance | Tags, budgets, alerts and Azure Policy |

### Real-time example

If the interviewer asks: *"You suddenly notice the Azure cost has increased significantly. What will you do?"*

> "First, I would check Cost Management to identify which subscription, resource group and resource caused the increase. Then I would compare the current cost with previous days or months. I would check for newly created resources, increased VM sizes, unexpected scaling, storage growth, data transfer and services that were accidentally left running. Once I identify the cause, I would take corrective action and configure budgets, alerts, tagging and policies to prevent the same issue from happening again."

### Important incident example

If an expensive Azure service was accidentally left running and generated a large bill, don't just say you deleted it. Say:

> "I would first identify the resource and confirm why it was created. I would stop or remove it if it is unnecessary, then review the activity logs to understand how it happened. After that, I would introduce Azure Policy, budgets, cost alerts and appropriate RBAC controls. For non-production environments, I would also implement scheduled shutdowns. The goal is to prevent the same cost issue from recurring."

That is a much stronger answer, because it covers **detection → correction → root cause → prevention**.

---

## Q12. A Storage Account has become public in Azure. How do you remediate it? <em>(scenario)</em>

Answer in this order.

### Interview-ready answer

> "First, I would identify exactly what has become public. I would check the Storage Account networking configuration, public network access, firewall rules, private endpoints, and container-level public access.
>
> If public access is not required, I would disable public network access and allow access only through the required VNet or Private Endpoint. I would also disable anonymous blob access at the storage-account level and verify that containers are not configured for public access.
>
> Then I would check IAM and RBAC permissions to make sure no users or applications have excessive access. I would review Activity Logs to determine how the configuration became public.
>
> Finally, I would enforce the configuration using Azure Policy and Terraform so that the setting cannot accidentally be changed again."

### Key settings to check

#### 1. Storage account public network access

Set **Public network access = Disabled**, then use:

```text
Private Endpoint
       |
       v
     VNet
       |
       v
Storage Account
```

If public access is genuinely required, restrict it to **selected networks / IPs** rather than allowing all networks.

#### 2. Anonymous blob access

Check that **Allow Blob anonymous access = Disabled**.

Also verify that each container's **Public access level** is not `Blob` or `Container`. It should normally be `Private`.

#### 3. RBAC / IAM

Review:

- Storage Blob Data Reader
- Storage Blob Data Contributor
- Storage Blob Data Owner
- Subscription and resource-group permissions

Remove unnecessary permissions and follow least privilege.

#### 4. Private Endpoint

For applications running inside Azure, use:

```text
AKS / VM / App Service
        |
       VNet
        |
Private Endpoint
        |
Storage Account
```

Also verify that Private DNS resolution is working.

### Prevention

Use **Azure Policy** to audit or deny insecure configurations, for example:

```text
Deny: storage accounts with public network access enabled
```

You can also enforce it through Terraform:

```hcl
resource "azurerm_storage_account" "example" {
  name                = "stexample123"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

  public_network_access_enabled   = false
  allow_nested_items_to_be_public = false
}
```

### Strong troubleshooting flow

```text
Identify exposure
       ↓
Check public network access
       ↓
Check container anonymous access
       ↓
Check firewall / IP rules
       ↓
Check Private Endpoint / DNS
       ↓
Review RBAC
       ↓
Check Activity Logs
       ↓
Remediate
       ↓
Azure Policy + Terraform
       ↓
Monitor continuously
```

**One important distinction:** "the storage account is public" can mean different things. **Public network access** and **anonymous blob/container access** are separate controls, so check both.

---

## Q13. Store a database connection string securely with Key Vault and Managed Identity <em>(scenario)</em>

A good version of this scenario is:

> "Your application is running on Azure App Service / AKS and needs to connect to an Azure PostgreSQL database. The database connection string contains sensitive information. How would you securely manage the connection string using Azure Key Vault and Managed Identity?"

### Architecture

```text
Application
   |
   | Managed Identity
   v
Azure Key Vault
   |
   | Connection string
   v
PostgreSQL
```

### Implementation

#### 1. Enable Managed Identity

Enable a **system-assigned managed identity** on the App Service or AKS workload.

```text
Application
    |
    | Identity
    v
Microsoft Entra ID
```

The application doesn't need a username or password to authenticate to Key Vault.

#### 2. Store the connection string in Key Vault

For example:

```text
Secret name:
postgres-connection-string

Secret value:
Host=postgres.example.com;
Database=appdb;
Username=appuser;
Password=********;
```

The password is never stored in the application code or the Git repository.

#### 3. Give the identity access to Key Vault

Assign the application's managed identity the minimum required permission, for example **Key Vault Secrets User**. This follows the principle of least privilege.

#### 4. The application retrieves the secret

```text
Application
     |
     | Managed Identity token
     v
Microsoft Entra ID
     |
     v
Key Vault
     |
     | Secret
     v
Application
     |
     v
PostgreSQL
```

The application uses the Azure SDK or a Key Vault integration to retrieve the secret at runtime. On App Service, a **Key Vault reference** in the app settings (`@Microsoft.KeyVault(SecretUri=...)`) does this without code changes.

### If the application runs in AKS

Use **Microsoft Entra Workload ID** rather than putting a service principal secret inside a Kubernetes Secret.

```text
AKS Pod
   |
   | Workload Identity
   v
Microsoft Entra ID
   |
   v
Key Vault
   |
   v
PostgreSQL connection string
```

Another Kubernetes option is the **Secrets Store CSI Driver** with the Azure Key Vault provider, which mounts Key Vault secrets into the Pod.

### Interview-ready answer

> "I would never hardcode the database connection string or password in the application or Git repository. I would store the connection string as a secret in Azure Key Vault. I would enable Managed Identity on the application, or Workload Identity if the application is running on AKS. I would grant that identity only the required Key Vault secret access, such as Key Vault Secrets User. At runtime, the application authenticates to Key Vault using its identity and retrieves the connection string. The application then uses that connection string to connect to PostgreSQL. I would also use Private Endpoint and private DNS for Key Vault and PostgreSQL where required, and monitor Key Vault access through Azure Monitor."

### Follow-up: "What happens when the database password changes?"

> "I don't update the password in the application code. I update the secret in Key Vault. The application retrieves the current secret based on the application's secret-refresh mechanism. If the application caches the secret, I would configure an appropriate refresh interval or restart/reload mechanism."

**Even better, if the interviewer asks how to remove the password completely:** Azure Database for PostgreSQL Flexible Server supports **Microsoft Entra authentication**. The application's managed identity can then log in to the database with a token, so there is no database password to store or rotate at all.

### Security flow to remember

```text
No password in code
        ↓
Secret → Key Vault
        ↓
Managed Identity / Workload Identity
        ↓
RBAC → Key Vault
        ↓
Application gets the secret
        ↓
Private connection → PostgreSQL
```

This is the clean answer the interviewer is looking for: **Key Vault stores the secret, Managed Identity authenticates the application, RBAC controls access, and the database stays private where possible.**

---

## Q14. How do you restrict a developer's access instead of giving the Contributor role in Azure?

The right approach is **least-privilege RBAC**. Don't give developers the broad Contributor role unless they actually need it.

### Interview-ready answer

> "I would first understand what actions the developer needs to perform. Instead of assigning Contributor, I would create or use a more specific Azure RBAC role that provides only those required permissions. I would assign it at the lowest possible scope, such as a specific resource instead of the entire subscription. If no built-in role exactly matches the requirement, I would create a custom RBAC role with only the required actions."

### Example

Suppose a developer only needs to restart an Azure Web App and view its configuration.

Instead of:

```text
Subscription
    |
    └── Contributor ❌
```

give access only to the required App Service resource:

```text
Developer
   |
   └── Custom RBAC role
          |
          ├── Read Web App
          ├── Read configuration
          └── Restart Web App
```

### Built-in roles

Before creating a custom role, check whether an existing built-in role is enough:

| Requirement | Possible built-in role |
| --- | --- |
| View resources only | Reader |
| Manage VMs | Virtual Machine Contributor |
| Manage AKS | Azure Kubernetes Service Contributor Role |
| Read and write Storage blob data | Storage Blob Data Contributor |
| Manage Web Apps | Website Contributor (and Web Plan Contributor for App Service plans) |
| Read Key Vault secrets | Key Vault Secrets User |
| Manage Key Vault secrets | Key Vault Secrets Officer |

The exact role depends on what the developer actually needs.

### Scope matters

Don't assign the role at subscription level if it isn't necessary. Prefer:

```text
Subscription
   └── Resource Group
        └── Specific resource
             └── Developer role
```

rather than:

```text
Subscription
   └── Contributor ❌
```

### Custom role example

If no built-in role is suitable:

```json
{
  "Name": "Developer WebApp Operator",
  "IsCustom": true,
  "Description": "Read and restart web apps in one resource group",
  "Actions": [
    "Microsoft.Web/sites/read",
    "Microsoft.Web/sites/config/read",
    "Microsoft.Web/sites/restart/action"
  ],
  "NotActions": [],
  "AssignableScopes": [
    "/subscriptions/<subscription-id>/resourceGroups/<resource-group>"
  ]
}
```

Create it with `az role definition create --role-definition @role.json`, then assign it to the developer (or, better, to an Entra group) at the resource-group or resource scope.

### Also use PIM

For sensitive production access, use **Microsoft Entra Privileged Identity Management (PIM)**. Instead of permanent permissions:

```text
Developer
   ↓
Eligible for production access
   ↓
Request / approval
   ↓
Temporary role
   ↓
Access expires
```

### Strong final interview answer

> "I follow the principle of least privilege. I first identify exactly what permissions the developer requires, then use the closest built-in Azure RBAC role instead of Contributor. I assign it at the lowest required scope, preferably a specific resource or resource group. If no built-in role meets the requirement, I create a custom role with only the necessary actions. For production access, I prefer PIM with just-in-time and time-bound access. This prevents developers from accidentally modifying or deleting unrelated Azure resources."

---

## Q15. What is Azure Policy?

Azure Policy is an Azure **governance** service used to enforce organizational rules and compliance requirements on Azure resources.

It can **audit, deny, modify or deploy** configurations based on defined rules.

### Simple example

Suppose your organization says: *"All Storage Accounts must have public network access disabled."* You can create an Azure Policy:

```text
       Storage Account
             |
             v
   Public network access?
             |
       ┌─────┴─────┐
       |           |
   Disabled     Enabled
       |           |
    Allowed     Denied ❌
```

### Common use cases

- Prevent public access to Storage Accounts
- Require specific Azure regions
- Require mandatory tags such as Environment and Owner
- Prevent creation of expensive or unwanted resource SKUs
- Require encryption
- Enforce HTTPS
- Audit resources that don't comply
- Automatically add or modify certain configurations

### Azure Policy effects

Some common effects:

| Effect | Meaning |
| --- | --- |
| Deny | Prevents creating or updating a non-compliant resource |
| Audit | Allows the resource but reports it as non-compliant |
| Modify | Changes or adds resource configuration (for example tags) |
| DeployIfNotExists | Deploys a required configuration if it is missing |
| Disabled | The policy is not evaluated |

### Azure Policy vs. RBAC

This is a common interview question.

**RBAC answers: who can do what?**

```text
Developer → Contributor
Developer → Reader
```

**Azure Policy answers: which configurations are allowed in Azure?**

```text
Developer has Contributor access
          ↓
Tries to create a public Storage Account
          ↓
Azure Policy → DENY
```

So even if a user has Contributor, an Azure Policy can prevent certain resource configurations.

### Interview-ready answer

> "Azure Policy is a governance service used to enforce organizational standards and compliance across Azure resources. For example, I can create a policy to deny Storage Accounts with public network access enabled, enforce mandatory tags, or restrict deployments to approved regions. RBAC controls who can perform actions, while Azure Policy controls which resource configurations are allowed."

---

## DevSecOps

## Q16. Apart from pre-commit hooks, what other hooks and checks are there, inside and outside Git, and what is their purpose?

Think of pre-commit hooks as **one layer in a larger validation chain**. In DevOps, you can have checks on the developer machine, in the Git repository, in the CI/CD pipeline, in Kubernetes, in Terraform, and at the Azure governance level.

### 1. Git hooks

Git has several hooks that can run automatically.

| Hook | When it runs | Typical purpose |
| --- | --- | --- |
| `pre-commit` | Before the commit is created | Linting, formatting, secret scan |
| `commit-msg` | After the commit message is entered | Validate the commit message format |
| `pre-push` | Before `git push` | Run tests, security checks |
| `post-commit` | After the commit | Notifications, local automation |
| `pre-rebase` | Before a rebase | Prevent unsafe rebases |
| `post-checkout` | After a checkout | Environment or setup tasks |
| `post-merge` | After a merge | Dependency or setup tasks |
| `pre-receive` | Server side, before accepting a push | Enforce repository rules |
| `update` | Server side, per branch / ref | Control branch updates |
| `post-receive` | Server side, after a push | Trigger deployment or notification |

Most important for interviews:

**pre-commit**

```text
Developer
   ↓
git commit
   ↓
pre-commit hooks
   ↓
lint / format / secret scan
   ↓
Commit
```

**pre-push**

```text
git push
   ↓
pre-push hook
   ↓
tests / validation
   ↓
Remote repository
```

### 2. The pre-commit framework

The **pre-commit** framework is commonly used to manage Git hooks consistently across a team.

Example `.pre-commit-config.yaml` (pin each `rev` to the latest release):

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
```

Purpose:

- YAML validation
- JSON validation
- Remove trailing whitespace
- Detect merge conflicts
- Detect secrets
- Run formatters and linters

### 3. Terraform checks

For Terraform projects, these are very common.

- **`terraform fmt`** formats Terraform code: `terraform fmt -check`
- **`terraform validate`** checks that the configuration is syntactically and structurally valid.
- **TFLint** (`tflint`) catches potential errors and best-practice issues, such as a wrong Azure resource configuration, an invalid argument or deprecated configuration.
- **Checkov** (`checkov -d .`) scans IaC for security and compliance issues, such as a storage account that allows public access, an NSG that allows unrestricted inbound traffic, or missing encryption.
- **tfsec** (`tfsec .`) is a Terraform-focused security scanner. In modern setups, many teams use **Trivy** instead, because tfsec has been merged into it.
- **Trivy** (`trivy config .`) scans Terraform/IaC, containers, filesystems and more.

### 4. Secret scanning

These are extremely important. They stop credentials and sensitive information from entering the repository.

- **Gitleaks** (`gitleaks detect`) detects secrets accidentally committed to Git: cloud keys, Azure credentials, API tokens, passwords and private keys.
- **TruffleHog** is another secret-detection tool:

```bash
trufflehog git file://. --since-commit HEAD~10
```

### 5. Code quality and linting

- **ShellCheck** (`shellcheck script.sh`) detects common shell scripting problems. For example, in `if [ $x = "test" ]` it flags the unquoted `$x`.
- **Pylint** (`pylint script.py`) checks Python code quality, errors, naming and bad practices.
- **Black** (`black .`) formats Python code.
- **Flake8** (`flake8 .`) lints Python code.

### 6. YAML and Kubernetes validation

- **kubeconform** (`kubeconform deployment.yaml`) validates Kubernetes manifests against the Kubernetes schemas.
- **kube-linter** (`kube-linter lint deployment.yaml`) checks manifests for common configuration and security problems.
- **`kubectl apply --dry-run`** validates without creating resources:

```bash
kubectl apply --dry-run=client -f deployment.yaml
kubectl apply --dry-run=server -f deployment.yaml   # server-side validation
```

### 7. Docker checks

- **Hadolint** (`hadolint Dockerfile`) lints Dockerfiles: bad practices, unnecessary packages, poor layer usage, missing version pinning.
- **Trivy** (`trivy image myapp:1.0`) scans container images for OS vulnerabilities, application dependency vulnerabilities, secrets and misconfigurations.

### 8. CI/CD pipeline checks

These don't run as Git hooks. They run after the code reaches the CI system.

```text
Developer
   ↓
Git pre-commit
   ↓
Git push
   ↓
CI pipeline
   ↓
Build
   ↓
Unit tests
   ↓
SonarQube
   ↓
Security scan
   ↓
Docker build
   ↓
Trivy
   ↓
Deploy
```

Common tools:

| Tool | Purpose |
| --- | --- |
| SonarQube | Code quality and security |
| Trivy | Container and IaC scanning |
| Snyk | Dependency and security scanning |
| OWASP Dependency-Check | Dependency vulnerabilities |
| Checkov | IaC security |
| TFLint | Terraform linting |
| ShellCheck | Shell linting |
| Hadolint | Dockerfile linting |

### 9. SonarQube

SonarQube is a **CI/CD quality gate**, not a Git hook. It checks bugs, vulnerabilities, code smells, duplications and test coverage.

```text
Build
  ↓
Unit tests
  ↓
SonarQube scan
  ↓
Quality gate
  ↓
PASS → continue
FAIL → stop the pipeline
```

### 10. Azure Policy

This is **not** a Git hook. It works at the Azure resource / governance level.

```text
Terraform
   ↓
Azure
   ↓
Azure Policy
   ↓
Storage Account has public access
   ↓
DENY
```

Common policies: require tags, restrict Azure regions, deny public Storage Accounts, require HTTPS, require encryption, restrict resource SKUs.

### 11. Kubernetes admission control

These run when Kubernetes resources are submitted to the API server.

- **OPA Gatekeeper** enforces organizational policies, for example "every container must have resource limits".

```text
Deployment
    ↓
Gatekeeper
    ↓
Container must have resource limits
    ↓
PASS / DENY
```

- **Kyverno** is a Kubernetes-native policy engine. Example policies: require resource limits, require labels, disallow privileged containers, allow only approved container registries.
- **Pod Security Admission** is built into Kubernetes and enforces the Pod Security Standards: Privileged, Baseline and Restricted.

### 12. Dependency scanning

For application dependencies:

- **npm:** `npm audit`
- **Maven:** `mvn dependency-check:check` (OWASP Dependency-Check plugin)
- **OWASP Dependency-Check** scans application dependencies for known vulnerabilities.
- **Snyk** can scan source code, dependencies, containers and IaC.

### 13. A good DevOps validation architecture

For an Azure DevOps / Kubernetes / Terraform profile, remember this:

```text
                Developer
                    |
                    v
             Git pre-commit
                    |
       +------------+------------+
       |            |            |
   Formatting    Linting    Secret scan
       |            |            |
       +------------+------------+
                    |
                  Push
                    |
                    v
              CI pipeline
                    |
       +------------+-------------+
       |            |             |
   Terraform    SonarQube       Tests
   validate
       |
 TFLint / Checkov
       |
     Trivy
       |
  Docker build
       |
 Trivy image scan
       |
 Kubernetes validation
       |
       v
     Deploy
       |
       v
Kubernetes admission
Gatekeeper / Kyverno
       |
       v
     Azure
       |
       v
  Azure Policy
```

### The key distinction for interviews

Don't say all of these are pre-commit hooks. That's incorrect. Say:

> "Git hooks run locally or server-side around Git operations. Tools like pre-commit, ShellCheck and Gitleaks can be integrated as Git hooks. Terraform validate, TFLint, Checkov, Trivy and SonarQube are usually also run in CI because local hooks alone can be bypassed. Kubernetes admission controllers such as Kyverno or Gatekeeper enforce policies at cluster admission time, while Azure Policy governs Azure resources."

That distinction shows you understand **where each control belongs**, not just the tool names.

---

## CI/CD and monitoring

## Q17. If there is an issue with unit testing, how will you assist the developer?

### Interview-ready answer

> "If a unit test is failing, I first check the CI/CD pipeline logs to identify whether the failure is due to the application code, test code, environment, dependency, or pipeline configuration.
>
> I share the exact error and failing test case with the developer and help reproduce the issue locally. If it's a code or test logic issue, the developer fixes it. If it's an environment or pipeline issue, such as a missing dependency, incorrect environment variable, wrong configuration, or test database connectivity, I troubleshoot and fix that part.
>
> After the fix, I rerun the unit tests and verify that the complete test suite passes before allowing the pipeline to continue."

### Practical flow

```text
            Unit test failure
                    |
                    v
             Check CI/CD logs
                    |
                    v
           Identify root cause
                    |
       +------------+-------------+
       |            |             |
   Code issue   Test issue   Environment /
       |            |         pipeline issue
       |            |             |
   Developer    Developer       DevOps
     fixes        fixes          fixes
       |            |             |
       +------------+-------------+
                    |
                    v
             Run tests again
                    |
                    v
                  PASS
                    |
                    v
            Continue pipeline
```

### Example

Suppose the pipeline shows:

```text
Tests run: 25
Failures: 1

PaymentServiceTest
Expected: 200
Actual: 500
```

I would:

1. Check the complete stack trace.
2. Identify the failing test and recent code changes.
3. Try to reproduce it locally.
4. Check whether the failure is application logic, test data, dependency, or environment related.
5. Share the evidence with the developer.
6. If the issue is environmental, fix the pipeline or configuration.
7. Re-run the tests.
8. Verify the full suite passes.

In Azure DevOps, publishing results with the `PublishTestResults@2` task makes the failing test, its error message and its history visible in the pipeline's **Tests** tab, which makes it much easier to share with the developer.

### Strong DevOps interview point

Don't say *"I ask the developer to fix it."* Say:

> "I don't necessarily fix application logic myself, but I help the developer isolate the problem. I provide the logs, error details, reproduction steps, and environment information. If the problem is infrastructure or CI/CD related, I take ownership of that part and fix it."

That shows proper collaboration between Developer and DevOps, instead of treating every test failure as a developer problem.

---

## Q18. You have Splunk, Grafana and Prometheus. How do you use these tools effectively for multitasking?

The key is not to use all three tools for the same purpose. Give each tool a clear responsibility and use them together for incident investigation.

### Interview-ready answer

> "I use Prometheus and Grafana mainly for real-time infrastructure and application metrics, and Splunk for centralized log analysis. I don't continuously monitor all three independently. I use dashboards and alerts to identify an issue, then correlate metrics with logs to find the root cause."

### How I use them

| Tool | Primary purpose | Example |
| --- | --- | --- |
| Prometheus | Collect metrics and alerting | CPU, memory, pod restarts, request rate |
| Grafana | Visualize metrics and dashboards | AKS health, application latency |
| Splunk | Centralized log analysis | Application errors, exceptions, HTTP 500/503 |

### Example: production issue

Suppose users report that the application is slow.

```text
User reports high latency
        ↓
Grafana dashboard
        ↓
API latency increased
        ↓
Prometheus metrics
        ↓
Pod CPU / memory / restart count
        ↓
Identify affected service
        ↓
Splunk
        ↓
Search application logs
        ↓
Find errors / exceptions
        ↓
Root cause
        ↓
Fix + verify in Grafana
```

For example, Grafana shows:

```text
API latency: 200ms → 5 seconds
Pod restarts: increasing
Memory: 90%+
```

Prometheus confirms the memory increase. Then I search Splunk:

```text
index=production service=payment "OutOfMemory"
```

If Splunk shows repeated `OutOfMemoryError`, I know the issue is likely related to memory consumption rather than network latency.

### How I multitask

If I'm handling multiple applications:

**1. Use centralized dashboards.** Create Grafana dashboards for:

```text
Production
 ├── AKS
 ├── Application
 ├── Database
 └── Infrastructure
```

**2. Configure alerts.** Prometheus can alert on conditions such as:

- CPU > 80%
- Memory > 85%
- Pod restart count increasing
- HTTP 5xx above a threshold
- High API latency

Example PromQL expressions behind such alerts:

```text
# Pod restarts in the last 15 minutes
increase(kube_pod_container_status_restarts_total[15m]) > 3

# More than 5% of requests returning 5xx
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m])) > 0.05
```

This means I don't have to manually watch dashboards all day.

**3. Use Splunk saved searches.** Maintain saved searches for common problems:

- HTTP 500
- HTTP 503
- OutOfMemory
- Connection refused
- Timeout
- Authentication failure

**4. Prioritize incidents.**

```text
P1 / Production outage
        ↓
P2 / Major degradation
        ↓
P3 / Individual service issue
        ↓
P4 / Non-production issue
```

### Strong interview answer

> "For multitasking, I rely heavily on alerts and dashboards rather than manually monitoring every system. Prometheus collects metrics and triggers alerts, Grafana gives me a centralized view of infrastructure and application health, and Splunk helps me drill into logs when an alert fires. For example, if Grafana shows high latency, I use Prometheus to determine whether CPU, memory, pods or request rates are responsible, then use Splunk to correlate that with application errors. I prioritize production incidents first and use predefined dashboards and saved Splunk queries to investigate multiple applications efficiently."

Simple rule to remember:

```text
Prometheus = metrics and alerting
Grafana    = visualization
Splunk     = logs and investigation
```

---

## Azure networking

## Q19. How do you set up health probes in a load balancer?

An Azure Load Balancer **health probe** checks whether a backend VM or instance is healthy before sending traffic to it.

### Interview-ready answer

> "I configure a health probe on the Azure Load Balancer and associate it with the backend pool through a load-balancing rule. The probe periodically checks a specific port and protocol on the backend instances. Only healthy instances receive traffic."

### Example

```text
Azure Load Balancer
        |
        | Health probe
        | TCP : 8080
        v
Backend pool
   ├── VM1 : 8080  → Healthy
   ├── VM2 : 8080  → Healthy
   └── VM3 : 8080  → Unhealthy
```

Traffic is sent only to VM1 and VM2.

### Types of Azure Load Balancer probes

| Type | Checks | Example | Use when |
| --- | --- | --- | --- |
| TCP | The port accepts a TCP connection | Port 8080 | You only need to know the service is listening |
| HTTP | An HTTP endpoint returns **200 OK** | Port 8080, path `/health` | You want an application-level health check |
| HTTPS | Same as HTTP, over TLS (Standard SKU only) | Port 443, path `/health` | The endpoint only serves HTTPS |

Any HTTP status other than 200, or a timeout, counts as a failed probe.

### Important settings

| Setting | Example |
| --- | --- |
| Protocol | HTTP |
| Port | 8080 |
| Path (HTTP/HTTPS only) | `/health` |
| Interval | 5 seconds |
| Unhealthy threshold | 2 consecutive failures |

If the backend fails the required number of consecutive probes, Azure Load Balancer marks it unhealthy and stops sending **new** connections to it. Existing connections are not cut immediately.

### Azure CLI example

```bash
# 1. Create the probe
az network lb probe create \
  --resource-group my-rg \
  --lb-name my-lb \
  --name app-health-probe \
  --protocol Http \
  --port 8080 \
  --path /health \
  --interval 5 \
  --probe-threshold 2

# 2. Associate it with a load-balancing rule
az network lb rule create \
  --resource-group my-rg \
  --lb-name my-lb \
  --name app-rule \
  --protocol Tcp \
  --frontend-port 80 \
  --backend-port 8080 \
  --frontend-ip-name my-frontend \
  --backend-pool-name my-backend-pool \
  --probe-name app-health-probe
```

### Common interview follow-up

> *"The VM is running, but the Load Balancer shows it as unhealthy. What will you check?"*

- Is the application actually listening on the probe port?
- Is the probe path correct?
- Does `/health` return HTTP 200?
- Does the NSG allow probe traffic? Probes come from **168.63.129.16**, so the NSG must allow the `AzureLoadBalancer` service tag. A custom "deny all inbound" rule placed above the default rules blocks the probes.
- Is the load-balancing rule configured correctly?
- Is the backend pool associated with the correct NIC or IP?
- Is the application binding to the correct interface and port? An app bound only to `127.0.0.1` passes a local test but fails the probe.

On the VM:

```bash
ss -lntp                               # is anything listening on 8080, and on which address?
curl -i http://localhost:8080/health   # does it return 200?
```

If `curl` works locally but the probe still fails, I'd investigate NSG rules, the guest OS firewall, routing, application binding and the probe configuration.

---

## Kubernetes

## Q20. What is the CrashLoopBackOff error, and how will you troubleshoot it?

### What is CrashLoopBackOff?

CrashLoopBackOff means a Kubernetes container starts, crashes or exits, Kubernetes restarts it, and the container keeps crashing repeatedly. Kubernetes gradually increases the delay between restarts (10s, 20s, 40s … up to 5 minutes), hence **BackOff**.

It is usually an application or container startup issue, not necessarily a node issue.

### Common reasons

- Application configuration error
- Missing or incorrect environment variables
- Secret or ConfigMap missing
- Wrong database or API connection
- Application listening on the wrong port
- Incorrect command or entrypoint
- Missing dependency
- OOMKilled due to insufficient memory
- Liveness probe failure
- Permission issues

### How will you troubleshoot?

I would follow this order.

**1. Check pod status**

```bash
kubectl get pods -n <namespace>
```

```text
payment-api-7d8f9c6b7f-x2abc   0/1   CrashLoopBackOff   5   10m
```

**2. Describe the pod**

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Check:

- Events
- Last State
- Exit code
- Reason
- Probe failures
- Mount, Secret or ConfigMap errors

**3. Check current logs**

```bash
kubectl logs <pod-name> -n <namespace>
```

**4. Check logs from the previous crashed container.** This is very important for CrashLoopBackOff:

```bash
kubectl logs <pod-name> -n <namespace> --previous
```

For example:

```text
Error connecting to PostgreSQL
Connection refused
Application startup failed
```

Now I know the container is crashing because of a database connection problem.

**5. Check the container's last state**

```bash
kubectl get pod <pod-name> -n <namespace> \
  -o jsonpath='{.status.containerStatuses[*].lastState}'
```

If you see `reason: OOMKilled` (exit code **137**), investigate memory requests and limits. Other common exit codes:

| Exit code | Usual meaning |
| --- | --- |
| 0 | The process finished, but a Deployment expects it to keep running (wrong command) |
| 1 | Application error at startup |
| 126 / 127 | Command not executable / not found (wrong entrypoint) |
| 137 | Killed by SIGKILL, usually OOMKilled |
| 143 | Terminated by SIGTERM |

**6. Check configuration**

```bash
kubectl get configmap -n <namespace>
kubectl get secrets -n <namespace>
```

Verify that the required environment variables, ConfigMaps and Secrets exist and are correctly mounted or referenced.

**7. Check probes.** If logs look normal but the container keeps restarting:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for `Liveness probe failed`, then verify the application's health endpoint, port and `initialDelaySeconds` (a slow-starting app needs a longer delay or a startup probe).

Note: only a failing **liveness** probe restarts the container. A failing **readiness** probe just removes the pod from Service endpoints, so it doesn't cause CrashLoopBackOff.

### Interview-ready answer

> "CrashLoopBackOff means the container is repeatedly starting and crashing, so Kubernetes keeps restarting it and applies an increasing backoff delay.
>
> First, I check `kubectl get pods` and `kubectl describe pod` to understand the restart reason and events. Then I check `kubectl logs` and especially `kubectl logs --previous`, because the current container may have only just restarted and the useful error is in the previous one.
>
> I then verify the exit code, OOMKilled status, ConfigMaps, Secrets, environment variables, application configuration, database connectivity, container command or entrypoint, and the liveness probe.
>
> Once I identify the root cause, I fix the application, configuration, resource or probe issue and monitor the pod using `kubectl get pods` and `kubectl rollout status`."

### Simple troubleshooting flow

```text
CrashLoopBackOff
       ↓
kubectl describe pod
       ↓
kubectl logs --previous
       ↓
Check exit code / reason
       ↓
 ┌───────────────┬────────────────┬─────────────────┐
 │ OOMKilled     │ App error      │ Probe failure   │
 │               │                │                 │
 │ Check limits  │ Check config,  │ Check endpoint  │
 │ & memory      │ DB, secrets    │ & port          │
 └───────────────┴────────────────┴─────────────────┘
       ↓
Fix root cause
       ↓
Verify pod becomes Ready
```

---

## Azure migration

## Q21. How do you migrate servers from on-premises to Azure?

I would follow a **plan → assess → replicate → test → migrate → validate → decommission** approach.

### 1. Assess the existing servers

First, I collect:

- Number of servers
- OS version
- CPU, memory and disk requirements
- Applications and services running
- Database dependencies
- Network dependencies
- Ports and firewall rules
- DNS requirements
- Application dependencies

I use **Azure Migrate** to discover and assess the on-premises servers and get sizing and cost recommendations. Its dependency analysis shows which servers talk to each other, so they can be migrated together in the same wave.

### 2. Prepare Azure

```text
Azure subscription
      ↓
Resource groups
      ↓
     VNet
 ┌────┴─────┐
Subnet    Subnet
 App        DB
      ↓
NSG / Firewall
      ↓
VPN / ExpressRoute
```

I also configure:

- VNet and subnets
- NSGs
- VPN or ExpressRoute connectivity
- DNS
- Azure RBAC
- Monitoring
- Backup
- Key Vault if required

### 3. Replicate the servers

I use the **Migration and modernization** tool in Azure Migrate (previously called Server Migration). VMware VMs can be replicated agentless or agent-based, Hyper-V VMs replicate through the Hyper-V host, and physical servers need the replication agent (Mobility service).

```text
On-prem server
      ↓
Azure Migrate
      ↓
Continuous replication
      ↓
Azure managed disk
```

The server keeps running on-premises while its data is replicated to Azure.

### 4. Test migration

Before the production cutover, I perform a **test migration** into an isolated, non-production VNet. I verify:

- The application starts correctly
- Network connectivity
- Database connectivity
- DNS
- Firewall and NSG rules
- Application functionality
- Performance
- Monitoring and backup

Test migration doesn't impact the production server.

### 5. Production cutover

During the migration window:

```text
Stop / quiesce application
        ↓
Final data sync
        ↓
Stop on-prem server
        ↓
Complete migration
        ↓
Start Azure VM
        ↓
Update DNS / traffic
        ↓
Validate application
```

Then I monitor the application closely. The on-premises server stays switched off but intact, so the rollback plan is to switch DNS back to it.

### 6. Decommission on-premises

After business validation and a defined rollback period, I decommission the old server according to the organization's change-management and retention process.

### Interview-ready answer

> "For on-prem to Azure migration, I normally use Azure Migrate. First, I assess the existing servers, their sizing, applications, dependencies, network and database requirements. Then I prepare the Azure environment with VNet, subnets, NSGs, connectivity through VPN or ExpressRoute, RBAC, monitoring and backup.
>
> Next, I install the required Azure Migrate replication components and continuously replicate the on-prem servers to Azure. I perform a test migration to validate the application, networking and dependencies. During the production cutover, I stop or quiesce the application, perform the final synchronization, migrate the server, start it in Azure, update DNS or traffic routing, and validate the application. After a successful stabilization period, I decommission the on-prem server.
>
> The key goal is to minimize downtime and have a tested rollback plan before production cutover."

### Important interview point

Don't say *"I just copy the VM to Azure."* Say:

```text
Assess → Dependency mapping → Azure preparation → Replication → Test migration → Cutover → Validation → Decommission
```

Also mention **Azure Migrate** as the primary tool for a typical server migration scenario.

---

## Azure VM operations

## Q22. An application is down on an Azure Windows Server VM. How do you troubleshoot it? <em>(scenario)</em>

I troubleshoot from the outside in: **Azure infrastructure → VM → network → Windows → application → dependencies**.

### 1. Check the Azure VM health

```bash
az vm get-instance-view \
  --resource-group <rg> \
  --name <vm-name> \
  --query "instanceView.statuses"
```

I check:

- Is the VM **running**?
- Resource Health and any recent Azure platform issues
- The Activity Log for recent changes (resize, restart, NSG or extension changes)
- Boot diagnostics (screenshot) to see whether Windows booted at all
- CPU, memory, disk and network metrics in Azure Monitor

If the VM itself is unavailable, I fix the VM before looking at the application. If RDP doesn't work, I can still use **Run Command** or the **Serial Console** from the portal.

### 2. Check network connectivity

I verify:

- NSG rules on the NIC and the subnet
- Load Balancer or Application Gateway health probe status
- Public/private IP
- The required application port is open, including the **Windows Firewall** inside the VM

For example, if the application uses port 8080:

```powershell
# On the VM itself
Test-NetConnection localhost -Port 8080

# From another server in the VNet
Test-NetConnection <private-ip> -Port 8080
```

If it works locally but not from another server, the problem is the NSG, Windows Firewall, routing or the application binding only to `127.0.0.1`.

### 3. Check the Windows service

```powershell
Get-Service <service-name>
```

If it is stopped:

```powershell
Start-Service <service-name>
```

I also check whether the service keeps stopping or fails to start, because restarting it only hides the real problem.

### 4. Check whether the application is listening

```powershell
netstat -ano | findstr :8080
```

or:

```powershell
Get-NetTCPConnection -LocalPort 8080 -State Listen
```

If nothing is listening on the expected port, I investigate the application or service itself.

### 5. Check Windows Event Viewer

```text
Event Viewer
 ├── Windows Logs
 │    ├── Application
 │    └── System
 └── Applications and Services Logs (application-specific)
```

Or from PowerShell:

```powershell
Get-WinEvent -LogName Application -MaxEvents 50 |
  Where-Object LevelDisplayName -eq 'Error'
```

I look for:

- Application crashes
- Service failures (Service Control Manager events in the System log)
- .NET errors
- Permission issues
- Disk or resource problems

### 6. Check the application logs

For example, `C:\Program Files\<Application>\logs\`, or `C:\inetpub\logs\LogFiles\` for IIS.

I search for:

- `ERROR` / `Exception`
- `Connection refused`
- `Timeout`
- `OutOfMemory`
- `Access denied`

### 7. Check the dependencies

If the application is running but still unavailable, I check what it depends on:

- SQL Server / PostgreSQL
- Downstream APIs
- Storage
- DNS
- Key Vault
- Active Directory / Entra ID
- Other application servers

```powershell
Test-NetConnection <database-server> -Port 1433
Resolve-DnsName <database-server>
```

### 8. Check resource utilization

```powershell
# Top CPU consumers
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10

# Top memory consumers
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10

# Free disk space
Get-PSDrive -PSProvider FileSystem
```

I also check Azure Monitor for CPU, memory, disk space, disk IOPS, network and VM availability. A full disk is a very common reason for a service failing to start or write logs.

### Interview-ready answer

> "If an application is down on an Azure Windows Server, I first determine whether the issue is with Azure infrastructure, the VM, the network, the Windows service, the application or its dependencies.
>
> First, I check the VM status, Resource Health, Azure Monitor metrics, the Activity Log and boot diagnostics. Then I verify the NSG rules and the Load Balancer or Application Gateway health probes, and test the application port with `Test-NetConnection`.
>
> If network connectivity is fine, I connect to the VM and check whether the application service is running and listening on the expected port. Then I check Event Viewer and the application logs for errors or crashes, and check CPU, memory and disk.
>
> Finally, I verify dependencies such as the database, APIs, DNS and authentication. Once I identify the root cause, I fix it, restart the service only if required, validate the application end to end, and monitor it to make sure the issue doesn't recur."

### Simple troubleshooting flow

```text
Application down
       ↓
Azure VM healthy?
       ↓
Network / NSG / LB / App Gateway?
       ↓
Port reachable? (incl. Windows Firewall)
       ↓
Windows service running?
       ↓
Application listening?
       ↓
Event Viewer + application logs
       ↓
CPU / memory / disk?
       ↓
Database / API / DNS dependencies?
       ↓
Fix → Validate → Monitor
```

### Strong interview point

Don't immediately restart the server. First **collect evidence** and identify whether the problem is infrastructure, network, Windows service, application or dependency. A restart can clear the symptom and destroy the evidence you need for the root cause.

---

## Q23. If an application on a VM has dependencies, how do you make sure you update them?

I don't update dependencies directly in production without checking the impact. I follow a controlled update and change-management process.

### Example

Suppose the application depends on:

- .NET runtime
- Java
- IIS
- Windows libraries
- Database drivers
- Third-party agents

### How I handle it

#### 1. Identify the dependencies

- Check the application documentation and configuration
- Check the installed software and versions
- Review vulnerability and scanning reports

```powershell
Get-Package | Sort-Object Name | Select-Object Name, Version
```

#### 2. Check the required version

- Confirm which version the application supports
- Check compatibility and release notes for breaking changes before upgrading

#### 3. Test in a lower environment

```text
Dev → QA → UAT → Production
```

I update the dependency in Dev first and run the application's unit and integration tests, then promote it through QA and UAT.

#### 4. Take a backup and prepare a rollback plan

- VM backup or disk snapshot, where appropriate
- Backup of the application configuration
- Keep the previous dependency version/installer available

#### 5. Raise a change request

Document the dependency, current version, target version, impact, expected downtime and rollback plan, and get the required approval for production.

#### 6. Update during the maintenance window

Install the approved version using the organization's standard package or software-management tool, not an ad-hoc download.

#### 7. Validate after the update

```powershell
Get-Service <service-name>
Test-NetConnection <dependency> -Port <port>
```

Then check the logs and test the application end to end.

#### 8. Monitor, and roll back if required

If the application starts failing after the update, I follow the rollback plan and restore the previous version or configuration.

### Interview-ready answer

> "If a VM has application dependencies that need updating, I first identify the dependency and check its compatibility with the application. I don't upgrade it directly in production. I test the new version in Dev, QA and UAT with application and integration testing, prepare a backup and rollback plan, and raise a change request.
>
> After approval, I update the dependency during the maintenance window and validate the service, ports, logs and application functionality. Finally, I monitor the application and roll back if the update causes issues."

### Key point

In enterprise environments, updates should be **automated and standardized** rather than done manually on every VM:

| What | Tool |
| --- | --- |
| Windows OS patches | Azure Update Manager |
| Application dependencies and configuration | Ansible, PowerShell DSC, SCCM / Intune |
| Application packaging and rollout | CI/CD pipelines |
| New VMs | A golden image (Azure Compute Gallery) that already has the approved versions |

---

## Load balancing

## Q24. How does a Layer 4 load balancer distribute traffic?

Layer 4 (L4) load balancing works at the **TCP/UDP** level. It makes routing decisions using the connection's flow information:

- Source IP
- Destination IP
- Source port
- Destination port
- Protocol (TCP/UDP)

It does **not** inspect the HTTP URL, headers, cookies or application content like a Layer 7 load balancer does.

### Example in Azure

```text
Client
   |
   | TCP :443
   ↓
Azure Load Balancer
   |
   ├── VM1 :443
   ├── VM2 :443
   └── VM3 :443
```

Azure Load Balancer has:

| Component | Purpose |
| --- | --- |
| Frontend IP | The public or private IP clients connect to |
| Backend pool | VM1, VM2, VM3 |
| Load-balancing rule | Maps frontend port 443 → backend port 443 |
| Health probe | Decides which backend instances are healthy (see Q19) |

When a new connection arrives, the load balancer picks a healthy backend and forwards the flow. All packets of the same connection go to the same backend.

```text
Client A ──→ Load Balancer ──→ VM1
Client B ──→ Load Balancer ──→ VM2
Client C ──→ Load Balancer ──→ VM3
```

### It is hash-based, not strict round-robin

Azure Load Balancer uses a **5-tuple hash** (source IP, source port, destination IP, destination port, protocol) by default. So distribution is not a strict VM1 → VM2 → VM3 round-robin sequence.

If the application needs a client to keep hitting the same VM, I change the **session persistence** on the rule:

| Mode | Hash | Effect |
| --- | --- | --- |
| None (default) | 5-tuple | Each new connection can land on any VM |
| Client IP | 2-tuple (source IP, destination IP) | Same client IP → same VM |
| Client IP and protocol | 3-tuple (+ protocol) | Same client IP and protocol → same VM |

Azure Load Balancer is also **pass-through**: it doesn't terminate the TCP or TLS connection, so the backend sees the original client IP and handles TLS itself.

### Health probe

```text
VM1 → Healthy
VM2 → Unhealthy ❌
VM3 → Healthy
```

The load balancer stops sending **new** connections to VM2 and sends them to the healthy instances.

### Interview-ready answer

> "At Layer 4, the load balancer distributes traffic based on TCP/UDP connection information such as source IP, destination IP, source port, destination port and protocol. It doesn't inspect application-level information like HTTP URLs or headers.
>
> In Azure Load Balancer, I configure a frontend IP, a backend pool, a load-balancing rule and a health probe. When a client connects to the frontend IP, the load balancer uses a hash of the flow to pick a healthy backend and forwards the connection to it. If a backend fails the health probe, new connections are not sent to it. If the application needs stickiness, I set session persistence to client IP."

### L4 vs. L7

| Layer 4 | Layer 7 |
| --- | --- |
| TCP/UDP | HTTP/HTTPS |
| IP + port based | URL, header, host and cookie based |
| Doesn't understand application content | Understands application content |
| Pass-through, no TLS termination | Can terminate TLS, do path-based routing and WAF |
| Azure Load Balancer | Azure Application Gateway / Front Door |
| Very fast and simple | More application-aware |

### One-line answer

> "L4 load balancing distributes TCP/UDP connections across healthy backend servers based on network flow information, not HTTP application content."

---

## VNet connectivity

## Q25. How do you establish a connection between two VNets (VNet-to-VNet)?

The most common approach is **VNet Peering**.

### Example

```text
VNet-A                         VNet-B
10.0.0.0/16                    10.1.0.0/16
    |                              |
    |------- VNet Peering ---------|
```

### Steps

#### 1. Make sure the address spaces don't overlap

```text
VNet-A → 10.0.0.0/16
VNet-B → 10.1.0.0/16
```

Peering can't be created between VNets with overlapping address spaces.

#### 2. Create the peering in both directions

```text
VNet-A → VNet-B
VNet-B → VNet-A
```

```bash
az network vnet peering create \
  --resource-group rg-a \
  --vnet-name vnet-a \
  --name vnet-a-to-vnet-b \
  --remote-vnet <vnet-b-resource-id> \
  --allow-vnet-access

az network vnet peering create \
  --resource-group rg-b \
  --vnet-name vnet-b \
  --name vnet-b-to-vnet-a \
  --remote-vnet <vnet-a-resource-id> \
  --allow-vnet-access
```

Both sides must show the peering status as **Connected**.

#### 3. Configure NSG / firewall rules

For example, if an application in VNet-A needs to access PostgreSQL in VNet-B:

```text
VNet-A VM
   |
   | TCP 5432
   ↓
VNet-B PostgreSQL
```

Allow TCP 5432 only from the required source subnet or IP. The default NSG rule `AllowVnetInBound` already includes peered VNets, so in practice I add a tighter rule rather than relying on the default.

#### 4. Verify connectivity

```powershell
Test-NetConnection 10.1.2.10 -Port 5432
```

or from Linux:

```bash
nc -zv 10.1.2.10 5432
```

### If the VNets are in different regions

Use **Global VNet Peering**.

```text
VNet-A (East US)
       |
Global VNet Peering
       |
VNet-B (West Europe)
```

### If the VNets are in different subscriptions

That's also supported (even across Entra ID tenants), as long as I have the required permissions, such as **Network Contributor**, on both VNets.

### Important: peering is not transitive

```text
VNet-A ↔ VNet-B ↔ VNet-C
```

VNet-A **cannot** reach VNet-C through VNet-B automatically. For that I either peer A and C directly, or use a **hub-and-spoke** design where traffic is routed through Azure Firewall or an NVA in the hub, or use **Azure Virtual WAN**.

### Interview-ready answer

> "To connect two Azure VNets, I normally use VNet Peering. First, I make sure the address spaces don't overlap. Then I create the peering in both directions, configure the required NSG and firewall rules, and verify connectivity between the required subnets or resources.
>
> If the VNets are in different regions, I use Global VNet Peering. Peering isn't transitive, so if I need transitive connectivity across many VNets or hybrid connectivity with on-premises, I'd use a hub-and-spoke architecture with Azure Firewall or an NVA, or Azure Virtual WAN."

### Follow-up: "Why not VPN?"

| Option | When to use |
| --- | --- |
| VNet Peering | Preferred for direct VNet-to-VNet connectivity. Traffic stays on the Microsoft backbone with low latency and high bandwidth, and no gateway is needed |
| VNet-to-VNet VPN | Uses VPN gateways and IPsec tunnels. Useful when encrypted tunnels are specifically required or peering isn't suitable, but it's limited by gateway bandwidth and adds cost |
| Virtual WAN | Large-scale hub-and-spoke connectivity across many VNets, branches and on-premises sites |

### One-line answer

> "For normal VNet-to-VNet connectivity, I use VNet Peering; for cross-region connectivity, Global VNet Peering."

---

## TLS and certificates

## Q26. Your team uses HTTP for the frontend and backend. How do you change it to HTTPS? <em>(scenario)</em>

I treat this as a **TLS termination and end-to-end encryption** change. It's not just changing `http` to `https`: I need to configure certificates, listeners, backend communication and application settings.

### Typical Azure architecture

```text
User
  |
  | HTTPS :443
  ↓
Application Gateway
  |
  | HTTPS :443
  ↓
Frontend
  |
  | HTTPS :443
  ↓
Backend API
  |
  | TLS
  ↓
Database / external services
```

Note: Azure Load Balancer works at Layer 4 and is pass-through, so it can't terminate TLS. For TLS termination I use **Application Gateway** (or Front Door), or terminate on the application itself.

### Steps I would follow

#### 1. Get a TLS certificate

Use a certificate from a trusted CA, preferably stored and managed in **Azure Key Vault** or the organization's certificate-management solution. For example:

```text
app.company.com
api.company.com
```

The certificate's CN/SAN must match the hostname.

#### 2. Configure HTTPS on the frontend

On Application Gateway:

```text
HTTPS listener
Port: 443
Certificate: app.company.com (referenced from Key Vault)
```

Then add a redirect:

```text
HTTP :80  →  HTTPS :443
```

So users going to `http://app.company.com` are redirected to `https://app.company.com`.

I also set an SSL policy that enforces **TLS 1.2 or higher**.

#### 3. Enable HTTPS on the backend

The backend application must listen on HTTPS, for example `https://api.company.com:443`, with its own certificate and TLS settings on the application server.

#### 4. Change the frontend API configuration

If the frontend currently calls:

```text
http://api.company.com/api/payment
```

change it to:

```text
https://api.company.com/api/payment
```

This matters because a page loaded over HTTPS calling an HTTP API causes **mixed-content** errors in browsers. I also make sure cookies are marked `Secure`.

#### 5. Configure backend certificate validation

For Application Gateway to talk to the backend over HTTPS, I update the **backend settings** to use HTTPS on port 443 and make sure the hostname matches the backend certificate. If the backend certificate isn't from a well-known CA, I upload its trusted root certificate to Application Gateway.

#### 6. Update NSG / firewall rules

```text
TCP 443 → allowed
TCP 80  → only for the redirect, if required
```

Don't expose unnecessary ports.

#### 7. Test before production

- Certificate validity and chain
- TLS handshake and version/cipher requirements
- HTTP → HTTPS redirect
- Frontend → backend API calls
- Authentication and callbacks (redirect URIs often need updating to `https://`)
- WebSockets, if used
- No mixed-content errors
- Application logs

Then deploy through the normal **Dev → QA → UAT → Production** process.

### Interview-ready answer

> "If the frontend and backend are using HTTP, I'd migrate them to HTTPS by first getting trusted TLS certificates, stored in Key Vault, and configuring HTTPS listeners. In Azure, I can use Application Gateway for TLS termination and redirect HTTP port 80 to HTTPS 443.
>
> For end-to-end encryption, I'd also configure HTTPS between Application Gateway and the backend. I'd update the frontend API URLs from HTTP to HTTPS, configure backend certificate validation, update NSG and firewall rules, and test the complete flow in lower environments before production.
>
> I'd make sure HTTP is either disabled or only used to redirect to HTTPS, and enforce TLS 1.2 or higher according to the organization's security standards."

### Strong point to mention

> *"Is SSL termination at Application Gateway enough?"*

> "It's enough if encryption is only required from the client to Application Gateway. If the security requirement is end-to-end encryption, I'll configure HTTPS from Application Gateway to the backend as well."

---

## Q27. If a certificate expires, how do you make sure it won't impact the application? <em>(scenario)</em>

The goal is that a certificate **never** reaches its expiry date in production: renew and deploy it before it expires, and automate monitoring so it doesn't become an incident.

### How I would handle it

#### 1. Monitor certificate expiry

I keep an inventory and monitor certificates in:

- Azure Key Vault
- Application Gateway
- App Service
- Reverse proxies (NGINX, ingress controllers)
- Windows / IIS servers

I set alerts at, for example, **30, 15 and 7 days** before expiry. Key Vault publishes `CertificateNearExpiry` and `CertificateExpired` events to **Event Grid**, which I can route to email, Teams or a ticketing system.

#### 2. Automate renewal

For Key Vault certificates, I configure the **lifetime action** to auto-renew, for example 30 days before expiry. This works for self-signed certificates and CAs integrated with Key Vault (such as DigiCert and GlobalSign). For other CAs, renewal still needs the CSR to be signed and merged manually, so the alert is essential there.

#### 3. Deploy the renewed certificate

After renewal, I make sure the new certificate is actually being used by the component terminating TLS:

```text
New certificate
      ↓
Azure Key Vault
      ↓
Application Gateway
      ↓
HTTPS :443
      ↓
Application
```

If Application Gateway references the Key Vault secret **without a version**, it picks up the renewed certificate automatically (it polls Key Vault every 4 hours). If it references a specific version, or the certificate was uploaded manually, I have to update it myself.

#### 4. Validate before expiry

```bash
curl -Iv https://app.company.com

# Check the expiry dates directly
openssl s_client -connect app.company.com:443 -servername app.company.com </dev/null \
  | openssl x509 -noout -dates -subject
```

I check:

- Certificate expiry date
- Certificate chain
- Hostname / SAN
- TLS handshake
- Application availability

#### 5. Have a rollback plan

If the new certificate causes an issue (for example, a missing intermediate certificate), I can revert to the previous, still-valid certificate version.

### If it has already expired

1. Renew or reissue the certificate immediately
2. Import it into Key Vault (or the TLS endpoint) and update the listener or binding
3. Validate with `curl` / `openssl` and confirm the application is working
4. Do an RCA on why the alert didn't fire or wasn't acted on, and add the certificate to monitoring and auto-renewal

### Interview-ready answer

> "To make sure an expiring certificate doesn't impact the application, I don't wait for the expiry date. I monitor certificate expiry and configure alerts well in advance, typically at 30, 15 and 7 days. Where supported, I enable automatic renewal in Azure Key Vault.
>
> Once the certificate is renewed, I make sure it's deployed to the TLS termination point, such as Application Gateway, App Service or IIS. I validate the certificate chain, hostname, expiry date and HTTPS connectivity using tools like `curl` or `openssl`. I monitor the application after the change and keep a rollback plan.
>
> The key is: monitor → renew → deploy → validate → alert."

### Follow-up: "How will you automate this?"

> "I use Key Vault certificate auto-renewal where supported, with Event Grid and Azure Monitor alerts for near-expiry notifications. Services like Application Gateway reference the versionless Key Vault secret, so they pick up the renewed certificate automatically. For anything else, the pipeline deploys the renewed certificate to the TLS endpoint."

### Important

Renewing a certificate in Key Vault doesn't mean every consuming service is immediately using it. I always verify each service's certificate binding/reference and how it picks up renewals.

---

## Azure VM automation

## Q28. How do you implement auto-shutdown for a VM?

The simplest approach is the built-in **Auto-shutdown** feature, or an automation-based schedule for many VMs.

### Option 1: Azure VM Auto-shutdown

For an individual non-production VM, configure it in the Azure Portal:

```text
VM
 ↓
Operations
 ↓
Auto-shutdown
 ↓
Enable
 ↓
Set shutdown time and timezone
 ↓
(Optional) Notification before shutdown
```

Or with the CLI (the time is in UTC, `HHMM`):

```bash
az vm auto-shutdown \
  --resource-group my-rg \
  --name dev-vm \
  --time 2000 \
  --email "team@company.com"
```

For example:

```text
Dev VM
  ↓
Auto-shutdown
  ↓
Every day at 8:00 PM
```

Auto-shutdown **deallocates** the VM, so compute charges stop. It only shuts down; it doesn't start the VM again.

### Option 2: Azure Automation / Logic Apps

For multiple VMs, I prefer centralized automation:

```text
Azure Automation / Logic App
          ↓
Scheduled trigger
          ↓
Find tagged VMs
          ↓
Stop (deallocate) VMs
```

For example, using tags:

```text
Environment  = Dev
AutoShutdown = Yes
```

An Azure Automation runbook using a managed identity:

```powershell
Connect-AzAccount -Identity

Get-AzVM -Status |
  Where-Object { $_.Tags['AutoShutdown'] -eq 'Yes' -and $_.PowerState -eq 'VM running' } |
  ForEach-Object {
      Stop-AzVM -ResourceGroupName $_.ResourceGroupName -Name $_.Name -Force -NoWait
  }
```

A matching runbook can start the VMs in the morning. Microsoft also provides the **Start/Stop VMs v2** solution, which does this with schedules and tags out of the box.

### Stop vs. deallocate

| Command | Result | Compute billing |
| --- | --- | --- |
| `az vm stop` / shutdown from inside the OS | Stopped | **Still billed** |
| `az vm deallocate` / `Stop-AzVM` / portal Stop | Stopped (deallocated) | Not billed |

Disks are still billed in both cases.

### Important point

I would not automatically shut down **production** VMs unless there is an explicit business requirement.

For Dev/QA:

```text
Start → 8:00 AM
        ↓
Run during working hours
        ↓
Shutdown → 8:00 PM
```

This can significantly reduce compute costs (see Q11).

### Interview-ready answer

> "For Azure VMs, I can configure the built-in Auto-shutdown feature for individual development or test VMs. If there are many VMs, I prefer centralized automation using Azure Automation runbooks, Logic Apps or the Start/Stop VMs solution. I use tags such as `Environment=Dev` and `AutoShutdown=Yes` to identify which VMs to stop, and make sure they're deallocated so compute billing stops. I configure the correct timezone and schedule, and exclude production VMs unless there's a specific requirement."

---

## Q29. Can we do cron scheduling in a VM?

Yes. Inside a **Linux** Azure VM, cron works exactly as it does on an on-prem Linux server.

### Example

Edit the crontab:

```bash
crontab -e
```

Run a script every day at 8 PM:

```text
0 20 * * * /path/to/script.sh
```

| Field | Value | Meaning |
| --- | --- | --- |
| Minute | `0` | At minute 0 |
| Hour | `20` | At 8 PM |
| Day of month | `*` | Every day |
| Month | `*` | Every month |
| Day of week | `*` | Every day of the week |

### Shutting down the VM from cron

```text
0 20 * * * /sbin/shutdown -h now
```

This shuts down the **operating system**, but Azure still shows the VM as *Stopped*, not *Stopped (deallocated)*, so compute is **still billed** (see Q28).

### Better approach for an Azure VM

If the goal is to deallocate the VM to save cost, I prefer Azure-native scheduling (Auto-shutdown, Azure Automation or Logic Apps) rather than an OS-level cron job.

If cron must be used, it can call the Azure CLI with the VM's **managed identity**:

```text
0 20 * * * /usr/bin/az login --identity && /usr/bin/az vm deallocate --resource-group my-rg --name my-vm >> /var/log/vm-deallocate.log 2>&1
```

This requires:

- A system-assigned managed identity on the VM
- A role such as **Virtual Machine Contributor**, scoped only to that VM
- Full paths in the crontab, because cron runs with a minimal `PATH`

### Interview-ready answer

> "Yes, we can use cron inside a Linux Azure VM for OS-level tasks such as scripts, log cleanup, backups or scheduled jobs. For Azure resource operations like starting or deallocating the VM, I'd prefer Azure-native scheduling such as Auto-shutdown, Azure Automation or Logic Apps, because shutting down the OS from cron doesn't deallocate the VM. If I do use cron with the Azure CLI, I authenticate with a managed identity instead of storing credentials on the VM."

### Important

For a **Windows** Azure VM, the equivalent of cron is **Task Scheduler**:

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\scripts\cleanup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 8pm
Register-ScheduledTask -TaskName "DailyCleanup" -Action $action -Trigger $trigger -User "SYSTEM"
```

---

## Azure VM security

## Q30. How do you remediate access to a Windows Azure server? <em>(scenario)</em>

If there is unauthorized or excessive access to a Windows Azure VM, I remediate it using **identity, network and least-privilege** controls.

### 1. Identify who currently has access

I check every path into the VM:

- Azure RBAC assignments on the VM, resource group and subscription
- Microsoft Entra ID users and groups
- Local Windows users and groups
- NSG rules allowing RDP
- Just-in-time (JIT) access, if enabled

```bash
az role assignment list \
  --scope <vm-resource-id> \
  --include-inherited \
  -o table
```

`--include-inherited` matters, because most access usually comes from the resource group or subscription, not the VM itself.

### 2. Remove unnecessary Azure permissions

If someone has excessive permissions such as Contributor, I replace them with the minimum required role (see Q14):

```text
Developer → Reader
Support   → Virtual Machine Contributor
Admin     → Appropriate privileged role, through PIM
```

Note that **Virtual Machine Contributor** can run Run Command and VM extensions, which means it can effectively get admin rights inside the OS, so I treat it as a privileged role.

For production, I use **Microsoft Entra ID + PIM** for time-bound, approved access instead of permanent admin assignments.

If the VM uses Entra ID login, OS access is controlled by the **Virtual Machine Administrator Login** and **Virtual Machine User Login** roles, so I review those too.

### 3. Secure RDP

Don't expose RDP (3389) to the internet.

Bad:

```text
Internet → TCP 3389 → VM
Source: *
```

Better:

```text
Admin network / VPN / Bastion
        ↓
     TCP 3389
        ↓
       VM
```

I use:

- NSG rules restricted to specific source IPs
- **Azure Bastion**, so the VM doesn't need a public IP at all
- VPN or ExpressRoute
- **Just-in-time VM access** (Defender for Cloud), which opens 3389 only for a requested time window and source IP

### 4. Remove unnecessary local accounts

On the Windows VM:

```powershell
Get-LocalUser

# Who is in the local Administrators group?
Get-LocalGroupMember Administrators

# Remove unauthorized admins
Remove-LocalGroupMember -Group "Administrators" -Member "<user>"

# Disable an account that shouldn't be used
Disable-LocalUser -Name "<user>"
```

### 5. Check and rotate credentials

If credentials may have been compromised:

- Disable or reset the affected account
- Rotate passwords, including the local admin password (`az vm user update` or Windows LAPS)
- Rotate service account credentials
- Review stored credentials and scripts on the server
- Prefer managed identities over passwords where possible

### 6. Review the logs

- Azure Activity Log (who changed RBAC, NSGs, ran Run Command or reset passwords)
- Microsoft Entra sign-in logs
- Windows Security event log

| Event ID | Meaning |
| --- | --- |
| 4624 | Successful logon (logon type 10 = RDP) |
| 4625 | Failed logon |
| 4672 | Logon with admin privileges |
| 4720 / 4732 | User account created / added to a local group |

I look for suspicious successful or failed logins, logins at unusual times or from unexpected IPs, and newly created accounts.

### Interview-ready answer

> "If I find excessive or unauthorized access to a Windows Azure VM, I first identify how users are getting access: Azure RBAC, Entra ID, local Windows accounts or RDP. I remove unnecessary RBAC permissions and follow least privilege, and for production I use PIM and JIT access instead of permanent admin access.
>
> I restrict RDP using NSGs, VPN or Azure Bastion instead of exposing port 3389 to the internet. On the VM, I review local users and the Administrators group and remove unauthorized accounts. If credentials are compromised, I disable the account and rotate the credentials. Finally, I review the Azure Activity Log, Entra sign-in logs and Windows Security logs to find out whether the access was actually misused."

### Strong one-line answer

> "I remediate access using least privilege with Entra ID and RBAC, PIM/JIT, restricted RDP through Bastion or VPN, removal of unnecessary local admins, credential rotation, and log auditing."

---

## Containers

## Q31. A Docker image deployment takes 10 minutes. How do you reduce it to 5 minutes using ACI? <em>(scenario)</em>

First I identify **where** the 10 minutes is spent: image build, image push, image pull or container startup.

### First, find the bottleneck

```text
Build → Push to ACR → ACI pulls image → Container starts
  ?          ?               ?                 ?
```

- Build and push times are in the CI/CD pipeline logs.
- Pull and start times are in the ACI container events:

```bash
az container show \
  --resource-group my-rg \
  --name my-app \
  --query "containers[0].instanceView.events" \
  -o table
```

The `Pulling` → `Pulled` → `Started` timestamps show how long the pull and startup took.

```bash
# How big is the image, and which layers are the largest?
docker image ls myapp
docker history myapp:v1.2.3
```

ACI doesn't keep your image cached between deployments, so **every new container group pulls the full image**. That's why image size has a big impact on ACI deployment time.

### 1. Reduce the image size with a multi-stage build

Keep the build environment out of the runtime image:

```dockerfile
FROM node:22 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

The final image contains only NGINX and the built files, not Node.js, the source code or `node_modules`.

### 2. Use a smaller base image

Where compatible, prefer:

```text
node:22-alpine
nginx:alpine
python:3.12-slim
```

instead of full OS images. If the app can run on **Linux containers instead of Windows containers**, that alone can save several minutes, because Windows images are many GB.

### 3. Optimize the Docker layers

Put the files that change most often at the end:

```dockerfile
COPY package*.json ./
RUN npm ci

COPY . .
```

Dependencies are then reinstalled only when `package*.json` changes, not on every code change. In the pipeline, I also enable layer caching (for example, BuildKit `--cache-from` the previous image in ACR) so the build doesn't start from scratch each time.

### 4. Keep ACR close to ACI

```text
ACR (East US)
      ↓
ACI (East US)
```

Same region means a faster pull. If ACI runs in several regions, ACR Premium **geo-replication** keeps a copy of the image in each region.

### 5. Don't ship what isn't needed at runtime

Remove:

- Build tools
- Source code not needed at runtime
- Package manager caches
- Debug tools
- Test files

Use a `.dockerignore`:

```text
.git
node_modules
*.log
.env
tests
```

### 6. Use proper image tags

For deployments, use immutable version tags:

```text
myapp:v1.2.3
```

rather than relying only on `myapp:latest`. This makes deployments predictable and rollbacks easy.

### 7. Check application startup

If the container is pulled quickly but takes a long time to become ready, the problem is the application: slow initialization, warm-up tasks, migrations at startup, or waiting on a slow dependency.

### Interview-ready answer

> "If an ACI deployment takes 10 minutes and the target is 5, I'd first measure where the time goes: Docker build, ACR push, ACI image pull or application startup. ACI pulls the full image for every new container group, so if the pull is the bottleneck, I reduce the image size using multi-stage builds, lightweight base images and `.dockerignore`, and keep ACR in the same region as ACI.
>
> I'd also optimize the Docker layers and use pipeline layer caching to speed up the build, and use versioned image tags. If the application startup is slow, I'd investigate initialization and dependency calls. I wouldn't blindly add more CPU or memory, because the real bottleneck needs to be identified first."

### Very important interview point

If they specifically say *"using ACI"*, don't claim ACI itself magically makes the deployment twice as fast. Say:

> "ACI is the runtime. To reduce deployment time, I optimize the image pull and startup path: mainly image size, ACR locality and application initialization."
