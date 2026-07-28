# Grafana Monitoring Summary

## Purpose and Architecture

Grafana is a visualization, exploration and alerting platform. It normally queries monitoring data where it is stored rather than storing the raw metrics, logs or traces itself.

Grafana does store its own users, organizations, data-source configuration, dashboards, alert configuration and other metadata.

Common data sources include:

- Prometheus for metrics
- Loki for logs
- Tempo for traces
- Azure Monitor and Log Analytics for Azure platform monitoring data
- Elasticsearch/OpenSearch and supported SQL databases

Plugins can add data sources, panels and applications. Install only approved plugins and manage them like any other software dependency.

When Grafana and the backend run in different containers, `localhost` points to the Grafana container. Use the internal service address instead:

```text
Prometheus: http://prometheus:9090
Loki:       http://loki:3100
```

After adding a data source, test the connection and use **Explore** to validate a simple query before building a dashboard.

## Building an Effective Dashboard

1. Define the operational question and audience.
2. Add variables for environment, cluster, namespace or service without creating uncontrolled query cardinality (number of unique label combinations).
3. Start with user impact: latency, traffic, errors and saturation (how close a resource is to its limit).
4. Add dependency, infrastructure and business panels only when they support a decision.
5. Set the correct units, legends, thresholds, minimum/maximum values and no-data behavior.
6. Add deployment annotations and links to logs, traces and runbooks.
7. Test multiple time ranges, refresh intervals, empty data, partial failure and a real incident period.
8. Provision or export dashboards to version control and review changes.

Use an overview dashboard for service health and drill-down dashboards for detailed evidence. Avoid displaying every available metric, misleading averages, expensive queries and panels without a clear owner or response.

## Common Visualizations

| Visualization | Suitable use |
|---|---|
| Time series | Trends such as request rate, latency, CPU or memory |
| Stat | A single important value such as availability or current error rate |
| Gauge/Bar gauge | A value with meaningful limits, such as capacity utilization |
| Table | Detailed status, labels, instances or ranked results |
| Bar chart | Comparison across services, versions or categories |
| Pie chart | A small number of meaningful proportions; avoid many slices |
| State timeline/Status history | Discrete states such as up/down, health or deployment state |
| Logs | Log lines and parsed fields from a logging data source |
| Text | Instructions, ownership, runbook links or dashboard context |

Community dashboards can accelerate setup, but imported dashboards must be reviewed. Validate their metric names, jobs, labels, variables, queries and panel assumptions instead of treating the dashboard ID as production-ready.

## Grafana Alerting

Grafana Alerting evaluates rules, groups rule instances, and sends notifications through contact points selected by notification policies. Labels determine ownership and routing; annotations provide the human-readable summary, description and runbook.

For Prometheus-only rules, Prometheus rules plus Alertmanager are often the simplest source of truth. Grafana-managed alerting is useful when a rule must query another supported data source or combine expressions.

Do not maintain the same rule independently in both systems.

A host CPU alert must calculate a rate from the CPU counter before applying a threshold:

```promql
100 * (
  1 - avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  )
) > 90
```

Configure a suitable pending duration, test firing and resolved behavior, and ensure a no-data or data-source error cannot silently hide an outage.

## Security and Operations

- Replace bootstrap credentials immediately; never leave the default administrator password in place.
- Use SSO, least-privilege (minimum required access) roles, team/folder permissions and separate service accounts.
- Keep Grafana behind private access or a secured ingress with TLS; do not expose port `3000` directly to the internet.
- Store data-source and notification credentials in a secret manager such as Azure Key Vault, not dashboard JSON or source control.
- Restrict anonymous access, audit administrative changes, patch Grafana and approved plugins, and protect against unsafe dashboard snapshots.
- Back up the Grafana database and provisioned resources, then test restoration.
- Monitor Grafana availability, query errors, alert evaluation, notification failures and resource usage.

Azure Managed Grafana is an option for Azure-focused environments and integrates with Azure identity and Azure Monitor data sources while reducing platform maintenance.
