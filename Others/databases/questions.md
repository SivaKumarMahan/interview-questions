## 1. An application cannot connect to its database. What do you check first and how do you investigate?

**Answer:**

I identify the exact client, database endpoint, port, environment, error, and start time. “Connection refused,” timeout, TLS error, authentication failure, and pool exhaustion are different failures.

From the affected runtime I test DNS, route, TCP, and TLS, then use a safe database client with the same identity where approved.

I do not print the password or open the database publicly.

I inspect application connection-string source and secret version, certificate/CA and hostname, security-group/firewall/NetworkPolicy, proxy or private endpoint, database listener and availability, user status/expiry/permissions, max connections, pool settings, replication/failover state, and recent deploy/schema/network/credential changes.

Database and application logs are correlated by timestamp and connection source.
I fix the proven layer: DNS/route/rule, listener, rotated secret consumption, certificate, account, connection leak/pool, or database health. I verify a real read/write transaction as appropriate, latency, pool recovery, denied unauthorized access, and failover.

Preventive controls include managed identity or rotated secrets, private connectivity, TLS, pool metrics, connection SLOs, and tested credential/failover changes.

## 2. Write a query to find the fifth-highest salary.

**Answer:**

For the fifth **distinct** salary, use a window function:

```sql
SELECT salary
FROM (
  SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS salary_rank
  FROM Employee
) ranked
WHERE salary_rank = 5;
```

`DENSE_RANK` treats equal salaries as one rank. If the question instead means the fifth row after sorting, use `ROW_NUMBER`; clarify the requirement and index/limit the query appropriately for a large table.

## 3. What is the difference between clustered and non-clustered indexes?

**Answer:**

A clustered index determines the physical or ordered storage of table rows, so a table normally has one. A non-clustered index is a separate structure containing indexed keys plus a row location or included columns; a table can have several.

Indexes improve selected read patterns but add write, storage, and maintenance cost. I choose them from real query plans and column cardinality (the number of distinct values), not by indexing every column.

## 4. A database partition is full and the production application is down. What do you do?

**Answer:**

I declare the incident, confirm the full filesystem/tablespace and customer impact, stop nonessential writes or shift traffic if the runbook permits, and protect backups/evidence.

I identify the growth source—logs, temporary data, runaway job, retention failure, WAL/binlogs, index rebuild or data load—then use the approved path to extend capacity, archive/purge only validated data, or fail over.

I do not delete unknown database files. After recovery I validate transactions and replication, then fix retention/capacity alerts, growth forecasting and the responsible workload.
