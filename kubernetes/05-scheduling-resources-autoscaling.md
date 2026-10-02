# Kubernetes: Scheduling, Resources, and Autoscaling

> Scheduler, affinity, taints/tolerations, requests and limits, OOMKilled, eviction, PDBs, HA placement, HPA/VPA, Cluster Autoscaler/Karpenter, and cost.

## Key Concepts

### Scheduling

The scheduler filters and scores nodes using:

- Resource requests and allocatable capacity
- Node selectors and node affinity
- Pod affinity and anti-affinity
- Taints and tolerations
- Topology spread constraints
- Volume topology
- Pod priority and preemption

Required anti-affinity can make Pods unschedulable when there are too few eligible nodes or zones. Prefer soft rules when strict separation is not essential and monitor scheduling events.

When a node becomes unreachable, Pods usually receive default `NoExecute` tolerations for `not-ready` and `unreachable` conditions. Per-Pod `tolerationSeconds` can alter how long they remain bound.

Exact behavior depends on cluster configuration and workload type.

### Requests and Limits

- **Request:** Used for scheduling and influences resource guarantees.
- **Limit:** Enforced maximum for memory and a throttling boundary for CPU.

A container exceeding its memory limit can be terminated as `OOMKilled`. During node pressure, QoS class, usage relative to requests, and Pod priority influence eviction.

Existing Pod specifications are generally replaced through their controller when resource settings change. In-place resize availability depends on the Kubernetes version, feature status, and cluster support; do not assume it is universally available.

### Autoscaling

- **HPA:** Changes replica count using resource or custom/external metrics.
- **VPA:** Recommends or updates Pod resource sizing according to its mode.
- **Cluster Autoscaler:** Adds or removes nodes based on unschedulable Pods and utilization rules.

When HPA metrics are unavailable, scaling behavior depends on which metrics fail and available recommendations. Monitor HPA conditions rather than assuming every metrics failure freezes replicas.

### Vertical Scaling vs. Horizontal Scaling

Vertical and horizontal scaling are two ways to give an application more capacity as its workload increases.

| Vertical scaling | Horizontal scaling |
| --- | --- |
| Increases the CPU or memory available to an existing Pod. | Increases the number of Pod replicas. |
| Also called **scale up**. | Also called **scale out**. |
| Makes one Pod more powerful. | Distributes the workload across multiple Pods. |
| Usually replaces or restarts the Pod to apply new resource settings; in-place resizing depends on cluster support. | Creates new Pods without changing the existing replicas. |
| Is limited by the capacity of a single node. | Can use capacity across multiple nodes. |
| Suits applications that cannot run multiple instances easily. | Suits stateless applications such as web servers and APIs. |

Suppose an application starts with one Pod that has one CPU and 2 GB of memory:

- **Vertical scaling:** Increase the Pod from one to four CPUs and from 2 GB to 8 GB of memory. The application still has one Pod, but that Pod has more capacity.
- **Horizontal scaling:** Increase the replica count from one to five while each Pod keeps one CPU and 2 GB of memory. A Kubernetes Service distributes traffic across the ready Pods.

#### Horizontal Pod Autoscaler

The Horizontal Pod Autoscaler (HPA) automatically increases or decreases the number of Pod replicas according to CPU, memory, or custom/external metrics. For example, when CPU utilization rises above a configured target such as 70%, HPA might increase a workload from two Pods to five.

#### Vertical Pod Autoscaler

The Vertical Pod Autoscaler (VPA) recommends or, depending on its mode, applies CPU and memory requests to right-size Pods. For example:

| Resource | Current | Recommended |
| --- | ---: | ---: |
| CPU | `500m` | `1000m` |
| Memory | `512Mi` | `2Gi` |

Applying a VPA recommendation commonly requires Pod replacement, although behavior depends on VPA mode and support for in-place Pod resizing. Avoid using HPA and VPA on the same CPU or memory signal without careful design because their control loops can conflict.

#### Which Approach Is Preferred?

Horizontal scaling is generally preferred for stateless Kubernetes workloads because it:

- Improves availability by keeping multiple replicas.
- Handles Pod or node failures better because other ready Pods can serve traffic.
- Scales beyond the capacity of a single machine.
- Fits stateless microservices naturally.

Vertical scaling is useful when:

- The application cannot be distributed easily across multiple instances, as with some legacy or stateful applications.
- The workload needs more CPU or memory but gains little from additional replicas.

In production, the approaches can complement each other: use VPA recommendations to right-size Pods, HPA to adjust replica count, and a node autoscaler to provide enough cluster capacity.

#### 30-Second Interview Answer

Vertical scaling, or scale up, means increasing the CPU and memory available to a Pod. It improves the capacity of one Pod but is limited by the resources of a node and commonly requires Pod replacement.

Horizontal scaling, or scale out, means increasing the number of Pod replicas. Kubernetes typically uses VPA for vertical scaling and HPA for horizontal scaling.

For stateless production workloads, horizontal scaling is generally preferred because it provides better availability, fault tolerance, and scalability.

### Kubernetes Autoscaling: HPA, VPA, Cluster Autoscaler, and Karpenter

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

#### Horizontal Pod Autoscaler

HPA adds or removes replicas based on CPU, memory, custom metrics, or external metrics.

```bash
kubectl autoscale deployment web --cpu-percent=70 --min=3 --max=20
```

This keeps CPU use near 70%, with at least 3 and at most 20 replicas.

