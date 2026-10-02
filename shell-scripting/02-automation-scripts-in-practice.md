# Shell Scripting: Automation Scripts in Practice

> Real DevOps scripts: monitoring and cleanup, backups and rotation, remote downloads over SSH, service checks, user provisioning, and PowerShell in CI/CD and cost work.

## Key Concepts

### Monitoring and Cleanup

| Task | What matters |
|---|---|
| Disk monitoring | Watch the right filesystem, and put useful detail in the alert. |
| Log cleanup | Check the directory, retention period, and ownership. Use `logrotate` or `journald` policy instead of deleting files by hand. |
| Fixing a service | Check its config, verify it's healthy after start/reload, keep the logs, limit retries, and alert instead of looping forever. |

### Disk usage monitoring (multi-mount)

Checks every mounted filesystem in one pass, rather than a single hardcoded mount point:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

THRESHOLD=80

df -h | awk 'NR>1 {print $5 " " $6}' | while read -r usage mount
do
    usage=${usage%\%}

    if (( usage >= THRESHOLD )); then
        echo "WARNING: $mount is ${usage}% full"
    fi
done
```

- `df -h` gets filesystem usage in human-readable format.
- `awk 'NR>1 {print $5 " " $6}'` skips the header row and extracts the `Use%` and mount-point columns.
- `while read -r usage mount` assigns those two fields per line.
- `usage=${usage%\%}` strips the trailing `%` sign via parameter expansion.
- `(( usage >= THRESHOLD ))` does the numeric comparison.

Example output:

```
WARNING: /data is 87% full
WARNING: /backup is 92% full
```

**Production improvements:** log warnings, send email/Slack notifications, ignore temporary filesystems if appropriate (`tmpfs`, etc.), use a lock so overlapping cron runs don't double-alert, and schedule with cron or a systemd timer.

### Log cleanup

```bash
find /var/log/myapp -type f -name "*.log" -mtime +30 -delete
```

- `find` - search.
- `/var/log/myapp` - starting directory.
- `-type f` - regular files only.
- `-name "*.log"` - only `.log` files.
- `-mtime +30` - modified more than 30 days ago.
- `-delete` - delete matches.

**Always dry-run destructive `find` commands first:**

```bash
find /var/log/myapp -type f -name "*.log" -mtime +30 -print
```

Review the output before adding `-delete` to the same command.

**`mtime`/`atime`/`ctime`:**

- `mtime` - file *content* modification time.
- `atime` - last access time.
- `ctime` - metadata/status change time (permissions, ownership, etc. - not content).

### Service health check and restart

```bash
SERVICE=nginx

if ! systemctl is-active --quiet "$SERVICE"; then
    echo "Restarting $SERVICE..."
    systemctl restart "$SERVICE"

    if systemctl is-active --quiet "$SERVICE"; then
        echo "Restart successful"
    else
        echo "Restart failed"
        exit 1
    fi
fi
```

`systemctl is-active --quiet` returns success (exit `0`) when the service is active, non-zero otherwise. `!` negates that, so the block only runs when the service is *not* active. The second `is-active` check after `restart` verifies the restart actually worked - restarting doesn't guarantee the service came back up healthy.

**Production improvements:** log restart attempts, send alerts on failure, limit retry count (don't restart-loop forever against a service that keeps crashing), check `journalctl -u "$SERVICE" -n 50` for failure details, and schedule with cron/a systemd timer.

### Email alerting

```bash
mail -s "Disk Usage Alert" admin@example.com < report.txt
```

- `mail` - send email.
- `-s` - subject.
- `admin@example.com` - recipient.
- `< report.txt` - use `report.txt` as the email body.

This requires the host to have a configured MTA such as Postfix, Sendmail, or Exim - `mail` doesn't send anything on its own without one. In cloud environments, Slack, Teams, PagerDuty, or Azure Monitor Action Groups are often preferred over configuring an MTA on every host.

### Backups

A backup script should:

- Create its destination safely
- Preserve permissions where that matters
- Never back up its own output into itself
- Write to a temporary name and rename it into place once complete
- Checksum or encrypt the backup, per policy
- Enforce a retention period
- Copy the backup somewhere that won't fail along with the original
- Get restored occasionally to prove it actually works

A command returning exit code zero is not proof that the data can be recovered.

### Safe Bash Backup Rotation Example

This example dumps a PostgreSQL database from a container, checks the output isn't empty, and removes backups older than seven days. In production, credentials should come from a protected runtime source, and backups should also be encrypted, copied to separate storage, monitored, and tested by actually restoring them.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

readonly db_container="db-container"
readonly backup_dir="/backups"
readonly timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
readonly backup_file="${backup_dir}/database-${timestamp}.sql"

mkdir -p -- "$backup_dir"

docker exec "$db_container" \
  pg_dump --username=postgres --dbname=mydb >"$backup_file"

if [[ ! -s "$backup_file" ]]; then
  echo "Backup is empty: $backup_file" >&2
  exit 1
fi

find "$backup_dir" -maxdepth 1 -type f \
  -name 'database-*.sql' -mtime +7 -print -delete

echo "Backup completed: $backup_file"
```

