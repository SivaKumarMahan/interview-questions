# Shell Scripting: Cheat Sheet and Interview Scripts

> A quick-revision Bash cheat sheet (syntax, tests, conditionals, loops, functions, text tools, one-liners, debugging), then the scripts interviewers most often ask you to write: CPU monitoring and alert email, service auto-restart, Kubernetes Pod check, log cleanup with cron, and short output and syntax questions.

## Key Concepts

### Script basics

```bash
#!/usr/bin/env bash        # shebang: finds bash in PATH (or #!/bin/bash)
# full-line comment
echo "hi"                  # inline comment

chmod +x script.sh
./script.sh                # needs the execute bit (and read)
bash script.sh             # no execute bit needed
```

Without a shebang, the script runs in whatever shell started it.

### Variables, input and arguments

```bash
NAME="DevOps"              # no spaces around =
echo "$NAME"               # DevOps   (double quotes expand)
echo '$NAME'               # $NAME    (single quotes are literal)
read -r -p "Name: " name   # read user input (-p is bash)

$0          # script name
$1 $2       # first and second argument
$#          # number of arguments
"$@"        # all arguments, each kept separate
$?          # exit status of the last command
${1:-x}     # "x" if $1 is empty or unset
```

Always quote variables: `"$VAR"`.

### Tests: strings, numbers, files

| Test | Meaning |
| --- | --- |
| `[ "$a" = "$b" ]`, `[ "$a" != "$b" ]` | Strings equal / not equal |
| `[ -z "$s" ]`, `[ -n "$s" ]` | String empty / not empty |
| `-eq -ne -lt -gt -le -ge` | Integer comparisons: `[ "$n" -gt 5 ]` |
| `-f file`, `-d dir`, `-e path` | Regular file, directory, exists |
| `-s file` | File exists and size > 0 |
| `-r -w -x` | Readable, writable, executable |

Spaces inside `[ ]` are required: `[ -f file ]`, not `[-f file]`.

### Conditionals, logic and case

```bash
if [ "$n" -gt 0 ]; then
  echo "positive"
elif [ "$n" -eq 0 ]; then
  echo "zero"
else
  echo "negative"
fi

[ -f f ] && echo yes        # AND: run if the test succeeded
[ -f f ] || echo no         # OR: run if it failed
[ ! -d dir ]                # NOT

case "$1" in
  start)     echo "starting" ;;
  stop|quit) echo "stopping" ;;
  *)         echo "usage: $0 start|stop" ;;
esac
```

In `case`, `|` separates alternatives, `*` is the default and `;;` ends each branch.

`[[ ]]` works in bash, zsh and ksh but not plain `sh`. It does not word-split and supports patterns:

```bash
[[ $f == *.log ]]              # glob match
[[ $v =~ ^[a-z]+[0-9]+$ ]]     # regex
[[ $a == x && $b == y ]]       # && inside
```

### Loops

```bash
for i in 1 2 3; do echo "$i"; done
for ((i=0; i<3; i++)); do echo "$i"; done
while [ "$n" -gt 0 ]; do n=$((n-1)); done     # runs while true
until [ "$n" -ge 3 ]; do n=$((n+1)); done     # runs until true
break        # leave the loop
continue     # jump to the next round

for f in *.log; do
  [ -e "$f" ] || continue      # if nothing matches, *.log stays literal
  echo "$f"
done

while IFS= read -r line; do    # lines of a file
  echo "$line"
done < file.txt

while IFS= read -r l; do       # lines of a command
  echo "$l"
done < <(command)
```

In bash, `cmd | while read ...` runs the loop in a subshell, so variables set inside it are lost after the loop. Use `done < <(cmd)` instead.

### Functions

```bash
greet() {
  local name=$1               # local keeps the variable inside the function
  echo "Hello, $name"
}
greet DevOps

add() { echo $(( $1 + $2 )); }
sum=$(add 2 3)                # 5: pass values back with echo and $( )
is_even() { (( $1 % 2 == 0 )); }
if is_even 4; then echo even; fi
```

`return` only sets a status from 0 to 255. Declare and assign separately (`local x; x=$(cmd)`), otherwise `local` hides the command's exit status.

### Text tools

```bash
grep -rniE "error|fail" /var/log/app   # recursive, line numbers, ignore case, extended regex
grep -c ERROR app.log                  # count
grep -v DEBUG app.log                  # exclude

awk '{print $1}' file                  # column 1
awk -F: '{print $1}' /etc/passwd       # custom separator
awk '$3 > 100' file                    # filter rows
awk 'BEGIN{print "go"} END{print NR}' f

sed 's/old/new/g' file                 # replace
sed '/DEBUG/d' file                    # delete matching lines
sed -n '2,3p' file                     # print lines 2-3
sed -i.bak 's/a/b/g' file              # edit in place, keep a backup

cut -d: -f1 /etc/passwd                # field 1
sort f; sort -n f; sort -r f; sort -u f
sort f | uniq; sort f | uniq -c        # uniq only removes ADJACENT duplicates
tr 'a-z' 'A-Z'; tr -d '\r'; tr -s ' '
wc -l; wc -w; wc -c
head -n 5 f; tail -n 5 f; tail -f app.log
```

### One-liners

```bash
# Delete logs older than 7 days (run with -print first to see what would go)
find /var/log/app -name "*.log" -mtime +7 -delete

# Count lines in all logs
cat *.log | wc -l

# Replace a string in many files
find . -name "*.txt" -exec sed -i.bak 's/foo/bar/g' {} +

# Top 5 values in a column (for example client IPs)
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5

# Is a service running?
systemctl is-active --quiet nginx && echo up || echo down
pgrep -x nginx > /dev/null && echo up          # without systemd

# Disk usage alert
df -hP / | awk 'NR==2 {gsub("%","",$5); if ($5+0 > 80) print "Disk high:", $5 "%"}'

# Watch errors live
tail -f app.log | grep --line-buffered ERROR

# CSV and JSON
cut -d, -f2 file.csv          # simple CSV only (no quoted commas)
jq -r '.name' file.json       # jq is a separate tool
```

