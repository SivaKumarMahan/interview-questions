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
