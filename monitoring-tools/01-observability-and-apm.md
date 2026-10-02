# Monitoring Tools: Observability Fundamentals and APM

> Monitoring versus observability, signal flow, golden signals, correlation, alert quality, and APM tools such as Dynatrace, Datadog, New Relic and OpenTelemetry.

## Key Concepts

### Monitoring and Observability

**Monitoring** checks known conditions using predefined metrics, dashboards and alerts. **Observability** is broader: it's the ability to understand what's happening inside a system just from its outputs, including behavior nobody predicted when the dashboards were built.

The main signals are:

- **Metrics:** numeric time series that show scope, rate and trends efficiently.
- **Logs:** timestamped event records that explain what a component decided or experienced.
- **Traces:** the end-to-end path of a request across services and dependencies.
- **Profiles:** sampled CPU or memory behavior that helps locate expensive code.

A trace contains multiple spans. For example:

```text
Trace: customer places an order
├── API span: validate request       40 ms
├── Inventory span: reserve stock   120 ms
├── Payment span: authorize payment 300 ms
└── Database span: save order        60 ms
```

Each span can record service, operation, duration, status and a few carefully chosen attributes. A shared trace or correlation ID is what connects traces to logs. Request IDs belong in traces and logs — never in metric labels.

### Typical Signal Flow

```text
Applications, hosts and Kubernetes
        ↓ instrumentation/exporters/collector
Metrics → Prometheus or Azure Monitor
Logs    → Loki or Log Analytics
Traces  → Tempo or Application Insights
        ↓
Grafana / Azure dashboards
        ↓
Alerting, investigation and runbooks
```

OpenTelemetry provides vendor-neutral APIs, SDKs and collectors for this data. Grafana Alloy is an OpenTelemetry Collector distribution that can collect and route metrics, logs and traces to compatible backends.

### Golden Signals and SRE Practice

The four golden signals are:

| Signal | What it tells you |
|---|---|
| **Latency** | How long successful and failed operations take |
| **Traffic** | Demand — requests, transactions or messages |
| **Errors** | Explicit failures and incorrect results |
| **Saturation** | How close a constrained resource is to its limit |

Define user-visible **service-level indicators (SLIs)** and a **service-level objective (SLO)** with an error budget. Multi-window, multi-burn-rate alerts catch both a fast severe burn and a slower sustained one, without paging for harmless short spikes.

Monitoring shouldn't mean someone staring at a dashboard all day. Dashboards are for understanding; alerts should only notify an owner when there's a timely action to take.

Capacity forecasts, loss-of-redundancy signals, and security or data-integrity signals fill in the gaps around SLO alerting.

### Correlation and Incident Investigation

During an incident:

1. Confirm customer impact, which services are affected, the environment, and the time window.
2. Use metrics to work out the scope and when the behavior changed.
3. Follow a trace or exemplar to find the slow or failing dependency.
4. Search structured logs using the trace ID, and compare the first failure against recent deployments or configuration changes.
5. Mitigate safely, confirm recovery using the original user-visible signal, and preserve evidence for the root-cause writeup.

Keep service, environment, version, cluster and region attributes consistent across all three signal types so you can pivot between them. Also keep a handle on cardinality — the number of unique label combinations a metric produces — along with sampling, redaction, access, retention and cost.

### Alert Quality

Cut noise through ownership, deduplication, grouping, inhibition, maintenance windows, and removing alerts nobody can act on. When several alerts fire at once, prioritize by customer or business impact, security or data risk, SLO burn, scope of impact, and urgency.

Declare a single incident for a shared root cause and group the downstream symptoms under it.

**Serverless observability** follows an event across APIs, functions, queues and dependencies, and covers invocation, error, duration, cold start, throttling, concurrency, retries, queue age and dead-letter behavior.

**AIOps** can group related symptoms, spot unusual behavior, rank likely causes, forecast risk, and suggest controlled runbooks. It supports good instrumentation, clear service targets, responder judgment and root-cause review — it doesn't replace any of them.

Any automated action needs constrained authority, an audit trail, a rollback path and verification afterward. Detailed AIOps material is maintained in [`Ops/05-aiops.md`](../Ops/05-aiops.md).

### What APM Does

Application Performance Monitoring (APM) connects a user's request to everything that handled it: the service code, its dependencies, and the underlying infrastructure. It does this through request metrics, distributed traces, error tracking, logs, service topology maps, profiling, and sometimes real-user and synthetic monitoring.

### Common APM Tools

| Tool | Type |
| --- | --- |
| Dynatrace | Commercial, full-stack |
| Datadog | Commercial, full-stack |
| New Relic | Commercial, full-stack |
| Application Insights | Azure-native |
| OpenTelemetry | Vendor-neutral instrumentation and export standard |

Dynatrace, Datadog, and New Relic are commercial platforms that cover the full stack. Application Insights is Azure's native option. OpenTelemetry isn't a platform on its own — it's a standard way to instrument code and export the data, so you can send it to whichever backend you choose.

### Choosing an APM Tool