### Errors and debugging

```bash
exit 0 / exit 1            # success / failure
echo $?                    # last exit status
set -e                     # exit on error
set -u                     # unset variable is an error
set -o pipefail            # a pipeline fails if any part fails
set -x                     # print every command (trace)
set -euo pipefail          # common combination

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT   # cleanup on exit, errors and Ctrl+C (not kill -9)
```

`set -e` is ignored inside `if` conditions and in `&&` / `||` lists, so check important steps explicitly. Run `shellcheck script.sh` before committing scripts.

### Quick reference

| Item | Syntax |
| --- | --- |
| Variable | `NAME="DevOps"` |
| Argument | `./script.sh arg1` → `$1` |
| If | `if [ -f file ]; then ... fi` |
| For loop | `for i in 1 2 3; do ... done` |
| Function | `greet() { echo "Hi"; }` |
| Grep | `grep -i "error" log.txt` |
| Awk | `awk -F: '{print $1}' /etc/passwd` |
| Sed | `sed -i.bak 's/foo/bar/g' f.txt` |

## Interview Questions

<details><summary>Q1. [Basic] What is the output of <code>echo hi || echo hello</code>, and what is the risk in <code>a &amp;&amp; b || c</code>?</summary>

**Answer:**

The output is only `hi`. `||` runs the right side only if the left side **fails**; `echo hi` succeeds (exit status 0), so `echo hello` never runs.

| Expression | Output |
| --- | --- |
| `echo hi \|\| echo hello` | `hi` |
| `echo hi && echo hello` | `hi` then `hello` |
| `false \|\| echo hello` | `hello` |
| `false && echo hello` | nothing |

The trap: `a && b || c` is **not** a real if-else. `c` also runs when `a` succeeds but `b` fails:

```bash
true && false || echo "this still prints"
```

Use a real `if a; then b; else c; fi` when the difference matters.

</details>

<details><summary>Q2. [Basic] What does <code>-mtime +7</code> mean in <code>find</code>?</summary>

**Answer:**

`-mtime` tests a file's **modification time** in whole 24-hour periods:

| Option | Meaning |
| --- | --- |
| `-mtime +7` | Modified **more than 7** full days ago (in practice 8 days or older) |
| `-mtime 7` | Exactly 7 full days ago |
| `-mtime -7` | Less than 7 days ago |
| `-mmin -30` | Modified in the last 30 minutes |

Because the age is rounded down to whole days, `+7` matches files that are at least 8 × 24 hours old. Related options: `-atime` (last access) and `-ctime` (last status change). Example:

```bash
find /var/log/myapp -type f -name "*.log" -mtime +7 -print     # check first
find /var/log/myapp -type f -name "*.log" -mtime +7 -delete
find /var/log -type f -size +50M -mtime +30 -delete           # larger than 50 MB and older than 30 days
```

</details>

<details><summary>Q3. [Intermediate] Write a shell script to monitor CPU utilization and send an email when it goes above 90%.</summary>

**Answer:**

```bash
#!/usr/bin/env bash
# cpu_alert.sh - alert when CPU usage is above a threshold
set -euo pipefail

THRESHOLD=${1:-90}
EMAIL="oncall@example.com"
HOST=$(hostname)

# Read /proc/stat twice, one second apart, and compare busy time with total time.
read -r _ u1 n1 s1 i1 w1 x1 y1 z1 _ < /proc/stat
sleep 1
read -r _ u2 n2 s2 i2 w2 x2 y2 z2 _ < /proc/stat

idle=$(( (i2 + w2) - (i1 + w1) ))
total=$(( (u2+n2+s2+i2+w2+x2+y2+z2) - (u1+n1+s1+i1+w1+x1+y1+z1) ))
usage=$(( 100 * (total - idle) / total ))

echo "$(date '+%F %T') CPU usage: ${usage}%"

if (( usage > THRESHOLD )); then
  top_procs=$(ps -eo pid,user,%cpu,%mem,cmd --sort=-%cpu | head -n 6)
  printf 'CPU usage on %s is %s%% (threshold %s%%).\n\nTop processes:\n%s\n' \
    "$HOST" "$usage" "$THRESHOLD" "$top_procs" \
    | mail -s "ALERT: CPU ${usage}% on ${HOST}" "$EMAIL"
fi
```

Schedule it every 5 minutes with cron:

```text
*/5 * * * * /usr/local/bin/cpu_alert.sh 90 >> /var/log/cpu_alert.log 2>&1
```

Points to mention:

- Reading `/proc/stat` avoids parsing `top` output, which differs between versions. A simpler version is `top -bn1 | grep "Cpu(s)"` or `mpstat 1 1`.
- `mail` needs a mail agent (`mailutils` or `s-nail` plus Postfix or an SMTP relay). In the cloud I would send to a Slack or Teams webhook with `curl` instead.
- A single sample can spike; to avoid noise, alert only after several consecutive high readings.
- In production I use Prometheus with Alertmanager or Azure Monitor alerts, and keep scripts like this for hosts without an agent.

</details>

<details><summary>Q4. [Intermediate] Write a shell script that monitors a service and restarts it automatically if it goes down.</summary>

**Answer:**

