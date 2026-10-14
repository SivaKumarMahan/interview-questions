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

Any automated action needs constrained authority, an audit trail, a rollback path and verification afterward. Detailed AIOps material is maintained in [`ops/05-aiops.md`](../ops/05-aiops.md).

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

<details><summary>Q1. [Basic] What are the four golden signals?</summary>

**Answer:**

Latency, traffic, errors, and saturation. Saturation means how close a resource is to its limit. For an API, I'd measure percentile latency, request rate, the ratio of failed or incorrect outcomes, and the limiting resources — things like CPU, queues, pools or connections.

Together these connect user impact to demand and capacity better than CPU alone would. I define an SLO around them, alert on sustained impact or error-budget burn, and drop into component-level detail only for diagnosis.

</details>

<details><summary>Q2. [Basic] How do you compare metrics, logs and traces?</summary>

**Answer:**

Metrics tell you when and where a symptom started. Traces show which hop is slow or failing. Structured logs explain what that component decided or did. All three share service, environment, version, region and trace-context fields so you can move between them.

In practice, I narrow the time window, compare against healthy traffic, pick a trace example from the latency or error signal, look up its trace ID in the logs, and overlay recent deployment or configuration changes.

I keep an eye on cardinality — the number of unique label combinations a metric can produce — since unbounded cardinality can overwhelm a metrics system. I also retain error and tail traces appropriately and redact sensitive log and trace fields. After a fix, I confirm all three signals recover, along with the actual business transaction.

</details>

<details><summary>Q3. [Advanced] How would you implement a comprehensive observability strategy for a microservices architecture deployed across multiple Kubernetes clusters?</summary>

**Answer:**

The strategy rests on three pillars: metrics, logs and traces. For metrics, I'd deploy Prometheus with Thanos for long-term storage and cross-cluster querying.

Each service exposes its own business and technical metrics through Prometheus exporters, with standardized Grafana dashboards for service health and performance.

For logging, I'd run Fluent Bit as a DaemonSet to collect container logs and forward them to OpenSearch, with structured JSON logging standardized across services so queries stay consistent.

For distributed tracing, I'd instrument every service with OpenTelemetry, adjust sampling rates to traffic volume, and send traces to Jaeger for visualization and analysis. Service-to-service dependencies get mapped automatically from Istio service mesh data, which also supplies request rate, error and duration metrics. I'd define SLOs per service using Prometheus recording rules and alert on error-budget consumption.

All observability data carries consistent metadata — cluster, namespace, service, version — so it can be correlated across systems. This is what takes MTTR from hours down to minutes: you can trace the root cause of a problem that spans several services instead of hunting through each one separately.

</details>

<details><summary>Q4. [Advanced] How do you observe serverless or multi-cloud workflows?</summary>

**Answer:**

I propagate trace context and an event ID across API, function, queue and dependency boundaries, and collect invocation, error, duration, cold start, throttling, concurrency, retry, queue age and dead-letter signals. OpenTelemetry gives consistent instrumentation across these; platform-native tools add extra service-specific detail.

Dashboards are organized around the business flow rather than individual services. I only replay failed events after the underlying cause is fixed, and only with idempotency controls in place — meaning it's safe to process the same event twice. Sampling, privacy, retention, cardinality and cost all need to be designed for deliberately, not left as defaults.

</details>

<details><summary>Q5. [Intermediate] Compare Dynatrace, Datadog, New Relic and OpenTelemetry.</summary>

**Answer:**

Dynatrace, Datadog, and New Relic are commercial observability platforms. Each combines agents, APM, infrastructure monitoring, logs, traces, topology maps, user-experience data, and automated analysis, in different mixes.

OpenTelemetry is different. It's an open standard for instrumenting code and collecting telemetry data, not a complete product for storing and analyzing it. You still need a backend to send that data to.

When choosing between them, I look at runtime, cloud, and Kubernetes coverage, trace quality, profiling, real-user and synthetic monitoring, integrations, data residency, access control, sampling and retention limits, operational effort, and cost. I run a pilot against a real service and a real incident query before deciding.

