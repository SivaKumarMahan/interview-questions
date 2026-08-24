## 1. How do you configure a useful Grafana dashboard?

**Answer:**

I start with a data source that has least privilege — just enough access to query, nothing more — and I test the connection. I add variables for things like environment, cluster, or service so people can filter without editing the dashboard.

The main overview is built around the signals that matter most: latency, traffic, errors, saturation (how close a resource is to its limit), and business outcomes.

Each panel needs the right units, useful percentiles, clear legends, and thresholds. I add deployment annotations and link out to logs, traces, and runbooks so someone investigating an issue doesn't have to leave the dashboard to find context.

Drill-down dashboards hold the detailed evidence for each component.

Before calling it done, I test multiple time ranges, empty data, refresh load, and permissions. I compare what the panel shows against the raw source data, and I version the dashboard as code where I can.

I avoid misleading averages, cramming in too many panels, and variables with too many possible values (high cardinality).

SSO, role-based access, credential isolation, and backups are part of the setup, not an afterthought.

## 2. Should an alert be defined in Prometheus or Grafana?

**Answer:**

If the alert only needs Prometheus metrics, I use Prometheus rules with Alertmanager. That keeps evaluation close to the data, and Alertmanager's routing is mature.

Grafana Alerting makes more sense when a rule needs to combine data from multiple sources, or when Grafana is the team's official alerting platform.

The choice comes down to high availability, who owns the rule, and how the data source is run day to day. Whichever I pick, I treat it as the one source of truth, version it, and test that notifications actually deliver. I never define the same alert in both places — that just creates confusion about which one is authoritative.

## 3. What is Grafana's role compared with Prometheus or CloudWatch?

**Answer:**

Prometheus and CloudWatch each collect, store, and query monitoring data in their own way. Grafana sits on top as the visualization and exploration layer. It can query both of them, plus Loki, Elasticsearch, Azure Monitor, and tracing systems, all from one place.

Grafana doesn't create good observability by itself. You still need correct instrumentation, real SLOs, clear ownership, sensible retention, and runbooks. Grafana just makes all of that easier to see and act on.
