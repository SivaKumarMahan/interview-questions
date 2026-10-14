# Linux: Most Asked Basics and Commands

> The Linux questions asked in almost every DevOps screening round: core concepts, numeric and special permissions, users and sudo, everyday networking commands, finding and searching files, secure file transfer, and mounting filesystems with `/etc/fstab`.

## Key Concepts

### Reading a permission string

`ls -l` prints a string such as `drwxr-xr--`:

| Position | Meaning | Example `drwxr-xr--` |
| --- | --- | --- |
| 1 | File type: `-` file, `d` directory, `l` symbolic link | `d` = directory |
| 2–4 | Owner (user) permissions | `rwx` = read, write, execute |
| 5–7 | Group permissions | `r-x` = read, execute |
| 8–10 | Others (everyone else) | `r--` = read only |

Each permission has a number, and each digit of a mode is the sum for one class:

| Permission | Value | On a file | On a directory |
| --- | --- | --- | --- |
| `r` read | 4 | Read the content | List the names inside (`ls`) |
| `w` write | 2 | Change the content | Create, delete or rename entries (also needs `x`) |
| `x` execute | 1 | Run it as a program or script | Enter it with `cd` and reach files inside |
| `-` none | 0 | – | – |

So `rwx` = 4+2+1 = 7, `r-x` = 5, `r--` = 4, and `chmod 754 file` gives the owner everything, the group read and execute, and others read.

The permissions are **independent**. Write does not include read, and execute does not include read or write: a file with mode `300` (`-wx------`) can be written to but not read. A shell script needs **both** `r` and `x` to run as `./script.sh`, because the shell has to read it.

### Changing permissions and owners

```bash
chmod 755 deploy.sh          # numeric mode
chmod u+x deploy.sh          # symbolic: add execute for the owner
chmod g-w,o-rwx secrets.env  # remove group write, remove everything for others
chmod -R 750 /opt/app        # recursive (use with care)
chown appuser:appgroup /opt/app -R
chmod 400 key.pem            # SSH private keys: owner read only
```

`u` = owner, `g` = group, `o` = others, `a` = all. SSH refuses a private key that others can read, so keys must be `400` or `600`. Never use `chmod 777` or `chmod -R 777` to "fix" an access problem; find the right owner or group instead.

### Special permission bits (the fourth digit)

A four-digit mode such as `2775` puts the special bits first:

| Bit | Value | Effect | Shown in `ls -l` |
| --- | --- | --- | --- |
| setuid | 4 | An executable runs as its owner (for example `/usr/bin/passwd` runs as root) | `s` in the owner's `x` position |
| setgid | 2 | On a directory, new files inherit the directory's group (shared team folders) | `s` in the group's `x` position |
| sticky | 1 | On a directory, only a file's owner can delete it (for example `/tmp`, mode `1777`) | `t` in the others' `x` position |

A capital `S` or `T` means the special bit is set but the execute bit under it is not.

### Users, groups and sudo

| Task | Command |
| --- | --- |
| Create a user with a home directory | `sudo useradd -m -s /bin/bash john` (Debian also has `adduser`) |
| Set or change a password | `sudo passwd john` |
| Create a group | `sudo groupadd devops` |
| Add a user to a group (keep other groups) | `sudo usermod -aG devops john` |
| Show a user's groups | `groups john` or `id john` |
| Who am I | `whoami`, `id` |
| Delete a user and the home directory | `sudo userdel -r john` |
| Edit sudo rules safely | `sudo visudo` or `sudo visudo -f /etc/sudoers.d/devops` |

Users are stored in `/etc/passwd`, password hashes in `/etc/shadow`, and groups in `/etc/group`. Without `-a`, `usermod -G` **replaces** all of the user's extra groups. New group membership applies only to new login sessions.

Example sudo rules in `/etc/sudoers.d/devops`:

```text
%devops  ALL=(ALL) ALL                                     # full sudo for the group
deploy   ALL=(root) NOPASSWD: /usr/bin/systemctl restart nginx   # one command only
```

Sudo controls which commands a user can run as another user. It does not change file permissions: a user can still be denied a file unless the command runs through `sudo`.

### Everyday networking commands

| Command | What it shows |
| --- | --- |
| `ip a` (`ip addr show`) | Interfaces and IP addresses. Replaces `ifconfig` (package `net-tools`, deprecated) |
| `ip route` | Routing table and default gateway |
| `hostname`, `hostname -I`, `hostnamectl` | Host name, all IP addresses, set the name permanently (`hostnamectl set-hostname web01`) |
| `ping host` | ICMP reachability and round-trip time (`Ctrl+C` stops it and prints statistics) |
| `nslookup name`, `dig name` | DNS resolution (DNS uses port 53) |
| `curl -v http://host:port` | HTTP request with headers and TLS details |
| `wget URL` | Download a file to the current directory |
| `ss -tulpn` | Listening TCP and UDP ports and the owning process (replaces `netstat`) |
| `/etc/hosts` | Static name-to-IP mapping, checked before DNS by default |
| `/etc/resolv.conf` | DNS servers and search domains used for lookups |

### Command summary

| Command | Purpose | Example |
| --- | --- | --- |
| `chmod` | Change permissions | `chmod 755 script.sh` |
| `chown` | Change owner and group | `chown app:app /opt/app` |
| `ps aux`, `top`, `htop` | Running processes | `ps aux --sort=-%cpu` |
| `kill` | Send a signal | `kill -15 1234` |
| `free -h` | Memory usage | `free -h` |
| `uptime` | Running time and load averages | `uptime` |
| `df -h`, `df -hT` | Free space per filesystem (with type) | `df -hT` |
| `du -sh` | Size of a directory | `du -sh /var/log` |
| `lsblk` | Disks, partitions and mount points | `lsblk -f` |
| `mount`, `findmnt` | Mounted filesystems | `findmnt /data` |
| `which` | Path of a command | `which python3` |
| `tree` | Directory tree (install the package) | `tree -L 2 /etc/nginx` |
| `grep` | Search text | `grep -n ERROR app.log` |

## Interview Questions

<details><summary>Q1. [Basic] What is Linux, and how is it different from Unix?</summary>

**Answer:**

Linux is an open-source, Unix-like operating system kernel. Together with GNU tools and other software it forms distributions such as Ubuntu, RHEL, Amazon Linux and Debian, which run most servers, cloud VMs, containers and DevOps tools.

| | Unix | Linux |
| --- | --- | --- |
| Origin | AT&T Bell Labs, 1969 | Linus Torvalds, 1991, written from scratch |
| Licence | Mostly proprietary (AIX, HP-UX, Solaris) | Open source (GPL) |
| Hardware | Usually tied to a vendor's hardware | Runs almost anywhere: x86, ARM, mainframes |
| Cost | Commercial licences | Free; paid support is optional (RHEL, SUSE) |

Linux follows the same ideas as Unix (everything is a file, small tools combined with pipes, multi-user permissions), but it contains no original Unix code.

</details>

<details><summary>Q2. [Basic] What is a process, and how is it different from a thread?</summary>

**Answer:**

A **process** is a running instance of a program. It has its own PID, memory space, open files and environment. A **thread** is a unit of execution inside a process: threads of the same process share its memory and open files, but each has its own stack and registers.

| | Process | Thread |
| --- | --- | --- |
| Memory | Separate address space | Shared with other threads of the process |
| Creation cost | Higher (`fork`) | Lower |
| Failure impact | A crash usually affects only that process | A crash can bring down the whole process |
| Communication | Pipes, sockets, shared memory | Direct shared memory (needs locking) |

Check processes with `ps aux`, `top` or `htop`, and threads with `ps -eLf` or `top -H -p <PID>`.

