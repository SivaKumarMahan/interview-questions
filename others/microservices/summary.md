# Microservices Summary

**Microservices** split a system into independently owned, independently deployable services, each aligned to one cohesive business capability. Each service owns its own logic and, usually, its own data, and talks to others through stable APIs or events.

This can improve team autonomy, independent scaling, and fault isolation, but it also brings network failures, distributed data consistency, versioning, security, observability, and operational cost. A **modular monolith** is often safer until independent ownership or scaling actually provides measurable value.

```text
client -> API gateway -> service A -> service B
                         |             |
                       data A        data B
                         \-> event broker -> service C
```

**Production design** relies on explicit contracts, backward compatibility, timeouts, retry budgets with jitter, circuit breaking, bulkheads, rate limits, safe-to-repeat operations, queues for buffering, health and readiness checks, workload identity, access limited to only what's needed, centralized secrets, structured logs, metrics, and distributed traces.

Retries should never multiply load or accidentally repeat work that isn't safe to repeat.

Avoid a shared database that lets every service modify every table. Cross-service workflows use event-driven patterns, the outbox/inbox pattern, consumers that safely handle duplicate messages, or sagas, depending on the consistency you actually need.

Monitoring follows the real user transaction across the gateway, services, queues, and data stores, and includes deployment and version context.

## Example Azure Implementation

On Azure, a practical implementation runs independently deployable services on AKS, stores signed and scanned images in ACR, uses Helm or GitOps for release configuration, and exposes only the necessary routes through an ingress/Gateway with a WAF-capable edge.

Cosmos DB or Azure SQL gets chosen per service based on its data needs, Redis handles low-latency caching, and Service Bus provides durable async work with back-pressure.

These services should use private endpoints and private DNS wherever that's supported.

Workloads use managed or workload identity to reach Key Vault and other Azure services, instead of putting shared connection strings in manifests. Azure Monitor, Log Analytics, and Application Insights provide the platform's monitoring data, logs, traces, and availability checks.

The design still needs contract versioning, retry limits, safe-to-repeat operations, dead-letter handling, data backup and recovery, and failure testing — cloud services don't remove the usual distributed-systems failure modes.
