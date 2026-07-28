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

I build one versioned image and promote the same image to Production.

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

### Example

Suppose an application has three replicas. During deployment, Kubernetes creates one new Pod.

The readiness probe must pass before that Pod receives traffic. Kubernetes then removes one old Pod and repeats the process.

At least three ready Pods continue serving users throughout the rollout.

### In short

I use multiple replicas, `maxUnavailable: 0`, correct readiness and startup probes, graceful shutdown, and enough cluster capacity. I keep application and database changes backward compatible, monitor the rollout, and roll back immediately if health checks or user requests fail.