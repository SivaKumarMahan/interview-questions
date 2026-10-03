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

---

## Q8. How is your application accessed using a NodePort Service?

With a **NodePort** Service, an application is accessed using the **Node IP + NodePort**.

### Flow

```text
User / Client
     |
     | http://<Node-IP>:30080
     ↓
Kubernetes Node
     |
     | NodePort 30080
     ↓
NodePort Service
     |
     ↓
Pod
     |
     ↓
Application container :8080
```

### Example

Suppose your application is listening on port 8080 inside the Pod.

Service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080
```

Here:

- `targetPort: 8080` → application port inside the Pod
- `port: 80` → Service port
- `nodePort: 30080` → port exposed on every eligible node

You can access it using:

```text
http://<Node-IP>:30080
```

For example:

```text
http://10.10.1.20:30080
```

Kubernetes then forwards the request:

```text
10.10.1.20:30080
        ↓
NodePort Service :80
        ↓
Pod :8080
```

### How do you find the NodePort?

```bash
kubectl get svc my-app
```

Example:

```text
NAME     TYPE       CLUSTER-IP    EXTERNAL-IP   PORT(S)
my-app   NodePort   10.0.10.50    <none>        80:30080/TCP
```

Find the node IP:

```bash
kubectl get nodes -o wide
```

Then access:

```text
http://<NODE-IP>:30080
```

### Important point in AKS

If the AKS nodes have private IPs, you cannot normally access the NodePort directly from the public internet using those private IPs.

You would typically use:

```text
Internet
   ↓
Azure Load Balancer / Application Gateway
   ↓
AKS
   ↓
Service
   ↓
Pods
```

For production applications, NodePort is generally **not** the preferred external exposure mechanism. LoadBalancer or Ingress is more common.

### Interview answer

> "With a NodePort Service, Kubernetes exposes a port on the nodes, usually in the 30000-32767 range. The client accesses the application using the Node IP and NodePort, for example `http://10.10.1.20:30080`. Kubernetes forwards that request to the Service, and the Service routes it to one of the backend Pods. In AKS, for production external access, I would normally use a LoadBalancer or Ingress rather than exposing NodePort directly."

---

## Q9. What is the difference between CMD and ENTRYPOINT?

In a Dockerfile, both `CMD` and `ENTRYPOINT` define what runs when a container starts, but they behave differently.

### Simple difference

- **CMD** → provides the default command or default arguments. It can easily be overridden.
- **ENTRYPOINT** → defines the main executable. Arguments can be passed to it, but the executable normally remains fixed.

### Example with CMD

```dockerfile
FROM ubuntu:22.04

CMD ["echo", "Hello World"]
```

Run:

```bash
docker run myimage
```

Output:

```text
Hello World
```

But you can override it:

```bash
docker run myimage echo "Hi Siva"
```

Output:

```text
Hi Siva
```

The original `CMD` is completely replaced.

### Example with ENTRYPOINT

```dockerfile
FROM ubuntu:22.04

ENTRYPOINT ["echo"]
```

Run:

```bash
docker run myimage "Hello World"
```

Output:

```text
Hello World
```

Here:

```text
ENTRYPOINT = echo
Argument   = Hello World
```

The argument is **appended** to the `ENTRYPOINT`.

### Using both together

This is a very common pattern:

```dockerfile
FROM ubuntu:22.04

ENTRYPOINT ["echo"]
CMD ["Hello World"]
```

Run:

```bash
docker run myimage
```

Result:

```text
Hello World
```

Effectively:

```bash
echo "Hello World"
```

If you run:

```bash
docker run myimage "Hi Siva"
```

Result:

```text
Hi Siva
```

So:

```text
ENTRYPOINT = fixed executable
CMD        = default argument
```

### Comparison

