# Artifact Repository Summary

An artifact repository stores, versions and distributes the immutable outputs of a software build. It is different from:

- **Source control:** Stores source code and change history.
- **CI/CD system:** Builds, tests, approves and deploys software.
- **Pipeline artifact:** Transfers files between jobs/stages or retains output from a particular pipeline run.
- **Package repository:** Provides long-lived, package-manager-native storage and version resolution.
- **Container registry:** Stores OCI/container images and manifests.

The main selection rule is:

```text
Azure DevOps-native package feeds -> Azure Artifacts
Azure container images            -> Azure Container Registry
Multi-platform universal repo     -> JFrog Artifactory or Nexus Repository
GitHub-native packages/images     -> GitHub Packages
```

---

## 1. Azure Artifacts

Azure Artifacts is normally the best choice when the organization is strongly centered on Azure DevOps and needs package feeds without operating a separate repository platform.

It supports:

- NuGet.
- npm.
- Maven.
- Python.
- Cargo.
- Universal Packages.

Core capabilities include:

- Organization- or project-scoped feeds.
- Direct Azure Pipelines integration.
- Upstream sources for approved public or internal package feeds.
- Feed permissions.
- Package versioning.
- Views such as `@Local`, `@Prerelease` and `@Release`.
- Package promotion between views.
- Retention policies.

### Example flow

```text
source code
-> Azure Pipeline build and tests
-> create application.zip
-> publish application.zip as Universal Package version 2.5.1
-> deploy 2.5.1 to Development
-> promote the same 2.5.1 to the approved feed view
-> deploy the same package version to QA and Production
```

The application is built once. QA and Production receive the same immutable version rather than rebuilding the ZIP.

Feed views change package visibility; they do not create a different package binary. Packages are published to the base feed and can then be promoted. Azure Artifacts does not support demoting a package from a view, so promotion is treated as a controlled release decision.

### Universal Package example

```bash
az artifacts universal publish \
  --organization https://dev.azure.com/<organization> \
  --project <project> \
  --scope project \
  --feed application-packages \
  --name orders-application \
  --version 2.5.1 \
  --path ./package
```

### When to select Azure Artifacts

Choose it when:

- Azure Repos and Azure Pipelines are the primary delivery platform.
- The required package formats are supported.
- Teams want managed feeds with minimal separate infrastructure.
- Azure DevOps permissions and project organization match the governance model.
- The organization does not need the broader repository formats or cross-platform repository capabilities of Artifactory or Nexus.

### Important container distinction

For containerized applications, use **Azure Container Registry (ACR)** rather than Azure Artifacts:

```text
JAR, npm, NuGet or Universal Package -> Azure Artifacts
Docker/OCI image                     -> Azure Container Registry
```

ACR provides container/OCI-specific storage, manifests, tags, digests and AKS integration.

---

## 2. JFrog Artifactory

JFrog Artifactory is a widely recognized enterprise universal repository manager. It is useful when a large organization has many technologies, delivery platforms, teams and locations.

JFrog documents a broad set of integrated package types and repository capabilities. Common formats include:

- Docker/OCI images.
- Helm charts.
- Maven and Gradle packages.
- npm packages.
- NuGet packages.
- PyPI packages.
- Generic ZIP, TAR, JAR and binary files.

Repository types include:

- **Local:** Stores internally produced artifacts.
- **Remote:** Proxies and caches an external repository.
- **Virtual:** Aggregates compatible local and remote repositories behind one client URL.
- **Federated:** Synchronizes repository content and metadata across multiple Artifactory deployments according to the supported topology.

Representative design:

```text
maven-local
maven-snapshots-local
maven-central-remote
        \   |   /
      maven-virtual
           |
  developers and CI systems
```

### When to select JFrog Artifactory

Choose it when:

- The enterprise uses many package technologies.
- Teams operate across multiple CI/CD platforms or clouds.
- One central artifact platform is required across business units.
- Repository federation/multi-site patterns are important.
- Advanced metadata, promotion, traceability and security-platform integration are required.
- The organization can support the licensing and operational model.

### Strong interview answer

> For a large enterprise with multiple technologies and delivery platforms, I would consider JFrog Artifactory because it provides a central repository for many artifact formats, hosted and proxied dependencies, unified client endpoints, metadata, traceability and security integration. I would still validate licensing, supported formats, availability requirements and operational cost against Nexus and managed cloud alternatives.

Artifactory is not automatically the best option only because it supports many formats. The decision must include scale, team skills, high availability, disaster recovery, security, support and total cost.

---

## 3. Sonatype Nexus Repository

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

### Repository types

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

### When to select Nexus Repository

Choose it when:

- The organization needs a self-hosted repository manager.
- Java, Maven and related package ecosystems are heavily used.
- A central proxy/cache for public dependencies is required.
- The organization wants an alternative to JFrog.
- Community Edition meets a smaller deployment's needs.
- Professional capabilities such as supported HA, staging/build promotion, enterprise SSO, repository import/export or Azure Blob Store are required and licensed.

### Strong interview answer

