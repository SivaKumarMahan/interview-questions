# Linux: Fundamentals and Overview

> What Linux is, the filesystem hierarchy, the boot process, a map of the core areas, everyday commands, and cross-topic scenario flows and best practices.

## Key Concepts

### Core Areas

- **Files/navigation:** `pwd`, `ls`, `cd`, `mkdir`, `cp`, `mv`, `touch`, `cat`, `less`, and cautious removal.
- **System information:** date/time, uptime/load, logged-in users, kernel/CPU/memory, filesystem and directory usage.
- **Processes:** `ps`, `top`, `pidstat`, signals, process states, parent/child relationships, and service ownership.
- **Permissions:** owner/group/other, read/write/execute, `chmod`, `chown`, ACLs, `sudo`, and safe account management.
- **Archives:** `tar` create/list/extract with gzip/bzip2/xz where appropriate.
- **Networking:** DNS, route, TCP/TLS, SSH, listening sockets, and packet/path investigation.
- **Services/logs:** `systemd` status/start/stop/reload, `journalctl`, application logs, log rotation, and boot history.

### Why Linux Matters in DevOps

Linux is widely used for production servers, container hosts and cloud workloads, although Windows and other operating systems also remain important. DevOps engineers need command-line investigation skills because most servers are managed remotely without a graphical interface.

The sections below cover the areas that come up daily in production: process management, networking, filesystem navigation, permissions, disk usage, search and filtering, package management, system configuration, monitoring, and service management.

### Operating Systems and Virtualization

An operating system sits between applications and hardware. It schedules processes, manages physical and virtual memory, provides filesystems and device drivers, and enforces identity and access controls.

Linux is common in servers, containers, cloud platforms and automation because it is scriptable, stable and supported by a large open-source ecosystem.

Virtualization lets multiple isolated virtual machines share one physical host:

- A **Type 1 hypervisor** runs directly on hardware. Examples include VMware ESXi and Hyper-V in its bare-metal role.
- A **Type 2 hypervisor** runs as an application on a host OS. Examples include VirtualBox and VMware Workstation.

VMs give OS-level isolation and can be snapshotted, but a snapshot is not an independent backup. Before relying on a VM snapshot for deployment protection, confirm application consistency, retention, storage impact and restore behavior.

Production recovery still needs backups kept somewhere that would not fail along with the primary system, plus tested restoration.

### Linux Filesystem Hierarchy

| Path | Typical purpose |
|---|---|
| `/` | Root of the filesystem hierarchy |
| `/boot` | Bootloader, kernel and boot-related files |
| `/dev` | Device nodes |
| `/etc` | System and service configuration |
| `/home` | Regular users' home directories |
| `/opt` | Optional or third-party application trees |
| `/run` | Volatile runtime state |
| `/tmp` | Temporary files; cleanup behavior is distribution-specific |
| `/usr` | Most user-space programs, libraries and shared data |
| `/var` | Variable data such as logs, queues, caches and databases |

Modern distributions often merge `/bin`, `/sbin` and `/lib` into `/usr` using symbolic links. Common local filesystems include ext4, XFS and Btrfs. The best choice depends on distribution support, workload, and your recovery and snapshot requirements.

Inspect mounts and devices with:

```bash
findmnt
lsblk -f
df -hT
df -i
```

Do not assume `/tmp` is always cleared on reboot, and do not manually delete unfamiliar content from `/var` to solve disk pressure.

### Daily operations

```bash
# Process monitoring
ps aux | grep python                  # Find Python processes
top -p $(pgrep nginx)                 # Monitor specific processes
htop                                  # Interactive process manager

# Network debugging
ss -tulpn | grep :80                  # Check web server port
ping -c 3 database-server             # Test connectivity
curl -I https://api.example.com       # Check API health

# File operations
tail -f /var/log/app.log              # Follow application logs
find /var/log -name "*.log" -mtime -1 # Today's log files
grep -r "ERROR" /var/log/ | tail -10  # Recent errors

# System health
df -h                                 # Disk space check
free -h                               # Memory usage
systemctl status docker               # Service status
```

### Scenario Flow