</details>

<details><summary>Q3. [Basic] What is the difference between <code>/</code> and <code>/home</code>, and what is stored in <code>/etc</code>?</summary>

**Answer:**

`/` is the root of the whole filesystem tree; every path starts there. `/home` is one directory under it that holds normal users' personal directories, for example `/home/john`. The root user's home is `/root`, not `/home/root`.

Other directories to know:

| Directory | Contents |
| --- | --- |
| `/etc` | System and application configuration: `/etc/passwd`, `/etc/fstab`, `/etc/ssh/sshd_config`, `/etc/nginx/` |
| `/var` | Changing data: logs in `/var/log`, caches, spool files |
| `/usr/bin`, `/usr/sbin` | Installed programs |
| `/opt` | Optional or third-party applications |
| `/tmp` | Temporary files (often cleared on reboot) |
| `/proc`, `/sys` | Virtual files exposing kernel and process information |
| `/dev` | Device files such as `/dev/sda` |

</details>

<details><summary>Q4. [Basic] What is a shell?</summary>

**Answer:**

A shell is a command-line interpreter: it reads the commands you type (or a script), expands variables and wildcards, runs programs, and connects them with pipes and redirections. Common shells are `bash` (the default on most distributions), `sh` (POSIX, `dash` on Ubuntu), `zsh` and `ksh`.

```bash
echo $SHELL          # your login shell
cat /etc/shells      # installed shells
chsh -s /bin/zsh     # change your login shell
```

</details>

<details><summary>Q5. [Basic] What is the difference between <code>sudo</code> and <code>su</code>, and between <code>su user</code> and <code>su - user</code>?</summary>

**Answer:**

- `sudo command` runs **one command** as another user (root by default). It asks for **your own** password, checks the rules in `/etc/sudoers`, and logs every command, so it supports least privilege and auditing.
- `su user` **switches** to another user's shell and asks for **that user's** password. `su` with no user means root.
- `su - user` (or `su -l`) starts a full login shell: it loads that user's environment (`PATH`, home directory, profile files). `su user` keeps most of your current environment, which can cause confusing behaviour.

In production I prefer `sudo` with specific rules, disable direct root login over SSH, and use `sudo -i` only when a root shell is really needed. Type `exit` to return to the previous user.

</details>

<details><summary>Q6. [Basic] What is SSH, and how do you access a Linux server?</summary>

**Answer:**

SSH (Secure Shell) is an encrypted protocol for remote login and command execution. It uses **TCP port 22** by default, and SFTP and SCP run over the same SSH connection (so the default SFTP port is also 22).

```bash
ssh -i ~/.ssh/key.pem ubuntu@10.0.1.15          # key-based login
ssh -J bastion-user@bastion app-user@10.0.2.10   # through a jump host
```

Typical access paths in the cloud:

- SSH with a key pair through a **bastion** or jump host, or a VPN.
- **Azure Bastion** or **AWS Systems Manager Session Manager**, which need no public IP or open port 22.
- The serial console for recovery when networking is broken.

Good practice: key-based login only (`PasswordAuthentication no`), `PermitRootLogin no`, keys with `chmod 400`, and port 22 allowed only from trusted ranges.

</details>

<details><summary>Q7. [Basic] How comfortable are you with Linux, what do you do on it regularly, and why is Linux important in DevOps?</summary>

**Answer:**

Answer with specific, honest tasks rather than "very comfortable". For example:

> "I work on Linux every day. Our build agents, Kubernetes nodes and most VMs run Ubuntu and RHEL. I troubleshoot CPU, memory and disk issues with `top`, `df`, `du` and `journalctl`, manage systemd services, write Bash scripts for health checks and log cleanup, schedule them with cron, manage users, permissions and SSH keys, check ports and DNS with `ss`, `curl` and `dig`, and patch servers. I'm comfortable on the command line, and I look up rare options rather than guessing."

