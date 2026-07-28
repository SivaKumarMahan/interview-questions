## 1. What are microservices, and how are they different from a monolith?

**Answer:**

A monolith deploys several capabilities as one application unit. Microservices divide them into independently deployable services with clear business and data ownership.

For example, orders, payments and inventory may have separate teams, APIs and data stores.

Microservices help when capabilities need independent release, scaling, technology or ownership. They are not automatically better: every boundary adds latency, partial failure, API compatibility, security, deployment and observability work.

I start with a modular design and extract a service only when the boundary has measurable value and a team can operate it.

## 2. How do microservices communicate reliably?

**Answer:**

Synchronous HTTP/gRPC is suitable when the caller needs an immediate response. Asynchronous queues/events decouple services and absorb spikes when immediate completion is unnecessary. Contracts are versioned and backward compatible.

Every remote call has a deadline/timeout. Retries are limited, use backoff (increasing wait between retries)/jitter and apply only to temporary and idempotent (safe to run more than once) operations.

Circuit breakers, bulkheads, connection-pool limits and rate limits prevent one dependency from exhausting the whole system. Messages use stable IDs, idempotent (safe to run more than once) consumers, dead-letter handling and observable retry state.

## 3. How do you handle transactions across multiple microservices?

**Answer:**

I avoid a distributed database transaction across services where possible. Each service commits its own local transaction.

A saga coordinates a sequence of steps and compensating actions, while an outbox writes the business change and event record in one local transaction so an asynchronous publisher cannot lose the event.

For an order, Order creates `Pending`, Payment authorizes, Inventory reserves and Order becomes `Confirmed`. If inventory fails, compensation releases payment authorization.

All commands/events have idempotency (safe repeat behavior) keys because delivery may repeat. I define which consistency is immediate versus eventual and monitor stuck saga steps and dead letters.

## 4. A release causes high latency across many services. How do you investigate?

**Answer:**

I establish start time, affected paths, regions and versions, then inspect gateway P95/P99, error ratio, traffic and saturation (how close a resource is to its limit).

Distributed traces identify the earliest slow hop; I compare processing time with database, cache, queue and external calls and compare deployment/configuration events.

I check retry storms, pool exhaustion, DNS/TLS, autoscaling lag and payload changes.

I stabilize by rolling back or shifting traffic, disabling the costly feature, rate limiting or scaling the proven bottleneck. I do not restart or scale every service blindly.

Recovery requires the real user transaction, latency, errors, saturation (how close a resource is to its limit) and backlog to normalize. The follow-up adds the missing performance test, timeout/retry budget, capacity rule or deployment gate.

## 5. How do you secure and observe microservices?

**Answer:**

At the edge I use strong authentication, authorization, rate limits and input validation. Internally, workloads use short-lived identity, mTLS where required, least-privilege (minimum required access) service authorization, network policy and external secret management.

Images are minimal, signed/scanned and run non-root with resource limits.

Every service emits limited metrics, structured redacted logs and distributed traces with service, environment, version and trace ID. Dashboards show latency, traffic, errors, saturation (how close a resource is to its limit), dependency health, queue age and business outcomes; alerts are SLO-based and owned.

Audit logs cover sensitive actions. Observability data never contains tokens or unnecessary personal data.

## 6. When would you use SQS rather than Kafka, or vice versa?

**Answer:**

I use SQS when I need a managed queue for decoupled work, simple producer/consumer scaling, retries and dead-letter queues without operating a streaming platform. It is a good fit for asynchronous commands and background jobs.

I use Kafka when multiple consumers need an ordered, durable event log, replay, high throughput, consumer-managed offsets and stream processing. Neither guarantees business-level exactly-once behavior by itself: consumers must be idempotent (safe to run more than once) and monitor age/lag, failures and DLQs.

The choice follows delivery semantics, retention/replay, ordering scope, throughput and operational ownership.

## 7. What are a Kafka broker and a consumer group?

**Answer:**

A Kafka broker is a server in the Kafka cluster that stores topic partitions, serves producers/consumers and participates in replication and leader election.

A consumer group is a set of consumers sharing a group ID; Kafka assigns each partition to at most one active consumer in that group, allowing parallel processing while retaining partition order.

Different groups can consume the same topic independently. I monitor consumer lag, partition balance, broker disk/replication health, ISR, throughput and failed consumers; consumers must be idempotent (safe to run more than once) because retries and rebalances can cause reprocessing.
