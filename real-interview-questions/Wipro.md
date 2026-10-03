# Wipro - Interview Questions

## Q1. What is umask?

`umask` in Linux defines the default permission restrictions applied when a new file or directory is created.

Think of it as a **permission filter**.

### Default permissions

Linux starts with:

- **Files:** `666` → `rw-rw-rw-`
- **Directories:** `777` → `rwxrwxrwx`

Then `umask` removes permissions from these defaults.

### Example

```bash
umask
```

Output:

```text
0022
```

For a new file:

```text
  666
- 022
-----
  644
```

So the file gets:

```text
-rw-r--r--
```

For a directory:

```text
  777
- 022
-----
  755
```

So the directory gets:

```text
drwxr-xr-x
```

### Common umask values

| umask | New file | New directory |
| --- | --- | --- |
| 022 | 644 | 755 |
| 027 | 640 | 750 |
| 077 | 600 | 700 |
| 002 | 664 | 775 |

### Important interview point

`umask` does **not** directly set permissions. It **removes** permissions from the default permissions.

For example:

```bash
umask 077
touch test.txt
```

Result:

```text
-rw-------
```

And:

```bash
mkdir testdir
```

Result:

```text
drwx------
```

### How to change it

Temporarily, for the current shell:

```bash
umask 027
```

Check it:

```bash
umask
```

For a persistent user setting, it is commonly configured in shell startup files such as:

```text
~/.bashrc
```

### Interview answer

> "umask is used in Linux to control the default permissions of newly created files and directories. It acts as a permission mask by removing permissions from the default 666 for files and 777 for directories. For example, with umask 022, new files get 644 and directories get 755."

---

## Q2. How do you authenticate to an AKS cluster?

To authenticate to an AKS cluster, the standard approach is to use **Azure AD / Microsoft Entra ID** with `kubectl`.

### 1. Log in to Azure

```bash
az login
```

If you have multiple subscriptions:

```bash
az account set --subscription "<subscription-name>"
```

### 2. Get the AKS credentials

```bash
az aks get-credentials \
  --resource-group my-rg \
  --name my-aks
```

This downloads and merges the AKS credentials into your local kubeconfig, usually:

```text
~/.kube/config
```

### 3. Verify authentication

```bash
kubectl get nodes
```

or:

```bash
kubectl get pods -A
```

If Entra ID integration is enabled, `kubectl` can authenticate using your Azure identity.

### In a DevOps pipeline

For Azure DevOps, I would normally use an **Azure Resource Manager service connection** or a **workload identity / service principal**, depending on the setup.

For example, the pipeline authenticates to Azure and then retrieves the AKS credentials:

```bash
az login
az aks get-credentials \
  --resource-group my-rg \
  --name my-aks \
  --overwrite-existing

kubectl get pods
```

For automated workloads, avoid storing usernames/passwords or long-lived client secrets. Workload identity / managed identity is preferred where supported.

### AKS authentication vs. authorization

This distinction is important in interviews.

**Authentication = Who are you?**

```text
Azure AD / Microsoft Entra ID
        ↓
     kubectl
        ↓
  AKS API Server
```

**Authorization = What are you allowed to do?**

```text
   Microsoft Entra ID
          ↓
Azure RBAC / Kubernetes RBAC
          ↓
Permissions on AKS resources
```

For example, you may successfully authenticate to AKS but still get:

```text
Error from server (Forbidden)
```

because your identity doesn't have the required Kubernetes RBAC or Azure RBAC permissions.

### Interview answer

> "I authenticate to AKS using Microsoft Entra ID. First I log in using `az login`, select the required subscription, and run `az aks get-credentials` to configure the kubeconfig. Then I use `kubectl` to interact with the cluster. In CI/CD, I use an Azure service connection or workload identity rather than personal credentials. Authentication verifies the identity, while Kubernetes RBAC or Azure RBAC controls what that identity can access."

---

## Q3. What is a headless Service?

A **headless Service** in Kubernetes is a Service that does **not** get a ClusterIP. It is mainly used when you want to communicate directly with individual Pods rather than through a single virtual IP.

