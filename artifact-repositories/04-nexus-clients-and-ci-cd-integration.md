# Artifact Repositories: Nexus Clients and CI/CD Integration

> Configuring Maven, Gradle, npm, NuGet, and Docker clients for Nexus, and publishing from Azure DevOps, Jenkins, and GitHub Actions.

## Interview Questions

### 1. How do you configure Maven, Gradle, npm or NuGet clients to use Nexus Repository?

**Answer:**

#### Maven

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

#### Gradle

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

#### npm

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

#### NuGet

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

### 2. How do developers consume artifacts stored in Nexus Repository?

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

### 3. How do you upload Docker images to Nexus Repository?

**Answer:**

First I create a Docker hosted repository and set up a connector or subdomain endpoint for it. Then I enable the Docker Bearer Token Realm, apply TLS, and grant the CI user upload privileges.

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
- Use immutable version tags or digests; do not rely on `latest`.
- Enable the Docker Bearer Token Realm.
- Separate pull endpoints/groups from write endpoints unless an approved Pro writable-group design is used.

### 4. How do you integrate Nexus Repository with Azure DevOps, Jenkins or GitHub Actions?

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

#### Azure DevOps

- Store the Nexus credential in Azure Key Vault/protected secret variables.
- Inject it only into the publishing step.
- Use Maven/Gradle/npm/NuGet/Docker native commands.
- Do not expose publishing credentials to pull-request validation.

#### Jenkins

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

The credential is folder-scoped. The job runs on an isolated agent. Command tracing is turned off around the secret use. I do not rely on Jenkins's log masking as protection against malicious pipeline code — masking hides a secret from the log, it does not stop a script from misusing it.

#### GitHub Actions

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

For release publishing, I use a protected GitHub Environment. I restrict which reviewers and branches can trigger it, and I pin actions to reviewed commits.

If Nexus is integrated with an enterprise identity/token broker, I prefer short-lived credentials. Otherwise I rotate the dedicated Nexus token/password through Azure Key Vault and keep its repository permissions minimal.

### 5. How would you configure Azure DevOps to publish artifacts to Nexus Repository?

**Answer:**

For a Maven project, I configure:

1. A least-privilege Nexus CI service account — one that only gets the access it actually needs, nothing more.
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

In a real pipeline I prefer one Maven invocation, such as `mvn clean deploy`, run after all required gates pass. Alternatively I deliberately preserve the exact tested workspace and artifact. Either way, I make sure the publish step never accidentally recompiles and ships different bytes than what was tested.

The CI identity gets `add/edit` only on the required hosted repository. It does not get Nexus administration or delete permission. Pull-request pipelines never get publishing credentials at all.

### 6. How can Nexus Repository improve build performance in an enterprise environment?

**Answer:**

Nexus caches external dependencies near developers and build agents. The first request may still go out to the remote source, but later builds reuse the cached copy instead.

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

A proxy can also make builds slower. That happens if Nexus is undersized, its blob or database storage is slow, it does too many remote checks, or network latency is high. Cache settings need to balance freshness against performance.