```bash
#!/usr/bin/env bash
# service_watchdog.sh - restart a service if it is not active
set -uo pipefail

SERVICE=${1:?usage: $0 <service-name>}
LOG=/var/log/service_watchdog.log
MAX_RETRIES=3

log() { echo "$(date '+%F %T') [$SERVICE] $*" >> "$LOG"; }

if systemctl is-active --quiet "$SERVICE"; then
  exit 0
fi

log "service is down, attempting restart"
for attempt in $(seq 1 "$MAX_RETRIES"); do
  systemctl restart "$SERVICE"
  sleep 5
  if systemctl is-active --quiet "$SERVICE"; then
    log "restarted successfully on attempt $attempt"
    exit 0
  fi
  log "restart attempt $attempt failed"
done

log "service still down after $MAX_RETRIES attempts"
journalctl -u "$SERVICE" -n 50 --no-pager >> "$LOG"
# send an alert here (mail, Slack or Teams webhook)
exit 1
```

Run it every minute from root's crontab: `* * * * * /usr/local/bin/service_watchdog.sh nginx`.

Better option for systemd services: let systemd do it, with a drop-in (`sudo systemctl edit nginx`):

```ini
[Service]
Restart=on-failure
RestartSec=5
```

`systemctl is-active` only proves the process is alive. For a real health check, also test the endpoint, for example `curl -fsS --max-time 5 http://localhost/health`, and restart if that fails.

</details>

<details><summary>Q5. [Intermediate] Write a shell script to check whether a Kubernetes Pod is running.</summary>

**Answer:**

```bash
#!/usr/bin/env bash
# check_pods.sh - check that all Pods of an app are Running and Ready
set -euo pipefail

NAMESPACE=${1:-default}
APP_LABEL=${2:?usage: $0 <namespace> <app-label>}

pods=$(kubectl get pods -n "$NAMESPACE" -l "app=$APP_LABEL" \
  -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.phase}{" "}{.status.containerStatuses[*].ready}{"\n"}{end}')

if [ -z "$pods" ]; then
  echo "No pods found for app=$APP_LABEL in $NAMESPACE"
  exit 2
fi

failed=0
while read -r name phase ready; do
  if [ "$phase" = "Running" ] && [[ "$ready" != *false* ]]; then
    echo "OK    $name ($phase, ready)"
  else
    echo "FAIL  $name (phase=$phase ready=$ready)"
    failed=1
  fi
done <<< "$pods"

exit "$failed"
```

Simpler checks for a pipeline:

```bash
kubectl rollout status deployment/myapp -n prod --timeout=120s
kubectl wait --for=condition=Ready pod -l app=myapp -n prod --timeout=120s
```

A Pod can show `Running` while a container is not ready or is restarting, so check readiness (and the restart count) rather than only the phase.

</details>

<details><summary>Q6. [Basic] Write a script for weekly log cleanup, and schedule it to run every week.</summary>

**Answer:**

```bash
#!/usr/bin/env bash
# log_cleanup.sh - compress logs older than 1 day, delete logs older than 30 days
set -euo pipefail

LOG_DIR=${1:-/var/log/myapp}
RETENTION_DAYS=30

[ -d "$LOG_DIR" ] || { echo "Directory $LOG_DIR not found"; exit 1; }

echo "$(date '+%F %T') cleanup started in $LOG_DIR"
before=$(du -sh "$LOG_DIR" | cut -f1)

find "$LOG_DIR" -type f -name "*.log" -mtime +1 -exec gzip -q {} \;
find "$LOG_DIR" -type f -name "*.gz" -mtime +"$RETENTION_DAYS" -print -delete

after=$(du -sh "$LOG_DIR" | cut -f1)
echo "$(date '+%F %T') cleanup finished: $before -> $after"
```

Schedule it every Sunday at 02:00 with `crontab -e`:

```text
0 2 * * 0 /usr/local/bin/log_cleanup.sh /var/log/myapp >> /var/log/log_cleanup.log 2>&1
```

Cron fields are minute, hour, day of month, month and day of week (`0` = Sunday). Alternatives: `@weekly`, a script in `/etc/cron.weekly/`, or a systemd timer with `OnCalendar=weekly`.

Points to mention: compressing a file that the application still writes to can lose lines, so for active logs use logrotate (see [Linux sysadmin scenarios](../linux/11-sysadmin-scenarios.md)). Always test with `-print` before `-delete`, and use full paths in cron because cron has a minimal `PATH`.

</details>

<details><summary>Q7. [Basic] Write a script to count the ERROR lines in a log file, in Bash and in Python.</summary>

**Answer:**

Bash:

```bash
grep -c "ERROR" app.log
grep -o "ERROR.*" app.log | sort | uniq -c | sort -rn | head    # most frequent errors
```

Python:

```python
from collections import Counter

count = 0
messages = Counter()
with open("app.log", encoding="utf-8", errors="replace") as f:
    for line in f:              # reads one line at a time, so large files are fine
        if "ERROR" in line:
            count += 1
            messages[line.split("ERROR", 1)[1].strip()[:80]] += 1

print("Total ERROR messages:", count)
for msg, n in messages.most_common(5):
    print(n, msg)
```

Reading line by line keeps memory use low even for multi-gigabyte logs.

</details>

<details><summary>Q8. [Intermediate] Why are variables set inside <code>cmd | while read</code> lost, and why should you write <code>local x; x=$(cmd)</code>?</summary>

**Answer:**

**Pipes create subshells.** In bash, every part of a pipeline runs in its own subshell, so a counter changed inside `while` disappears when the loop ends:

```bash
count=0
grep ERROR app.log | while read -r line; do count=$((count+1)); done
echo "$count"          # prints 0

count=0
while read -r line; do count=$((count+1)); done < <(grep ERROR app.log)
echo "$count"          # correct value
```

**`local` hides exit status.** `local x=$(cmd)` returns the status of `local` (always 0), so `set -e` and `$?` do not see a failing `cmd`:

```bash
f() {
  local out
  out=$(false)         # now set -e and $? see the failure
}
```

The same applies to `export VAR=$(cmd)`.

