# Repetitive Interview Questions

## Have you faced any Production issues, and how did you tackle them?

### Detailed answer

Yes, I have handled Production issues involving AKS deployments, container memory, Azure Container Registry, database connections, and Application Gateway. I follow the same simple approach for each issue:

```text
understand the problem
-> check logs, Events, and metrics
-> identify the cause
-> restore the service
-> verify that users can access it
-> apply a permanent fix
-> add monitoring to prevent it happening again
```

I do not restart Pods without checking the reason for the failure. I first check recent deployments, Kubernetes Events, logs, and monitoring data. I restore the service safely, verify that it works, and then make a permanent correction.

The following are simple examples from an Azure, AKS and VM environment.

---

### Scenario 1: A new AKS release caused HTTP 502 errors

**Interviewer:** After deploying a new application version to AKS, users started receiving HTTP 502 errors. How would you troubleshoot and fix it?

**Candidate:**

An HTTP 502 error means the gateway cannot get a valid response from the application. If it starts immediately after a deployment, I would first check whether the new Pods are healthy and ready to receive traffic.

Here's how I would troubleshoot it:

#### Check the Pods

```bash
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
```

I would check whether the Pods are `Running` and `Ready`. The Events section may show readiness probe failures, container restarts, or configuration errors.

#### Check the application logs

```bash
kubectl logs <pod-name> -n <namespace>
```

The logs help confirm whether the application failed to start, cannot connect to another service, or is listening on the wrong port.

#### Check the Service

```bash
kubectl get service -n <namespace>
kubectl get endpoints -n <namespace>
```

If the Service has no endpoints, it usually means the Pod labels do not match the Service selector or the Pods are not Ready.

#### Check the rollout

```bash
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

If the new release is unhealthy, I would stop further deployment and roll back to the last working Helm revision:

```bash
helm rollback <release-name> <revision> -n <namespace>
```

#### Fix the root cause

Depending on the evidence, I would:

- Correct the readiness probe path or port.
- Increase the startup time if the application needs longer to start.
- Correct the Service selector or target port.
- Fix a missing configuration value or dependency connection.
- Roll back the application if the new version introduced the problem.

#### Example

Suppose the application needs 60 seconds to start, but the health check begins after 10 seconds. The Pod is marked unhealthy before it is ready, so Application Gateway has no healthy backend and returns 502.

I would add or adjust the startup probe, redeploy, and verify that the Pods become Ready.

In short: I would check the Pods, logs, Service endpoints, health probes, and rollout status. I would roll back if users are affected, fix the failed configuration, and then verify the application through the external URL.

---

### Scenario 2: Java Pods were repeatedly `OOMKilled`

**Interviewer:** Your pods are repeatedly getting OOMKilled. How would you troubleshoot and fix it?

**Candidate:**

An OOMKilled error means the container used more memory than its allowed memory limit. The Linux kernel kills the process to protect the node.

Here's how I would troubleshoot it:

#### Confirm the reason

```bash
kubectl describe pod <pod-name>
```

In the Events section, I would verify that the container was terminated with `Reason: OOMKilled`.

#### Check memory usage

```bash
kubectl top pod <pod-name>
kubectl top node
```

This helps me understand whether the Pod is actually consuming excessive memory or if the node itself is under memory pressure.

#### Review resource requests and limits

```yaml
resources:
  requests:
    memory: 512Mi
  limits:
    memory: 1Gi