| | CMD | ENTRYPOINT |
| --- | --- | --- |
| Purpose | Default command / arguments | Main executable |
| Easily overridden? | Yes | Not normally |
| Arguments appended? | No, if CMD is overridden | Yes |
| Common use | Default behavior | The container's main application |

### Interview answer

> "CMD and ENTRYPOINT both define the container startup behavior. CMD provides a default command or arguments and can be completely overridden when running the container. ENTRYPOINT defines the main executable, and runtime arguments are normally appended to it. We can also use them together, where ENTRYPOINT is the fixed executable and CMD provides its default arguments."

**One important interview point:** prefer the JSON (exec) form:

```dockerfile
ENTRYPOINT ["java", "-jar", "app.jar"]
```

rather than the shell form:

```dockerfile
ENTRYPOINT java -jar app.jar
```

The exec form handles signals and process management more cleanly, which matters for containers running in Kubernetes.

---

## Q10. If a Secret is changed while Pods are running, what is the effect?

It depends on **how the Secret is consumed by the Pod**. This is an important Kubernetes interview question.

### 1. Secret used as an environment variable

Example:

```yaml
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db-secret
      key: password
```

If you change the Secret:

```bash
kubectl edit secret db-secret
```

the environment variable inside an already-running container does **not** change.

The Pod must be restarted or recreated to pick up the new value:

```bash
kubectl rollout restart deployment my-app
```

Flow:

```text
Secret changed
     ↓
Existing Pod
     ↓
Environment variable keeps the OLD value
     ↓
Pod restart
     ↓
NEW value loaded
```

### 2. Secret mounted as a volume

Example:

```yaml
volumes:
- name: secret-volume
  secret:
    secretName: db-secret
```

Here, Kubernetes **can update the mounted Secret files inside the running Pod** after the Secret changes. There can be a short propagation delay.

```text
Secret changed
      ↓
Kubernetes updates the mounted volume
      ↓
File inside the Pod gets the new value
```

However, there is an important catch: **your application must actually re-read the file.**

If the application reads the secret only during startup and keeps it in memory, changing the mounted file won't change the application's behavior. You may still need to restart or reload the application.

### 3. Secret baked into the Docker image

If you put a secret directly into the image:

```dockerfile
ENV DB_PASSWORD=mysecret
```

changing a Kubernetes Secret has **no effect**. The secret is already part of the image and container configuration.

This is also a bad security practice.

### Interview answer

> "The effect depends on how the Secret is consumed. If the Secret is injected as an environment variable, changing the Kubernetes Secret does not update the environment variable in an existing Pod, so we need to restart the Pod to pick up the new value. If the Secret is mounted as a volume, Kubernetes can update the mounted files automatically after a short propagation delay, but the application must re-read the file or reload the configuration. If the application only reads the secret during startup, we still need a restart or reload."

### One more production point

If you're using **Azure Key Vault with the Secrets Store CSI Driver**, the behavior is slightly different, because the secret can be synced from Key Vault and rotated depending on the rotation configuration. But again, whether the application sees the new value depends on whether it reads the mounted file dynamically or only at startup.

---

## Q11. In Helm, if you want to deploy one specific version out of three, how will you deploy it?

If you have 3 versions of the same Helm chart or application and specifically want to deploy version 2, you need to distinguish between the **Helm chart version** and the **application (image) version**.

### 1. If you mean the Helm chart version

Suppose your Helm repository has:

```text
myapp
├── 1.0.0
├── 2.0.0
└── 3.0.0
```

First check the available versions:

```bash
helm search repo myapp --versions
```

Then explicitly install version 2.0.0:

```bash
helm upgrade --install myapp myrepo/myapp \
  --version 2.0.0
```

`--version` tells Helm which chart version to use.

### 2. If you mean the application / image version

Suppose the same chart can deploy:

```text
myapp:1.0
myapp:2.0
myapp:3.0
```

You can specify the image tag:

```bash
helm upgrade --install myapp ./mychart \
  --set image.tag=2.0
```

