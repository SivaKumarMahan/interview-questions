# Repetitive Interview Questions

## What approach do you follow to ensure zero-downtime deployments in Production?

### Detailed answer

In my project, zero downtime is treated as an **end-to-end availability objective**, not as a single pipeline option. The CI/CD tool can start a deployment, but uninterrupted service depends on application compatibility, AKS workload design, traffic routing, database migration strategy, capacity, observability and rollback.

Our release path is:

```text
reviewed code
-> tested Java artifact
-> immutable Docker image in Azure Container Registry
-> deploy a small number of new AKS Pods
-> route traffic only after readiness succeeds
-> validate technical and business signals
-> continue, pause or roll back
```

For normal application releases, I use a controlled Kubernetes rolling update. For higher-risk changes, I prefer canary or blue-green deployment so that traffic can be shifted gradually and restored quickly.

### 1. Make the application safe for overlapping versions

During a zero-downtime rollout, the old and new application versions run at the same time. Therefore, both versions must remain compatible.

Before deployment, I confirm:

- APIs remain backward compatible for existing clients.
- Events and messages can be understood by both versions.
- Configuration supports old and new Pods during the transition.
- Sessions are externalized or the application is stateless where practical.
- Shared caches and files do not assume only one application version.
- Background jobs cannot run twice or process the same work unsafely.
- The application handles `SIGTERM` and stops accepting new work gracefully.
- Long-running requests have a defined drain and timeout behavior.
- Database changes remain compatible with both application versions.

Large features are placed behind reviewed feature flags when appropriate. This separates **deployment** from **feature release**: the new code can be deployed safely while the risky behavior remains disabled, and the feature can be enabled gradually after validation.

### 2. Build once and promote an immutable artifact

The CI pipeline compiles and tests the Java application, builds the Docker image, scans it and pushes it to Azure Container Registry. The release is identified by an immutable image digest:

```text
Git commit -> ACR image tag -> immutable digest
```

Dev, QA/UAT and Production receive the same digest. We do not rebuild from environment-specific branches, use `latest`, or manually copy files into Production. This guarantees that the artifact tested in lower environments is the one deployed to Production.

The deployment record includes:

- Git commit and pull request.
- Test, quality and security results.
- ACR image digest.
- Helm chart and configuration version.
- Database migration compatibility.
- Approver and change record.
- Previous known-good digest and rollback procedure.

### 3. Run multiple replicas

A single replica cannot provide application-level availability during replacement. Production workloads run multiple replicas, sized so that the remaining healthy Pods can handle traffic while another Pod starts or terminates.

Replicas are distributed across nodes and, where required, Availability Zones using topology spread constraints or pod anti-affinity. This prevents all replicas from being lost with one node or zone.

I also verify that:

- AKS has enough node capacity for surge Pods.
- Cluster autoscaling limits and startup time are understood.
- Critical system and application workloads use appropriate node pools.
- Resource requests reflect real scheduling needs.
- CPU and memory limits do not cause throttling or `OOMKilled` during rollout.
- Downstream services can handle old and new replicas together.

### 4. Configure a controlled AKS rolling update

A representative Deployment pattern is:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments-api
spec:
  replicas: 3
  minReadySeconds: 20
  progressDeadlineSeconds: 600
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: payments-api
  template:
    metadata:
      labels:
        app: payments-api
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: payments-api
          image: <acr-name>.azurecr.io/payments-api@sha256:<digest>
          ports:
            - name: http
              containerPort: 8080
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          startupProbe:
            httpGet:
              path: /health/startup
              port: http
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: /health/ready
              port: http
            periodSeconds: 5
            timeoutSeconds: 2
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health/live
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 3
```

The exact numbers come from load and startup testing; they are not copied blindly between services.

The important settings are:

- **`maxUnavailable: 0`:** Kubernetes should not intentionally reduce the number of available replicas during the rollout.
- **`maxSurge: 1`:** One extra Pod can start before an old Pod is removed.
- **`minReadySeconds`:** A new Pod must remain Ready for a minimum period before it is treated as available.
- **`progressDeadlineSeconds`:** A stalled rollout becomes visible instead of waiting indefinitely.

`maxUnavailable: 0` requires enough CPU, memory, IP and quota capacity for surge Pods. Without capacity, the rollout can remain Pending rather than provide zero downtime.

### 5. Use probes for the correct purpose

I configure three different health checks:

- **Startup probe:** Protects a slow-starting Java application from premature liveness failure.
- **Readiness probe:** Decides whether the Pod can safely receive traffic.
- **Liveness probe:** Restarts a genuinely stuck container.

Readiness is the key traffic gate. The Service should route requests only to Ready endpoints. A new Pod does not receive traffic merely because its process started.

Probe endpoints must be lightweight and intentional. Liveness should not fail just because a noncritical external dependency has a temporary problem; otherwise every replica can restart during the same dependency outage. Readiness may consider critical dependencies only when the application truly cannot serve useful traffic without them.

The pipeline validates probe paths in lower environments and monitors readiness failures during rollout.

### 6. Protect voluntary disruptions with a PodDisruptionBudget

A representative PodDisruptionBudget is:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: payments-api
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: payments-api
```

