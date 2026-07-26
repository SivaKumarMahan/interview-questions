# Azure DevOps Detailed Interview Notes

## End-to-End Terraform, Azure DevOps, Helm, and AKS Pipeline

**Project flow:**

1. **Terraform** provisions the resource group, virtual network, Azure Container Registry, AKS cluster, Key Vault, identities, and required role assignments. State is stored in an encrypted and locked remote backend.
2. **Azure Pipelines** runs Terraform formatting, validation, security checks, plan review, approval, and apply using a workload-identity service connection.
3. A **Node.js application** is installed, linted, unit-tested, and packaged.
4. The pipeline builds a minimal container image, scans it, publishes the immutable digest to ACR, and records build provenance.
5. **Helm** deploys that digest to AKS with environment-specific values, readiness/liveness probes, resource requests, and `--atomic --wait` behavior.
6. **Post-deployment checks** verify Pods, LoadBalancer or Ingress routing, application health, logs, and monitoring. Production promotion stops or rolls back when health gates fail.

Important investigation areas from this project were Terraform state and lock handling, ACR authentication, Azure service-connection identity and RBAC, Helm rendering and release history, Kubernetes Events, and rollout health. The main design rule is **build once and promote the same immutable artifact** rather than rebuilding for each environment.

---