These tools' built-in automation can point toward a likely cause, but any actual change still needs evidence and a safe approval process. I don't let a vendor's suggestion skip review.

</details>

<details><summary>Q6. [Advanced] How do you design SLO-based alerting with low fatigue?</summary>

**Answer:**

I define a user-visible SLI with a target and a time window, calculate its error budget, and use multi-window, multi-burn-rate alerts. A fast, severe burn pages quickly. A slower, sustained burn catches decline over time without paging for harmless short spikes.

Capacity trends that aren't urgent go to tickets or dashboards instead of pages.

Every page includes an owner, supporting evidence, the SLO impact, and a runbook. Grouping, deduplication, inhibition and maintenance windows cut down on alert storms. After incidents, I test that alerts actually get delivered and review false positives, missed incidents, how actionable each alert was, and overall page volume.

</details>

<details><summary>Q7. [Advanced] Multiple critical alerts fire together. How do you prioritize?</summary>

**Answer:**

I prioritize by customer or business impact, security or data-integrity risk, SLO burn, how widespread the impact is, and urgency — not by which alert happened to fire first. I declare a single incident, assign command and communications roles, find the earliest shared dependency, and suppress the downstream duplicate alerts it's causing.

One responder stabilizes the situation — a known rollback, a traffic shift, or isolating the failing component — while another preserves evidence for later. After recovery, the incident timeline is used to improve dependency mapping, severities and runbooks.

</details>

<details><summary>Q8. [Advanced] Infrastructure is healthy and dashboards are green, but the system feels slow. What do you check first?</summary>

**Answer:**

I treat the user-reported slowness as valid evidence on its own. First I confirm its scope using real-user monitoring, synthetic transactions and business KPIs — conversion rate, successful checkouts, queue completion. "Green" dashboards often only cover host CPU and basic availability, not the actual user experience.

I compare against a healthy baseline across p95/p99 latency, errors by route, client and network geography, DNS/TLS timing, dependency latency, resource saturation, queue age, database connection pools, and any recent changes.

Then I add the missing user-facing SLI and alert on it, so the dashboard reflects the actual service outcome instead of just infrastructure reachability.

</details>

<details><summary>Q9. [Intermediate] How do you use APM to find a latency regression?</summary>

**Answer:**

First, I mark the deployment time in the APM tool. Then I compare request latency percentiles and error rates before and after that point, split out by version.

I pick a few representative slow traces and break down where the time is actually going: gateway, service code, database, cache, queue, or an external dependency.

I check whether the runtime is running close to a resource limit, like CPU, memory, threads, or a connection pool, and pull logs for the same trace ID. I compare all of this against healthy traffic to confirm where the real difference is.

Once I've proven the bottleneck, I fix it: a rollback, added capacity, or a targeted code fix.

Finally, I re-check the original slow user transaction to confirm it's actually fixed, and I add a regression test or an SLO alert so it doesn't slip through unnoticed next time.

</details>

<details><summary>Q10. [Intermediate] How do you troubleshoot high latency on a load balancer?</summary>

**Answer:**

First I figure out where the latency actually is: DNS/connect/TLS, load-balancer processing, the backend connection, or the application's own response time. I compare the load balancer's total time against the backend's response time, status codes, healthy target count, connection limits, TLS handshake time, request rate, and how traffic is spread across regions.

Then I check backend CPU/memory, queue depth, pod readiness, application traces, database/cache dependencies, network drops, and any recent changes. High total time with low backend time points toward the edge, network, or TLS. High backend time means the problem is downstream.

I mitigate safely — by removing bad targets, scaling, rolling back, or shifting traffic — then confirm p95/p99 latency and error rate have actually recovered, and write down the root cause.

</details>

<details><summary>Q11. [Intermediate] How do you monitor API performance in Azure API Management or an API gateway?</summary>

**Answer:**

I track request volume, the success/error ratio by status code, gateway latency, backend latency, throttling, cache hit rate, policy errors, backend health, and dependency failures. Application Insights or OpenTelemetry links the gateway's requests to the backend's traces, while Azure Monitor and APIM diagnostics give me the platform-level data.

