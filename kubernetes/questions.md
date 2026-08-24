## 1. Explain Kubernetes architecture.

**Answer:**

Kubernetes has two parts: a control plane and worker nodes. The API server is the front door. It authenticates requests, checks permissions, validates the data, and exposes the cluster API.

etcd stores the desired and current state of the cluster.

The scheduler picks a node for each new Pod. The controller managers continuously reconcile objects like Deployments and Nodes — that means they keep checking the actual state and pushing it back toward the desired state.

On each worker node, kubelet watches the Pods assigned to it and tells a container runtime, such as containerd, to run them. A CNI plugin handles Pod networking. Service routing is handled by kube-proxy or, in newer setups, an eBPF data plane.

Here's the flow end to end. You run `kubectl apply`, which sends the desired state to the API server. The API server saves that state. The Deployment controller creates a ReplicaSet and Pods. The scheduler binds the Pods to nodes. Kubelet runs them. The controllers keep reconciling in the background.

In a managed service like EKS or AKS, the cloud provider runs the control plane for you. You still own the nodes, the workloads, and the configuration, and you still have to design for high availability yourself.

## 2. What are the roles of kubelet, kube-apiserver, and kube-proxy in EKS?

**Answer:**

In EKS, AWS runs the highly available API server for you. It's the front door for every request, and it handles authentication, authorization, admission, and validation.

Kubelet runs on each worker node. It registers the node, reports its status, and makes sure the containers in its assigned Pods match their specs by talking to the container runtime. Kube-proxy sets up the networking rules that translate a Service's stable virtual IP into the actual Pod IPs behind it. Some CNI or eBPF setups replace this function.

If the API server becomes unreachable, existing containers usually keep running. But scheduling, exec and log access, status updates, and controller actions all degrade.

When I troubleshoot this, I check node status, the kubelet journal, EKS control-plane logs, security groups, routes, DNS, certificate and IAM authentication, and the health of CNI and kube-proxy.

I cordon an unstable node before doing any corrective work on it.

## 3. What are Pods, Deployments, and Services?

**Answer:**

A Pod is the smallest schedulable unit in Kubernetes. It holds one or more tightly coupled containers that share the same IP address, port space, and any declared volumes.

A Deployment declares a stateless Pod template and a replica count. It manages ReplicaSets underneath, which gives you self-healing, rolling updates, and rollback.

A Service selects Pods by label and gives them a stable DNS name and IP, even though the Pods themselves come and go and their addresses change.

For example, say three API Pods are controlled by a Deployment, and a ClusterIP Service called `orders-api` selects the label `app: orders`. Clients call the Service's DNS name, and EndpointSlices keep track of which Pods are currently ready.

During a rollout, the Deployment creates new Pods, readiness gates when they start receiving traffic through the Service, and the old Pods terminate gradually.

I verify all of this with `kubectl get deploy,rs,pods,svc,endpointslice`, rollout status, events, and a test request from a debug Pod.

## 4. What is a ConfigMap and what is a Secret?

**Answer:**

A ConfigMap stores non-sensitive configuration — key/value pairs or whole files. A Secret stores sensitive data, but by default it's only base64-encoded, not encrypted — encoding is not the same as encryption. Both can be exposed to a Pod as environment variables or as mounted volumes.

I keep the application image immutable, meaning it doesn't change after it's built, and separate from the environment configuration. I never put passwords in ConfigMaps or in Git. Production secrets come from a system like Vault, AWS Secrets Manager, or Azure Key Vault, using workload identity and tools like External Secrets or a Secrets Store CSI driver where possible.

I also turn on encryption at rest, use least-privilege RBAC, meaning roles that grant only the access someone actually needs, enable audit logging, rotate credentials, and isolate secrets by namespace.

Updating an environment variable requires the Pod to be recreated. A mounted, projected file may refresh on its own, but the application still has to reread it. When troubleshooting, I check the object and key names, the namespace, the volume or event, permissions, the rendered value without printing the secret itself, and whether consumers of the value have been rolled out.

## 5. What is a ReplicaSet and how does it ensure the desired Pod count?

**Answer:**

A ReplicaSet is defined by a label selector, a Pod template, and a desired replica count. Its controller compares the number of matching, active Pods against that desired count. Too few, and it creates more. Too many, and it deletes the extras.

It keeps reconciling continuously, so if you delete one Pod it manages, a replacement shows up.

In practice I create a Deployment rather than a ReplicaSet directly, because a Deployment adds versioned rollout and rollback and manages multiple ReplicaSets underneath. If replicas aren't appearing, I check the Deployment and ReplicaSet conditions, events, whether the selector matches the template labels, quota, admission, and scheduling:
```bash
kubectl describe deploy api
kubectl describe rs <name>
kubectl get events --sort-by=.metadata.creationTimestamp
```

A correct replica count only proves the Pods exist — not that the application is actually ready. I still have to check readiness and the Service endpoints separately.

## 6. What is the difference between ReplicaSet, Deployment, StatefulSet, and DaemonSet?

**Answer:**

- A ReplicaSet keeps N interchangeable, matching Pods running.
- A Deployment manages ReplicaSets to give you stateless rolling updates and rollback.
- A StatefulSet gives replicas a stable ordinal name and DNS entry, usually one PVC per Pod, and ordered behavior.
- A DaemonSet runs one Pod per eligible node — typically used for CNI, log collection, metrics, security, or storage agents.

I choose based on identity and lifecycle, not just on whether the workload has data. A stateless API uses a Deployment. A database that needs `db-0` and its own volume might use a StatefulSet, though a managed database service is often the better call. A node-level log collector uses a DaemonSet.

Whatever I pick, it still needs probes, resource limits, security settings, monitoring, and a disruption plan. To verify it's working, I look at the controller's conditions, the desired/current/ready counts, events, and how the workload actually behaves.

## 7. What is the difference between a Deployment and a StatefulSet?

**Answer:**

Deployment Pods are interchangeable. They get randomly generated names, support flexible parallel rolling updates, and are the right choice for stateless services.

StatefulSet Pods have a stable, ordinal identity, like `db-0`. They get stable DNS through a headless Service, they're created and deleted in order by default, and `volumeClaimTemplates` keeps one PVC tied to each ordinal.

If you delete `db-1`, Kubernetes recreates `db-1` — the other Pods don't get renamed, and its PVC normally stays intact. A StatefulSet by itself doesn't make an application highly available or replicate its data. The database itself still has to handle quorum, replication, and backup.

Before I use a StatefulSet, I check the storage topology, the Pod management and update strategy, failover behavior, backups, and disruption handling. A managed database can reduce a lot of that operational risk.

## 8. When should you use a StatefulSet instead of a Deployment?

**Answer:**

I reach for a StatefulSet when the workload needs a stable member identity, stable per-replica storage, predictable DNS, or an ordered lifecycle. Examples are ZooKeeper, Kafka, or a database cluster where membership depends on ordinal position.

Before choosing it, I ask a few questions. Can replicas be swapped out interchangeably? Does each one need its own volume? Who's responsible for replication, leader election, backup, repair, and upgrades? Would a managed service or operator be safer?

I test what happens when a Pod is deleted or rescheduled, when a zone fails and storage has to reattach, an ordered rollout, scaling up and down, backup and restore, and losing quorum. If the application's state actually lives outside the Pods and the Pods are interchangeable, a Deployment is simpler — even if those Pods mount shared, read-only data.

## 9. Can you attach a volume to a Deployment? How is it different from a StatefulSet?

**Answer:**

Yes. A Deployment's Pod template can mount ConfigMap, Secret, ephemeral, host, or persistent volumes.

Having multiple replicas reference the same PVC only works if the storage's access mode and backend actually support that kind of concurrent access. A typical block disk with ReadWriteOnce access can't be mounted read-write from multiple nodes at once.

A StatefulSet's `volumeClaimTemplates`, on the other hand, creates a predictable PVC per ordinal — something like `data-db-0` — and that PVC stays tied to the Pod even when it's replaced. That's what gives each member its own disk with a stable identity.

I check the PVC and PV access mode, the StorageClass, the reclaim policy, topology, mount events, CSI logs, and the application's own concurrency assumptions. For stateless applications, I try to keep persistent state outside the Pods entirely.

If you need shared content, use a storage backend that's actually built for multiple writers — don't assume switching to a Deployment changes the underlying storage rules.

## 10. What could cause a StatefulSet Pod to fail when rescheduled to a different availability zone?

**Answer:**

Cloud block volumes like EBS are tied to a single availability zone. The PV carries that zone's node affinity, so a Pod scheduled in a different zone simply can't attach it.

Other causes include a stale VolumeAttachment, a multi-attach lock, not enough capacity in the zone, a CSI failure, node affinity or taints, or lost permissions.

I check the Pod's events, the PVC and PV, the PV's node affinity, the StorageClass binding mode, the VolumeAttachment, CSI controller and node logs, and the node's zone labels. `WaitForFirstConsumer` helps prevent new claims from being provisioned in the wrong zone in the first place.

For data that already exists, I schedule the Pod back in the volume's zone, restore or replicate it to supported storage, or move to a storage architecture actually designed for multi-zone availability. I don't edit the PV's affinity blindly — the physical location of the storage doesn't move just because I changed a field.

## 11. How do PV and PVC behave across zones in EKS or Kubernetes in general?

**Answer:**

A PVC is a namespaced request for storage. A PV is the actual cluster storage object it binds to. Dynamic provisioning uses a StorageClass to create that PV automatically.

With EBS, the disk and its PV are tied to one availability zone, so the Pod has to be scheduled there too. Setting `volumeBindingMode: WaitForFirstConsumer` delays provisioning and binding until the scheduler already knows where the Pod will land.

I only configure allowed topologies when it's actually required, and I spread StatefulSet replicas using topology rules while making sure each volume stays reachable from wherever its Pod lands. When a PVC is stuck Pending, I check the StorageClass and whether there's a default one, capacity, access mode, the CSI provisioner, quota, events, and topology.

If the Pod is Pending after the PVC is already bound, I check the PV's node affinity against the nodes that are actually eligible.

Multi-AZ availability for an application needs replicated application data or storage designed for that — not a single zonal disk that somehow spans zones on its own.

## 12. What happens when a StatefulSet Pod cannot mount its volume after moving to another node?

**Answer:**

The Pod may sit in Pending or ContainerCreating with an error like `FailedAttachVolume`, `Multi-Attach`, `FailedMount`, a timeout, or a filesystem error. I preserve the events and check:

```bash
kubectl describe pod <pod>
kubectl get pvc,pv
kubectl describe pv <pv>
kubectl get volumeattachment
kubectl logs -n kube-system <csi-controller-pod>
```

I compare the node's zone against the PV's zone, confirm the old node actually detached, check CSI health, the cloud disk's state, IAM, the mount path and filesystem, and node capacity.

The fix might be rescheduling to the correct zone, carefully recovering a failed detach, restarting or replacing a CSI or node component once I have evidence it's the cause, or restoring the data.

Once it mounts, I check the filesystem and application data and keep monitoring — I don't just consider the job done because the Pod shows Running.

## 13. What is a DaemonSet and when would you use it?

**Answer:**

A DaemonSet makes sure one Pod runs on every eligible node, based on labels, affinity, and tolerations. When a node joins the cluster, it gets a Pod. When a node leaves, that Pod goes with it.

Typical uses are Fluent Bit, node-exporter, a CNI or CSI node plugin, a security agent, or anything that needs host networking or storage access.

Because this Pod runs on every node, I always set resource requests and limits for it, restrict hostPath and privileged access, choose the right tolerations, and pick a sensible `maxUnavailable` for updates. A broken DaemonSet can affect the whole cluster at once.

I check the desired, current, ready, and misscheduled counts, events, per-node coverage, logs, and the node-level resource impact. Control-plane nodes need explicit toleration and compatibility — I don't assume every DaemonSet should run there.

## 14. If you want two Pods per node instead of one, what alternatives to DaemonSet can you use?

**Answer:**

A single DaemonSet only ever creates one Pod per eligible node. If you genuinely need two independent agents, running two separate DaemonSets is the clearest way to do it.

A Deployment with replicas set to twice the number of eligible nodes, combined with topology spreading, can aim for an even distribution — but it doesn't actually guarantee exactly two Pods per node as nodes come and go.

Before building either, I ask why two are needed. If it's about throughput, one multi-threaded agent might solve it better. If it's about redundancy, a Deployment might be the answer instead. I define `topologySpreadConstraints` by hostname, account for capacity, anti-affinity, and autoscaler behavior, and then test adding, removing, and failing nodes.

The scheduling policy should express the actual requirement, not lean on a replica-count formula that goes stale the moment the cluster changes shape.

## 15. What is the difference between a Kubernetes Job and CronJob?

**Answer:**

A Job runs a one-off task until it reaches the required number of successful completions. It supports parallelism and a `backoffLimit` for retries. A CronJob creates Jobs on a schedule, and adds a `concurrencyPolicy`, a starting deadline, the ability to suspend, and history limits.

For a backup CronJob, I set `concurrencyPolicy: Forbid` so runs don't overlap, pick the right timezone and schedule, set an active deadline and resource requests, and alert on a missed or failed Job.

The task itself needs to be idempotent — safe to run more than once — because retries or duplicate scheduling can happen. I make the output use unique transaction or backup IDs to guarantee that.

I check the CronJob's last schedule time, the Jobs it created, Pod events and logs, exit codes, the timezone, controller availability, and concurrency. A successful Job doesn't prove the backup is restorable — I still need to test restores separately.

## 16. What are liveness, readiness, and startup probes?

**Answer:**

A startup probe gates the liveness and readiness probes for a slow-starting application. Readiness removes an unready Pod from the Service's endpoints without restarting it. Liveness restarts a process that can't recover on its own. All three can use HTTP, TCP, exec, or, where supported, gRPC.

I keep the liveness probe local and conservative. If it checks something like a downstream database that's temporarily down, it can restart every healthy app at once and make the outage worse. Readiness can check whatever's actually needed to serve traffic. I set the thresholds based on measured startup and recovery times, not guesses.

When a probe fails, I check `kubectl describe`, hit the endpoint manually from inside the Pod, check the path, port, and scheme, the bind address, the timing, resource pressure, and the logs. I fix the probe or the application — I don't just disable the probe permanently to force a rollout through.

