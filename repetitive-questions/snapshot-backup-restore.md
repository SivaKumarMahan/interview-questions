# Repetitive Interview Questions

## What is a snapshot, how do you take a backup before deployments, and how do you restore it?

**Interviewer:** What backup do you take before a Production deployment, and how do you restore it if the deployment fails?

**Candidate:**

A snapshot is a point-in-time copy of a disk or volume. A backup is a protected copy used for longer-term recovery. I choose the protection based on what the deployment changes.

I do not take a database or disk snapshot for every stateless application deployment. If only the container image changes and all important data is stored in managed services, a versioned image and Helm history may be enough for rollback.

## Decide what needs protection

Before deployment, I ask:

- Is the database changing?
- Is a persistent volume changing?
- Is infrastructure being replaced?
- How much data loss is acceptable?
- How quickly must the service be restored?

These answers decide whether I need an application rollback, database backup, disk snapshot, or full disaster-recovery process.

## Stateless AKS application

For a normal stateless AKS application, I keep:

- The previous container image.
- Helm release history.
- Kubernetes and Helm configuration in Git.
- Terraform or Bicep code.

Check Helm history:

```bash
helm history <release-name> -n <namespace>
```

Restore a previous application revision:

```bash
helm rollback <release-name> <revision> -n <namespace>
```

This is usually faster than restoring storage when no stored data changed.

## Kubernetes persistent-volume snapshot

If the deployment changes important data on a persistent volume, I can create a `VolumeSnapshot` when the storage driver supports it.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-before-release
  namespace: production
spec:
  volumeSnapshotClassName: <volume-snapshot-class>
  source:
    persistentVolumeClaimName: application-data
```

Check the snapshot:

```bash
kubectl get volumesnapshot -n production
kubectl describe volumesnapshot data-before-release -n production
```

The snapshot should show `readyToUse: true` before I depend on it.

### Restore the volume

Create a new claim from the snapshot:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-application-data
  namespace: production
spec:
  storageClassName: managed-csi
  dataSource:
    name: data-before-release
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

I normally restore to a new volume, validate the data, and then update the workload. This is safer than overwriting the current volume immediately.

## Azure managed-disk snapshot

For an Azure managed disk, I can create a snapshot:

```bash
az snapshot create \
  --resource-group <resource-group> \
  --name <snapshot-name> \
  --source <disk-resource-id>
```

To recover, I create a new disk from the snapshot and attach or mount it through the approved process.

A disk snapshot may contain data that was still being written. For a database, I prefer the database's own backup method because it understands transactions.

## Azure Database for PostgreSQL

Azure Database for PostgreSQL provides automatic backups and point-in-time restore within the configured retention period.

Before a risky database change, I:

- Confirm that backups are healthy.
- Confirm the retention period.
- Record the deployment time.
- Test the restore process in a non-Production environment.
- Use a backward-compatible database change where possible.

Point-in-time restore normally creates a new database server. I validate the restored data before moving application traffic to it.

## Virtual machine backup

For a VM-based application, I use Azure Backup when full-machine recovery is required. A disk snapshot can be useful before a small disk-level change, but it is not a replacement for a managed backup policy.

Before taking a snapshot, I make the application data consistent when required—for example, by stopping writes or using the application's supported backup process.

## Terraform state and infrastructure

I protect Terraform state in a private Blob container with versioning and recovery protection.

Before an infrastructure change:

```bash
terraform plan
```

I review whether any resource will be deleted or replaced. To recover, I restore the correct state version only when necessary and make sure it matches the real Azure resources.

I do not edit Terraform state manually during an incident unless there is a reviewed recovery plan.

## Key Vault and configuration

For Key Vault, I enable soft delete and purge protection. For application configuration, I keep approved versions in Git.

Secrets are rotated or restored through Key Vault; they are not copied into source control as a backup.

## Pre-deployment checklist

Before a high-risk deployment, I confirm:

- The previous image and Helm revision are available.
- Required database backups are healthy.
- Required snapshots are complete.
- Configuration is version-controlled.
- The restore steps and owner are known.
- The recovery process has been tested.

## Restore process

If deployment causes a problem:

1. Stop or pause the deployment.
2. Confirm what changed.
3. Roll back the application if data is still valid.
4. Restore data only if the data itself was changed or damaged.
5. Restore into a separate resource where possible.
6. Validate the data and application.
7. Move traffic back safely.
8. Monitor errors and user requests.

## Restore verification

I do not consider a restore successful only because the command completed. I verify:

- Pods are Running and Ready.
- The application can read and write expected data.
- Record counts or important business data are correct.
- External application requests work.
- Error rate and response time are normal.

## Example

Suppose a release includes a database change and is deployed at 10:00. At 10:15, users report incorrect data.

I stop the rollout, check whether the application can be rolled back without restoring the database, and preserve current evidence. If a data restore is required, I restore PostgreSQL to a new server from a time just before 10:00, validate the records, and switch the application only after approval.

## In short

I first identify what the deployment changes. For a stateless application, I normally use the previous image and Helm revision.

For persistent volumes, I use a tested volume or disk snapshot. For databases, I use the database's supported backup and point-in-time restore.

After any restore, I validate both the data and the complete user request.
