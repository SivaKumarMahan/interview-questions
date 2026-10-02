# Lab 1: Fix a Broken Kubernetes Deployment

> Debug a Deployment on a local kind cluster that has two bugs: a crash that causes `CrashLoopBackOff`, and a readiness probe that keeps the Pods out of the Service.

**Time:** about 30 minutes. **Level:** Intermediate.

## What you practise

- Reading `kubectl describe` Events and `kubectl logs --previous`
- Telling a crashing container apart from a container that runs but is not ready
- Checking Service endpoints and why a rollout gets stuck
- The same troubleshooting order used in [kubernetes/08-troubleshooting.md](../../kubernetes/08-troubleshooting.md)

## Prerequisites

| Tool | Tested with | Install |
| --- | --- | --- |
| Docker | 29.1 | <https://docs.docker.com/engine/install/> |
| kind | v0.33.0 | <https://kind.sigs.k8s.io/docs/user/quick-start/#installation> |
| kubectl | v1.35 | <https://kubernetes.io/docs/tasks/tools/> |

## Files

| File | Purpose |
| --- | --- |
| `kind-config.yaml` | A one-node kind cluster called `broken-deploy-lab` |
| `broken/` | The manifests with the two bugs: Namespace, ConfigMap, Deployment, Service |
| `solution/` | The fixed manifests. Try not to open these until you have finished. |

## Steps

### 1. Create the cluster and deploy the broken app

```bash
kind create cluster --config kind-config.yaml
kubectl apply -f broken/namespace.yaml
kubectl apply -f broken/
kubectl -n lab get pods -w
```

After about 30 seconds the Pods show `Error` and then `CrashLoopBackOff`, and the restart count keeps going up. Press `Ctrl+C` to stop watching.

### 2. Find the first bug

Work through it in this order:

```bash
kubectl -n lab describe pod -l app=web | sed -n '/Last State/,/Exit Code/p'
kubectl -n lab logs deploy/web --previous
```

<details><summary>Hint</summary>

The container exits with code 1 straight after it starts. The logs of the previous container say which file and which line nginx cannot parse. Look at that line in `broken/configmap.yaml`.

</details>

<details><summary>Answer</summary>

`index index.html` is missing its semicolon, so nginx fails with `unexpected "}" in /etc/nginx/conf.d/default.conf:6` and exits. Kubernetes restarts it, it fails again, and the back-off delay grows: that is `CrashLoopBackOff`.

Fix it and restart the Pods so they read the new config:

```bash
kubectl apply -f solution/configmap.yaml
kubectl -n lab rollout restart deploy/web
```

A ConfigMap change does not restart Pods by itself, which is why you need the `rollout restart`.

</details>

### 3. Find the second bug

```bash
kubectl -n lab get pods
```

The Pods are now `Running`, but `READY` shows `0/1` and the rollout never finishes. Find out why:

```bash
kubectl -n lab get events --field-selector reason=Unhealthy
kubectl -n lab get endpointslices -l kubernetes.io/service-name=web \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"  ready="}{.conditions.ready}{"\n"}{end}'
kubectl -n lab rollout status deploy/web --timeout=20s
```

<details><summary>Hint</summary>

Compare the port in the readiness probe with the port nginx listens on in the ConfigMap.

</details>

<details><summary>Answer</summary>

The readiness probe checks port `8080`, but nginx listens on port `80`, so every probe gets `connection refused`. Pods that are not ready are kept out of the Service: every endpoint shows `ready=false`, and the Service sends traffic nowhere.

The rollout is stuck for the same reason. A rolling update only removes old Pods once new Pods are ready, and the new Pod never becomes ready.

The liveness probe uses port `80`, so it passes. That is why the container is not restarted this time.

```bash
kubectl apply -f solution/deployment.yaml
kubectl -n lab rollout status deploy/web
```

</details>

### 4. Prove that the fix works

```bash
kubectl -n lab port-forward svc/web 8080:80
# in a second terminal
curl -s localhost:8080/healthz
curl -s localhost:8080/ | grep title
```

## Expected result

```text
$ kubectl -n lab get pods
NAME                   READY   STATUS    RESTARTS   AGE
web-57f9d76589-4dbjz   1/1     Running   0          12s
web-57f9d76589-8v8d8   1/1     Running   0          6s

$ curl -s localhost:8080/healthz
ok

$ curl -s localhost:8080/ | grep title
<title>Welcome to nginx!</title>
```

- Both Pods are `1/1 Running` with no new restarts.
- Every EndpointSlice address shows `ready=true`.
- `kubectl -n lab rollout status deploy/web` prints `successfully rolled out`.

Pod names and IP addresses will be different on your machine.

## Clean up

```bash
kind delete cluster --name broken-deploy-lab
```

## Interview takeaways

- `CrashLoopBackOff` means the container keeps exiting. Read the exit code and `logs --previous` first.
- `Running` but `0/1` means the readiness probe fails. The container works, but it gets no traffic.
- A failing readiness probe can stall a rolling update. That protects users from a bad version.
- Related questions: [kubernetes/08-troubleshooting.md](../../kubernetes/08-troubleshooting.md) and the probe questions in [kubernetes/02-workloads-and-pod-lifecycle.md](../../kubernetes/02-workloads-and-pod-lifecycle.md).
