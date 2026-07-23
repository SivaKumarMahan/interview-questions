## 1. Which database signals would you put on a production dashboard?

**Answer:**

Availability, transaction/query rate, P95/P99 latency, error ratio, connections and pool wait, CPU/memory/cache, disk capacity/latency, lock/deadlock count, replication lag, failover status, backup age/result and a real read/write transaction where safe. I segment by database, operation and application without using unbounded query/user labels.

## 2. How do you investigate database connection failures?

**Answer:**

I distinguish refused, timeout, TLS, authentication and pool exhaustion, then correlate application and database logs by time/source. I check endpoint/DNS/network, listener/availability, secret version and identity, certificate, max connections/pool leak, replication/failover and recent changes. I fix the proven layer and verify an appropriate real transaction, latency, pool recovery and denied unauthorized access.

## 3. How do monitoring and alerts support a safe database migration?

**Answer:**

Beforehand I establish backup/restore evidence and baseline latency, error, locks, capacity and replication. During expand-and-contract or blue-green work I watch migration progress, lock duration, replication lag, application versions, read/write correctness and SLOs; abort thresholds and owner are predefined. After cutover I verify data and business transactions through a stability window before removing the old schema or environment.
