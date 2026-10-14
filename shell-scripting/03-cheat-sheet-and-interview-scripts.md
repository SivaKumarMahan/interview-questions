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
