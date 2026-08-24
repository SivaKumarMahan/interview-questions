# Linux Operations Summary

## Core Areas

- **Files/navigation:** `pwd`, `ls`, `cd`, `mkdir`, `cp`, `mv`, `touch`, `cat`, `less`, and cautious removal.
- **System information:** date/time, uptime/load, logged-in users, kernel/CPU/memory, filesystem and directory usage.
- **Processes:** `ps`, `top`, `pidstat`, signals, process states, parent/child relationships, and service ownership.
- **Permissions:** owner/group/other, read/write/execute, `chmod`, `chown`, ACLs, `sudo`, and safe account management.
- **Archives:** `tar` create/list/extract with gzip/bzip2/xz where appropriate.
- **Networking:** DNS, route, TCP/TLS, SSH, listening sockets, and packet/path investigation.
- **Services/logs:** `systemd` status/start/stop/reload, `journalctl`, application logs, log rotation, and boot history.

## Operating Systems and Virtualization

An operating system sits between applications and hardware. It schedules processes, manages physical and virtual memory, provides filesystems and device drivers, and enforces identity and access controls.

Linux is common in servers, containers, cloud platforms and automation because it is scriptable, stable and supported by a large open-source ecosystem.

Virtualization lets multiple isolated virtual machines share one physical host:

- A **Type 1 hypervisor** runs directly on hardware. Examples include VMware ESXi and Hyper-V in its bare-metal role.
- A **Type 2 hypervisor** runs as an application on a host OS. Examples include VirtualBox and VMware Workstation.

VMs give OS-level isolation and can be snapshotted, but a snapshot is not an independent backup. Before relying on a VM snapshot for deployment protection, confirm application consistency, retention, storage impact and restore behavior.

Production recovery still needs backups kept somewhere that would not fail along with the primary system, plus tested restoration.

## Linux Filesystem Hierarchy

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

## Scenario Flow

| Scenario | What to check |
|---|---|
| Disk at 100% | Filesystem and inode pressure, the largest directories and files, files that are deleted but still held open by a process, log or journal growth, package or container caches, and which application owns the growth. Free only data you've confirmed is safe to remove, restore some headroom, then add retention and capacity alerts. |
| Slowness or high CPU | Load average, CPU mode breakdown, memory and swap, I/O wait, disk latency, network, the top processes and threads, application logs, recent changes, traffic, and dependencies. Only kill a process or reboot after identifying the cause and the risk — treat it as containment, not a fix. |
| Unresponsive system | Use console or out-of-band access. Check load, processes stuck in `D` state, memory pressure and OOM events, I/O, kernel logs, the filesystem, and hardware or cloud platform health. |
| Configuration change not taking effect | Validate syntax, confirm which config path is actually active, compare the rendered configuration against the live one, reload or restart safely, then check service logs. |
| User or permission change | Use approved identity processes, grant only the permissions actually needed, set correct group and ACL ownership, and verify as the target account. Avoid scripts that embed default passwords or grant `sudo` automatically. |

Never copy broad `rm -rf` examples from a cheat sheet straight into production.

---

## Why Linux Matters in DevOps

Linux is widely used for production servers, container hosts and cloud workloads, although Windows and other operating systems also remain important. DevOps engineers need command-line investigation skills because most servers are managed remotely without a graphical interface.

The sections below cover the areas that come up daily in production: process management, networking, filesystem navigation, permissions, disk usage, search and filtering, package management, system configuration, monitoring, and service management.

## 1. Process Management: Your Applications Under the Hood

When an application crashes, consumes too much CPU, or stops responding, you need to look at its processes.

### The commands you'll actually use

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

### Process hierarchy matters

```bash
# See the family tree of processes
pstree                    # Visual process tree
pstree -p                 # Include process IDs
```

This shows parent-child relationships. Do not assume killing a parent process also ends its children — a child can catch the signal, keep running, or get re-parented to another process.

For managed applications, use the service manager or orchestrator instead of killing processes directly, so shutdown and restart behavior stays consistent.

## 2. Networking: How Your Services Talk

Services depend on the network to reach each other. When networking breaks, everything built on top of it breaks too.

### Network interface management

```bash
# Modern way to check network setup
ip addr show              # Show all network interfaces
ip link show              # Show network devices

# The old way (still works)
ifconfig                  # Shows interface configuration
```