Custom metrics can include requests per second, latency, and active users. A Prometheus Adapter can expose these metrics to Kubernetes. KEDA is commonly used for event-based scaling from sources such as Service Bus, Kafka, RabbitMQ, and storage queues.

Resource requests must be set correctly because CPU-based HPA compares actual use with the requested CPU. Missing or unrealistic requests can produce poor scaling decisions. Limits provide an upper boundary but are not the basis of this utilization calculation.

#### Cluster Autoscaler and Karpenter

The Cluster Autoscaler adds a worker node when pods are pending because no existing node has enough capacity. It can remove underused nodes when their pods can safely run elsewhere.

Karpenter also provisions nodes for pending pods and can choose a suitable node size dynamically. It is commonly associated with AWS. AKS normally uses the Cluster Autoscaler.

#### Vertical Pod Autoscaler

VPA recommends or updates CPU and memory requests based on observed usage. Applying an update can require the pod to be recreated. VPA is useful when increasing the size of a pod is more suitable than adding replicas. Avoid letting VPA and HPA control the same CPU or memory signal without careful design.

#### Keeping scaling safe

- A readiness probe prevents traffic from reaching a new pod until it is ready.
- A PodDisruptionBudget keeps a minimum number of replicas available during voluntary disruptions such as maintenance.
- Caching reduces repeated work and database calls.
- Queues absorb traffic bursts and let workers process jobs at a controlled rate.

### Autoscaling

HPA changes Pod replica count from CPU, memory, or custom/external metrics. VPA recommends or changes Pod resource sizing and may restart Pods.

Cluster Autoscaler or the provider node autoscaler adds/removes worker-node capacity when Pods cannot schedule or nodes are underused.

Metrics Server supplies common resource metrics; production scaling must also validate resource requests, min/max limits, stabilization, dependency capacity, startup time, and safe scale-down.

### Operations Notes

- Readiness controls whether a Pod receives traffic. Liveness restarts a container that's stuck. Startup probes protect applications that take a while to start. HPA scales the number of replicas horizontally. Size requests and limits properly, and handle node-level (cluster/node) autoscaling as a separate concern.

## Interview Questions

<details><summary>Q1. [Intermediate] How does the Kubernetes scheduler decide where to place Pods?</summary>

**Answer:**

The scheduler watches for Pods that haven't been scheduled yet. First it filters out any node that fails a hard requirement: not enough allocatable resources for the requests, a node selector or required affinity that doesn't match, a taint with no matching toleration, a volume topology or binding mismatch, a port conflict, or another plugin rule.

Then it scores the remaining, feasible nodes on preferred affinity, spreading, resource balance, and topology, and binds the Pod to the best one. Kubelet is what actually starts it.

For a Pending Pod, I read the scheduling event first:

```bash
kubectl describe pod <pod>
kubectl get nodes --show-labels
kubectl top nodes
```

I check the requests, taints, selectors and affinity, topology constraints, PVC, quota, node capacity and IPs, and the autoscaler. I fix the actual constraint or add capacity — deleting and recreating an identical Pod doesn't solve a problem that was never going to schedule in the first place.

</details>

<details><summary>Q2. [Advanced] What are common scheduling challenges in a multi-node, multi-AZ setup?</summary>

**Answer:**

The usual challenges are zonal volumes conflicting with where a Pod needs to run, uneven replica distribution, strict anti-affinity rules with too few zones to satisfy them, exhausted subnet IPs or instance quotas in an AZ, taints and node selectors, mixed node architectures, and autoscaler node groups that just can't satisfy the constraints. Cross-zone traffic also adds latency and cost.

I design topology spread across hostname and zone, choosing `ScheduleAnyway` or `DoNotSchedule` depending on how strict the requirement really is. I use `WaitForFirstConsumer` for storage, keep capacity available in each zone, and test what happens if a zone goes down. When investigating, I group the Pending events together and compare eligible nodes, PV zone, subnet IPs, quotas, and autoscaler logs.

The goal isn't perfect spreading at all costs — hard constraints can actually reduce availability if one zone fails, so I choose between strict and preferred rules deliberately.

</details>

<details><summary>Q3. [Intermediate] Suppose I want a pod to be scheduled on a specific node only. How can I achieve this?</summary>

You can control pod scheduling using `nodeSelector`, Node Affinity, or the `nodeName` field:

- **`nodeSelector`:** Add labels to nodes and use `nodeSelector` in the pod spec.
- **Node Affinity:** More flexible, using `requiredDuringSchedulingIgnoredDuringExecution`.
- **`nodeName`:** Directly specify the node name (bypasses the scheduler).

```yaml
spec:
  nodeSelector:
    disktype: ssd
  # OR
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/hostname
            operator: In
            values: ["node-1"]
```

</details>

<details><summary>Q4. [Intermediate] How do you troubleshoot Kubernetes pod scheduling due to taints?</summary>

**Answer:** Run kubectl describe node → Check taints → Add tolerations in pod spec → Or remove taints if not needed.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

</details>

<details><summary>Q5. [Advanced] When using anti-affinity rules, is it possible to create a "deadlock" where no new Pods can be scheduled?</summary>

**Answer:**

Yes, overly restrictive anti-affinity rules can create scheduling deadlocks.

Common deadlock scenarios:

- `requiredDuringSchedulingIgnoredDuringExecution` with insufficient nodes.
- Zone anti-affinity with limited availability zones.
- A combination of multiple affinity rules creating impossible constraints.

