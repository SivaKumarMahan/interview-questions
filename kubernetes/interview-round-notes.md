# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Kubernetes

### 3.1 How confident are you in Kubernetes & Docker? (rating question)

Give an honest self-rating with evidence, e.g. *"8/10 — I run production EKS clusters: writing manifests/Helm charts, HPA/VPA autoscaling, RBAC, network policies, and I've handled incident troubleshooting (CrashLoopBackOff, pending pods, node pressure)."* Avoid claiming 10/10; back the number with concrete work.

### 3.2 How do you stop / delete a pod?
```bash
kubectl delete pod <name>            # deletes; a controller (Deployment/RS) recreates it
kubectl scale deploy <name> --replicas=0   # actually stop the workload
kubectl delete deploy <name>         # remove workload entirely
```
Deleting a bare pod managed by a Deployment just triggers a rescheduled replacement — to truly stop it, scale the controller to 0 or delete the controller.

### 3.3 How do you replicate a pod?

Don't manage pods directly — use a **Deployment** (or ReplicaSet/StatefulSet) and set replicas:
```bash
kubectl scale deployment <name> --replicas=3
# or in the manifest:  spec.replicas: 3
```
The ReplicaSet controller maintains the desired count. For auto-scaling use an **HPA** (§3.6).

### 3.4 Command to get logs in Kubernetes
```bash
kubectl logs <pod>                      # current logs
kubectl logs <pod> -c <container>       # specific container in multi-container pod
kubectl logs -f <pod>                   # follow (tail)
kubectl logs <pod> --previous           # logs from previous crashed container
kubectl logs -l app=web --tail=100      # by label selector
```
For aggregated, persistent logs use centralized logging (§8.4), since pod logs vanish when the pod is deleted.

### 3.5 A pod is not responding / stuck in Pending — troubleshooting approach

General flow:
```bash
kubectl get pods -o wide
kubectl describe pod <name>     # EVENTS section is the key signal
kubectl logs <name> [--previous]
kubectl get events --sort-by=.lastTimestamp
```
**Pending** almost always means it can't be scheduled — read the events:
- **Insufficient CPU/memory** → no node has room. Add nodes / adjust requests / cluster-autoscaler.
- **Unschedulable due to taints/affinity/nodeSelector** → no node matches.
- **PVC unbound** → no matching PV / StorageClass, or zone mismatch.
- **ImagePullBackOff** (this is a different phase) → bad image name/tag or missing registry credentials.

**Not responding / restarting:**
- `CrashLoopBackOff` → app crashes on start; check `logs --previous`, config, missing env/secrets, failing dependency.
- **Failing probes** → liveness/readiness misconfigured (wrong path/port, timeout too tight) restarting a healthy app or keeping it out of the Service.
- **OOMKilled** (`describe` shows reason) → raise memory limit or fix the leak.

### 3.6 A pod is under heavy load — keep it healthy before it dies (auto-scaling)

- **Horizontal Pod Autoscaler (HPA):** scale replicas on CPU/memory or custom/external metrics (e.g. requests-per-second via Prometheus Adapter, or KEDA for event-driven).
  ```bash
  kubectl autoscale deployment web --cpu-percent=70 --min=3 --max=20
  ```
- **Set proper resource requests/limits** so the scheduler and HPA behave predictably.
- **Cluster Autoscaler / Karpenter** to add nodes when pods can't be scheduled.
- **Readiness probes + PodDisruptionBudget** to keep enough healthy replicas during scaling/rollouts.
- **VPA** for right-sizing single-instance workloads. Add caching/queues to shed load.

### 3.7 Challenges with StatefulSets & persistent storage

- **StatefulSets** give stable network identity (`pod-0`, `pod-1`), ordered deployment/scaling, and stable per-pod storage via `volumeClaimTemplates`.
- **Challenges:**
  - **Storage is zone-bound:** an EBS volume lives in one AZ, so the pod is pinned to that AZ — plan topology spread and multi-AZ replication at the app layer.
  - **Scaling down doesn't delete PVCs** (by design, to protect data) — orphaned volumes cost money; clean up deliberately.
  - **Ordered operations** make rollouts slower; upgrades must respect quorum (e.g. databases).
  - **Backups & data migration** are your responsibility — use volume snapshots (CSI snapshots) and app-level backups.
  - **Rescheduling** requires the CSI driver to detach/attach; can be slow.
- **Best practice:** use CSI drivers with dynamic provisioning + a proper StorageClass, run stateful workloads via battle-tested operators where possible, and back up regularly.

### 3.8 Automated zero-downtime EKS upgrades

1. **Upgrade the control plane** first (`eks update-cluster-version`) — AWS manages it; one minor version at a time.
2. **Upgrade managed add-ons** (VPC CNI, CoreDNS, kube-proxy) to compatible versions.
3. **Node groups:** use **managed node groups** or **Karpenter**; create new nodes on the new version, then **cordon & drain** old nodes so pods reschedule gracefully. Managed node groups do this rolling update for you.
4. **Protect availability:** PodDisruptionBudgets, multiple replicas, readiness probes, and topology spread ensure capacity during drains.
5. **Validate compatibility** beforehand: check deprecated APIs (`kubent`/`pluto`), test in a non-prod cluster, and automate the whole flow via IaC (Terraform/eksctl) + a pipeline.

---
