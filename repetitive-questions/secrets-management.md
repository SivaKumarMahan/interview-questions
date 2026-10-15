# Repetitive Interview Questions

## How do you manage secrets in your project?

**Interviewer:** How do you securely store and use passwords, tokens, and certificates? Where do you store your secrets?

**Candidate:**

I store Production secrets in Azure Key Vault and let applications access them through managed identity or AKS Workload Identity. I do not store secret values in Git, Docker images, pipeline YAML, or Terraform code.

```text
Azure DevOps pipeline -> service connection (workload identity federation) -> Key Vault
AKS Pod              -> Workload Identity                                   -> Key Vault
App Service          -> managed identity                                    -> Key Vault
```

Access to the vault uses Azure RBAC with least privilege, and the vault has soft delete and purge protection enabled.

## What is a secret?

Examples include:

- Database passwords.
- API keys.
- Access tokens.
- Private certificates and keys.
- Storage credentials.
- Webhook tokens.

Normal values such as an application URL, feature flag, or log level are configuration, not secrets.

## Basic flow

```text
Application
-> proves its identity
-> Azure Key Vault checks permission
-> application reads the required secret
```

The application receives access without storing a long-lived Azure username and password.

## Azure Key Vault

I use separate vaults for environments such as Development and Production.

```text
kv-project-development
kv-project-production
```

This prevents a Development identity from reading Production secrets and makes access easier to review.

Create or update a secret:

```bash
az keyvault secret set \
  --vault-name <vault-name> \
  --name <secret-name> \
  --value <secret-value>
```

In real use, I avoid typing secrets directly into commands that may be saved in shell history. I use an approved secure input or automation method.

## Authentication and permission

There are two separate questions:

1. **Who is the application?** Managed identity or workload identity answers this.
2. **What may it do?** Azure RBAC gives only the required Key Vault permission.

For example, an orders API may read only its database secret. It does not receive permission to delete the vault or read every team's secrets.

## AKS Workload Identity

For an AKS application, I connect a Kubernetes ServiceAccount to an Azure managed identity.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  namespace: production
  annotations:
    azure.workload.identity/client-id: "<managed-identity-client-id>"
```

The Deployment's Pod template uses that ServiceAccount:

```yaml
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: orders-api
```

The application can then request a token for its identity and read permitted Key Vault secrets.

### How does AKS connect to Key Vault?

No client secret is stored in the cluster. The Pod's Kubernetes token is exchanged for an Entra ID token.

```text
Pod (ServiceAccount orders-api)
-> Kubernetes ServiceAccount token
-> AKS OIDC issuer
-> Entra ID checks the federated credential
-> token for the user-assigned managed identity
-> Key Vault (role: Key Vault Secrets User)
```

One-time setup:

```bash
# 1. Turn on OIDC issuer, Workload Identity and the Key Vault CSI add-on
az aks update -g my-rg -n my-aks --enable-oidc-issuer --enable-workload-identity
az aks enable-addons -g my-rg -n my-aks --addons azure-keyvault-secrets-provider

# 2. Create the identity and trust the Kubernetes ServiceAccount
az identity create -g my-rg -n id-orders-api
OIDC_ISSUER=$(az aks show -g my-rg -n my-aks --query oidcIssuerProfile.issuerUrl -o tsv)
az identity federated-credential create \
  --name orders-api-fic \
  --identity-name id-orders-api \
  --resource-group my-rg \
  --issuer "$OIDC_ISSUER" \
  --subject system:serviceaccount:production:orders-api \
  --audience api://AzureADTokenExchange

# 3. Least-privilege access on one vault only
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee <identity-client-id> \
  --scope <key-vault-resource-id>
```

Remember:

- AAD Pod Identity is deprecated. Use Workload Identity.
- The `--subject` must match the namespace and ServiceAccount name exactly, or the token exchange fails.
- If the vault is private, AKS needs the private endpoint and the `privatelink.vaultcore.azure.net` DNS zone linked to its VNet.

## Two ways to use secrets in AKS

### Option 1: Application reads Key Vault directly

The application uses the Azure SDK and its workload identity.

This is useful when:

- The application already supports Key Vault.
- The latest secret value is needed at runtime.
- The application can handle retries and secret refresh.

### Option 2: Secrets Store CSI Driver

The CSI driver can mount Key Vault values as files inside the Pod.

```text
Pod starts
-> CSI driver on the node reads the SecretProviderClass
-> authenticates with the Pod's workload identity
-> fetches the listed secrets from Key Vault
-> mounts them as files, for example /mnt/secrets/database-password
-> application reads the file
```

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: orders-api-secrets
  namespace: production
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: "<managed-identity-client-id>"
    keyvaultName: "<vault-name>"
    tenantId: "<tenant-id>"
    objects: |
      array:
        - |
          objectName: database-password
          objectType: secret
```

