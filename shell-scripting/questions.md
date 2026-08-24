# Shell Scripting Interview Questions

---

### 1. How would you write a script to download the latest backup file from a remote server using SSH?

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

---

### 2. What is an example of a complex automation script you have written?

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

---

### 3. How do you debug automation scripts?

**Answer:**

I reproduce the failure with the same inputs and environment, then narrow it down to the first command that actually fails.

```bash
bash -n deploy.sh             # syntax
shellcheck deploy.sh          # common errors
bash -x deploy.sh --dry-run   # trace; avoid when secrets may print
```

I check the shebang line, the executable bit, PATH, the working directory, the user running it, environment variables, file permissions, exit codes, quoting, pipelines, network/DNS, and dependency versions. Scheduled jobs often fail simply because cron runs with a much smaller environment than an interactive shell.

I add `set -Eeuo pipefail` carefully, log useful context, and use `trap 'echo "failed at line $LINENO" >&2' ERR`. Once it's fixed, I test the success case, invalid input, a timeout, partial output, running it twice in a row, and cleanup. I redact secrets before sharing any trace output.

---

### 4. How can PowerShell help with cost optimization?

**Answer:**

PowerShell can inventory resources, apply schedules, and produce cleanup reports for someone to review. For example, I can find unattached Azure managed disks without deleting anything yet:

```powershell
$disks = Get-AzDisk | Where-Object { $_.ManagedBy -eq $null }
$disks | Select-Object Name, ResourceGroupName, DiskSizeGB, TimeCreated |
    Export-Csv ./unattached-disks.csv -NoTypeInformation
```

My process is: report, then owner review, then approval, then deletion after a retention period. Other useful automations are stopping non-production VMs after hours, spotting idle public IPs and snapshots, enforcing tags, right-sizing resources based on real usage, and setting budget alerts.

I use a managed identity, `-WhatIf` where it's supported, scope restrictions, exclusions for protected resources, audit logs, and a recoverable holding period before anything is actually deleted. The goal is to save money without hurting availability, performance, or the retention rules we're required to follow.

---

### 5. Was PowerShell part of CI or CD?

**Answer:**

PowerShell can be part of both.

In CI it can validate configuration, run Pester tests, calculate version numbers, build packages, and check the output of ARM/Bicep/Terraform. In CD it can authenticate with a workload identity, deploy resources, update configuration, run smoke tests, and trigger a rollback.

I keep scripts in Git as modules or functions instead of writing large blocks of inline pipeline code. The pipeline passes explicit parameters, secrets come from the platform's secret store, and scripts return a non-zero exit code on failure.

Any function that changes something destructive supports `ShouldProcess`/`-WhatIf`. I test the script on its own and pin the Az module version, so an automatic module upgrade can't quietly change production behavior.

---

### 6. Write a Bash script to add two numbers.

**Answer:**

I check that both inputs are actually integers instead of trusting Bash arithmetic to reject bad input on its own.

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || ! $1 =~ ^-?[0-9]+$ || ! $2 =~ ^-?[0-9]+$ ]]; then
  echo "Usage: $0 <integer> <integer>" >&2
  exit 2
fi

printf '%s\n' "$(( $1 + $2 ))"
```

For example, `./add.sh 10 20` returns `30`, and `./add.sh ten 20` returns a usage error instead of a wrong answer. For numbers bigger than Bash's integer range, or for decimals, I'd use `bc`, Python, or another tool built for real math.

---

### 7. Write a Bash script to find the biggest file in a folder.

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

In automation I'd run this through a properly authorized service account or a configuration-management module, rather than embedding a password. I check `nginx -t` after any config change, keep logs around if it fails, and make sure running the script twice is safe.

A monitoring system should be the one that catches the outage in the first place — this script is a fix, not a substitute for a health check.

---

### 9. What does `echo $?` indicate in Linux shell scripting?

**Answer:**

`$?` holds the exit status of the last command or pipeline that just finished. By convention, zero means success and anything else means that command failed in its own specific way.

You have to capture it immediately, because running any other command — even `echo` or `cd` — overwrites it.

```bash
curl --fail --silent https://service.example/health
status=$?
if (( status != 0 )); then
  printf 'Health check failed with exit code %d\n' "$status" >&2
fi
```

For a pipeline, I turn on `set -o pipefail`, since otherwise `$?` only reflects the last command in the chain. In production scripts I handle expected failures explicitly and give them useful context, rather than treating `set -e` as a substitute for real error handling.
