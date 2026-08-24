# Shell Scripting Interview Summary

## Shell Automation

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

- `$0` is the script's own name.
- `$1`, `$2`, and so on are the arguments passed in.
- `$#` is how many arguments were passed.
- `"$@"` expands to all the arguments, keeping each one intact.
- `$(command)` captures a command's output — always think about its exit status and whether it has a trailing newline.
- `read -r variable` reads input without treating backslashes as escape characters.

Quote your expansions unless you actually want word splitting or globbing to happen. Use `[[ ... ]]` for conditionals, `(( count += 1 ))` for arithmetic, and `case` when you have several string options to match.

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

Use `local` variables inside functions, return a meaningful status code, and pass commands as arguments rather than building command strings for `eval`. A retry has to be limited, visible in the logs, and safe to run again on something that may have already partly succeeded.

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

`>` overwrites a file, `>>` appends to it, `2>` redirects standard error, and `|` connects one command's output to the next command's input. With `set -o pipefail`, the whole pipeline counts as failed if any command in it fails, not just the last one.

`set -e` is not complete error handling on its own — it has exceptions depending on context. Check for expected failures explicitly, use traps for cleanup, and actually test what happens when things go wrong. Run `shellcheck` during development and in CI.

## Environment and Secret Handling

An exported variable is passed down to any child process:

```bash
export APP_ENV="production"
export APP_PORT="8080"
```

Environment variables are fine for regular, non-sensitive configuration. Don't hardcode database passwords, API keys, or default passwords in scripts, shell history, profile files, or committed `.env` files.

Pull secrets at runtime from an approved secret manager, never echo them, and unset temporary values once you're done with them.

## Monitoring and Cleanup

| Task | What matters |
|---|---|
| Disk monitoring | Watch the right filesystem, and put useful detail in the alert. |
| Log cleanup | Check the directory, retention period, and ownership. Use `logrotate` or `journald` policy instead of deleting files by hand. |
| Fixing a service | Check its config, verify it's healthy after start/reload, keep the logs, limit retries, and alert instead of looping forever. |

## Backups

A backup script should:

- Create its destination safely
- Preserve permissions where that matters
- Never back up its own output into itself
- Write to a temporary name and rename it into place once complete
- Checksum or encrypt the backup, per policy
- Enforce a retention period
- Copy the backup somewhere that won't fail along with the original
- Get restored occasionally to prove it actually works

A command returning exit code zero is not proof that the data can be recovered.

## User Provisioning

User provisioning scripts should never hardcode or print passwords, and should never hand out broad `sudo` access automatically. Use your organization's approved identity tooling, make account/group/SSH-key setup safe to run more than once, grant only the access someone actually needs, log what happened, set an expiry, and have a clear offboarding path.

Shell scripting is a good fit for small tasks. Once you're dealing with heavier parsing, state, transactions, or complex error recovery, reach for a proper language or a configuration-management tool instead.