Mount it in the Pod:

```yaml
volumeMounts:
  - name: secrets
    mountPath: /mnt/secrets
    readOnly: true
volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: orders-api-secrets
```

The application reads the value from a file such as:

```text
/mnt/secrets/database-password
```

If the application needs an environment variable, the SecretProviderClass can also sync the value into a Kubernetes Secret:

```yaml
spec:
  secretObjects:
    - secretName: orders-api-db
      type: Opaque
      data:
        - objectName: database-password
          key: DB_PASSWORD
```

Remember:

- The synced Secret exists only while at least one Pod mounts the CSI volume.
- Syncing stores the value in etcd too, so I prefer reading the mounted file.
- If the fetch fails (wrong permission, DNS, or secret name), the Pod stays in `ContainerCreating` and `kubectl describe pod` shows a `FailedMount` event.

## Kubernetes Secrets

A Kubernetes Secret is useful for applications that require Kubernetes-native secret references, but base64 encoding is not encryption by itself.

If Kubernetes Secrets are used, I enable encryption at rest, restrict RBAC, avoid committing values to Git, and prefer an external secret source.

```bash
kubectl auth can-i get secrets \
  --as=system:serviceaccount:production:orders-api \
  -n production
```

This helps verify whether a ServiceAccount has secret access.

Restrict RBAC to the one Secret the workload needs:

```yaml
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["orders-api-db"]
    verbs: ["get"]
```

Other points I mention:

- **Encryption at rest:** AKS encrypts etcd storage at the platform level. For an extra layer with my own key, I enable KMS etcd encryption with a Key Vault key (`--enable-azure-keyvault-kms`).
- **Volume over env var:** a mounted file can be updated without a restart, and env vars leak more easily through crash dumps, debug output, and `kubectl describe`.
- **GitOps without plain values in Git:**
  - **Sealed Secrets** encrypts the Secret so the encrypted file is safe to commit. Only the controller in the cluster can decrypt it.
  - **External Secrets Operator** syncs values from Key Vault (or Vault, AWS Secrets Manager) into Kubernetes Secrets.
  - **Key Vault CSI driver** (my default on AKS) does not need a Secret object at all.

## What happens if a Secret changes while Pods are running?

**Interviewer:** You update a Kubernetes Secret. Do the running Pods see the new value?

**Candidate:**

It depends on how the Pod consumes the Secret.

| How it is used | Effect of the change |
| --- | --- |
| Environment variable (`secretKeyRef`) | No change. The Pod keeps the old value until it restarts. |
| Volume mount | The file is updated after a short delay (kubelet sync, usually under a minute or two). |
| Volume mount with `subPath` | Not updated. Needs a restart. |
| Baked into the image (`ENV` in Dockerfile) | No effect at all. Rebuild the image. This is also a security problem. |
| Key Vault CSI driver with rotation enabled | Mounted file is refreshed on the poll interval (default 2 minutes). Synced env vars still need a restart. |

```text
Secret changed
-> env var: old value stays -> kubectl rollout restart -> new value
-> volume:  file updated     -> app must re-read the file
```

```bash
kubectl rollout restart deployment orders-api -n production
kubectl rollout status deployment orders-api -n production
```

Remember:

- Even when the file changes, an application that read the value only at startup keeps the old one in memory.
- Some teams use a controller such as Stakater Reloader to roll the Deployment automatically when a Secret changes.
- Enable CSI rotation with `az aks addon update -g my-rg -n my-aks --addon azure-keyvault-secrets-provider --enable-secret-rotation`.

## How do you keep secrets out of container images?

**Interviewer:** How do you secure secrets in container images?

**Candidate:**

I never put a secret inside an image. Anyone who can pull the image can read every layer. The image contains only the application, and secrets are injected at runtime.

I avoid:

```dockerfile
ENV DB_PASSWORD=MyPassword123
COPY .env /app/.env
```

```bash
docker build --build-arg DB_PASSWORD=MyPassword123 .
```

Build arguments and `ENV` values can be seen with `docker history` and image metadata.

