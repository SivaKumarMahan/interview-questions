# Sonatype Nexus Repository Interview Questions

The answers use an Azure-focused project model:

```text
developer or CI pipeline
-> Nexus Repository group for dependency downloads
-> compile, test and security checks
-> publish internal package to a hosted repository
-> promote the same approved artifact
-> deploy to Azure compute or AKS
```

Nexus Repository stores and distributes build inputs and outputs. Azure DevOps, Jenkins or GitHub Actions orchestrates the pipeline; Nexus does not replace the CI/CD engine.

---

## 1. What is Sonatype Nexus Repository, and why is it used in CI/CD pipelines?

**Answer:**

Sonatype Nexus Repository is a repository manager for storing, proxying, organizing and distributing software components such as Maven packages, npm packages, NuGet packages, Python packages, Helm charts and container images.

In CI/CD, I use it as the controlled system of record for dependencies and build outputs:

```text
external dependency
-> Nexus proxy cache
-> Nexus group endpoint
-> developer and CI build

internal source
-> build and tests
-> versioned package/image
-> Nexus hosted repository
-> controlled promotion/deployment
```

It provides:

- A central location for internal artifacts.
- Package-manager-native endpoints.
- Caching of approved external dependencies.
- Faster and more repeatable builds.
- Reduced direct internet dependency.
- Authentication, authorization and auditability.
- Release/snapshot separation.
- Retention and cleanup controls.
- A stable artifact URL independent of one pipeline run.
- Integration points for vulnerability policy and supply-chain governance.

Nexus should store immutable (not changed after creation) build artifacts, not source code. Git remains the source-code system, and the CI/CD platform remains responsible for building, testing, approving and deploying.

---

## 2. What are the different repository types available in Nexus Repository?

**Answer:**

The three main repository types are:

1. **Hosted repository:** Stores packages produced or deliberately uploaded by the organization.
2. **Proxy repository:** Proxies and caches a remote package repository.
3. **Group repository:** Presents multiple compatible hosted, proxy or nested group repositories through one client URL.

Example Maven design:

```text
maven-releases       hosted
maven-snapshots      hosted
maven-central-proxy  proxy
maven-public         group containing the three repositories
```

Developers normally download from the group. CI publishes to the appropriate hosted repository. A proxy is not a normal publication destination.

Nexus also separates the repository format from its type. For example, `maven2 (hosted)`, `maven2 (proxy)` and `maven2 (group)` share the Maven format but perform different roles.

---

## 3. What is the difference between Hosted, Proxy and Group repositories in Nexus?

**Answer:**

| Type | Purpose | Read behavior | Write behavior | Example |
| --- | --- | --- | --- | --- |
| Hosted | Store organization-owned or approved uploaded components | Reads local content | CI publishes here | `maven-releases` |
| Proxy | Cache a remote repository | Serves cache or fetches from remote | Clients do not publish internal builds here | `maven-central-proxy` |
| Group | Combined compatible repositories behind one URL | Searches members in configured order | Normally read-only; some Pro formats support a selected writable member | `maven-public` |

A proxy cache is controlled by component and metadata cache-age settings. Nexus checks the local cache first and consults the remote source when required.

A group simplifies client configuration, but member order matters. If two members contain the same coordinate, the first matching repository wins.

I put trusted internal sources and proxies in a deliberate order and use routing rules/content governance to reduce dependency-confusion risk.

Permissions on a group endpoint allow users to consume member content through that group. They do not automatically grant direct access to every member URL.

---

## 4. How would you configure Azure DevOps to publish artifacts to Nexus Repository?

**Answer:**

For a Maven project, I configure:

1. A least-privilege (minimum required access) Nexus CI service account.
2. A hosted snapshots repository and hosted releases repository.
3. `distributionManagement` in `pom.xml`.
4. A Maven `settings.xml` whose server ID matches the POM repository ID.
5. Nexus credentials stored as protected Azure DevOps secrets, preferably retrieved from Azure Key Vault.
6. A branch/tag rule deciding whether a snapshot or release can publish.

`pom.xml`:

```xml
<distributionManagement>
  <repository>
    <id>nexus-releases</id>
    <url>https://nexus.example.com/repository/maven-releases/</url>
  </repository>
  <snapshotRepository>
    <id>nexus-snapshots</id>
    <url>https://nexus.example.com/repository/maven-snapshots/</url>
  </snapshotRepository>
</distributionManagement>
```

