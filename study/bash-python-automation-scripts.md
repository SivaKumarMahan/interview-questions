# Bash and Python Automation Scripts

Short, practical scripts that come up in "write a script that..." interview questions - Kubernetes rollout checks, Docker cleanup, disk monitoring, log backups, and the Python equivalents built on `subprocess`.

## Contents

1. [Kubernetes deployment rollout status check](#1-kubernetes-deployment-rollout-status-check)
2. [Docker disk cleanup script](#2-docker-disk-cleanup-script)
3. [Linux disk usage monitoring script](#3-linux-disk-usage-monitoring-script)
4. [Log backup script](#4-log-backup-script)
5. [Python: Kubernetes pod health check](#5-python-kubernetes-pod-health-check)
6. [Python: Docker image age script](#6-python-docker-image-age-script)

---

## 1. Kubernetes deployment rollout status check

Waits for a rollout to finish and, if it doesn't, dumps enough context (pods + recent events) to start troubleshooting immediately instead of just failing silently.

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

`kubectl rollout status --timeout=180s` blocks until the rollout completes or the timeout is hit. `$?` captures its exit code - non-zero means the rollout didn't finish cleanly, so the script pulls the current pod list and the 20 most recent namespace events (sorted by timestamp) before exiting non-zero itself, so a calling CI/CD pipeline stage also fails.

---

## 2. Docker disk cleanup script

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

- `docker system df` - shows current disk usage broken down by images, containers, volumes, and build cache, so you have a before/after picture.
- `docker image prune -af` - removes **all** images not referenced by any container (`-a`), without a confirmation prompt (`-f`). Useful on build agents where old, unused image layers accumulate.
- `docker container prune -f` - removes stopped containers.

This is a build-agent housekeeping script, not something to run against a host with images you might still need - `-a` is aggressive.

---

## 3. Linux disk usage monitoring script

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

`USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')` gets the disk usage of the root filesystem: `df /` prints the filesystem table, `awk 'NR==2 {print $5}'` grabs the `Use%` column from the second line (the data row), and `sed 's/%//'` strips the `%` sign so the value can be compared numerically. A non-zero exit code on breach makes this usable directly as a monitoring/cron check.

---

## 4. Log backup script

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

`mkdir -p` ensures the backup directory exists without erroring if it already does. `tar -czf` creates a gzip-compressed archive (`c` = create, `z` = gzip, `f` = file) named with the current date, so re-running the script on a different day produces a separate, non-overwriting backup file.

---

## 5. Python: Kubernetes pod health check

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

With `namespace = "production"`, the `subprocess.run()` call is equivalent to running:

```bash
kubectl get pods -n production -o json
```

**How `subprocess.run()` is being used here:**

- The list `["kubectl", "get", "pods", "-n", namespace, "-o", "json"]` is the command and its arguments - no shell string parsing involved, which avoids shell-injection issues.
- `capture_output=True` captures stdout and stderr instead of letting them print directly to the terminal.
- `text=True` returns `result.stdout`/`result.stderr` as strings instead of bytes.
- `result.returncode` holds the exit status of the command - `0` usually means success, non-zero means failure (e.g. `if result.returncode != 0: print(result.stderr)`).

The overall flow:

```
Python script
     |
     v
subprocess.run()
     |
     v
kubectl get pods
     |
     v
Kubernetes API
     |
     v
JSON output (result.stdout)
     |
     v
json.loads()
     |
     v
Python dictionary
     |
     v
Iterate pod["status"]["phase"] and flag anything != "Running"
```

This is a common pattern for wrapping `kubectl` (or any CLI tool) in Python when you need to process structured output rather than just eyeballing text - `-o json` plus `json.loads()` turns an opaque CLI into something you can iterate over programmatically.

---

## 6. Python: Docker image age script

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

`docker images --format "{{.ID}} {{.CreatedAt}}"` lists every local image as `<image-id> <created-timestamp>`, using Docker's Go-template formatting to strip out everything except the two fields needed. `cutoff = datetime.now() - timedelta(days=7)` computes "7 days ago" as a comparison point.

As written, the script only prints the raw `ID CreatedAt` lines - to actually act on image age you'd parse each line's timestamp (Docker's `CreatedAt` format needs explicit parsing, e.g. with `datetime.strptime`) and compare it against `cutoff`, then collect the IDs older than the cutoff to remove with `docker rmi`. This is the same overall shape as the pod-health-check script: shell out with `subprocess.run()`, capture structured-ish text output, then parse and filter it in Python.
