# Repetitive Interview Questions

## What approach do you follow to ensure zero-downtime deployments in Production?

**Interviewer:** How do you deploy an application to Production without downtime?

**Candidate:**

For zero-downtime deployment, the old version must continue serving users until the new version is healthy and ready. I use multiple replicas, rolling updates, health probes, graceful shutdown, and monitoring.

### Run multiple replicas

I run at least two replicas for an application that must remain available.

```yaml
spec:
  replicas: 3
```

With only one Pod, users can experience downtime while that Pod is replaced.

### Use a rolling update

A rolling update creates new Pods gradually and removes old Pods only after the new ones are Ready.

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

- `maxSurge: 1` allows one extra Pod during deployment.
- `maxUnavailable: 0` keeps all required replicas available.

The cluster must have enough CPU and memory for the extra Pod.

### Configure health probes

```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  failureThreshold: 30
  periodSeconds: 5

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  periodSeconds: 5

livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  periodSeconds: 10
```

- **Startup probe:** Gives a slow application enough time to start.
- **Readiness probe:** Sends traffic only when the Pod is ready.
- **Liveness probe:** Restarts an application that is stuck.

Readiness is the most important probe during a rollout because an unready Pod should not receive user traffic.

### Shut down gracefully

When an old Pod is removed, the application should finish current requests before stopping.

```yaml
spec:
  terminationGracePeriodSeconds: 30
```

The application should also handle the termination signal and stop accepting new requests.

### Protect replicas during maintenance

A PodDisruptionBudget prevents too many replicas from being removed together during planned maintenance.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: orders-api
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: orders-api
```

This helps during node drains, but it does not protect against every unexpected failure.

### Keep changes compatible

During a rolling update, old and new versions run at the same time. Therefore:

- API changes should remain backward compatible.
- Database changes should work with both versions.
- Configuration should not break the old version.
- Sessions should not depend on one specific Pod.

For a database change, I normally add a new column first and remove the old column only in a later release.

### Validate before Production

Before deployment, I run:

- Unit and integration tests.
- Security and image scans.
- Deployment tests in a lower environment.
- A basic application request after deployment.

I build one versioned image and promote the same image to Production. I do not rebuild it for Production, because a rebuild can pull different base layers or packages. After Stage is approved, Production deploys the exact image by digest:

```yaml
image: myacr.azurecr.io/orders-api@sha256:<digest-tested-in-stage>
```

Only configuration changes between environments (Helm values, ConfigMaps, Key Vault), never the image.

### Monitor the rollout

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/<deployment-name> -n <namespace>
kubectl get pods -n <namespace>
kubectl get endpoints -n <namespace>
```

During the rollout, I monitor error rate, response time, Pod readiness, restarts, and Application Gateway backend health.

If the new release is unhealthy, I stop or roll it back:

```bash
kubectl rollout undo deployment/<deployment-name> -n <namespace>
```

With Helm, I let Helm wait for the rollout and roll back automatically if it fails:

```bash
helm lint ./charts/orders-api
helm upgrade --install orders-api ./charts/orders-api \
  -f values-prod.yaml --set image.tag=1.4.2 \
  -n prod --rollback-on-failure --wait --timeout 10m

helm history orders-api -n prod
helm rollback orders-api 3 -n prod
```

`--rollback-on-failure` is the Helm 4 name. In Helm 3 the same flag is `--atomic`.

Without Helm, I get the same safety from raw manifests: immutable image tags, `kubectl rollout status` as a pipeline gate, and `kubectl rollout undo`. Helm adds reusable templates, per-environment values files, and release history.

### Deployment strategies

#### Rolling deployment

New Pods gradually replace old Pods. This is simple and works well for normal low-risk releases.

#### Canary deployment

A small percentage of users receives the new version first. If the error rate remains normal, more traffic is moved to it.

```text
95% traffic -> old version
 5% traffic -> new version
```

This is useful for higher-risk changes.

#### Blue-green deployment

The old and new versions run separately. After the new version passes testing, traffic switches to it.

```text
Blue  = current version
Green = new version
```

This gives a fast rollback but requires extra capacity.

#### Blue-green or canary: which one?

**Interviewer:** Why would you use blue-green instead of canary?

**Candidate:** Blue-green switches all traffic at once, after the new version is fully tested. Canary moves traffic gradually and uses real users as the test.

| | Blue-green | Canary |
| --- | --- | --- |
| Traffic | 0% -> 100% in one switch | 5% -> 25% -> 100% |
| Testing | Full test before any user traffic | Small slice of real traffic |
| Rollback | Switch back to Blue | Move traffic away from new version |
| Cost | Two full environments for a short time | Less duplicate capacity, but needs traffic splitting and good metrics |

I choose blue-green when I want a simple release and an instant rollback, for example App Service slot swaps. I choose canary when the change is risky and only real traffic will show the problem, and I have good error-rate and latency alerts to decide whether to continue.

Remember:

- Neither strategy is zero-downtime by itself. Startup, health checks, and database compatibility still decide the result.
- Rollback only works if the old version still works with the current database schema.

### Example

Suppose an application has three replicas. During deployment, Kubernetes creates one new Pod.

The readiness probe must pass before that Pod receives traffic. Kubernetes then removes one old Pod and repeats the process.

At least three ready Pods continue serving users throughout the rollout.

### In short

I use multiple replicas, `maxUnavailable: 0`, correct readiness and startup probes, graceful shutdown, and enough cluster capacity. I keep application and database changes backward compatible, monitor the rollout, and roll back immediately if health checks or user requests fail.

