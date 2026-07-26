# Host Monitoring Summary

## What to Monitor

Host monitoring covers:

- CPU utilization, load, context switching and I/O wait
- Memory availability, cache, swap and out-of-memory events
- Filesystem capacity, inode use, growth and disk I/O latency
- Network throughput, errors, drops and connections
- Process and service health
- Certificate expiry, time synchronization and operating-system logs

`node-exporter` exposes Linux host metrics on `/metrics`, normally on port `9100`. Windows exporter provides Windows performance counters. Prometheus scrapes these endpoints and Grafana visualizes the stored time series.

```text
Host → Node Exporter → Prometheus → Grafana
                              └──→ alert rule → Alertmanager
```

Restrict exporter endpoints to the monitoring network because infrastructure metrics reveal operational details. Do not expose port `9100` publicly.

## Example PromQL

```promql
# CPU usage percentage
100 * (
  1 - avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[5m])
  )
)

# Available-memory-based usage percentage
100 * (
  1 -
  node_memory_MemAvailable_bytes
  /
  node_memory_MemTotal_bytes
)

# Root filesystem usage percentage
100 * (
  1 -
  node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
  /
  node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
)

# Target scrape failure
up{job="node"} == 0
```

For custom batch jobs or machine-local facts that cannot expose an HTTP endpoint, the Node Exporter textfile collector can read atomically written Prometheus metric files. It should not be used to export high-cardinality application events.

## Container Monitoring

cAdvisor provides container CPU, memory, filesystem and network usage. It often needs sensitive host mounts and privileges, so review its permissions carefully. In AKS, prefer supported kubelet/cAdvisor scraping through the cluster monitoring solution instead of deploying a broadly privileged standalone container without review. Use kube-state-metrics separately for Kubernetes object state; it does not provide actual container resource consumption.

## Investigation Flow

For a target-down alert:

1. Check Prometheus target discovery, labels and the latest scrape error.
2. Verify DNS/network reachability and the exporter process or pod.
3. Query the exporter `/metrics` endpoint from the Prometheus network.
4. Check TLS/authentication, firewall or NetworkPolicy changes.
5. Review resource exhaustion and exporter logs.
6. Restore service and confirm multiple successful scrapes and alert resolution.

For **high CPU**, compare user, system, I/O wait and steal time, then identify the responsible process or container. For **memory**, distinguish cache from real pressure and examine swap, OOM events and growth. For **disk**, separate capacity, inode and latency problems.

Service monitoring should verify the process, listening port, dependencies and a real health transaction instead of restarting a failed process forever. Alert on sustained actionable conditions and forecasted exhaustion. After remediation, confirm application latency and errors as well as the host metric.