</details>

<details><summary>Q9. [Basic] What do the grep options -v, -i, -r, -c, -o and -E do? Give an example of each.</summary>

**Answer:**

`grep` prints the lines that match a pattern. `-v` inverts the match, `-i` ignores case, `-r` searches directories recursively, `-c` counts matching lines, `-o` prints only the matched text, and `-E` enables extended regular expressions.

All examples use this `app.log`:

```text
INFO Application started
ERROR Database connection failed
INFO User logged in
error Timeout occurred
WARNING High memory usage
ERROR Service unavailable
```

**1. `grep`: find matching lines**

```bash
grep "ERROR" app.log
```

```text
ERROR Database connection failed
ERROR Service unavailable
```

Use case: find errors in application logs. The search is case-sensitive, so `error Timeout occurred` is not shown.

**2. `grep -v`: exclude matching lines**

```bash
grep -v "ERROR" app.log
```

```text
INFO Application started
INFO User logged in
error Timeout occurred
WARNING High memory usage
```

Use case: remove noise, for example `grep -v DEBUG app.log`, or drop comment lines with `grep -v '^#' nginx.conf`.

**3. `grep -i`: ignore upper and lower case**

```bash
grep -i "error" app.log
```

```text
ERROR Database connection failed
error Timeout occurred
ERROR Service unavailable
```

Use case: the same word appears as `ERROR`, `Error` or `error`.

**4. `grep -r`: search directories recursively**

```bash
grep -r "ERROR" /var/log/myapp/
```

```text
/var/log/myapp/app.log:ERROR Database connection failed
/var/log/myapp/archive/old.log:ERROR Disk full
```

Each match is prefixed with its file name. Add `-n` for line numbers, `-l` to list only the file names, and `--include="*.log"` to search only log files.

**5. `grep -c`: count matching lines**

```bash
grep -c "ERROR" app.log
```

```text
2
```

`-c` counts matching **lines**, not every occurrence: a line with `ERROR` twice counts once. To count every occurrence, use `grep -o "ERROR" app.log | wc -l`.

**6. `grep -o`: print only the matching text**

With a `users.log` containing:

```text
User ID: 101 logged in
User ID: 102 logged in
User ID: 103 logged out
```

```bash
grep -oE '[0-9]+' users.log
```

```text
101
102
103
```

Use `[0-9]+` (one or more digits) rather than `[0-9]*`, because `*` also matches an empty string. Use case: extract IDs or IP addresses, for example `grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' access.log | sort | uniq -c | sort -rn | head`.

**7. `grep -E`: extended regular expressions**

```bash
grep -E "ERROR|WARNING" app.log
```

```text
ERROR Database connection failed
WARNING High memory usage
ERROR Service unavailable
```

With `-E`, `|` means OR, and `+`, `?`, `{n}` and `( )` work without backslashes. Without `-E` you need `grep "ERROR\|WARNING"` (GNU grep) or `grep -e ERROR -e WARNING`.

**Quick revision:**

| Option | Meaning | Example |
| --- | --- | --- |
| (none) | Show matching lines | `grep "ERROR" app.log` |
| `-v` | Show lines that do not match | `grep -v "ERROR" app.log` |
| `-i` | Ignore case | `grep -i "error" app.log` |
| `-r` | Search directories recursively | `grep -r "ERROR" /var/log/` |
| `-c` | Count matching lines | `grep -c "ERROR" app.log` |
| `-o` | Print only the matched text | `grep -oE '[0-9]+' users.log` |
| `-E` | Extended regex | `grep -E "ERROR\|WARNING" app.log` |
| `-n` | Show line numbers | `grep -n "ERROR" app.log` |

In the table, `\|` only stops Markdown from splitting the cell; type a plain `|` in the terminal.

**Practical DevOps example (Kubernetes Pod logs):**

```bash
kubectl logs my-pod | grep -i "error"                 # error lines, any case
kubectl logs my-pod | grep -ic "error"                # how many
kubectl logs my-pod | grep -iv "health"               # hide health-check noise
kubectl logs my-pod --since=1h | grep -iE "error|exception|timeout"
```

**Interview-ready answer:**

> "`grep` filters lines that match a pattern. I use `-i` for case-insensitive searches, `-v` to exclude noise such as debug or health-check lines, `-r` to search a whole log directory, `-c` to count matching lines, `-o` to extract just the matched value such as an ID or IP address, and `-E` for extended patterns like `ERROR|WARNING`. For example, `kubectl logs my-pod | grep -iE 'error|exception'` quickly shows the problems in a Pod's logs. One detail: `-c` counts lines, so to count every occurrence I use `grep -o pattern file | wc -l`."

</details>

<details><summary>Q10. [Basic] What is awk, and how do you use it to print columns, filter rows and calculate totals?</summary>

**Answer:**

`awk` is a small programming language for text in columns. It reads input line by line, splits each line into fields, and runs `pattern { action }` rules on it. `$1` is the first field, `$3` the third and `$0` the whole line. It can also aggregate (sums, counts, grouping) in one pass, which is why it is the right tool whenever the data has columns: `df`, `ps`, CSV files, access logs.

**1. Print a column**

`servers.txt`:

```text
web01 192.168.1.10 Running
web02 192.168.1.11 Stopped
web03 192.168.1.12 Running
```

| `$1` | `$2` | `$3` |
| --- | --- | --- |
| web01 | 192.168.1.10 | Running |

```bash
awk '{print $3}' servers.txt
```

```text
Running
Stopped
Running
```

By default, fields are separated by spaces or tabs (any number of them).

**2. Print several columns**

```bash
awk '{print $1, $3}' servers.txt
```

```text
web01 Running
web02 Stopped
web03 Running
```

The comma prints a space between fields. Use `printf` for aligned output: `awk '{printf "%-8s %s\n", $1, $3}' servers.txt`.

