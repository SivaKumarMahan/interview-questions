# Kubernetes Operations and Stateful Workloads

## 1. Viewing Pod Logs

Use `kubectl logs` to read the output of an application running in a pod.

| Command | Purpose |
| --- | --- |
| `kubectl logs <pod>` | Show the current logs of the default container |
| `kubectl logs <pod> -c <container>` | Show logs from one container in a multi-container pod |
| `kubectl logs -f <pod>` | Follow new log messages in real time; press `Ctrl+C` to stop |
| `kubectl logs <pod> --previous` | Show logs from the previous container instance after a restart |
| `kubectl logs -l app=web --tail=100` | Show the last 100 lines from pods with the label `app=web` |
| `kubectl logs <pod> --tail=50` | Show only the last 50 lines |
| `kubectl logs <pod> --since=30m` | Show logs from the last 30 minutes |
| `kubectl logs <pod> --timestamps` | Include a timestamp on each line |
| `kubectl logs <pod> --all-containers=true` | Show logs from every container in the pod |
| `kubectl logs <pod> -c app --previous` | Show previous logs for a specific container |
| `kubectl logs deployment/myapp` | Show logs from a pod managed by a Deployment |
| `kubectl logs job/my-job` | Show logs from a Job |

### Basic pod troubleshooting

Run these commands in order:

```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl logs <pod-name> --previous
kubectl get events --sort-by=.metadata.creationTimestamp
```

This can reveal application errors, container crashes, failed image pulls, scheduling problems, and resource shortages. For `CrashLoopBackOff`, previous logs are especially useful because they show what happened before the container restarted.

## 2. Monitoring AKS with Prometheus and Grafana

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

### How it works

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

## 3. Kubernetes Autoscaling

Kubernetes can scale at three levels:

| Autoscaler | What it changes | Typical use |
| --- | --- | --- |
| Horizontal Pod Autoscaler (HPA) | Number of pod replicas | Stateless applications and workers |
| Vertical Pod Autoscaler (VPA) | Pod CPU and memory requests | Workloads that need better resource sizing |
| Cluster Autoscaler | Number of worker nodes | Pods cannot be scheduled because the cluster is full |

The normal scale-up flow is:

```text
Traffic increases
      ↓
HPA creates more pods
      ↓
Pods remain Pending if nodes are full
      ↓
Cluster Autoscaler adds a node
      ↓
The scheduler places the pending pods
```

### Horizontal Pod Autoscaler

HPA adds or removes replicas based on CPU, memory, custom metrics, or external metrics.

```bash
kubectl autoscale deployment web --cpu-percent=70 --min=3 --max=20
```

This keeps CPU use near 70%, with at least 3 and at most 20 replicas.

Custom metrics can include requests per second, latency, and active users. A Prometheus Adapter can expose these metrics to Kubernetes. KEDA is commonly used for event-based scaling from sources such as Service Bus, Kafka, RabbitMQ, and storage queues.

Resource requests must be set correctly because CPU-based HPA compares actual use with the requested CPU. Missing or unrealistic requests can produce poor scaling decisions. Limits provide an upper boundary but are not the basis of this utilization calculation.

### Cluster Autoscaler and Karpenter

The Cluster Autoscaler adds a worker node when pods are pending because no existing node has enough capacity. It can remove underused nodes when their pods can safely run elsewhere.

Karpenter also provisions nodes for pending pods and can choose a suitable node size dynamically. It is commonly associated with AWS. AKS normally uses the Cluster Autoscaler.

### Vertical Pod Autoscaler

VPA recommends or updates CPU and memory requests based on observed usage. Applying an update can require the pod to be recreated. VPA is useful when increasing the size of a pod is more suitable than adding replicas. Avoid letting VPA and HPA control the same CPU or memory signal without careful design.

### Keeping scaling safe

- A readiness probe prevents traffic from reaching a new pod until it is ready.
- A PodDisruptionBudget keeps a minimum number of replicas available during voluntary disruptions such as maintenance.
- Caching reduces repeated work and database calls.
- Queues absorb traffic bursts and let workers process jobs at a controlled rate.

## 4. StatefulSets

A StatefulSet manages applications that need stable identity or persistent storage, such as databases, Kafka, Elasticsearch, and ZooKeeper.

### Main features

- Stable pod names such as `mysql-0`, `mysql-1`, and `mysql-2`
- Predictable DNS names for communication between members
- A separate persistent volume for each pod through `volumeClaimTemplates`
- Ordered creation, scaling, deletion, and rolling updates by default

If `mysql-1` is recreated, it keeps the same identity and reconnects to its own persistent volume. When scaling down, Kubernetes removes the highest-numbered pod first. Its PVC normally remains so that data is not accidentally lost.

### Deployment compared with StatefulSet

| Feature | Deployment | StatefulSet |
| --- | --- | --- |
| Pod identity | Replaceable, usually with random suffixes | Stable ordinal names |
| Storage | Often ephemeral or shared | Usually one persistent volume per pod |
| Start and removal order | Usually parallel or unrestricted | Ordered by default |
| Common workloads | Web applications and APIs | Databases and clustered data systems |

### Challenges and good practices

- Cloud disks may be tied to one availability zone. The pod must run on a node that can attach its disk, so plan zones, topology, and application-level replication.
- Scaling down normally leaves PVCs behind. Review unused PVCs and delete them only after confirming that their data is no longer needed.
- Ordered updates can be slow. Plan upgrades around the application's leader, replication, and quorum rules.
- A persistent volume is not a backup. Use CSI volume snapshots and application-level backup tools, and regularly test restores.
- Moving a pod after node failure requires the disk to detach and attach elsewhere, which can delay recovery.
- Use a suitable StorageClass and CSI driver with dynamic provisioning.
- Prefer a mature Kubernetes operator for complex databases when it can safely manage upgrades, backups, failover, and recovery.

## Short Interview Summary

For pod failures, inspect pod status, description, current and previous logs, and recent events. In AKS monitoring, applications expose metrics, Prometheus discovers and stores them, Grafana displays them, and Alertmanager routes alerts. HPA scales pods, Cluster Autoscaler scales nodes, and VPA adjusts pod resource requests. StatefulSets are used when pods need stable names and their own persistent storage, but they require careful planning for zones, backups, upgrades, and recovery.