## 17. How do resource requests and limits work?

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

## 18. How do you fix OOMKilled Pods?

**Answer:**

First I confirm it's really OOMKilled: `lastState.terminated.reason: OOMKilled`, exit code 137, the events, memory metrics, and whether it's node pressure or a container-limit issue. I compare against recent traffic, releases, and config changes, and look at heap or native memory use, caching, concurrency, payload size, and possible leaks.

For an immediate, safe fix, I might roll back, reduce traffic or concurrency, scale out replicas, or raise the limit — only within what the node can actually support and only with evidence behind it. For a JVM app, I make sure the heap size leaves room for native memory inside the container limit.

The permanent fix removes the leak or the unbounded cache, or right-sizes the resources properly.

I update requests and limits through the controller, load-test the change, and keep watching working set, RSS, GC, OOM events, and node headroom, with alerts in place. Just raising the memory limit without finding the root cause can just move the failure to the node level or raise cost.

## 19. What is a PodDisruptionBudget and why is it useful?

**Answer:**

A PodDisruptionBudget, or PDB, limits how many **voluntary** disruptions can happen at once to a set of Pods, using `minAvailable` or `maxUnavailable`. The eviction API used by node drains and the cluster autoscaler respects it.

It doesn't protect against crashes, node loss, OOM kills, or application failures, and it doesn't create replicas either.

For a three-replica API, `minAvailable: 2` allows exactly one voluntary eviction at a time. I make sure the selector is correct, replicas are actually spread across nodes and zones, readiness is accurate, and the budget still allows maintenance to happen — an impossible PDB can block node drains and upgrades entirely.

When a drain is stuck, I check `kubectl get pdb`, the current healthy and desired counts, allowed disruptions, unavailable Pods, and the controller's replica count. I fix the underlying health or capacity issue, or make a deliberate, approved risk decision — I don't just bypass a production safeguard casually.

## 20. How does Kubernetes handle self-healing at Pod and node level?

**Answer:**

At the container level, kubelet restarts it according to the restart policy and probe results. At the Pod level, controllers like ReplicaSet, StatefulSet, or Job create replacements whenever the desired state isn't met.

The scheduler places the new Pods, and Services only send traffic to ready endpoints. When a node stops sending heartbeats, it becomes NotReady or Unreachable, and taint-based eviction combined with tolerations decides when managed Pods actually get replaced.

Self-healing has real limits. A standalone Pod isn't recreated. Persistent volume topology can block scheduling. Not enough capacity or overly strict affinity can leave a Pod Pending. Corrupted data doesn't heal itself. And a single replica still means downtime when it fails.

I validate all this with controlled Pod and node failure tests, watching events, replacement time, readiness, traffic, storage, and SLOs. A PDB protects against voluntary disruption — it does nothing for a node crash.

## 21. How does the Kubernetes scheduler decide where to place Pods?

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

## 22. What are common scheduling challenges in a multi-node, multi-AZ setup?

**Answer:**

The usual challenges are zonal volumes conflicting with where a Pod needs to run, uneven replica distribution, strict anti-affinity rules with too few zones to satisfy them, exhausted subnet IPs or instance quotas in an AZ, taints and node selectors, mixed node architectures, and autoscaler node groups that just can't satisfy the constraints. Cross-zone traffic also adds latency and cost.

I design topology spread across hostname and zone, choosing `ScheduleAnyway` or `DoNotSchedule` depending on how strict the requirement really is. I use `WaitForFirstConsumer` for storage, keep capacity available in each zone, and test what happens if a zone goes down. When investigating, I group the Pending events together and compare eligible nodes, PV zone, subnet IPs, quotas, and autoscaler logs.

The goal isn't perfect spreading at all costs — hard constraints can actually reduce availability if one zone fails, so I choose between strict and preferred rules deliberately.

## 23. A Pod is stuck in ImagePullBackOff. How do you troubleshoot?

**Answer:**

`ImagePullBackOff` means the pull failed and kubelet is now backing off between retries. I start by reading the exact event:

```bash
kubectl describe pod <pod>
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].image}'
kubectl get serviceaccount <sa> -o yaml
```

`not found` usually means the wrong repo or tag. `unauthorized` usually means a pull secret or IAM problem. A timeout or DNS error points to networking between the node and the registry. A manifest mismatch can mean a CPU architecture mismatch.

I verify the image and digest actually exist, check credentials such as IRSA or a managed identity, the secret's namespace and the ServiceAccount, registry limits and certificates, and the node's DNS, egress, disk, and runtime logs.

I fix the manifest or the access problem, confirm the image now pulls and starts, and run the application's health checks. To prevent it happening again, I add CI registry validation, digest pinning, credential-expiry monitoring, and a registry path that works across multiple AZs.

## 24. How do you troubleshoot CrashLoopBackOff?

**Answer:**

CrashLoopBackOff means the container keeps exiting and restarting, and kubelet is deliberately delaying each retry. I preserve the evidence first:

```bash
kubectl describe pod <pod>
kubectl logs <pod> -c <container> --previous
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState}'
```

I look at the exit code and reason — OOMKilled, Error, Completed — the command and arguments, config and Secret mounts, permissions, dependency and DNS reachability, probe failures, the port, the runtime, and any recent image or config change. Exit 0 under a restart policy of `Always` usually means the command was wrong for a long-running workload.

If a recent release caused this, I roll back first. To debug further, I run the same image with a command override or an ephemeral container where that's appropriate. I don't weaken production probes permanently just to make a rollout pass.

Once it's fixed, I verify the restart count is stable, readiness passes, logs and dependency health look normal, and I add a regression or preflight test.

## 25. A Pod is stuck in CrashLoopBackOff, but logs show no errors. How do you debug?

**Answer:**

The current logs can be empty because the container exits before its logger even starts, because it writes to a file instead of stdout, or because the useful output is actually in the previous instance. So I check `--previous`, the termination reason, message, and exit code, along with events and probes.

I compare the image's ENTRYPOINT against the manifest's command and arguments, environment and config mounts, the working directory, user and file permissions, architecture, OOM, and dependency reachability.

I can spin up a temporary debug Pod using the same image but with a `sleep` command instead, then inspect the filesystem and config and manually run the application under approved, non-production conditions. Ephemeral containers help too, as long as the target runs long enough to attach to.

If the process never even starts, I also check the node, runtime, and kubelet logs. The real fix gets codified in the image or manifest, tested, rolled out, and verified — a manual change inside a running Pod is never the permanent fix.

## 26. All Pods in one namespace suddenly fail readiness checks. What is your troubleshooting approach?

**Answer:**

Because this hits one whole namespace at the same time, I suspect a shared change or dependency rather than a bug in one application's code. I pin down the start time and check namespace events, and any recent rollout, config, Secret, NetworkPolicy, ServiceAccount, or quota change, along with the nodes hosting these Pods.

I call the readiness endpoint from inside a failing Pod, then from another Pod, and check the application logs. I test DNS and any shared database, cache, or API, check certificate and secret expiry, service endpoints, egress policy, and resource pressure.

I also compare against a namespace or environment that isn't affected.

For immediate mitigation, I might roll back a config, policy, or release, or restore a broken dependency, while preserving the evidence. Then I confirm the endpoints repopulate and real requests actually succeed.

To prevent a repeat, I add config canaries, secret-expiry alerts, policy tests, synthetic probes on dependencies, and better change correlation.

## 27. A critical Pod gets evicted due to node pressure. How do you prevent it from happening again?

**Answer:**

First I confirm the eviction reason from the Pod's status and events: memory, disk, inodes, PIDs, ephemeral storage, or a taint. I check the node's conditions, the kubelet's eviction messages, top and metrics data, and whether the filesystem, runtime, or logs are growing, along with what other Pods are doing.

I set measured requests, appropriate limits including ephemeral storage, log rotation, and cleanup. I also add capacity or autoscaling and spread replicas out. Critical workloads can deliberately use a PriorityClass and a Guaranteed or Burstable QoS class, but keep in mind priority can evict other workloads — it's not extra capacity.

A PDB doesn't stop this kind of eviction, because node pressure is involuntary, not voluntary.

I fix the source of the pressure, replace the node if it's unhealthy, confirm rescheduling and SLOs recover, and add alerts on capacity and growth forecasts. Changing kubelet's eviction thresholds is a last resort, tested platform decision — not a way to hide the fact that there isn't enough capacity.

## 28. Your cluster autoscaler is not scaling up even though Pods are Pending. What do you investigate?

**Answer:**

The Cluster Autoscaler only scales up if a Pending Pod could actually schedule on a new node from a managed node group. So I check the Pod's `FailedScheduling` event and the autoscaler's own logs and status.

Common causes are a node group already at its max size, a cloud quota or capacity limit, exhausted subnet IPs, requests bigger than any available node, a selector, affinity, or taint mismatch, a zonal PV or topology constraint, an unsupported architecture or missing GPU, an unrecognized node group, or an IAM or API failure.

I work out whether any available node template would actually satisfy the Pod. Then I fix the real constraint, config, or capacity issue — I don't just raise the max node count blindly. After the fix, I measure the time from Pending to node provisioning, to node Ready, to Pod Ready, and I check that scale-down still respects safety, PDBs, and cost.

A PDB mainly affects scale-down, not the initial scale-up. HPA also needs realistic requests, and the node autoscaler needs to respond fast enough for the actual demand.

## 29. HPA cannot scale Pods fast enough during a massive traffic surge. How do you handle it?

**Answer:**

First, I protect the users: rate limiting or load shedding, caching, pushing work onto a queue, rolling back an inefficient release, and manually raising replicas if it's safe and there's capacity. Then I check the HPA's conditions and current metric, how delayed that metric is, `maxReplicas`, the requests, Pod startup and readiness, Pending events, the node autoscaler, and any downstream bottleneck.

To prevent it next time, I raise the minimum replica count for headroom against sudden traffic, plan ahead for known peaks, and switch to a leading metric like queue depth or request concurrency through HPA or KEDA instead of a lagging one like CPU. I also tune the scale-up policy, optimize image pull and startup time, pre-provision nodes or use Karpenter, and make sure the database and cache can actually scale with it.

I load-test the burst scenario and measure detection time, Pod Ready time, node provisioning time, error rate, latency, and cost. Adding more Pods can't fix a shared dependency that's already saturated.

## 30. What do you do when a node hosting critical workloads crashes permanently?

**Answer:**

First I confirm the cloud instance or node is actually gone and check the user impact, make sure remaining capacity is enough, and stop routing to the unhealthy endpoints — readiness and the node controller normally handle that on their own. Managed, stateless Pods get recreated once the node is marked NotReady and eviction kicks in. I watch scheduling, storage attachment, and SLOs during that.

Stateful workloads need fencing and a clean detach first, to avoid a split-brain situation before anything reattaches.

For a node that's intermittently reachable, I cordon it. For a node that's permanently gone, I remove and replace it through the node group, after confirming there's no recoverable local data or forensic need. I don't rely on a PDB here — a PDB only controls voluntary disruption, not a crash.

Once recovery is done, I verify replicas are spread across zones, data is consistent, endpoints are correct, and the application actually transacts. The root-cause review covers node health, autoscaler capacity, replica spreading, any assumptions about local data, and how long failover took.

## 31. An entire Kubernetes region goes down. How do you fail over workloads?

**Answer:**

Regional recovery has to be designed ahead of time: an independent cluster and control plane in a second region, data that's actually replicated or restorable, a registry, config, and secrets that are available there too, IaC and GitOps, a global traffic manager, spare capacity, a runbook, and a defined RTO and RPO.

During the actual outage, I declare the incident, confirm data replication and consistency and who has authority to act, scale up or activate the secondary region, validate critical dependencies with a synthetic transaction, and then shift traffic over gradually while monitoring. Writes may need fencing to prevent a split-brain situation.

Communication and who owns the recovery decision are made explicit up front.

Failing back is also planned: reconcile the data, restore the primary region, test it, and shift traffic back gradually. Regular fire drills measure the actual RTO and RPO, not the theoretical one.

Just having manifests in Git isn't disaster recovery if the data, DNS, secrets, quota, or dependencies aren't actually available in the second region.

## 32. Why is a single Kubernetes control plane for multi-region deployments risky?

**Answer:**

Control-plane components and etcd need a low-latency, reliable quorum. Stretching that across distant regions adds latency and awkward partition behavior. Losing connectivity between regions can lose quorum entirely, or leave nodes unmanaged.

A single control plane also becomes a shared failure domain for upgrades, security, and configuration — meaning one bad change or outage there can take down everything that depends on it at once.

I normally run one independent cluster per region, all managed from the same versioned IaC and GitOps setup but with region-specific configuration. Global traffic routing and application or data replication are what actually provide failover between services.

Access, policy, and observability are standardized across regions without coupling their runtime quorum together.

The trade-off is more clusters and more work keeping them operationally consistent, which is addressed through automation and fleet management. I test losing a whole region or control plane, not just a single Pod failure.

## 33. How do you securely manage secrets and certificates in EKS?

**Answer:**

I use EKS Pod Identity or IRSA so a ServiceAccount gets short-lived AWS permissions instead of long-lived credentials. Secrets themselves live in Secrets Manager or Parameter Store, and get mounted or synced in using the Secrets Store CSI driver or External Secrets.

If a Kubernetes Secret does exist, I turn on envelope encryption with KMS and keep RBAC and audit narrow — remember, base64 is not encryption.

Certificates go through cert-manager with an approved issuer, such as a private CA or ACM integration, with renewal alerts and a tested reload path. I never put secrets in Helm values, Git, or environment logs.

When troubleshooting, I check the ServiceAccount's annotation and association, the OIDC trust relationship, the IAM policy, CSI or operator logs, the secret's version, KMS, network endpoints and DNS, and file permissions. A rotation test confirms the application picks up the new value without an outage and that the old credentials actually get revoked.

## 34. How do you handle certificate rotation in on-prem Kubernetes clusters?

**Answer:**

I start with an inventory: who owns each certificate, its issuer, purpose, expiry, trust chain, and consumers. For kubeadm clusters, I check `kubeadm certs check-expiration`, back up etcd and config, follow the version-specific documented renewal steps, update admin kubeconfigs and restart static Pods or components as needed, and then verify nodes, the API server, and controllers.

