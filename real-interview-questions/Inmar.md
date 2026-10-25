# Inmar - Interview Questions

## Kubernetes

<details><summary>Q1. If pods are OOMKilled, what is the issue, and what will you do to fix it?</summary>

**OOMKilled** means "Out Of Memory Killed". The container tried to use **more memory than its memory limit**, so the Linux kernel killed it. Kubernetes then restarts the container, and if it keeps happening, the pod goes into `CrashLoopBackOff`.

### How to confirm it

```bash
kubectl get pods -n dev
# NAME                  READY  STATUS             RESTARTS
# springboot-app-7d9f   0/1    CrashLoopBackOff   6

kubectl describe pod springboot-app-7d9f -n dev
```

In the output, look for:

```text
Last State:     Terminated
  Reason:       OOMKilled
  Exit Code:    137
Limits:
  memory:       512Mi
```

**Exit code 137** = the process was killed with signal 9 (`SIGKILL`), which is what the OOM killer sends.

Then check the memory trend and the logs from before the crash:

```bash
kubectl top pod -n dev
kubectl logs springboot-app-7d9f -n dev --previous
```

In Grafana or Azure Monitor, check `container_memory_working_set_bytes` for the pod: does memory jump suddenly (traffic spike) or grow slowly until it hits the limit (memory leak)?

### Common causes

| Cause | Example |
| --- | --- |
| Memory limit too low | The app genuinely needs 1 GiB, but the limit is 512 MiB |
| JVM not aligned with the container limit | Java heap (`-Xmx`) is set close to or above the container limit, leaving no room for non-heap memory |
| Memory leak | Memory grows steadily over hours until the pod is killed |
| Traffic spike | Too many requests per pod; each request holds data in memory |
| Large in-memory work | Loading a full file or a big query result into memory |

**Not the same as eviction:** if the **node** runs out of memory, the kubelet **evicts** pods (status `Evicted`). OOMKilled is about the **container's own limit**.

### How to fix

1. **Right-size the memory** based on real usage (monitoring or VPA recommendations), with some headroom:

   ```yaml
   resources:
     requests:
       memory: "1Gi"
     limits:
       memory: "1Gi"   # same as request for predictable memory
   ```

2. **Align the JVM with the container** (for Java apps). Let the JVM size the heap as a percentage of the container limit:

   ```yaml
   env:
     - name: JAVA_TOOL_OPTIONS
       value: "-XX:MaxRAMPercentage=75.0 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp"
   ```

3. **If it is a leak**, increasing memory only delays the crash. Take a heap dump, analyze it (Eclipse MAT, VisualVM), and fix the code (unclosed connections, caches without size limits, etc.).
4. **If it is a traffic spike**, use HPA to add more pods so each pod handles less load.
5. **Set alerts** on pod restarts and memory usage close to the limit, so you find out before users do.

### Interview answer

> "OOMKilled means the container used more memory than its limit, so the kernel killed it, and we see exit code 137 in `kubectl describe pod`. I first check the memory trend in Grafana or Azure Monitor. If memory jumps with traffic, I scale out with HPA or increase the limit. If it grows slowly, it's probably a memory leak, so I take a heap dump and get the code fixed instead of just adding memory. For Java apps, I make sure the heap is sized with `MaxRAMPercentage` so the JVM stays within the container limit. Finally, I set the requests and limits based on real usage and add alerts on restarts."

</details>

---

<details><summary>Q2. What are some examples of stateful and stateless applications?</summary>

**Stateless:** the application does **not keep any data inside itself** between requests. Any pod can handle any request, and if a pod dies, a new one can replace it with no data loss.

**Stateful:** the application **stores data that must survive** restarts, and each instance often has its own identity and its own disk.

### Examples

| Stateless | Stateful |
| --- | --- |
| React/Angular frontend served by Nginx | Databases: MySQL, PostgreSQL, MongoDB, SQL Server |
| Spring Boot REST API (sessions kept in Redis or JWT) | Message brokers: Kafka, RabbitMQ |
| API gateway | Elasticsearch |
| Azure Functions (HTTP trigger) | Redis with persistence enabled |
| Image resizing / PDF generation service | Jenkins (job history in `JENKINS_HOME`) |

### Simple example

Online shopping site:

- The **product API** reads products from the database and returns them. It stores nothing itself, so it is **stateless**. Run 3 or 30 copies, and any copy can answer.
- The **database** stores orders and users. It is **stateful**. If you lose its disk, you lose the orders.

### In Kubernetes

| | Stateless | Stateful |
| --- | --- | --- |
| Workload type | Deployment | StatefulSet |
| Pod names | Random (`api-7d9f-x2k`) | Stable (`mongo-0`, `mongo-1`) |
| Storage | None, or shared | Own PVC per pod |
| Scaling | Easy, any order | Ordered, one by one |

**Best practice:** keep applications stateless and move the state to managed services (Azure SQL, Azure Cache for Redis, Storage). Then scaling, rolling updates, and recovery become simple.

### Interview answer

> "A stateless application keeps no data between requests, so any instance can serve any request. Examples are a React frontend or a Spring Boot REST API that keeps sessions in Redis. A stateful application stores data that must survive restarts, like MySQL, MongoDB, Kafka, or Elasticsearch. In Kubernetes, I run stateless apps as Deployments and stateful apps as StatefulSets with a PVC per pod. Where possible, I keep the apps stateless and put the state in managed services like Azure SQL or Azure Cache for Redis."

</details>

---

<details><summary>Q3. How do you use a LoadBalancer type Service in Kubernetes?</summary>

A `LoadBalancer` Service exposes the application **outside the cluster** using the cloud's load balancer. In AKS, Kubernetes asks Azure to create a rule on an **Azure Load Balancer** with an IP address, which sends traffic to the pods.

### Service types compared

| Type | Reachable from | Use case |
| --- | --- | --- |
| ClusterIP (default) | Inside the cluster only | Backend APIs, databases |
| NodePort | `<NodeIP>:30000-32767` | Testing, rarely in production |
| LoadBalancer | An external (or internal VNet) IP | Exposing a service directly, non-HTTP traffic |

### Example: public LoadBalancer

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-lb
  namespace: dev
spec:
  type: LoadBalancer
  selector:
    app: frontend
  ports:
    - port: 80          # port on the load balancer
      targetPort: 8080  # port on the container
```

```bash
kubectl apply -f service.yaml
kubectl get svc frontend-lb -n dev --watch
# NAME          TYPE           CLUSTER-IP    EXTERNAL-IP     PORT(S)
# frontend-lb   LoadBalancer   10.0.120.15   <pending>       80:31234/TCP
# frontend-lb   LoadBalancer   10.0.120.15   20.81.45.120    80:31234/TCP
```

After a minute, `EXTERNAL-IP` changes from `<pending>` to a public IP. `curl http://20.81.45.120` reaches the app.

### Example: internal LoadBalancer (only inside the VNet)

For services that only other VNet resources or on-premises systems should reach:

```yaml
metadata:
  name: backend-internal-lb
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
```

### Flow

```text
User --> Azure Load Balancer (public IP:80)
             |
             v
         AKS node --> kube-proxy rules --> frontend pod (8080)
```

### When to use Ingress instead

Each LoadBalancer Service gets its **own IP and load-balancer rule**. With 10 web services, that means 10 IPs. For HTTP/HTTPS, it is better to use **one Ingress controller** (NGINX or Application Gateway for Containers) with a single IP that routes by host or path, and handles TLS in one place. Use LoadBalancer for non-HTTP traffic (TCP/UDP, such as databases or MQTT) or for the Ingress controller itself.

### If EXTERNAL-IP stays `<pending>`

```bash
kubectl describe svc frontend-lb -n dev
```

Look at Events. A common cause in AKS is that the cluster identity lacks **Network Contributor** permission on the VNet subnet or public IP resource group.

### Interview answer

> "A LoadBalancer Service exposes pods outside the cluster. In AKS, when I create it, the cloud controller manager creates an Azure Load Balancer rule and public IP, and traffic goes to the pods behind the Service. For services that should be reachable only inside the VNet, I add the `azure-load-balancer-internal` annotation. For HTTP apps, I usually prefer one Ingress controller instead of a LoadBalancer per service, to save IPs and manage TLS in one place. If the external IP stays pending, I check the Service events and the cluster identity's network permissions."

</details>

---

<details><summary>Q4. What is the cloud controller manager?</summary>

The **cloud-controller-manager (CCM)** is a control-plane component that **connects Kubernetes to the cloud provider's APIs** (Azure, AWS, GCP). It lets Kubernetes create and manage cloud resources, such as load balancers, automatically.

Kubernetes itself does not know how to create an Azure Load Balancer. The CCM does that translation.

### What it does

| Controller inside CCM | What it does | Example in AKS |
| --- | --- | --- |
| **Service controller** | Creates and updates cloud load balancers for `type: LoadBalancer` Services | Creates the Azure Load Balancer rule and public IP |
| **Node controller** | Adds cloud information to nodes and removes nodes whose VM no longer exists | Adds labels for region, zone, and VM size |
| **Route controller** | Configures network routes between nodes | Updates the route table for kubenet clusters |

(Disk creation is handled by CSI drivers today, not by the CCM.)

### Example

```text
kubectl apply -f service.yaml   (type: LoadBalancer)
          |
          v
API server stores the Service
          |
          v
Cloud controller manager sees it
          |
          v
Calls Azure API: create LB rule + public IP
          |
          v
Writes the IP back to the Service status (EXTERNAL-IP)
```

You can see the node information it adds:

```bash
kubectl get nodes --show-labels | grep -o 'topology.kubernetes.io/zone=[^,]*'
kubectl describe node <node-name> | grep ProviderID
```

### In AKS

The CCM (cloud-provider-azure) runs in the **Microsoft-managed control plane**, so you don't install or upgrade it. What you **do** need is the right permissions: the cluster's managed identity needs rights on the VNet, subnet, and public IPs it manages. Missing permissions are a common reason for `EXTERNAL-IP <pending>`.

### Interview answer

> "The cloud controller manager is the control-plane component that connects Kubernetes to the cloud APIs. Its service controller creates the Azure Load Balancer and public IP when I create a LoadBalancer Service, its node controller adds cloud details like the zone and VM size to nodes, and the route controller manages routes for kubenet. In AKS it is managed by Microsoft, so my part is making sure the cluster identity has the network permissions it needs."

</details>

---

<details><summary>Q5. What are a Deployment, StatefulSet, and DaemonSet? Give examples.</summary>

All three are controllers that create and manage pods, but for different kinds of applications.

| | Deployment | StatefulSet | DaemonSet |
| --- | --- | --- | --- |
| Use for | Stateless apps | Stateful apps | One pod on every node |
| Pod names | Random (`api-7d9f-x2k`) | Fixed, ordered (`mongo-0`, `mongo-1`) | One per node |
| Storage | Usually none or shared | Own PVC per pod (kept after restart) | Often node paths (logs) |
| Scaling | `replicas: N`, any order | Ordered, one at a time | Follows the number of nodes |
| Examples | Spring Boot API, React frontend, Nginx | MongoDB, Kafka, Elasticsearch, Zookeeper | Fluent Bit, node-exporter, Azure Monitor agent, kube-proxy, CSI node drivers |

