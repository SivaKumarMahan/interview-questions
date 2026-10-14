# Monitoring Tools: Host Monitoring and Netdata

> Monitoring Linux and Windows hosts and containers, host PromQL, CPU/memory/disk investigations, and Netdata's architecture and secure deployment.

## Key Concepts

### What to Monitor on Hosts

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

### Example Host PromQL

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

### Container Monitoring

cAdvisor reports container CPU, memory, filesystem, and network usage. It often needs sensitive host mounts and elevated privileges, so review what access it's actually granted.

In AKS, prefer the supported kubelet/cAdvisor scraping built into the cluster monitoring solution, rather than deploying your own broadly privileged container without review. Use kube-state-metrics separately for Kubernetes object state — it reports things like desired vs. available replicas, not actual container resource usage.

### Host Investigation Flow

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

### What Netdata Is

Netdata is a real-time infrastructure monitoring platform built around the **Netdata Agent**. The Agent runs on a host, automatically finds collectors, gathers high-frequency system and application metrics, stores recent data locally, shows dashboards and evaluates health alerts.

It's a good fit for fast host and container troubleshooting. It can run alongside Prometheus, cloud-native monitoring, or a larger observability platform instead of replacing them.

### Netdata Parent-Child Architecture

For more than a handful of systems, **Child Agents** stream their metrics to one or more **Parent Agents**. The Parent centralizes retention, dashboards and alert processing so you don't have to check every node separately.

When you rely on this for production, plan for:

- Sizing Parent storage and ingestion capacity for the number of nodes and metrics involved.
- Protecting streaming credentials and using TLS between Children and Parents.
- Restricting access to the Parent, and having a recovery plan if it goes down.
- Testing what happens when a Child loses its connection and reconnects.

### Netdata Security and Networking

The Agent's local web UI, API and streaming service all use configurable networking. Port `19999` is the documented default, but it should never be exposed broadly to the internet — put it behind authentication and a secured proxy, or restrict it to a private management path.

### What to Monitor with Netdata

| Area | What to check |
|---|---|
| Host resources | CPU, load, memory, swap, disks, filesystems, network |
| Workloads | Processes, containers, supported applications |
| Netdata itself | Collector status, chart dimensions, clock accuracy |
| Alerting | Alert routing, resolution, and who owns each alert |
| Parent-Child | Retention limits and parent/child connectivity |

### Where Netdata Fits

A good-looking dashboard isn't the whole job. Alerts still need an owner and a runbook, and user-facing service SLIs still need application or synthetic instrumentation on top of what Netdata collects. Netdata is strongest for fast infrastructure visibility; it's not a replacement for defining what "healthy" means for your actual service.

## Interview Questions

<details><summary>Q1. [Basic] What do you monitor on Linux and Windows servers?</summary>

**Answer:**

On both platforms I watch CPU and load, plus the top processes. I watch memory and swap usage, and out-of-memory events. I watch disk capacity, inode usage, disk I/O, and how fast disk usage is growing. I watch network errors and connection counts, service and process state, open ports, certificate expiry, time sync, pending updates, and OS and application logs.

I always compare these against request latency, errors, and traffic, because a host can look perfectly healthy while the application running on it is broken.

On Linux I'd typically use node-exporter, journald, and process or service exporters. On Windows I'd use windows_exporter, Performance Monitor counters, and Event Viewer forwarding. Cloud-native or commercial agents can replace or add to any of these.

Alerts should be based on sustained conditions, owned by a specific team, and linked to a runbook.

</details>

<details><summary>Q2. [Basic] What is Netdata, and when would you use it?</summary>

**Answer:**

Netdata runs an Agent on a host. The Agent finds collectors on its own, gathers real-time metrics, shows dashboards and evaluates health alerts.

I use it for fast infrastructure visibility: troubleshooting CPU, memory, disk, network, processes and containers. It gives useful dashboards with almost no setup.

It can sit alongside Prometheus, Grafana or cloud monitoring rather than replace them. I still need to define application SLIs, retention, access control and who owns each incident. Installing a tool by itself does not prove the service is available to customers.

</details>

<details><summary>Q3. [Basic] How is Netdata different from Prometheus and Grafana?</summary>

**Answer:**

Netdata focuses on an integrated Agent: automatic collectors, real-time dashboards and health alerts with almost no setup. Prometheus is a time-series system built around labeled scraping, querying and rules, and is commonly used for services and Kubernetes. Grafana visualizes data from many different sources.

The three can coexist. Netdata handles rapid diagnosis on a single node, Prometheus handles selected platform and application metrics with a long-term architecture, and Grafana gives you shared dashboards across sources.

I pick between them based on scale, retention needs, query language, how well application instrumentation is exposed, integrations, operational effort, access and data residency requirements, and cost — not by declaring one tool universally better.

</details>

<details><summary>Q4. [Intermediate] How does Netdata Parent-Child monitoring work?</summary>

