# Artifact Repositories: Operations, HA, Backup, and Migration

> Running Nexus in production: best practices, retention and cleanup, monitoring, backup and restore, high availability and DR, and migrating from Artifactory.

## Interview Questions

### 1. What best practices would you follow when deploying Nexus Repository in Production?

**Answer:**

My Production checklist includes:

- Size from measured request, component and storage growth.
- Use a supported current Nexus, Java, database and operating system.
- Run Nexus under a dedicated non-root service account.
- Use external PostgreSQL for production-scale workloads according to Sonatype guidance.
- Use supported durable blob storage; on Azure, validate edition support for Azure Blob Storage.
- Use TLS and restrict network exposure.
- Put a supported reverse proxy/load balancer in front where required.
- Disable or tightly control anonymous access.
- Integrate enterprise identity and least-privilege roles.
- Separate hosted release, snapshot, proxy and group repositories.
- Disable release redeploy.
- Configure routing rules and approved external remotes.
- Use cleanup policies and capacity alerts.
- Back up database, blobs and configuration consistently.
- Test restore, upgrade and rollback-from-backup procedures.
- Monitor application, JVM, database, blob and infrastructure.
- Patch in a tested maintenance process.
- Pin pipeline clients/endpoints and protect their credentials in Azure Key Vault.
- Scan, sign and retain an SBOM and provenance record for important releases — provenance meaning where the artifact came from and how it was built.
- Document ownership, RPO, RTO, escalation and support procedures.

I test representative restore, download, publish and client builds before declaring the service production-ready.

### 2. How would you configure retention policies or clean up old artifacts in Nexus Repository?

**Answer:**

I define retention from business and recovery requirements before enabling deletion.

Process:

1. Classify repositories: snapshots, releases, proxy caches and regulatory artifacts.
2. Define cleanup criteria such as last downloaded, last updated, age, regex/version pattern or format-specific rules.
3. Preview/test the policy against a non-production or representative repository.
4. Assign cleanup policies to hosted/proxy repositories.
5. Schedule repository cleanup tasks during an appropriate window.
6. Retain soft-deleted blobs for a recovery period where supported.
7. Run the compact blob-store task off-peak to reclaim physical storage.
8. Monitor results and available storage.

Example policy:

```text
snapshot repository:
  delete snapshots older than approved age
  retain recent versions needed for active branches

release repository:
  never delete deployed/legally retained releases automatically
  retain all supported and rollback versions

proxy repository:
  remove components not downloaded for the approved cache period
```

Cleanup only soft-deletes content at first. Blob-store compaction is the step that permanently reclaims the space. I never schedule compaction without a tested backup, a recovery plan, and a policy review first.

Nexus Pro offers additional retention controls such as retaining selected versions. Exact criteria depend on format and product version.

### 3. How do you monitor the health and storage utilization of a Nexus Repository server?

**Answer:**

I monitor four layers:

1. **Application:** Status/writable endpoints, request rate, latency, error codes, task failures and read-only state.
2. **JVM/process:** Heap, garbage collection, threads, file descriptors, CPU and restarts.
3. **Data services:** PostgreSQL availability/latency/connections, blob-store state, capacity and I/O latency.
4. **Infrastructure:** VM/Pod health, disk, network, load balancer and certificate expiry.

Useful Nexus endpoints include:

```text
GET /service/rest/v1/status
GET /service/rest/v1/status/writable
GET /service/metrics/healthcheck
```

The Nexus status endpoint does not replace database, disk or infrastructure monitoring.

In Azure, I send host/container and Nexus logs to Azure Monitor/Log Analytics and use the approved metrics platform. Alerts include:

- Status/read/write failure.
- HTTP 5xx or latency increase.
- Blob-store/disk thresholds and rapid growth.
- PostgreSQL failures or saturation.
- JVM memory/GC pressure.
- Cleanup/backup/task failure.
- Certificate nearing expiry.
- Authentication failures and unusual artifact deletion/download.

I forecast capacity rather than waiting for a disk-full outage. The repository size shown in the UI may not include all of the metadata, index and storage overhead, so I also watch the underlying blob-store metrics directly.

### 4. How do you back up and restore a Nexus Repository instance?

**Answer:**

A valid backup must protect the matching set of:

- Nexus database containing metadata and configuration.
- Blob stores containing artifact binaries.
- Required data-directory/application configuration.
- Encryption/secret material required to restore the instance.
- License and deployment configuration where applicable.

For an embedded H2 deployment, I use the supported database backup task, and I back up the other required data at the same time so everything stays consistent. For PostgreSQL, I use a supported PostgreSQL backup or point-in-time-recovery process, coordinated with blob-store backups or snapshots, following Sonatype's guidance.

High-level restore:

1. Declare an outage/recovery window and stop writes.
2. Provision the same supported Nexus version/configuration.
3. Restore the database and matching blob-store recovery point.
4. Restore required data/configuration securely.
5. Start Nexus and inspect startup logs.
6. Verify repositories and blob-store state.
7. Test representative downloads and a controlled publication.
8. Run only supported integrity/repair procedures when required, preferably with Sonatype Support for data inconsistency.
9. Confirm clients/pipelines and monitoring.

I test restore regularly and measure the actual recovery point and recovery time objectives (RPO/RTO). A backup job reporting success is not proof the system can actually be recovered.

I avoid taking an uncoordinated live filesystem copy. If the database metadata and the blob content are captured at slightly different moments, they can end up inconsistent with each other.

### 5. How would you configure high availability or disaster recovery for Nexus Repository?

**Answer:**

Supported active/active high availability is a Nexus Repository Pro capability.

An Azure HA design includes:

```text
clients
-> Azure/application load-balancing layer
-> multiple Nexus Pro nodes in one low-latency region
-> shared supported Azure Blob Store
-> external Azure Database for PostgreSQL Flexible Server
```

Requirements include:

- Same supported Nexus version/configuration on every node.
- Separate failure domains (groups of resources that can fail together) for nodes.
- Low-latency shared PostgreSQL and blob storage.
- Health-aware load balancing.
- Per-node local working storage as documented.
- Monitoring of nodes, database, blob storage and inter-service latency.
- Tested node-failure and upgrade procedures.

I do not stretch one HA cluster across distant regions. The database and blob latency between regions creates consistency risk that can make the setup unsupported or unsafe. Cross-region disaster recovery is designed separately, using supported backups, replication or content-replication features, and a documented failover process.

DR plan:

1. Define RPO/RTO.
2. Protect database with supported backup/PITR.
3. Protect blob content with the approved storage recovery design.
4. Preserve configuration/secret/license dependencies.
5. Provision the secondary environment through IaC.
6. Restore coordinated data.
7. Validate integrity and representative client operations.
8. Switch DNS/traffic through an approved process.
9. Test regularly.

HA reduces node downtime. It does not replace backup or regional disaster recovery.

### 6. How would you migrate artifacts from JFrog Artifactory to Nexus Repository?

**Answer:**

I treat it as a controlled platform migration, not only a file copy.

Mapping:

```text
Artifactory local  -> Nexus hosted
Artifactory remote -> Nexus proxy
Artifactory virtual -> Nexus group
```

Plan:

1. Inventory repositories, formats, size, artifact counts, clients, permissions, retention, checksums and custom workflows.
2. Identify unsupported/edition-specific features and redesign them.
3. Build Nexus repositories, blob stores, TLS, identities, roles and groups.
4. Migrate users/groups through the approved identity system rather than copying passwords.
5. Export local Artifactory repository content.
6. Import into Nexus hosted repositories using the Pro import process, or republish through native clients/scripts where that feature is unavailable.
7. Recreate external sources as Nexus proxy repositories rather than copying an entire remote cache blindly.
8. Optionally proxy Artifactory temporarily from Nexus for artifacts not yet migrated.
9. Update pilot builds to use Nexus group/hosted endpoints.
10. Validate coordinates, checksums, representative builds, publish/download, access and performance.
11. Freeze new writes to Artifactory, perform final delta migration and switch clients.
12. Monitor, keep a rollback window and retire Artifactory only after acceptance.

Configuration, permissions, virtual/group order, properties and metadata do not necessarily migrate one-to-one. Component counts and storage sizes may also differ because repository managers store indexes/metadata differently.

I do not just blindly redirect every URL. I update clients to point at explicit Nexus endpoints and verify the behavior works.
