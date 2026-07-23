# Kubernetes Monitoring Summary

Monitor **four layers**:

- **Control plane:** API availability/latency/errors, scheduler/controller queues and `etcd` health for self-managed clusters.
- **Nodes:** `Ready` condition, CPU/memory, disk/inodes/PIDs, network, `kubelet`, runtime, CNI, CoreDNS and certificate expiry.
- **Workloads:** Pending Pods, restarts, unavailable replicas, Jobs, HPA, PDB, PVC/CSI and Ingress health.
- **Applications:** availability, latency, traffic, errors, saturation, dependencies and business transactions.

`kube-prometheus-stack` commonly provides Prometheus Operator, Grafana, Alertmanager, `node-exporter` and `kube-state-metrics`. Add application `ServiceMonitor`s, centralized structured logs through Fluent Bit to Loki/Elasticsearch/cloud logging, and OpenTelemetry traces to Tempo/Jaeger or a vendor platform. Liveness/readiness probes affect workload behavior but are not a monitoring system.

For **multi-cluster monitoring**, attach stable cluster/account/region/environment labels, retain tenant access boundaries, use remote write or Thanos/Mimir/managed Prometheus for global queries, and centralize dashboards without making one cluster a single point of failure. Test missing-scrape, dropped-log, alert-routing and backend-outage scenarios. Monitor the monitoring stack's ingestion, storage, cardinality and cost.
