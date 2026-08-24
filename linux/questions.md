## 1. Do you have hands-on Linux experience? Which platform?

**Answer:**

I answer honestly, naming the platforms, how long I worked with them, and what I actually did. For example: "I have administered Ubuntu and RHEL/Amazon Linux application servers. My work included systemd services, user and sudo and SSH setup, package patching, filesystems and LVM, network and DNS and firewall checks, cron jobs, logs, performance troubleshooting, hardening, backups, and CI/CD deployment."

Then I give a real example. Once a disk filled up because logs were not being rotated. I found the filesystem and the open files, safely freed up space, checked that the application could still write, and then added log rotation plus alerts at 70% and 85% full. This shows I actually investigated the problem, not just that I can name a few distributions.

I also make clear which tasks I owned myself versus which were handled by a managed service or a separate cloud team.

## 2. What are common Linux commands you use?

**Answer:**

I group commands by what they're for. For files: `ls`, `find`, `cp`, `mv`, `stat`. For text and logs: `less`, `grep`, `awk`, `sed`, `tail`. For processes: `ps`, `top`, `pidstat`, `kill`. For resource checks: `free`, `vmstat`, `df`, `du`, `iostat`. For network: `ip`, `ss`, `dig`, `curl`, `nc`. For services: `systemctl`, `journalctl`. For permissions: `chmod`, `chown`, `getfacl`. And for transferring or archiving data: `rsync`, `scp`, `tar`.

I use them carefully. I quote file paths, gather read-only evidence before changing anything, use `--` before an untrusted filename, look at what a recursive or delete command will touch before running it, and keep a record of commands and their output during an incident. I pick a command to test one specific idea. Running a pile of commands without understanding what they show is not troubleshooting.

## 3. How do you check running processes?

**Answer:**

For a snapshot, I run `ps -eo pid,ppid,user,stat,lstart,etime,%cpu,%mem,cmd --sort=-%cpu`. For a live view, `top` or `htop`. For trends over time, `pidstat -p <pid> 1`. `pgrep -af name` finds matching command lines, and for a systemd service I use `systemctl status` and `journalctl -u`.

I look at the owner, parent process, state (running, sleeping, uninterruptible, or zombie), how long it has run, CPU and memory use, threads, and open files or ports. A process showing up in `ps` is not necessarily healthy, so I also check the application's own health endpoint or metrics.

I don't kill anything until I know who owns it and what it's for, and I capture logs or a memory dump first if that evidence would otherwise be lost.

## 4. How do you kill a process in one command?

**Answer:**

Normally I use the service manager or a plain SIGTERM: `systemctl stop app` or `kill -TERM <pid>`, then wait and check it actually stopped. SIGTERM gives the process a chance to clean up, drain connections, and flush data.

If it hasn't exited after a reasonable, approved wait, I check its state first — a process stuck in uninterruptible sleep (D state) can't be killed until the kernel operation it's waiting on finishes — and capture evidence, then use `kill -KILL` only as a last resort.

I avoid broad `pkill` unless I've confirmed the pattern with `pgrep -af` first. After the process is gone, I check whether its parent or supervisor — systemd or Kubernetes, for example — will restart it, check the ports and data consistency, and confirm the application is actually healthy. Killing a process is a mitigation, not a fix for the underlying cause.

## 5. How do you check disk usage?

**Answer:**

`df -hT` shows how full each filesystem is; `df -i` shows inode usage instead of space. Once I know which filesystem is affected, I dig in with `du -xhd1 /path | sort -h` and keep drilling down from there. `find` can list the biggest files, and `lsof +L1` finds files that were deleted but are still open, which `du` won't show.

I compare what `df` and `du` report, and check mount points, reserved blocks, sparse files, and container or log paths.

I never delete files I don't recognize, or system or database files. Instead I stop whatever is generating the growth, rotate or archive the data that's safe to remove, or add storage, then confirm the service can still write, and add alerts based on retention and capacity forecasts.

## 6. How do you find free memory?

**Answer:**

`free -h` — but I look at the `available` column, not `free`, because Linux uses spare RAM for cache that it can reclaim when needed. `vmstat 1` shows swap activity (`si`/`so`) and how many processes are running or blocked. `ps --sort=-%mem`, `smem`, `pmap`, and `pidstat -r` help identify what's using the memory.

I also check the kernel's out-of-memory logs: `journalctl -k | grep -i oom`.

I look at this against the actual workload and its trend over time. High used memory or cache alone is normal. Sustained swapping, allocation failures, OOM kills, or rising latency are the real signs of pressure.

I fix the actual cause — a leak, a cache setting, a config change — or right-size and scale the service based on evidence. Restarting is only a temporary fix, and I preserve diagnostics before doing it.

## 7. How do you archive or compress a directory?

**Answer:**

```bash
tar -C /path/to -czf backup-$(date +%F).tar.gz directory
tar -tzf backup-2026-07-19.tar.gz | head
mkdir restore && tar -C restore -xzf backup-2026-07-19.tar.gz
sha256sum backup-2026-07-19.tar.gz > backup.sha256
```

`tar` bundles files and keeps their metadata; gzip compresses the result. I use `-C` so the archive doesn't store unwanted absolute paths, look inside the archive before extracting it, extract anything untrusted into its own isolated directory, verify the checksum, and do a test restore.

For a live database or data that's actively changing, I use an application-consistent backup instead of tarring files while they're being written to. Encryption and where backups are kept follow whatever the data policy requires.

## 8. Do you need a password or key for SSH?

**Answer:**

SSH supports passwords, public keys, certificates, multi-factor auth through PAM, and federated or session-based systems. In production and cloud environments, password login and direct root login are usually disabled, and access goes through keys, certificates, or a session manager like SSM instead.

The client proves it holds the private key; the server just stores the matching public key in `authorized_keys` with the right ownership and permissions.

The private key needs protecting — a passphrase, an agent, or hardware storage where possible — and it should never be copied broadly onto servers or into CI systems. Each person should have their own key. Access is logged, and keys get rotated or revoked.

If a key is lost, I remove its public key, issue a new pair through a process that verifies identity, test the new access before closing the recovery session, and treat the old private key as compromised if it might still exist somewhere.

## 9. How do you list all SSH users?

**Answer:**

There's no single "list of SSH users" to query. I build the picture from accounts with an interactive shell (`getent passwd`, excluding ones set to `nologin` or `false`), the `AllowUsers`/`AllowGroups`/`Deny*` rules, PAM and directory groups, sudo rules, and authorized keys or SSH certificates.

To see who's actually using SSH, I check the auth logs and current sessions with `who`, `w`, `last`, and `journalctl -u sshd`.

