# Shell Scripting Detailed Interview Notes

## Safe Bash Backup Rotation Example

This example dumps a PostgreSQL database from a container, checks the output isn't empty, and removes backups older than seven days. In production, credentials should come from a protected runtime source, and backups should also be encrypted, copied to separate storage, monitored, and tested by actually restoring them.
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

I'd also generate a checksum, upload the backup to storage that can't be changed after it's written, alert if the backup fails or never runs, and regularly restore it into a separate test database. Deleting by age like this is clearer and safer than trying to parse `ls` output.

## Shell Error Handling and Logging

For any automation script, start with a deliberate strict-mode choice such as `set -Eeuo pipefail`. Keep in mind that `-e` has some shell-specific exceptions, so you should still check important commands explicitly rather than relying on it alone. Add an `ERR` trap to capture the line number and command that failed, then exit with a useful status code.

Log both stdout and stderr while still showing them on screen, for example with `exec > >(tee -a "$log_file") 2>&1`. Never print secrets, always quote variables, use `mktemp` for temporary files, and test what happens when things fail, not just the happy path.
