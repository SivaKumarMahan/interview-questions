# Kubernetes Interview Topics

Legend: ✅ covered · — not covered

| Topic | `summary.txt` | `questions.txt` | `notes.txt` |
| --- | :---: | :---: | :---: |
| Containers vs. Kubernetes | ✅ | — | — |
| Cluster and control-plane architecture | ✅ | ✅ | ✅ |
| Pods and shared namespaces | ✅ | ✅ | ✅ |
| Deployments and ReplicaSets | ✅ | ✅ | ✅ |
| StatefulSets | ✅ | ✅ | ✅ |
| DaemonSets | ✅ | ✅ | ✅ |
| Jobs, CronJobs, and init containers | ✅ | ✅ | ✅ |
| Manifests and desired state | ✅ | ✅ | ✅ |
| ConfigMaps, Secrets, and ServiceAccounts | ✅ | ✅ | ✅ |
| Services, ports, Ingress, DNS, Pod networking, and NetworkPolicy (centralized) | — | — | — |
| PV, PVC, StorageClass, and access modes | ✅ | ✅ | ✅ |
| Scheduler, affinity, taints, and tolerations | ✅ | ✅ | ✅ |
| Requests, limits, OOM handling, and autoscaling | ✅ | ✅ | ✅ |
| Health probes and self-healing | ✅ | ✅ | ✅ |
| Rolling, blue-green, and canary deployments | ✅ | ✅ | ✅ |
| RBAC, workload identity, and secret management | ✅ | ✅ | ✅ |
| Security contexts, Pod security, and compliance | ✅ | ✅ | ✅ |
| Image and supply-chain security | ✅ | ✅ | ✅ |
| Pod, node, and storage troubleshooting | ✅ | ✅ | ✅ |
| Backup, restore, Velero, and disaster recovery | ✅ | ✅ | ✅ |
| Monitoring, logging, chaos engineering, and observability | ✅ | ✅ | ✅ |
| Cluster and fleet upgrades | ✅ | ✅ | ✅ |
| CI/CD and GitOps | ✅ | ✅ | ✅ |
| CRDs, custom controllers, and Kubernetes Operators | ✅ | ✅ | ✅ |
| Service mesh architecture and optimization | ✅ | ✅ | — |

## Coverage Gaps

### Summary topics without dedicated interview questions

- Containers vs. Kubernetes
- Helm/Flux GitOps implementation details

## Consolidated Material

- `questions.txt` contains 120 answered questions, including detailed CRD and custom-controller design, reconciliation, lifecycle, troubleshooting, and examples.
- `notes.txt` combines the former `notes.txt`, `notes1.txt`, and `notes2.txt` material under topic headings.
- `summary.txt` includes a quick-revision section for production investigation, security, delivery, scaling, stateful recovery, observability, and chaos-engineering scenarios.
- Kubernetes service discovery, ports, Ingress, DNS, CNI, NetworkPolicy, and connectivity scenarios are maintained in [`networking/kubernetes`](../networking/kubernetes/README.md).