**Answer:**

Children collect metrics locally and stream them to one or more configured Parent Agents. Parents centralize those metrics and can provide dashboards, retention and health evaluation on behalf of their children.

This means you don't have to browse every node separately. Depending on configuration, buffering and replication can also preserve collection through some network interruptions.

When central monitoring is critical, I plan for more than one parent, or a clear recovery strategy. I size CPU, memory, disk and network from the node count and metric volume, use stable host labels, apply TLS and access controls, and watch for stream disconnects, lag, retention limits and how close the parent is to its own resource limits.

I test what happens on connection loss and reconnection. I don't just assume centralized monitoring is highly available.

</details>

<details><summary>Q5. [Intermediate] How would you deploy Netdata securely in production?</summary>

**Answer:**

I use a pinned, supported deployment method and give it only the host or container access it actually needs. I restrict the local dashboard and API to localhost or a private management path, require authenticated access, protect configuration and streaming keys, and use TLS between Children and Parents.

I never expose the default port `19999` publicly without a secured proxy and an authorization design in front of it.

For centralized monitoring, Child Agents stream to resilient Parent capacity, or use the approved cloud connection model. Firewall rules allow only the paths that are actually needed.

I also define retention and storage limits, labels, alert receivers and backups, and test agent and parent upgrades in a lower environment first.

</details>

<details><summary>Q6. [Intermediate] How do you investigate a high-CPU alert safely?</summary>

**Answer:**

First I confirm the alert is real: how long has it been happening, and is it actually affecting users? I check recent traffic and recent changes, then break the CPU time down into user, system, steal, and I/O-wait time to find the responsible process or thread.

Where I can, I collect application and runtime evidence before restarting anything, since a restart destroys that evidence.

To stabilize things, I shift traffic away, scale out, or stop a task I've confirmed is non-essential and runaway. Then I fix the actual cause: bad code, a slow query, a config issue, a scheduled job, or just not enough capacity.

Afterward I confirm user-facing latency and errors are back to normal, check CPU under real load, and improve the alert or add a regression test so it's caught earlier next time.

</details>

<details><summary>Q7. [Intermediate] Netdata shows high CPU. How do you investigate?</summary>

**Answer:**

First I check whether the CPU spike is sustained, which cores are affected, and whether user, system, iowait or steal time dominates. I compare that against process and cgroup charts, traffic, load, recent deployments and any scheduled jobs.

On the host I confirm with `top`, `pidstat` or an equivalent tool, and look at application or runtime evidence before restarting anything.

To mitigate, I shift traffic, roll back, scale out, or stop a runaway task I've confirmed is nonessential. Then I fix the underlying cause: code, a bad query, configuration or capacity. I check that application latency and errors recover, along with Netdata's own CPU and load charts.

A host-level CPU alert is supporting evidence. It is not the root cause by itself.

</details>

<details><summary>Q8. [Intermediate] How do you monitor disk exhaustion?</summary>

**Answer:**

I track filesystem usage, inode usage, growth rate, and a forecast of when it will hit full, plus disk queue depth on collectors and containers.

When investigating, I look for what's actually growing: a specific directory, files that are open but already deleted, logs, temp data, package caches, or genuine application data.

I clean up using supported rotation and cleanup tools, and I never delete a file in production if I don't know what it is. To prevent this from recurring, I rely on retention policies, quotas, separate capacity where it makes sense, and alerts that fire early enough to act safely.

</details>

<details><summary>Q9. [Basic] How do you identify and investigate the ten highest-memory processes?</summary>

**Answer:**

For a point-in-time view I run:

```bash
ps -eo pid,ppid,user,%mem,rss,vsz,etime,cmd --sort=-rss | head -n 11
```

That gives one header line plus the ten highest processes. I sort by RSS rather than VSZ because RSS is the actual resident physical memory in use, though shared memory can still make per-process totals a bit imprecise.

`ps aux --sort=-%mem | head -n 11` works as a shorter alternative.

I don't assume the top process is leaking from a single sample. I check `free -h`, `vmstat 1`, swap usage, and OOM logs. Then I watch that specific PID over time with `pidstat -r -p <pid> 1`, along with application and runtime metrics and historical monitoring data.

I compare the growth pattern against traffic, deployments, and scheduled jobs. If the impact is severe, I scale out or restart gracefully, but only after preserving diagnostics first. Then I fix the actual leak, cache or heap configuration, workload sizing, or resource limit, and confirm memory, latency, and error rate are back to normal under regular load.

</details>

<details><summary>Q10. [Intermediate] Before it reaches 90%, how do you set up monitoring and alerts to the right teams? <em>(asked in interview round)</em></summary>

**Answer:**

I alert **early and on trend**, not only on a static threshold: a warning at 75–80%, a critical alert at 90%, and a **"will fill within N hours"** prediction. Alerts are routed by **ownership labels or tags** to the right team's channel, with a runbook link.

