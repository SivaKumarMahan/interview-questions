# Kubernetes Detailed Interview Notes

These notes provide extended explanations, commands, YAML examples, investigation flows, corrective actions, and preventive measures for Kubernetes interviews. Numbered interview questions and scenario answers are maintained in `questions.txt`; concise revision material is maintained in `summary.md`.

---

## Cluster Operations, Workloads, Monitoring, Upgrades, and Troubleshooting

### Q: There are 1 master and 3 worker nodes. If the master fails, what happens? Will pods keep running or will they crash?

**What happens if the master fails:**

- The existing pods running on worker nodes will **continue to run normally**, because worker nodes and their `kubelet` processes keep the containers alive.
- However, **no new pods can be scheduled** or changes applied, because:
  - The scheduler is down.
  - The API server is unreachable.
  - The control plane cannot make decisions.

So your cluster is temporarily **frozen** — workloads keep running, but no management operations work (no deployments, scaling, or restarts if a node crashes).

**Preventive measure:** Use a **High Availability (HA) control plane** — multiple master nodes spread across zones (e.g., 3 masters). That way, even if one master fails, the cluster continues to function fully.

---

### Q: One of your worker nodes is not joining the cluster. How would you debug the issue?

If a worker node isn't joining the cluster, I'd first check the `kubeadm join` token validity, network connectivity to the API server, and kubelet logs for authentication or connection errors. Then I'd verify kubelet and container runtime status, DNS/hostname resolution, and finally reset and rejoin the node if necessary.

**1. Check the `kubeadm join` command output:**

When you run `kubeadm join`, it provides output that can indicate issues (e.g., token expired, unable to connect to API server).

**2. Verify network connectivity:**

```bash
ping <control-plane-ip>
telnet <control-plane-ip> 6443
```

- From the worker node, try pinging the master node's IP address.
- Use `curl` or `wget` to test connectivity to the API server endpoint (`https://<master-ip>:6443`).

**3. Check kubelet logs:**

On the worker node, check kubelet logs for errors related to authentication or connection issues:

```bash
journalctl -u kubelet -xe
```

**4. Verify kubelet and container runtime status:**

```bash
sudo systemctl status kubelet
sudo systemctl status docker      # or containerd
```

**5. Check DNS and hostname resolution:**

- Ensure the worker node can resolve the master node's hostname if using hostnames instead of IPs.
- Try `nslookup` or `dig` commands to verify DNS resolution.

**6. Reset and rejoin the node:**

```bash
sudo kubeadm token list                        # Check if the token is still valid
sudo kubeadm token create --print-join-command  # Create a new token on the master if expired
sudo kubeadm reset                              # On the worker node, reset the kubeadm state
```

Then rejoin the cluster using the `kubeadm join` command provided by the master node.

---

### Q: What is a DaemonSet in Kubernetes and when would you use it?

A **DaemonSet** in Kubernetes ensures that a copy of a specific pod runs on all (or selected) nodes in the cluster. It's used for deploying system-level services that need to run on every node, such as log collectors, monitoring agents, or network plugins.

**Use cases for DaemonSets:**

- **Log Collection:** Deploying log collection agents (e.g., Fluentd, Logstash) on all nodes to gather and forward logs.
- **Monitoring:** Running monitoring agents (e.g., Prometheus Node Exporter, Datadog Agent) on each node to collect metrics.
- **Networking:** Deploying network plugins (e.g., Calico, Weave) that require a pod on every node for network management.
- **Storage:** Running storage daemons (e.g., GlusterFS, Ceph) that need to be present on all nodes for distributed storage.

**Example DaemonSet YAML:**

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: log-collector
spec:
  selector:
    matchLabels:
      app: log-collector
  template:
    metadata:
      labels:
        app: log-collector
    spec:
      containers:
      - name: fluentd
        image: fluent/fluentd:latest
        resources:
          limits:
            memory: "200Mi"
            cpu: "100m"