`.ci/settings.xml` contains references, not literal credentials:

```xml
<settings>
  <servers>
    <server>
      <id>nexus-releases</id>
      <username>${env.NEXUS_USERNAME}</username>
      <password>${env.NEXUS_PASSWORD}</password>
    </server>
    <server>
      <id>nexus-snapshots</id>
      <username>${env.NEXUS_USERNAME}</username>
      <password>${env.NEXUS_PASSWORD}</password>
    </server>
  </servers>
</settings>
```

Representative Azure Pipeline:

```yaml
stages:
  - stage: Build
    jobs:
      - job: TestAndPackage
        pool:
          name: azure-ci-agents
        steps:
          - checkout: self
            clean: true

          - task: AzureKeyVault@2
            inputs:
              azureSubscription: azure-wif-ci-secrets
              KeyVaultName: <ci-key-vault-name>
              SecretsFilter: nexus-ci-username,nexus-ci-password

          - bash: |
              set -euo pipefail
              mvn -B --settings .ci/settings.xml clean verify
            displayName: Build and test
            env:
              NEXUS_USERNAME: $(nexus-ci-username)
              NEXUS_PASSWORD: $(nexus-ci-password)

          - bash: |
              set -euo pipefail
              mvn -B --settings .ci/settings.xml deploy -DskipTests
            displayName: Publish package to Nexus
            condition: |
              and(
                succeeded(),
                eq(variables['Build.SourceBranch'], 'refs/heads/main')
              )
            env:
              NEXUS_USERNAME: $(nexus-ci-username)
              NEXUS_PASSWORD: $(nexus-ci-password)
```

In a real pipeline I prefer one Maven invocation such as `mvn clean deploy` after all required gates, or I deliberately preserve the exact tested workspace/artifact. I do not accidentally compile different bytes during the publish step.

The CI identity receives `add/edit` only on the required hosted repository. It does not receive Nexus administration or delete permission. Pull-request pipelines do not receive publishing credentials.

---

## 5. How do developers consume artifacts stored in Nexus Repository?

**Answer:**

Developers configure their package manager to resolve from a Nexus group URL rather than contacting every hosted and public repository directly.

Examples:

```text
Maven/Gradle -> https://nexus.example.com/repository/maven-public/
npm          -> https://nexus.example.com/repository/npm-group/
NuGet        -> https://nexus.example.com/repository/nuget-group/index.json
PyPI         -> https://nexus.example.com/repository/pypi-group/simple
Docker/OCI   -> nexus-docker.example.com/team/image:version
```

The package manager requests a coordinate such as:

```text
com.example:orders-client:2.4.0
```

Nexus searches the group members in order and returns either an internal hosted artifact or a cached/proxied external dependency.

Credentials are supplied through the developer's approved credential/token mechanism, not committed in project files. CI uses a separate non-human read identity.

---

## 6. How does Nexus Repository act as a proxy for public repositories such as Maven Central or npm?

**Answer:**

An administrator creates a proxy repository with the public repository's remote URL and cache settings. Developers point their clients to the Nexus group, not directly to the public service.

Request flow:

```text
client requests package
-> Nexus checks local cache
-> cache hit: Nexus returns local content
-> cache miss: Nexus requests approved remote
-> Nexus stores response and metadata
-> Nexus returns it to client
-> later clients reuse cache
```

Nexus uses component and metadata maximum-age settings to decide when cached data should be revalidated. Negative-cache behavior can also affect how quickly a newly published remote component becomes visible after an earlier 404.

Benefits include:

- Fewer repeated external downloads.
- Faster builds near the Nexus server.
- Reduced internet egress.
- A central allow/deny and routing point.
- Some resilience when the remote service is unavailable, but only for already cached content.
- Visibility into which components the organization consumes.

I restrict Nexus outbound access to approved registries and use TLS validation. A proxy does not mean every remote component is safe; vulnerability, license, signature and policy controls remain necessary.

---

## 7. What package formats are supported by Sonatype Nexus Repository?

**Answer:**

Current Nexus Repository documentation lists formats including:

- Alpine.
- Ansible.
- Apt.
- CocoaPods.
- Composer/PHP.
- Conan.
- Conda.
- Docker/OCI.
- Git LFS.
- Go.
- Helm.
- Hugging Face.
- Maven.
- npm.
- NuGet.
- p2.
- Pub.
- PyPI.
- R.
- Raw.
- RubyGems.
- Rust/Cargo.
- Swift.
- Terraform.
- Yum.

The **Raw** format stores arbitrary files when no native package format applies.

Format availability and supported hosted/proxy/group capabilities can differ by Nexus edition and release. In an interview, I explain the formats relevant to the project—Maven, npm, NuGet, Docker and Helm—then verify the exact product/version matrix instead of claiming every format supports every repository type.
---

## 8. How do you upload Docker images to Nexus Repository?

**Answer:**

I first create a Docker hosted repository, configure a supported connector or subdomain endpoint, enable the Docker Bearer Token Realm, apply TLS and grant the CI user upload privileges.

Representative commands:

```bash
NEXUS_REGISTRY=nexus-docker.example.com
IMAGE_NAME=orders-service
IMAGE_VERSION=2.4.0

printf '%s' "$NEXUS_PASSWORD" |
  docker login "$NEXUS_REGISTRY" \
    --username "$NEXUS_USERNAME" \
    --password-stdin

docker build \
  --tag "$NEXUS_REGISTRY/$IMAGE_NAME:$IMAGE_VERSION" \
  .

docker push \
  "$NEXUS_REGISTRY/$IMAGE_NAME:$IMAGE_VERSION"

docker logout "$NEXUS_REGISTRY"
```

If connector ports are used, the registry is similar to:

```text
nexus.example.com:5001
```

I then record the pushed digest and deploy by digest where supported:

```text
nexus-docker.example.com/orders-service@sha256:<digest>
```

Important controls:

- Use HTTPS with a trusted certificate.
- Do not use `--password` on the command line.
- Give the pipeline write permission only to the hosted repository.
- Scan before publication and continuously rescan stored images.
- Use immutable (not changed after creation) version tags/digests; do not rely on `latest`.
- Enable the Docker Bearer Token Realm.
- Separate pull endpoints/groups from write endpoints unless an approved Pro writable-group design is used.

---

## 9. What is the purpose of a Repository Group in Nexus?

**Answer:**

A repository group provides one stable URL that aggregates several repositories of a compatible format.

For Maven:

```text
maven-public group
├── maven-releases hosted
├── maven-snapshots hosted
├── approved-third-party hosted
└── maven-central-proxy proxy
```

Developers configure only `maven-public`. Administrators can add, remove or reorder back-end repositories without modifying every developer and pipeline configuration.

Groups improve:

- Client simplicity.
- Central policy enforcement.
- Migration flexibility.
- Availability of internal and external components through one endpoint.
- Consistent authentication.

Member order must be deliberate. I also avoid placing untrusted repositories ahead of internal namespaces because the wrong component could be selected.

---

## 10. How do you implement versioning and release management using Nexus Repository?

**Answer:**

I use a documented version strategy appropriate to the package format:

- Maven snapshot: `2.4.0-SNAPSHOT`.
- Maven release: `2.4.0`.
- Semantic version: `MAJOR.MINOR.PATCH`.
- Pre-release: `2.5.0-rc.1`.
- Docker readable tag: release version and/or Git commit.
- Docker immutable (not changed after creation) identity: digest.

Release rules:

1. The source commit is immutable (not changed after creation) and reviewed.
2. CI generates the version from the release process.
3. Tests, quality and security gates complete.
4. CI publishes once to the correct hosted repository.
5. Release repositories use a disable-redeploy policy where appropriate.
6. The artifact checksum/digest is recorded.
7. Environments receive the same artifact; they do not rebuild it.
8. Release notes link version, commit, pipeline and artifact.

I avoid overwriting a released coordinate. If `2.4.0` is incorrect, I publish `2.4.1`; I do not silently replace `2.4.0`.

For Pro deployments, staging/build-promotion features can formalize the process. In other editions, the pipeline can implement controlled publication/promotion using supported repository APIs, but it must verify that the source and destination bytes/checksums are identical.
---

## 11. How would you configure authentication and authorization in Nexus Repository?

**Answer:**

I separate authentication from authorization.

Authentication options depend on edition/deployment and can include:

- Local Nexus users.
- External identity realms such as LDAP.
- SAML/SSO capabilities in applicable Pro deployments.
- User tokens/API keys where supported.
- Dedicated CI service accounts.

