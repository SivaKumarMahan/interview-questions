# GitHub Actions Detailed Interview Notes

## End-to-End GitHub Actions, Terraform, EKS, and Kubernetes Project

**Architecture:**

- Modular Terraform provisions a VPC, public/private subnets, routes, security controls, IAM roles, and an EKS cluster.
- Terraform state uses a remote backend that is encrypted, versioned, and locked. Production applies need approval and use short-lived identity.
- A Node.js application is built into a small container image. It's published with a commit-SHA tag or digest, so the image is immutable, meaning it never changes after it's created. That way the exact image that gets tested is the one that gets deployed.
- Kubernetes manifests use Kustomize overlays for environment differences and define Deployments, Services, Ingress, probes, and resource limits.
- Prometheus and Grafana provide cluster and application monitoring.

**GitHub Actions flow:**

```text
pull request → lint/test → Terraform and manifest validation → security scans
merge → build image → Trivy scan → sign/publish digest
      → update/deploy desired state → rollout and application verification
```

The workflow uses GitHub OIDC federation instead of stored cloud access keys. Third-party actions are pinned to trusted versions or commit SHAs. Production environments are restricted, and untrusted pull requests never get deployment credentials. The image that gets tested is the same image that gets deployed.

When something fails, I check the first failed job, then the runner and action version, OIDC claims and IAM trust, registry authentication, the Terraform plan and state, EKS endpoint connectivity, Kubernetes events, Ingress health, and monitoring dashboards.

I only retry a job when it's idempotent, meaning safe to run more than once, and when I know the underlying cause was temporary.
