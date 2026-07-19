# Artifact Repositories and Registries

This folder is the parent location for interview material about package repositories, artifact management, container registries, retention, promotion, and software-distribution controls.

Future content should be organized into product-specific subfolders here, for example:

- `Nexus/` — Sonatype Nexus Repository
- `JFrog-Artifactory/` — JFrog Artifactory and JFrog Platform
- `GitHub-Packages/` — GitHub-hosted packages and containers
- `GitLab-Package-Registry/` — GitLab packages and container registry
- `Azure-Artifacts/` — Azure DevOps feeds and package management
- `AWS-CodeArtifact/` — AWS managed package repositories
- `Google-Artifact-Registry/` — Google Cloud packages and images
- `Azure-Container-Registry/` — private Azure container images and artifacts
- `Amazon-ECR/` — AWS Elastic Container Registry
- `Harbor/` — open-source container registry, signing, and replication

Create a product subfolder only when relevant content is added. Each subfolder should contain its own `README.md` topic index and any applicable `questions.txt`, `notes.txt`, `summary.txt`, or example files.

Cross-product topics can be stored directly in this folder, including artifact immutability, checksums and signatures, SBOM storage, promotion between environments, proxy repositories, access control, replication, cleanup, retention, backup, disaster recovery, and troubleshooting failed uploads or downloads.

## Current Content

- `questions.txt` — trusted production registries and artifact-signing verification
- `scenario-questions.txt` — artifact-storage security, production registry security, and failed image-push troubleshooting
