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

For batch jobs or machine-local facts that can't expose an HTTP endpoint, the Node Exporter textfile collector can read metric files that were written atomically. Don't use it to export application events with a large number of unique label combinations (high cardinality) — it's meant for host-level facts, not application telemetry.

## Container Monitoring

cAdvisor reports container CPU, memory, filesystem, and network usage. It often needs sensitive host mounts and elevated privileges, so review what access it's actually granted.

In AKS, prefer the supported kubelet/cAdvisor scraping built into the cluster monitoring solution, rather than deploying your own broadly privileged container without review. Use kube-state-metrics separately for Kubernetes object state — it reports things like desired vs. available replicas, not actual container resource usage.

## Investigation Flow

For a target-down alert:

1. Check Prometheus target discovery, labels and the latest scrape error.
2. Verify DNS/network reachability and the exporter process or pod.
3. Query the exporter `/metrics` endpoint from the Prometheus network.
4. Check TLS/authentication, firewall or NetworkPolicy changes.
5. Review resource exhaustion and exporter logs.
6. Restore service and confirm multiple successful scrapes and alert resolution.

For **high CPU**, compare user, system, I/O wait, and steal time to find the responsible process or container. For **memory**, tell cache usage apart from real memory pressure, and check swap, OOM events, and growth trend.

For **disk**, separate capacity, inode, and latency problems.

Service monitoring should check the process, the listening port, its dependencies, and a real health-check transaction, not just restart a failed process forever. Alert on conditions that are sustained and actionable, and on forecasted exhaustion, not every brief blip.

After fix, confirm application latency and errors as well as the host metric.