Kubelet's own certificate rotation is checked separately.

Application TLS goes through cert-manager with an internal ACME setup or CA, with alerts well before expiry. Rotation happens in stages: issue the new certificate with an overlap period so both are trusted, deploy or reload the consumers, verify the full TLS chain, SAN, and hostname from a real client, and only then revoke and remove the old one.

I test all of this in non-production first and document the recovery steps. Blindly replacing certificate files can break quorum or API access, so I plan for maintenance windows and console access ahead of time.

## 35. How do you secure a Kubernetes cluster?

**Answer:**

I secure every layer:

- Identity, MFA, and RBAC with only the permissions people actually need.
- A private or restricted API endpoint with audit logging.
- Patched control-plane and worker-node versions.
- Pod Security Admission, non-root containers, no privilege escalation, dropped capabilities, seccomp, and read-only filesystems.
- Signed, scanned, digest-pinned images.
- NetworkPolicies and controlled outbound traffic.
- External secrets, workload identity, and encryption.
- Quotas, tenant separation, runtime detection, central logs, and backups.

Policies are versioned and tested, and any exception has an expiry date. Nodes use fixed, replaceable images where possible, and etcd data and backups stay protected. I continuously check RBAC, public exposure, deprecated versions, and certificate expiry, and I test what happens when a deployment gets denied and how the incident procedure holds up.

Security is about managing threat and risk, not a checklist. No single tool "secures Kubernetes" — what matters is verifying the controls actually work and that response and restore procedures hold up under a real test.

## 36. How do you enforce that all images come from a trusted internal registry?

**Answer:**

CI builds the image, scans it, generates an SBOM, signs it, and pushes it to the approved registry. An admission policy tool like Kyverno, Gatekeeper, or the cloud provider's own policy engine rejects anything from a non-approved registry, and ideally requires a digest, a signature, and provenance — meaning proof of where the artifact actually came from and how it was built — rather than just checking the registry hostname, since compromised registry credentials could still push a bad tag under a trusted name.

I restrict who has pull and push roles on the registry, protect the signing identity, use immutable tags with a retention policy, keep the registry on a private network, and audit access. I roll the policy out in audit mode first, test it against both compliant and noncompliant Pods, allow controlled exceptions in specific namespaces with an owner and an expiry date, and monitor denials.

I also control which fields can mutate the image reference and who can use ephemeral containers or node runtime access. If the registry becomes unavailable, disaster recovery uses an approved, replicated registry — bypassing image verification is only ever a high-risk, explicitly documented emergency action.

## 37. How do you isolate workloads in a multi-tenant EKS cluster?

**Answer:**

Namespaces are the first boundary, but they aren't complete hard tenancy on their own. I combine them with tenant-specific Entra or IAM groups mapped to namespaced RBAC, separate ServiceAccounts and IRSA roles, default-deny network policy, quotas and LimitRanges, Pod security and admission control, trusted images, secrets isolation, and tenant-scoped logs, metrics, and cost labels.

Sensitive tenants get dedicated node groups with taints and a hardened runtime, and sometimes even separate clusters or cloud accounts when stronger isolation, compliance, or a smaller blast radius is required. Cluster-scoped resources, CRDs, webhooks, privileged Pods, and node access all stay platform-team-only.

I test cross-namespace API, network, secret, and IAM access, and resource-exhaustion attempts. I audit access and review quotas regularly. Whether to share a cluster at all follows the threat model, not just cost.

## 38. Kubelet is constantly restarting on one node. How do you isolate the issue?

**Answer:**

First I confirm it's really just one node, and cordon or drain it if that's safe to protect the workloads on it, and I preserve the logs. Then I check `systemctl status kubelet`, `journalctl -u kubelet`, the restart count and exit reason, config and flags, certificate expiry, system time, disk, inodes, memory, PIDs, the container runtime, and network, DNS, and firewall access to the API server.

I compare against a healthy node's version and config, and check for any recent image or bootstrap change. CNI errors here could be a symptom or the actual cause. For a managed node group, I usually favor replacing the node from a known-good image once I have evidence, rather than hand-repairing it.

After the fix or replacement, I verify the node is Ready, kubelet, the runtime, and CNI are healthy, test Pod scheduling, networking, volumes, logs, and exec, and then uncordon it. The root-cause review adds image validation, certificate and disk alerts, or a rollout canary.

## 39. An application upgrade caused downtime even with rolling updates. How do you prevent it next time?

**Answer:**

I line up the rollout timeline against endpoints, readiness, termination, capacity, errors, and any database or dependency change. Common causes are running only one replica, readiness firing too early or checking the wrong thing, a liveness probe killing the app mid-startup, `maxUnavailable` set too aggressively with no surge capacity, the app ignoring SIGTERM, load-balancer propagation delay, an incompatible config, schema, or API change, or simply not enough resources.

The fix usually involves multiple replicas spread across nodes, a startup and readiness probe tuned from measured timings, `maxUnavailable: 0` where there's capacity for it, a preStop hook with a real termination grace period and connection draining, a PDB for maintenance windows, and a backward-compatible expand-and-contract approach to schema changes. CI runs smoke tests and canary health gates with a rollback path.

I reproduce the failure in a load test and measure how many requests actually get dropped during the rollout. Zero downtime is an end-to-end architecture decision, not just a Deployment strategy setting.

## 40. How do you perform rolling updates and rollbacks in Kubernetes?

**Answer:**

I change the versioned manifest or image digest and apply it through CI or GitOps. The Deployment creates a new ReplicaSet and scales it up according to `maxSurge` and `maxUnavailable`. I watch it happen:

```bash
kubectl diff -f deployment.yaml
kubectl apply -f deployment.yaml
kubectl rollout status deploy/api --timeout=5m
kubectl rollout history deploy/api
```

I check the Pods, events, readiness, and the application's own error rate, latency, and smoke tests. If something regresses, I pause or roll back with `kubectl rollout undo deploy/api --to-revision=N`, or a Git revert or Helm rollback, and then validate.

A rollback might not undo a ConfigMap change, an external system change, or a database change. That's why releases use immutable config and artifacts, and backward-compatible migrations. Whatever failed gets its evidence preserved and fixed before I try the rollout again.

## 41. How do you achieve blue-green deployments in Kubernetes?

**Answer:**

I run Blue, the current version, and Green, the candidate, as two separate Deployments with distinct version labels. A stable production Service or Ingress route points at Blue.

I deploy Green, test it through a preview Service or hostname, including dependency and data compatibility, and then atomically switch the Service selector or traffic route over to it. I monitor the switch, and I can switch back for a fast rollback since Blue is still running.

I make sure there's enough capacity for both at once, and check sessions, caching, background jobs, database schema compatibility, and that there are no duplicate consumers of the same queue or resource. The Service selector switch itself is fast, but I still watch endpoint and load-balancer propagation. A weighted route can ramp traffic more gradually if needed.

Once I'm confident, I remove Blue and the old resources, with approval. The pipeline records the versions involved, and automated synthetic checks and SLO gates back the decision. Any destructive database migration waits until the rollback window has closed.

## 42. How do you safely update a Kubernetes cluster version?

**Answer:**

I start with an inventory: the current version, version skew, support status, deprecated APIs (checked with tools like `pluto` or `kubent`), and compatibility across CRDs, webhooks, operators, CNI, CSI, Ingress, and metrics, plus PDB coverage, capacity, and backups. For self-managed etcd, I actually test a backup and restore. I upgrade dev, then staging, under real workload tests first.

For production, I set up a maintenance window and communicate it, upgrade the control plane by one supported version increment, validate the API and controllers, update add-ons, add or upgrade a new node pool, and cordon and drain nodes gradually — respecting PDBs and any local or stateful workload — validating each batch before moving to the next. Then I retire the old node pool.

I monitor SLOs, Pending Pods, restarts, DNS, networking, storage, and admission throughout.

Rolling back a managed control plane usually isn't possible, so recovery often means fixing forward, rolling back the node pool, or failing the workload over elsewhere. I keep IaC, a runbook, and post-upgrade evidence, and I never skip an unsupported version jump.

## 43. What is the role of etcd and how do you back it up?

**Answer:**

etcd stores the entire Kubernetes API's state. If it loses quorum or the data itself, the cluster loses its management state along with it. For a self-managed stacked or external etcd, I use the correct TLS endpoints and take a consistent snapshot:

```bash
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
 --cacert=ca.crt --cert=server.crt --key=server.key snapshot save snapshot.db
etcdctl snapshot status snapshot.db --write-out=table
```

I encrypt it, store it off-cluster with a retention policy, control access and audit it, and keep the matching manifests and certificates alongside it. I actually test the documented restore process in an isolated environment. Managed services back up their own control plane, but recovering workload manifests and data is still on the customer.

I monitor quorum and member health, fsync latency, DB size, and available space. Checking snapshot status is not the same as testing a real restore.

## 44. Kubernetes etcd performance is degrading. What are root causes and fixes?

**Answer:**

Symptoms usually show up as API latency, timeouts, or leader changes. I check etcd's own metrics, logs, and member health, leader and quorum status, WAL and backend commit and fsync latency, disk throughput and space, CPU and memory, network latency and loss, DB size, alarms, how much object and event churn there is, and the overall API request load.

For mitigation, I cut down abusive or noisy clients and events, protect the disk, and replace an unhealthy member only through the documented, quorum-safe procedure. Longer term, I look at a dedicated low-latency SSD, an odd number of quorum members on a low-latency network, resource headroom, compaction followed by a controlled defrag of one member at a time per the official guidance, quotas, and better monitoring.

I always snapshot before maintenance and never restart or remove more than one quorum member at a time. Afterward I validate the API's SLOs and controller health. For managed Kubernetes, I escalate to the provider with metrics and a time window, while I check my own client load in parallel.

## 45. Multiple nodes show high disk I/O due to container logs. What do you do?

**Answer:**

I confirm the actual write source using node and disk metrics and file growth, and compare that against the app's release, its log level, and whether the log agent is duplicating output. For an immediate fix, I reduce a noisy debug log or a runaway loop, or roll back the release, protect node capacity, rotate logs through kubelet or runtime settings, and ship them centrally.

I don't blindly `rm` active log files — a deleted-but-open file still holds onto its disk space, and hand-editing the runtime directory can corrupt its state.

For the long term, I move to structured logs at the right level, add rate limiting or sampling, set size and file retention, tune Fluent Bit's backpressure and buffers, use a separate disk where that's designed in, set ephemeral-storage requests and limits, and add disk and inode forecast alerts.

I confirm the application's logs are still sufficient, the agent delivers them without loss within the required window, node I/O, pressure, and restarts are back to normal, and central log cost and cardinality — meaning the number of unique label combinations being tracked — stay under control.

## 46. How do you design a Kubernetes operator?

**Answer:**

I define a versioned CRD spec to capture what the user wants, and a status with conditions to capture what's actually happening.

The controller watches the custom resource and the objects it owns, and reconciles them idempotently: fetch the object, handle deletion or a finalizer, compute what's actually needed, create or update the owned objects, check their readiness, update the status and `observedGeneration`, and requeue with a backoff — meaning it waits a bit longer between each retry.

I use owner references for anything Kubernetes should clean up automatically, least-privilege RBAC, conflict and retry handling, events, metrics, and logs, leader election, rate limits, and validation, defaulting, or conversion webhooks only when they're actually needed. Calls to external systems need idempotency keys — something that makes it safe to repeat the same call — and a cleanup or finalizer timeout.

Tests cover reconciling the same state repeatedly, partial failure, deletion, an upgrade or schema conversion, and a dependency outage — not just the happy path. A good operator encodes the real lifecycle of its domain, not just a wrapper around a Deployment.

## 47. What metrics are monitored to ensure cluster health?

**Answer:**

I monitor control-plane and API availability, latency, and errors, the scheduler and controller work queues, and etcd where it's self-managed. On nodes, I watch Ready status, CPU, memory, disk, inodes, PIDs, network, kubelet, and the runtime. I also watch CNI and CoreDNS, Pending or restarting Pods, unavailable replicas, Jobs, HPA, PDB, PVCs and CSI, Ingress, and certificate expiry.

The most important signals are the workload's own SLIs: availability, latency, traffic, errors, saturation — meaning how close a resource is to its limit — and the actual business transaction succeeding. Capacity forecasts and cost round this out.

Alerts focus on actionable symptoms — SLO burn, zero Ready replicas, node pressure — each with a runbook attached. Dashboards are for diagnosing, not alerting. I test the alerts themselves and compare across cluster, version, and deployment labels.

I keep metric cardinality under control, since it's easy to let it explode. And healthy nodes don't automatically mean healthy users.

## 48. What logging and monitoring solutions do you recommend for Kubernetes?

**Answer:**

A common stack is Prometheus Operator, kube-state-metrics, and node-exporter for metrics, with Alertmanager and Grafana on top. Logs go through Fluent Bit into Loki, Elasticsearch, OpenSearch, or a cloud logging service. Tracing goes through OpenTelemetry into Tempo, Jaeger, or a vendor tool. Managed options like CloudWatch, Azure Monitor, or GCP Operations cut down on platform operations work.

The choice depends on scale, retention and query needs, high availability, tenancy, security and data-residency requirements, how well it integrates with what you already have, the team's skill set, and cost. I standardize structured logs with consistent correlation and resource attributes, sampling, retention tiering, and access control.

The observability platform also has to observe itself: scrape and ingest failures, dropped logs, storage growth, and cardinality.

I define SLO dashboards and alerts, and run incident drills that trace one request across ingress, service, and database. The number of tools matters far less than having reliable, correlated signals and clear ownership of them.

## 49. How would you debug a sudden spike in latency across services?

**Answer:**

First I pin down the incident's start time, scope, and affected regions, and compare traffic, errors, saturation, and recent deployments.

I start at the ingress P95 and P99 and trace one representative slow request across services. I compare time spent in the service itself against time spent in a dependency like a database, cache, or external call, plus queueing, retries, timeouts, DNS, networking, and node pressure.

I also check HPA and node scaling, cold starts, and any configuration or certificate change.

Mitigation might mean rolling back, shifting traffic, scaling the actual bottleneck, disabling an expensive feature, rate limiting, or restoring a broken dependency. I avoid blindly scaling or restarting every service.

