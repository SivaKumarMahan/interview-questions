# Kubernetes: Storage and Stateful Apps

> PV/PVC/StorageClass, access modes, zones and topology, StatefulSets, and running stateful services.

## Key Concepts

### Storage

- **PersistentVolume (PV):** Cluster storage resource.
- **PersistentVolumeClaim (PVC):** Namespaced request for storage.
- **StorageClass:** Defines dynamic provisioning behavior.
- **VolumeSnapshot:** Snapshot API object when supported by the CSI driver.

Common access modes:

- `ReadWriteOnce` (RWO): read-write from a single node; multiple Pods on that node may be possible depending on the driver.
- `ReadWriteOncePod` (RWOP): read-write by one Pod.
- `ReadOnlyMany` (ROX): read-only from many nodes.
- `ReadWriteMany` (RWX): read-write from many nodes.

Zone-bound disks can prevent a StatefulSet Pod from mounting after scheduling into another zone. Use topology-aware StorageClasses, appropriate node affinity, and a tested backup/restore strategy.

A single PV is normally bound to one PVC. Cross-namespace failures are more commonly caused by multiple PVs using the same storage backend or by an RWX service failure, not multiple ordinary PVCs binding independently to one PV.

Use no persistent mount for stateless workloads whose local data can disappear when a container or Pod is replaced. Use `emptyDir` only for Pod-lifetime scratch space shared by containers.

Use a PVC for data that must survive Pod replacement; choose the StorageClass, access mode, capacity, topology, expansion, snapshot and backup behavior from application requirements. A mount is not itself a backup, and stateful databases also require application-consistent recovery testing.

### PV, PVC, StorageClass, and Pod flow

A PersistentVolumeClaim is the workload's request for capacity, access mode, and optionally a StorageClass. A PersistentVolume represents storage made available to the cluster.

A StorageClass and CSI driver can dynamically provision a suitable PV, after which the claim binds to it and the Pod mounts the claim:

```text
Pod -> PVC -> bound PV -> CSI-backed storage
```

The PV lifecycle is independent of an individual Pod, but data survival also depends on the reclaim policy, storage service, zone topology, backup, and restore design.

In AKS, Azure Disk commonly fits single-node block storage and Azure Files supports shared file access; choose through workload access and performance requirements rather than assuming all persistent storage behaves the same.

### StatefulSets: features, comparison, and good practices

A StatefulSet manages applications that need stable identity or persistent storage, such as databases, Kafka, Elasticsearch, and ZooKeeper.

#### Main features

- Stable pod names such as `mysql-0`, `mysql-1`, and `mysql-2`
- Predictable DNS names for communication between members
- A separate persistent volume for each pod through `volumeClaimTemplates`
- Ordered creation, scaling, deletion, and rolling updates by default

If `mysql-1` is recreated, it keeps the same identity and reconnects to its own persistent volume. When scaling down, Kubernetes removes the highest-numbered pod first. Its PVC normally remains so that data is not accidentally lost.

#### Deployment compared with StatefulSet

| Feature | Deployment | StatefulSet |
| --- | --- | --- |
| Pod identity | Replaceable, usually with random suffixes | Stable ordinal names |
| Storage | Often ephemeral or shared | Usually one persistent volume per pod |
| Start and removal order | Usually parallel or unrestricted | Ordered by default |
| Common workloads | Web applications and APIs | Databases and clustered data systems |

#### Challenges and good practices

- Cloud disks may be tied to one availability zone. The pod must run on a node that can attach its disk, so plan zones, topology, and application-level replication.
- Scaling down normally leaves PVCs behind. Review unused PVCs and delete them only after confirming that their data is no longer needed.
- Ordered updates can be slow. Plan upgrades around the application's leader, replication, and quorum rules.
- A persistent volume is not a backup. Use CSI volume snapshots and application-level backup tools, and regularly test restores.
- Moving a pod after node failure requires the disk to detach and attach elsewhere, which can delay recovery.
- Use a suitable StorageClass and CSI driver with dynamic provisioning.
- Prefer a mature Kubernetes operator for complex databases when it can safely manage upgrades, backups, failover, and recovery.

### Stateful Workloads and Disaster Recovery

- Stateful failover must cover data replication, quorum, storage topology, fencing, leader election, DNS or traffic switching, and application consistency. StatefulSets alone do not provide database replication.
- For failed PV mounts, inspect PVC/PV/StorageClass, CSI Events and logs, access mode, topology, attachment state, quota, identity, and filesystem health. Do not force-detach or delete state until ownership and backups are verified.
- Disaster recovery begins with business-approved RTO/RPO. Protect manifests, cluster state, persistent data, secrets, certificates, DNS, identity, dependencies, and runbooks in another failure domain, then prove them through restore and failover exercises.
- Multi-region and multi-cloud recovery must control write ownership to avoid split brain and use tested weighted traffic or DNS cutover with an explicit rollback window.

