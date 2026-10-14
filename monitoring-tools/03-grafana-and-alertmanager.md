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

<details><summary>Q7. [Basic] How do you add Prometheus as a data source in Grafana, and why might the test fail?</summary>

**Answer:**

1. **Connections → Data sources → Add data source → Prometheus.**
2. Set the URL: `http://localhost:9090` if both run directly on the same VM, `http://prometheus:9090` in Docker Compose, or the in-cluster service name in Kubernetes, for example `http://prometheus-server.monitoring.svc:9090`.
3. Click **Save & test**.

Common failures:

- `localhost` used inside a container: it points to the Grafana container itself, not Prometheus.
- Wrong port, such as using 9090 for Loki (Loki listens on 3100).
- Firewall or network policy blocking Grafana from reaching Prometheus.
- Prometheus behind a proxy that requires authentication not set in the data source.

In production, I provision data sources as code (YAML provisioning or Terraform) instead of clicking in the UI.

</details>

<details><summary>Q8. [Basic] How do you import a community dashboard, and what do you check afterwards?</summary>

**Answer:**

**Dashboards → New → Import**, enter the grafana.com ID (for example `1860` Node Exporter Full, or `19908` for cAdvisor), click **Load**, select the Prometheus data source and **Import**.

Afterwards I check:

- Panels show data: if not, the dashboard's variables or `job` labels do not match my scrape config.
- Queries use `rate()` correctly and units are right.
- The dashboard is not too heavy (dozens of panels over long time ranges slow down Prometheus).
- I save a cleaned-up copy in Git so it is versioned, instead of relying on the imported original.

</details>

<details><summary>Q9. [Intermediate] In Grafana alerting, what are alert rules, contact points and notification policies?</summary>

**Answer:**

| Part | What it does | Example |
| --- | --- | --- |
| Alert rule | Query plus condition, evaluation interval and pending period; adds labels and annotations | CPU above 90% for 5 minutes, `severity=critical` |
| Contact point | Where a notification is sent | Slack channel, Teams, email, PagerDuty, webhook |
| Notification policy | A routing tree that matches alert labels to contact points, with grouping, timing and muting | `severity=critical` → on-call PagerDuty; everything else → Slack |

Flow: the rule fires → labels are matched by the notification policy → the alert is grouped and sent to the contact point. Silences and mute timings suppress notifications during maintenance.

Grafana can also use an external **Alertmanager** as a data source, so alerts from Prometheus and Grafana can be viewed and silenced in one place.

</details>

<details><summary>Q10. [Intermediate] How would you integrate Prometheus with Grafana for application monitoring? <em>(asked in interview round)</em></summary>

**Answer:**

Prometheus collects and stores metrics by scraping HTTP endpoints. Grafana does not collect metrics itself; it queries Prometheus as a data source and visualizes the results in dashboards and alerts.

**Flow:**

```text
Application (/metrics endpoint)   node-exporter / kube-state-metrics
        \                                   /
         \  scrape every 15-30s            /
          v                               v
                 Prometheus (TSDB)
                  |            |
     PromQL query |            | alert rules
                  v            v
               Grafana     Alertmanager --> Slack / email / PagerDuty
```

**Steps:**

**Step 1: Expose metrics from the application**

Use a Prometheus client library (Java Micrometer, Python `prometheus_client`, Go `client_golang`) so the app exposes `/metrics` with request count, latency histogram and error count.

**Step 2: Install Prometheus and Grafana**

On Kubernetes the usual way is the `kube-prometheus-stack` Helm chart, which installs Prometheus Operator, Prometheus, Alertmanager, Grafana, node-exporter and kube-state-metrics.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

**Step 3: Tell Prometheus to scrape the application**

With the operator, create a `ServiceMonitor` that selects the application Service.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: orders-api
  namespace: monitoring
  labels:
    release: monitoring          # must match the Prometheus serviceMonitorSelector
spec:
  namespaceSelector:
    matchNames: ["orders"]
  selector:
    matchLabels:
      app: orders-api
  endpoints:
    - port: http-metrics         # named port on the Service
      path: /metrics
      interval: 30s
```

Without the operator, add a job to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: orders-api
    metrics_path: /metrics
    static_configs:
      - targets: ["orders-api.internal:8080"]
```

Confirm the target is `UP` in the Prometheus UI under Status, Targets.

**Step 4: Add Prometheus as a Grafana data source**

The Helm chart does this automatically. Otherwise, provision it as code:

```yaml
# /etc/grafana/provisioning/datasources/prometheus.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-server.monitoring.svc:9090
    isDefault: true
```

**Step 5: Build dashboards with PromQL**

Use the RED method (rate, errors, duration) for services:

```text
Request rate : sum(rate(http_server_requests_seconds_count{app="orders-api"}[5m]))
Error rate % : 100 * sum(rate(http_server_requests_seconds_count{app="orders-api",status=~"5.."}[5m]))
               / sum(rate(http_server_requests_seconds_count{app="orders-api"}[5m]))
p95 latency  : histogram_quantile(0.95, sum by (le) (rate(http_server_requests_seconds_bucket{app="orders-api"}[5m])))
```

Store dashboards as JSON in Git and load them through provisioning or a ConfigMap with the Grafana sidecar label, so they are versioned.

**Step 6: Add alerting**

Define alert rules in Prometheus (`PrometheusRule`) and route them through Alertmanager, or use Grafana alerting. Alert on symptoms such as error rate and latency, not on every metric.

**Important points:**

- Grafana is only the visualization and alerting layer; if a panel is empty, check the Prometheus target and the PromQL query first.
- Watch label cardinality: user IDs or request IDs as labels can overload Prometheus.
- Secure Grafana with SSO and role-based access, and do not expose Prometheus publicly.
- For long retention or multiple clusters, use remote write to Thanos, Mimir or a managed Prometheus service.

See also: [monitoring-tools/11](../monitoring-tools/11-prometheus-grafana-hands-on-setup.md) and [monitoring-tools/03](../monitoring-tools/03-grafana-and-alertmanager.md).

**Interview-ready answer:**

> "I first make sure the application exposes a `/metrics` endpoint using a Prometheus client library. On Kubernetes I install the `kube-prometheus-stack` Helm chart and create a `ServiceMonitor` so Prometheus scrapes the application Service, then I confirm the target is up. In Grafana I add Prometheus as a data source, ideally through provisioning so it is in code. I build dashboards around request rate, error rate and p95 latency using PromQL, and keep the dashboard JSON in Git. Finally I add alert rules for error rate and latency and route them through Alertmanager to Slack or email."

</details>

<details><summary>Q11. [Advanced] Thousands of alerts fire at once. How do you find the real problem? <em>(asked in interview round)</em></summary>

**Answer:**

A flood of alerts is usually one root cause with many symptoms. I stop reading alerts one by one, look for the **earliest** and **lowest-layer** failure, and fix the alerting so the next incident produces a handful of meaningful pages.

**Steps:**

1. **Declare an incident** and assign roles (incident commander, communications) so people do not work in parallel on symptoms.
2. **Check user impact** first: SLO dashboards, synthetic checks, error rate at the edge.
3. **Group alerts** by time, cluster, zone, service and dependency. Look at what fired **first**.
4. **Look for the common dependency**: network, DNS, a database, an identity provider, a certificate, a cloud provider incident, a configuration change.
5. **Check change logs**: deployments, infrastructure changes, certificate expiry, feature flags.
6. **Mitigate** the shared cause; most alerts should resolve on their own.
7. **Afterwards**: add inhibition rules, grouping, dependency-aware alerting, and move cause-based alerts from pages to tickets.

**Decision flow:**

```text
Alert storm
      |
      v
Is the user-facing SLO affected? --> sets severity and urgency
      |
      v
Sort by first-fired time + group by zone/cluster/service
      |
      v
Common layer? network / DNS / DB / auth / cloud region / cert --> fix that first
      |
      v
Recent change in that layer? --> roll back
```

**Alertmanager grouping and inhibition:**

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
inhibit_rules:
  - source_matchers: [ 'alertname = ClusterUnreachable' ]
    target_matchers: [ 'severity =~ "warning|critical"' ]
    equal: ['cluster']
  - source_matchers: [ 'alertname = DatabaseDown' ]
    target_matchers: [ 'alertname = HighErrorRate' ]
    equal: ['environment']
```

**Important points:**

- Page on symptoms (SLO burn, user-facing errors); send cause-level alerts (CPU, disk, single Pod restarts) to tickets or dashboards.
- Every page must be actionable and have a runbook link.
- Track alert volume and pages per on-call shift as a reliability metric.

See also: [Observability and APM](../monitoring-tools/01-observability-and-apm.md), [Grafana and Alertmanager](../monitoring-tools/03-grafana-and-alertmanager.md), [SRE](../ops/03-sre.md)

**Interview-ready answer:**

> "When thousands of alerts fire, it is almost always one cause with many symptoms, so I do not try to read them individually. I declare an incident, check user impact on the SLO dashboards, and then group alerts by time, cluster, zone and service to find which fired first and which layer they share. That usually points to something common such as DNS, the network, a database, an identity provider or a certificate, and I check whether anything changed there. Fixing that one component normally clears most of the alerts. Afterwards I improve the alerting: grouping and inhibition rules in Alertmanager, paging only on symptom-based SLO alerts, and sending cause-level alerts to tickets."

</details>