I validate the user's actual transaction, latency, and error rate, and watch it recover. The root-cause review identifies the change that started it and any amplification — a retry storm or pool exhaustion, for example — and adds a test, more capacity, a timeout or retry budget, an alert, or a deployment gate.

## 50. How do you integrate Kubernetes into a CI/CD pipeline?

**Answer:**

On a pull request, I run tests, lint, and secret, dependency, and IaC scans. On the main branch, I build the image once, generate an SBOM, scan it, sign it, and push it by its immutable digest.

I render the Helm or Kustomize output and run schema and policy checks against it. I deploy to staging through GitOps where possible, or with a least-privilege CI identity otherwise, then run rollout, smoke, and integration checks.

Once approved, I progressively promote that same digest through the higher environments, monitoring SLOs and ready to roll back traffic or version at any point.

Secrets come from an external manager or workload identity — never an admin kubeconfig in the pipeline. Environments, config, and state stay separated, and concurrency controls prevent two overlapping deploys to the same production environment. Database changes follow an expand, migrate, contract pattern.

The pipeline records the commit, the image digest, the manifests or chart used, the scan results, approvals, the cluster, deployment, and revision, and the verification results. If a deploy fails, its events and logs are preserved, and it's reverted through Git, Helm, or the controller once it's safe to do so.

## 51. How do you connect Jenkins to a Kubernetes cluster?

**Answer:**

I prefer a short-lived cloud or workload identity mapped to Kubernetes RBAC, or better yet a GitOps setup where Jenkins just updates Git and a controller does the actual deploy. If Jenkins does connect directly, it gets a dedicated ServiceAccount and role limited to a specific namespace, resources, and verbs, a protected credential scope, and an isolated deployment agent — never a `cluster-admin` kubeconfig.

The Jenkins Kubernetes plugin might also spin up ephemeral build agents, but that's separate from deployment access. The pipeline verifies the context and namespace, renders and diffs the manifests, deploys, checks rollout and smoke tests, and logs everything for audit.

For an authentication failure, I check the credential, IAM token, or OIDC setup, the kubeconfig context, API DNS, network, CA, and time sync, and RBAC with `kubectl auth can-i`. I test both an allowed and a denied operation. I rotate tokens regularly, restrict who can approve the production stage, and never print a kubeconfig or token in the logs.

## 52. Have you upgraded Kubernetes clusters?

**Answer:**

A strong, honest answer states my exact role, the scale, the version, and the actual steps I followed. For example: I inventoried deprecated APIs, version skew, and compatibility across CNI, CSI, Ingress, metrics, and operators, tested a backup restore, ran the upgrade in dev and staging, and then scheduled it for production.

I upgraded the control plane by one supported minor version, validated the API and add-ons, created or upgraded a canary node pool, and cordoned and drained nodes gradually while respecting PDBs and any stateful or local data. I monitored Pending Pods, restarts, DNS, networking, storage, and SLOs throughout, then removed the old node pool. I kept spare capacity, clear communication, and a recovery plan the whole time.

Afterward I validated real transactions, policy and security, and backups, and recorded the evidence and any issues in the root-cause review. If I only assisted on part of it, I say exactly what my responsibility was rather than claiming end-to-end ownership.

## 53. Do you update only images or also replicas, storage, and CPU?

**Answer:**

I manage the whole desired state, not just the image: the image digest, replicas and HPA, requests and limits, probes, config and Secret references, the security context, Service, Ingress, and policy, volumes, and annotations. Each of these carries its own risk and needs its own validation.

Changing the image, config, or resources rolls the Pods, so I verify the rollout, capacity, and performance afterward. Manually changing replicas can fight with HPA or GitOps trying to set it back.

Some StorageClass and PVC fields are immutable, and need proper data migration, expansion, topology, or backup work instead — I never casually edit a stateful volume. Changing a Service's selector or port can cause an outage on its own.

Every change flows through a Git diff, render, schema, and policy checks, a lower environment first, then a progressive rollout to production, SLO verification, and a rollback or recovery path. "Deployment" really means configuration plus artifact together, not just the image.

## 54. How do you stop a Pod in Kubernetes?

**Answer:**

There's no normal "stop and keep" state for a Pod in Kubernetes. Deleting it terminates it, and its controller just recreates it if the desired replica count still says it should exist.

To actually stop a workload, you change its owner instead: scale a Deployment or StatefulSet to zero if that's safe, suspend a CronJob, or delete or update the controller through Git or IaC.

```bash
kubectl get pod <pod> -o jsonpath='{.metadata.ownerReferences}'
kubectl scale deploy/api --replicas=0
```

Before stopping anything in production, I check the traffic it's handling, its PDB, any state or background work it holds, graceful termination, and get approval. For a single unhealthy Pod, deleting it is only a diagnostic step or a fix after I've already captured logs and evidence — then I validate the replacement.

GitOps can revert a manual scale-down on its own, so I either update the actual source of truth or use an approved, temporary override instead.

## 55. How do you replicate a Pod?

**Answer:**

You use the controller for this. A Deployment for interchangeable stateless Pods, a StatefulSet for stable identity and storage. You set `spec.replicas` directly, or let an HPA manage it.

```bash
kubectl scale deployment api --replicas=5
kubectl rollout status deployment/api
```

Before scaling, I check requests, node and IP capacity, the Service's selector and readiness, shared dependency or database connection capacity, session and state handling, and licensing. More Pods won't help if the actual bottleneck is a database or something serialized — I load-test to confirm.

For automatic scaling, I configure the metrics, min and max, and behavior settings, plus node autoscaling. I verify the Ready replica count, how endpoints are distributed across zones, latency and error rate, and cost. I also update the Git source so GitOps doesn't quietly undo a manual change.

## 56. What command gets logs from a Pod?

**Answer:**

```bash
kubectl logs <pod> -n <ns> -c <container> --since=30m --timestamps
kubectl logs <pod> -n <ns> -c <container> --previous
kubectl logs -n <ns> -l app=api --all-containers --prefix --tail=200
```

`--previous` is essential for a container that already restarted. `kubectl describe` gives you events and termination details separately. If there are no logs at all, the app might be writing to a file instead, exiting before it even logs anything, or there's a runtime or kubelet issue, or I'm just looking at the wrong container.

Production logs should be structured and centralized, because Pod logs themselves are ephemeral. I make sure they include a correlation ID and timestamp, redact secrets and PII, and avoid an unbounded `-f` tail during an incident.

I compare the logs against deployment history, metrics, and traces rather than treating one log line as proof on its own.

## 57. What do you do if a Pod is not responding?

**Answer:**

First clarify where the Pod is not responding: inside the process, through its health endpoint, through the Service, or from outside the cluster.

I check `get` and `describe`, current and previous logs, the restart reason, exit code, OOM events, resource use, probes, the application port, the EndpointSlice, a direct request to the Pod versus one through the Service, DNS, network policy, and dependencies.

Also compare node health with recent deployment or configuration changes.

If there's real user impact, I pull it out of traffic through readiness or a rollback, or scale up a healthy version instead — I don't repeatedly kill it without evidence. An ephemeral debug container or a memory dump can capture a hang or deadlock. A node-level issue might need a cordon, drain, or replacement.

Once it's fixed, I verify the Pod is Ready with stable restarts, the Service endpoints are correct, and a real transaction succeeds with normal latency and error rate. The root-cause review adds a timeout, a probe fix, better monitoring, resource resizing, or a regression test.

## 58. What do you do if a Pod is getting heavy load and must remain healthy?

**Answer:**

I confirm request rate, latency, error rate, CPU, memory, concurrency, and how saturated any downstream dependency is. For an immediate fix, I scale out replicas if the workload is stateless and there's capacity, rate limit or load shed, cache, push work onto a queue, shift traffic, or roll back an inefficient change.

I also make sure readiness and graceful termination are working and the node autoscaler has capacity to add.

Longer term, I put the HPA on a metric that actually reflects load, set a minimum for headroom, cap the maximum based on what dependencies can handle, optimize startup time and image size, size requests and limits from load tests, use a PDB and spreading, and add connection pooling and a retry budget. KEDA works well for queue-based scaling.

I also optimize the code, database, or cache directly, since scaling horizontally can just amplify a bottleneck instead of fixing it.

I load-test both the traffic surge and a node failure, and measure HPA detection time, Pod and node Ready time, P95 latency, error rate, and cost. Alerts should fire before saturation actually becomes a problem, not after.

## 59. What happens if kubelet is not running?

**Answer:**

Kubelet stops sending heartbeats and status, and it stops managing the Pod lifecycle. Existing containers might keep running under the runtime, but no newly assigned Pods will start, and probes, restarts, config updates, and volume operations are no longer reliably handled. Exec and log access through kubelet also fails.

The node becomes NotReady, and managed Pods may eventually get replaced once tolerations expire — though that carries a split-brain risk for stateful workloads if the old process is still actually running.

I cordon the node, check `systemctl` and `journalctl` for kubelet, the runtime, config and certificates, disk and memory, and API connectivity, DNS, networking, and time sync. If it's a fixed, replaceable node image, I preserve the evidence and then replace it.

After recovery, I verify the node is Ready, CNI and CSI are healthy, a test Pod schedules fine, networking, logs, and exec work, and the application itself is healthy. I monitor kubelet's service, certificates, and disk going forward to catch this earlier next time.

## 60. How do you troubleshoot high Pod restart counts?

**Answer:**

First I identify which container, when it first started, how often it's happening, and why: `describe`, `logs --previous`, the container status's `lastState` and exit code, events, and metrics.

I classify the cause: OOM, a failed liveness probe, an application error, a completion under a restart policy of `Always`, a node or runtime issue, a config or Secret problem, a dependency or DNS failure, a permissions issue, or a rollout gone wrong.

I compare against the image, config, node, and an unaffected replica. To mitigate, I roll back, scale, or pull it out of traffic, and for a hang I capture a memory dump before it restarts again. Then I fix the code, config, probe, resources, or dependency, and deploy that fix through the controller.

I confirm the restart count has stabilized — keeping in mind the counter itself persists for the life of the Pod — readiness is good, transactions succeed, and SLOs hold over an observation window. To prevent it recurring, I add an alert on restart rate and reason, tune startup and liveness settings, test for memory leaks, add a dependency timeout or circuit breaker, run a config preflight check, and use a canary rollout.
Kubernetes Scenario-Based Interview Questions
==============================================

The following questions focus on production incidents and design decisions. Each answer explains the investigation flow, likely evidence, corrective action, verification, and preventive measures expected in an interview.

## 61. How do you troubleshoot Kubernetes nodes showing “NotReady”?

**Answer:** Run kubectl describe node → Check kubelet, docker/containerd logs → Verify network plugins → Restart node or replace if unhealthy.

**Detailed interview approach:**
I first run `kubectl get nodes -o wide` and `kubectl describe node <node>` and read the Conditions, Events, capacity, taints, and lease time.

From console access, I check `systemctl status kubelet`, `journalctl -u kubelet`, containerd, disk and inodes, memory pressure, time sync, certificates, and connectivity to the API server.

I cordon the node to stop new scheduling, and only drain it once disruption budgets and replacement capacity actually allow it.

Then I fix the real cause — disk cleanup, a CNI or runtime repair, certificate renewal, a route or firewall change, or replacing the node — and verify the node comes back Ready, system Pods are healthy, workloads reschedule, and alerts clear.

If this keeps happening, the fix is repairing the node image or node pool, not repeatedly restarting the node.

## 62. How do you troubleshoot slow image pulls in Kubernetes?

**Answer:** Check registry health, use image caching on nodes, enable parallel pulls, reduce image size, and use local/private mirrors.
Mini-case: Our pods were delayed by 2 mins due to 3GB images; slimming base images + enabling node cache cut startup time to <20s.

**Detailed interview approach:**
`kubectl describe pod <pod>` normally gives me the useful event: unauthorized, manifest not found, a DNS timeout, a certificate failure, a rate limit, or an architecture mismatch.

I verify the image name and digest actually exist, that the node can reach the registry, and that the Pod or its service account references the correct `imagePullSecret`.

I test or rotate credentials without printing them, and check registry IAM, the secret's namespace, proxy and CA trust, egress policy, quota, and node disk. I fix the specific layer that's broken, run a controlled rollout, and confirm new Pods pull successfully and become Ready.

To prevent it recurring, I use workload identity where it's supported, expiring registry credentials, signed and scanned smaller images, registry mirrors, and alerts on image-pull events.

## 63. How do you handle Kubernetes API server overload?

**Answer:** Scale API servers horizontally, add rate limiting, optimize controller workloads, and increase etcd performance.
Mini-case: Cluster had 50 controllers hammering the API; tuning cache sizes + scaling API server replicas fixed latency.

**Detailed interview approach:**
I confirm API-server latency, error rate, and inflight request metrics, audit volume, etcd latency and space, and control-plane CPU and memory. The API's audit logs and metrics usually point to a specific controller, user, a bad list/watch pattern, or a discovery storm.

To reduce the impact, I rate-limit or scale down the offending client or controller and pause any noisy automation. In a managed cluster, I bring in the provider to scale the control plane itself.

The permanent fix uses shared informers and watches, pagination, client backoff, realistic QPS and burst settings, fewer high-volume audit rules, and a healthy etcd.

Before closing the incident, I verify kubectl latency, controller queues, scheduling, admission webhooks, and any application-side change. Control-plane SLOs and alerts should catch saturation before clients start timing out.

## 64. How do you manage Kubernetes upgrades across 50+ clusters?

**Answer:** Automate upgrades with tools like Rancher/Anthos, test in staging first, roll out gradually, and monitor workloads post-upgrade. Mini-case: Anthos automated rolling upgrades; a failed upgrade in staging paused rollout and prevented production outages.
**Detailed interview approach:**
I review version skew, removed APIs, CNI, CSI, and Ingress compatibility, add-on versions, quotas, and maintenance constraints. I test the exact upgrade on a representative non-production cluster and run API deprecation and workload disruption checks against it.

In production, I upgrade the control plane first, then move through one node pool or failure domain at a time: cordon, drain respecting PDBs, replace or upgrade, and verify before moving on to the next.

I monitor API errors, DNS, networking, scheduling, and node and application SLOs, and keep the rollback and recovery options documented, since a control-plane downgrade often isn't supported.

