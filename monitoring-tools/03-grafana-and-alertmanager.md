# Monitoring Tools: Grafana Dashboards and Alertmanager

> Grafana dashboards, visualizations and alerting, and how Alertmanager routes, groups and delivers Prometheus alerts.

## Key Concepts

### Grafana Purpose and Architecture

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

### Building an Effective Grafana Dashboard

1. Define the operational question and the audience first.
2. Add variables for environment, cluster, namespace, or service. Keep the number of unique values a variable can produce (cardinality) under control, or queries will blow up.
3. Start with what affects users: latency, traffic, errors, and saturation — how close a resource is to its limit.
4. Add dependency, infrastructure, and business panels only when they support a decision.
5. Set the correct units, legends, thresholds, minimum/maximum values, and no-data behavior.
6. Add deployment annotations and link to logs, traces, and runbooks.
7. Test multiple time ranges, refresh intervals, empty data, partial failures, and a real incident period.
8. Provision or export dashboards to version control and review changes like code.

Use one overview dashboard for overall service health, and separate drill-down dashboards for detailed evidence. Avoid showing every available metric, using misleading averages, running expensive queries, or adding panels nobody owns or acts on.

### Common Grafana Visualizations

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

### Grafana Alerting

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

### Grafana Security and Operations

- Replace bootstrap credentials immediately; never leave the default administrator password in place.
- Use SSO, least-privilege roles (grant only the access someone actually needs), team and folder permissions, and separate service accounts.
- Keep Grafana behind private access or a secured ingress with TLS. Don't expose port `3000` directly to the internet.
- Store data-source and notification credentials in a secret manager such as Azure Key Vault, not in dashboard JSON or source control.
- Restrict anonymous access, audit administrative changes, patch Grafana and any approved plugins, and guard against unsafe dashboard snapshots.
- Back up the Grafana database and provisioned resources, and test that the restore actually works.
- Monitor Grafana's own availability, query errors, alert evaluation, notification failures, and resource usage.

Azure Managed Grafana is worth considering in Azure-heavy environments. It integrates with Azure identity and Azure Monitor data sources, and it takes platform maintenance off your plate.

### Alertmanager's Role in the Alerting Flow

Prometheus evaluates PromQL alert rules. When a rule fires, Prometheus sends the alert to Alertmanager. Alertmanager doesn't evaluate PromQL itself — its job is managing how those alerts get delivered.

```text
Prometheus rule evaluation
        ↓
Alertmanager
        ├── groups related alerts
        ├── deduplicates repeats
        ├── applies inhibition and silences
        └── routes by labels to receivers
```

| Feature | What it does |
| --- | --- |
| Grouping | Combines related alerts into one manageable notification |
| Deduplication | Stops repeated copies of the same alert going out |
| Routing | Picks a receiver based on labels like team, service, environment, and severity |
| Inhibition | Suppresses symptom alerts when a known parent alert is already firing |
| Silence | Temporarily suppresses matching alerts, usually during planned maintenance |

Alertmanager can deliver to email, webhooks, incident-management platforms, and controlled chat integrations. For critical alerts, use an on-call system with acknowledgement and escalation — don't rely on chat alone, since messages can be missed.

### Connecting Alertmanager to Prometheus

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

The Prometheus rule should include enough context for routing and response:

```yaml
groups:
  - name: application-health
    rules:
      - alert: ApplicationHighErrorRate
        expr: |
          sum by (service) (
            rate(http_requests_total{status=~"5.."}[5m])
          )
          /
          sum by (service) (
            rate(http_requests_total[5m])
          ) > 0.05
        for: 10m
        labels:
          severity: critical
          team: application
        annotations:
          summary: "High error rate for {{ $labels.service }}"
          description: "More than 5% of requests have failed for 10 minutes."
          runbook_url: "https://runbooks.example/application-high-error-rate"
```

### Alertmanager Routing Example

```yaml
route:
  receiver: default-notifications
  group_by: ["alertname", "service", "environment"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers:
        - severity="critical"
      receiver: critical-on-call

receivers:
  - name: default-notifications
    webhook_configs:
      - url_file: /run/secrets/default_webhook_url

  - name: critical-on-call
    webhook_configs:
      - url_file: /run/secrets/on_call_webhook_url
```

Keep receiver credentials in Kubernetes Secrets or an external secret manager such as Azure Key Vault. Never commit webhook URLs, API tokens, or SMTP passwords to the repo.

### Alertmanager Testing and Best Practices

- Alert on sustained, actionable problems or SLO burn — not on every brief threshold breach.
- Use stable ownership labels and consistent severity levels across the board.
- Include the observed impact, current value, start time, a dashboard link, and a runbook link in every notification.
- Test a safe firing condition end to end: the right route, grouping, template rendering, acknowledgement, escalation, and the resolved notification.
- Test silences and maintenance windows, and don't leave broad or permanent suppressions sitting in place afterward.
- Monitor Alertmanager itself: its health, notification failures, queue behavior, and config reloads.
- For high availability, run Alertmanager as a supported cluster, and actually test what happens when one instance or one receiver fails.

### Alertmanager and Grafana Integration

Grafana can add Prometheus Alertmanager as a data source to inspect alerts and manage silences from its UI. With that setup, the contact points, policies, and templates stay managed inside Alertmanager itself — they aren't edited as Grafana's own alerting configuration.

## Interview Questions

