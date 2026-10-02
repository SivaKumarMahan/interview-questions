# Kubernetes: Architecture and Fundamentals

> Cluster architecture, control plane, etcd, the API request flow, core objects, namespaces, CRDs/operators, and cross-topic revision checklists.

## Key Concepts

### Interview Revision Checklist

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

### Operations and Stateful Workloads Summary

For pod failures, inspect pod status, description, current and previous logs, and recent events. In AKS monitoring, applications expose metrics, Prometheus discovers and stores them, Grafana displays them, and Alertmanager routes alerts. HPA scales pods, Cluster Autoscaler scales nodes, and VPA adjusts pod resource requests. StatefulSets are used when pods need stable names and their own persistent storage, but they require careful planning for zones, backups, upgrades, and recovery.

### Containers and Kubernetes

Docker and other container runtimes run containers on a host. Kubernetes orchestrates containers across a cluster by declaring desired state, scheduling workloads, maintaining replicas, exposing services, managing configuration, and recovering from failures.

| Container runtime | Kubernetes |
| --- | --- |
| Runs containers | Orchestrates containerized workloads |
| Usually scoped to one host | Coordinates multiple nodes |
| Container lifecycle is managed directly | Controllers continuously reconcile — bring the actual state in line with the desired state |
| Networking and scaling are configured manually | Provides service discovery, rollout, and scaling APIs |

Kubernetes still needs a CRI-compatible runtime such as containerd. Kubernetes is not a replacement for container images or runtimes.

### Control Plane

- **kube-apiserver:** Front end for Kubernetes API requests and the main communication hub.
- **etcd:** Strongly consistent key-value store containing cluster state.
- **kube-scheduler:** Assigns unscheduled Pods to suitable nodes.
- **kube-controller-manager:** Runs controllers that reconcile resources such as nodes, Deployments, and Jobs.
- **cloud-controller-manager:** Integrates supported cloud-provider capabilities.

### Worker Node

- **kubelet:** Ensures the containers described by Pod specifications are running on its node.
- **Container runtime:** Pulls images and runs containers.
- **kube-proxy or eBPF data plane:** Implements Service networking, depending on the cluster network implementation.
- **CNI plugin:** Provides Pod networking and often NetworkPolicy enforcement.

If the control plane is temporarily unavailable, existing containers can keep running, but new scheduling, updates, and controller-driven recovery stop. A production cluster should use a highly available control plane.

### Operations Notes

- `kubelet` runs on each node. It reconciles the Pod specs assigned to that node with the container runtime — it keeps what's actually running in line with what was requested. `kubectl` is just the client CLI; it is not a control-plane component. Metrics Server supplies the resource metrics behind `kubectl top` and, usually, HPA.
- A highly available control plane needs multiple API servers behind a load balancer and an odd-numbered healthy etcd quorum. Worker-node failure causes Pods to be evicted/rescheduled after node-health timeouts; the exact behavior depends on controllers, PDBs, storage and scheduling capacity.

### What happens after `kubectl apply`

`kubectl` submits a declarative object to the API server. Authentication, authorization, admission, and schema validation run before the desired state is persisted in etcd.

Controllers observe the new state and create or update lower-level objects such as ReplicaSets. The scheduler assigns unscheduled Pods using resources, affinity, taints, topology, and policy.

Kubelet on the selected node asks the container runtime through CRI to pull the image and start containers. Probes determine whether the container is alive and ready; Services and Ingress route only when endpoints and readiness are correct.

### What happens after `kubectl apply -f app.yaml`

1. `kubectl` reads the manifest, resolves its API resource, and sends an authenticated request to the API server.
2. The API server performs authentication, authorization, schema/defaulting and admission checks, then persists accepted desired state in etcd.
3. Informers notify the relevant reconcilers. For a Deployment, its controller creates or updates a ReplicaSet, and the ReplicaSet controller creates Pods. For a Pod created directly, there is no workload controller in this creation path.
4. The scheduler watches unscheduled Pods and selects a node using resource requests, constraints, affinity, taints/tolerations, topology, and policy.
5. The selected node's kubelet observes the PodSpec and asks the container runtime through CRI to pull images and start containers. CNI configures networking and CSI mounts storage where required.
6. Kubelet reports status through the API server. Readiness controls whether Services send traffic; liveness and startup probes govern restart behavior.

When this flow fails, investigate the stage indicated by evidence: API/RBAC/admission errors, controller events, Pending scheduling events, image-pull failures, CNI/CSI errors, probe failures, or application logs.

Start with `kubectl describe`, events, current and previous logs, and the owning controller rather than repeatedly deleting the Pod.

