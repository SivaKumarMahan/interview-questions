## 1. What are the four golden signals?

**Answer:**

Latency, traffic, errors, and saturation. Saturation means how close a resource is to its limit. For an API, I'd measure percentile latency, request rate, the ratio of failed or incorrect outcomes, and the limiting resources — things like CPU, queues, pools or connections.

Together these connect user impact to demand and capacity better than CPU alone would. I define an SLO around them, alert on sustained impact or error-budget burn, and drop into component-level detail only for diagnosis.

## 2. How do you design SLO-based alerting with low fatigue?

**Answer:**

I define a user-visible SLI with a target and a time window, calculate its error budget, and use multi-window, multi-burn-rate alerts. A fast, severe burn pages quickly. A slower, sustained burn catches decline over time without paging for harmless short spikes.

Capacity trends that aren't urgent go to tickets or dashboards instead of pages.

Every page includes an owner, supporting evidence, the SLO impact, and a runbook. Grouping, deduplication, inhibition and maintenance windows cut down on alert storms. After incidents, I test that alerts actually get delivered and review false positives, missed incidents, how actionable each alert was, and overall page volume.

## 3. How do you compare metrics, logs and traces?

**Answer:**

Metrics tell you when and where a symptom started. Traces show which hop is slow or failing. Structured logs explain what that component decided or did. All three share service, environment, version, region and trace-context fields so you can move between them.

In practice, I narrow the time window, compare against healthy traffic, pick a trace example from the latency or error signal, look up its trace ID in the logs, and overlay recent deployment or configuration changes.

I keep an eye on cardinality — the number of unique label combinations a metric can produce — since unbounded cardinality can overwhelm a metrics system. I also retain error and tail traces appropriately and redact sensitive log and trace fields. After a fix, I confirm all three signals recover, along with the actual business transaction.

## 4. Multiple critical alerts fire together. How do you prioritize?

**Answer:**

I prioritize by customer or business impact, security or data-integrity risk, SLO burn, how widespread the impact is, and urgency — not by which alert happened to fire first. I declare a single incident, assign command and communications roles, find the earliest shared dependency, and suppress the downstream duplicate alerts it's causing.

One responder stabilizes the situation — a known rollback, a traffic shift, or isolating the failing component — while another preserves evidence for later. After recovery, the incident timeline is used to improve dependency mapping, severities and runbooks.

## 5. How do you observe serverless or multi-cloud workflows?

**Answer:**

I propagate trace context and an event ID across API, function, queue and dependency boundaries, and collect invocation, error, duration, cold start, throttling, concurrency, retry, queue age and dead-letter signals. OpenTelemetry gives consistent instrumentation across these; platform-native tools add extra service-specific detail.

Dashboards are organized around the business flow rather than individual services. I only replay failed events after the underlying cause is fixed, and only with idempotency controls in place — meaning it's safe to process the same event twice. Sampling, privacy, retention, cardinality and cost all need to be designed for deliberately, not left as defaults.

## 6. How does AIOps use observability data without becoming another source of noise?

**Answer:**

I give AIOps consistent service topology, clear ownership, deployment history, and high-quality metrics, logs and traces. Then I check its correlation and anomaly results against incidents that were actually confirmed.

Done well, it groups related symptoms together, ranks impact, and supplies evidence for a probable cause — instead of raising a new alert for every anomaly score it produces. Only signals that are actionable and confident enough about user impact should page anyone. Forecasts and weak anomalies go to dashboards or tickets instead.

I monitor the underlying models for missing data, drift, precision and false-positive rate. Any automated remediation is limited to narrow, pre-approved runbooks, with approval steps where needed and SLO verification after it acts.

## 7. How would you implement a comprehensive observability strategy for a microservices architecture deployed across multiple Kubernetes clusters?

**Answer:**

The strategy rests on three pillars: metrics, logs and traces. For metrics, I'd deploy Prometheus with Thanos for long-term storage and cross-cluster querying.

Each service exposes its own business and technical metrics through Prometheus exporters, with standardized Grafana dashboards for service health and performance.

For logging, I'd run Fluent Bit as a DaemonSet to collect container logs and forward them to OpenSearch, with structured JSON logging standardized across services so queries stay consistent.

For distributed tracing, I'd instrument every service with OpenTelemetry, adjust sampling rates to traffic volume, and send traces to Jaeger for visualization and analysis. Service-to-service dependencies get mapped automatically from Istio service mesh data, which also supplies request rate, error and duration metrics. I'd define SLOs per service using Prometheus recording rules and alert on error-budget consumption.

All observability data carries consistent metadata — cluster, namespace, service, version — so it can be correlated across systems. This is what takes MTTR from hours down to minutes: you can trace the root cause of a problem that spans several services instead of hunting through each one separately.

## 8. Infrastructure is healthy and dashboards are green, but the system feels slow. What do you check first?

**Answer:**

I treat the user-reported slowness as valid evidence on its own. First I confirm its scope using real-user monitoring, synthetic transactions and business KPIs — conversion rate, successful checkouts, queue completion. "Green" dashboards often only cover host CPU and basic availability, not the actual user experience.

I compare against a healthy baseline across p95/p99 latency, errors by route, client and network geography, DNS/TLS timing, dependency latency, resource saturation, queue age, database connection pools, and any recent changes.

Then I add the missing user-facing SLI and alert on it, so the dashboard reflects the actual service outcome instead of just infrastructure reachability.
