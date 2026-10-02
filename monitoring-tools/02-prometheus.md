# Monitoring Tools: Prometheus

> How Prometheus scrapes and stores metrics, metric types, exporters, configuration, PromQL, recording and alerting rules, and production practices.

## Key Concepts

### What Prometheus Does

Prometheus is a pull-based monitoring system. It's also a time-series database, a PromQL query engine, and a rule evaluator all in one. It periodically scrapes HTTP metric endpoints, stores each sample with a timestamp and labels, evaluates recording and alerting rules, and exposes the data to tools like Grafana.

The usual flow looks like this:

```text
Application / host / Kubernetes
        ↓ exposes /metrics
Exporter or instrumented application
        ↓ scraped by Prometheus
Prometheus TSDB + PromQL + rules
        ├── Grafana dashboards
        └── Alertmanager notifications
```

A time series is a metric name plus a unique set of labels. For example, `http_requests_total{service="orders",status="200"}` is a different time series from the same metric with `status="500"`.

Keep labels limited and operationally useful. Never use request IDs, user IDs, timestamps or unbounded URL values as labels — each unique combination of label values creates a new time series, and too many of those (high cardinality) can overwhelm Prometheus.

### Metric Types

- **Counter:** a value that normally only goes up, such as total requests or errors. Query it with `rate()` or `increase()`, never a raw average.
- **Gauge:** a value that can go up or down, such as memory usage, queue depth or active sessions.
- **Histogram:** observations sorted into buckets, such as request duration. Prometheus can aggregate these server-side and estimate percentiles with `histogram_quantile()`.
- **Summary:** observations with quantiles calculated on the client side. These quantiles generally can't be combined reliably across instances.

### Exporters and Kubernetes Resources

Common metric sources include:

| Source | Purpose |
|---|---|
| Node Exporter | Linux CPU, memory, load, filesystem and network metrics |
| Kubelet/cAdvisor | Pod and container CPU, memory, filesystem and network usage |
| kube-state-metrics | Kubernetes object state such as desired/available replicas and pod phase |
| Blackbox Exporter | HTTP, TCP, DNS and ICMP synthetic probes |
| Application client library | Business and application metrics exposed at `/metrics` |

With Prometheus Operator, `ServiceMonitor`, `PodMonitor`, `Probe` and `PrometheusRule` resources provide Kubernetes-native target and rule configuration.

### Basic Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]

  - job_name: cadvisor
    static_configs:
      - targets: ["cadvisor:8080"]

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

In Kubernetes, prefer service discovery and `ServiceMonitor`/`PodMonitor` resources over hardcoding static pod IPs. Before reloading configuration, run:

```bash
promtool check config /etc/prometheus/prometheus.yml
promtool check rules /etc/prometheus/rules/*.yml
```

On the Prometheus **Targets** page, confirm the target is discovered, its state is `UP`, the labels are correct, and the last scrape didn't error. The `up` metric only tells you the scrape succeeded — it doesn't prove the application itself is healthy.

### Useful PromQL

```promql
# Unreachable scrape targets
up == 0

# CPU usage percentage by host
100 * (
  1 - avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  )
)

# Memory usage percentage by host
100 * (
  1 -
  node_memory_MemAvailable_bytes
  /
  node_memory_MemTotal_bytes
)

# Filesystem usage percentage
100 * (
  1 -
  node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
  /
  node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}
)

# Request rate by service and status
sum by (service, status) (
  rate(http_requests_total[5m])
)

# 5xx error ratio
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))

# 95th-percentile request duration
histogram_quantile(
  0.95,
  sum by (le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

Use a range long enough to cover several scrapes. Only aggregate away instance-level labels when that actually matches the question you're asking.

### Recording and Alerting Rules

Recording rules precompute expressions that are expensive or used often. Alerting rules should describe a sustained, actionable symptom, and include ownership and troubleshooting context.

```yaml
groups:
  - name: host-health
    rules:
      - alert: HostHighCPU
        expr: |
          100 * (
            1 - avg by (instance) (
              rate(node_cpu_seconds_total{mode="idle"}[5m])
            )
          ) > 90
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High CPU on {{ $labels.instance }}"
          description: "CPU usage has exceeded 90% for 5 minutes."
          runbook_url: "https://runbooks.example/host-high-cpu"