```

In this example, a DaemonSet named `log-collector` deploys a Fluentd container on every node in the cluster to collect logs.

---

### Q: How does Kubernetes perform rolling updates using YAML to achieve zero downtime deployments?

Kubernetes performs rolling updates using the **Deployment** resource, which allows you to update your application without downtime by gradually replacing old pods with new ones. You can specify the update strategy and parameters in the Deployment YAML file.

**Example Deployment YAML for a rolling update:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0   # Number of pods that can be unavailable during the update
      maxSurge: 1         # Number of extra pods that can be created temporarily during the update
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app-container
        image: my-app:1.0.0
```

To perform a rolling update, update the image version in the Deployment YAML (e.g., change `my-app:1.0.0` to `my-app:1.1.0`) and apply the changes using `kubectl apply -f deployment.yaml`.

Kubernetes will then:

1. Create new pods with the updated image.
2. Gradually terminate old pods while ensuring that the specified number of replicas is maintained.
3. Use `maxUnavailable` and `maxSurge` settings to control the pace of the update, ensuring zero downtime.

You can monitor the update process using:

```bash
kubectl rollout status deployment my-app
kubectl get pods -o wide
```

**Additional features for zero downtime:**

- Use **readiness probes** to ensure traffic isn't sent to unready Pods.
- The Kubernetes **Service** handles load balancing across old and new Pods during rollout.
- Supports **canary** or **blue-green** strategies if you want finer control.
- Supports **pause/resume** rollout (`kubectl rollout pause/resume`) for manual approval.

**If something goes wrong:**

```bash
kubectl rollout undo deployment my-app
```

---

### Q: How do you implement centralized monitoring for multiple Kubernetes clusters in Azure? What tools would you use, and why?

A centralized place to monitor:

- Cluster health
- Node and Pod metrics
- Application logs
- Alerts and dashboards

| Layer                           | Tool                                                   | Purpose                                                         | Centralized Integration                              |
| ------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------- | ---------------------------------------------------- |
| **Metrics & Logs Collection**   | **Azure Monitor / Container Insights (Log Analytics)** | Collects CPU, memory, pod, and container logs from all clusters | Centralized Log Analytics workspace                  |
| **Dashboards & Visualization**  | **Grafana**                                            | Custom dashboards using data from Azure Monitor or Prometheus   | Single Grafana instance connects to all data sources |
| **Prometheus (Optional)**       | **Prometheus + Azure Managed Prometheus**              | Cluster-level scraping of metrics                               | Can be federated or exported to Azure Monitor        |
| **Log Storage**                 | **Log Analytics Workspace**                            | Stores logs from all clusters                                   | Single shared workspace                              |
| **Alerting**                    | **Azure Monitor Alerts** + **Prometheus Alertmanager** | Alerts based on thresholds and log queries                      | Centralized alert routing                            |
| **Event Correlation / Tracing** | **Azure Application Insights**                         | Distributed tracing, dependency maps, and custom telemetry      | Application-level observability                      |
| **Notifications**               | **Azure Action Groups / Slack / Email**                | Sends alerts to teams                                           | Unified notification routing                         |

**Tools explanation:**

- **Azure Monitor / Container Insights:** Native Azure tool for monitoring AKS clusters, providing deep integration with Azure services.
- **Grafana:** Popular open-source dashboarding tool that can visualize data from multiple sources, including Azure Monitor and Prometheus.
- **Prometheus:** Widely used for Kubernetes monitoring; can be integrated with Azure Managed Prometheus for scalability.
- **Log Analytics Workspace:** Centralized storage for logs, making it easy to query and analyze data from multiple clusters.
- **Azure Application Insights:** Provides application-level monitoring and tracing, useful for microservices architectures.

This setup allows for a comprehensive, centralized monitoring solution across multiple Kubernetes clusters in Azure, leveraging both native Azure tools and popular open-source solutions.

**Steps to implement:**

**1. Create a central Log Analytics workspace:**

```bash
az monitor log-analytics workspace create \
  -g monitoring-rg \
  -n central-law
```

**2. Enable Container Insights for each AKS cluster:**

```bash
az aks enable-addons \
  --resource-group <cluster-rg> \
  --name <aks-cluster-name> \
  --addons monitoring \
  --workspace-resource-id /subscriptions/<subscription-id>/resourceGroups/monitoring-rg/providers/Microsoft.OperationalInsights/workspaces/central-law
```

