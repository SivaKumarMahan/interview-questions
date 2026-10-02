# Shell Scripting: Bash Fundamentals and Error Handling

> What a production-grade shell script needs: structure, arguments, conditionals, loops, functions, redirection, traps, exit codes, secrets, error handling, and debugging.

## Key Concepts

### Shell Automation

Common DevOps scripts handle things like disk-capacity monitoring, controlled log cleanup, restarting or fixing a service, verified backups, and user-account workflows. A production script should have:

- A clear interpreter line
- `set -Eeuo pipefail` where it makes sense
- Quoted variables
- Input validation
- Safe temporary files
- Meaningful exit codes
- Logging that never includes secrets
- A lock so it can't run twice at once
- A cleanup trap

### Script Structure and Inputs

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    printf 'Usage: %s <service-name>\n' "$0" >&2
}

if (( $# != 1 )); then
    usage
    exit 64
fi

service_name=$1

if systemctl is-active --quiet "$service_name"; then
    printf '%s is active\n' "$service_name"
else
    printf '%s is not active\n' "$service_name" >&2
    exit 1
fi
```

- `$0` is the script's own name.
- `$1`, `$2`, and so on are the arguments passed in.
- `$#` is how many arguments were passed.
- `"$@"` expands to all the arguments, keeping each one intact.
- `$(command)` captures a command's output — always think about its exit status and whether it has a trailing newline.
- `read -r variable` reads input without treating backslashes as escape characters.

Quote your expansions unless you actually want word splitting or globbing to happen. Use `[[ ... ]]` for conditionals, `(( count += 1 ))` for arithmetic, and `case` when you have several string options to match.

### Production shell script structure

A production script should have:

- A clear interpreter line.
- `set -Eeuo pipefail` where appropriate.
- Quoted variables.
- Input validation.
- Safe temporary files.
- Meaningful exit codes.
- Logging that never includes secrets.
- Locks for concurrency where the script shouldn't run twice at once.
- Cleanup traps.

Basic structure:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    printf 'Usage: %s <service-name>\n' "$0" >&2
}

if (( $# != 1 )); then
    usage
    exit 64
fi

service_name=$1

if systemctl is-active --quiet "$service_name"; then
    printf '%s is active\n' "$service_name"
else
    printf '%s is not active\n' "$service_name" >&2
    exit 1
fi
```

### Shell fundamentals glossary

| Symbol/pattern | Meaning |
| --- | --- |
| `$0` | Invoked script name/path |
| `$1`, `$2`, ... | Positional arguments |
| `$#` | Argument count |
| `"$@"` | All arguments, preserving each as a separate word/boundary |
| `$(command)` | Command substitution |
| `read -r` | Reads input without treating backslashes as escapes |
| Quoting | Quote variable expansions unless word splitting/globbing is intentional |
| `[[ ... ]]` | Bash conditional |
| `(( ... ))` | Arithmetic evaluation |
| `case` | Multiple string alternatives |

### Loops and Functions

```bash
for file in ./*.txt; do
    [[ -e "$file" ]] || continue
    printf 'Processing %s\n' "$file"
done

retry_command() {
    local attempt
    for (( attempt = 1; attempt <= 3; attempt++ )); do
        if "$@"; then
            return 0
        fi
        sleep "$attempt"
    done
    return 1
}
```

Use `local` variables inside functions, return a meaningful status code, and pass commands as arguments rather than building command strings for `eval`. A retry has to be limited, visible in the logs, and safe to run again on something that may have already partly succeeded.

### Redirection, Pipelines and Traps

```bash
temporary_file=$(mktemp)

cleanup() {
    rm -f -- "$temporary_file"
}
trap cleanup EXIT

if ! producer >"$temporary_file" 2>producer-error.log; then
    printf 'Producer failed\n' >&2
    exit 1
fi

consumer <"$temporary_file"
```

`>` overwrites a file, `>>` appends to it, `2>` redirects standard error, and `|` connects one command's output to the next command's input. With `set -o pipefail`, the whole pipeline counts as failed if any command in it fails, not just the last one.

`set -e` is not complete error handling on its own — it has exceptions depending on context. Check for expected failures explicitly, use traps for cleanup, and actually test what happens when things go wrong. Run `shellcheck` during development and in CI.

### Environment and Secret Handling

An exported variable is passed down to any child process:

```bash
export APP_ENV="production"
export APP_PORT="8080"
```

Environment variables are fine for regular, non-sensitive configuration. Don't hardcode database passwords, API keys, or default passwords in scripts, shell history, profile files, or committed `.env` files.

Pull secrets at runtime from an approved secret manager, never echo them, and unset temporary values once you're done with them.

### Shell Error Handling and Logging

For any automation script, start with a deliberate strict-mode choice such as `set -Eeuo pipefail`. Keep in mind that `-e` has some shell-specific exceptions, so you should still check important commands explicitly rather than relying on it alone. Add an `ERR` trap to capture the line number and command that failed, then exit with a useful status code.

Log both stdout and stderr while still showing them on screen, for example with `exec > >(tee -a "$log_file") 2>&1`. Never print secrets, always quote variables, use `mktemp` for temporary files, and test what happens when things fail, not just the happy path.

## Interview Questions

### 1. What does `echo $?` indicate in Linux shell scripting?

**Answer:**

`$?` holds the exit status of the last command or pipeline that just finished. By convention, zero means success and anything else means that command failed in its own specific way.

You have to capture it immediately, because running any other command — even `echo` or `cd` — overwrites it.

```bash
curl --fail --silent https://service.example/health
status=$?
if (( status != 0 )); then
  printf 'Health check failed with exit code %d\n' "$status" >&2
fi
```

For a pipeline, I turn on `set -o pipefail`, since otherwise `$?` only reflects the last command in the chain. In production scripts I handle expected failures explicitly and give them useful context, rather than treating `set -e` as a substitute for real error handling.

### 2. Write a Bash script to add two numbers.

**Answer:**

I check that both inputs are actually integers instead of trusting Bash arithmetic to reject bad input on its own.

```bash
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || ! $1 =~ ^-?[0-9]+$ || ! $2 =~ ^-?[0-9]+$ ]]; then
  echo "Usage: $0 <integer> <integer>" >&2
  exit 2
fi

printf '%s\n' "$(( $1 + $2 ))"
```

For example, `./add.sh 10 20` returns `30`, and `./add.sh ten 20` returns a usage error instead of a wrong answer. For numbers bigger than Bash's integer range, or for decimals, I'd use `bc`, Python, or another tool built for real math.

### 3. How do you debug automation scripts?

**Answer:**

I reproduce the failure with the same inputs and environment, then narrow it down to the first command that actually fails.

```bash
bash -n deploy.sh             # syntax
shellcheck deploy.sh          # common errors
bash -x deploy.sh --dry-run   # trace; avoid when secrets may print
```

I check the shebang line, the executable bit, PATH, the working directory, the user running it, environment variables, file permissions, exit codes, quoting, pipelines, network/DNS, and dependency versions. Scheduled jobs often fail simply because cron runs with a much smaller environment than an interactive shell.

I add `set -Eeuo pipefail` carefully, log useful context, and use `trap 'echo "failed at line $LINENO" >&2' ERR`. Once it's fixed, I test the success case, invalid input, a timeout, partial output, running it twice in a row, and cleanup. I redact secrets before sharing any trace output.
### 4. Shell Script Error Handling

#### The script

```bash
#!/bin/bash

cp /backup/app.tar.gz /tmp/
tar -xzf /tmp/app.tar.gz
systemctl restart nginx

echo "Deployment successful"
```

#### What happens with the current script?

If:

```bash
cp /backup/app.tar.gz /tmp/
```

fails, the script continues executing by default.

So the flow is:

```text
cp fails
  ↓
tar -xzf /tmp/app.tar.gz
  ↓
systemctl restart nginx
  ↓
echo "Deployment successful"
```

The `tar` command may also fail because the archive wasn't copied, but the script still continues.

Worst case, `systemctl restart nginx` could restart the service using an old or partially updated deployment, and the script still prints:

```text
Deployment successful
```

That's incorrect.

#### Simple fix: `set -e`

```bash
#!/bin/bash
set -e

cp /backup/app.tar.gz /tmp/
tar -xzf /tmp/app.tar.gz
systemctl restart nginx

echo "Deployment successful"
```

Now:

```text
cp fails
  ↓
Script exits
  ↓
tar is NOT executed
  ↓
nginx is NOT restarted
  ↓
"Deployment successful" is NOT printed
```

This is the basic answer expected in an interview.

#### Better production version

```bash
#!/bin/bash
set -euo pipefail

cp /backup/app.tar.gz /tmp/
tar -xzf /tmp/app.tar.gz
systemctl restart nginx

echo "Deployment successful"
```

#### What does `set -euo pipefail` mean?

**`set -e`** — Exit when a command fails.
`cp file /tmp/` fails → script exits.

**`set -u`** — Treat undefined variables as errors.
For example: `echo "$APP_VERSION"` — if `APP_VERSION` was never defined, the script fails instead of silently continuing.

**`set -o pipefail`** — Normally, in `command1 | command2`, the exit status is usually based on the last command. With `pipefail`, the pipeline fails if an earlier command fails.

#### Add explicit error handling

```bash
#!/bin/bash
set -euo pipefail

echo "Starting deployment..."

if ! cp /backup/app.tar.gz /tmp/app.tar.gz; then
    echo "ERROR: Failed to copy application archive"
    exit 1
fi

if ! tar -xzf /tmp/app.tar.gz -C /opt/app; then
    echo "ERROR: Failed to extract application archive"
    exit 1
fi

if ! systemctl restart nginx; then
    echo "ERROR: Failed to restart nginx"
    exit 1
fi

echo "Deployment successful"
```

This gives you a clear failure point.

#### One important interview detail

Don't blindly say "`set -e` makes every Bash script fail safely." Bash has some contexts where `set -e` behaves differently, particularly around conditions, `&&`, `||`, `if`, loops, and pipelines.

For critical deployment automation, combine `set -euo pipefail` with explicit checks around important operations.

#### Strong interview answer

"By default, Bash does not stop when a command fails. If `cp` fails, the script continues to `tar`, then potentially restarts nginx, and finally prints 'Deployment successful'. That's dangerous because the deployment could be incomplete. I would use `set -euo pipefail` so unexpected command failures stop the script, and for critical deployment steps I would also use explicit error handling with `if ! command; then ... exit 1; fi` so the failure is clearly logged."

#### Remember

Without error handling: `cp fails → script continues` ❌
With `set -e`: `cp fails → script stops` ✅
Production: `set -euo pipefail` + explicit checks for critical operations
### 5. common shell interview questions (quick-fire)

**1. Why use `#!/usr/bin/env bash`?**
It's the shebang, telling the OS to use Bash. `env` finds Bash through `PATH`, which is more portable than hardcoding `/bin/bash` (which doesn't exist at that path on every system).

**2. What is `set -Eeuo pipefail`?**
- `-e` - exit immediately on a command failure.
- `-E` - preserves `ERR` traps inside functions and subshells (without it, `-e`'s effect can silently not propagate into a function).
- `-u` - treats unset variables as errors instead of expanding to empty strings.
- `pipefail` - makes a pipeline fail if *any* command in it fails, not just the last one.

**3. Why quote variables?**
To prevent spaces and special characters from causing word splitting or unintended glob expansion.

```bash
rm "$file"
```

Without quotes, a filename containing a space would be split into multiple arguments.

**4. What is `$0`?**
The script's own name/path.

**5. What are `$1`, `$2`, etc.?**
Positional parameters - the arguments passed to the script, in order.

**6. What is `$#`?**
The number of arguments passed to the script.

**7. What is `"$@"`?**
All arguments, with each one preserved as a separate word - critical when forwarding arguments to another command, since `"$@"` won't merge an argument containing spaces into a neighboring one.

**8. What is `$(command)`?**
Command substitution - runs `command` and substitutes its output.

```bash
today=$(date)
```

**9. Why use `read -r`?**
To prevent backslashes in the input from being interpreted as escape characters - without `-r`, `read` treats `\` specially, which is almost never what you want when reading arbitrary text.

**10. `[ ]` vs `[[ ]]`?**
`[[ ]]` is Bash-specific and safer/more expressive - it handles strings with spaces without extra quoting headaches, supports `&&`/`||` directly, and supports pattern/regex matching (`=~`).

**11. When do you use `(( ))`?**
For arithmetic, e.g. `(( count += 1 ))`. Also usable as a truthiness check inside `if`, e.g. `if (( usage >= 80 ))`.

**12. Why use `case`?**
Cleaner than a chain of `if`/`elif` branches when checking a variable against multiple possible string values.

**13. What is input validation, in this context?**
Checking that arguments and values are valid *before* performing actions with them - e.g. confirming an argument count, a file exists, or a value is numeric before using it destructively.

**14. Why use meaningful exit codes?**
Automation tools (CI/CD, cron, monitoring) key off exit codes to determine success/failure. `0` means success; non-zero means failure. `64` is a conventional code for command-line usage errors (from BSD's `sysexits.h` convention).

**15. What is `trap`?**
Runs commands when the script exits or receives a signal - the standard way to guarantee cleanup even if the script exits early or is interrupted.

```bash
trap 'rm -f /tmp/myfile' EXIT
```

**16. Why use lock files?**
To prevent multiple instances of the same script from running concurrently - important for anything scheduled (cron) that might still be running when the next scheduled run starts.

**17. Why avoid logging secrets?**
Logs are often widely readable (shared log aggregators, ticket attachments, support access). Passwords, tokens, and keys should never be written to logs.

**18. What does `systemctl is-active --quiet` do?**
Checks a service's state purely through its exit code, without printing status output - ideal for use inside an `if` condition in a script.

**19. Why `printf` instead of `echo`?**
`printf` has more predictable formatting and better portability across shells - `echo`'s handling of flags like `-e` and backslash escapes varies between implementations.

**20. "What shell automation have you done?"**
Disk monitoring, old log cleanup, backup verification, service restart/health checks, user account workflows, email/Slack alerts, and CI/CD automation.