### How it works

Normally:

```text
      Client
        ↓
Service (ClusterIP)
        ↓
Pod 1   Pod 2   Pod 3
```

With a headless Service:

```text
      Client
        ↓
       DNS
        ↓
Pod 1   Pod 2   Pod 3
```

You create it using:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  clusterIP: None
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```

The important configuration is:

```yaml
clusterIP: None
```

Instead of returning one ClusterIP, Kubernetes DNS returns the **Pod IP addresses** associated with the Service.

### Why use it?

Headless Services are commonly used for:

- StatefulSets
- Databases such as PostgreSQL, Cassandra and MongoDB
- Applications where Pods need to discover each other
- Systems where clients need to connect to a specific Pod

For example, with a StatefulSet:

```text
my-service
    ↓
pod-0   pod-1   pod-2
```

Each Pod can have a stable DNS identity such as:

```text
pod-0.my-service
pod-1.my-service
pod-2.my-service
```

### Normal vs. headless Service

| Normal Service | Headless Service |
| --- | --- |
| Has a ClusterIP | `clusterIP: None` |
| Provides a virtual IP | No virtual IP |
| Traffic goes through the Service | DNS can return the Pod IPs |
| Common for stateless apps | Common for StatefulSets |
| Load balancing through the Service | Client can discover individual Pods |

### Interview answer

> "A headless Service is a Kubernetes Service with `clusterIP: None`. It doesn't provide a virtual ClusterIP. Instead, Kubernetes DNS returns the IP addresses of the Pods selected by the Service. It's commonly used with StatefulSets and databases where applications need direct Pod discovery and stable network identities."

---

## Q4. How do you integrate Jenkins with Kubernetes?

There are two common ways to integrate Jenkins with Kubernetes. For a DevOps interview, explain the **Kubernetes plugin with dynamic agents**, because that's the common production pattern.

### 1. Jenkins runs outside Kubernetes

For example:

```text
Developer
   ↓
GitHub
   ↓
Jenkins
   ↓
Kubernetes Cluster
   ↓
Dynamic Jenkins Agent Pod
   ↓
Build / Test / Docker / Deploy
```

Jenkins can be running on a VM, while Kubernetes provides temporary build agents.

### 2. Configure Jenkins to communicate with AKS

In Jenkins, install and configure the **Kubernetes plugin**.

Jenkins needs credentials to access the Kubernetes API. For AKS, this can be configured using appropriate Kubernetes credentials or Azure identity-based authentication.

Jenkins then connects to the Kubernetes cluster and can create agent Pods dynamically.

### 3. Define a Kubernetes agent

For example:

```groovy
pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: build
    image: maven:3.9-eclipse-temurin-17
    command:
    - sleep
    args:
    - 99d
