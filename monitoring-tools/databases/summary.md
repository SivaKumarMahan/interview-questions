# Database Monitoring Summary

**Database monitoring** includes availability and connection success, query latency and throughput, errors, active/max connections and pool wait, CPU/memory/cache, storage capacity and I/O, locks/deadlocks, slow queries, replication lag, failover state, backup age/result and restore-test evidence.

Application and database telemetry must share time, service/environment and trace context. A connection timeout, authentication failure, TLS error and pool exhaustion are different incidents. During migration or blue-green change, monitor locks, replication lag, error rate, latency and data correctness and keep one controlled writer during cutover.

Alert from user impact and exhaustion risk, not every slow query. Query text and parameters may contain sensitive data, so capture and retention require redaction and access control. A successful backup job is incomplete until restoration and application validation are tested.
