# Deloitte LLP - Interview Questions

## Q1. What do you do if a Terraform deployment fails in the middle of `terraform apply`?

If a Terraform deployment fails midway through `terraform apply`, I don't immediately rerun apply. First I find out what failed, what was already created, and what Terraform recorded in state.

### My troubleshooting flow

```
terraform apply
      |
      X Failure
      |
      +--> Check pipeline / Terraform error
      |
      +--> Check Terraform state
      |
      +--> Check Azure resource
      |
      +--> Check dependency / permissions / configuration
      |
      +--> terraform plan
      |
      +--> Fix issue
      |
      +--> terraform apply
```

### 1. Check the exact Terraform error

First I look at the Terraform output:

```bash
terraform apply
```

or in Azure DevOps, I check the failed pipeline task logs.

For more detailed logs:

```bash
TF_LOG=INFO terraform apply
```

For very detailed debugging:

```bash
TF_LOG=DEBUG terraform apply
```

I don't normally keep DEBUG enabled in CI because the logs become very big and may show sensitive information.

### 2. Check Terraform state

First:

```bash
terraform state list
```

This tells me what Terraform currently knows about.

Then I check a specific resource:

```bash
terraform state show azurerm_linux_virtual_machine.vm
```

I compare this with what actually exists in Azure.

For example:

```
Terraform state:
VM exists

Azure:
VM exists
```

That means the resource was created successfully before the later resource failed.

### 3. Check Azure directly

I verify the actual resource:

```bash
az resource show \
  --ids <resource-id>
```

Or service-specific commands:

```bash
az vm show ...
az network vnet show ...
az aks show ...
```

This is important because Terraform state and the real Azure environment can be different for some time after a failed apply.

### 4. Run terraform plan

After understanding the failure, I run:

```bash
terraform plan
```

This is one of the most important steps.

Terraform compares:

```
Configuration
      +
State
      +
Actual infrastructure
      |
      v
Desired changes
```

For example, suppose Terraform created:

```
VNet        ✓
Subnet      ✓
NSG         ✓
AKS         ✗
```

After fixing the AKS issue:

```bash
terraform plan
```

may show that only AKS needs to be created.

Then:

```bash
terraform apply
```

Terraform does not recreate resources that are already correct in state.

### 5. If the resource exists but isn't in state

This is an important scenario.

Suppose Azure has the resource:

```
Azure:
Storage Account ✓

Terraform state:
Storage Account ✗
```

I don't blindly create it again.

I import it:

```bash
terraform import azurerm_storage_account.example <resource-id>
```

Then:

```bash
terraform plan
```

I make sure the Terraform configuration matches the existing resource.

### 6. If Terraform state is locked

If the pipeline crashed while Terraform was running, the remote state may still be locked.

First I check that no Terraform operation is actually running.

Then, if the lock is really stale:

```bash
terraform force-unlock <LOCK_ID>
```

I use `force-unlock` carefully. Running it while another Terraform operation is active can corrupt the state.

### 7. Don't manually delete everything

A common bad approach is:

```
Deployment failed
      ↓
Delete all Azure resources
      ↓
Run terraform apply again
```

I don't do that unless there is a specific reason.

Terraform is made to recover from partial applies. I find the failed resource, fix the problem, run plan, and then continue with apply.

### Example interview scenario

Suppose my Terraform creates:

```
Resource Group       ✓
VNet                 ✓
Subnet               ✓
AKS                  ✗
```

AKS fails because of an invalid SKU.

I would run:

```bash
terraform state list
```

to verify the resources that were created successfully.

Then check the AKS error in the pipeline.

Fix the SKU in the Terraform code.

Run:

```bash
terraform plan
```

I expect Terraform to show only the remaining AKS changes, not recreate the already-created resources.

Then:

```bash
terraform apply
```

Finally verify:

```bash
terraform plan
```

The expected result is:

```
No changes. Your infrastructure matches the configuration.
```

### Interview answer

> "If Terraform fails midway, I first check the exact error in the Terraform or Azure DevOps logs. Then I check `terraform state list` and `terraform state show` to understand which resources were successfully recorded. I also verify the actual Azure resources because I need to know whether the resource was created even if the Terraform operation failed. After fixing the root cause, I run `terraform plan` to see the remaining changes and then run `terraform apply` again. If a resource exists in Azure but isn't in state, I import it rather than recreating it. If there is a stale state lock, I verify no Terraform process is running and then use `terraform force-unlock` carefully. I avoid manually deleting infrastructure unless there is a specific reason."

---

## Q2. Have you done any automation using scripting? What have you done?

Yes. For an Azure DevOps interview, give a specific practical example, not just "I have written shell scripts."

### Strong interview answer

> "Yes, I have used both Bash and Python scripting for DevOps automation. One common automation I worked on was checking the health of application deployments and automating repetitive Azure and Kubernetes operations.
>
> For example, after an AKS deployment, instead of manually checking every pod, I used a Bash script to check pod status, deployment rollout status, and restart counts. If the deployment was unhealthy, the script captured the relevant pod logs and events and returned a non-zero exit code, which caused the Azure DevOps pipeline to fail.
>
> I have also used scripting for tasks like Azure resource checks, Docker image cleanup, Kubernetes operations, log collection, and automating repetitive pipeline activities."

### Small Bash example

```bash
#!/bin/bash

NAMESPACE="production"
DEPLOYMENT="myapp"

echo "Checking deployment..."

kubectl rollout status deployment/$DEPLOYMENT \
  -n $NAMESPACE \
  --timeout=180s

if [ $? -ne 0 ]; then
    echo "Deployment failed"

    echo "Pods:"
    kubectl get pods -n $NAMESPACE

    echo "Recent events:"
    kubectl get events -n $NAMESPACE --sort-by=.lastTimestamp | tail -20

    exit 1
fi

echo "Deployment successful"
```

I can call this from Azure DevOps:

```yaml
- script: |
    chmod +x scripts/check-deployment.sh
    ./scripts/check-deployment.sh
  displayName: 'Validate AKS Deployment'
```

### Another good example: Azure resource automation

Instead of manually checking multiple resources:

```bash
#!/bin/bash

RESOURCE_GROUP="my-rg"

az resource list \
  --resource-group "$RESOURCE_GROUP" \
  --query "[].{Name:name,Type:type}" \
  -o table
```

This can be added to a scheduled Azure DevOps pipeline.

### Python example

For more complex automation, I would use Python rather than a large Bash script.

For example, checking Azure resources:

```python
import subprocess

resource_group = "my-rg"

result = subprocess.run(
    ["az", "resource", "list",
     "--resource-group", resource_group,
     "-o", "json"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Azure resource check failed")
    exit(1)

print(result.stdout)
```

### If interviewer asks "Why scripting when Terraform/Ansible already exist?"

Answer:

> "I don't use scripting to replace Terraform or Ansible. I use the right tool for the task. Terraform is for infrastructure provisioning, Ansible is useful for configuration management, and Bash or Python is useful for glue automation, validation, health checks, log collection, API calls, and tasks that don't justify a full IaC solution."

---

## Q3. Give 5 automation examples each in Shell script and Python

For an Azure DevOps / DevOps interview, use examples that sound like real day-to-day work, not generic programming exercises.

## 5 Shell scripting automation examples

### 1. Kubernetes deployment health check

Used after deployment to check that pods are running and rollout is completed.

```bash
#!/bin/bash

NAMESPACE="production"
DEPLOYMENT="myapp"

kubectl rollout status deployment/$DEPLOYMENT \
  -n $NAMESPACE \
  --timeout=180s

if [ $? -ne 0 ]; then
    echo "Deployment failed"

    kubectl get pods -n $NAMESPACE
    kubectl get events -n $NAMESPACE --sort-by=.lastTimestamp | tail -20

    exit 1
fi

echo "Deployment successful"
```

