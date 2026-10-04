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