```

If the limit is too low for the application, I would increase it based on the application's normal memory usage.

#### Check the application

- Look for memory leaks.
- Verify if a recent deployment introduced higher memory consumption.

Review application logs:

```bash
kubectl logs <pod-name> --previous
```

#### Monitor over time

I would use monitoring tools like Prometheus and Grafana to see memory usage trends instead of relying on a single point in time.

#### Enable autoscaling if appropriate

If memory usage increases with traffic, I would configure a Horizontal Pod Autoscaler (HPA) based on memory or CPU metrics to distribute the load across more Pods.

#### If it is a memory leak

A leak looks different from a limit that is simply too small:

```text
Limit too small -> memory jumps at peak traffic, drops when traffic drops
Memory leak     -> memory climbs steadily, never comes back down, Pod is OOMKilled, cycle repeats
```

How I handled it in one incident:

```text
Memory alert + restart count rising
-> kubectl describe pod: Reason OOMKilled, Exit Code 137
-> Grafana: memory grows after every request cycle, never released
-> Mitigation: add replicas and a slightly higher limit so users are not affected
-> Share graphs, heap dump and logs with developers -> they fix the code
-> Deploy the fixed build through CI/CD -> memory stays flat
-> Add a memory alert (for example, above 85% of the limit for 15 minutes)
```

For Java, I also check that the JVM heap respects the container limit, for example `-XX:MaxRAMPercentage=75.0`. If the heap is larger than the limit, the container is OOMKilled before Java can throw `OutOfMemoryError`.

Remember:

- Raising the memory limit is only a temporary mitigation. The permanent fix is the code fix.
- I prove a leak with a trend over hours or days, not with one `kubectl top` value.
- After the fix, the same graph showing flat memory is my proof that the root cause was correct.

#### Example

Suppose a Java application has a memory limit of `512Mi`, but during peak traffic it uses `700Mi`. Kubernetes kills the container because it exceeds the limit.

I would first confirm the usage. Then I'd either increase the memory limit — for example to `1Gi` — if that's justified, or optimize the application's memory consumption.

In short: I would verify the OOMKilled event, check memory metrics, review resource limits, analyze application behavior, and then either optimize the application or adjust the Kubernetes resource configuration.

---

### Scenario 3: AKS Pods entered `ImagePullBackOff` after an identity change

**Interviewer:** Your AKS Pods are showing ImagePullBackOff. How would you troubleshoot and fix it?

**Candidate:**

`ImagePullBackOff` means Kubernetes cannot download the container image. It waits and retries with an increasing delay.

Here's how I would troubleshoot it:

#### Check the exact error

```bash
kubectl describe pod <pod-name> -n <namespace>
```

In the Events section, I would look for messages such as:

- `not found` — the image name or tag is wrong.
- `unauthorized` — AKS does not have permission to pull the image.
- `connection timeout` — AKS cannot reach the registry.

#### Check the image name

```bash
kubectl get deployment <deployment-name> -n <namespace> -o yaml
```

I would verify the registry name, repository, image name, and tag. I would also confirm that the image exists in Azure Container Registry.

#### Check ACR permissions

For AKS to pull an image from ACR, its kubelet identity normally needs the `AcrPull` role on the registry. If the Events show `unauthorized`, I would verify and restore the correct role assignment.

#### Check network access

If the registry uses a firewall or private endpoint, I would verify that the AKS network can reach ACR and resolve its DNS name.

#### Restart the rollout

After correcting the image, permission, or network issue, I would restart and verify the deployment:

```bash
kubectl rollout restart deployment/<deployment-name> -n <namespace>
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

#### Example

Suppose a cleanup accidentally removes the `AcrPull` role from the AKS kubelet identity. New Pods cannot download their images and enter `ImagePullBackOff`, while old Pods may continue running. I would restore the `AcrPull` role and restart the rollout.

In short: I would read the Pod Events, verify the image name and tag, check ACR permissions, and test network access. After fixing the cause, I would restart the deployment and confirm that all Pods are Running and Ready.

---

### Scenario 4: Azure Database for PostgreSQL connections were exhausted

**Interviewer:** Your application is getting database connection timeout errors during peak traffic. How would you troubleshoot and fix it?

**Candidate:**

A database connection timeout usually means the application cannot get a database connection within the allowed time. This can happen when there are too many connections, slow queries, or connections that are not closed correctly.

Here's how I would troubleshoot it:

#### Check the application logs

```bash
kubectl logs <pod-name> -n <namespace>
```

