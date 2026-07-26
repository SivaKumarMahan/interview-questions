# Repetitive Interview Questions

## What storage type do you use in your project, and how do you use it?

### Detailed answer

In my Azure project, we do not use one storage type for every requirement. We select storage from the application access pattern, sharing requirement, performance, durability, RPO/RTO and cost.

The main storage services are:

```text
unstructured objects and files -> Azure Blob Storage
shared filesystem across Pods  -> Azure Files
single-workload block storage  -> Azure Managed Disk through an AKS PVC
temporary Pod scratch data     -> emptyDir/ephemeral storage
transactional relational data  -> Azure Database for PostgreSQL
Terraform remote state         -> dedicated private Azure Blob container
container images               -> Azure Container Registry
```

Our primary application-object storage is **Azure Blob Storage in a general-purpose v2 Storage Account**. AKS workloads use managed identity/workload identity to access Blob Storage through a private endpoint. For Kubernetes volume mounts, we use Azure Disk or Azure Files according to the required access mode; we do not place transactional database data in arbitrary container filesystems.

### 1. Azure Blob Storage for unstructured data

We use block blobs for unstructured objects such as:

- User-uploaded documents and images.
- Generated reports and exports.
- Large application files that should not live inside a container image.
- Approved backup or archive exports.
- Deployment artifacts when an artifact-specific service is not required.
- Static content where the architecture calls for object storage.

The application does not write these files to a Pod's local filesystem because a Pod can be rescheduled or deleted at any time. Instead, it uploads the object to a dedicated Blob container and stores only the object identifier and business metadata in PostgreSQL.

A simplified flow is:

```text
client/application
-> Java service running in AKS
-> workload identity
-> private Blob endpoint
-> application container
```

The Java application uses the Azure Storage SDK with `DefaultAzureCredential` or the approved workload-identity credential chain. No storage-account key is embedded in source code, Docker images, Helm values or Kubernetes Secrets.

The managed identity receives only the required data-plane role at the narrowest practical scope. For example:

- A read-only consumer gets a Blob data-reader role.
- An uploader gets permission to create/write objects in the required container.
- A lifecycle or administrative identity is separate from the application identity.

The application validates file type, size, name and authorization before upload. Object names use generated identifiers rather than trusting a client-supplied path. Sensitive files have explicit retention, malware-scanning and download-authorization requirements.

### 2. Blob type selection

Azure Blob Storage provides different blob types:

- **Block blobs:** The normal choice for documents, images, packages, exports and most application objects.
- **Append blobs:** Optimized for append-oriented patterns, but application and platform logs in our design normally go to Azure Monitor/Log Analytics rather than using Blob Storage as the live logging system.
- **Page blobs:** Random-access page storage used for specialized scenarios; Azure managed disks abstract this requirement for our VM and AKS block-storage use cases.

For most project data, I use block blobs. The application accesses them through the API/SDK instead of mounting the entire container as a filesystem unless there is a specific filesystem requirement.

### 3. Storage account type and performance

For normal application objects, we use a **general-purpose v2 (`StorageV2`) account** because it supports Blob Storage, Azure Files and lifecycle/data-protection capabilities.

The performance tier follows the workload:

- **Standard:** Cost-effective for normal documents, reports, backups and general-purpose objects.
- **Premium block blob:** Considered for consistently low-latency or high-transaction object workloads after measurement.
- **Premium file shares:** Considered when a shared filesystem needs higher and more predictable performance.

I do not choose Premium only because it sounds better. I measure object size, request rate, latency, throughput, concurrency and cost before selecting it.

Storage accounts are separated when environments, ownership, network boundaries, retention, compliance or blast radius differ. Production does not share unrestricted containers and credentials with Development.

### 4. Redundancy selection

Redundancy is selected from the failure the business needs to survive:

| Redundancy | Protects against | Typical decision |
| --- | --- | --- |
| LRS | Local hardware/rack failure within one datacenter | Lower-cost noncritical or replaceable data |
| ZRS | Datacenter/zone failure within the region | Production data requiring in-region zone resilience |
| GRS | Regional copy in a paired region | Regional disaster-recovery requirement where secondary data is not normally readable |
| RA-GRS | GRS plus read access to the secondary | Read access to replicated secondary data is required |
| GZRS | Zone resilience in primary plus geo-replication | Production data requiring zone and regional protection |
| RA-GZRS | GZRS plus secondary read access | Both resilience and secondary read access are required |

For Production, I normally prefer ZRS when the service and region support it and the requirement is zone resilience. If the approved disaster-recovery design requires a regional copy, I evaluate GZRS/RA-GZRS and the actual failover procedure. Replication is not the same as backup: accidental deletion or corruption can also be replicated, so versioning, soft delete and independent backup/retention may still be required.

The exact SKU must be validated against the selected account type, service, region and feature requirements.

### 5. Access tiers and lifecycle

Blob access tiers control cost based on how frequently data is accessed:

- **Hot:** Frequently accessed active objects.
- **Cool or Cold:** Infrequently accessed objects that still need online access, subject to service availability and retention/cost behavior.
- **Archive:** Long-term data that can tolerate offline rehydration time.

We start active objects in the appropriate online tier and use lifecycle policies to transition or delete data based on business retention. A representative policy might:

```text
active report -> Hot
after approved inactivity period -> Cool/Cold
after compliance period -> Archive or delete
```

Lifecycle rules use prefixes or blob index tags such as application, environment, data class and retention class. We test rules in non-production and review the effect on current versions, snapshots, soft-deleted objects and legal/immutability requirements before enabling deletion.

Archive is not suitable when the application expects immediate retrieval. Rehydration time and cost are part of the RTO design.

### 6. Security controls for Storage Accounts

Production Storage Accounts use layered controls:

- Disable or restrict public network access according to the design.
- Use private endpoints for required Blob/File access.
- Configure Private DNS so AKS resolves the service to the private address.
- Use Microsoft Entra ID, managed identity and Azure RBAC instead of account keys.
- Disable shared-key authorization where all required integrations support that policy.
- Require secure transfer and current TLS policy.
- Use encryption at rest; use customer-managed keys only when compliance requires and operations can support them.
- Separate management-plane permission from data-plane permission.
- Apply least privilege at account/container scope as appropriate.
- Enable diagnostic logs, metrics, alerts and Defender controls according to policy.
- Protect deletion and overwrite with versioning, soft delete, container protection, immutability or backup where required.
- Use Azure Policy to enforce approved network, encryption, redundancy and diagnostic settings.

Private endpoints do not remove the need for identity authorization. They provide a private network path; RBAC still decides which identity can read or write data.

### 7. Data protection and recovery

For critical Blob data, I evaluate:

- Blob versioning for recoverable object history.
- Blob and container soft delete.
- Point-in-time or backup capabilities where supported and required.
- Immutable storage for regulated write-once/retention scenarios.
- Lifecycle rules to control old-version and snapshot cost.
- Separate backups or exports when the RPO/DR design requires independence.

Versioning and soft delete are useful protections against accidental overwrite or deletion, but they are not a replacement for a complete backup and disaster-recovery plan.

The restore process is tested:

1. Identify the correct object version or recovery point.
2. Restore or copy it to a validation name/container first.
3. Verify checksum, metadata, permissions and application readability.
4. Promote it to the active object through the controlled process.
5. Monitor application behavior.
6. Retain evidence and follow the lifecycle policy.

### 8. Azure Disk for AKS block storage

When a Pod requires persistent block storage—commonly for a single stateful workload—we request Azure Disk through a Kubernetes PVC and the Azure Disk CSI driver.

A representative PVC is:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: application-data
  namespace: application
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: <approved-azure-disk-storage-class>
  resources:
    requests:
      storage: 128Gi
```

The Pod mounts the claim:

```yaml
spec:
  containers:
    - name: application
      image: <acr-name>.azurecr.io/application@sha256:<digest>
      volumeMounts:
        - name: application-data
          mountPath: /var/lib/application
  volumes:
    - name: application-data
      persistentVolumeClaim:
        claimName: application-data
