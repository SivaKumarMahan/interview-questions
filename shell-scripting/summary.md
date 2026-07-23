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
