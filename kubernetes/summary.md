# Kubernetes Interview Preparation Summary

## 1. Containers and Kubernetes

Docker and other container runtimes run containers on a host. Kubernetes orchestrates containers across a cluster by declaring desired state, scheduling workloads, maintaining replicas, exposing services, managing configuration, and recovering from failures.

| Container runtime | Kubernetes |
| --- | --- |
| Runs containers | Orchestrates containerized workloads |
| Usually scoped to one host | Coordinates multiple nodes |
| Container lifecycle is managed directly | Controllers continuously reconcile desired state |
| Networking and scaling are configured manually | Provides service discovery, rollout, and scaling APIs |

Kubernetes still needs a CRI-compatible runtime such as containerd. Kubernetes is not a replacement for container images or runtimes.

## 2. Cluster Architecture

### 2.1 Control Plane

- **kube-apiserver:** Front end for Kubernetes API requests and the main communication hub.
- **etcd:** Strongly consistent key-value store containing cluster state.
- **kube-scheduler:** Assigns unscheduled Pods to suitable nodes.
- **kube-controller-manager:** Runs controllers that reconcile resources such as nodes, Deployments, and Jobs.
- **cloud-controller-manager:** Integrates supported cloud-provider capabilities.

### 2.2 Worker Node

- **kubelet:** Ensures the containers described by Pod specifications are running on its node.
- **Container runtime:** Pulls images and runs containers.
- **kube-proxy or eBPF data plane:** Implements Service networking, depending on the cluster network implementation.
- **CNI plugin:** Provides Pod networking and often NetworkPolicy enforcement.

If the control plane is temporarily unavailable, existing containers can keep running, but new scheduling, updates, and controller-driven recovery stop. A production cluster should use a highly available control plane.

## 3. Core Kubernetes Objects

### 3.1 Pod

A Pod is the smallest schedulable unit. Containers in one Pod share:

- One network namespace, Pod IP, and port space
- `localhost` connectivity
- Declared volumes
- Pod metadata and lifecycle

Two containers in the same Pod cannot bind the same IP and port at the same time.

### 3.2 Workload Controllers

| Object | Purpose |
| --- | --- |
| ReplicaSet | Maintains a desired number of matching Pods |
| Deployment | Manages stateless replicas and declarative rollouts |
| StatefulSet | Provides stable identities, ordered behavior, and per-Pod storage templates |
| DaemonSet | Runs a Pod on every eligible node or selected group of nodes |
| Job | Runs work to completion |
| CronJob | Creates Jobs on a schedule |

Deleting `app-1` from a StatefulSet recreates `app-1`; the other Pods are not renamed. Stable ordinals preserve network and storage identity.

DaemonSet Pods receive tolerations for several node conditions, but scheduling onto control-plane nodes normally requires an explicit toleration for the applicable control-plane taint.

### 3.3 Configuration Objects

- **ConfigMap:** Non-sensitive configuration.
- **Secret:** Sensitive data; base64 encoding is not encryption.
- **ServiceAccount:** Workload identity within the Kubernetes API.
- **Namespace:** Logical isolation and scope for namespaced resources.

Prefer an external secret manager and workload identity for production credentials. Apply encryption at rest, RBAC, audit logging, and least privilege.

## 4. Manifests and Desired State

