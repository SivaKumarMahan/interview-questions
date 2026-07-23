# Observability Summary

**Monitoring** reports known conditions; **observability** uses system outputs to investigate unfamiliar behavior. Metrics show trends and scope, traces show the request path and slow/failing hop, and structured logs explain local decisions. All signals need consistent service, environment, version, region and trace context. Request IDs belong in traces/logs, not metric labels.

The **golden signals** are latency, traffic, errors and saturation. Define user-visible SLIs and an SLO with an error budget. Multi-window, multi-burn-rate alerts page for fast severe or slower sustained budget consumption while ignoring harmless short spikes. Capacity forecasts and loss-of-redundancy signals complement SLO alerts.

Reduce noise through ownership, deduplication, grouping, inhibition, maintenance windows and removal of unactionable alerts. During multiple simultaneous alerts, prioritize customer/business impact, security/data risk, SLO burn, blast radius and urgency; declare one incident, group downstream symptoms and stabilize the shared failure while preserving evidence.

**Serverless observability** correlates an event across API, functions, queues and dependencies and covers invocation, error, duration, cold start, throttle, concurrency, retry, queue age and dead-letter behavior. OpenTelemetry, platform telemetry and structured correlation support multi-cloud flows. Sampling, retention, cardinality, privacy and telemetry cost are design requirements.

**AIOps** consumes this observability context to correlate symptoms, identify anomalies, rank probable causes, forecast risk and recommend or execute guarded runbooks. It complements rather than replaces dashboards, SLOs, responder judgment and root-cause review. Any automated action requires evidence, constrained authority, audit logs, rollback and verification against the original user-visible signal. Detailed AIOps material is maintained in [`Ops/AIOps`](../../Ops/AIOps/README.md).
