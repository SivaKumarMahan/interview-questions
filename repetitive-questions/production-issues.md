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

The following are five simple examples from an Azure and AKS environment.

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

#### Example

Suppose a Java application has a memory limit of `512Mi`, but during peak traffic it uses `700Mi`. Kubernetes kills the container because it exceeds the limit.

I would first confirm the usage, then either increase the memory limit—for example, to `1Gi`—if justified, or optimize the application's memory consumption.

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

**Interviewer:** The AKS Pods are healthy, but Azure Application Gateway is returning HTTP 502. How would you troubleshoot and fix it?

**Candidate:**

If the Pods are healthy but Application Gateway returns 502, the problem is usually between the gateway and the application backend. I would check each part of the request path.

```text
User
-> Application Gateway
-> Ingress or Service
-> Pod
```

Here's how I would troubleshoot it:

#### Check the Pods and Service

```bash
kubectl get pods -n <namespace>
kubectl get service -n <namespace>
kubectl get endpoints -n <namespace>
```

The Pods should be Ready, and the Service should have endpoints. No endpoints usually means the Service selector does not match the Pods or the Pods are not Ready.

#### Test the application inside the cluster

I would call the Service from another Pod. If it works inside the cluster, the application and Service are probably healthy, and I would continue checking Application Gateway.

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

Application Gateway access logs and Pod logs help show whether requests reach the application and what response is returned.

#### Fix the issue

Depending on the evidence, I would correct the health probe, backend port, routing rule, certificate, or network access. I would then confirm that Application Gateway reports the backend as Healthy.

#### Example

Suppose the application health endpoint changes from `/health` to `/actuator/health`, but Application Gateway still checks `/health`. The probe receives a 404 response, marks every backend Unhealthy, and returns 502 to users.

I would update the probe path and verify the application through the public URL.

In short: I would check the Pods, Service endpoints, Application Gateway backend health, health probe, routing, and logs. After fixing the failed setting, I would test the complete path from the public URL to the Pod.

---

## How I handled these incidents effectively

I use these basic steps for Production issues:

1. **Understand the impact.** Check which application and users are affected.
2. **Collect information.** Check Kubernetes Events, logs, metrics, and recent changes.
3. **Restore the service.** Roll back or correct the failed setting.
4. **Verify the result.** Test the application as a user would, not only the Pod status.
5. **Fix the cause.** Correct the application, Kubernetes configuration, permission, or network setting.
6. **Prevent recurrence.** Add monitoring, alerts, tests, and documentation.

## Recommended interview structure

For each Production incident, I use the STAR method:

- **Situation:** What failed, which environment was affected and what users observed.
- **Task:** My responsibility during the incident.
- **Action:** Evidence collected, mitigation, technical fix and coordination.
- **Result:** How service recovery was verified and what prevention was added.

I avoid saying only, “I restarted the Pod and it worked.” I explain what failed, how I found the cause, how I fixed it, and how I prevented it from happening again.

## Concise interview answer

Yes, I have handled several Production issues in AKS. These include Pods failing after a deployment, `OOMKilled` errors, `ImagePullBackOff`, database connection timeouts, and Application Gateway 502 errors.

For every issue, I first check the Pod Events, logs, metrics, and recent changes. I identify the exact cause instead of restarting the Pod immediately.

I then roll back or correct the failed setting, verify that users can access the application, and add monitoring or tests to prevent the same issue from happening again.
