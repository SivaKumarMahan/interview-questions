## 1. What is in `prometheus.yml` and how do you validate it?

**Answer:**

It usually defines the global scrape and evaluation intervals, scrape jobs and service discovery, relabeling rules, rule files, remote write, and Alertmanager targets. In Kubernetes, Operator resources like `ServiceMonitor` and `PodMonitor` often generate this scrape configuration for you.

To validate it, I run `promtool check config`, check the Targets page for discovery, TLS or auth errors, confirm the expected labels with a sample query, and reload it through the supported method. Credentials go through secret files or the platform's secret integration, not plain text in the config.

I also watch scrape duration and failures, and keep an eye on label cardinality — the number of unique label combinations a metric produces — so a single bad target can't destabilize the whole Prometheus instance.

## 2. How do you alert when disk use exceeds 80%?

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

## 3. How do you operate Prometheus for Kubernetes at production scale?

**Answer:**

I deploy a pinned kube-prometheus-stack or a managed service, and configure resource limits, persistent storage, retention, high availability, RBAC/authentication and ServiceMonitors. Node Exporter, kube-state-metrics and kubelet/cAdvisor cover nodes, object state and containers; applications expose their own business and request metrics on top of that.

For long retention or queries across clusters, I use remote write into Thanos, Mimir, or a managed backend. I monitor Prometheus's own memory and disk usage, rule evaluation time, failed scrapes, remote-write backlog, and cardinality.

I inject test alerts and simulate a lost target to confirm the whole pipeline works. Stable cluster and service labels support multi-cluster queries, but unlimited request or user labels are not allowed — they blow up cardinality.
