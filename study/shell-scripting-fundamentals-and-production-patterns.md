# Shell Scripting Fundamentals and Production Patterns

Bash fundamentals ($0/$#/"$@"/quoting/traps), the 20 questions that come up around them, and production-grade automation patterns - disk monitoring, log cleanup, backup verification, service health checks, email alerts, and cron.

For Kubernetes/Docker-specific automation scripts (rollout status checks, image cleanup, Python equivalents), see [bash-python-automation-scripts.md](bash-python-automation-scripts.md) - this file covers general-purpose Linux/shell operations instead.

## Contents

1. [Production shell script structure](#1-production-shell-script-structure)
2. [Shell fundamentals glossary](#2-shell-fundamentals-glossary)
3. [20 common shell interview questions](#3-20-common-shell-interview-questions)
4. [Disk usage monitoring (multi-mount)](#4-disk-usage-monitoring-multi-mount)
5. [Log cleanup](#5-log-cleanup)
6. [Backup verification](#6-backup-verification)
7. [Service health check and restart](#7-service-health-check-and-restart)
8. [Email alerting](#8-email-alerting)
9. [Cron](#9-cron)

---

## 1. Production shell script structure

A production script should have:

- A clear interpreter line.
- `set -Eeuo pipefail` where appropriate.
- Quoted variables.
- Input validation.
- Safe temporary files.
- Meaningful exit codes.
- Logging that never includes secrets.
- Locks for concurrency where the script shouldn't run twice at once.
- Cleanup traps.

Basic structure:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    printf 'Usage: %s <service-name>\n' "$0" >&2
}

if (( $# != 1 )); then
    usage
    exit 64
fi

service_name=$1

if systemctl is-active --quiet "$service_name"; then
    printf '%s is active\n' "$service_name"
else
    printf '%s is not active\n' "$service_name" >&2
    exit 1
fi
```

---

## 2. Shell fundamentals glossary

| Symbol/pattern | Meaning |
| --- | --- |
| `$0` | Invoked script name/path |
| `$1`, `$2`, ... | Positional arguments |
| `$#` | Argument count |
| `"$@"` | All arguments, preserving each as a separate word/boundary |
| `$(command)` | Command substitution |
| `read -r` | Reads input without treating backslashes as escapes |
| Quoting | Quote variable expansions unless word splitting/globbing is intentional |
| `[[ ... ]]` | Bash conditional |
| `(( ... ))` | Arithmetic evaluation |
| `case` | Multiple string alternatives |

---

## 3. 20 common shell interview questions

**1. Why use `#!/usr/bin/env bash`?**
It's the shebang, telling the OS to use Bash. `env` finds Bash through `PATH`, which is more portable than hardcoding `/bin/bash` (which doesn't exist at that path on every system).

**2. What is `set -Eeuo pipefail`?**
- `-e` - exit immediately on a command failure.
- `-E` - preserves `ERR` traps inside functions and subshells (without it, `-e`'s effect can silently not propagate into a function).
- `-u` - treats unset variables as errors instead of expanding to empty strings.
- `pipefail` - makes a pipeline fail if *any* command in it fails, not just the last one.

**3. Why quote variables?**
To prevent spaces and special characters from causing word splitting or unintended glob expansion.

```bash
rm "$file"
```

Without quotes, a filename containing a space would be split into multiple arguments.

**4. What is `$0`?**
The script's own name/path.

**5. What are `$1`, `$2`, etc.?**
Positional parameters - the arguments passed to the script, in order.

**6. What is `$#`?**
The number of arguments passed to the script.

**7. What is `"$@"`?**
All arguments, with each one preserved as a separate word - critical when forwarding arguments to another command, since `"$@"` won't merge an argument containing spaces into a neighboring one.

**8. What is `$(command)`?**
Command substitution - runs `command` and substitutes its output.

```bash
today=$(date)
```

**9. Why use `read -r`?**
To prevent backslashes in the input from being interpreted as escape characters - without `-r`, `read` treats `\` specially, which is almost never what you want when reading arbitrary text.

**10. `[ ]` vs `[[ ]]`?**
`[[ ]]` is Bash-specific and safer/more expressive - it handles strings with spaces without extra quoting headaches, supports `&&`/`||` directly, and supports pattern/regex matching (`=~`).

**11. When do you use `(( ))`?**
For arithmetic, e.g. `(( count += 1 ))`. Also usable as a truthiness check inside `if`, e.g. `if (( usage >= 80 ))`.

**12. Why use `case`?**
Cleaner than a chain of `if`/`elif` branches when checking a variable against multiple possible string values.

**13. What is input validation, in this context?**
Checking that arguments and values are valid *before* performing actions with them - e.g. confirming an argument count, a file exists, or a value is numeric before using it destructively.

**14. Why use meaningful exit codes?**
Automation tools (CI/CD, cron, monitoring) key off exit codes to determine success/failure. `0` means success; non-zero means failure. `64` is a conventional code for command-line usage errors (from BSD's `sysexits.h` convention).

**15. What is `trap`?**
Runs commands when the script exits or receives a signal - the standard way to guarantee cleanup even if the script exits early or is interrupted.

```bash
trap 'rm -f /tmp/myfile' EXIT
```

**16. Why use lock files?**
To prevent multiple instances of the same script from running concurrently - important for anything scheduled (cron) that might still be running when the next scheduled run starts.

**17. Why avoid logging secrets?**
Logs are often widely readable (shared log aggregators, ticket attachments, support access). Passwords, tokens, and keys should never be written to logs.

**18. What does `systemctl is-active --quiet` do?**
Checks a service's state purely through its exit code, without printing status output - ideal for use inside an `if` condition in a script.

**19. Why `printf` instead of `echo`?**
`printf` has more predictable formatting and better portability across shells - `echo`'s handling of flags like `-e` and backslash escapes varies between implementations.

**20. "What shell automation have you done?"**
Disk monitoring, old log cleanup, backup verification, service restart/health checks, user account workflows, email/Slack alerts, and CI/CD automation.

---

## 4. Disk usage monitoring (multi-mount)

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

---

## 5. Log cleanup

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

---

## 6. Backup verification

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

---

## 7. Service health check and restart

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

---

## 8. Email alerting

```bash
mail -s "Disk Usage Alert" admin@example.com < report.txt
```

- `mail` - send email.
- `-s` - subject.
- `admin@example.com` - recipient.
- `< report.txt` - use `report.txt` as the email body.

This requires the host to have a configured MTA such as Postfix, Sendmail, or Exim - `mail` doesn't send anything on its own without one. In cloud environments, Slack, Teams, PagerDuty, or Azure Monitor Action Groups are often preferred over configuring an MTA on every host.

---

## 9. Cron

Cron is the Linux job scheduler used to run scripts automatically on a schedule.

```bash
chmod +x /opt/scripts/log_cleanup.sh

crontab -e
```

Run every day at 2 AM:

```
0 2 * * * /opt/scripts/log_cleanup.sh
```

```bash
crontab -l
```

**System-wide cron locations:**

- `/etc/crontab`
- `/etc/cron.d/`
- `/etc/cron.daily/`
- `/etc/cron.weekly/`
- `/etc/cron.monthly/`
- `/etc/cron.hourly/`

User crontabs (via `crontab -e`) are stored under system-managed spool locations such as `/var/spool/cron` or `/var/spool/cron/crontabs`, rather than edited as plain files directly.

**Log cron output** so failures are visible after the fact rather than silently swallowed:

```
0 2 * * * /opt/scripts/log_cleanup.sh >> /var/log/log_cleanup.log 2>&1
```

**Check the cron service is running:**

```bash
# Ubuntu/Debian
systemctl status cron

# RHEL/CentOS
systemctl status crond
```

**Enable at boot:**

```bash
systemctl enable cron
# or
systemctl enable crond
```

### Short interview answer

I used cron to automate log cleanup, disk checks, backup verification, log rotation, and health checks. Scripts were tested manually first, scheduled with `crontab -e`, and configured to log both output and errors (`>> log 2>&1`) so failures are visible after the fact rather than silent.
