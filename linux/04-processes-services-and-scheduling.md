# Linux: Processes, Services, and Scheduling

> Inspecting and signalling processes, zombies and orphans, systemd services and targets, and cron scheduling.

## Key Concepts

### Process Management: Your Applications Under the Hood

When an application crashes, consumes too much CPU, or stops responding, you need to look at its processes.

#### The commands you'll actually use

See what's running:

```bash
# The holy trinity of process monitoring
ps aux                    # Snapshot of all processes
top                       # Real-time view (like Task Manager)
htop                      # Enhanced version (install it everywhere)
```

When you run `ps aux` on a production server, check the `%CPU` and `%MEM` columns for outliers, and look for any process that shouldn't be running at all.

Kill misbehaving processes:

```bash
# Find the troublemaker first
ps aux | grep nginx

# Kill it gently
kill 1234

# Kill it with force (when gentle doesn't work)
kill -9 1234

# Signal all matching processes only after confirming the exact target
pkill -TERM -x nginx
```

Try a plain `kill` before `kill -9`. A plain `kill` sends `SIGTERM`, which asks the process to shut down cleanly. `kill -9` sends `SIGKILL`, which ends it immediately with no chance to clean up.

#### Process hierarchy matters

```bash
# See the family tree of processes
pstree                    # Visual process tree
pstree -p                 # Include process IDs
```

This shows parent-child relationships. Do not assume killing a parent process also ends its children — a child can catch the signal, keep running, or get re-parented to another process.

For managed applications, use the service manager or orchestrator instead of killing processes directly, so shutdown and restart behavior stays consistent.

### Service Management: Controlling Your Applications

Modern Linux uses `systemd` for service management.

#### Systemd service control

```bash
# Basic service operations
sudo systemctl start nginx            # Start web server
sudo systemctl stop nginx             # Stop web server
sudo systemctl restart nginx          # Restart (stop then start)
sudo systemctl reload nginx           # Reload config without restart

# Service status and health
systemctl status nginx                # Detailed service status
systemctl is-active nginx             # Quick active check
systemctl is-enabled nginx            # Check if starts at boot

# Enable/disable services
sudo systemctl enable nginx           # Start automatically at boot
sudo systemctl disable nginx          # Don't start at boot
```

#### Service discovery and troubleshooting

```bash
# List services
systemctl list-units --type=service   # All services
systemctl list-units --failed         # Only failed services
systemctl list-unit-files --type=service | grep enabled  # Boot-enabled services

# Log investigation
journalctl -u nginx                       # Service-specific logs
journalctl -u nginx --since "1 hour ago"  # Recent logs
journalctl -f -u nginx                    # Follow logs in real-time
```

#### Legacy service management

```bash
# Traditional service command (still works)
sudo service nginx start              # Start service
sudo service nginx status             # Check status
sudo /etc/init.d/nginx restart        # Direct init script
```

### Cron for scheduled shell automation

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

#### Short interview answer

I used cron to automate log cleanup, disk checks, backup verification, log rotation, and health checks. Scripts were tested manually first, scheduled with `crontab -e`, and configured to log both output and errors (`>> log 2>&1`) so failures are visible after the fact rather than silent.

## Interview Questions

<details><summary>Q1. [Basic] How do you check running processes?</summary>

**Answer:**

For a snapshot, I run `ps -eo pid,ppid,user,stat,lstart,etime,%cpu,%mem,cmd --sort=-%cpu`. For a live view, `top` or `htop`. For trends over time, `pidstat -p <pid> 1`. `pgrep -af name` finds matching command lines, and for a systemd service I use `systemctl status` and `journalctl -u`.

I look at the owner, parent process, state (running, sleeping, uninterruptible, or zombie), how long it has run, CPU and memory use, threads, and open files or ports. A process showing up in `ps` is not necessarily healthy, so I also check the application's own health endpoint or metrics.

I don't kill anything until I know who owns it and what it's for, and I capture logs or a memory dump first if that evidence would otherwise be lost.

