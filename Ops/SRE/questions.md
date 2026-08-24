## 1. How would you design a self-healing platform for critical production services?

**Answer:**

I build self-healing around known failure modes, using actions that are safe and limited in scope.

Redundant instances spread across separate failure domains (groups of resources that could fail together), health and readiness checks, the orchestrator continuously reconciling state, autoscaling, queue-based buffering, timeouts on dependencies, and automatically pulling bad instances out of traffic — these handle most common component failures.

Data services are different: they need quorum, replication, backups, and fencing, because blindly restarting a failed database can cause corruption or a split-brain situation.

Detection relies on SLIs that reflect what users actually see, plus evidence from individual components. Every automated action has clear prerequisites, a rate limit, a cooldown period, a maximum number of attempts, an audit log, and a path to escalate to a human.

Examples: replacing an unhealthy instance with a fresh, unmodified one, restarting a stateless process that's confirmed to be deadlocked, scaling based on queue age, or failing traffic over to a healthy region. Automation should never delete state, grant broad access, or loop forever.

I test this by injecting controlled failures, to confirm detection works, the fix works, customer impact is limited, and it correctly falls back to a human when it should. Dashboards track whether actions succeeded and whether the same issue keeps recurring.

Self-healing shortens recovery time. It doesn't replace root-cause analysis, capacity planning, or a tested disaster-recovery plan.

## 2. How do you handle cascading failures across multiple microservices?

**Answer:**

First I stabilize demand and protect the dependencies that are still healthy: stop risky releases, rate-limit at the edge, drop non-critical work, open circuit breakers, cap retries with jittered backoff (a growing, slightly randomized wait between retries) and a retry budget, bound queue sizes, and only scale where the dependency can actually absorb more load.

Unlimited retries and timeouts that all fire at once are what turn a small failure into a full cascade.

Using traces, the service topology, saturation levels (how close each resource is to its limit), queue age, and the timing of errors, I find the earliest shared dependency that actually failed, rather than treating every downstream 5xx as its own separate incident.

Bulkheads, separate resource pools, per-tenant quotas, idempotency (so retries are always safe), deadlines that propagate across calls, fallbacks, and cached or degraded responses all keep the blast radius small.

Once things recover, I safely replay any buffered work, confirm data correctness and that SLOs have recovered, and load-test the new limits. The post-incident review updates dependency ownership, capacity assumptions, retry and timeout standards, alerts, and failure-mode exercises.

## 3. How do you design disaster recovery with an RTO under five minutes and a defined RPO?

**Answer:**

First I confirm the business cost actually justifies that target. An RTO (recovery time objective) under five minutes generally needs a pre-provisioned warm or active secondary environment, automated detection and traffic switching, independent identity, DNS, certificates, and observability, and enough spare capacity to absorb the failover.

Backups alone can't hit that RTO. The RPO (recovery point objective) is what decides whether you need synchronous or asynchronous replication, and how much data loss is acceptable in the worst case.

I map every dependency: compute, data, object storage, queues, secrets, DNS, third parties, CI/CD, and the people involved. Data replication needs fencing and clear write ownership to avoid split-brain.

Infrastructure and configuration are versioned, but the actual restore and failover steps are automated and safe to run more than once. Health checks use real transactions, not just whether a host is up.

Game days simulate region and dependency failures, and measure detection, decision-making, data promotion, scaling, traffic shift, and validation. I record the RTO and RPO actually achieved, replication lag, how data was reconciled, and how failback went.

If the tests can't hit five minutes, I report that gap honestly and either change the architecture or reset the expectation — I don't claim a target that hasn't been proven.

## 4. Explain your production incident-management process.

**Answer:**

I assess impact and severity, declare a single incident, assign an incident commander plus technical leads, communications, and a scribe, and open a timestamped channel to track the timeline.

The team protects safety, security, and data integrity first, then stabilizes users through rollback, a traffic shift, disabling a feature, scaling, or isolating the problem.

We preserve evidence and build testable hypotheses from metrics, logs, traces, deploys, and audit changes, instead of making several random changes at once and hoping one works.

Stakeholders get regular updates covering impact, what's being done, who owns it, and when the next update will come. Every action has an expected result and a rollback plan.

Recovery means confirming real customer and business transactions work, plus SLOs and backlog — not just that infrastructure shows green. Any temporary access or workaround gets removed or explicitly tracked.

The blameless review looks at both technical and organizational contributing factors, gaps in detection, what worked well, and concrete actions with an owner and a date. We update tests, architecture, runbooks, alerts, capacity plans, and game days, then check later that those fixes actually worked.

## 5. A deployment succeeds, but latency rises from 80 ms to two seconds. How do you investigate it?

**Answer:**

A successful deployment only tells you the control plane did its job — it says nothing about performance. I compare the new and old versions under identical traffic, and break latency down by DNS, connection/TLS, gateway or queue time, application time, cache, database, and downstream calls, using traces and proxy/application metrics.

I line up the exact time of the change against configuration changes, feature flags, schema changes, the instance mix, garbage collection, CPU throttling, connection pools, query plans, cache hit rate, payload size, retries, and zone or region routing.

If the SLO impact is real, I pause the rollout or route traffic back to the last healthy version while preserving evidence. Comparing a canary against the baseline helps tell whether it's the new code, a shared dependency, or a traffic change.

I avoid the easy trap of just raising the timeout — that hides the latency problem and eats even more resources.

Once I've made the targeted fix, I load-test the real path, confirm p50/p95/p99 latency and error rates, saturation, dependency health, and business metrics, and add a regression test or deployment guard based on what actually caused it.

## 6. Can strict use of the Single Responsibility Principle increase complexity in a distributed system? (True or False)

**Answer:**

True. A good responsibility boundary improves ownership and makes changes safer to isolate, but applying the principle too mechanically can leave you with far too many tiny services.

Every service boundary adds a network call, a new way to partially fail, its own deployment and versioning, observability, security, data-consistency concerns, testing, and coordination between teams. "Single responsibility" should describe one cohesive business capability with clear ownership — not one class or function per service.

I look at coupling, how often each part changes independently, scaling needs, who owns the data, latency, transaction requirements, team ownership, and how mature the team's operations are. A well-structured modular monolith can genuinely be safer than splitting into microservices too early.

I only pull out a separate service when the boundary gives measurable independent value and the team can actually operate it — and I revisit that decision as usage changes.