This protects availability during voluntary disruptions such as node drains and certain maintenance operations. It does not replace the Deployment rolling-update settings, and it cannot protect against every involuntary failure such as a node crash.

The budget must match the replica count and actual capacity. An impossible PDB can block node maintenance or cluster upgrades, so we test node drain behavior and monitor allowed disruptions.

### 7. Drain traffic and terminate gracefully

When Kubernetes terminates an old Pod, the application must stop receiving new traffic and complete or cancel in-flight work safely.

The shutdown sequence should be:

```text
Pod begins termination
-> readiness becomes false
-> endpoint is removed from service routing
-> ingress/Application Gateway updates backend routing
-> existing requests drain
-> application handles SIGTERM and closes resources
-> container exits before the grace period ends
```

The application handles `SIGTERM`, stops accepting new work, completes bounded in-flight requests, closes database/message connections and exits cleanly. `terminationGracePeriodSeconds` is based on the longest supported request and measured routing propagation.

Where a `preStop` hook is needed, it performs a tested drain action or calibrated delay. I do not add an arbitrary long sleep without measuring endpoint and Application Gateway/ingress convergence because that only hides the timing problem.

Application Gateway and ingress health probes must use the correct host, port and path so that external traffic follows the same readiness contract as Kubernetes.

### 8. Choose the deployment strategy from risk

#### Rolling deployment

Rolling update is the normal choice for backward-compatible stateless services:

```text
start one new Pod
-> wait until Ready and stable
-> remove one old Pod gracefully
-> repeat
```

It uses less extra capacity than blue-green but temporarily runs two versions together and requires strong compatibility.

#### Canary deployment

For a high-risk application change, a small percentage of traffic goes to the new version first:

```text
stable 95% / canary 5%
-> validate
-> stable 75% / canary 25%
-> validate
-> canary 100% or roll back
```

The actual steps and observation time depend on traffic volume and risk. Promotion gates evaluate errors, latency, saturation and business success. If a threshold fails, canary traffic returns to zero while the stable version continues serving users.

A progressive delivery controller such as Argo Rollouts or Flagger can automate weighted rollout and metric analysis when the platform has adopted it. Otherwise, the pipeline uses a controlled, observable process rather than pretending that a standard rolling update provides traffic weighting.

#### Blue-green deployment

For major or difficult-to-reverse changes, the new green version is deployed alongside the existing blue version. Green is tested internally and then receives a controlled traffic switch. Blue remains available during the observation window for fast failback.

Blue-green provides strong isolation and rapid traffic rollback but requires extra capacity and careful handling of databases, queues, scheduled jobs and other shared state.

### 9. Use backward-compatible database migrations

Database changes are a common cause of downtime and failed rollback. I use **expand, migrate and contract**:

1. **Expand:** Add new tables, columns or indexes without removing anything required by the old version.
2. **Deploy compatible code:** Old and new application versions can use the expanded schema.
3. **Migrate/backfill:** Move data through a monitored, restartable process.
4. **Switch usage:** Enable the new path after validation.
5. **Contract later:** Remove obsolete schema only after the rollback window closes and no old consumer remains.

I avoid combining a destructive `DROP`, incompatible rename or required data rewrite with the initial application rollout. Long-running migrations are separated from Pod startup, tested for lock/IO impact and monitored on Azure Database for PostgreSQL.

If the application rollout fails, the previous image can run against the expanded schema. Database restoration is reserved for an approved data-recovery incident; it is not treated as a normal application rollback.

### 10. Separate configuration and secrets from the image

The image remains identical across environments. Non-sensitive environment differences come from reviewed Helm values and ConfigMaps. Secrets and certificates remain in Azure Key Vault and are accessed through managed identity/workload identity and an approved integration.

Configuration changes are versioned and promoted with the release. The pipeline checks compatibility before traffic reaches new Pods. We do not edit Production manually and leave undocumented drift.

For feature flags:

- Changes have an owner and audit trail.
- Risky features can be enabled for a small audience.
- A kill switch can disable the feature without rolling back the complete application.
- Flags have removal criteria to prevent permanent complexity.

### 11. Validate before Production

Before Production deployment, the same release passes:

- Pull-request review and protected branch policies.
- Unit and integration tests.
- SonarQube/quality gate.
- Secret, dependency, container, IaC and Kubernetes policy scans.
- Image scan and immutable ACR publication.
- Helm rendering/linting and policy validation.
- Deployment to Dev and QA/UAT.
- Smoke, API, regression and compatibility tests.
- Load testing for material performance or scaling changes.
- Rollback rehearsal for high-risk releases.

Production deployment requires the appropriate approval and change window. The deployment identity is least privilege and separate from the build identity.

### 12. Execute and monitor the Production rollout

The pipeline deploys through Helm using the exact image digest:

```bash
helm upgrade --install <release> <chart> \
  --namespace <namespace> \
  --values <production-values> \
  --set image.digest=<approved-digest> \
  --wait \
  --atomic \
  --timeout <approved-timeout>
```

`--wait` and `--atomic` help detect failed Helm upgrades and restore the previous release state, but they are not a complete zero-downtime guarantee. The workload still needs correct replicas, rollout settings, probes, capacity, compatibility and external verification.

During deployment, I monitor:

```bash
kubectl rollout status deployment/<name> \
  -n <namespace> \
  --timeout=<approved-timeout>
kubectl get pods -n <namespace> -w
kubectl get events -n <namespace> \
  --sort-by=.metadata.creationTimestamp
```

The pipeline also watches:

- Available and unavailable replicas.
- Readiness and restart rate.
- Pending Pods and node pressure.
- HTTP 5xx rate.
- p95/p99 latency.
- Application Insights dependency failures.
- JVM CPU, memory and garbage collection.
- Database connections and query latency.
- Queue depth and background-job completion.
- A real external business transaction through Application Gateway.

Azure Monitor, Log Analytics, Application Insights, Prometheus and Grafana provide the health evidence. The release proceeds only when the defined signals remain healthy through the observation window.

### 13. Pause or roll back automatically when gates fail

Before deployment, we record the previous known-good Helm revision and ACR digest. If the new version fails readiness, smoke tests, error-rate, latency or business gates:

1. Stop further rollout or traffic increase.
2. Preserve logs, Events, metrics and traces.
3. Return traffic to the stable version.
4. Roll back to the previous Helm revision/digest when application and database compatibility permit.
5. Verify user recovery through the external path.
6. Block the failed digest from further promotion.
7. Complete root-cause analysis before attempting another release.

For a Helm-managed application:

```bash
helm history <release> -n <namespace>
helm rollback <release> <known-good-revision> \
  -n <namespace> \
  --wait \
  --timeout <approved-timeout>
```

Rollback is periodically tested in a representative non-production environment. An untested rollback procedure is only a document, not a recovery capability.

### 14. Protect the platform as well as the application

Application zero downtime also depends on AKS and Azure architecture:

- AKS node pools have sufficient capacity and autoscaling boundaries.
- Replicas are distributed across nodes/zones.
- PodDisruptionBudgets protect node maintenance.
- Node upgrades use controlled surge and drain behavior.
- ACR, Key Vault, Private DNS and private endpoints are highly available for the required path.
- Application Gateway has correct backend health probes.
- Azure Database for PostgreSQL uses the required availability, backup and recovery design.
- Terraform/Bicep changes are reviewed and staged separately from routine application releases.
- Monitoring exists before the deployment begins.

We avoid changing application code, database schema, AKS, networking and identity in one large release unless there is a tested dependency plan. Smaller independently reversible changes reduce blast radius.

### 15. Cases where zero downtime cannot be promised

I do not promise zero downtime when the architecture cannot support it. Examples include:

- A single application replica.
- A destructive database migration.
- A stateful application with no replication or failover.
- An incompatible API/protocol change.
- Insufficient capacity for surge Pods.
- A dependency with no redundancy.
- A certificate, DNS or network cutover without overlap.
- A platform migration with an untested data path.

In those situations, I redesign the change, introduce parallel capacity or replication, break it into backward-compatible phases, or schedule an approved maintenance window with a clear user communication and recovery plan.

### How this approach ensures zero downtime

The approach works because:

- Old Pods stay available until new Pods are Ready.
- Multiple replicas and topology distribution avoid a single replacement outage.
- Surge capacity prevents availability from dropping during rollout.
- Readiness and Application Gateway probes protect traffic.
- Graceful termination drains old Pods safely.
- Old and new application/database versions remain compatible.
- The same immutable artifact is tested and promoted.
- Canary or blue-green limits risk for major changes.
- Observability gates verify user health during deployment.
- The previous known-good digest remains available for rollback.

### Concise interview answer

I treat zero downtime as an application and architecture requirement, not just a pipeline option. We build the Java application once, publish an immutable Docker digest to ACR and promote the same digest through Dev, QA/UAT and Production.

In AKS, Production runs multiple replicas distributed across nodes or zones. The Deployment uses `RollingUpdate`, normally with `maxUnavailable: 0` and controlled `maxSurge`, plus startup, readiness and liveness probes, resource requests, a PodDisruptionBudget and graceful `SIGTERM` handling. A new Pod receives traffic only after readiness succeeds, while the old Pod remains available until traffic drains.

For higher-risk releases, we use canary or blue-green deployment with automated smoke tests and Azure Monitor, Application Insights, Prometheus and Grafana gates for error rate, latency, saturation and business transactions. Database changes follow expand, migrate and contract so old and new versions remain compatible. If a gate fails, we stop promotion and restore the previous Helm revision and ACR digest. This combination of compatibility, controlled traffic, capacity, health checks, monitoring and tested rollback is how I minimize or eliminate Production downtime.