Or, preferably, use a values file:

```yaml
image:
  repository: myacr.azurecr.io/myapp
  tag: "2.0"
```

Then:

```bash
helm upgrade --install myapp ./mychart \
  -f values-prod.yaml
```

### 3. If the versions already exist as Helm releases

If you mean deploying or rolling back to an earlier release revision, check:

```bash
helm history myapp
```

Example:

```text
REVISION   STATUS
1          superseded
2          superseded
3          deployed
```

To go back to revision 1:

```bash
helm rollback myapp 1
```

Then verify:

```bash
helm status myapp
```

### Interview answer

> "First I clarify whether the version refers to the Helm chart version or the application image version. If I need a specific Helm chart version, I use `helm upgrade --install` with `--version`, for example `--version 2.0.0`. If I need a specific application version, I pass the required image tag using `--set image.tag=2.0`. If the required version was already deployed previously and I need to revert to that release, I check `helm history` and use `helm rollback` with the required revision."

---

## Q12. What will happen if kubelet is not running?

If kubelet is not running on a Kubernetes worker node, that node **cannot properly participate in Kubernetes workload management**.

### What does kubelet do?

kubelet is the agent running on every worker node. It:

- Communicates with the Kubernetes API server.
- Watches for Pods assigned to its node.
- Creates and manages containers through the container runtime.
- Handles liveness, readiness and startup probes.
- Reports node and Pod status back to the API server.

### If kubelet stops

Suppose:

```text
              API Server
                  |
          ----------------
          |              |
       Node-1          Node-2
     kubelet ✅      kubelet ❌
```

The API server will eventually detect that Node-2 is not responding.

Check:

```bash
kubectl get nodes
```

You may see:

```text
NAME      STATUS
node-1    Ready
node-2    NotReady
```

### What happens to existing Pods?

This is an important distinction.

The container runtime **may continue running existing containers** even if kubelet stops. But kubelet is no longer managing them or reporting their state to the API server.

So you can have:

```text
kubelet ❌
    |
    └── Existing containers may continue running
```

but Kubernetes loses reliable management and health reporting for that node.

After the node is considered unavailable, Kubernetes may eventually evict and reschedule workloads, depending on the Pod and controller configuration.

### What happens to new Pods?

The scheduler may initially see the node as available, but once the node becomes `NotReady` and is no longer considered suitable, new Pods won't normally be scheduled there.

Existing workloads managed by Deployments or ReplicaSets can be recreated on healthy nodes after eviction.

### Troubleshooting

On the affected node:

```bash
systemctl status kubelet
```

Check the logs:

```bash
journalctl -u kubelet -f
```

Restart it:

```bash
systemctl restart kubelet
```

Then:

```bash
kubectl get nodes
```

### Interview answer

> "Kubelet is the agent responsible for managing Pods on a Kubernetes node and communicating node and Pod status to the API server. If kubelet stops, existing containers may continue running through the container runtime, but Kubernetes loses management and status reporting for that node. The node will eventually become NotReady, new workloads won't be scheduled there, and controllers may reschedule affected Pods to healthy nodes. I would troubleshoot using `systemctl status kubelet` and `journalctl -u kubelet`."

---

## Q13. Pods are in NotReady state and nodes are in NotReady state. What is the reason?

There are two different problems here: **Pod NotReady** and **Node NotReady**. The troubleshooting approach is slightly different.

### 1. Pod is NotReady

First check:

```bash
kubectl get pods
kubectl describe pod <pod-name>
```

Look at the **Conditions** and **Events**.

Common reasons:

#### Readiness probe failure

```text
Readiness probe failed: HTTP probe failed with statuscode: 503
```

The application may be running, but it isn't ready to receive traffic.

Check:

```bash
kubectl logs <pod-name>
kubectl describe pod <pod-name>
```

#### Application or container problem

Examples:

```text
CrashLoopBackOff
OOMKilled
ImagePullBackOff
```

