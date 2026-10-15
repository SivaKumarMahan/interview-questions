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

**Interviewer:** How do backup and restore work for PostgreSQL?

**Candidate:** There are two layers. Azure Database for PostgreSQL Flexible Server takes the **automatic** backups (full snapshots plus WAL), and I use `pg_dump` / `pg_restore` for **logical** copies when I need one database, one table, or a copy outside Azure.

Built-in backups (Flexible Server):

- Retention is **7 to 35 days** (default 7). Point-in-time restore to any second inside that window.
- **Geo-redundant backup** copies backups to the paired region. It must be chosen when the server is created.
- For longer retention (months or years, for audit), use **Azure Backup** with a Backup vault.
- Single Server was retired in March 2025, so new answers should talk about Flexible Server.

Point-in-time restore always creates a **new** server:

```bash
az postgres flexible-server restore \
  --resource-group rg-data \
  --name pg-orders-restore-0959 \
  --source-server pg-orders-prod \
  --restore-time "2026-10-15T09:59:00Z"
```

Logical backup and restore:

```bash
# Custom format: compressed, lets you restore selected objects
pg_dump -h pg-orders-prod.postgres.database.azure.com -U dbadmin -d orders \
  -Fc -f orders_$(date +%F).dump

# Restore into a new database, 4 parallel jobs, ignore original owners
pg_restore -h pg-orders-restore.postgres.database.azure.com -U dbadmin \
  -d orders_restored --no-owner -j 4 orders_2026-10-15.dump

# Restore only one table
pg_restore -h <host> -U dbadmin -d orders_restored -t payments orders_2026-10-15.dump
```

Remember:

- A plain `pg_dump > file.sql` is restored with `psql`; a custom-format dump (`-Fc`) is restored with `pg_restore`.
- `pg_dump` does not include roles. Recreate users and grants separately (`pg_dumpall --roles-only`, with `--no-role-passwords` on a managed service).
- The restored server needs the same networking as the old one (private endpoint or VNet integration, private DNS, firewall rules) before the app can connect.
- Test the restore regularly and write down how long it took. That number is your real RTO.

## Virtual machine backup

For a VM-based application, I use Azure Backup when full-machine recovery is required. A disk snapshot can be useful before a small disk-level change, but it is not a replacement for a managed backup policy.

Before taking a snapshot, I make the application data consistent when required—for example, by stopping writes or using the application's supported backup process.

With Azure Backup, the VM is protected in a **Recovery Services vault** with a policy (daily or hourly schedule plus daily/weekly/monthly retention):

```bash
az backup protection enable-for-vm \
  --resource-group rg-app --vault-name rsv-prod \
  --vm vm-app-01 --policy-name DailyPolicy

# On-demand backup before a risky change (date is dd-mm-yyyy)
az backup protection backup-now \
  --resource-group rg-app --vault-name rsv-prod \
  --container-name vm-app-01 --item-name vm-app-01 \
  --backup-management-type AzureIaasVM --retain-until 30-11-2026
```

Restore options from a recovery point:

- **Create a new VM** - safest, the old one stays for comparison.
- **Restore disks** - then attach them or build a VM from them.
- **Replace existing disks** - in place, when the VM itself must come back.
- **File recovery** - mount the recovery point and copy back a few files.
- **Cross-region restore** - when the vault is GRS with cross-region restore enabled.

Windows VMs get application-consistent backups through VSS. Linux VMs need pre/post scripts (for example, to freeze a database) for application consistency; otherwise they are file-system consistent.

## Backup vs Site Recovery vs Azure Migrate

**Interviewer:** How do you migrate on-prem servers to Azure, and how is that different from backup and DR?

**Candidate:** They solve three different problems, and people often mix them up.

