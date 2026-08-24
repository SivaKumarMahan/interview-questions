# Secure Azure Database Connectivity

1. Pick the managed database and availability model — Azure SQL, PostgreSQL, MySQL, or Cosmos DB — based on backup needs, zone/region, RTO, RPO, and performance.
2. Provision it through reviewed IaC, with diagnostic settings on, deletion protection where it's supported, backup retention set, and a private endpoint.
3. Connect the application over VNet integration, private DNS, routes, and firewall rules scoped as narrowly as possible. Avoid exposing the database publicly unless there's a real, controlled reason to.
4. Prefer managed identity and Microsoft Entra authentication. If a password or connection secret is unavoidable, store it in Key Vault and pull it at runtime — never bake it into an image or a repository.
5. Require TLS certificate validation. Use connection pooling, limited timeouts, retry with backoff (waiting a bit longer between each retry), and safe locking during migrations.

Investigation flow for a failed connection:

```text
DNS/private endpoint → route/NSG/firewall → TCP port → TLS
→ identity/token audience and database user → database health/quota
→ pool exhaustion, timeout, query and application logs
```

I test from the real workload identity and subnet, and check both an allowed path and a path that should be denied. I compare Azure Activity/diagnostic logs, and watch connection failures, pool use, query latency, deadlocks, storage, and failover.

An administrator connecting successfully from the portal doesn't prove the application's own connection path works.
