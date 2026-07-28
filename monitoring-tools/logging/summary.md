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

Applications should write structured JSON containing timestamp, severity, service, environment, version, trace/correlation ID and meaningful event fields. Credentials, tokens, personal information and other secrets must be redacted before ingestion.

Azure-focused options include Azure Monitor Agent with Log Analytics. A portable Grafana stack commonly uses Grafana Alloy as the collector, Loki for storage/querying and Grafana for exploration and dashboards.

## Loki Architecture

Loki is a log aggregation backend designed around label-based streams. It indexes stream labels rather than building a full-text index for every log line, then stores compressed log chunks.

This can reduce index overhead, but performance and cost still depend on correct labels, query scope, retention and storage design.

```text
Container/file/journal logs
        ↓
Grafana Alloy
        ↓ pushes labeled streams
Loki :3100
        ↓ queried with LogQL
Grafana
```

Promtail appears in older monitoring guides as the Loki log agent. Promtail reached end of life in March 2026, so use Grafana Alloy for new deployments and plan migration for remaining Promtail configurations.

Good Loki labels are stable and limited, such as `service`, `environment`, `namespace`, `pod` and `container`. A request ID, user ID or timestamp should remain a parsed log field rather than a label.

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

- Define retention, archive and deletion rules based on operational and compliance requirements.
- Restrict access by team and environment, encrypt data in transit and at rest, and audit sensitive searches.
- Control debug logging and multiline parsing; monitor collector buffering, dropped entries, backpressure and retry behavior.
- Avoid high-cardinality (number of unique label combinations) Loki labels and queries that scan unnecessarily broad time ranges.
- Separate tenant data when required and monitor Loki/Alloy health independently of the applications they observe.
- Store dashboards and collector configuration in version control and pin reviewed component versions.

When log volume suddenly increases, identify the service, version and logger responsible; protect storage and ingestion; reduce unsafe verbosity through a controlled change; preserve required audit evidence; and verify that collectors did not drop data. Do not respond by blindly deleting production logs.
During an incident, narrow the time and service scope, start from a metric alert or trace exemplar, search the shared trace ID and compare the first failure with deployments and dependency events.
