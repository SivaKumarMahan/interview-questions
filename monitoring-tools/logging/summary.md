# Logging Summary

Centralized logging flow is application `stdout`/`stderr` or managed-service logs `-> collector/agent -> durable searchable backend -> dashboards/alerts`. Common stacks are Fluent Bit/Fluentd or Logstash to Elasticsearch/OpenSearch and Kibana, or Fluent Bit/Promtail to Loki and Grafana. CloudWatch Logs, Azure Log Analytics, Splunk and Loggly are managed/SaaS alternatives.

Use **structured JSON** with timestamp, severity, service, environment, version, trace/correlation ID and meaningful event fields. Redact credentials, tokens and personal data before ingestion. Control debug logging, multiline parsing, collector buffers/backpressure, index/label cardinality, hot/warm/cold retention, archive, access and deletion policy.

When **volume explodes**, identify which service/version/logger changed, stabilize storage and ingestion, reduce unsafe verbosity through a controlled change, preserve required security/audit evidence and verify no collector loss. Do not simply delete production logs. During an incident, narrow the time and service scope, start from a metric or trace exemplar, query the shared trace ID and correlate the first failure with deployments and dependency events.