### Deployment: Spring Boot API

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orders-api
  template:
    metadata:
      labels:
        app: orders-api
    spec:
      containers:
        - name: orders-api
          image: myacr.azurecr.io/orders-api:v1.2.0
```

Any of the 3 pods can serve any request. Rolling updates replace them one by one.

### StatefulSet: MongoDB with a disk per pod

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mongo
spec:
  serviceName: mongo        # headless Service for stable DNS names
  replicas: 3
  selector:
    matchLabels:
      app: mongo
  template:
    metadata:
      labels:
        app: mongo
    spec:
      containers:
        - name: mongo
          image: mongo:7.0
          volumeMounts:
            - name: data
              mountPath: /data/db
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: managed-csi
        resources:
          requests:
            storage: 20Gi
```

Pods are `mongo-0`, `mongo-1`, `mongo-2`. If `mongo-1` restarts, it comes back with the **same name and the same disk** (`data-mongo-1`).

### DaemonSet: log collector on every node

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
        - name: fluent-bit
          image: fluent/fluent-bit:3.0
          volumeMounts:
            - name: varlog
              mountPath: /var/log
              readOnly: true
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
```

When Cluster Autoscaler adds a node, the DaemonSet automatically starts a Fluent Bit pod on it.

Related: a **Job** runs a task to completion once (DB migration), and a **CronJob** runs on a schedule (nightly report).

### Interview answer

> "A Deployment is for stateless apps like a Spring Boot API: pods are interchangeable and updated with rolling updates. A StatefulSet is for stateful apps like MongoDB or Kafka: each pod has a stable name like `mongo-0` and its own persistent disk that stays with it after restarts. A DaemonSet runs one pod on every node, for node-level agents like Fluent Bit for logs, node-exporter for metrics, or the Azure Monitor agent. New nodes automatically get the DaemonSet pod."

</details>

---

<details><summary>Q6. What are the components of the control plane and data plane in Kubernetes?</summary>

- The **control plane** is the "brain": it stores the desired state and makes decisions.
- The **data plane** (worker nodes) is the "muscle": it actually runs the application pods.

```text
                     CONTROL PLANE
  +----------------------------------------------------+
  |  kube-apiserver  <-->  etcd                        |
  |       ^                                            |
  |       |-- kube-scheduler                           |
  |       |-- kube-controller-manager                  |
  |       |-- cloud-controller-manager                 |
  +-------|--------------------------------------------+
          |
  +-------|-------------------+  +---------------------------+
  | Worker node 1             |  | Worker node 2             |
  |  kubelet                  |  |  kubelet                  |
  |  kube-proxy               |  |  kube-proxy               |
  |  container runtime        |  |  container runtime        |
  |  CNI plugin               |  |  CNI plugin               |
  |  [pod] [pod] [pod]        |  |  [pod] [pod]              |
  +---------------------------+  +---------------------------+
```

### Control plane components

| Component | Role |
| --- | --- |
| **kube-apiserver** | Front door of the cluster. All requests (`kubectl`, pipelines, kubelets) go through it. Handles authentication and authorization. |
| **etcd** | Key-value database that stores the whole cluster state (Deployments, Secrets, ConfigMaps). |
| **kube-scheduler** | Picks the best node for each new pod based on resources, taints, and affinity. |
| **kube-controller-manager** | Runs controllers that keep actual state = desired state (for example, if a pod dies, the ReplicaSet controller creates a new one). |
| **cloud-controller-manager** | Talks to Azure for load balancers, node information, and routes (see Q4). |

### Data plane (worker node) components

| Component | Role |
| --- | --- |
| **kubelet** | Agent on each node. Starts the pods assigned to the node, runs probes, and reports status. |
| **kube-proxy** | Programs iptables/IPVS rules so Service IPs reach the right pods (Cilium can replace it). |
| **Container runtime** | Actually runs the containers (containerd in AKS, see Q7). |
| **CNI plugin** | Gives pods IPs and networking (see Q8). |

Cluster add-ons like **CoreDNS** and **metrics-server** run as pods on the worker nodes.

### What happens on `kubectl apply -f deployment.yaml`

1. `kubectl` sends the Deployment to the **API server**, which stores it in **etcd**.
2. The **controller manager** creates a ReplicaSet and the pod objects.
3. The **scheduler** assigns each pod to a node.
4. The **kubelet** on that node asks **containerd** to pull the image and start the container; the **CNI** assigns an IP.
5. The kubelet reports "Running" back to the API server.

### In AKS

Microsoft manages the whole **control plane** (you don't see those VMs, and etcd is backed up for you). You manage the **node pools** (VM size, count, upgrades) and the workloads. The Standard tier adds an uptime SLA for the API server.

### Interview answer

> "The control plane has the API server as the entry point, etcd to store the cluster state, the scheduler to place pods on nodes, the controller manager to keep the actual state matching the desired state, and the cloud controller manager to talk to Azure. The data plane is the worker nodes, each running the kubelet, kube-proxy, the container runtime, which is containerd, and the CNI plugin. In AKS, Microsoft manages the control plane, and we manage the node pools and workloads."

</details>

---

<details><summary>Q7. What container runtime have you used in Kubernetes?</summary>

The container runtime is the software on each node that **pulls images and runs the containers**. The kubelet talks to it through the **CRI** (Container Runtime Interface).

In AKS, the runtime is **containerd**. AKS moved from Docker to containerd for Linux node pools from Kubernetes 1.19, and Kubernetes removed Docker support (dockershim) completely in 1.24.

### How to check

```bash
kubectl get nodes -o wide
# NAME                     STATUS  VERSION  OS-IMAGE           CONTAINER-RUNTIME
# aks-nodepool1-123-vmss0  Ready   v1.30.x  Ubuntu 22.04.x LTS containerd://1.7.x
```

### Common question: "Then can we still use Docker images?"

**Yes.** Docker builds images in the standard **OCI** format, and containerd runs OCI images. Developers still use `docker build` and push to ACR; only the runtime on the node changed.

### Debugging on the node

Without Docker on the node, `docker ps` does not work. Use `crictl` instead:

```bash
kubectl debug node/aks-nodepool1-123-vmss0 -it --image=mcr.microsoft.com/cbl-mariner/busybox:2.0
chroot /host
crictl ps          # running containers
crictl images      # images on the node
crictl logs <container-id>
```

Other runtimes you may hear about: **CRI-O** (used by OpenShift) and sandboxed runtimes like **Kata Containers** (AKS Pod Sandboxing) for strong isolation.

### Interview answer

> "We used containerd, which is the default runtime in AKS. The kubelet talks to it through CRI. Docker images still work because they're standard OCI images; we build with Docker in the pipeline and push to ACR, and containerd runs them on the nodes. For node-level debugging, I use `kubectl debug node` and `crictl`, because there is no Docker CLI on the nodes."

</details>

---

<details><summary>Q8. What are the uses of a network plugin in Kubernetes?</summary>

Kubernetes defines **networking rules** (every pod gets its own IP, and every pod can reach every other pod without NAT), but it does not implement them itself. The **network plugin (CNI)** implements them.

### Uses

| Use | What it means |
| --- | --- |
| **Assign pod IPs** | Each pod gets an IP when it starts (from a VNet subnet or an overlay range). |
| **Pod-to-pod communication** | Pods on different nodes can talk to each other, through routing or encapsulation. |
| **Connect to the outside network** | Pods can reach VNet resources, private endpoints, on-premises, and the internet. |
| **Network policies** | Allow or deny traffic between pods (for example, only the backend can reach the database). Supported by Azure NPM, Calico, or Cilium. |
| **Performance and scale** | eBPF-based plugins (Cilium) process traffic faster and can replace kube-proxy. |
| **Observability and encryption** | Some plugins show traffic flows (Cilium Hubble) and encrypt node-to-node traffic (WireGuard). |

### Example: NetworkPolicy enforced by the plugin

Only frontend pods can call the backend on port 8080:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

**Important:** if the cluster has no network policy engine enabled, Kubernetes accepts this YAML but **nothing enforces it**.

### AKS options

Azure CNI Overlay, Azure CNI (pod subnet), Kubenet (legacy), and Azure CNI Powered by Cilium. See [Epam3.md, Q4](Epam3.md) for a comparison table, and [Epam3.md, Q14](Epam3.md) for how the plugin assigns pod IPs.

### Interview answer

> "The network plugin implements pod networking. It assigns IPs to pods, lets pods on different nodes talk to each other, connects them to the VNet and external services, and enforces NetworkPolicies, such as allowing only the frontend to call the backend. Advanced plugins like Cilium also give better performance with eBPF, traffic visibility, and encryption. In AKS, we used Azure CNI Overlay with network policies enabled."

Only name the plugin your cluster actually used.

</details>

---

<details><summary>Q9. How do you increase nodes automatically in Kubernetes?</summary>

Use the **Cluster Autoscaler**. It adds nodes when pods cannot be scheduled because of insufficient CPU or memory (`Pending`), and removes nodes that stay underused.

**Key point:** it does **not** add nodes just because CPU is high. The trigger is **pending pods**. That is why it works together with HPA: HPA adds pods, and if they don't fit, Cluster Autoscaler adds nodes.

```text
Traffic up --> HPA adds pods --> pods Pending (no space)
                                     |
                                     v
                     Cluster Autoscaler adds a node
                                     |
                                     v
                        Pods scheduled on the new node
```

### Enable it in AKS

On a new cluster:

```bash
az aks create -g rg-aks-dev -n aks-dev \
  --node-count 3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10
```

On an existing node pool:

```bash
az aks nodepool update -g rg-aks-dev --cluster-name aks-dev \
  --name userpool \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 8
```

Change the limits later with `--update-cluster-autoscaler`.

With Terraform (azurerm 4.x):

```hcl
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "userpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D4s_v5"
  auto_scaling_enabled  = true   # enable_auto_scaling in azurerm 3.x
  min_count             = 2
  max_count             = 8
}
```

If you manage the node count with the autoscaler, don't also hard-code `node_count` changes in Terraform, or Terraform and the autoscaler will fight. Use `lifecycle { ignore_changes = [node_count] }`.

### Tuning

The **autoscaler profile** controls behaviour, for example how long a node must be unused before removal (`scale-down-unneeded-time`, default 10 minutes):

```bash
az aks update -g rg-aks-dev -n aks-dev \
  --cluster-autoscaler-profile scale-down-unneeded-time=15m
