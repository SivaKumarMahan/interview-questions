## 1. How do you rollback failed database migrations in CI/CD?
**Answer:** Use version-controlled migration tools (Liquibase/Flyway) → Write rollback scripts → Trigger rollback step in pipeline.

**Detailed interview approach:**
I deploy an immutable artifact through a strategy matched to risk: rolling for routine stateless changes, canary for metric-based exposure, or blue-green for fast traffic switching. The pipeline runs prechecks, deploys to a small/no-traffic target, performs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and SLO/error budget. If thresholds fail it stops traffic and rolls back to the previous artifact/config; database changes use expand-and-contract because application rollback cannot undo destructive schema changes. I verify recovery, record the result, and improve the test or guard that should have caught the failure earlier.

## 2. How do you manage database schema in CI/CD pipelines?
**Answer:** Use Liquibase or Flyway migration scripts → Run as pipeline step → Ensure backward compatibility.

**Detailed interview approach:**
Database changes use versioned, forward-compatible migrations. I back up and test restore, measure table size/lock behavior, and use expand-and-contract: add nullable/new structures, deploy code that supports old and new versions, backfill in bounded batches, switch reads/writes, then remove old structures in a later release. The pipeline uses a migration lock, timeout, monitoring, and one authorized runner. Rollback normally means roll forward with a corrective migration or switch compatible application code; destructive down scripts can lose data. For blue-green databases I continuously replicate, control a single writer, validate lag and data, cut over connections gradually, and retain the old side for an agreed rollback window.

## 3. How do you manage blue-green deployment for databases?
**Answer:** Use DB replication or shadow DB → Apply schema changes in green DB → Switch app traffic → Validate before retiring blue DB.

**Detailed interview approach:**
I deploy an immutable artifact through a strategy matched to risk: rolling for routine stateless changes, canary for metric-based exposure, or blue-green for fast traffic switching. The pipeline runs prechecks, deploys to a small/no-traffic target, performs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and SLO/error budget. If thresholds fail it stops traffic and rolls back to the previous artifact/config; database changes use expand-and-contract because application rollback cannot undo destructive schema changes. I verify recovery, record the result, and improve the test or guard that should have caught the failure earlier.

## 4. How do you handle database credential rotation in CI/CD pipelines?
**Answer:** • Store DB credentials in Secret Manager / Key Vault.
• Fetch secrets at runtime in pipelines.
• Use Kubernetes secrets/ConfigMaps.
• Automate credential rotation and ensure apps re-read from secret storage.

**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak. Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient. Pre-commit/server-side scans, protected logs, least privilege, expiry, and rotation tests prevent recurrence.

## 5. How do you perform zero-downtime DB migration in CI/CD?
**Answer:** Use Liquibase/Flyway migration scripts → Apply backward-compatible schema changes → Deploy app → Apply destructive changes only later.

**Detailed interview approach:**
I use an expand-and-contract migration. First I take and test a backup, measure table size/lock behavior, and add backward-compatible columns/tables/indexes without removing what the old application needs. I deploy code that can work with both schemas, backfill data in small resumable batches, monitor locks, replication lag, latency, and errors, then switch reads/writes. Only after every old application version is gone do I remove the old schema in a later release. The pipeline uses a migration lock, timeout, named owner, and verification query. Rollback normally means switching compatible application behavior or rolling forward with a corrective migration, because reversing a destructive migration may lose data.