If the build itself needs a secret (for example, a private package feed token), I use a BuildKit secret mount. It is available only during that `RUN` step and is not saved in a layer:

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
```

```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t orders-api:1.4.0 .
```

At runtime:

```text
Image (no secrets) -> AKS Pod -> Workload Identity -> Key Vault -> secret as mounted file
```

Remember:

- Add `.env` and key files to `.dockerignore` and `.gitignore`.
- Scan the repository with Gitleaks and the image with `trivy image --scanners vuln,secret`.
- If a secret was baked into a pushed image, rotate the secret, rebuild the image, and delete the old image tags from ACR. Removing the line from the Dockerfile is not enough.

## How do you store a database connection string with Key Vault and Managed Identity?

**Interviewer:** Your App Service or AKS application connects to Azure PostgreSQL. How do you handle the connection string?

**Candidate:**

```text
Application
-> managed identity (App Service) or Workload Identity (AKS)
-> Entra ID token
-> Key Vault (Key Vault Secrets User on this vault)
-> connection string
-> PostgreSQL over a private endpoint
```

1. Store the connection string as a secret, for example `postgres-connection-string`.
2. Enable managed identity on the App Service, or Workload Identity on AKS.
3. Give that identity **Key Vault Secrets User** on that vault only.
4. Read it at runtime.

On App Service, no code change is needed. I use a Key Vault reference in the app settings:

```text
DB_CONNECTION = @Microsoft.KeyVault(SecretUri=https://kv-project-production.vault.azure.net/secrets/postgres-connection-string/)
```

A versionless reference picks up a new secret version automatically (App Service refreshes it within 24 hours, or on restart).

**Follow-up: How do you remove the password completely?**

Azure Database for PostgreSQL Flexible Server supports Microsoft Entra authentication. The application's managed identity is added as a database role and logs in with a token, so there is no database password to store or rotate.

```text
App identity -> Entra token for PostgreSQL -> database login as that identity
```

This is my preferred design for new applications.

## CI/CD secrets

Pipeline secrets are stored in the platform's protected credential store or retrieved from Key Vault.

Examples:

- Jenkins Credentials.
- Azure DevOps secret variables or variable groups.
- GitHub Actions Secrets or environment secrets.
- GitLab protected and masked variables.

The pipeline should:

- Mask secret values in logs.
- Limit secrets to the required job.
- Restrict Production secrets to protected environments or branches.
- Prefer short-lived identity-based access.

I do not write this:

```yaml
password: MyProductionPassword
```

### Azure DevOps

**Interviewer:** How do you manage credentials in Azure DevOps?

**Candidate:**

| Need | What I use |
| --- | --- |
| Simple secret value | Secret pipeline variable (masked, cannot be viewed after saving) |
| Shared or Production secrets | Variable group linked to Key Vault, or the `AzureKeyVault@2` task |
| Access to Azure, ACR, AKS | Service connection with workload identity federation (no stored client secret) |
| Files such as a certificate or kubeconfig | Secure Files library with `DownloadSecureFile@1` |

```yaml
variables:
  - group: prod-keyvault-secrets   # linked to Key Vault

steps:
  - task: AzureKeyVault@2
    inputs:
      azureSubscription: prod-service-connection
      KeyVaultName: kv-project-production
      SecretsFilter: 'DB-PASSWORD'

  - script: ./run-migration.sh
    env:
      DB_PASSWORD: $(DB-PASSWORD)   # secrets are not exposed to scripts unless mapped
```

Remember:

- Secret variables are not passed to scripts as environment variables automatically. I map them with `env:` only in the step that needs them.
- I do not `echo` secrets. Masking works only for exact known values, so encoded or split values can still leak.
- The service connection's identity gets least-privilege RBAC, and the Production service connection has approvals and checks.

### Jenkins

**Interviewer:** How do you store secrets in Jenkins?

**Candidate:**

I store them in the Jenkins Credentials store (Manage Jenkins -> Credentials) and reference them by ID. For Production on Azure, I prefer Key Vault as the source.

```groovy
withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
    sh 'mvn sonar:sonar -Dsonar.token="$SONAR_TOKEN"'
}
```

Remember:

- Use single quotes in `sh '...'` so the shell reads the variable. With double quotes, Groovy puts the secret into the command string and Jenkins warns about it.
- Do not use `set -x` or `echo` around secret commands.
- Never put secrets in the `environment {}` block as plain text.
- If the agent runs on an Azure VM, it can use the VM's managed identity (`az login --identity`) and read Key Vault, so no Azure client secret is stored in Jenkins at all.
- Restrict credentials with folder-level scope so one team's job cannot use another team's Production credential.

## Terraform

Terraform creates Key Vaults, identities, and permissions, but I avoid putting normal application secret values directly in Terraform code.

```hcl
resource "azurerm_key_vault" "production" {
  name                = "kv-project-production"
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  soft_delete_retention_days = 90
  purge_protection_enabled   = true
}
```

Terraform state can contain sensitive data, so it is stored in a private, protected backend.

### How do you secure the Terraform state file?

**Interviewer:** How do you secure your Terraform state?

**Candidate:**

State is never local and never in Git. I use an Azure Storage Account backend with Entra ID authentication instead of storage account keys.

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstateprod"
    container_name       = "tfstate"
    key                  = "prod/network.tfstate"
    use_azuread_auth     = true
  }
}
```

