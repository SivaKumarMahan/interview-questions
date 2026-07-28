## 1. How would you design a self-healing platform for critical production services?

**Answer:**

I design self-healing around known failure modes and safe, limited actions.

Redundant instances across failure domains (groups of resources that can fail together), health/readiness checks, orchestrator reconciliation (making actual state match desired state), autoscaling, queue-based buffering, dependency timeouts, and automated traffic removal handle common component failures.

Data services need quorum, replication, backups, and fencing; restarting a failed database blindly can create corruption or split brain.

Detection uses user-visible SLIs plus component evidence. Each automation has prerequisites, rate limits, cooldown, maximum attempts, audit logs, and escalation.

Examples include replacing an unhealthy immutable (not changed after creation) instance, restarting a proven deadlocked stateless process, scaling on queue age, or failing traffic to a healthy region. Automation never deletes state, opens broad access, or loops indefinitely.

I inject controlled failures to test detection, fix, customer impact, and fallback to humans. Dashboards show action success and repeated recurrence.

Self-healing reduces recovery time; it does not remove root-cause analysis, capacity planning, or tested disaster recovery.

## 2. How do you handle cascading failures across multiple microservices?

**Answer:**

I stabilize demand and protect healthy dependencies first: stop risky releases, rate-limit at the edge, shed noncritical work, open circuit breakers, cap retries with jittered backoff (increasing wait between retries) and budgets, bound queues, and scale only where the dependency can accept more load.

Unlimited retries and synchronized timeouts amplify a small failure into a cascade.
Using traces, service topology, saturation (how close a resource is to its limit), queue age, and error timing, I identify the earliest failing shared dependency rather than treating every downstream 5xx as a separate incident.

Bulkheads, separate pools, per-tenant quotas, idempotency (safe repeat behavior), deadlines propagated across calls, fallbacks, and cached/degraded responses contain scope of impact.
After recovery I replay buffered work safely, verify data correctness and SLO recovery, and test the new limits under load. The post-incident review updates dependency ownership, capacity assumptions, retry/timeout standards, alerts, and failure-mode exercises.

## 3. How do you design disaster recovery with an RTO under five minutes and defined RPO?

**Answer:**

I first confirm that the business cost justifies the target. An RTO below five minutes generally requires a pre-provisioned warm or active secondary environment, automated detection and traffic switching, independent identity/DNS/certificates/observability, and enough recovery capacity.

Backups alone cannot meet that RTO. RPO determines synchronous versus asynchronous replication and the possible data-loss window.

I map every dependency: compute, data, object storage, queues, secrets, DNS, third parties, CI/CD, and people. Data replication includes fencing and write ownership to prevent split brain.

Infrastructure and configuration are versioned, but actual restore/failover procedures are automated and idempotent (safe to run more than once). Health checks use real transactions, not only host status.

Game days simulate region and dependency failures and measure detection, decision, data promotion, scaling, traffic shift, and validation. I record achieved RTO/RPO, replication lag, data reconciliation (making actual state match desired state), and failback.

If tests cannot meet five minutes, I report the gap and change architecture or expectation rather than claiming an unproven target.

## 4. Explain your production incident-management process.

**Answer:**

I assess impact and severity, declare one incident, assign incident commander, technical leads, communications, and scribe, and start a timestamped channel/timeline.

The team protects safety, security, and data integrity, then stabilizes users through rollback, traffic shift, feature disablement, scaling, or isolation.

We preserve evidence and form testable hypotheses from metrics, logs, traces, deploys, and audit changes instead of making simultaneous random changes.

Stakeholders receive impact, mitigation, owner, and next-update time. Each action has an expected result and rollback.

Recovery requires customer/business transaction checks plus SLO and backlog validation, not merely green infrastructure. Temporary access and mitigations are removed or tracked.

The blameless review identifies technical and organizational contributors, detection gaps, what helped, and measurable actions with owners/dates. We update tests, architecture, runbooks, alerts, capacity, and game days and later verify the actions worked.

## 5. A deployment succeeds, but latency rises from 80 ms to two seconds. How do you investigate it?

**Answer:**

I treat deployment success as only a control-plane result. I compare new and old versions under the same traffic and segment latency into DNS, connect/TLS, gateway/queue, application, cache, database, and downstream time using traces and proxy/application metrics.

I compare the exact change time with configuration, feature flags, schema, instance mix, GC, CPU throttling, connection pools, query plans, cache hit rate, payload size, retries, and zone/region routing.

If SLO impact is material, I pause progression or route traffic back to the last healthy version while preserving evidence. A canary comparison can distinguish code from shared dependency or traffic changes.

I avoid simply increasing timeout, which hides latency and consumes more resources.

After the targeted fix I load-test the real path, confirm p50/p95/p99 and errors, saturation (how close a resource is to its limit), dependency health, and business metrics, and add a performance regression test or deployment guard based on the discovered cause.

## 6. Can strict use of the Single Responsibility Principle increase complexity in a distributed system? (True or False)

**Answer:**

True. A useful responsibility boundary improves ownership and change isolation, but applying the principle mechanically can create too many tiny services.

Every service boundary adds network calls, partial failures, deployment/versioning, observability, security, data consistency, testing, and team coordination. A “single responsibility” should reflect a cohesive business capability and ownership boundary, not one class or function per service.

I evaluate coupling, independent change frequency, scaling, data ownership, latency, transaction needs, team ownership, and operational maturity. A well-structured modular monolith can be safer than premature microservices.

I extract a service when the boundary provides measurable independent value and the team can operate it; architecture is reviewed as usage changes.
