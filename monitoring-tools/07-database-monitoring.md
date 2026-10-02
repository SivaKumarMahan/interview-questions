# Monitoring Tools: Database Monitoring

> Database signals, connection failures, migrations, alerting, sensitive data, and tested backups.

## Key Concepts

### Database Monitoring Overview

Database monitoring needs to cover both the database itself and how the application experiences it.

### What to Monitor in Databases

| Area | Signals |
| --- | --- |
| Availability | Connection success rate |
| Performance | Query latency, throughput, errors |
| Connections | Active/max connections, pool wait time |
| Resources | CPU, memory, cache usage, storage capacity, I/O |
| Data integrity | Locks, deadlocks, slow queries |
| Replication | Replication lag, failover state |
| Backups | Backup age, backup result, restore-test evidence |

Application and database monitoring data need to share the same time source, service and environment labels, and trace context. Without that, you can't line up a slow request in the app with what the database was doing at that moment.

### Types of Connection Failures

A connection timeout, an authentication failure, a TLS error, and pool exhaustion are all different problems with different causes. Treat them as separate incidents rather than lumping them together as "connection issues."

### Migrations and Blue-Green Changes

During a migration or a blue-green cutover, watch locks, replication lag, error rate, latency, and data correctness. Keep exactly one controlled writer active during the cutover — two writers at once is how you get data corruption.

### Alerting

Alert based on user impact and the risk of running out of capacity, not on every slow query. A single slow query is usually noise; a rising trend toward connection pool exhaustion is not.

### Sensitive Data in Database Monitoring

Query text and parameters can contain sensitive data. Redact them before capture, and control who can access stored query logs and how long they're retained.

### Backups Aren't Done Until Tested

A backup job succeeding is not the same as a backup being usable. Treat a backup as incomplete until you've tested the restore and validated the application against the restored data.

## Interview Questions

<details><summary>Q1. [Intermediate] Which database signals would you put on a production dashboard?</summary>

**Answer:**

I'd track availability, transaction and query rate, P95/P99 latency, error ratio, connection count and pool wait time, CPU/memory/cache usage, disk capacity and latency, lock and deadlock count, replication lag, failover status, backup age and result, and — where it's safe — a real read/write transaction.

I segment these by database, operation, and application, but I avoid unlimited query or user labels, since that drives up cardinality and cost.

</details>

<details><summary>Q2. [Intermediate] How do you investigate database connection failures?</summary>

**Answer:**

First I figure out what kind of failure it is: refused, timeout, TLS, authentication, or pool exhaustion. Then I compare application and database logs by time and source.

I check the endpoint and DNS, the network path, the listener's availability, the secret version and identity being used, the certificate, max connections or a pool leak, replication or failover state, and any recent changes.

I fix the layer that's actually proven to be the cause, then confirm with a real transaction, latency, pool recovery, and that unauthorized access is still denied.

</details>

<details><summary>Q3. [Advanced] How do monitoring and alerts support a safe database migration?</summary>

**Answer:**

Before the migration, I confirm backup and restore actually work, and I record baseline latency, error rate, locks, capacity, and replication lag.

During an expand-and-contract or blue-green migration, I watch migration progress, lock duration, replication lag, application versions, read/write correctness, and SLOs. Abort thresholds and the owner responsible for that call are agreed on beforehand.

After cutover, I verify data and business transactions through a stability window before removing the old schema or environment.

</details>