I would look for errors such as `connection timeout`, `too many connections`, or repeated database failures.

#### Check the number of Pods

```bash
kubectl get pods -n <namespace>
kubectl get hpa -n <namespace>
```

Each Pod can open several database connections. When HPA adds more Pods, the total number of connections can increase quickly.

#### Check database metrics

I would use Azure Monitor to check:

- Active database connections.
- Maximum allowed connections.
- CPU and memory usage.
- Slow or long-running queries.

#### Review connection settings

I would check how many connections each Pod can open and make sure the total stays within the database limit. I would also verify that the application closes connections after use.

#### Fix the issue

Depending on the cause, I would:

- Reduce the number of connections allowed per Pod.
- Fix code that does not close connections.
- Optimize slow database queries.
- Set an appropriate maximum replica count in HPA.
- Increase database capacity only when the existing limit is genuinely too small.

#### Example

Suppose the database safely supports 100 connections. If five Pods can each open 30 connections, they may request up to 150 connections.

I would reduce each Pod to a safe value, such as 15 connections, so five Pods use at most 75 and leave capacity for other work.

In short: I would check application logs, database metrics, Pod count, and connection settings. I would then reduce unnecessary connections, fix the application or queries, and make sure autoscaling does not exceed database capacity.

---

### Scenario 5: Application Gateway returned 502 after a routing/probe change

**Interviewer:** The AKS Pods are healthy (`1/1 Running`), but users get HTTP 502 or 504 from Azure Application Gateway. How would you troubleshoot and fix it?

**Candidate:**

`1/1 Running` only means the container is up and its readiness probe passes. It does not prove the full request path works. I would check each part of the path, from the outside in.

```text
User
-> Application Gateway
-> Ingress controller
-> Service
-> Pod
-> Dependencies (for example, PostgreSQL)
```

The status code gives the first clue:

- **502 Bad Gateway:** the gateway got a bad response or could not connect. Think unhealthy backend, wrong port, HTTP/HTTPS or certificate mismatch, no endpoints.
- **504 Gateway Timeout:** the gateway connected but waited too long. Think slow application, slow queries, or a dependency that hangs.

Here's how I would troubleshoot it:

#### Check the Pods and Service

```bash
kubectl get pods -n <namespace>
kubectl get service -n <namespace>
kubectl get endpoints -n <namespace>
```

The Pods should be Ready, and the Service should have endpoints. No endpoints usually means the Service selector does not match the Pods or the Pods are not Ready.

#### Test the application inside the cluster

I would call the Service from a temporary Pod:

```bash
kubectl run curl-test --rm -it --image=curlimages/curl -n <namespace> -- \
  curl -sv http://<service-name>:<port>/health
```

If it fails, the problem is between Service, Pod and application. If it works inside the cluster, the application and Service are probably healthy, and I would continue checking the Ingress and Application Gateway.

#### Check the Ingress controller

```bash
kubectl describe ingress <ingress-name> -n <namespace>
kubectl logs -n <ingress-namespace> <ingress-controller-pod>
```

I check the backend service name, port and host/path rules. In the controller logs I look for `upstream timed out`, `connection refused` or `no live upstreams`.

#### Check backend health

In Application Gateway, I would check whether the backend is shown as Healthy or Unhealthy. If it is Unhealthy, I would review the health probe:

- Probe path, such as `/health`.
- Protocol, HTTP or HTTPS.
- Backend port.
- Timeout setting.
- Expected response code.

#### Check routing and network access

I would verify that the gateway points to the correct backend and port. I would also check firewall and network rules if the gateway cannot connect to the AKS backend.

#### Check logs

```bash
kubectl logs <pod-name> -n <namespace>
```

Application Gateway access logs and Pod logs help show whether requests reach the application and what response is returned. For a 504, I look in the application logs for database timeouts, `too many connections` or a full connection pool (see Scenario 4 and Scenario 9).

#### Fix the issue