### Port monitoring — the detective work

```bash
# Who's using what port?
netstat -tulpn            # Show all listening ports with processes
ss -tulpn                 # Modern replacement (faster)

# Specific port investigation
lsof -i :80               # What's using port 80?
lsof -i :3306             # Check if MySQL is running
```

### Network troubleshooting arsenal

```bash
# Is the server reachable?
ping google.com           # Basic connectivity test
ping -c 4 server.com      # Send only 4 packets

# Trace the network path
traceroute google.com     # Show every router hop

# DNS investigation
dig google.com            # Detailed DNS lookup
nslookup google.com       # Simple DNS check
```

### Firewall management

```bash
# Ubuntu/Debian firewall (UFW - User Friendly Firewall)
sudo ufw status           # Check firewall status
sudo ufw enable           # Turn on firewall
sudo ufw allow 22         # Allow SSH
sudo ufw allow 80/tcp     # Allow HTTP traffic
sudo ufw deny 8080        # Block specific port

# Traditional iptables (more complex but powerful)
sudo iptables -L          # List all rules
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT  # Allow HTTPS
```

## 3. File System Navigation

You'll spend a lot of time navigating server filesystems, so knowing these commands well saves real time.

### Navigation

```bash
pwd                       # Where am I?
cd /var/log               # Go to logs directory
cd ..                     # Go up one level
cd ~                      # Go home
cd -                      # Go to previous directory
```

### File and directory operations

```bash
# Creating things
mkdir -p /path/to/deep/directory    # Create nested directories
touch config.yaml                    # Create empty file

# Copying and moving
cp app.py app.py.backup              # Backup before changes
cp -r /source/dir /destination/      # Copy entire directories
mv oldname.txt newname.txt           # Rename files

# Removing (be careful!)
rm filename                          # Delete file
rm -rf directory                     # Delete directory and contents (DANGEROUS!)
```

Run `ls` first to confirm exactly what a delete command will affect, before running `rm`.

### File viewing techniques

```bash
# Quick file inspection
cat config.yaml           # Show entire file
head -20 app.log          # First 20 lines
tail -50 error.log        # Last 50 lines
tail -f application.log   # Follow log in real-time (lifesaver for debugging)

# Paginated viewing
less large-file.txt       # Navigate large files
```

## 4. File Permissions: The Security Foundation

Understanding permissions prevents security issues and deployment failures.

### Understanding the permission matrix

```text
rwx rwx rwx
│   │   └── Others (everyone else)
│   └────── Group (file's group)
└────────── Owner (file creator)

r = read (4)    - Can view file content
w = write (2)   - Can modify file
x = execute (1) - Can run file as program
```

### Permission management in practice

```bash
# Symbolic notation (readable)
chmod u+x script.sh       # Give owner execute permission
chmod g-w file.txt        # Remove group write permission
chmod o+r document.pdf    # Give others read permission
chmod a+x binary          # Give everyone execute permission

# Numeric notation (faster once you learn it)
chmod 755 script.sh       # rwxr-xr-x (common for scripts)
chmod 644 config.txt      # rw-r--r-- (common for config files)
chmod 600 private.key     # rw------- (private keys)
chmod 777 file.txt        # rwxrwxrwx (AVOID THIS - security risk!)
```

### Ownership management

```bash
# Change file ownership
sudo chown user:group file.txt      # Change both user and group
sudo chown jenkins config.yaml      # Change only owner
sudo chown :docker script.sh        # Change only group

# Recursive ownership changes
sudo chown -R nginx:nginx /var/www/html   # Change entire directory tree
```

### Users, groups and special permissions

```bash
id username
groups username
sudo useradd --create-home --shell /bin/bash username
sudo passwd username
sudo usermod -aG application-team username
sudo userdel --remove username
```

Check your distribution's account-management policy before creating or deleting users. `useradd` defaults vary between distributions, and removing a home directory can destroy data. At scale, prefer a central identity system over local accounts.

The key account files are `/etc/passwd`, `/etc/shadow` and `/etc/group`. Password hashes live in `/etc/shadow`, which only privileged users can read. UID ranges for system versus regular users are distribution-configurable, so don't assume a universal `0–999` boundary.

There are also three special permission bits, set as an extra digit before the normal three:

