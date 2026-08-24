# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Kubernetes

### 3.1 How confident are you in Kubernetes & Docker? (rating question)

Give an honest self-rating and back it up with real work. For example: *"8/10 — I run production EKS clusters: writing manifests and Helm charts, HPA/VPA autoscaling, RBAC, network policies, and troubleshooting incidents like CrashLoopBackOff, pending pods, and node pressure."* Avoid claiming a perfect 10/10. A number backed by concrete examples is always more convincing.

### 3.2 How do you stop / delete a pod?
```bash
kubectl delete pod <name>            # deletes; a controller (Deployment/RS) recreates it
kubectl scale deploy <name> --replicas=0   # actually stop the workload
kubectl delete deploy <name>         # remove workload entirely
```
If a Deployment manages the pod, deleting the pod alone just triggers a replacement. To actually stop the workload, scale the Deployment to zero replicas or delete the Deployment itself.

### 3.3 How do you replicate a pod?

Don't manage pods directly. Use a Deployment (or a ReplicaSet or StatefulSet) and set the replica count:
```bash
kubectl scale deployment <name> --replicas=3
# or in the manifest:  spec.replicas: 3
```
The ReplicaSet controller keeps the pod count at whatever you set. For automatic scaling, use an HPA (see §3.6).

### 3.4 Command to get logs in Kubernetes
```bash
kubectl logs <pod>                      # current logs
kubectl logs <pod> -c <container>       # specific container in multi-container pod
kubectl logs -f <pod>                   # follow (tail)
kubectl logs <pod> --previous           # logs from previous crashed container
kubectl logs -l app=web --tail=100      # by label selector
```
Pod logs disappear once the pod is deleted, so for logs you need to keep, send them to a centralized logging system (see §8.4).

### 3.5 A pod is not responding / stuck in Pending — troubleshooting approach

Start with this general flow:
```bash
kubectl get pods -o wide
kubectl describe pod <name>     # EVENTS section is the key signal
kubectl logs <name> [--previous]
kubectl get events --sort-by=.lastTimestamp
```
A pod stuck in **Pending** almost always means the scheduler can't place it. Read the events to see why:
- **Insufficient CPU or memory** — no node has room. Add nodes, adjust the requests, or let the cluster autoscaler add capacity.
- **Unschedulable due to taints, affinity, or a nodeSelector** — no node matches the pod's requirements.
- **PVC unbound** — there's no matching PV or StorageClass, or a zone mismatch.
- **ImagePullBackOff** (a different phase) — the image name or tag is wrong, or the registry credentials are missing.

If the pod is running but not responding, or keeps restarting:
- `CrashLoopBackOff` means the app crashes on startup. Check `logs --previous`, the config, missing env vars or secrets, and any failing dependency.
- Failing liveness or readiness probes can restart a healthy app or keep it out of the Service. Check the probe's path, port, and timeout.
- `OOMKilled` (shown by `describe`) means the container ran out of memory. Raise the memory limit or fix the leak.

### 3.6 A pod is under heavy load — keep it healthy before it dies (auto-scaling)

- Use the Horizontal Pod Autoscaler (HPA) to add or remove replicas based on CPU, memory, or custom/external metrics — for example requests-per-second through the Prometheus Adapter, or KEDA for event-driven scaling.
  ```bash
  kubectl autoscale deployment web --cpu-percent=70 --min=3 --max=20
  ```
- Set proper resource requests and limits so the scheduler and HPA make good decisions.
- Use the Cluster Autoscaler or Karpenter to add nodes when pods can't be scheduled.
- Use readiness probes together with a PodDisruptionBudget to keep enough healthy replicas during scaling and rollouts.
- Use the VPA to right-size single-instance workloads, and add caching or queues to reduce load.

### 3.7 Challenges with StatefulSets & persistent storage

StatefulSets give pods a stable network identity (`pod-0`, `pod-1`), ordered deployment and scaling, and stable per-pod storage through `volumeClaimTemplates`.

The main challenges:
- Storage is tied to a zone. An EBS volume lives in one availability zone, so its pod is pinned there too. Plan topology spread and multi-AZ replication at the application layer.
- Scaling down does not delete PVCs — this is by design, to protect data. Orphaned volumes still cost money, so clean them up deliberately once you confirm the data isn't needed.
- Ordered operations make rollouts slower, and upgrades must respect the application's quorum rules, as with databases.
- Backups and data migration are your responsibility. Use CSI volume snapshots and application-level backups.
- Rescheduling a pod to a new node requires the CSI driver to detach and reattach the volume, which can be slow.

Best practice: use CSI drivers with dynamic provisioning and a proper StorageClass, run stateful workloads through mature operators where possible, and back up regularly.

### 3.8 Automated zero-downtime EKS upgrades

1. Upgrade the control plane first, one minor version at a time, using `eks update-cluster-version`. AWS manages this part.
2. Upgrade the managed add-ons (VPC CNI, CoreDNS, kube-proxy) to versions compatible with the new control plane.
3. Upgrade the node groups. Use managed node groups or Karpenter to create new nodes on the new version, then cordon and drain the old nodes so pods reschedule gracefully. Managed node groups handle this rolling update for you.
4. Protect availability during the drains with PodDisruptionBudgets, multiple replicas, readiness probes, and topology spread.
5. Validate compatibility beforehand: check for deprecated APIs with tools like `kubent` or `pluto`, test the upgrade in a non-production cluster, and automate the whole flow with IaC (Terraform or eksctl) plus a pipeline.

---
