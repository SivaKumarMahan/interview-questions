# Azure DevOps Detailed Interview Notes

## End-to-End Terraform, Azure DevOps, Helm, and AKS Pipeline

**Project flow:**

1. **Terraform** provisions the resource group, virtual network, Azure Container Registry, AKS cluster, Key Vault, identities, and the role assignments they need. State is stored in an encrypted, locked remote backend.
2. **Azure Pipelines** runs Terraform formatting, validation, security checks, plan review, approval, and apply, using a workload-identity service connection.
3. A **Node.js application** gets installed, linted, unit-tested, and packaged.
4. The pipeline builds a minimal container image, scans it, and publishes it to ACR with a digest — a fixed reference that always points to that exact image and never changes. It also records where the artifact came from and how it was built.
5. **Helm** deploys that same image to AKS, with environment-specific values, readiness and liveness probes, resource requests, and `--atomic --wait` so a bad rollout gets rolled back automatically.
6. **Post-deployment checks** confirm Pods are healthy, LoadBalancer or Ingress routing works, the application is healthy, and logs and monitoring look normal. Production promotion stops or rolls back when any of these health checks fail.

The main areas I had to dig into on this project were Terraform state and lock handling, ACR authentication, the Azure service connection's identity and RBAC, Helm's rendering and release history, Kubernetes Events, and rollout health.

The main design rule underneath all of it: **build the artifact once, and promote that exact same version through every environment**, rather than rebuilding it for each one.