> Nexus Repository is a centralized repository manager that hosts internal artifacts, proxies external dependencies and exposes repository groups through stable URLs. I commonly use hosted repositories for organization-owned packages, proxy repositories for public dependencies and group repositories for developer consumption. CI publishes immutable versions, while downstream environments promote and deploy the same checksum or digest.

Nexus Repository should not be confused with separately licensed Sonatype supply-chain products. Vulnerability policy, quarantine and lifecycle capabilities must be validated against the actual Nexus/Sonatype licenses in use.

---

## 4. GitHub Packages

GitHub Packages is a good choice when the development workflow is already centered on GitHub repositories and GitHub Actions.

Common package registries include:

- npm.
- Maven.
- Gradle.
- NuGet.
- RubyGems.
- Container/OCI packages through GitHub Container Registry.

Packages can be associated with a repository, user or organization depending on the registry and permission model. Some package types inherit repository permissions, while others support more granular package permissions.

Representative flow:

```text
GitHub repository
-> pull-request checks
-> GitHub Actions build/test/scan
-> publish versioned package or container digest
-> protected GitHub Environment approval
-> deploy the same package/digest
```

### When to select GitHub Packages

Choose it when:

- Source code is hosted in GitHub.
- GitHub Actions is the primary CI/CD platform.
- Packages should be closely associated with repositories or organizations.
- The required package formats are supported.
- The team wants fewer external platforms.
- GitHub permissions, billing, retention and networking meet enterprise requirements.

GitHub Packages is less suitable when the organization requires a broad universal repository manager, extensive proxy/group behavior across many ecosystems, or repository services shared equally by several unrelated source-control platforms.

---

## Quick comparison

| Capability | Azure Artifacts | JFrog Artifactory | Nexus Repository | GitHub Packages |
| --- | --- | --- | --- | --- |
| Best fit | Azure DevOps-centric teams | Large multi-technology enterprise | Self-hosted/universal repository, strong Maven use | GitHub-centric teams |
| Managed option | Azure DevOps service | JFrog cloud option | Nexus Repository Cloud option; self-hosting common | GitHub service |
| Internal packages | Yes | Yes | Yes | Yes |
| External dependency proxy | Upstream sources | Remote repositories | Proxy repositories | More limited than a universal repository manager |
| Unified endpoint | Feed/upstream model | Virtual repository | Group repository | Registry/package endpoint model |
| Generic binaries | Universal Packages | Generic repository | Raw repository | Release assets may be a separate GitHub feature |
| Containers | Use ACR for Azure design | Supported | Supported | GitHub Container Registry |
| Cross-CI/CD use | Possible, Azure-native | Strong | Strong | Best with GitHub |
| Self-hosted repository | Azure DevOps Server scenarios vary | Available | Available | GitHub Enterprise capabilities vary |
| Enterprise HA/promotion | Managed service behavior | Licensed capability | Primarily Professional capabilities | Managed platform/environment workflow |

Always verify the current edition, supported package format, repository type, retention, geographic availability and license before selecting a product.

---

## Package promotion principle

The selected product may call the mechanism a feed view, staging, promotion, release repository or another term. The design principle remains:

```text
build once
-> assign immutable version
-> test and scan
-> publish once
-> record checksum/digest
-> promote visibility/status
-> deploy the same bytes to every environment
```

Promotion must not rebuild the package. For containers, promotion and deployment should preserve the immutable OCI digest.

---

## Selection examples

### Azure DevOps Java project

```text
Source: Azure Repos
CI/CD: Azure Pipelines
Java packages: Azure Artifacts Maven feed
Container images: Azure Container Registry
Deployment: Helm to AKS
```

This minimizes external tooling and integrates with Azure permissions and pipelines.

### Large multi-language enterprise

```text
Source: multiple Git platforms
CI/CD: Azure DevOps + Jenkins + GitHub Actions + GitLab CI
Packages: Maven + npm + NuGet + PyPI + Helm + containers
Repository: JFrog Artifactory or Nexus Repository
```

The decision between Artifactory and Nexus depends on formats, enterprise identity, HA/DR, multi-site requirements, promotion, security integrations, support and cost.

### GitHub-native product

```text
Source: GitHub
CI/CD: GitHub Actions
Packages: GitHub Packages
Containers: GitHub Container Registry or ACR when Azure deployment policy requires it
Deployment: Protected GitHub Environment to Azure/AKS
```

---

## Concise interview answer

I select an artifact repository from the organization's technology and operating model rather than choosing one product for every case.

For an Azure DevOps-focused organization, I use Azure Artifacts for supported package feeds and Universal Packages, while container images go to Azure Container Registry. Azure Artifact views support controlled package visibility and promotion.

For a large multi-language and multi-CI/CD enterprise, I evaluate JFrog Artifactory or Sonatype Nexus Repository. Artifactory offers a broad universal-repository ecosystem with local, remote, virtual and federated models. Nexus provides hosted, proxy and group repositories and is a strong choice for self-hosting, Maven-heavy environments and centralized dependency caching.

When source code and automation are primarily in GitHub, GitHub Packages can reduce the number of external tools for supported formats and container packages.

Irrespective of the tool, I build once, publish an immutable version, record its checksum or digest, promote the same artifact through environments, protect publishing with least privilege and retain tested backup and recovery procedures.