```

### Things that stop it from working

- Pods have **no resource requests**, so the scheduler thinks they fit and they never go Pending.
- The pool is already at `max-count`, or the subscription has no vCPU **quota** left.
- Scale-down is blocked by pods with local storage, strict PodDisruptionBudgets, or pods not managed by a controller.

Another option in AKS is **Node Auto-Provisioning** (based on Karpenter), which picks the best VM size for the pending pods automatically.

### Interview answer

> "I enable the Cluster Autoscaler on the AKS node pool with a minimum and maximum node count. It adds nodes when pods are Pending because of insufficient resources, and removes underused nodes after a while. It works together with HPA: HPA adds pods for traffic, and the Cluster Autoscaler adds nodes when those pods don't fit. For it to work well, every pod must have resource requests, and the subscription must have enough vCPU quota."

</details>

---

<details><summary>Q10. What is CSI in Kubernetes?</summary>

**CSI = Container Storage Interface.** It is a standard API between Kubernetes and storage systems.

Before CSI, storage code for each cloud was **inside Kubernetes itself** ("in-tree"), so every storage fix needed a new Kubernetes release. With CSI, each storage vendor writes its own **driver** that plugs into Kubernetes, and it can be updated independently.

### What a CSI driver does

| Step | Example with Azure Disk |
| --- | --- |
| **Create** the volume | Creates a managed disk when a PVC is created |
| **Attach** it to the node | Attaches the disk to the VM where the pod is scheduled |
| **Mount** it into the pod | Formats and mounts the disk at the container path |
| **Expand / snapshot / delete** | Resizes the disk, takes snapshots, deletes it when no longer needed |

A CSI driver usually has two parts:

- **Controller plugin** (Deployment): creates, deletes, attaches, and detaches volumes using the cloud API.
- **Node plugin** (DaemonSet): mounts the volume on each node.

### CSI drivers in AKS

| Driver | Storage | Typical use |
| --- | --- | --- |
| `disk.csi.azure.com` | Azure Managed Disks | Databases, one pod per disk (ReadWriteOnce) |
| `file.csi.azure.com` | Azure Files (SMB/NFS) | Shared files across many pods (ReadWriteMany) |
| `blob.csi.azure.com` | Azure Blob (BlobFuse/NFS) | Large unstructured data, ML datasets |
| `secrets-store.csi.k8s.io` | Azure Key Vault (via provider) | Mount secrets and certificates as files (see Q14) |

The Disk and Files drivers are enabled by default in AKS.

```bash
kubectl get csidrivers
kubectl get storageclass
# NAME                    PROVISIONER          
# managed-csi (default)   disk.csi.azure.com
# managed-csi-premium     disk.csi.azure.com
# azurefile-csi           file.csi.azure.com
# azurefile-csi-premium   file.csi.azure.com
```

### Interview answer

> "CSI is the Container Storage Interface, a standard that lets storage vendors write drivers for Kubernetes without changing Kubernetes code. The driver creates, attaches, mounts, expands, and snapshots volumes. In AKS, we use the Azure Disk CSI driver for databases that need a dedicated disk, the Azure Files CSI driver for storage shared by many pods, and the Secrets Store CSI driver to mount Key Vault secrets into pods."

</details>

---

<details><summary>Q11. How is storage managed in Kubernetes?</summary>

Containers are **temporary**: when a container restarts, anything written inside it is lost. Kubernetes uses **volumes** to keep or share data.

### Types of storage

| Type | Lifetime | Example use |
| --- | --- | --- |
| `emptyDir` | Lives as long as the pod | Temp files, cache, sharing files with a sidecar |
| `configMap` / `secret` | Managed by Kubernetes | Config files, certificates mounted as files |
| `hostPath` | Node's disk | Node agents like log collectors (avoid for apps) |
| **PersistentVolume (PV) + PVC** | Independent of the pod | Databases, uploaded files, anything that must survive |

### The persistent storage building blocks

```text
StorageClass  -> "how" to create storage (disk type, reclaim policy)
      |
PVC           -> developer asks: "I need 20Gi, ReadWriteOnce"
      |
PV            -> the actual storage (Azure Disk), created automatically
      |
Pod           -> mounts the PVC at /data
```

**Dynamic provisioning** is the normal way: the developer creates only a PVC, and the StorageClass + CSI driver creates the disk and the PV automatically.

### Example StorageClass

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: premium-retain
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_LRS
reclaimPolicy: Retain                 # keep the disk if the PVC is deleted
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

| Setting | Why it matters |
| --- | --- |
| `reclaimPolicy: Retain` | Protects production data if someone deletes the PVC. `Delete` (the default) removes the disk too. |
| `WaitForFirstConsumer` | Creates the disk in the same availability zone as the node where the pod lands. |
| `allowVolumeExpansion` | Lets you increase the PVC size later without recreating it. |

### Other parts of storage management

- **Access modes:** ReadWriteOnce (one node, Azure Disk) vs ReadWriteMany (many pods, Azure Files). See Q12.
- **StatefulSets** use `volumeClaimTemplates` to give each pod its own PVC.
- **Backup:** Azure Backup for AKS or Velero, plus volume snapshots.
- **Monitoring:** alert when a volume is nearly full (`kubelet_volume_stats_used_bytes`).

### Interview answer

> "Container storage is temporary, so Kubernetes uses volumes. For temporary or shared data inside a pod, I use `emptyDir`; for config, ConfigMaps and Secrets. For data that must survive, I use PersistentVolumeClaims with a StorageClass, so the CSI driver creates the Azure Disk or Azure Files share automatically. For production, I use a StorageClass with `Retain`, `WaitForFirstConsumer`, and volume expansion enabled, and I back up the volumes with Azure Backup for AKS or Velero."

</details>

---

<details><summary>Q12. What are PV and PVC?</summary>

- **PV (PersistentVolume):** the **actual piece of storage** in the cluster, such as an Azure Disk or Azure Files share. It is a cluster-level resource.
- **PVC (PersistentVolumeClaim):** a **request for storage** made by an application, such as "I need 10Gi, ReadWriteOnce". It belongs to a namespace.

Simple analogy: the **PV is a parking space**; the **PVC is your parking ticket** asking for a space of a certain size. Kubernetes matches them (**binding**), and the pod uses the ticket.

### Example: PVC + pod (dynamic provisioning)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: uploads-pvc
  namespace: dev
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: managed-csi
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: uploads-app
  namespace: dev
spec:
  containers:
    - name: app
      image: myacr.azurecr.io/uploads-app:v1.0.0
      volumeMounts:
        - name: uploads
          mountPath: /app/uploads
  volumes:
    - name: uploads
      persistentVolumeClaim:
        claimName: uploads-pvc
```

When the pod is scheduled, the CSI driver creates a 10Gi Azure Disk and a PV, and the PVC becomes `Bound`.

```bash
kubectl get pvc -n dev
# NAME          STATUS   VOLUME          CAPACITY   ACCESS MODES   STORAGECLASS
# uploads-pvc   Bound    pvc-3f2a...     10Gi       RWO            managed-csi

kubectl get pv
```

### Access modes

| Mode | Meaning | Azure storage |
| --- | --- | --- |
| ReadWriteOnce (RWO) | Read-write by one node | Azure Disk |
| ReadOnlyMany (ROX) | Read-only by many nodes | Azure Files, Blob |
| ReadWriteMany (RWX) | Read-write by many nodes | Azure Files, Blob |
| ReadWriteOncePod (RWOP) | Read-write by a single pod | Azure Disk |

### Static vs dynamic

- **Dynamic:** create only the PVC; the StorageClass creates the PV. (Normal case.)
- **Static:** an admin creates the PV for **existing** storage (for example, an existing Azure Files share with data), and the PVC binds to it.

### Common issues

| Symptom | Cause |
| --- | --- |
| PVC stuck in `Pending` | Wrong StorageClass name, no quota, or waiting for a pod (`WaitForFirstConsumer`, which is normal) |
| Pod stuck in `ContainerCreating` with "Multi-Attach error" | An RWO disk is still attached to another node; use RWX storage if many pods need it |
| PV in `Released` state | The PVC was deleted and the reclaim policy is `Retain`; the data is kept and the PV must be cleaned up manually to reuse |

### Interview answer

> "A PV is the actual storage, like an Azure Disk, and a PVC is the application's request for storage of a certain size and access mode. Kubernetes binds the PVC to a PV, and the pod mounts the PVC. Normally we use dynamic provisioning: we create only the PVC, and the StorageClass and CSI driver create the disk and the PV. I choose Azure Disk with ReadWriteOnce for databases, and Azure Files with ReadWriteMany when several pods share the same files."

</details>

---

<details><summary>Q13. What is encryption at rest in Kubernetes?</summary>

**Encryption at rest** means data stored on disk is encrypted, so if someone gets the disk or a backup, they cannot read the data. In Kubernetes, there are two places to think about:

1. **etcd**, which stores cluster objects, including **Secrets**.
2. **Disks**: node OS disks and the persistent volumes (PVs) used by apps.

### Important point: Kubernetes Secrets are only base64-encoded

```bash
kubectl get secret db-secret -n dev -o jsonpath='{.data.password}' | base64 -d
# MyPassword123
```

Base64 is **encoding, not encryption**. Anyone with read access to Secrets or to etcd can decode them. That is why we need encryption at rest for etcd and RBAC restrictions on who can read Secrets.

### In vanilla Kubernetes

Admins configure an `EncryptionConfiguration` on the API server, ideally with a **KMS provider**, so Secrets are encrypted before they are written to etcd:

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - kms:
          apiVersion: v2
          name: azure-kms
          endpoint: unix:///opt/azurekms.socket
      - identity: {}
```

### In AKS

| Layer | Default | Extra option (customer-managed keys) |
| --- | --- | --- |
| etcd | Encrypted at rest by Azure with Microsoft-managed keys | **KMS etcd encryption** with your own key in Azure Key Vault |
| Node OS disks | Azure Storage encryption with platform-managed keys | Disk Encryption Set with your key from Key Vault |
| Temp disks and disk cache on the node | Not covered by storage encryption | **Encryption at host** |
| PVs (Azure Disk / Files) | Encrypted with platform-managed keys | StorageClass `diskEncryptionSetID` parameter with your key |

Enable KMS etcd encryption with a Key Vault key:

```bash
az aks update -g rg-aks-prod -n aks-prod \
  --enable-azure-keyvault-kms \
  --azure-keyvault-kms-key-id "$KEY_ID" \
  --azure-keyvault-kms-key-vault-network-access Public
```

(The cluster needs a user-assigned managed identity with permission to use the key. For a private Key Vault, use `Private` network access.)

Encryption at host for a node pool:

```bash
az aks nodepool add -g rg-aks-prod --cluster-name aks-prod \
  --name securepool --enable-encryption-at-host
```

### Better practice for secrets

Instead of storing real secrets in Kubernetes Secrets, keep them in **Azure Key Vault** and mount them with the Secrets Store CSI driver (Q14) or read them through Workload ID.

### Interview answer

> "Encryption at rest protects stored data. In Kubernetes, the main concern is etcd, because Secrets are only base64-encoded, not encrypted. In AKS, etcd and disks are already encrypted by Azure with Microsoft-managed keys. For stricter compliance, I enable KMS etcd encryption with a key in Key Vault, use a Disk Encryption Set for customer-managed keys on OS disks and PVs, and enable encryption at host for temp disks. I also prefer keeping secrets in Key Vault and mounting them with the Secrets Store CSI driver."

</details>

---

<details><summary>Q14. How do you integrate external services with CSI?</summary>

The most common case is **Azure Key Vault → pods** using the **Secrets Store CSI driver** with the **Azure Key Vault provider**. Key Vault secrets, keys, and certificates are mounted into the pod as files, and can optionally be synced to a Kubernetes Secret. The second case is mounting **existing Azure Storage** (Files/Blob) with the storage CSI drivers.

### Case 1: Azure Key Vault secrets in a pod

```text
Pod (serviceAccount with Workload ID)
   |
   | mounts volume (driver: secrets-store.csi.k8s.io)
   v
