## 1. What are microservices, and how are they different from a monolith?

**Answer:**

A monolith bundles several capabilities into one application unit. Microservices split them into services that deploy independently, each with clear ownership of its own business logic and data.

For example, orders, payments, and inventory might each have their own team, API, and data store.

Microservices help when capabilities really need to release, scale, or be owned independently. They're not automatically better — every boundary you add brings extra latency, a new way to partially fail, API compatibility work, security, deployment, and observability overhead.

I start with a modular design and only pull out a separate service once the boundary has measurable value and a team is ready to operate it.

## 2. How do microservices communicate reliably?

**Answer:**

Synchronous HTTP/gRPC makes sense when the caller needs an answer right away. Asynchronous queues or events decouple services and absorb traffic spikes when an immediate response isn't necessary. Contracts are versioned and stay backward-compatible.

Every remote call has a deadline or timeout. Retries are capped, use backoff with jitter (a growing, slightly randomized wait between attempts), and only apply to operations that are temporary failures and safe to repeat.

Circuit breakers, bulkheads, connection-pool limits, and rate limits keep one struggling dependency from taking down the whole system. Messages carry stable IDs, consumers are built to handle a duplicate message safely, and there's dead-letter handling and visible retry state.

## 3. How do you handle transactions across multiple microservices?

**Answer:**

I try to avoid a distributed database transaction spanning multiple services. Instead, each service commits its own local transaction.

A saga coordinates a sequence of steps plus compensating actions if something fails partway through. An outbox pattern writes the business change and the event record in one local transaction, so an async publisher can never lose that event.

For an order: Order creates it as `Pending`, Payment authorizes the charge, Inventory reserves stock, and Order becomes `Confirmed`. If inventory fails, a compensating action releases the payment authorization.

Every command and event carries a key that makes it safe to process twice, since delivery can repeat. I'm explicit about which parts of the system need immediate consistency versus which can be eventually consistent, and I monitor for stuck saga steps and dead letters.

## 4. A release causes high latency across many services. How do you investigate?

**Answer:**

First I pin down the start time, which paths, regions, and versions are affected, then check the gateway's P95/P99 latency, error ratio, traffic, and saturation.

Distributed traces show me the earliest slow hop. I compare processing time against database, cache, queue, and external calls, and line it up against deployment or configuration events.

I check for retry storms, pool exhaustion, DNS/TLS issues, autoscaling lag, and payload changes.

To stabilize things, I roll back or shift traffic, disable the costly feature, add rate limiting, or scale the confirmed bottleneck — I don't restart or scale every service blindly.

Recovery means the real user transaction, latency, errors, saturation, and backlog all return to normal. Afterward, I add whatever was missing: a performance test, a timeout/retry budget, a capacity rule, or a deployment gate.

## 5. How do you secure and observe microservices?

**Answer:**

At the edge, I use strong authentication, authorization, rate limits, and input validation. Internally, workloads use short-lived identities, mTLS where it's needed, service-to-service authorization limited to what's needed, network policy, and external secret management.

Images are minimal, signed and scanned, and run as non-root with resource limits.

Every service emits a limited set of metrics, structured and redacted logs, and distributed traces tagged with service, environment, version, and trace ID. Dashboards show latency, traffic, errors, saturation, dependency health, queue age, and business outcomes, and alerts are tied to SLOs with a clear owner.

Audit logs cover sensitive actions. Observability data should never contain tokens or unnecessary personal data.

## 6. When would you use SQS rather than Kafka, or vice versa?

**Answer:**

I use SQS when I need a managed queue for decoupled work, simple producer/consumer scaling, retries, and dead-letter queues, without running a whole streaming platform. It's a good fit for async commands and background jobs.

I use Kafka when multiple consumers need an ordered, durable event log, replay, high throughput, consumer-managed offsets, and stream processing. Neither one guarantees exactly-once behavior at the business level on its own — consumers still need to handle duplicates safely, and you still need to watch lag, failures, and dead-letter queues.

The choice comes down to delivery semantics, whether you need retention/replay, how wide the ordering needs to be, throughput, and who's going to operate it.

## 7. What are a Kafka broker and a consumer group?

**Answer:**

A Kafka broker is a server in the cluster that stores topic partitions, serves producers and consumers, and takes part in replication and leader election.

A consumer group is a set of consumers sharing a group ID. Kafka assigns each partition to at most one active consumer within that group, so you get parallel processing while still preserving order within each partition.

Different groups can consume the same topic independently of each other. I keep an eye on consumer lag, partition balance, broker disk and replication health, the in-sync replica count, throughput, and failed consumers — and consumers need to handle duplicates safely, since retries and rebalances can cause the same message to be reprocessed.