**3. Set up Grafana:**

- Deploy Grafana in a separate AKS cluster or use Azure Managed Grafana.
- **Configure data sources:** Add Azure Monitor and Prometheus as data sources in Grafana.
- **Create dashboards:** Build dashboards to visualize metrics and logs from all clusters.

**4. Set up alerting:**

Configure alerts in Azure Monitor and Prometheus Alertmanager to notify teams via preferred channels.

```bash
az monitor metrics alert create \
  -n "HighCPUAlert" \
  -g monitoring-rg \
  --scopes "/subscriptions/<subID>/resourceGroups/monitoring-rg/providers/Microsoft.OperationalInsights/workspaces/central-law" \
  --condition "avg(kubernetes.container.cpuUsageNanoCores) > 800000000" \
  --description "CPU usage too high"
```

**5. (Optional) Integrate Application Insights:**

Instrument applications running in the clusters with Application Insights SDKs for deeper observability.

This approach ensures you have a robust, scalable, and centralized monitoring solution for multiple Kubernetes clusters in Azure.

---

### Q: How have you upgraded a Kubernetes cluster in production in Azure? What steps did you take to ensure zero downtime?

In production, I upgrade AKS clusters with zero downtime by upgrading the control plane first, followed by node pools sequentially using Azure CLI. Each node is drained gracefully, with workloads protected by readiness probes, multiple replicas, and PodDisruptionBudgets. I monitor during the process via Azure Monitor and Grafana, and test in staging beforehand. This rolling approach ensures continuous availability — users never see downtime.

**Steps for a zero-downtime AKS upgrade:**

**1. Pre-upgrade preparation:**

- Review the AKS release notes for breaking changes.
- Test the upgrade process in a staging environment.
- Ensure all workloads have multiple replicas and readiness/liveness probes configured.
- Define **PodDisruptionBudgets (PDBs)** to limit voluntary disruptions.

**2. Upgrade the control plane:**

```bash
az aks upgrade --resource-group <resource-group> --name <aks-cluster-name> --kubernetes-version <new-version> --control-plane-only
```

**3. Upgrade node pools sequentially:**

- The node is cordoned (no new pods scheduled).
- Pods are evicted and rescheduled on healthy nodes.
- A new node with the upgraded image joins the cluster.
- The old node is deleted once draining completes.

```bash
# List node pools
az aks nodepool list --resource-group <resource-group> --cluster-name <aks-cluster-name>

# Upgrade each node pool one at a time
az aks nodepool upgrade --resource-group <resource-group> --cluster-name <aks-cluster-name> --name <nodepool-name> --kubernetes-version <new-version>
```

**4. Monitor the upgrade:**

- Use Azure Monitor and Grafana dashboards to track cluster health, node status, and application performance.
- Check for any Pod evictions or disruptions.

**5. Post-upgrade validation:**

- Verify that all nodes are running the new Kubernetes version.
- Ensure all applications are functioning correctly.
- Review logs for any errors or warnings.

**6. Rollback plan:**

- Have a rollback plan in case of issues, such as restoring from backups or redeploying previous versions of applications.

By following these steps, I ensure a smooth AKS upgrade with zero downtime for end-users.

---

### Q: How do you troubleshoot a pod that is stuck in the 'Pending' state in Kubernetes?

To troubleshoot a pod stuck in the 'Pending' state, I would follow these steps:

**1. Check pod description:**

```bash
kubectl describe pod <pod-name>
```

Look for events at the bottom of the output for clues (e.g., insufficient resources, scheduling issues).

**2. Check node resources:**

```bash
kubectl get nodes -o wide
kubectl describe node <node-name>
```

Ensure nodes have enough CPU, memory, and disk space to schedule the pod.

**3. Verify resource requests and limits:**

Check if the pod's resource requests exceed available resources on any node.

**4. Check taints and tolerations:**

```bash
kubectl describe node <node-name>
```

- Look for any taints on nodes that might prevent the pod from being scheduled.
- Check if the pod has the necessary tolerations to be scheduled on those nodes.

**5. Check node selectors and affinity rules:**

Ensure the pod's `nodeSelector` or affinity rules match available nodes.

