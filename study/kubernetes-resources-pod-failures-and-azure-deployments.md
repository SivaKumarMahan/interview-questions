# Kubernetes Resources, Pod Failures, and Azure Deployments

## 1. Resource Requests and Limits in Kubernetes

Resource requests and limits control how much CPU and memory a container is expected and allowed to use.

### Resource requests

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

### Resource limits

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

### Complete example

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

### Why they are useful

- Help the scheduler place pods on suitable nodes.
- Stop one container from using too many shared resources.
- Reduce resource contention between applications.
- Improve cluster stability and predictable performance.
- Give autoscalers useful resource information.

Requests and limits should be based on measured application usage. Values that are too low can cause throttling, memory failures, or poor scheduling decisions. Values that are too high can waste cluster capacity.

### Short interview answer

Resource requests describe the CPU and memory a container needs, and the scheduler uses them when selecting a node. Limits define how much the container can use. CPU use above its limit is throttled, while exceeding a memory limit can cause `OOMKilled`. Correct values improve scheduling, stability, and resource sharing.

## 2. Troubleshooting an Azure Resource Deployment Failure

Use a structured process to find the resource and reason that caused the failure.

### 1. Check the deployment error

Review the failed deployment in the Azure portal or with the Azure CLI:

```bash
az deployment group show \
  --resource-group <resource-group> \
  --name <deployment-name>
```

Look for the error code, detailed message, and failed resource.

### 2. Inspect deployment operations

```bash
az deployment operation group list \
  --resource-group <resource-group> \
  --name <deployment-name>
```

The operation history helps identify the exact step that failed.

### 3. Validate the deployment code

For ARM templates, Bicep, or Terraform, check for:

- Syntax and type errors
- Missing or incorrect parameters
- Invalid resource references
- Incorrect dependency order
- Unsupported or outdated API versions

Validate the deployment before applying it when the tool supports validation or a preview operation.

### 4. Check access and governance

Confirm that the user, service principal, or managed identity has the required RBAC role at the correct scope. Also check whether an Azure Policy or resource lock is blocking the operation.

Use least privilege: assign only the permissions required by the deployment instead of automatically granting `Owner`.

### 5. Check Azure constraints

Common causes include:

- A globally unique resource name is already in use.
- The selected SKU is unavailable in the region.
- A subscription or regional quota has been reached.
- The resource type is not registered for the subscription.
- Network, subnet, DNS, or private endpoint settings are invalid.
- A dependent resource does not exist or is in another scope.

### 6. Review the Activity Log

The Azure Activity Log can show authorization failures, policy denials, and control-plane errors. If a deployment runs in a CI/CD pipeline, inspect the pipeline logs as well.

### 7. Fix, redeploy, and verify

Correct the template, parameters, access, or Azure configuration. Run validation or a preview, redeploy, and then confirm that every expected resource is healthy.

### Short interview answer

Start with the deployment error and operation history to identify the failed resource. Then validate the infrastructure code and parameters, verify RBAC and Azure Policy, and check names, regions, SKUs, quotas, API versions, dependencies, and networking. Review the Activity Log for more detail, fix the root cause, redeploy, and verify the result.

### Worked example: AuthorizationFailed

An ACR deployment fails with `AuthorizationFailed` because the deploying service principal only has the `Reader` role on the resource group. Step 4 above (check access and governance) catches this immediately: `az deployment operation group list` shows the exact operation that was denied, and the fix is to assign the role the deployment actually needs (e.g. `Contributor` scoped to that resource group, or a narrower custom role) rather than reaching for `Owner`. Reassign the role and rerun the pipeline.

## 3. What Happens When One Pod Goes Down?

For normal stateless replicas, pods do not directly coordinate recovery. Kubernetes controllers and Services handle it.

Suppose a Deployment requires three replicas:

```text
Pod 1: Ready
Pod 2: Failed
Pod 3: Ready
```

The recovery flow is:

1. Kubernetes detects that Pod 2 is no longer healthy or running.
2. The Deployment's ReplicaSet sees that only two replicas remain and creates a replacement pod.
3. The Service stops routing new traffic to the failed or unready pod.
4. Pod 1 and Pod 3 continue handling requests.
5. The replacement pod starts and runs its readiness probe.
6. After the readiness probe succeeds, Kubernetes adds it to the Service endpoints and it begins receiving traffic.

