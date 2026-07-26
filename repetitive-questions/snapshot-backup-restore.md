# Repetitive Interview Questions

## What is a snapshot, how do you take a backup before deployments, and how do you restore it if an issue occurs?

### Detailed answer

A **snapshot** is a point-in-time copy of storage, such as an Azure managed disk or a Kubernetes persistent volume. It captures the blocks and data state visible at that moment and can be used to create a new disk or volume.

A snapshot is useful for fast operational recovery, but it is not automatically a complete backup or disaster-recovery solution. A backup normally adds scheduled protection, retention policy, recovery-point management, monitoring, access controls, independent storage or vault protection, and documented restore workflows.

| Snapshot | Managed backup |
| --- | --- |
| Point-in-time storage copy | Policy-driven protection and recovery service |
| Usually fast to create and restore | Designed for longer retention and managed recovery |
| Can be crash-consistent unless the application is quiesced | Can support application-consistent recovery for supported workloads |
| Often remains in the same subscription/region or storage failure domain | Can provide vault and redundancy options based on service and policy |
| Protects a disk/volume, not necessarily the complete application | Can protect VM, AKS resources, persistent data or database recovery points |
| Retention and cleanup may be manual | Retention and lifecycle are policy controlled |
| Does not prove that restoration works | Still requires regular restore testing |

My pre-deployment approach is **risk-based**. I do not take a snapshot before every stateless application release. For a normal AKS deployment, rollback uses the previous immutable ACR image digest and Helm revision. I take or verify data backups before changes that could affect persistent state, such as database migrations, disk changes, VM upgrades, storage-driver changes, destructive scripts or infrastructure replacements.

### 1. Start with RTO, RPO and the change risk

Before deciding what to back up, I identify:

- **RPO:** How much data loss the business can accept.
- **RTO:** How quickly the service must be restored.
- Which application and data components the change can affect.
- Whether the change is reversible without restoring data.
- Whether old and new application versions remain data-compatible.
- The last successful backup and last tested restore.
- Backup retention, region, encryption, immutability and access requirements.
- The restore owner, approver and exact recovery runbook.

The backup method follows the component:

| Deployment/change | Protection used before deployment |
| --- | --- |
| Stateless Java application on AKS | Previous ACR digest, Helm revision and versioned configuration |
| AKS application with PVC data | Azure Backup for AKS or CSI `VolumeSnapshot`, with application-consistency handling |
| Azure VM application or OS change | Azure VM Backup on-demand recovery point; managed disk snapshot only for a justified disk-level use case |
| Azure managed data disk | Azure Disk Backup or a controlled incremental snapshot |
| Azure Database for PostgreSQL migration | Verify native backup/PITR window; take an on-demand backup where supported or a logical backup when required |
| Terraform/Bicep infrastructure change | Git history, reviewed plan and backend state protection; workload-specific backups for data |
| Key Vault secret/certificate change | Versioning, soft delete, purge protection and rotation/runbook—not plaintext export to Git |

### 2. Normal stateless AKS deployment

For a stateless AKS service, the application image is immutable and persistent data lives in an external managed database or approved storage service. Before deployment, the pipeline records:

```text
current Production Git commit
current ACR image digest
current Helm revision
current configuration version
new release digest
database migration compatibility
```

If the new application version fails, I restore the previous Helm revision and ACR digest:

```bash
helm history <release> -n <namespace>
helm rollback <release> <known-good-revision> \
  -n <namespace> \
  --wait \
  --timeout <approved-timeout>
```

No disk snapshot is required for this application-only rollback because the container filesystem is disposable. Taking snapshots of stateless Pods would add cost and complexity without protecting the real source of state.

### 3. AKS resources and persistent-volume backup

For stateful AKS workloads, I prefer a managed Kubernetes-aware backup rather than manually snapshotting the underlying Azure disk without understanding the application.

Azure Backup for AKS can protect selected namespaces, Kubernetes resources and supported CSI-backed persistent volumes through a Backup vault and the AKS backup extension. The backup policy defines schedule and retention, and an on-demand backup can be initiated before a high-risk change.

Before relying on the backup, I verify:

- The correct namespaces, labels and resource types are included.
- PVCs and their supported storage types are included.
- Backup jobs and recovery points show success.
- The vault, blob storage and snapshot resource group are healthy.
- Managed identities and RBAC permit backup and restore.
- Required cluster-scoped resources, Secrets and CRDs are included according to policy.
- The backup has the required operational/vault retention and regional protection.
- A restore into a test namespace or cluster has been proven.

For a database running inside Kubernetes, a raw storage snapshot can be crash-consistent but not application-consistent. I use supported pre/post backup hooks or the database-native backup process to flush, freeze or quiesce writes safely. For distributed databases with several volumes, all required volumes and transaction state must form a consistent recovery point.

### 4. Kubernetes `VolumeSnapshot`

When the CSI driver and platform support it, a `VolumeSnapshot` requests a point-in-time snapshot of a PVC:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: orders-data-predeploy-<change-id>
  namespace: orders
spec:
  volumeSnapshotClassName: <approved-snapshot-class>
  source:
    persistentVolumeClaimName: orders-data
```

I verify that the snapshot is ready:

```bash
kubectl get volumesnapshot -n orders
kubectl describe volumesnapshot \
  orders-data-predeploy-<change-id> \
  -n orders
```

A successful Kubernetes object creation alone is not enough. I confirm `readyToUse`, the bound `VolumeSnapshotContent`, the storage-provider snapshot and the retention/deletion policy.

To restore, I normally create a **new PVC** from the snapshot:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: orders-data-restored
  namespace: orders
spec:
  storageClassName: <approved-storage-class>
  dataSource:
    name: orders-data-predeploy-<change-id>
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: <required-capacity>
```

I mount the restored PVC to an isolated validation Pod or restored workload first. After checking filesystem/database consistency and application behavior, I perform a controlled cutover. I do not delete or overwrite the original PVC until recovery is confirmed and the retention policy permits it.

### 5. Azure VM backup before deployment

For a Production Azure VM, Azure Backup is preferred over an ad hoc OS-disk snapshot for most recovery scenarios. The VM is protected through a Recovery Services vault and a policy.

Before a high-risk application, agent, OS or configuration change, I:

1. Confirm that the VM is protected and recent scheduled backups succeeded.
2. Check which OS and data disks are included.
3. Verify retention, vault redundancy and access controls.
4. Trigger an on-demand backup/recovery point when the change policy requires one.
5. Monitor the backup job until it completes successfully.
6. Record the recovery point, timestamp and retention in the change ticket.
7. Confirm the restore procedure and estimated recovery time.

I do not start the deployment merely because the backup job was submitted. The required recovery point must be complete and visible.

Azure Backup restoration can:

- Create a new VM from a recovery point.
- Restore the VM disks for controlled reconstruction.
- Replace supported existing disks.
- Recover selected files in supported scenarios.

My safest normal approach is to restore to an alternate VM or restore disks separately, validate the application and data, and then perform a controlled traffic/DNS/load-balancer cutover. An in-place replacement has a larger blast radius and is used only through an approved runbook.

### 6. Azure managed disk snapshot

A managed disk snapshot is appropriate for a specific disk-level recovery or troubleshooting requirement. Where application consistency matters, I stop or quiesce writes according to the application runbook before taking it.

An example Azure CLI command is:

```bash
az snapshot create \
  --resource-group <resource-group> \
  --name <snapshot-name> \
  --source <managed-disk-resource-id> \
  --incremental true
```

I tag the snapshot with the application, environment, source disk, change/reference, creation time, owner and expiry. Retention cleanup is automated and never based only on a name.

To restore, I create a **new managed disk** from the snapshot:

```bash
az disk create \
  --resource-group <resource-group> \
  --name <restored-disk-name> \
  --source <snapshot-resource-id>
```

Then I attach it as a data disk to a validation VM or use the approved process to create/recover the VM. I validate:

- Filesystem consistency.
- Encryption and disk settings.
- File ownership and permissions.
- Application or database consistency.
- Performance after the snapshot-copy process.
- VM identity, network, extensions, monitoring and backup protection.

A disk snapshot does not capture every external dependency, NIC rule, managed identity assignment, DNS record, Key Vault permission or application transaction. The infrastructure configuration still comes from Terraform/Bicep and the complete restore runbook.

### 7. Azure Database for PostgreSQL backup

Azure Database for PostgreSQL Flexible Server automatically creates backups and transaction-log recovery data within the configured retention period. Point-in-time restore creates a **new server** rather than overwriting the source server.

