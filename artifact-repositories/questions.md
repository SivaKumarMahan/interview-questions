## Q. Which container registry should you trust for production images?

**Answer:**

I trust an organization-approved registry—not an image merely because it is public or popular. The registry must provide strong identity and least-privilege repositories, TLS and encryption, immutable tags or digest-based deployment, vulnerability scanning, audit logs, retention and recovery, replication/availability, and integration with signing, SBOM, and admission policy. Examples may include ECR, ACR, GCR/Artifact Registry, JFrog Artifactory, Nexus, Harbor, or another managed internal service.

Base images come from allowlisted publishers, are mirrored internally, pinned by digest, scanned, and rebuilt on an owned schedule. CI authenticates with short-lived identity, signs the resulting digest, and only the release workflow can write production repositories. Kubernetes or the runtime verifies approved registry, signature/provenance, and policy before deployment.

I test pull behavior during registry/AZ failure and monitor auth failures, scan findings, replication lag, storage, and unusual downloads. A private registry alone is not a trust guarantee; provenance and controlled production promotion establish trust.

## Q. How do you sign software artifacts and verify them before deployment?

**Answer:**

I sign the immutable digest after the build and security checks, using a protected key or keyless workload identity tied to the CI workflow. Containers and OCI Helm charts can use Cosign; classic Helm charts can use provenance signatures; packages may use ecosystem-native signing. The signature and provenance identify the source commit, builder/workflow, artifact digest, and relevant attestations such as SBOM or test results.

Deployment policy verifies digest, signature identity/issuer, expected repository/workflow, and required attestations before admitting or promoting the artifact. Keys have owners, rotation, revocation, and audit; CI jobs do not receive long-lived exported private keys. Offline or recovery verification is tested.

Signing proves origin and integrity, not quality. Code review, tests, scanning, policy checks, and runtime controls remain necessary. If a key or workflow is compromised, I revoke trust, identify every affected digest, rebuild from a trusted pipeline, and prevent those artifacts from deployment.

### Q: Artifacts in Azure DevOps

**A:** In Azure DevOps, artifacts refer to the files or packages produced as a result of a build or release pipeline. They can include compiled code, binaries, libraries, configuration files, or any other output that needs to be stored and shared for deployment or further processing. Azure DevOps provides a built-in artifact management system that allows teams to publish, store, and consume artifacts efficiently.

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

I first determine why the artifact is large and whether all files are deployment inputs. I remove build caches/debug output, use package/container registries, compress suitable content, split independent packages, and use incremental dependency caching—not artifact rebuilding.

Artifacts have explicit retention and immutable versions. Agents and storage are placed close to consumers where possible; parallel downloads are used only if supported and beneficial. I monitor upload/download time, size trend, storage cost, and deployment time.

For very large datasets or VM images, I use the appropriate storage/image service and pass a versioned reference through the pipeline rather than transferring it as a normal pipeline artifact.

---