| Tool | Problem it solves | How it works | Typical recovery |
|---|---|---|---|
| **Azure Backup** | Data was deleted or corrupted | Point-in-time copies kept in a vault | Restore from a recovery point; RPO up to the last backup, RTO in hours |
| **Azure Site Recovery (ASR)** | A whole region or data centre is down | Continuous replication to a second region | Fail over in minutes; RPO in seconds to minutes |
| **Azure Migrate** | Move on-prem servers to Azure once | Discover -> assess -> replicate -> test -> cut over | One-time move, then decommission |

Migration flow with Azure Migrate:

```text
Discover + assess (sizing, cost, dependencies)
  -> prepare landing zone (VNet, NSG, VPN/ExpressRoute, DNS, RBAC)
  -> replicate servers (agentless for VMware/Hyper-V, Mobility agent for physical)
  -> test migration into an isolated VNet
  -> cutover: stop app, final sync, migrate, switch DNS
  -> enable Azure Backup + monitoring on the new VMs
  -> keep on-prem switched off but intact until sign-off (rollback)
```

DR flow with Site Recovery:

```text
Replicate VM to secondary region -> recovery plan (order: DB, then app, then web)
  -> test failover into isolated VNet (no impact on production)
  -> real failover -> commit -> re-protect -> fail back later
```

Remember:

- **Replication is not backup.** If data is corrupted or ransomware encrypts it, ASR replicates the damage. You need both.
- Always do a **test** migration or **test** failover before the real one.
- After migration, the new VMs are not protected automatically - enable Azure Backup and, if required, ASR.

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

## Restoring a Jenkins backup - will it work?

**Interviewer:** If you restore a Jenkins backup, will it work?

**Candidate:** Yes, if the backup is complete and I restore onto the **same Jenkins version and plugin versions**. Most failed restores come from a missing `secrets/` folder or a plugin mismatch.

Everything lives in `JENKINS_HOME` (usually `/var/lib/jenkins`):

```text
JENKINS_HOME/
  config.xml                 global settings
  credentials.xml            stored credentials (encrypted)
  secrets/                   master.key, hudson.util.Secret - keys that decrypt the credentials
  jobs/<job>/config.xml      job definitions (builds/ = history, optional)
  plugins/                   installed plugins
  users/, nodes/             users and agent definitions
  workspace/, caches/        can be skipped - rebuilt on the next run
```

Backup:

```bash
# Take it when Jenkins is quiet (or stopped) so files are consistent
tar -C /var/lib -czf /backup/jenkins-home-$(date +%F).tar.gz \
  --exclude='jenkins/workspace' --exclude='jenkins/caches' jenkins
```

Restore:

```bash
sudo systemctl stop jenkins
sudo mv /var/lib/jenkins /var/lib/jenkins.old            # keep the old copy
sudo tar -C /var/lib -xzpf /backup/jenkins-home-2026-10-15.tar.gz
sudo chown -R jenkins:jenkins /var/lib/jenkins
sudo systemctl start jenkins
journalctl -u jenkins -f                                 # watch for plugin errors
```

Why a restore fails:

- **No `secrets/` folder** -> `credentials.xml` is restored but cannot be decrypted, so every credential is broken. Store this backup encrypted, because it contains the keys.
- **Different Jenkins or plugin versions** -> plugins fail to load and jobs show errors. Restore on the same version first, then upgrade in a controlled way.
- **Wrong owner** -> Jenkins cannot read its own files.
- **New hostname** -> update the Jenkins URL; agents may need to reconnect.

After the restore I check: login works, jobs are listed, one credential is used successfully, agents are online, and one real pipeline runs end to end.

Remember:

- Better than only file backups: keep Jenkins **as code** - Configuration as Code (JCasC) YAML, a pinned `plugins.txt`, and `Jenkinsfile`s in Git. Then a rebuild is repeatable, and the backup mainly protects credentials and build history.
- On Kubernetes or a VM, a disk/PVC snapshot of `JENKINS_HOME` is a good extra layer, but test that it actually restores.
- A backup that has never been restored is not a proven backup.

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