Depending on the evidence, I would correct the health probe, backend port, routing rule, certificate, or network access. I would then confirm that Application Gateway reports the backend as Healthy.

#### Example

Suppose the application health endpoint changes from `/health` to `/actuator/health`, but Application Gateway still checks `/health`. The probe receives a 404 response, marks every backend Unhealthy, and returns 502 to users.

I would update the probe path and verify the application through the public URL.

In short: I would check the Pods, Service endpoints, Application Gateway backend health, health probe, routing, and logs. After fixing the failed setting, I would test the complete path from the public URL to the Pod.

Remember:

- The key command is `kubectl get endpoints <service-name>` (or `kubectl get endpointslices`). Pods can be Running while the Service has zero endpoints.
- 502 usually means "cannot talk to the backend". 504 usually means "backend is too slow".

---

### Scenario 6: A Pod is in `CrashLoopBackOff` after a new deployment

**Interviewer:** After a new deployment, the Pod shows `0/1 CrashLoopBackOff` with 4 restarts. How do you troubleshoot and fix it?

**Candidate:**

`CrashLoopBackOff` means the container starts, crashes, and Kubernetes keeps restarting it. The wait between restarts grows (10s, 20s, 40s, up to 5 minutes). It is usually an application or configuration problem, not a node problem.

```text
kubectl describe pod (Events, Last State, Exit Code)
-> kubectl logs --previous (why did the last container die?)
-> find the cause: config, Secret, DB, port, command, memory, liveness probe
-> fix the Deployment / ConfigMap / Secret / image
-> kubectl rollout status -> 1/1 Running -> test the Service
```

#### Check the Pod and the crashed container's logs

```bash
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
```

`--previous` is the most important flag here. The current container may have just restarted, so the real error is in the previous one.

#### Read the exit code

```bash
kubectl get pod <pod-name> -n <namespace> \
  -o jsonpath='{.status.containerStatuses[*].lastState.terminated}'
```

| Exit code | Usual meaning |
| --- | --- |
| 0 | Process finished, but a Deployment expects it to keep running (wrong command) |
| 1 | Application error at startup |
| 126 / 127 | Command not executable / not found (wrong entrypoint) |
| 137 | Killed with SIGKILL, usually `OOMKilled` |
| 143 | Terminated with SIGTERM |

#### Fix the cause

- Missing or wrong environment variable, ConfigMap or Secret -> correct it and redeploy.
- Database connection refused -> check the connection settings (see Scenario 9).
- `OOMKilled` -> see Scenario 2.
- `Liveness probe failed` -> fix the probe path or port, or add a startup probe for a slow app.
- Bad image or code bug -> roll back to the last good version, then fix.

```bash
kubectl rollout status deployment/<deployment-name> -n <namespace>
kubectl get endpoints -n <namespace>
```

#### Example

A new release added a required `DB_HOST` variable, but the value was missing in the Production values file. The app exited with code 1 and the log said `DB_HOST is not set`. I rolled back with Helm to restore service, added the value, redeployed, and confirmed the Pod was `1/1 Running` and the API responded.

Remember:

- Only a failing **liveness** probe restarts a container. A failing **readiness** probe only removes the Pod from the Service endpoints.
- I do not delete the Pod again and again. The new Pod will crash for the same reason.

---

### Scenario 7: A Pod is stuck in `Pending` and is not scheduled

**Interviewer:** A Pod is not getting scheduled on any node. Why, and how do you fix it?

**Candidate:**

A `Pending` Pod means the scheduler could not find a node that meets all its rules. The scheduler writes the exact reason in the Pod Events.

```bash
kubectl describe pod <pod-name> -n <namespace>
```

```text
0/3 nodes are available: 3 Insufficient memory.
0/3 nodes are available: 3 node(s) had untolerated taint {dedicated: gpu}.
0/3 nodes are available: 3 node(s) didn't match Pod's node affinity/selector.
```

