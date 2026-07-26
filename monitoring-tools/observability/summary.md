# Observability Summary

## Monitoring and Observability

**Monitoring** checks known conditions with predefined metrics, dashboards and alerts. **Observability** is the ability to understand a system's internal state from its outputs, including behavior that was not predicted when the dashboards were created.

The main telemetry signals are:

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

Each span can record service, operation, duration, status and carefully selected attributes. A shared trace or correlation ID connects traces and logs. Request IDs belong in traces and logs, not metric labels.

## Typical Signal Flow

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

OpenTelemetry provides vendor-neutral APIs, SDKs and collectors for telemetry. Grafana Alloy is an OpenTelemetry Collector distribution that can collect and route metrics, logs and traces to compatible backends.

## Golden Signals and SRE Practice

The four golden signals are:

- **Latency:** how long successful and failed operations take.
- **Traffic:** demand, such as requests, transactions or messages.
- **Errors:** explicit failures and incorrect results.
- **Saturation:** how close a constrained resource is to its limit.

Define user-visible **service-level indicators (SLIs)** and a **service-level objective (SLO)** with an error budget. Multi-window, multi-burn-rate alerts identify both fast severe and slower sustained budget consumption without paging for harmless short spikes.

Monitoring is not continuous manual dashboard watching. Dashboards support understanding; alerts should notify an owner only when a timely action is available. Capacity forecasts, loss-of-redundancy signals and security/data-integrity signals complement SLO alerting.

## Correlation and Incident Investigation

During an incident:

1. Confirm customer impact, affected services, environment and time window.
2. Use metrics to determine scope and when the behavior changed.
3. Follow a trace or exemplar to identify the slow or failing dependency.
4. Search structured logs using the trace ID and compare the first failure with deployments or configuration changes.
5. Mitigate safely, verify recovery using the original user-visible signal and preserve evidence for root-cause analysis.

Use consistent service, environment, version, cluster and region attributes across signals. Control telemetry cardinality, sampling, redaction, access, retention and cost.

## Alert Quality

Reduce noise through ownership, deduplication, grouping, inhibition, maintenance windows and removal of unactionable alerts. During simultaneous alerts, prioritize customer/business impact, security or data risk, SLO burn, blast radius and urgency. Declare one incident for a shared cause and group downstream symptoms.

**Serverless observability** follows an event across APIs, functions, queues and dependencies and covers invocation, error, duration, cold start, throttling, concurrency, retries, queue age and dead-letter behavior.

**AIOps** can correlate symptoms, identify anomalies, rank probable causes, forecast risk and recommend guarded runbooks. It complements rather than replaces good instrumentation, SLOs, responder judgment and root-cause review. Automated actions require constrained authority, audit evidence, rollback and verification. Detailed AIOps material is maintained in [`Ops/AIOps`](../../Ops/AIOps/README.md).