| Bit | Value | Effect |
|---|---|---|
| setuid | `4000` | An executable runs with the file owner's identity, not the identity of whoever ran it. |
| setgid | `2000` | An executable runs with the file's group identity. On a directory, new files inherit that directory's group. |
| sticky bit | `1000` | On a shared directory, only a file's owner or a privileged user can delete or rename it. |

Audit these bits carefully. Executables with setuid or setgid set can be used to escalate privileges if misconfigured.

## 5. File System Usage: Avoiding the Disk Space Disaster

Monitoring disk usage prevents most storage-related incidents.

### Disk space monitoring

```bash
# Check available space
df -h                     # Human-readable disk usage
df -i                     # Check inode usage (can run out even with space)

# Find what's eating your disk
du -h /var/log            # Directory size
du -sh *                  # Size of each item in current directory
du -h --max-depth=1 /     # Top-level directory sizes
```

### Finding space hogs

```bash
# Find large files
find / -size +100M -type f 2>/dev/null    # Files larger than 100MB
find /var/log -name "*.log" -size +50M    # Large log files

# Find old files (potential cleanup candidates)
find /tmp -type f -mtime +30              # Files older than 30 days
```

## 6. Search and Filter: Finding Needles in Haystacks

Being able to search and filter quickly saves real time when you're troubleshooting a production issue.

### File finding

```bash
# Find files by name
find /var/log -name "*.log"           # All log files
find /etc -name "*nginx*"             # Anything with nginx in name
find / -type f -name "config.yaml"    # Specific filename anywhere

# Find by size and date
find /var/log -size +100M             # Large log files
find /tmp -mtime +7                   # Files older than 7 days
find /etc -type f -perm 777           # World-writable files (security risk)
```

### Text processing powerhouse

```bash
# grep - your text searching best friend
grep "ERROR" /var/log/app.log         # Find errors in logs
grep -r "database" /etc/              # Recursively search for "database"
grep -i "warning" *.log               # Case-insensitive search
grep -n "failed" app.log              # Show line numbers
grep -v "DEBUG" app.log               # Exclude debug messages

# Real-world log analysis
grep "500" /var/log/nginx/access.log | wc -l     # Count 500 errors
grep "$(date '+%Y-%m-%d')" /var/log/app.log       # Today's logs only
```

### Advanced text processing

```bash
# awk - column extraction magic
awk '{print $1}' /var/log/nginx/access.log            # Extract IP addresses
awk -F: '{print $1}' /etc/passwd                      # Extract usernames
awk '$9 == 404 {print $1}' /var/log/nginx/access.log  # IPs with 404 errors

# sed - stream editing
sed 's/old/new/g' config.txt          # Replace all occurrences
sed -n '10,20p' large-file.txt        # Print lines 10-20

# cut - simple column extraction
cut -d: -f1 /etc/passwd               # First field using : delimiter
cut -c1-10 filename                   # Characters 1-10 of each line

# sort and unique analysis
sort /var/log/ips.txt | uniq -c | sort -nr    # Count and sort unique IPs
```

## 7. Package Management: Installing and Managing Software

### APT (Ubuntu/Debian) — the most common

```bash
# Update package database first (always!)
sudo apt update                       # Refresh package lists
sudo apt upgrade                      # Upgrade installed packages

# Install software
sudo apt install nginx                # Install web server
sudo apt install htop git curl        # Multiple packages at once

# Remove software
sudo apt remove nginx                 # Remove package
sudo apt purge nginx                  # Remove package and configs
sudo apt autoremove                   # Clean up orphaned dependencies

# Search for packages
apt search docker                     # Find docker-related packages
apt list --installed | grep python    # List installed Python packages
```

### YUM/DNF (RedHat/CentOS/Fedora)

```bash
# YUM (older RHEL/CentOS systems)
sudo yum update                       # Update all packages
sudo yum install docker               # Install Docker
sudo yum remove docker                # Remove Docker

# DNF (newer Fedora/RHEL systems)
sudo dnf update                       # Update packages
sudo dnf install podman               # Install container runtime
sudo dnf search kubernetes            # Search for packages
```

Run `apt update` before `apt install` so you install from the current package list rather than a stale cached one.

## 8. System Configuration: Making Your Environment Work

### System information commands