A Kubernetes manifest is YAML or JSON describing the desired state of an API object.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: example/web:1.0.0
```

Common manifests define Deployments, StatefulSets, Services, Ingresses, ConfigMaps, Secrets, HPAs, Jobs, and NetworkPolicies.

## 5. Services and Application Networking

Detailed coverage has moved to `networking/kubernetes/summary.md`.

## 6. Storage

- **PersistentVolume (PV):** Cluster storage resource.
- **PersistentVolumeClaim (PVC):** Namespaced request for storage.
- **StorageClass:** Defines dynamic provisioning behavior.
- **VolumeSnapshot:** Snapshot API object when supported by the CSI driver.

Common access modes:

- `ReadWriteOnce` (RWO): read-write from a single node; multiple Pods on that node may be possible depending on the driver.
- `ReadWriteOncePod` (RWOP): read-write by one Pod.
- `ReadOnlyMany` (ROX): read-only from many nodes.
- `ReadWriteMany` (RWX): read-write from many nodes.

Zone-bound disks can prevent a StatefulSet Pod from mounting after scheduling into another zone. Use topology-aware StorageClasses, appropriate node affinity, and a tested backup/restore strategy.

A single PV is normally bound to one PVC. Cross-namespace failures are more commonly caused by multiple PVs using the same storage backend or by an RWX service failure, not multiple ordinary PVCs binding independently to one PV.

## 7. Scheduling

The scheduler filters and scores nodes using:

- Resource requests and allocatable capacity
- Node selectors and node affinity
- Pod affinity and anti-affinity
- Taints and tolerations
- Topology spread constraints
- Volume topology
- Pod priority and preemption

Required anti-affinity can make Pods unschedulable when there are too few eligible nodes or zones. Prefer soft rules when strict separation is not essential and monitor scheduling events.

When a node becomes unreachable, Pods usually receive default `NoExecute` tolerations for `not-ready` and `unreachable` conditions. Per-Pod `tolerationSeconds` can alter how long they remain bound. Exact behavior depends on cluster configuration and workload type.

## 8. Resource Management and Autoscaling

### 8.1 Requests and Limits

- **Request:** Used for scheduling and influences resource guarantees.
- **Limit:** Enforced maximum for memory and a throttling boundary for CPU.

A container exceeding its memory limit can be terminated as `OOMKilled`. During node pressure, QoS class, usage relative to requests, and Pod priority influence eviction.

Existing Pod specifications are generally replaced through their controller when resource settings change. In-place resize availability depends on the Kubernetes version, feature status, and cluster support; do not assume it is universally available.

### 8.2 Autoscaling

- **HPA:** Changes replica count using resource or custom/external metrics.
- **VPA:** Recommends or updates Pod resource sizing according to its mode.
- **Cluster Autoscaler:** Adds or removes nodes based on unschedulable Pods and utilization rules.

When HPA metrics are unavailable, scaling behavior depends on which metrics fail and available recommendations. Monitor HPA conditions rather than assuming every metrics failure freezes replicas.

## 9. Health Checks, Self-Healing, and Disruptions

- **Startup probe:** Protects slow-starting applications from premature liveness checks.
- **Readiness probe:** Controls whether a Pod receives Service traffic.
- **Liveness probe:** Restarts a container considered unhealthy.
- **PodDisruptionBudget:** Limits voluntary disruption to a replicated workload.

Readiness gates traffic; liveness should detect an unrecoverable process, not temporary dependency slowness. Poor probes are a common source of rollout downtime and restart loops.

## 10. Rollouts and Deployment Strategies

A Deployment rolling update gradually scales a new ReplicaSet up while scaling the old one down. `maxSurge` and `maxUnavailable` control capacity during the rollout.

For low-risk updates:

- Use multiple replicas across nodes/zones.
- Define realistic readiness and startup probes.
- Set resource requests.
- Use a PodDisruptionBudget and graceful shutdown.
- Configure `preStop` and sufficient termination grace where needed.
- Monitor the rollout and application metrics.
- Keep a tested rollback method.

If a Deployment is updated again during an active rollout, Kubernetes creates or uses a ReplicaSet for the newest Pod template and converges toward that latest state.

Blue-green and canary releases can be implemented with Services, multiple Deployments, Ingress/service-mesh routing, or progressive-delivery tools.

## 11. Jobs and Init Containers

Init containers run sequentially before application containers. If an init container fails with Pod `restartPolicy: Never`, the Pod fails and the main containers never start. A higher-level controller may create another Pod.

A Job maintains the requested parallelism and continues creating Pods until it reaches successful completions or a failure limit such as `backoffLimit`.

## 12. Security

Use layered controls:

- Strong identity integration and least-privilege RBAC
- Namespaces, quotas, and tenancy boundaries
- Pod Security Admission
- Non-root containers and restrictive security contexts
- Read-only root filesystems
- Dropped Linux capabilities and seccomp profiles
- Trusted, signed, and scanned images
- NetworkPolicies
- External secret stores and workload identity
- API audit logs and runtime monitoring
- Regular cluster and node-image upgrades

A security context can define `runAsUser`, `runAsGroup`, `fsGroup`, `allowPrivilegeEscalation`, capabilities, SELinux options, seccomp, privileged mode, and read-only filesystem settings.

Deleting a ServiceAccount does not necessarily terminate existing Pods immediately. Bound tokens are short-lived and refreshed; access will eventually fail when refresh or authorization no longer succeeds. New Pods referencing a missing ServiceAccount cannot be admitted.

## 13. Troubleshooting Workflow

Use a consistent order:

```bash
kubectl get pod <pod> -o wide
kubectl describe pod <pod>
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl logs <pod> --all-containers
kubectl logs <pod> --previous
kubectl get deploy,rs,svc,endpointslice,ingress
kubectl top pod
kubectl top node
```

### CrashLoopBackOff

Check current and previous logs, exit code, events, command/arguments, environment, mounted configuration, dependencies, probes, and OOM status. `kubectl port-forward` is unreliable while the container repeatedly crashes; use logs, an ephemeral debug container, or a stable Service target when appropriate.

### ImagePullBackOff

Check image name/tag, registry reachability, credentials, pull secrets, ServiceAccount configuration, architecture compatibility, and registry rate limits.

### Pending Pod

Check scheduling events, requests, affinity, taints, topology spread, quotas, pending PVCs, node selectors, and autoscaler status.

### Network or 503 Failure

See `networking/kubernetes/summary.md` for the investigation flow.

### NodeNotReady

Check kubelet and runtime health, certificates, disk/memory/PID pressure, CNI state, system logs, control-plane connectivity, and cloud instance health.

## 14. Backup, Restore, and Disaster Recovery

Protect:

- Cluster configuration and manifests
- Persistent application data
- etcd for self-managed control planes
- External dependencies, certificates, and secrets according to policy

Velero can back up Kubernetes resources and coordinate supported volume snapshots. Test restores regularly; an untested backup is not a recovery plan. Managed Kubernetes providers protect their control plane, but customers remain responsible for workload data and configuration recovery.

Multi-region recovery normally uses separate clusters, replicated data, independently deployable configuration, and DNS or global traffic management. One stretched control plane creates a large failure domain.

## 15. Monitoring and Observability

Monitor control-plane/API health, node conditions, Pod restarts, pending Pods, CPU/memory, disk and inode pressure, network errors, workload latency/errors, HPA conditions, and persistent storage.

Common stacks include Prometheus, Grafana, Alertmanager, cloud-native container insights, OpenTelemetry, and centralized log platforms. Correlate infrastructure metrics with application telemetry.

## 16. CI/CD and GitOps

A typical delivery flow builds and scans an image, publishes it to a registry, validates manifests or Helm charts, deploys to a lower environment, runs tests, and promotes an immutable version.

- **Push deployment:** CI credentials apply changes to the cluster.
- **Pull-based GitOps:** Argo CD or Flux reconciles cluster state from Git/OCI sources.

GitOps provides continuous reconciliation and drift visibility. Projects that combine Terraform, EKS/AKS, Helm, Jenkins, Argo CD/Flux, Prometheus, and Grafana demonstrate the full infrastructure-to-observability lifecycle.

## Production Microservices Design Checklist

A microservices platform should define clear service and data ownership, package each service in a small non-root image, and keep configuration separate from the image. Kubernetes Deployments, Services, Ingress, ConfigMaps, external secret integration, resource requests, and health probes form the basic workload contract.

Traffic design includes a supported ingress controller, TLS automation, authentication, rate limiting, and private service communication. A service mesh such as Istio or Linkerd is justified when workload identity, mTLS, traffic policy, or detailed service telemetry outweighs its additional operational cost.

Scaling must cover both Pods and nodes. HPA handles suitable utilization or application metrics, VPA recommends or changes resource sizing with restart considerations, KEDA handles event/queue-driven demand, and the cluster autoscaler supplies node capacity. Load testing must verify dependency limits and scale-down behavior.

Security includes namespace and RBAC boundaries, default-deny NetworkPolicies, Pod Security Admission, read-only/non-root containers, signed and scanned images, SBOMs, and secrets retrieved through workload identity. Observability combines Prometheus metrics, Grafana dashboards, structured logs through Fluent Bit/Loki or another log store, and OpenTelemetry/Jaeger traces with consistent service and request identifiers.


## 17. Advanced Interview Scenarios

Be ready to reason through:

1. Failed init containers and Pod restart policies
2. Stable StatefulSet Pod identities
3. DaemonSets, taints, and tolerations
4. Deployment changes during an active rolling update
5. Node failure detection and Pod eviction timing
6. Port conflicts between containers in one Pod
7. RWO vs. RWOP vs. RWX storage semantics
8. HPA behavior during metrics failures
9. Debugging containers in CrashLoopBackOff
10. ServiceAccount deletion and token rotation
11. Anti-affinity scheduling deadlocks
12. Job replacement Pods and failure limits
13. Requests, limits, OOM kills, and eviction
14. Default-deny egress NetworkPolicies
15. Shared storage failure domains

## 18. Interview Revision Checklist

- Kubernetes architecture and reconciliation
- Pods and workload controllers
- Manifests, ConfigMaps, Secrets, and ServiceAccounts
- Service types, Ingress, DNS, and NetworkPolicy
- PV, PVC, StorageClass, access modes, and topology
- Scheduling, affinity, taints, and disruption handling
- Requests, limits, HPA, VPA, and cluster autoscaling
- Probes, rolling updates, and rollback
- Security context, RBAC, admission, and image security
- Troubleshooting Pods, nodes, storage, and networking
- Backup, disaster recovery, monitoring, CI/CD, and GitOps

## 19. Advanced Production Scenarios

The detailed scenario answers are consolidated in `questions.txt`. For quick revision, group them into the following investigation areas.

### 19.1 Control Plane and Node Reliability

- For `NodeNotReady`, inspect node Conditions and Events, kubelet/container-runtime status, disk and memory pressure, certificates, time synchronization, CNI state, and API-server reachability. Cordon before repair and drain only when disruption budgets and replacement capacity allow it.
- For API-server overload, correlate request latency, inflight requests, audit logs, etcd latency, admission-webhook performance, and noisy controllers. Rate-limit or pause the offending client, then correct its list/watch, cache, pagination, and backoff behavior.
- For etcd corruption, protect quorum and evidence, use the distribution-supported member replacement or snapshot restore process, and validate API objects and controllers before accepting writes. Velero application backups do not replace etcd snapshots.
- Fleet upgrades should move from a representative staging cluster through controlled production waves. Check removed APIs and add-on compatibility, respect version skew, upgrade node pools gradually, and stop promotion when workload SLOs regress.

### 19.2 Workload Failures and Scheduling

- Start with `kubectl describe` Events, then current and previous logs. Distinguish image, configuration, command, dependency, probe, permission, scheduling, and resource failures before changing anything.
- `Pending` Pods require scheduler evidence: CPU or memory shortage, taints, affinity, quota, unbound PVC, topology, or autoscaler limits. Fix the reported constraint rather than deleting the Pod repeatedly.
- `Terminating` Pods require checking finalizers, preStop hooks, grace periods, attached storage, API reachability, and the responsible controller. Force deletion is a last resort after understanding state and data risk.
- For OOM, eviction, restart, and resource-leak incidents, compare requests and limits with observed use, node pressure, throttling, heap or file-descriptor growth, and application metrics. Right-size from load-test evidence and verify after rollout.

### 19.3 Security and Compliance

- Use identity-based least privilege, separate service accounts, Pod Security Admission, non-root/read-only containers, seccomp, approved signed images, default-deny network controls, encrypted secrets, and audit/runtime monitoring.
- A leaked secret must be revoked and rotated immediately; removing it from a log or Git file is not remediation. Investigate access, update consumers through an overlap period, verify the new value, and then revoke the old value.
- Certificate incidents require identifying the exact endpoint and owner, checking expiry, SAN, SNI, issuer, chain, and consumer reload. Automate renewal and alert well before expiry.
- Multi-tenant and multi-cluster designs need explicit isolation boundaries, quotas, policy enforcement, centralized identity and audit, and separate clusters where the risk boundary requires it.

### 19.4 Delivery, Scaling, and Cost

- Zero-downtime delivery depends on immutable versions, realistic readiness/startup probes, adequate surge capacity, graceful shutdown, compatible database changes, rollout monitoring, and a tested rollback—not only `RollingUpdate` settings.
- Canary and blue-green strategies promote releases using health and business metrics. Keep the old version available during the validation window and automate rollback when thresholds fail.
- HPA scales Pods, a node autoscaler supplies schedulable capacity, and event-driven scaling handles queue or custom demand. Validate metric freshness, resource requests, min/max limits, stabilization windows, dependency capacity, and scale-down behavior.
- Cost optimization combines usage evidence, right-sizing, autoscaling, appropriate node pools, spot capacity for tolerant workloads, log retention, storage lifecycle, quotas, schedules, and SLO verification after each change.

### 19.5 Stateful Workloads and Disaster Recovery

- Stateful failover must cover data replication, quorum, storage topology, fencing, leader election, DNS or traffic switching, and application consistency. StatefulSets alone do not provide database replication.
- For failed PV mounts, inspect PVC/PV/StorageClass, CSI Events and logs, access mode, topology, attachment state, quota, identity, and filesystem health. Do not force-detach or delete state until ownership and backups are verified.
- Disaster recovery begins with business-approved RTO/RPO. Protect manifests, cluster state, persistent data, secrets, certificates, DNS, identity, dependencies, and runbooks in another failure domain, then prove them through restore and failover exercises.
- Multi-region and multi-cloud recovery must control write ownership to avoid split brain and use tested weighted traffic or DNS cutover with an explicit rollback window.

### 19.6 Observability, Chaos, and Continuous Improvement

- Monitor availability, latency, errors, traffic, saturation, control-plane health, node pressure, scheduling, restarts, storage, DNS, and important business transactions using correlated metrics, structured logs, traces, and deployment events.
- Chaos experiments require a hypothesis, bounded blast radius, steady-state metrics, approval, abort conditions, and a rollback. Begin in non-production and use the findings to improve redundancy, timeouts, retries, alerts, and runbooks.
- After every incident, verify the real application path, remove temporary access or scaling, capture the root cause and contributing controls, assign preventive actions, and test that monitoring detects recurrence.

## 20. Screenshot Revision: Kubernetes Operating Model

### What happens after `kubectl apply`

`kubectl` submits a declarative object to the API server. Authentication, authorization, admission, and schema validation run before the desired state is persisted in etcd. Controllers observe the new state and create or update lower-level objects such as ReplicaSets. The scheduler assigns unscheduled Pods using resources, affinity, taints, topology, and policy. Kubelet on the selected node asks the container runtime through CRI to pull the image and start containers. Probes determine whether the container is alive and ready; Services and Ingress route only when endpoints and readiness are correct.

### Core object memory model

- Pod: smallest runnable unit; one or more tightly coupled containers.
- Deployment/ReplicaSet: stateless replicas, rollout, rollback, and desired count.
- StatefulSet: stable identity and storage orchestration; it does not itself replicate application data.
- DaemonSet: one Pod on every matching node, commonly agents and node services.
- Job/CronJob: finite or scheduled work.
- ConfigMap/Secret: non-secret configuration versus sensitive values; Secret objects still require encryption, RBAC, and safe delivery.
- PV/PVC/StorageClass: supplied storage, a workload claim, and dynamic provisioning policy.
- Namespace/RBAC: organizational and authorization boundaries; stronger multi-tenancy also needs policy, quotas, and network isolation.

### Autoscaling

HPA changes Pod replica count from CPU, memory, or custom/external metrics. VPA recommends or changes Pod resource sizing and may restart Pods. Cluster Autoscaler or the provider node autoscaler adds/removes worker-node capacity when Pods cannot schedule or nodes are underused. Metrics Server supplies common resource metrics; production scaling must also validate resource requests, min/max limits, stabilization, dependency capacity, startup time, and safe scale-down.

### Production-issue checklist

Repeated issue charts consolidate to one evidence-based flow:

- CrashLoopBackOff: inspect current/previous logs, exit code, command, configuration, probes, permissions, dependencies, and OOM evidence.
- ImagePullBackOff: verify image digest/tag, registry existence and reachability, architecture, pull secret/service account, CA/proxy, and node disk.
- Pending: read scheduler Events for resource shortage, taints, affinity, quota, topology, or unbound PVC.
- OOMKilled/high CPU or memory: measure Pod and node usage, throttling, requests/limits, GC/query/process behavior, traffic, HPA, and node pressure before scaling or tuning.
- NodeNotReady: inspect Conditions/Events, kubelet/runtime, disk/memory/PID pressure, certificates, time, CNI, and API connectivity; cordon before repair and drain only when safe.
- PVC Pending/mount failure: inspect PVC/PV/StorageClass, access mode, topology, CSI logs, identity, quota, and attachment state before any destructive storage action.

### Controlled cluster upgrade

Back up self-managed etcd and cluster configuration, confirm workload/backup health, review deprecated APIs and add-on compatibility, respect supported version skew, and rehearse in staging. Upgrade the control plane through the distribution/provider-supported procedure, then cordon and drain worker nodes one at a time while respecting PDBs and replacement capacity. Upgrade kubelet/runtime/node images and CNI/CSI/Ingress/DNS add-ons in their supported sequence. Verify nodes, system Pods, application transactions, SLOs, and rollback/recovery after every wave. Do not copy version numbers from a screenshot; select currently supported versions from the platform documentation.

## 21. API Request Lifecycle and Persistent Storage

### What happens after `kubectl apply -f app.yaml`

1. `kubectl` reads the manifest, resolves its API resource, and sends an authenticated request to the API server.
2. The API server performs authentication, authorization, schema/defaulting and admission checks, then persists accepted desired state in etcd.
3. Informers notify the relevant reconcilers. For a Deployment, its controller creates or updates a ReplicaSet, and the ReplicaSet controller creates Pods. For a Pod created directly, there is no workload controller in this creation path.
4. The scheduler watches unscheduled Pods and selects a node using resource requests, constraints, affinity, taints/tolerations, topology, and policy.
5. The selected node's kubelet observes the PodSpec and asks the container runtime through CRI to pull images and start containers. CNI configures networking and CSI mounts storage where required.
6. Kubelet reports status through the API server. Readiness controls whether Services send traffic; liveness and startup probes govern restart behavior.

When this flow fails, investigate the stage indicated by evidence: API/RBAC/admission errors, controller events, Pending scheduling events, image-pull failures, CNI/CSI errors, probe failures, or application logs. Start with `kubectl describe`, events, current and previous logs, and the owning controller rather than repeatedly deleting the Pod.

### PV, PVC, StorageClass, and Pod flow

A PersistentVolumeClaim is the workload's request for capacity, access mode, and optionally a StorageClass. A PersistentVolume represents storage made available to the cluster. A StorageClass and CSI driver can dynamically provision a suitable PV, after which the claim binds to it and the Pod mounts the claim:

```text
Pod -> PVC -> bound PV -> CSI-backed storage
```

The PV lifecycle is independent of an individual Pod, but data survival also depends on the reclaim policy, storage service, zone topology, backup, and restore design. In AKS, Azure Disk commonly fits single-node block storage and Azure Files supports shared file access; choose through workload access and performance requirements rather than assuming all persistent storage behaves the same.

## 22. Custom Resources and Controllers

A CRD adds a declarative resource type to the Kubernetes API with group, names, scope, served/storage versions and an OpenAPI schema. Kubernetes then provides persistence in etcd, API discovery, watch, labels, RBAC and standard `kubectl` interaction. A CRD alone does not create workload or cloud resources.

A custom controller watches desired custom objects and reconciles actual state through an idempotent loop. It manages owned resources or external APIs, records `status.observedGeneration` and Conditions, handles deletion through carefully designed finalizers, and retries transient failures with bounded backoff. Production design requires schema/version migration, least-privilege RBAC, leader election, metrics/logs/events, conflict handling, idempotent external operations and tests for restart, duplicate events, partial failure and deletion.

## 23. The Building Blocks Story: Why Each Concept Exists

Each Kubernetes concept exists because the previous one was not enough. This is the progression from a single Pod to a fully elastic, predictable cluster.

### You start with a Pod

A Pod runs your container. Simple, clean, done — until it crashes. Nobody restarts it; it is just gone. In production, that is not acceptable.

### So you use a Deployment

A Deployment watches your pods. One dies and it creates another. You want 3 running, it keeps 3 running. You want to scale to 10, one command does it. **Pods were too fragile for production. Deployment fixed that.**

### The problem: unstable Pod IPs

Every pod gets a new IP when it restarts. You have 3 pods running your app, and another service needs to talk to them. Which IP do you use? They keep changing. You cannot hardcode them or track them at scale.

### So you use a Service

A Service gives your app one stable IP address. It finds your pods using labels, not IPs. Pods die and come back with new IPs — the Service does not care, it always finds them. It also load balances: incoming traffic is distributed across all healthy pods automatically. **Pods had unstable IPs. Service fixed that.**

### The problem: external access (LoadBalancer Service)

Your app still needs to be accessible from the internet, so you use a **LoadBalancer Service**. This creates a real cloud load balancer (AWS ALB, Azure LB, GCP LB) and your app gets a public endpoint. It works perfectly — until you have 10 services. Now you have 10 load balancers, each costing money every month, even the 6 that handle almost no traffic. **LoadBalancer Services solved external access, but one per service does not scale.**

### So you use Ingress

One load balancer, all your services behind it. Ingress routes traffic based on rules: a request for `/api` goes to the API service, a request for `/dashboard` goes to the frontend service. One entry point, smart routing, one cloud load balancer on your bill. But Ingress is just a set of rules — something has to execute them.

### So you use an Ingress Controller

Nginx, Traefik, the AWS Load Balancer Controller — these are the actual engines that read your Ingress rules and make the routing happen. Ingress without a controller is just a config file nobody reads. **The Ingress Controller made the rules actually work.**

### The problem: configuration

Now your app is running, but it needs configuration — database URL, API keys, environment name, feature flags. So you hardcode them inside the container. It works on your laptop. You deploy to staging: wrong database URL. You deploy to production: wrong API key. You fix it by rebuilding the image every time config changes. In production, rebuilding an image to change a config value is not acceptable.

### So you use a ConfigMap

A ConfigMap holds your configuration outside the container. You inject it into your pod at runtime as environment variables or a mounted file. Change the ConfigMap, redeploy, and your app picks up the new values — the image never changes, the config does. The same image runs in dev, staging, and production with different configs. **Hardcoded config made your image environment-specific. ConfigMap fixed that.**

### The problem: secrets in plain text

Your database password is sitting in a ConfigMap. ConfigMaps are not encrypted, and anyone with basic `kubectl` access can read them. You just stored your production database credentials in plain text inside your cluster. That is not a mistake — that is a security incident.

### So you use a Secret

A Secret holds sensitive data: passwords, tokens, certificates, API keys. It is stored separately from ConfigMaps with its own access controls. Your app reads it at runtime; your image never sees it. You control who in the cluster can access which Secret. **ConfigMaps were not safe for sensitive data. Secrets fixed that.**

### The problem: manual scaling

Traffic starts growing and manual scaling breaks you. Some days 100 users, some days 10,000. You are running 3 pods; on a busy day all three are maxed out, responses are slow, requests time out. You jump on, bump it to 8 pods, crisis over. Traffic drops at night and 8 pods sit idle, wasting money. Next spike, you do it all over again. You cannot babysit your cluster every time traffic changes.

### So you use HPA (Horizontal Pod Autoscaler)

HPA watches your pods continuously. CPU goes above 70 percent, it adds more pods automatically. Traffic drops, it scales back down automatically. You define the minimum and maximum; Kubernetes does the rest. Your app handles the spike and you are not woken up at 2am to manually scale. **Manual scaling could not keep up with real traffic. HPA fixed that.**

### The problem: Pending pods with no node capacity

Scaling pods created a new problem. HPA adds pods during a traffic spike, but your nodes are full. The new pods sit in `Pending` state — they cannot be scheduled because there is no capacity. HPA did its job, but your cluster had nowhere to put the pods. Scaling pods without scaling nodes is half a solution.

### So you use Cluster Autoscaler or Karpenter

They watch for pods stuck in `Pending`. Not enough capacity? They add a new node automatically, pending pods get scheduled, and traffic is handled. Load drops, nodes sit underutilized, and they remove them automatically — you only pay for the compute you actually need. On EKS, Karpenter is the better choice: it is faster and more cost efficient, provisioning the exact right node for your workload instead of waiting for a fixed node group to scale. **HPA scaled your pods, Karpenter scaled your nodes — together they make your cluster truly elastic.**

### The problem: uncontrolled resource usage

One last problem, and it is the one that takes things down silently. Everything is scaling — pods coming up, nodes being added. One pod starts consuming 4GB of memory when it was never supposed to. Nobody told Kubernetes that, so it keeps consuming, starving every other pod on that node. Those pods start failing and a cascade begins. One rogue pod with no limits affects your entire node. An unpredictable cluster is an unreliable cluster.

### So you use Resource Requests and Limits

Requests tell Kubernetes the minimum your pod needs to be scheduled on a node. Limits tell Kubernetes the maximum it is ever allowed to consume. The scheduler places pods intelligently across nodes using requests, and limits make sure one noisy pod cannot take down everything around it. Your cluster runs predictably — every pod gets what it needs, nothing more. **Uncontrolled resource usage made your cluster unpredictable. Requests and Limits fixed that.**

### The problem: every pod restarts at once during a deploy

You deploy a new image and every pod restarts at the same time. For 30 seconds your app is completely down, users see errors, and your on-call phone starts ringing.

### So you use a RollingUpdate strategy

Kubernetes kills one pod, starts a new one, waits for it to be healthy, then moves to the next. Your users never notice the deploy happened. **A simultaneous restart caused downtime. RollingUpdate fixed that.**

### The problem: an unhealthy version still receives traffic

Your new version has a silent bug. Health checks pass but the app returns wrong data, and by the time you notice, the old version is completely gone.

### So you use a Readiness Probe

Kubernetes only sends traffic to a pod when it is actually ready to handle it. Bad pods stay out of rotation automatically. **A pod serving traffic before it was truly ready caused bad responses. Readiness probes fixed that.**

### The problem: a restarting pod loses all its data

Your database pod restarts and loses all its data. Containers are stateless — every restart is a fresh start with an empty disk. That is fine for your API, not fine for Postgres.

### So you use PersistentVolumes and PVCs

Storage exists outside the pod lifecycle. Your data survives crashes, restarts, and rescheduling. **Ephemeral container storage lost data. PersistentVolumes and PVCs fixed that.**

### The problem: stateful pods need a sticky, ordered identity

You have one database pod. It gets rescheduled to a different node and needs the same disk to follow it. PVCs work for Deployments, but ordered, sticky identities do not.

### So you use a StatefulSet

Each pod gets a stable name, a stable identity, and a stable volume that follows it. `pod-0` is always `pod-0`, not some random hash. **Deployments could not give stable identity. StatefulSets fixed that.**

### The problem: a run-once job keeps restarting

Your ML training job runs for 6 hours and you need exactly one run. A Deployment would keep restarting it forever after it finishes.

### So you use a Job

Kubernetes runs it to completion and stops. No restarts after success, no babysitting, one clean run. **Deployments could not model run-to-completion work. Jobs fixed that.**

### The problem: you need one pod on every node

You want a log collector or monitoring agent on every single node, but a Deployment does not guarantee one pod per node.

### So you use a DaemonSet

One pod lands on every node automatically, including new nodes Karpenter just added. No manual scheduling, no missed nodes. **Deployments could not guarantee per-node coverage. DaemonSets fixed that.**

### The problem: no access guardrails

Your team keeps accidentally deploying to the wrong namespace and wiping production configs. No guardrails — one bad `kubectl` command causes real damage.

### So you use RBAC

Roles define what actions are allowed. RoleBindings attach them to users or service accounts. Your junior dev can read logs but cannot delete deployments in prod. **Unrestricted access caused accidental damage. RBAC fixed that.**

### The problem: low-value work steals resources from critical work

You have a critical payment service and a batch analytics job on the same node. The batch job spikes and steals CPU from payments, tripling checkout latency during every report run.

### So you use PriorityClasses

Payment pods get high priority, batch pods get low. When nodes run out of resources, Kubernetes evicts the batch job first — not the thing making you money. **Equal treatment of unequal workloads caused contention. PriorityClasses fixed that.**

### The problem: one team starves a shared cluster

Three teams share one cluster and one team's runaway pods keep starving the others.

### So you use ResourceQuota

Each namespace gets a hard ceiling on CPU, memory, and object counts. One team cannot blow up the cluster for everyone else. **A shared cluster had no fairness boundaries. ResourceQuota fixed that.**

### The problem: Kubernetes does not understand your complex app

You need to run Kafka in Kubernetes. Kafka has brokers, topics, partition leadership, and a very specific idea of how it wants to be operated. StatefulSets alone do not know any of that.

### So you use a CRD

You teach Kubernetes what a Kafka cluster is. Now `kubectl` understands Kafka as a first-class object. But the CRD is just a schema — nobody acts on it. You create a `KafkaCluster` resource and nothing happens.

### So you add an Operator

It watches your custom resources and takes action — provisioning brokers, handling rebalancing, managing rolling upgrades. It encodes the operational knowledge a human expert would have. Strimzi does this for Kafka; the Prometheus Operator does it for monitoring stacks. **A CRD alone was just a schema. The Operator made it act.**

### The problem: the wrong pods land on expensive nodes

Your GPU nodes are expensive, but regular API pods keep landing on them — $8 per hour wasted serving JSON.

### So you use Taints and Tolerations

GPU nodes are tainted, so only pods that explicitly tolerate that taint can land there. Your API pods never touch the GPU nodes again. But toleration is just permission, not a guarantee — your ML pods *can* land on GPU nodes, but they might still end up on CPU nodes.

### So you add Node Affinity

Your ML pods now declare a hard requirement for nodes with the `gpu=true` label. Permission plus preference becomes a guarantee. **Taints kept the wrong pods off; Node Affinity pulled the right pods on.**

### The full story

| Concept | Problem it fixed |
| --- | --- |
| **Deployment** | A Pod ran your app but had no resilience |
| **Service** | Pods had unstable IPs |
| **Ingress** | One load balancer per service was too expensive |
| **Ingress Controller** | Ingress needed something to execute its rules |
| **ConfigMap** | Hardcoded config made images inflexible |
| **Secret** | ConfigMaps were not safe for sensitive data |
| **HPA** | Manual scaling could not keep up with traffic |
| **Cluster Autoscaler / Karpenter** | Pod scaling without node scaling left pods `Pending` |
| **Resource Requests and Limits** | Uncontrolled resource usage made clusters unpredictable |
| **RollingUpdate strategy** | Restarting every pod at once caused deploy downtime |
| **Readiness Probe** | Pods received traffic before they were truly ready |
| **PersistentVolumes / PVCs** | Ephemeral container storage lost data on restart |
| **StatefulSet** | Deployments could not give stable, ordered identity |
| **Job** | Deployments could not model run-to-completion work |
| **DaemonSet** | Deployments could not guarantee one pod per node |
| **RBAC** | Unrestricted access caused accidental damage |
| **PriorityClasses** | Low-value work stole resources from critical work |
| **ResourceQuota** | One team could starve a shared cluster |
| **CRD** | Kubernetes did not understand complex apps like Kafka |
| **Operator** | A CRD alone was just a schema; nobody acted on it |
| **Taints and Tolerations** | The wrong pods landed on expensive/special nodes |
| **Node Affinity** | Permission alone did not guarantee correct placement |

Each concept exists because the previous one was not enough. That is how you stop memorizing Kubernetes and start understanding it.

## 24. Traffic Routing on EKS: ALB, Ingress, Gateway API, API Gateway, Service Mesh, and Network Policies

ALB, Ingress, Gateway API, API Gateway, Service Mesh, and Network Policies all seem to route traffic, and the features overlap — most can do HTTP routing and TLS termination, and several use Nginx or Envoy as the engine. The clarity comes not from "what does it do" but from "why does it exist." Each layer was born to solve a production problem the previous setup could not handle.

**2026 context:** In March 2026, Ingress NGINX moved into formal retirement (no more security patches). Kubernetes 1.36 (released April 22, 2026) marks the shift to **Gateway API** as the official successor to Ingress. Ingress itself is not deprecated, but new investment should go to Gateway API.

### ALB vs a LoadBalancer Service

Your service runs in a pod. You can hit it from inside the cluster, but nobody outside can reach it. So you create a **LoadBalancer Service** and Kubernetes provisions a real cloud load balancer with a public URL. It works perfectly — until you have 10 services and 10 cloud load balancers, each on your AWS bill every month. **LoadBalancer Service solved external access, but one per service does not scale.**

So you put one **AWS Application Load Balancer (ALB)** in front of everything. ALB is an AWS-managed load balancer that runs outside your cluster and routes to many services by path or host — `/api/products` to the product service, `/api/orders` to the order service. One AWS load balancer instead of ten. The catch: you configure the ALB through the AWS Console or Terraform, so developers cannot ship a new microservice without an infrastructure ticket, and the routing rules (outside the cluster) drift from the cluster's YAML. **ALB cut costs, but it took routing control away from your team.**

### Kubernetes Ingress and the Ingress Controller

Ingress is a Kubernetes resource that defines routing rules in YAML. Developers commit an Ingress file alongside their service code, so routing lives where the code lives. But Ingress is just a config file — something has to read and execute it. That something is the **Ingress Controller**: Nginx Ingress, Traefik, or the AWS Load Balancer Controller.

On EKS, most teams use the **AWS Load Balancer Controller**. You write Ingress YAML; the controller talks to AWS and provisions an ALB with the right rules automatically. You get the cost benefit of one ALB and the YAML-first control of Kubernetes. **ALB without Ingress was unmanageable from the cluster side. Ingress fixed that.**

### Why Gateway API exists (Ingress limitations)

Ingress was the default for ten years, but it had limits:

- It only handled HTTP and HTTPS. Routing TCP or UDP needed vendor-specific extensions.
- Advanced features (canary deployments, traffic splitting, header-based routing) required many annotations, and each controller had its own syntax — migrating meant rewriting all of them.
- The platform team and application team shared the same Ingress resource, with no clean ownership separation.
- As of March 2026, Ingress NGINX is no longer maintained.

So the Kubernetes community built **Gateway API**.

### What Gateway API is and how it differs from Ingress

Gateway API is the official successor to Ingress (GA in November 2023, with adoption accelerating through 2025–2026). It splits the old Ingress resource into three role-oriented pieces:

- **GatewayClass** — defines the type of underlying infrastructure. The platform team owns this.
- **Gateway** — the actual entry point; listens on ports and handles TLS. Cluster operators manage these.
- **HTTPRoute** (and **TCPRoute**, **GRPCRoute**) — the actual routing rules. Application developers own these.

Each team manages what it should, with no argument about who owns the Ingress. Gateway API also supports L4 protocols natively (TCP, UDP, gRPC) and has built-in traffic splitting and header-based routing without annotations. On EKS, the AWS Load Balancer Controller supports Gateway API as of 2026: you write Gateway and HTTPRoute resources, the controller provisions an ALB, and you get the same cost benefits as Ingress with a cleaner model.

**Guidance:** For a new EKS project in 2026, use Gateway API. If you run Ingress in production today, you have time — Ingress is stable and not deprecated — but the future investment is Gateway API.

### Service mesh: service-to-service traffic

Now your microservices talk to each other inside the cluster via ClusterIP Services. It works until something fails, and then you have no idea which call broke or whether pod-to-pod traffic was even encrypted. Some pods retry forever, some give up immediately, and every team writes retry logic differently. You want mTLS between every service, consistent retries, and distributed tracing.

So you install a **service mesh** — Istio, Linkerd, or Consul. It injects a sidecar proxy into every pod; all pod-to-pod traffic goes through the sidecar, which handles mTLS, retries, timeouts, tracing, and traffic splitting. Application code stays clean while the mesh handles the plumbing. **Service-to-service traffic was a black box. Service mesh fixed that.**

### Network Policies: locking down pod-to-pod traffic

By default, any pod can talk to any other pod — your frontend pod can reach your payments database, your build pod can reach your auth service. If one pod is compromised, the attacker can move laterally to anything.

So you use **Network Policies** — a Kubernetes resource defining which pods can talk to which. You write "only the order service can reach the payments database" and "the frontend can only reach the API Gateway." Compromised pods cannot reach what they should not. **A flat cluster network was a security risk. Network Policies fixed that.**

### API Gateway: managing what your APIs do

Your platform works — internal traffic is meshed, network policies lock things down, external traffic comes in through Gateway API. Then the business launches a mobile app, a partner wants API access, a third-party developer wants to integrate. Now you need API keys, per-customer rate limits, and centralized JWT validation. If you add auth and rate-limiting code to every service, six microservices become six different implementations of the same thing, and per-customer limits (Customer A: 1000 req/sec, Customer B: 100, free tier: 10) get scattered everywhere.

So you add an **API Gateway** — Kong, APISIX, AWS API Gateway, or Tyk. It sits between your Gateway/Ingress and your microservices and handles everything that is not business logic: API key validation, JWT validation, per-customer rate limiting, request transformation, response caching, usage analytics. A request comes in, the gateway checks the API key, sees the customer's plan allows 1000 req/sec, and forwards to the right service. **API-level concerns scattered across services made the platform fragile. API Gateway fixed that.**

### Gateway API vs API Gateway (do I need both?)

The names are almost identical but they are not the same thing:

- **Gateway API** is a Kubernetes specification for routing traffic. It replaces Ingress and handles north-south routing *into* the cluster.
- **API Gateway** is an architectural pattern for API management — auth, rate limiting, API keys, transformations, analytics.

You can implement an API Gateway *using* Gateway API resources (Kong and Envoy Gateway support both), but Gateway API on its own does not give you API key management or per-customer rate limits — that is API Gateway territory. The simple rule: **Gateway API gets traffic into the cluster; API Gateway manages what your APIs do once it is in.** In 2026 the line is blurring (Kong, Envoy Gateway, and APISIX do both), but conceptually they solve different problems.

### Production patterns on EKS

There are three real patterns, each fitting a different stage of your platform.

**Pattern 1 — Internal app or simple frontend.** A React frontend and a few microservices behind it; the frontend is the only client. No third-party API consumers, no API keys.

```text
Internet → AWS ALB → Gateway API (ALB Controller) → Microservices
```

The AWS Load Balancer Controller provisions the ALB from your Gateway and HTTPRoute resources. One YAML, one AWS bill. This is what ~80% of EKS workloads look like — no API Gateway, no service mesh. **The trap:** engineers add an Nginx "API Gateway" Deployment here because a tutorial said so. It is a reverse proxy with extra steps and a monthly cost.

**Pattern 2 — Public APIs for mobile or third-party clients.** Now you have a mobile app and partners integrating. You need API keys, per-customer rate limits, and centralized JWT validation.

```text
Internet → AWS ALB → Gateway API → API Gateway (Kong / APISIX / Envoy Gateway) → Microservices
```

Gateway API still gets traffic into the cluster; what is new is the API Gateway between it and your services (deployed in-cluster as a Deployment with 2+ replicas). Customer A gets 1000 req/sec, Customer B gets 100, free tier gets 10 — none of that logic touches your microservices. Most teams skip this until they have already polluted every service with auth code, then spend a quarter ripping it out.

**Pattern 3 — Scale, with internal traffic too.** Mobile clients hit public APIs, the frontend hits internal APIs, and services talk constantly. You need different policies for different traffic and observability across all of it.

```text
Internet
   ↓