Authorization uses:

- **Privileges:** Actions such as browse, read, add, edit, delete and repository administration.
- **Roles:** Collections of privileges.
- **Content selectors:** More detailed access to paths/namespaces.
- **Users/groups:** Assigned one or more roles.

Example roles:

```text
developers-read
  browse/read maven-public and npm-group

orders-ci-publisher
  browse/read/add/edit orders hosted repository
  no delete
  no repository administration

release-manager
  approved promotion operations

nexus-operator
  system operations without unnecessary artifact publication
```

I:

- Disable anonymous access unless there is a justified read-only use case.
- Change the initial administrator password.
- Use named administrator accounts and MFA/SSO where available.
- Avoid sharing `admin` credentials with pipelines.
- Restrict role-management permissions because a user able to assign roles can escalate privileges.
- Review access periodically and remove leavers/stale service accounts.
- Keep Production publisher and reader permissions separate where required.

---

## 12. How do you integrate Nexus Repository with Azure DevOps, Jenkins or GitHub Actions?

**Answer:**

The integration pattern is the same:

```text
pipeline
-> authenticate with a least-privilege Nexus identity
-> configure package client
-> restore dependencies from group
-> build/test/scan
-> publish to hosted repository
-> record coordinate/checksum/digest
```

### Azure DevOps

- Store the Nexus credential in Azure Key Vault/protected secret variables.
- Inject it only into the publishing step.
- Use Maven/Gradle/npm/NuGet/Docker native commands.
- Do not expose publishing credentials to pull-request validation.

### Jenkins

```groovy
withCredentials([
    usernamePassword(
        credentialsId: 'orders-nexus-publisher',
        usernameVariable: 'NEXUS_USERNAME',
        passwordVariable: 'NEXUS_PASSWORD'
    )
]) {
    sh '''
        set +x
        mvn -B --settings .ci/settings.xml clean deploy
    '''
}
```

The credential is folder-scoped, the job runs on an isolated agent and command tracing is disabled around secret use. Jenkins masking is not treated as protection from malicious pipeline code.

### GitHub Actions

```yaml
- name: Publish Maven package
  if: github.ref == 'refs/heads/main'
  env:
    NEXUS_USERNAME: ${{ secrets.NEXUS_USERNAME }}
    NEXUS_PASSWORD: ${{ secrets.NEXUS_PASSWORD }}
  run: |
    set +x
    mvn -B --settings .ci/settings.xml clean deploy
```

I use a protected GitHub Environment for release publishing, restrict reviewers/branches and pin actions to reviewed commits.

If Nexus is integrated with an enterprise identity/token broker, I prefer short-lived credentials. Otherwise I rotate the dedicated Nexus token/password through Azure Key Vault and keep its repository permissions minimal.

---

## 13. What are snapshot and release repositories, and why are they kept separate?

**Answer:**

Snapshots represent work in progress. Releases represent approved immutable (not changed after creation) versions.

| Property | Snapshot | Release |
| --- | --- | --- |
| Example | `2.4.0-SNAPSHOT` | `2.4.0` |
| Stability | May change as development continues | Must remain immutable (not changed after creation) |
| Retention | Aggressive cleanup is normal | Retain according to deployment/compliance policy |
| Redeploy | Often permitted by snapshot policy | Normally disabled |
| Consumer | Development/test | Controlled release consumers |

Maven can translate a snapshot into timestamped snapshot artifacts while retaining the logical `-SNAPSHOT` version.

Separation prevents unstable builds from being mistaken for releases and allows different retention, write access and deployment policies. Production should not resolve an unpinned snapshot.

---

## 14. How would you configure retention policies or clean up old artifacts in Nexus Repository?

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

Cleanup initially soft-deletes content; blob-store compaction permanently reclaims space. I never schedule compaction without tested backup/recovery and policy review.

Nexus Pro offers additional retention controls such as retaining selected versions. Exact criteria depend on format and product version.

---

## 15. How do you back up and restore a Nexus Repository instance?

**Answer:**

A valid backup must protect the matching set of:

- Nexus database containing metadata and configuration.
- Blob stores containing artifact binaries.
- Required data-directory/application configuration.
- Encryption/secret material required to restore the instance.
- License and deployment configuration where applicable.