### Pod

A Pod is the smallest schedulable unit. Containers in one Pod share:

- One network namespace, Pod IP, and port space
- `localhost` connectivity
- Declared volumes
- Pod metadata and lifecycle

Two containers in the same Pod cannot bind the same IP and port at the same time.

### Configuration Objects

- **ConfigMap:** Non-sensitive configuration.
- **Secret:** Sensitive data; base64 encoding is not encryption.
- **ServiceAccount:** Workload identity within the Kubernetes API.
- **Namespace:** Logical isolation and scope for namespaced resources.

Prefer an external secret manager and workload identity for production credentials. Apply encryption at rest, RBAC, audit logging, and least privilege (only the permissions needed).

### Core object memory model

- Pod: smallest runnable unit; one or more tightly coupled containers.
- Deployment/ReplicaSet: stateless replicas, rollout, rollback, and desired count.
- StatefulSet: stable identity and storage orchestration; it does not itself replicate application data.
- DaemonSet: one Pod on every matching node, commonly agents and node services.
- Job/CronJob: finite or scheduled work.
- ConfigMap/Secret: non-secret configuration versus sensitive values; Secret objects still require encryption, RBAC, and safe delivery.
- PV/PVC/StorageClass: supplied storage, a workload claim, and dynamic provisioning policy.
- Namespace/RBAC: organizational and authorization boundaries; stronger multi-tenancy also needs policy, quotas, and network isolation.

### Manifests and Desired State

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

### Namespaces

A Namespace is a logical scope within one Kubernetes cluster. It organizes resources by team, application, tenant or environment and enables namespace-scoped RBAC, ResourceQuota, LimitRange, NetworkPolicy and name isolation.

The same resource name can exist in separate namespaces, so `dev/nginx`, `qa/nginx` and `production/nginx` do not conflict.

```bash
kubectl get pods -n dev
kubectl get pods -n qa
kubectl get pods -n production
```

Namespaces are not strong security boundaries by themselves. Pods can normally communicate across namespaces through Services such as `api.payments.svc.cluster.local`; use enforced ingress and egress NetworkPolicies, workload identity and least-privilege RBAC to allow only the required paths.

Cluster-scoped objects such as Nodes, PersistentVolumes and StorageClasses are not namespaced.

### Custom Resources and Controllers

A CRD adds a declarative resource type to the Kubernetes API with group, names, scope, served/storage versions and an OpenAPI schema. Kubernetes then provides persistence in etcd, API discovery, watch, labels, RBAC and standard `kubectl` interaction.

A CRD alone does not create workload or cloud resources.

A custom controller watches desired custom objects and reconciles actual state to match them, through a loop that is idempotent — safe to run again and again without causing harm.

It manages owned resources or external APIs, records `status.observedGeneration` and Conditions, handles deletion through carefully designed finalizers, and retries temporary failures with limited backoff.

Production design requires schema/version migration, least-privilege RBAC, leader election, metrics/logs/events, conflict handling, idempotent external operations, and tests for restart, duplicate events, partial failure, and deletion.

### The Building Blocks Story: Why Each Concept Exists

Each Kubernetes concept exists because the previous one was not enough. This is the progression from a single Pod to a fully elastic, predictable cluster.

#### You start with a Pod

A Pod runs your container. Simple, clean, done — until it crashes. Nobody restarts it; it is just gone. In production, that is not acceptable.

#### So you use a Deployment

A Deployment watches your pods. One dies and it creates another. You want 3 running, it keeps 3 running. You want to scale to 10, one command does it. **Pods were too fragile for production. Deployment fixed that.**

#### The problem: unstable Pod IPs

Every pod gets a new IP when it restarts. You have 3 pods running your app, and another service needs to talk to them. Which IP do you use? They keep changing. You cannot hardcode them or track them at scale.

#### So you use a Service

A Service gives your app one stable IP address. It finds your pods using labels, not IPs.

Pods die and come back with new IPs, but the Service always finds them. It also distributes incoming traffic across all ready Pods.

**The problem was unstable Pod IPs. A Service provides a stable address and load balancing.**

#### The problem: external access (LoadBalancer Service)

Your app still needs to be accessible from the internet, so you use a **LoadBalancer Service**. This creates a real cloud load balancer (AWS ALB, Azure LB, GCP LB) and your app gets a public endpoint.

It works perfectly — until you have 10 services. Now you have 10 load balancers, each costing money every month, even the 6 that handle almost no traffic. **LoadBalancer Services solved external access, but one per service does not scale.**

#### So you use Ingress

