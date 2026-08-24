# Database Monitoring Summary

Database monitoring needs to cover both the database itself and how the application experiences it.

## What to Monitor

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

## Types of Connection Failures

A connection timeout, an authentication failure, a TLS error, and pool exhaustion are all different problems with different causes. Treat them as separate incidents rather than lumping them together as "connection issues."

## Migrations and Blue-Green Changes

During a migration or a blue-green cutover, watch locks, replication lag, error rate, latency, and data correctness. Keep exactly one controlled writer active during the cutover — two writers at once is how you get data corruption.

## Alerting

Alert based on user impact and the risk of running out of capacity, not on every slow query. A single slow query is usually noise; a rising trend toward connection pool exhaustion is not.

## Sensitive Data

Query text and parameters can contain sensitive data. Redact them before capture, and control who can access stored query logs and how long they're retained.

## Backups Aren't Done Until Tested

A backup job succeeding is not the same as a backup being usable. Treat a backup as incomplete until you've tested the restore and validated the application against the restored data.
