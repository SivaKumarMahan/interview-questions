# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Docker

### 2.1 What is Docker?

Docker is a containerization platform. It packages an application together with its dependencies, libraries, and configuration into a portable **image**, which then runs as an isolated **container**.

Containers share the host machine's kernel instead of booting a full guest operating system, using two Linux features — namespaces for isolation and cgroups for resource limits. That's what makes them lightweight and able to start in milliseconds. It also solves the classic "works on my machine" problem, because the same image runs the same way everywhere, from a developer's laptop to production.

### 2.2 How is Docker useful and how do you use it in a pipeline?

- **Consistency:** the same image runs in CI, staging, and production.
- **Isolation and density:** you can run many containers on one host, each with its resource usage capped by cgroups.
- **Fast, reliable deploys:** once an image is built and tagged, that exact build never changes — you ship an image tag, and rolling back just means re-deploying the previous tag.
- **In a pipeline:** build the image, run unit and integration tests inside it, scan it for vulnerabilities (with a tool like Trivy or Grype), push it to a registry (like ECR or GHCR) under a fixed tag, then deploy it to Kubernetes or ECS. Multi-stage builds keep the final image small and free of build tools.

### 2.3 Can Docker containers be used as CI/CD agents?

Yes — this is standard practice:

- **Jenkins:** the Docker and Kubernetes plugins spin up a fresh container for each build. You get a clean, reproducible environment that's thrown away afterward.
- **GitLab CI:** each job runs inside a container defined by `image:`.
- **GitHub Actions:** `container:` runs job steps inside a container, and you can also run service containers alongside it.

The benefits are isolation, reproducibility, no "snowflake" build agents that drift out of sync, and easy control over which tool versions each job uses.

---