One load balancer, all your services behind it. Ingress routes traffic based on rules: a request for `/api` goes to the API service, a request for `/dashboard` goes to the frontend service.

One entry point, smart routing, one cloud load balancer on your bill. But Ingress is just a set of rules — something has to execute them.

#### So you use an Ingress Controller

Nginx, Traefik, the AWS Load Balancer Controller — these are the actual engines that read your Ingress rules and make the routing happen. Ingress without a controller is just a config file nobody reads. **The Ingress Controller made the rules actually work.**

#### The problem: configuration

Now your app is running, but it needs configuration — database URL, API keys, environment name, feature flags. So you hardcode them inside the container.

It works on your laptop. You deploy to staging: wrong database URL.

You deploy to production: wrong API key. You fix it by rebuilding the image every time config changes.

In production, rebuilding an image to change a config value is not acceptable.

#### So you use a ConfigMap

A ConfigMap holds your configuration outside the container. You inject it into your pod at runtime as environment variables or a mounted file.

Change the ConfigMap, redeploy, and the application receives the new values without rebuilding the image. The same image can run in Development, Staging, and Production with different configuration.

**The problem was environment-specific configuration inside the image. A ConfigMap keeps normal configuration outside it.**

#### The problem: secrets in plain text

Your database password is sitting in a ConfigMap. ConfigMaps are not encrypted, and anyone with basic `kubectl` access can read them.

You just stored your production database credentials in plain text inside your cluster. That is not a mistake — that is a security incident.

#### So you use a Secret

A Secret holds sensitive data: passwords, tokens, certificates, API keys. It is stored separately from ConfigMaps with its own access controls.

Your application reads the Secret at runtime, so the image never contains the value. RBAC controls which users and service accounts can read it.

**The problem was sensitive data in a ConfigMap. A Secret provides a separate object with access controls, although it still needs encryption and careful RBAC.**

#### The problem: manual scaling

Traffic starts growing and manual scaling breaks you. Some days 100 users, some days 10,000.

You are running 3 pods; on a busy day all three are maxed out, responses are slow, requests time out. You jump on, bump it to 8 pods, crisis over.

Traffic drops at night and 8 pods sit idle, wasting money. Next spike, you do it all over again.

You cannot babysit your cluster every time traffic changes.

#### So you use HPA (Horizontal Pod Autoscaler)

HPA watches your pods continuously. CPU goes above 70 percent, it adds more pods automatically.

Traffic drops, it scales back down automatically. You define the minimum and maximum; Kubernetes does the rest.

Your app handles the spike and you are not woken up at 2am to manually scale. **Manual scaling could not keep up with real traffic. HPA fixed that.**

#### The problem: Pending pods with no node capacity

Scaling pods created a new problem. HPA adds pods during a traffic spike, but your nodes are full.

The new pods sit in `Pending` state — they cannot be scheduled because there is no capacity. HPA did its job, but your cluster had nowhere to put the pods.

Scaling pods without scaling nodes is half a solution.

#### So you use Cluster Autoscaler or Karpenter

They watch for pods stuck in `Pending`. Not enough capacity?

They add a new node automatically, pending pods get scheduled, and traffic is handled. Load drops, nodes sit underutilized, and they remove them automatically — you only pay for the compute you actually need.

On EKS, Karpenter is the better choice: it is faster and more cost efficient, provisioning the exact right node for your workload instead of waiting for a fixed node group to scale. **HPA scaled your pods, Karpenter scaled your nodes — together they make your cluster truly elastic.**

#### The problem: uncontrolled resource usage

One last problem, and it is the one that takes things down silently. Everything is scaling — pods coming up, nodes being added.

One pod starts consuming 4GB of memory when it was never supposed to. Nobody told Kubernetes that, so it keeps consuming, starving every other pod on that node.

Those pods start failing and a cascade begins. One rogue pod with no limits affects your entire node.

An unpredictable cluster is an unreliable cluster.

#### So you use Resource Requests and Limits

Requests tell Kubernetes the minimum your pod needs to be scheduled on a node. Limits tell Kubernetes the maximum it is ever allowed to consume.

The scheduler uses requests when placing Pods on nodes. Limits stop a container from using more than its allowed amount, although memory limits can cause `OOMKilled` and CPU limits can cause throttling.

**The problem was uncontrolled resource use. Requests support scheduling, and limits provide a boundary.**

#### The problem: every pod restarts at once during a deploy

You deploy a new image and every pod restarts at the same time. For 30 seconds your app is completely down, users see errors, and your on-call phone starts ringing.

#### So you use a RollingUpdate strategy

