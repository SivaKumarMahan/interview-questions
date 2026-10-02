# Artifact Repositories: Azure Artifacts, JFrog Artifactory, and GitHub Packages

> How Azure Artifacts, JFrog Artifactory, and GitHub Packages work and when to select each one.

## Key Concepts

### Azure Artifacts

Azure Artifacts is usually the best choice when the organization is built around Azure DevOps and needs package feeds without running a separate repository platform.

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

#### Example flow

```text
source code
-> Azure Pipeline build and tests
-> create application.zip
-> publish application.zip as Universal Package version 2.5.1
-> deploy 2.5.1 to Development
-> promote the same 2.5.1 to the approved feed view
-> deploy the same package version to QA and Production
```

The application is built once. QA and Production receive that same unchanging version rather than a rebuilt ZIP.

Feed views change package visibility; they do not create a different package binary. Packages are published to the base feed and can then be promoted.

Azure Artifacts does not support demoting a package from a view, so promotion is treated as a controlled release decision.

#### Universal Package example

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

#### When to select Azure Artifacts

Choose it when:

- Azure Repos and Azure Pipelines are the primary delivery platform.
- The required package formats are supported.
- Teams want managed feeds with minimal separate infrastructure.
- Azure DevOps permissions and project organization match the governance model.
- The organization does not need the broader repository formats or cross-platform repository capabilities of Artifactory or Nexus.

#### Important container distinction

For containerized applications, use **Azure Container Registry (ACR)** rather than Azure Artifacts:

```text
JAR, npm, NuGet or Universal Package -> Azure Artifacts
Docker/OCI image                     -> Azure Container Registry
```

ACR provides container/OCI-specific storage, manifests, tags, digests and AKS integration.

### JFrog Artifactory

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
- **Federated:** Synchronizes content and metadata across multiple Artifactory deployments, following whichever topology is supported.

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

#### When to select JFrog Artifactory

Choose it when:

- The enterprise uses many package technologies.
- Teams operate across multiple CI/CD platforms or clouds.
- One central artifact platform is required across business units.
- Repository federation/multi-site patterns are important.
- Advanced metadata, promotion, traceability and security-platform integration are required.
- The organization can support the licensing and operational model.

#### Strong interview answer

> For a large enterprise with multiple technologies and delivery platforms, I would consider JFrog Artifactory. It gives you one central repository for many artifact formats, both hosted and proxied dependencies, unified client endpoints, metadata, and traceability and security integration. I'd still check licensing, supported formats, availability requirements, and operational cost against Nexus and managed cloud alternatives before deciding.

Supporting many formats doesn't automatically make Artifactory the right choice. The decision also has to weigh scale, team skills, high availability, disaster recovery, security, support, and total cost.

### GitHub Packages

GitHub Packages is a good choice when the development workflow is already centered on GitHub repositories and GitHub Actions.

Common package registries include:

- npm.
- Maven.
- Gradle.
- NuGet.
- RubyGems.
- Container/OCI packages through GitHub Container Registry.

Packages can be associated with a repository, user or organization depending on the registry and permission model. Some package types inherit repository permissions, while others support more detailed package permissions.

Representative flow:

```text
GitHub repository
-> pull-request checks
-> GitHub Actions build/test/scan
-> publish versioned package or container digest
-> protected GitHub Environment approval
-> deploy the same package/digest
```

#### When to select GitHub Packages

Choose it when:

- Source code is hosted in GitHub.
- GitHub Actions is the primary CI/CD platform.
- Packages should be closely associated with repositories or organizations.
- The required package formats are supported.
- The team wants fewer external platforms.
- GitHub permissions, billing, retention and networking meet enterprise requirements.

GitHub Packages is less suitable when the organization needs a broad universal repository manager, extensive proxy/group behavior across many ecosystems, or repository services shared equally across several unrelated source-control platforms.