**6. Review Cluster Autoscaler (if applicable):**

If using a cluster autoscaler, check if it's functioning correctly and can scale up nodes if needed.

**7. Check for pending PVCs:**

If the pod uses Persistent Volume Claims (PVCs), ensure they are bound to available Persistent Volumes (PVs).

```bash
kubectl get pvc
```

**8. Review scheduler logs:**

If you have access to the scheduler logs, check for any errors or issues related to pod scheduling.

**9. Look for quotas:**

Check if there are any resource quotas in the namespace that might be preventing the pod from being scheduled.

```bash
kubectl get resourcequota -n <namespace>
```

By systematically going through these steps, I can identify and resolve the issue causing the pod to remain in the 'Pending' state.

---

## Kubernetes API, Authentication, Secrets, Common Failures, Backup, and Scaling

### Q: In K8s, as etcd is a key-value store DB, can we write something manually to it?

Yes, you can write data manually to etcd in Kubernetes, but it is **generally not recommended**.

- etcd is the backing store for all cluster data in Kubernetes, and manually modifying its contents can lead to inconsistencies and potential cluster instability.
- If you do need to interact with etcd directly, you can use the `etcdctl` command-line tool.
- It is crucial to ensure that you are working with the correct version of `etcdctl` that matches your etcd server version.
- Before making any changes, it is highly advisable to **back up your etcd data**.

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

---

### Q: What is the command to access a pod, and how can you define or create a Kubernetes object?

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

---

### Q: How do you handle authentication for AKS clusters and store secrets securely in Kubernetes?

**Authentication for AKS clusters:**

1. **Azure Active Directory (AAD) Integration:** AKS can be integrated with Azure AD to manage user access to the cluster. This allows you to use Azure AD identities for authentication and role-based access control (RBAC) within the cluster.
2. **kubeconfig file:** When you create an AKS cluster, a kubeconfig file is generated that contains the necessary credentials to access the cluster. Use the `az aks get-credentials` command to download and configure your kubeconfig file.
3. **Service Principals and Managed Identities:** AKS can use Azure Service Principals or Managed Identities for authenticating applications running in the cluster to access Azure resources securely.

**Storing secrets securely in Kubernetes:**

1. **Kubernetes Secrets:** Kubernetes provides a built-in resource called Secrets to store sensitive information such as passwords, OAuth tokens, and SSH keys. Secrets are base64-encoded and can be created using YAML manifests or the `kubectl create secret` command.
2. **Encryption at Rest:** You can enable encryption at rest for Secrets in Kubernetes by configuring the encryption providers in the API server.
3. **External Secret Management Tools:** For enhanced security, you can use external secret management tools like HashiCorp Vault, Azure Key Vault, or AWS Secrets Manager. These tools can be integrated with Kubernetes to fetch secrets dynamically at runtime.
4. **RBAC Policies:** Implement Role-Based Access Control (RBAC) policies to restrict access to Secrets based on user roles and permissions.
5. **Avoid Hardcoding Secrets:** Never hardcode sensitive information in your application code or configuration files. Always use Secrets or external secret management solutions.

By following these practices, you can ensure secure authentication for your AKS clusters and safely manage sensitive information within your Kubernetes environment.

---

### Q: What are common Kubernetes errors you have faced (like CrashLoopBackOff, ImagePullError) and how did you resolve them?

**1. CrashLoopBackOff**

- **Cause:** Occurs when a container repeatedly crashes after starting.
- **Resolution:** Check the container logs using `kubectl logs <pod-name>` to identify the root cause. Common issues include application errors, misconfigurations, or missing dependencies. Fix the underlying issue and redeploy the pod.

**2. ImagePullBackOff**

- **Cause:** Occurs when Kubernetes cannot pull the container image from the specified registry.
- **Resolution:** Verify that the image name and tag are correct. Ensure the container registry is accessible and that any required authentication (e.g., image pull secrets) is properly configured. You can also check the events using `kubectl describe pod <pod-name>` for more details.

**3. ErrImageNeverPull**

- **Cause:** Occurs when the `imagePullPolicy` is set to `"Never"` and the image is not present on the node.
- **Resolution:** Change the `imagePullPolicy` to `"IfNotPresent"` or `"Always"` in the pod specification, or ensure the image is pre-pulled on the nodes.