Kubernetes kills one pod, starts a new one, waits for it to be healthy, then moves to the next. Your users never notice the deploy happened. **A simultaneous restart caused downtime. RollingUpdate fixed that.**

#### The problem: an unhealthy version still receives traffic

Your new version has a silent bug. Health checks pass but the app returns wrong data, and by the time you notice, the old version is completely gone.

#### So you use a Readiness Probe

Kubernetes only sends traffic to a pod when it is actually ready to handle it. Bad pods stay out of rotation automatically. **A pod serving traffic before it was truly ready caused bad responses. Readiness probes fixed that.**

#### The problem: a restarting pod loses all its data

Your database pod restarts and loses all its data. Containers are stateless — every restart is a fresh start with an empty disk. That is fine for your API, not fine for Postgres.

#### So you use PersistentVolumes and PVCs

Storage exists outside the pod lifecycle. Your data survives crashes, restarts, and rescheduling. **Ephemeral container storage lost data. PersistentVolumes and PVCs fixed that.**

#### The problem: stateful pods need a sticky, ordered identity

You have one database pod. It gets rescheduled to a different node and needs the same disk to follow it. PVCs work for Deployments, but ordered, sticky identities do not.

#### So you use a StatefulSet

Each pod gets a stable name, a stable identity, and a stable volume that follows it. `pod-0` is always `pod-0`, not some random hash. **Deployments could not give stable identity. StatefulSets fixed that.**

#### The problem: a run-once job keeps restarting

Your ML training job runs for 6 hours and you need exactly one run. A Deployment would keep restarting it forever after it finishes.

#### So you use a Job

Kubernetes runs it to completion and stops. No restarts after success, no babysitting, one clean run. **Deployments could not model run-to-completion work. Jobs fixed that.**

#### The problem: you need one pod on every node

You want a log collector or monitoring agent on every single node, but a Deployment does not guarantee one pod per node.

#### So you use a DaemonSet

One pod lands on every node automatically, including new nodes Karpenter just added. No manual scheduling, no missed nodes. **Deployments could not guarantee per-node coverage. DaemonSets fixed that.**

#### The problem: no access guardrails

Your team keeps accidentally deploying to the wrong namespace and wiping production configs. No guardrails — one bad `kubectl` command causes real damage.

#### So you use RBAC

Roles define what actions are allowed. RoleBindings attach them to users or service accounts. Your junior dev can read logs but cannot delete deployments in prod. **Unrestricted access caused accidental damage. RBAC fixed that.**

#### The problem: low-value work steals resources from critical work

You have a critical payment service and a batch analytics job on the same node. The batch job spikes and steals CPU from payments, tripling checkout latency during every report run.

#### So you use PriorityClasses

Payment pods get high priority, batch pods get low. When nodes run out of resources, Kubernetes evicts the batch job first — not the thing making you money. **Equal treatment of unequal workloads caused contention. PriorityClasses fixed that.**

#### The problem: one team starves a shared cluster

Three teams share one cluster and one team's runaway pods keep starving the others.

#### So you use ResourceQuota

Each namespace gets a hard ceiling on CPU, memory, and object counts. One team cannot blow up the cluster for everyone else. **A shared cluster had no fairness boundaries. ResourceQuota fixed that.**

#### The problem: Kubernetes does not understand your complex app

You need to run Kafka in Kubernetes. Kafka has brokers, topics, partition leadership, and a very specific idea of how it wants to be operated. StatefulSets alone do not know any of that.

#### So you use a CRD

You teach Kubernetes what a Kafka cluster is. Now `kubectl` understands Kafka as a first-class object. But the CRD is just a schema — nobody acts on it. You create a `KafkaCluster` resource and nothing happens.

#### So you add an Operator

It watches your custom resources and takes action — provisioning brokers, handling rebalancing, managing rolling upgrades. It encodes the operational knowledge a human expert would have.

Strimzi does this for Kafka; the Prometheus Operator does it for monitoring stacks. **A CRD alone was just a schema. The Operator made it act.**

#### The problem: the wrong pods land on expensive nodes

Your GPU nodes are expensive, but regular API pods keep landing on them — $8 per hour wasted serving JSON.

#### So you use Taints and Tolerations

GPU nodes are tainted, so only pods that explicitly tolerate that taint can land there. Your API pods never touch the GPU nodes again.

But toleration is just permission, not a guarantee — your ML pods *can* land on GPU nodes, but they might still end up on CPU nodes.

#### So you add Node Affinity

Your ML pods now declare a hard requirement for nodes with the `gpu=true` label. Permission plus preference becomes a guarantee. **Taints kept the wrong pods off; Node Affinity pulled the right pods on.**