Backups and a tested cluster-rebuild path are required before rolling this out across the whole fleet.

## 65. How do you handle Kubernetes certificate expiration?

**Answer:** Monitor cert expiry, automate renewals with cert-manager, rotate cluster certs regularly, and alert on failures. Mini-case: Cert-manager auto-renewed TLS certs before expiry; a Grafana alert ensured we never missed rotation deadlines.

**Detailed interview approach:**
First I identify which certificate actually expired — public ingress, an internal service, the API server, kubelet, a webhook, or a client — and check its issuer, SAN, chain, secret, and expiry with `openssl s_client` or `openssl x509`, plus the relevant controller's status.

For cert-manager, I check the Certificate, CertificateRequest, Order or Challenge objects, controller logs, DNS or HTTP challenge reachability, and the issuer's credentials.

I renew or rotate it through the supported controller, reload the consumer, and verify the complete chain and hostname from a real client. Cluster-level certificates follow the platform's specific rotation procedure and node or control-plane sequence.

Alerts at 30, 14, and 7 days out, automated renewal tests, an owner inventory, and protected issuer keys are what prevent an emergency expiry in the first place.

## 66. How do you implement cross-region failover for Kubernetes control planes?

**Answer:** Run HA clusters with regional control planes, replicate etcd across zones, set up DNS failover, and test regularly. Mini-case: A zone failure in us-central caused automatic API server failover to backup region; developers continued kubectl operations without noticing.
**Detailed interview approach:**
I start with a business-approved RTO and RPO, then identify the data, configuration, identity, DNS and network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a genuinely separate failure domain or account.

I automate restoring into a clean environment and validate integrity, application transactions, monitoring, and access before switching any traffic over. A backup isn't considered successful until a restore drill has actually proven it works.

Regular drills record the actual recovery time, any missing dependency, and any manual step needed, and that feeds back into updating the runbook, capacity planning, DNS TTLs, contact paths, and backup retention.

## 67. How do you handle Kubernetes etcd datastore corruption?

**Answer:** Restore from snapshot, rebuild control plane if required, ensure regular backups, and test restore procedure. Mini-case: When an upgrade corrupted etcd, Velero backups allowed full cluster restore in 30 minutes, saving production downtime.

**Detailed interview approach:**
I stop control-plane writes where the recovery procedure requires it, and preserve member logs, health data, disk evidence, and the latest known-good snapshot. I check `etcdctl endpoint health` and `status`, quorum, alarms, disk latency and space, certificates, and whether the corruption affects just one member or the whole cluster.

Recovery uses whatever method the Kubernetes distribution actually supports: replacing one failed member from healthy quorum, or restoring a verified snapshot into a new, consistent cluster and pointing the API servers at it. Velero on its own is not an etcd backup.

I validate API objects, controllers, Nodes, Secrets, and workloads before letting any new changes through. Scheduled, encrypted snapshots stored in a genuinely separate failure domain, and regular restore drills, are what actually prove the RPO and RTO.

## 68. How do you enforce zero-trust security in a Kubernetes cluster?

**Answer:** Disable default network connectivity, apply strict NetworkPolicies, enforce PodSecurityAdmission, use mTLS with a service mesh, and verify identity per request.

Mini-case: We deployed Istio with strict mTLS and namespace isolation; even if an attacker gained pod access, they couldn’t reach other services without valid identity.
**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 69. How do you detect and stop crypto-mining workloads in Kubernetes?

**Answer:** Enable anomaly detection (Falco/Azure Defender), restrict containers from running privileged mode, enforce quotas, and monitor unusual CPU spikes. Mini-case: A compromised pod started crypto-mining; Falco detected suspicious syscalls and Kubernetes killed the pod within seconds.
**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 70. How does Kubernetes handle scaling, rolling updates, and self-healing, and how do you scale a deployment manually and automatically?

**Answer:** Kubernetes uses controllers to keep actual state equal to desired state. A Deployment declares the required image and replica count, while its ReplicaSet keeps that number of Pods running.

If a container fails, kubelet restarts it according to the Pod policy. If a Pod disappears, the ReplicaSet creates another.

If a node fails, the control plane schedules replacement Pods on healthy nodes when capacity and storage constraints allow it.

For a rolling update, the Deployment creates a new ReplicaSet and gradually adds new Pods while removing old ones. I configure readiness and startup probes so traffic reaches only healthy Pods, and I tune `maxSurge` and `maxUnavailable` to maintain capacity.

I monitor with `kubectl rollout status deployment/<name>` and application metrics. If the release is unhealthy, I stop or reverse it with `kubectl rollout undo deployment/<name>`.

Manual scaling is appropriate for a planned, temporary change:

```bash
kubectl scale deployment api --replicas=6
kubectl get deployment api
kubectl get pods -l app=api
```

For automatic scaling, I configure an HPA using CPU, memory, or application metrics. Resource requests must be realistic because utilization-based HPA calculations depend on them:

```bash
kubectl autoscale deployment api --min=3 --max=20 --cpu-percent=65
kubectl get hpa
kubectl describe hpa api
```

HPA scales Pods, while Cluster Autoscaler or a provider-specific node autoscaler adds nodes when Pods remain Pending because the cluster lacks capacity. I load-test the complete path and verify scale-up time, maximum limits, Pod distribution, graceful scale-down, and cost alerts.

## 71. How do you handle stateful service failover in Kubernetes across zones/regions?

**Answer:** Use StatefulSets with appropriate storage classes, enable cross-zone replication for the datastore (e.g., multi-zone DB clusters), design DNS failover and leader election, and test failover procedures.

Mini-case: We configured a multi-zone PostgreSQL cluster with synchronous replicas; during a zone outage, automated leader election and DNS failover restored write availability within minutes.
**Detailed interview approach:**
I inspect the Pod, PVC, PV, StorageClass, CSI controller and node Pods, and their Events. The message usually points to pending provisioning, a topology mismatch, an attach conflict, a permissions issue, quota, a mount failure, or a filesystem error.

I confirm the access mode, requested capacity, zone or node affinity, reclaim policy, secret or IAM access, CSI logs, and the cloud disk's attachment state. For a stateful workload, I protect the data and avoid force-detaching or deleting a PVC until I've confirmed ownership and that backups exist.

I repair whichever layer is broken — binding, CSI, permissions, or storage — remount it through the controller, and validate that the application can actually read, write, and fail over. Regular snapshots, restore tests, CSI monitoring, and sensible topology settings are what prevent this.

## 72. How do you manage secret rotation across CI/CD, Kubernetes, and apps?

**Answer:** Centralize secrets in Vault/Key Vault/Secret Manager, use dynamic short-lived credentials where possible, automate rotation with scripts/events, update pipeline/runtime fetch logic to fetch latest secrets at runtime, and test rotation in staging.

Mini-case: We used Azure Key Vault with rotation policy; CI fetched secrets at job runtime and apps used managed identities to request short-lived tokens, removing the need for static credentials.
**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store — never in Git, YAML, images, command arguments, or build artifacts. A job gets a short-lived identity and fetches only the secret it actually needs for that stage. Masking output is only a secondary control, since an encoded or transformed value can still leak.

Rotation uses an overlap period: issue the new value, update the consumers, verify it works, revoke the old value, and audit for failures. If a scan finds a secret committed to the repo, I revoke it immediately, check where it was used, remove it from active history where that's appropriate, and rotate any downstream credentials too — just deleting the line isn't enough.

Pre-commit and server-side scans, protected logs, least privilege, expiry, and rotation tests are what prevent this from happening again.

## 73. How do you architect multi-tenant Kubernetes clusters securely?

**Answer:** Use namespaces + strict RBAC per tenant, network policies to isolate traffic, resource quotas & limit ranges, PodSecurity admission controls, encrypt secrets, and audit logging per namespace. Consider separate clusters for high-security tenants.

Mini-case: We separated dev/test tenants into namespaces with network policies; when a noisy tenant consumed CPU, quotas throttled them preventing cross-tenant impact.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 74. How do you troubleshoot Kubernetes CrashLoopBackOff with ConfigMap errors?

**Answer:** Check mounted config → Validate YAML → Fix key-value mismatches → Restart pod.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

## 75. How do you prepare for disaster recovery in Kubernetes?

**Answer:** Backup cluster state with Velero → Store manifests in Git → Automate redeployment in DR cluster.

**Detailed interview approach:**
I start with a business-approved RTO and RPO, then identify the data, configuration, identity, DNS and network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a genuinely separate failure domain or account.

I automate restoring into a clean environment and validate integrity, application transactions, monitoring, and access before switching any traffic over. A backup isn't considered successful until a restore drill has actually proven it works.

Regular drills record the actual recovery time, any missing dependency, and any manual step needed, and that feeds back into updating the runbook, capacity planning, DNS TTLs, contact paths, and backup retention.

## 76. How do you troubleshoot Kubernetes pods not pulling images from private registry?

**Answer:** Create imagePullSecret → Attach to service account → Validate registry credentials.

**Detailed interview approach:**
`kubectl describe pod <pod>` normally gives me the useful event: unauthorized, manifest not found, a DNS timeout, a certificate failure, a rate limit, or an architecture mismatch.

I verify the image name and digest actually exist, that the node can reach the registry, and that the Pod or its service account references the correct `imagePullSecret`.

I test or rotate credentials without printing them, and check registry IAM, the secret's namespace, proxy and CA trust, egress policy, quota, and node disk. I fix the specific layer that's broken, run a controlled rollout, and confirm new Pods pull successfully and become Ready.

To prevent it recurring, I use workload identity where it's supported, expiring registry credentials, signed and scanned smaller images, registry mirrors, and alerts on image-pull events.

## 77. How do you implement chaos engineering in Kubernetes?

**Answer:** Use Chaos Mesh/LitmusChaos → Inject pod/node failures → Test resilience → Monitor recovery.

**Detailed interview approach:**
I define a hypothesis tied to an SLO — something like "losing one Pod causes no user-visible errors" — and I make sure monitoring, a rollback path, a clear owner, and abort thresholds are all in place first.

I run the experiment in staging first, then in production with the smallest possible scope: one service or Pod, a low-traffic window, a short duration, and no other risky change happening at the same time.

Tools like Chaos Mesh can inject Pod, network, or resource faults, but access to them is tightly controlled. Something watches error rate, latency, saturation, and data integrity the whole time, and stops the experiment immediately if it crosses a threshold.

I compare what actually recovered against the hypothesis, record any gaps, fix the probes, capacity, retries, or runbooks, and rerun it. Chaos engineering is never just unlimited random failure — it's a controlled experiment.

## 78. How do you secure CI/CD pipelines running in Kubernetes?

**Answer:** Run pipelines as non-root → Restrict namespaces → Use PodSecurityPolicies/OPA → Isolate sensitive workloads.

**Detailed interview approach:**
I use SSO and MFA, role-based authorization, CSRF protection, TLS, a private controller, patched core and plugins, and I never run builds directly on the controller.

Credentials live in Jenkins Credentials or an external vault, scoped to the smallest folder or job that needs them. Pipelines use `withCredentials`, avoid shell tracing, and never interpolate a secret into a command line or artifact.

Agents are ephemeral, isolated, non-root where possible, and get a short-lived cloud identity. If a secret ever shows up in the logs, masking isn't enough — I stop the exposure, revoke and rotate the credential, restrict or delete the retained logs where policy allows, audit where it was used, and fix the step that printed it.

Configuration, plugins, and the restore process are all backed up and tested.

## 79. How do you troubleshoot Kubernetes pod scheduling due to taints?

**Answer:** Run kubectl describe node → Check taints → Add tolerations in pod spec → Or remove taints if not needed.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

## 80. How do you handle Kubernetes pods stuck in Terminating state?

**Answer:** Run kubectl delete pod --force --grace-period=0 → Check finalizers → Investigate volumes/network issues.

**Detailed interview approach:**
I check `kubectl describe pod`, the deletion timestamp, finalizers, the owner, node status, volume attachments, and kubelet, CNI, and CSI events. A Pod can get stuck Terminating because a finalizer has unfinished cleanup, the node is unreachable, a preStop hook is taking longer than the grace period, or storage or network teardown is stuck.

I fix whatever's actually responsible — the controller, node, or plugin — and let it delete normally. I only force-delete after confirming the process isn't still serving or writing, and that a stateful volume won't end up attached to two nodes at once. Force deletion removes the API object, but the process could still be running on an unreachable node.

I verify the replacement is healthy and cleanup finished, then fix the underlying finalizer timeout, controller issue, or node fencing so it doesn't happen again.

## 81. How do you manage Kubernetes CronJobs efficiently?

**Answer:** Set concurrency policy → Use resource limits → Monitor with Prometheus alerts → Clean up old jobs.

**Detailed interview approach:**
I set the schedule, timezone, service account, resource requests and limits, deadline, retry behavior, and history retention deliberately. `concurrencyPolicy: Forbid` prevents overlapping runs of work that isn't safe to run twice at once, while `Replace` only makes sense if a new run should just cancel the old one.

Jobs are idempotent, and use a database or distributed lock whenever duplicate execution would actually cause harm. I check the CronJob and Job Events and logs, missed schedules, the controller's clock, image pulls, quota, and dependency errors.

Success is a business result, not just a completed Pod, so I alert on the last successful timestamp and duration. `ttlSecondsAfterFinished` and history limits clean up old Jobs without deleting evidence I still need for audit.

## 82. How do you manage secrets in Kubernetes?

**Answer:** Store in Kubernetes Secrets (base64 encoded) → Encrypt at rest → Integrate with Vault/Key Vault for rotation.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 83. How do you troubleshoot Kubernetes pods stuck in “Pending”?

**Answer:** Run kubectl describe pod → Check node resource availability → Verify PVC binding → Ensure taints/tolerations are configured.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

## 84. How do you manage multi-cloud Kubernetes deployments?

**Answer:** Use Rancher, Anthos (GCP), or Azure Arc → Standardize with Helm/ArgoCD → Centralized monitoring/logging.

**Detailed interview approach:**
I standardize cluster creation, baseline add-ons, policy, identity, ingress, storage, observability, and GitOps through versioned modules, while keeping each cluster's state and failure domain independent of the others.

