# Azure DevOps Summary

## End-to-End CI/CD Pipeline

1. A developer works through a feature branch and a pull request in Azure Repos or another Git provider. Branch policies require review, build validation, and the right checks.
2. Azure Pipelines restores dependencies, compiles the code, runs unit and integration tests, and runs static, dependency, secret, infrastructure-as-code, and container security checks.
3. The pipeline produces a versioned package or image that never changes once built, and publishes it to Azure Artifacts or Azure Container Registry with a clear link back to the commit it came from.
4. Deployment promotes that same artifact through Dev, Test, Staging/UAT, and Production. Configuration for each environment lives outside the artifact — the artifact itself never gets rebuilt.
5. Protected environments use checks like approval, policy, a change window, an exclusive lock, health evidence, and automated smoke tests. Blue-green, canary, or rolling deployment cuts down production risk where it's supported.
6. Azure Monitor, Log Analytics, and Application Insights confirm availability, errors, latency, dependency health, infrastructure health, and that real business transactions still work. If verification fails, promotion stops or a known rollback kicks in.

Deployment targets can include App Service, AKS, Functions, VMs, and hybrid infrastructure. Authenticate with workload federation or managed identity wherever you can, give each stage only the access it needs, protect production service connections, and keep pipeline and audit evidence around.

## GitHub Actions with Azure DevOps

GitHub Actions and Azure DevOps can work together when GitHub is where the code lives and Azure DevOps owns the controlled deployment. The split in responsibility needs to be explicit:

```text
GitHub pull request
  -> GitHub Actions: build, test and fast security checks
  -> publish a package or image digest that never changes
  -> Azure DevOps: consume that exact version
  -> deployment-environment approvals and checks
  -> deploy to AKS
  -> smoke tests and Azure Monitor verification
```

Azure Pipelines can also connect directly to a GitHub repository and handle both CI and CD itself. Running two separate automation systems only makes sense when it reflects real team ownership or a governance requirement — otherwise it just adds more authentication, traceability, and troubleshooting complexity than you need.

For a split pipeline like this:

- Publish the package to an artifact repository, or the image to Azure Container Registry. Never pass an unverified, mutable `latest` tag between the two systems.
- Record the commit SHA, the build run, the SBOM (the list of everything that went into the build), the scan result, and a fixed artifact version or digest that won't change later.
- Only trigger or authorize a deployment once the artifact actually exists — never rebuild it inside Azure DevOps.
- Use GitHub OIDC with an Azure workload identity, or an Azure DevOps workload-federated service connection, instead of a long-lived cloud credential.
- Restrict the GitHub connection, service connection, environment, and agent pool to only the pipelines that are authorized to use them.
- Send deployment status back to the source commit, so reviewers can trace the build and release evidence from there.

## Approvals, Gates and Protected Resources

For YAML pipelines, configure **Approvals and checks** on the protected resource — usually an Azure DevOps environment, service connection, variable group, secure file, or agent pool.

The resource owner controls these checks outside the pipeline's YAML, so a contributor can't remove a production approval just by editing the pipeline file.

Useful checks include:

- Manual approval by the correct production owner
- Branch control requiring a protected release branch
- Required templates
- Business hours or change window
- Azure Monitor alert query
- Invoke Azure Function or REST API for an external policy decision
- Exclusive lock to prevent overlapping production deployments

Classic release pipelines still support pre-deployment approvals and gates, but new designs usually go with multistage YAML and protected environments instead. To actually enforce a Trivy scan result, make the scan stage fail on findings, publish the scan evidence, or expose an approved policy service through a supported check.

Running Trivy earlier in the pipeline doesn't automatically make it a gate on its own.

An approval is not a substitute for automated validation. The approver should be able to see the change, the exact artifact version, the test and scan results, which environment is affected, the deployment plan, health evidence, and how to roll back.

## Container Security Stage

Build the image once, push it to ACR, resolve its digest (a fixed reference that always points to that exact image), and scan that digest with an approved, version-pinned Trivy installation or task:

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
          displayName: Scan the image with Trivy
```

`--exit-code 1` makes findings at the chosen severities fail the job. The severity levels, how unfixed findings are handled, and the exception process should all come from organization policy, not from whatever a pipeline author happens to pick.

Pin and verify the scanner itself. Don't assume `apt install trivy` is safe to run on every hosted image without checking.

Trivy gives you build-time vulnerability evidence. Microsoft Defender for Containers complements that with vulnerability assessment for the registry and running images, security-posture recommendations, and runtime threat detection.

Neither tool replaces image signing, admission controls, minimal images, patching, running as non-root, or an actual incident-response plan.

## Key Vault Integration

The pipeline authenticates through a protected service connection backed by workload identity federation, managed identity, or a narrowly scoped service principal. It only gets the Key Vault data-plane role needed to read the specific secrets it uses.

Secrets are fetched at runtime and handed to the task that needs them — they're never committed to Git or printed to logs.

```text
reviewed code -> pipeline identity -> Key Vault authorization
              -> runtime secret -> deployment -> smoke test
```

Use separate vaults, or strong authorization boundaries, to keep environments apart. Add private endpoints and firewall rules where required, rotation and expiry alerts, purge protection and recovery controls, and diagnostic logging.

Applications should fetch secrets through managed identity themselves, rather than having secrets baked into artifacts or Kubernetes manifests.

Secret masking is a last safety net, not a real guarantee — avoid echoing values, exposing them on the command line, putting them in output variables, or running untrusted scripts near them.

Fetch only the specific secrets you actually need, rather than using `SecretsFilter: '*'`:

```yaml
- task: AzureKeyVault@2
  displayName: Retrieve deployment secrets
  inputs:
    azureSubscription: production-workload-federation
    KeyVaultName: kv-orders-production
    SecretsFilter: database-password,external-api-key
    RunAsPreJob: false
```

`RunAsPreJob: false` makes the retrieved variables available only to later tasks in the job. Setting it to `true` exposes them to the whole job, so only do that when you actually need to.

The service connection still needs its own explicit Key Vault data-plane authorization, and it still needs to be able to reach the vault over the network.

## Terraform Delivery with Azure DevOps

A Terraform pipeline should run from reviewed Git code, using a protected Azure Resource Manager service connection — ideally workload identity federation, with a narrowly scoped service principal only when that's really necessary.

A self-hosted agent makes sense when it needs to reach private endpoints or private Azure APIs, but it has to be patched, isolated, and monitored, and it should never run untrusted pull-request code with production credentials attached.

```text
pull request -> fmt/validate -> tfsec/Checkov -> plan artifact -> review
protected environment -> approval -> apply saved plan -> smoke test -> audit evidence
```

Keep Terraform modules reusable, and keep Dev, QA, and Production separate by state, identity, approval, subscription or resource scope, and policy — not just by swapping variable files. Use an encrypted, versioned remote state backend with locking, and never keep state or service-principal secrets in the repository.

Publish the plan for review, apply that exact reviewed plan, and hold onto the pipeline logs, deployment metadata, and rollback or recovery instructions.
