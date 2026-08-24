## 1. Which database signals would you put on a production dashboard?

**Answer:**

I'd track availability, transaction and query rate, P95/P99 latency, error ratio, connection count and pool wait time, CPU/memory/cache usage, disk capacity and latency, lock and deadlock count, replication lag, failover status, backup age and result, and — where it's safe — a real read/write transaction.

I segment these by database, operation, and application, but I avoid unlimited query or user labels, since that drives up cardinality and cost.

## 2. How do you investigate database connection failures?

**Answer:**

First I figure out what kind of failure it is: refused, timeout, TLS, authentication, or pool exhaustion. Then I compare application and database logs by time and source.

I check the endpoint and DNS, the network path, the listener's availability, the secret version and identity being used, the certificate, max connections or a pool leak, replication or failover state, and any recent changes.

I fix the layer that's actually proven to be the cause, then confirm with a real transaction, latency, pool recovery, and that unauthorized access is still denied.

## 3. How do monitoring and alerts support a safe database migration?

**Answer:**

Before the migration, I confirm backup and restore actually work, and I record baseline latency, error rate, locks, capacity, and replication lag.

During an expand-and-contract or blue-green migration, I watch migration progress, lock duration, replication lag, application versions, read/write correctness, and SLOs. Abort thresholds and the owner responsible for that call are agreed on beforehand.

After cutover, I verify data and business transactions through a stability window before removing the old schema or environment.
