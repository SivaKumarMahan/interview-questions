# Grafana Monitoring Summary

## Purpose and Architecture

Grafana is a visualization, exploration, and alerting platform. It normally doesn't store your raw metrics, logs, or traces itself — it queries them from wherever they already live.

What Grafana does store is its own metadata: users, organizations, data-source configuration, dashboards, and alert configuration.

Common data sources include:

- Prometheus for metrics
- Loki for logs
- Tempo for traces
- Azure Monitor and Log Analytics for Azure platform monitoring data
- Elasticsearch/OpenSearch and supported SQL databases

Plugins can add new data sources, panels, and applications. Treat them like any other software dependency: install only approved plugins and keep them updated.

When Grafana and the backend run in different containers, `localhost` points to the Grafana container. Use the internal service address instead:

```text
Prometheus: http://prometheus:9090
Loki:       http://loki:3100
```

After adding a data source, test the connection and use **Explore** to validate a simple query before building a dashboard.

## Building an Effective Dashboard

1. Define the operational question and the audience first.
2. Add variables for environment, cluster, namespace, or service. Keep the number of unique values a variable can produce (cardinality) under control, or queries will blow up.
3. Start with what affects users: latency, traffic, errors, and saturation — how close a resource is to its limit.
4. Add dependency, infrastructure, and business panels only when they support a decision.
5. Set the correct units, legends, thresholds, minimum/maximum values, and no-data behavior.
6. Add deployment annotations and link to logs, traces, and runbooks.
7. Test multiple time ranges, refresh intervals, empty data, partial failures, and a real incident period.
8. Provision or export dashboards to version control and review changes like code.

Use one overview dashboard for overall service health, and separate drill-down dashboards for detailed evidence. Avoid showing every available metric, using misleading averages, running expensive queries, or adding panels nobody owns or acts on.

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

Community dashboards can save setup time, but always review an imported dashboard before trusting it. Check its metric names, job labels, variables, and queries against your own environment — don't assume a dashboard is production-ready just because it's popular.

## Grafana Alerting

Grafana Alerting evaluates rules, groups the resulting alert instances, and sends notifications through contact points chosen by notification policies. Labels decide ownership and routing. Annotations carry the human-readable summary, description, and runbook link.

For rules that only need Prometheus metrics, Prometheus rules plus Alertmanager are often the simplest source of truth. Grafana-managed alerting is useful when a rule needs to query another data source, or combine expressions across sources.

Don't maintain the same rule independently in both systems — pick one as the source of truth.

A host CPU alert must calculate a rate from the CPU counter before applying a threshold:

```promql
100 * (
  1 - avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  )
) > 90
```

Set a sensible pending duration and test both the firing and resolved behavior. Make sure a no-data or data-source error can't silently hide a real outage.

## Security and Operations

- Replace bootstrap credentials immediately; never leave the default administrator password in place.
- Use SSO, least-privilege roles (grant only the access someone actually needs), team and folder permissions, and separate service accounts.
- Keep Grafana behind private access or a secured ingress with TLS. Don't expose port `3000` directly to the internet.
- Store data-source and notification credentials in a secret manager such as Azure Key Vault, not in dashboard JSON or source control.
- Restrict anonymous access, audit administrative changes, patch Grafana and any approved plugins, and guard against unsafe dashboard snapshots.
- Back up the Grafana database and provisioned resources, and test that the restore actually works.
- Monitor Grafana's own availability, query errors, alert evaluation, notification failures, and resource usage.

Azure Managed Grafana is worth considering in Azure-heavy environments. It integrates with Azure identity and Azure Monitor data sources, and it takes platform maintenance off your plate.