Why it matters: most cloud servers, containers (container images are Linux userlands), Kubernetes nodes, CI/CD agents and DevOps tools run on Linux, so debugging production almost always ends at a Linux shell.

</details>

<details><summary>Q8. [Basic] What do the permission numbers 7, 5, 4 and 0 mean, and what are modes 755 and 555?</summary>

**Answer:**

Each digit is the sum of read (4), write (2) and execute (1):

| Digit | Letters | Meaning |
| --- | --- | --- |
| 7 | `rwx` | Read, write, execute |
| 6 | `rw-` | Read, write |
| 5 | `r-x` | Read, execute |
| 4 | `r--` | Read only |
| 0 | `---` | No access |

- **755** (`rwxr-xr-x`): the owner can do everything; the group and others can read and run it. Typical for scripts, binaries and web directories.
- **555** (`r-xr-xr-x`): everyone can read and run, nobody can write, not even the owner (root can still change it). Used for files that must not be edited by accident.
- Other common modes: `644` for normal files, `600` for secrets, `400` for SSH private keys, `700` for `~/.ssh`.

</details>

<details><summary>Q9. [Intermediate] A script has mode 755 and you run <code>chmod 7444 script.sh</code>. What happens?</summary>

**Answer:**

A four-digit mode sets the special bits with the first digit, so `7444` means:

- `7` = setuid (4) + setgid (2) + sticky (1).
- `444` = `r--r--r--`: read only for owner, group and others.

```bash
$ chmod 7444 script.sh
$ ls -l script.sh
-r-Sr-Sr-T 1 john john 120 Oct 14 10:00 script.sh
$ ./script.sh
bash: ./script.sh: Permission denied
$ bash script.sh        # still works, because only read permission is needed
```

What to say in the interview:

1. The script **loses its execute bit for everyone**, so `./script.sh` fails with "Permission denied", even for root (root needs at least one `x` bit to execute a file).
2. The capital `S` and `T` show that the special bits are set but have no effect, because there is no execute bit underneath them.
3. Linux ignores setuid and setgid on scripts anyway, and the sticky bit has no meaning on a regular file today.
4. It can still be run as `bash script.sh`, because the interpreter only needs to read the file.

To fix it: `chmod 755 script.sh`.

</details>

<details><summary>Q10. [Basic] Does write permission include read, and does execute include read and write?</summary>

**Answer:**

No. Read, write and execute are three independent bits. Some study notes claim they are "layered", which is wrong:

- `chmod 200 file` (`-w-------`): you can append or overwrite the file, but `cat file` fails.
- `chmod 100 script.sh` (`--x------`): a compiled binary can run, but a shell script cannot, because the shell must also **read** it.
- On a directory, `r` without `x` lets you list names but not open the files; `x` without `r` lets you open a file if you already know its exact name.

Root bypasses read and write checks, which is why these surprises usually show up only for normal users and service accounts.

</details>

<details><summary>Q11. [Basic] How do you create a user, give it a password, add it to a group, give it sudo access, and remove it?</summary>

**Answer:**

```bash
sudo useradd -m -s /bin/bash satya      # -m creates /home/satya
sudo passwd satya                        # password is not echoed while typing
sudo groupadd devops
sudo usermod -aG devops satya            # -a keeps the existing groups
groups satya                             # verify; or: id satya, getent group devops
echo '%devops ALL=(ALL) ALL' | sudo tee /etc/sudoers.d/devops
sudo chmod 440 /etc/sudoers.d/devops
sudo visudo -c                           # validate all sudoers files
sudo userdel -r satya                    # -r also removes the home directory and mail spool
```

Points to mention:

- Always edit sudo rules with `visudo` (or validate with `visudo -c`). A syntax error in sudoers can lock everyone out of sudo.
- Grant sudo through a group (`%devops`, or the `sudo` / `wheel` group) rather than individual lines, and limit commands where possible.
- The user must log in again for a new group to apply.
- In cloud environments, users are often managed centrally (Entra ID or AD login, Ansible, or cloud-init) rather than by hand on each server.