**Interview explanation:**

> "I used a shell script after AKS deployment to automatically check rollout status. If the rollout failed, the script collected pod status and Kubernetes events and failed the Azure DevOps pipeline."

### 2. Docker image cleanup

Useful on self-hosted agents where old Docker images fill up the disk.

```bash
#!/bin/bash

echo "Docker disk usage:"
docker system df

echo "Removing unused images..."

docker image prune -af

echo "Removing unused containers..."
docker container prune -f

echo "Cleanup completed"
```

**Interview explanation:**

> "On self-hosted build agents, Docker images can consume a lot of disk space. I automated cleanup of unused images and containers using a shell script and scheduled it through cron or an Azure DevOps pipeline."

### 3. Check disk space and alert

```bash
#!/bin/bash

THRESHOLD=80

USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

echo "Disk usage: $USAGE%"

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    echo "WARNING: Disk usage is above $THRESHOLD%"
    exit 1
else
    echo "Disk usage is normal"
fi
```

**Interview explanation:**

> "I used shell scripting to monitor disk utilization on Linux servers. If usage crossed the configured threshold, the script returned a failure code so the monitoring or pipeline process could trigger an alert."

### 4. Backup and compress application logs

```bash
#!/bin/bash

LOG_DIR="/var/log/myapp"
BACKUP_DIR="/backup/logs"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_DIR/myapp-$DATE.tar.gz" "$LOG_DIR"

echo "Log backup created:"
ls -lh "$BACKUP_DIR/myapp-$DATE.tar.gz"
```

**Interview explanation:**

> "I automated application log backup by compressing the logs and creating a date-based archive. This helps with log retention and prevents the server disk from filling up."

### 5. Azure resource inventory

```bash
#!/bin/bash

RESOURCE_GROUP="my-rg"

echo "Azure resources in $RESOURCE_GROUP"

az resource list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[].{Name:name,Type:type,Location:location}" \
    -o table
```

**Interview explanation:**

> "I used Azure CLI inside a shell script to automate resource inventory. Instead of manually checking resources in the Azure portal, the script retrieves resource names, types and locations and can be scheduled or integrated into a pipeline."

## 5 Python automation examples

Python is more useful when the automation needs API calls, JSON processing, complex logic, or bigger workflows.

### 1. Check Azure resources using Azure CLI

```python
import subprocess
import json

resource_group = "my-rg"

result = subprocess.run(
    [
        "az", "resource", "list",
        "--resource-group", resource_group,
        "-o", "json"
    ],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Failed to retrieve Azure resources")
    exit(1)

resources = json.loads(result.stdout)

for resource in resources:
    print(resource["name"], resource["type"])
```

**Interview explanation:**

> "I used Python when I needed to process Azure CLI JSON output. The script retrieves resources, parses the JSON and performs additional logic such as filtering or reporting."

### 2. Kubernetes pod health checker

```python
import subprocess
import json

namespace = "production"

result = subprocess.run(
    ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Unable to retrieve pods")
    exit(1)

data = json.loads(result.stdout)

failed = []

for pod in data["items"]:
    name = pod["metadata"]["name"]
    phase = pod["status"].get("phase")

    if phase != "Running":
        failed.append(name)

if failed:
    print("Unhealthy pods:")
    for pod in failed:
        print(pod)
    exit(1)

print("All pods are healthy")
```

**Interview explanation:**

> "I used Python to query Kubernetes, parse the JSON response and identify pods that were not running. This was integrated into the deployment validation stage of the CI/CD pipeline."

### 3. Docker image cleanup based on age

Python gives more control than a simple `docker prune`.

```python
import subprocess
from datetime import datetime, timedelta

result = subprocess.run(
    ["docker", "images", "--format", "{{.ID}} {{.CreatedAt}}"],
    capture_output=True,
    text=True
)

cutoff = datetime.now() - timedelta(days=7)

for line in result.stdout.splitlines():
    print(line)
```

In a real implementation, I would parse the creation timestamp and remove images older than the retention period.

**Interview explanation:**

> "I used Python when cleanup rules became more complex, for example retaining the latest N images or deleting images older than a defined number of days."

### 4. Parse application logs and find errors

```python
import re

log_file = "application.log"

error_count = 0

with open(log_file, "r") as file:
    for line in file:
        if re.search(r"\bERROR\b|\bEXCEPTION\b", line):
            print(line.strip())
            error_count += 1

print(f"Total errors: {error_count}")

if error_count > 100:
    print("High number of errors detected")
    exit(1)
```

**Interview explanation:**

> "I used Python for log analysis because it is easier to implement filtering and pattern matching. The script scans application logs, identifies ERROR and EXCEPTION entries, counts them and can fail a pipeline or trigger an alert if the count exceeds a threshold."

### 5. Automated health check for application APIs

```python
import requests

urls = [
    "https://myapp.com/health",
    "https://myapp.com/api/health"
]

for url in urls:
    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            print(f"PASS: {url}")
        else:
            print(f"FAIL: {url} - {response.status_code}")

    except requests.RequestException as e:
        print(f"ERROR: {url} - {e}")
```

**Interview explanation:**

> "After deployment, I can use Python to call application health endpoints and verify that the APIs are responding correctly. This can be part of the post-deployment validation stage."

## How to answer in the interview

If they ask:

> "What automation have you done using Shell and Python?"

Give this answer:

> "I have used shell scripting mainly for lightweight Linux, Kubernetes and CI/CD automation. Five examples are Kubernetes deployment health checks, Docker cleanup on self-hosted agents, Linux disk-space monitoring, application log backup and Azure resource inventory using Azure CLI.
>
> I use Python when the automation requires more complex logic or data processing. For example, I have used Python for Azure resource processing, Kubernetes pod health checks, Docker image cleanup based on retention rules, application log analysis, and API health checks.
>
> I generally use Bash for simple command orchestration and pipeline tasks, while I prefer Python when I need JSON processing, API integration, error handling, or more complex business logic."

## The important distinction

| Shell | Python |
|---|---|
| Quick server automation | Complex automation |
| Linux commands | APIs |
| kubectl / az / docker orchestration | JSON processing |
| File operations | Log analysis |
| Simple health checks | Complex health checks |
| CI/CD helper scripts | Larger automation tools |

---

# Multiple Choice Questions (Deloitte - Saturday 2:31 PM)

## Q4. When using DevOps methodology for product development, what is the correct sequence to be followed?

Given steps:

1. Build the package with all necessary configurations
2. Test the project at each level and integrate it
3. Commit all code by using source control
4. Release the first version of the product
5. Bring the product into operation
6. Deploy the build in production server

Options:

- `1 -> 2 -> 3 -> 4 -> 6 -> 5`
- `6 -> 2 -> 3 -> 1 -> 4 -> 5`
- `5 -> 6 -> 3 -> 1 -> 4 -> 2`
- `2 -> 3 -> 4 -> 6 -> 5 -> 1`

**Correct answer:** `1 -> 2 -> 3 -> 4 -> 6 -> 5`

**Why:**

1. Build the package with required configurations
2. Test the project at each level and integrate it
3. Commit code to source control
4. Release the first version of the product
5. Deploy the build to the production server
6. Bring the product into operation

---

## Q5. What is the purpose of GitLab Environments in CI/CD?

Options:

1. To configure access control for CI/CD pipelines
2. To specify the platforms on which the application is deployed
3. To manage different deployment environments (e.g. development, staging, production)
4. To define the geographical regions where GitLab Runners are deployed

**Correct answer: Option 3** — To manage different deployment environments (development, staging, production)

**Explanation:**

GitLab Environments represent the different places where your application is deployed, such as:

- Development
- Testing
- Staging
- Production

They help to track deployments, deployment history, and environment status.