A central inventory or fleet layer reports versions, policy compliance, capacity, certificates, and health, but workload credentials and namespace RBAC stay least-privilege on each cluster individually.

Deployments roll out from a representative canary cluster to waves of others, and stop automatically on an SLO or policy failure. Cross-cluster traffic uses private connectivity, explicit DNS or service discovery, mTLS identity, and narrow firewall rules.

I test what happens if a whole cluster or region is lost, avoid any hidden shared control-plane dependency, and automate upgrades and drift correction with audited exceptions.

## 85. How do you manage Kubernetes cluster upgrades with zero downtime?

**Answer:** Upgrade control plane first → Drain nodes one by one → Use pod disruption budgets → Monitor workloads.

**Detailed interview approach:**
I review version skew, removed APIs, CNI, CSI, and Ingress compatibility, add-on versions, quotas, and maintenance constraints. I test the exact upgrade on a representative non-production cluster and run API deprecation and workload disruption checks against it.

In production, I upgrade the control plane first, then move through one node pool or failure domain at a time: cordon, drain respecting PDBs, replace or upgrade, and verify before moving on to the next.

I monitor API errors, DNS, networking, scheduling, and node and application SLOs, and keep the rollback and recovery options documented, since a control-plane downgrade often isn't supported.

Backups and a tested cluster-rebuild path are required before rolling this out across the whole fleet.

## 86. How do you detect & fix Kubernetes resource leaks?

**Answer:** Monitor unused PVCs, ConfigMaps, Secrets → Use cleanup jobs → Apply resource quotas.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

## 87. How do you troubleshoot Azure Kubernetes Service (AKS) scaling issues?

**Answer:** Check cluster autoscaler logs → Verify VM quotas in Azure → Ensure correct resource requests/limits.

**Detailed interview approach:**
First I decide whether the demand actually needs more Pods, bigger Pods, or more nodes. I look at request rate, latency, CPU and memory, throttling, Pending Pods, and dependency limits.

HPA needs realistic resource requests or application metrics, and tested min/max and stabilization settings. The node autoscaler supplies capacity for whatever's unschedulable.

For an immediate incident, I might safely scale with `kubectl scale deployment <name> --replicas=<n>` while I investigate the actual traffic or performance cause.

I verify readiness, load distribution, scaling events, dependency health, a graceful scale-down, and cost. Load tests and capacity alerts are what prove the whole path works before the next real peak.

## 88. How do you manage stateful applications in Kubernetes?

**Answer:** Use StatefulSets → PersistentVolumeClaims → Ensure proper storage class → Backup with Velero.

**Detailed interview approach:**
I inspect the Pod, PVC, PV, StorageClass, CSI controller and node Pods, and their Events. The message usually points to pending provisioning, a topology mismatch, an attach conflict, a permissions issue, quota, a mount failure, or a filesystem error.

I confirm the access mode, requested capacity, zone or node affinity, reclaim policy, secret or IAM access, CSI logs, and the cloud disk's attachment state. For a stateful workload, I protect the data and avoid force-detaching or deleting a PVC until I've confirmed ownership and that backups exist.

I repair whichever layer is broken — binding, CSI, permissions, or storage — remount it through the controller, and validate that the application can actually read, write, and fail over. Regular snapshots, restore tests, CSI monitoring, and sensible topology settings are what prevent this.

## 89. How do you handle Kubernetes secret exposure in logs?

**Answer:** Prevent kubectl describe from showing → Use kubectl get secret -o jsonpath securely → Audit RBAC → Enable encryption at rest.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 90. How do you enforce compliance in Kubernetes clusters?

**Answer:** Use OPA/Gatekeeper or Kyverno for policy enforcement → Restrict images, namespaces, resource limits.

**Detailed interview approach:**
I translate requirements into versioned, testable controls at several layers: source and branch rules, CI scanners, Terraform plan policy, Kubernetes admission policy, and cloud-native organization policy.

Typical examples require encryption, approved regions and images, non-root Pods, resource limits, labels and tags, private exposure, and least-privilege identity.

Each rule has unit tests with both allowed and denied fixtures, and produces an actionable reason plus a fix. Hard violations block the change, while approved exceptions are scoped, owned, and set to expire automatically.

Runtime and audit monitoring catches any change that happens outside CI. I track exceptions, false positives, and time to remediate, and periodically map the evidence back to each control, so compliance actually reflects real risk reduction rather than just a checklist.

## 91. How do you handle pod eviction in Kubernetes?

**Answer:** Check node pressure (CPU/memory/disk) → Reschedule pods to healthy nodes → Use PodDisruptionBudgets to protect critical pods.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

## 92. How do you implement rollback in Azure Kubernetes Service (AKS)?

**Answer:** Use kubectl rollout undo for deployments, or Helm rollback (helm rollback release name ).

**Detailed interview approach:**
I deploy an immutable artifact through a strategy matched to the risk involved: rolling for routine stateless changes, canary for metric-based exposure, or blue-green for a fast traffic switch.

The pipeline runs prechecks, deploys to a small or no-traffic target, runs readiness and business smoke tests, and then advances while watching error rate, latency, saturation, and the SLO or error budget.

If a threshold fails, it stops traffic and rolls back to the previous artifact or config. Database changes use an expand-and-contract approach, since an application rollback can't undo a destructive schema change. I verify recovery, record the result, and improve whatever test or guard should have caught the failure earlier.

## 93. How do you debug failed persistent volume (PV) mounts in Kubernetes?

**Answer:** Check PVC status (kubectl describe pvc) → Validate storage class → Check node permissions → Fix provisioner issues.

**Detailed interview approach:**
I inspect the Pod, PVC, PV, StorageClass, CSI controller and node Pods, and their Events. The message usually points to pending provisioning, a topology mismatch, an attach conflict, a permissions issue, quota, a mount failure, or a filesystem error.

I confirm the access mode, requested capacity, zone or node affinity, reclaim policy, secret or IAM access, CSI logs, and the cloud disk's attachment state. For a stateful workload, I protect the data and avoid force-detaching or deleting a PVC until I've confirmed ownership and that backups exist.

I repair whichever layer is broken — binding, CSI, permissions, or storage — remount it through the controller, and validate that the application can actually read, write, and fail over. Regular snapshots, restore tests, CSI monitoring, and sensible topology settings are what prevent this.

## 94. How do you handle Kubernetes pod scheduling failures?

**Answer:** Run kubectl describe pod → Check taints/tolerations → Check node resources → Add tolerations or scale nodes.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

## 95. How do you enforce least privilege (only the permissions needed) in Kubernetes?

**Answer:** Use RBAC roles → Bind only necessary permissions → Restrict cluster admin → Enable PodSecurityPolicies/OPA.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 96. How do you manage multiple Kubernetes clusters securely?

**Answer:** Use Rancher, Anthos, or Azure Arc → Apply consistent RBAC & policies → Centralized monitoring/logging.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 97. How do you optimize Kubernetes cluster costs?

**Answer:** Use Cluster Autoscaler, rightsizing pods with requests/limits, spot/preemptible nodes, and scale workloads by time of day.

**Detailed interview approach:**
I compare cost by service, account or subscription, region, tag, SKU, and usage metric against the normal baseline and recent deployments. I check whether the increase comes from real traffic, runaway autoscaling, orphaned resources, log or egress volume, a pricing or commitment change, or even compromised compute.

I contain it safely with budgets, scaling caps, quotas, or shutting down confirmed non-production waste — never by blindly deleting stateful production resources. Terraform plans get cost estimates and require policy or approval above certain thresholds.

Required tags, anomaly alerts, rightsizing, schedules, lifecycle retention, reserved or spot instance choices, and owner showback are what make cost optimization an ongoing habit rather than a one-time cleanup. I always verify performance and SLOs are still fine after reducing cost.

## 98. How do you implement multi-region deployments in Kubernetes?

**Answer:** Use multiple clusters across regions → Manage via Anthos (GCP) or Azure Arc → Route traffic with global load balancer.

**Detailed interview approach:**
I start with a business-approved RTO and RPO, then identify the data, configuration, identity, DNS and network, certificates, dependencies, and the people and runbooks needed to actually recover.

Manifests and infrastructure are versioned, but stateful data and secrets need encrypted backups or replication into a genuinely separate failure domain or account.

I automate restoring into a clean environment and validate integrity, application transactions, monitoring, and access before switching any traffic over. A backup isn't considered successful until a restore drill has actually proven it works.

Regular drills record the actual recovery time, any missing dependency, and any manual step needed, and that feeds back into updating the runbook, capacity planning, DNS TTLs, contact paths, and backup retention.

## 99. How do you implement auto-healing in Kubernetes?

**Answer:** Use liveness probes → If container fails health check, kubelet restarts it → Integrate with Horizontal Pod Autoscaler for scaling.

**Detailed interview approach:**
First I decide whether the demand actually needs more Pods, bigger Pods, or more nodes. I look at request rate, latency, CPU and memory, throttling, Pending Pods, and dependency limits.

HPA needs realistic resource requests or application metrics, and tested min/max and stabilization settings. The node autoscaler supplies capacity for whatever's unschedulable.

For an immediate incident, I might safely scale with `kubectl scale deployment <name> --replicas=<n>` while I investigate the actual traffic or performance cause.

I verify readiness, load distribution, scaling events, dependency health, a graceful scale-down, and cost. Load tests and capacity alerts are what prove the whole path works before the next real peak.

## 100. How do you troubleshoot “OOMKilled” pods in Kubernetes?

**Answer:** Pod exceeded memory → Check logs/events → Increase memory limit → Optimize app memory usage → Use HPA to spread load.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

## 101. How do you troubleshoot “Node Not Ready” in Kubernetes?

**Answer:** Run kubectl describe node → Check kubelet logs → Verify Docker/container runtime → Restart node services → Replace unhealthy node if needed.

**Detailed interview approach:**
I first run `kubectl get nodes -o wide` and `kubectl describe node <node>` and read the Conditions, Events, capacity, taints, and lease time.

From console access, I check `systemctl status kubelet`, `journalctl -u kubelet`, containerd, disk and inodes, memory pressure, time sync, certificates, and connectivity to the API server.

I cordon the node to stop new scheduling, and only drain it once disruption budgets and replacement capacity actually allow it.

Then I fix the real cause — disk cleanup, a CNI or runtime repair, certificate renewal, a route or firewall change, or replacing the node — and verify the node comes back Ready, system Pods are healthy, workloads reschedule, and alerts clear.

If this keeps happening, the fix is repairing the node image or node pool, not repeatedly restarting the node.

## 102. What if Kubernetes cluster nodes are running out of resources?

**Answer:** Check node metrics → Add more nodes (cluster autoscaler) → Tune resource requests/limits → Reschedule pods across nodes.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

## 103. How do you handle configuration drift in Kubernetes?

**Answer:** Use GitOps tools like ArgoCD/Flux → Ensure cluster config matches Git repo → Auto-revert manual changes.

**Detailed interview approach:**
Git holds the reviewed, desired configuration in immutable, versioned commits. Argo CD or Flux continuously compares that against the live cluster and reconciles any difference.

I separate environment permissions and repositories, require branch protection and policy or security checks, and give the controller only the cluster scope it actually needs.

A manual emergency change might temporarily pause sync, but it gets captured through a pull request right away — otherwise reconciliation will correctly remove it again. A rollback is just a Git revert to the last known-good commit, followed by a sync and a health and SLO check.

Secrets use an external-secret or encrypted-secret workflow, never plaintext in Git. Sync failures, drift, controller access, and audit events are all monitored, and destructive pruning has explicit safeguards around it.

## 104. How do you secure Kubernetes cluster?

**Answer:**
• Use RBAC for access control.
• Enable Network Policies.
• Regularly patch cluster.
• Restrict container privileges (no root user).
• Use Secrets API for sensitive data.

**Detailed interview approach:**
I apply defense in depth: private or restricted API access, SSO with least-privilege RBAC, separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit and runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect an exposure, I isolate the workload, preserve audit and runtime evidence, revoke tokens or credentials, check for lateral movement, and rebuild from a trusted image.

I verify both the denied and the allowed paths with real service accounts, and periodically review RBAC, unused permissions, certificate and secret rotation, patch levels, backup and restore, and any policy exceptions still open.

## 105. How do you troubleshoot high pod restart counts in Kubernetes?

**Answer:** • Check pod logs for crash reason.
• Validate resource limits.
• Verify liveness/readiness probes.
• Fix config/secret errors.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

## 106. How do you perform Canary Deployment in Kubernetes?

**Answer:** Deploy a new version to a small % of users → Use Istio/NGINX Ingress for traffic routing → Gradually increase traffic → Rollback if errors.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

## 107. How do you troubleshoot “ImagePullBackOff” in Kubernetes?

**Answer:**
Check if image exists in registry.
Validate credentials/secret for private registry.
Verify image tag.
Fix and redeploy.

**Detailed interview approach:**
`kubectl describe pod <pod>` normally gives me the useful event: unauthorized, manifest not found, a DNS timeout, a certificate failure, a rate limit, or an architecture mismatch.

I verify the image name and digest actually exist, that the node can reach the registry, and that the Pod or its service account references the correct `imagePullSecret`.

I test or rotate credentials without printing them, and check registry IAM, the secret's namespace, proxy and CA trust, egress policy, quota, and node disk. I fix the specific layer that's broken, run a controlled rollout, and confirm new Pods pull successfully and become Ready.

To prevent it recurring, I use workload identity where it's supported, expiring registry credentials, signed and scanned smaller images, registry mirrors, and alerts on image-pull events.

## 108. How do you set resource limits in Kubernetes?

**Answer:** Define requests & limits in pod spec → Ensures fair resource allocation and prevents pod from consuming all CPU/memory.

**Detailed interview approach:**
I use `kubectl describe pod <pod>` and read the scheduler's Events instead of guessing. They tell me whether it's insufficient CPU or memory, a taint, a node selector or affinity mismatch, an unbound PVC, a topology constraint, pod limits, or quota.

I compare the requests against `kubectl top nodes`, the nodes' allocatable values, taints, labels, quotas, and autoscaler logs. Then I fix whatever's actually blocking the Pod: right-size the requests, add a justified toleration or label, fix the PVC or storage class, relax an overly strict affinity rule, or add node capacity.