For an embedded H2 deployment, I use the supported database backup task and back up the other required data consistently. For PostgreSQL, I use a supported PostgreSQL backup/PITR process and coordinate it with blob-store backup/snapshots according to Sonatype guidance.
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

I test restore regularly and measure actual RPO/RTO. A backup job reporting success is not proof that the system can be recovered.

I avoid taking an uncoordinated live filesystem copy because database metadata and blob content can become inconsistent.

---

## 16. How would you migrate artifacts from JFrog Artifactory to Nexus Repository?

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

I do not redirect every URL blindly; I update clients to explicit Nexus endpoints and verify behavior.

---

## 17. What is the difference between Nexus Repository OSS and Nexus Repository Pro?

**Answer:**

The historically named OSS offering is presented in current documentation as **Community Edition**, while the licensed enterprise offering is **Professional Edition**. Exact packaging and entitlement can change, so I confirm the version-specific feature matrix during design.
Community Edition provides the core repository-manager capabilities needed to host, proxy and group supported formats.

Professional Edition adds enterprise capabilities that currently include areas such as:

- Supported high availability/resilient architectures.
- SAML/SSO and additional enterprise identity integrations.
- User-token support.
- Staging and build promotion.
- Content replication.
- Tagging.
- Repository import/export.
- Azure Blob Store support.
- Group blob stores.
- Additional cleanup/version-retention controls.
- Writable group deployment for selected formats.
- Enterprise support.

Sonatype Repository Firewall/Lifecycle/IQ supply-chain policy capabilities may be separate products or licenses. I do not describe every vulnerability/isolate feature as automatically included in Nexus Pro.

The choice depends on availability objectives, identity, storage, promotion, support and compliance requirements—not merely artifact count.

---

## 18. How do you secure sensitive artifacts stored in Nexus Repository?

**Answer:**

I apply defense in depth:

- HTTPS only with trusted certificates.
- Restricted network exposure through private connectivity/firewalls/reverse proxy.
- Anonymous access disabled unless explicitly justified.
- Enterprise SSO/MFA where supported.
- Least-privilege (minimum required access) roles and content selectors.
- Separate identities for humans, CI readers, CI publishers and administrators.
- Secrets stored in Azure Key Vault, not pipeline YAML or client project files.
- Encryption at rest through the database/blob-storage design.
- Immutable (not changed after creation) release coordinates and disabled redeploy.
- Audit/security logging and alerts for unusual download/upload/delete behavior.
- Supported Nexus/Java/OS versions and timely patching.
- Routing rules to constrain namespace/source behavior.
- Artifact scanning, SBOM, signing and checksum verification in the supply-chain process.
- Tested backups with restricted access.

If an artifact is confidential, I also prevent it from appearing in a broadly readable group and restrict backup/support-bundle access. The name and metadata themselves may be sensitive even when the binary is encrypted.

I never run Nexus as the operating-system root account.

---

## 19. How would you troubleshoot a pipeline that fails to publish artifacts to Nexus?

**Answer:**

I start with the exact HTTP status and client error.

| Symptom | Likely areas |
| --- | --- |
| `401` | Missing/invalid credential, wrong auth realm/token |
| `403` | Authenticated but missing add/edit privilege, content selector or policy block |
| `404` | Wrong repository URL/name/path or reverse-proxy routing |
| `400/409` | Invalid package metadata, duplicate/redeploy policy or format-specific conflict |
| `5xx` | Nexus/database/blob-store/internal failure |
| Timeout | DNS, TLS, firewall, reverse proxy, saturation (how close a resource is to its limit) or remote storage latency |

Flow:

1. Confirm the failure is publish, not dependency restore.
2. Record pipeline run, package coordinate, target URL, status and Nexus request ID/time.
3. Verify DNS and TLS chain from the same agent.
4. Check the endpoint is a compatible **hosted** repository.
5. Validate credentials without printing them.
6. Verify repository privileges and content selectors for that exact path.
7. Check release/snapshot version policy and redeploy policy.
8. Confirm package metadata and filename/coordinate.
9. Check Nexus status/writable endpoint, logs, database and blob-store capacity.
10. Compare with the last successful run/configuration.
11. Retry only if evidence shows a temporary failure.

For Docker, I additionally verify the Docker Bearer Token Realm, connector/subdomain, TLS certificate and separate login to the correct endpoint.

For Maven, I check that the `distributionManagement` repository ID matches the `<server>` ID in `settings.xml`.