---

## Q6. Which of the options given below is the correct AWS DevOps tools workflow?

Options:

1. X-Ray -> CodeCommit -> CodeBuild -> CloudWatch
2. CodePipeline -> CodeCommit -> CodeBuild -> CodeDeploy
3. CodePipeline -> CloudWatch -> CodeBuild -> CodeDeploy
4. CloudWatch -> CodeCommit -> X-Ray -> CodeDeploy

**Correct answer: Option 2** — CodePipeline -> CodeCommit -> CodeBuild -> CodeDeploy

**Explanation:**

- **CodePipeline** - orchestrates the whole CI/CD flow
- **CodeCommit** - source code repository
- **CodeBuild** - builds and tests the code
- **CodeDeploy** - deploys the build to the servers

CloudWatch and X-Ray are monitoring tools, not part of the build and deploy chain.

---

## Q7. What should you do when your branch has merge conflicts with the main branch?

**Correct answer:** Pull the latest main branch, manually resolve conflicts, commit, and push the changes

**Steps:**

1. Pull / update the latest main branch
2. Resolve the conflicting sections manually
3. Commit the resolved changes
4. Push the updated branch
5. Re-run the merge / PR validation

---

## Q8. What is an Azure DevOps Service Connection used for?

Options:

1. Connecting Azure DevOps to an on-premises SQL database
2. Authenticating pipelines to external services like Azure and GitHub
3. Sharing artifacts between different DevOps organizations
4. Linking Azure DevOps boards to user email accounts

**Correct answer: Option 2** — Authenticating pipelines to external services like Azure and GitHub

**Explanation:**

An Azure DevOps Service Connection stores the authentication and configuration details a pipeline needs to securely connect to external services such as:

- Azure subscriptions
- Docker registries
- GitHub
- Kubernetes clusters

---

## Q9. Which Azure Monitor component collects telemetry from applications automatically?

Options:

1. Data Factory
2. Azure Batch
3. Azure Advisor
4. Application Insights

**Correct answer: Option 4** — Application Insights

**Explanation:**

Application Insights collects application telemetry such as:

- Requests
- Exceptions
- Response times
- Dependencies
- Performance metrics

---

## Q10. How do you resolve merge conflicts?

I resolve Git merge conflicts by finding the conflicting files, understanding both changes, resolving them manually, testing, and then completing the merge.

### Typical process

Suppose I'm merging `feature` into `main`:

```bash
git checkout main
git pull origin main

git merge feature
```

If there is a conflict:

```
CONFLICT (content): Merge conflict in deployment.yaml
Automatic merge failed
```

### 1. Identify conflicted files

```bash
git status
```

Example:

```
both modified: deployment.yaml
both modified: values.yaml
```

### 2. Open the conflicted file

Git adds markers:

```yaml
<<<<<<< HEAD
replicas: 3
image: myapp:v1
=======
replicas: 5
image: myapp:v2
>>>>>>> feature
```

Here:

```
HEAD    = current branch
feature = incoming branch
```

I don't blindly choose "ours" or "theirs". I understand why both changes were made and decide what the final configuration should be.

For example:

```yaml
replicas: 5
image: myapp:v2
```

Then remove the conflict markers:

```
<<<<<<<
=======
>>>>>>>
```

### 3. Check for remaining conflicts

```bash
git status
```

I can also search:

```bash
git diff --check
```

### 4. Stage the resolved files

```bash
git add deployment.yaml
git add values.yaml
```

Then verify:

```bash
git status
```

### 5. Complete the merge

```bash
git commit
```

Git creates the merge commit.

Then:

```bash
git push origin main
```

### If the conflict happens during rebase

The process is slightly different:

```bash
git rebase main
```

If there is a conflict:

```bash
git status
```

Resolve the file, then:

```bash
git add deployment.yaml
git rebase --continue
```

If more conflicts come, repeat the same process.

If I need to stop the rebase:

```bash
git rebase --abort
```

For a merge:

```bash
git merge --abort
```

### Important interview scenario

If a developer says:

> "I have a PR with conflicts. What will you do?"

I would say:

> "I first pull the latest target branch and reproduce the conflict locally. I identify the conflicting files using `git status`, inspect both changes, and resolve the conflict based on the intended application behavior rather than blindly choosing ours or theirs. Then I run `git diff --check`, unit tests and any relevant build or validation, stage the resolved files and complete the merge or rebase. Finally, I push the updated branch and verify the PR pipeline again."

### Useful commands to remember

```bash
git status
git diff
git diff --check

git merge <branch>
git merge --abort

git rebase <branch>
git rebase --continue
git rebase --abort

git add <file>
git commit
git push
```

**Key point:** A merge conflict is not just a Git problem. The correct resolution depends on the intended behaviour of the code or configuration. Always test after resolving it.

---

## Q11. Give 5 more automation examples — restarting services, checking error logs, taking backups, sending alert emails

Yes. Those are better real-world DevOps automation examples for an interview. Use examples where you can clearly explain the manual work that was eliminated.

### 5 Shell scripting automation examples

#### 1. Automatically restart a failed service

Problem: Application service occasionally stops. Someone had to SSH into the server, check it and restart it.

```bash
#!/bin/bash

SERVICE="myapp"

if systemctl is-active --quiet "$SERVICE"; then
    echo "$SERVICE is running"
else
    echo "$SERVICE is down"
    systemctl restart "$SERVICE"

    if systemctl is-active --quiet "$SERVICE"; then
        echo "$SERVICE restarted successfully"
    else
        echo "Failed to restart $SERVICE"
        exit 1
    fi
fi
```

Automation flow:

```
Check service
     |
     v
Service down?
     |
     v
  Restart
     |
     v
Still down?
     |
     v
Send alert
```

**Interview explanation:**

> "I automated service health checking. If the service was down, the script automatically restarted it and returned a failure if the restart didn't succeed."

#### 2. Check application logs for errors and send email

Problem: DevOps team had to manually search logs for `ERROR` and `Exception`.

```bash
#!/bin/bash

LOG_FILE="/var/log/myapp/application.log"
ERROR_COUNT=$(grep -Ei "ERROR|Exception|Failed" "$LOG_FILE" | wc -l)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "Found $ERROR_COUNT errors in application logs"

    grep -Ei "ERROR|Exception|Failed" "$LOG_FILE" \
        | tail -50 > /tmp/app_errors.txt

    mail -s "Application Error Alert" devops@example.com \
        < /tmp/app_errors.txt
fi
```

You can schedule this using cron:

```
*/10 * * * * /opt/scripts/check_logs.sh
```

**Interview explanation:**

> "I automated log monitoring using grep and cron. If the script found application errors, it collected the recent errors and sent an email to the support team."

#### 3. Automated server backup

Problem: Manual backup of configuration files and application data.

```bash
#!/bin/bash

SOURCE="/opt/myapp/config"
BACKUP="/backup/myapp"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP"

tar -czf "$BACKUP/myapp_config_$DATE.tar.gz" "$SOURCE"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully"
else
    echo "Backup failed"
    exit 1
fi
```

Schedule:

```
0 2 * * * /opt/scripts/backup.sh
```

**Interview explanation:**

> "I automated daily configuration backups using tar and cron. The backup file had a timestamp, and the script returned a failure if the backup operation failed."

#### 4. Disk-space monitoring and alert

Problem: Servers were running out of disk space because of logs and temporary files.

```bash
#!/bin/bash

THRESHOLD=80

USAGE=$(df -P / | awk 'NR==2 {gsub("%",""); print $5}')

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    echo "Disk usage is $USAGE%"

    df -h / | mail \
        -s "Disk Space Alert" \
        devops@example.com
else
    echo "Disk usage is $USAGE%"
fi
```

**Interview explanation:**

