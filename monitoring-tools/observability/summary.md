# Observability Summary

## Monitoring and Observability

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

OpenTelemetry provides vendor-neutral APIs, SDKs and collectors for this data. Grafana Alloy is an OpenTelemetry Collector distribution that can collect and route metrics, logs and traces to compatible backends.

## Golden Signals and SRE Practice

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

## Correlation and Incident Investigation

During an incident:

1. Confirm customer impact, which services are affected, the environment, and the time window.
2. Use metrics to work out the scope and when the behavior changed.
3. Follow a trace or exemplar to find the slow or failing dependency.
4. Search structured logs using the trace ID, and compare the first failure against recent deployments or configuration changes.
5. Mitigate safely, confirm recovery using the original user-visible signal, and preserve evidence for the root-cause writeup.

Keep service, environment, version, cluster and region attributes consistent across all three signal types so you can pivot between them. Also keep a handle on cardinality — the number of unique label combinations a metric produces — along with sampling, redaction, access, retention and cost.

## Alert Quality

Cut noise through ownership, deduplication, grouping, inhibition, maintenance windows, and removing alerts nobody can act on. When several alerts fire at once, prioritize by customer or business impact, security or data risk, SLO burn, scope of impact, and urgency.

Declare a single incident for a shared root cause and group the downstream symptoms under it.

**Serverless observability** follows an event across APIs, functions, queues and dependencies, and covers invocation, error, duration, cold start, throttling, concurrency, retries, queue age and dead-letter behavior.

**AIOps** can group related symptoms, spot unusual behavior, rank likely causes, forecast risk, and suggest controlled runbooks. It supports good instrumentation, clear service targets, responder judgment and root-cause review — it doesn't replace any of them.

Any automated action needs constrained authority, an audit trail, a rollback path and verification afterward. Detailed AIOps material is maintained in [`Ops/AIOps`](../../Ops/AIOps/README.md).