The right choice depends on: application and runtime coverage, whether instrumentation is automatic or manual, Kubernetes and cloud integration, topology mapping, query and retention needs, sampling behavior, data residency, access control, operational effort, and cost.

### Using APM Well

A tool by itself isn't observability. To get real value out of it:

- Define clear service and business indicators to track.
- Propagate trace context across service calls.
- Mark deployments so before/after comparisons are easy.
- Redact sensitive data from captured attributes.
- Assign clear ownership for dashboards and alerts.

### Diagnosing a Slow API

1. Compare P95/P99 latency and error rates before and after the change.
2. Pick a few representative slow traces to dig into.
3. Separate time spent in service code from time spent in dependencies.
4. Check database, cache, and external calls, and check whether the runtime is close to a resource limit.
5. Fix the proven bottleneck.
6. Re-verify the original slow user transaction to confirm it's resolved.

## Interview Questions

### 1. What are the four golden signals?

**Answer:**

Latency, traffic, errors, and saturation. Saturation means how close a resource is to its limit. For an API, I'd measure percentile latency, request rate, the ratio of failed or incorrect outcomes, and the limiting resources — things like CPU, queues, pools or connections.

Together these connect user impact to demand and capacity better than CPU alone would. I define an SLO around them, alert on sustained impact or error-budget burn, and drop into component-level detail only for diagnosis.

### 2. How do you compare metrics, logs and traces?

**Answer:**

Metrics tell you when and where a symptom started. Traces show which hop is slow or failing. Structured logs explain what that component decided or did. All three share service, environment, version, region and trace-context fields so you can move between them.

In practice, I narrow the time window, compare against healthy traffic, pick a trace example from the latency or error signal, look up its trace ID in the logs, and overlay recent deployment or configuration changes.

I keep an eye on cardinality — the number of unique label combinations a metric can produce — since unbounded cardinality can overwhelm a metrics system. I also retain error and tail traces appropriately and redact sensitive log and trace fields. After a fix, I confirm all three signals recover, along with the actual business transaction.

### 3. How would you implement a comprehensive observability strategy for a microservices architecture deployed across multiple Kubernetes clusters?

**Answer:**

The strategy rests on three pillars: metrics, logs and traces. For metrics, I'd deploy Prometheus with Thanos for long-term storage and cross-cluster querying.

Each service exposes its own business and technical metrics through Prometheus exporters, with standardized Grafana dashboards for service health and performance.

For logging, I'd run Fluent Bit as a DaemonSet to collect container logs and forward them to OpenSearch, with structured JSON logging standardized across services so queries stay consistent.

For distributed tracing, I'd instrument every service with OpenTelemetry, adjust sampling rates to traffic volume, and send traces to Jaeger for visualization and analysis. Service-to-service dependencies get mapped automatically from Istio service mesh data, which also supplies request rate, error and duration metrics. I'd define SLOs per service using Prometheus recording rules and alert on error-budget consumption.

All observability data carries consistent metadata — cluster, namespace, service, version — so it can be correlated across systems. This is what takes MTTR from hours down to minutes: you can trace the root cause of a problem that spans several services instead of hunting through each one separately.

### 4. How do you observe serverless or multi-cloud workflows?

**Answer:**

I propagate trace context and an event ID across API, function, queue and dependency boundaries, and collect invocation, error, duration, cold start, throttling, concurrency, retry, queue age and dead-letter signals. OpenTelemetry gives consistent instrumentation across these; platform-native tools add extra service-specific detail.

Dashboards are organized around the business flow rather than individual services. I only replay failed events after the underlying cause is fixed, and only with idempotency controls in place — meaning it's safe to process the same event twice. Sampling, privacy, retention, cardinality and cost all need to be designed for deliberately, not left as defaults.

### 5. Compare Dynatrace, Datadog, New Relic and OpenTelemetry.

**Answer:**

Dynatrace, Datadog, and New Relic are commercial observability platforms. Each combines agents, APM, infrastructure monitoring, logs, traces, topology maps, user-experience data, and automated analysis, in different mixes.

OpenTelemetry is different. It's an open standard for instrumenting code and collecting telemetry data, not a complete product for storing and analyzing it. You still need a backend to send that data to.

When choosing between them, I look at runtime, cloud, and Kubernetes coverage, trace quality, profiling, real-user and synthetic monitoring, integrations, data residency, access control, sampling and retention limits, operational effort, and cost. I run a pilot against a real service and a real incident query before deciding.

These tools' built-in automation can point toward a likely cause, but any actual change still needs evidence and a safe approval process. I don't let a vendor's suggestion skip review.

### 6. How do you design SLO-based alerting with low fatigue?

**Answer:**

I define a user-visible SLI with a target and a time window, calculate its error budget, and use multi-window, multi-burn-rate alerts. A fast, severe burn pages quickly. A slower, sustained burn catches decline over time without paging for harmless short spikes.

Capacity trends that aren't urgent go to tickets or dashboards instead of pages.

Every page includes an owner, supporting evidence, the SLO impact, and a runbook. Grouping, deduplication, inhibition and maintenance windows cut down on alert storms. After incidents, I test that alerts actually get delivered and review false positives, missed incidents, how actionable each alert was, and overall page volume.