> "I created a shell script that checks disk utilization periodically. If usage crossed 80%, it automatically sent an email alert so we could take action before the server became unavailable."

#### 5. Automated log cleanup

Problem: Application logs were filling the server.

```bash
#!/bin/bash

LOG_DIR="/var/log/myapp"

find "$LOG_DIR" \
    -type f \
    -name "*.log" \
    -mtime +7 \
    -delete

echo "Old logs cleaned successfully"
```

**Interview explanation:**

> "I automated log retention using the Linux find command. Logs older than seven days were removed based on our retention requirement. This prevented unnecessary disk consumption."

### 5 Python automation examples

Python examples should demonstrate where Python is better than a simple Bash command, especially API calls, JSON processing, structured reporting and exception handling.

#### 1. Restart service and send email if restart fails

```python
import subprocess
import smtplib
from email.message import EmailMessage

SERVICE = "myapp"

status = subprocess.run(
    ["systemctl", "is-active", "--quiet", SERVICE]
)

if status.returncode != 0:
    print(f"{SERVICE} is down. Restarting...")

    restart = subprocess.run(
        ["systemctl", "restart", SERVICE]
    )

    if restart.returncode != 0:
        msg = EmailMessage()
        msg["Subject"] = "Service Restart Failed"
        msg["From"] = "devops@example.com"
        msg["To"] = "support@example.com"

        msg.set_content(
            f"Unable to restart {SERVICE}"
        )

        with smtplib.SMTP("smtp.example.com", 25) as smtp:
            smtp.send_message(msg)

        raise SystemExit(1)

print("Service is running")
```

**Interview explanation:**

> "I used Python to monitor a Linux service. If it was down, the script attempted a restart. If the restart failed, it automatically sent an email notification."

#### 2. Parse logs and generate an error report

Python is useful when log analysis becomes more complex.

```python
import re

log_file = "/var/log/myapp/application.log"

errors = []

with open(log_file) as file:
    for line in file:
        if re.search(r"ERROR|Exception|Failed", line, re.IGNORECASE):
            errors.append(line.strip())

with open("/tmp/error_report.txt", "w") as report:
    report.write("Application Error Report\n")
    report.write("=" * 40 + "\n")

    for error in errors[-100:]:
        report.write(error + "\n")

print(f"Found {len(errors)} errors")
```

You can then email `/tmp/error_report.txt`.

**Interview explanation:**

> "I used Python to parse application logs, identify different error patterns using regular expressions, generate a report and send it to the support team."

#### 3. Automated backup with retention

```python
import shutil
from pathlib import Path
from datetime import datetime, timedelta

source = Path("/opt/myapp/config")
backup_dir = Path("/backup/myapp")

backup_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

archive = backup_dir / f"config_{timestamp}"

shutil.make_archive(
    str(archive),
    "gztar",
    source
)

print(f"Backup created: {archive}.tar.gz")

# Remove backups older than 7 days
cutoff = datetime.now() - timedelta(days=7)

for file in backup_dir.glob("*.tar.gz"):
    if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
        file.unlink()
        print(f"Deleted old backup: {file}")
```

**Interview explanation:**

> "I used Python to automate backups and retention. It created timestamped compressed backups and automatically removed backups older than the retention period."

#### 4. Monitor multiple servers and send one email report

This is a good Python example because you're handling multiple servers and structured results.

```python
import subprocess

servers = [
    "server01",
    "server02",
    "server03"
]

failed = []

for server in servers:

    result = subprocess.run(
        ["ssh", server, "systemctl is-active myapp"],
        capture_output=True,
        text=True
    )

    status = result.stdout.strip()

    if status != "active":
        failed.append((server, status))

if failed:
    print("Failed servers:")

    for server, status in failed:
        print(server, status)
else:
    print("All servers are healthy")
```

This can be extended to send one consolidated email:

```
Server Health Report

server01 -> OK
server02 -> FAILED
server03 -> OK
```

**Interview explanation:**

> "Instead of checking servers individually, I used Python to connect to multiple servers, check the application service status, generate a consolidated report and notify the team if any server was unhealthy."

#### 5. API health monitoring

Python is very useful for automating application/API checks.

```python
import requests

apis = {
    "Login API": "https://myapp.com/api/login/health",
    "Order API": "https://myapp.com/api/orders/health",
    "Payment API": "https://myapp.com/api/payment/health"
}

failed = []

for name, url in apis.items():

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            failed.append(
                f"{name}: HTTP {response.status_code}"
            )

    except requests.RequestException as error:
        failed.append(f"{name}: {error}")

if failed:
    print("API failures detected:")

    for error in failed:
        print(error)

    exit(1)

print("All APIs are healthy")
```

**Interview explanation:**

> "I used Python to monitor multiple application APIs. The script checked HTTP status codes and connection failures and generated an alert when an API was unavailable. This was useful as a post-deployment health check."

### Which examples should you tell the interviewer?

I'd use these 10 examples because they sound realistic for a DevOps role:

| Shell | Python |
|---|---|
| Restart failed service | Restart service + email alert |
| Search logs for errors | Parse logs + generate report |
| Automated server backup | Backup + retention |
| Disk-space monitoring | Monitor multiple servers |
| Log cleanup | API health monitoring |

### Best 30-second answer

> "Yes, I have automated several repetitive operational tasks using Shell and Python. In Shell, I automated service restart, application log error checking with email alerts, server backups, disk-space monitoring and log cleanup using cron. In Python, I used scripts for more complex automation such as service monitoring with email notifications, parsing application logs and generating reports, backup and retention management, checking multiple servers, and API health monitoring. These scripts reduced manual intervention and could be integrated with our Azure DevOps pipelines or scheduled through cron."

---

## Q12. How have you reduced cloud cost in Azure? Give a few examples.

For an Azure DevOps interview, give practical cost-saving examples and explain what you changed, why, and how you measured it.

### 1. Right-size VMs

> "I reviewed VM CPU and memory utilization using Azure Monitor. If a VM was consistently underutilized, for example using only 10-20% CPU, I recommended moving it to a smaller SKU."

Example:

```
Before:
D4s_v5 -> 4 vCPU / 16 GB

After:
D2s_v5 -> 2 vCPU / 8 GB
```

I would validate the workload before downsizing and monitor it after the change.

Cost saving: Lower compute cost without affecting application performance.

### 2. Stop non-production resources after working hours

For Dev/Test environments, resources don't need to run 24/7.

```
Dev VM
  |
  v
Stop at 8 PM
  |
  v
Start at 8 AM
```

I can automate this with Azure Automation, Logic Apps, Functions, or scheduled Azure DevOps jobs.

For example:

```bash
az vm deallocate \
  --resource-group dev-rg \
  --name dev-vm
```

Important: `deallocate` is different from simply shutting down the OS because deallocation releases the VM compute allocation.

Cost saving: Avoid paying for compute during unused hours.

### 3. AKS node optimization

I would monitor:

- CPU utilization
- Memory utilization
- Pod density
- Node utilization
- Cluster autoscaler behavior

If nodes are consistently underutilized, I can reduce the node count or use a smaller VM SKU.

For example:

```
Before:
5 x D4s_v5 nodes

After:
3 x D4s_v5 nodes
```

I can also use Cluster Autoscaler so AKS adds/removes nodes based on pending workload.

```
Low workload
     |
     v
Fewer nodes

High workload
     |
     v
More nodes
```

### 4. Use Azure Reservations / Savings Plan

For workloads that are predictable and continuously running, such as production VMs, I would evaluate:

- Azure Reservations
- Azure Savings Plan for Compute

Instead of paying the full pay-as-you-go rate for stable workloads.

For example:

```
Production VM
Runs 24 x 7
        |
        v
Analyze historical usage
        |
        v
Commit appropriate capacity
        |
        v
Lower compute cost
```