AWS ALB (TLS, WAF)
   ↓
Gateway API
   ↓
   ├─→ /api/public/*   → API Gateway → Microservices (with Istio sidecars)
   └─→ /api/internal/* ─────────────→ Microservices (with Istio sidecars)
                                              ↑
                                     Network Policies enforce
                                     pod-to-pod access rules
```

Public traffic goes through the API Gateway (auth, rate limits, transformations). Internal frontend traffic skips the gateway — it is trusted, latency-sensitive, and needs no API key validation. Service-to-service traffic goes through the service mesh (mTLS, distributed tracing). Network Policies enforce who can talk to whom across the cluster. Each layer does one job well.

### How to know which pattern you need

Ask one question: **who is calling your APIs?**

- Only your own frontend → **Pattern 1**.
- A mobile app or third-party clients → **Pattern 2**.
- 50+ services where you care about mTLS, distributed tracing, and zero-trust networking → **Pattern 3**.

Most teams skip Pattern 1 because they read a microservices blog, then over-engineer toward Pattern 3 because they read a Netflix blog. The right answer is almost always one step simpler than what you think you need.

### Common mistakes (get the names right)

- A Nginx Deployment routing traffic is **not** an API Gateway. It is a reverse proxy.
- An Ingress Controller is **not** a load balancer. It is a router that sits behind one.
- A service mesh is **not** an API Gateway. It handles east-west (service-to-service) traffic; API Gateway handles north-south (internet-to-service) traffic.
- Network Policies are **not** a firewall. They are pod-level traffic rules enforced by your CNI.

### Should I migrate from Ingress to Gateway API in 2026?

- **New EKS project:** yes — use Gateway API from day one.
- **Running Ingress with the AWS Load Balancer Controller:** you have time. Ingress is stable and not deprecated; AWS supports both.
- **Using Ingress NGINX specifically:** plan your migration — the project is in retirement as of March 2026 with no more security patches.

The migration path is straightforward: Ingress and Gateway API can run side by side. Move new services to Gateway API and migrate old ones one at a time.

### Frequently asked questions

- **Is API Gateway the same as Kubernetes Ingress?** No. Ingress (and its successor Gateway API) is a Kubernetes resource for routing external traffic to services. API Gateway is a pattern for API-level concerns like authentication, rate limiting, and API keys. Both can route HTTP, but they solve different problems.
- **Is API Gateway the same as Gateway API?** No, despite the near-identical names. Gateway API is a Kubernetes specification that replaces Ingress. API Gateway is an architectural pattern. You can implement an API Gateway using Gateway API resources, but they are not the same thing.
- **Do I need both ALB and Ingress on EKS?** Yes. ALB is the AWS-managed load balancer; Ingress (or Gateway API) is the Kubernetes resource that tells the AWS Load Balancer Controller how to configure the ALB. They work together.
- **Is Ingress NGINX deprecated?** It entered formal retirement in March 2026. It still works, but no new security patches will be released. Plan migration to Gateway API or another supported Ingress Controller.
- **Can I use AWS API Gateway with EKS?** Yes, via a Network Load Balancer or VPC Link. But most EKS teams prefer in-cluster API Gateways like Kong, APISIX, or Envoy Gateway because they are easier to configure with Kubernetes-native tools.
- **Do I need a service mesh if I have an API Gateway?** They solve different problems. API Gateway handles north-south traffic (internet to your services); service mesh handles east-west traffic (service to service). Most teams need both at scale.
- **What is the difference between Gateway API and API Gateway in Kubernetes?** Gateway API is a Kubernetes specification for routing external traffic into the cluster (it replaces Ingress). API Gateway is a pattern handling authentication, rate limiting, and API management. Some tools (Kong, Envoy Gateway) implement both.

### Takeaway

Each layer between your user and your pod exists because the previous setup was not enough:

- **ALB** gets traffic to your cluster.
- **Gateway API (or Ingress)** gets traffic into your services.
- **Service Mesh** secures and observes pod-to-pod traffic.
- **Network Policies** enforce who can talk to whom.
- **API Gateway** manages what your public APIs do.