I'd also generate a checksum, upload the backup to storage that can't be changed after it's written, alert if the backup fails or never runs, and regularly restore it into a separate test database. Deleting by age like this is clearer and safer than trying to parse `ls` output.

### Backup verification

```bash
BACKUP="/backup/db.tar.gz"

if [[ -f "$BACKUP" && -s "$BACKUP" ]]; then
    echo "Backup verified"
else
    echo "Backup failed"
    exit 1
fi
```

- `-f` checks that the path exists and is a regular file.
- `-s` checks that the file size is greater than zero.
- `&&` requires both conditions.
- `exit 1` reports failure to whatever automation is calling this script.

**Production improvements:**

```bash
tar -tzf "$BACKUP" >/dev/null
```

validates that the archive is actually a well-formed `tar.gz` (not just a non-empty file - a truncated or corrupted archive would still pass the basic `-f`/`-s` check but fail this). `sha256sum` can be used for checksum verification against a known-good hash. Also check backup *age* with `find` (a backup job that silently stopped running would still leave a valid-looking old file behind), and log results with alerting on failure.

### User Provisioning

User provisioning scripts should never hardcode or print passwords, and should never hand out broad `sudo` access automatically. Use your organization's approved identity tooling, make account/group/SSH-key setup safe to run more than once, grant only the access someone actually needs, log what happened, set an expiry, and have a clear offboarding path.

Shell scripting is a good fit for small tasks. Once you're dealing with heavier parsing, state, transactions, or complex error recovery, reach for a proper language or a configuration-management tool instead.

## Interview Questions

<details><summary>Q1. [Intermediate] How would you write a script to download the latest backup file from a remote server using SSH?</summary>

**Answer:**

I check the source and destination, find the newest completed backup on the remote server, copy it to a temporary local file, verify its checksum, and only then rename it into place. I don't assume the newest file is complete just because it exists.

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

I use a dedicated read-only SSH key, verify host keys, restrict what the remote account can do, check local free space, and alert on failure. A checksum match only proves the file transferred correctly — a real restore test is what proves the backup is actually useful.

</details>

<details><summary>Q2. [Basic] Write a Bash script to find the biggest file in a folder.</summary>

**Answer:**

With GNU `find`, I print the size in bytes, sort numerically, and safely show the first result:

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

Filenames can contain newlines, so a fully general production version would use null-delimited processing or a different language. I also don't delete the result automatically — first I check whether it's an active log, an open file, a database file, or a protected backup.

</details>

<details><summary>Q3. [Intermediate] Shell Script Disk Monitoring Bug</summary>

#### The script

```bash
DISK=$(df -h / | awk 'NR==2 {print $5}')

if [ $DISK -gt 80 ]; then
    echo "Disk usage is high"
fi
```

#### The bug

`df -h` prints the usage column with a `%` sign, e.g. `85%`. So `$DISK` holds the string `85%`, not the number `85`. The comparison:

```bash
[ 85% -gt 80 ]
```

fails with an "integer expression expected" error, because `-gt` needs a plain integer, not a string with a `%` at the end.

#### The fix

Strip the `%` sign before comparing, and avoid `-h` (human-readable units like `1.2G` also break numeric comparisons) — use plain block output instead:

```bash
DISK=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$DISK" -gt 80 ]; then
    echo "Disk usage is high"
fi
```

`df -P` gives POSIX-standard single-line output (avoids line-wrapping issues with very long device names), and `tr -d '%'` removes the percent sign so `$DISK` is a clean integer.

#### Short interview answer

"The bug is that `df -h` includes a `%` sign in the usage field, so the variable holds something like `85%`, and comparing that with `-gt` in a numeric test fails or behaves unexpectedly. The fix is to strip the `%` character with `tr -d '%'` before the comparison, and use `df -P` instead of `-h` for reliable single-line, script-friendly output."

</details>

<details><summary>Q4. [Basic] Write a shell script that starts Nginx only when it is not running.</summary>

**Answer:**

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

In automation I'd run this through a properly authorized service account or a configuration-management module, rather than embedding a password. I check `nginx -t` after any config change, keep logs around if it fails, and make sure running the script twice is safe.

A monitoring system should be the one that catches the outage in the first place — this script is a fix, not a substitute for a health check.

</details>

<details><summary>Q5. [Intermediate] What is an example of a complex automation script you have written?</summary>

**Answer:**

A good example is a deployment script that validates its inputs, checks dependencies, takes a backup, deploys a fixed build artifact, runs smoke tests, and rolls back automatically if anything fails.

My flow is:

1. Parse the environment and version; reject anything unrecognized.
2. Acquire a lock so two deployments can't run at once.
3. Confirm the artifact's signature or checksum and check available disk space.
4. Record the current version so I can roll back to it.
5. Drain or remove the instance from traffic.
6. Deploy and restart, with a timeout.
7. Run a health check and a real call to a dependency.
8. Roll back to the old version if any check fails.
9. Bring traffic back, release the lock, emit metrics, and notify the team.