When latency increases, I compare gateway time against backend time, break it down by API/operation/region/status, and check for recent policy or deployment changes, quota limits, TLS/DNS issues, and backend capacity. I sample payload metadata carefully, without logging tokens or sensitive request bodies.

Alerts are tied to actual SLO/error-budget impact, and synthetic tests exercise both authentication and a real, lightweight API call.

</details>

<details><summary>Q12. [Intermediate] How do you monitor API performance in Apigee/Azure API Management? <em>(scenario)</em></summary>

**Answer:** Collect API response time, error rate, and request logs. Add dashboards for the service target, configure useful alerts, and apply rate limiting where needed.

**Mini-case:** Apigee showed a 30% response-time increase for one backend API. The backend pods were at their resource limit, so scaling them restored normal response times.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation (how close a resource is to its limit), and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

</details>

<details><summary>Q13. [Intermediate] How do you investigate high API latency in GCP/Azure APIs? <em>(scenario)</em></summary>

**Answer:** Check Cloud Trace / Application Insights → Identify slow endpoints → Scale backend pods → Add caching/CDN.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation, and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

</details>

<details><summary>Q14. [Intermediate] How do you handle high latency issues in GCP/Azure services? <em>(scenario)</em></summary>

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

</details>

<details><summary>Q15. [Advanced] How does AIOps use observability data without becoming another source of noise?</summary>

**Answer:**

I give AIOps consistent service topology, clear ownership, deployment history, and high-quality metrics, logs and traces. Then I check its correlation and anomaly results against incidents that were actually confirmed.

Done well, it groups related symptoms together, ranks impact, and supplies evidence for a probable cause — instead of raising a new alert for every anomaly score it produces. Only signals that are actionable and confident enough about user impact should page anyone. Forecasts and weak anomalies go to dashboards or tickets instead.

I monitor the underlying models for missing data, drift, precision and false-positive rate. Any automated remediation is limited to narrow, pre-approved runbooks, with approval steps where needed and SLO verification after it acts.

</details>

<details><summary>Q16. [Advanced] CPU and memory are normal, but latency increased 10x. What do you check? <em>(asked in interview round)</em></summary>

**Answer:**

Normal CPU and memory mean the service is probably **waiting**, not working: on a dependency, a lock, a pool, the network or the disk. I use traces and the golden signals to find where the time is spent.

**Steps:**

1. **Scope it**: all endpoints or one? All instances or one? All regions? p50 or only p99? When did it start, and what changed?
2. **Traces**: open slow traces and find the span that grew: database, cache, external API, queue.
3. **Dependencies**: database slow queries, locks, replication lag, connection count; cache hit rate; third-party API latency.
4. **Pools and queues**: connection pool, thread pool or worker saturation (requests waiting for a connection look like latency with low CPU).
5. **Runtime**: garbage collection pauses, CPU throttling from container limits (`container_cpu_cfs_throttled_periods_total`) even when average CPU looks normal.
6. **Network and DNS**: TCP retransmissions, DNS lookup times, cross-zone or cross-region calls, TLS handshakes, load balancer queueing.
7. **Disk I/O**: high `await` with low CPU.
8. **Recent change**: release, config, feature flag, traffic mix, data growth (a query that became slow as a table grew).

**Decision flow:**

```text
Latency 10x, CPU/memory normal
      |
      v
One endpoint or all? one --> trace that endpoint --> slow span (DB query? external API?)
      |all
      v
One instance/zone? yes --> bad node, noisy neighbour, AZ network --> remove from rotation
      |no
      v
Pool saturation / throttling / GC? --> pool metrics, cfs throttling, GC logs
      |
      v
Shared dependency slow? --> DB locks/slow queries, cache misses, DNS, third party
```

**Example queries:**

```promql
histogram_quantile(0.99, sum by (le, route) (rate(http_server_request_duration_seconds_bucket[5m])))

sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="prod"}[5m]))
  / sum by (pod) (rate(container_cpu_cfs_periods_total{namespace="prod"}[5m]))

hikaricp_connections_pending{application="orders"}
```

