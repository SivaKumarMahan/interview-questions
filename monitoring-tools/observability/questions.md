## 1. What are the four golden signals?

**Answer:**

Latency, traffic, errors and saturation. For an API I measure percentile latency, request rate, failed/incorrect outcome ratio and limiting resources such as CPU, queues, pools or connections. They connect user impact to demand and capacity better than CPU alone. I define an SLO, alert on sustained impact/error-budget burn and use component detail for diagnosis.

## 2. How do you design SLO-based alerting with low fatigue?

**Answer:**

I define a user-visible SLI and target/window, calculate its error budget, and use multi-window multi-burn-rate alerts. A fast severe burn pages quickly; a slower sustained burn detects degradation without paging for harmless spikes. Nonurgent capacity trends create tickets or dashboards.

Every page has owner, evidence, SLO impact and runbook. Grouping, deduplication, inhibition and maintenance windows reduce storms. I test delivery and review false positives, missed incidents, actionability and page volume after incidents.

## 3. How do you correlate metrics, logs and traces?

**Answer:**

Metrics locate when and where a symptom began, traces reveal the slow/failing hop, and structured logs explain that component's decision. They share service, environment, version, region and W3C trace context. I narrow the time window, compare healthy traffic, select a trace exemplar from the latency/error signal, query its ID in logs and overlay deployment/configuration events.

I control metric cardinality, retain error/tail traces appropriately and redact sensitive log/trace attributes. After the fix, all signals and the business transaction must recover.

## 4. Multiple critical alerts fire together. How do you prioritize?

**Answer:**

I prioritize customer/business impact, security/data-integrity risk, SLO burn, blast radius and urgency—not notification order. I declare one incident, assign command and communications roles, identify the earliest shared dependency and inhibit downstream duplicates. One responder stabilizes through a known rollback, traffic shift or isolation while another preserves evidence. After recovery, the timeline improves dependency mapping, severities and runbooks.

## 5. How do you observe serverless or multi-cloud workflows?

**Answer:**

I propagate trace context and an event ID through API, function, queue and dependency boundaries and collect invocation, error, duration, cold start, throttle, concurrency, retry, queue age and dead-letter signals. OpenTelemetry provides consistent instrumentation while platform tools supply native service evidence. Dashboards follow the business flow, and replay occurs only after the cause is fixed with idempotency controls. Sampling, privacy, retention, cardinality and cost are designed explicitly.

## 6. How does AIOps use observability data without becoming another source of noise?

**Answer:**

I give AIOps consistent service topology, ownership, deployments and high-quality metrics, logs and traces, then evaluate correlation and anomaly results against confirmed incidents. It groups dependent symptoms, ranks impact and supplies evidence for a probable cause instead of generating one new alert for every anomaly score.

Only actionable, sufficiently confident user-impact signals page. Forecasts and weak anomalies go to dashboards or tickets. Models are monitored for missing data, drift, precision and false-positive rate. Automated remediation uses bounded runbooks, approval where needed and post-action SLO verification.

## 7. How would you implement a comprehensive observability strategy for a microservices architecture deployed across multiple Kubernetes clusters?

**Answer:**

The strategy rests on three pillars: metrics, logs, and traces. For metrics, I deploy Prometheus with Thanos for long-term storage and cross-cluster querying. Each service exposes custom business and technical metrics through Prometheus exporters, with standardized Grafana dashboards for service health and performance.

For logging, I use Fluent Bit as a DaemonSet to collect container logs and forward them to OpenSearch, with structured JSON logging standardized across services for consistent querying. For distributed tracing, I implement OpenTelemetry instrumentation in all services with sampling rates adjusted to traffic volume, sending traces to Jaeger for visualization and analysis.

Service-to-service dependencies are mapped automatically through Istio service mesh telemetry, which also provides request rate, error, and duration metrics. I implement SLOs for each service using Prometheus recording rules and alert on error-budget consumption. All observability data is tagged with consistent metadata (cluster, namespace, service, version), enabling correlation across systems. This approach reduces MTTR from hours to minutes by quickly identifying the root cause of complex issues spanning multiple services.