Example deadlock:

```yaml
# If you have only 2 nodes and request 3 Pods with this rule
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app: myapp
      topologyKey: kubernetes.io/hostname
```

Solutions:

- Use `preferredDuringSchedulingIgnoredDuringExecution` instead of `required`.
- Ensure adequate node diversity.
- Monitor Pod scheduling events.

</details>

<details><summary>Q6. [Intermediate] How can you ensure high availability for your application deployed in a Kubernetes cluster?</summary>

Implement these strategies:

- **Multiple replicas:** Use a Deployment with `replicas > 1`.
- **Pod Disruption Budgets:** Ensure a minimum number of pods during updates.
- **Anti-affinity rules:** Spread pods across nodes/zones.
- **Health checks:** Configure readiness and liveness probes.
- **Resource limits:** Set appropriate requests and limits.
- **Multi-zone deployment:** Use node affinity for zone distribution.
- **Horizontal Pod Autoscaler:** Scale based on metrics.
- **Rolling updates:** Zero-downtime deployments.

</details>

<details><summary>Q7. [Advanced] How do you build a highly available Kubernetes cluster?</summary>

- **Multiple control plane nodes** - normally 3 or 5 (odd numbers, for etcd quorum).
- **Distribute nodes across Availability Zones** - both control plane and worker nodes, so a single zone failure doesn't take down the cluster.
- **Highly available etcd** - etcd is the cluster's source of truth; losing quorum on it is losing the cluster's ability to make any changes.
- **Multiple application replicas** - so a single Pod or node failure doesn't cause an outage.
- **Readiness and liveness probes** - so traffic only reaches healthy Pods, and unhealthy containers get restarted automatically.
- **Rolling updates** with suitable `maxUnavailable`/`maxSurge` - see "How do `maxSurge` and `maxUnavailable` control a rolling update?" in `07-deployments-upgrades-cicd.md` for the full mechanics.
- **Pod Disruption Budgets (PDBs)** - guarantee a minimum number of replicas stay available during voluntary disruptions like node maintenance.
- **Load Balancer/Ingress** for traffic distribution.
- **HPA and Cluster Autoscaler** - so capacity keeps pace with load.
- **Back up etcd**, and keep the cluster's own definition as infrastructure as code, so the control plane itself is recoverable.

#### If a worker node fails

Kubernetes marks the node `NotReady`, removes its Pods' endpoints from any Services routing to them, and schedules replacement Pods on healthy nodes. Because multiple replicas were already spread across nodes, traffic continues flowing through the surviving replicas while the replacements come up.

#### Short interview answer

HA in Kubernetes is a stack of measures working together: multiple control plane nodes with HA etcd spread across Availability Zones, multiple Pod replicas backed by readiness/liveness probes and PDBs, rolling updates tuned via `maxSurge`/`maxUnavailable`, HPA plus Cluster Autoscaler for capacity, and regular etcd backups. When a worker node fails, Kubernetes marks it `NotReady`, pulls its Pods out of Service endpoints, and reschedules them elsewhere - the surviving replicas keep serving traffic in the meantime.

</details>

<details><summary>Q8. [Basic] How do resource requests and limits work?</summary>

**Answer:**

Requests are what the scheduler uses to place a Pod, and they influence its QoS class. Limits are hard ceilings enforced at runtime. CPU is compressible — going over the limit just throttles it.

Memory isn't compressible — going over the cgroup limit can get the container OOMKilled. A namespace's LimitRange or ResourceQuota can enforce defaults and bounds on top of this.

```yaml
resources:
  requests: { cpu: 250m, memory: 256Mi }
  limits: { cpu: "1", memory: 512Mi }
```

I size these from observed usage percentiles and load tests, plus some headroom — not from guesses. I keep monitoring usage, throttling, OOM events, evictions, latency, and Pending Pods.

VPA can help recommend values. Requests that are too high waste capacity or block scheduling. Memory limits that are too low cause crashes. CPU limits can hurt latency-sensitive workloads. The right policy really depends on the workload.

</details>

<details><summary>Q9. [Basic] What are resource requests and limits, and why are they useful?</summary>

Resource requests and limits control how much CPU and memory a container is expected and allowed to use.

#### Resource requests

A request tells Kubernetes how much CPU or memory a container normally needs. The scheduler uses requests to find a node with enough available capacity.

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
```

In this example:

- `500m` means half of one CPU core.
- `512Mi` means 512 mebibytes of memory.

A request is mainly a scheduling value. It does not stop the container from using more resources when capacity is available.

#### Resource limits

A limit is the maximum amount of a resource that the container may use.

```yaml
resources:
  limits:
    cpu: "1"
    memory: "1Gi"