```

The `for` duration stops a short spike from firing immediately. Test the whole path: rule expression, pending state, firing state, Alertmanager route, notification, and the resolved notification too.

### Production Practices

| Practice | Why it matters |
|---|---|
| Persist the TSDB and size retention | Match it to ingestion rate, disk capacity and compliance needs |
| Monitor Prometheus itself | Watch failed scrapes, rule evaluation failures, storage growth, compaction and cardinality |
| Use recording rules | Precompute repeated expensive queries; keep dashboard query ranges reasonable |
| Run HA replicas when required | For long retention or global queries, pair with a managed service, Thanos, or Mimir |
| Keep endpoints private | Prometheus, exporters and service-discovery endpoints stay off the public network |
| Secure access | TLS and authentication at the ingress or reverse proxy, and discovery credentials scoped to only what they need |
| Pin and back up | Pin reviewed container versions, back up config/rules, and manage both through version control |

For an Azure-based environment, Azure Monitor's managed service for Prometheus plus Azure Managed Grafana can cut down the operational work for AKS monitoring. Self-managed Prometheus is still worth it where you need full configuration control or portability.

### Local Prometheus Learning Stack

A Docker Compose lab typically runs Prometheus (`9090`), Grafana (`3000`), Node Exporter (`9100`), cAdvisor (`8080`), Loki (`3100`) and Alertmanager (`9093`) together. Use service names for container-to-container URLs, like `http://prometheus:9090`, and bind web ports to `127.0.0.1` for local practice.

Publicly exposing monitoring ports or using unpinned `latest` images is not a production design.

## Interview Questions

<details><summary>Q1. [Intermediate] What is in <code>prometheus.yml</code> and how do you validate it?</summary>

**Answer:**

It usually defines the global scrape and evaluation intervals, scrape jobs and service discovery, relabeling rules, rule files, remote write, and Alertmanager targets. In Kubernetes, Operator resources like `ServiceMonitor` and `PodMonitor` often generate this scrape configuration for you.

To validate it, I run `promtool check config`, check the Targets page for discovery, TLS or auth errors, confirm the expected labels with a sample query, and reload it through the supported method. Credentials go through secret files or the platform's secret integration, not plain text in the config.

I also watch scrape duration and failures, and keep an eye on label cardinality — the number of unique label combinations a metric produces — so a single bad target can't destabilize the whole Prometheus instance.

</details>

<details><summary>Q2. [Intermediate] How do you alert when disk use exceeds 80%?</summary>

**Answer:**

```yaml
- alert: FilesystemSpaceLow
  expr: |
    100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
      / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}) > 80
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Filesystem usage above 80% on {{ $labels.instance }}"
```

I exclude filesystems that don't matter, like read-only ones, include the mount point and a runbook link in the annotations, and use a `for` duration so a brief spike doesn't page anyone. When investigating, I check the growth rate, inode usage, files that are open but deleted, logs, containers, and application data.

A time-to-full forecast and a critical threshold are often more useful than a single fixed percentage. I test both the rule and the receiver before trusting it.

</details>

<details><summary>Q3. [Advanced] How do you operate Prometheus for Kubernetes at production scale?</summary>

**Answer:**

I deploy a pinned kube-prometheus-stack or a managed service, and configure resource limits, persistent storage, retention, high availability, RBAC/authentication and ServiceMonitors. Node Exporter, kube-state-metrics and kubelet/cAdvisor cover nodes, object state and containers; applications expose their own business and request metrics on top of that.

For long retention or queries across clusters, I use remote write into Thanos, Mimir, or a managed backend. I monitor Prometheus's own memory and disk usage, rule evaluation time, failed scrapes, remote-write backlog, and cardinality.

I inject test alerts and simulate a lost target to confirm the whole pipeline works. Stable cluster and service labels support multi-cluster queries, but unlimited request or user labels are not allowed — they blow up cardinality.

</details>
