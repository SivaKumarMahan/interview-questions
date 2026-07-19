# Safe Shell Script Patterns

## Service check and remediation

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

service_name=${1:-nginx}
if systemctl is-active --quiet "$service_name"; then
  printf '%s is running\n' "$service_name"
  exit 0
fi

systemctl start "$service_name"
systemctl is-active --quiet "$service_name" || {
  journalctl -u "$service_name" -n 50 --no-pager >&2 || true
  exit 1
}
```

## Disk threshold

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

threshold=${THRESHOLD_PERCENT:-80}
usage=$(df -P / | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
if (( usage >= threshold )); then
  printf 'CRITICAL: root filesystem is %s%% used\n' "$usage" >&2
  exit 2
fi
printf 'OK: root filesystem is %s%% used\n' "$usage"
```

## Backup skeleton

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

source_dir=${SOURCE_DIR:?Set SOURCE_DIR}
backup_dir=${BACKUP_DIR:?Set BACKUP_DIR}
mkdir -p -- "$backup_dir"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$backup_dir/backup-$stamp.tar.gz"
tar -C "$(dirname "$source_dir")" -czf "$archive" "$(basename "$source_dir")"
sha256sum "$archive" > "$archive.sha256"
tar -tzf "$archive" >/dev/null
```

A production backup additionally needs encryption, remote failure-domain copy, retention, monitoring, and restore testing. User-management scripts should use approved identity tools and must not embed a default password or automatic broad sudo.
