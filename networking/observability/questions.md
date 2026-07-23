# Observability Networking Interview Questions

### 1. How do you troubleshoot high latency on a load balancer?

**Answer:**

I establish whether latency is at DNS/connect/TLS, load balancer processing, backend connection, or application response. I compare load-balancer total time with backend response time, status codes, healthy target count, connection limits, TLS handshakes, request rate, and regional distribution.

Then I inspect backend CPU/memory, queue depth, Pod readiness, app traces, database/cache dependencies, network drops, and recent changes. A high total time with low backend time points toward edge/network/TLS; high backend time moves investigation downstream.

I mitigate safely by removing bad targets, scaling, rollback, or traffic shift, then validate P95/P99 and error rate and document the root cause.

---

### 2. How do you monitor API performance in Azure API Management or an API gateway?

**Answer:**

I track request volume, success/error ratio by status, gateway latency, backend latency, throttling, cache hit rate, policy errors, backend health, and dependency failures. Application Insights or OpenTelemetry correlates gateway requests with backend traces, while Azure Monitor/APIM diagnostics provide platform data.

For increased latency I compare gateway vs. backend time, segment by API/operation/region/status, inspect recent policy/deployment changes, quotas, TLS/DNS, and backend capacity. I sample payload metadata safely without logging tokens or sensitive bodies.

Alerts reflect SLO/error-budget impact, and synthetic tests exercise authentication plus a real lightweight API flow.
