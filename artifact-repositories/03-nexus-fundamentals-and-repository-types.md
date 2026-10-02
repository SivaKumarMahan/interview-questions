# Artifact Repositories: Nexus Fundamentals and Repository Types

> What Sonatype Nexus Repository is, hosted, proxy, and group repositories, supported formats, OSS versus Pro, and why teams use it.

## Key Concepts

### Nexus in an Azure-Focused CI/CD Project Model

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

### Sonatype Nexus Repository

Sonatype Nexus Repository is a popular universal repository manager and a common alternative to JFrog Artifactory. Current Sonatype documentation provides Community and Professional editions and supports a broad set of repository formats.

Supported formats include:

- Docker/OCI.
- Maven.
- Helm.
- npm.
- NuGet.
- PyPI.
- Yum and Apt.
- Rust/Cargo.
- Conan.
- Ansible.
- Go.
- Raw/generic files.
- Additional language and operating-system package formats.

The exact hosted, proxy and group capabilities depend on the format and product version.

Nexus works with Azure DevOps, Jenkins, GitHub Actions, GitLab CI, Bitbucket-based workflows and other CI/CD systems through native package clients, plugins and REST APIs.

#### Repository types

- **Hosted:** Stores internal packages and approved uploaded content.
- **Proxy:** Caches content retrieved from an external repository.
- **Group:** Combines compatible hosted, proxy and group repositories behind one endpoint.

Example:

```text
maven-releases hosted
maven-snapshots hosted
maven-central-proxy
        \   |   /
      maven-public group
```

Developers normally download through `maven-public`; authorized CI pipelines publish to the relevant hosted repository.

#### When to select Nexus Repository

Choose it when:

- The organization needs a self-hosted repository manager.
- Java, Maven and related package ecosystems are heavily used.
- A central proxy/cache for public dependencies is required.
- The organization wants an alternative to JFrog.
- Community Edition meets a smaller deployment's needs.
- Professional capabilities such as supported HA, staging/build promotion, enterprise SSO, repository import/export or Azure Blob Store are required and licensed.

#### Strong interview answer

> Nexus Repository is a centralized repository manager. It hosts internal artifacts, proxies external dependencies, and exposes repository groups through stable URLs. I typically use hosted repositories for organization-owned packages, proxy repositories for public dependencies, and group repositories for developer consumption. CI publishes versions that never change afterward, and downstream environments promote and deploy that same checksum or digest.

Don't confuse Nexus Repository with the separately licensed Sonatype supply-chain products. Check vulnerability policy, isolation, and lifecycle capabilities against the actual Nexus/Sonatype licenses in use, not against what the product line as a whole can do.

### Concise Interview Summary: Nexus Repository

Sonatype Nexus Repository is a centralized repository manager. It hosts internal build artifacts, proxies public dependencies, and exposes multiple repositories through group endpoints.

In my Azure CI/CD flow, Maven, npm, NuGet and Docker clients all download through a Nexus group. Only protected main or release pipelines publish versioned artifacts to hosted repositories. I keep snapshots separate from immutable releases, disable release redeployment, capture checksums and digests, and promote the same tested artifact instead of rebuilding it for each environment.

Azure DevOps, Jenkins and GitHub Actions each use a dedicated least-privilege Nexus identity, and its credentials are protected through Azure Key Vault or the platform's own protected secret mechanism.

For Production, I secure Nexus with TLS, private network access, enterprise authentication where it's available, RBAC and content selectors, logging, cleanup policies, capacity monitoring, and coordinated database and blob-store backups.

Nexus Pro comes into play when the project needs capabilities such as supported HA, Azure Blob Store, enterprise SSO, staging and promotion, or repository import and export.

When troubleshooting, I start with the HTTP status, the exact repository type and URL, and the artifact coordinate. From there I check authentication, privilege, release/snapshot and redeploy policies, client configuration, TLS and network, the database, blob storage, and the Nexus logs.

## Interview Questions

### 1. What is Sonatype Nexus Repository, and why is it used in CI/CD pipelines?

**Answer:**

Sonatype Nexus Repository is a repository manager. It stores, proxies, organizes and distributes software components such as Maven packages, npm packages, NuGet packages, Python packages, Helm charts and container images.

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

Nexus should store build artifacts that are immutable, meaning they never change once created. It should not store source code. Git stays the source-code system. The CI/CD platform stays responsible for building, testing, approving and deploying.

### 2. What are the different repository types available in Nexus Repository?

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

### 3. What is the difference between Hosted, Proxy and Group repositories in Nexus?

**Answer:**

| Type | Purpose | Read behavior | Write behavior | Example |
| --- | --- | --- | --- | --- |
| Hosted | Store organization-owned or approved uploaded components | Reads local content | CI publishes here | `maven-releases` |
| Proxy | Cache a remote repository | Serves cache or fetches from remote | Clients do not publish internal builds here | `maven-central-proxy` |
| Group | Combined compatible repositories behind one URL | Searches members in configured order | Normally read-only; some Pro formats support a selected writable member | `maven-public` |

A proxy cache is controlled by component and metadata cache-age settings. Nexus checks the local cache first and consults the remote source when required.

A group simplifies client configuration, but member order matters. If two members contain the same coordinate, the first matching repository wins.

I put trusted internal sources and proxies in a deliberate order. I also use routing rules and content governance to cut the risk of dependency confusion, where a malicious public package with the same name could get pulled in instead of the internal one.

Permissions on a group endpoint allow users to consume member content through that group. They do not automatically grant direct access to every member URL.

### 4. What is the purpose of a Repository Group in Nexus?

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

### 5. How does Nexus Repository act as a proxy for public repositories such as Maven Central or npm?

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

Nexus uses maximum-age settings on components and metadata to decide when cached data needs revalidating. It also has a negative cache: if a request 404s, Nexus remembers that for a while, so a component published to the remote right after can take a bit longer to show up.

Benefits include:

- Fewer repeated external downloads.
- Faster builds near the Nexus server.
- Reduced internet egress.
- A central allow/deny and routing point.
- Some resilience when the remote service is unavailable, but only for already cached content.
- Visibility into which components the organization consumes.

I restrict Nexus outbound access to approved registries and use TLS validation. A proxy does not mean every remote component is safe; vulnerability, license, signature and policy controls remain necessary.

### 6. How does Nexus Repository reduce dependency on external package repositories?

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

### 7. What package formats are supported by Sonatype Nexus Repository?

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

Which formats support hosted, proxy and group repositories can differ by Nexus edition and release. In an interview, I talk about the formats relevant to the project — Maven, npm, NuGet, Docker and Helm — and then check the exact version matrix rather than assuming every format supports every repository type.

### 8. What is the difference between Nexus Repository OSS and Nexus Repository Pro?

**Answer:**

The offering historically called OSS is now called **Community Edition** in the current documentation. The licensed enterprise offering is **Professional Edition**. Exact packaging and entitlement can change over time, so I confirm the version-specific feature matrix during design rather than assuming.

Community Edition provides the core repository-manager capabilities needed to host, proxy and group the supported formats.

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

Sonatype's Repository Firewall, Lifecycle and IQ supply-chain policy tools may be separate products or licenses. I do not assume every vulnerability or quarantine feature is automatically included in Nexus Pro.

The choice comes down to availability targets, identity needs, storage, promotion workflow, support and compliance requirements. It is not just about how many artifacts you store.