Before a risky schema or data deployment, I:

1. Verify the configured retention period meets the RPO.
2. Confirm the earliest and latest restore points.
3. Review the most recent successful backup and backup alerts.
4. Create an on-demand backup where the selected server/storage tier supports it and policy requires it.
5. Use `pg_dump` or another approved logical backup when object-level portability or independent validation is required.
6. Record the UTC timestamp immediately before the change.
7. Confirm private networking, DNS, firewall, identity and cutover steps for a restored server.
8. Prefer backward-compatible expand/migrate/contract schema changes so normal application rollback does not require database restore.

A restore to a known UTC time can be initiated with:

```bash
az postgres flexible-server restore \
  --resource-group <target-resource-group> \
  --name <new-restored-server-name> \
  --source-server <source-server-name-or-resource-id> \
  --restore-time <utc-iso8601-time>
```

The restoration workflow is:

```text
choose a point before the bad change
-> restore as a new PostgreSQL server
-> configure/validate private networking and DNS
-> validate users, extensions, parameters and data
-> run integrity and application tests
-> decide full cutover or object-level recovery
-> update connection routing/secrets through the controlled process
-> monitor
```

If only a table or set of rows was damaged, it can be safer to restore a new server, validate it, extract the required object/data and repair the current server through a database-approved process. A full point-in-time cutover can discard valid transactions created after the restore time, so it requires business and data-owner approval.

### 8. Terraform state and infrastructure recovery

Terraform state is not a backup of the Azure resources. It maps Terraform resource addresses to remote object IDs and attributes. Restoring an old state file does not restore a deleted VM, disk, database or AKS workload.

I protect the remote Azure Storage backend with:

- Encryption.
- Least-privilege RBAC.
- Network restrictions/private access where required.
- Blob versioning and soft delete.
- Locking/lease behavior.
- Diagnostic and access logging.
- Retention and recovery procedure.

Before infrastructure deployment, the pipeline publishes and reviews a saved plan. If an infrastructure change fails:

1. Inspect the actual Azure resources and current state.
2. Revert or correct the Terraform/Bicep code in Git.
3. Run a fresh reviewed plan.
4. Apply the corrective change through the protected pipeline.
5. Use workload backups to recover data where required.

I restore a previous state version only for a genuine state-loss/corruption incident and only through the Terraform state-recovery runbook. Blindly replacing the current state can create duplicate resources, orphan objects or destructive plans.

### 9. Configuration, Helm and Git recovery

The backup for desired application configuration is version control plus release metadata:

- Git commit and protected release tag.
- Helm chart version and release history.
- Environment-specific reviewed values.
- ACR image digest.
- Pipeline artifacts and test/scan evidence.
- Terraform/Bicep source and plan evidence.

If a configuration deployment fails, I revert the configuration in Git, run validation and redeploy. Emergency manual corrections are recorded and reconciled into Git immediately so that the next deployment does not reintroduce the issue.

Git history is not a backup of runtime database or volume data, while a storage snapshot is not a backup of the desired configuration. Both layers are required.

### 10. Azure Key Vault recovery

Key Vault secrets, keys and certificates use versioning, soft delete, purge protection, RBAC and rotation policies. Applications refer to the approved secret/certificate version through managed identity.

For an incorrect but uncompromised secret version, I can reactivate or reference a known valid version according to policy. If a secret is exposed or suspected to be compromised, I revoke and rotate it rather than restoring the compromised value.

I never back up Key Vault values by printing them into a pipeline log, plaintext file, Helm values or Git. Recovery must preserve both the value and the authorization/configuration required for consumers to retrieve it.

### 11. Pre-deployment backup checklist

Before a high-risk deployment, I verify:

- [ ] The change and affected stateful components are identified.
- [ ] RPO and RTO are approved.
- [ ] Latest scheduled backup succeeded.
- [ ] Required on-demand recovery point completed.
- [ ] Snapshot/backup timestamp is before the change.
- [ ] Application-consistent hooks or quiescing were used where required.
- [ ] Backup retention will outlive the rollback window.
- [ ] Backup is encrypted and protected through least privilege.
- [ ] Restore permissions, networking, DNS, identity and capacity are available.
- [ ] Previous application digest, Helm revision and configuration are recorded.
- [ ] Database migration is backward compatible or has an approved recovery plan.
- [ ] Restore was tested recently in an isolated environment.
- [ ] Restore owner, approver, commands and verification tests are documented.