**Important points:**

- Averages hide problems; always look at percentiles and per-instance breakdowns.
- CPU throttling with low average usage is common with tight CPU limits and spiky workloads.
- Retries with no backoff can turn a small slowdown into a 10x latency increase.

See also: [Observability and APM](../monitoring-tools/01-observability-and-apm.md), [SRE](../ops/03-sre.md), [Linux performance troubleshooting](../linux/09-performance-troubleshooting-and-production.md)

**Interview-ready answer:**

> "If CPU and memory are normal, the service is usually waiting on something rather than working hard. I scope the problem first: which endpoints, which instances, which percentile, and what changed at that time. Then I open distributed traces and find the span whose duration grew, which typically points to a slow database query, lock contention, a cache miss storm or a slow third-party API. I check connection and thread pool saturation, garbage collection pauses and CPU throttling from container limits, because those all add latency without high CPU. I also look at DNS and network retransmissions. Once I find the cause, I mitigate, for example by rolling back, scaling the pool or failing over, and then fix it properly."

</details>

<details><summary>Q17. [Advanced] Logs look normal but users report failures. What next? <em>(asked in interview round)</em></summary>

**Answer:**

If the logs look clean, either the failure happens **before** the request reaches the application, the application is **not logging** the failure, or I am **looking at the wrong logs**. I reproduce from the user's side and follow the request.

**Steps:**

1. **Get specifics**: time, region, user, request ID, URL, error message, browser or client version.
2. **Reproduce** from the user's perspective: synthetic checks, `curl` from outside, different regions and networks.
3. **Check the edge**: CDN, WAF (blocked requests), DNS, TLS certificate, load balancer and ingress logs. Many failures never reach the app.
4. **Check the right logs**: correct environment, all instances, all regions; log sampling or dropped logs in the pipeline.
5. **Use traces and request IDs**: follow one failing request across services.
6. **Look for silent failures**: errors caught and returned as `200` with an error body, timeouts in the client, frontend JavaScript errors (use real-user monitoring).
7. **Look at metrics**: error rate by status code at the edge, latency percentiles, dependency errors.
8. **Fix observability gaps** found during the investigation.

**Decision flow:**

```text
Users fail, logs clean
      |
      v
Reproducible from outside? --no--> region/ISP/client specific: DNS, CDN POP, client version
      |yes
      v
Reaches the LB/ingress? --no--> DNS, TLS, WAF, CDN
      |yes
      v
Reaches the app? --no--> LB/ingress errors, routing, health of targets
      |yes
      v
App returns success but wrong? --> silent errors, frontend errors, data issue --> traces + RUM
```

**Commands:**

```bash
curl -sv https://app.example.com/api/orders -H 'X-Request-ID: debug-123'
dig +short app.example.com @8.8.8.8
echo | openssl s_client -connect app.example.com:443 -servername app.example.com 2>/dev/null \
  | openssl x509 -noout -dates
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --since=30m | grep -v ' 200 '
```

**Important points:**

- Correlation IDs that travel from the edge through every service make this kind of problem fast to solve.
- Log levels can hide errors (`WARN` filtered out, or exceptions swallowed).
- Synthetic monitoring and real-user monitoring catch what server logs cannot see.

See also: [Logging](../monitoring-tools/04-logging.md), [Observability and APM](../monitoring-tools/01-observability-and-apm.md), [Production issues](../repetitive-questions/production-issues.md)

**Interview-ready answer:**

> "If logs look normal, the failure is probably happening before the request reaches the app, or the app is not logging it. I get specifics from users, such as time, region and request IDs, and try to reproduce from outside. Then I work from the edge inward: DNS, CDN, WAF blocks, TLS certificate, load balancer and ingress logs, because many failures never reach the application. I make sure I am looking at the right environment and all instances, and check for log sampling. Next I follow a failing request with traces and look for silent failures, such as errors returned with status 200 or frontend JavaScript errors visible only in real-user monitoring. Finally I close the observability gap so the next failure is visible."

</details>