| Scenario | What to check |
|---|---|
| Disk at 100% | Filesystem and inode pressure, the largest directories and files, files that are deleted but still held open by a process, log or journal growth, package or container caches, and which application owns the growth. Free only data you've confirmed is safe to remove, restore some headroom, then add retention and capacity alerts. |
| Slowness or high CPU | Load average, CPU mode breakdown, memory and swap, I/O wait, disk latency, network, the top processes and threads, application logs, recent changes, traffic, and dependencies. Only kill a process or reboot after identifying the cause and the risk — treat it as containment, not a fix. |
| Unresponsive system | Use console or out-of-band access. Check load, processes stuck in `D` state, memory pressure and OOM events, I/O, kernel logs, the filesystem, and hardware or cloud platform health. |
| Configuration change not taking effect | Validate syntax, confirm which config path is actually active, compare the rendered configuration against the live one, reload or restart safely, then check service logs. |
| User or permission change | Use approved identity processes, grant only the permissions actually needed, set correct group and ACL ownership, and verify as the target account. Avoid scripts that embed default passwords or grant `sudo` automatically. |

Never copy broad `rm -rf` examples from a cheat sheet straight into production.

### Best Practices That Will Save Your Career

1. **Always backup before making changes.**

   ```bash
   cp config.yaml config.yaml.backup
   ```

2. **Test commands safely first.**

   ```bash
   # Test what files will be deleted
   find /tmp -name "*.tmp" -type f
   # Then actually delete them
   find /tmp -name "*.tmp" -type f -delete
   ```

3. **Manage configuration through reviewed version control or configuration management.** Avoid casually running `git init` across `/etc` — it can capture secrets and misleading generated state. Tools such as Ansible, or a carefully configured `etckeeper` setup, are safer patterns.

4. **Monitor logs in real-time during deployments.**

   ```bash
   # One terminal for deployment
   sudo systemctl restart myapp
   # Another terminal for monitoring
   tail -f /var/log/myapp.log
   ```

5. **Learn keyboard shortcuts.**

   - `Ctrl+C`: Cancel current command
   - `Ctrl+Z`: Suspend current command
   - `Ctrl+R`: Search command history
   - `Tab`: Auto-complete commands and paths

## Interview Questions

<details><summary>Q1. [Basic] Do you have hands-on Linux experience? Which platform?</summary>

**Answer:**

I answer honestly, naming the platforms, how long I worked with them, and what I actually did. For example: "I have administered Ubuntu and RHEL/Amazon Linux application servers. My work included systemd services, user and sudo and SSH setup, package patching, filesystems and LVM, network and DNS and firewall checks, cron jobs, logs, performance troubleshooting, hardening, backups, and CI/CD deployment."

Then I give a real example. Once a disk filled up because logs were not being rotated. I found the filesystem and the open files, safely freed up space, checked that the application could still write, and then added log rotation plus alerts at 70% and 85% full. This shows I actually investigated the problem, not just that I can name a few distributions.

I also make clear which tasks I owned myself versus which were handled by a managed service or a separate cloud team.

</details>

<details><summary>Q2. [Basic] What are common Linux commands you use?</summary>

**Answer:**

I group commands by what they're for. For files: `ls`, `find`, `cp`, `mv`, `stat`. For text and logs: `less`, `grep`, `awk`, `sed`, `tail`. For processes: `ps`, `top`, `pidstat`, `kill`. For resource checks: `free`, `vmstat`, `df`, `du`, `iostat`. For network: `ip`, `ss`, `dig`, `curl`, `nc`. For services: `systemctl`, `journalctl`. For permissions: `chmod`, `chown`, `getfacl`. And for transferring or archiving data: `rsync`, `scp`, `tar`.

I use them carefully. I quote file paths, gather read-only evidence before changing anything, use `--` before an untrusted filename, look at what a recursive or delete command will touch before running it, and keep a record of commands and their output during an incident. I pick a command to test one specific idea. Running a pile of commands without understanding what they show is not troubleshooting.

</details>

<details><summary>Q3. [Intermediate] Walk through the Linux boot process from firmware to login.</summary>

**Answer:**

Firmware — BIOS or UEFI — initializes the hardware and picks a boot device. The bootloader, usually GRUB, loads the chosen kernel and initramfs.

The kernel initializes drivers, mounts the initial root filesystem, and starts PID 1, normally systemd. Systemd then mounts the remaining filesystems, starts services and targets in the right order, and brings up a console or display manager.

If boot fails, I use the bootloader's options, the emergency or rescue target, `journalctl -b`, kernel messages, filesystem checks, and a look at any recent configuration changes.

I keep a known-good kernel and a rescue path available before changing any boot configuration.

</details>
