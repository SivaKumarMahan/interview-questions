## 1. How do you configure a useful Grafana dashboard?

**Answer:**

I add a least-privilege data source and test it, create controlled variables such as environment/cluster/service, and build an overview around latency, traffic, errors, saturation and business outcomes. Panels have correct units, useful percentiles, legends and thresholds; deployment annotations and links connect to logs, traces and runbooks. Drill-down dashboards contain component evidence.

I test multiple time ranges, empty data, refresh load and permissions, compare the panel query with the source, and version the dashboard as code where possible. I avoid misleading averages, too many panels and high-cardinality variables. SSO/RBAC, credential isolation and backup are part of the setup.

## 2. Should an alert be defined in Prometheus or Grafana?

**Answer:**

For Prometheus-only metrics, Prometheus rules and Alertmanager keep evaluation close to the data and provide mature routing. Grafana Alerting is useful when a rule spans supported data sources or Grafana is the governed alerting platform. I choose based on HA, ownership, data-source availability and operations, define one source of truth, version it and test delivery. I never create the same alert independently in both.

## 3. What is Grafana's role compared with Prometheus or CloudWatch?

**Answer:**

Prometheus and CloudWatch collect/store/query telemetry in their respective models. Grafana is primarily the visualization, exploration and alert-presentation layer that can query both plus Loki, Elasticsearch, Azure Monitor and tracing systems. Grafana does not automatically create good observability; teams still need correct instrumentation, SLOs, ownership, retention and runbooks.
