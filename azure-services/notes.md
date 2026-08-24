# Azure Services Detailed Interview Notes

## AKS Microservices Architecture

**Core components:**

- **AKS cluster:** A managed Kubernetes control plane, with node pools sized and separated to match each workload's needs.
- **Virtual Network:** The private network boundary for nodes, Pods, private endpoints, and any controlled connection back to on-premises systems.
- **Azure Container Registry:** Private storage for container images that have been scanned and signed. AKS pulls them using managed identity and RBAC.
- **Ingress and Azure Load Balancer/Application Gateway:** Handles external entry, TLS termination, routing, health checks, and an optional web application firewall.
- **Azure Pipelines:** Builds, tests, and scans the code, publishes an image that won't change once tagged, and promotes releases that have passed review.
- **Helm:** Packages Kubernetes resources and environment-specific values, and keeps a versioned history so upgrades and rollbacks are possible.
- **Azure Monitor:** Collects monitoring data from the control plane, nodes, containers, applications, logs, metrics, and traces.

**Deployment flow:**

1. Provision the VNet, AKS, ACR, identity, private DNS, ingress, monitoring, and policies through reviewed infrastructure-as-code.
2. Build and scan each microservice image, then push its digest (a fixed, unchangeable reference to that exact image) to ACR.
3. Validate and deploy versioned Helm charts, with readiness and startup probes and realistic resource requests.
4. Send a small amount of traffic to the new version, run smoke and business tests, and watch errors, latency, how close resources are to their limits, and the health of dependencies.
5. Either promote gradually, or roll back the traffic and the release if the health checks fail.

A production setup also needs zone distribution, autoscaling, PodDisruptionBudgets, NetworkPolicies, workload identity, secrets pulled from an external store, backup and restore, certificate rotation, cost controls, and a regional recovery plan that's actually been tested.
