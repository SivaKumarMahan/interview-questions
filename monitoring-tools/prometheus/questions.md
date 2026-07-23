## 1. What is in `prometheus.yml` and how do you validate it?

**Answer:**

It commonly defines global scrape/evaluation intervals, scrape jobs and service discovery, relabeling, rule files, remote write and Alertmanager targets. In Kubernetes, Operator resources such as ServiceMonitor and PodMonitor often generate scrape configuration.

I run `promtool check config`, inspect the Targets page for discovery/TLS/auth errors, verify expected labels and a sample query, and reload through the supported method. Credentials use secret files or platform secret integration. I also watch scrape duration/failures and label cardinality so one target cannot destabilize Prometheus.

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

I exclude irrelevant/read-only filesystems, include mount point and runbook, and use a duration to avoid transient noise. Investigation checks growth rate, inode use, open-deleted files, logs, containers and application data. A time-to-full forecast and critical threshold may be more urgent than a fixed percentage. I test both the rule and receiver.

## 3. How do you operate Prometheus for Kubernetes at production scale?

**Answer:**

I deploy a pinned kube-prometheus-stack or managed service, configure resources, persistent storage, retention, HA, RBAC/authentication and ServiceMonitors. node-exporter, kube-state-metrics and kubelet/cAdvisor cover nodes, object state and containers; applications expose business and request metrics.

For long retention/global queries I use remote write with Thanos/Mimir or a managed backend. I monitor Prometheus memory/disk, rule time, failed scrapes, remote-write backlog and cardinality. I inject test alerts and simulate a lost target. Stable cluster/service labels support multi-cluster queries, while unbounded request/user labels are prohibited.