```

This container can use up to one CPU core and 1 GiB of memory.

- If it tries to use more CPU than its limit, its CPU time is throttled.
- If it exceeds its memory limit, it may be terminated with an `OOMKilled` reason and then restarted according to the pod's restart policy.

#### Complete example

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

This configuration suits an application that normally needs about 0.5 CPU and 512 MiB of memory but occasionally needs more during a traffic spike.

#### Why they are useful

- Help the scheduler place pods on suitable nodes.
- Stop one container from using too many shared resources.
- Reduce resource contention between applications.
- Improve cluster stability and predictable performance.
- Give autoscalers useful resource information.

Requests and limits should be based on measured application usage. Values that are too low can cause throttling, memory failures, or poor scheduling decisions. Values that are too high can waste cluster capacity.

#### Short interview answer

Resource requests describe the CPU and memory a container needs, and the scheduler uses them when selecting a node. Limits define how much the container can use. CPU use above its limit is throttled, while exceeding a memory limit can cause `OOMKilled`. Correct values improve scheduling, stability, and resource sharing.

</details>

<details><summary>Q10. [Basic] How do you set resource limits in Kubernetes?</summary>

**Answer:** Define requests & limits in pod spec → Ensures fair resource allocation and prevents pod from consuming all CPU/memory.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

</details>

<details><summary>Q11. [Intermediate] How do you optimize resource requests and limits for containers in a production cluster?</summary>

Optimizing resource requests and limits is crucial for ensuring efficient resource utilization, preventing resource contention, and maintaining application performance.

1. **Analyze application resource usage:**
   - Monitor the resource usage of your applications using tools like Prometheus, Grafana, or the Kubernetes Metrics Server.
   - Collect data on CPU and memory consumption under different load conditions to understand the resource requirements of your applications.
2. **Set resource requests:**
   - Resource requests define the **minimum** amount of CPU and memory that a container needs to run.
   - Set requests based on the average resource usage observed during monitoring. This ensures that the scheduler can make informed decisions about pod placement.
3. **Set resource limits:**
   - Resource limits define the **maximum** amount of CPU and memory that a container can use.
   - Set limits slightly above the peak usage observed during monitoring to prevent containers from consuming excessive resources and affecting other workloads.
4. **Use Vertical Pod Autoscaler (VPA):**
   - VPA automatically adjusts the resource requests and limits of pods based on their actual usage.
   - Deploy VPA in your cluster to help optimize resource allocation dynamically.
5. **Implement Horizontal Pod Autoscaler (HPA):**
   - HPA scales the number of pod replicas based on resource usage metrics, helping to distribute the load and optimize resource utilization.
6. **Conduct load testing:**
   - Perform load testing to simulate real-world traffic and observe how your applications behave under stress.
   - Use the results to fine-tune resource requests and limits.
7. **Review and adjust regularly:**
   - Regularly review resource usage metrics and adjust requests and limits as needed based on changes in application behavior or workload patterns.
8. **Avoid over-provisioning:**
   - Avoid setting excessively high resource requests and limits, as this can lead to wasted resources and increased costs.
   - Aim for a balance between ensuring application performance and efficient resource utilization.
9. **Use namespaces and resource quotas:**
   - Organize workloads into namespaces and apply resource quotas to limit the total resource consumption for each namespace.
   - This helps prevent any single team or application from consuming all cluster resources.

By following these strategies, you can optimize resource requests and limits for containers in your production Kubernetes cluster, leading to improved performance and cost-efficiency.

</details>

<details><summary>Q12. [Intermediate] Can a Pod's resource requests be modified after creation, and what's the difference between requests and limits during OOM scenarios?</summary>

**Answer:**

**Resource modification:** Resource requests and limits cannot be modified after Pod creation. You must recreate the Pod or use VPA (Vertical Pod Autoscaler) for automatic adjustments.

OOM behavior differences:

- **Requests:** Used for scheduling decisions; guaranteed resources.
- **Limits:** Maximum resources allowed, enforced by the kernel.

During OOM scenarios:

- **Container exceeds limits:** The container is immediately killed (OOMKilled).
- **Node memory pressure:** Pods exceeding requests are candidates for eviction.
- **Priority-based eviction:** Lower priority Pods are evicted first.

```yaml
resources:
  requests:
    memory: "64Mi"     # Guaranteed
    cpu: "250m"
  limits:
    memory: "128Mi"    # Maximum allowed
    cpu: "500m"
```

</details>

<details><summary>Q13. [Intermediate] How do you fix OOMKilled Pods?</summary>

**Answer:**

First I confirm it's really OOMKilled: `lastState.terminated.reason: OOMKilled`, exit code 137, the events, memory metrics, and whether it's node pressure or a container-limit issue. I compare against recent traffic, releases, and config changes, and look at heap or native memory use, caching, concurrency, payload size, and possible leaks.

For an immediate, safe fix, I might roll back, reduce traffic or concurrency, scale out replicas, or raise the limit — only within what the node can actually support and only with evidence behind it. For a JVM app, I make sure the heap size leaves room for native memory inside the container limit.

The permanent fix removes the leak or the unbounded cache, or right-sizes the resources properly.

I update requests and limits through the controller, load-test the change, and keep watching working set, RSS, GC, OOM events, and node headroom, with alerts in place. Just raising the memory limit without finding the root cause can just move the failure to the node level or raise cost.

</details>

<details><summary>Q14. [Intermediate] How do you troubleshoot “OOMKilled” pods in Kubernetes?</summary>

**Answer:** Pod exceeded memory → Check logs/events → Increase memory limit → Optimize app memory usage → Use HPA to spread load.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

</details>

<details><summary>Q15. [Intermediate] How do you troubleshoot OOMKilled Pods step by step?</summary>

An `OOMKilled` status means the container used more memory than its configured limit, so the Linux kernel killed the process to protect the node.

#### 1. Confirm the reason

```bash
kubectl describe pod <pod-name>
```

Check the Events section for `Reason: OOMKilled`, and note the exit code (`137`, which is `128 + SIGKILL`).

#### 2. Check current memory usage

```bash
kubectl top pod <pod-name>
kubectl top node
```

This shows whether the container is genuinely near its limit, and whether the node itself is under memory pressure.

#### 3. Review resource requests and limits

```yaml
resources:
  requests:
    memory: 512Mi
  limits:
    memory: 1Gi