## Interview Questions

### 1. Can you attach a volume to a Deployment? How is it different from a StatefulSet?

**Answer:**

Yes. A Deployment's Pod template can mount ConfigMap, Secret, ephemeral, host, or persistent volumes.

Having multiple replicas reference the same PVC only works if the storage's access mode and backend actually support that kind of concurrent access. A typical block disk with ReadWriteOnce access can't be mounted read-write from multiple nodes at once.

A StatefulSet's `volumeClaimTemplates`, on the other hand, creates a predictable PVC per ordinal — something like `data-db-0` — and that PVC stays tied to the Pod even when it's replaced. That's what gives each member its own disk with a stable identity.

I check the PVC and PV access mode, the StorageClass, the reclaim policy, topology, mount events, CSI logs, and the application's own concurrency assumptions. For stateless applications, I try to keep persistent state outside the Pods entirely.

If you need shared content, use a storage backend that's actually built for multiple writers — don't assume switching to a Deployment changes the underlying storage rules.

### 2. What could cause a StatefulSet Pod to fail when rescheduled to a different availability zone?

**Answer:**

Cloud block volumes like EBS are tied to a single availability zone. The PV carries that zone's node affinity, so a Pod scheduled in a different zone simply can't attach it.

Other causes include a stale VolumeAttachment, a multi-attach lock, not enough capacity in the zone, a CSI failure, node affinity or taints, or lost permissions.

I check the Pod's events, the PVC and PV, the PV's node affinity, the StorageClass binding mode, the VolumeAttachment, CSI controller and node logs, and the node's zone labels. `WaitForFirstConsumer` helps prevent new claims from being provisioned in the wrong zone in the first place.

For data that already exists, I schedule the Pod back in the volume's zone, restore or replicate it to supported storage, or move to a storage architecture actually designed for multi-zone availability. I don't edit the PV's affinity blindly — the physical location of the storage doesn't move just because I changed a field.

### 3. How do PV and PVC behave across zones in EKS or Kubernetes in general?

**Answer:**

A PVC is a namespaced request for storage. A PV is the actual cluster storage object it binds to. Dynamic provisioning uses a StorageClass to create that PV automatically.

With EBS, the disk and its PV are tied to one availability zone, so the Pod has to be scheduled there too. Setting `volumeBindingMode: WaitForFirstConsumer` delays provisioning and binding until the scheduler already knows where the Pod will land.

I only configure allowed topologies when it's actually required, and I spread StatefulSet replicas using topology rules while making sure each volume stays reachable from wherever its Pod lands. When a PVC is stuck Pending, I check the StorageClass and whether there's a default one, capacity, access mode, the CSI provisioner, quota, events, and topology.

If the Pod is Pending after the PVC is already bound, I check the PV's node affinity against the nodes that are actually eligible.

Multi-AZ availability for an application needs replicated application data or storage designed for that — not a single zonal disk that somehow spans zones on its own.

### 4. What happens when a StatefulSet Pod cannot mount its volume after moving to another node?

**Answer:**

The Pod may sit in Pending or ContainerCreating with an error like `FailedAttachVolume`, `Multi-Attach`, `FailedMount`, a timeout, or a filesystem error. I preserve the events and check:

```bash
kubectl describe pod <pod>
kubectl get pvc,pv
kubectl describe pv <pv>
kubectl get volumeattachment
kubectl logs -n kube-system <csi-controller-pod>
```

I compare the node's zone against the PV's zone, confirm the old node actually detached, check CSI health, the cloud disk's state, IAM, the mount path and filesystem, and node capacity.

The fix might be rescheduling to the correct zone, carefully recovering a failed detach, restarting or replacing a CSI or node component once I have evidence it's the cause, or restoring the data.

Once it mounts, I check the filesystem and application data and keep monitoring — I don't just consider the job done because the Pod shows Running.

### 5. If you create a PVC with `ReadWriteOnce` access mode, can multiple Pods on the same node access it simultaneously?

**Answer:**

This depends on the storage provider and how it implements `ReadWriteOnce` (RWO).

Technical details:

- **RWO specification:** The volume can be mounted as read-write by a single node.
- **Implementation varies:** Some storage providers allow multiple Pods on the same node to access RWO volumes.
- **Not guaranteed:** This behavior is not guaranteed by the Kubernetes specification.

Safe approaches:

- Use `ReadWriteMany` (RWX) for multi-Pod access.
- Use StatefulSets for predictable single-Pod-per-volume relationships.
- Test your specific storage provider's behavior.

