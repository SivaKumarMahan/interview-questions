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

<details><summary>Q13. [Basic] Write a shell script to delete all files from a specific directory safely. <em>(asked in interview round)</em></summary>

**Answer:**

"Safely" is the key word. The script must validate the input, refuse dangerous paths such as `/`, show what will be deleted (dry run), ask for confirmation, and keep the directory itself.

**Flow:**

```text
Parse options (-n dry run, -a all, -y yes)
        |
        v
Validate: argument given, not empty, is a directory
        |
        v
Resolve real path, block / and system paths
        |
        v
List / count matches  --(dry run)--> print and exit
        |
        v
Confirm --> find -mindepth 1 ... -delete
```

**Script:**

```bash
#!/usr/bin/env bash
# clean_dir.sh - safely delete files inside a directory (the directory itself is kept)
#
# Usage: ./clean_dir.sh [-n] [-a] [-y] <directory>
#   -n  dry run: only list what would be deleted
#   -a  delete everything inside, including subdirectories (default: files only)
#   -y  do not ask for confirmation (for cron / automation)

set -euo pipefail

usage() {
  echo "Usage: $0 [-n] [-a] [-y] <directory>" >&2
  exit 1
}

DRY_RUN=false
ALL=false
ASSUME_YES=false

while getopts ":nay" opt; do
  case "$opt" in
    n) DRY_RUN=true ;;
    a) ALL=true ;;
    y) ASSUME_YES=true ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 1 ]] || usage

TARGET="$1"

# 1. Basic validation
if [[ -z "${TARGET// /}" ]]; then
  echo "ERROR: directory path is empty" >&2
  exit 1
fi
if [[ ! -d "$TARGET" ]]; then
  echo "ERROR: '$TARGET' is not a directory" >&2
  exit 1
fi

# 2. Resolve symlinks and ../ so the checks below cannot be bypassed
TARGET="$(realpath -- "$TARGET")"

# 3. Refuse root, system directories and the home directory itself
case "$TARGET" in
  / | /bin | /boot | /dev | /etc | /home | /lib | /lib64 | /opt | /proc | \
  /root | /run | /sbin | /srv | /sys | /usr | /var)
    echo "ERROR: refusing to clean protected path '$TARGET'" >&2
    exit 1
    ;;
esac
if [[ "$TARGET" == "${HOME:-}" ]]; then
  echo "ERROR: refusing to clean the home directory" >&2
  exit 1
fi

# 4. Build the find expression
#    -xdev        : do not cross into other mounted filesystems
#    -mindepth 1  : never match the target directory itself
FIND_ARGS=(-xdev -mindepth 1)
if ! $ALL; then
  FIND_ARGS+=( \( -type f -o -type l \) )   # regular files and symlinks only
fi

COUNT=$(find "$TARGET" "${FIND_ARGS[@]}" -printf '.' | wc -c)
echo "Target : $TARGET"
echo "Matches: $COUNT"

if [[ "$COUNT" -eq 0 ]]; then
  echo "Nothing to delete."
  exit 0
fi

if $DRY_RUN; then
  echo "Dry run - these would be deleted:"
  find "$TARGET" "${FIND_ARGS[@]}" -print
  exit 0
fi

if ! $ASSUME_YES; then
  read -r -p "Delete $COUNT item(s) under $TARGET? [y/N] " answer
  if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# 5. Delete. -delete does not follow symlinks, so a link to /etc removes only the link.
find "$TARGET" "${FIND_ARGS[@]}" -delete
echo "Deleted $COUNT item(s) from $TARGET"
```

**Usage:**

```bash
chmod +x clean_dir.sh
./clean_dir.sh -n /var/app/tmp        # preview
./clean_dir.sh /var/app/tmp           # delete files, keep subdirectories, ask first
./clean_dir.sh -a -y /var/app/tmp     # delete everything inside, no prompt
```

To delete only old files, add an age test, for example `find "$TARGET" -xdev -mindepth 1 -type f -mtime +7 -delete`.

**Important points:**

