# Shell Scripting Interview Summary

## Shell Automation

Useful DevOps scripts include disk-capacity monitoring, controlled log retention, service health/remediation, verified backups, and user/account workflows. Production scripts should use:

- A clear interpreter
- `set -Eeuo pipefail` where appropriate
- Quoted variables
- Input validation
- Safe temporary files
- Meaningful exit codes
- Logging without secrets
- Locks for concurrency
- Cleanup traps

## Script Structure and Inputs

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

- `$0` is the invoked script name.
- `$1`, `$2`, and so on are positional arguments.
- `$#` is the argument count.
- `"$@"` expands to all arguments while preserving their boundaries.
- `$(command)` captures command output; always consider its exit status and trailing-newline behavior.
- `read -r variable` reads input without treating backslashes as escapes.

Quote expansions unless intentional word splitting or glob expansion is required. Use `[[ ... ]]` for Bash conditionals, arithmetic contexts such as `(( count += 1 ))` for numbers, and `case` for multiple string alternatives.

## Loops and Functions

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

Use `local` variables inside functions, return meaningful status codes, and pass commands as arguments rather than constructing command strings for `eval`. A retry must be bounded, observable and safe for an operation that may have partially succeeded.

## Redirection, Pipelines and Traps

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

`>` replaces a file, `>>` appends, `2>` redirects standard error, and `|` connects one command's standard output to the next command's standard input. With `set -o pipefail`, a pipeline is unsuccessful when any component fails, not only the last one.

`set -e` is not complete error handling: its behavior has contextual exceptions. Check expected failures explicitly, use traps for cleanup, and test failure paths. Run `shellcheck` during development and CI.

## Environment and Secret Handling

An exported variable is inherited by child processes:

```bash
export APP_ENV="production"
export APP_PORT="8080"
```

Use environment variables for non-sensitive configuration when appropriate. Do not hardcode database passwords, API keys or default user passwords in scripts, shell history, profiles or committed `.env` files. Retrieve secrets at runtime through the approved secret manager, avoid echoing them, and unset temporary values when practical.

## Monitoring and cleanup

**Disk monitoring** must select the intended filesystem and alert with context. **Log cleanup** must validate the directory, retention and ownership and should normally use `logrotate`/`journald` policy rather than raw deletion. **Service remediation** should validate configuration, check health after start/reload, preserve logs, limit retries, and alert rather than looping forever.

## Backups

A backup script must:

- Create destination safely
- Preserve permissions where needed
- Avoid recursively backing up its own output
- Use an atomic name
- Checksum/encrypt according to policy
- Enforce retention
- Copy to another failure domain
- Regularly prove restoration

A command returning zero is **not** proof that the data is recoverable.

## User provisioning

User provisioning should not hardcode or echo passwords and should not automatically grant broad `sudo`. Use approved identity management, idempotent account/group/SSH-key configuration, least privilege, audit, expiry, and an offboarding path. Shell is suitable for small orchestration; use a stronger language or configuration-management tool when parsing, state, transactions, or complex error recovery grows.
