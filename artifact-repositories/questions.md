## Q. Which container registry should you trust for production images?

**Answer:**

I trust an organization-approved registry, not an image just because it is public or popular.

The registry needs strong identity controls and repositories locked down to the minimum access people actually need. It also needs TLS and encryption, tags that can't be changed after creation (or deployment by digest instead of tag), vulnerability scanning, audit logs, retention and recovery, replication and availability, and integration with signing, SBOM, and admission policy.

Examples include ECR, ACR, GCR/Artifact Registry, JFrog Artifactory, Nexus, Harbor, or another managed internal service.

Base images come from allowlisted publishers. They're mirrored internally, pinned by digest, scanned, and rebuilt on a schedule the team owns. CI authenticates with a short-lived identity, signs the resulting digest, and only the release workflow can write to production repositories.

Kubernetes or the runtime checks that the image comes from an approved registry, verifies its signature and provenance (proof of where it came from and how it was built), and checks policy before deployment.

I test pull behavior during a registry or availability-zone failure, and monitor auth failures, scan findings, replication lag, storage, and unusual downloads. A private registry alone doesn't guarantee trust. Provenance and controlled promotion into production are what actually establish it.

## Q. How do you sign software artifacts and verify them before deployment?

**Answer:**

I sign the digest after the build and security checks pass, using a protected key or a keyless workload identity tied to the CI workflow. Containers and OCI Helm charts can use Cosign. Classic Helm charts can use provenance signatures. Packages can use whatever signing mechanism is native to that ecosystem.

The signature and provenance record the source commit, the builder or workflow that produced it, the artifact digest, and any attestations such as SBOM or test results.

Deployment policy checks the digest, the signature's identity and issuer, the expected repository or workflow, and any required attestations before admitting or promoting the artifact. Keys have owners, rotation, revocation, and audit trails. CI jobs never get long-lived exported private keys.

I also test offline or recovery-mode verification, so it still works when something else is down.

Signing proves origin and integrity, not quality. Code review, tests, scanning, policy checks, and runtime controls are still needed on top of it.

If a key or workflow is compromised, I revoke trust, find every digest signed with it, rebuild from a trusted pipeline, and block those old artifacts from deployment.

### Q: Artifacts in Azure DevOps

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

---

### Q: How do you handle large artifacts efficiently in pipelines?

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

---

### Q. How do you publish and consume artifacts in Azure DevOps?

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

---

### Q. How do you handle large artifacts efficiently in Azure Pipelines?

**Answer:**

I first work out why the artifact is large and whether every file in it is actually needed for deployment. I remove build caches and debug output, use package or container registries instead of raw file transfer, compress suitable content, split independent packages, and cache dependencies incrementally rather than rebuilding the whole artifact.

Artifacts get explicit retention rules and versions that don't change once published. I place agents and storage close to consumers where possible, and I only use parallel downloads if the tooling supports it and it actually helps.

I monitor upload/download time, size trend, storage cost, and deployment time.

For very large datasets or VM images, I use the appropriate storage/image service and pass a versioned reference through the pipeline rather than transferring it as a normal pipeline artifact.

---