**3. Filter rows with a condition**

```bash
awk '$3 == "Running" {print $1}' servers.txt
```

```text
web01
web03
```

`awk` checks column 3 and prints column 1 only when the condition is true. Regex filters work too: `awk '/Stopped/ {print $1}' servers.txt`.

**4. Sum a column**

`memory.txt`:

```text
server memory
web01 40
web02 60
web03 75
```

```bash
awk 'NR > 1 {sum += $2} END {print sum}' memory.txt
```

```text
175
```

- `NR` is the current line (record) number, so `NR > 1` skips the header.
- `sum += $2` adds column 2 to a running total.
- `END { }` runs once after all lines are read; `BEGIN { }` runs once before.

Average: `awk 'NR > 1 {sum += $2; n++} END {print sum / n}' memory.txt` prints `58.3333`.

**5. Count matching rows**

```bash
awk '$3 == "Running" {count++} END {print count + 0}' servers.txt
```

```text
2
```

`count + 0` prints `0` instead of an empty line when nothing matches.

**6. CSV files with `-F`**

`employees.csv`:

```text
Name,Department,Salary
Ravi,DevOps,60000
Kumar,Testing,45000
Priya,DevOps,70000
```

```bash
awk -F ',' 'NR > 1 {print $1}' employees.csv
awk -F ',' 'NR > 1 && $2 == "DevOps" {print $1, $3}' employees.csv
awk -F ',' 'NR > 1 {total[$2] += $3} END {for (d in total) print d, total[d]}' employees.csv
```

```text
Ravi
Kumar
Priya

Ravi 60000
Priya 70000

DevOps 130000
Testing 45000
```

The last command groups by department with an associative array; the order of a `for (d in total)` loop is not guaranteed, so pipe to `sort` if order matters. `-F ','` only handles simple CSV; quoted fields that contain commas need a real CSV parser.

**7. Practical DevOps example: disk usage**

```bash
df -hP | awk 'NR > 1 {print $1, $5}'
```

```text
/dev/sda1 65%
/dev/sdb1 82%
```

Only filesystems above 80%:

```bash
df -hP | awk 'NR > 1 && $5+0 > 80 {print $6, $5}'
```

```text
/data 82%
```

`$5+0` turns `82%` into the number `82` for the comparison. `-P` (POSIX format) keeps each filesystem on one line, so long device names do not wrap and shift the columns.

More one-liners you will use:

```bash
awk -F: '$3 >= 1000 {print $1}' /etc/passwd                     # normal (non-system) users
ps aux | awk 'NR > 1 {mem[$1] += $4} END {for (u in mem) print u, mem[u] "%"}'   # memory % per user
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5   # top 5 client IPs
awk '$9 >= 500 {count++} END {print count + 0}' access.log         # HTTP 5xx count (combined log format)
```

**Quick revision:**

| Syntax | Meaning |
| --- | --- |
| `$1`, `$2`, `$NF` | First field, second field, last field |
| `$0` | The whole line |
| `-F ','` | Use a comma as the field separator |
| `NR` | Current line number |
| `NF` | Number of fields in the line |
| `BEGIN { }` | Runs before reading input |
| `END { }` | Runs after all input |
| `sum += $2` | Add column 2 to a total |
| `count++` | Increase a counter |
| `arr[$1] += $2` | Group and sum by a key |

**Interview-ready answer:**

> "`awk` is a text-processing language for column-based data. It splits every line into fields, so `awk '{print $3}'` prints the third column, and I can add conditions such as `$3 == "Running"` to filter rows. With `NR`, `BEGIN` and `END` it can skip headers and calculate sums, averages or counts in a single pass, and with arrays it can group values, for example memory per user from `ps aux`. A typical use is `df -hP | awk 'NR > 1 && $5+0 > 80 {print $6, $5}'` to list filesystems above 80% usage. I use `grep` to find lines, `awk` to work with columns and calculations, and `sed` to edit text."

</details>

<details><summary>Q11. [Basic] What is sed, and how do you use it to replace, delete and print lines?</summary>

**Answer:**

`sed` is a **stream editor**: it reads text line by line, applies editing commands, and writes the result to standard output. Its most common use is substitution with `sed 's/old/new/g'`, plus deleting or printing lines and line ranges. By default it **does not change the file**; it only prints the edited text, unless you use `-i`.

**1. Search and replace**

`app.conf`:

```text
environment=dev
server=web01
environment=dev
```

```bash
sed 's/dev/prod/g' app.conf
```

```text
environment=prod
server=web01
environment=prod
```

- `s` means substitute.
- `dev` is the pattern to find (a regular expression).
- `prod` is the replacement.
- `g` replaces every occurrence on each line, not just the first.

**2. Replace only the first occurrence on each line**

```bash
echo "dev dev dev" | sed 's/dev/prod/'
```

```text
prod dev dev
```

Without `g`, only the first match on each line is replaced. `s/dev/prod/2` replaces only the second one.

**3. Change the file itself with `-i`**

```bash
sed -i 's/dev/prod/g' app.conf        # edit in place
sed -i.bak 's/dev/prod/g' app.conf    # edit in place and keep app.conf.bak
```

Always run the command **without** `-i` first and check the output, or compare afterwards with `diff app.conf.bak app.conf`. On macOS (BSD `sed`), in-place editing without a backup is `sed -i '' 's/dev/prod/g' app.conf`.

**4. Delete lines that match a pattern**

`app.conf`:

```text
server=web01
debug=true
port=8080
```

```bash
sed '/debug/d' app.conf
```

```text
server=web01
port=8080
```

`d` means delete. Common uses: `sed '/^#/d' nginx.conf` removes comment lines, and `sed '/^$/d' file` removes empty lines.

**5. Delete lines by number**

