# Shell Scripting Detailed Interview Notes

## Safe Bash Backup Rotation Example

This example creates a PostgreSQL dump from a container, verifies that the output is non-empty, and removes backups older than seven days. In production, credentials should come from a protected runtime mechanism and backups should be encrypted, copied to separate storage, monitored, and restore-tested.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

readonly db_container="db-container"
readonly backup_dir="/backups"
readonly timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
readonly backup_file="${backup_dir}/database-${timestamp}.sql"

mkdir -p -- "$backup_dir"

docker exec "$db_container" \
  pg_dump --username=postgres --dbname=mydb >"$backup_file"

if [[ ! -s "$backup_file" ]]; then
  echo "Backup is empty: $backup_file" >&2
  exit 1
fi

find "$backup_dir" -maxdepth 1 -type f \
  -name 'database-*.sql' -mtime +7 -print -delete

echo "Backup completed: $backup_file"
```

I would additionally generate a checksum, upload to versioned immutable storage, alert on failure or missing successful backup, and regularly restore into an isolated database. Retention by age is clearer and safer than parsing `ls` output.

## Shell Error Handling and Logging

For automation, begin with a deliberate strict-mode choice such as `set -Eeuo pipefail`; understand that `-e` has shell-context exceptions, so important commands should still be checked explicitly. Use an `ERR` trap to add line number and command context, then exit with a useful status. Log both stdout and stderr while preserving visibility, for example `exec > >(tee -a "$log_file") 2>&1`. Avoid printing secrets, quote variables, use `mktemp` for temporary files, and test failure paths rather than only the happy path.
