# Repetitive Interview Questions

## What storage type do you use in your project, and how do you use it?

**Interviewer:** Which Azure storage services do you use, and how do you choose between them?

**Candidate:**

I choose storage based on the type of data and how the application needs to access it. I do not use one storage service for every requirement.

| Requirement | Azure service |
| --- | --- |
| Images, documents, logs, and backups | Blob Storage |
| A disk attached to one AKS workload | Azure Disk |
| Shared files used by multiple Pods | Azure Files |
| Application transactions | Azure Database for PostgreSQL |
| Container images | Azure Container Registry |
| Terraform state | Private Blob container |

## Azure Blob Storage

I use Blob Storage for unstructured files such as:

- Images and videos.
- Reports and documents.
- Log archives.
- Application exports.
- Backup files.

Example upload:

```bash
az storage blob upload \
  --account-name <storage-account> \
  --container-name reports \
  --name report.pdf \
  --file report.pdf \
  --auth-mode login
```

### Blob types

- **Block blob:** Normal files such as images, PDFs, and backups.
- **Append blob:** Data that is added at the end, such as some logging scenarios.
- **Page blob:** Random read/write data, mainly used by virtual disks.

For most application files, I use block blobs.

### Access tiers

- **Hot:** Frequently accessed data. Highest storage cost, lowest read cost.
- **Cool:** Infrequently accessed data. Minimum 30 days.
- **Cold:** Rarely accessed data that must still be readable at once. Minimum 90 days.
- **Archive:** Offline tier for long-term retention. Minimum 180 days. A blob must be rehydrated to Hot or Cool before it can be read, which can take hours.

If a blob leaves a tier before its minimum period, Azure charges an early-deletion fee.

I use lifecycle rules to move older files to a cheaper tier or delete them after the retention period.

Example:

```text
0-30 days    -> Hot
31-90 days   -> Cool
After 90 days -> Archive or delete
```

## Azure Disk

Azure Disk provides block storage that behaves like a disk attached to a node. In AKS, it is commonly used through a PersistentVolumeClaim.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: application-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: managed-csi
```

This works well when one workload needs its own persistent disk. A normal Azure Disk is tied to an availability zone and is not the default choice for many Pods writing to the same volume.

## Azure Files

Azure Files provides a shared file system. I use it when multiple Pods or systems need to access the same files.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-files
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: azurefile-csi
```

Typical uses include shared reports, uploaded content, or legacy applications that require a shared folder.

## Temporary Pod storage

For temporary files that can disappear when the Pod is deleted, I use `emptyDir`.

```yaml
volumes:
  - name: temporary-data
    emptyDir: {}
```

I do not use it for important business data because it follows the lifetime of the Pod.

## Azure Database for PostgreSQL

I use PostgreSQL for structured transactional data such as users, orders, and payments.

It provides:

- Tables and relationships.
- Transactions.
- Backups and point-in-time restore.
- High-availability options.
- Monitoring and access controls.

I keep database data outside the AKS Pods so that replacing a Pod does not delete the data.

## Terraform state

Terraform state is stored in a dedicated private Blob container.

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-platform"
    storage_account_name = "tfstateaccount"
    container_name       = "tfstate"
    key                  = "production.tfstate"
  }
}
```

The storage account has:

- Restricted access.
- State locking.
- Versioning or recovery protection.
- Separate state files for separate environments.

Terraform state may contain sensitive information, so I do not make the container public.

## Azure Container Registry

Azure Container Registry stores container images rather than normal application files.

```bash
docker build -t <registry>.azurecr.io/orders-api:1.2.0 .
docker push <registry>.azurecr.io/orders-api:1.2.0
```

AKS receives permission to pull images through its identity. I use a version or digest instead of `latest`.

## Redundancy

The redundancy option depends on how much failure protection the application needs:

- **LRS:** Copies data within one datacenter.
- **ZRS:** Copies data across availability zones in one region.
- **GRS/GZRS:** Also copies data to another region.

Higher protection usually costs more, so I choose it from the application's availability and recovery requirement.

## Security

For storage security, I:

- Disable public access unless it is required.
- Use managed identity and Azure RBAC.
- Use private endpoints for sensitive workloads.
- Require HTTPS.
- Encrypt data at rest.
- Use short-lived SAS tokens only when delegated access is needed.
- Monitor access and configuration changes.

I do not store account keys in source code.

## Scenario: a Storage Account became public. How do you fix it?

**Interviewer:** A Storage Account has become public. How do you remediate it?

**Candidate:** First I find out **what kind of public** it is. There are two separate settings, and I check both:

| Setting | What it means |
| --- | --- |
| **Public network access** | Anyone on the internet can reach the account endpoint (they still need a key, SAS or RBAC) |
| **Anonymous blob access** | Anyone can read blobs **without any credentials** - this is the dangerous one |

Remediation flow:

```text
Identify the exposure (network access? anonymous container?)
        |
