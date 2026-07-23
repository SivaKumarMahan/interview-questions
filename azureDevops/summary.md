# Azure DevOps Summary

## End-to-End CI/CD Pipeline

1. A developer works through a feature branch and pull request in Azure Repos or another Git provider. Branch policies require review, build validation, and appropriate checks.
2. Azure Pipelines restores dependencies, compiles, runs unit/integration tests, and performs static, dependency, secret, IaC, and container security checks.
3. The pipeline produces an immutable, versioned package or image and publishes it to Azure Artifacts or Azure Container Registry with traceability to the commit.
4. Deployment promotes the same artifact through Dev, Test, Staging/UAT, and Production. Environment-specific configuration is external; the artifact is not rebuilt per environment.
5. Protected environments use checks such as approval, policy, change window, exclusive lock, health evidence, and automated smoke tests. Blue-green, canary, or rolling deployment reduces production risk where supported.
6. Azure Monitor, Log Analytics, and Application Insights verify availability, errors, latency, dependencies, infrastructure health, and business transactions. Failed verification stops promotion or initiates a known rollback.

Deployment targets can include App Service, AKS, Functions, VMs, and hybrid infrastructure. Authenticate with workload federation or managed identity where possible, grant each stage least privilege, protect production service connections, and retain pipeline and audit evidence.

## Key Vault Integration

The pipeline authenticates through a protected service connection backed by workload identity federation, managed identity, or a narrowly scoped service principal. It receives only the Key Vault data-plane role needed to read specified secrets. Secrets are retrieved at runtime and passed to the consuming task without being committed to Git or printed to logs.

```text
reviewed code -> pipeline identity -> Key Vault authorization
              -> runtime secret -> deployment -> smoke test
```

Use separate vaults or strong authorization boundaries for environments, private endpoints and firewall rules where required, rotation and expiry alerts, purge protection and recovery controls, and diagnostic logging. Prefer applications retrieving secrets through managed identity rather than baking secrets into artifacts or Kubernetes manifests. Secret masking is a last safety net: avoid echoing values, command-line exposure, output variables, and untrusted scripts.
