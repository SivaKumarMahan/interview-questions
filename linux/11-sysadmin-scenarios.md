# Linux: System Administration Scenarios

> Practical sysadmin scenarios: who is logged in, services that fail or hang, inaccessible mounts, process signals and job control, restricting root, auditing file changes, safe reboots, swap, socket states, per-user resource limits, slow boots, DNS problems, and log rotation.

## Key Concepts

### Process signals

| Signal | Number | Sent by | Effect |
| --- | --- | --- | --- |
| `SIGHUP` | 1 | `kill -HUP <PID>` | Many daemons reload their configuration |
| `SIGINT` | 2 | `Ctrl+C` | Interrupt the foreground program |
| `SIGQUIT` | 3 | `Ctrl+\` | Quit and write a core dump |
| `SIGKILL` | 9 | `kill -9 <PID>` | Kernel stops the process immediately; cannot be caught, no cleanup |
| `SIGTERM` | 15 | `kill <PID>`, `systemctl stop` | Ask the process to exit cleanly (default for `kill`) |
| `SIGCONT` | 18 | `fg`, `bg`, `kill -CONT <PID>` | Continue a stopped process |
| `SIGSTOP` | 19 | `kill -STOP <PID>` | Pause the process; cannot be caught |
| `SIGTSTP` | 20 | `Ctrl+Z` | Pause from the terminal; can be caught |

Numbers are for Linux on x86 and ARM. Always prefer `SIGTERM` over `SIGKILL`, so the application can flush buffers, release locks and close database connections.

### Job control

```bash
long_task &        # start in the background; prints [1] <PID>
jobs -l            # list jobs of this shell with PIDs
fg %1              # bring job 1 to the foreground
Ctrl+Z             # pause the foreground job
bg %1              # continue job 1 in the background
kill %1            # SIGTERM to job 1
nohup long_task > out.log 2>&1 &   # keep running after logout (or use tmux / a systemd unit)
```

### Key places and tools

| Need | Tool |
| --- | --- |
| Logins and sessions | `w`, `who`, `last`, `lastb`, `loginctl` |
| Service state and logs | `systemctl status`, `journalctl -xeu <service>` |
| Validate config before restart | `nginx -t`, `apachectl configtest`, `sshd -t`, `named-checkconf`, `promtool check config` |
| File change auditing | `stat`, `auditd` (`auditctl`, `ausearch`) |
| Sockets | `ss -s`, `ss -tan`, `ss -tulpn` |
| Per-user limits | `/etc/security/limits.conf`, systemd slices (`CPUQuota`, `MemoryMax`) |
| Boot time | `systemd-analyze`, `blame`, `critical-chain` |

## Interview Questions

<details><summary>Q1. [Basic] Several users are logged in. How do you check who is logged in and from where?</summary>

**Answer:**

```bash
w                     # users, terminal (pts/0), source IP, login time, idle time, current command
who                   # shorter list of sessions
last -a | head -n 10  # recent logins with the remote host in the last column
lastb | head          # failed login attempts (needs sudo)
loginctl list-sessions
```

`w` is the most useful because it also shows what each user is running right now. `last` reads `/var/log/wtmp` and `lastb` reads `/var/log/btmp`. To end a session: `sudo pkill -KILL -t pts/1` or `sudo loginctl terminate-session <id>`.

</details>

<details><summary>Q2. [Intermediate] After you edit a configuration file, the service won't start. How do you troubleshoot and recover?</summary>

**Answer:**

1. **Read the exact error:**

   ```bash
   systemctl status nginx
   journalctl -xeu nginx --since "10 min ago"
   ```

   This usually shows the file and line number of the problem.
2. **Run the service's own validator:** `nginx -t`, `apachectl configtest`, `sshd -t`, `named-checkconf`, `haproxy -c -f <file>`.
3. **Compare with the last working version:** `diff /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf`, or `git diff` if the configuration is managed in Git.
4. **Recover fast:** restore the backup and start the service, then fix the change calmly.

   ```bash
   sudo cp /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf
   sudo systemctl restart nginx
   ```

5. If the **unit file** itself was changed, run `sudo systemctl daemon-reload` first.

**Prevention:** always back up or version the file before editing, validate before restarting, and use `reload` instead of `restart` where the service supports it, so a bad config does not take the running service down. In production, configuration should come from Ansible or Git with a validation step in the pipeline.

</details>

<details><summary>Q3. [Intermediate] A filesystem is mounted but not accessible. What could be the reasons?</summary>

**Answer:**

| Possible cause | How to check | Fix |
| --- | --- | --- |
| Permissions or ownership on the mount point | `ls -ld /data`, `id <user>`, `getfacl /data` | `chown` / `chmod` or ACLs for the right group |
| Remounted read-only after disk errors | `findmnt /data` shows `ro`, `dmesg -T \| tail -30` shows I/O or filesystem errors | Find the cause, then repair and remount |
| Stale NFS or SMB mount | `ls` hangs, "Stale file handle"; `showmount -e <server>`, `df -hT` hangs | Fix the server or network, then `umount -f` or `umount -l` and mount again |
| Filesystem full or out of inodes | `df -h /data`, `df -i /data` | Free space or inodes |
| Something mounted on top | `findmnt -R /data` | Unmount the extra mount |
| SELinux context | `ls -Z /data`, `ausearch -m avc` | `restorecon -R /data` or the correct `semanage fcontext` |
| `noexec` option | `findmnt -o OPTIONS /data` | Remount without `noexec` if executables must run there |

To repair corruption, **unmount first** and only then run `fsck` (or `xfs_repair` for XFS). Never run `fsck` on a mounted filesystem. `umount -l` is a *lazy* unmount that only detaches the path; it does not make the filesystem safe to check.

</details>

<details><summary>Q4. [Intermediate] A service is running but not responding. How do you troubleshoot it?</summary>

**Answer:**

1. **Is it really running and listening?** `systemctl status app`, `ss -tulpn | grep <port>`, `curl -v localhost:<port>/health`.
2. **Resources:** `top -p <PID>` or `pidstat -p <PID> 1` for CPU and memory, `free -h`, `df -h`. A process at 100% CPU may be in a busy loop; one at 0% CPU may be blocked.
3. **What is it waiting on?**

   ```bash
   cat /proc/<PID>/status | grep State   # D = waiting on I/O (uninterruptible)
   sudo strace -f -p <PID> -s 99         # live system calls: stuck on read, connect, futex?
   sudo lsof -p <PID>                    # open files, sockets, database connections
   ```

4. **Thread state for runtimes:** `jstack <PID>` for Java (deadlocks, exhausted thread pools), `py-spy dump --pid <PID>` for Python.
5. **Dependencies:** database, cache, DNS, downstream API timeouts in the application logs (`journalctl -u app`).
6. **Recover:** take a thread dump or core first if possible (evidence for the root cause), then `systemctl restart app`. Add a health check so systemd, the load balancer or Kubernetes restarts it automatically next time.

</details>

<details><summary>Q5. [Basic] What is the difference between terminating, killing, stopping and continuing a process? How do you stop foreground and background processes?</summary>

**Answer:**

| Action | Signal | What happens |
| --- | --- | --- |
| Terminate | `SIGTERM` (15): `kill <PID>` | Polite request; the process can clean up and exit |
| Kill | `SIGKILL` (9): `kill -9 <PID>` | Kernel removes it immediately; no cleanup, possible data loss |
| Stop (pause) | `SIGSTOP` (19) or `Ctrl+Z` (`SIGTSTP`) | Process stays in memory with the same PID but gets no CPU |
| Continue | `SIGCONT` (18): `fg`, `bg`, `kill -CONT <PID>` | A stopped process runs again |

**Foreground process:** `Ctrl+C` sends `SIGINT`. If it ignores that, `Ctrl+\` sends `SIGQUIT` (which also writes a core dump), or open another terminal and use `kill`.

**Background process:**

```bash
jobs -l                     # jobs started from this shell
kill %1                     # by job number
pgrep -af myscript          # find the PID of any process by name
kill <PID>                  # try SIGTERM first
pkill -f myscript           # by command-line pattern (check with pgrep -af first)
kill -9 <PID>               # only if it does not exit after SIGTERM
```

A process in state `D` (waiting for disk or NFS) cannot be killed even with `-9` until the I/O returns.

</details>

<details><summary>Q6. [Intermediate] How do you prevent a user from switching to root?</summary>

**Answer:**

1. **Remove sudo rights:** take the user out of the admin group and check for direct rules.

   ```bash
   sudo gpasswd -d john sudo        # Ubuntu; the group is "wheel" on RHEL
   sudo grep -r john /etc/sudoers /etc/sudoers.d/
   sudo -l -U john                  # what john can still run
   ```

2. **Restrict `su` to the wheel group:** in `/etc/pam.d/su`, enable

   ```text
   auth required pam_wheel.so use_uid
   ```

   Now only members of `wheel` can use `su`, even if they know the root password.
3. **Lock the root password and block root SSH:** `sudo passwd -l root` and `PermitRootLogin no` in `sshd_config`.
4. **Watch for indirect root:** sudo rules that allow editors, shells or `find -exec` (for example `sudo vim` can spawn a shell), and membership of the `docker` group, which gives root-equivalent access.
5. For service accounts that should never log in: `sudo usermod -s /usr/sbin/nologin svc_app`.

</details>

<details><summary>Q7. [Intermediate] A file was changed unexpectedly. How do you find out when and by whom?</summary>

**Answer:**

1. **When:** `stat /etc/app.conf` shows:
   - **Modify** (mtime): when the content last changed.
   - **Change** (ctime): when the content or metadata (permissions, owner) last changed. It is not the creation time, and it cannot be set by `touch`, so it is harder to fake.
   - **Access** (atime): last read (often not updated, because of `relatime`).
2. **Who, if auditing was enabled:** `auditd` records the user, process and time.

   ```bash
   sudo auditctl -w /etc/app.conf -p wa -k app-conf    # watch writes and attribute changes
   sudo ausearch -k app-conf -i                         # who changed it, with which command
   ```

   Make the rule permanent in `/etc/audit/rules.d/`.
3. **Without auditd:** match the mtime against `last` (who was logged in), `journalctl _COMM=sudo` or `/var/log/auth.log` / `/var/log/secure` (sudo commands), users' `.bash_history`, configuration management runs (Ansible, Puppet, Chef), and recent package updates (`/var/log/dpkg.log`, `dnf history`).
4. **Prevent it:** put important configuration under Git or Ansible so every change is reviewed, and add file integrity monitoring (auditd rules, AIDE, or Defender for Servers / Wazuh).

</details>

<details><summary>Q8. [Intermediate] After patching, a reboot is required. How do you check that, and how do you reboot safely?</summary>

**Answer:**

1. **Is a reboot needed?** Ubuntu: `/var/run/reboot-required` exists. RHEL: `needs-restarting -r`. Check uptime with `uptime` or `uptime -s`.
2. **Prepare:** take the server out of the load balancer or drain the node (`kubectl drain` for a Kubernetes node), confirm backups or a snapshot, and inform users or the change ticket.
3. **Warn logged-in users and schedule:**

   ```bash
   sudo wall "Server rebooting in 5 minutes for patching. Please save your work."
   sudo shutdown -r +5 "Post-patch maintenance reboot"
   sudo shutdown -c          # cancel if needed
   ```

4. **Verify after the reboot:** `uname -r` shows the new kernel, `systemctl --failed` is empty, applications respond to health checks, then add the server back to the load balancer.
5. Patch servers in batches (one availability zone or one VMSS update domain at a time), so the service stays up.

</details>

<details><summary>Q9. [Basic] How do you make a service start automatically after a reboot?</summary>

**Answer:**

```bash
sudo systemctl enable nginx          # create the boot-time link
sudo systemctl enable --now nginx    # enable and start immediately
systemctl is-enabled nginx           # enabled / disabled / masked
systemctl is-active nginx
```

For your own application, create a unit file such as `/etc/systemd/system/myapp.service` with `Restart=on-failure` and `WantedBy=multi-user.target`, then run `sudo systemctl daemon-reload` and `sudo systemctl enable --now myapp`.

On old SysVinit systems the equivalents were `chkconfig myapp on` (RHEL 6) and `update-rc.d myapp enable` (old Debian and Ubuntu).

</details>

<details><summary>Q10. [Intermediate] How do you check swap usage and whether swapping hurts performance?</summary>

**Answer:**

```bash
free -h                      # total and used swap
swapon --show                # swap devices and files
vmstat 1 5                   # si / so columns: memory swapped in / out per second
grep VmSwap /proc/*/status 2>/dev/null | sort -k2 -n | tail   # which processes are in swap
cat /proc/sys/vm/swappiness  # default 60
```

- Some used swap with `si` and `so` near zero is fine: idle memory was moved out once.
- Continuous non-zero `si` and `so` means the server is **thrashing**: it is short of RAM and performance drops sharply.

Fixes: find the memory-hungry process, add RAM or resize the VM, fix memory leaks, or set memory limits. Lower swappiness for latency-sensitive servers:

```bash
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
```

Kubernetes nodes traditionally run without swap, so the kubelet's memory limits and evictions behave predictably.

</details>

<details><summary>Q11. [Advanced] A server is hitting its connection limits. How do you analyse socket connection states?</summary>

**Answer:**

```bash
ss -s                                              # summary: total, TCP established, timewait
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn   # count per state
ss -tn state established '( dport = :443 or sport = :443 )' \
  | awk 'NR>1 {print $4}' | cut -d: -f1 | sort | uniq -c | sort -rn | head   # top peers
```

How to read the states:

| Many sockets in | Usually means | Action |
| --- | --- | --- |
| `ESTABLISHED` | Real load, or slow clients holding connections | Scale out, add keep-alive limits, check for one abusive client |
| `TIME_WAIT` | Many short connections closed by this host | Use connection pooling and keep-alive; widen `net.ipv4.ip_local_port_range`; `net.ipv4.tcp_tw_reuse=1` for outbound connections |
| `CLOSE_WAIT` | The **application** did not close sockets after the peer closed them | Application bug (connection leak); fix the code, restart as a workaround |
| `SYN-RECV` | SYN flood or a backlog that is too small | Check `net.core.somaxconn`, SYN cookies, and DDoS protection |

Also check the process file-descriptor limit (`cat /proc/<PID>/limits`), because every socket uses a file descriptor.

</details>

<details><summary>Q12. [Advanced] How do you stop one user from consuming all CPU and memory on a shared server?</summary>

**Answer:**

**1. PAM limits** (per login session) in `/etc/security/limits.conf` or `/etc/security/limits.d/`:

```text
john  hard  nproc   1000    # max processes
john  hard  nofile  4096    # max open files
```

These apply at the next login. They limit counts, not CPU percentage or RAM.

**2. systemd and cgroups** (real CPU and memory limits for everything the user runs):

```bash
id -u john                                                 # for example 1001
sudo systemctl set-property user-1001.slice CPUQuota=200% MemoryMax=4G
systemd-cgtop                                              # live usage per slice
```

`CPUQuota=200%` means at most two CPU cores. For services, set `CPUQuota=`, `MemoryMax=` and `TasksMax=` in the unit file.

**3. Short term:** `renice +10 -u john` lowers the priority of the user's processes.

On shared build servers, the better long-term fix is isolation: separate agents, containers with resource limits, or Kubernetes requests and limits.

</details>

<details><summary>Q13. [Intermediate] The server boots slowly. How do you find out why?</summary>

**Answer:**

```bash
systemd-analyze                    # time in firmware, loader, kernel and userspace
systemd-analyze blame | head -15   # units ranked by start-up time
systemd-analyze critical-chain     # the chain of units that actually delayed boot
systemd-analyze plot > boot.svg    # visual timeline
journalctl -b -p warning           # warnings from this boot
```

Common causes: `NetworkManager-wait-online` or `systemd-networkd-wait-online` waiting for a network that never comes up, an `/etc/fstab` entry for a missing disk or NFS share (use `nofail` and `_netdev`), `cloud-init` on cloud VMs, DNS timeouts, and services with long start timeouts. A unit that takes long in `blame` is a problem only if it also appears in `critical-chain`.

</details>

<details><summary>Q14. [Intermediate] How do you troubleshoot DNS resolution problems on a Linux server?</summary>

**Answer:**

1. **Reproduce the way the application resolves:** `getent hosts api.example.com` (uses `/etc/nsswitch.conf`, so it checks `/etc/hosts` first).
2. **Query DNS directly:** `dig api.example.com`, `nslookup api.example.com`.
3. **Check which DNS server is used:** `cat /etc/resolv.conf`, and on systemd-resolved systems `resolvectl status` (the `127.0.0.53` address in `resolv.conf` is only a local stub).
4. **Compare with a specific server:** `dig @10.0.0.4 api.example.com`, `dig @168.63.129.16 ...` in Azure. If one server answers and another doesn't, the problem is forwarding or the server.
5. **Look for overrides:** a stale entry in `/etc/hosts`, a wrong `search` domain, or a private DNS zone not linked to the VNet or VPC (private endpoints resolving to public IPs).
6. **Network to DNS:** port 53 UDP and TCP allowed by firewalls (`nc -zvu <dns-ip> 53`).
7. **Caching:** `resolvectl flush-caches`, and remember that applications such as Java cache DNS themselves.

</details>

<details><summary>Q15. [Intermediate] How do you clean up or rotate logs without affecting running services?</summary>

**Answer:**

Use **logrotate** instead of deleting files by hand. Deleting a log that a process still has open does not free the space (the process keeps writing to the deleted file).

`/etc/logrotate.d/myapp`:

```text
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    maxsize 500M
    postrotate
        systemctl reload myapp > /dev/null 2>&1 || true
    endscript
}
```

- Use `postrotate` with a reload (or `kill -HUP`) when the application can reopen its log file.
- Use `copytruncate` only when it cannot: logrotate copies the file and truncates the original, which can lose a few lines written during the copy.
- Test with `sudo logrotate -d /etc/logrotate.d/myapp` (dry run) and force once with `-f`.

For an emergency, truncate instead of deleting: `sudo truncate -s 0 /var/log/myapp/app.log`. If a large file was already deleted while still open, find it with `sudo lsof +L1` and either restart the process or truncate it through `/proc/<PID>/fd/<FD>`. Limit the systemd journal with `journalctl --vacuum-size=1G` or `SystemMaxUse=` in `journald.conf`.

</details>
