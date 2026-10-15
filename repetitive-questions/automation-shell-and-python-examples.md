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

**Set 3 - short scripts asked in real interviews**

- [Ping a list of IPs and write a CSV report](#ping-a-list-of-ips-and-write-a-csv-report)
- [Check SSH login on all servers](#check-ssh-login-on-all-servers)
- [Health check for 500 Linux VMs - disk, memory, Nginx, CSV report](#health-check-for-500-linux-vms---disk-memory-nginx-csv-report)
- [Find missing tags in a JSON file with jq](#find-missing-tags-in-a-json-file-with-jq)
- [Check if a file exists](#check-if-a-file-exists)
- [Cron scheduling inside a VM](#cron-scheduling-inside-a-vm)
- [What is umask?](#what-is-umask)

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

**Follow-up: check every filesystem, then find what is using the space.**

```bash
#!/usr/bin/env bash
set -euo pipefail

THRESHOLD=${1:-80}

# -P keeps each filesystem on one line; skip pseudo filesystems
df -P -x tmpfs -x devtmpfs -x overlay -x efivarfs | awk -v t="$THRESHOLD" '
  NR > 1 { sub(/%/, "", $5); if ($5 + 0 >= t) printf "WARNING: %s is %s%% full\n", $6, $5 }'

# Then find the biggest directories (stay on one filesystem with -x)
du -xh --max-depth=1 /var 2>/dev/null | sort -hr | head -10
```

Flow: `df` tells you **which filesystem** is full -> `du` tells you **which directory** is using it -> check big logs, old Docker images, core dumps. If `df` says full but `du` does not add up, a deleted file is still held open by a process: `lsof +L1`.

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

```text
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

```text
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

```text
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

**Follow-up: "delete logs older than N days" - make N a parameter and add a dry run.**

```bash
#!/usr/bin/env bash
# Usage: ./cleanup_logs.sh /var/log/myapp 7 [--dry-run]
set -euo pipefail

LOG_DIR=${1:?Usage: $0 <dir> <days> [--dry-run]}
DAYS=${2:?Usage: $0 <dir> <days> [--dry-run]}
[[ -d $LOG_DIR ]] || { echo "Not a directory: $LOG_DIR" >&2; exit 2; }
[[ $DAYS =~ ^[0-9]+$ ]] || { echo "Days must be a number" >&2; exit 2; }

if [[ ${3:-} == --dry-run ]]; then
  find "$LOG_DIR" -type f -name '*.log*' -mtime +"$DAYS" -print
else
  find "$LOG_DIR" -type f -name '*.log*' -mtime +"$DAYS" -print -delete
fi
```

Remember:

- `-mtime +7` means **more than 7 full days**. `find` drops the fraction, so a file 7 days and 5 hours old is not matched; it must be 8 days old.
- Always run once without `-delete` (dry run) and validate the input path - an empty variable must never turn into `find /`.
- For a log that a running service still writes to, use `logrotate` instead. Deleting an open file does not free the space until the process closes it.

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

```text
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

# Set 3 - short scripts asked in real interviews

These are the "write a script for X" questions that came up live. Write the short version first, then mention the production details (timeouts, quoting, parallel runs).

## Ping a list of IPs and write a CSV report

**Interviewer:** Write a shell script to ping a list of IPs.

**Candidate:** I keep the IPs in a file, read them with a `while read` loop, send one ping with a timeout, and use the exit code to decide UP or DOWN.

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT=${1:-ips.txt}
OUTPUT=ping_report.csv

echo "IP,Status,Response_ms" > "$OUTPUT"

while read -r ip; do
  [[ -z $ip || $ip == \#* ]] && continue      # skip blank lines and comments

  if reply=$(ping -c 1 -W 2 "$ip" 2>/dev/null); then
    ms=$(grep -o 'time=[0-9.]*' <<< "$reply" | cut -d= -f2 || true)
    echo "$ip,UP,${ms:-N/A}" >> "$OUTPUT"
  else
    echo "$ip,DOWN,N/A" >> "$OUTPUT"
  fi
done < "$INPUT"

echo "Report: $OUTPUT"
```

Output:

```text
IP,Status,Response_ms
10.0.1.4,UP,0.84
10.0.1.5,DOWN,N/A
```

Remember:

- `-c 1` = one packet, `-W 2` = wait 2 seconds. Without a timeout, one dead host slows the whole loop.
- A failed ping does not always mean the server is down. Azure NSGs and firewalls often block ICMP. Check the real service port too: `nc -z -w 3 "$ip" 443`.
- For hundreds of IPs, run in parallel: `xargs -P 50 -I{} sh -c 'ping -c1 -W2 "$1" >/dev/null 2>&1 && echo "$1,UP" || echo "$1,DOWN"' _ {} < ips.txt`.

## Check SSH login on all servers

**Interviewer:** Write a script to check whether SSH login works on all servers.

**Candidate:** I run a harmless remote command (`true`) on each server with key-based login. `BatchMode=yes` stops it from waiting for a password, and `ConnectTimeout` stops it from hanging.

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT=${1:-servers.txt}
SSH_USER=${SSH_USER:-devops}
OUTPUT=ssh_report.csv

echo "Server,SSH_Status" > "$OUTPUT"

while read -r server; do
  [[ -z $server || $server == \#* ]] && continue

  # -n: do not let ssh read the rest of servers.txt from stdin
  if ssh -n -o BatchMode=yes -o ConnectTimeout=5 \
         -o StrictHostKeyChecking=accept-new \
         "$SSH_USER@$server" true 2>/dev/null; then
    echo "$server,LOGIN_OK" >> "$OUTPUT"
  else
    echo "$server,LOGIN_FAILED" >> "$OUTPUT"
  fi
done < "$INPUT"

echo "Report: $OUTPUT"
```

Remember:

- **The classic bug:** without `-n`, `ssh` reads the loop's stdin, eats the rest of `servers.txt`, and the loop stops after the first server.
- Use `SSH_USER`, not `USER`, so you do not overwrite the shell's own `$USER`.
- `accept-new` trusts a new host once but still rejects a **changed** key. `StrictHostKeyChecking=no` is only for a lab. In production, ship a managed `known_hosts` file.
- To tell "network down" from "key rejected", check port 22 first with `nc -z -w 3 "$server" 22`.

## Health check for 500 Linux VMs - disk, memory, Nginx, CSV report

**Interviewer:** You manage 500 Linux VMs. Write a Bash script that checks disk, memory and Nginx, writes a CSV, handles unreachable servers, and reports only the unhealthy ones.

**Candidate:** I run it from a central jump/management server with SSH keys. Two things make it work at 500 servers: **one SSH call per server** (not three), and **parallel runs** with `xargs -P`. A server that does not answer is marked `UNREACHABLE` and the script moves on.

```text
servers.txt -> xargs -P 25 -> check_server (1 SSH call, 30s max)
                                 |-- SSH fails       -> UNREACHABLE
                                 |-- disk/mem >= 80% -> UNHEALTHY
                                 |-- nginx != active -> UNHEALTHY
                                 `-- else            -> HEALTHY
           -> health_<time>.csv (all) -> unhealthy_<time>.csv (only problems)
```

```bash
#!/usr/bin/env bash
# Usage: ./fleet_health.sh servers.txt
set -euo pipefail

SERVERS_FILE=${1:?Usage: $0 servers.txt}
export DISK_MAX=${DISK_MAX:-80}
export MEM_MAX=${MEM_MAX:-80}
PARALLEL=${PARALLEL:-25}
STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="health_${STAMP}.csv"
UNHEALTHY="unhealthy_${STAMP}.csv"

# Runs on the remote server: returns 3 lines (disk %, memory %, nginx state)
REMOTE_CMD=$(cat <<'EOF'
df -P / | awk 'NR==2 {sub(/%/, "", $5); print $5}'
free | awk '/^Mem:/ {printf "%d\n", ($2 - $7) * 100 / $2}'
systemctl is-active nginx || true
EOF
)
export REMOTE_CMD

check_server() {
  local server=$1 out disk mem nginx status reasons=""

  # ConnectTimeout = host unreachable; timeout 30 = remote command hangs
  if ! out=$(timeout 30 ssh -n -o BatchMode=yes -o ConnectTimeout=5 \
                 "$server" "$REMOTE_CMD" 2>/dev/null); then
    echo "$server,UNREACHABLE,N/A,N/A,N/A,\"SSH failed or timed out\""
    return 0
  fi
  { read -r disk; read -r mem; read -r nginx; } <<< "$out"

  if [[ ! $disk =~ ^[0-9]+$ ]]; then reasons+="disk check failed; "
  elif (( disk >= DISK_MAX )); then reasons+="disk ${disk}%; "; fi

  if [[ ! $mem =~ ^[0-9]+$ ]]; then reasons+="memory check failed; "
  elif (( mem >= MEM_MAX )); then reasons+="memory ${mem}%; "; fi

  [[ $nginx == active ]] || reasons+="nginx ${nginx:-unknown}; "

  if [[ -z $reasons ]]; then status=HEALTHY; reasons=none
  else status=UNHEALTHY; reasons=${reasons%; }; fi

  echo "$server,$status,${disk:-N/A},${mem:-N/A},${nginx:-N/A},\"$reasons\""
}
export -f check_server

echo "Server,Status,Disk_%,Memory_%,Nginx,Reason" > "$REPORT"

# Skip blank lines and comments, check 25 servers at a time
grep -Ev '^[[:space:]]*(#|$)' "$SERVERS_FILE" \
  | xargs -P "$PARALLEL" -I{} bash -c 'check_server "$1"' _ {} \
  | sort >> "$REPORT"

# Header + every row that is not HEALTHY
awk -F, 'NR == 1 || $2 != "HEALTHY"' "$REPORT" > "$UNHEALTHY"

count=$(( $(wc -l < "$UNHEALTHY") - 1 ))
echo "Full report: $REPORT"
echo "Unhealthy:   $UNHEALTHY ($count servers)"
(( count == 0 )) || exit 1      # non-zero exit so cron/pipeline can alert
```

Unhealthy report:

```text
Server,Status,Disk_%,Memory_%,Nginx,Reason
web-017,UNHEALTHY,91,52,active,"disk 91%"
web-142,UNHEALTHY,45,88,inactive,"memory 88%; nginx inactive"
web-311,UNREACHABLE,N/A,N/A,N/A,"SSH failed or timed out"
```

Remember:

- **Memory:** use `total - available`, not the `used` column. Linux uses free RAM for cache, and `available` counts what can be reclaimed.
- **Sequential is too slow:** 500 servers x 5-second timeout can take over 40 minutes. With `-P 25` it is a couple of minutes.
- `systemctl is-active` prints `active`, `inactive` or `failed` and exits non-zero when not active, so `|| true` keeps the output without failing the remote command.
- The non-zero exit lets cron, an Azure DevOps scheduled pipeline or a monitoring job raise an alert, and the CSV can be emailed or uploaded to Blob Storage.
- **At real scale I would not grow this script forever.** For 500 VMs, Azure Monitor Agent + a log alert on `Heartbeat` (unreachable), disk and memory metrics is the permanent answer, and Ansible (`forks`) is better for running checks or fixes across the fleet. The script is good for a quick audit.

## Find missing tags in a JSON file with jq

**Interviewer:** You have a JSON file of resources. Find which ones are missing required tags.

**Candidate:** I pass the required keys into `jq` as an array and, for each object, keep the keys that are missing or empty.

```json
[
  { "name": "server1", "environment": "prod", "owner": "devops" },
  { "name": "server2", "environment": "prod" },
  { "name": "server3", "owner": "devops" }
]
```

```bash
jq -r --argjson req '["name","environment","owner"]' '
  .[] as $o
  | [ $req[] | select($o[.] == null or $o[.] == "") ] as $missing
  | select($missing | length > 0)
  | "\($o.name // "unknown"): missing \($missing | join(", "))"
' servers.json
```

```text
server2: missing owner
server3: missing environment
```

The same idea on real Azure resources (`tags` can be `null`, so default it to `{}`):

```bash
az resource list --query "[].{name:name, tags:tags}" -o json \
  | jq -r --argjson req '["Environment","Owner","CostCenter"]' '
      .[]
      | (.tags // {}) as $t
      | [ $req[] | select($t[.] == null) ] as $missing
      | select($missing | length > 0)
      | [.name, ($missing | join(";"))] | @csv' > missing-tags.csv
```

Remember:

- Save the object first (`.[] as $o`). Inside `$req[] | select(...)`, the `.` is the **tag name**, not the object - the most common mistake here.
- `has("owner")` is true even when the value is `null`. Checking `== null` catches both "key missing" and "key is null".
- jq is case-sensitive, but Azure tag **names** are not, so `environment` and `Environment` count as the same tag in Azure. Normalise with `ascii_downcase` if teams are inconsistent.
- The script **finds** missing tags. To **prevent** them, use Azure Policy ("Require a tag on resources" with Deny, or "Inherit a tag from the resource group" with Modify).

## Check if a file exists

**Interviewer:** Write a script to check if `/etc/config.js` exists.

```bash
#!/usr/bin/env bash
set -euo pipefail

FILE=${1:-/etc/config.js}

if [[ -f $FILE ]]; then
  echo "$FILE exists"
else
  echo "$FILE not found" >&2
  exit 1
fi
```

| Test | True when |
|---|---|
| `-e` | Path exists (file, directory, anything) |
| `-f` | It is a regular file |
| `-d` | It is a directory |
| `-s` | File exists and is not empty |
| `-r` / `-w` / `-x` | Current user can read / write / execute it |

Remember: return a non-zero exit code when the file is missing, so a pipeline step or the next script stops. A config file that exists but is empty usually needs `-s`, not just `-f`.

## Cron scheduling inside a VM

**Interviewer:** Can we use cron in a VM?

**Candidate:** Yes. Inside a Linux Azure VM, cron works the same as on any Linux server. I use it for OS-level jobs such as log cleanup, backups and health scripts.

```bash
crontab -e       # edit the current user's jobs
crontab -l       # list them
```

```text
# min hour day-of-month month day-of-week  command
0 20 * * *   /opt/scripts/cleanup_logs.sh /var/log/myapp 7 >> /var/log/cleanup.log 2>&1
*/10 * * * * /usr/bin/flock -n /tmp/health.lock /opt/scripts/health.sh >> /var/log/health.log 2>&1
```

Remember:

- Cron has a **minimal environment** - use full paths, set `PATH` at the top of the crontab, and redirect output to a log file. "Works by hand, fails in cron" is almost always this.
- `flock -n` stops a second run from starting if the previous one is still running.
- Cron times use the VM's timezone (Azure VMs default to UTC).
- `shutdown -h now` from cron stops the OS, but the VM shows **Stopped**, not **Stopped (deallocated)**, so compute is still billed. To save cost, use VM Auto-shutdown, Azure Automation or the Start/Stop VMs v2 solution - or call `az vm deallocate` after `az login --identity` using the VM's managed identity with a narrowly scoped role.
- `systemd` timers are the modern alternative: logs go to `journalctl` and missed runs can be caught up (`Persistent=true`). On Windows, the equivalent is Task Scheduler.

## What is umask?

**Candidate:** `umask` is the mask that **removes** permissions from newly created files and directories. Files start from `666`, directories from `777`, and the umask bits are taken away.

```text
umask 022 -> files 644 (rw-r--r--)   dirs 755 (rwxr-xr-x)   default on most systems
umask 027 -> files 640 (rw-r-----)   dirs 750 (rwxr-x---)   group can read, others nothing
umask 077 -> files 600 (rw-------)   dirs 700 (rwx------)   private, good for backups and keys
```

```bash
umask          # show current value, e.g. 0022
umask 077      # only for this shell or script
```

Remember:

- It is a bit mask, not subtraction. With `umask 033`, a new file is `644`, not `633`, because files never get execute bits by default.
- It only affects **new** files. Use `chmod` to change existing ones.
- In scripts that write backups or secrets, put `umask 077` at the top (as in the backup script below) so nothing is readable by other users, even for a moment.
- Persistent value: `~/.bashrc` for one user, `/etc/login.defs` or `/etc/profile` system-wide; for a systemd service, `UMask=` in the unit file.

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

Source: [others/coding-challenges/interview-round-notes.md](../others/coding-challenges/interview-round-notes.md)

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

Source: [shell-scripting/02-automation-scripts-in-practice.md](../shell-scripting/02-automation-scripts-in-practice.md)

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

Source: [shell-scripting/02-automation-scripts-in-practice.md](../shell-scripting/02-automation-scripts-in-practice.md)

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

Source: [shell-scripting/02-automation-scripts-in-practice.md](../shell-scripting/02-automation-scripts-in-practice.md)

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

Source: [shell-scripting/01-bash-fundamentals-and-error-handling.md](../shell-scripting/01-bash-fundamentals-and-error-handling.md)

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

Source: [shell-scripting/02-automation-scripts-in-practice.md](../shell-scripting/02-automation-scripts-in-practice.md)

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

Source: [shell-scripting/01-bash-fundamentals-and-error-handling.md](../shell-scripting/01-bash-fundamentals-and-error-handling.md)

```bash
bash -n deploy.sh             # syntax
shellcheck deploy.sh          # common errors
bash -x deploy.sh --dry-run   # trace; avoid when secrets may print
```

Check the shebang, executable bit, PATH, working directory, user, environment variables, permissions, exit codes, quoting, pipelines, network/DNS, and dependency versions. Scheduled jobs often fail because cron has a minimal environment.

## PowerShell

### Azure cost optimization - find unattached managed disks

Source: [shell-scripting/02-automation-scripts-in-practice.md](../shell-scripting/02-automation-scripts-in-practice.md)

Reports rather than deletes, so an owner can review first.

```powershell
$disks = Get-AzDisk | Where-Object { $_.ManagedBy -eq $null }
$disks | Select-Object Name, ResourceGroupName, DiskSizeGB, TimeCreated |
    Export-Csv ./unattached-disks.csv -NoTypeInformation
```

The process is report -> owner validation -> approval -> deletion after retention. Other automations stop non-production VMs after business hours, find idle public IPs and snapshots, enforce tags, right-size from metrics, and create budget alerts.

## Python

### Call a REST API safely

Source: [python/03-automation-apis-and-data.md](../python/03-automation-apis-and-data.md)

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

Source: [python/03-automation-apis-and-data.md](../python/03-automation-apis-and-data.md)

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

Source: [python/03-automation-apis-and-data.md](../python/03-automation-apis-and-data.md)

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

Source: [others/coding-challenges/interview-round-notes.md](../others/coding-challenges/interview-round-notes.md)

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

Source: [python/03-automation-apis-and-data.md](../python/03-automation-apis-and-data.md)

- `argparse` or typed configuration with validation
- Structured logs with correlation IDs and no secrets
- Specific exception handling, timeouts, limited retries, and exit codes
- Idempotency or a safe resume strategy
- Unit and integration tests, linting, typing, and security scans
- Pinned dependencies and reproducible packaging
- Least-privilege identity and external secrets
- Metrics/alerts and a documented runbook

### Scheduling Python automation

Source: [python/03-automation-apis-and-data.md](../python/03-automation-apis-and-data.md)

Options: cron / systemd timers, GitHub Actions or Azure Pipelines schedules, Kubernetes CronJobs, Azure Functions timers, and workflow orchestrators.

For a Kubernetes CronJob, set concurrency policy, deadlines, history limits, resource requests, and failure alerts. For any scheduler, the script must be idempotent and use a distributed lock if overlapping runs would be unsafe. Secrets come from workload identity or a secret manager, not the schedule definition.
