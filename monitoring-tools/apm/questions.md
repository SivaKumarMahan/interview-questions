## 1. Compare Dynatrace, Datadog, New Relic and OpenTelemetry.

**Answer:**

Dynatrace, Datadog, and New Relic are commercial observability platforms. Each combines agents, APM, infrastructure monitoring, logs, traces, topology maps, user-experience data, and automated analysis, in different mixes.

OpenTelemetry is different. It's an open standard for instrumenting code and collecting telemetry data, not a complete product for storing and analyzing it. You still need a backend to send that data to.

When choosing between them, I look at runtime, cloud, and Kubernetes coverage, trace quality, profiling, real-user and synthetic monitoring, integrations, data residency, access control, sampling and retention limits, operational effort, and cost. I run a pilot against a real service and a real incident query before deciding.

These tools' built-in automation can point toward a likely cause, but any actual change still needs evidence and a safe approval process. I don't let a vendor's suggestion skip review.

## 2. How do you use APM to find a latency regression?

**Answer:**

First, I mark the deployment time in the APM tool. Then I compare request latency percentiles and error rates before and after that point, split out by version.

I pick a few representative slow traces and break down where the time is actually going: gateway, service code, database, cache, queue, or an external dependency.

I check whether the runtime is running close to a resource limit, like CPU, memory, threads, or a connection pool, and pull logs for the same trace ID. I compare all of this against healthy traffic to confirm where the real difference is.

Once I've proven the bottleneck, I fix it: a rollback, added capacity, or a targeted code fix.

Finally, I re-check the original slow user transaction to confirm it's actually fixed, and I add a regression test or an SLO alert so it doesn't slip through unnoticed next time.
