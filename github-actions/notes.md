# GitHub Actions Detailed Interview Notes

## End-to-End GitHub Actions, Terraform, EKS, and Kubernetes Project

**Architecture:**

- Modular Terraform provisions a VPC, public/private subnets, routes, security controls, IAM roles, and an EKS cluster.
- Terraform state uses an encrypted, versioned, locked remote backend; production apply uses approval and short-lived identity.
- A Node.js application is built into a small container image and published with an immutable (not changed after creation) commit-SHA tag or digest.
- Kubernetes manifests use Kustomize overlays for environment differences and define Deployments, Services, Ingress, probes, and resources.
- Prometheus and Grafana provide cluster and application monitoring.

**GitHub Actions flow:**

```text
pull request → lint/test → Terraform and manifest validation → security scans
merge → build image → Trivy scan → sign/publish digest
      → update/deploy desired state → rollout and application verification
```

The workflow should use GitHub OIDC federation instead of stored cloud access keys, pin third-party actions to trusted versions or commit SHAs, restrict production environments, and prevent untrusted pull requests from receiving deployment credentials. The exact image tested is the image deployed.
For failure investigation, I check the first failed job, runner and action version, OIDC claims and IAM trust, registry authentication, Terraform plan/state, EKS endpoint connectivity, Kubernetes Events, Ingress health, and monitoring.

I retry only when the job is idempotent (safe to run more than once) and the underlying temporary cause is known.
