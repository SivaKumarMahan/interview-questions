# Linux Operations Summary

## Core Areas

- **Files/navigation:** `pwd`, `ls`, `cd`, `mkdir`, `cp`, `mv`, `touch`, `cat`, `less`, and cautious removal.
- **System information:** date/time, uptime/load, logged-in users, kernel/CPU/memory, filesystem and directory usage.
- **Processes:** `ps`, `top`, `pidstat`, signals, process states, parent/child relationships, and service ownership.
- **Permissions:** owner/group/other, read/write/execute, `chmod`, `chown`, ACLs, `sudo`, and safe account management.
- **Archives:** `tar` create/list/extract with gzip/bzip2/xz where appropriate.
- **Networking:** DNS, route, TCP/TLS, SSH, listening sockets, and packet/path investigation.
- **Services/logs:** `systemd` status/start/stop/reload, `journalctl`, application logs, log rotation, and boot history.

## Scenario Flow

For **100% disk usage**, determine filesystem/inode pressure, largest directories/files, deleted-but-open files, log/journal growth, package/container caches, and application ownership. Free only confirmed safe data, restore headroom, and add retention/capacity alerts. Never copy broad `rm -rf` examples from a cheat sheet into production.

For **slowness or high CPU**, correlate load, CPU modes, memory/swap, I/O wait, disk latency, network, top processes/threads, application logs, recent changes, traffic, and dependencies. A kill or reboot is containment only after identifying the process and risk.

For an **unresponsive system**, use console/out-of-band access and check load, `D` state processes, memory pressure/OOM, I/O, kernel logs, filesystem, and hardware/cloud health. For configuration changes that do not take effect, validate syntax, confirm the active path, compare rendered/live configuration, reload or restart safely, and inspect service logs.

**User and permission changes** should use approved identity processes, least privilege, correct group/ACL ownership, and verification as the target account. Avoid scripts that embed default passwords or grant `sudo` automatically.

---

## Why Linux Matters in DevOps

Every production server you'll work with runs Linux. Every container runs on Linux. Every cloud instance runs Linux. When things break at 3 AM (and they will), you diagnose issues using Linux commands, not GUI tools.

Forget about memorizing 500 commands. Focus on the concepts and tools you'll use daily in production. Here are the 10 essential areas every DevOps engineer should master.

## 1. Process Management: Your Applications Under the Hood

When your application crashes, consumes too much CPU, or becomes unresponsive, you need to understand processes.

### The commands you'll actually use

See what's running:

```bash
# The holy trinity of process monitoring
ps aux                    # Snapshot of all processes
top                       # Real-time view (like Task Manager)
htop                      # Enhanced version (install it everywhere)
```

When running `ps aux` on a production server, look for high CPU usage processes (`%CPU` column), memory hogs (`%MEM` column), and processes that shouldn't be running.

Kill misbehaving processes:

```bash
# Find the troublemaker first
ps aux | grep nginx

# Kill it gently
kill 1234

# Kill it with force (when gentle doesn't work)
kill -9 1234

# Nuclear option - kill all instances
killall nginx
```

**Pro tip:** Always try `kill` before `kill -9`. The gentle kill allows the process to clean up properly.

### Process hierarchy matters

```bash
# See the family tree of processes
pstree                    # Visual process tree
pstree -p                 # Include process IDs
```

This shows parent-child relationships. Kill a parent process, and its children die too — essential for understanding how applications spawn sub-processes.

## 2. Networking: How Your Services Talk

In a microservices world, everything is connected. When networking breaks, everything breaks.

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

You'll spend countless hours navigating server file systems. Efficiency here saves hours daily.

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

**Safety tip:** Always use `ls` to verify what you're about to delete.

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

Efficient searching separates good DevOps engineers from frustrated ones.

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

**Production tip:** Always run `apt update` before `apt install` to ensure you get the latest package versions.

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
source ~/.bashrc                      # Reload configuration
```

### Environment variables

```bash
# View environment
env                                   # All environment variables
echo $PATH                            # Show PATH variable
echo $HOME                            # Home directory

# Set temporary variables
export API_KEY="your-key-here"        # For current session

# Set permanent variables
echo 'export API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc                      # Reload to activate
```

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

**Performance tip:** If swap usage is high, your system needs more RAM or has a memory leak.

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

3. **Use version control for configuration files.**

   ```bash
   cd /etc/nginx
   sudo git init
   sudo git add .
   sudo git commit -m "Initial nginx config"
   ```

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
