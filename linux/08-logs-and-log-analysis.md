# Linux: Logs and Log Analysis

> Where Linux logs live, journalctl, log rotation, reading and tailing logs, and extracting data from log files.

## Key Concepts

### System Logging Notes

Log locations vary by Linux distribution and by which service manager it uses. With systemd, you query services and the kernel with `journalctl`. Older-style files usually live under `/var/log/`, such as `syslog`, `messages`, `auth.log`, or logs specific to an application.

`tail -n 4 /var/log/messages` prints the last four lines of that file, if it exists. For centralized logging, keep timestamps, host and service identity, and access controls intact, and let `logrotate` handle retention, compression, and safely rotating large files.

## Interview Questions

### 1. What logs appear under `/var/log`?

**Answer:**

Typical examples are authentication logs (`auth.log` or `secure`), general system messages (`syslog` or `messages`), kernel messages, package manager history, `audit/audit.log`, cron logs, boot logs, and application directories like `nginx`, `apache2`, or `containers`. Rotated files usually end in `.1` or `.gz`.

The exact set depends on the distribution, because many systems now send most service output to the systemd journal instead of a flat file. I use `journalctl -u <service>`, `journalctl -p err`, and `journalctl --since ...` alongside whatever's in `/var/log`.

I check permissions and never truncate or change production logs during an investigation without preserving the evidence first.

### 2. Where are Apache logs usually located?

**Answer:**

On Debian and Ubuntu, they're usually under `/var/log/apache2/`; on RHEL-family systems, under `/var/log/httpd/`. The common files are `access.log` and `error.log`, but virtual hosts can point to separate files.

I confirm the actual path from configuration rather than assuming it:

```bash
apachectl -S
grep -R "^[[:space:]]*\(CustomLog\|ErrorLog\)" /etc/apache2 /etc/httpd 2>/dev/null
journalctl -u apache2 --since today   # or httpd
```

For a failed request, I match the timestamp, client IP, URL, and status code in the access log, then use the request ID or timestamp to find the matching entry in the error log and any upstream application logs.

### 3. How do you check logs from the last 7 days?

**Answer:**

For systemd, I give it a precise time range and unit, for example:

```bash
journalctl -u nginx --since "2026-07-12 00:00:00" --until "2026-07-19 00:00:00" -o short-iso
```

For plain log files, I first find the current and rotated files under `/var/log`. Note that `find ... -mtime -7` filters by the file's modification time, not by individual log entries. I use `grep` on plain files and `zgrep` on `.gz` files, then filter further by timestamp format, request ID, host, or severity.

I account for timezone differences and log rotation boundaries, and export a read-only copy when I need to preserve evidence from an incident.

### 4. How do you investigate a service crash using system logs?

**Answer:**

I establish which service, which host, and the exact failure window, then use `systemctl status <service>`, `journalctl -u <service> --since '30 minutes ago'`, and `journalctl -k` for kernel or OOM evidence. I compare the exit code, restart count, and any configuration, deployment, dependency, or resource changes around that time.

If it makes sense, I validate the configuration and try to reproduce it safely in a lower environment. After fixing it with a rollback, a targeted configuration change, or added capacity, I confirm the health checks pass and add an actionable alert or runbook for that failure mode.

### 5. What is log rotation?

**Answer:**

Log rotation stops a constantly growing log file from filling up the disk. Based on time or size, the current file gets renamed, older copies may be compressed, and anything past the retention limit gets deleted.

On Linux this is usually driven by `/etc/logrotate.conf` and files under `/etc/logrotate.d/`.

Before changing a rule, I test it with `logrotate -d /etc/logrotate.conf`. A service that keeps a file open needs a `postrotate` step to reload it — for example `systemctl reload nginx`. `copytruncate` is a fallback option, but it can lose a small amount of data.

I check permissions, ownership, any retention or compliance requirements, disk usage, and the next scheduled run rather than just forcing a rotation blindly.

### 6. A log file shows junk characters. How do you check and recover it?

**Answer:**

I keep a copy first, then check what the file actually is:

```bash
file app.log
xxd -l 64 app.log
gzip -t app.log.gz       # if it is expected to be gzip
```

It might be compressed, UTF-16, contain ANSI control codes, or just be a binary application log rather than corrupted text. I try a safe conversion on the copy — for example `iconv -f UTF-16 -t UTF-8 input > output` — and use `less -R`, `strings`, or the application's own log viewer as needed.

I also check for disk errors, an interrupted rotation, or multiple processes writing incompatible formats to the same file. If integrity checks fail, I restore the log from backup or a central logging system rather than overwrite the only copy of the evidence during an incident.

### 7. How do you print the last 15 lines of a file in Linux?

**Using the `tail` command**

The `tail` command prints the last part of a file.

```bash
tail -n <number_of_lines> <filename>
tail -n 15 /var/log/syslog
```

**Continuously monitor file updates (live view)**

```bash
tail -f filename.txt
```

If you want the last 15 lines of a command's output instead of a file:

```bash
dmesg | tail -n 15
```

### 8. How would you view the last few lines of a huge log file that's continuously updated?

"I'd use `tail -f logfile.log` to stream the last lines in real time."

### 9. log file processing - using tools like grep to extract IP addresses and count occurrences?

**A:** You can combine `grep` with `awk`, `sort`, and `uniq` to pull IP addresses out of log files and count how often each one appears. Here's the approach step by step:

1. **Extract the IP addresses.**

   Use `grep` with a regular expression to find IP addresses in the log file.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log
   ```

   What each part does:

   - `grep`
   - `-E` turns on extended regex
   - `-o` prints only the matching text, not the whole line
   - `'([0-9]{1,3}\.){3}[0-9]{1,3}'` matches an IPv4 address (like `10.0.0.5`)

2. **Count how often each one appears.**

   Pipe the output through `sort` and `uniq` to count each unique IP.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log | sort | uniq -c | sort -nr
   ```

   - `sort` puts the IPs in order so identical lines sit next to each other
   - `uniq -c` counts how many times each unique IP shows up
   - `sort -nr` sorts those counts from highest to lowest

   This gives you a list of IP addresses with their occurrence counts, highest first.

3. **Save the results to a file.**

   You can redirect the output to a file for later analysis.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log | sort | uniq -c | sort -nr > ip_counts.txt
   ```

4. **If the IP is always the first field on the line:**

   You can simplify the extraction with `awk` instead.

   Example:

   ```bash
   awk '{print $1}' logfile.log | sort | uniq -c | sort -nr
   ```