### 7. Multiple critical alerts fire together. How do you prioritize?

**Answer:**

I prioritize by customer or business impact, security or data-integrity risk, SLO burn, how widespread the impact is, and urgency — not by which alert happened to fire first. I declare a single incident, assign command and communications roles, find the earliest shared dependency, and suppress the downstream duplicate alerts it's causing.

One responder stabilizes the situation — a known rollback, a traffic shift, or isolating the failing component — while another preserves evidence for later. After recovery, the incident timeline is used to improve dependency mapping, severities and runbooks.

### 8. Infrastructure is healthy and dashboards are green, but the system feels slow. What do you check first?

**Answer:**

I treat the user-reported slowness as valid evidence on its own. First I confirm its scope using real-user monitoring, synthetic transactions and business KPIs — conversion rate, successful checkouts, queue completion. "Green" dashboards often only cover host CPU and basic availability, not the actual user experience.

I compare against a healthy baseline across p95/p99 latency, errors by route, client and network geography, DNS/TLS timing, dependency latency, resource saturation, queue age, database connection pools, and any recent changes.

Then I add the missing user-facing SLI and alert on it, so the dashboard reflects the actual service outcome instead of just infrastructure reachability.

### 9. How do you use APM to find a latency regression?

**Answer:**

First, I mark the deployment time in the APM tool. Then I compare request latency percentiles and error rates before and after that point, split out by version.

I pick a few representative slow traces and break down where the time is actually going: gateway, service code, database, cache, queue, or an external dependency.

I check whether the runtime is running close to a resource limit, like CPU, memory, threads, or a connection pool, and pull logs for the same trace ID. I compare all of this against healthy traffic to confirm where the real difference is.

Once I've proven the bottleneck, I fix it: a rollback, added capacity, or a targeted code fix.

Finally, I re-check the original slow user transaction to confirm it's actually fixed, and I add a regression test or an SLO alert so it doesn't slip through unnoticed next time.

### 10. How do you troubleshoot high latency on a load balancer?

**Answer:**

First I figure out where the latency actually is: DNS/connect/TLS, load-balancer processing, the backend connection, or the application's own response time. I compare the load balancer's total time against the backend's response time, status codes, healthy target count, connection limits, TLS handshake time, request rate, and how traffic is spread across regions.

Then I check backend CPU/memory, queue depth, pod readiness, application traces, database/cache dependencies, network drops, and any recent changes. High total time with low backend time points toward the edge, network, or TLS. High backend time means the problem is downstream.

I mitigate safely — by removing bad targets, scaling, rolling back, or shifting traffic — then confirm p95/p99 latency and error rate have actually recovered, and write down the root cause.

### 11. How do you monitor API performance in Azure API Management or an API gateway?

**Answer:**

I track request volume, the success/error ratio by status code, gateway latency, backend latency, throttling, cache hit rate, policy errors, backend health, and dependency failures. Application Insights or OpenTelemetry links the gateway's requests to the backend's traces, while Azure Monitor and APIM diagnostics give me the platform-level data.

When latency increases, I compare gateway time against backend time, break it down by API/operation/region/status, and check for recent policy or deployment changes, quota limits, TLS/DNS issues, and backend capacity. I sample payload metadata carefully, without logging tokens or sensitive request bodies.

Alerts are tied to actual SLO/error-budget impact, and synthetic tests exercise both authentication and a real, lightweight API call.

### 12. How do you monitor API performance in Apigee/Azure API Management? *(scenario)*

**Answer:** Collect API response time, error rate, and request logs. Add dashboards for the service target, configure useful alerts, and apply rate limiting where needed.

**Mini-case:** Apigee showed a 30% response-time increase for one backend API. The backend pods were at their resource limit, so scaling them restored normal response times.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation (how close a resource is to its limit), and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

### 13. How do you investigate high API latency in GCP/Azure APIs? *(scenario)*

**Answer:** Check Cloud Trace / Application Insights → Identify slow endpoints → Scale backend pods → Add caching/CDN.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation, and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

### 14. How do you handle high latency issues in GCP/Azure services? *(scenario)*

**Answer:**

- Check network logs.
- Use Cloud Monitoring (Stackdriver/Azure Monitor).
- Scale infra (VMs, AKS nodes).
- Optimize load balancer & caching.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation, and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

### 15. How does AIOps use observability data without becoming another source of noise?

**Answer:**

I give AIOps consistent service topology, clear ownership, deployment history, and high-quality metrics, logs and traces. Then I check its correlation and anomaly results against incidents that were actually confirmed.

Done well, it groups related symptoms together, ranks impact, and supplies evidence for a probable cause — instead of raising a new alert for every anomaly score it produces. Only signals that are actionable and confident enough about user impact should page anyone. Forecasts and weak anomalies go to dashboards or tickets instead.

I monitor the underlying models for missing data, drift, precision and false-positive rate. Any automated remediation is limited to narrow, pre-approved runbooks, with approval steps where needed and SLO verification after it acts.