```bash
sed '2d' app.conf       # delete line 2
sed '2,4d' app.conf     # delete lines 2 to 4
sed '$d' app.conf       # delete the last line
```

These print the remaining lines; the file is unchanged unless you add `-i`.

**6. Print a line or a range**

```bash
sed -n '2p' app.conf              # only line 2
sed -n '2,4p' app.conf            # lines 2 to 4
sed -n '/START/,/END/p' app.log   # from a line matching START to the next line matching END
```

`-n` turns off automatic printing, and `p` prints the selected lines. `sed -n '100,200p' big.log` is a quick way to view part of a large log file.

**7. Practical DevOps example: change an application port**

`app.env`:

```text
APP_PORT=8080
HEALTH_URL=http://localhost:8080/health
```

`sed 's/8080/9090/' app.env` would change **both** lines, which may not be what you want. Match the key instead of the value:

```bash
sed -i 's/^APP_PORT=.*/APP_PORT=9090/' app.env
```

```text
APP_PORT=9090
HEALTH_URL=http://localhost:8080/health
```

`^` anchors the match to the start of the line and `.*` matches the old value, whatever it was. This is safer than replacing a bare number or word: for example, `s/dev/prod/g` would also turn `devops-team` into `prodops-team`.

**8. Practical example: replace a URL**

```bash
sed 's|http://dev\.example\.com|https://prod.example.com|g' app.env
```

```text
API_URL=https://prod.example.com
```

`|` is used as the separator instead of `/`, so the slashes in the URL do not need escaping. In the pattern, `.` matches any character, so escape it as `\.` to match a literal dot.

**9. Use a variable in a pipeline**

```bash
IMAGE_TAG="1.4.2"
sed -i "s|^\(\s*image:\s*myregistry/api:\).*|\1${IMAGE_TAG}|" k8s/deployment.yaml
```

Use double quotes so `${IMAGE_TAG}` expands. `\( \)` captures the part to keep, and `\1` puts it back. For structured files (YAML, JSON), prefer `yq`, `jq`, Helm values or Kustomize; `sed` is fine for simple key=value files and one-off fixes.

**Quick revision:**

| Command | Purpose |
| --- | --- |
| `sed 's/old/new/g' file` | Replace all occurrences on each line |
| `sed 's/old/new/' file` | Replace the first occurrence on each line |
| `sed -i 's/old/new/g' file` | Edit the file in place |
| `sed -i.bak 's/old/new/g' file` | Edit in place and keep a backup |
| `sed 's\|old\|new\|g' file` | Use `\|` as the separator (paths and URLs) |
| `sed '/pattern/d' file` | Delete matching lines |
| `sed '2d' file`, `sed '2,4d' file` | Delete line 2, or lines 2 to 4 |
| `sed -n '2p' file` | Print only line 2 |
| `sed -n '2,4p' file` | Print lines 2 to 4 |
| `sed -n '/START/,/END/p' file` | Print a block between two patterns |

In the table, `\|` only stops Markdown from splitting the cell; type a plain `|` in the terminal.

**grep, awk or sed?** Use `grep` to find lines, `awk` to work with columns and calculations, and `sed` to change text.

**Interview-ready answer:**

> "`sed` is a stream editor that searches, replaces, deletes or prints text line by line. For example, `sed 's/dev/prod/g' app.conf` replaces `dev` with `prod` in the output, and `sed -n '2,4p'` prints lines 2 to 4. It does not change the file unless I use `-i`, so I always run the command without `-i` first, and in scripts I use `-i.bak` to keep a backup. In deployments I anchor the pattern to the key, for example `s/^APP_PORT=.*/APP_PORT=9090/`, so I don't accidentally replace the same value elsewhere in the file. For YAML or JSON I prefer `yq` or `jq`, because they understand the structure."

</details>

<details><summary>Q12. [Basic] How do you use cut, sort and uniq, and what does <code>sort | uniq -c | sort -rn</code> do?</summary>

**Answer:**

- `cut` extracts fields by a delimiter (or characters by position). It is simpler and faster than `awk` when you only need a column and the delimiter is consistent.
- `sort` orders lines alphabetically, numerically or in reverse.
- `uniq` removes or counts **adjacent** duplicate lines, so it is almost always used after `sort`.
- `sort | uniq -c | sort -rn` is the standard "count and rank" pipeline.

**1. `cut`: extract columns:**

`servers.csv`:

```text
web01,192.168.1.10,Running
web02,192.168.1.11,Stopped
web03,192.168.1.12,Running
```

```bash
cut -d ',' -f1 servers.csv       # first field
```

```text
web01
web02
web03
```

```bash
cut -d ',' -f2 servers.csv       # second field
```

```text
192.168.1.10
192.168.1.11
192.168.1.12
```

```bash
cut -d ',' -f1,3 servers.csv     # fields 1 and 3
```

```text
web01,Running
web02,Stopped
web03,Running
```

- `-d ','` sets the delimiter (one character only; the default is a tab).
- `-f1` selects field 1; `-f1,3` selects fields 1 and 3; `-f2-` selects field 2 to the end.

**By character position:** with `ids.txt` containing `SERVER101`, `SERVER102` and `SERVER103`:

```bash
cut -c7-9 ids.txt
```

```text
101
102
103
```

**Real examples:**

```bash
cut -d: -f1 /etc/passwd          # all user names
cut -d: -f1,7 /etc/passwd        # user name and login shell
```

**Limit:** `cut` treats every delimiter as a field boundary, so it fails on output aligned with several spaces, such as `ps` or `df`. There, use `awk '{print $2}'` or squeeze the spaces first with `tr -s ' ' | cut -d ' ' -f2`.

**2. `sort`: order lines:**

`names.txt` contains `Ravi`, `Anitha`, `Siva` and `Kumar`; `numbers.txt` contains `100`, `20`, `3` and `50`.