**Option A: AWS CloudWatch agent + alarm + SNS:**

**1. CloudWatch agent config** (publishes `disk_used_percent` in the `CWAgent` namespace):

```json
{
  "metrics": {
    "append_dimensions": { "InstanceId": "${aws:InstanceId}" },
    "metrics_collected": {
      "disk": {
        "measurement": ["used_percent", "inodes_free"],
        "resources": ["/", "/var/log", "/data"],
        "ignore_file_system_types": ["tmpfs", "devtmpfs", "overlay"],
        "metrics_collection_interval": 60
      }
    }
  }
}
```

**2. Alarm routed to the owning team's SNS topic:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "disk-root-80-i-0abc123" \
  --namespace CWAgent --metric-name disk_used_percent \
  --dimensions Name=InstanceId,Value=i-0abc123 Name=path,Value=/ Name=device,Value=nvme0n1p1 Name=fstype,Value=xfs \
  --statistic Average --period 300 --evaluation-periods 3 \
  --threshold 80 --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:111122223333:team-payments-alerts
```

The dimensions must match exactly what the agent publishes (check with `aws cloudwatch list-metrics --namespace CWAgent`). The SNS topic fans out to email, Slack/Teams (via Amazon Q Developer in chat applications or a Lambda) or `PagerDuty`. At scale, alarms are created from IaC per instance, or via a Lambda triggered when instances launch, using the instance's `Team` tag to pick the topic.

**Option B: Prometheus + `node_exporter` + Alertmanager:**

```yaml
groups:
  - name: disk
    rules:
      - alert: DiskUsageHigh
        expr: |
          (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}
             / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"}) * 100 > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.instance }} {{ $labels.mountpoint }} is {{ $value | humanize }}% full"
          runbook_url: https://wiki.example.com/runbooks/disk-full

      - alert: DiskWillFillIn24h
        expr: |
          predict_linear(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}[6h], 24 * 3600) < 0
          and node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}
            / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"} < 0.4
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.instance }} {{ $labels.mountpoint }} will fill within 24h"
```

The `team` label comes from scrape config relabeling (for example from an EC2 tag via `ec2_sd_configs`, or a Kubernetes label), and Alertmanager routes on it:

```yaml
route:
  receiver: default-ops
  group_by: [alertname, instance, mountpoint]
  routes:
    - matchers: ['team="payments"', 'severity="critical"']
      receiver: payments-pagerduty
    - matchers: ['team="payments"']
      receiver: payments-slack
    - matchers: ['team="data"']
      receiver: data-slack
receivers:
  - name: default-ops
    slack_configs:
      - channel: "#ops-alerts"
        api_url_file: /etc/alertmanager/secrets/slack-ops-url
  - name: payments-slack
    slack_configs:
      - channel: "#payments-alerts"
        api_url_file: /etc/alertmanager/secrets/slack-payments-url
  - name: payments-pagerduty
    pagerduty_configs:
      - routing_key_file: /etc/alertmanager/secrets/pd-payments-key
  - name: data-slack
    slack_configs:
      - channel: "#data-alerts"
        api_url_file: /etc/alertmanager/secrets/slack-data-url
```

```text
node_exporter / CloudWatch agent (per mount point)
        |
        v
Prometheus rules / CloudWatch alarms
  warning 80% | predicted full in 24h | critical 90%
        |
        v
Alertmanager routes by team label  /  SNS topic per team
        |
        v
Slack/Teams (warning)  |  PagerDuty/on-call (critical)  + runbook link
```

**Important points:**

- Monitor each relevant mount point and inodes, and exclude pseudo filesystems (`tmpfs`, `overlay`).
- `predict_linear` catches fast growth long before a static threshold, and avoids paging for disks that are high but stable.
- Use `for:` / evaluation periods to avoid flapping, and group or inhibit alerts to reduce noise.
- Every alert should have an owner, severity and runbook; consider automated remediation (log cleanup via SSM Automation) for known causes.

See also: [Prometheus](../monitoring-tools/02-prometheus.md), [Grafana and Alertmanager](../monitoring-tools/03-grafana-and-alertmanager.md), [AWS and Azure monitoring](../monitoring-tools/08-aws-and-azure-monitoring.md).

**Interview-ready answer:**

> "I set up disk monitoring per mount point with alerts at two levels plus a trend alert. On AWS, the CloudWatch agent publishes `disk_used_percent`, and a CloudWatch alarm at 80% sends to the owning team's SNS topic, chosen from the instance's team tag, which forwards to Slack or `PagerDuty`. In Prometheus environments, `node_exporter` exposes filesystem metrics, and I have a threshold rule plus a `predict_linear` rule that fires if the disk will fill within 24 hours. Alertmanager routes on the team and severity labels, so warnings go to the team channel and critical alerts page on-call. Each alert includes the host, mount point and a runbook link, and I use `for` durations to avoid flapping."

</details>
