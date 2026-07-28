# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Docker

### 2.1 What is Docker?

Docker is a containerization platform that packages an application with its dependencies, libraries, and config into a portable **image** that runs as an isolated **container**.

Containers share the host OS kernel (via namespaces + cgroups) rather than booting a full guest OS, so they are lightweight and start in milliseconds — solving "works on my machine" by making runtime environments consistent from dev → prod.

### 2.2 How is Docker useful and how do you use it in a pipeline?

- **Consistency:** the same image runs in CI, staging, and prod.
- **Isolation & density:** many containers per host, resource-limited via cgroups.
- **Fast, immutable (not changed after creation) deploys:** ship an image tag, roll back by re-deploying the previous tag.
- **In a pipeline:** build image → run unit/integration tests inside it → scan (Trivy/Grype) → push to a registry (ECR/GHCR) with an immutable (not changed after creation) tag → deploy to Kubernetes/ECS. Use multi-stage builds to keep images small and free of build tools.

### 2.3 Can Docker containers be used as CI/CD agents?

Yes — this is standard practice:
- **Jenkins:** the Docker/Kubernetes plugins spin up an ephemeral container per build (agent-per-build), giving a clean, reproducible environment that is destroyed after.
- **GitLab CI:** each job runs in a container defined by `image:`.
- **GitHub Actions:** `container:` runs job steps inside a container; you can also run service containers.
Benefits: isolation, reproducibility, no snowflake agents, easy tooling versioning.

---
