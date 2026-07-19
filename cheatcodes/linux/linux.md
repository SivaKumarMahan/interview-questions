# Linux Command Cheatcode

## Files and system

```bash
pwd
ls -lah
find <path> -type f -mtime -7
date
uptime
whoami
uname -a
free -h
df -hT
df -ih
du -xhd1 <path> | sort -h
```

## Processes and I/O

```bash
ps -eo pid,ppid,user,state,%cpu,%mem,cmd --sort=-%cpu | head
top
pidstat -p <pid> 1
iostat -xz 1 5
ss -lntup
lsof +L1
journalctl -p warning --since '1 hour ago'
```

## Services

```bash
systemctl status <service>
systemctl is-active <service>
systemctl reload <service>
systemctl restart <service>
journalctl -u <service> --since '30 minutes ago'
```

Validate configuration and impact before reload/restart.

## Networking and SSH

```bash
ip -br address
ip route
dig <name>
curl -vk https://<host>/health
nc -vz <host> <port>
ssh -vvv <user>@<host>
```

## Permissions

```bash
namei -l <path>
stat <path>
getfacl <path>
chmod 0750 <path>
chown <owner>:<group> <path>
```

Avoid `chmod -R`/`chown -R` until the exact tree and symlink behavior are reviewed. Broad `chmod 777` is not a fix.

## Large files and log cleanup

```bash
# Ten largest files under /var/log (allocated size)
sudo find /var/log -xdev -type f -exec du -h -- {} + 2>/dev/null \
  | sort -hr | head -n 10

# Ten largest files on the root filesystem
sudo find / -xdev -type f -exec du -h -- {} + 2>/dev/null \
  | sort -hr | head -n 10

# .log files larger than 100 MiB
sudo find /var/log -xdev -type f -name '*.log' -size +100M -print

# Preview .log files older than 30 days
sudo find /var/log -xdev -type f -name '*.log' -mtime +30 -print

# Delete only after preview, approval, retention checks and backup verification
sudo find /var/log -xdev -type f -name '*.log' -mtime +30 -delete
```

Prefer application retention, `logrotate`, or journald settings over manual deletion. Check open-deleted files with `sudo lsof +L1`; deleting an open file may not release disk space until its process closes the descriptor.

## Highest-memory processes

```bash
# Header plus ten processes, sorted by resident memory
ps -eo pid,ppid,user,%mem,rss,vsz,etime,cmd --sort=-rss | head -n 11

# Short alternative
ps aux --sort=-%mem | head -n 11

free -h
vmstat 1
pidstat -r -p <pid> 1
journalctl -k | grep -i oom
```