I never print private or sensitive key material. What comes out of a review is: the user, who owns the account, why it exists, how it authenticates, its privilege level, when it was last used, and when it expires.

Stale accounts or keys get disabled through an approved process, and I monitor for new ones. Service accounts should use a non-interactive shell unless they genuinely need SSH.

## 10. A user cannot log in. How will you troubleshoot?

**Answer:**

I split the problem into network and authentication. On the client side: DNS, IP reachability, whether the port is open, and `ssh -vvv` for detail. On the server, using console or another access path: is sshd running and listening, is its config valid (`sshd -t`), what does the firewall or SELinux say, and what's the exact reason in the auth log.

Then I check the account itself: `getent passwd`, whether it's locked or expired (`passwd -S`, `chage -l`), its shell and home directory, the Allow/Deny and PAM rules, group membership, and whether the key actually matches. For SSH, the home directory usually can't be writable by others, `.ssh` needs mode 700, `authorized_keys` needs mode 600 with the right owner, and SELinux context may need restoring.

I make the smallest fix that solves the problem, test that the user can now log in and that unauthorized access is still denied, and never loosen security broadly to work around this. I record the actual root cause — an expired account, a wrong key, a permission or config issue — and follow up with an expiry alert or better onboarding automation.

## 11. A user was added to sudoers, but sudo still does not work. What could be wrong?

**Answer:**

I capture the exact error `sudo` gives, then run `id user` and `sudo -l -U user`, and check `/etc/sudoers` and any included files, their order, group membership and whether the session needs a refresh, hostname or command restrictions, `secure_path`, and the account's PAM state. I only validate syntax with `visudo -c`, and only edit with `visudo` or `visudo -f`.

I give the narrowest set of commands needed rather than `ALL=(ALL) ALL`, prefer a group-based rule managed through configuration management, and then test both an allowed command and one that should stay denied.

I check audit logs to confirm the access is actually being used. Note that `NOPASSWD` only skips the password prompt — it doesn't grant authorization by itself, so adding it is not a general fix for sudo problems.

## 12. A user's home directory is missing. How will you restore it?

**Answer:**

I first confirm the account's home path with `getent passwd user`, check whether the filesystem or mount is actually there, and rule out a network home that's just temporarily unavailable versus one that was actually deleted. If I'm about to restore data, I stop the user's processes first so nothing is writing to it.

To recreate it: `install -d -m 700 -o user -g group /home/user`, copy `/etc/skel` only for the default files, restore from backup while preserving ownership, ACLs, and extended attributes, and fix the SELinux context with `restorecon` if needed.

I avoid running a recursive chown across mounted or shared data without reviewing the scope first. I check that login, shell, SSH, and application files work, compare the restore against the original timing and content, and look into how the directory was deleted. Then I put backup, tighter access, and lifecycle automation in place so it doesn't happen again.

## 13. What does `chmod 755` mean?

**Answer:**

The three octal digits are for owner, group, and others: read is 4, write is 2, execute is 1. `755` means the owner gets read, write, execute; the group and everyone else get read and execute. On a directory, read lets you list names, write lets you create or delete entries, and execute lets you enter or access entries. On a regular file, execute just means it can be run.

```bash
chmod 755 /opt/app/bin/start
stat -c '%A %a %U:%G %n' /opt/app/bin/start
```

I don't use 755 for everything — config files and secrets need tighter permissions, and shared directories often need setgid or ACLs instead. Permissions also depend on the parent directories, ACLs, mount options, and SELinux or AppArmor.

## 14. What is `chown`?

**Answer:**

`chown user:group path` changes both owner and group; `chgrp` changes only the group. Ownership is what standard Linux permission checks and service access are based on.

Before a recursive change, I preview it with `find` first, confirm the mount boundaries and any symlinks, and check what the application actually needs — a wrong `chown -R` on `/`, a database, or a whole system tree can break things or expose data. Where supported I use `chown -R --from=old:group new:group /explicit/path`, or a targeted `find -xdev` instead.

Afterward I verify with `stat` or `getfacl`, confirm the service still runs and can read and write as expected, and check the SELinux context separately since ownership doesn't fix that. I put the change into package or configuration management so it stays in place.

## 15. A script is executable by one user but not another. How do you resolve this?

**Answer:**

I run the script as the failing user and see whether I get "Permission denied" or an interpreter-not-found error — that tells me a lot. Then I check `namei -l /path/script` (execute or traverse permission is needed on every parent directory), `ls -l` or `getfacl`, `id`, whether the shebang's interpreter is itself executable, line endings, whether the mount has `noexec`, and SELinux/AppArmor/audit logs.

Running `bash script` directly can help tell whether it's the execute bit or `noexec` versus a problem in the script itself, but it's not a real fix. I grant access through the right group, ACL, or ownership and the minimum directory traversal needed — never world-writable or 777. For SELinux, I restore the correct label or policy rather than turning SELinux off.

Sometimes the user needs a new session for a group change to take effect. I confirm the intended user can now run it and that anyone unauthorized still can't, then put the permissions into configuration management.

## 16. How do you set default file and directory permissions?

**Answer:**

By default, new files start at 666 and directories at 777, minus the umask. A umask of `022` gives 644 for files and 755 for directories; `027` gives 640 and 750. I set this in the shell profile or, for a service, in systemd's `UMask=` — though the application itself may set an explicit mode regardless.

For a shared project directory, I use setgid plus a default ACL:

```bash
chmod 2770 /srv/team
setfacl -m g:team:rwx,d:g:team:rwx,d:o::--- /srv/team
getfacl /srv/team
```

I test by actually creating a file or directory as the service user. Umask doesn't change files that already exist, and ACLs can change the effective permission on top of it. I avoid defaults that are more open than necessary.

## 17. What are sticky bit, setuid, and setgid?

**Answer:**

The sticky bit (`+t`) is used on shared directories like `/tmp`, which typically has mode `1777`. It means only the file's owner, the directory's owner, or a privileged user can delete or rename a file there. Setgid on a directory (`2xxx`) makes new files inside inherit the directory's group; setgid on an executable makes it run with the file's group instead of the caller's.

Setuid on an executable (`4xxx`) makes it run as the file's owner — often root. Linux generally ignores setuid on shell scripts.

These bits matter for security. I list them with `find / -xdev -perm /6000 -type f`, check what package they belong to and why they're there, and remove any that shouldn't be there through an approved change. I'd rather use `sudo`, Linux capabilities, or a proper service design than a custom setuid program, and I test and audit whatever I change.

## 18. What is the purpose of `grep`?

**Answer:**

`grep` picks out lines that match a pattern. Useful flags: `-i` for case-insensitive, `-n` for line numbers, `-r` for recursive, `-E` for extended regex, `-F` for a literal string, `-C` for surrounding context, `-v` to invert the match.