#### The full story

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

### Production Microservices Design Checklist

A microservices platform should define clear service and data ownership, package each service in a small non-root image, and keep configuration separate from the image.

Kubernetes Deployments, Services, Ingress, ConfigMaps, external secret integration, resource requests, and health probes form the basic workload contract.
Traffic design includes a supported ingress controller, TLS automation, authentication, rate limiting, and private service communication. A service mesh such as Istio or Linkerd is justified when workload identity, mTLS, traffic policy, or detailed service monitoring data outweighs its additional operational cost.
Scaling must cover both Pods and nodes. HPA handles suitable utilization or application metrics, VPA recommends or changes resource sizing with restart considerations, KEDA handles event/queue-driven demand, and the cluster autoscaler supplies node capacity.

Load testing must verify dependency limits and scale-down behavior.

Security includes namespace and RBAC boundaries, default-deny NetworkPolicies, Pod Security Admission, read-only/non-root containers, signed and scanned images, SBOMs, and secrets retrieved through workload identity.

Observability combines Prometheus metrics, Grafana dashboards, structured logs through Fluent Bit/Loki or another log store, and OpenTelemetry/Jaeger traces with consistent service and request identifiers.

### Advanced Interview Scenarios

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

## Interview Questions

### 1. How confident are you in Kubernetes & Docker? (rating question) *(asked in interview round)*

Give an honest self-rating and back it up with real work. For example: *"8/10 — I run production EKS clusters: writing manifests and Helm charts, HPA/VPA autoscaling, RBAC, network policies, and troubleshooting incidents like CrashLoopBackOff, pending pods, and node pressure."* Avoid claiming a perfect 10/10. A number backed by concrete examples is always more convincing.

### 2. Explain Kubernetes architecture.

**Answer:**

Kubernetes has two parts: a control plane and worker nodes. The API server is the front door. It authenticates requests, checks permissions, validates the data, and exposes the cluster API.

etcd stores the desired and current state of the cluster.

The scheduler picks a node for each new Pod. The controller managers continuously reconcile objects like Deployments and Nodes — that means they keep checking the actual state and pushing it back toward the desired state.

On each worker node, kubelet watches the Pods assigned to it and tells a container runtime, such as containerd, to run them. A CNI plugin handles Pod networking. Service routing is handled by kube-proxy or, in newer setups, an eBPF data plane.

Here's the flow end to end. You run `kubectl apply`, which sends the desired state to the API server. The API server saves that state. The Deployment controller creates a ReplicaSet and Pods. The scheduler binds the Pods to nodes. Kubelet runs them. The controllers keep reconciling in the background.

In a managed service like EKS or AKS, the cloud provider runs the control plane for you. You still own the nodes, the workloads, and the configuration, and you still have to design for high availability yourself.

### 3. What happens when `kubectl apply` runs?

```bash
kubectl apply -f deployment.yaml
```

1. `kubectl` reads the YAML and prepares the API request.
2. The request goes to the Kubernetes API Server.
3. The API Server authenticates and authorizes the request.
4. Admission controllers and validation are applied.
5. The desired state is stored in `etcd`.
6. Controllers reconcile the desired state - for a Deployment, the Deployment Controller creates or updates a ReplicaSet.
7. The Scheduler assigns new Pods to suitable worker nodes.
8. The Kubelet on the selected node asks the container runtime to pull the image and start the container.
9. The CNI configures Pod networking.
10. Readiness checks determine when the Pod can start receiving traffic.

```text
kubectl apply
  -> API Server
  -> etcd
  -> Deployment Controller
  -> ReplicaSet
  -> Scheduler
  -> Kubelet
  -> Container Runtime
  -> Pod Running
```

#### Short interview answer

`kubectl apply` sends the manifest to the API Server, which authenticates the request, runs it through admission controllers, and persists the desired state in `etcd`. From there, the relevant controller (e.g. the Deployment Controller) reconciles that state into a ReplicaSet, the Scheduler places the resulting Pods on suitable nodes, and the Kubelet on each node pulls the image and starts the container - with the CNI wiring up networking and readiness checks gating when traffic actually starts flowing.

### 4. What are the roles of kubelet, kube-apiserver, and kube-proxy in EKS?

**Answer:**

In EKS, AWS runs the highly available API server for you. It's the front door for every request, and it handles authentication, authorization, admission, and validation.

Kubelet runs on each worker node. It registers the node, reports its status, and makes sure the containers in its assigned Pods match their specs by talking to the container runtime. Kube-proxy sets up the networking rules that translate a Service's stable virtual IP into the actual Pod IPs behind it. Some CNI or eBPF setups replace this function.

