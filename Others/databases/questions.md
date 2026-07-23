## 1. An application cannot connect to its database. What do you check first and how do you investigate?

**Answer:**

I identify the exact client, database endpoint, port, environment, error, and start time. “Connection refused,” timeout, TLS error, authentication failure, and pool exhaustion are different failures. From the affected runtime I test DNS, route, TCP, and TLS, then use a safe database client with the same identity where approved. I do not print the password or open the database publicly.

I inspect application connection-string source and secret version, certificate/CA and hostname, security-group/firewall/NetworkPolicy, proxy or private endpoint, database listener and availability, user status/expiry/permissions, max connections, pool settings, replication/failover state, and recent deploy/schema/network/credential changes. Database and application logs are correlated by timestamp and connection source.

I fix the proven layer: DNS/route/rule, listener, rotated secret consumption, certificate, account, connection leak/pool, or database health. I verify a real read/write transaction as appropriate, latency, pool recovery, denied unauthorized access, and failover. Preventive controls include managed identity or rotated secrets, private connectivity, TLS, pool metrics, connection SLOs, and tested credential/failover changes.
