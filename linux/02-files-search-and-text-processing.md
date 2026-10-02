# Linux: Files, Search, and Text Processing

> Navigating the filesystem, file operations, links, archives, finding files, grep/awk/sed text processing, pipes, redirection, and Vim.

## Key Concepts

### File System Navigation

You'll spend a lot of time navigating server filesystems, so knowing these commands well saves real time.

#### Navigation

```bash
pwd                       # Where am I?
cd /var/log               # Go to logs directory
cd ..                     # Go up one level
cd ~                      # Go home
cd -                      # Go to previous directory
```

#### File and directory operations

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

#### File viewing techniques

```bash
# Quick file inspection
cat config.yaml           # Show entire file
head -20 app.log          # First 20 lines
tail -50 error.log        # Last 50 lines
tail -f application.log   # Follow log in real-time (lifesaver for debugging)

# Paginated viewing
less large-file.txt       # Navigate large files
```

### Search and Filter: Finding Needles in Haystacks

Being able to search and filter quickly saves real time when you're troubleshooting a production issue.

#### File finding

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

#### Text processing powerhouse

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

#### Advanced text processing

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

## Interview Questions

### 1. What is the purpose of `grep`?

**Answer:**

`grep` picks out lines that match a pattern. Useful flags: `-i` for case-insensitive, `-n` for line numbers, `-r` for recursive, `-E` for extended regex, `-F` for a literal string, `-C` for surrounding context, `-v` to invert the match.

```bash
grep -nC 3 -E 'ERROR|FATAL' /var/log/app.log
zgrep -h 'request_id=abc123' /var/log/app.log*.gz
```

I narrow the search to a specific time range or set of files, and use a literal string match when the pattern comes from user input rather than a real regex. A match is just a clue, not the root cause — I compare its timestamp and details against other service and system metrics.

I'm careful not to expose secrets when sharing output. For structured logs, I'd rather use `jq` or a proper log query tool than a fragile regex.

### 2. Which `grep` flag shows lines not containing a keyword?

**Answer:**

`-v` inverts the match:

```bash
grep -vF 'health-check' access.log
grep -Ev 'DEBUG|TRACE' app.log
```

`-F` treats the keyword as a literal string; `-E` lets you use alternation and other regex features. I quote patterns carefully, and I remember `grep`'s exit code matters: 0 means it found a match, 1 means it found nothing, and anything higher means an error — which matters if a script uses `set -e`.

For binary, compressed, or rotated logs, I pick the right tool — `grep -a`, `zgrep`, or a proper log query — rather than forcing it. I keep the original log file intact rather than overwriting it just to get a filtered view.

### 3. What is the difference between `find` and `locate`?

**Answer:**

`find` walks the actual directory tree right now, and can filter by name, type, owner, time, size, permissions, and filesystem, then safely act on what it finds. For example, `find /var/log -xdev -type f -mtime +30 -print` gives current, accurate matches, but it can take a while on a big tree.

`locate '*.conf'` instead queries an index that `updatedb` built earlier, so it's very fast, but it can list files that were since deleted, or miss files that were just created, and which paths are excluded depends on its configuration. I use `locate` for a quick look and confirm with `stat`; I use `find` when I need completeness, the current state, or need to act on the results.

Before running `find` with `-delete` or `-exec`, I always run the same expression with `-print` first to see exactly what it will touch.

### 4. How do you find all files modified in the last 10 minutes?

**Answer:**

I use `find` with the `-mmin` filter:

```bash
sudo find /var/log -type f -mmin -10 -printf '%TY-%Tm-%Td %TH:%TM %s %p\n'
```

`-10` means less than ten minutes ago, while `+10` means more than ten minutes ago. I search a specific path rather than `/` first, to keep it fast and avoid permission errors everywhere.

If this is part of an incident, I sort the results and compare the modification times against when the deployment or failure happened. I don't run `-delete` right away — I look at the matches, who owns them, and what they're for first.

### 5. What are hard links and soft links?

**Answer:**

A hard link is just another directory entry pointing at the same inode. Both names are equally valid references to the same file — deleting one name leaves the data available through the other.

Hard links normally can't cross filesystems or point at directories. `ls -li` shows the shared inode number and the link count.

A symbolic link is a small separate file that just contains a target path: `ln -s /opt/app/current app`. It can cross filesystems and point at a directory, but it becomes a dangling link if the target moves.

I use symlinks for switching between versioned releases, and hard links for certain backup or deduplication setups — keeping in mind that editing a hard-linked file changes the data everywhere it's linked, since it's all the same inode.

### 6. How do you archive or compress a directory?

**Answer:**

```bash
tar -C /path/to -czf backup-$(date +%F).tar.gz directory
tar -tzf backup-2026-07-19.tar.gz | head
mkdir restore && tar -C restore -xzf backup-2026-07-19.tar.gz
sha256sum backup-2026-07-19.tar.gz > backup.sha256
```

`tar` bundles files and keeps their metadata; gzip compresses the result. I use `-C` so the archive doesn't store unwanted absolute paths, look inside the archive before extracting it, extract anything untrusted into its own isolated directory, verify the checksum, and do a test restore.

For a live database or data that's actively changing, I use an application-consistent backup instead of tarring files while they're being written to. Encryption and where backups are kept follow whatever the data policy requires.