```bash
# Know your system
uname -a                              # Complete system info
lscpu                                 # CPU information
free -h                               # Memory usage
lsblk                                 # Block devices (disks)
df -h                                 # Disk usage

# OS and version info
cat /etc/os-release                   # OS version details
hostnamectl                           # Hostname and system info
```

### Shell configuration

```bash
# Profile files (loaded in order)
/etc/profile                          # System-wide login profile
~/.bash_profile                       # User login profile
~/.bashrc                             # User interactive shell config

# Create useful aliases
alias ll='ls -la'                     # Long listing
alias la='ls -la'                     # All files with details
alias grep='grep --color=auto'        # Colored grep output
alias k='kubectl'                     # Kubernetes shortcut

# Make aliases permanent
echo "alias ll='ls -la'" >> ~/.bashrc
source ~/.bashrc                      # Reload trusted configuration
```

### Environment variables

```bash
# View environment
env                                   # All environment variables
echo $PATH                            # Show PATH variable
echo $HOME                            # Home directory

# Non-sensitive runtime configuration
export APP_ENV="development"
```

Environment variables pass down to child processes, and they can leak through debugging output, crash reports, CI logs, or process inspection. Don't store long-lived secrets in shell profiles or committed `.env` files. Use an approved secret manager and short-lived credentials instead.

### Vim essentials

```text
vim file.conf    open a file
i                enter Insert mode
Esc              return to Normal mode
:w               write changes
:q               quit
:wq              write and quit
:q!              quit and discard unsaved changes
/pattern         search forward
n / N            next / previous match
:set number      show line numbers
gg / G           first / last line
0 / $            start / end of line
```

Validate a service's configuration before reloading it. Keep a recoverable copy, or better, manage the configuration in version control.

### Pipes and redirection

```bash
command >output.txt          # Replace stdout file
command >>output.txt         # Append stdout
command 2>error.log          # Replace stderr file
command >all.log 2>&1        # Send stdout and stderr to one file
command <input.txt           # Read stdin from a file
producer | consumer          # Producer stdout becomes consumer stdin

ps aux | sort -k4 -rn | head -10
du -ah /var/log | sort -rh | head -10
tail -F /var/log/app.log | grep --line-buffered ERROR
```

Redirection is processed by the shell before the command starts. `>` truncates an existing file, and `sudo command > /root/file` does not make the shell's redirection privileged.

Quote variables and use `set -o pipefail` in scripts when an earlier pipeline command failing must fail the pipeline.

## 9. System Monitoring: Keeping Your Finger on the Pulse

### Load and performance monitoring

```bash
# System overview
uptime                                # Load average and uptime
w                                     # Who's logged in and doing what
top                                   # Real-time process monitoring
htop                                  # Enhanced process viewer

# Memory analysis
free -h                               # Memory usage summary
cat /proc/meminfo                     # Detailed memory info
vmstat 1 5                            # Virtual memory stats (1 sec intervals, 5 times)

# I/O performance
iostat 1 5                            # Disk I/O statistics
sar 1 5                               # System activity report
```

### Swap usage analysis

```bash
# Check swap status
swapon --show                         # Active swap partitions
cat /proc/swaps                       # Swap usage details
free -h                               # Memory and swap summary
```

High swap usage alone doesn't prove there's memory pressure or a leak. Check swap-in/swap-out activity, available memory, OOM events, page-fault behavior, and per-process growth before deciding whether to tune the workload or add RAM.

## 10. Service Management: Controlling Your Applications

Modern Linux uses `systemd` for service management.

### Systemd service control

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

### Service discovery and troubleshooting

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

### Legacy service management

```bash
# Traditional service command (still works)
sudo service nginx start              # Start service
sudo service nginx status             # Check status
sudo /etc/init.d/nginx restart        # Direct init script
```

## The Commands You'll Use Every Day

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

### Emergency debugging

```bash
# High CPU investigation
ps aux --sort=-%cpu | head -10        # Top CPU users

# Memory issues
ps aux --sort=-%mem | head -10        # Top memory users
cat /proc/meminfo | grep Available    # Available memory

# Disk space emergency
du -sh /* | sort -hr | head -10       # Largest directories
find /var/log -name "*.log" -size +100M  # Large log files
```

## Best Practices That Will Save Your Career

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