| Reason in Events | Check | Fix |
| --- | --- | --- |
| Insufficient CPU / memory | `kubectl describe node`, `kubectl top nodes` | Lower requests, or add nodes (cluster autoscaler or bigger node pool) |
| `nodeSelector` / affinity mismatch | `kubectl get nodes --show-labels` | Fix the label or the rule |
| Untolerated taint | `kubectl describe node` (Taints) | Add a matching toleration, or use the right node pool |
| Node `NotReady` | `kubectl get nodes` | Fix the node (Scenario 8) |
| Topology spread / anti-affinity too strict | The Pod spec | Relax the rule or add nodes in more zones |
| PVC not bound | `kubectl get pvc` | Fix the StorageClass or the disk zone |

Example of a matching toleration:

```yaml
tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
```

Remember:

- The scheduler uses **requests**, not real usage. A node can look idle in `kubectl top` and still be "full" for the scheduler.
- In AKS, if the cluster autoscaler is on but no node is added, I check its max node count and the subscription vCPU quota.

---

### Scenario 8: Nodes are `NotReady` (kubelet or control plane problem)

**Interviewer:** Pods and nodes are both `NotReady`. What is the reason? What happens if kubelet stops? What if etcd is down?

**Candidate:**

These are two different problems, and I troubleshoot them differently.

| | Pod NotReady | Node NotReady |
| --- | --- | --- |
| Start with | `kubectl describe pod`, `kubectl logs` | `kubectl describe node` (Conditions) |
| Usual causes | Readiness probe failing, app error, dependency down, wrong probe port | kubelet down, containerd down, memory / disk / PID pressure, network to API server, expired kubelet certificate |

If a node is `NotReady`, every Pod on it is affected, so I start with the node.

#### Check the node

```bash
kubectl get nodes
kubectl describe node <node-name>
```

In Conditions I look for `MemoryPressure=True`, `DiskPressure=True`, `PIDPressure=True`, or `Ready=Unknown` with "Kubelet stopped posting node status".

#### Check kubelet and the container runtime on the node

```bash
systemctl status kubelet
journalctl -u kubelet --since "30 min ago"
systemctl status containerd
```

On AKS, I do not SSH to nodes by default. I open a debug Pod on the node and use the host file system:

```bash
kubectl debug node/<node-name> -it --image=mcr.microsoft.com/azurelinux/busybox:1.36
chroot /host
```

#### What happens if kubelet stops?

```text
kubelet stops
-> node stops reporting status -> node becomes NotReady (after about 40 seconds)
-> existing containers may keep running, but nobody manages or reports them
-> no new Pods are scheduled there
-> after the eviction timeout (about 5 minutes), Deployment Pods are recreated on healthy nodes
```

The fix is to find why kubelet stopped (full disk, bad config, expired certificate), fix it, and restart kubelet. On AKS, node auto-repair also tries to reboot or reimage an unhealthy node. If it does not recover, I cordon, drain and reimage the node.

#### What if etcd is down?

etcd stores the whole cluster state. The API server reads and writes everything through it.

```text
kubectl -> kube-apiserver -> etcd
```

- Running Pods usually keep running, because kubelet on each node keeps what it already has.
- But you cannot reliably create, update, delete or scale anything. `kubectl get pods` may fail with `etcdserver: request timed out`.
- In HA, etcd runs 3 or 5 members and needs a quorum. With 3 members, losing 1 is fine. Losing 2 stops the control plane.
- On AKS, Microsoft manages the control plane and etcd. My job is to check the AKS Resource Health, use the Standard tier (uptime SLA) for Production, and back up my workloads and manifests (Velero or Azure Backup for AKS, plus GitOps).

Remember:

- Pod NotReady -> look at the app. Node NotReady -> look at the node.
- I find the exact condition before restarting anything.

---

### Scenario 9: The AKS application cannot connect to Azure Database for PostgreSQL

**Interviewer:** The application runs in AKS but cannot connect to PostgreSQL. How do you troubleshoot it?

**Candidate:**

I do not assume the database is down. I check each layer in order and stop when I find the broken one.