</details>

<details><summary>Q2. [Basic] How do you kill a process in one command?</summary>

**Answer:**

Normally I use the service manager or a plain SIGTERM: `systemctl stop app` or `kill -TERM <pid>`, then wait and check it actually stopped. SIGTERM gives the process a chance to clean up, drain connections, and flush data.

If it hasn't exited after a reasonable, approved wait, I check its state first — a process stuck in uninterruptible sleep (D state) can't be killed until the kernel operation it's waiting on finishes — and capture evidence, then use `kill -KILL` only as a last resort.

I avoid broad `pkill` unless I've confirmed the pattern with `pgrep -af` first. After the process is gone, I check whether its parent or supervisor — systemd or Kubernetes, for example — will restart it, check the ports and data consistency, and confirm the application is actually healthy. Killing a process is a mitigation, not a fix for the underlying cause.

</details>

<details><summary>Q3. [Basic] Command to kill a process <em>(asked in interview round)</em></summary>

```bash
ps aux | grep <name>     # find PID
kill <PID>               # ask it to stop gracefully
kill -9 <PID>            # force-kill, last resort
pkill -f <pattern>       # kill by command pattern
kill -HUP <PID>          # reload config for many daemons
```

Try a plain `kill` first so the process can clean up after itself. Only use `-9` if it ignores that and refuses to stop.

</details>

<details><summary>Q4. [Basic] What is the difference between <code>kill -15</code> and <code>kill -9</code>?</summary>

**Answer:**

`kill -15` sends SIGTERM, which an application can catch and handle — stop accepting new work, flush its state, close connections cleanly. `kill -9` sends SIGKILL — the kernel stops the process immediately, and it gets no chance to clean up.

I start with SIGTERM, look into why shutdown is taking too long if it is, and only reach for SIGKILL when the process is genuinely stuck and I understand what an abrupt stop will cost. Neither one should be used carelessly on a database or other critical service.

</details>

<details><summary>Q5. [Intermediate] How do you identify which process is writing to a file in real time?</summary>

**Answer:**

I start with `sudo lsof /path/file` or `sudo fuser -v /path/file` — both show which processes currently have the file open. I confirm the PID and command with `ps -fp <pid>`, and check its systemd unit with `systemctl status <service>`.

To watch activity over time, `inotifywait -m /path/file` shows changes as they happen. If the file gets opened and closed too quickly to catch that way, Linux's audit subsystem is more reliable:

```bash
sudo auditctl -w /path/file -p wa -k file_write
sudo ausearch -k file_write
```

I remove the temporary audit rule once I'm done. I don't stop a process until I know whether it's a legitimate writer, a misconfigured service, or something suspicious.

</details>

<details><summary>Q6. [Intermediate] What are zombie processes and how do you remove them?</summary>

**Answer:**

A zombie is a child process that has already exited, but whose parent hasn't called `wait()` to collect its exit status yet. It uses almost no memory or CPU, but it still holds a slot in the process table. I find them with `ps -eo pid,ppid,state,cmd | awk '$3=="Z"'` and then look at the parent PID.

Sending a signal to a zombie does nothing, since it's already dead. I first try asking the parent to reload or restart gracefully; when the parent itself exits, PID 1 normally adopts and cleans up any leftover zombies.

If zombies keep piling up, the real fix belongs in the parent program — it needs to handle `SIGCHLD` and call `wait` or `waitpid`. I also check the process-count limit, since enough zombies can actually prevent new processes from starting.

</details>

<details><summary>Q7. [Intermediate] Zombie and orphan processes <em>(asked in interview round)</em></summary>

A zombie process has already exited, but its parent never called `wait()` to collect its exit status, so its entry lingers in the process table with state `Z`. It uses no memory or CPU, just a slot in the process table. To clear it, get the parent to reap it by handling `SIGCHLD`. If the parent is broken, kill the parent instead — the zombie is re-parented to init and reaped from there. You cannot `kill -9` a zombie; it's already dead.