| Command | Output (one value per line) | Meaning |
| --- | --- | --- |
| `sort names.txt` | Anitha, Kumar, Ravi, Siva | Alphabetical |
| `sort -r names.txt` | Siva, Ravi, Kumar, Anitha | Reverse |
| `sort numbers.txt` | 100, 20, 3, 50 | Alphabetical, so wrong for numbers |
| `sort -n numbers.txt` | 3, 20, 50, 100 | Numeric |
| `sort -rn numbers.txt` | 100, 50, 20, 3 | Largest first |

Other useful options:

```bash
sort -u file                     # sort and remove duplicates
sort -h sizes.txt                # human-readable sizes: 512K < 20M < 1G
sort -t, -k3 -n data.csv         # by field 3, comma-separated
du -sh /var/log/* | sort -rh | head -5   # five largest items
```

**3. `uniq`: remove or count adjacent duplicates:**

`errors.txt`:

```text
ERROR
ERROR
WARNING
ERROR
WARNING
WARNING
```

```bash
uniq errors.txt
```

```text
ERROR
WARNING
ERROR
WARNING
```

The third `ERROR` is still there, because `uniq` only compares each line with the one before it.

```bash
uniq -c errors.txt               # count adjacent runs
```

```text
      2 ERROR
      1 WARNING
      1 ERROR
      2 WARNING
```

```bash
sort errors.txt | uniq -c        # sort first to count every value correctly
```

```text
      3 ERROR
      3 WARNING
```

Other options: `uniq -d` prints only values that are duplicated, and `uniq -u` prints only values that appear once.

**4. Count and rank: `sort | uniq -c | sort -rn`:**

`ip.log`:

```text
10.0.0.1
10.0.0.2
10.0.0.1
10.0.0.3
10.0.0.1
10.0.0.2
```

```bash
sort ip.log | uniq -c | sort -rn
```

```text
      3 10.0.0.1
      2 10.0.0.2
      1 10.0.0.3
```

```text
sort      ->  groups identical lines together
uniq -c   ->  counts each group
sort -rn  ->  ranks by count, highest first
head      ->  keeps the top N (optional)
```

**Practical DevOps examples:**

```bash
# Top 5 client IPs in an Nginx access log (the IP is the first field)
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5

# Most common HTTP status codes
awk '{print $9}' access.log | sort | uniq -c | sort -rn

# Most frequent error messages
grep ERROR app.log | cut -d ' ' -f3- | sort | uniq -c | sort -rn | head

# Login shells in use
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn
```

The top-IP list helps find heavy clients or suspicious patterns, but a high request count alone does not prove an attack: it can be a proxy, a NAT gateway or a health checker.

**Quick revision:**

| Command | Purpose |
| --- | --- |
| `cut -d ',' -f1 file.csv` | First comma-separated field |
| `cut -d ',' -f1,3 file.csv` | Fields 1 and 3 |
| `cut -c1-5 file.txt` | First five characters |
| `sort file.txt` | Sort alphabetically |
| `sort -n file.txt` | Sort numerically |
| `sort -rn file.txt` | Largest number first |
| `sort -u file.txt` | Sort and remove duplicates |
| `uniq file.txt` | Remove adjacent duplicates |
| `uniq -c file.txt` | Count adjacent duplicates |
| `sort file.txt \| uniq -c` | Count every value |
| `sort file.txt \| uniq -c \| sort -rn` | Count and rank by frequency |

In the table, `\|` only stops Markdown from splitting the cell; type a plain `|` in the terminal.

**Interview-ready answer:**

> "`cut` extracts columns by a delimiter, for example `cut -d: -f1 /etc/passwd` lists user names; it is quicker than `awk` when the delimiter is consistent, but for space-aligned output I use `awk`. `sort` orders lines, and I use `-n` for numbers, `-r` for reverse and `-h` for sizes like `du` output. `uniq` only removes or counts adjacent duplicates, so I always sort first. To find the most frequent values I use `sort | uniq -c | sort -rn`, for example `awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5` to see the top client IPs during an incident."

</details>

<details><summary>Q13. [Intermediate] What is jq, and why should you use it instead of grep or sed for JSON?</summary>

**Answer:**

`jq` is a command-line JSON processor: it parses, filters and transforms JSON. Most DevOps tools now output JSON (`kubectl`, Azure CLI, AWS CLI, `terraform output -json`, REST APIs), so it is worth learning properly. Parsing JSON with `grep` and `sed` is fragile and a well-known anti-pattern, because they see text, not structure.

**1. Basics: read fields**

`server.json`:

```json
{
  "name": "web01",
  "ip": "192.168.1.10",
  "status": "Running",
  "cpu": 75
}
```

```bash
jq '.' server.json          # whole document, pretty-printed (also validates the JSON)
jq '.name' server.json      # "web01"   (a JSON string, with quotes)
jq -r '.name' server.json   # web01     (-r = raw output, no quotes)
jq -r '.ip' server.json     # 192.168.1.10
```

`.` is the current input, and `.name` reads the `name` field. Use `-r` whenever the value goes into a shell variable or another command.

**2. Arrays: iterate, format and filter**

`pods.json`:

```json
{
  "items": [
    { "name": "frontend", "status": "Running" },
    { "name": "backend",  "status": "Pending" },
    { "name": "database", "status": "Running" }
  ]
}
```

```bash
jq -r '.items[].name' pods.json
```

```text
frontend
backend
database
```

`[]` iterates over every element of the array.

```bash
jq -r '.items[] | "\(.name) \(.status)"' pods.json
```

```text
frontend Running
backend Pending
database Running
```

`|` passes each item to the next expression, and `\( )` inserts a value into a string.

```bash
jq -r '.items[] | select(.status == "Running") | .name' pods.json
```

