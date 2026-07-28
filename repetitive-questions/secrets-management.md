# Repetitive Interview Questions

## How do you manage secrets in your project?

**Interviewer:** How do you securely store and use passwords, tokens, and certificates?

**Candidate:**

I store Production secrets in Azure Key Vault and let applications access them through managed identity or AKS Workload Identity. I do not store secret values in Git, Docker images, pipeline YAML, or Terraform code.

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

## Two ways to use secrets in AKS

### Option 1: Application reads Key Vault directly

The application uses the Azure SDK and its workload identity.

This is useful when:

- The application already supports Key Vault.
- The latest secret value is needed at runtime.
- The application can handle retries and secret refresh.

### Option 2: Secrets Store CSI Driver

The CSI driver can mount Key Vault values as files inside the Pod.

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

## Kubernetes Secrets

A Kubernetes Secret is useful for applications that require Kubernetes-native secret references, but base64 encoding is not encryption by itself.

If Kubernetes Secrets are used, I enable encryption at rest, restrict RBAC, avoid committing values to Git, and prefer an external secret source.

```bash
kubectl auth can-i get secrets \
  --as=system:serviceaccount:production:orders-api \
  -n production
```

This helps verify whether a ServiceAccount has secret access.

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