```text
App logs (exact error)
-> configuration (host, port 5432, database, user)
-> DNS (does the hostname resolve to the private IP?)
-> network (can the Pod reach TCP 5432?)
-> authentication and permissions
-> database health (connections, CPU, storage)
```

The error message points to the layer:

| Error | Layer to check |
| --- | --- |
| `could not translate host name` | DNS, Private DNS Zone link |
| `connection timed out` | NSG, firewall, route, Private Endpoint |
| `connection refused` | Wrong port or host |
| `password authentication failed` | Secret value, user, Entra ID token |
| `no pg_hba.conf entry` / SSL error | Firewall rule or `sslmode=require` missing |
| `too many connections` | Connection limits (Scenario 4) |

#### Test from inside the cluster

```bash
kubectl run dns-test --rm -it --image=busybox:1.36 -n <namespace> -- \
  nslookup <server>.postgres.database.azure.com

kubectl run pg-test --rm -it --image=postgres:16 -n <namespace> -- \
  psql "host=<server>.postgres.database.azure.com port=5432 dbname=<db> user=<user> sslmode=require"
```

If DNS and TCP work but `psql` fails, the problem is credentials or permissions, not the network.

#### Check the Azure side

- With Private Endpoint, the name must resolve to a private IP through the `privatelink.postgres.database.azure.com` Private DNS Zone, and that zone must be linked to the AKS VNet. With VNet integration (private access), the Flexible Server uses its own private DNS zone, which must also be linked.
- NSG rules on the AKS subnet and database subnet allow 5432.
- Server status, active connections against `max_connections`, CPU and storage in Azure Monitor.

```sql
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
```

#### Example

After a new Private DNS Zone was created in a different VNet, the hostname from AKS resolved to the public IP, and public access was disabled. Pods got `connection timed out`. I linked the Private DNS Zone to the AKS VNet, `nslookup` returned the private IP, and the application connected without a restart.

Remember:

- Never print the real password in logs while testing.
- With Workload Identity and Entra ID authentication, an `authentication failed` error can mean a missing database role for the identity, not a wrong password.

---

### Scenario 10: A Deployment YAML fails to apply

**Interviewer:** This Deployment YAML is broken. What is wrong?

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
name: app
spec:
replicas: 3
template:
metadata:
labels:
app: app
spec:
containers:
- image: nginx
```

**Candidate:**

I check three things first: indentation, the selector matching the Pod labels, and the container name and image.

1. **Indentation.** YAML uses spaces to show nesting. `name` must be under `metadata`, `replicas` under `spec`, and so on.
2. **Missing `selector`.** A `apps/v1` Deployment needs `spec.selector.matchLabels`, and it must match the template labels.
3. **Missing container `name`.** Every container needs a name.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - name: app
          image: nginx:1.27
```

I catch this before Production:

```bash
kubectl apply --dry-run=server -f deployment.yaml
helm lint ./chart && helm template ./chart | kubeconform -strict
```

Remember:

- The hierarchy is `Deployment -> spec -> template -> spec -> containers`.
- I also pin the image tag (`nginx:1.27`, not `nginx` or `latest`) so a rollback has a real version to go back to.

---

### Scenario 11: An application is down on an Azure Windows Server VM

**Interviewer:** An application on an Azure Windows Server VM is down. How do you troubleshoot it?

**Candidate:**

I go from the outside in and collect evidence before restarting anything, because a restart can hide the root cause.

```text
Azure VM healthy?
-> network: NSG, Load Balancer / App Gateway probe, Windows Firewall
-> Windows service running?
-> app listening on its port?
-> Event Viewer and app logs
-> CPU / memory / disk
-> dependencies: database, DNS, APIs, Key Vault
-> fix -> validate end to end -> monitor
```

#### Check the VM in Azure

```bash
az vm get-instance-view -g <rg> -n <vm-name> --query "instanceView.statuses"
```

