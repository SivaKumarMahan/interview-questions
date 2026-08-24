# Logging Summary

## Centralized Logging

A centralized logging flow is:

```text
Application stdout/stderr, files or journal
        ↓
Collector/agent
        ↓
Durable searchable backend
        ↓
Dashboards, searches and alerts
```

Applications should write structured JSON with timestamp, severity, service, environment, version, trace or correlation ID, and meaningful event fields. Credentials, tokens, personal information, and other secrets must be redacted before ingestion — not caught afterward.

Azure-focused setups often use Azure Monitor Agent with Log Analytics. A portable, cloud-agnostic stack commonly uses Grafana Alloy as the collector, Loki for storage and querying, and Grafana for exploring the results and building dashboards.

## Loki Architecture

Loki is a log aggregation backend built around label-based streams. Instead of building a full-text index for every log line, it indexes only the stream labels and stores the actual log content as compressed chunks.

This can cut index overhead significantly, but performance and cost still come down to correct labels, sensible query scope, retention, and storage design.

```text
Container/file/journal logs
        ↓
Grafana Alloy
        ↓ pushes labeled streams
Loki :3100
        ↓ queried with LogQL
Grafana
```

Promtail shows up in older monitoring guides as the Loki log agent. It reached end of life in March 2026, so new deployments should use Grafana Alloy instead, and any remaining Promtail configurations should be migrated.

Good Loki labels are stable and few in number — things like `service`, `environment`, `namespace`, `pod`, and `container`. A request ID, user ID, or timestamp should stay a parsed log field, not a label.

## LogQL Examples

```logql
# Error text for one service
{service="orders-api", environment="prod"} |= "ERROR"

# Parse JSON and filter by a field
{namespace="orders-prod"} | json | level="error"

# Count matching error lines over five minutes
sum by (service) (
  count_over_time(
    {environment="prod"} |= "ERROR" [5m]
  )
)
```

In a containerized lab, configure the Grafana data source as `http://loki:3100`; port `9090` is normally Prometheus, not Loki.

## Operational Practices

- Define retention, archive, and deletion rules based on operational and compliance requirements.
- Restrict access by team and environment, encrypt data in transit and at rest, and audit sensitive searches.
- Control debug logging and multiline parsing. Monitor collector buffering, dropped entries, backpressure, and retry behavior.
- Keep Loki labels low-cardinality — avoid labels with many unique combinations of values — and avoid queries that scan unnecessarily broad time ranges.
- Separate tenant data when required, and monitor Loki/Alloy health independently of the applications they observe.
- Store dashboards and collector configuration in version control, and pin reviewed component versions.

## Handling a Log Volume Spike

When log volume suddenly increases: identify the service, version, and logger responsible. Protect storage and ingestion first. Reduce unsafe verbosity through a controlled, reviewed change. Preserve any audit evidence you're required to keep. Then verify collectors didn't drop data along the way. Don't respond by blindly deleting production logs.

## Incident Triage

During an incident, narrow the time range and service scope right away. Start from a metric alert or a trace exemplar, search for the shared trace ID, and compare the first failure against recent deployments and dependency events.