<details><summary>Q18. [Advanced] How do you investigate high latency using Prometheus, Grafana and OpenTelemetry? <em>(asked in interview round)</em></summary>

**Answer:**

I use the three tools together: **Prometheus** tells me *that* latency is high and *where* (service, route, instance), **OpenTelemetry traces** tell me *which span* inside the request is slow, and **Grafana** links them, with logs, in one workflow.

**Steps:**

1. **Confirm in Prometheus/Grafana**: p95/p99 latency per service and route from histogram metrics; when did it start; does it correlate with traffic, deployments or errors?
2. **Narrow down**: break down by route, instance, zone and version. One route points to code or a query; one instance points to a node; all routes point to a shared dependency.
3. **Check saturation signals**: CPU throttling, pool usage, queue depth, GC, database metrics.
4. **Jump to traces**: Grafana exemplars on the latency histogram link to an OpenTelemetry trace for a slow request (in Tempo or Jaeger). Or query traces by service and duration.
5. **Read the trace waterfall**: find the longest span, sequential calls that could be parallel, retries, N+1 query patterns, gaps (time spent waiting in queues).
6. **Correlate logs** using the trace ID.
7. **Fix and verify**: compare latency before and after on the same dashboard.

**Flow:**

```text
Grafana alert: p99 latency high
      |
      v
Prometheus breakdown by route / pod / version / zone
      |
      v
Exemplar click --> OpenTelemetry trace in Tempo/Jaeger
      |
      v
Slow span? DB query | external HTTP | cache miss | lock wait | queue time
      |
      v
Logs for same trace_id --> root cause --> fix --> verify on dashboard
```

**Queries:**

```promql
# p99 latency per route (OpenTelemetry semantic conventions, seconds)
histogram_quantile(0.99,
  sum by (le, http_route) (rate(http_server_request_duration_seconds_bucket{service_name="checkout"}[5m])))

# Is it one pod?
histogram_quantile(0.99,
  sum by (le, pod) (rate(http_server_request_duration_seconds_bucket{service_name="checkout"}[5m])))

# Downstream client latency
histogram_quantile(0.99,
  sum by (le, server_address) (rate(http_client_request_duration_seconds_bucket{service_name="checkout"}[5m])))
```

TraceQL in Grafana Tempo to find slow traces with a slow database span:

```text
{ resource.service.name = "checkout" && duration > 2s } >> { span.db.system != nil && duration > 1s }
```

**OpenTelemetry Collector essentials:**

```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:
processors:
  batch: {}
  tail_sampling:
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 1000 }
exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling, batch]
      exporters: [otlp/tempo]
```

**Important points:**

- Use histograms, not summaries, so percentiles can be aggregated across instances.
- Tail-based sampling keeps the slow and failed traces you actually need, at a fraction of the cost.
- Exact metric names depend on the instrumentation and exporter; OpenTelemetry semantic conventions use `http.server.request.duration` in seconds, exported to Prometheus as `http_server_request_duration_seconds`.
- `tls: insecure` is only for an in-cluster example; use TLS between collectors and back ends in production.

See also: [Observability and APM](../monitoring-tools/01-observability-and-apm.md), [Prometheus](../monitoring-tools/02-prometheus.md), [Grafana and Alertmanager](../monitoring-tools/03-grafana-and-alertmanager.md), [Prometheus and Grafana hands-on setup](../monitoring-tools/11-prometheus-grafana-hands-on-setup.md)

**Interview-ready answer:**

> "I start in Grafana with Prometheus histogram metrics to confirm the latency increase and see p95 and p99 by route, Pod, version and zone, which tells me whether it is one endpoint, one instance or everything. I check saturation signals like CPU throttling, connection pools and database metrics at the same time. Then I click an exemplar on the latency panel to open an OpenTelemetry trace in Tempo or Jaeger, and read the waterfall to find the slow span, such as a database query, an external call, a lock or retries. Using the trace ID, I pull the matching logs. The collector uses tail-based sampling so slow and failed traces are always kept. After the fix, I verify on the same dashboard that latency is back to normal."

</details>