</details>

<details><summary>Q12. [Basic] Which commands do you use to check network configuration and name resolution?</summary>

**Answer:**

```bash
ip a                         # IP addresses (ifconfig is the older net-tools command)
ip route                     # default gateway and routes
hostname -I                  # all IPs of this host
ping -c 4 10.0.2.5           # basic reachability (ICMP may be blocked by firewalls)
nslookup api.example.com     # or: dig +short api.example.com
getent hosts api.example.com # resolves exactly as applications do (/etc/hosts first, then DNS)
cat /etc/resolv.conf         # which DNS servers are used
curl -v https://api.example.com/health
ss -tulpn                    # what is listening locally
```

`/etc/hosts` holds static entries that override DNS, which is useful for testing but easy to forget about later. `/etc/resolv.conf` lists the DNS servers; on systemd-resolved systems use `resolvectl status` to see the real upstream servers.

</details>

<details><summary>Q13. [Intermediate] How do you troubleshoot a Linux server in general?</summary>

**Answer:**

I go from the symptom to the resource, top-down:

1. **Scope:** what is broken (one service or the whole host), since when, and what changed (deployments, patches, config).
2. **Reachability:** can I reach it (`ping`, `ssh`, cloud console)? If not, check the security group or NSG, routes and the serial console.
3. **Load and resources:** `uptime` for load average, `top` or `htop` for CPU and memory, `free -h`, `df -h` and `df -i` for disk and inodes, `iostat -xz 1` for I/O.
4. **Services:** `systemctl status <service>`, `systemctl --failed`.
5. **Logs:** `journalctl -u <service> --since "1 hour ago"`, `journalctl -p err -b`, `/var/log/syslog` or `/var/log/messages`, `dmesg -T` for kernel errors such as OOM kills or disk errors.
6. **Network:** `ss -tulpn` for listening ports, `curl` to the health endpoint, `dig` for DNS.
7. **Fix, verify and record:** apply the smallest safe fix, confirm with metrics, and write down the root cause and a preventive action (alert, limit, automation).

</details>

<details><summary>Q14. [Intermediate] An application should listen on port 8080 but cannot be reached. How do you troubleshoot port-related issues?</summary>

**Answer:**

1. **Is it listening, and on which address?**

   ```bash
   sudo ss -tulpn | grep :8080
   ```

   `127.0.0.1:8080` means it accepts only local connections; it must listen on `0.0.0.0:8080` (or the server IP) to be reachable from outside. No output means the application is not running or failed to bind.
2. **Is the port already taken?** "Address already in use" in the logs: `sudo ss -ltnp 'sport = :8080'` or `sudo lsof -i :8080` shows the other process.
3. **Test locally, then remotely:** `curl -v localhost:8080`, then from another host `nc -zv <ip> 8080` or `curl -v http://<ip>:8080`.
4. **Host firewall:** `sudo ufw status`, `sudo firewall-cmd --list-all`, or `sudo iptables -L -n`.
5. **SELinux** (RHEL): a non-standard port may need `semanage port -a -t http_port_t -p tcp 8080`. Check `ausearch -m avc -ts recent`.
6. **Cloud network:** security group or NSG, network ACLs, load balancer listener and health probe, route tables.
7. Ports below 1024 need root or the `CAP_NET_BIND_SERVICE` capability.

</details>

<details><summary>Q15. [Intermediate] How do you monitor CPU utilization and context switches in Linux?</summary>

**Answer:**

**CPU utilization:**

```bash
top                      # press 1 for per-core view, P to sort by CPU
mpstat -P ALL 1 5        # per-core usage (sysstat package)
vmstat 1 5               # us, sy, id, wa, st columns
pidstat -u 1 5           # CPU per process
sar -u 1 5               # current, and history if sysstat collection is enabled
```

