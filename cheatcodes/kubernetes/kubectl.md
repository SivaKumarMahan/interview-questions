# Kubernetes and `kubectl` Cheatcode

## Context and cluster

```bash
kubectl config get-contexts
kubectl config current-context
kubectl config use-context <context>
kubectl config set-context --current --namespace=<namespace>
kubectl cluster-info
kubectl version
kubectl api-resources
kubectl get nodes -o wide
```

Always confirm context and namespace before a change.

## Namespaces and resources

```bash
kubectl get namespaces
kubectl create namespace <namespace>
kubectl get all -n <namespace>
kubectl get all --all-namespaces
kubectl get deploy,rs,ds,sts,job,cronjob -n <namespace>
kubectl get svc,ingress,endpointslice -n <namespace>
kubectl get pv
kubectl get pvc,storageclass -n <namespace>
kubectl get configmap,secret -n <namespace>
```

## Pods and troubleshooting

```bash
kubectl get pods -A -o wide
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> -c <container>
kubectl logs <pod> -n <namespace> -c <container> --previous
kubectl exec -it <pod> -n <namespace> -c <container> -- /bin/sh
kubectl debug -it <pod> -n <namespace> --image=<approved-debug-image>
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl top pods -A
kubectl top nodes
```

## Deployments and rollout

```bash
kubectl apply --dry-run=server -f app.yaml
kubectl diff -f app.yaml
kubectl apply -f app.yaml
kubectl get deployment <name> -n <namespace>
kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout history deployment/<name> -n <namespace>
kubectl set image deployment/<name> <container>=<image>@sha256:<digest> -n <namespace>
kubectl scale deployment/<name> --replicas=<count> -n <namespace>
kubectl rollout undo deployment/<name> -n <namespace>
```

For production, prefer reviewed GitOps/manifests over imperative image changes.

## ConfigMaps and Secrets

```bash
kubectl create configmap <name> --from-file=<path> -n <namespace> --dry-run=client -o yaml
kubectl create configmap <name> --from-literal=<key>=<value> -n <namespace> --dry-run=client -o yaml
kubectl describe configmap <name> -n <namespace>
kubectl create secret generic <name> --from-file=<path> -n <namespace> --dry-run=client -o yaml
kubectl describe secret <name> -n <namespace>
```

Do not commit generated Secret YAML or print secret data. Prefer external secret management.

## Autoscaling

```bash
kubectl get hpa -A
kubectl describe hpa <name> -n <namespace>
kubectl autoscale deployment <name> --min=2 --max=10 --cpu-percent=70 -n <namespace>
kubectl top pods -n <namespace>
kubectl top nodes
```

Validate Metrics Server, resource requests, scaling limits, stabilization, and node capacity.

## Node maintenance and upgrade inspection

```bash
kubectl version
kubectl get nodes -o wide
kubectl cordon <node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
kubectl uncordon <node>
kubectl get pods -A
```

Drain can disrupt workloads and delete `emptyDir` data. Review PDBs, state, replicas, and replacement capacity first. Use the supported distribution/provider upgrade procedure; do not copy obsolete screenshot versions.

## Quick issue routing

```text
CrashLoopBackOff → describe → current/previous logs → config/probe/resource/dependency
ImagePullBackOff → Events → image/digest → registry auth/network/CA → node disk
Pending → scheduler Events → resources/taints/affinity/quota/PVC/autoscaler
503 → ingress/LB → Service → EndpointSlice → readiness → Pod/dependency
NodeNotReady → Conditions → kubelet/runtime → pressure/CNI/cert/API path
PVC Pending → PVC/PV/StorageClass → CSI Events/logs → topology/quota/identity
```