```bash
grep -nC 3 -E 'ERROR|FATAL' /var/log/app.log
zgrep -h 'request_id=abc123' /var/log/app.log*.gz
```

I narrow the search to a specific time range or set of files, and use a literal string match when the pattern comes from user input rather than a real regex. A match is just a clue, not the root cause — I compare its timestamp and details against other service and system metrics.

I'm careful not to expose secrets when sharing output. For structured logs, I'd rather use `jq` or a proper log query tool than a fragile regex.

## 19. Which `grep` flag shows lines not containing a keyword?

**Answer:**

`-v` inverts the match:

```bash
grep -vF 'health-check' access.log
grep -Ev 'DEBUG|TRACE' app.log
```

`-F` treats the keyword as a literal string; `-E` lets you use alternation and other regex features. I quote patterns carefully, and I remember `grep`'s exit code matters: 0 means it found a match, 1 means it found nothing, and anything higher means an error — which matters if a script uses `set -e`.

For binary, compressed, or rotated logs, I pick the right tool — `grep -a`, `zgrep`, or a proper log query — rather than forcing it. I keep the original log file intact rather than overwriting it just to get a filtered view.

## 20. How do you find all files modified in the last 10 minutes?

**Answer:**

I use `find` with the `-mmin` filter:

```bash
sudo find /var/log -type f -mmin -10 -printf '%TY-%Tm-%Td %TH:%TM %s %p\n'
```

`-10` means less than ten minutes ago, while `+10` means more than ten minutes ago. I search a specific path rather than `/` first, to keep it fast and avoid permission errors everywhere.

If this is part of an incident, I sort the results and compare the modification times against when the deployment or failure happened. I don't run `-delete` right away — I look at the matches, who owns them, and what they're for first.

## 21. How do you find large unused files across multiple partitions?

**Answer:**

I first list the mounted filesystems with `df -hT`, then search each relevant one separately. For example:

```bash
sudo find /data -xdev -type f -size +1G -mtime +30 \
  -printf '%s %u %TY-%Tm-%Td %p\n' | sort -nr | head -50
```

This finds files bigger than 1 GB that haven't been touched in over 30 days. Modification time alone doesn't prove a file is unused, so I also check access patterns, whether anything has it open with `lsof`, who owns it, retention rules, and who's responsible for it.

I archive or move a small, approved batch first, confirm the service is fine, and only then delete anything. If this keeps happening, I set up retention or log rotation instead of doing manual cleanup over and over.

## 22. How do you identify which process is writing to a file in real time?

**Answer:**

I start with `sudo lsof /path/file` or `sudo fuser -v /path/file` — both show which processes currently have the file open. I confirm the PID and command with `ps -fp <pid>`, and check its systemd unit with `systemctl status <service>`.

To watch activity over time, `inotifywait -m /path/file` shows changes as they happen. If the file gets opened and closed too quickly to catch that way, Linux's audit subsystem is more reliable:

```bash
sudo auditctl -w /path/file -p wa -k file_write
sudo ausearch -k file_write
```

I remove the temporary audit rule once I'm done. I don't stop a process until I know whether it's a legitimate writer, a misconfigured service, or something suspicious.

## 23. A log file shows junk characters. How do you check and recover it?

**Answer:**

I keep a copy first, then check what the file actually is:

```bash
file app.log
xxd -l 64 app.log
gzip -t app.log.gz       # if it is expected to be gzip
```

It might be compressed, UTF-16, contain ANSI control codes, or just be a binary application log rather than corrupted text. I try a safe conversion on the copy — for example `iconv -f UTF-16 -t UTF-8 input > output` — and use `less -R`, `strings`, or the application's own log viewer as needed.

I also check for disk errors, an interrupted rotation, or multiple processes writing incompatible formats to the same file. If integrity checks fail, I restore the log from backup or a central logging system rather than overwrite the only copy of the evidence during an incident.

## 24. Where are Apache logs usually located?

**Answer:**

On Debian and Ubuntu, they're usually under `/var/log/apache2/`; on RHEL-family systems, under `/var/log/httpd/`. The common files are `access.log` and `error.log`, but virtual hosts can point to separate files.

I confirm the actual path from configuration rather than assuming it:

```bash
apachectl -S
grep -R "^[[:space:]]*\(CustomLog\|ErrorLog\)" /etc/apache2 /etc/httpd 2>/dev/null
journalctl -u apache2 --since today   # or httpd
```

For a failed request, I match the timestamp, client IP, URL, and status code in the access log, then use the request ID or timestamp to find the matching entry in the error log and any upstream application logs.

## 25. What logs appear under `/var/log`?

**Answer:**

Typical examples are authentication logs (`auth.log` or `secure`), general system messages (`syslog` or `messages`), kernel messages, package manager history, `audit/audit.log`, cron logs, boot logs, and application directories like `nginx`, `apache2`, or `containers`. Rotated files usually end in `.1` or `.gz`.

The exact set depends on the distribution, because many systems now send most service output to the systemd journal instead of a flat file. I use `journalctl -u <service>`, `journalctl -p err`, and `journalctl --since ...` alongside whatever's in `/var/log`.

I check permissions and never truncate or change production logs during an investigation without preserving the evidence first.

## 26. What is log rotation?

**Answer:**

Log rotation stops a constantly growing log file from filling up the disk. Based on time or size, the current file gets renamed, older copies may be compressed, and anything past the retention limit gets deleted.

On Linux this is usually driven by `/etc/logrotate.conf` and files under `/etc/logrotate.d/`.

Before changing a rule, I test it with `logrotate -d /etc/logrotate.conf`. A service that keeps a file open needs a `postrotate` step to reload it — for example `systemctl reload nginx`. `copytruncate` is a fallback option, but it can lose a small amount of data.

I check permissions, ownership, any retention or compliance requirements, disk usage, and the next scheduled run rather than just forcing a rotation blindly.

## 27. A service is consuming 100% CPU. How will you find and fix it?

**Answer:**

First I check whether "100%" means one core or the whole machine, using `top`, `mpstat -P ALL 1`, and `pidstat -u -p ALL 1`. I find the PID and its busiest threads with `top -H -p <pid>`, then compare when it started and when CPU usage rose against traffic, cron jobs, deployments, and the service's own logs.

What I check next depends on the runtime: a Java thread dump (`jstack`), a .NET dump, a Python stack trace, or `strace -p <pid>` for a short, controlled window.

If customers are affected, I rate-limit traffic, pull the unhealthy instance out of the load balancer, scale up healthy replicas, or restart it gracefully after collecting evidence.

The real fix might be correcting an infinite loop, improving a query or index, adding a timeout, setting a resource limit, or adding capacity. Afterward I check CPU, latency, errors, and actual business transactions, and add an alert or regression test for what I found.

