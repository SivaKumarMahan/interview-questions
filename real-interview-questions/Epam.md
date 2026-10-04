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
