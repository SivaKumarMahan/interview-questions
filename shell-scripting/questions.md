# Shell Scripting Interview Questions

---

### 1. How would you write a script to download the latest backup file from a remote server using SSH?

**Answer:**

I validate the source and destination, find the newest completed backup remotely, copy it to a temporary local filename, verify its checksum, and atomically rename it. I do not assume that the newest file is complete merely because it exists.

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

I use a dedicated read-only SSH key, verify host keys, restrict remote permissions, check local free space, and alert on failure. A restore test proves the backup is useful; checksum success only proves transfer integrity.

---

### 2. What is an example of a complex automation script you have written?

**Answer:**

A strong example is a deployment script that validates inputs, checks dependencies, takes a backup, deploys an immutable (not changed after creation) artifact, performs smoke tests, and rolls back if validation fails.

My flow is:

1. Parse the environment and version; reject unknown values.
2. Acquire a lock to prevent concurrent deployment.
3. Confirm artifact signature/checksum and available disk space.
4. Capture the current version for rollback.
5. Drain or remove the instance from traffic.
6. Deploy and restart with a timeout.
7. Test health and a real dependency call.
8. Restore the old version if checks fail.
9. Return traffic, release the lock, emit metrics, and notify the team.

I use `set -Eeuo pipefail`, a cleanup trap, structured logs, quoted variables, explicit exit codes, and a dry-run mode. In an interview I explain one failure found—for example, a health endpoint passed while database authentication failed—and how I added a dependency smoke test to prevent recurrence.
---

### 3. How do you debug automation scripts?

**Answer:**

I reproduce with the same inputs and environment, then isolate the first failing command.

```bash
bash -n deploy.sh             # syntax
shellcheck deploy.sh          # common errors
bash -x deploy.sh --dry-run   # trace; avoid when secrets may print
```

I check the shebang, executable bit, PATH, working directory, user, environment variables, file permissions, command exit codes, quoting, pipelines, network/DNS, and dependency versions. Scheduled jobs often fail because cron has a minimal environment.

I add `set -Eeuo pipefail` carefully, log useful context, and use `trap 'echo "failed at line $LINENO" >&2' ERR`. After fixing, I test success, invalid input, timeout, partial output, repeated execution, and cleanup. I redact secrets before sharing traces.

---

### 4. How can PowerShell help with cost optimization?

**Answer:**

PowerShell can inventory resources, apply schedules, and generate reviewable cleanup reports. For example, I can find unattached Azure managed disks without deleting them immediately:

```powershell
$disks = Get-AzDisk | Where-Object { $_.ManagedBy -eq $null }
$disks | Select-Object Name, ResourceGroupName, DiskSizeGB, TimeCreated |
    Export-Csv ./unattached-disks.csv -NoTypeInformation
```

My process is report → owner validation → approval → deletion after retention. Other automations stop non-production VMs after business hours, identify idle public IPs and snapshots, enforce tags, right-size resources from metrics, and create budget alerts.
I use managed identity, `-WhatIf` where supported, scope restrictions, exclusions for protected resources, audit logs, and a recoverable holding period. Cost savings are measured without violating availability, performance, or retention requirements.

---

### 5. Was PowerShell part of CI or CD?

**Answer:**

PowerShell can participate in both.

In CI it can validate configuration, run Pester tests, calculate versions, build packages, and inspect ARM/Bicep/Terraform output. In CD it can authenticate using workload identity, deploy resources, update configuration, run smoke tests, and trigger rollback.
I keep scripts in Git as modules/functions rather than embedding large inline pipeline blocks. The pipeline passes explicit parameters, secrets come from the platform secret store, and scripts return non-zero on failure.

Destructive functions support `ShouldProcess`/`-WhatIf`. I test the script independently and pin the Az module version so an automatic module upgrade does not unexpectedly change production behavior.

---

### 6. Write a Bash script to add two numbers.

**Answer:**

I validate that both inputs are integers instead of relying on Bash arithmetic to silently accept bad input.

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || ! $1 =~ ^-?[0-9]+$ || ! $2 =~ ^-?[0-9]+$ ]]; then
  echo "Usage: $0 <integer> <integer>" >&2
  exit 2
fi

printf '%s\n' "$(( $1 + $2 ))"
```

Examples are `./add.sh 10 20` returning `30` and `./add.sh ten 20` returning a usage error. For values larger than Bash integer range or decimal arithmetic, I would use `bc`, Python, or another suitable numeric tool.

---

### 7. Write a Bash script to find the biggest file in a folder.

**Answer:**

For GNU `find`, I output size in bytes, sort numerically, and safely display the first result:

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

I mention that filenames can contain newlines, so a fully general production implementation should use null-delimited processing or another language. I also avoid deleting the result automatically: first verify whether it is an active log, open file, database file, or protected backup.
---

### 8. Write a shell script that starts Nginx only when it is not running.

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

In automation I run this through a properly authorized service account or configuration-management module rather than embedding a password. I validate `nginx -t` after configuration changes, preserve logs on failure, and make repeated execution safe.

A monitoring system should detect the outage; the script is fix, not the only health check.

---

### 9. What does `echo $?` indicate in Linux shell scripting?

**Answer:**

`$?` is the exit status of the most recently completed foreground command or pipeline. By convention, zero means success and a nonzero value indicates a command-specific failure.

It must be captured immediately because running `echo`, `cd`, or another command replaces it.

```bash
curl --fail --silent https://service.example/health
status=$?
if (( status != 0 )); then
  printf 'Health check failed with exit code %d\n' "$status" >&2
fi
```

For pipelines I enable `set -o pipefail`; otherwise `$?` normally reflects only the final command. In production scripts I handle expected failures explicitly and include useful context rather than using `set -e` as a substitute for designed error handling.