<details><summary>Q1. [Basic] What is Grafana's role compared with Prometheus or CloudWatch?</summary>

**Answer:**

Prometheus and CloudWatch each collect, store, and query monitoring data in their own way. Grafana sits on top as the visualization and exploration layer. It can query both of them, plus Loki, Elasticsearch, Azure Monitor, and tracing systems, all from one place.

Grafana doesn't create good observability by itself. You still need correct instrumentation, real SLOs, clear ownership, sensible retention, and runbooks. Grafana just makes all of that easier to see and act on.

</details>

<details><summary>Q2. [Intermediate] How do you configure a useful Grafana dashboard?</summary>

**Answer:**

I start with a data source that has least privilege — just enough access to query, nothing more — and I test the connection. I add variables for things like environment, cluster, or service so people can filter without editing the dashboard.

The main overview is built around the signals that matter most: latency, traffic, errors, saturation (how close a resource is to its limit), and business outcomes.

Each panel needs the right units, useful percentiles, clear legends, and thresholds. I add deployment annotations and link out to logs, traces, and runbooks so someone investigating an issue doesn't have to leave the dashboard to find context.

Drill-down dashboards hold the detailed evidence for each component.

Before calling it done, I test multiple time ranges, empty data, refresh load, and permissions. I compare what the panel shows against the raw source data, and I version the dashboard as code where I can.

I avoid misleading averages, cramming in too many panels, and variables with too many possible values (high cardinality).

SSO, role-based access, credential isolation, and backups are part of the setup, not an afterthought.

</details>

<details><summary>Q3. [Intermediate] Should an alert be defined in Prometheus or Grafana?</summary>

**Answer:**

If the alert only needs Prometheus metrics, I use Prometheus rules with Alertmanager. That keeps evaluation close to the data, and Alertmanager's routing is mature.

Grafana Alerting makes more sense when a rule needs to combine data from multiple sources, or when Grafana is the team's official alerting platform.

The choice comes down to high availability, who owns the rule, and how the data source is run day to day. Whichever I pick, I treat it as the one source of truth, version it, and test that notifications actually deliver. I never define the same alert in both places — that just creates confusion about which one is authoritative.

</details>

<details><summary>Q4. [Intermediate] How do you configure alerts in Prometheus and Grafana, and which one should you use?</summary>

You can configure alerts in both Prometheus and Grafana, but they serve slightly different purposes.

#### 7.1 Prometheus alerting (recommended)

Prometheus uses Alertmanager for alerting.

Flow:

```
Prometheus -> Alert Rules -> Alertmanager -> Email/Slack/Teams/PagerDuty
```

Example alerts:

- CPU > 80% for 5 minutes
- Memory > 80%
- Pod in CrashLoopBackOff
- Node NotReady
- Disk usage > 90%
- Deployment replicas unavailable

Prometheus continuously evaluates alert rules written in PromQL. When a condition is met, it sends the alert to Alertmanager, which handles routing, grouping, silencing, and notifications.

#### 7.2 Grafana alerting

Grafana can also create alerts based on data from Prometheus (or other data sources).

Example:

- High application response time
- HTTP 5xx error rate
- Dashboard panel threshold exceeded

Grafana sends notifications directly to Email, Microsoft Teams, Slack, PagerDuty or Webhooks.

#### 7.3 Which one should you use?

- **Prometheus + Alertmanager:** best for infrastructure and Kubernetes alerts. It is the standard choice in production.
- **Grafana:** best for dashboard-based alerts and when you have multiple data sources besides Prometheus.

#### 7.4 Interview answer

> "Alerts can be configured in both Prometheus and Grafana. In production, I typically use Prometheus Alertmanager for Kubernetes and infrastructure alerts because it evaluates PromQL rules and provides features like grouping, routing, and silencing before sending notifications to Teams, Slack, or email. Grafana also supports alerting, and I mainly use it for dashboard-based or application-level alerts. Both integrate well with Prometheus, but Alertmanager is generally the preferred solution for Kubernetes monitoring."

</details>

<details><summary>Q5. [Intermediate] How does Alertmanager reduce alert noise?</summary>

**Answer:**

Alertmanager cuts noise in a few ways. It groups alerts from the same incident together, deduplicates repeated notifications, routes alerts by their labels, inhibits lower-priority alerts when a parent failure is already firing, and lets you silence alerts during planned maintenance.

I use stable labels for team, service, environment, and severity, and I design the routing tree around who actually owns each alert.

I also regularly review alerts that never lead to any action. If an alert doesn't drive a response, I remove it or demote it, rather than just spacing out how often it repeats.

</details>

<details><summary>Q6. [Intermediate] How do you integrate Alertmanager with Slack, Teams or PagerDuty securely?</summary>

**Answer:**

I set up the receiver and route in Alertmanager, but I never put webhook or API credentials directly in the config file. Those go into Kubernetes Secrets or an external secret manager instead.

Each notification includes the service name, the impact, how long it's been happening, the current value, a link to the dashboard, a link to the runbook, and a link to acknowledge or silence the alert.

Grouping and inhibition stop this from turning into a flood of messages during a big incident.

To test it, I fire a non-production test alert and check that it reaches the right receiver, that the firing and resolved messages both look correct, and that escalation works as expected. Slack and Teams are good for collaboration, but critical pages also go through PagerDuty or a similar tool, because a chat message can easily be missed.

Credentials get rotated on a regular schedule, and any change to the routing configuration goes through review.

</details>
