## 1. How do you rollback failed database migrations in CI/CD?

**Answer:** Use a version-controlled migration tool (Liquibase/Flyway), write rollback scripts, and trigger a rollback step in the pipeline.

**Detailed interview approach:**
I deploy a fixed artifact (its contents never change once built) using a strategy that matches the risk: rolling for routine stateless changes, canary when I want to check metrics on a small slice of traffic, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or zero-traffic target, runs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and the SLO/error budget.

If any threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record what happened, and improve whatever test or guard should have caught the problem earlier.

## 2. How do you manage database schema in CI/CD pipelines?

**Answer:** Use Liquibase or Flyway migration scripts, run them as a pipeline step, and make sure changes stay backward-compatible.

**Detailed interview approach:**
Database changes go through versioned migrations that stay compatible with the previous version.

I back up the database and test the restore, measure table size and lock behavior, and use an expand-and-contract approach: add new nullable structures, deploy code that supports both the old and new versions, backfill data in limited batches, switch reads and writes over, then remove the old structures in a later release.

The pipeline uses a migration lock, a timeout, monitoring, and a single authorized runner. Rolling back usually means rolling forward with a corrective migration, or switching to compatible application code — a destructive "down" script can lose data.

For blue-green databases, I replicate continuously, keep a single writer at a time, validate lag and data, cut connections over gradually, and keep the old side around for an agreed rollback window.

## 3. How do you manage blue-green deployment for databases?

**Answer:** Use database replication or a shadow database, apply schema changes to the green database, switch application traffic over, and validate before retiring the blue database.

**Detailed interview approach:**
I deploy a fixed artifact (its contents never change once built) using a strategy that matches the risk: rolling for routine stateless changes, canary when I want to check metrics on a small slice of traffic, or blue-green when I need a fast traffic switch.

The pipeline runs prechecks, deploys to a small or zero-traffic target, runs readiness and business smoke tests, then advances while watching error rate, latency, saturation, and the SLO/error budget.

If any threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record what happened, and improve whatever test or guard should have caught the problem earlier.

## 4. How do you handle database credential rotation in CI/CD pipelines?

**Answer:**
- Store database credentials in Secret Manager or Key Vault.
- Fetch secrets at runtime in the pipeline.
- Use Kubernetes secrets/ConfigMaps.
- Automate the rotation, and make sure apps re-read from secret storage instead of caching credentials forever.

**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store — never in Git, YAML, images, command arguments, or artifacts. Jobs get a short-lived identity and fetch only the secret they need for that stage. Masking is a backup control, since an encoded or transformed value can still leak.

Rotation works with an overlap: issue the new value, update consumers, verify it works, revoke the old value, and audit for failures. If a scan finds a committed secret, I revoke it right away, check how it was used, remove it from active history where appropriate, and rotate anything downstream that trusted it — just deleting the line isn't enough.

Pre-commit and server-side scans, protected logs, minimal access, expiry, and rotation tests all help prevent it from happening again.

## 5. How do you perform zero-downtime DB migration in CI/CD?

**Answer:** Use Liquibase/Flyway migration scripts, apply backward-compatible schema changes first, deploy the app, and only apply destructive changes later.

**Detailed interview approach:**
I use an expand-and-contract migration. First I take and test a backup, measure table size and lock behavior, and add backward-compatible columns, tables, or indexes without removing anything the old application still needs.

I deploy code that works with both the old and new schema, backfill data in small batches that can safely resume if interrupted, and monitor locks, replication lag, latency, and errors, then switch reads and writes over. Only once every old version of the application is gone do I remove the old schema, in a later release.

The pipeline uses a migration lock, a timeout, a named owner, and a verification query. Rolling back usually means switching to compatible application behavior, or rolling forward with a corrective migration — reversing a destructive migration can lose data.

