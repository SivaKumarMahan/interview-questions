# Repetitive Interview Questions

## Have you faced any Production issues, and how did you tackle them?

### Detailed answer

Yes, I have handled Production issues involving AKS deployments, container resources, Azure Container Registry access, database connections and Application Gateway routing. I follow a consistent incident-management approach:

```text
detect and acknowledge
-> assess user impact and severity
-> stop the blast radius
-> collect evidence
-> form and test a hypothesis
-> mitigate or roll back
-> verify user recovery
-> identify root cause
-> implement preventive actions
```

I do not begin by randomly restarting services. I first correlate alerts with recent deployments and configuration changes, preserve logs and Events, and assign one incident coordinator. The immediate goal is to restore service safely; detailed root-cause analysis and long-term correction follow after stabilization.

The following are five representative scenarios aligned with the Azure platform I have supported.

---

### Scenario 1: A new AKS release caused HTTP 502 errors

#### Situation and impact

After deploying a new version of a Java microservice to Production AKS, Application Gateway began returning intermittent HTTP 502 responses. The pipeline showed that the Helm deployment command completed, but several new Pods never became Ready. Because this was a rolling deployment, old and new replicas temporarily existed together, and only requests routed toward the unhealthy release were affected.

#### Investigation

I first paused further promotion and checked the release timeline against Azure Monitor and Application Insights. The error increase started immediately after the deployment.

I then inspected the workload:

```bash
kubectl get pods -n <namespace> -o wide
kubectl rollout status deployment/<name> \
  -n <namespace> \
  --timeout=<approved-timeout>
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> \
  -c <container> --previous
kubectl get events -n <namespace> \
  --sort-by=.metadata.creationTimestamp
helm history <release> -n <namespace>
```

The Kubernetes Events showed readiness failures. Application logs showed that the service required more startup time after a dependency initialization change, but the readiness/liveness configuration treated it as failed too early. As a result, the containers restarted before initialization completed and never became stable.

#### Immediate mitigation

I stopped the rollout and rolled the Helm release back to the previous known-good revision and ACR image digest:

```bash
helm rollback <release> <known-good-revision> \
  -n <namespace> \
  --wait \
  --timeout <approved-timeout>
```

I verified that all restored Pods were Ready, Application Gateway backend health recovered, smoke tests passed, and the 502 rate returned to baseline. We kept the service under observation before closing the incident.

#### Root cause and permanent fix

The application startup behavior had changed, but the Kubernetes probes had not been updated or load-tested with the new startup time.

I worked with the development team to:

- Add a startup probe to protect slow initialization.
- Keep readiness focused on whether the Pod can safely receive traffic.
- Keep liveness focused on a genuinely stuck process rather than temporary dependency latency.
- Tune thresholds from measured startup behavior instead of guessing.
- Add a pipeline test that validates the health endpoints.
- Deploy the correction through a small canary before full rollout.
- Add an alert for unavailable replicas and repeated probe failures.

#### Interview takeaway

The important point is that I did not consider a successful Helm command to be a successful release. Kubernetes readiness, Application Gateway health, Application Insights errors and a real API test determined whether the deployment was successful.

---

### Scenario 2: Java Pods were repeatedly `OOMKilled`

#### Situation and impact

During a traffic increase, one Java service developed high latency and intermittent failures. AKS kept recreating Pods, so the service appeared to recover briefly and then fail again. Azure Monitor and Prometheus showed increasing memory usage and container restarts.

#### Investigation

I checked the Pod status and last termination reason:

```bash
kubectl get pods -n <namespace>
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> \
  -c <container> --previous
kubectl top pod -n <namespace> --containers
kubectl top node
```

`kubectl describe` showed `OOMKilled`, confirming that the container crossed its memory limit. I correlated:

- Container working-set memory.
- Memory request and limit.
- JVM heap and garbage-collection metrics.
- Request rate and payload size.
- Application Insights traces.
- Recent application changes.
- Node memory pressure and other workloads on the node.

The root cause was not simply “AKS needs more memory.” The JVM heap, an application cache and concurrent request volume together could exceed the container limit. Horizontal scaling also created more replicas with the same unsafe settings.

#### Immediate mitigation

I reduced the blast radius by routing traffic to healthy replicas and stopping further rollout of the affected version. After confirming node capacity, we temporarily adjusted replicas and memory settings to stabilize the service while preserving enough cluster headroom. If the problem was introduced by the latest release, the safer action was to restore the previous known-good digest.

I avoided only increasing the memory limit without analysis because that could move the failure from the Pod to the node and affect unrelated services.

#### Root cause and permanent fix

The development and platform teams:

- Sized the JVM heap relative to the container limit and left room for non-heap/native memory.
- Bounded the in-memory cache and corrected the code path retaining large objects.
- Streamed large payloads instead of loading them completely into memory where appropriate.
- Right-sized requests and limits using observed percentiles.
- Load-tested the service at expected concurrency.
- Configured HPA using meaningful demand signals while respecting downstream capacity.
- Added alerts for memory growth, OOM termination, restart rate, throttling and node pressure.
- Added dashboard annotations for deployments to correlate regressions quickly.

#### Interview takeaway

The effective fix combined application correction and platform tuning. Kubernetes restart behavior restored individual containers, but it could not fix a memory leak or unsafe JVM/container sizing.

---

### Scenario 3: AKS Pods entered `ImagePullBackOff` after an identity change

#### Situation and impact

After an identity and RBAC cleanup, a deployment created new Pods that entered `ErrImagePull` and then `ImagePullBackOff`. Existing Pods continued serving traffic, so we prevented immediate user impact, but the release could not progress and the application had reduced recovery capacity.

#### Investigation

I checked the Pod Events rather than assuming the image was missing:

```bash
kubectl describe pod <pod> -n <namespace>
kubectl get events -n <namespace> \
  --sort-by=.metadata.creationTimestamp
```

I verified:

- The registry name, repository, tag and digest.
- That the image existed in Azure Container Registry.
- ACR network access and private DNS resolution from the AKS network.
- The AKS kubelet managed identity.
- The role assignment and scope used for image pulls.
- Whether the Pod incorrectly depended on an outdated `imagePullSecret`.

The Event message showed an authorization failure. During RBAC cleanup, the `AcrPull` assignment for the AKS kubelet identity had been removed.

#### Immediate mitigation

I stopped the deployment so Kubernetes would not continue creating failing replicas. After confirming the correct kubelet identity and registry scope, I restored the least-privilege `AcrPull` assignment. I waited for RBAC propagation, restarted only the affected rollout and verified that the exact approved image digest could be pulled.

I did not work around the issue by adding registry administrator credentials to a Kubernetes Secret. That would have introduced a long-lived credential and hidden the identity problem.

#### Root cause and permanent fix

The role assignment had been changed outside the complete AKS-to-ACR dependency review.

Preventive actions included:

- Managing the identity and `AcrPull` assignment through Terraform/Bicep.
- Protecting identity and RBAC changes with CODEOWNERS review.
- Running a pre-deployment image-pull validation in a representative namespace.
- Alerting on `ErrImagePull` and `ImagePullBackOff`.
- Documenting the distinction between the pipeline push identity and AKS pull identity.
- Reviewing ACR private endpoint, Private DNS and firewall paths as part of the deployment checklist.

#### Interview takeaway

The pipeline identity that pushes an image to ACR and the AKS kubelet identity that pulls it are different authorization paths. Verifying that distinction led to a targeted fix without weakening registry security.

---

### Scenario 4: Azure Database for PostgreSQL connections were exhausted

#### Situation and impact

A Java microservice began returning intermittent 5xx responses and database timeouts during peak traffic. AKS Pods were Running and Ready, but Application Insights dependency telemetry showed slow and failed PostgreSQL calls. Azure Database for PostgreSQL metrics showed connections approaching the safe limit.

#### Investigation

I correlated:

- Application request rate and 5xx responses.
- Application Insights dependency duration and failures.
- Active, idle and waiting database connections.
- Database CPU, memory, storage and lock behavior.
- HikariCP or application connection-pool metrics.
- Number of AKS replicas and the maximum pool size per replica.
- Long-running queries and connection leaks.

The aggregate pool size had not been calculated across all replicas. When HPA added Pods, each Pod created its full connection pool, and the total approached the database limit. Some application paths also held connections longer than expected.

#### Immediate mitigation

I paused unnecessary scaling and reduced pressure on the affected service. With the database/application owner, we identified confirmed stale or problematic sessions and avoided terminating valid transactions blindly. Where required, we temporarily adjusted capacity or traffic while restoring a safe connection budget.

We did not simply keep increasing the server connection limit, because each database connection consumes memory and uncontrolled growth can create a larger performance failure.

#### Root cause and permanent fix

We corrected the application and platform configuration by:

- Calculating a total connection budget and dividing it across replicas.
- Reducing pool size and setting sensible acquisition, idle and maximum-lifetime values.
- Ensuring every code path closes connections correctly.
- Optimizing slow queries and adding justified indexes.
- Using bounded retries with backoff rather than retry storms.
- Evaluating Azure Database for PostgreSQL connection pooling/PgBouncer where appropriate.
- Aligning HPA maximum replicas with database capacity.
- Adding alerts for connection utilization, pool wait time, query latency and failed dependencies.
- Load-testing scaling behavior rather than testing only one Pod.