## 28. A process is causing high memory usage. How do you locate and stop it?

**Answer:**

I check both overall system pressure and the specific process:

```bash
free -m
vmstat 1
ps -eo pid,ppid,user,%mem,rss,vsz,cmd --sort=-rss | head
pmap -x <pid> | tail -1
```

RSS is resident memory; VSZ alone can be misleading. I check swap activity, OOM messages (`journalctl -k | grep -i oom`), container or cgroup limits, the request load, and whether memory keeps climbing, which points to a leak.

Where it's safe, I capture a heap dump or runtime metrics before stopping the process. I use `systemctl stop` or `kill -TERM` first, and only `kill -KILL` if a graceful shutdown fails.

Then I fix the actual leak or cache setting, set realistic limits and alerts, and load-test the fix.

## 29. What are zombie processes and how do you remove them?

**Answer:**

A zombie is a child process that has already exited, but whose parent hasn't called `wait()` to collect its exit status yet. It uses almost no memory or CPU, but it still holds a slot in the process table. I find them with `ps -eo pid,ppid,state,cmd | awk '$3=="Z"'` and then look at the parent PID.

Sending a signal to a zombie does nothing, since it's already dead. I first try asking the parent to reload or restart gracefully; when the parent itself exits, PID 1 normally adopts and cleans up any leftover zombies.

If zombies keep piling up, the real fix belongs in the parent program — it needs to handle `SIGCHLD` and call `wait` or `waitpid`. I also check the process-count limit, since enough zombies can actually prevent new processes from starting.

## 30. How do you fix "Too many open files" in Linux?

**Answer:**

I figure out whether this is a per-process limit or a system-wide one. I check `cat /proc/<pid>/limits`, count descriptors with `ls /proc/<pid>/fd | wc -l`, look at what they are with `lsof -p <pid>`, and check `/proc/sys/fs/file-nr`.

Repeated sockets or files of the same type usually point to a leak somewhere.

For a systemd service, a controlled way to raise the limit is:

```ini
[Service]
LimitNOFILE=65536
```

After `systemctl daemon-reload`, I restart during an approved window and confirm the new limit with `/proc/<new-pid>/limits`. Raising the limit only buys time if the application is leaking connections, so I also fix how it closes or pools connections, tune traffic if needed, and set an alert well before the new limit is hit.

## 31. How do you analyze high system load?

**Answer:**

Load average counts both runnable tasks and tasks stuck waiting on I/O, so it's not the same thing as CPU percentage. I compare the 1/5/15-minute load numbers against the CPU count, then use `vmstat 1` (looking at run/block queues and swap), `mpstat -P ALL 1`, `iostat -xz 1`, and `pidstat -dur 1` to figure out what the actual bottleneck is.

A high run-queue with busy CPUs points to CPU contention. A high block count, I/O wait, or long disk queues point to storage. Swapping and major page faults point to memory pressure. I also check `ps` for processes stuck in D state and look at NFS or downstream service latency.

I address whatever resource or workload is actually the problem, compare it against the normal baseline and any recent changes, and confirm latency and errors actually recover — not just that the load number dropped.

## 32. How do you debug a kernel panic?

**Answer:**

My first priority is saving the panic message and getting service back up through the approved failover or reboot procedure. I collect the console or serial output, hypervisor events, the previous boot's journal (`journalctl -k -b -1`), and any crash dump under `/var/crash`.

I note the kernel version and any recent changes to drivers, kernel, firmware, hardware, or workload.

If `kdump` is set up, I analyze the matching unstripped kernel and crash dump with the `crash` tool, or hand them to the vendor. I look for the module that faulted, the stack trace, machine-check errors, OOM or panic settings, and whether it's reproducible.

A temporary fix might be rolling back a kernel or driver, or moving the workload elsewhere. The real fix is a patched kernel, driver, or replacing failed hardware. I make sure `kdump` works and console access is ready before the next incident.

## 33. How do you fix NTP time sync issues?

**Answer:**

I check `timedatectl`, `chronyc tracking`, and `chronyc sources -v` to see the offset, which source is selected, and whether sources are reachable. Then I confirm the time service is running, its configured sources actually resolve, and UDP port 123 is allowed through.

On virtual machines, I also check whether the hypervisor's own time sync is enabled and conflicting.

For a large offset, jumping the clock can break databases and authentication, so I follow the application's maintenance procedure. For a small offset, chrony should adjust it gradually and safely. After fixing `/etc/chrony.conf`, I reload or restart chronyd and confirm the offset is shrinking and a source is marked selected (`^*`).

I keep monitoring drift, and use multiple approved internal time sources so a single NTP server isn't a single point of failure.

## 34. A scheduled cron job is not executing. How do you debug?

**Answer:**

I check the crontab for the right user with `crontab -l -u user`, confirm the five time fields and timezone are correct, and that `cron` or `crond` is actually running. Then I check `journalctl -u cron` or `/var/log/cron`, and any mail output cron generates.

Cron runs with a small environment and a different working directory than an interactive shell, so I use absolute paths for commands and files, a valid shebang, executable permissions, and explicitly set any variables the job needs. A useful temporary test entry:

```cron
*/5 * * * * /opt/jobs/report.sh >>/var/log/report-cron.log 2>&1
```

I run the exact same command as the cron user with a clean environment, check for locking issues and SELinux/AppArmor denials, and confirm the expected output actually happened. For anything important, I add failure alerting and make sure a retry is safe to run again without causing problems.

## 35. How do you schedule a cron job every 15 minutes?

**Answer:**

The crontab entry is:

```cron
*/15 * * * * /usr/local/bin/collect-metrics.sh >>/var/log/collect-metrics.log 2>&1
```

This runs at minutes 0, 15, 30, and 45 of every hour — not fifteen minutes after the previous run finishes. I use absolute paths, set the shebang and executable permission, and install it under the right service account.

If overlapping runs would be unsafe, I wrap it with `flock -n /run/collect-metrics.lock ...`. I test the script as that user and add monitoring, since cron itself only proves the job started, not that the actual task succeeded.

## 36. What happens when `/` is 100% full?

**Answer:**

When root fills up, applications can't write logs, PID files, temp files, package databases, uploads, or database transactions. Services can crash or fail to start, and even logging in can fail if PAM or the shell can't write what it needs.

Running out of inodes causes the exact same symptom even when `df -h` shows free space, so I check both `df -hT` and `df -i`.

I make sure I can still get in, find the filesystem that's growing and the safest large files to deal with, and cut down on writes where I can. I rotate or archive known logs, clear approved caches or temp data, or add storage — I never blindly delete things under `/var/lib`.

