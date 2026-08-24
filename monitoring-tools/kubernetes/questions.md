## 1. What metrics prove Kubernetes cluster health?

**Answer:**

I look at four layers.

At the control plane: API server availability, latency, and error rate; scheduler and controller queue depth; and etcd health, where I own it.

At the node level: whether nodes are Ready, CPU and memory use, disk space, inodes and process limits, network health, and the state of kubelet, the container runtime, CNI, and CoreDNS.

At the workload level: Pending Pods, restart counts, unavailable replicas, Job status, HPA and PDB behavior, PVC/CSI health, and Ingress and certificate status.

Most importantly, I watch the application itself: availability, latency, traffic, errors, saturation, and at least one real business transaction. Saturation means how close a resource is to its limit. Healthy nodes don't prove healthy users, so this layer matters more than the others.

Alerts focus on symptoms that actually need action — an SLO burning too fast, zero Ready replicas, a node under pressure. Diagnostic detail belongs in dashboards, not alerts. I validate every alert, tag it with cluster, version, and deployment labels, and keep an eye on cardinality — too many unique label combinations driving up cost and noise.

## 2. How do you implement centralized monitoring for many Kubernetes or AKS clusters?

**Answer:**

Each cluster runs its own collectors and exporters, tagged with a stable identity: cluster name, subscription or account, region, and environment.

Metrics are remote-written to a managed Prometheus setup, or to a Thanos/Mimir architecture, and Grafana provides shared dashboards with access scoped per tenant.

Logs flow through buffered node agents into a central backend — Log Analytics, Loki, OpenSearch, or whatever platform is standard — while OpenTelemetry handles trace export. On Azure this often combines Azure Monitor/Container Insights, Managed Prometheus, and Managed Grafana.

I design for high availability, retention, cost, network and private access, and tenant isolation. I watch for dropped data and backpressure, and I test what happens when a cluster, backend, or network link fails. Central visibility isn't an excuse to give every team access to every cluster, and it shouldn't turn into one shared failure domain that takes every cluster down at once.

## 3. How do you monitor Kubernetes logs?

**Answer:**

`kubectl logs` and `kubectl logs --previous` are fine for debugging one Pod right now. They aren't a production logging strategy.

In production, applications write structured logs to stdout/stderr. A DaemonSet collector — Fluent Bit is a common choice — ships them to a central backend: Loki, Elasticsearch/OpenSearch, a cloud logging service, or a SaaS platform.

Every log line should carry service, namespace, Pod, version, and trace ID, but never secrets or personal data.

I configure buffers, backpressure handling, multiline parsing, retention, and access controls, and I alert when the collector itself fails or drops records. During an incident, I start from the affected transaction and its trace ID instead of searching every log in the cluster.
