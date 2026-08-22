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