#### Interview takeaway

The issue appeared to be a Kubernetes application failure, but end-to-end telemetry showed that the real bottleneck was the combined connection behavior of all replicas and the database.

---

### Scenario 5: Application Gateway returned 502 after a routing/probe change

#### Situation and impact

After a configuration release, users received HTTP 502 errors through Azure Application Gateway, although the AKS Pods and Service appeared healthy from inside the cluster.

#### Investigation

I traced the request path instead of stopping at Pod health:

```text
client
-> DNS
-> Application Gateway listener and routing rule
-> backend setting and health probe
-> ingress/Service
-> Pod readiness and application port
```

I checked:

- Application Gateway provisioning and operational state.
- Listener, hostname, certificate and routing-rule priority.
- Backend pool membership and backend health details.
- Probe protocol, host, path, port, timeout and accepted response.
- Application Gateway access and performance logs in Log Analytics.
- WAF logs for blocked requests.
- NSG, UDR, Private DNS and firewall paths.
- Ingress, Service endpoints and Pod application logs.
- Backend TLS hostname and certificate trust where HTTPS was used.

The backend-health details showed that the custom probe returned an unexpected response after the application health path changed. The Pods were healthy, but Application Gateway considered every backend unhealthy and therefore returned 502.

#### Immediate mitigation

I reverted the probe/routing configuration through the controlled deployment process or temporarily restored the backward-compatible health endpoint, depending on which option had the lowest risk. After the change, I verified that Application Gateway reported healthy backends, smoke tests passed externally and the 502 rate returned to baseline.

I avoided disabling WAF, opening broad NSG rules or changing multiple network components simultaneously because that would increase exposure and make the root cause harder to prove.

#### Root cause and permanent fix

The application endpoint and gateway probe configuration were released independently.

We prevented recurrence by:

- Versioning Application Gateway configuration through Terraform/Bicep.
- Reviewing application and probe changes together.
- Testing the full external path before Production promotion.
- Keeping health endpoints backward compatible during rollout.
- Adding an alert for unhealthy backend count and 502 rate.
- Adding synthetic monitoring through Application Gateway rather than testing only the ClusterIP.
- Validating backend TLS hostname/certificate and Private DNS in pre-production.
- Requiring a targeted rollback plan for networking changes.

#### Interview takeaway

“Pods are healthy” does not prove that users can reach the application. I followed the complete Layer-7 path and used Application Gateway backend-health evidence to isolate the failing hop.

---

## How I handled these incidents effectively

Across these scenarios, the effective practices were:

1. **I used evidence before action.** Deployment history, Kubernetes Events, previous container logs, Azure metrics and Application Insights traces guided the investigation.
2. **I limited the blast radius.** I paused rollout, retained healthy replicas and used rollback or traffic control rather than allowing a bad version to continue.
3. **I separated mitigation from root cause.** Restoring service came first; permanent code, configuration or architecture correction followed.
4. **I verified the user journey.** Recovery required an external smoke test or business transaction, not only a green Kubernetes status.
5. **I preserved security.** I did not solve identity failures with administrator credentials or network failures with broad access.
6. **I automated prevention.** Fixes were moved into Terraform/Bicep, Helm, pipeline gates, dashboards, alerts and runbooks.
7. **I documented and communicated.** Stakeholders received impact, mitigation and recovery updates, followed by a blameless RCA with owners and deadlines.

## Recommended interview structure

For each Production incident, I use the STAR method:

- **Situation:** What failed, which environment was affected and what users observed.
- **Task:** My responsibility during the incident.
- **Action:** Evidence collected, mitigation, technical fix and coordination.
- **Result:** How service recovery was verified and what prevention was added.

I avoid saying only, “I restarted the Pod and it worked.” A strong answer explains why the Pod failed, how I proved the cause, how I restored service safely and what change prevented recurrence.

## Concise interview answer

Yes, I have handled several Azure Production incidents. For example, after an AKS release we saw intermittent 502 errors. I correlated the deployment with Application Insights, inspected Kubernetes Events and previous logs, and found that new Pods were failing readiness because application startup time had changed. I stopped the rollout, restored the previous Helm revision and ACR digest, verified Application Gateway health and a real API transaction, and then added a proper startup probe, tuned readiness from measured behavior and introduced canary validation.

I have also handled Java Pods being `OOMKilled`, AKS image pulls failing after an ACR RBAC change, PostgreSQL connection exhaustion caused by aggregate connection pools across scaled replicas, and Application Gateway 502 errors caused by an outdated health probe. In each case, I first limited impact, used logs/metrics/traces to isolate the failing layer, applied the smallest safe mitigation, verified user recovery and then automated the permanent fix through code, pipeline gates, monitoring and runbooks.
