# CI/CD and DevOps Delivery Summary

An end-to-end delivery pipeline turns a reviewed commit into a verified, running service. Here's how the pieces fit together.

## The Flow

1. A developer writes code and gets it reviewed in GitHub, GitLab, or Azure Repos.
2. A CI system, such as **GitHub Actions** or **Jenkins**, triggers on a pull request or a protected merge.
3. Unit and integration tests, static analysis (**SonarQube**), and dependency, IaC, secret, and container scans (**Trivy**) run to give fast feedback.
4. The build produces one package or Docker image that never changes once it's built. It generates an SBOM and provenance data — a record of where the artifact came from and how it was built — signs the image, and pushes it to a registry like **ECR**.
5. **Terraform** provisions the infrastructure. **Ansible** configures machines, where that model is used.
6. **Helm** or **Kustomize** manifests describe the Kubernetes resources. A GitOps repository records the desired image digest, and **Argo CD** or **Flux** reconciles it — meaning it keeps adjusting the cluster until it matches what's in Git — across clusters like EKS or AKS.
7. A Service, Ingress, or load balancer only routes users to workloads that are actually ready.
8. **Prometheus**, **Grafana**, logs, traces, an APM tool like **Dynatrace**, **Alertmanager**, **Slack**, and **PagerDuty** support verification and day-to-day operations.

## Key Principles

- **Build once, promote everywhere.** The same digest moves through every environment — nothing gets rebuilt along the way.
- **Keep configuration external.** Environment differences and secrets live outside the artifact, in version control or a secret manager.
- **Protect production.** Use protected identities and approvals, progressive delivery, health and SLO gates, and a rollback path that's independent of the deploy path.
- **CI proves quality, CD controls promotion.** CI's job is to prove the artifact is good. CD's job is to move it forward safely and confirm the real application works.

## Tools by Stage

| Stage | Typical tools |
| --- | --- |
| Source control | GitHub, GitLab, Azure Repos |
| CI orchestration | GitHub Actions, Jenkins |
| Code quality | SonarQube |
| Security scanning | Trivy, plus dependency/IaC/secret scanners |
| Infrastructure | Terraform, Ansible |
| Kubernetes packaging | Helm, Kustomize |
| GitOps delivery | Argo CD, Flux |
| Target clusters | EKS, AKS |
| Observability | Prometheus, Grafana, Dynatrace |
| Alerting & notifications | Alertmanager, Slack, PagerDuty |

## CI vs. Continuous Delivery vs. Continuous Deployment

**DevOps** is the broader culture and practice: collaboration, automation, measurement, and continuous improvement. CI/CD sits inside that.

| Term | What it means |
| --- | --- |
| Continuous Integration (CI) | Integrate and test changes frequently, so problems surface early |
| Continuous Delivery | Always keep an approved artifact ready to deploy, with a human deciding when to release it |
| Continuous Deployment | Automatically release every change that passes, within defined risk controls |