## How did you upgrade the AKS Kubernetes version without downtime?

**Interviewer:** How did you upgrade the Kubernetes version, and what challenges did you face?

**Candidate:**

I upgrade AKS one minor version at a time, first in a lower environment and then in Production. I upgrade the control plane first, then each node pool in a controlled way. Replicas, PDBs, readiness probes, and spare node capacity keep the application available while nodes are drained.

```text
Check supported versions and release notes
  -> Check deprecated APIs, Helm charts, ingress controller, add-ons
  -> Upgrade Dev/QA, run smoke tests
  -> Prod: upgrade control plane only
  -> Upgrade node pools one by one (surge node -> cordon -> drain -> reimage)
  -> Verify nodes, pods, ingress, dashboards, smoke tests
```

```bash
az aks get-upgrades -g rg-prod -n aks-prod -o table

# Control plane first
az aks upgrade -g rg-prod -n aks-prod \
  --kubernetes-version 1.33.2 --control-plane-only

# Then each node pool, with an extra surge node and a drain timeout
az aks nodepool upgrade -g rg-prod --cluster-name aks-prod -n userpool \
  --kubernetes-version 1.33.2 --max-surge 33% --drain-timeout 30

kubectl get nodes -o wide
kubectl get pods -A | grep -v Running
```

In my project the version is set in Bicep, and a Shell/Python script runs the node pool upgrades one at a time and checks pod health between pools. Upgrades run inside a planned maintenance window.

### Challenges I faced

| Challenge | What I did |
| --- | --- |
| Deprecated APIs removed in the new version | Found them with `kubent`/`pluto` and the AKS deprecated-API insights, then updated manifests and Helm charts |
| Ingress controller or add-on not compatible | Upgraded it to a supported version before the cluster upgrade |
| Drain blocked by a PDB | Fixed PDBs that allowed zero disruption |
| Single-replica workloads | Raised replicas to at least 2 before the upgrade |
| Not enough capacity for evicted Pods | Used `--max-surge` and checked quota for the surge nodes |

One real example: a service had 2 replicas and a PDB with `minAvailable: 2`. Zero disruptions were allowed, so the node drain stopped. I saw it in the node events, changed the PDB to `maxUnavailable: 1`, and the upgrade continued without downtime.

Remember:

- AKS does not allow skipping minor versions. 1.31 -> 1.33 means two upgrades.
- For a very risky upgrade, I create a new node pool on the new version, move workloads to it, and then delete the old pool. This is blue-green at node pool level.
- Auto-upgrade channels plus a planned maintenance window keep clusters on supported versions.

## Can rotating secrets or certificates cause downtime?

**Interviewer:** Will there be downtime when you rotate a secret in Key Vault?

**Candidate:**

Rotating the secret in Key Vault does not cause downtime by itself. Downtime happens if the old credential stops working before every Pod is using the new one. So I keep both valid for a short overlap.

```text
Create new credential (old one still valid)
  -> Put new version in Key Vault
  -> Pods pick it up (CSI driver refresh or rolling restart)
  -> Validate the application
  -> Disable the old credential
```

- With the Key Vault CSI driver and `--enable-secret-rotation`, the mounted file is refreshed (default every 2 minutes).
- If the application reads the secret only at startup, I do a rolling restart. With multiple replicas and readiness probes, users see no downtime:

```bash
kubectl rollout restart deployment/orders-api -n prod
kubectl rollout status deployment/orders-api -n prod
```

- Secrets synced as environment variables never change inside a running Pod. They always need a restart.

The same idea works for TLS certificates. I enable auto-renewal in Key Vault and point Application Gateway to the **versionless** secret ID, so it picks up the renewed certificate (it checks every 4 hours). Expiry alerts at 30, 15, and 7 days catch anything that does not renew automatically.

## How do you get zero downtime on Azure App Service?

**Interviewer:** What are deployment slots, and how do you use them?

**Candidate:**

A deployment slot is a separate live copy of the Web App with its own host name. I deploy the new version to the `staging` slot, test it, and then swap it with Production. The swap warms up the instances first, so users do not see a cold start.

```text
Pipeline -> deploy v2 to staging slot
         -> smoke tests on staging URL
         -> approval
         -> swap staging <-> production
         -> v1 is now in staging (rollback = swap back)
```

```yaml
- task: AzureWebApp@1
  inputs:
    azureSubscription: azure-prod-connection
    appType: webAppLinux
    appName: orders-web
    deployToSlotOrASE: true
    resourceGroupName: rg-prod
    slotName: staging
    package: $(Pipeline.Workspace)/drop/app.jar

- task: AzureAppServiceManage@0
  inputs:
    azureSubscription: azure-prod-connection
    Action: Swap Slots
    WebAppName: orders-web
    ResourceGroupName: rg-prod
    SourceSlot: staging
```

Remember:

- Slots need Standard tier or higher.
- Mark environment-specific values (for example the database connection string) as **deployment slot settings**, so they stay with their slot during a swap.
- Set a warm-up path (`WEBSITE_SWAP_WARMUP_PING_PATH`) and enable the App Service health check, so the swap waits for a healthy app.
- **Traffic %** on a slot sends a small share of users to it, which gives a simple canary.
- Keep at least 2 instances and configure autoscale on the App Service Plan (for example, scale out when CPU is above 70% for 10 minutes). Scaling out adds instances; scaling up changes the plan size.
