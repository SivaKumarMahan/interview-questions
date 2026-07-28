# Secure Azure Database Connectivity

1. Select the managed database and availability model: Azure SQL, PostgreSQL, MySQL, or Cosmos DB, including backup, zone/region, RTO, RPO, and performance requirements.
2. Provision it through reviewed IaC with diagnostic settings, deletion protection where supported, backup retention, and a private endpoint.
3. Connect the application network through VNet integration, private DNS, routes, and narrowly scoped firewall rules. Avoid public database exposure unless there is a justified and controlled requirement.
4. Prefer managed identity and Microsoft Entra authentication. If a password or connection secret is unavoidable, store it in Key Vault and retrieve it at runtime; never bake it into an image or repository.
5. Require TLS certificate validation and use connection pooling, limited timeouts, retry with backoff (increasing wait between retries), and safe migration locking.

Investigation flow for a failed connection:

```text
DNS/private endpoint → route/NSG/firewall → TCP port → TLS
→ identity/token audience and database user → database health/quota
→ pool exhaustion, timeout, query and application logs
```

I test from the real workload identity and subnet, verify both an allowed and denied path, compare Azure Activity/diagnostic logs, and monitor connection failures, pool use, query latency, deadlocks, storage, and failover.

A successful portal connection from an administrator does not prove the application path is correct.