Disable anonymous blob access + set containers to Private
        |
Disable public network access -> use Private Endpoint / selected networks
        |
Review keys, SAS tokens and RBAC
        |
Activity Log + storage logs -> who changed it, was data read?
        |
Prevent: Azure Policy + Terraform/Bicep
```

Quick commands:

```bash
# Which containers allow anonymous access?
az storage container list --account-name <account> --auth-mode login \
  --query "[].{name:name, access:properties.publicAccess}" -o table

# Lock the account down
az storage account update -g <rg> -n <account> \
  --allow-blob-public-access false \
  --public-network-access Disabled
```

If some clients really need internet access, I set it to **selected networks** with IP rules instead of all networks.

After closing the exposure:

- If anonymous access was on, I check the storage logs (diagnostic settings to Log Analytics) to see whether data was read.
- If a key or SAS may have leaked, I rotate the account keys. Rotating keys invalidates account SAS tokens signed with that key.
- I remove extra RBAC roles such as Storage Blob Data Contributor or Owner where they are not needed.

Prevention in code:

```hcl
resource "azurerm_storage_account" "app" {
  name                     = "stappprod001"
  resource_group_name      = azurerm_resource_group.app.name
  location                 = azurerm_resource_group.app.location
  account_tier             = "Standard"
  account_replication_type = "ZRS"

  public_network_access_enabled   = false
  allow_nested_items_to_be_public = false # no anonymous blob access
  shared_access_key_enabled       = false # Entra ID only, no account keys
  min_tls_version                 = "TLS1_2"
}
```

And Azure Policy (built-in) with **Deny** effect:

```text
Storage accounts should disable public network access
Storage account public access should be disallowed
```

Remember:

- Public network access and anonymous blob access are different controls.
- Turn on private access only after the Private Endpoint and Private DNS are tested, or the application will break.
- Before disabling shared keys, check that nothing still uses a connection string. Some tools and older SDKs need keys.

## Azure Functions writing generated files to Blob Storage

**Interviewer:** An Azure Function generates a PDF and stores it in a Storage Account. How is the storage part set up?

**Candidate:** In my project, an Azure Function picked up requests from Service Bus, generated the document, and saved it to Blob Storage.

```text
Request -> Service Bus queue
              |
         Azure Function (managed identity)
              |
         Generate PDF
              |
         Blob Storage
           input/      <- source files (if a file upload starts the flow)
           output/     <- generated PDFs
           failed/     <- files that could not be processed
```

Storage-side points:

- **Separate containers** for input, output and failed files, all private.
- **Managed identity** on the Function App, with **Storage Blob Data Contributor** scoped to the account or to the output container. No account keys in app settings.
- The Function App also has its own **host storage** (`AzureWebJobsStorage`). I use an identity-based connection (`AzureWebJobsStorage__accountName`) instead of a connection string.
- If the flow starts from a file upload, a **Blob Created** event through **Event Grid** triggers the Function. This is faster and more reliable than the old polling blob trigger.
- **Idempotent writes:** use a fixed blob name such as `output/<request-id>.pdf`, so a retry overwrites the same file instead of creating duplicates.
- **Lifecycle rule:** move PDFs older than 30 days to Cool and delete them after the retention period.
- Users download through a **short-lived user delegation SAS** or through the API, never through a public container.

Remember:

- Blob is the right choice here because PDFs are unstructured files.
- Keep the generated-file account private, with a Private Endpoint if the Function is VNet-integrated.

## Backup and recovery

The exact protection depends on the service:

- Blob versioning and soft delete protect files.
- Disk snapshots provide point-in-time disk copies.
- PostgreSQL supports backup and point-in-time restore.
- Terraform state uses versioning and restricted access.

A backup is useful only if the restore process has been tested.

## Troubleshooting

For an AKS volume problem:

```bash
kubectl get pvc,pv -n <namespace>
kubectl describe pvc <pvc-name> -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
```

I check whether the claim is bound, whether the disk is in the correct zone, and whether the CSI driver reported an attach or mount error.

For Blob access problems, I check the application identity, role assignment, firewall, private DNS, and whether the container and blob names are correct.

## Example

Suppose an application stores user-uploaded images and order data. I put the images in Blob Storage because they are files, and I put the orders in PostgreSQL because they need transactions and queries.

If several Pods must read the same generated report folder, I use Azure Files.

## In short

I use Blob Storage for files, Azure Disk for a single workload's persistent disk, Azure Files for shared folders, PostgreSQL for transactional data, ACR for images, and a private Blob container for Terraform state. I select the service based on access pattern, availability, security, cost, and recovery needs.