- Never write `rm -rf $DIR/*`. If `DIR` is empty or unset, it becomes `rm -rf /*`. `set -u` and the empty-path check prevent this.
- Quote every variable so paths with spaces work and are not split.
- `find -mindepth 1` keeps the directory itself; `-delete` handles hidden files and huge directories without "argument list too long" errors.
- Use `realpath` before the protected-path check, otherwise `/tmp/../etc` or a symlink could slip through.
- Always offer a dry run; in production, log what was deleted.

See also: [shell-scripting/03](../shell-scripting/03-cheat-sheet-and-interview-scripts.md).

**Interview-ready answer:**

> "I would not use a plain `rm -rf` on a variable, because an empty variable can turn it into `rm -rf /*`. My script uses `set -euo pipefail`, checks that an argument was passed, that it is not empty and that it is a directory. It resolves the real path with `realpath` and refuses `/`, system directories and the home directory. It then uses `find` with `-mindepth 1` so the directory itself stays, shows a count, supports a dry-run flag and asks for confirmation. The actual deletion is `find ... -delete`, which also handles hidden files and does not follow symlinks."

</details>

<details><summary>Q14. [Intermediate] Write a shell script to generate an alert when CPU utilization exceeds a defined threshold. <em>(asked in interview round)</em></summary>

**Answer:**

The script measures CPU usage, compares it with a threshold, and sends an alert (log, syslog and optionally a webhook such as Slack or Teams). It reads `/proc/stat` twice a few seconds apart, which is more reliable than parsing `top` output, and uses a cooldown so it does not send the same alert every minute.

**Flow:**

```text
cron (every 5 min) --> read /proc/stat --> sleep N --> read again
                                                  |
                                                  v
                                  usage = 100 * (busy delta / total delta)
                                                  |
                               usage >= threshold and not in cooldown?
                                    |                     |
                                   yes                    no --> log OK, exit
                                    v
                    log + logger + webhook (top 5 processes in the log)
```

**Script:**

```bash
#!/usr/bin/env bash
# cpu_alert.sh - alert when CPU utilization exceeds a threshold
#
# Usage: ./cpu_alert.sh [threshold_percent]     (default 80)
# Optional env vars:
#   INTERVAL=5            seconds between the two samples
#   COOLDOWN=900          seconds to wait before alerting again
#   WEBHOOK_URL=https://hooks.slack.com/services/...   (Slack / Teams incoming webhook)
#   LOG_FILE=/var/log/cpu_alert.log

set -euo pipefail

THRESHOLD="${1:-80}"
INTERVAL="${INTERVAL:-5}"
COOLDOWN="${COOLDOWN:-900}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
LOG_FILE="${LOG_FILE:-/var/log/cpu_alert.log}"
STATE_FILE="${STATE_FILE:-/tmp/cpu_alert.last}"
HOST="$(hostname)"

if ! [[ "$THRESHOLD" =~ ^[0-9]+$ ]] || (( THRESHOLD < 1 || THRESHOLD > 100 )); then
  echo "ERROR: threshold must be an integer between 1 and 100" >&2
  exit 1
fi

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

# Prints "<total> <idle>" from the aggregate cpu line of /proc/stat
read_cpu() {
  local _cpu user nice system idle iowait irq softirq steal _rest
  read -r _cpu user nice system idle iowait irq softirq steal _rest < /proc/stat
  echo "$((user + nice + system + idle + iowait + irq + softirq + steal)) $((idle + iowait))"
}

read -r total1 idle1 <<< "$(read_cpu)"
sleep "$INTERVAL"
read -r total2 idle2 <<< "$(read_cpu)"

total_delta=$((total2 - total1))
idle_delta=$((idle2 - idle1))
if (( total_delta <= 0 )); then
  log "WARN: could not calculate CPU usage"
  exit 0
fi
usage=$(( 100 * (total_delta - idle_delta) / total_delta ))

if (( usage < THRESHOLD )); then
  log "OK: CPU ${usage}% on ${HOST} (threshold ${THRESHOLD}%)"
  exit 0
fi

# Cooldown: avoid sending the same alert on every run
now=$(date +%s)
last=0
if [[ -f "$STATE_FILE" ]]; then
  last=$(cat "$STATE_FILE")
fi
if (( now - last < COOLDOWN )); then
  log "ALERT suppressed (cooldown): CPU ${usage}% on ${HOST}"
  exit 0
fi
echo "$now" > "$STATE_FILE"

message="ALERT: CPU ${usage}% on ${HOST} exceeds ${THRESHOLD}%"
log "$message"
log "Top processes:"
ps -eo pid,user,comm,%cpu --sort=-%cpu | head -n 6 | tee -a "$LOG_FILE"
logger -t cpu_alert -p user.warning "$message"

if [[ -n "$WEBHOOK_URL" ]]; then
  curl -fsS -m 10 -X POST -H 'Content-Type: application/json' \
    -d "{\"text\": \"${message}\"}" "$WEBHOOK_URL" > /dev/null \
    || log "WARN: failed to send webhook alert"
fi

exit 2   # non-zero so cron wrappers or CI can detect the alert
```