I wouldn't use a long-term commitment for highly variable or temporary workloads.

### 5. Remove unused resources

This is one of the easiest cost optimizations.

I regularly look for unused:

- Managed disks
- Snapshots
- Public IPs
- Load balancers
- Old VM resources
- Unused NICs
- Old container images
- Unused App Service plans
- Old backups

For example, a VM may be deleted but its managed disk remains.

```
VM deleted
   |
   v
Disk still exists
   |
   v
Still generating cost
```

I can use Azure Resource Graph/CLI to identify orphaned resources and clean them up after validation.

### 6. Storage lifecycle management

For storage accounts, I can move old data to cheaper tiers.

```
Hot
 |
 v
Cool
 |
 v
Archive
```

For logs or backups that are rarely accessed:

```
Recent logs -> Hot
Older logs  -> Cool
Old backups -> Archive
```

I would configure lifecycle management rules rather than manually moving files.

### 7. Optimize Azure DevOps build agents

If we're using self-hosted agents, I can clean up:

- Old Docker images
- Containers
- Build artifacts
- Temporary files
- Workspace files

For Microsoft-hosted agents, I avoid unnecessary work by improving pipeline efficiency, such as:

- Dependency caching
- Parallel jobs
- Incremental builds
- Docker layer caching

This doesn't just reduce Azure infrastructure cost. It reduces pipeline execution time and compute consumption.

### 8. Container image optimization

For Docker workloads, I use:

- Multi-stage builds
- Smaller base images
- `.dockerignore`
- Layer caching

For example:

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

Instead of putting Node.js, npm, source code and build dependencies into the production image, the final image only contains Nginx and the built application.

This reduces:

- ACR storage
- Image transfer time
- AKS pull time
- Container storage usage

### 9. Log retention optimization

Logs can become surprisingly expensive.

I review:

```
Log Analytics
     |
     v
Retention
     |
     v
Ingestion volume
     |
     v
Cost
```

I avoid sending unnecessary verbose/debug logs to Log Analytics in production.

For example:

```
DEBUG -> Don't collect in production unless required
INFO  -> Keep where useful
ERROR -> Always retain
```

I also configure appropriate retention and archive older data where required.

### 10. Resource tagging and cost analysis

I use consistent tags:

```
Environment = Production
Application = Payments
Owner       = DevOps
CostCenter  = 1234
```

Then Azure Cost Management can help identify which application/team/environment is consuming money.

Example:

```
Application A -> ₹80,000/month
Application B -> ₹25,000/month
Unused Dev    -> ₹15,000/month
```

Then I investigate the biggest unexpected spend first.

### Strong interview answer

If they ask "How have you reduced Azure cloud costs?", say:

> "I have approached cost optimization mainly through resource utilization and automation. First, I used Azure Monitor metrics to identify underutilized VMs and right-size them. For non-production environments, I automated VM shutdown and startup during non-working hours. For AKS, I monitored node and pod utilization and used appropriate node sizing and cluster autoscaling to avoid running unnecessary nodes.
>
> I also cleaned up orphaned resources such as unattached managed disks, unused public IPs, snapshots and old container images. For storage, I used lifecycle policies to move older data from Hot to Cool or Archive tiers. For stable production workloads, I would evaluate Azure Reservations or Savings Plans based on historical usage.
>
> On the DevOps side, I optimized Docker images using multi-stage builds and cleaned up self-hosted agent resources. I also reviewed Log Analytics ingestion and retention so we weren't unnecessarily storing verbose logs. Finally, I used resource tagging and Azure Cost Management to identify which applications and environments were actually driving the cost."

### If they ask "How did you prove the saving?"

Don't say "I think it reduced the cost."

Say:

> "I compared the Azure Cost Management data before and after the change, while controlling for workload changes. For example, after right-sizing or shutting down non-production resources, I compared the monthly compute cost and validated that application performance and availability remained within the required limits."

That's a much stronger DevOps interview answer.

---

## Q13. What are the key Helm commands to remember for deployment and rollback?

### Helm deployment

The standard command is:

```bash
helm upgrade --install myapp ./helm/myapp \
  -n production \
  --create-namespace \
  -f values-prod.yaml \
  --set image.tag=123
```

What each part means:

- `upgrade --install` → Install if the release doesn't exist; otherwise upgrade it.
- `myapp` → Helm release name.
- `./helm/myapp` → Helm chart location.
- `-n production` → Kubernetes namespace.
- `--create-namespace` → Creates namespace if it doesn't exist.
- `-f values-prod.yaml` → Environment-specific configuration.
- `--set image.tag=123` → Overrides the image tag.

### Check deployment

```bash
helm list -n production
helm status myapp -n production
helm history myapp -n production
```

You can also verify the Kubernetes rollout:

```bash
kubectl rollout status deployment/myapp -n production
```

### Helm rollback

First check the release history:

```bash
helm history myapp -n production
```

Example:

```
REVISION   STATUS
1          superseded
2          superseded
3          deployed
```

If revision 3 has an issue and you want to go back to revision 2:

```bash
helm rollback myapp 2 -n production
```

Then verify:

```bash
helm status myapp -n production
helm history myapp -n production
```

And:

```bash
kubectl rollout status deployment/myapp -n production
```

### Important interview point

Don't confuse Helm rollback with Kubernetes rollback.

Helm:

```bash
helm rollback myapp 2 -n production
```

Kubernetes:

```bash
kubectl rollout undo deployment/myapp -n production
```

If the application was deployed and managed by Helm, I generally prefer Helm rollback, because Helm understands the release history and restores the chart configuration associated with that revision.

### Typical CI/CD flow

```
Build application
       |
       v
Build Docker image
       |
       v
Push image to ACR
       |
       v
helm upgrade --install
       |
       v
AKS deployment
       |
       v
Health/rollout check
       |
       v
PASS -> Continue
FAIL -> helm rollback
```

### Interview answer

> "For deployment, I normally use `helm upgrade --install`, which installs the release if it doesn't exist and upgrades it if it already exists. I pass the environment-specific values file and the Docker image tag generated by the CI pipeline. After deployment, I verify the Helm release and Kubernetes rollout. If the new version causes an issue, I check `helm history` and execute `helm rollback <release> <revision> -n <namespace>` to restore the previous Helm release."

---

## Q14. You have one Terraform state file for the entire company's infrastructure — how can multiple people use it at the same time?

If you have one Terraform state file for the entire company infrastructure, you should not store it locally or let everyone directly edit it. You put it in a remote backend with state locking.

For Azure, a common setup is Azure Storage Account + Blob Storage.

### Architecture

```
Developer A --.
Developer B --|
Developer C --+--> Azure Storage Account
DevOps CI/CD -|         |
Developer D --'         +-- terraform.tfstate
                             + State Lock
```

### Backend configuration

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-rg"
    storage_account_name = "tfstatecompany"
    container_name       = "tfstate"
    key                  = "company-infra.tfstate"
  }
}
```

Then everyone runs:

```bash
terraform init
```

Terraform knows that the state is stored remotely.

### What happens if two people run Terraform at the same time?

Suppose Developer A runs:

```bash
terraform apply
```

Terraform acquires the state lock.

```
Developer A
    |
    | terraform apply
    v
State Lock = ACQUIRED
    |
    v
Modify state
    |
    v
Release Lock
```

If Developer B tries to run `terraform apply` while A has the lock:

```
Developer B
    |
    | terraform apply
    v
State Lock = BUSY
    |
    X