**4. NodeNotReady**

- **Cause:** Indicates that a node is not in a ready state to schedule pods.
- **Resolution:** Check the node status using `kubectl get nodes` and investigate the node logs for issues such as resource exhaustion, network problems, or kubelet failures. Resolve the underlying issue and ensure the node is healthy.

**5. PersistentVolumeClaim (PVC) Pending**

- **Cause:** Occurs when a PVC cannot be bound to a PersistentVolume (PV).
- **Resolution:** Ensure that there are available PVs that match the storage class, access modes, and size requested by the PVC. You can create additional PVs or adjust the PVC specifications as needed.

**6. Unauthorized (401) Errors**

- **Cause:** Occurs when there are authentication or authorization issues.
- **Resolution:** Verify that the kubeconfig file is correctly configured and that the user has the necessary RBAC permissions to perform the requested actions.

**7. DNS Resolution Issues**

- **Cause:** Pods may fail to resolve DNS names, leading to connectivity issues.
- **Resolution:** Check the CoreDNS pods and their logs for errors. Ensure that the DNS configuration is correct and that network policies allow DNS traffic.

By systematically diagnosing and addressing these common errors, you can maintain a healthy and stable cluster environment.

---

### Q: What is your strategy for backup and restore in a cluster?

A comprehensive backup and restore strategy for a Kubernetes cluster involves several key components to ensure data integrity, availability, and quick recovery in case of failures. Here's a general approach:

1. **Identify critical data:** Determine which data needs to be backed up, including etcd data, Persistent Volumes, configuration files, and application state.
2. **Backup etcd:**
   - Use `etcdctl` to create regular backups of the etcd database, which stores the cluster state.
   - Schedule automated etcd backups using cron jobs or backup tools.
3. **Backup Persistent Volumes:**
   - Use volume snapshot features provided by your cloud provider or storage solution to create snapshots of Persistent Volumes.
   - Consider using tools like Velero, Kasten, or Stash for managing backups of Persistent Volumes and application data.
4. **Backup configuration and manifests:**
   - Store Kubernetes manifests (YAML files) for deployments, services, and other resources in a version-controlled repository (e.g., Git).
   - Regularly export the current state of the cluster using `kubectl get all --all-namespaces -o yaml` and back it up.
5. **Automate backups:**
   - Implement automated backup processes using scripts or backup tools to ensure regular and consistent backups.
   - Schedule backups during off-peak hours to minimize impact on cluster performance.
6. **Test restore procedures:**
   - Regularly test the restore process to ensure that backups can be successfully restored.
   - Document the restore procedures and ensure that team members are familiar with them.
7. **Monitor backup health:**
   - Implement monitoring and alerting for backup jobs to ensure they complete successfully.
   - Use logging to track backup activities and identify any issues promptly.
8. **Secure backups:**
   - Store backups in secure locations, such as encrypted storage or offsite locations.
   - Implement access controls to restrict who can access backup data.
9. **Disaster recovery plan:**
   - Develop a disaster recovery plan that outlines the steps to recover the cluster in case of catastrophic failures.
   - Include **RTO** (Recovery Time Objective) and **RPO** (Recovery Point Objective) targets in the plan.

By following this strategy, you can ensure that your Kubernetes cluster is well-protected against data loss and can be quickly restored in the event of a failure.

---

### Q: How do you use Velero for backup and restore in Azure Kubernetes Service?

Velero is an open-source tool that provides backup, restore, and disaster recovery capabilities for Kubernetes clusters.

**1. Install Velero:**

- First, install the Velero CLI on your local machine. You can download it from the official Velero GitHub releases page.
- Next, install Velero in your AKS cluster:

```bash
velero install \
  --provider azure \
  --bucket <your-velero-bucket> \
  --secret-file <path-to-your-azure-credentials-file> \
  --backup-location-config resourceGroup=<your-resource-group>,storageAccount=<your-storage-account>
```

Replace `<your-velero-bucket>`, `<path-to-your-azure-credentials-file>`, `<your-resource-group>`, and `<your-storage-account>` with your actual values.

