# Monitoring Tools: Kubernetes Monitoring

> The layers of Kubernetes monitoring, the standard stack, multi-cluster setups, and Kubernetes log triage.

## Key Concepts

### The Four Layers of Kubernetes Monitoring

Kubernetes monitoring breaks down into four layers, from the platform down to the actual user experience:

| Layer | What to watch |
| --- | --- |
| Control plane | API availability, latency, and errors; scheduler and controller queue depth; `etcd` health (self-managed clusters only) |
| Nodes | `Ready` condition, CPU/memory, disk/inodes/PIDs, network, `kubelet`, runtime, CNI, CoreDNS, certificate expiry |
| Workloads | Pending Pods, restarts, unavailable replicas, Jobs, HPA, PDB, PVC/CSI, Ingress health |
| Applications | Availability, latency, traffic, errors, saturation, dependencies, business transactions |

Saturation means how close a resource is to its limit — it's the layer most likely to catch a problem users actually feel.

### Standard Kubernetes Monitoring Stack

`kube-prometheus-stack` commonly provides the Prometheus Operator, Grafana, Alertmanager, `node-exporter`, and `kube-state-metrics`. On top of that, add application `ServiceMonitor`s, centralized structured logs shipped through Fluent Bit to Loki, Elasticsearch, or cloud logging, and OpenTelemetry traces sent to Tempo, Jaeger, or a vendor platform.

Liveness and readiness probes change how a workload behaves — they restart or reroute traffic away from unhealthy Pods — but they are not a monitoring system on their own.

### Monitoring AKS with Prometheus and Grafana

The monitoring flow is:

```text
Application exposes /metrics
        ↓
Prometheus discovers the target through Kubernetes
        ↓
Prometheus regularly scrapes and stores the metrics
        ↓
Grafana queries Prometheus and displays dashboards
        ↓
Alertmanager sends notifications when rules are triggered
```

### How Prometheus and Grafana monitoring works on AKS

1. The application exposes values such as request count, errors, memory use, and response time through a `/metrics` endpoint.
2. Prometheus watches the Kubernetes API and discovers pods, services, endpoints, and nodes. New replicas can therefore be found automatically.
3. Prometheus sends HTTP requests to each metrics endpoint at a configured interval, often every 15 to 30 seconds.
4. It stores each metric with its timestamp, value, and labels in a time-series database.
5. Grafana uses Prometheus as a data source. It runs PromQL queries and turns the results into graphs, tables, gauges, and other dashboard panels. Grafana does not collect the metrics itself.
6. Prometheus evaluates alert rules. When a rule is true, Alertmanager groups, de-duplicates, and routes notifications to systems such as email, Microsoft Teams, Slack, or PagerDuty.

Example PromQL queries:

```promql
rate(http_requests_total[5m])
sum(container_memory_usage_bytes)
```

Common dashboard and alert signals include:

- CPU and memory use
- Request rate and response time
- HTTP error rate
- Pod restarts and unavailable pods
- Network and disk use
- Node health

### Kubernetes metric sources

| Component | What it provides |
| --- | --- |
| `kube-state-metrics` | State of pods, Deployments, nodes, PVCs, and other Kubernetes objects |
| `node-exporter` | Node CPU, memory, disk, filesystem, and network metrics |
| `cAdvisor` | Container CPU, memory, filesystem, and network metrics |
| Kubelet and API server | Node, pod, and Kubernetes API metrics |
| CoreDNS | DNS metrics |

### Installing kube-prometheus-stack with Helm

In production this is normally installed as a single Helm release rather than assembled component by component:

```bash
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

This one chart typically brings in Prometheus, Grafana, Alertmanager, `kube-state-metrics`, and `node-exporter` together, pre-wired to scrape the cluster.

### Multi-Cluster Monitoring

Attach stable cluster, account, region, and environment labels to everything. Keep tenant access boundaries in place so one team's dashboard access doesn't leak into another's cluster. Use remote write, or Thanos/Mimir/managed Prometheus, to run queries across clusters, and centralize dashboards without turning any single cluster into a point of failure for the rest.

### Testing and Cost

Test the failure scenarios directly: a missing scrape, a dropped log, broken alert routing, a backend outage. And monitor the monitoring stack itself — its ingestion rate, storage use, cardinality (the number of unique label combinations it's tracking), and cost.

### Kubernetes Log Triage

Start with the failing container's current and previous logs, its Pod description, and its ordered events.

On a node, `/var/log/containers/` and `/var/log/pods/` usually hold the container and pod log files. Evidence from kubelet, the runtime, CNI, and the kernel is usually found through the system journal instead — exact paths vary by Linux distribution and runtime.

Compare timestamps against deployments, node pressure, image pulls, probe failures, and network events.

For AKS, use Azure Monitor/Container Insights, Log Analytics, and the enabled AKS diagnostic categories to get evidence from the managed control plane. Don't assume you have direct host access, or that API server, scheduler, and etcd logs sit at fixed paths — a managed control plane doesn't work that way.

Application teams should emit structured logs to stdout/stderr with service, environment, version, and trace ID. Collectors are responsible for redacting secrets and applying buffering, retention, and access controls.

## Interview Questions

### 1. What metrics prove Kubernetes cluster health?

**Answer:**

I look at four layers.

At the control plane: API server availability, latency, and error rate; scheduler and controller queue depth; and etcd health, where I own it.

At the node level: whether nodes are Ready, CPU and memory use, disk space, inodes and process limits, network health, and the state of kubelet, the container runtime, CNI, and CoreDNS.

At the workload level: Pending Pods, restart counts, unavailable replicas, Job status, HPA and PDB behavior, PVC/CSI health, and Ingress and certificate status.

Most importantly, I watch the application itself: availability, latency, traffic, errors, saturation, and at least one real business transaction. Saturation means how close a resource is to its limit. Healthy nodes don't prove healthy users, so this layer matters more than the others.

Alerts focus on symptoms that actually need action — an SLO burning too fast, zero Ready replicas, a node under pressure. Diagnostic detail belongs in dashboards, not alerts. I validate every alert, tag it with cluster, version, and deployment labels, and keep an eye on cardinality — too many unique label combinations driving up cost and noise.

### 2. How do you implement centralized monitoring for many Kubernetes or AKS clusters?

**Answer:**

Each cluster runs its own collectors and exporters, tagged with a stable identity: cluster name, subscription or account, region, and environment.

Metrics are remote-written to a managed Prometheus setup, or to a Thanos/Mimir architecture, and Grafana provides shared dashboards with access scoped per tenant.

Logs flow through buffered node agents into a central backend — Log Analytics, Loki, OpenSearch, or whatever platform is standard — while OpenTelemetry handles trace export. On Azure this often combines Azure Monitor/Container Insights, Managed Prometheus, and Managed Grafana.

I design for high availability, retention, cost, network and private access, and tenant isolation. I watch for dropped data and backpressure, and I test what happens when a cluster, backend, or network link fails. Central visibility isn't an excuse to give every team access to every cluster, and it shouldn't turn into one shared failure domain that takes every cluster down at once.

### 3. How do you monitor Kubernetes logs?

**Answer:**

`kubectl logs` and `kubectl logs --previous` are fine for debugging one Pod right now. They aren't a production logging strategy.

In production, applications write structured logs to stdout/stderr. A DaemonSet collector — Fluent Bit is a common choice — ships them to a central backend: Loki, Elasticsearch/OpenSearch, a cloud logging service, or a SaaS platform.

Every log line should carry service, namespace, Pod, version, and trace ID, but never secrets or personal data.

I configure buffers, backpressure handling, multiline parsing, retention, and access controls, and I alert when the collector itself fails or drops records. During an incident, I start from the affected transaction and its trace ID instead of searching every log in the cluster.
### 4. How do you troubleshoot missing metrics in Prometheus and Grafana?

If a target's metrics aren't showing up in Grafana, work through it in order:

1. **Check Prometheus Pods** - `kubectl get pods -n monitoring` to confirm Prometheus itself is running.
2. **Check Prometheus Targets** - in the Prometheus UI, confirm the target shows as `UP`, not `DOWN`.
3. **Confirm the `/metrics` endpoint** - `curl` the application's metrics port directly to confirm it's actually exposing data.
4. **Check ServiceMonitor/PodMonitor** - confirm a `ServiceMonitor` or `PodMonitor` resource exists and its label selector actually matches the target Service/Pod.
5. **Check NetworkPolicies/firewalls** - confirm nothing is blocking Prometheus from reaching the target's metrics port.
6. **Review Prometheus logs** - scrape errors (TLS, auth, timeouts) usually show up here.