```

Confirm the limit is actually appropriate for the workload rather than an arbitrary guess - see [§1](#1-resource-requests-and-limits-in-kubernetes) above.

#### 4. Check the application itself

- Look for memory leaks.
- Check whether a recent deployment increased memory usage (new dependency, new caching behavior, a changed batch size).
- Review logs from the crashed container specifically:

```bash
kubectl logs <pod-name> --previous
```

#### 5. Monitor memory over time

Use Prometheus and Grafana to see whether memory grows steadily (a leak) or spikes under specific traffic (a genuine capacity issue) - see "Monitoring AKS with Prometheus and Grafana" in [monitoring-tools/06-kubernetes-monitoring.md](../monitoring-tools/06-kubernetes-monitoring.md).

#### 6. Decide: raise the limit, or fix the application

If traffic-driven memory growth is expected and legitimate, consider a Horizontal Pod Autoscaler so load is spread across more replicas instead of concentrated in one container. If a Java application has a 512Mi limit but needs 700Mi at peak, confirm the usage is genuine load (not a leak) before simply raising the limit.

#### Short interview answer

I'd confirm the OOMKilled event and exit code with `kubectl describe pod`, check current memory pressure with `kubectl top`, and review the configured requests/limits. Then I'd check the application for a memory leak or a recent change that increased memory use, using `kubectl logs --previous` for the crashed container. I'd monitor memory over time with Prometheus/Grafana to distinguish a leak from genuine load, and either raise the limit (if justified) or fix the application - adding HPA if the growth is traffic-driven.

</details>

<details><summary>Q16. [Advanced] You have a memory leak in one of your microservices and the pod keeps getting OOMKilled. Walk me through how you would diagnose and fix it without taking down your production service.</summary>

**Answer:**

This is a scenario question — the interviewer wants to see how you think under pressure, not just whether you know the commands.

First, understand the scope of impact. How many replicas are running, and what is the traffic impact of one pod being killed?

Five replicas with one OOMKilled every 30 minutes gives you time to investigate. Two replicas both getting OOMKilled is an active incident, and investigation comes second.

Assuming you have time, the investigation path:

```bash
kubectl top pods                 # current memory consumption across pods
kubectl describe pod <pod>       # check Last State -> exit code 137 = OOMKilled
```

Now determine whether this is a real memory leak or just a limit set too low — two different problems with different fixes. Look at Prometheus, specifically `container_memory_working_set_bytes` over time:

- **Memory grows continuously with no plateau** → a leak.
- **Memory is stable but just above your limit** → the limit is wrong.

If it is a real leak, that is ultimately a developer problem.

Your job as a DevOps engineer is to buy the team time without an outage: temporarily raise the memory limit to stop the OOMKills, set an alert at 80% of the new limit so you know when it is approaching again, and give developers the metrics they need to find the leak.
If the limit was simply too low, right-size it — look at actual peak memory usage from Prometheus over the last 30 days and set the limit to something reasonable above that.

The part most people miss: make sure it does not happen again silently. Set a Prometheus alert on `OOMKilled` events so you are notified immediately next time, and consider whether the Vertical Pod Autoscaler can right-size requests and limits automatically over time.

The interviewer is checking whether you think in systems, not just commands — anyone can Google the `kubectl` commands; not everyone thinks about the alert that catches the next incident before it becomes an outage.

</details>

<details><summary>Q17. [Intermediate] CrashLoopBackOff Caused by OOMKilled</summary>

#### What the describe output shows

```text
Last State:     Terminated
Reason:         OOMKilled
Exit Code:      137
```

#### What this means

`OOMKilled` means the container tried to use more memory than its configured `resources.limits.memory`, so the kernel killed it. Kubernetes then restarts it, it hits the same memory limit again, and gets killed again — that's the crash loop. Exit code 137 = 128 + 9 (SIGKILL), confirming it was force-killed, not a normal app crash.

#### What to check next

```bash
kubectl top pod payment-api        # actual memory usage vs limit
kubectl describe pod payment-api   # confirm limits and OOM events
kubectl logs payment-api --previous
```

Then decide:

- Is the limit just too low for normal usage? → Increase `resources.limits.memory`.
- Is the app leaking memory over time? → Fix the leak; increasing the limit only delays the crash.
- Did traffic or batch size spike? → Consider HPA or reducing per-request memory use.

#### Short interview answer

"OOMKilled with exit code 137 means the container exceeded its memory limit and the kernel killed it, which causes the restart loop. I'd check actual memory usage with `kubectl top pod` versus the configured limit, look at the app logs for signs of a memory leak, and either raise the memory limit if it's genuinely under-provisioned or fix the leak if usage keeps climbing over time."

</details>

<details><summary>Q18. [Intermediate] How do you detect &amp; fix Kubernetes resource leaks?</summary>

**Answer:** Monitor unused PVCs, ConfigMaps, Secrets → Use cleanup jobs → Apply resource quotas.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

</details>

<details><summary>Q19. [Intermediate] What if Kubernetes cluster nodes are running out of resources?</summary>

**Answer:** Check node metrics → Add more nodes (cluster autoscaler) → Tune resource requests/limits → Reschedule pods across nodes.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

</details>

<details><summary>Q20. [Basic] What is a PodDisruptionBudget and why is it useful?</summary>

**Answer:**

A PodDisruptionBudget, or PDB, limits how many **voluntary** disruptions can happen at once to a set of Pods, using `minAvailable` or `maxUnavailable`. The eviction API used by node drains and the cluster autoscaler respects it.

It doesn't protect against crashes, node loss, OOM kills, or application failures, and it doesn't create replicas either.

For a three-replica API, `minAvailable: 2` allows exactly one voluntary eviction at a time. I make sure the selector is correct, replicas are actually spread across nodes and zones, readiness is accurate, and the budget still allows maintenance to happen — an impossible PDB can block node drains and upgrades entirely.

When a drain is stuck, I check `kubectl get pdb`, the current healthy and desired counts, allowed disruptions, unavailable Pods, and the controller's replica count. I fix the underlying health or capacity issue, or make a deliberate, approved risk decision — I don't just bypass a production safeguard casually.

</details>

<details><summary>Q21. [Advanced] What is a PodDisruptionBudget, and when does ignoring it cause a real production outage?</summary>

**Answer:**

Most candidates have heard of PodDisruptionBudget (PDB); few understand what happens when it is missing.

Suppose you run a three-replica deployment of your payment service, and the cluster needs node maintenance — Karpenter consolidating underutilized nodes, or a team upgrading the EKS node group. Kubernetes starts draining nodes one by one.

Without a PDB, Kubernetes can evict all three payment-service pods at the same time if they all happened to sit on nodes being drained. Within seconds the service has zero running pods and is completely down.

This is not a failure — it is Kubernetes doing exactly what you asked, because you never told it any limits.

A PDB lets you declare the minimum number of pods that must stay running during voluntary disruptions:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: payment-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: payment
```

