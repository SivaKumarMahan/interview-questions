# Observability Networking Interview Questions

### 1. How do you troubleshoot high latency on a load balancer?

**Answer:**

First I figure out where the latency actually is: DNS/connect/TLS, load-balancer processing, the backend connection, or the application's own response time. I compare the load balancer's total time against the backend's response time, status codes, healthy target count, connection limits, TLS handshake time, request rate, and how traffic is spread across regions.

Then I check backend CPU/memory, queue depth, pod readiness, application traces, database/cache dependencies, network drops, and any recent changes. High total time with low backend time points toward the edge, network, or TLS. High backend time means the problem is downstream.

I mitigate safely — by removing bad targets, scaling, rolling back, or shifting traffic — then confirm p95/p99 latency and error rate have actually recovered, and write down the root cause.

---

### 2. How do you monitor API performance in Azure API Management or an API gateway?

**Answer:**

I track request volume, the success/error ratio by status code, gateway latency, backend latency, throttling, cache hit rate, policy errors, backend health, and dependency failures. Application Insights or OpenTelemetry links the gateway's requests to the backend's traces, while Azure Monitor and APIM diagnostics give me the platform-level data.

When latency increases, I compare gateway time against backend time, break it down by API/operation/region/status, and check for recent policy or deployment changes, quota limits, TLS/DNS issues, and backend capacity. I sample payload metadata carefully, without logging tokens or sensitive request bodies.

Alerts are tied to actual SLO/error-budget impact, and synthetic tests exercise both authentication and a real, lightweight API call.
