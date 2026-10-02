# Azure DevOps: Security and Secrets

> Container security scanning, Key Vault integration, securing pipelines, and least-privilege access.

## Key Concepts

### Container Security Stage

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

### Key Vault Integration

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

## Interview Questions

<details><summary>Q1. [Intermediate] How do you secure Azure Pipelines?</summary>

**Answer:**

I protect the repository and its YAML from unreviewed changes, restrict who can edit or queue pipelines, use workload-identity service connections scoped to the minimum needed, protect environments and variable groups, and isolate self-hosted agents. Untrusted pull requests can't reach production secrets or runners.

Tasks, templates, and images are pinned to specific versions and reviewed. The pipeline runs secret, source, dependency, infrastructure-as-code, and image scans, publishes signed artifacts that never change once built, and keeps audit evidence. Secrets never end up in artifacts, cache, or logs.

I review organization and project permissions, which pipelines each service connection is authorized for, agent pools, OAuth token scope, retention settings, and extensions. For a supply-chain incident, I have a plan covering revocation, identifying affected artifacts, and rebuilding from trusted sources.

</details>

<details><summary>Q2. [Intermediate] Azure DevOps Pipeline Secret Exposure</summary>

#### The pipeline

```yaml
variables:
  DB_USER: "admin"
  DB_PASSWORD: "Production@123"
  API_KEY: "abc123xyz"

steps:
- script: |
    echo "Deploying application"
    echo "DB Password: $(DB_PASSWORD)"
    echo "API Key: $(API_KEY)"
```

#### What is wrong

1. **Secrets are hardcoded in plain text** directly in the YAML, which is normally stored in source control — anyone with repo read access can see the real password and API key.
2. **Secrets are printed to the build log** via `echo`. Even if these were pipeline secret variables, Azure DevOps only masks variables it *knows* are secret — and even then, log masking can be bypassed (e.g., by echoing partial characters), so printing secrets is a bad practice regardless.
3. Non-secret variables like `DB_USER` don't need protecting, but `DB_PASSWORD` and `API_KEY` clearly do and are treated the same as any other plain variable here.

#### How to redesign it

- Store secrets in an **Azure Key Vault** and link them into the pipeline via a variable group, or mark them as **secret variables** in the pipeline UI/library (never in the YAML file itself).
- Never `echo` a secret value, even for debugging.

```yaml
variables:
  - group: payment-api-secrets   # variable group linked to Azure Key Vault

steps:
- script: |
    echo "Deploying application"
    ./deploy.sh
  env:
    DB_USER: $(DB_USER)
    DB_PASSWORD: $(DB_PASSWORD)
    API_KEY: $(API_KEY)
```

The script receives the secrets as environment variables at runtime without ever printing or committing them.

#### Short interview answer

"There are two problems: real secrets are hardcoded directly in version-controlled YAML, and the script prints them to the build log where anyone with log access can read them. I'd move the secrets into Azure Key Vault, reference them through a linked variable group so they're marked secret and get masked, pass them into the script as environment variables, and remove the `echo` statements that print them entirely."

</details>

<details><summary>Q3. [Advanced] How do you enforce least privilege access in GCP or Azure pipelines? <em>(scenario)</em></summary>

**Answer:** Use service accounts with the minimum roles they need, rotate keys regularly, and audit pipeline IAM policies.

**Detailed interview approach:**

I start from the exact principal, resource, action, scope, and denial from the error and the cloud's audit logs. I check the effective IAM or RBAC, including inherited roles, deny policies, conditional bindings, the tenant/project/subscription, and the token's audience and expiry.

I reproduce with a harmless call using the same identity, then grant the narrowest predefined or custom role at the smallest possible scope — never Owner or Admin just to make the pipeline pass. Workload identity or managed identity replaces static service-account keys wherever it can.

If a key has leaked, I disable or revoke it right away, check what it was used for and what it changed, rotate anything related, and rebuild the identity path properly using workload identity. Regular access reviews, expiry dates, policy tests, and audit alerts keep roles from creeping wider over time.

</details>