With `minAvailable: 2`, Kubernetes can only evict one payment pod at a time. It drains the node, waits for that pod to be rescheduled and healthy elsewhere, then proceeds to the next node.

The keyword is **voluntary disruptions** — node drains, cluster upgrades, Karpenter consolidation. A PDB does **not** protect you from a node crashing or a pod being OOMKilled; that is a different problem.

I have seen this play out: a team upgrading their EKS node group with no PDBs sent three critical services to zero pods simultaneously during the drain. Even in a 2am maintenance window it caused a 20-minute outage, because nobody had defined the minimum acceptable state during disruption.

That specific scenario is what PDB is for.

</details>

<details><summary>Q22. [Intermediate] A critical Pod gets evicted due to node pressure. How do you prevent it from happening again?</summary>

**Answer:**

First I confirm the eviction reason from the Pod's status and events: memory, disk, inodes, PIDs, ephemeral storage, or a taint. I check the node's conditions, the kubelet's eviction messages, top and metrics data, and whether the filesystem, runtime, or logs are growing, along with what other Pods are doing.

I set measured requests, appropriate limits including ephemeral storage, log rotation, and cleanup. I also add capacity or autoscaling and spread replicas out. Critical workloads can deliberately use a PriorityClass and a Guaranteed or Burstable QoS class, but keep in mind priority can evict other workloads — it's not extra capacity.

A PDB doesn't stop this kind of eviction, because node pressure is involuntary, not voluntary.

I fix the source of the pressure, replace the node if it's unhealthy, confirm rescheduling and SLOs recover, and add alerts on capacity and growth forecasts. Changing kubelet's eviction thresholds is a last resort, tested platform decision — not a way to hide the fact that there isn't enough capacity.

</details>

<details><summary>Q23. [Intermediate] How do you handle pod eviction in Kubernetes?</summary>

**Answer:** Check node pressure (CPU/memory/disk) → Reschedule pods to healthy nodes → Use PodDisruptionBudgets to protect critical pods.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

</details>

<details><summary>Q24. [Intermediate] When a node becomes <code>NotReady</code>, how long does it take for Pods to be evicted, and can this be controlled per Pod?</summary>

**Answer:**

By default, Pods are evicted after 5 minutes (300 seconds) when a node becomes `NotReady`. This is controlled by the `--pod-eviction-timeout` flag on the kube-controller-manager.

Per-Pod control options:

- **Toleration with `tolerationSeconds`:** Control how long a Pod tolerates node conditions.
- **PodDisruptionBudgets:** Limit how many Pods can be evicted simultaneously.
- **Priority and preemption:** Higher priority Pods evict lower priority ones first.