If the API server becomes unreachable, existing containers usually keep running. But scheduling, exec and log access, status updates, and controller actions all degrade.

When I troubleshoot this, I check node status, the kubelet journal, EKS control-plane logs, security groups, routes, DNS, certificate and IAM authentication, and the health of CNI and kube-proxy.

I cordon an unstable node before doing any corrective work on it.

### 5. What are Pods, Deployments, and Services?

**Answer:**

A Pod is the smallest schedulable unit in Kubernetes. It holds one or more tightly coupled containers that share the same IP address, port space, and any declared volumes.

A Deployment declares a stateless Pod template and a replica count. It manages ReplicaSets underneath, which gives you self-healing, rolling updates, and rollback.

A Service selects Pods by label and gives them a stable DNS name and IP, even though the Pods themselves come and go and their addresses change.

For example, say three API Pods are controlled by a Deployment, and a ClusterIP Service called `orders-api` selects the label `app: orders`. Clients call the Service's DNS name, and EndpointSlices keep track of which Pods are currently ready.

During a rollout, the Deployment creates new Pods, readiness gates when they start receiving traffic through the Service, and the old Pods terminate gradually.

I verify all of this with `kubectl get deploy,rs,pods,svc,endpointslice`, rollout status, events, and a test request from a debug Pod.

### 6. What is a ConfigMap and what is a Secret?

**Answer:**

A ConfigMap stores non-sensitive configuration — key/value pairs or whole files. A Secret stores sensitive data, but by default it's only base64-encoded, not encrypted — encoding is not the same as encryption. Both can be exposed to a Pod as environment variables or as mounted volumes.

I keep the application image immutable, meaning it doesn't change after it's built, and separate from the environment configuration. I never put passwords in ConfigMaps or in Git. Production secrets come from a system like Vault, AWS Secrets Manager, or Azure Key Vault, using workload identity and tools like External Secrets or a Secrets Store CSI driver where possible.

I also turn on encryption at rest, use least-privilege RBAC, meaning roles that grant only the access someone actually needs, enable audit logging, rotate credentials, and isolate secrets by namespace.

Updating an environment variable requires the Pod to be recreated. A mounted, projected file may refresh on its own, but the application still has to reread it. When troubleshooting, I check the object and key names, the namespace, the volume or event, permissions, the rendered value without printing the secret itself, and whether consumers of the value have been rolled out.

### 7. What are ConfigMap, Secret, ServiceAccount and Namespace in Kubernetes?

**Quick definitions:**

- **ConfigMap:** non-sensitive configuration.
- **Secret:** sensitive data; base64 encoding is not encryption.
- **ServiceAccount:** workload identity within the Kubernetes API.
- **Namespace:** logical isolation and scope for namespaced resources.

#### 12.1 What is a ConfigMap?

> "A ConfigMap is used to store non-sensitive configuration data separately from the application. This allows us to change configuration without rebuilding the container image."

Examples of data stored in a ConfigMap:

- Application URLs
- Port numbers
- Feature flags
- Environment names
- Log levels

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
```

The application can consume this as environment variables, mounted files, or command-line arguments.

#### 12.2 What is a Secret?

> "A Secret stores sensitive information such as passwords, API keys, database credentials, and certificates. Kubernetes stores Secret values as Base64-encoded data, but Base64 is only an encoding mechanism, not encryption. For stronger security, Secrets should be encrypted at rest and integrated with external secret managers like Azure Key Vault or HashiCorp Vault."

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQ=
```

The pod can consume the Secret as environment variables or mounted files.

**Follow-up: Is a Kubernetes Secret encrypted?**

> "By default, Secret values are Base64 encoded, which is not secure because anyone can decode them. In production, we enable encryption at rest in etcd and often integrate Kubernetes with Azure Key Vault or another external secrets manager."

#### 12.3 What is a ServiceAccount?

> "A ServiceAccount provides an identity for a pod when it communicates with the Kubernetes API. Instead of using a user's credentials, applications running inside pods use a ServiceAccount to authenticate and authorize API requests."

Examples:

- Reading ConfigMaps
- Listing Pods
- Accessing Secrets (if permitted)
- Interacting with the Kubernetes API

A ServiceAccount works together with RBAC (Role and RoleBinding) to define what actions the pod is allowed to perform.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
```

Assign it to a pod:

```yaml
spec:
  serviceAccountName: app-sa
