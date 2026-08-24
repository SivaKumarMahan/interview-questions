## 1. An application cannot connect to its database. What do you check first and how do you investigate?

**Answer:**

First I pin down the exact client, database endpoint, port, environment, error message, and when it started. "Connection refused," a timeout, a TLS error, an authentication failure, and pool exhaustion are all different problems with different causes.

From the affected runtime, I test DNS, routing, TCP, and TLS, then connect with a safe database client using the same identity, if that's approved.

I never print the password or expose the database publicly to test it.

I check the app's connection-string source and secret version, the certificate/CA and hostname, security-group/firewall/NetworkPolicy rules, any proxy or private endpoint, whether the database listener is up, the user's status/expiry/permissions, max connections, pool settings, replication/failover state, and any recent deploy, schema, network, or credential change.

I correlate database and application logs by timestamp and connection source.

Then I fix whatever layer I've actually confirmed is broken: DNS/routing, the listener, a secret that didn't rotate properly, a certificate, an account, a connection leak or pool issue, or the database's own health. I verify with a real read/write transaction, check latency, confirm the pool recovers, confirm unauthorized access is still denied, and check failover.

To prevent it happening again: managed identity or properly rotated secrets, private connectivity, TLS, pool metrics, connection SLOs, and testing credential and failover changes before they ship.

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

`DENSE_RANK` treats equal salaries as one rank. If the question actually means the fifth row after sorting instead, use `ROW_NUMBER`. Either way, clarify what's meant and make sure the query is indexed and limited properly on a large table.

## 3. What is the difference between clustered and non-clustered indexes?

**Answer:**

A clustered index determines the physical, ordered storage of the table's rows, so a table normally has only one. A non-clustered index is a separate structure holding the indexed keys plus a pointer to the row (or some included columns) — a table can have several of these.

Indexes speed up specific read patterns, but they cost extra on writes, storage, and maintenance. I choose which columns to index based on real query plans and how many distinct values a column has, not by just indexing everything.

## 4. A database partition is full and the production application is down. What do you do?

**Answer:**

I declare the incident, confirm the filesystem or tablespace is actually full and how customers are affected, stop non-essential writes or shift traffic if the runbook allows it, and make sure backups and evidence are protected.

I figure out what's actually growing — logs, temporary data, a runaway job, a retention failure, WAL/binlogs, an index rebuild, or a data load — then use the approved path to add capacity, archive or purge only data I've confirmed is safe to remove, or fail over.

I never delete a database file I don't recognize. Once it's fixed, I validate transactions and replication, then fix the retention and capacity alerts, growth forecasting, and whatever workload actually caused it.