Read the split: high `us` is application code, high `sy` is kernel work, high `wa` means waiting for disk, and `st` (steal) on a VM means the hypervisor is short of CPU.

**Context switches** (the CPU switching from one task to another):

```bash
vmstat 1 5                        # cs column = context switches per second (system-wide)
pidstat -w 1 5                    # per process: cswch/s (voluntary), nvcswch/s (involuntary)
grep ctxt_switches /proc/<PID>/status
```

- Many **voluntary** switches: the process is waiting for I/O, locks or the network.
- Many **involuntary** switches: there are more runnable threads than CPUs, so the scheduler keeps pre-empting them (CPU contention).

A sudden jump in `cs` together with a high run queue (`r` in `vmstat` above the number of cores) points to too many threads, lock contention or a noisy neighbour.

For continuous monitoring, I use Node Exporter with Prometheus or Azure Monitor rather than running these by hand (see [monitoring-tools](../monitoring-tools/02-prometheus.md)).

</details>

<details><summary>Q16. [Basic] Explain the <code>sort</code> command.</summary>

**Answer:**

`sort` orders lines of text. It sorts alphabetically by default, so `10` comes before `9`.

```bash
sort names.txt                    # alphabetical
sort -n numbers.txt               # numeric
sort -r file                      # reverse
sort -u file                      # sort and remove duplicates
sort -h sizes.txt                 # human-readable sizes: 2K < 1M < 3G
sort -t: -k3 -n /etc/passwd       # by field 3 (UID), ":" as separator
sort -k2,2 -k1,1 file             # by column 2, then column 1
du -sh * | sort -rh | head -5     # five largest items
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head   # top client IPs
```

`uniq` removes only **adjacent** duplicates, which is why it is almost always used after `sort`.

</details>

<details><summary>Q17. [Basic] How do you find a file from the root of the server, or find where a command is installed?</summary>

**Answer:**

```bash
sudo find / -name "app.conf" 2>/dev/null           # exact name, hide permission errors
sudo find / -iname "*nginx*.conf" -type f 2>/dev/null
find /var/log -type f -name "*.log" -mtime -1      # changed in the last day
locate app.conf                                    # fast, uses a database (run updatedb first)
which python3                                      # first match in PATH
whereis nginx                                      # binary, source and man pages
type ll                                            # alias, function, builtin or file
```

`find` searches the live filesystem, so it is slower but always current. `locate` is fast but only as current as its last `updatedb` run. `which` only searches the directories in `PATH`.

</details>

<details><summary>Q18. [Basic] How do you search a file for errors or exceptions and show line numbers?</summary>

**Answer:**

```bash
grep -n "ERROR" app.log                         # -n adds line numbers
grep -niE "error|exception|fail" app.log        # case-insensitive, several patterns
grep -rniE "error|exception" /var/log/myapp/    # recursive through a directory
grep -n -C 3 "Exception" app.log                # 3 lines of context before and after
grep -c "ERROR" app.log                         # count matching lines
grep -v "DEBUG" app.log                         # exclude lines
zgrep -n "ERROR" app.log.1.gz                   # search rotated, compressed logs
journalctl -u myapp -p err --since today        # systemd service errors
```

For Java stack traces, `-A 20` (lines after) shows the full trace after the `Exception` line.

</details>

<details><summary>Q19. [Intermediate] How do you securely copy files between two Linux servers? What is the difference between SFTP, SCP and FTP?</summary>

**Answer:**

| Tool | Example | Best for |
| --- | --- | --- |
| `rsync` over SSH | `rsync -avzP -e ssh /data/ user@host:/backup/` | Large or repeated transfers: copies only changes, resumes, keeps permissions |
| `scp` | `scp -r ./build user@host:/opt/app/` | Quick one-off copy of a file or folder |
| `sftp` | `sftp user@host`, then `put` and `get` | Interactive or scripted file sessions, partner file exchange |
| FTP | `ftp host` | Legacy only; avoid |