Once it's recovered, I restart only the services that were actually affected, check filesystem and application integrity, confirm monitoring is working, and fix retention or capacity so it can't silently happen again.

## 37. The `/` partition is full. How do you find and delete large files safely?

**Answer:**

I confirm the filesystem with `df -hT /` and inodes with `df -i /`, then stay on that same filesystem while I look for usage:

```bash
sudo du -xhd1 / 2>/dev/null | sort -h
sudo find / -xdev -type f -size +500M -printf '%s %p\n' 2>/dev/null | sort -nr | head
```

Before deleting anything, I check who owns it, when it was last modified, whether anything has it open, retention rules, and whether a mount is hiding data underneath it. Logs should normally go through `logrotate` or get safely reopened by the service, and application or database files need to follow the owner's own procedure.

I make the smallest cleanup that actually recovers space, confirm `df`, service health, and logs afterward, then set up rotation, quotas, alerts, or an expansion. I also check `lsof +L1` if `du` can't explain what `df` is reporting.

## 38. Deleted large files but disk space is not freeing up. Why?

**Answer:**

Linux removes the filename right away, but the actual data blocks stay allocated as long as any process still has the file open. I confirm this with:

```bash
sudo lsof +L1
```

The output shows the process, PID, file descriptor, and how much space it's holding onto. The safest fix is to reload or restart that service so it closes and reopens the file — for some daemons, a documented signal like `SIGHUP` is enough.

In an emergency, truncating through `/proc/<pid>/fd/<fd>` is possible but risky, and I'd only do it following an approved procedure. I confirm the space is freed with `df`, then fix the rotation setup so it properly signals the service next time.

## 39. What happens when a file is deleted but still open by a process?

**Answer:**

`unlink()` removes the directory entry, so new commands can't find the file by name anymore, but the inode and its data blocks stay around until the last open file descriptor closes. The process that has it open can keep reading or writing that data, and `df` still counts it as used space even though `du` can't see it.

I demonstrate or diagnose this with `lsof +L1` and by checking `/proc/<pid>/fd/<number>`, which usually shows `(deleted)`. To free it, I get the application to close the descriptor — normally through a graceful reload or restart.

This is also why replacing a deployed binary on disk doesn't automatically change the code a running process already has loaded in memory.

## 40. What is inode exhaustion and how do you resolve it?

**Answer:**

Every file and directory needs an inode.

A filesystem full of millions of tiny files can hit 100% inode usage while plenty of data blocks are still free — a new file then fails with "No space left on device." I check `df -i` and narrow down which directories have the most files, for example with `find /var -xdev -type f -printf '%h\n' | sort | uniq -c | sort -nr | head`.

I figure out what actually created all those files — sessions, a mail queue, a cache, container layers, or unrotated temp data — and clean it up using that system's own supported method.

For a lasting fix, I might move the workload, redesign how storage or objects are used, or rebuild the filesystem with an inode density suited to the workload — inode count generally can't be increased in place on ext filesystems.

I add monitoring for file count as well as bytes used.

## 41. Why do `df -h` and `du -sh` show different usage?

**Answer:**

`df` reads the filesystem's own allocation metadata, while `du` walks the visible directory tree and adds up what it finds. The most common cause of a big difference is a deleted-but-open file, which I check with `lsof +L1`.

Other causes: reserved blocks or metadata overhead, files hidden underneath a mount point, not having permission to see everything during the `du` scan, snapshots, or comparing two different filesystems by mistake.

I make sure both commands are looking at the same mount (`findmnt` and `du -x`), run `du` with enough permission, check for open-deleted files and snapshots, and check mount points. Sparse files can go the other way — `ls -l` can show a large size while the file actually takes up little space — and `du --apparent-size` explains that.

I fix whatever the actual cause turns out to be, rather than trusting either number blindly.

## 42. How do you check disk partitions and usage?

**Answer:**

I use a different command for each layer: `lsblk -f` shows disks, partitions, filesystems, UUIDs, and mount points. `df -hT` shows how full each mounted filesystem is. `findmnt` shows how things are mounted and with what options. `blkid` confirms filesystem identifiers. `fdisk -l` or `parted -l` shows the partition table.

For LVM, I also run `pvs`, `vgs`, and `lvs -a -o +devices` to see how physical volumes map to volume groups and logical volumes. Before changing anything, I write down this mapping and confirm the exact device by size, serial number, and path.

Cloud disk size, partition size, LVM size, filesystem size, and actual mounted capacity are all separate layers, and growing one doesn't automatically grow the others.

## 43. How do you extend a partition without unmounting it?

**Answer:**

I first confirm the layout and filesystem with `lsblk -f`, `findmnt`, and the LVM commands, take a backup or snapshot, and check that the filesystem actually supports growing while mounted. After the underlying cloud or virtual disk is expanded, a plain partition can sometimes be grown with `growpart /dev/sda 2`.

For LVM, a typical controlled flow is:

```bash
sudo pvresize /dev/sda2
sudo lvextend -L +10G /dev/vg0/data
sudo xfs_growfs /data              # XFS, use mount point
# or: sudo resize2fs /dev/vg0/data # ext4
```

The exact device names vary every time, so I never just paste commands without checking them against the real layout. I verify each layer afterward with `pvs`/`lvs`, `lsblk`, and `df -hT`. Shrinking is a very different, riskier operation, and XFS can't be shrunk in place at all.

## 44. What steps are needed to add a new disk to a Linux server?

**Answer:**

Once the platform attaches the disk, I identify it by serial number and size with `lsblk -o NAME,SIZE,TYPE,SERIAL,MOUNTPOINTS` — I never just assume it's `/dev/sdb`. I confirm it has no data on it that matters, create a GPT partition if needed, then set up the approved filesystem or add it to LVM.

I create the mount point, mount it temporarily, set ownership, and test that I can read and write to it. For it to survive a reboot, I use the filesystem's UUID from `blkid` in `/etc/fstab` rather than a device name that could change.

I validate with `findmnt --verify` and `mount -a` before actually rebooting, then confirm capacity and permissions. I also update backups, monitoring, and application configuration to cover the new location.

## 45. How do you mount and unmount filesystems in Linux?

**Answer:**

I create an empty mount point and mount it using the UUID with an explicit filesystem type and options, for example `mount -t xfs UUID=<uuid> /data`. I confirm with `findmnt /data`, test permissions, and only add a reviewed entry to `/etc/fstab` once the temporary mount is working.

`findmnt --verify` and `mount -a` catch fstab syntax errors before they cause problems at the next reboot.

Before running `umount /data`, I stop or redirect whatever applications are using it, and check `lsof +f -- /data` or `fuser -vm /data` if it says it's busy. I avoid lazy or forced unmounts unless I fully understand the risk of data loss or stale file handles.

