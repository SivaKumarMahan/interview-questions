# Prometheus Summary

## What Prometheus Does

Prometheus is a pull-based monitoring system, time-series database, PromQL query engine and rule evaluator. It periodically scrapes HTTP metric endpoints, stores each sample with a timestamp and labels, evaluates recording and alerting rules, and exposes data to tools such as Grafana.
The usual flow is:

```text
Application / host / Kubernetes
        ↓ exposes /metrics
Exporter or instrumented application
        ↓ scraped by Prometheus
Prometheus TSDB + PromQL + rules
        ├── Grafana dashboards
        └── Alertmanager notifications
```

A time series consists of a metric name and a unique label set. For example, `http_requests_total{service="orders",status="200"}` is different from the same metric with `status="500"`.

Labels should be limited and operationally useful. Never use request IDs, user IDs, timestamps or unlimited URL values as metric labels because they create excessive cardinality (number of unique label combinations).

## Metric Types

- **Counter:** a value that normally only increases, such as requests or errors. Query it with `rate()` or `increase()`, not a raw average.
- **Gauge:** a value that can rise or fall, such as memory usage, queue depth or active sessions.
- **Histogram:** observations distributed into buckets, such as request duration. It supports server-side aggregation and percentile estimation with `histogram_quantile()`.
- **Summary:** observations with client-calculated quantiles. Quantiles generally cannot be aggregated reliably across instances.

## Exporters and Kubernetes Resources

Common metric sources include:

| Source | Purpose |
|---|---|
| Node Exporter | Linux CPU, memory, load, filesystem and network metrics |
| Kubelet/cAdvisor | Pod and container CPU, memory, filesystem and network usage |
| kube-state-metrics | Kubernetes object state such as desired/available replicas and pod phase |
| Blackbox Exporter | HTTP, TCP, DNS and ICMP synthetic probes |
| Application client library | Business and application metrics exposed at `/metrics` |

With Prometheus Operator, `ServiceMonitor`, `PodMonitor`, `Probe` and `PrometheusRule` resources provide Kubernetes-native target and rule configuration.

## Basic Configuration

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

In Kubernetes, prefer service discovery and `ServiceMonitor`/`PodMonitor` resources over maintaining static pod IPs. Before reloading configuration, run:

```bash
promtool check config /etc/prometheus/prometheus.yml
promtool check rules /etc/prometheus/rules/*.yml
```

On the Prometheus **Targets** page, confirm the target is discovered, its state is `UP`, the labels are correct and the last scrape has no error. The `up` metric reports scrape success; it does not prove that the application itself is healthy.

## Useful PromQL

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

Use a range long enough to contain several scrapes. Combined away instance-level labels only when that matches the question being asked.

## Recording and Alerting Rules

Recording rules precompute frequently used or expensive expressions. Alerting rules should describe sustained, actionable symptoms and include ownership and troubleshooting context.

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

The `for` duration prevents a short spike from immediately firing. Test the complete path: rule expression, pending state, firing state, Alertmanager route, notification and resolved notification.

## Production Practices

- Persist the TSDB and size retention according to ingestion rate, disk capacity and compliance needs.
- Monitor Prometheus itself: failed scrapes, rule evaluation failures, storage growth, compaction, cardinality (number of unique label combinations) and remote-write backlog.
- Use recording rules for repeated expensive queries and keep dashboards within reasonable query ranges.
- Run highly available replicas when required. Long retention and global querying can use a compatible managed service, Thanos or Mimir.
- Keep Prometheus, exporters and service-discovery endpoints on private networks. Use TLS, authentication/authorization at the ingress or reverse proxy, and least-privilege (minimum required access) discovery credentials.
- Pin reviewed container versions, back up configuration/rules, and provision them through version control.

For an Azure-based environment, Azure Monitor managed service for Prometheus and Azure Managed Grafana can reduce the operational work for AKS monitoring. Self-managed Prometheus remains useful where configuration control or portability is required.

## Local Learning Stack

A Docker Compose lab commonly contains Prometheus (`9090`), Grafana (`3000`), Node Exporter (`9100`), cAdvisor (`8080`), Loki (`3100`) and Alertmanager (`9093`). Use service names for container-to-container URLs, such as `http://prometheus:9090`, and bind web ports to `127.0.0.1` for local practice.

Publicly exposing monitoring ports or using unpinned `latest` images is not a production design.
