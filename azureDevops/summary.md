# Azure DevOps Summary

## End-to-End CI/CD Pipeline

1. A developer works through a feature branch and pull request in Azure Repos or another Git provider. Branch policies require review, build validation, and appropriate checks.
2. Azure Pipelines restores dependencies, compiles, runs unit/integration tests, and performs static, dependency, secret, IaC, and container security checks.
3. The pipeline produces an immutable, versioned package or image and publishes it to Azure Artifacts or Azure Container Registry with traceability to the commit.
4. Deployment promotes the same artifact through Dev, Test, Staging/UAT, and Production. Environment-specific configuration is external; the artifact is not rebuilt per environment.
5. Protected environments use checks such as approval, policy, change window, exclusive lock, health evidence, and automated smoke tests. Blue-green, canary, or rolling deployment reduces production risk where supported.
6. Azure Monitor, Log Analytics, and Application Insights verify availability, errors, latency, dependencies, infrastructure health, and business transactions. Failed verification stops promotion or initiates a known rollback.

Deployment targets can include App Service, AKS, Functions, VMs, and hybrid infrastructure. Authenticate with workload federation or managed identity where possible, grant each stage least privilege, protect production service connections, and retain pipeline and audit evidence.

## GitHub Actions with Azure DevOps

GitHub Actions and Azure DevOps can be combined when GitHub is the source platform and Azure DevOps owns controlled deployments. The responsibility boundary must be explicit:

```text
GitHub pull request
  -> GitHub Actions: build, test and fast security checks
  -> publish immutable package or image digest
  -> Azure DevOps: consume that exact version
  -> deployment-environment approvals and checks
  -> deploy to AKS
  -> smoke tests and Azure Monitor verification
```

Azure Pipelines can also connect directly to a GitHub repository and perform both CI and CD. Using two automation systems is justified only when it reflects real team ownership or governance requirements; otherwise it adds authentication, traceability and troubleshooting complexity.

For a split pipeline:

- Publish the package to an artifact repository or the image to Azure Container Registry. Do not pass an unverified mutable `latest` tag between systems.
- Record commit SHA, build run, SBOM, scan result and immutable artifact version/digest.
- Trigger or authorize deployment only after the artifact is available; never rebuild it in Azure DevOps.
- Use GitHub OIDC and an Azure workload identity, or an Azure DevOps workload-federated service connection, instead of long-lived cloud credentials.
- Restrict the GitHub connection, service connection, environment and agent pool to authorized pipelines.
- Return deployment status to the source commit so reviewers can trace build and release evidence.

## Approvals, Gates and Protected Resources

For YAML pipelines, configure **Approvals and checks** on the protected resource—commonly an Azure DevOps environment, service connection, variable group, secure file or agent pool. The resource owner controls these checks outside the pipeline YAML, so a contributor cannot remove a production approval merely by editing the pipeline.

Useful checks include:

- Manual approval by the correct production owner
- Branch control requiring a protected release branch
- Required templates
- Business hours or change window
- Azure Monitor alert query
- Invoke Azure Function or REST API for an external policy decision
- Exclusive lock to prevent overlapping production deployments

Classic release pipelines also support pre-deployment approvals and gates, but new designs commonly use multistage YAML and protected environments. A Trivy result is normally enforced by making the scan stage fail, publishing scan evidence, or exposing an approved policy service through a supported check. It is not automatically a built-in gate simply because Trivy ran earlier.

An approval is not a substitute for automated validation. The approver should see the change, immutable artifact version, test/scan results, affected environment, deployment plan, health evidence and rollback method.

## Container Security Stage

Build the image once, push it to ACR, resolve its digest, and scan that digest with an approved and version-pinned Trivy installation or task:

```yaml
- stage: SecurityScan
  dependsOn: Build
  jobs:
    - job: ScanImage
      steps:
        - script: |
            trivy image \
              --exit-code 1 \
              --severity HIGH,CRITICAL \
              --ignore-unfixed \
              "$(acrLoginServer)/orders-api@$(imageDigest)"
          displayName: Scan immutable image with Trivy
```

`--exit-code 1` makes findings at the selected severities fail the job. The severity, ignored/unfixed behavior and exception process must be organization policy rather than arbitrary pipeline choices. Pin and verify the scanner itself; do not assume `apt install trivy` works safely on every hosted image.

Trivy provides build-time vulnerability evidence. Microsoft Defender for Containers complements it with registry and running-image vulnerability assessment, security posture and runtime threat detection. Neither tool replaces image signing, admission controls, minimal images, patching, non-root execution or incident response.

## Key Vault Integration

The pipeline authenticates through a protected service connection backed by workload identity federation, managed identity, or a narrowly scoped service principal. It receives only the Key Vault data-plane role needed to read specified secrets. Secrets are retrieved at runtime and passed to the consuming task without being committed to Git or printed to logs.

```text
reviewed code -> pipeline identity -> Key Vault authorization
              -> runtime secret -> deployment -> smoke test
```

Use separate vaults or strong authorization boundaries for environments, private endpoints and firewall rules where required, rotation and expiry alerts, purge protection and recovery controls, and diagnostic logging. Prefer applications retrieving secrets through managed identity rather than baking secrets into artifacts or Kubernetes manifests. Secret masking is a last safety net: avoid echoing values, command-line exposure, output variables, and untrusted scripts.

Fetch only the required secrets rather than using `SecretsFilter: '*'`:

```yaml
- task: AzureKeyVault@2
  displayName: Retrieve deployment secrets
  inputs:
    azureSubscription: production-workload-federation
    KeyVaultName: kv-orders-production
    SecretsFilter: database-password,external-api-key
    RunAsPreJob: false
```

`RunAsPreJob: false` exposes the retrieved variables only to later tasks in the job. Setting it to `true` makes them available to the whole job and should be used only when required. The service connection still needs explicit Key Vault data-plane authorization and network reachability.

## Terraform Delivery with Azure DevOps

A Terraform pipeline should run from reviewed Git code using a protected Azure Resource Manager service connection—preferably workload identity federation, with a narrowly scoped service principal only when necessary. A self-hosted agent is appropriate when it must reach private endpoints or private Azure APIs, but it must be patched, isolated, monitored and prevented from running untrusted pull-request code with production credentials.

```text
pull request -> fmt/validate -> tfsec/Checkov -> plan artifact -> review
protected environment -> approval -> apply saved plan -> smoke test -> audit evidence
```

Keep Terraform modules reusable and make Dev, QA and Production separate by state, identity, approval, subscription/resource scope and policy—not just by variable files. Use an encrypted, versioned remote state backend with locking; do not keep state or service-principal secrets in the repository. Publish the plan for review, apply the reviewed saved plan, and retain pipeline logs, deployment metadata and rollback/recovery instructions.