```

**Follow-up: Why not use the default ServiceAccount?**

> "The default ServiceAccount often has broader permissions than required. Following the principle of least privilege, I create dedicated ServiceAccounts with only the permissions the application needs."

#### 12.4 What is a Namespace?

> "A Namespace is a logical partition within a Kubernetes cluster. It isolates resources, allowing multiple teams or environments to share the same cluster without resource name conflicts."

For example:

```
Cluster
│
├── dev
│     ├── pods
│     ├── services
│
├── test
│     ├── pods
│     ├── services
│
└── prod
      ├── pods
      ├── services
```

Each namespace can have its own Pods, Services, ConfigMaps, Secrets, resource quotas and RBAC policies.

**Follow-up: Can two namespaces have pods with the same name?**

Yes.

```
dev/nginx
prod/nginx
```

These are different resources because they belong to different namespaces.

#### 12.5 Difference table

| Resource | Purpose | Contains |
|---|---|---|
| ConfigMap | Store non-sensitive configuration | URLs, ports, feature flags |
| Secret | Store sensitive data | Passwords, API keys, certificates |
| ServiceAccount | Identity for pods | Authentication to Kubernetes API |
| Namespace | Logical isolation | Groups and isolates resources |

#### 12.6 One-line interview summary

- **ConfigMap** -> stores non-sensitive configuration.
- **Secret** -> stores sensitive data; Base64 encoding is not encryption.
- **ServiceAccount** -> provides a pod's identity to access the Kubernetes API.
- **Namespace** -> logically isolates resources within a cluster for different teams or environments.

### 8. Why does each layer of the Kubernetes tooling ecosystem exist, and what problem does each tool solve?

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

### 9. What is etcd, and what actually happens to your cluster if it goes down?

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

### 10. In K8s, as etcd is a key-value store DB, can we write something manually to it?

Yes, you can write data manually to etcd in Kubernetes, but it's generally not a good idea.

- etcd is the backing store for all cluster data in Kubernetes. Modifying its contents by hand can leave the cluster inconsistent or unstable.
- If you do need to interact with etcd directly, use the `etcdctl` command-line tool.
- Make sure the `etcdctl` version you use matches your etcd server version.
- Back up your etcd data before making any changes.

Here's a basic example of how to interact with etcd using `etcdctl`:

```bash
# Set environment variables for etcdctl
export ETCDCTL_API=3
export ETCDCTL_ENDPOINTS=https://<etcd-server-ip>:2379
export ETCDCTL_CACERT=/path/to/ca.crt
export ETCDCTL_CERT=/path/to/client.crt
export ETCDCTL_KEY=/path/to/client.key

# Put a key-value pair
etcdctl put mykey "myvalue"

# Get a value by key
etcdctl get mykey

# Delete a key
etcdctl del mykey
```

Remember, direct manipulation of etcd should be done with extreme caution and typically only in advanced scenarios where you fully understand the implications. In most cases, it is better to use `kubectl` and Kubernetes APIs to manage cluster state.

### 11. There are 1 master and 3 worker nodes. If the master fails, what happens? Will pods keep running or will they crash?

**What happens if the master fails:**

The pods already running on the worker nodes keep running normally. Worker nodes and their `kubelet` processes keep the containers alive on their own.

But no new pods can be scheduled and no changes can be applied, because:
- The scheduler is down.
- The API server is unreachable.
- The control plane can't make any decisions.

So the cluster is temporarily frozen. Workloads keep running, but nothing management-related works — no deployments, no scaling, no restarts if a node crashes.

The fix is a highly available control plane: run multiple master nodes spread across zones, for example three masters. That way, if one master fails, the cluster keeps working normally.

### 12. What happens if the firewall between the Kubernetes master node and worker nodes gets broken?

**Impact:**

- API server becomes inaccessible.
- kubelet can't communicate with the master.
- Pod scheduling stops.
- Service discovery fails.
- Existing pods may continue running but can't be managed.

**Recovery steps:**

- Restore firewall rules for the required ports (6443, 10250, 2379-2380, etc.).
- Check component health: API server, etcd, kubelet.
- Restart cluster components if needed.
- Verify node communication with `kubectl get nodes`.
- Test pod creation and service connectivity.

### 13. How do you enter a running Pod, and what is the correct way to define Kubernetes objects?

**Answer:**

I identify the namespace, Pod, and container, and run only the command I actually need:

```bash
kubectl get pods -n payments
kubectl exec -it -n payments api-7d9f6 -c api -- /bin/sh
```

A minimal image might not even have a shell, so I use an approved ephemeral debug container with `kubectl debug` instead. I avoid installing tools or permanently changing configuration inside a running container, since those changes aren't tracked anywhere and just disappear the moment it restarts.

Objects are declared with `apiVersion`, `kind`, `metadata`, and `spec`, then reviewed and applied through GitOps or `kubectl apply -f`. I validate manifests with a server-side dry-run, schema and policy checks, and a diff, then verify the rollout and application health afterward.

CRDs extend the API with entirely new object types. A StorageClass, by the way, is a specific storage-provisioning object — not a general-purpose Kubernetes "class" of anything.

### 14. What is the command to access a pod, and how can you define or create a Kubernetes object?

To access a pod in Kubernetes, you can use the `kubectl exec` command. This command allows you to run commands inside a running pod.

**1. First, get the name of the pod you want to access:**

```bash
kubectl get pods
```

**2. Once you have the pod name, use the following command to access it:**

```bash
kubectl exec -it <pod-name> -- /bin/bash
```

Replace `<pod-name>` with the actual name of your pod. The `-it` flags allow you to interactively access the pod's shell.

**Defining/creating a Kubernetes object:**

In Kubernetes, every resource like a Pod, Deployment, or Service is an **object** in the Kubernetes API. These objects are defined in YAML manifests with fields like `apiVersion`, `kind`, `metadata`, and `spec`.

Here's an example of a simple Pod object using a YAML file:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: my-container
    image: nginx
    ports:
    - containerPort: 80
```