```yaml
# Safer approach for multi-Pod access
accessModes:
- ReadWriteMany  # Instead of ReadWriteOnce
```

### 6. If a Persistent Volume gets corrupted, can multiple PVCs bound to it cause cascading failures across different namespaces?

**Answer:**

Yes, if multiple PVCs from different namespaces are bound to the same corrupted PV, it can cause cascading failures.

Scenarios for cross-namespace impact:

- **Shared storage backend:** Multiple PVs on the same underlying storage.
- **ReadWriteMany volumes:** Multiple PVCs accessing the same PV.
- **Storage class dependencies:** Shared storage infrastructure.

Cascading failure patterns:

- **Data corruption spreads:** Applications in multiple namespaces fail.
- **Storage backend overload:** Performance decline affects all PVs.
- **Backup system failures:** Corrupt data propagates to backups.

Prevention strategies:

```yaml
# Use namespace-specific storage classes
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: namespace-a-storage
parameters:
  zone: us-west1-a
  type: pd-ssd
```

- Implement proper backup and disaster recovery.
- Use separate storage backends for critical namespaces.
- Monitor storage health across all namespaces.

### 7. How do you debug failed persistent volume (PV) mounts in Kubernetes?

**Answer:** Check PVC status (kubectl describe pvc) → Validate storage class → Check node permissions → Fix provisioner issues.

**Detailed interview approach:**
I inspect the Pod, PVC, PV, StorageClass, CSI controller and node Pods, and their Events. The message usually points to pending provisioning, a topology mismatch, an attach conflict, a permissions issue, quota, a mount failure, or a filesystem error.

I confirm the access mode, requested capacity, zone or node affinity, reclaim policy, secret or IAM access, CSI logs, and the cloud disk's attachment state. For a stateful workload, I protect the data and avoid force-detaching or deleting a PVC until I've confirmed ownership and that backups exist.

I repair whichever layer is broken — binding, CSI, permissions, or storage — remount it through the controller, and validate that the application can actually read, write, and fail over. Regular snapshots, restore tests, CSI monitoring, and sensible topology settings are what prevent this.

### 8. All pods in a StatefulSet are trying to connect to the same storage volume. What's wrong, and how do you fix it?

**Issue:** StatefulSets should have unique PVCs per pod, but they're sharing storage.

**Root cause:**

- Incorrect `volumeClaimTemplates` configuration.
- PVC not created per pod instance.
- Storage class misconfiguration.

**Solution:** Use `volumeClaimTemplates` so each pod gets its own PVC:

```yaml
spec:
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
      storageClassName: fast-ssd
```

Each StatefulSet pod gets its own PVC with the naming pattern `<claim-name>-<pod-name>-<ordinal>` (e.g., `data-mysql-0`, `data-mysql-1`).

### 9. When using a StatefulSet with 3 replicas and you delete replica-1, will replica-2 and replica-3 be renamed to maintain sequential ordering?

**Answer:**

No, Kubernetes does not rename existing StatefulSet Pods. If you delete `myapp-1`, only that specific Pod gets recreated with the same name. `myapp-2` and `myapp-3` retain their original names.

StatefulSet naming behavior:

- Pod names are persistent and ordinal-based (`myapp-0`, `myapp-1`, `myapp-2`).
- When a Pod is deleted, it's recreated with the same name and ordinal.
- Existing Pods are never renamed to fill gaps.
- This maintains stable network identities and persistent storage associations.

This is crucial for applications requiring stable network identities like databases or distributed systems.

### 10. What happens to a StatefulSet pod when its node goes into NotReady state? How is that different from a Deployment pod?

**Answer:**

The common answer — "the pod gets rescheduled" — is wrong for a StatefulSet, and it exposes someone who has never run stateful workloads in production.

When a node loses network connectivity, Kubernetes does not immediately know whether the node is dead or just temporarily unreachable, so it waits. By default it waits about five minutes before marking pods on that node as `Terminating`.

From there, StatefulSets and Deployments behave completely differently:

- **Deployment pod:** After the timeout, Kubernetes reschedules the pod on another node. The pod gets a new identity, a new IP, and life continues.
- **StatefulSet pod:** Kubernetes will **not** reschedule it automatically. The pod stays in `Terminating` indefinitely.

The reason is StatefulSet's core guarantee: no two pods with the same identity run at the same time. Suppose the node is not actually dead — it just lost network for a while.

If Kubernetes rescheduled `postgres-0` onto another node, you would now have two `postgres-0` instances both writing to the same data. That is a split-brain scenario, and it corrupts your database.

So Kubernetes deliberately does nothing and waits for a human to intervene.

In production this means you have to make a decision. Is the node actually dead? If yes, you force delete the pod:

```bash
kubectl delete pod postgres-0 --force --grace-period=0
```

If no, you wait for the node to come back. This is why stateful workloads on Kubernetes are complex — the safety guarantee that protects you from corruption is the same thing that keeps your pod stuck when a node dies.

I hit exactly this in a banking environment. A node went `NotReady` at 11pm and the on-call engineer, unaware of this behavior, waited for an automatic recovery that was never going to come.

We lost two hours before someone force deleted the pod. That production context is what the interviewer is really looking for.

### 11. How do you manage stateful applications in Kubernetes?

**Answer:** Use StatefulSets → PersistentVolumeClaims → Ensure proper storage class → Backup with Velero.

**Detailed interview approach:**
I inspect the Pod, PVC, PV, StorageClass, CSI controller and node Pods, and their Events. The message usually points to pending provisioning, a topology mismatch, an attach conflict, a permissions issue, quota, a mount failure, or a filesystem error.

I confirm the access mode, requested capacity, zone or node affinity, reclaim policy, secret or IAM access, CSI logs, and the cloud disk's attachment state. For a stateful workload, I protect the data and avoid force-detaching or deleting a PVC until I've confirmed ownership and that backups exist.

I repair whichever layer is broken — binding, CSI, permissions, or storage — remount it through the controller, and validate that the application can actually read, write, and fail over. Regular snapshots, restore tests, CSI monitoring, and sensible topology settings are what prevent this.

### 12. How do you handle stateful service failover in Kubernetes across zones/regions?

**Answer:** Use StatefulSets with appropriate storage classes, enable cross-zone replication for the datastore (e.g., multi-zone DB clusters), design DNS failover and leader election, and test failover procedures.

Mini-case: We configured a multi-zone PostgreSQL cluster with synchronous replicas; during a zone outage, automated leader election and DNS failover restored write availability within minutes.
**Detailed interview approach:**
I inspect the Pod, PVC, PV, StorageClass, CSI controller and node Pods, and their Events. The message usually points to pending provisioning, a topology mismatch, an attach conflict, a permissions issue, quota, a mount failure, or a filesystem error.

I confirm the access mode, requested capacity, zone or node affinity, reclaim policy, secret or IAM access, CSI logs, and the cloud disk's attachment state. For a stateful workload, I protect the data and avoid force-detaching or deleting a PVC until I've confirmed ownership and that backups exist.

I repair whichever layer is broken — binding, CSI, permissions, or storage — remount it through the controller, and validate that the application can actually read, write, and fail over. Regular snapshots, restore tests, CSI monitoring, and sensible topology settings are what prevent this.

### 13. How would you migrate a stateful application to Kubernetes with minimal downtime?

**Answer:**

First I document data ownership, consistency requirements, storage IOPS, dependencies, DNS, backups, and what RTO and RPO are actually acceptable. I only use a StatefulSet when stable identity or ordered behavior is actually required — a managed external database can be the safer choice if the team isn't set up to operate a distributed datastore inside Kubernetes.

The target environment needs the right storage topology, anti-affinity, disruption budgets, probes, resource requests, and a tested backup and restore process.

I provision the target in parallel, restore a recent backup into it, and use database-native replication or change-data capture to keep it in sync with ongoing writes. I validate schema compatibility, transactions, performance, failover, monitoring, and restore before actually cutting over.

At cutover, I pause writes if consistency requires it, apply the final delta, switch the connection or shift weighted traffic over, and watch errors, latency, replication lag, and data correctness closely.

The old environment stays read-only during an agreed rollback window. Rolling back is only safe once I understand who owns the writes and how the data would reconcile back.

Once things are stable, I stop the temporary replication, rotate the migration credentials, verify another restore still works, and record the actual downtime and recovery behavior for next time.

### 14. Challenges with StatefulSets & persistent storage *(asked in interview round)*

StatefulSets give pods a stable network identity (`pod-0`, `pod-1`), ordered deployment and scaling, and stable per-pod storage through `volumeClaimTemplates`.

The main challenges:
- Storage is tied to a zone. An EBS volume lives in one availability zone, so its pod is pinned there too. Plan topology spread and multi-AZ replication at the application layer.
- Scaling down does not delete PVCs — this is by design, to protect data. Orphaned volumes still cost money, so clean them up deliberately once you confirm the data isn't needed.
- Ordered operations make rollouts slower, and upgrades must respect the application's quorum rules, as with databases.
- Backups and data migration are your responsibility. Use CSI volume snapshots and application-level backups.
- Rescheduling a pod to a new node requires the CSI driver to detach and reattach the volume, which can be slow.

Best practice: use CSI drivers with dynamic provisioning and a proper StorageClass, run stateful workloads through mature operators where possible, and back up regularly.