An orphan is a child process whose parent died first. It gets re-parented to init or systemd (PID 1) right away, and PID 1 reaps it when it exits. This is normally harmless.

In containers, run an init process (`--init` or `tini`) so PID 1 can reap zombies properly.

</details>

<details><summary>Q8. [Basic] What are runlevels or systemd targets?</summary>

**Answer:**

SysV runlevels represented boot modes — commonly 1 for single-user/rescue, 3 for multi-user text mode, 5 for graphical, and 0/6 for halt/reboot, though the exact meaning could vary by system. Systemd instead uses targets, which group units and their dependencies together — things like `rescue.target`, `multi-user.target`, and `graphical.target`.

I check the default with `systemctl get-default`, change it permanently with `systemctl set-default multi-user.target`, or switch the current boot state with `systemctl isolate ...`. `isolate` can stop services that aren't required by the target it switches to, so I use console access and understand the impact before doing it.

The old runlevel numbers map roughly onto targets, but systemd's dependency model is much richer than a single number.

</details>

<details><summary>Q9. [Intermediate] A scheduled cron job is not executing. How do you debug?</summary>

**Answer:**

I check the crontab for the right user with `crontab -l -u user`, confirm the five time fields and timezone are correct, and that `cron` or `crond` is actually running. Then I check `journalctl -u cron` or `/var/log/cron`, and any mail output cron generates.

Cron runs with a small environment and a different working directory than an interactive shell, so I use absolute paths for commands and files, a valid shebang, executable permissions, and explicitly set any variables the job needs. A useful temporary test entry:

```cron
*/5 * * * * /opt/jobs/report.sh >>/var/log/report-cron.log 2>&1
```

I run the exact same command as the cron user with a clean environment, check for locking issues and SELinux/AppArmor denials, and confirm the expected output actually happened. For anything important, I add failure alerting and make sure a retry is safe to run again without causing problems.

</details>

<details><summary>Q10. [Basic] How do you schedule a cron job every 15 minutes?</summary>

**Answer:**

The crontab entry is:

```cron
*/15 * * * * /usr/local/bin/collect-metrics.sh >>/var/log/collect-metrics.log 2>&1
```

This runs at minutes 0, 15, 30, and 45 of every hour — not fifteen minutes after the previous run finishes. I use absolute paths, set the shebang and executable permission, and install it under the right service account.

If overlapping runs would be unsafe, I wrap it with `flock -n /run/collect-metrics.lock ...`. I test the script as that user and add monitoring, since cron itself only proves the job started, not that the actual task succeeded.

</details>

<details><summary>Q11. [Intermediate] How do you troubleshoot a failing service using logs, systemd and Bash? <em>(asked in interview round)</em></summary>

**Answer:**

`systemd` tells me *how* the service failed (exit code, signal, restart loop), the journal tells me *why*, and Bash lets me reproduce the start command with the same environment.

**Steps:**

1. `systemctl status <svc>`: state, main PID, exit code or signal, last log lines.
2. `journalctl -u <svc> -b -n 200 --no-pager`, and `-f` while restarting.
3. Inspect the unit: `systemctl cat <svc>` shows the unit plus drop-ins. Check `ExecStart`, `User`, `WorkingDirectory`, `EnvironmentFile`.
4. Check restart behaviour: `Restart=`, `StartLimitBurst`. A unit in `failed` after too many restarts needs `systemctl reset-failed`.
5. Reproduce manually as the service user: `sudo -u appuser bash -x /opt/app/start.sh`.
6. Check the common causes: port in use, missing file or permission, bad config syntax, missing environment variable, dependency not up, disk full, SELinux.
7. After editing a unit, run `systemctl daemon-reload` before restarting.

**Decision flow:**

