# Grafana Monitoring Summary

Grafana queries **data sources** such as Prometheus, Azure Monitor, CloudWatch, Loki, Elasticsearch/OpenSearch and tracing systems. A dashboard should answer an operational question, not merely display available metrics.

**Dashboard flow:** configure a least-privilege data source and test it; create variables for environment, cluster and service; build panels for latency, traffic, errors, saturation and business outcomes; set units, legends and meaningful thresholds; link logs/traces/runbooks; annotate deployments; validate time range, refresh behavior and empty-data handling; then version dashboards as code where possible.

Use overview dashboards for user impact and drill-down dashboards for dependencies and resource evidence. Avoid expensive queries, misleading averages, uncontrolled template-variable cardinality and panels with no owner or decision. Protect Grafana with SSO/RBAC, TLS, restricted data-source credentials, backups and audited changes.

**Grafana Alerting** is useful for rules spanning supported data sources. Prometheus rules plus Alertmanager are often preferable for Prometheus-only alerts. Choose one source of truth for each alert and do not duplicate the same rule in both systems.