| | FTP | SFTP | SCP |
| --- | --- | --- | --- |
| Encryption | None: passwords and data in plain text | Yes (SSH) | Yes (SSH) |
| Port | 21 (control) + data ports | 22 | 22 |
| Features | List, rename, delete, resume | List, rename, delete, resume | Copy only |
| Use today | Avoid | Recommended for file exchange | Fine for simple copies; recent OpenSSH runs `scp` over the SFTP protocol |

FTPS (FTP over TLS) is different from SFTP. I use key-based authentication, restrict the account to SFTP when needed (`ForceCommand internal-sftp`), and verify large copies with `sha256sum`.

</details>

<details><summary>Q20. [Intermediate] How do you mount a filesystem, make it mount automatically after reboot, and find its UUID?</summary>

**Answer:**

**1. Identify the disk and its UUID:**

```bash
lsblk -f                 # disks, partitions, filesystem type, UUID, mount point
sudo blkid /dev/sdb1     # UUID and TYPE of one device
```

`blkid` and `lsblk -f` are the commands that identify the filesystem UUID. Use the UUID rather than `/dev/sdb1`, because device names can change after a reboot or when disks are added (very common on cloud VMs).

**2. Mount it manually and test:**

```bash
sudo mkdir -p /data
sudo mount /dev/sdb1 /data          # or: sudo mount UUID=<uuid> /data
df -hT /data
```

**3. Make it permanent in `/etc/fstab`:**

```text
UUID=3f1c...e9a2  /data  xfs  defaults,nofail  0  2
```

The fields are: device, mount point, filesystem type, options, dump (0) and fsck order (0 = skip, 1 = root, 2 = others). `nofail` lets the server boot even if the disk is missing, which matters for cloud data disks.

**4. Test before rebooting** (this is how you fix an fstab entry permanently and safely):

```bash
sudo cp /etc/fstab /etc/fstab.bak
sudo findmnt --verify            # checks syntax, UUIDs and types
sudo umount /data && sudo mount -a   # mounts everything in fstab; errors appear now, not at boot
findmnt /data
```

If a bad fstab entry already stops the server from booting, use the cloud serial console or rescue mode, remount root read-write (`mount -o remount,rw /`), fix or comment out the line, and reboot.

</details>

<details><summary>Q21. [Basic] How do you check the current directory? <em>(asked in interview round)</em></summary>

**Answer:**

Use `pwd` (print working directory).

```bash
pwd          # /home/ubuntu/app
pwd -P       # physical path, resolves symbolic links
```

**Important point:** in scripts, use absolute paths or `cd` explicitly, because the working directory depends on where the script was started.

</details>

<details><summary>Q22. [Basic] How do you check disk space? <em>(asked in interview round)</em></summary>

**Answer:**

```bash
df -h                             # free/used space per filesystem
df -i                             # inode usage
du -sh /var/log                   # size of one directory
du -sh /var/* | sort -h           # biggest directories under /var
```

**Important point:** a disk can show free space in `df -h` but still fail with "No space left on device" if inodes are full (`df -i`), or if a deleted file is still held open by a process (`lsof +L1`).

See also: [Disk, storage and filesystems](../linux/05-disk-storage-and-filesystems.md).

</details>

<details><summary>Q23. [Basic] How do you check memory usage? <em>(asked in interview round)</em></summary>

**Answer:**

```bash
free -h          # total, used, free, buff/cache, available
vmstat 1 5       # memory, swap in/out, CPU every second, 5 times
top              # sort by memory with Shift+M
```

**Important point:** look at the **available** column, not "free". Linux uses spare memory for cache, which is released when applications need it.

</details>

<details><summary>Q24. [Basic] How do you check running processes? <em>(asked in interview round)</em></summary>

