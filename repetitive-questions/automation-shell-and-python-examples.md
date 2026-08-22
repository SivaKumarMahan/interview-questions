# Automation Examples - Shell and Python

For an Azure DevOps / DevOps interview, use examples that sound like real operational automation rather than generic programming exercises.

## Contents

**Set 1 - pipeline and cloud focused**

- [5 Shell scripting automation examples](#5-shell-scripting-automation-examples)
- [5 Python automation examples](#5-python-automation-examples)
- [How to answer in the interview](#how-to-answer-in-the-interview)
- [The important distinction](#the-important-distinction)

**Set 2 - server operations focused**

- [5 more Shell scripting automation examples](#5-more-shell-scripting-automation-examples)
- [5 more Python automation examples](#5-more-python-automation-examples)
- [Which examples should you tell the interviewer?](#which-examples-should-you-tell-the-interviewer)
- [Best 30-second answer](#best-30-second-answer)

**Collected from elsewhere in this repo**

- [More automation scripts from other notes in this repo](#more-automation-scripts-from-other-notes-in-this-repo)

---

## 5 Shell scripting automation examples

### 1. Kubernetes deployment health check

Used after deployment to verify that pods are running and rollout completed.

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

Useful on self-hosted agents where old Docker images consume disk space.

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

---

## 5 Python automation examples

Python is more useful when the automation involves API calls, JSON processing, complex logic, or larger workflows.

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

Python can provide more control than a simple `docker prune`.

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

---

## How to answer in the interview

If they ask:

> "What automation have you done using Shell and Python?"

Give this answer:

> "I have used shell scripting mainly for lightweight Linux, Kubernetes and CI/CD automation. Five examples are Kubernetes deployment health checks, Docker cleanup on self-hosted agents, Linux disk-space monitoring, application log backup and Azure resource inventory using Azure CLI.
>
> I use Python when the automation requires more complex logic or data processing. For example, I have used Python for Azure resource processing, Kubernetes pod health checks, Docker image cleanup based on retention rules, application log analysis, and API health checks.
>
> I generally use Bash for simple command orchestration and pipeline tasks, while I prefer Python when I need JSON processing, API integration, error handling, or more complex business logic."

---

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

# Set 2 - server operations focused

Another set of ten examples. These lean more towards Linux server operations - service restarts, log monitoring, email alerts and retention - while Set 1 above leans towards Kubernetes, Docker and Azure. Both sets are good answers; pick whichever matches the job description.

## 5 more Shell scripting automation examples

### 1. Automatically restart a failed service

**Problem:** the application service occasionally stops. Someone had to SSH into the server, check it and restart it.

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
Service down?
     |
Restart
     |
Still down?
     |
Send alert
```

**Interview:**

> "I automated service health checking. If the service was down, the script automatically restarted it and returned a failure if the restart didn't succeed."

### 2. Check application logs for errors and send email

**Problem:** the DevOps team had to manually search logs for ERROR and Exception.

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

Schedule it with cron:

```
*/10 * * * * /opt/scripts/check_logs.sh
```

**Interview:**

> "I automated log monitoring using grep and cron. If the script found application errors, it collected the recent errors and sent an email to the support team."

### 3. Automated server backup

**Problem:** manual backup of configuration files and application data.

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

**Interview:**

> "I automated daily configuration backups using tar and cron. The backup file had a timestamp, and the script returned a failure if the backup operation failed."

### 4. Disk-space monitoring and alert

**Problem:** servers were running out of disk space because of logs and temporary files.

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

**Interview:**

> "I created a shell script that checks disk utilization periodically. If usage crossed 80%, it automatically sent an email alert so we could take action before the server became unavailable."

### 5. Automated log cleanup

**Problem:** application logs were filling the server.

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

**Interview:**

> "I automated log retention using the Linux find command. Logs older than seven days were removed based on our retention requirement. This prevented unnecessary disk consumption."

## 5 more Python automation examples

Python examples should show where Python is better than a simple Bash command - especially API calls, JSON processing, structured reporting and exception handling.

### 1. Restart service and send email if restart fails

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

**Interview:**

> "I used Python to monitor a Linux service. If it was down, the script attempted a restart. If the restart failed, it automatically sent an email notification."

### 2. Parse logs and generate an error report

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

**Interview:**

> "I used Python to parse application logs, identify different error patterns using regular expressions, generate a report and send it to the support team."

### 3. Automated backup with retention

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

**Interview:**

> "I used Python to automate backups and retention. It created timestamped compressed backups and automatically removed backups older than the retention period."

### 4. Monitor multiple servers and send one email report

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

**Interview:**

> "Instead of checking servers individually, I used Python to connect to multiple servers, check the application service status, generate a consolidated report and notify the team if any server was unhealthy."

### 5. API health monitoring

Python is very useful for automating application / API checks.

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

**Interview:**

> "I used Python to monitor multiple application APIs. The script checked HTTP status codes and connection failures and generated an alert when an API was unavailable. This was useful as a post-deployment health check."

## Which examples should you tell the interviewer?

These ten examples sound realistic for a DevOps role:

| Shell | Python |
|---|---|
| Restart failed service | Restart service + email alert |
| Search logs for errors | Parse logs + generate report |
| Automated server backup | Backup + retention |
| Disk-space monitoring | Monitor multiple servers |
| Log cleanup | API health monitoring |

## Best 30-second answer

> "Yes, I have automated several repetitive operational tasks using Shell and Python. In Shell, I automated service restart, application log error checking with email alerts, server backups, disk-space monitoring and log cleanup using cron. In Python, I used scripts for more complex automation such as service monitoring with email notifications, parsing application logs and generating reports, backup and retention management, checking multiple servers, and API health monitoring. These scripts reduced manual intervention and could be integrated with our Azure DevOps pipelines or scheduled through cron."

---

# More automation scripts from other notes in this repo

These are the shell and Python automation scripts already written in other folders, collected here so everything is in one place. The source file is linked with each one.

## Shell

### Service check and fix

Source: [cheatcodes/shell-scripting/scripts.md](../cheatcodes/shell-scripting/scripts.md)

Checks whether a service is running and starts it if not. On failure it prints the last 50 journal lines so the reason is captured.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

service_name=${1:-nginx}
if systemctl is-active --quiet "$service_name"; then
  printf '%s is running\n' "$service_name"
  exit 0
fi

systemctl start "$service_name"
systemctl is-active --quiet "$service_name" || {
  journalctl -u "$service_name" -n 50 --no-pager >&2 || true
  exit 1
}
```

### Disk threshold check (safer version)

Source: [cheatcodes/shell-scripting/scripts.md](../cheatcodes/shell-scripting/scripts.md)

Same idea as shell example 3 above, but uses `df -P` so the output format is portable, and the threshold comes from an environment variable.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

threshold=${THRESHOLD_PERCENT:-80}
usage=$(df -P / | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
if (( usage >= threshold )); then
  printf 'CRITICAL: root filesystem is %s%% used\n' "$usage" >&2
  exit 2
fi
printf 'OK: root filesystem is %s%% used\n' "$usage"
```

### Backup skeleton with checksum and verification

Source: [cheatcodes/shell-scripting/scripts.md](../cheatcodes/shell-scripting/scripts.md)

Better than the simple `tar -czf` example above because it uses a UTC timestamp, writes a SHA256 checksum, and verifies the archive can be listed.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

source_dir=${SOURCE_DIR:?Set SOURCE_DIR}
backup_dir=${BACKUP_DIR:?Set BACKUP_DIR}
mkdir -p -- "$backup_dir"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$backup_dir/backup-$stamp.tar.gz"
tar -C "$(dirname "$source_dir")" -czf "$archive" "$(basename "$source_dir")"
sha256sum "$archive" > "$archive.sha256"
tar -tzf "$archive" >/dev/null
```

A production backup additionally needs encryption, a remote failure-domain copy, retention, monitoring, and restore testing. A command returning zero is **not** proof that the data is recoverable.

### Log rotation and cleanup with Slack notification

Source: [Others/coding-challenges/interview-round-notes.md](../Others/coding-challenges/interview-round-notes.md)

Compresses logs older than a day, deletes archives past retention, cleans `/tmp`, and notifies Slack on both success and failure using a `trap`.

```bash
#!/usr/bin/env bash
set -euo pipefail                      # fail fast, catch undefined vars, pipe failures
LOG_DIR="/var/log/myapp"; RETENTION_DAYS=14; SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

notify() { [[ -n "$SLACK_WEBHOOK" ]] && curl -sf -X POST -d "{\"text\":\"$1\"}" "$SLACK_WEBHOOK" || true; }
trap 'notify "log-cleanup failed at line $LINENO"' ERR

# rotate + compress logs older than 1 day
find "$LOG_DIR" -type f -name '*.log' -mtime +1 -exec gzip {} \;
# delete archives older than retention
deleted=$(find "$LOG_DIR" -type f -name '*.gz' -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
# clean tmp + old cache
find /tmp -type f -atime +7 -delete
notify "log-cleanup done: removed $deleted old archives, disk now $(df -h / | awk 'NR==2{print $5}')"
```

Talking points: `set -euo pipefail`, `trap ... ERR` for error handling, idempotency, using `logrotate` in real setups, and scheduling via cron or a systemd timer.

### Download the latest backup from a remote server over SSH

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

Finds the newest backup remotely, copies it to a temporary name, verifies the checksum, then atomically renames it. It does not assume the newest file is complete just because it exists.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

remote="backup@10.0.0.10"
remote_dir="/backups"
local_dir="/restore"
mkdir -p "$local_dir"

latest=$(ssh -o BatchMode=yes "$remote" \
  "find '$remote_dir' -maxdepth 1 -type f -name '*.tar.gz' -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2-")

[[ -n "$latest" ]] || { echo "No backup found" >&2; exit 1; }

name=$(basename "$latest")
tmp="$local_dir/.${name}.partial"
rsync --partial --progress "$remote:$latest" "$tmp"
ssh "$remote" "sha256sum '$latest'" | sed "s|$latest|$tmp|" | sha256sum --check -
mv "$tmp" "$local_dir/$name"
echo "Downloaded and verified: $local_dir/$name"
```

### Start Nginx only if it is not already running

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

```bash
#!/usr/bin/env bash
set -euo pipefail

if systemctl is-active --quiet nginx; then
  echo 'Nginx is already running'
  exit 0
fi

echo 'Nginx is not running; attempting startup'
sudo systemctl start nginx

if systemctl is-active --quiet nginx; then
  echo 'Nginx started successfully'
else
  echo 'Nginx failed to start' >&2
  sudo systemctl status nginx --no-pager >&2 || true
  sudo journalctl -u nginx -n 50 --no-pager >&2 || true
  exit 1
fi
```

### Find the biggest file in a folder

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

```bash
#!/usr/bin/env bash
set -euo pipefail

dir=${1:-.}
[[ -d $dir ]] || { echo "Not a directory: $dir" >&2; exit 2; }

result=$(find "$dir" -type f -printf '%s\t%p\n' 2>/dev/null | sort -nr | head -n1)
[[ -n $result ]] || { echo "No readable files found" >&2; exit 1; }

size=${result%%$'\t'*}
path=${result#*$'\t'}
printf 'Largest file: %q (%s bytes)\n' "$path" "$size"
```

Do not delete the result automatically - first check whether it is an active log, open file, database file, or protected backup.

### Capture an exit code correctly

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

`$?` must be captured immediately, because running `echo` or `cd` replaces it.

```bash
curl --fail --silent https://service.example/health
status=$?
if (( status != 0 )); then
  printf 'Health check failed with exit code %d\n' "$status" >&2
fi
```

For pipelines, enable `set -o pipefail`; otherwise `$?` reflects only the final command.

### A "complex automation script" answer

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

If asked for an example of a complex script you have written, describe a deployment script that:

1. Parses the environment and version; rejects unknown values.
2. Acquires a lock to prevent concurrent deployment.
3. Confirms artifact signature/checksum and available disk space.
4. Captures the current version for rollback.
5. Drains or removes the instance from traffic.
6. Deploys and restarts with a timeout.
7. Tests health and a real dependency call.
8. Restores the old version if checks fail.
9. Returns traffic, releases the lock, emits metrics, and notifies the team.

Mention `set -Eeuo pipefail`, a cleanup trap, structured logs, quoted variables, explicit exit codes, and a dry-run mode. A good story to add: a health endpoint passed while database authentication failed, so a dependency smoke test was added.

### Debugging automation scripts

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

```bash
bash -n deploy.sh             # syntax
shellcheck deploy.sh          # common errors
bash -x deploy.sh --dry-run   # trace; avoid when secrets may print
```

Check the shebang, executable bit, PATH, working directory, user, environment variables, permissions, exit codes, quoting, pipelines, network/DNS, and dependency versions. Scheduled jobs often fail because cron has a minimal environment.

## PowerShell

### Azure cost optimization - find unattached managed disks

Source: [shell-scripting/questions.md](../shell-scripting/questions.md)

Reports rather than deletes, so an owner can review first.

```powershell
$disks = Get-AzDisk | Where-Object { $_.ManagedBy -eq $null }
$disks | Select-Object Name, ResourceGroupName, DiskSizeGB, TimeCreated |
    Export-Csv ./unattached-disks.csv -NoTypeInformation
```

The process is report -> owner validation -> approval -> deletion after retention. Other automations stop non-production VMs after business hours, find idle public IPs and snapshots, enforce tags, right-size from metrics, and create budget alerts.

## Python

### Call a REST API safely

Source: [python/questions.md](../python/questions.md)

Sets a timeout, checks the status code, and handles each failure type separately.

```python
import requests

url = "https://api.example.com/v1/health"
try:
    response = requests.get(url, timeout=(3, 10))
    response.raise_for_status()
    payload = response.json()
    print(payload["status"])
except requests.Timeout:
    raise SystemExit("API request timed out")
except requests.HTTPError as exc:
    raise SystemExit(f"API returned {exc.response.status_code}")
except (requests.ConnectionError, ValueError) as exc:
    raise SystemExit(f"API request failed: {exc}")
```

### Run shell commands from Python

Source: [python/questions.md](../python/questions.md)

Use an argument list with `check=True` and a timeout. Avoid `shell=True` for user-controlled input because it allows command injection.

```python
import subprocess

result = subprocess.run(
    ["kubectl", "get", "pods", "-n", "payments", "-o", "json"],
    check=True,
    capture_output=True,
    text=True,
    timeout=30,
)
```

Handle `CalledProcessError` and `TimeoutExpired`, and redact sensitive arguments.

### Process a large log file without loading it into memory

Source: [python/questions.md](../python/questions.md)

Streams line by line and counts HTTP status codes.

```python
from collections import Counter

counts = Counter()
with open("access.log", encoding="utf-8", errors="replace") as handle:
    for line_number, line in enumerate(handle, start=1):
        parts = line.split()
        if len(parts) < 9:
            continue
        counts[parts[8]] += 1

print(counts.most_common())
```

### Parse and chart AWS CloudWatch metrics

Source: [Others/coding-challenges/interview-round-notes.md](../Others/coding-challenges/interview-round-notes.md)

Pulls 24 hours of EC2 CPU data and saves a graph.

```python
import boto3, datetime as dt
import matplotlib.pyplot as plt

cw = boto3.client("cloudwatch")
resp = cw.get_metric_statistics(
    Namespace="AWS/EC2", MetricName="CPUUtilization",
    Dimensions=[{"Name": "InstanceId", "Value": "i-0abc123"}],
    StartTime=dt.datetime.utcnow() - dt.timedelta(hours=24),
    EndTime=dt.datetime.utcnow(),
    Period=300, Statistics=["Average", "Maximum"],
)
points = sorted(resp["Datapoints"], key=lambda d: d["Timestamp"])
times = [p["Timestamp"] for p in points]
avg   = [p["Average"] for p in points]

plt.plot(times, avg, label="Avg CPU %")
plt.xlabel("Time"); plt.ylabel("CPU %"); plt.legend(); plt.title("EC2 CPU (24h)")
plt.tight_layout(); plt.savefig("cpu.png")
```

Talking points: boto3 credentials via IAM role or OIDC, pagination for large ranges, pandas for rolling averages and anomaly detection, and error handling.

### Making a Python automation script production-ready

Source: [python/questions.md](../python/questions.md)

- `argparse` or typed configuration with validation
- Structured logs with correlation IDs and no secrets
- Specific exception handling, timeouts, limited retries, and exit codes
- Idempotency or a safe resume strategy
- Unit and integration tests, linting, typing, and security scans
- Pinned dependencies and reproducible packaging
- Least-privilege identity and external secrets
- Metrics/alerts and a documented runbook

### Scheduling Python automation

Source: [python/questions.md](../python/questions.md)

Options: cron / systemd timers, GitHub Actions or Azure Pipelines schedules, Kubernetes CronJobs, Azure Functions timers, and workflow orchestrators.

For a Kubernetes CronJob, set concurrency policy, deadlines, history limits, resource requests, and failure alerts. For any scheduler, the script must be idempotent and use a distributed lock if overlapping runs would be unsafe. Secrets come from workload identity or a secret manager, not the schedule definition.