| Control | Why |
| --- | --- |
| Entra ID + RBAC (`Storage Blob Data Contributor` only for the pipeline identity) | No shared access keys |
| Private endpoint or firewall, public access off | Only the build agents can reach it |
| Blob versioning and soft delete | Recover a corrupted or deleted state |
| State locking (blob lease, automatic with `azurerm`) | Stops two applies at the same time |
| Separate state per environment | A Dev mistake cannot touch Production state |
| `*.tfstate` and `*.tfstate.backup` in `.gitignore` | Never committed |

Remember:

- `sensitive = true` only hides the value in plan output. It is still saved in the state file.
- Newer Terraform (1.10+) has ephemeral values, and 1.11+ has write-only arguments (for example `value_wo` on `azurerm_key_vault_secret`), which keep a value out of state when the provider supports it.
- Nobody edits state by hand. I use `terraform state mv` or `import` blocks.

## Secret rotation

Rotation means replacing an old secret with a new one.

My process is:

1. Create the new secret version.
2. Let the application read the new value.
3. Test the application.
4. Revoke the old value.
5. Monitor for failures.

For a database password, the database and application change must be coordinated so the application does not lose access.

I alert before certificates or secrets expire.

### Is there downtime when you rotate a Key Vault secret?

**Interviewer:** Will there be downtime when you rotate secrets in Key Vault?

**Candidate:**

No. Adding a new secret version in Key Vault does not cause downtime by itself. The risk is in how the application picks up the new value and when the old credential stops working.

```text
1. Create the new credential (old one still valid)
2. Store it as a new Key Vault version
3. Application picks it up (refresh, or rolling restart)
4. Validate the application
5. Disable the old credential
```

- If the app reads the secret at runtime, or re-reads the mounted file, no restart is needed.
- If it reads the secret only at startup, I do a rolling restart. With several replicas and a PodDisruptionBudget, traffic keeps flowing.
- I use the two-credential pattern where possible: Storage Accounts have `key1` and `key2`, and for a database I can keep two users or let the old password stay valid until all Pods use the new one.

Remember: downtime happens when the old credential is revoked before every Pod has the new one.

## Network security

For sensitive environments, Key Vault uses:

- Private endpoint.
- Private DNS.
- Restricted public access.
- Firewall rules.

The AKS network must be able to resolve and reach the private Key Vault address.

## Troubleshooting secret access

If an application cannot read a secret, I check:

### Identity

Is the Pod using the expected ServiceAccount and managed identity?

```bash
kubectl get pod <pod-name> -n <namespace> -o yaml
kubectl get serviceaccount <service-account> -n <namespace> -o yaml
```

### Permission

Does that identity have permission to read the required secret in the correct vault?

### Network

Can the Pod resolve and reach the Key Vault endpoint? Are private DNS and firewall settings correct?

### Secret name

Does the secret exist, and is the application using the correct name and version?

### CSI Driver

```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get secretproviderclass -n <namespace>
```

The Pod Events may show identity, permission, or mount errors.

## If a secret is leaked

I treat an exposed secret as compromised:

1. Revoke or rotate it immediately.
2. Check access logs and affected systems.
3. Update applications with the replacement.
4. Remove the value from source history if needed.
5. Add a scan or control to prevent recurrence.

Deleting the visible line from Git is not enough because the value may remain in history or logs.

## Backup and recovery

I enable Key Vault soft delete and purge protection. I also document who can recover a deleted secret or vault.

A backup does not replace rotation. If a credential is exposed, restoring the old exposed value would not make it safe.

## Common mistakes I avoid

- Hardcoding secrets.
- Committing `.env` files.
- Printing secrets in logs.
- Giving every application access to the entire vault.
- Using long-lived service-principal passwords when identity is available.
- Storing Production values in a Development vault.
- Forgetting rotation and expiration alerts.
- Assuming Kubernetes base64 values are encrypted.

## Example

Suppose an AKS orders API needs a PostgreSQL password. I store it in the Production Key Vault, give only the orders API workload identity permission to read it, and mount it through the CSI driver.

The value never appears in Git or the container image. When I rotate it, I create the new value, verify the application, and then revoke the old one.

## In short

I store secrets in Azure Key Vault, use managed identity or AKS Workload Identity, and grant only the required read permission. Applications retrieve secrets directly or through the CSI driver.

Pipeline secrets stay in protected credential stores, and I use rotation, expiration alerts, private networking, audit logs, soft delete, and a tested response process for leaks.
