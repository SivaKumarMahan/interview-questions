# Artifact Repositories: Pipeline Artifacts, Versioning, and Promotion

> Publishing and consuming pipeline artifacts, handling large artifacts, snapshot versus release versioning, and promoting the same artifact across environments.

## Key Concepts

### Package promotion principle

The selected product may call the mechanism a feed view, staging, promotion, release repository or another term. The design principle remains:

```text
build once
-> assign a version that will not change
-> test and scan
-> publish once
-> record checksum/digest
-> promote visibility/status
-> deploy the same bytes to every environment
```

Promotion must never rebuild the package. For containers, promotion and deployment should preserve the same OCI digest all the way through.

## Interview Questions

<details><summary>Q1. [Basic] Artifacts in Azure DevOps</summary>

**A:** In Azure DevOps, artifacts refer to the files or packages produced as a result of a build or release pipeline. They can include compiled code, binaries, libraries, configuration files, or any other output that needs to be stored and shared for deployment or further processing.

Azure DevOps provides a built-in artifact management system that allows teams to publish, store, and consume artifacts efficiently.

Artifacts in Azure DevOps are typically managed through the following features:

1. **Build Artifacts**: During a build pipeline, you can define tasks to publish artifacts. These artifacts are then stored in the Azure DevOps server and can be downloaded or used in subsequent stages of the pipeline.
2. **Release Artifacts**: In a release pipeline, you can consume artifacts produced by build pipelines. These artifacts can be deployed to various environments as part of the release process.
3. **Artifact Feeds**: Azure Artifacts is a service within Azure DevOps that allows you to create and manage package feeds. You can publish and consume packages (like NuGet, npm, Maven, etc.) within your organization, making it easier to share code and dependencies across teams.
4. **Retention Policies**: Azure DevOps allows you to set retention policies for artifacts, helping you manage storage by automatically deleting old or unused artifacts based on defined criteria.

To publish artifacts in a build pipeline, you can use the **"Publish Build Artifacts"** task. Here's an example of how to publish artifacts in a YAML pipeline:

```yaml
trigger:
  - main
pool:
  vmImage: 'ubuntu-latest'
steps:
  - task: Maven@3
    inputs:
      mavenPomFile: 'pom.xml'
      goals: 'package'
  - task: PublishBuildArtifacts@1
    inputs:
      PathtoPublish: '$(Build.ArtifactStagingDirectory)'
      ArtifactName: 'drop'
      publishLocation: 'Container'
```

In this example, after building a Maven project, the build artifacts are published to the Azure DevOps server under the name `drop`.

Overall, Azure DevOps provides a robust system for managing artifacts, enabling teams to streamline their CI/CD processes and ensure that the right files are available for deployment and distribution.

</details>

<details><summary>Q2. [Intermediate] How do you publish and consume artifacts in Azure DevOps?</summary>

**Answer:**

The build stage creates a tested artifact once and publishes it with version, commit SHA, checksum, and retention. Deployment stages download that exact artifact rather than rebuilding.

```yaml
- publish: $(Build.ArtifactStagingDirectory)
  artifact: application

- download: current
  artifact: application
```

Pipeline artifacts suit build outputs; Azure Artifacts feeds host NuGet, npm, Maven, Python, and Universal Packages. Container images go to a registry such as ACR.

I restrict write permissions, scan/sign artifacts, avoid secrets, and clean by retention policy. During investigation I verify artifact ID/digest and that the deployed environment used the same version tested in staging.

</details>

<details><summary>Q3. [Intermediate] How do you handle large artifacts efficiently in pipelines?</summary>

**A:** Handling large artifacts efficiently in pipelines requires a combination of strategies to optimize storage, transfer, and processing. Here are some best practices to manage large artifacts effectively:

1. **Use Artifact Repositories**: Instead of storing large artifacts directly in the pipeline, use dedicated artifact repositories like Azure Artifacts, Nexus, or Artifactory. These repositories are optimized for storing and managing large files and packages.
2. **Compress Artifacts**: Before publishing artifacts, compress them using formats like ZIP or TAR. This reduces the size of the files being transferred and stored, leading to faster uploads and downloads.
3. **Incremental Builds**: Implement incremental builds to avoid rebuilding and republishing unchanged artifacts. This can significantly reduce the size of artifacts and the time taken to process them.
4. **Use Caching**: Leverage caching mechanisms to store frequently used dependencies and artifacts. This can speed up build times and reduce the need to download large files repeatedly.
5. **Split Artifacts**: If possible, split large artifacts into smaller, more manageable pieces. This allows for parallel processing and reduces the impact of failures during transfers.
6. **Optimize Network Transfers**: Use efficient protocols for transferring large files, such as HTTP/2 or FTP, and consider using Content Delivery Networks (CDNs) to distribute artifacts closer to the deployment targets.
7. **Set Retention Policies**: Implement retention policies to automatically delete old or unused artifacts. This helps manage storage costs and keeps the artifact repository clean.
8. **Monitor and Analyze**: Regularly monitor artifact sizes and transfer times. Use this data to identify bottlenecks and optimize the pipeline accordingly.
9. **Use Streaming**: For very large artifacts, consider using streaming techniques to process data in chunks rather than loading the entire artifact into memory at once.
10. **Parallel Downloads**: If your pipeline supports it, implement parallel downloads for large artifacts to speed up the retrieval process.