Secrets Store CSI driver + Azure Key Vault provider
   |
   | authenticates as the user-assigned managed identity
   v
Azure Key Vault --> secret written as a file: /mnt/secrets/database-password
```

**Step 1: Enable the add-on**

```bash
az aks enable-addons -g rg-aks-dev -n aks-dev \
  --addons azure-keyvault-secrets-provider

# Optional: refresh mounted secrets when they change in Key Vault
az aks addon update -g rg-aks-dev -n aks-dev \
  --addon azure-keyvault-secrets-provider \
  --enable-secret-rotation
```

**Step 2: Identity and access**

Set up Workload ID with a user-assigned managed identity, a federated credential for the service account, and the **Key Vault Secrets User** role. These are the same steps as [Epam3.md, Q9](Epam3.md).

**Step 3: Create a `SecretProviderClass`** (tells the driver what to fetch)

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: kv-db-secrets
  namespace: dev
spec:
  provider: azure
  parameters:
    clientID: "<USER_ASSIGNED_CLIENT_ID>"
    keyvaultName: "<KEYVAULT_NAME>"
    tenantId: "<TENANT_ID>"
    objects: |
      array:
        - |
          objectName: database-password
          objectType: secret
  secretObjects:                 # optional: also create a Kubernetes Secret
    - secretName: db-secret
      type: Opaque
      data:
        - objectName: database-password
          key: password
```

**Step 4: Mount it in the Deployment**

```yaml
spec:
  template:
    metadata:
      labels:
        app: springboot-app
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: springboot-sa
      containers:
        - name: app
          image: myacr.azurecr.io/springboot-app:v1.0.0
          volumeMounts:
            - name: secrets-store
              mountPath: /mnt/secrets
              readOnly: true
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
      volumes:
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: kv-db-secrets
```

**Step 5: Verify**

```bash
kubectl exec -n dev deploy/springboot-app -- ls /mnt/secrets
# database-password
```

If the pod is stuck in `ContainerCreating`, run `kubectl describe pod` and look for mount errors: usually a wrong client ID, a missing role assignment, or the Key Vault firewall blocking access.

Note: the synced Kubernetes Secret (`db-secret`) exists only while a pod is mounting the volume.

### Case 2: Existing Azure Files share (static provisioning)

To mount an existing file share that already has data, create a PV that points to it:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: shared-reports-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: azurefile-csi
  csi:
    driver: file.csi.azure.com
    volumeHandle: "rg-storage#streportsprod#reports"   # unique ID: rg#account#share
    volumeAttributes:
      resourceGroup: rg-storage
      storageAccount: streportsprod
      shareName: reports
    nodeStageSecretRef:
      name: azure-storage-secret     # storage account name and key
      namespace: dev
```

Then a PVC with the same `storageClassName` and `volumeName: shared-reports-pv` binds to it.

### Interview answer

> "I integrate external services with the CSI drivers. For secrets, I enable the Azure Key Vault Secrets Store CSI add-on, create a SecretProviderClass listing the Key Vault secrets, and mount it as a volume in the pod. The driver authenticates with Workload ID, using a user-assigned managed identity that has the Key Vault Secrets User role, so there are no credentials in the cluster. I enable secret rotation, and optionally sync to a Kubernetes Secret for apps that need environment variables. For existing Azure Files or Blob storage, I create a static PV that points to the share, and the pods mount it through a PVC."

</details>

---

## Networking

<details><summary>Q15. What is a subnet?</summary>

A **subnet** is a **smaller range of IP addresses inside a network** (VNet). You split a VNet into subnets to group and isolate resources, just like dividing a building into floors.

### Example

```text
VNet: vnet-app-prod   10.10.0.0/16   (65,536 addresses)
 |
 +-- snet-frontend     10.10.1.0/24   (256 addresses) -> App Gateway
 +-- snet-backend      10.10.2.0/24   (256 addresses) -> AKS nodes
 +-- snet-data         10.10.3.0/24   (256 addresses) -> private endpoints for SQL, Key Vault
```

### CIDR notation in simple words

The number after `/` says how many bits are fixed for the network. The **smaller** the number, the **bigger** the range.

| CIDR | Total IPs | Usable in Azure (minus 5 reserved) |
| --- | --- | --- |
| /16 | 65,536 | 65,531 |
| /24 | 256 | 251 |
| /26 | 64 | 59 |
| /27 | 32 | 27 |
| /29 | 8 | 3 (smallest allowed in Azure) |

**Azure reserves 5 IPs in every subnet:** the network address (`.0`), the default gateway (`.1`), two for Azure DNS (`.2`, `.3`), and the broadcast address (`.255` in a /24).

### Why we use subnets

- **Security:** attach an **NSG** to each subnet (only backend can reach data).
- **Routing:** attach a **route table** (send traffic through Azure Firewall).
- **Delegation:** some services need their own subnet (App Service VNet integration, Azure Container Instances).
- **Special subnets** with fixed names: `GatewaySubnet` (VPN/ExpressRoute), `AzureFirewallSubnet`, `AzureBastionSubnet`.

### Create with Azure CLI

```bash
az network vnet subnet create \
  -g rg-network \
  --vnet-name vnet-app-prod \
  -n snet-backend \
  --address-prefixes 10.10.2.0/24
```

**Real tip:** for AKS with Azure CNI (pod IPs from the subnet), size the subnet generously. A /24 runs out quickly when every pod takes an IP.

### Interview answer

> "A subnet is a smaller IP range inside a VNet that groups related resources. For example, in a 10.10.0.0/16 VNet, I create separate /24 subnets for the frontend, backend, and data tiers, attach NSGs to control traffic between them, and route tables to send traffic through the firewall. Azure reserves 5 IPs in every subnet, so a /24 gives 251 usable IPs. I size subnets based on growth, especially for AKS, where pods can consume subnet IPs."

</details>

---

<details><summary>Q16. What are protocols and their types? What are ports (443, 80)? What is DNS?</summary>

### Protocol

A **protocol** is a set of rules that two systems follow to communicate, like a common language.

**Transport protocols** (how data is delivered):

| Protocol | How it works | Used by |
| --- | --- | --- |
| **TCP** | Connection-based, reliable, ordered; resends lost data | HTTP/HTTPS, SSH, databases |
| **UDP** | No connection, faster, no delivery guarantee | DNS queries, video streaming, VoIP |
| **ICMP** | Network diagnostics, no ports | `ping`, `traceroute` |

**Application protocols** (what the data means): HTTP, HTTPS, SSH, FTP/SFTP, SMTP, DNS, RDP.

### Port

An IP address finds the **machine**; a **port** finds the **application** on that machine. Example: one VM runs Nginx on port 80 and SSH on port 22. Ports go from 0 to 65535.

| Port | Protocol | Use |
| --- | --- | --- |
| **80** | HTTP | Web traffic, **not encrypted** |
| **443** | HTTPS | Web traffic **encrypted with TLS** |
| 22 | SSH | Linux remote login |
| 3389 | RDP | Windows remote desktop |
| 53 | DNS | Name resolution (UDP, and TCP for large responses) |
| 25 / 587 | SMTP | Sending email |
| 1433 | SQL Server / Azure SQL | Database |
| 3306 | MySQL | Database |
| 5432 | PostgreSQL | Database |
| 6379 | Redis | Cache |
| 6443 | Kubernetes API (default) | AKS exposes the API server on 443 |

**80 vs 443:** on port 80, anyone in the middle can read the traffic (passwords, cookies). On 443, TLS encrypts it. In production, we redirect 80 → 443 and allow only 443 from the internet.

### DNS

**DNS (Domain Name System)** translates names into IP addresses, like a phone book: `www.example.com` → `20.81.45.120`.

How a lookup works:

```text
Browser: "what is the IP of app.example.com?"
   |
   v
Local cache / OS resolver
   |
   v
DNS resolver (ISP or Azure DNS 168.63.129.16)
   |
   +--> Root server      -> "ask the .com servers"
   +--> .com server      -> "ask example.com's name servers"
   +--> example.com NS   -> "app.example.com = 20.81.45.120"
   |
   v
Answer cached for the TTL (for example 300 seconds)
```

Common record types:

| Record | Purpose | Example |
| --- | --- | --- |
| A | Name → IPv4 address | `app.example.com → 20.81.45.120` |
| AAAA | Name → IPv6 address | |
| CNAME | Name → another name | `www → app.example.com` |
| MX | Mail server for the domain | |
| TXT | Text, used for domain verification, SPF | |
| NS | Name servers for the zone | |
| PTR | IP → name (reverse lookup) | |

**In Azure:** Azure DNS hosts public zones, and **Private DNS zones** resolve private endpoint names (for example `mykv.privatelink.vaultcore.azure.net` → `10.10.3.5`) inside VNets.

**Troubleshooting commands:**

```bash
nslookup app.example.com
dig app.example.com +short
nc -zv app.example.com 443      # is the port open?
```

### Interview answer

> "A protocol is a set of communication rules. TCP is reliable and connection-based, used for HTTP, SSH, and databases; UDP is faster with no delivery guarantee, used for DNS queries and streaming. A port identifies the application on a host: 80 is HTTP, which is unencrypted, and 443 is HTTPS, which is encrypted with TLS, so in production we only expose 443 and redirect 80 to it. DNS translates names to IPs using records like A, CNAME, and TXT. In Azure, I use Private DNS zones so private endpoint names resolve to private IPs. For troubleshooting, I check DNS with `nslookup` first and then the port with `nc`."

</details>

---

<details><summary>Q17. What are TLS and certificates, and how do we use them?</summary>

**TLS (Transport Layer Security)** encrypts data **in transit** between a client and a server. HTTPS is simply HTTP over TLS. (SSL is the old name; SSL itself is deprecated.)

TLS gives three things:

1. **Encryption:** nobody in the middle can read the data.
2. **Authentication:** the client knows it is really talking to `app.example.com`, not a fake server.
3. **Integrity:** data cannot be changed in transit without being detected.

### Certificate

A **certificate** is a digital ID card for a server. It contains:

- The **domain name** (for example `app.example.com`, or `*.example.com` for a wildcard).
- The server's **public key**.
- The **issuer** (Certificate Authority, such as DigiCert or Let's Encrypt) and its signature.
- **Validity dates** (expiry).

The matching **private key** stays secret on the server. The browser trusts the certificate because a CA it already trusts signed it.

### Simplified TLS handshake

```text
Client                                   Server
  | --- Hello (TLS versions, ciphers) ---> |
  | <-- Certificate (public key) --------- |
  | checks: trusted CA? correct domain?    |
  |         not expired?                   |
  | --- key exchange --------------------> |
  | <====== encrypted session (HTTPS) ===> |
```

**mTLS (mutual TLS):** both sides present certificates. Used between microservices (service mesh) or for partner APIs.

### How we use them in projects

| Where | How |
| --- | --- |
| AKS Ingress | **cert-manager** gets free Let's Encrypt certificates and renews them automatically |
| Application Gateway | Certificate stored in **Key Vault**, referenced by the listener; App Gateway auto-picks renewed versions |
| App Service | Custom domain + App Service managed certificate or Key Vault certificate |
| Service-to-service | mTLS through Istio |
| Kubernetes itself | The API server, kubelets, and etcd use certificates internally (managed by AKS; rotate with `az aks rotate-certs`) |

### Example: cert-manager with Let's Encrypt on AKS

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: devops-team@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: frontend
  namespace: prod
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - app.example.com
      secretName: app-example-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-svc
                port:
                  number: 80
```