After unmounting, I confirm it's gone from `findmnt` — writing beneath a mount point that isn't actually mounted, or leaving a stray mount point, can quietly fill up the root filesystem.

## 46. How do you create and mount a swap file?

**Answer:**

I first check `free -h`, `swapon --show`, how much disk space is available, and whether the workload or platform even supports a swap file. Then:

Example:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

I confirm it with `swapon --show` and `free -h`, then add `/swapfile none swap sw 0 0` to `/etc/fstab`. Mode `600` matters here, because swap can contain sensitive data that was in memory.

Swap can prevent a sudden OOM kill for some workloads, but it's much slower than RAM and isn't a substitute for fixing a memory leak or sizing memory correctly. I also pick and document an appropriate `vm.swappiness` value rather than changing it without evidence.

## 47. How do you remount a filesystem read-write without rebooting?

**Answer:**

If it was mounted read-only on purpose and the filesystem is healthy, I use `sudo mount -o remount,rw /mountpoint` and confirm with `findmnt -no OPTIONS /mountpoint`. If this needs to survive a reboot, I update `/etc/fstab` too.

But if the kernel remounted it read-only itself because of I/O or filesystem errors, forcing it back to read-write can make corruption worse. In that case I first check `journalctl -k`, storage or cloud health, and SMART data.

I fail over or stop writes, back up whatever is still readable, unmount or boot into rescue mode, run the proper filesystem repair tool, and only remount once the underlying storage problem is actually fixed.

## 48. How do you fix a corrupted filesystem using `fsck`?

**Answer:**

I confirm the exact device and filesystem type with `lsblk -f` and protect the data first. `fsck` is really a front end mainly for ext-family filesystems; XFS uses `xfs_repair` instead, and the filesystem normally needs to be unmounted first.

For the root filesystem, I boot into rescue or emergency mode, or attach the disk to a separate recovery host.

For ext4, I might first run a read-only check with `e2fsck -fn /dev/mapper/vg-lv`, review what it finds, then run the actual repair while it's unmounted. I avoid the automatic `-y` flag on valuable data unless the recovery plan is fine with that risk.

Afterward I mount it read-only first if that makes sense, check `lost+found`, validate the application's data, and look into whatever underlying disk, power, or kernel issue caused the corruption in the first place, rather than treating it as a one-off event.

## 49. How do you recover a deleted file in Linux?

**Answer:**

I stop or reduce writes right away, since new data can overwrite the blocks the deleted file used. My order of options is: the application's own recycle bin or version history, backups, a storage or LVM snapshot, a replica, and then an open file descriptor (`lsof +L1`) that might still let me copy from `/proc/<pid>/fd/<fd>` to another filesystem.

If none of that works, I unmount or snapshot the filesystem and do any forensic recovery on a copy, using filesystem-specific tools. Recovery isn't guaranteed, especially on SSDs with TRIM enabled, so I set that expectation up front and preserve the evidence.

Once I have a recovered file, I check it with a checksum or against the application, restore the correct owner and permissions, document the incident, and push for better tested backups and deletion controls.

## 50. A Linux server is not booting due to filesystem corruption. How do you recover it?

**Answer:**

I use console access to capture the exact boot error and tell the difference between real filesystem corruption and a bad `/etc/fstab` entry, a missing device, or a bootloader problem. I boot into recovery or rescue media, or attach the root disk to a helper host, map any encrypted or LVM volumes, and take a snapshot before doing any repair.

With the affected filesystems unmounted, I run the right checker — `e2fsck` for ext, `xfs_repair` for XFS — review the UUIDs and options in `/etc/fstab`, and check disk or platform health. I mount it read-only and check the critical files before bringing it back into service.

I only rebuild initramfs or the bootloader if the evidence points there, reboot through console, verify all mounts and services and application consistency, and restore from backup if the repair can't guarantee the data is intact.

## 51. How do you check disk I/O performance?

**Answer:**

I start with `iostat -xz 1`, `vmstat 1`, and `pidstat -d 1`. I compare throughput and IOPS against what the disk is actually rated for, and look at `await`, average queue size, utilization, and how much CPU time is spent waiting on I/O.

`iotop` helps pin down the exact process, and cloud metrics can reveal throttled IOPS or throughput, or exhausted burst credits.

High utilization by itself isn't necessarily bad — the real evidence is rising latency and actual application impact. I compare it against backups, queries, compaction jobs, deployments, and kernel or storage errors happening around the same time.

Fixes can include tuning a query or index, adding caching, moving batch jobs to a quieter time, separating data and log volumes onto different disks, provisioning more IOPS, or scaling up. I take a baseline and remeasure the same workload after making the change.

## 52. What is the fastest way to copy huge files across servers?

**Answer:**

The best method depends on the network, how much is changing, how many files there are, and whether any downtime is acceptable. For a large, resumable transfer I usually use:

```bash
rsync -aHAX --info=progress2 --partial source/ user@host:/data/destination/
```

Compression (`-z`) helps on a slower network if the data compresses well, but wastes CPU on data that's already compressed. I run an initial copy while the source is still live, then pause writes or take a snapshot, then run a final delta sync to catch up.

For cloud volumes, a snapshot, replication, or object storage might be faster and safer than a file copy. I estimate the bandwidth and disk space needed, protect any credentials involved, throttle the transfer if it would affect production, and verify file counts and checksums before cutting over.

## 53. What are hard links and soft links?

**Answer:**

A hard link is just another directory entry pointing at the same inode. Both names are equally valid references to the same file — deleting one name leaves the data available through the other.

Hard links normally can't cross filesystems or point at directories. `ls -li` shows the shared inode number and the link count.

A symbolic link is a small separate file that just contains a target path: `ln -s /opt/app/current app`. It can cross filesystems and point at a directory, but it becomes a dangling link if the target moves.

I use symlinks for switching between versioned releases, and hard links for certain backup or deduplication setups — keeping in mind that editing a hard-linked file changes the data everywhere it's linked, since it's all the same inode.

## 54. What is the difference between `find` and `locate`?

**Answer:**

`find` walks the actual directory tree right now, and can filter by name, type, owner, time, size, permissions, and filesystem, then safely act on what it finds. For example, `find /var/log -xdev -type f -mtime +30 -print` gives current, accurate matches, but it can take a while on a big tree.

`locate '*.conf'` instead queries an index that `updatedb` built earlier, so it's very fast, but it can list files that were since deleted, or miss files that were just created, and which paths are excluded depends on its configuration. I use `locate` for a quick look and confirm with `stat`; I use `find` when I need completeness, the current state, or need to act on the results.

Before running `find` with `-delete` or `-exec`, I always run the same expression with `-print` first to see exactly what it will touch.