I also check Resource Health, the Activity Log for recent changes, boot diagnostics and Azure Monitor metrics. If RDP does not work, I use Run Command or the Serial Console:

```bash
az vm run-command invoke -g <rg> -n <vm-name> \
  --command-id RunPowerShellScript \
  --scripts "Get-Service <service-name>; Get-PSDrive -PSProvider FileSystem"
```

#### Check the service, port and logs on the VM

```powershell
Get-Service <service-name>
Get-NetTCPConnection -LocalPort 8080 -State Listen
Test-NetConnection <private-ip> -Port 8080        # from another VM in the VNet
Get-WinEvent -LogName Application -MaxEvents 50 | Where-Object LevelDisplayName -eq 'Error'
Test-NetConnection <db-server> -Port 1433          # dependency check
```

If the port works locally but not from another VM, the cause is the NSG, Windows Firewall, or the app binding only to `127.0.0.1`.

#### Example

The service stopped after a weekend. Event Viewer showed write failures, and `C:` had 0 bytes free because IIS logs were never cleaned. I freed space, started the service, tested the URL, and added a disk-space alert in Azure Monitor and a scheduled log cleanup task.

Remember:

- A full disk is one of the most common reasons a Windows service will not start.
- I keep dependency updates on VMs controlled: test in lower environments, back up, and keep a rollback plan (see the rollback-strategy file).

---

## How I handled these incidents effectively

I use these basic steps for Production issues:

1. **Understand the impact.** Check which application and users are affected.
2. **Collect information.** Check Kubernetes Events, logs, metrics, and recent changes.
3. **Restore the service.** Roll back or correct the failed setting.
4. **Verify the result.** Test the application as a user would, not only the Pod status.
5. **Fix the cause.** Correct the application, Kubernetes configuration, permission, or network setting.
6. **Prevent recurrence.** Add monitoring, alerts, tests, and documentation.

## Did you provide RCA to clients?

**Interviewer:** Did you prepare RCAs for clients? What did they contain?

**Candidate:**

Yes. For every Production incident with client impact, we confirmed the root cause internally first, then shared a written RCA and walked the client through it in a call.

```text
1. Incident summary
2. Business impact (who, what, how long)
3. Timeline (detected, mitigated, resolved)
4. Detection (which alert or report)
5. Immediate mitigation
6. Root cause
7. Permanent fix
8. Preventive actions, with owners and dates
```

Example: Pods were restarting with `OOMKilled` (Scenario 2). Impact: some requests failed for about 20 minutes. Mitigation: more replicas and a temporary higher limit. Root cause: a memory leak in the application. Permanent fix: a code fix deployed through CI/CD, with memory flat afterwards. Prevention: a memory alert and a review of requests and limits for all services.

Remember:

- I write it in simple business language for the client, without blame and without heavy jargon.
- An RCA is complete only when every preventive action has an owner and a date.

## Recommended interview structure

For each Production incident, I use the STAR method:

- **Situation:** What failed, which environment was affected and what users observed.
- **Task:** My responsibility during the incident.
- **Action:** Evidence collected, mitigation, technical fix and coordination.
- **Result:** How service recovery was verified and what prevention was added.

I avoid saying only, “I restarted the Pod and it worked.” I explain what failed, how I found the cause, how I fixed it, and how I prevented it from happening again.

## Concise interview answer

Yes, I have handled several Production issues in AKS. These include Pods failing after a deployment, `CrashLoopBackOff`, `OOMKilled` from a memory leak, `ImagePullBackOff`, Pending Pods, `NotReady` nodes, PostgreSQL connection failures, and Application Gateway 502/504 errors. I have also fixed applications that were down on Azure Windows VMs.

For every issue, I first check the Pod Events, logs, metrics, and recent changes. I identify the exact cause instead of restarting the Pod immediately.

I then roll back or correct the failed setting, verify that users can access the application, and add monitoring or tests to prevent the same issue from happening again. For client-facing incidents, I also share an RCA with the timeline, root cause and preventive actions.