Save this YAML content to a file named `my-pod.yaml` and then create the Pod using:

```bash
kubectl apply -f my-pod.yaml
```

This command will create the Pod in your Kubernetes cluster based on the specifications defined in the YAML file.

**What is a Kubernetes "class"?**

In Kubernetes, there isn't a concept specifically called a "Kubernetes class." However, you might be referring to **Custom Resource Definitions (CRDs)** or **Storage Classes**:

- **Custom Resource Definitions (CRDs)** allow you to define your own resource types in Kubernetes, enabling you to extend the Kubernetes API.
- **Storage Classes** define different types of storage (like SSDs, HDDs) that can be dynamically provisioned for Persistent Volumes in Kubernetes.

### 15. What is the difference between `kubectl exec` and `kubectl run`?

**`kubectl exec`** - runs a command inside an *existing* Pod's container.

```bash
kubectl exec -it nginx-pod -- /bin/bash
kubectl exec -it nginx-pod -- /bin/sh
kubectl exec nginx-pod -- ls /app
kubectl exec nginx-pod -- env
kubectl exec -it nginx-pod -c app-container -- /bin/bash
```

`-it` attaches an interactive terminal; `-c` selects a specific container in a multi-container Pod.

**`kubectl run`** - creates a *new*, standalone Pod, mainly for quick testing/debugging.

```bash
kubectl run nginx --image=nginx
kubectl run ubuntu --image=ubuntu -it -- /bin/bash
kubectl run debug --image=busybox -it --rm -- sh
kubectl run test --image=busybox -- sleep 3600
```

The `--rm` flag in the `debug` example is worth calling out specifically - it deletes the Pod automatically once the interactive session ends, which is the standard pattern for a throwaway debug Pod that doesn't linger in the cluster.

#### Short interview answer

`kubectl exec` runs a command inside a Pod that's already running - useful for inspecting a live application. `kubectl run` creates a brand-new standalone Pod, which is mainly useful for spinning up a temporary debug/test Pod (often with `--rm` so it cleans itself up) rather than working with an existing workload.

### 16. What is a CustomResourceDefinition (CRD), and when would you create one?

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

### 17. What is a custom Kubernetes controller, and how does its reconciliation (making actual state match desired state) loop work?

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

### 18. How do you design a Kubernetes operator?

**Answer:**

I define a versioned CRD spec to capture what the user wants, and a status with conditions to capture what's actually happening.

The controller watches the custom resource and the objects it owns, and reconciles them idempotently: fetch the object, handle deletion or a finalizer, compute what's actually needed, create or update the owned objects, check their readiness, update the status and `observedGeneration`, and requeue with a backoff — meaning it waits a bit longer between each retry.

I use owner references for anything Kubernetes should clean up automatically, least-privilege RBAC, conflict and retry handling, events, metrics, and logs, leader election, rate limits, and validation, defaulting, or conversion webhooks only when they're actually needed. Calls to external systems need idempotency keys — something that makes it safe to repeat the same call — and a cleanup or finalizer timeout.

Tests cover reconciling the same state repeatedly, partial failure, deletion, an upgrade or schema conversion, and a dependency outage — not just the happy path. A good operator encodes the real lifecycle of its domain, not just a wrapper around a Deployment.