Clients should connect through the Service rather than to individual pod IP addresses because pods are temporary and their IP addresses can change.

### Important distinction

Kubernetes coordinates pod replacement and traffic routing, but it does not manage application data consistency. Stateful or distributed applications may still need their own leader election, replication, quorum, or recovery logic.

### Short interview answer

When a pod fails, the Deployment creates a replacement to restore the desired replica count. During recovery, the Service routes traffic only to ready pods. Once the new pod passes its readiness probe, it is added to the Service and starts receiving traffic. Distributed applications may also require their own coordination logic for data and leadership.

## 4. Troubleshooting OOMKilled Pods

An `OOMKilled` status means the container used more memory than its configured limit, so the Linux kernel killed the process to protect the node.

### 1. Confirm the reason

```bash
kubectl describe pod <pod-name>
```

Check the Events section for `Reason: OOMKilled`, and note the exit code (`137`, which is `128 + SIGKILL`).

### 2. Check current memory usage

```bash
kubectl top pod <pod-name>
kubectl top node
```

This shows whether the container is genuinely near its limit, and whether the node itself is under memory pressure.

### 3. Review resource requests and limits

```yaml
resources:
  requests:
    memory: 512Mi
  limits:
    memory: 1Gi
```

Confirm the limit is actually appropriate for the workload rather than an arbitrary guess - see [§1](#1-resource-requests-and-limits-in-kubernetes) above.

### 4. Check the application itself

- Look for memory leaks.
- Check whether a recent deployment increased memory usage (new dependency, new caching behavior, a changed batch size).
- Review logs from the crashed container specifically:

```bash
kubectl logs <pod-name> --previous
```

### 5. Monitor memory over time

Use Prometheus and Grafana to see whether memory grows steadily (a leak) or spikes under specific traffic (a genuine capacity issue) - see [§2 in kubernetes-operations-and-stateful-workloads.md](kubernetes-operations-and-stateful-workloads.md#2-monitoring-aks-with-prometheus-and-grafana).

### 6. Decide: raise the limit, or fix the application

If traffic-driven memory growth is expected and legitimate, consider a Horizontal Pod Autoscaler so load is spread across more replicas instead of concentrated in one container. If a Java application has a 512Mi limit but needs 700Mi at peak, confirm the usage is genuine load (not a leak) before simply raising the limit.

### Short interview answer

I'd confirm the OOMKilled event and exit code with `kubectl describe pod`, check current memory pressure with `kubectl top`, and review the configured requests/limits. Then I'd check the application for a memory leak or a recent change that increased memory use, using `kubectl logs --previous` for the crashed container. I'd monitor memory over time with Prometheus/Grafana to distinguish a leak from genuine load, and either raise the limit (if justified) or fix the application - adding HPA if the growth is traffic-driven.

## 5. AKS ImagePullBackOff After an Identity Change

`ImagePullBackOff` means Kubernetes cannot pull the container image. When this starts right after an identity change, the first suspect is that the new identity lost registry access - not the image itself.

### 1. Confirm the error

```bash
kubectl describe pod <pod-name>
```

Check Events for `401 Unauthorized`, `403 Forbidden`, or `failed to pull image`.

### 2. Verify the managed identity

```bash
az aks show -g <resource-group> -n <cluster-name>
```

Confirm which identity the cluster is actually using now.

### 3. Check ACR role assignments

```bash
az role assignment list --assignee <managed-identity-id>
```

The identity needs `AcrPull` on the Azure Container Registry. If it was swapped (e.g. Identity A → Identity B) and only Identity A had `AcrPull`, pods lose the ability to authenticate to ACR immediately.

### 4. Verify the image name and tag

Rule out a genuinely wrong reference before assuming it's purely a permissions issue.

### 5. Fix and restart

Assign `AcrPull` to the correct identity, then:

```bash
kubectl rollout restart deployment <deployment-name>
```

### Short interview answer

Since the failure started after an identity change, I'd first verify which managed identity AKS is now using with `az aks show`, then check whether that identity has `AcrPull` on the registry with `az role assignment list`. If it doesn't - which is the common cause after an identity swap - I'd assign the role, confirm the image name/tag are correct, and restart the deployment to force a fresh pull.