```

Azure Disk is primarily selected for `ReadWriteOnce` block-storage patterns. I consider:

- Required IOPS, throughput and latency.
- Capacity and expansion.
- Zone/topology constraints.
- Pod rescheduling and disk attachment behavior.
- Reclaim policy.
- Snapshot and Azure Backup for AKS support.
- Filesystem consistency and application-consistent backup.
- Node/volume attachment limits.

I do not use a raw Azure Disk PVC as the default for a horizontally scaled service that needs every replica to write the same filesystem.

### 9. Azure Files for shared AKS storage

When multiple Pods need a shared filesystem, Azure Files can be mounted through the Azure Files CSI driver with an appropriate access mode, commonly `ReadWriteMany`.

A representative claim is:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-content
  namespace: application
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: <approved-azure-files-storage-class>
  resources:
    requests:
      storage: 256Gi
```

Typical use cases include shared generated content, compatibility with an application that expects SMB/NFS semantics, or shared files consumed by several replicas.

Before using Azure Files, I validate:

- Protocol requirements such as SMB or NFS.
- Linux/Windows client compatibility.
- File-locking and permission semantics.
- Metadata-heavy versus sequential throughput behavior.
- Performance tier and share limits.
- Private endpoint and DNS behavior.
- Identity/authentication support for the selected pattern.
- Backup, snapshot, retention and restore support.

For a cloud-native service, direct Blob API access is often more scalable than converting object storage into a shared filesystem. Azure Files is used when filesystem semantics are a real application requirement.

### 10. Ephemeral Pod storage

For temporary files, unpacked content, caches and intermediate processing that may safely disappear with the Pod, we use:

- Container writable layer for very limited disposable data.
- `emptyDir` for Pod-lifetime scratch space shared by containers.
- Memory-backed `emptyDir` only for small, justified sensitive/performance use cases with strict memory controls.

Ephemeral storage has requests/limits and monitoring because filling node storage can evict Pods and affect other workloads.

I never store business-critical data only in the container filesystem or `emptyDir`. If the Pod must survive rescheduling without data loss, the data belongs in a persistent or external service.

### 11. Azure Database for PostgreSQL for transactional data

Structured transactional data belongs in Azure Database for PostgreSQL rather than Blob Storage or a shared filesystem.

We use PostgreSQL for:

- Relational business entities.
- Transactions and consistency constraints.
- Queries and indexes.
- Application metadata, including references to Blob objects.

A common pattern is:

```text
PostgreSQL:
  document ID, owner, status, blob URI/key, checksum, timestamps

Blob Storage:
  actual document bytes
```

The application connects through private networking using the approved identity/credential pattern. We monitor connections, query latency, CPU, storage, locks and backup health. Native backups/PITR and the tested recovery plan protect transactional data.

Large binary content is normally kept in Blob Storage so that database size, backup duration and transaction performance remain manageable.

### 12. Terraform state in a dedicated Blob container

Terraform remote state is stored as a Blob in a dedicated, tightly controlled Storage Account/container. It is separated from general application data because state can contain sensitive infrastructure metadata.

A representative backend is:

```hcl
terraform {
  backend "azurerm" {
    storage_account_name = "<state-storage-account>"
    container_name       = "tfstate"
    key                  = "production/platform.tfstate"
    use_azuread_auth     = true
  }
}
```

The backend uses Azure Blob native locking and consistency behavior. CI/CD authenticates through Microsoft Entra workload identity or managed identity rather than embedding an account key in backend configuration.

Controls include:

- Separate state keys or accounts based on environment and blast radius.
- Least-privilege Blob data access for the pipeline identity.
- Private endpoint and approved runner network path.
- Versioning and soft delete.
- Encryption and diagnostic logs.
- No state file in Git, email or developer-shared folders.
- No application identity access to Terraform state.
- Tested state-recovery procedure.