**Schedule it:**

```bash
chmod +x /opt/scripts/cpu_alert.sh
crontab -e
# every 5 minutes, threshold 85%
*/5 * * * * WEBHOOK_URL=https://hooks.slack.com/services/XXX /opt/scripts/cpu_alert.sh 85 >/dev/null 2>&1
```

To test, generate load with `yes > /dev/null &` (one per core), run the script with a low threshold, then stop the load with `kill %1`.

**Production alternative:**

In production, I would use a monitoring system instead of a cron script, for example `node_exporter` with a Prometheus rule:

```yaml
groups:
  - name: node
    rules:
      - alert: HighCpuUsage
        expr: 100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CPU above 85% on {{ $labels.instance }} for 10 minutes"
```

On AWS, the equivalent is a CloudWatch alarm on `CPUUtilization` with an SNS action.

**Important points:**

- Sample over an interval; a single reading of `/proc/stat` only gives the average since boot.
- Avoid alert noise: use a cooldown in scripts, or a `for:` duration in Prometheus.
- Include context in the alert (host, value, top processes) so the on-call engineer can act quickly.
- Do not put webhook URLs in the script; pass them through environment variables or a secret store.

See also: [shell-scripting/02](../shell-scripting/02-automation-scripts-in-practice.md).

**Interview-ready answer:**

> "My script takes a threshold as an argument and validates it. It reads the aggregate CPU line from `/proc/stat` twice, a few seconds apart, and calculates usage from the busy and idle deltas, which is more reliable than parsing `top`. If usage is above the threshold, it logs the value with the top CPU processes, writes to syslog with `logger`, and posts to a Slack or Teams webhook passed in through an environment variable. It uses a cooldown file so the same alert is not sent on every run, and I schedule it with cron every five minutes. In production I would prefer `node_exporter` with a Prometheus alert rule that has a `for` duration, or a CloudWatch alarm on AWS."

</details>

<details><summary>Q15. [Advanced] You have 10,000 endpoints. How would you check whether all of them are working? <em>(asked in interview round)</em></summary>

**Answer:**

Checking 10,000 endpoints one after another is too slow (10,000 × 2 seconds is over 5 hours). The key is **bounded concurrency with timeouts**: run, say, 100–200 checks in parallel, give each a strict connect/total timeout, retry transient failures once or twice, and write a report of failures. For ongoing checks, I move it into monitoring (Blackbox exporter or synthetic canaries) instead of a script.

**Steps:**

1. Put the endpoints in a file (one URL per line) or pull them from an inventory/service catalog.
2. Define "working": HTTP status 2xx/3xx, optionally response time below a threshold or a keyword in the body.
3. Run checks in parallel with a concurrency limit so you don't exhaust file descriptors or overload a shared backend.
4. Use timeouts and a small number of retries with backoff.
5. Produce a summary (total, healthy, failed) and a CSV of failures, then alert or open tickets.

```text
endpoints.txt (10,000 URLs)
        |
        v
Worker pool (100-200 concurrent, timeout 5s, retry 2)
        |
        v
Result per URL: status code, latency, error
        |
        +--> report.csv (failures only)
        +--> summary: 9,982 OK / 18 failed
        +--> alert / ticket
```

**Bash: `xargs -P` with `curl`:**

```bash
#!/usr/bin/env bash
set -euo pipefail

check() {
  local url="$1" out
  out=$(curl -sS -o /dev/null -L \
        --connect-timeout 3 --max-time 5 \
        --retry 2 --retry-delay 1 \
        -w '%{http_code} %{time_total}' "$url" 2>/dev/null) || out="000 0"
  echo "$url $out"
}
export -f check

xargs -a endpoints.txt -P 100 -I{} bash -c 'check "$@"' _ {} > results.txt

awk '$2 !~ /^[23]/' results.txt > failed.txt
echo "Total: $(wc -l < results.txt)  Failed: $(wc -l < failed.txt)"
```

