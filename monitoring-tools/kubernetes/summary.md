# Kubernetes Monitoring Summary

## The Four Layers

Kubernetes monitoring breaks down into four layers, from the platform down to the actual user experience:

| Layer | What to watch |
| --- | --- |
| Control plane | API availability, latency, and errors; scheduler and controller queue depth; `etcd` health (self-managed clusters only) |
| Nodes | `Ready` condition, CPU/memory, disk/inodes/PIDs, network, `kubelet`, runtime, CNI, CoreDNS, certificate expiry |
| Workloads | Pending Pods, restarts, unavailable replicas, Jobs, HPA, PDB, PVC/CSI, Ingress health |
| Applications | Availability, latency, traffic, errors, saturation, dependencies, business transactions |

Saturation means how close a resource is to its limit — it's the layer most likely to catch a problem users actually feel.

## Standard Stack

`kube-prometheus-stack` commonly provides the Prometheus Operator, Grafana, Alertmanager, `node-exporter`, and `kube-state-metrics`. On top of that, add application `ServiceMonitor`s, centralized structured logs shipped through Fluent Bit to Loki, Elasticsearch, or cloud logging, and OpenTelemetry traces sent to Tempo, Jaeger, or a vendor platform.

Liveness and readiness probes change how a workload behaves — they restart or reroute traffic away from unhealthy Pods — but they are not a monitoring system on their own.

## Multi-Cluster Monitoring

Attach stable cluster, account, region, and environment labels to everything. Keep tenant access boundaries in place so one team's dashboard access doesn't leak into another's cluster. Use remote write, or Thanos/Mimir/managed Prometheus, to run queries across clusters, and centralize dashboards without turning any single cluster into a point of failure for the rest.

## Testing and Cost

Test the failure scenarios directly: a missing scrape, a dropped log, broken alert routing, a backend outage. And monitor the monitoring stack itself — its ingestion rate, storage use, cardinality (the number of unique label combinations it's tracking), and cost.

## Kubernetes Log Triage

Start with the failing container's current and previous logs, its Pod description, and its ordered events.

On a node, `/var/log/containers/` and `/var/log/pods/` usually hold the container and pod log files. Evidence from kubelet, the runtime, CNI, and the kernel is usually found through the system journal instead — exact paths vary by Linux distribution and runtime.

Compare timestamps against deployments, node pressure, image pulls, probe failures, and network events.

For AKS, use Azure Monitor/Container Insights, Log Analytics, and the enabled AKS diagnostic categories to get evidence from the managed control plane. Don't assume you have direct host access, or that API server, scheduler, and etcd logs sit at fixed paths — a managed control plane doesn't work that way.

Application teams should emit structured logs to stdout/stderr with service, environment, version, and trace ID. Collectors are responsible for redacting secrets and applying buffering, retention, and access controls.
