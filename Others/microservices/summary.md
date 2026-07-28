# Microservices Summary

**Microservices** split a system into independently owned and deployable services aligned to cohesive business capabilities. Each service owns its logic and normally its data boundary and communicates through stable APIs or events.

This can improve team autonomy, independent scaling and fault isolation, but adds network failures, distributed data consistency, versioning, security, observability and operational cost. A **modular monolith** is often safer until independent ownership or scaling provides measurable value.

```text
client -> API gateway -> service A -> service B
                         |             |
                       data A        data B
                         \-> event broker -> service C
```

**Production design** uses explicit contracts, backward compatibility, timeouts, retry budgets with jitter, circuit breaking, bulkheads, rate limits, idempotency (safe repeat behavior), queues for buffering, health/readiness, workload identity, least privilege (only the permissions needed), centralized secrets, structured logs, metrics and distributed traces.

Retries must not multiply load or duplicate non-idempotent (safe to run more than once) work.
Avoid a shared database that lets every service modify every table. Cross-service workflows use event-driven patterns, outbox/inbox, idempotent (safe to run more than once) consumers or sagas according to consistency needs.

Monitoring follows the user transaction across gateway, services, queues and data stores and includes deployment/version context.

## Example Azure Implementation

On Azure, a practical implementation runs independently deployable services on AKS, stores signed/scanned images in ACR, uses Helm or GitOps for release configuration, and exposes only the required north-south routes through an ingress/Gateway and WAF-capable edge.

Cosmos DB or Azure SQL is chosen per service/data requirement; Redis supports low-latency caching; Service Bus provides durable asynchronous work and back-pressure.

These services should use private endpoints and private DNS where supported.

Workloads use managed/workload identity to access Key Vault and Azure services, rather than shared connection strings in manifests. Azure Monitor, Log Analytics and Application Insights provide platform monitoring data, logs, traces and availability checks.

The design must still include contract versioning, retry limits, idempotency (safe repeat behavior), dead-letter handling, data backup/recovery and failure testing; cloud services do not remove distributed-systems failure modes.