**Answer:**

```bash
ps aux                              # all processes
ps aux --sort=-%cpu | head          # top CPU consumers
ps -ef | grep nginx                 # find a process
top                                 # live view (htop if installed)
```

**Important point:** stop a process gently with `kill <pid>` (SIGTERM) first; use `kill -9` only if it does not stop, because it gives no chance to clean up.

See also: [Processes, services and scheduling](../linux/04-processes-services-and-scheduling.md).

</details>

<details><summary>Q25. [Basic] What is the difference between chmod and chown? <em>(asked in interview round)</em></summary>

**Answer:**

- `chmod` changes **permissions** (read, write, execute for owner, group, others).
- `chown` changes **ownership** (user and group).

```bash
chmod 640 app.conf               # owner rw, group r, others none
chmod u+x deploy.sh              # add execute for owner
chown appuser:appgroup app.conf  # change owner and group
chown -R www-data:www-data /var/www
```

**Important point:** avoid `chmod 777`; give the minimum permissions needed. Changing ownership normally requires root (`sudo`).

See also: [Users, permissions and SSH](../linux/03-users-permissions-and-ssh.md).

</details>

<details><summary>Q26. [Basic] How do you find large files? <em>(asked in interview round)</em></summary>

**Answer:**

```bash
find / -xdev -type f -size +500M -exec ls -lh {} \; 2>/dev/null
du -ah /var | sort -rh | head -20
```

`-xdev` stays on one filesystem (skips `/proc` and other mounts), and `2>/dev/null` hides permission errors.

**Important point:** before deleting a large log, check whether a process has it open; truncate it with `truncate -s 0 file.log` instead of `rm`, otherwise the space is not released until the process restarts.

See also: [Files, search and text processing](../linux/02-files-search-and-text-processing.md).

</details>

<details><summary>Q27. [Basic] How do you check system logs? <em>(asked in interview round)</em></summary>

**Answer:**

```bash
journalctl -u nginx --since "1 hour ago"   # logs for one service
journalctl -p err -b                       # errors since the last boot
journalctl -f                              # follow live
dmesg -T | tail                            # kernel messages (OOM, disk, hardware)
tail -f /var/log/syslog                    # Ubuntu/Debian (/var/log/messages on RHEL)
```

**Important point:** `/var/log/auth.log` (Debian/Ubuntu) or `/var/log/secure` (RHEL) shows login and `sudo` activity, useful for security checks.

See also: [Logs and log analysis](../linux/08-logs-and-log-analysis.md).

</details>

<details><summary>Q28. [Basic] How do you schedule a recurring task? <em>(asked in interview round)</em></summary>

**Answer:**

Use `cron` with `crontab -e`, or a systemd timer.

```bash
crontab -e     # edit the current user's cron jobs
crontab -l     # list them
```

```text
# minute hour day-of-month month day-of-week command
0 2 * * *   /opt/scripts/backup.sh >> /var/log/backup.log 2>&1   # every day at 02:00
*/15 * * * * /opt/scripts/health-check.sh                         # every 15 minutes
```

systemd timers (`systemctl list-timers`) are an alternative with logging in `journalctl` and catch-up of missed runs (`Persistent=true`).

**Important point:** cron runs with a minimal environment and `PATH`, so use absolute paths and redirect output to a log file.

</details>

<details><summary>Q29. [Basic] How do you check which process is using a port? <em>(asked in interview round)</em></summary>

**Answer:**

```bash
sudo ss -lntup | grep :8080        # listening TCP/UDP sockets with process
sudo lsof -i :8080                 # process holding port 8080
sudo fuser 8080/tcp                # PID using the port
```

**Important point:** run with `sudo`, otherwise the process name and PID of other users' processes are not shown. `ss` replaces the older `netstat`.

See also: [Linux networking](../linux/06-networking.md).

</details>