`curl` returns `000` when it cannot connect at all (DNS failure, timeout, TLS error). GNU `parallel` (`parallel -j 100 check :::: endpoints.txt`) works the same way and adds a job log and progress bar.

**Python: `asyncio` with a concurrency limit:**

```python
#!/usr/bin/env python3
import asyncio
import csv

import httpx

CONCURRENCY = 200
TIMEOUT = httpx.Timeout(5.0, connect=3.0)

async def check(client, sem, url):
    async with sem:
        for attempt in range(3):
            try:
                r = await client.get(url, follow_redirects=True)
                return url, r.status_code, round(r.elapsed.total_seconds(), 3), ""
            except httpx.HTTPError as exc:
                if attempt == 2:
                    return url, 0, 0, type(exc).__name__
                await asyncio.sleep(2 ** attempt)

async def main():
    with open("endpoints.txt") as f:
        urls = [line.strip() for line in f if line.strip()]
    sem = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY)
    async with httpx.AsyncClient(timeout=TIMEOUT, limits=limits) as client:
        results = await asyncio.gather(*(check(client, sem, u) for u in urls))

    failed = [r for r in results if not (200 <= r[1] < 400)]
    with open("failed.csv", "w", newline="") as f:
        csv.writer(f).writerows([("url", "status", "seconds", "error"), *failed])
    print(f"Total: {len(results)}  OK: {len(results) - len(failed)}  Failed: {len(failed)}")

asyncio.run(main())
```

**Ongoing monitoring instead of a script:**

- **Prometheus Blackbox exporter**: probe each URL with the `http_2xx` module; alert on `probe_success == 0` for 2–5 minutes.
- **CloudWatch Synthetics canaries** or **Route 53 health checks** for the most critical public endpoints.
- Grafana dashboard grouped by service/team so failures route to the right owner.

**Important points:**

- Always set both a connect timeout and a total timeout; one hung endpoint must not stall the run.
- Limit concurrency; unbounded parallelism can hit file descriptor limits (`ulimit -n`), exhaust NAT Gateway ports or look like a DoS to a WAF.
- Use `HEAD` only if the endpoints support it; many apps return 405 for `HEAD`, so `GET` on a lightweight `/health` path is safer.
- Report root causes by category (DNS, TLS, timeout, 5xx) so teams can act quickly.

See also: [Prometheus (Blackbox exporter)](../monitoring-tools/02-prometheus.md), [Shell automation scripts in practice](../shell-scripting/02-automation-scripts-in-practice.md).

**Interview-ready answer:**

> "I would never check 10,000 endpoints sequentially. I put the URLs in a file and run checks in parallel with a bounded worker pool, for example `xargs -P 100` with `curl` using a connect timeout, a total timeout and two retries, or a Python `asyncio` script with `httpx` and a semaphore of around 200. Each result records the status code, latency and error type, and I output a summary plus a CSV of only the failures. I treat 2xx and 3xx as healthy and group failures by DNS, TLS, timeout or 5xx so the right team can act. I limit concurrency so I don't hit file descriptor limits or trigger the WAF. For continuous checking I would move this into the Prometheus Blackbox exporter or CloudWatch Synthetics with alerts, instead of running a script by hand."

</details>

<details><summary>Q16. [Intermediate] Write a Bash script to identify failed services and alert on disk usage above 85%. <em>(asked in interview round)</em></summary>

**Answer:**

The script checks `systemd` for failed units and every real filesystem for usage above a threshold, prints a report, sends an alert (Slack-compatible webhook or syslog) only when something is wrong, and exits non-zero so it also works as a cron job or monitoring check.

**Approach:**

1. Use `systemctl list-units --state=failed` for failed services.
2. Use `df -P` (POSIX output, one line per filesystem) and skip pseudo filesystems.
3. Collect problems into an array; alert once with a summary.
4. Use `set -euo pipefail`, quote variables and avoid parsing errors from long device names.

