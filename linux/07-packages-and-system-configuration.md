# Linux: Packages and System Configuration

> APT and YUM/DNF package management, system information, shell profiles and aliases, and environment variables.

## Key Concepts

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

## Interview Questions

<details><summary>Q1. [Intermediate] <code>yum</code> or <code>apt</code> installation is failing. How do you troubleshoot?</summary>

**Answer:**

I read the actual error message first. I check disk space, inodes, and the system clock, then whether the repository is reachable over DNS, TLS, and any proxy, whether the configured release or version is right, and whether the GPG key is valid.

A lock error means another `apt`, `dpkg`, `dnf`, or `yum` process is already running — I find that process rather than deleting the lock file while a transaction is in progress.

On Debian-based systems I use `apt-get update`, `apt-cache policy`, `dpkg --audit`, and `dpkg --configure -a` if something got interrupted. On RHEL-based systems I use `dnf repolist -v`, `dnf makecache`, and `dnf history`.

I check the repository and package logs, resolve any held or broken dependencies deliberately, and never disable signature checks. Once it's fixed, I install the exact package, confirm its version and that the service works, and put the repository configuration back to what's approved.

</details>

<details><summary>Q2. [Intermediate] Package manager versus compiling from source: when do you use each?</summary>

**Answer:**

I prefer the supported `apt`, `dnf`, or `yum` package, because it gives dependency management, signed updates, an inventory of what's installed, security patches, and a clean way to remove it later.

I only compile from source when a needed feature or version isn't available in the approved repositories, and whoever owns the system accepts the extra burden of patching it, knowing where the build came from and how it was built, keeping the build reproducible, and being able to roll it back.

For production, I package the build myself or use a trusted repository, rather than leave untracked binaries sitting under `/usr/local`.

</details>