Wait / fail
```

Terraform prevents both users from modifying the same state simultaneously.

### Important distinction

Multiple people can access the remote state, but they should not modify the same state simultaneously.

For example:

```bash
terraform plan
```

can generally be run by multiple people, but:

```bash
terraform apply
```

should be controlled/serialized.

### In a real company

I would not actually recommend one state file for the entire company. That's a bad design because the blast radius becomes huge.

Instead, split state by logical scope/environment:

```
tfstate/
├── networking-prod.tfstate
├── networking-dev.tfstate
├── aks-prod.tfstate
├── aks-dev.tfstate
├── database-prod.tfstate
└── application-prod.tfstate
```

Or use separate Terraform root modules and state per environment.

This gives you:

- Smaller blast radius
- Less state contention
- Better access control
- Faster plans
- Easier troubleshooting
- Safer production changes

### Interview answer

> "I would store the Terraform state remotely in an Azure Storage Account using the `azurerm` backend. Azure Blob Storage provides centralized state storage, and Terraform uses state locking to prevent concurrent state modifications. If one engineer is running `terraform apply`, Terraform acquires the lock and another engineer cannot modify that same state until the lock is released. However, I wouldn't recommend having one state file for the entire company. I would split the infrastructure into multiple state files based on environment and logical components, such as networking, AKS and databases, to reduce contention and blast radius."

---

## Q15. How do you avoid duplicating YAML across Azure DevOps pipelines?

In Azure DevOps, I avoid duplicating YAML by using templates, parameters, variables, and stages/jobs templates.

The most common approach is to create reusable YAML templates and pass parameters to them.

### Example

Suppose I have `dev`, `qa`, and `prod` stages. Instead of writing the same deployment steps three times:

```
azure-pipelines.yml
templates/
  build.yml
  deploy.yml
```

#### 1. Create a reusable template

`templates/deploy.yml`

```yaml
parameters:
- name: environment
  type: string

- name: namespace
  type: string

- name: replicas
  type: number
  default: 2

stages:
- stage: Deploy_${{ parameters.environment }}
  displayName: Deploy to ${{ parameters.environment }}

  jobs:
  - job: Deploy
    steps:
    - script: |
        echo "Deploying to ${{ parameters.environment }}"
        echo "Namespace: ${{ parameters.namespace }}"
        echo "Replicas: ${{ parameters.replicas }}"
      displayName: Deploy application
```

#### 2. Reuse the template

In `azure-pipelines.yml`:

```yaml
trigger:
- main

stages:

- template: templates/deploy.yml
  parameters:
    environment: dev
    namespace: dev
    replicas: 1

- template: templates/deploy.yml
  parameters:
    environment: qa
    namespace: qa
    replicas: 2

- template: templates/deploy.yml
  parameters:
    environment: prod
    namespace: prod
    replicas: 3
```

Now the deployment logic exists only once.

### Another common approach: steps template

If only the steps are repeated, I use a steps template.

`templates/build-steps.yml`:

```yaml
steps:

- checkout: self

- script: |
    npm install
    npm test
    npm run build
  displayName: Build and Test

- task: Docker@2
  inputs:
    command: buildAndPush
    repository: myapp
    tags: |
      $(Build.BuildId)
```

Then:

```yaml
stages:

- stage: Dev
  jobs:
  - job: Build
    steps:
    - template: templates/build-steps.yml

- stage: QA
  jobs:
  - job: Build
    steps:
    - template: templates/build-steps.yml
```

### What I use in real projects

I normally structure it like:

```
azure-pipelines.yml
templates/
├── build.yml
├── test.yml
├── sonar.yml
├── docker-build.yml
├── helm-deploy.yml
└── security-scan.yml
```

The main pipeline becomes mostly orchestration:

```
Main Pipeline
     |
     +-- Build template
     |
     +-- Test template
     |
     +-- SonarQube template
     |
     +-- Docker template
     |
     +-- Deploy template
```

For multiple repositories, I would take this one step further and use an Azure DevOps YAML repository / centralized template repository. That allows many pipelines to consume the same templates.

### Interview answer

> "I avoid duplicating YAML by creating reusable templates. Depending on the requirement, I use step templates for common steps, job templates for reusable jobs, and stage templates for complete environment deployments. I pass environment-specific values such as environment name, namespace, replica count, and image tag through parameters. For organization-wide reuse, I keep these templates in a centralized Azure Repos repository and reference them from different application pipelines. This gives us one place to maintain common CI/CD logic instead of modifying every pipeline individually."

---

## Q16. How do you integrate Azure DevOps with Kubernetes/AKS?

You integrate Azure DevOps with Kubernetes/AKS mainly to automate application deployment through a CI/CD pipeline.

### End-to-end flow

```
Developer
   |
   v
Git Repository
   |
   v
Azure DevOps CI Pipeline
   |
   +--> Build application
   +--> Unit tests
   +--> SonarQube scan
   +--> Build Docker image
   +--> Push image to ACR
   |
   v
Azure DevOps CD Pipeline
   |
   +--> Authenticate to AKS
   +--> Helm / kubectl
   +--> Deploy application
   |
   v
AKS Cluster
   |
   +--> Deployment
   +--> Service
   +--> Ingress
   +--> Pods
```

### 1. Create Azure resources

Typically I use:

- Azure Container Registry (ACR) for Docker images
- AKS for Kubernetes
- Azure DevOps for source code and CI/CD
- Helm for Kubernetes deployments

Example:

```
Azure DevOps
     |
     +------> ACR
     |          |
     |          +--> application:v1.0
     |
     +------> AKS
                |
                +--> Pods
                +--> Services
                +--> Ingress
```

### 2. Create Azure DevOps Service Connection

For Azure resources, I create an Azure Resource Manager service connection.

For example:

```
Azure DevOps
     |
     v
Azure Resource Manager Service Connection
     |
     +--> ACR
     +--> AKS
```

The service connection provides authentication without putting Azure credentials directly inside the YAML file.

### 3. Build and push Docker image

Example:

```yaml
- task: Docker@2
  inputs:
    containerRegistry: 'ACR-Service-Connection'
    repository: 'myapp'
    command: 'buildAndPush'
    Dockerfile: '**/Dockerfile'
    tags: |
      $(Build.BuildId)
```

This builds `myapp:<BuildId>` and pushes it to ACR.

### 4. Connect Azure DevOps to AKS

There are different approaches.

For AKS, I commonly use the Azure Resource Manager service connection with the Kubernetes/AKS deployment task.

For example:

```yaml
- task: KubernetesManifest@1
  inputs:
    action: deploy
    connectionType: azureResourceManager
    azureSubscriptionConnection: 'Azure-Service-Connection'
    azureResourceGroup: 'my-rg'
    kubernetesCluster: 'my-aks'
    namespace: 'default'
    manifests: |
      manifests/deployment.yaml
      manifests/service.yaml
```

Azure DevOps obtains the AKS credentials and performs the deployment.

### 5. Using Helm

In real projects, I would generally prefer Helm for application deployment.

Example:

```yaml
- task: HelmDeploy@1
  inputs:
    connectionType: 'Azure Resource Manager'
    azureSubscription: 'Azure-Service-Connection'
    azureResourceGroup: 'my-rg'
    kubernetesCluster: 'my-aks'
    namespace: 'production'
    command: 'upgrade'
    chartType: 'FilePath'
    chartPath: 'helm/myapp'
    releaseName: 'myapp'
    overrideValues: |
      image.repository=myacr.azurecr.io/myapp
      image.tag=$(Build.BuildId)
```

The important part is that the pipeline dynamically passes the newly built image tag into the Helm deployment.

### 6. Complete practical pipeline

A simplified pipeline could look like:

```yaml
stages:

- stage: Build
  jobs:
  - job: Build
    steps:

    - checkout: self

    - task: SonarQubePrepare@7
      inputs:
        SonarQube: 'SonarQube-Connection'
        scannerMode: 'Other'

    - script: |
        mvn clean test
      displayName: 'Build and Test'

    - task: SonarQubeAnalyze@7

    - task: Docker@2
      inputs:
        containerRegistry: 'ACR-Service-Connection'
        repository: 'myapp'
        command: 'buildAndPush'
        Dockerfile: '**/Dockerfile'
        tags: |
          $(Build.BuildId)