'''
        }
    }

    stages {
        stage('Build') {
            steps {
                container('build') {
                    sh 'mvn clean package'
                }
            }
        }

        stage('Test') {
            steps {
                container('build') {
                    sh 'mvn test'
                }
            }
        }
    }
}
```

When the pipeline starts, Jenkins asks Kubernetes to create an agent Pod:

```text
Jenkins Controller
       |
       | Kubernetes API
       ↓
   AKS Cluster
       |
       ↓
 Jenkins Agent Pod
       |
       ├── Build
       ├── Test
       └── Deploy
```

After the pipeline finishes, the temporary agent Pod can be removed.

### 4. Deploy the application to AKS

Another common pattern is:

```text
Git
 ↓
Jenkins
 ↓
Build
 ↓
Unit Test
 ↓
SonarQube
 ↓
Docker Build
 ↓
Trivy Scan
 ↓
Push Image → ACR
 ↓
Helm / kubectl
 ↓
AKS
```

Example:

```bash
docker build -t myacr.azurecr.io/myapp:1.0 .
docker push myacr.azurecr.io/myapp:1.0

helm upgrade --install myapp ./helm \
  --set image.repository=myacr.azurecr.io/myapp \
  --set image.tag=1.0
```

### Important distinction

There are actually two separate integrations you should understand:

- **Jenkins → Kubernetes:** used to create dynamic Jenkins agent Pods.
- **Jenkins → AKS application deployment:** used to deploy your application using `kubectl` or `helm`.

### Interview answer

> "I have integrated Jenkins with Kubernetes using the Kubernetes plugin. Jenkins acts as the controller and Kubernetes provides dynamic agent Pods. When a pipeline starts, Jenkins requests Kubernetes to create an agent Pod with the required tools such as Maven, Docker or kubectl. The pipeline executes on that temporary Pod and the Pod is removed after the job completes. For application deployment, Jenkins authenticates to AKS and uses Helm or kubectl to deploy the application. In our Azure setup, the container images are pushed to ACR and then deployed to AKS."

---

## Q5. If etcd is not available, can you access the Kubernetes cluster?

**No, not normally.** If etcd is completely unavailable in a Kubernetes control plane, the cluster will not function correctly.

### Why?

etcd is the key-value database that stores the Kubernetes cluster state, including:

- Pods and Deployments
- Services
- ConfigMaps and Secrets
- Nodes
- RBAC configuration
- Cluster configuration and desired state

The architecture is roughly:

```text
kubectl
   ↓
kube-apiserver
   ↓
etcd
```

When you run:

```bash
kubectl get pods
```

the request goes to the kube-apiserver, which needs etcd to retrieve the cluster state.

### What happens if etcd is down?

You might still be able to reach the API server:

```bash
kubectl version
```

or establish a connection to the API endpoint, but operations that need to read or write cluster state will generally fail or be unavailable.

For example:

```bash
kubectl get pods
```

may return an error such as:

```text
etcdserver: request timed out
```

**Existing workloads may continue running temporarily**, because the kubelet and container runtime on the worker nodes keep running the Pods they already know about.

But you won't be able to reliably:

- Create new Pods
- Delete or update resources
- Scale Deployments
- Schedule new workloads
- Update the cluster state

### Important interview point

Don't say:

> "If etcd is down, Kubernetes immediately goes down."

That's not precise. A better answer is:

> "etcd is the persistent state store of Kubernetes. If etcd becomes unavailable, the API server may still be reachable, and existing workloads can continue running for some time. However, Kubernetes cannot reliably read or update cluster state, so operations such as creating, updating, deleting, or scaling resources will fail. If etcd is permanently lost, the control plane cannot operate normally."

### What about an HA cluster?

In production, etcd is usually deployed with multiple members, for example:

```text
          kube-apiserver
           /    |    \
          ↓     ↓     ↓
       etcd-1 etcd-2 etcd-3
```

etcd uses **quorum**. With 3 members, you need 2 members available for quorum.

So if one etcd node fails, the Kubernetes control plane can continue operating:

```text
etcd-1 ❌
etcd-2 ✅
etcd-3 ✅
```

If quorum is lost, the control plane cannot reliably process state changes:

```text
etcd-1 ❌
etcd-2 ❌
etcd-3 ✅
```

**AKS note:** in Azure Kubernetes Service, Microsoft manages the control-plane components, including the etcd layer. You generally don't administer the managed control-plane etcd members directly, as you would in a self-managed Kubernetes cluster.

---

## Q6. A Pod is not getting scheduled on a node. Why?

If a Pod is not getting scheduled to a Kubernetes node, the first thing I check is:

```bash
kubectl get pods
kubectl describe pod <pod-name>
```

Look at the **Events** section at the bottom. It usually tells you exactly why the scheduler rejected the nodes.

### Common reasons

#### 1. Insufficient CPU or memory

```text
0/3 nodes are available:
3 Insufficient memory
```

Check:

```bash
kubectl describe node <node-name>
kubectl top nodes
```

The Pod's resource requests may be too high:

```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
```

Either reduce the request or add or scale nodes.

#### 2. nodeSelector mismatch

The Pod has:

```yaml
nodeSelector:
  environment: production
```

but no node has that label.

Check:

```bash
kubectl get nodes --show-labels
```

Add the required label if appropriate:

```bash
kubectl label node <node-name> environment=production
```

#### 3. Node affinity mismatch

For example:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
```

If no node satisfies the required affinity rules, the Pod stays `Pending`. Check the scheduler events with:

```bash
kubectl describe pod <pod-name>
```

#### 4. Taints and tolerations

Check the node:

```bash
kubectl describe node <node-name>
```

You might see:

```text
Taints:
dedicated=gpu:NoSchedule
```

If the Pod doesn't have a matching toleration, it won't be scheduled there. Example toleration:

```yaml
tolerations:
- key: "dedicated"
  operator: "Equal"
  value: "gpu"
  effect: "NoSchedule"
```

#### 5. Node is NotReady

Check:

```bash
kubectl get nodes
```

If you see:

```text
NAME       STATUS
node-01    NotReady
```

investigate:

```bash
kubectl describe node node-01
```

#### 6. Restrictive topology rules

For example:

- `topologySpreadConstraints`
- Pod affinity
- Pod anti-affinity

These can prevent the scheduler from finding a valid node.

### My troubleshooting sequence

> "First, I check whether the Pod is in Pending state using `kubectl get pods`. Then I run `kubectl describe pod <pod-name>` and check the scheduler Events. I specifically check for insufficient CPU or memory, nodeSelector or affinity mismatch, node taints without tolerations, node NotReady status, and topology or scheduling constraints. I then verify node capacity and labels using `kubectl describe node` and `kubectl get nodes --show-labels`. Based on the scheduler error, I fix the resource request, labels, tolerations, affinity rules, or node capacity."

The key command to remember is:

```bash
kubectl describe pod <pod-name>
```

The **Events** section is usually the starting point for a Pod scheduling issue.

---

## Q7. What are static and dynamic IPs for Pods?

In Kubernetes, the important point is that **Pod IPs are normally dynamic**. A Pod's IP can change when the Pod is recreated.

### Dynamic Pod IP

Suppose you deploy 3 Pods:

```text
app-1 → 10.244.1.5
app-2 → 10.244.1.6
app-3 → 10.244.1.7
```

If `app-2` is deleted and recreated:

```text
app-2 → 10.244.2.10
```

The IP can change. That's why applications should not directly depend on Pod IPs.

Instead, use a **Kubernetes Service**:

```text
Client
  ↓
Service
  ↓
Pod 1   Pod 2   Pod 3
```

The Service provides a stable endpoint while the Pod IPs can change.

### What about a "static Pod IP"?

In standard Kubernetes, you generally don't assign a permanent static IP directly to a normal Pod.

For example, this is **not** a normal Kubernetes pattern:

```yaml
spec:
  podIP: 10.244.1.10
```

Pod IP allocation is handled by the cluster's networking (the CNI plugin).

There are specialized networking configurations where a Pod can receive a predictable or fixed IP, but that's different from the normal Kubernetes model.

### A StatefulSet gives a stable identity

This is an important interview distinction.

A StatefulSet can give Pods stable names, for example:

```text
postgres-0
postgres-1
postgres-2
```

and, with a headless Service, stable DNS names:

```text
postgres-0.postgres
postgres-1.postgres
postgres-2.postgres
```

But a stable identity does **not** necessarily mean the Pod IP stays fixed.

### Static vs. dynamic

| | Dynamic Pod IP | Static / fixed IP |
| --- | --- | --- |
| Normal Kubernetes Pod | ✅ Yes | ❌ Normally no |
| IP can change after recreation | ✅ Yes | Depends on the networking setup |
| Should the application depend on the IP? | ❌ No | Usually avoid it |
| Recommended access | Kubernetes Service | Service / specialized networking |
| StatefulSet | IP can change | Stable DNS identity instead |

### Interview answer

> "Pod IPs in Kubernetes are normally dynamic. When a Pod is recreated, it can receive a different IP. Therefore, we don't use Pod IPs directly for application communication. We use a Kubernetes Service, which provides a stable endpoint and routes traffic to the current Pod IPs. StatefulSets provide stable Pod names and DNS identities, but that doesn't mean the Pod IP itself is permanently static."
