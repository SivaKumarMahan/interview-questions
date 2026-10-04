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