```text
frontend
database
```

`select()` keeps only the items for which the condition is true.

**3. Kubernetes examples**

```bash
# All Pod names
kubectl get pods -o json | jq -r '.items[].metadata.name'

# Pod name and phase
kubectl get pods -o json | jq -r '.items[] | "\(.metadata.name) \(.status.phase)"'

# Pods whose phase is not Running
kubectl get pods -A -o json | jq -r '
  .items[]
  | select(.status.phase != "Running")
  | "\(.metadata.namespace)/\(.metadata.name) \(.status.phase)"'

# Containers that are not ready or have restarted (a Running Pod can still be unhealthy)
kubectl get pods -o json | jq -r '
  .items[] | .metadata.name as $pod
  | .status.containerStatuses[]?
  | select(.ready == false or .restartCount > 0)
  | "\($pod) \(.name) ready=\(.ready) restarts=\(.restartCount)"'
```

The phase only says the Pod is scheduled and its containers started. A container can still be crash-looping or failing its readiness probe, which is why the last example checks `ready` and `restartCount`. The `?` after `containerStatuses[]` skips Pods that don't have the field yet (for example Pending Pods).

**4. Azure CLI examples**

```bash
az vm list -o json | jq -r '.[].name'
az vm list -o json | jq -r '.[] | "\(.name) \(.resourceGroup)"'
```

```text
web-vm01 rg-web
app-vm01 rg-app
```

Azure CLI also has a built-in `--query` option (JMESPath), which avoids the extra tool:

```bash
az vm list --query "[].{name:name, rg:resourceGroup}" -o tsv
```

Use `--query` for simple selections, and `jq` for more complex logic or when you combine output from several tools.

**5. Filter by a number**

`vms.json`:

```json
[
  { "name": "vm01", "cpu": 40 },
  { "name": "vm02", "cpu": 85 },
  { "name": "vm03", "cpu": 92 }
]
```

```bash
jq '.[] | select(.cpu > 80)' vms.json            # full objects
jq -r '.[] | select(.cpu > 80) | .name' vms.json  # names only
```

```text
vm02
vm03
```

Numbers are compared as numbers, not as text, which `grep` cannot do.

**6. Count elements**

```bash
jq 'length' vms.json                                         # 3
kubectl get pods -o json | jq '.items | length'               # number of Pods
jq '[.[] | select(.cpu > 80)] | length' vms.json              # 2: count matches
```

`length` returns the number of elements for an array, the number of keys for an object, and the number of characters for a string. To count matches, wrap the filter in `[ ]` to make an array first.

**7. More features you will use in scripts**

```bash
# Pass a shell variable safely (no quoting problems)
STATUS=Running
jq -r --arg s "$STATUS" '.items[] | select(.status == $s) | .name' pods.json

# Read a value into a variable; -e makes jq fail if the result is null or false
IP=$(jq -er '.ip' server.json) || { echo "ip missing"; exit 1; }

# Default value when a field is missing
jq -r '.region // "unknown"' server.json

# CSV or TSV for reports
jq -r '.[] | [.name, .cpu] | @csv' vms.json      # "vm01",40

# Change a value and write a new file (jq does not edit in place)
jq '.status = "Stopped"' server.json > server.tmp && mv server.tmp server.json

# Terraform outputs
terraform output -json | jq -r '.vnet_id.value'

# Compact one-line output, for example for logs
jq -c '.items[]' pods.json
```

**8. Why not grep or sed?**

```json
{
  "name": "frontend",
  "status": { "phase": "Running" },
  "labels": { "previous-state": "Running" }
}
```

`grep "Running" file.json` matches **both** lines, and it cannot tell which object or field a value belongs to. It also breaks when the JSON is minified onto one line, when key order changes, or when values contain escaped quotes. `jq -r '.status.phase' file.json` returns exactly `Running` from the field you asked for.

| Tool | Understands | Use it for |
| --- | --- | --- |
| `grep` | Lines of text | Finding lines in logs |
| `sed` | Lines of text | Editing plain text and simple config files |
| `awk` | Columns | Tabular output and calculations |
| `jq` | JSON structure: objects, arrays, data types | Anything that is JSON |
| `yq` | YAML (jq-like syntax) | Kubernetes manifests, Helm values, pipelines |

**Quick revision:**

| Expression | Purpose |
| --- | --- |
| `jq '.' file.json` | Pretty-print and validate |
| `jq '.name' file.json` | Read a field |
| `jq -r '.name' file.json` | Raw string without quotes |
| `jq '.items[]' file.json` | Iterate over an array |
| `jq '.a.b.c' file.json` | Read a nested field |
| `jq '.[] \| select(.cpu > 80)' file.json` | Filter by a condition |
| `jq 'length' file.json` | Count array elements or object keys |
| `jq --arg x "$VAR" '...'` | Use a shell variable safely |
| `jq -r '.[] \| [.a, .b] \| @csv'` | Output CSV |
| `jq -r '.items[].metadata.name'` | Kubernetes Pod names |

In the table, `\|` only stops Markdown from splitting the cell; type a plain `|` in the terminal.

**Interview-ready answer:**

> "`jq` is a command-line JSON processor. Since `kubectl`, Azure CLI, AWS CLI and Terraform all output JSON, I use it in scripts to extract fields, filter objects with `select`, count elements and build reports. For example, `kubectl get pods -o json | jq -r '.items[] | select(.status.phase != "Running") | .metadata.name'` lists Pods that aren't running. I use `-r` for raw values, `--arg` to pass shell variables safely, and `-e` so a script fails when a field is missing. I avoid `grep` and `sed` for JSON because they only see text: they break on nested or minified JSON and can match the wrong field, while `jq` understands the structure. For simple Azure CLI selections I also use the built-in `--query` option."

</details>