The CI/CD pipeline can enforce these checks by requiring a successful backup job/recovery-point identifier before allowing a destructive deployment stage to continue.

### 12. Restore process when an issue occurs

If the deployment causes a problem, I follow this sequence:

1. **Stop the change:** Pause rollout, block further promotion and preserve evidence.
2. **Assess impact:** Determine whether the fault is application, configuration, storage, database or infrastructure.
3. **Prefer the least destructive recovery:** Roll back the application/configuration when data is still correct.
4. **Select the recovery point:** Choose the last known-good point before corruption, using UTC and business confirmation.
5. **Restore separately:** Create a new PVC, disk, VM or PostgreSQL server whenever possible.
6. **Rebuild dependencies:** Apply required network, DNS, identity, RBAC, certificates, extensions and monitoring configuration from code.
7. **Validate:** Check integrity, security, performance and the real application transaction.
8. **Cut over:** Shift traffic or update the approved endpoint/secret only after validation.
9. **Monitor:** Observe errors, latency, resources, database health and business transactions.
10. **Retain the original:** Do not delete the original or recovery point until recovery is confirmed and retention policy permits it.
11. **Document:** Record actual RPO/RTO, data loss if any, commands, approvals and preventive actions.

### 13. Restore verification

I do not call the recovery successful merely because Azure reports that the restore job completed. I verify:

- The restored point and data timestamp are correct.
- Filesystem/database consistency checks pass.
- Expected schemas, rows, files and objects exist.
- Encryption and permissions are correct.
- Managed identity and Key Vault access work.
- Private DNS, NSGs, private endpoints and routes work.
- Application Pods or VMs start without errors.
- Smoke, API and business transaction tests pass.
- Monitoring, alerts and backup protection are enabled on the restored resource.
- Performance is acceptable under representative load.

After cutover, I retain an observation period and have a fall-back plan if the restored environment also fails.

### 14. Common mistakes I avoid

- Taking a disk snapshot and calling it a complete application backup.
- Taking snapshots before every stateless deployment without a recovery need.
- Assuming a successful backup means the restore will work.
- Snapshotting a live database without application-consistency handling.
- Restoring directly over Production before isolated validation.
- Restoring an old Terraform state to recover actual infrastructure.
- Forgetting networking, identity, RBAC, DNS and certificates after a restore.
- Keeping backups in the same failure domain without evaluating disaster recovery.
- Retaining snapshots forever without ownership or lifecycle policy.
- Restoring a compromised secret.
- Performing a full database PITR when only a small object needs recovery.
- Starting a deployment before the on-demand backup job completes.

### How this protects Production

This approach protects Production because:

- Stateless releases use fast artifact rollback without unnecessary storage restoration.
- Stateful changes have a recovery point matched to the data technology.
- Snapshots are application-consistent where the workload requires it.
- Restores create separate resources for validation before cutover.
- Database PITR and object-level recovery minimize accidental data loss.
- Infrastructure and runtime data are protected through different mechanisms.
- Backup success and restore testing are monitored and auditable.
- RPO, RTO, retention and ownership are agreed before the incident.

### Concise interview answer

A snapshot is a point-in-time copy of a disk or persistent volume. It is useful for quick operational recovery, but it is not always a complete backup because it may be crash-consistent, remain in the same failure domain and exclude application configuration, identity, networking or other dependencies.

Before deployment, I first check whether the change affects persistent data. For a normal stateless AKS release, I record the current Helm revision and immutable ACR digest; rollback does not need a disk snapshot. For an AKS workload with PVCs, I use Azure Backup for AKS or a CSI `VolumeSnapshot` with application-consistency hooks. For VMs, I verify Azure Backup and create an on-demand recovery point before a risky change. For Azure Database for PostgreSQL, I verify the PITR window and create an on-demand or logical backup where required.

If an issue occurs, I stop the deployment and prefer application rollback when the data is still valid. If data restoration is necessary, I restore to a new PVC, disk, VM or PostgreSQL server, validate integrity, networking, identity and the complete application flow, and only then perform a controlled cutover. I never restore an old Terraform state expecting it to recreate lost data, and I do not consider the backup strategy complete until restore testing proves the required RPO and RTO.