I don't remove a protective taint just to get past the problem. I verify scheduling, readiness, distribution across failure domains, and whether the cluster autoscaler will handle the same situation automatically next time.

## 109. How do you monitor logs in Kubernetes?

**Answer:** Use kubectl logs for quick debugging → For centralized logging, use EFK (Elasticsearch + Fluentd + Kibana) or Loki + Grafana.

**Detailed interview approach:**
I define the service indicators first — availability, latency, errors, traffic, saturation, and the key business outcomes — then collect correlated metrics, structured logs, and traces with consistent service, environment, version, and request IDs.

Dashboards show both the symptoms and the dependencies behind them. SLO-based alerts route by severity and ownership, each with a runbook attached.

At scale, I combine or downsample older metrics, sample traces intelligently, and apply hot, warm, and cold log retention based on what's actually needed for debugging and compliance. During an incident I follow one request across every layer and compare it against deployment and config events.

I verify alert delivery and recovery regularly, and tune out noisy or unactionable signals.

## 110. How do you handle a failed deployment in Kubernetes?

**Answer:** Use kubectl describe pod and kubectl logs to check errors → If critical, rollback with kubectl rollout undo deployment <name> → Fix and redeploy.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

## 111. How do you ensure zero downtime deployment in Kubernetes?

**Answer:** Use RollingUpdate strategy in deployments, configure readiness probes, and keep replicas running until new pods are healthy.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

## 112. How do you monitor Kubernetes clusters?

**Answer:** Use Prometheus + Grafana for metrics, ELK/EFK stack for logs, and Kubernetes liveness/readiness probes for pod health.

**Detailed interview approach:**
I define the service indicators first — availability, latency, errors, traffic, saturation, and the key business outcomes — then collect correlated metrics, structured logs, and traces with consistent service, environment, version, and request IDs.

Dashboards show both the symptoms and the dependencies behind them. SLO-based alerts route by severity and ownership, each with a runbook attached.

At scale, I combine or downsample older metrics, sample traces intelligently, and apply hot, warm, and cold log retention based on what's actually needed for debugging and compliance. During an incident I follow one request across every layer and compare it against deployment and config events.

I verify alert delivery and recovery regularly, and tune out noisy or unactionable signals.

## 113. What will you do if a pod is stuck in CrashLoopBackOff?

**Answer:** Run kubectl describe pod and kubectl logs → Check startup script, image, or config issue → Fix error → Redeploy.

**Detailed interview approach:**
I compare the current and previous container failure using `kubectl describe pod <pod>`, `kubectl logs <pod> -c <container>`, and `kubectl logs <pod> -c <container> --previous`.

I look at the exit code, reason, events, probes, command and arguments, environment, mounted ConfigMaps and Secrets, permissions, and dependency reachability.

Exit code 137 usually points to OOM; a connection or config error needs a different fix. I reproduce the issue with the exact image and configuration in a safe namespace, fix the actual application, config, resource, or probe problem, and deploy a new revision instead of just repeatedly deleting the Pod.

I watch the rollout status, restart count, logs, latency, and error rate afterward, and roll back to the last healthy revision if the impact keeps growing.

## 114. How do you perform blue-green deployment in Kubernetes?

**Answer:** Run two environments (Blue = current, Green = new) → Route traffic to Green only after successful validation → Rollback to Blue if issues occur.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness and startup probes, a graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and the availability target — setting zero unavailable only makes sense if the cluster can actually host the surge capacity that requires.

I deploy an immutable image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. A rollback uses `kubectl rollout undo deployment/<name>`, or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible configuration and database changes, and an actually-tested rollback path are what make an update genuinely low-risk.

## 115. How would you migrate a stateful application to Kubernetes with minimal downtime?

**Answer:**

First I document data ownership, consistency requirements, storage IOPS, dependencies, DNS, backups, and what RTO and RPO are actually acceptable. I only use a StatefulSet when stable identity or ordered behavior is actually required — a managed external database can be the safer choice if the team isn't set up to operate a distributed datastore inside Kubernetes.

The target environment needs the right storage topology, anti-affinity, disruption budgets, probes, resource requests, and a tested backup and restore process.

I provision the target in parallel, restore a recent backup into it, and use database-native replication or change-data capture to keep it in sync with ongoing writes. I validate schema compatibility, transactions, performance, failover, monitoring, and restore before actually cutting over.

At cutover, I pause writes if consistency requires it, apply the final delta, switch the connection or shift weighted traffic over, and watch errors, latency, replication lag, and data correctness closely.

The old environment stays read-only during an agreed rollback window. Rolling back is only safe once I understand who owns the writes and how the data would reconcile back.

Once things are stable, I stop the temporary replication, rotate the migration credentials, verify another restore still works, and record the actual downtime and recovery behavior for next time.

## 116. How would you design a GitOps workflow for more than 20 teams with independent release cycles?

**Answer:**

I separate platform configuration from application delivery. A platform team owns the cluster add-ons, admission policy, namespaces, common charts, and the GitOps controllers themselves.

Each application team owns its own scoped repository or directory. Argo CD Projects, or Flux's own tenancy rules, restrict which repositories, namespaces, clusters, and resource kinds each team can touch, so one team can't alter another team's workloads or the cluster-wide controls.

The flow looks like this: commit, CI tests and scans it, it becomes an immutable signed image, a pull request updates the digest or chart version, policy and the owner review it, GitOps reconciles the cluster, and then progressive health checks confirm it's actually working.

Teams release independently within their own application boundaries. Promotion just moves the same tested artifact forward instead of rebuilding it for each environment.

ApplicationSets, or generated configuration, cut down on repetition without collapsing everything into one giant shared values file.

I add branch protection, CODEOWNERS, schema and policy tests, external secret references, sync ordering for dependencies, safe pruning, and rollback through a Git revert. Dashboards track sync health, drift, controller permissions, rollout SLOs, and how long reconciliation actually takes.

Break-glass changes are time-limited and get captured back into Git immediately.

## 117. How do you enter a running Pod, and what is the correct way to define Kubernetes objects?

**Answer:**

I identify the namespace, Pod, and container, and run only the command I actually need:

```bash
kubectl get pods -n payments
kubectl exec -it -n payments api-7d9f6 -c api -- /bin/sh
```

A minimal image might not even have a shell, so I use an approved ephemeral debug container with `kubectl debug` instead. I avoid installing tools or permanently changing configuration inside a running container, since those changes aren't tracked anywhere and just disappear the moment it restarts.

Objects are declared with `apiVersion`, `kind`, `metadata`, and `spec`, then reviewed and applied through GitOps or `kubectl apply -f`. I validate manifests with a server-side dry-run, schema and policy checks, and a diff, then verify the rollout and application health afterward.

CRDs extend the API with entirely new object types. A StorageClass, by the way, is a specific storage-provisioning object — not a general-purpose Kubernetes "class" of anything.

## 118. What does `kubectl describe` do, and how do you use it during troubleshooting?

**Answer:**

`kubectl describe <resource> <name>` gives you a human-readable view of the live object: metadata, selected spec and status fields, Conditions, related resources, and recent Events. Common examples are `kubectl describe pod`, `kubectl describe node`, and `kubectl describe pvc`.

For a Pod, I look at the container state, the last termination reason and exit code, the image, mounts, probes, requests and limits, where it's placed, and any scheduling, image-pull, probe, or volume Events.

It doesn't replace logs, metrics, or the full YAML, so I compare it against `kubectl logs --previous`, the sorted Events, `kubectl get -o yaml`, node or runtime logs, and monitoring data.

I fix the cause once I actually have evidence for it, then confirm the Conditions, readiness, and the real application transaction all recover.

## 119. What is a CustomResourceDefinition (CRD), and when would you create one?

**Answer:**

A CRD extends the Kubernetes API with an entirely new resource type. Once it's installed, users can create, read, update, watch, label, and authorize custom objects using normal Kubernetes tools.

For example, a platform team could define a `Database` resource whose spec describes the engine, size, and backup policy.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databases.platform.example.com
spec:
  group: platform.example.com
  scope: Namespaced
  names:
    plural: databases
    singular: database
    kind: Database
    shortNames: [db]
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: [engine, storageGiB]
              properties:
                engine:
                  type: string
                  enum: [postgres, mysql]
                storageGiB:
                  type: integer
                  minimum: 10
      subresources:
        status: {}
```

The CRD gives the new object storage, discovery, validation, and API behavior, but it doesn't perform the actual business action on its own. A custom controller is normally what turns the `Database` object's desired state into real cloud or Kubernetes resources.

I reach for a CRD when the concept has a genuinely meaningful declarative lifecycle, multiple users or tools need a real Kubernetes API contract for it, and reconciling it actually adds domain value. I don't create one just to store arbitrary configuration — a ConfigMap or an external API is often simpler.

A production CRD needs a structural schema, clear defaults and validation, status Conditions, printer columns where they're useful, RBAC, versioning, and a conversion or migration plan before its stored schema ever changes.

## 120. What is a custom Kubernetes controller, and how does its reconciliation (making actual state match desired state) loop work?

**Answer:**

A custom controller watches one or more Kubernetes resources and continuously moves the actual state toward the desired state. An operator is a controller plus domain-specific operational knowledge — things like provisioning, upgrades, backup, or failover.

The reconciliation flow looks like this:

```text
watch event -> enqueue key -> read desired and actual state
-> handle deletion/finalizer -> calculate required change
-> create/update owned or external resources -> observe health
-> update status/conditions -> requeue when required
```

Reconciliation has to be idempotent — running it repeatedly with the same desired and actual state should never produce a harmful extra action.

The resource's generation number changes whenever its spec changes. The controller records `status.observedGeneration` and Conditions like `Ready`, `Progressing`, or `Degraded`, so users can see whether their latest change has actually been processed.

I use owner references for anything Kubernetes should own and clean up automatically, and finalizers only for cleanup that genuinely has to happen before deletion. I keep RBAC least-privilege, use leader election so only one replica is active at a time, rate-limited queues, optimistic-concurrency retries, limited external calls, timeouts, and metrics, events, and logs.

Calls to external APIs need their own idempotency tokens and a way to recover from a partial success.

If a controller isn't reconciling, I check CRD or version discovery, the controller Pod and leader election, RBAC denials, watch or list errors, work-queue depth and retries, the resource's generation and Conditions, finalizers, dependent events, and external API failures.

Tests cover reconciling the same state repeatedly, a lost watch or restart, a conflict, a dependency outage, deletion, a schema upgrade, and partial creation — not just the happy path.

## 121. If a Pod has initContainers that fail but the main container has `restartPolicy: Never`, what happens to the Pod status?

**Answer:**

When an initContainer fails and the Pod has `restartPolicy: Never`, the Pod remains in the `Init:Error` or `Init:CrashLoopBackOff` state permanently. The main container never starts because initContainers must complete successfully before the main containers can begin.
Key points:

- InitContainers run sequentially and must succeed.
- With `restartPolicy: Never`, failed initContainers won't restart.
- The Pod becomes permanently stuck in a failed init state.
- You need to delete and recreate the Pod to resolve this.

```yaml
apiVersion: v1
kind: Pod
spec:
  restartPolicy: Never
  initContainers:
  - name: init-container
    image: busybox
    command: ['sh', '-c', 'exit 1']  # This will fail
  containers:
  - name: main-container
    image: nginx  # This will never start
```

## 122. When using a StatefulSet with 3 replicas and you delete replica-1, will replica-2 and replica-3 be renamed to maintain sequential ordering?

**Answer:**

No, Kubernetes does not rename existing StatefulSet Pods. If you delete `myapp-1`, only that specific Pod gets recreated with the same name. `myapp-2` and `myapp-3` retain their original names.

StatefulSet naming behavior:

- Pod names are persistent and ordinal-based (`myapp-0`, `myapp-1`, `myapp-2`).
- When a Pod is deleted, it's recreated with the same name and ordinal.
- Existing Pods are never renamed to fill gaps.
- This maintains stable network identities and persistent storage associations.

This is crucial for applications requiring stable network identities like databases or distributed systems.

## 123. Can a DaemonSet Pod be scheduled on a master node that has a `NoSchedule` taint without explicitly adding tolerations?

**Answer:**

No, DaemonSet Pods cannot be scheduled on nodes with `NoSchedule` taints unless they have matching tolerations. However, there's an important exception.

The DaemonSet controller automatically adds tolerations for:

- `node.kubernetes.io/not-ready`
- `node.kubernetes.io/unreachable`
- `node.kubernetes.io/disk-pressure`
- `node.kubernetes.io/memory-pressure`
- `node.kubernetes.io/pid-pressure`
- `node.kubernetes.io/network-unavailable`

For master nodes with the `node-role.kubernetes.io/master:NoSchedule` taint, you must explicitly add:

```yaml
spec:
  template:
    spec:
      tolerations:
      - key: node-role.kubernetes.io/master
        operator: Exists
        effect: NoSchedule
```

## 124. If you update a Deployment's image while a rolling update is in progress, will Kubernetes wait for the current rollout to complete or start a new one immediately?

**Answer:**

Kubernetes immediately starts a new rollout, canceling the current one. This behavior is called "rollout interruption."

What happens:

- The current rolling update stops immediately.
- A new ReplicaSet is created for the updated image.
- The previous ReplicaSet (from the interrupted rollout) begins scaling down.
- The new ReplicaSet scales up according to the rolling update strategy.

You can observe this with:

```bash
kubectl rollout status deployment/myapp
kubectl rollout history deployment/myapp
```

This can lead to more Pods than expected during the transition period, so monitor resource usage carefully.

## 125. When a node becomes `NotReady`, how long does it take for Pods to be evicted, and can this be controlled per Pod?

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

## 126. Is it possible for a Pod to have multiple containers sharing the same port on localhost, and what happens if they try to bind simultaneously?

**Answer:**

No, multiple containers in the same Pod cannot bind to the same port on localhost simultaneously. Since containers in a Pod share the same network namespace, they share the same IP address and port space.

What happens:

- The first container successfully binds to the port.
- The second container gets a "port already in use" error.
- The failing container may crash or go into CrashLoopBackOff.

Solutions:

- Use different ports for each container.
- Use a sidecar proxy pattern.
- Configure one container as the primary port handler.

```yaml
# This will cause conflicts
containers:
- name: app1
  ports:
  - containerPort: 8080