**2. Create backups:**

```bash
velero backup create <backup-name> --include-namespaces <namespace1>,<namespace2>
```

Replace `<backup-name>` with a name for your backup and `<namespace1>,<namespace2>` with the namespaces you want to include.

**3. Monitor backup status:**

```bash
velero backup get
```

**4. Restore from backups:**

```bash
velero restore create --from-backup <backup-name>
```

Replace `<backup-name>` with the name of the backup you want to restore from.

**5. Monitor restore status:**

```bash
velero restore get
```

**6. Schedule regular backups:**

```bash
velero schedule create <schedule-name> --schedule "0 2 * * *" --include-namespaces <namespace1>,<namespace2>
```

Replace `<schedule-name>` with a name for your schedule and adjust the cron expression as needed.

**7. Clean up old backups:**

```bash
velero backup delete <backup-name>
```

Replace `<backup-name>` with the name of the backup you want to delete.

By following these steps, you can effectively use Velero to manage backups and restores in your Azure Kubernetes Service (AKS) cluster.

---

### Q: How do you implement autoscaling when traffic fluctuates heavily in Kubernetes?

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

---

### Q: How do you optimize resource requests and limits for containers in a production cluster?

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

---

## Pod and Container Security Contexts

### Q: Kubernetes security contexts — configuring permissions and access controls?

Kubernetes **Security Contexts** allow you to define security settings for Pods and Containers. They help configure permissions and access controls to enhance the security of your applications running in a Kubernetes cluster. Here are some key aspects:

**1. User and Group IDs:**

Specify the user ID (UID) and group ID (GID) that a container should run as using the `runAsUser` and `runAsGroup` fields.

```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 3000
```

**2. Privileged containers:**

Set the `privileged` field to `true` to allow a container to run with elevated privileges.

```yaml
securityContext:
  privileged: true
```

**3. Read-only root filesystem:**

Enforce a read-only root filesystem for a container by setting the `readOnlyRootFilesystem` field to `true`.

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

**4. Capabilities:**

Add or drop Linux capabilities for a container using the `capabilities` field.

```yaml
securityContext:
  capabilities:
    add: ["NET_ADMIN"]
    drop: ["MKNOD"]
```

**5. Seccomp profiles:**

Specify a seccomp profile to restrict system calls that a container can make.

```yaml
securityContext:
  seccompProfile:
    type: Localhost
    localhostProfile: "profiles/seccomp.json"
```

**6. SELinux options:**

Set SELinux options for a container using the `seLinuxOptions` field.

```yaml
securityContext:
  seLinuxOptions:
    level: "s0:c123,c456"
```

**7. Pod-level security context:**

Define a security context at the Pod level that applies to all containers within the Pod.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  securityContext:
    runAsUser: 1000
    fsGroup: 2000
  containers:
  - name: mycontainer
    image: myimage
```

By configuring security contexts, you can enforce security policies and ensure that your applications run with the appropriate permissions and access controls in a Kubernetes environment.

---

## Scheduling, Networking, Security, HA, and Troubleshooting Scenarios

### Q: Suppose I want a pod to be scheduled on a specific node only. How can I achieve this?

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

---

### Q: How can you restrict which pod can access other pods in Kubernetes?

Use Network Policies to control traffic flow between pods:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: allowed-app
```

Network policies work at L3/L4 and require a CNI that supports them (Calico, Cilium, etc.).

---

### Q: I am getting a 503 error when hitting a load balancer URL that routes traffic to applications deployed in a Kubernetes cluster. How will you troubleshoot this?

Follow this systematic approach:

- **Check service endpoints:** `kubectl get endpoints <service-name>`.
- **Verify pod health:** `kubectl get pods` — check if pods are ready.
- **Check service configuration:** Ensure correct port mapping and selectors.
- **Test internal connectivity:** `kubectl exec` into a pod and test the service.
- **Check ingress/load balancer logs:** Look for backend connection errors.
- **Verify health checks:** Ensure readiness/liveness probes are configured properly.
- **Check resource limits:** Pods might be throttled due to resource constraints.

---

### Q: I am getting a CrashLoopBackOff error for one of the pods in a namespace. What should be the reason?