Check:

```bash
kubectl logs <pod-name>
kubectl logs <pod-name> --previous
```

#### Dependency problem

For example, the application is running but cannot connect to:

- PostgreSQL
- Redis
- another microservice
- an external API

The readiness probe may therefore fail.

#### Wrong port or probe configuration

For example, the application listens on `8080` but the readiness probe checks `8081`. The Pod stays NotReady.

### 2. Node is NotReady

Check:

```bash
kubectl get nodes
kubectl describe node <node-name>
```

Look at the **Conditions** section.

Common reasons:

#### Kubelet is down

```bash
systemctl status kubelet
```

Check the logs:

```bash
journalctl -u kubelet
```

#### Node has CPU, memory or disk pressure

Check:

```bash
kubectl describe node <node-name>
```

You may see:

```text
MemoryPressure=True
DiskPressure=True
PIDPressure=True
```

For example, if the node's disk is full, kubelet may report `DiskPressure=True`.

#### Container runtime problem

For example, containerd is down:

```bash
systemctl status containerd
```

If the container runtime isn't working, kubelet cannot properly manage containers.

#### Network problem

The node may not be able to communicate with the Kubernetes API server. Check the kubelet logs and network connectivity.

#### CNI / network plugin problem

If Azure CNI or another Kubernetes networking component is broken, Pods may have networking problems, and the node can become unhealthy depending on the failure.

#### Certificate or authentication issue

Kubelet certificates or credentials can expire or become invalid, preventing proper communication with the API server.

### Very important interview distinction

Don't troubleshoot both in exactly the same way.

| | Pod NotReady | Node NotReady |
| --- | --- | --- |
| Start with | `kubectl describe pod <pod>`, `kubectl logs <pod>` | `kubectl describe node <node>`, then on the node: `systemctl status kubelet`, `systemctl status containerd`, `journalctl -u kubelet` |
| Focus on | Readiness probe, application, dependencies, container status, configuration | Kubelet, container runtime, CPU / memory / disk pressure, network, certificates, node health |

### Interview answer

> "If a Pod is NotReady, I first check `kubectl describe pod` and the Pod logs. I specifically look for readiness probe failures, application issues, dependency connectivity, incorrect ports, or resource problems. If a Node is NotReady, I check `kubectl describe node` and look at the node conditions. Then I verify kubelet and container runtime status, CPU, memory and disk pressure, network connectivity to the API server, and kubelet logs. I identify the exact condition or event first rather than restarting components blindly."

---

## Q14. If you restore a backup in Jenkins, will it work?

**Yes**, a Jenkins backup can be restored and Jenkins can work, but it depends on **what was backed up** and whether the restore is **compatible** with the Jenkins environment.

### What needs to be backed up?

The most important Jenkins data is the `JENKINS_HOME` directory. It contains things like:

```text
JENKINS_HOME/
├── jobs/
├── credentials.xml
├── config.xml
├── users/
├── nodes/
├── plugins/
├── secrets/
├── fingerprints/
└── pipelines / jobs configuration
```

A proper backup should protect the Jenkins configuration, jobs, credentials, secrets, and other required metadata.

### Restore process

Suppose the old Jenkins server failed:

```text
Old Jenkins
     ↓
Backup JENKINS_HOME
     ↓
New Jenkins server
     ↓
Install a compatible Jenkins version
     ↓
Restore JENKINS_HOME
     ↓
Start Jenkins
```

For example:

```bash
systemctl stop jenkins
```

Restore the backup into the correct Jenkins home:

```bash
cp -r /backup/jenkins_home/* /var/lib/jenkins/
```

Fix the ownership:

```bash
chown -R jenkins:jenkins /var/lib/jenkins
```

Then:

```bash
systemctl start jenkins
```

Verify:

```bash
systemctl status jenkins
```

### Important issue: plugins

This is where restores can fail.