I use `set -Eeuo pipefail`, a cleanup trap, structured logs, quoted variables, explicit exit codes, and a dry-run mode. In an interview I like to describe one real failure I found — for example, a health endpoint that passed while database authentication was actually failing — and how I added a dependency smoke test so it wouldn't happen again.

</details>

<details><summary>Q6. [Advanced] Shell Script for 500 Servers</summary>

#### The script

```bash
#!/bin/bash

for server in $(cat servers.txt)
do
    ssh $server "df -h"
    ssh $server "systemctl status nginx"
done
```

#### Problems

1. **Fully sequential** — with 500 servers, this runs one SSH connection at a time; if each takes even a few seconds, the whole run takes a very long time.
2. **No error handling** — if a server is unreachable, the script just moves to the next one with no logging of the failure, no exit code check, and no summary of failures.
3. **Unquoted variable** (`$server`) — breaks on any hostname with spaces or unexpected characters, and is generally unsafe shell practice.
4. **Two separate SSH connections per server** — doubles connection overhead; both commands could run in one SSH session.
5. **No timeout** — a single unreachable/hanging server can block the whole script indefinitely (no `ConnectTimeout`).
6. **No parallelism control** — running all 500 at once could also overwhelm the network/local machine, so unlimited parallelism isn't safe either.

#### Improved version for production

```bash
#!/bin/bash
set -uo pipefail

SERVERS_FILE="servers.txt"
MAX_PARALLEL=20
TIMEOUT=10

check_server() {
    local server="$1"
    if ! ssh -o ConnectTimeout="$TIMEOUT" -o BatchMode=yes "$server" \
        "df -h && systemctl status nginx" > "logs/${server}.log" 2>&1; then
        echo "FAILED: $server"
    else
        echo "OK: $server"
    fi
}
export -f check_server
export TIMEOUT

mkdir -p logs

xargs -a "$SERVERS_FILE" -P "$MAX_PARALLEL" -I{} bash -c 'check_server "$@"' _ {}
```

Key improvements:

- `xargs -P` runs checks in parallel with a controlled limit (20 at a time), instead of one at a time.
- `-o ConnectTimeout` prevents one dead server from hanging the whole run.
- Each server's output is logged to its own file for later review.
- Success/failure is printed per server instead of silently continuing.

#### Short interview answer

"With 500 servers, running SSH sequentially is far too slow and has no error handling — a hung or unreachable server can block everything indefinitely. I'd add `ConnectTimeout` to fail fast on unreachable hosts, run checks in parallel with a controlled concurrency limit using something like `xargs -P`, log each server's output to its own file, and print a clear success/failure summary instead of silently continuing past errors."

</details>

<details><summary>Q7. [Intermediate] How can PowerShell help with cost optimization?</summary>

**Answer:**

PowerShell can inventory resources, apply schedules, and produce cleanup reports for someone to review. For example, I can find unattached Azure managed disks without deleting anything yet:

```powershell
$disks = Get-AzDisk | Where-Object { $_.ManagedBy -eq $null }
$disks | Select-Object Name, ResourceGroupName, DiskSizeGB, TimeCreated |
    Export-Csv ./unattached-disks.csv -NoTypeInformation
```

My process is: report, then owner review, then approval, then deletion after a retention period. Other useful automations are stopping non-production VMs after hours, spotting idle public IPs and snapshots, enforcing tags, right-sizing resources based on real usage, and setting budget alerts.

I use a managed identity, `-WhatIf` where it's supported, scope restrictions, exclusions for protected resources, audit logs, and a recoverable holding period before anything is actually deleted. The goal is to save money without hurting availability, performance, or the retention rules we're required to follow.

</details>

<details><summary>Q8. [Basic] Was PowerShell part of CI or CD?</summary>

**Answer:**

PowerShell can be part of both.

In CI it can validate configuration, run Pester tests, calculate version numbers, build packages, and check the output of ARM/Bicep/Terraform. In CD it can authenticate with a workload identity, deploy resources, update configuration, run smoke tests, and trigger a rollback.

I keep scripts in Git as modules or functions instead of writing large blocks of inline pipeline code. The pipeline passes explicit parameters, secrets come from the platform's secret store, and scripts return a non-zero exit code on failure.

Any function that changes something destructive supports `ShouldProcess`/`-WhatIf`. I test the script on its own and pin the Az module version, so an automatic module upgrade can't quietly change production behavior.

</details>

<details><summary>Q9. [Intermediate] Kubernetes deployment rollout status check</summary>

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

</details>

<details><summary>Q10. [Intermediate] Docker disk cleanup script</summary>

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

</details>

<details><summary>Q11. [Intermediate] Linux disk usage monitoring script</summary>

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

</details>

<details><summary>Q12. [Intermediate] Log backup script</summary>

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

</details>