- stage: Deploy
  dependsOn: Build
  jobs:
  - job: Deploy
    steps:

    - task: HelmDeploy@1
      inputs:
        connectionType: 'Azure Resource Manager'
        azureSubscription: 'Azure-Service-Connection'
        azureResourceGroup: 'my-rg'
        kubernetesCluster: 'my-aks'
        namespace: 'production'
        command: 'upgrade'
        chartType: 'FilePath'
        chartPath: 'helm/myapp'
        releaseName: 'myapp'
        install: true
        overrideValues: |
          image.repository=myacr.azurecr.io/myapp
          image.tag=$(Build.BuildId)
```

### 7. How authentication works

There are actually two separate authentication requirements:

**Azure DevOps → Azure/AKS**

Use an Azure Resource Manager service connection.

```
Azure DevOps
      |
      | Service Connection
      v
    Azure
      |
      +--> AKS
      +--> ACR
```

**AKS → ACR**

AKS also needs permission to pull the image from ACR.

A common approach is to give the AKS kubelet identity the `AcrPull` role on the registry.

```
AKS kubelet identity
        |
        | AcrPull
        v
       ACR
        |
        v
   Docker image
```

This is important. Azure DevOps being able to push to ACR does not automatically mean AKS can pull from ACR.

### Interview answer

> "I integrate Azure DevOps with AKS using CI/CD. In the CI stage, the pipeline checks out the code, runs unit tests and SonarQube analysis, builds the Docker image and pushes it to Azure Container Registry. For deployment, I configure an Azure Resource Manager service connection and use Helm or KubernetesManifest tasks to authenticate with AKS and deploy the application. We normally use Helm charts with environment-specific values and pass the Docker image tag generated by the CI pipeline. AKS is given AcrPull permission so that its kubelet identity can pull the image from ACR. After deployment, I verify the rollout using kubectl and monitor the application through Azure Monitor or Prometheus and Grafana."

---

## Q17. How do you integrate SonarQube in an Azure DevOps pipeline?

In an Azure DevOps CI pipeline, SonarQube is normally integrated as a sequence of tasks:

```
Code -> Build -> SonarQube analysis -> Quality Gate -> Publish artifact
```

### 1. Create SonarQube project

In SonarQube:

- Create a project.
- Note the Project Key.
- Generate a SonarQube token.

Example:

```
Project Key: my-java-app
```

### 2. Create the Service Connection in Azure DevOps

In Azure DevOps:

```
Project Settings -> Service connections -> New service connection -> SonarQube
```

Provide:

- SonarQube server URL
- Authentication token
- Service connection name, for example `SonarQube-Connection`

This allows the Azure DevOps pipeline to authenticate with SonarQube.

### 3. Install SonarQube extension

From Azure DevOps Marketplace, install the SonarQube/SonarCloud extension for your organization.

Then the pipeline can use tasks such as:

- `SonarQubePrepare`
- `SonarQubeAnalyze`
- `SonarQubePublish`

### 4. Add tasks to the YAML pipeline

For example, for a Maven application:

```yaml
trigger:
- main

pool:
  vmImage: ubuntu-latest

steps:

- task: SonarQubePrepare@7
  inputs:
    SonarQube: 'SonarQube-Connection'
    scannerMode: 'Other'
    extraProperties: |
      sonar.projectKey=my-java-app
      sonar.projectName=my-java-app

- task: Maven@4
  inputs:
    mavenPomFile: 'pom.xml'
    goals: 'clean verify'
    publishJUnitResults: true

- task: SonarQubeAnalyze@7

- task: SonarQubePublish@7
  inputs:
    pollingTimeoutSec: '300'
```

The important point is that `SonarQubePrepare` comes before the build, because it configures the scanner.

### 5. How the flow works

```
Developer
   |
   v
Git Repository
   |
   v
Azure DevOps Pipeline
   |
   +--> SonarQubePrepare
   |
   +--> Build / Unit Tests
   |
   +--> SonarQubeAnalyze
   |
   +--> SonarQube Server
   |       |
   |       +--> Bugs
   |       +--> Vulnerabilities
   |       +--> Code Smells
   |       +--> Code Coverage
   |       +--> Quality Gate
   |
   +--> SonarQubePublish
   |
   v
Pipeline Result
```

### 6. Quality Gate

In a real project, I would also configure the pipeline so that a failed Quality Gate prevents the deployment.

For example:

```
Quality Gate
   |
   +-- Bugs = 0
   +-- Vulnerabilities = 0
   +-- Coverage >= 80%
   +-- Code Smells within threshold
   |
   +-- PASS --> Continue deployment
   |
   +-- FAIL --> Stop pipeline
```

### Interview answer

If the interviewer asks "How have you integrated SonarQube with Azure DevOps?", a good answer is:

> "I integrated SonarQube into Azure DevOps CI pipelines using the SonarQube Azure DevOps extension. First, I created a SonarQube project and configured a SonarQube service connection in Azure DevOps using the authentication token. In the YAML pipeline, I use `SonarQubePrepare` before the build, then execute the application build and unit tests, followed by `SonarQubeAnalyze` and `SonarQubePublish`. The analysis results are sent to the SonarQube server, where it checks bugs, vulnerabilities, code smells and coverage against the configured Quality Gate. If the Quality Gate fails, we prevent the pipeline from progressing to deployment."

**Important:** The exact task versions and scanner configuration depend on whether you're analyzing Maven, Gradle, .NET, Node.js, or another language.

---

## Q18. How would you improve/optimize Kubernetes deployments, with and without Helm?

### 1. Deployment without Helm

Without Helm, we manage Kubernetes manifests directly:

```
deployment.yaml
service.yaml
configmap.yaml
secret.yaml
ingress.yaml
```

Azure DevOps pipeline can deploy them using `kubectl` or `KubernetesManifest@1`.

Example:

```yaml
- task: KubernetesManifest@1
  inputs:
    action: deploy
    connectionType: azureResourceManager
    azureSubscriptionConnection: 'Azure-Connection'
    azureResourceGroup: 'my-rg'
    kubernetesCluster: 'my-aks'
    manifests: |
      k8s/deployment.yaml
      k8s/service.yaml
      k8s/ingress.yaml
```

Or directly:

```bash
kubectl apply -f k8s/
```

#### How I improve this

I avoid hardcoding image tags:

```yaml
image: myacr.azurecr.io/myapp:latest
```

Instead:

```yaml
image: myacr.azurecr.io/myapp:$(Build.BuildId)
```

Then I can deploy a specific immutable version.

I also use:

```bash
kubectl rollout status deployment/myapp
```

and:

```bash
kubectl rollout history deployment/myapp
```

For rollback:

```bash
kubectl rollout undo deployment/myapp
```

### 2. Deployment with Helm

With Helm, I package the Kubernetes resources into a Helm chart.

```
myapp/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-qa.yaml
├── values-prod.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── configmap.yaml
```

Instead of maintaining separate manifests for every environment, I keep common templates and change values.

For example:

```yaml
image:
  repository: myacr.azurecr.io/myapp
  tag: "1234"

replicaCount: 3
```

Then:

```bash
helm upgrade --install myapp ./helm/myapp \
  -f ./helm/myapp/values-prod.yaml \
  --set image.tag=1234 \
  -n production