Suppose the backup was created on Jenkins version A with plugin versions X, and you restore it onto a completely different Jenkins and plugin environment. You can run into:

- Plugin incompatibility
- Missing plugins
- Failed jobs
- Configuration errors

So ideally, restore onto the **same or a compatible Jenkins version and plugin versions**, then upgrade in a controlled manner.

### Credentials are especially important

Jenkins credentials are **encrypted**. Restoring only `credentials.xml` is not enough if the matching Jenkins encryption keys are missing.

That's why a proper Jenkins backup must include the relevant files under:

```text
JENKINS_HOME/secrets/
```

Without the required encryption keys, previously stored credentials may not be usable.

### Interview answer

> "Yes, Jenkins can be restored from backup, provided the backup is complete and the restored environment is compatible. I would normally back up the entire JENKINS_HOME, including job configurations, credentials, plugins, users, secrets, and system configuration. During DR, I install a compatible Jenkins version, restore JENKINS_HOME, maintain the correct ownership and permissions, verify plugins and credentials, and then start Jenkins. I would also test the restored pipelines before considering the recovery successful."

### Production best practice

Don't rely only on a Jenkins server snapshot. Keep regular, tested backups of `JENKINS_HOME` and periodically perform a restore test.

**A backup that has never been restored is not a proven backup.**

---

## Q15. How do you store secrets in Jenkins?

In Jenkins, I would **not** store secrets directly in the Jenkinsfile. I use **Jenkins Credentials** or an external secret manager such as **Azure Key Vault**.

### 1. Jenkins Credentials Store

Go to:

```text
Jenkins
 → Manage Jenkins
 → Credentials
 → Global
 → Add Credentials
```

You can store:

- Username / password
- Secret text
- SSH private key
- Certificate
- Secret files
- API tokens

For example, create a credential with the ID:

```text
azure-sp-credentials
```

Then use it in the pipeline:

```groovy
pipeline {
    agent any

    stages {
        stage('Deploy') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'azure-sp-credentials',
                        usernameVariable: 'AZURE_CLIENT_ID',
                        passwordVariable: 'AZURE_CLIENT_SECRET'
                    )
                ]) {
                    sh '''
                        az login \
                          --service-principal \
                          -u "$AZURE_CLIENT_ID" \
                          -p "$AZURE_CLIENT_SECRET" \
                          --tenant "$AZURE_TENANT_ID"
                    '''
                }
            }
        }
    }
}
```

The actual secret isn't written in the Jenkinsfile.

### 2. Mask secrets in console output

Jenkins credentials binding masks recognized secret values in build logs.

But don't do this:

```bash
echo "$AZURE_CLIENT_SECRET"
```

Even though Jenkins may mask it, never intentionally print secrets.

Also avoid:

```bash
set -x
```

when running commands that contain sensitive values.

### 3. External secret manager

In an Azure environment, I would prefer **Azure Key Vault** for important production secrets.

Example architecture:

```text
Jenkins
   |
   | Managed Identity / Workload Identity
   ↓
Azure Key Vault
   |
   ↓
Secrets
   |
   ↓
Application / Deployment
```

This keeps sensitive values outside Jenkins and provides centralized secret management, access control, auditing and rotation.

### 4. What I would avoid

Don't store secrets like this:

```groovy
environment {
    DB_PASSWORD = 'MyPassword123'
}
```

Don't commit this to Git:

```yaml
password: MyPassword123
```

Don't put credentials in Dockerfiles or container images.

### Interview answer

> "I store secrets using Jenkins Credentials rather than hardcoding them in the Jenkinsfile or Git repository. I create the credential in the Jenkins Credentials Store and reference it by credentialsId using withCredentials or the credentials binding mechanism. Jenkins masks the values in console output, and I make sure not to print secrets. For production environments, especially in Azure, I prefer using Azure Key Vault as the centralized secret store and allow Jenkins to access it through an appropriate identity."