- name: app2
  ports:
  - containerPort: 8080  # Conflict!
```

## 127. If you create a PVC with `ReadWriteOnce` access mode, can multiple Pods on the same node access it simultaneously?

**Answer:**

This depends on the storage provider and how it implements `ReadWriteOnce` (RWO).

Technical details:

- **RWO specification:** The volume can be mounted as read-write by a single node.
- **Implementation varies:** Some storage providers allow multiple Pods on the same node to access RWO volumes.
- **Not guaranteed:** This behavior is not guaranteed by the Kubernetes specification.

Safe approaches:

- Use `ReadWriteMany` (RWX) for multi-Pod access.
- Use StatefulSets for predictable single-Pod-per-volume relationships.
- Test your specific storage provider's behavior.

```yaml
# Safer approach for multi-Pod access
accessModes:
- ReadWriteMany  # Instead of ReadWriteOnce
```

## 128. When using a Horizontal Pod Autoscaler with custom metrics, what happens if the metrics server becomes unavailable during high load?

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

## 129. Can you run `kubectl port-forward` to a Pod that's in CrashLoopBackOff state, and will it work?

**Answer:**

It depends on the timing and Pod restart behavior.

- **During the container restart interval:** `kubectl port-forward` may work briefly if you catch the Pod between restarts and the container is temporarily running.
- **When the container is down:** Port-forward fails immediately with connection errors.

Practical approach:

```bash
# This usually fails
kubectl port-forward pod/failing-pod 8080:8080

# Better approach - port-forward to a service
kubectl port-forward service/myapp-service 8080:8080
```

For debugging CrashLoopBackOff:

- Use `kubectl logs pod-name --previous` to see crash logs.
- Check container startup probes and resource limits.
- Consider temporarily removing liveness probes for debugging.

## 130. If a ServiceAccount is deleted while Pods using it are still running, what happens to the mounted tokens and API access?

**Answer:**

Existing Pods continue to function with their mounted tokens, but with important limitations.

Immediate effects:

- **Running Pods:** Continue using cached/mounted tokens until Pod restart.
- **Token refresh:** May fail when tokens expire (typically 1 hour).
- **New Pods:** Cannot be created using the deleted ServiceAccount.

Token behavior:

- Mounted tokens remain valid until expiration.
- Kubernetes doesn't immediately revoke tokens from running Pods.
- Applications may experience authentication failures when tokens expire.

Recovery steps:

```bash
# Recreate the ServiceAccount
kubectl create serviceaccount myapp-sa

# Restart Pods to get new tokens
kubectl rollout restart deployment/myapp
```

## 131. When using anti-affinity rules, is it possible to create a "deadlock" where no new Pods can be scheduled?

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

## 132. If you have a Job with `parallelism: 3` and one Pod fails with `restartPolicy: Never`, will the Job create a replacement Pod?

**Answer:**

Yes, the Job controller will create a replacement Pod to maintain the desired parallelism level.

Job behavior with failures:

- **`restartPolicy: Never`:** Failed Pods are not restarted, but new Pods are created.
- **Parallelism maintenance:** The Job ensures the specified number of Pods are running.
- **Completion tracking:** The Job tracks successful completions vs. failures.

Example configuration:

```yaml
spec:
  parallelism: 3
  completions: 10
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: worker
        image: busybox
```

The Job keeps creating new Pods until it reaches the completion count or hits the backoff limit.

## 133. Can a Pod's resource requests be modified after creation, and what's the difference between requests and limits during OOM scenarios?

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

## 134. When using network policies, if you don't specify egress rules, are outbound connections blocked by default?

**Answer:**

Yes, when you create a NetworkPolicy that selects Pods but doesn't include egress rules, all outbound traffic from those Pods is blocked by default.

NetworkPolicy behavior:

- **No NetworkPolicy:** All traffic allowed (default).
- **NetworkPolicy with only ingress:** Egress remains open.
- **NetworkPolicy without an egress section:** All egress blocked.
- **Empty egress array:** All egress blocked.

Example blocking all egress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-egress
spec:
  podSelector:
    matchLabels:
      app: secure-app
  policyTypes:
  - Egress
  # No egress rules = deny all egress
```

## 135. If a Persistent Volume gets corrupted, can multiple PVCs bound to it cause cascading failures across different namespaces?

**Answer:**

Yes, if multiple PVCs from different namespaces are bound to the same corrupted PV, it can cause cascading failures.

Scenarios for cross-namespace impact:

- **Shared storage backend:** Multiple PVs on the same underlying storage.
- **ReadWriteMany volumes:** Multiple PVCs accessing the same PV.
- **Storage class dependencies:** Shared storage infrastructure.

Cascading failure patterns:

- **Data corruption spreads:** Applications in multiple namespaces fail.
- **Storage backend overload:** Performance decline affects all PVs.
- **Backup system failures:** Corrupt data propagates to backups.

Prevention strategies:

```yaml
# Use namespace-specific storage classes
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: namespace-a-storage
parameters:
  zone: us-west1-a
  type: pd-ssd
```

- Implement proper backup and disaster recovery.
- Use separate storage backends for critical namespaces.
- Monitor storage health across all namespaces.

## 136. Why does each layer of the Kubernetes tooling ecosystem exist, and what problem does each tool solve?

**Answer:**

Each tool in the Kubernetes ecosystem exists because the previous layer was not enough. The goal is not to collect tools but to understand the gap each one closes.

| Problem | Tool | What it fixed |
| --- | --- | --- |
| `kubectl` was painful at scale | **K9s** and **Lens** | Fast, visual cluster navigation and troubleshooting instead of raw commands |
| Manual deployment caused drift | **ArgoCD** | GitOps continuous reconciliation keeps the cluster matching Git |
| HPA only understood CPU | **KEDA** | Event-driven autoscaling on queues, custom metrics, and external triggers |
| Pod scaling without node scaling left Pods `Pending` | **Karpenter** | Just-in-time node provisioning to match pod demand |
| An open network was a risk | **Network Policies** | L3/L4 segmentation controlling which pods can talk to each other |
| Invisible traffic made debugging impossible | **Service Mesh** | mTLS, traffic management, and per-request monitoring data between services |
| Kubernetes Secrets were not secure enough | **Secrets Store CSI Driver** | Mounts secrets from external managers (Vault, AWS/Azure) instead of etcd base64 |
| No guardrails meant incidents | **Kyverno** | Policy-as-code admission control to validate, mutate, and enforce standards |
| No numbers meant no answers | **Prometheus** and **Grafana** | Metrics collection and dashboards for visibility |
| Metrics and logs could not connect the dots | **Jaeger** | Distributed tracing to follow a request across services |

Each layer addresses a limitation the previous one exposed: usability, delivery, scaling (pods, then nodes), security (network, secrets, policy), and observability (metrics, then traces).

That is how you stop collecting tools and start understanding them — by knowing the specific problem each one was adopted to solve.

## 137. What happens to a StatefulSet pod when its node goes into NotReady state? How is that different from a Deployment pod?

**Answer:**

The common answer — "the pod gets rescheduled" — is wrong for a StatefulSet, and it exposes someone who has never run stateful workloads in production.

When a node loses network connectivity, Kubernetes does not immediately know whether the node is dead or just temporarily unreachable, so it waits. By default it waits about five minutes before marking pods on that node as `Terminating`.

From there, StatefulSets and Deployments behave completely differently:

- **Deployment pod:** After the timeout, Kubernetes reschedules the pod on another node. The pod gets a new identity, a new IP, and life continues.
- **StatefulSet pod:** Kubernetes will **not** reschedule it automatically. The pod stays in `Terminating` indefinitely.

The reason is StatefulSet's core guarantee: no two pods with the same identity run at the same time. Suppose the node is not actually dead — it just lost network for a while.

If Kubernetes rescheduled `postgres-0` onto another node, you would now have two `postgres-0` instances both writing to the same data. That is a split-brain scenario, and it corrupts your database.

So Kubernetes deliberately does nothing and waits for a human to intervene.

In production this means you have to make a decision. Is the node actually dead? If yes, you force delete the pod:

```bash
kubectl delete pod postgres-0 --force --grace-period=0
```

If no, you wait for the node to come back. This is why stateful workloads on Kubernetes are complex — the safety guarantee that protects you from corruption is the same thing that keeps your pod stuck when a node dies.

I hit exactly this in a banking environment. A node went `NotReady` at 11pm and the on-call engineer, unaware of this behavior, waited for an automatic recovery that was never going to come.

We lost two hours before someone force deleted the pod. That production context is what the interviewer is really looking for.

## 138. Explain the difference between liveness, readiness, and startup probes. When does getting this wrong take down your production app?

**Answer:**

Everyone knows the definitions — liveness restarts the container if it fails, readiness removes the pod from Service endpoints if it fails, startup gates the other two until the app has initialized. The interviewer is testing whether you have seen what happens when these are configured wrong in production.

Three real scenarios:

**Scenario 1 — Liveness probe that is too aggressive.** Suppose your Java app takes 90 seconds to start, but the liveness probe begins checking at 10 seconds with a 5-second timeout. The app is still loading, does not respond, and liveness fails.

Kubernetes restarts the container, it starts loading again, liveness fails again, and you are in a `CrashLoopBackOff` that has nothing to do with the application being broken — the probe configuration is wrong.

The fix is a startup probe, which runs first and gives the slow app time to initialize; liveness and readiness only start after it succeeds:

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30   # 30 x 10s = 5 minutes to start
  periodSeconds: 10
```

**Scenario 2 — Readiness probe checking the wrong endpoint.** Suppose readiness checks `/health`, but the app marks itself ready before it finishes loading configuration from a remote config service.

Traffic starts hitting the pod, which serves requests with incomplete configuration, and users get wrong data or errors.

In production you want readiness to check a deeper endpoint that validates the app is *truly* ready — database connection pool initialized, config loaded, cache warmed — not just that the HTTP server started.

The difference between a shallow health check and a meaningful one is the difference between routing traffic to a broken pod or not.

**Scenario 3 — No readiness probe on a StatefulSet.** Suppose a Postgres StatefulSet with three replicas does a rolling upgrade. `pod-0` goes down, comes back, but has not finished replaying its WAL logs and is not ready for connections.

Without a readiness probe, Kubernetes has no way to know this — it marks the pod ready and routes traffic, and the application gets connection errors while Postgres is still recovering.

A proper readiness probe that checks whether Postgres is accepting connections keeps the pod out of the Service endpoints until it is actually ready.

Probe configuration is not a minor detail. It is what stands between a smooth deployment and a 2am incident.

## 139. What is a PodDisruptionBudget, and when does ignoring it cause a real production outage?

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

## 140. You have a memory leak in one of your microservices and the pod keeps getting OOMKilled. Walk me through how you would diagnose and fix it without taking down your production service.

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

## 141. What is the difference between RBAC and what Argo CD gives you for access control? Why do most production teams stop using raw RBAC for developer access?

**Answer:**

This question separates people who have worked in a real team from people who have only worked alone.

The textbook answer: RBAC is Kubernetes-native access control — Roles, ClusterRoles, RoleBindings. Give developers read access to their namespace, DevOps engineers full access, done.

That works on paper. In production with a real team it becomes painful fast.

Suppose you have 20 developers across four teams, each owning two microservices, plus five DevOps engineers who need full cluster access, plus product managers and stakeholders who want visibility without touching anything.

With raw RBAC you must create and manage Roles and RoleBindings for 25 people across multiple namespaces, distribute and manage their kubeconfig files, and repeat the whole dance whenever someone joins, leaves, or changes teams.

Manageable for five people; painful for 25; it does not scale.

The other problem is visibility. A developer who just wants to know whether their deployment went through needs `kubectl` access, which means learning `kubectl`, pod states, and deployment conditions.

Most developers do not want that — they want a dashboard that says green or red.

This is why, in my client's environment, we gave **Argo CD** access to the cluster, not the developers. Argo CD holds the cluster access; developers get access to the Argo CD dashboard only.

They can see their deployments, which version is running, whether a sync failed and why, and trigger a manual sync if needed.

All of that is controlled at the Argo CD level, not Kubernetes RBAC — no kubeconfig distribution, no RoleBinding per person, and stakeholders get read-only Argo CD access with zero Kubernetes exposure.

Argo CD also gives you drift protection that raw RBAC does not. If someone with `kubectl` access manually changes a deployment, raw RBAC leaves you blind until something breaks.

Argo CD immediately marks the app `OutOfSync` and can auto-heal it back to what is in Git. Git is the source of truth and nobody can override it silently.

That is the production answer — not just what RBAC is, but why teams move away from managing it manually and what they use instead.

## 142. Explain how Karpenter is different from Cluster Autoscaler. In 2026, why would you still choose Cluster Autoscaler?

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

## 143. What is etcd, and what actually happens to your cluster if it goes down?

**Answer:**

Everyone knows etcd is a key-value store. The real question is what breaks, and in what order, when etcd becomes unavailable.

When etcd goes down, your **existing workloads keep running**. Healthy pods on nodes continue, because the kubelet on each node is independent and does not need etcd to keep existing containers alive.

What stops working is everything that requires the control plane to make decisions:

- You cannot deploy anything new — the API server cannot write desired state, so it rejects all writes.
- You cannot scale, update a ConfigMap, or create a Secret.
- Any `kubectl` command that modifies cluster state fails.
- **Self-healing stops.** If a pod crashes while etcd is down, the controller manager cannot create a replacement. Your deployment said three replicas; one died; it stays dead until etcd comes back.

The dangerous part most people miss: etcd uses **Raft consensus**. A three-node etcd cluster needs two nodes for quorum.

Lose two of three and you lose quorum — now even reads start failing. The API server cannot read cluster state, `kubectl get` starts returning errors, and the cluster is read-only at best and completely unavailable at worst.

This is why etcd backup is not optional in production. In my client environment we took automated etcd snapshots every six hours and stored them in a separate S3 bucket in a different AWS region.

If you lose etcd data with no backup, you have lost your entire cluster state — you can see what is running from the pods, but Kubernetes has no record of desired state, and recovery without backups is extremely painful.

The answer the interviewer wants is not just what etcd is — it is that you understand the scope of impact of losing it and have a real backup and recovery plan.