State protection does not back up the resources themselves. Databases, disks, AKS persistent volumes and application data require their own backup strategies.

### 13. Azure Container Registry

Docker/OCI images are stored in Azure Container Registry, which is a purpose-built registry rather than a general application-file store.

The CI pipeline:

1. Builds the Java artifact and Docker image.
2. Scans the image.
3. Tags it with a release version and commit.
4. Pushes it to ACR through a least-privilege identity.
5. Records the immutable digest.

AKS pulls the approved image using its managed identity with the required pull permission. Production deploys by digest, and retention policies preserve known-good rollback images while removing confirmed obsolete artifacts according to policy.

### 14. Provisioning through Terraform/Bicep

Storage resources are provisioned through reviewed Terraform or Bicep modules rather than manually.

The module captures:

- Account kind and performance SKU.
- Redundancy.
- Containers/file shares.
- Private endpoints and Private DNS.
- Public-access restrictions.
- RBAC role assignments.
- Encryption and key requirements.
- Soft delete, versioning and retention.
- Lifecycle management.
- Diagnostic settings and alerts.
- Tags, ownership and cost metadata.

Environment-specific values are supplied at the root/module-call level. Credentials and secret values are not hardcoded into the module.

Changes run through:

```text
pull request
-> format/validate
-> security and Azure Policy checks
-> reviewed plan
-> protected apply
-> private DNS/RBAC/access verification
```

### 15. Monitoring and troubleshooting

I monitor:

- Availability and authentication failures.
- Request count and latency.
- Throttling and server-side errors.
- Capacity and object growth.
- Egress and transaction cost.
- Private endpoint and DNS health.
- Lifecycle/retention execution.
- Backup and restore jobs.
- Disk IOPS, throughput, latency and queue depth.
- PVC Pending, mount or attachment failures.
- File-share quota and protocol errors.
- PostgreSQL storage and connection behavior.

For Blob access failures, I separate:

```text
DNS/private endpoint
-> route/NSG/firewall
-> TLS endpoint
-> Microsoft Entra authentication
-> data-plane RBAC
-> container/object existence
-> application authorization
```

For an AKS mount failure, I inspect the PVC, PV, StorageClass, Pod Events, CSI controller/node logs, topology, access mode, quota, identity and backend storage health before detaching or deleting anything.

### 16. Storage selection rules

My selection rules are:

- Use **Blob Storage** for scalable unstructured objects accessed through an API.
- Use **Azure Files** only when multiple clients need shared filesystem semantics.
- Use **Azure Disk** when a workload needs persistent block storage with the supported attachment/access pattern.
- Use **ephemeral storage** only when losing the data with the Pod is acceptable.
- Use **PostgreSQL** for relational transactions and queries.
- Use a **dedicated Blob backend** for Terraform state.
- Use **ACR** for container images.
- Do not store secrets in any of these; use **Azure Key Vault**.

### Concise interview answer

In my project, the primary unstructured-data service is Azure Blob Storage in a general-purpose v2 Storage Account. Java microservices in AKS access Blob containers through workload identity and a private endpoint, so we do not store account keys in code or Kubernetes Secrets. We use block blobs for documents, reports and large application objects, while PostgreSQL stores the relational metadata and transactions.

For Kubernetes mounts, I use Azure Disk-backed PVCs for persistent block storage that follows a `ReadWriteOnce` pattern, and Azure Files when multiple Pods genuinely require a shared `ReadWriteMany` filesystem. Temporary processing uses `emptyDir`, and no critical data is left in a container filesystem. Terraform state is stored separately in a private, versioned Blob container with Entra authentication and native locking, while container images are stored in ACR.

For Production, I choose LRS, ZRS or geo-redundant options from the business RPO/RTO instead of using one SKU everywhere. Storage Accounts use private endpoints, Private DNS, managed identity, least-privilege RBAC, encryption, soft delete/versioning, lifecycle policies, monitoring and tested backup/restore. This gives us the correct balance of performance, availability, security and cost for each data type.