## 55. What are runlevels or systemd targets?

**Answer:**

SysV runlevels represented boot modes — commonly 1 for single-user/rescue, 3 for multi-user text mode, 5 for graphical, and 0/6 for halt/reboot, though the exact meaning could vary by system. Systemd instead uses targets, which group units and their dependencies together — things like `rescue.target`, `multi-user.target`, and `graphical.target`.

I check the default with `systemctl get-default`, change it permanently with `systemctl set-default multi-user.target`, or switch the current boot state with `systemctl isolate ...`. `isolate` can stop services that aren't required by the target it switches to, so I use console access and understand the impact before doing it.

The old runlevel numbers map roughly onto targets, but systemd's dependency model is much richer than a single number.

## 56. You need to secure a Linux server exposed to the internet with a weak root password. What steps do you take?

**Answer:**

I treat this as a possible compromise, not just a hardening exercise. I restrict access at the cloud firewall to approved networks, preserve authentication and audit evidence, and review successful logins, user accounts, SSH keys, sudo changes, running processes, anything persistent, and outbound connections.

If I suspect it was actually compromised, I isolate it and rebuild from a trusted image rather than trying to clean it in place.

I rotate the root password and every reachable secret, create named admin accounts with least privilege — meaning only the access each person actually needs — sudo, and MFA or bastion access, test that the new access works, then set `PermitRootLogin no` and normally turn off password-based SSH entirely.

I patch the system, remove services that aren't needed, turn on the host firewall and SELinux, centralize logs, and enable something like fail2ban or an EDR tool where it fits, and confirm backups are working.

I make these changes with a second session or console open, so I don't lock administrators out by mistake.

## 57. `yum` or `apt` installation is failing. How do you troubleshoot?

**Answer:**

I read the actual error message first. I check disk space, inodes, and the system clock, then whether the repository is reachable over DNS, TLS, and any proxy, whether the configured release or version is right, and whether the GPG key is valid.

A lock error means another `apt`, `dpkg`, `dnf`, or `yum` process is already running — I find that process rather than deleting the lock file while a transaction is in progress.

On Debian-based systems I use `apt-get update`, `apt-cache policy`, `dpkg --audit`, and `dpkg --configure -a` if something got interrupted. On RHEL-based systems I use `dnf repolist -v`, `dnf makecache`, and `dnf history`.

I check the repository and package logs, resolve any held or broken dependencies deliberately, and never disable signature checks. Once it's fixed, I install the exact package, confirm its version and that the service works, and put the repository configuration back to what's approved.

## 58. How do you find the top 5 CPU-consuming and memory-consuming processes?

**Answer:**

For a snapshot I use:

```bash
ps -eo pid,ppid,user,%cpu,%mem,rss,etime,cmd --sort=-%cpu | head -n 6
ps -eo pid,ppid,user,%cpu,%mem,rss,etime,cmd --sort=-rss  | head -n 6
```

I sort memory by RSS, since `%mem` is derived from it and VSZ can include large chunks of memory that aren't actually resident. A single snapshot can catch a brief spike or miss one entirely, so I confirm with `pidstat 1`, `top`, or historical data from `sar`/`atop`.

I also map each PID back to its service or container and compare it against request rate and any recent changes before deciding a process is actually abnormal.

## 59. How do you check logs from the last 7 days?

**Answer:**

For systemd, I give it a precise time range and unit, for example:

```bash
journalctl -u nginx --since "2026-07-12 00:00:00" --until "2026-07-19 00:00:00" -o short-iso
```

For plain log files, I first find the current and rotated files under `/var/log`. Note that `find ... -mtime -7` filters by the file's modification time, not by individual log entries. I use `grep` on plain files and `zgrep` on `.gz` files, then filter further by timestamp format, request ID, host, or severity.

I account for timezone differences and log rotation boundaries, and export a read-only copy when I need to preserve evidence from an incident.

## 60. What command generates an SSH key?

**Answer:**

For a modern user key I use:

```bash
ssh-keygen -t ed25519 -a 100 -C "sunil@company-laptop-2026"
```

I put it in a protected path, set a strong passphrase, and use `ssh-agent` rather than leaving the private key unencrypted on disk. The `.pub` file gets shared; the private key never gets emailed, checked into a repository, or copied onto a server.

If policy or old compatibility requires RSA instead, I use RSA 3072 or 4096. I install the public key for the right account and test a second working session before removing any old access.

## 61. What do you do if a user loses an SSH private key?

**Answer:**

I treat the key as potentially compromised. Using a separate, approved admin path, I find and remove its exact public-key line from every `authorized_keys` file, bastion, Git service, and automation account that trusted it.

I check the authentication logs for that key's fingerprint or user, and rotate other secrets if the lost device could have exposed them too.

The user generates a new passphrase-protected key on a trusted device, and administrators only ever receive the public half. I add it with correct ownership and permissions, test that it works, and record who owns it, why, and when it expires.

I never try to reconstruct or send a replacement private key over any channel. Centralized SSH certificates or managed access make future revocation and expiry much easier to handle.

## 62. How will you change user access or privileges?

**Answer:**

I start from the approved role and the principle of least privilege — only granting what's actually needed: which systems, which commands, which files, and for how long. I prefer group-based access over one-off permissions for individual users.

For sudo, I create a narrow file under `/etc/sudoers.d/` using `visudo -f`, list the exact commands where practical, and avoid broad passwordless root access.

For data access, I use owner and group permission bits or ACLs (`setfacl`), and confirm with `namei -l` or `getfacl`. I test with `sudo -l -U user` and an actual, non-destructive command, keep an emergency admin session open, and log the ticket and expiry date.

When access is removed, I revoke the group membership, sudo rule, and key entries, end any active sessions if needed, and check that no alternate way to get that privilege was left open.

## 63. How do you list the top 10 largest files anywhere on a Linux system?

**Answer:**

For a quick, system-wide look I can use:

```bash
sudo find / -type f -exec du -h -- {} + 2>/dev/null | sort -hr | head -n 10
```

`find / -type f` walks files starting from root, `du -h` reports how much disk space each one actually uses in human-readable units, `sort -hr` puts the biggest first, and `head -n 10` keeps the top ten.

Redirecting stderr hides permission errors and noise from `/proc`, but during a formal investigation I might want to see those errors, since a path I couldn't read means the search wasn't actually complete.

Scanning all of `/` can be slow and can wander into NFS, container, backup, or other mounted filesystems. I usually start with `df -hT` to find the full filesystem, and search just that mount with `-xdev`, for example:

```bash
sudo find /var -xdev -type f -exec du -h -- {} + 2>/dev/null \
  | sort -hr | head -n 10
```