**Flow:**

```text
Start
  |
  v
List failed systemd units --> add each to problems[]
  |
  v
df -P (exclude tmpfs/devtmpfs/overlay/squashfs) --> usage > threshold? --> add to problems[]
  |
  v
problems empty? --yes--> log OK, exit 0
  |no
  v
Send alert (webhook or logger) --> print report --> exit 1
```

**Script:**

```bash
#!/usr/bin/env bash
# health-check.sh - report failed systemd services and filesystems above a usage threshold.
# Usage: THRESHOLD=85 WEBHOOK_URL=https://hooks.example.com/xyz ./health-check.sh
set -euo pipefail

THRESHOLD="${THRESHOLD:-85}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
HOST="$(hostname -f 2>/dev/null || hostname)"

if ! [[ "${THRESHOLD}" =~ ^[0-9]+$ ]] || (( THRESHOLD < 1 || THRESHOLD > 100 )); then
  echo "THRESHOLD must be an integer between 1 and 100" >&2
  exit 2
fi

problems=()

# 1. Failed systemd units
while read -r unit _; do
  [[ -n "${unit}" ]] && problems+=("Service failed: ${unit}")
done < <(systemctl list-units --type=service --state=failed --no-legend --plain 2>/dev/null || true)

# 2. Disk usage above threshold (POSIX format, skip pseudo filesystems)
while read -r fs _size _used _avail pcent mount; do
  usage="${pcent%\%}"
  [[ "${usage}" =~ ^[0-9]+$ ]] || continue
  if (( usage > THRESHOLD )); then
    problems+=("Disk ${mount} (${fs}) at ${usage}% (threshold ${THRESHOLD}%)")
  fi
done < <(df -P -x tmpfs -x devtmpfs -x overlay -x squashfs | tail -n +2)

if (( ${#problems[@]} == 0 )); then
  echo "$(date -Is) ${HOST}: OK - no failed services, all disks <= ${THRESHOLD}%"
  exit 0
fi

report="$(printf '%s\n' "${problems[@]}")"
message="ALERT on ${HOST}:
${report}"

echo "${message}"

if [[ -n "${WEBHOOK_URL}" ]] && command -v jq >/dev/null 2>&1; then
  payload="$(jq -n --arg text "${message}" '{text: $text}')"
  curl -fsS --max-time 10 -H 'Content-Type: application/json' \
    -d "${payload}" "${WEBHOOK_URL}" >/dev/null || echo "Webhook delivery failed" >&2
else
  logger -t health-check -p user.err -- "${message}"
fi

exit 1
```

Run it from cron every five minutes:

```bash
*/5 * * * * THRESHOLD=85 WEBHOOK_URL=https://hooks.example.com/xyz /usr/local/bin/health-check.sh >> /var/log/health-check.log 2>&1
```

**Important points:**

- `df -P` keeps each filesystem on one line, so long device names do not break parsing.
- `jq` builds the JSON payload safely; string concatenation breaks on quotes and newlines.
- Exit codes (0 OK, 1 problems, 2 bad input) let the same script feed monitoring checks, cron alerting or a CI job.
- `while read` with process substitution keeps the array in the current shell; piping into `while` would run it in a separate child process and lose the results.
- In production, prefer node exporter and Alertmanager for this; the script is a fallback or a quick check.

See also: [Automation shell and Python examples](../repetitive-questions/automation-shell-and-python-examples.md), [Bash automation scripts in practice](../shell-scripting/02-automation-scripts-in-practice.md), [Shell scripting cheat sheet and interview scripts](../shell-scripting/03-cheat-sheet-and-interview-scripts.md)

**Interview-ready answer:**

> "The script uses `set -euo pipefail` and checks two things. For services it reads `systemctl list-units --state=failed` and adds each failed unit to a problems array. For disks it parses `df -P`, excluding pseudo filesystems like `tmpfs` and `overlay`, strips the percent sign and compares the usage to a configurable threshold, 85 by default. If the array is empty it logs OK and exits 0; otherwise it builds one summary message, sends it to a webhook with the JSON built by `jq`, or falls back to `logger`, and exits 1 so cron or a monitoring tool can act on it. I use process substitution so the array is not lost in a child process, and in production I would back this with node exporter alerts."

</details>
