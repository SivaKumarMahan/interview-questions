# Artifact Repositories: Fundamentals and Repository Selection

> What an artifact repository is, how it differs from source control, CI/CD, and container registries, and how to choose between Azure Artifacts, Artifactory, Nexus, and GitHub Packages.

## Key Concepts

### What an Artifact Repository Is

An artifact repository stores, versions, and distributes the outputs of a software build. Once a version is published, it doesn't change. It is different from:

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

### Quick comparison

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

### Selection examples

#### Azure DevOps Java project

```text
Source: Azure Repos
CI/CD: Azure Pipelines
Java packages: Azure Artifacts Maven feed
Container images: Azure Container Registry
Deployment: Helm to AKS
```

This minimizes external tooling and integrates with Azure permissions and pipelines.

#### Large multi-language enterprise

```text
Source: multiple Git platforms
CI/CD: Azure DevOps + Jenkins + GitHub Actions + GitLab CI
Packages: Maven + npm + NuGet + PyPI + Helm + containers
Repository: JFrog Artifactory or Nexus Repository
```

The decision between Artifactory and Nexus depends on formats, enterprise identity, HA/DR, multi-site requirements, promotion, security integrations, support and cost.

#### GitHub-native product

```text
Source: GitHub
CI/CD: GitHub Actions
Packages: GitHub Packages
Containers: GitHub Container Registry or ACR when Azure deployment policy requires it
Deployment: Protected GitHub Environment to Azure/AKS
```

### Concise Interview Answer: Choosing an Artifact Repository

I select an artifact repository from the organization's technology and operating model rather than choosing one product for every case.

For an Azure DevOps-focused organization, I use Azure Artifacts for supported package feeds and Universal Packages, while container images go to Azure Container Registry. Azure Artifact views support controlled package visibility and promotion.

For a large multi-language and multi-CI/CD enterprise, I evaluate JFrog Artifactory or Sonatype Nexus Repository. Artifactory offers a broad universal-repository ecosystem with local, remote, virtual and federated models.

Nexus provides hosted, proxy and group repositories and is a strong choice for self-hosting, Maven-heavy environments and centralized dependency caching.

When source code and automation are primarily in GitHub, GitHub Packages can reduce the number of external tools for supported formats and container packages.

Whatever tool is involved, the approach stays the same: build once, publish a version that won't change, record its checksum or digest, promote that same artifact through every environment, protect publishing with only the permissions people actually need, and keep backup and recovery procedures tested.

## Interview Questions

<details><summary>Q1. [Basic] What are the advantages of using Nexus Repository instead of storing build artifacts directly in Azure DevOps Pipeline Artifacts?</summary>

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

</details>