cert-manager requests the certificate, stores it in the `app-example-tls` Secret, and renews it before expiry.

To use an existing certificate manually:

```bash
kubectl create secret tls app-example-tls \
  --cert=app.example.com.crt --key=app.example.com.key -n prod
```

### Checking a certificate

```bash
openssl s_client -connect app.example.com:443 -servername app.example.com </dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

**Real issue to mention:** expired certificates cause outages. Automate renewal (cert-manager, Key Vault auto-renewal) and set alerts 30 days before expiry.

### Interview answer

> "TLS encrypts traffic in transit and proves the server's identity using a certificate. The certificate contains the domain name, the public key, the issuing CA, and the expiry date, and the private key stays on the server. In AKS, I use cert-manager with Let's Encrypt on the Ingress so certificates are issued and renewed automatically. For Application Gateway, I store certificates in Key Vault. Between microservices, we can use mTLS through a service mesh. I also monitor certificate expiry, because an expired certificate is a common cause of outages."

</details>

---

## Terraform and Bicep

<details><summary>Q18. What are Azure providers in Terraform, and how do you use them?</summary>

A **provider** is a plugin that lets Terraform talk to a platform's API. Terraform itself knows nothing about Azure; the provider translates your `.tf` code into Azure API calls.

### Azure-related providers

| Provider | Manages | Example resources |
| --- | --- | --- |
| **azurerm** (`hashicorp/azurerm`) | Azure resources through Azure Resource Manager | Resource groups, VNets, AKS, Key Vault, Storage |
| **azuread** (`hashicorp/azuread`) | Microsoft Entra ID objects | App registrations, service principals, groups |
| **azapi** (`azure/azapi`) | Any Azure resource directly through the ARM REST API | New or preview features not yet in azurerm |
| **azuredevops** (`microsoft/azuredevops`) | Azure DevOps | Projects, repos, service connections, pipelines |

Helper providers often used with them: `random` (unique names, passwords), `tls`, `kubernetes`, `helm`.

### How to use it

**1. Declare and pin the provider version** (usually in `providers.tf` or `versions.tf`):

```hcl
terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"   # any 4.x, but not 5.0
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
  }
}
```

**2. Configure it:**

```hcl
provider "azurerm" {
  features {}                           # required block, can be empty
  subscription_id = var.subscription_id # required in azurerm 4.x
}
```

The `features` block changes provider behaviour, for example:

```hcl
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
  subscription_id = var.subscription_id
}
```

**3. Run `terraform init`.** Terraform downloads the provider from the Terraform Registry and records the exact version in `.terraform.lock.hcl`. Commit this lock file so everyone and every pipeline uses the same version.

### Multiple subscriptions: provider aliases

Example: the spoke VNet is in the app subscription, and the hub VNet is in the network subscription.

```hcl
provider "azurerm" {
  features {}
  subscription_id = var.app_subscription_id
}

provider "azurerm" {
  alias           = "hub"
  features {}
  subscription_id = var.hub_subscription_id
}

resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  provider                  = azurerm.hub
  name                      = "hub-to-spoke"
  resource_group_name       = "rg-hub-network"
  virtual_network_name      = "vnet-hub"
  remote_virtual_network_id = azurerm_virtual_network.spoke.id
}
```

### Interview answer

> "A provider is the plugin that lets Terraform call a platform's API. For Azure, I mainly use `azurerm` for Azure resources, `azuread` for Entra ID objects like app registrations, and `azapi` for features not yet in azurerm. I declare them in `required_providers` with a pinned version, configure azurerm with the `features` block and subscription ID, and commit the `.terraform.lock.hcl` file. When I deploy to multiple subscriptions, for example hub and spoke, I use provider aliases."

</details>

---

<details><summary>Q19. How do you integrate Terraform with Azure?</summary>

Integration has three parts: **authentication**, a **remote backend for state**, and a **pipeline** to run it.

### 1. Authentication options

| Where Terraform runs | Recommended authentication |
| --- | --- |
| Your laptop | **Azure CLI**: `az login`, and Terraform uses that session |
| Azure DevOps / GitHub Actions | **Service principal or managed identity with OIDC** (workload identity federation, no secret) |
| Self-hosted agent VM in Azure | **Managed identity** of the VM |
| Last resort | Service principal with client secret (must be rotated) |

The provider reads these environment variables:

```bash
export ARM_CLIENT_ID="<app-or-identity-client-id>"
export ARM_TENANT_ID="<tenant-id>"
export ARM_SUBSCRIPTION_ID="<subscription-id>"
export ARM_USE_OIDC=true        # for workload identity federation
# export ARM_USE_MSI=true       # for a managed identity
```

The identity gets only the RBAC roles it needs, for example `Contributor` on the target resource group, plus `Storage Blob Data Contributor` on the state storage account.

### 2. Remote state in Azure Storage

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstate001"
    container_name       = "tfstate"
    key                  = "dev/app.tfstate"
    use_azuread_auth     = true   # use Entra ID instead of storage keys
    use_oidc             = true
  }
}
```

(See Q20 for locking.)

### 3. Azure DevOps pipeline

```yaml
stages:
  - stage: Plan
    jobs:
      - job: Plan
        steps:
          - task: AzureCLI@2
            displayName: Terraform init and plan
            inputs:
              azureSubscription: sc-azure-dev      # workload identity federation
              scriptType: bash
              scriptLocation: inlineScript
              addSpnToEnvironment: true            # exposes servicePrincipalId, tenantId, idToken
              inlineScript: |
                export ARM_CLIENT_ID="$servicePrincipalId"
                export ARM_TENANT_ID="$tenantId"
                export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
                export ARM_OIDC_TOKEN="$idToken"
                export ARM_USE_OIDC=true
                terraform init
                terraform plan -out=tfplan
          - publish: tfplan
            artifact: tfplan

  - stage: Apply
    dependsOn: Plan
    jobs:
      - deployment: Apply
        environment: dev        # add an approval check on this environment
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - download: current
                  artifact: tfplan
                # same AzureCLI@2 login as above, then:
                # terraform init && terraform apply $(Pipeline.Workspace)/tfplan/tfplan
```

Flow: PR → `fmt`, `validate`, `plan` (and a security scan such as Checkov) → review the plan → approval → `apply` the **saved plan**, so exactly what was reviewed is applied.

### Interview answer

> "I integrate Terraform with Azure in three parts. For authentication, locally I use the Azure CLI login, and in pipelines I use an Azure DevOps service connection with workload identity federation, passing the client ID, tenant ID, and OIDC token to the azurerm provider through `ARM_` environment variables, so there is no secret. The state is stored in an Azure Storage backend with Entra ID authentication and blob locking. The pipeline runs fmt, validate, and plan on the PR, saves the plan, and after approval applies exactly that plan."

</details>

---

<details><summary>Q20. How do you enable the lock mechanism in a storage account for the state file?</summary>

Good news: with the **azurerm backend**, state locking is **built in and automatic**. Terraform takes a **blob lease** on the state file during operations that write state. You do not need a separate lock table (unlike the older AWS S3 + DynamoDB setup).

```text
terraform apply (User A)  --> acquires lease on dev/app.tfstate --> runs
terraform apply (User B)  --> lease already taken --> "Error acquiring the state lock"
User A finishes           --> lease released --> User B can run
```

### Step 1: Create a secure storage account for state

```bash
az group create -n rg-tfstate -l eastus

az storage account create -n sttfstate001 -g rg-tfstate -l eastus \
  --sku Standard_GRS \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false

# Recover from accidental overwrite or deletion
az storage account blob-service-properties update \
  --account-name sttfstate001 -g rg-tfstate \
  --enable-versioning true \
  --enable-delete-retention true --delete-retention-days 30

az storage container create -n tfstate --account-name sttfstate001 --auth-mode login
```

### Step 2: Configure the backend (locking is automatic)

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstate001"
    container_name       = "tfstate"
    key                  = "dev/app.tfstate"
    use_azuread_auth     = true
  }
}
```

### Step 3: Protect the storage account itself with an Azure resource lock

The blob lease protects the **state file from concurrent runs**. An Azure **resource lock** protects the **storage account from being deleted**:

```bash
az lock create \
  --name lock-tfstate \
  --lock-type CanNotDelete \
  --resource-group rg-tfstate \
  --resource-name sttfstate001 \
  --resource-type Microsoft.Storage/storageAccounts
```

Use `CanNotDelete`, not `ReadOnly`. A `ReadOnly` lock blocks operations Terraform needs on the account.

### Check and release a lock

```bash
# Is the state file locked?
az storage blob show --account-name sttfstate001 -c tfstate -n dev/app.tfstate \
  --auth-mode login --query properties.lease

# Release a stuck lock (only after confirming nobody is running Terraform)
terraform force-unlock <LOCK_ID>

# If force-unlock does not work, break the blob lease
az storage blob lease break --account-name sttfstate001 -c tfstate \
  -b dev/app.tfstate --auth-mode login
```

A lock gets "stuck" when a pipeline is cancelled or an agent crashes in the middle of an apply.

### Interview answer

> "With the azurerm backend, locking is automatic: Terraform takes a blob lease on the state file, so a second run fails with 'Error acquiring the state lock' until the first one finishes. My part is to configure the backend and secure the storage account: no public access, Entra ID authentication, versioning, and soft delete for recovery, and a `CanNotDelete` resource lock on the account. If a lock gets stuck after a cancelled pipeline, I confirm nothing is running and then use `terraform force-unlock` with the lock ID."

</details>

---

<details><summary>Q21. If the state file is locked, where will you get the lock details: in terraform plan, apply, or both?</summary>

**Both.** By default, `terraform plan` and `terraform apply` both try to acquire the state lock, so if another operation holds it, **both** fail and show the lock details.

Other commands that also take the lock: `destroy`, `refresh`, `import`, `state mv`, `state rm`, and `taint`. Commands that only read or don't touch state, like `fmt`, `validate`, `output`, and `show`, don't need it.

### What the error looks like

```text
Error: Error acquiring the state lock

Error message: state blob is already locked
Lock Info:
  ID:        3f1c2a9e-7b4d-4c1e-9a2f-6d8e5b0c1a77
  Path:      tfstate/dev/app.tfstate
  Operation: OperationTypeApply
  Who:       azureuser@build-agent-01
  Version:   1.9.5
  Created:   2026-10-20 09:15:42.123 +0000 UTC
  Info:

Terraform acquires a state lock to protect the state from being written
by multiple users at the same time.
```

| Field | Tells you |
| --- | --- |
| **ID** | The lock ID, needed for `terraform force-unlock` |
| **Operation** | What the other run is doing (plan, apply) |
| **Who** | User and machine (for example a pipeline agent) |
| **Created** | When it started: an old timestamp suggests a stuck lock |

### What to do

1. Use **Who** and **Created** to find the other run: is a pipeline still running?
2. If it is running, **wait**, or use `-lock-timeout=10m` so Terraform retries instead of failing immediately:

   ```bash
   terraform apply -lock-timeout=10m
   ```

3. If the run was cancelled or crashed, release it:

   ```bash
   terraform force-unlock 3f1c2a9e-7b4d-4c1e-9a2f-6d8e5b0c1a77
   ```

`terraform plan -lock=false` skips locking. It is acceptable only for a quick read-only check, and **never** for apply.

### Interview answer

> "Both. Plan and apply both acquire the lock by default, so either one shows 'Error acquiring the state lock' with the lock info: the lock ID, the operation, who holds it, and when it was created. I use 'Who' and 'Created' to find the other run. If it's still running, I wait or use `-lock-timeout`. If it was a cancelled pipeline, I use `terraform force-unlock` with the lock ID. I never disable locking for apply."

</details>

---

<details><summary>Q22. What are workspaces and data sources in Terraform?</summary>

### Workspaces

A **workspace** lets you use the **same code with separate state files**. Each workspace has its own state, so `dev` and `qa` don't overwrite each other.

```bash
terraform workspace new dev
terraform workspace new qa
terraform workspace list
#   default
# * qa
#   dev
terraform workspace select dev
terraform apply -var-file=dev.tfvars
```

Use the workspace name inside the code:

```hcl
resource "azurerm_resource_group" "rg" {
  name     = "rg-app-${terraform.workspace}"   # rg-app-dev, rg-app-qa
  location = "eastus"
}
```

With the azurerm backend, each workspace gets its own state blob in the same container.

**Limitation:** all workspaces share the same backend and the same credentials, and it is easy to apply to the wrong one. For **production**, many teams prefer **separate folders or separate backend keys per environment** (with separate service connections), and use workspaces for short-lived or similar environments.

(In HCP Terraform / Terraform Cloud, a "workspace" means something bigger: a separate unit with its own state, variables, and runs.)

### Data sources

A **data source** **reads** information about something that **already exists** (created manually or by another Terraform project). It never creates or changes it.

| `resource` | `data` |
| --- | --- |
| Creates, updates, deletes | Only reads |
| `resource "azurerm_resource_group" "rg"` | `data "azurerm_resource_group" "shared"` |

Real examples:

```hcl
# Current login details (tenant ID, object ID of the pipeline identity)
data "azurerm_client_config" "current" {}

# A VNet created by the network team
data "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  virtual_network_name = "vnet-hub"
  resource_group_name  = "rg-network"
}

# A secret already in Key Vault
data "azurerm_key_vault" "kv" {
  name                = "kv-shared-dev"
  resource_group_name = "rg-shared"
}

data "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  key_vault_id = data.azurerm_key_vault.kv.id
}

resource "azurerm_kubernetes_cluster" "aks" {
  # ...
  default_node_pool {
    name           = "system"
    vm_size        = "Standard_D4s_v5"
    vnet_subnet_id = data.azurerm_subnet.aks.id
  }
}
```

Note: values read by data sources, including secrets, are stored in the state file, so the state must be secured.

### Interview answer

> "A workspace lets me use the same Terraform code with separate state files, for example dev and qa, and I can use `terraform.workspace` in names. For production, I prefer separate backend keys or folders per environment for stronger isolation. A data source reads existing resources without managing them, for example a subnet created by the network team, the current tenant with `azurerm_client_config`, or a secret from Key Vault, so I can reference them in my resources."

</details>

---

<details><summary>Q23. What are input variables in Terraform?</summary>

**Input variables** are the **parameters** of your Terraform code. Instead of hardcoding values like the location or VM size, you declare variables and pass different values per environment, so the same code works for dev, qa, and prod.

### Declaring a variable

```hcl
variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name"
  type        = string

  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "environment must be dev, qa, or prod."
  }
}

variable "node_count" {
  type    = number
  default = 3
}