Example toleration:

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 60  # Evict after 60 seconds instead of 300
```

</details>

<details><summary>Q25. [Basic] What is the difference between vertical and horizontal scaling in Kubernetes?</summary>

| Vertical scaling | Horizontal scaling |
| --- | --- |
| Gives a pod more CPU or memory | Adds more pod replicas |
| Also called scaling up | Also called scaling out |
| Makes one pod more powerful | Shares work across several pods |
| Often requires pod recreation | Adds new pods while current pods keep running |
| Limited by the size of a node | Can spread replicas across nodes |
| Useful for workloads that cannot use replicas | Usually best for stateless APIs and web applications |

#### Example

An application starts with one pod using one CPU and 2 GB of memory.

Vertical scaling changes it to one larger pod:

```text
1 CPU → 4 CPUs
2 GB  → 8 GB
```

Horizontal scaling keeps the same pod size but increases the count:

```text
1 pod → 5 pods
```

A Kubernetes Service distributes traffic across the ready replicas.

#### HPA and VPA

The Horizontal Pod Autoscaler (HPA) changes the number of replicas based on CPU, memory, custom, or external metrics.

The Vertical Pod Autoscaler (VPA) recommends or updates pod CPU and memory requests. Applying an update can require the pod to be recreated.

Horizontal scaling is usually preferred for stateless services because it improves availability and can grow beyond one node. Vertical scaling is useful for legacy, stateful, or single-instance applications that cannot easily share work across replicas.

#### Short interview answer

Vertical scaling gives an existing pod more CPU or memory and is limited by node capacity. Horizontal scaling adds more replicas and normally uses HPA. Horizontal scaling is often preferred for stateless services because it provides better availability and fault tolerance, while VPA is useful when a workload benefits from a larger pod.

</details>

<details><summary>Q26. [Intermediate] How do you implement autoscaling when traffic fluctuates heavily in Kubernetes?</summary>

To implement autoscaling when traffic fluctuates heavily, you can use the **Horizontal Pod Autoscaler (HPA)** and **Cluster Autoscaler**.

**1. Horizontal Pod Autoscaler (HPA):**

HPA automatically scales the number of pod replicas based on observed CPU utilization or other selected metrics.

```bash
kubectl autoscale deployment <deployment-name> --min=2 --max=10 --cpu-percent=50
```

Replace `<deployment-name>` with the name of your deployment. This command sets the minimum number of replicas to 2, the maximum to 10, and targets 50% CPU utilization.

You can also define HPA in a YAML manifest:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```

Apply the YAML manifest using:

```bash
kubectl apply -f hpa.yaml
```

**2. Cluster Autoscaler:**

The Cluster Autoscaler automatically adjusts the size of the Kubernetes cluster by adding or removing nodes based on the resource requests of the pods.

To set up Cluster Autoscaler in AKS, enable it through the Azure portal or use the Azure CLI:

```bash
az aks update \
  --resource-group <resource-group> \
  --name <aks-cluster-name> \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5
```

Replace `<resource-group>` and `<aks-cluster-name>` with your actual resource group and AKS cluster name.

**3. Monitor autoscaling:**

- Use `kubectl get hpa` to monitor the status of your Horizontal Pod Autoscaler.
- Use Azure Monitor or the Kubernetes dashboard to keep an eye on cluster resource usage and scaling activities.

**4. Test autoscaling:**

Simulate traffic spikes to test the autoscaling behavior and ensure that your application can handle increased load effectively.

By implementing HPA and Cluster Autoscaler, you can ensure that your Kubernetes cluster scales efficiently in response to fluctuating traffic demands.

</details>

<details><summary>Q27. [Advanced] HPA cannot scale Pods fast enough during a massive traffic surge. How do you handle it?</summary>

**Answer:**

First, I protect the users: rate limiting or load shedding, caching, pushing work onto a queue, rolling back an inefficient release, and manually raising replicas if it's safe and there's capacity. Then I check the HPA's conditions and current metric, how delayed that metric is, `maxReplicas`, the requests, Pod startup and readiness, Pending events, the node autoscaler, and any downstream bottleneck.

To prevent it next time, I raise the minimum replica count for headroom against sudden traffic, plan ahead for known peaks, and switch to a leading metric like queue depth or request concurrency through HPA or KEDA instead of a lagging one like CPU. I also tune the scale-up policy, optimize image pull and startup time, pre-provision nodes or use Karpenter, and make sure the database and cache can actually scale with it.

I load-test the burst scenario and measure detection time, Pod Ready time, node provisioning time, error rate, latency, and cost. Adding more Pods can't fix a shared dependency that's already saturated.

</details>

<details><summary>Q28. [Advanced] When using a Horizontal Pod Autoscaler with custom metrics, what happens if the metrics server becomes unavailable during high load?</summary>

**Answer:**

When the metrics server becomes unavailable, the HPA enters a degraded state.

Behavior during metrics unavailability:

- HPA stops making scaling decisions.
- The current replica count is maintained.
- No scale-up occurs even during high load.
- Events show "unable to get metrics" errors.

Recovery behavior:

- Once metrics are available again, HPA resumes normal operation.
- It may trigger rapid scaling based on accumulated load.
- Consider using multiple metrics sources for redundancy.

Monitoring considerations:

```bash
kubectl get hpa
kubectl describe hpa myapp-hpa
```

Best practices:

- Monitor metrics server health.
- Set up alerts for HPA failures.
- Consider backup scaling strategies (manual intervention procedures).

</details>

<details><summary>Q29. [Intermediate] What do you do if a Pod is getting heavy load and must remain healthy?</summary>

**Answer:**

I confirm request rate, latency, error rate, CPU, memory, concurrency, and how saturated any downstream dependency is. For an immediate fix, I scale out replicas if the workload is stateless and there's capacity, rate limit or load shed, cache, push work onto a queue, shift traffic, or roll back an inefficient change.

I also make sure readiness and graceful termination are working and the node autoscaler has capacity to add.

Longer term, I put the HPA on a metric that actually reflects load, set a minimum for headroom, cap the maximum based on what dependencies can handle, optimize startup time and image size, size requests and limits from load tests, use a PDB and spreading, and add connection pooling and a retry budget. KEDA works well for queue-based scaling.

I also optimize the code, database, or cache directly, since scaling horizontally can just amplify a bottleneck instead of fixing it.

I load-test both the traffic surge and a node failure, and measure HPA detection time, Pod and node Ready time, P95 latency, error rate, and cost. Alerts should fire before saturation actually becomes a problem, not after.

</details>