For the exact logical size with GNU tools, I can use `find ... -printf '%s\t%p\n' | sort -nr`; `du` instead reports allocated blocks, so sparse files can show a different number. Filenames containing newlines need a null-delimited or scripted approach instead.

Once I find a large file, I check it with `stat`, `file`, and `lsof`, and confirm the owner and retention policy. I don't delete it just because it's big.

## 64. How do you find which process is consuming the most memory?

**Answer:**

For a quick snapshot I use:

```bash
ps aux --sort=-%mem | head -n 11
```

The first line is the header, so `head -n 11` shows ten actual processes. For real investigation I prefer explicit columns sorted by resident memory:

```bash
ps -eo pid,ppid,user,%mem,rss,vsz,etime,cmd --sort=-rss | head -n 11
```

RSS is the physical memory the process actually has resident right now; VSZ includes virtual mappings and can look large without meaning real memory pressure. `%MEM` is fine for a quick comparison, but a single snapshot doesn't tell you if usage is growing.

I confirm system-wide pressure with `free -h`, `vmstat 1`, swap activity, and OOM evidence from `journalctl -k | grep -i oom`. Then I map the PID to its systemd service, container, or application, and watch it with `pidstat -r -p <pid> 1` or a runtime-specific tool.

Before restarting or killing anything, I capture logs and heap or thread diagnostics where relevant, confirm the actual user impact, and try graceful service control first. The permanent fix might be correcting a memory leak, tuning a cache or heap setting, setting resource limits, scaling traffic, or adding capacity.

## 65. How do you find the process using the most CPU right now?

**Answer:**

I take a snapshot first, then confirm the pattern holds over time:

```bash
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head -n 11
top -o %CPU
pidstat -u 1
```

I check the load average, CPU steal time, I/O wait, recent deployments, and traffic before acting. High load doesn't necessarily mean the CPU itself is saturated — tasks blocked on I/O can drive load up too.

I capture the PID, its service or container owner, and its logs, then mitigate it safely — scaling, rolling back, rate-limiting, or gracefully restarting whichever workload turns out to actually be the problem.

## 66. What does `chmod 754` set?

**Answer:**

It sets `rwxr-xr--`: the owner can read, write, and execute (7); the group can read and execute (5); everyone else can only read (4). On a directory, execute means being able to enter or access entries inside it, so someone with only read permission can list the names in it but can't actually go into it.

I check the target and its current permissions with `ls -ld`, avoid making sensitive files world-readable, and use groups or ACLs when plain mode bits aren't precise enough.

## 67. What is the difference between `kill -15` and `kill -9`?

**Answer:**

`kill -15` sends SIGTERM, which an application can catch and handle — stop accepting new work, flush its state, close connections cleanly. `kill -9` sends SIGKILL — the kernel stops the process immediately, and it gets no chance to clean up.

I start with SIGTERM, look into why shutdown is taking too long if it is, and only reach for SIGKILL when the process is genuinely stuck and I understand what an abrupt stop will cost. Neither one should be used carelessly on a database or other critical service.

## 68. How do you find and stop a process listening on port 8080?

**Answer:**

```bash
sudo ss -ltnp '( sport = :8080 )'
sudo lsof -nP -iTCP:8080 -sTCP:LISTEN
sudo systemctl stop <service-name>
```

I identify which service owns the port before stopping it — killing a bare PID can just get it recreated by a supervisor, and can interrupt users unexpectedly. If no service unit owns it, I use `kill -TERM <pid>`, confirm the listener is actually gone, and only escalate to `KILL` if it doesn't respond.

I also check containers (`docker ps` or `crictl ps`) and firewall or proxy configuration, since a port being reachable doesn't prove the application behind it is healthy.

## 69. A disk is 95% full. How do you find what is consuming space?

**Answer:**

I first identify the full filesystem with `df -hT`, then look only at that mount so another filesystem doesn't skew the result:

```bash
sudo du -xhd1 /var | sort -h
sudo find /var -xdev -type f -size +500M -printf '%s %p\n' | sort -nr | head
sudo lsof +L1
```

The last command finds deleted-but-open files, a common reason `du` and `df` disagree. I check logs, package caches, container images and volumes, temp files, snapshots, and inode usage (`df -i`).

I preserve the evidence and apply retention, rotation, resizing, or a controlled cleanup — I don't delete unknown production data just to make an alert go away.

## 70. How do you investigate a service crash using system logs?

**Answer:**

I establish which service, which host, and the exact failure window, then use `systemctl status <service>`, `journalctl -u <service> --since '30 minutes ago'`, and `journalctl -k` for kernel or OOM evidence. I compare the exit code, restart count, and any configuration, deployment, dependency, or resource changes around that time.

If it makes sense, I validate the configuration and try to reproduce it safely in a lower environment. After fixing it with a rollback, a targeted configuration change, or added capacity, I confirm the health checks pass and add an actionable alert or runbook for that failure mode.

## 71. Package manager versus compiling from source: when do you use each?

**Answer:**

I prefer the supported `apt`, `dnf`, or `yum` package, because it gives dependency management, signed updates, an inventory of what's installed, security patches, and a clean way to remove it later.

I only compile from source when a needed feature or version isn't available in the approved repositories, and whoever owns the system accepts the extra burden of patching it, knowing where the build came from and how it was built, keeping the build reproducible, and being able to roll it back.

For production, I package the build myself or use a trusted repository, rather than leave untracked binaries sitting under `/usr/local`.

## 72. The server has high load and an application reports "disk full", but `df -h` shows free space. What do you check?

**Answer:**

I check for inode exhaustion with `df -i`, since millions of small files can use up every inode while data blocks are still free.

I also check the actual mount namespace (`findmnt`, or the container's own namespace), quotas, a separate filesystem like `/tmp` that might be full on its own, filesystem errors or remount-read-only messages in `dmesg`, and deleted-but-open files with `lsof +L1`.

High load can also just be I/O wait from a storage problem rather than actual CPU work, so I check `iostat`, `vmstat`, latency and error metrics, and kernel logs. I fix the specific constraint I find, confirm the application can write again and what actually caused it, then set alerts for both bytes and inode usage.

## 73. Walk through the Linux boot process from firmware to login.

**Answer:**

Firmware — BIOS or UEFI — initializes the hardware and picks a boot device. The bootloader, usually GRUB, loads the chosen kernel and initramfs.

The kernel initializes drivers, mounts the initial root filesystem, and starts PID 1, normally systemd. Systemd then mounts the remaining filesystems, starts services and targets in the right order, and brings up a console or display manager.

If boot fails, I use the bootloader's options, the emergency or rescue target, `journalctl -b`, kernel messages, filesystem checks, and a look at any recent configuration changes.

I keep a known-good kernel and a rescue path available before changing any boot configuration.