```

Helm keeps track of the release, which makes upgrades and rollbacks easier.

```bash
helm history myapp
```

Rollback:

```bash
helm rollback myapp 2
```

### 3. How I improve the deployment

I would use several practices.

#### Immutable image tags

Don't use:

```
latest
```

Use:

- Build ID
- Git commit SHA
- Release version

For example:

```
myapp:20260822.15
```

#### Environment-specific values

```
values-dev.yaml
values-qa.yaml
values-prod.yaml
```

Keep the Helm template common and only change environment-specific configuration.

#### Health checks

Configure:

```yaml
livenessProbe:
readinessProbe:
startupProbe:
```

This prevents traffic from reaching an unhealthy application.

#### Rolling deployment

Use Kubernetes rolling updates:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

This allows the new version to come up before taking the old version down.

#### Automated validation

Before deployment:

```bash
helm lint ./helm/myapp
helm template myapp ./helm/myapp
```

You can also run security/scanning tools such as Trivy or Checkov depending on what you're scanning.

After deployment:

```bash
kubectl rollout status deployment/myapp -n production
kubectl get pods -n production
```

### Helm vs without Helm

| Without Helm | With Helm |
|---|---|
| Manage raw YAML | Package Kubernetes resources as charts |
| `kubectl apply` | `helm upgrade/install` |
| More YAML duplication across environments | Reusable templates |
| Rollback through Kubernetes revisions | Helm release rollback |
| Configuration management is manual | `values.yaml` handles configuration |
| Simple applications | Better for complex/multi-environment applications |

### Interview answer

> "I have used both approaches. Without Helm, I maintain Kubernetes manifests and deploy them through kubectl or the KubernetesManifest task in Azure DevOps. I use immutable image tags, rolling updates, readiness and liveness probes, and verify the rollout after deployment. For larger applications, I prefer Helm because it provides reusable templates and environment-specific values. The pipeline builds the Docker image, pushes it to ACR, and passes the generated image tag to Helm. We use `helm upgrade --install` for deployment, `helm history` for release tracking, and `helm rollback` when we need to revert. Before deployment, I validate the chart using `helm lint` and `helm template`, and after deployment I verify the Kubernetes rollout."

---

## Q19. How do you reduce Docker build time?

To reduce Docker build time, I focus mainly on Docker layer caching, build context, dependency installation, and BuildKit.

### 1. Use Docker layer caching

Docker reuses unchanged layers. So put frequently changing files toward the end.

Bad:

```dockerfile
COPY . .
RUN npm install
```

Every source-code change can invalidate the dependency layer.

Better:

```dockerfile
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build
```

Now `npm ci` can use the cache when only application code changes.

### 2. Use `.dockerignore`

Don't send unnecessary files to the Docker daemon.

```
.git
node_modules
target
*.log
.env
README.md
```

A smaller build context means less data to transfer and process.

### 3. Use multi-stage builds

For example:

```dockerfile
FROM node:20 AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
```

This improves the final image size and avoids carrying build dependencies into production.

### 4. Use BuildKit/build cache

In Azure DevOps, I can use Docker BuildKit or buildx caching.

For example:

```bash
docker buildx build \
  --cache-from type=registry,ref=myacr.azurecr.io/myapp:buildcache \
  --cache-to type=registry,ref=myacr.azurecr.io/myapp:buildcache,mode=max \
  -t myacr.azurecr.io/myapp:$(Build.BuildId) .
```

This is especially useful with self-hosted agents where builds happen frequently.

### 5. Don't install unnecessary packages

Instead of:

```dockerfile
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2
```

Combine related operations:

```dockerfile
RUN apt-get update && \
    apt-get install -y package1 package2 && \
    rm -rf /var/lib/apt/lists/*
```

This reduces layers and unnecessary data.

### 6. Use appropriate base images

Don't automatically use huge images.

For example:

```
ubuntu
```

may be much larger than:

```
alpine
```

or a language-specific slim image:

```
python:3.12-slim
node:20-slim
```

But I wouldn't choose Alpine blindly. Some applications have compatibility issues with musl libc.

### 7. Parallelize independent pipeline work

Docker itself isn't the only source of build time.

In Azure DevOps, I can run independent activities in parallel:

```
             +--> Unit Tests
             |
Code --------+--> SonarQube
             |
             +--> Dependency Scan
```

Then build the Docker image after the required validations complete.

### Interview answer

> "To reduce Docker build time, I first optimize Docker layer caching. I copy dependency files such as package.json or pom.xml before copying the application source, so dependency installation can be reused when only source code changes. I use a proper .dockerignore to reduce the build context, multi-stage builds to separate build and runtime dependencies, and BuildKit or buildx with registry-based caching for CI pipelines. I also avoid unnecessary packages and layers and choose appropriate base images. In Azure DevOps, I combine this with pipeline caching and parallel execution of independent tests and scans. The main goal is to make sure that unchanged layers are reused instead of rebuilding everything on every commit."

---

## Q20. How do you use multiple agents in an Azure DevOps YAML pipeline?

In Azure DevOps YAML, you use multiple agents by defining multiple jobs. Each job can run on a different agent or agent pool.

The key point is:

One job runs on one agent. Multiple jobs can run on multiple agents, and independent jobs can execute in parallel.

### 1. Multiple Microsoft-hosted agents

```yaml
stages:

- stage: Build
  jobs:

  - job: Backend
    pool:
      vmImage: ubuntu-latest
    steps:
    - script: |
        echo "Building backend"
        mvn clean package

  - job: Frontend
    pool:
      vmImage: ubuntu-latest
    steps:
    - script: |
        echo "Building frontend"
        npm install
        npm run build
```

Here Azure DevOps can allocate two separate agents:

```
                 Build Stage
                     |
          +----------+----------+
          |                     |
          v                     v
     Agent 1                Agent 2
     Backend                Frontend
        |                      |
      Maven                   npm
```

These jobs can run in parallel because there is no dependency between them.

### 2. Different self-hosted agent pools

You can also have different agents for different requirements.

```yaml
jobs:

- job: Build
  pool:
    name: Linux-Agent-Pool
  steps:
  - script: ./build.sh

- job: WindowsBuild
  pool:
    name: Windows-Agent-Pool
  steps:
  - powershell: .\build.ps1
```

For example:

```
Linux Agent Pool
    |
    +--> Agent 1 --> Linux build


Windows Agent Pool
    |
    +--> Agent 2 --> Windows build
```

This is useful when a particular workload requires a specific OS or installed software.

### 3. Sequential jobs using dependencies

If the second job depends on the first:

```yaml
jobs:

- job: Build
  pool:
    vmImage: ubuntu-latest
  steps:
  - script: |
      echo "Build application"

- job: Deploy
  dependsOn: Build
  pool:
    vmImage: ubuntu-latest
  steps:
  - script: |
      echo "Deploy application"
```

Flow:

```
Agent 1
Build
  |
  | completed
  v
Agent 2
Deploy
```

Notice that Deploy can use a completely different agent.

### 4. Parallel jobs

For CI, this is a common pattern:

```yaml
jobs:

- job: UnitTests
  pool:
    vmImage: ubuntu-latest
  steps:
  - script: npm test

- job: SonarQube
  pool:
    vmImage: ubuntu-latest
  steps:
  - script: echo "Run SonarQube"

- job: SecurityScan
  pool:
    vmImage: ubuntu-latest
  steps:
  - script: echo "Run security scan"
```

```
                    Pipeline
                       |
       +---------------+---------------+
       |               |               |
       v               v               v
    Agent 1          Agent 2         Agent 3
   Unit Test        SonarQube      Security Scan
```

This reduces total pipeline execution time.

### Important interview point

Don't say "I specify three agents in one job." That's not how Azure DevOps works.

The correct explanation is:

> "Azure DevOps assigns one agent to each job. If I need multiple agents, I split the work into multiple jobs. Independent jobs can run in parallel on different agents, and I can specify different agent pools for different jobs. If there is a dependency, I use `dependsOn` to execute the jobs sequentially."