<details><summary>Q30. [Intermediate] A pod is under heavy load — keep it healthy before it dies (auto-scaling) <em>(asked in interview round)</em></summary>

- Use the Horizontal Pod Autoscaler (HPA) to add or remove replicas based on CPU, memory, or custom/external metrics — for example requests-per-second through the Prometheus Adapter, or KEDA for event-driven scaling.
  ```bash
  kubectl autoscale deployment web --cpu-percent=70 --min=3 --max=20
  ```
- Set proper resource requests and limits so the scheduler and HPA make good decisions.
- Use the Cluster Autoscaler or Karpenter to add nodes when pods can't be scheduled.
- Use readiness probes together with a PodDisruptionBudget to keep enough healthy replicas during scaling and rollouts.
- Use the VPA to right-size single-instance workloads, and add caching or queues to reduce load.

</details>

<details><summary>Q31. [Intermediate] Your cluster autoscaler is not scaling up even though Pods are Pending. What do you investigate?</summary>

**Answer:**

The Cluster Autoscaler only scales up if a Pending Pod could actually schedule on a new node from a managed node group. So I check the Pod's `FailedScheduling` event and the autoscaler's own logs and status.

Common causes are a node group already at its max size, a cloud quota or capacity limit, exhausted subnet IPs, requests bigger than any available node, a selector, affinity, or taint mismatch, a zonal PV or topology constraint, an unsupported architecture or missing GPU, an unrecognized node group, or an IAM or API failure.

I work out whether any available node template would actually satisfy the Pod. Then I fix the real constraint, config, or capacity issue — I don't just raise the max node count blindly. After the fix, I measure the time from Pending to node provisioning, to node Ready, to Pod Ready, and I check that scale-down still respects safety, PDBs, and cost.

A PDB mainly affects scale-down, not the initial scale-up. HPA also needs realistic requests, and the node autoscaler needs to respond fast enough for the actual demand.

</details>

<details><summary>Q32. [Advanced] Explain how Karpenter is different from Cluster Autoscaler. In 2026, why would you still choose Cluster Autoscaler?</summary>

**Answer:**

Most candidates know Karpenter is newer and faster; few can explain the architectural difference and when Cluster Autoscaler is still the right choice.

**Cluster Autoscaler** works with your existing node groups. If you have a node group of `m5.xlarge` instances, then when pods are pending for lack of capacity, it adds another `m5.xlarge` to that group.

It can only add node types you have already configured. That means you must predict your workload in advance — a machine learning job that suddenly needs GPU cannot get a `p3.2xlarge` unless a node group with that type already exists; otherwise the pod stays `Pending`.

**Karpenter** watches pending pods and reads their requirements directly — CPU, memory, GPU, architecture, spot or on-demand — then calls the AWS EC2 API to provision the exact right instance type. No predefined node groups, no waiting for a group to scale, and a node in under 60 seconds in most cases.

Karpenter also does **consolidation**: when the cluster is underutilized it actively moves workloads off nodes it can terminate, so you are not paying for half-empty nodes idling at 3am.

So why still use Cluster Autoscaler in 2026?

- **You are not on EKS.** Karpenter's strongest support is on AWS; on GKE or AKS, Cluster Autoscaler is still the more mature, battle-tested option.
- **Compliance and predictability.** Some regulated industries must know exactly which instance types run their workloads. A banking client restricted to approved, audited instance types cannot let Karpenter decide dynamically — they need a controlled, predefined node group managed by Cluster Autoscaler.
- **Migration risk.** On a large existing cluster with complex node-group configuration, migrating to Karpenter is not zero risk. Many teams keep Cluster Autoscaler in production and run Karpenter experiments in lower environments first.

The strong answer shows you understand both tools and can make a context-based decision — not just "Karpenter is newer so it must be better."

</details>

<details><summary>Q33. [Intermediate] How do you troubleshoot Azure Kubernetes Service (AKS) scaling issues?</summary>

**Answer:** Check cluster autoscaler logs → Verify VM quotas in Azure → Ensure correct resource requests/limits.

**Detailed interview approach:**
First I decide whether the demand actually needs more Pods, bigger Pods, or more nodes. I look at request rate, latency, CPU and memory, throttling, Pending Pods, and dependency limits.

HPA needs realistic resource requests or application metrics, and tested min/max and stabilization settings. The node autoscaler supplies capacity for whatever's unschedulable.

For an immediate incident, I might safely scale with `kubectl scale deployment <name> --replicas=<n>` while I investigate the actual traffic or performance cause.

I verify readiness, load distribution, scaling events, dependency health, a graceful scale-down, and cost. Load tests and capacity alerts are what prove the whole path works before the next real peak.

</details>

<details><summary>Q34. [Intermediate] How do you optimize Kubernetes cluster costs?</summary>

**Answer:** Use Cluster Autoscaler, rightsizing pods with requests/limits, spot/preemptible nodes, and scale workloads by time of day.

**Detailed interview approach:**
I compare cost by service, account or subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the increase comes from real traffic, runaway autoscaling, orphaned resources, log or egress volume, a pricing or commitment change, or even compromised compute.

I contain it safely with budgets, scaling caps, quotas, or shutting down confirmed non-production waste — never by blindly deleting stateful production resources. Terraform plans get cost estimates and require policy or approval above certain thresholds.

Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved or spot instance choices, and owner showback are what make cost optimization an ongoing habit rather than a one-time cleanup. I always verify performance and SLOs are still fine after reducing cost.

</details>