**Common causes:**

- Application exits immediately after startup.
- Missing environment variables or config.
- Resource limits too restrictive.
- Failed liveness probe.
- Image issues or wrong command/args.

**Troubleshooting steps:**

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name> --previous
kubectl get events --sort-by='.lastTimestamp'
```

Check exit codes, resource requests/limits, and application logs.

---

### Q: A pod is in Pending state after the deployment is done. What can be the reason behind this?

Check these common issues:

- **Insufficient resources:** No node has enough CPU/memory.
- **Node selector/affinity:** No node matches the constraints.
- **PVC issues:** PersistentVolume not available or bound.
- **Image pull issues:** `imagePullSecrets` missing or wrong image.
- **Taints and tolerations:** Pod can't tolerate node taints.
- **Scheduler issues:** kube-scheduler not running properly.

Use `kubectl describe pod` and check the Events section for specific reasons.

---

### Q: How can you ensure high availability for your application deployed in a Kubernetes cluster?

Implement these strategies:

- **Multiple replicas:** Use a Deployment with `replicas > 1`.
- **Pod Disruption Budgets:** Ensure a minimum number of pods during updates.
- **Anti-affinity rules:** Spread pods across nodes/zones.
- **Health checks:** Configure readiness and liveness probes.
- **Resource limits:** Set appropriate requests and limits.
- **Multi-zone deployment:** Use node affinity for zone distribution.
- **Horizontal Pod Autoscaler:** Scale based on metrics.
- **Rolling updates:** Zero-downtime deployments.

---

### Q: I want to run a one-time database migration task before my application starts. How can I achieve this in Kubernetes?

Use Init Containers, which run and complete before the main containers start:

```yaml
spec:
  initContainers:
  - name: migration
    image: myapp:migration
    command: ['sh', '-c', 'run-migration.sh']
    env:
    - name: DB_HOST
      value: "postgres-service"
  containers:
  - name: app
    image: myapp:latest
```

Init containers are perfect for migrations, schema updates, or data seeding.

---

### Q: I want to give only read-only permissions to check logs for users. How can you set up RBAC for this?

Use a `ClusterRole` scoped to reading pods and pod logs, then bind it to the user:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: log-reader
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: log-reader-binding
subjects:
- kind: User
  name: log-user
roleRef:
  kind: ClusterRole
  name: log-reader
  apiGroup: rbac.authorization.k8s.io
```

---

### Q: What happens if the firewall between the Kubernetes master node and worker nodes gets broken?

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

---

### Q: What are the steps to be performed while upgrading a Kubernetes cluster?

- **Backup everything:** etcd, configurations, and application data.
- **Check compatibility:** Review release notes and breaking changes.
- **Update the control plane first:** API server, controller-manager, scheduler.
- **Update kubelet and kube-proxy** on nodes one by one.
- **Drain nodes before updating:** `kubectl drain <node> --ignore-daemonsets`.
- **Update CNI and other addons** to compatible versions.
- **Verify cluster health** after each step.
- **Test applications** and roll back if issues occur.
- **Uncordon nodes:** `kubectl uncordon <node>`.

---

### Q: How can you ensure that only pods with a specific label can talk to your backend service?

Use a NetworkPolicy that selects the backend pods and allows ingress only from pods with the required label:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-access-policy
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
          access-backend: "true"
    ports:
    - protocol: TCP
      port: 8080
```

Only pods with the label `access-backend: "true"` can reach the backend pods.

---

### Q: All pods in a StatefulSet are trying to connect to the same storage volume. What's wrong, and how do you fix it?

**Issue:** StatefulSets should have unique PVCs per pod, but they're sharing storage.

**Root cause:**

- Incorrect `volumeClaimTemplates` configuration.
- PVC not created per pod instance.
- Storage class misconfiguration.

**Solution:** Use `volumeClaimTemplates` so each pod gets its own PVC:

```yaml
spec:
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
      storageClassName: fast-ssd
```

Each StatefulSet pod gets its own PVC with the naming pattern `<claim-name>-<pod-name>-<ordinal>` (e.g., `data-mysql-0`, `data-mysql-1`).
