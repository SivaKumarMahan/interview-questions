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