By following these strategies, you can efficiently manage large artifacts in your pipelines, ensuring smooth and reliable CI/CD processes.

</details>

<details><summary>Q4. [Intermediate] How do you handle large artifacts efficiently in Azure Pipelines?</summary>

**Answer:**

I first work out why the artifact is large and whether every file in it is actually needed for deployment. I remove build caches and debug output, use package or container registries instead of raw file transfer, compress suitable content, split independent packages, and cache dependencies incrementally rather than rebuilding the whole artifact.

Artifacts get explicit retention rules and versions that don't change once published. I place agents and storage close to consumers where possible, and I only use parallel downloads if the tooling supports it and it actually helps.

I monitor upload/download time, size trend, storage cost, and deployment time.

For very large datasets or VM images, I use the appropriate storage/image service and pass a versioned reference through the pipeline rather than transferring it as a normal pipeline artifact.

</details>

<details><summary>Q5. [Intermediate] How do you implement versioning and release management using Nexus Repository?</summary>

**Answer:**

I use a documented version strategy appropriate to the package format:

- Maven snapshot: `2.4.0-SNAPSHOT`.
- Maven release: `2.4.0`.
- Semantic version: `MAJOR.MINOR.PATCH`.
- Pre-release: `2.5.0-rc.1`.
- Docker readable tag: release version and/or Git commit.
- Docker immutable identity: digest.

Release rules:

1. The source commit is immutable and reviewed.
2. CI generates the version from the release process.
3. Tests, quality and security gates complete.
4. CI publishes once to the correct hosted repository.
5. Release repositories use a disable-redeploy policy where appropriate.
6. The artifact checksum/digest is recorded.
7. Environments receive the same artifact; they do not rebuild it.
8. Release notes link version, commit, pipeline and artifact.

I avoid overwriting a released coordinate. If `2.4.0` is incorrect, I publish `2.4.1`; I do not silently replace `2.4.0`.

Nexus Pro's staging and build-promotion features can formalize this process. On other editions, the pipeline can do controlled publication and promotion itself through the repository APIs. Either way, it must verify that the source and destination bytes and checksums are identical.

</details>

<details><summary>Q6. [Basic] What are snapshot and release repositories, and why are they kept separate?</summary>

**Answer:**

Snapshots represent work in progress. Releases represent approved, immutable versions.

| Property | Snapshot | Release |
| --- | --- | --- |
| Example | `2.4.0-SNAPSHOT` | `2.4.0` |
| Stability | May change as development continues | Must remain immutable |
| Retention | Aggressive cleanup is normal | Retain according to deployment/compliance policy |
| Redeploy | Often permitted by snapshot policy | Normally disabled |
| Consumer | Development/test | Controlled release consumers |

Maven can turn a snapshot into timestamped snapshot artifacts internally, while the logical `-SNAPSHOT` version stays the same.

Keeping them separate stops an unstable build from being mistaken for a release. It also lets each side have its own retention, write access and deployment policy. Production should never resolve an unpinned snapshot.

</details>

<details><summary>Q7. [Intermediate] How do you automate artifact promotion from Development to Production using Nexus Repository?</summary>

**Answer:**

I promote one immutable artifact through the environments. I do not rebuild it for each one.

Flow:

```text
build exact commit
-> test and scan
-> publish immutable candidate
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
- Source is immutable.
- Test/security policy passed.
- Approver is authorized.
- Destination coordinate does not already contain different bytes.
- Source and destination checksum/digest match.
- Release metadata records commit, pipeline and approver.

With Nexus Pro, I use supported staging/build-promotion capabilities when they match the format and process. Without that capability, the pipeline can download once, verify checksum/signature and upload through the supported native/REST interface to a release hosted repository.

It then downloads or queries the destination to verify equality.

For Maven, snapshot and release coordinates are different things. I do not just rename a mutable snapshot and call it the tested release. The release workflow has to establish the exact immutable release bytes and their provenance in its own right.

</details>