variable "tags" {
  type = map(string)
  default = {
    owner = "devops"
  }
}
```

Use it with `var.<name>`:

```hcl
resource "azurerm_resource_group" "rg" {
  name     = "rg-app-${var.environment}"
  location = var.location
  tags     = var.tags
}
```

### Variable types

| Type | Example |
| --- | --- |
| `string` | `"eastus"` |
| `number` | `3` |
| `bool` | `true` |
| `list(string)` | `["10.10.1.0/24", "10.10.2.0/24"]` |
| `map(string)` | `{ owner = "devops", env = "dev" }` |
| `object({...})` | `{ name = "web", size = "Standard_B2s" }` |

### Variable arguments

| Argument | Purpose |
| --- | --- |
| `description` | Documents what it is for |
| `type` | Rejects wrong values early |
| `default` | Makes it optional; without it, the variable is required |
| `validation` | Custom rules with a clear error message |
| `sensitive` | Hides the value in plan/apply output (Q25) |
| `nullable` | Whether `null` is allowed |

### Ways to pass values

```bash
terraform apply -var="environment=dev"            # command line
terraform apply -var-file="dev.tfvars"            # tfvars file
export TF_VAR_environment=dev                     # environment variable
# or terraform.tfvars / *.auto.tfvars, which load automatically
```

If a required variable has no value, Terraform asks for it interactively (and fails in a pipeline, which is good).

### Interview answer

> "Input variables are the parameters of the Terraform code, so the same code can deploy different environments. I declare them with a description, type, and default if they're optional, and add validation rules, for example allowing only dev, qa, or prod. Values come from tfvars files per environment, `-var` on the command line, or `TF_VAR_` environment variables in the pipeline, and I mark secrets as sensitive."

</details>

---

<details><summary>Q24. What is the difference between local values and tfvars in Terraform?</summary>

- **Locals** are **internal helper values** calculated **inside** the code. They cannot be changed from outside.
- **tfvars files** are **value files** that **supply inputs** to variables from outside, usually one file per environment.

Simple analogy: variables are the **form fields**, tfvars is **how you fill in the form** for each environment, and locals are **calculations the code does** with what you filled in.

| | `locals` | `.tfvars` |
| --- | --- | --- |
| Purpose | Avoid repetition, compute values | Provide values for input variables |
| Defined in | `locals { }` block in `.tf` files | `dev.tfvars`, `prod.tfvars`, `terraform.tfvars` |
| Can be overridden from outside? | No | Yes, it is the outside input |
| Can use expressions and functions? | Yes | No, only literal values |
| Referenced as | `local.name` | Fills `var.name` |

### Example

`variables.tf`:

```hcl
variable "environment" { type = string }
variable "location"    { type = string }
variable "owner"       { type = string }
```

`dev.tfvars` (values from outside):

```hcl
environment = "dev"
location    = "eastus"
owner       = "devops-team"
```

`prod.tfvars`:

```hcl
environment = "prod"
location    = "westeurope"
owner       = "platform-team"
```

`main.tf` with locals (calculations inside):

```hcl
locals {
  name_prefix = "app-${var.environment}-${var.location}"

  common_tags = {
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_storage_account" "sa" {
  name                     = "st${var.environment}app001"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.common_tags   # same tags reused
}
```

```bash
terraform apply -var-file=dev.tfvars
terraform apply -var-file=prod.tfvars
```

### Variable value precedence (lowest to highest)

1. `default` in the variable block
2. `TF_VAR_` environment variables
3. `terraform.tfvars`
4. `terraform.tfvars.json`
5. `*.auto.tfvars` (alphabetical order)
6. `-var` and `-var-file` on the command line (the last one wins)

**Tip:** never commit secrets in tfvars files. Pass them from Key Vault or pipeline secret variables as `TF_VAR_` environment variables.

### Interview answer

> "Locals are internal values computed inside the code, like a name prefix or a common tags map, to avoid repetition. They can't be overridden from outside. A tfvars file supplies values for input variables from outside, usually one per environment, like `dev.tfvars` and `prod.tfvars`. So tfvars change what goes in, and locals compute values from it. I keep secrets out of tfvars and pass them as `TF_VAR_` environment variables from Key Vault."

</details>

---

<details><summary>Q25. Explain variables.tf, outputs.tf, and sensitive variables in Terraform.</summary>

Terraform reads **all `.tf` files in a folder together**. The file names are a **convention** for readability, not a requirement.

### Standard file layout

```text
app/
 ├── providers.tf      # terraform {}, required_providers, provider config, backend
 ├── main.tf           # resources and modules
 ├── variables.tf      # input variable declarations
 ├── outputs.tf        # output values
 ├── locals.tf         # local values (optional)
 ├── dev.tfvars        # values for dev
 └── prod.tfvars       # values for prod
```

### variables.tf

Declares the **inputs** of the configuration or module (see Q23):

```hcl
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "sql_admin_password" {
  description = "Admin password for Azure SQL"
  type        = string
  sensitive   = true
}
```

### outputs.tf

Exposes **values after apply**: to show them, to pass them to a pipeline, or to give them to a parent module.

```hcl
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.rg.name
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "sql_connection_string" {
  value     = "Server=tcp:${azurerm_mssql_server.sql.fully_qualified_domain_name},1433;"
  sensitive = true
}
```

```bash
terraform output                          # list all outputs
terraform output -raw aks_cluster_name    # use in a script or pipeline
terraform output -json                    # machine-readable
```

Real use: the infra pipeline outputs the AKS name and ACR login server, and the app deployment pipeline uses them. In modules, the parent reads outputs as `module.network.subnet_id`.

### Sensitive variables

`sensitive = true` **hides the value in the plan, apply, and output display**:

```text
  + administrator_login_password = (sensitive value)
```

**Important limitations:**

1. The value is **still stored in plain text in the state file**. So the state must be protected (private storage account, RBAC, encryption).
2. `terraform output -raw sql_connection_string` **still shows it**. `sensitive` only hides it from normal logs.
3. Don't put the value in tfvars committed to Git. Pass it in safely:

   ```bash
   export TF_VAR_sql_admin_password="$(az keyvault secret show \
     --vault-name kv-shared-dev -n sql-admin-password --query value -o tsv)"
   terraform apply -var-file=dev.tfvars
   ```

   Or in Azure DevOps, map a secret pipeline variable (linked to Key Vault) to `TF_VAR_sql_admin_password`.

Newer Terraform versions (1.10+) add **ephemeral** variables and (1.11+) **write-only** arguments, which keep secrets out of the state entirely, for providers that support them.

Even better: let Azure generate and manage the secret, or use Entra ID authentication for Azure SQL instead of passwords.

### Interview answer

> "`variables.tf` declares the inputs with their types, descriptions, defaults, and validation. `outputs.tf` exposes values after apply, like the AKS name or resource IDs, which I use in pipelines or pass between modules. Marking a variable or output as `sensitive` hides it in plan and apply logs, but it's still stored in plain text in the state file, so I secure the state backend and pass secrets from Key Vault through `TF_VAR_` environment variables instead of committing them in tfvars."

</details>

---

<details><summary>Q26. What is the Terraform Registry?</summary>

The **Terraform Registry** ([registry.terraform.io](https://registry.terraform.io)) is the public place where you find **providers** and **modules**, with their documentation and versions.

| It hosts | Example | Used for |
| --- | --- | --- |
| **Providers** | `hashicorp/azurerm`, `hashicorp/azuread`, `azure/azapi` | Talking to platform APIs (Q18) |
| **Modules** | Azure Verified Modules (`Azure/avm-res-...`) | Reusable, tested building blocks (VNet, AKS, Key Vault) |
| **Documentation** | Every resource's arguments, attributes, and examples | Daily reference when writing code |

### How Terraform uses it

When you run `terraform init`, Terraform downloads providers and modules from the registry using the **source address**:

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"    # registry.terraform.io/hashicorp/azurerm
      version = "~> 4.0"
    }
  }
}

module "vnet" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm"
  version = "x.y.z"   # pin the exact version shown on the registry page

  name                = "vnet-app-dev"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  address_space       = ["10.10.0.0/16"]
}
```

### Provider tiers

- **Official:** maintained by HashiCorp (`hashicorp/azurerm`).
- **Partner:** maintained by the vendor (`azure/azapi`, `microsoft/azuredevops`).
- **Community:** maintained by individuals; review them carefully before use.

### Private registry

Companies publish their **own approved modules** (for example, a standard AKS module with security settings built in) to a **private registry** in HCP Terraform / Terraform Enterprise, or reference them from a Git repo:

```hcl
module "aks" {
  source = "git::https://dev.azure.com/myorg/infra/_git/tf-modules//aks?ref=v1.4.0"
}
```

### Good practices

- Always **pin versions** for providers and modules.
- Read the module's inputs and outputs, and check how recently it was updated.
- Commit `.terraform.lock.hcl` for provider versions.

### Interview answer

> "The Terraform Registry is the public catalogue of providers and modules, with documentation for every resource. When I run `terraform init`, Terraform downloads the providers like `hashicorp/azurerm` and any registry modules, such as Azure Verified Modules, based on their source address and version. I always pin versions. In companies, we also keep our own standard modules in a private registry or a Git repo with version tags, so every team builds resources the same approved way."

</details>

---

<details><summary>Q27. Terraform has a state file. How is state managed in Bicep?</summary>

**Bicep has no state file.** Azure itself is the source of truth.

When you deploy a Bicep file, it is converted to an ARM template and sent to **Azure Resource Manager (ARM)**. ARM compares the template with the resources that **currently exist in Azure** and creates or updates whatever is different. Running the same deployment again makes no changes: deployments are **idempotent**.

| | Terraform | Bicep |
| --- | --- | --- |
| Where state is kept | `terraform.tfstate` (remote backend) | No state file; Azure (ARM) is the state |
| Must store and lock state? | Yes (storage account, blob lease) | No |
| Preview changes | `terraform plan` | `az deployment group what-if` |
| Deleting removed resources | Automatic (resource removed from code → destroyed) | Not by default (incremental mode); use **deployment stacks** |
| Deployment history | Your pipeline logs | Stored in Azure: resource group → **Deployments** |
| Clouds | Multi-cloud | Azure only |

### Preview changes with what-if

```bash
az deployment group what-if \
  --resource-group rg-app-dev \
  --template-file main.bicep \
  --parameters main.dev.bicepparam
```

```text
Resource changes: 1 to create, 1 to modify.
  + Microsoft.Storage/storageAccounts/stappdev001
  ~ Microsoft.Network/virtualNetworks/vnet-app-dev
```

### Deploy

```bash
az deployment group create \
  --resource-group rg-app-dev \
  --template-file main.bicep \
  --parameters main.dev.bicepparam
```

### What happens to resources you remove from the code?

- **Incremental mode (default):** resources not in the template are **left alone**. Removing a resource from Bicep does **not** delete it in Azure.
- **Complete mode:** deletes resources in the resource group that are not in the template. Risky, use with care.
- **Deployment stacks (recommended):** Azure tracks the set of resources the deployment manages, which is the closest thing to Terraform state. You choose what happens to removed resources and can block manual changes:

  ```bash
  az stack group create \
    --name stack-app-dev \
    --resource-group rg-app-dev \
    --template-file main.bicep \
    --parameters main.dev.bicepparam \
    --action-on-unmanage deleteResources \
    --deny-settings-mode denyDelete
  ```

### Drift

With no state file, there is no "state drift" problem. Each deployment compares against the real Azure resources. Manual changes in the portal are **overwritten** for properties defined in the template the next time the deployment runs, so `what-if` in the pipeline is how you detect them.

### Interview answer

> "Bicep doesn't use a state file. It compiles to an ARM template, and Azure Resource Manager compares it with the actual resources in Azure and applies only the differences, so Azure itself is the state. That means there's no state storage or locking to manage. I use `what-if` to preview changes, like `terraform plan`. By default, Bicep runs in incremental mode, so resources removed from the code are not deleted. To manage the full lifecycle, including deletion, I use deployment stacks, which track the managed resources and can also deny manual changes."

</details>

---

## Azure identity and access

<details><summary>Q28. What are Entra ID and enterprise applications in Azure?</summary>

### Microsoft Entra ID

**Microsoft Entra ID** (formerly **Azure Active Directory**) is Microsoft's cloud **identity service**. It answers two questions for everything in Azure and Microsoft 365:

- **Authentication:** who are you? (sign-in, MFA)
- **Authorization:** what are you allowed to access? (tokens, roles, consent)

It stores and manages:

| Object | Example |
| --- | --- |
| Users | `john@company.com` |
| Groups | `aks-admins`, `devops-team` |
| Applications (app registrations) | Our web app that lets users sign in with company accounts |
| Service principals / enterprise applications | The identity an app or pipeline uses in our tenant |
| Managed identities | The identity of an AKS workload or App Service |

Common features: **SSO**, **MFA**, **Conditional Access** (for example, block sign-in from outside allowed countries), **Privileged Identity Management** (just-in-time admin access).

**Entra ID roles vs Azure RBAC roles:** Entra ID roles (Global Administrator, User Administrator) manage the **directory**. Azure RBAC roles (Owner, Contributor, Reader) manage **Azure resources**. These are different systems.

### App registration vs enterprise application

This is the confusing part, so explain it with two objects:

| | App registration | Enterprise application |
| --- | --- | --- |
| What it is | The **application object**: the global definition of the app | The **service principal**: the app's instance in a specific tenant |
| Where it lives | Only in the tenant where the app was created | In every tenant that uses the app |
| What you configure | Redirect URIs, secrets/certificates, federated credentials, API permissions it requests | Who can use it (user assignment), SSO settings, admin consent, Conditional Access, sign-in logs |
| Analogy | The **class** | The **object/instance** |

When you create an app registration in the portal, Azure **automatically creates the matching enterprise application** (service principal) in your tenant.

### Real examples

1. **Our own app:** we create an app registration for a Spring Boot app so users sign in with Entra ID (OAuth2/OpenID Connect). In the enterprise application, we turn on "Assignment required" and assign only the `sales-team` group.
2. **A SaaS app (Jira, ServiceNow, Salesforce):** we add it from the **Enterprise applications gallery** and configure SAML SSO. There is no app registration in our tenant, because the vendor owns the app.
3. **Azure DevOps service connection:** it creates an app registration, and its service principal (enterprise application) gets RBAC roles on the subscription.
4. **Managed identities** also appear under Enterprise applications (filter by "Managed Identities"), but you manage them from the managed identity resource.

### Interview answer

> "Entra ID is Azure's identity service for users, groups, and applications, handling sign-in, MFA, Conditional Access, and tokens. An app registration is the global definition of an application, where we configure redirect URIs, credentials, and API permissions. An enterprise application is its service principal in our tenant, where we control who can use it, configure SSO, grant consent, and check sign-in logs. For example, for SaaS apps like ServiceNow, we add an enterprise application from the gallery for SSO, and for our own apps or pipelines, we create an app registration and assign roles to its service principal."

</details>

---

<details><summary>Q29. User-assigned vs system-assigned managed identity?</summary>

A **managed identity** gives an Azure resource its own identity in Entra ID, so it can access other Azure services (Key Vault, Storage, SQL) **without any passwords or secrets in code**. Azure creates and rotates the credentials.

| | System-assigned | User-assigned |
| --- | --- | --- |
| Created how | Enabled **on** a resource (a switch on the VM or App Service) | Created as a **separate Azure resource** |
| Lifecycle | Tied to the resource. Delete the VM → identity is deleted | Independent. Survives when resources are deleted |
| Shared? | No, one resource only | Yes, can be attached to **many** resources |
| Role assignments | Must be redone if the resource is recreated | Stay the same when resources are recreated |
| Best for | A single resource with its own access needs | Many resources needing the same access, AKS Workload ID, resources recreated often |

### Example: system-assigned (one App Service reads from Key Vault)

```bash
az webapp identity assign -g rg-app-dev -n app-orders-dev

PRINCIPAL_ID=$(az webapp identity show -g rg-app-dev -n app-orders-dev \
  --query principalId -o tsv)

az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$(az keyvault show -n kv-orders-dev --query id -o tsv)"
```

If the App Service is deleted, the identity and its access are removed automatically, so nothing is left over.

### Example: user-assigned (10 VMs in a scale set read from the same Storage account)

```bash
az identity create -g rg-app-dev -n id-batch-workers

az vmss identity assign -g rg-app-dev -n vmss-batch \
  --identities id-batch-workers
```

The role is assigned **once** to `id-batch-workers`. When the scale set is rebuilt, or another VM needs the same access, just attach the same identity.

### Why user-assigned is common in AKS and pipelines

- **AKS Workload ID** requires a user-assigned identity with a federated credential (see [Epam3.md, Q9](Epam3.md)).
- With Terraform or Bicep, you can create the identity and its role assignments **before** the resource exists, which avoids "identity not ready yet" ordering problems.

### Interview answer

> "A system-assigned identity is enabled on one resource and shares its lifecycle, so if I delete the App Service, its identity is deleted too. I use it when one resource needs its own access, like an App Service reading Key Vault. A user-assigned identity is a separate resource that can be attached to many resources and survives when they're deleted, so the role assignments stay. I use it for AKS Workload ID, for scale sets or multiple apps that need the same access, and when resources are recreated often by Terraform."

</details>

---

<details><summary>Q30. How do you create a custom role in Azure?</summary>

Create a **custom role** when no built-in role matches the access you need. Built-in roles are often too broad (Contributor) or too narrow (Reader).

**Scenario:** the support team should be able to **start, stop, and restart VMs** and view them, but **not create, delete, or resize** them.

### Step 1: Find the right actions

```bash
az provider operation show --namespace Microsoft.Compute \
  --query "resourceTypes[?name=='virtualMachines'].operations[].name" -o tsv
```

### Step 2: Write the role definition (`vm-operator-role.json`)

```json
{
  "Name": "VM Operator (Custom)",
  "IsCustom": true,
  "Description": "Can view, start, stop, and restart virtual machines.",
  "Actions": [
    "Microsoft.Compute/virtualMachines/read",
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/powerOff/action",
    "Microsoft.Compute/virtualMachines/deallocate/action",
    "Microsoft.Compute/virtualMachines/restart/action",
    "Microsoft.Compute/virtualMachines/instanceView/read",
    "Microsoft.Resources/subscriptions/resourceGroups/read"
  ],
  "NotActions": [],
  "DataActions": [],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/<subscription-id>"
  ]
}
```

| Field | Meaning |
| --- | --- |
| `Actions` | Allowed **management** operations (control plane) |
| `NotActions` | Operations removed from `Actions` (subtraction, not an explicit deny) |
| `DataActions` | Allowed operations on **data**, such as reading blobs or Key Vault secrets |
| `AssignableScopes` | Where the role can be assigned (management group, subscription, or resource group) |

### Step 3: Create the role

```bash
az role definition create --role-definition @vm-operator-role.json
```

### Step 4: Assign it (to a group, not individual users)

```bash
az role assignment create \
  --assignee-object-id "<support-team-group-object-id>" \
  --assignee-principal-type Group \
  --role "VM Operator (Custom)" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/rg-app-prod"
```

### Portal way

Subscription → **Access control (IAM)** → **Add** → **Add custom role** → start from scratch or **clone a built-in role** (for example, clone Virtual Machine Contributor and remove permissions) → add permissions → set assignable scopes → **Review + create**.

### Terraform way

```hcl
resource "azurerm_role_definition" "vm_operator" {
  name        = "VM Operator (Custom)"
  scope       = data.azurerm_subscription.current.id
  description = "Can view, start, stop, and restart virtual machines."

  permissions {
    actions = [
      "Microsoft.Compute/virtualMachines/read",
      "Microsoft.Compute/virtualMachines/start/action",
      "Microsoft.Compute/virtualMachines/powerOff/action",
      "Microsoft.Compute/virtualMachines/deallocate/action",
      "Microsoft.Compute/virtualMachines/restart/action",
      "Microsoft.Compute/virtualMachines/instanceView/read",
      "Microsoft.Resources/subscriptions/resourceGroups/read",
    ]
    not_actions = []
  }

  assignable_scopes = [data.azurerm_subscription.current.id]
}

resource "azurerm_role_assignment" "support_vm_operator" {
  scope              = azurerm_resource_group.prod.id
  role_definition_id = azurerm_role_definition.vm_operator.role_definition_resource_id
  principal_id       = var.support_group_object_id
}
```

### Good practices

- Start from the **least privilege**; avoid wildcards like `Microsoft.Compute/*`.
- Assign to **groups**, at the **smallest scope** needed.
- Keep role definitions in code (Terraform/Bicep) so changes are reviewed.
- Test with a test user before rolling out.

### Interview answer

> "When no built-in role fits, I create a custom role. For example, for a support team that should only start, stop, and restart VMs, I list the exact actions with `az provider operation show`, write a JSON definition with the Actions, any DataActions, and the assignable scopes, and create it with `az role definition create`. Then I assign it to the support group at the resource-group scope. In real projects, I keep custom roles in Terraform so changes go through review, and I follow least privilege with no broad wildcards."

</details>

---

<details><summary>Q31. How do you create a service connection manually and via Bicep code in Azure?</summary>

First, clarify one important point: an **Azure DevOps service connection is an Azure DevOps object, not an Azure resource**. Bicep deploys only Azure resources through ARM, so **Bicep cannot create the service connection itself**.

What we automate:

- **Bicep:** the **Azure side**: managed identity, federated credential, and role assignments.
- **Azure DevOps CLI / REST API / Terraform `azuredevops` provider:** the **service connection** itself.

### Method 1: Manually in Azure DevOps (workload identity federation)

**Automatic option (quickest, needs high permissions):**

1. Azure DevOps → **Project settings** → **Service connections** → **New service connection**.
2. Choose **Azure Resource Manager**.
3. Identity type: **App registration (automatic)**, credential: **Workload identity federation**.
4. Scope: **Subscription** → choose the subscription and, optionally, a **resource group** to limit access.
5. Name it, for example `sc-azure-dev`.
6. **Do not** tick "Grant access permission to all pipelines". Authorize pipelines individually.
7. Save. Azure DevOps creates the app registration, federated credential, and role assignment for you.

**Manual option (when you're not allowed to create app registrations, or want to use your own managed identity):**

1. Create a **user-assigned managed identity** (or app registration) in Azure.
2. In Azure DevOps, create the service connection with identity type **App registration or managed identity (manual)** and credential **Workload identity federation**.
3. Azure DevOps shows an **Issuer** and a **Subject identifier**. Copy them exactly.
4. In Azure, on the managed identity → **Federated credentials** → **Add** → "Other issuer" → paste the issuer and subject.
5. Give the identity an RBAC role (for example **Contributor** on the target resource group).
6. Back in Azure DevOps, enter the client ID, tenant ID, and subscription, then **Verify and save**.

Then add **Approvals and checks** on the service connection for production.

### Method 2: Azure side with Bicep

```bicep
param location string = resourceGroup().location
param adoIssuer string    // copied from the service connection
param adoSubject string   // copied from the service connection

resource deployIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-ado-deploy-dev'
  location: location
}

resource adoFederation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: deployIdentity
  name: 'ado-sc-azure-dev'
  properties: {
    issuer: adoIssuer
    subject: adoSubject
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

// Contributor on this resource group
resource contributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deployIdentity.id, 'contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
    principalId: deployIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output clientId string = deployIdentity.properties.clientId
```

```bash
az deployment group create -g rg-app-dev \
  --template-file ado-identity.bicep \
  --parameters adoIssuer="<issuer>" adoSubject="<subject>"
```

Then create the service connection with the `clientId` output (manually, with `az devops service-endpoint create`, or with the REST API).

### Method 3: Fully in code with Terraform

The `azuredevops` provider can create the service connection, and `azurerm` creates the identity and federated credential in the same run:

```hcl
resource "azurerm_user_assigned_identity" "ado" {
  name                = "id-ado-deploy-dev"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

resource "azuredevops_serviceendpoint_azurerm" "dev" {
  project_id                             = data.azuredevops_project.app.id
  service_endpoint_name                  = "sc-azure-dev"
  service_endpoint_authentication_scheme = "WorkloadIdentityFederation"

  credentials {
    serviceprincipalid = azurerm_user_assigned_identity.ado.client_id
  }

  azurerm_spn_tenantid      = data.azurerm_client_config.current.tenant_id
  azurerm_subscription_id   = data.azurerm_client_config.current.subscription_id
  azurerm_subscription_name = "sub-app-dev"
}

resource "azurerm_federated_identity_credential" "ado" {
  name                = "ado-sc-azure-dev"
  resource_group_name = azurerm_resource_group.rg.name
  parent_id           = azurerm_user_assigned_identity.ado.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azuredevops_serviceendpoint_azurerm.dev.workload_identity_federation_issuer
  subject             = azuredevops_serviceendpoint_azurerm.dev.workload_identity_federation_subject
}

resource "azurerm_role_assignment" "ado_contributor" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.ado.principal_id
}
```

### Interview answer

> "Manually, I go to Project settings, Service connections, and create an Azure Resource Manager connection with workload identity federation, scoped to the subscription or resource group, without granting access to all pipelines. If I'm using my own managed identity, I copy the issuer and subject from Azure DevOps into a federated credential on the identity and assign it an RBAC role. A service connection is an Azure DevOps object, not an Azure resource, so Bicep can't create it directly. With Bicep, I create the managed identity, federated credential, and role assignment, and then create the connection with the Azure DevOps CLI or REST API. If we want everything in code, the Terraform `azuredevops` provider can create the service connection too."

</details>

---

<details><summary>Q32. How do you create federated credentials, and how do you use them?</summary>

A **federated credential** tells Entra ID: *"Trust tokens from this external identity provider, but only for this exact subject."* The external system (Azure DevOps, GitHub Actions, AKS, GitLab) presents its own short-lived token, and Entra ID exchanges it for an Azure access token. **No client secret or certificate is stored anywhere.**

```text
GitHub Actions / Azure DevOps / AKS pod
        |  1. gets its own OIDC token (signed by the issuer)
        v
Microsoft Entra ID
        |  2. checks the federated credential:
        |     issuer matches? subject matches? audience matches?
        v
Azure access token (short-lived)
        |  3. used to call Azure with the identity's RBAC roles
        v
Azure resources
```

A federated credential has three key fields:

| Field | Meaning | Example |
| --- | --- | --- |
| **Issuer** | Who issues the external token | `https://token.actions.githubusercontent.com` |
| **Subject** | Which exact workload is trusted | `repo:myorg/orders-api:environment:prod` |
| **Audience** | Who the token is for | `api://AzureADTokenExchange` |

It can be added to an **app registration** or a **user-assigned managed identity** (up to 20 per identity).

### Example: GitHub Actions deploying to Azure

**Step 1: Create the identity and federated credential**

```bash
az identity create -g rg-cicd -n id-github-orders

az identity federated-credential create \
  --name github-orders-prod \
  --identity-name id-github-orders \
  --resource-group rg-cicd \
  --issuer "https://token.actions.githubusercontent.com" \
  --subject "repo:myorg/orders-api:environment:prod" \
  --audiences "api://AzureADTokenExchange"
```

For an app registration instead:

```bash
az ad app federated-credential create --id <app-id> --parameters '{
  "name": "github-orders-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:myorg/orders-api:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

**Step 2: Give it RBAC access**

```bash
az role assignment create \
  --assignee-object-id "$(az identity show -g rg-cicd -n id-github-orders --query principalId -o tsv)" \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "/subscriptions/<sub-id>/resourceGroups/rg-orders-prod"
```

**Step 3: Use it in the workflow**

```yaml
name: deploy
on:
  push:
    branches: [main]

permissions:
  id-token: write     # allows the job to request the OIDC token
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: prod   # must match the federated credential subject
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: az group show -n rg-orders-prod
```

The client ID, tenant ID, and subscription ID are **not secrets**. There is no password anywhere.

### Where else we use federated credentials

| Use case | Issuer | Subject |
| --- | --- | --- |
| Azure DevOps service connection | Shown in the service connection (Q31) | Shown in the service connection |
| AKS Workload ID | AKS OIDC issuer URL | `system:serviceaccount:<namespace>:<service-account>` ([Epam3.md, Q9](Epam3.md)) |
| GitLab CI | `https://gitlab.com` | `project_path:mygroup/myproject:ref_type:branch:ref:main` |

### Common errors

| Error | Cause |
| --- | --- |
| `AADSTS70021: No matching federated identity record found` | The subject doesn't match exactly (wrong branch, environment, repo name, or case) |
| `AADSTS700213` / audience errors | Audience is not `api://AzureADTokenExchange` |
| Login works, but deployment gets 403 | The identity is missing an RBAC role on the target scope |

### Interview answer

> "A federated credential lets an external workload like GitHub Actions, Azure DevOps, or an AKS pod use its own short-lived OIDC token to get an Azure token, so no client secret is stored. I add it to a user-assigned managed identity or app registration with three values: the issuer, the exact subject, for example a specific repo and environment, and the audience `api://AzureADTokenExchange`. Then I assign RBAC roles to the identity. In GitHub Actions, I set `id-token: write` and use `azure/login` with just the client, tenant, and subscription IDs. The most common error is a subject mismatch, so I keep the subject as specific as possible, for example scoped to the prod environment."

</details>

---

## Important interview tip

Describe only the work you actually performed. If a tool or setting here (for example, KMS etcd encryption, deployment stacks, or a specific network plugin) was configured by another team in your project, say so, and explain the parts you used, operated, or troubleshot.
