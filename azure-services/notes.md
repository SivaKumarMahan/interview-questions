# Azure Services Detailed Interview Notes

## AKS Microservices Architecture

**Core components:**

- **AKS cluster:** Managed Kubernetes control plane with node pools sized and isolated for workload needs.
- **Virtual Network:** Private network boundary for nodes, Pods, private endpoints, and controlled on-premises connectivity.
- **Azure Container Registry:** Private storage for scanned and signed container images; AKS pulls through managed identity/RBAC.
- **Ingress and Azure Load Balancer/Application Gateway:** External entry, TLS termination, routing, health probes, and optional WAF.
- **Azure Pipelines:** Builds, tests, scans, publishes immutable images, and promotes reviewed releases.
- **Helm:** Packages Kubernetes resources and environment values with versioned upgrade and rollback history.
- **Azure Monitor:** Collects control-plane, node, container, application, log, metric, and trace telemetry.

**Deployment flow:**

1. Provision VNet, AKS, ACR, identity, private DNS, ingress, monitoring, and policies through reviewed IaC.
2. Build and scan each microservice image and push its immutable digest to ACR.
3. Validate and deploy versioned Helm charts with readiness/startup probes and realistic resource requests.
4. Route a small amount of traffic, run smoke and business tests, and monitor errors, latency, saturation, and dependency health.
5. Promote gradually or roll back traffic and the application release when health gates fail.

Production design also includes zone distribution, autoscaling, PodDisruptionBudgets, NetworkPolicies, workload identity, external secrets, backup/restore, certificate rotation, cost controls, and a tested regional recovery plan.