```text
systemctl status
      |
      +-- status=203/EXEC ----> binary path or permissions wrong
      +-- status=217/USER ----> User= does not exist
      +-- status=1 / custom --> app error --> journalctl -u
      +-- signal=KILL --------> OOM killer or timeout --> dmesg, TimeoutStopSec
      +-- start-limit-hit ----> crash loop --> fix cause, reset-failed
```

**Commands:**

```bash
systemctl status myapp --no-pager -l
journalctl -u myapp -b --since "30 min ago" --no-pager
journalctl -u myapp -p err -n 50
systemctl cat myapp
systemctl show myapp -p ExecMainStatus -p NRestarts -p Result
systemctl list-dependencies myapp
sudo -u appuser bash -c 'set -a; . /etc/myapp/env; set +a; exec /opt/myapp/bin/myapp --config /etc/myapp/app.yml'
sudo ss -lntp | grep ':8080'          # port already taken?
sudo systemctl daemon-reload && sudo systemctl restart myapp
```

A quick Bash helper that prints the essentials for any failed unit:

```bash
#!/usr/bin/env bash
set -euo pipefail

for unit in $(systemctl list-units --state=failed --no-legend --plain | awk '{print $1}'); do
  echo "=== ${unit}"
  systemctl show "${unit}" -p Result -p ExecMainStatus -p NRestarts
  journalctl -u "${unit}" -n 20 --no-pager
done
```

**Important points:**

- Use `systemctl edit <svc>` for overrides rather than editing vendor unit files.
- Environment variables from your shell are not present under `systemd`; that is why "it works when I run it manually" is common.
- Log to `stdout`/`stderr` so the journal captures everything, and set journal retention so logs survive reboots (`Storage=persistent`).

See also: [Processes, services and scheduling](../linux/04-processes-services-and-scheduling.md), [Logs and log analysis](../linux/08-logs-and-log-analysis.md), [Bash fundamentals and error handling](../shell-scripting/01-bash-fundamentals-and-error-handling.md)

**Interview-ready answer:**

> "I start with `systemctl status` to see the exit code or signal, because that narrows it down quickly: 203 is a bad `ExecStart` path, a KILL signal often means the OOM killer, and start-limit-hit means a crash loop. Then I read `journalctl -u` for the actual error. I use `systemctl cat` to see the full unit including drop-ins, and check the user, working directory and environment file. If it is still unclear, I reproduce the start command manually as the service user with `bash -x`, which usually exposes a missing variable, permission or port conflict. After fixing it I run `daemon-reload` if I changed the unit, restart, and follow the journal to confirm it stays up."

</details>

<details><summary>Q12. [Intermediate] Handle zombie and orphan processes. <em>(asked in interview round)</em></summary>

**Answer:**

| | Zombie (`Z` state) | Orphan |
| --- | --- | --- |
| What | Finished, but the parent has not read its exit status with `wait()` | Still running, but its parent died |
| Resources | Only a process table entry (PID) | Normal resources |
| Who handles it | Parent must reap it | Re-parented to PID 1 (or a `subreaper`), which reaps it |

You cannot kill a zombie; it is already dead. Signal or restart the parent so it reaps the child, or kill the parent so the zombie is re-parented to PID 1 and reaped. Many zombies point to a parent bug and can exhaust PIDs. In containers, use an init such as `tini` (`docker run --init`) because the app often runs as PID 1 and does not reap children.

```bash
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'
kill -s SIGCHLD <PPID>     # ask the parent to reap
```

**Interview-ready answer:**

> A zombie is a process that has exited but whose parent has not collected its exit status, so it only holds a PID entry; an orphan is a live process whose parent died and that gets adopted by PID 1. I find zombies with `ps` filtered on state `Z` and look at their parent PID. Since a zombie cannot be killed, I send `SIGCHLD` to the parent or restart it, and if needed kill the parent so init reaps them. In containers I run a minimal init like `tini` so PID 1 reaps children properly.

See also: [Zombie and orphan processes](../linux/04-processes-services-and-scheduling.md)

</details>
