# Microservices Summary

**Microservices** split a system into independently owned and deployable services aligned to cohesive business capabilities. Each service owns its logic and normally its data boundary and communicates through stable APIs or events. This can improve team autonomy, independent scaling and fault isolation, but adds network failures, distributed data consistency, versioning, security, observability and operational cost. A **modular monolith** is often safer until independent ownership or scaling provides measurable value.

```text
client -> API gateway -> service A -> service B
                         |             |
                       data A        data B
                         \-> event broker -> service C
```

**Production design** uses explicit contracts, backward compatibility, timeouts, retry budgets with jitter, circuit breaking, bulkheads, rate limits, idempotency, queues for buffering, health/readiness, workload identity, least privilege, centralized secrets, structured logs, metrics and distributed traces. Retries must not multiply load or duplicate non-idempotent work.

Avoid a shared database that lets every service modify every table. Cross-service workflows use event-driven patterns, outbox/inbox, idempotent consumers or sagas according to consistency needs. Monitoring follows the user transaction across gateway, services, queues and data stores and includes deployment/version context.