---

## 20. How do you monitor the health and storage utilization of a Nexus Repository server?

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
- PostgreSQL failures or saturation (how close a resource is to its limit).
- JVM memory/GC pressure.
- Cleanup/backup/task failure.
- Certificate nearing expiry.
- Authentication failures and unusual artifact deletion/download.

I create capacity forecasts rather than waiting for a disk-full outage. Repository size shown in the UI may not include every metadata/index/storage overhead, so underlying blob-store metrics are also required.

---

## 21. How do you handle access control for different development teams in Nexus Repository?

**Answer:**

I design access around teams and actions:

```text
team-orders-developers
  read/browse common groups
  no release write

team-orders-ci
  read group
  add/edit only orders snapshot/release namespace
  no delete/admin

team-payments-ci
  separate hosted namespace and credential

release-managers
  approved promotion operation

repository-operators
  repository/system administration
```

I use:

- Identity-provider groups mapped to Nexus roles.
- Repository-view privileges.
- Content selectors for namespace/path-level separation.
- Separate service accounts for each pipeline/team.
- Environment-specific release permissions.
- Periodic access reviews.
- Immediate leaver/service-account cleanup.

Group repository read permission can expose content of its members through the group, so I do not place restricted artifacts in a broadly readable group.

---

## 22. What are the advantages of using Nexus Repository instead of storing build artifacts directly in Azure DevOps Pipeline Artifacts?

**Answer:**

They solve different problems.

| Nexus Repository | Azure Pipeline Artifact |
| --- | --- |
| Long-lived package repository | Primarily tied to a pipeline run |
| Native Maven/npm/NuGet/Docker/other protocols | General pipeline output transfer/download |
| Hosted, proxy and group behavior | No universal external dependency proxy/group |
| Shared across teams and CI platforms | Closely integrated with Azure Pipelines |
| Package coordinates/version browsing | Run/build-oriented identity |
| Central retention and release policy | Pipeline retention policy |
| Developer package-manager consumption | Excellent between pipeline jobs/stages |

I use Pipeline Artifacts for logs, test results, intermediate files or handoff within an Azure pipeline. I use Nexus for reusable, versioned software packages and centralized dependency proxying.

The two can coexist:

```text
test report -> Azure Pipeline Artifact
approved JAR/npm/NuGet/image -> Nexus Repository
```

---

## 23. How do you configure Maven, Gradle, npm or NuGet clients to use Nexus Repository?

**Answer:**

### Maven

`settings.xml` routes dependency resolution to the group:

```xml
<settings>
  <mirrors>
    <mirror>
      <id>nexus</id>
      <mirrorOf>*</mirrorOf>
      <url>https://nexus.example.com/repository/maven-public/</url>
    </mirror>
  </mirrors>
</settings>
```

Publishing credentials go under a `<server>` whose ID matches `distributionManagement`. Credentials are injected securely rather than committed.

### Gradle

```groovy
repositories {
    maven {
        url = uri("https://nexus.example.com/repository/maven-public/")
        credentials {
            username = System.getenv("NEXUS_USERNAME")
            password = System.getenv("NEXUS_PASSWORD")
        }
    }
}
```

Publishing uses a hosted URL in the `publishing.repositories` configuration, not the read group unless an explicitly supported writable-group feature is used.

### npm

`.npmrc`:

```ini
registry=https://nexus.example.com/repository/npm-group/
always-auth=true
```

Publish to hosted:

```bash
npm publish \
  --registry=https://nexus.example.com/repository/npm-hosted/
```

Use an approved token mechanism and avoid committing `_authToken`.

### NuGet

`nuget.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add
      key="Nexus"
      value="https://nexus.example.com/repository/nuget-group/index.json" />
  </packageSources>
</configuration>
```

Publish:

```bash
dotnet nuget push package.nupkg \
  --source https://nexus.example.com/repository/nuget-hosted/ \
  --api-key "$NEXUS_API_KEY"
```

I verify the Nexus repository's NuGet API version and endpoint. Version 3 group endpoints end in `/index.json`.

---

## 24. How can Nexus Repository improve build performance in an enterprise environment?

**Answer:**

Nexus caches external dependencies near developers and build agents. The first request may go to the remote source; later builds reuse the cached component.

Performance improvements come from:

- Avoiding repeated internet downloads.
- One group endpoint instead of many remote lookups.
- Local high-bandwidth/low-latency access.
- Reduced remote rate-limit exposure.
- Retaining commonly used components.
- Scaling Nexus, PostgreSQL and blob storage for measured traffic.
- Placing Nexus near CI runners and developers or using a supported multi-site design.

I measure:

- Cache hit/miss behavior.
- Download latency.
- Remote fetch latency.
- Nexus CPU/JVM.
- Database latency.
- Blob-store IOPS/throughput.
- Network throughput.
- Client concurrency.

A proxy can also make builds slower if Nexus is undersized, has slow blob/database storage, excessive remote checks or high network latency. Cache settings must balance freshness and performance.

---

## 25. What best practices would you follow when deploying Nexus Repository in Production?

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
- Integrate enterprise identity and least-privilege (minimum required access) roles.
- Separate hosted release, snapshot, proxy and group repositories.
- Disable release redeploy.
- Configure routing rules and approved external remotes.
- Use cleanup policies and capacity alerts.
- Back up database, blobs and configuration consistently.
- Test restore, upgrade and rollback-from-backup procedures.
- Monitor application, JVM, database, blob and infrastructure.
- Patch in a tested maintenance process.
- Pin pipeline clients/endpoints and protect their credentials in Azure Key Vault.
- Scan, sign and retain SBOM/provenance (where an artifact came from and how it was built) for important releases.
- Document ownership, RPO, RTO, escalation and support procedures.

I test representative restore, download, publish and client builds before declaring the service production-ready.

---

## 26. How would you configure high availability or disaster recovery for Nexus Repository?

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

I do not stretch one HA cluster across distant regions because database/blob latency and consistency risk can make it unsupported or unsafe. Cross-region disaster recovery is designed separately through supported backups, replication/content-replication capabilities and a documented failover process.
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

HA reduces node downtime; it does not replace backup or regional DR.

---

## 27. What is the role of Nexus Repository in software supply-chain management?

**Answer:**

Nexus is the controlled distribution point for software inputs and outputs.

It helps establish:

- Which external sources builds may use.
- Which internal artifact coordinate is authoritative.
- Who uploaded and downloaded components.
- Which immutable (not changed after creation) artifact was promoted/deployed.
- Central dependency inventory and usage visibility.
- An enforcement point for routing, access and retention.
- Integration with scanning, policy, SBOM, signatures and provenance (where an artifact came from and how it was built).

Representative flow:

```text
approved source
-> Nexus proxy/group
-> reproducible build
-> SAST/SCA/tests
-> artifact and SBOM
-> sign immutable (not changed after creation) checksum/digest
-> Nexus hosted/staging repository
-> approval/promotion
-> deployment verifies identity and digest
```

Nexus alone does not prove that an artifact is safe. Repository management, Sonatype Firewall/Lifecycle where licensed, CI security checks, signing, admission/deployment verification and incident response work together.

---

## 28. How does Nexus Repository reduce dependency on external package repositories?

**Answer:**

Nexus proxy repositories cache external packages and expose them through an internal group endpoint. Developers and CI systems no longer need direct access to every public repository.

This provides:

- Cached artifacts during some upstream outages.
- Lower external bandwidth.
- Central external-source configuration.
- Reduced exposure to remote rate limits.
- Ability to block or remove an upstream from client access.
- Stable internal URLs.

Limitations:

- An uncached component still requires the upstream.
- Metadata freshness/cache expiry can require upstream access.
- A remote package removed before it is cached may remain unavailable.
- Nexus itself becomes important shared infrastructure and needs HA/DR.
- Cached malware remains malware unless policy detects/blocks it.

For critical dependencies, I ensure release inputs are pinned, cached/hosted according to policy and included in recovery planning.

---

## 29. How do you automate artifact promotion from Development to Production using Nexus Repository?

**Answer:**

I promote an immutable (not changed after creation) artifact; I do not rebuild it for every environment.

Flow:

```text
build exact commit
-> test and scan
-> publish immutable (not changed after creation) candidate
-> record coordinate/checksum/digest
-> deploy candidate to Development
-> integration/UAT/security evidence
-> Production approval
-> Nexus Pro staging/build promotion or controlled repository operation
-> verify destination checksum/digest
-> deploy same artifact
```

The promotion pipeline validates:

- Source coordinate exists.
- Source is immutable (not changed after creation).
- Test/security policy passed.
- Approver is authorized.
- Destination coordinate does not already contain different bytes.
- Source and destination checksum/digest match.
- Release metadata records commit, pipeline and approver.

With Nexus Pro, I use supported staging/build-promotion capabilities when they match the format and process. Without that capability, the pipeline can download once, verify checksum/signature and upload through the supported native/REST interface to a release hosted repository.

It then downloads or queries the destination to verify equality.

For Maven, snapshot and release coordinates differ. I do not simply rename a mutable snapshot and assume it is the tested release; the release workflow must establish the exact immutable (not changed after creation) release bytes and provenance (where an artifact came from and how it was built).

---

## 30. What common issues have you encountered while using Nexus Repository, and how would you troubleshoot them?

**Answer:**

### Authentication and permission failures

Symptoms: `401` or `403`.

I verify credential expiry/token, realm, anonymous policy, user role, repository-view privilege, content selector and whether the request targets the group or a member directly.

### Release cannot be uploaded

I check:

- Snapshot sent to release repository or release sent to snapshot repository.
- Disable-redeploy policy rejecting an existing coordinate.
- Maven server ID mismatch.
- CI user has read but not add/edit.
- Invalid package metadata.

I publish a new version instead of enabling overwrite for an immutable (not changed after creation) release.

### Dependency exists remotely but Nexus returns not found

I check proxy remote URL, remote availability, routing rule, negative cache, metadata/component cache age and repository group membership/order. I invalidate the appropriate cache only with evidence; I do not repeatedly delete all caches.

### Docker login/push fails

I verify Docker Bearer Token Realm, connector/subdomain, TLS/SNI, reverse-proxy headers, registry endpoint, repository write permission and image name.

### npm scope resolves incorrectly

I check `.npmrc`, scoped-registry mapping, group order, authentication and whether publish is going to hosted rather than the read group.

### Nexus becomes read-only or returns 5xx

I inspect writable status, disk/blob capacity, PostgreSQL health/latency, JVM pressure, file descriptors and Nexus logs. I stop unsafe cleanup/retry loops and protect evidence.

### Slow builds

I separate client, Nexus, proxy-remote, database, blob-storage and network latency. I look at cache hits, metadata checks, concurrency, JVM GC and storage I/O rather than assuming the public repository is slow.

### Cleanup does not free disk

Cleanup may have soft-deleted components without compacting the blob store. I verify policy/task results, recovery-retention settings and schedule safe compaction after backup validation.

### Artifact is present but cannot be downloaded through a group

I check group member order, group read/browse privilege, content selector and format compatibility. Direct member permission and group permission are separate.

### General troubleshooting discipline

I collect:

```text
timestamp
pipeline/build ID
client and version
repository URL/type/format
artifact coordinate
HTTP status and request ID
Nexus version
recent configuration/deployment changes
server, database and blob-store health
```

Then I reproduce with the same client from the same network using a non-secret verbose mode, compare Nexus/reverse-proxy logs and fix the root cause. I avoid deleting caches, changing permissions to wildcard or restarting Nexus repeatedly without evidence.

---

## Concise interview summary

Sonatype Nexus Repository is a centralized repository manager used to host internal build artifacts, proxy public dependencies and expose multiple repositories through group endpoints.

In my Azure CI/CD flow, Maven, npm, NuGet or Docker clients download through a Nexus group; only protected main/release pipelines publish versioned artifacts to hosted repositories.
I separate snapshots from immutable (not changed after creation) releases, disable release redeployment, capture checksums/digests and promote the same tested artifact rather than rebuilding it.

Azure DevOps, Jenkins and GitHub Actions use dedicated least-privilege (minimum required access) Nexus identities whose credentials are protected through Azure Key Vault or the CI/CD platform's protected secret mechanism.
For Production, I secure Nexus with TLS, private network access, enterprise authentication where available, RBAC/content selectors, logging, cleanup policies, capacity monitoring and coordinated database/blob-store backups.

Nexus Pro is selected when the project requires capabilities such as supported HA, Azure Blob Store, enterprise SSO, staging/promotion or repository import/export.
When troubleshooting, I start with the HTTP status, exact repository type/URL and artifact coordinate, then check authentication, privilege, release/snapshot and redeploy policies, client configuration, TLS/network, database, blob storage and Nexus logs.
