# Repetitive Interview Questions

## How do you manage secrets in your project?

### Detailed answer

In my Azure project, I manage secrets through a centralized lifecycle rather than storing them independently in application repositories, pipelines or Kubernetes manifests. My first preference is to **remove the secret completely** by using Microsoft Entra ID, managed identity or workload identity. When a password, API token or other secret is unavoidable, I store it in Azure Key Vault and give only the required workload identity permission to retrieve it.

The main runtime flow is:

```text
AKS Pod
-> dedicated Kubernetes service account
-> projected service-account token
-> AKS OIDC issuer
-> Microsoft Entra Workload ID
-> short-lived Microsoft Entra token
-> private Azure Key Vault endpoint
-> only the specifically authorized secret
```

The application does not need an Azure client secret to retrieve its business secret. This solves the **secret-zero problem**: we do not protect one password by embedding another password in the Pod.

My core rules are:

- Prefer passwordless identity over a stored secret.
- Keep secrets out of Git, Docker images, Helm values, Terraform state and logs.
- Separate vaults and identities by application and environment.
- Grant least-privilege access at the narrowest practical scope.
- Use private network access in addition to identity authorization.
- Rotate secrets and certificates before expiry and test consumer reload behavior.
- Log access and alert on abnormal use or permission changes.
- Revoke exposed credentials immediately; removing them from source control is not enough.

---

## 1. What is considered a secret?

A secret is a value that grants access or proves identity and would create risk if disclosed. Examples include:

- Database passwords.
- Third-party API tokens.
- Client secrets for a legacy service principal.
- Private keys.
- Certificate private-key material.
- Webhook signing secrets.
- Encryption or signing material.
- Short-lived access tokens while they are valid.

I distinguish related data types:

| Data type | Example | Correct treatment |
| --- | --- | --- |
| Normal configuration | Port, feature flag, public URL | ConfigMap, App Configuration or approved settings |
| Secret | Password, API token, connection credential | Prefer elimination; otherwise Key Vault secret |
| Cryptographic key | Key used to sign/encrypt | Key Vault key or Managed HSM when required |
| Certificate | TLS certificate with private key | Key Vault certificate and certificate lifecycle |
| Public value | Tenant ID, client ID, public certificate | Versioned configuration, while still protecting integrity |

A client ID is normally an identifier, not a password. A tenant ID and subscription ID are also generally not secrets. I do not hide every configuration value as a secret because that makes real secrets harder to identify and govern.

Key Vault is not used as a general configuration database or a place for customer documents. Non-secret configuration belongs in Azure App Configuration, Kubernetes ConfigMaps or the application configuration system; business data belongs in the appropriate data store.

---

## 2. Secret inventory, ownership and classification

Every Production secret should have:

- A clear name and purpose.
- An owning application/team.
- An issuing/source system.
- One or more authorized consumers.
- Environment and data classification.
- Creation date, expiry date and rotation frequency.
- Rotation method and runbook.
- Incident owner and revocation procedure.
- A replacement or passwordless migration plan where possible.

A representative inventory record is:

```text
name: orders-payment-provider-token
environment: production
owner: orders-team
consumer: orders-api workload identity
source: approved external provider
vault: application-specific production vault
expiry: provider-defined date
rotation: dual-token procedure
alert window: before expiry
```

The inventory contains metadata, not the secret value.

Orphaned secrets are dangerous because nobody knows whether they can be rotated or deleted. I periodically review owners, consumers, last-use evidence, expiry and role assignments, then remove unused secrets through an approved process.

---

## 3. Azure Key Vault architecture

I use separate Key Vaults based on security and operational boundaries. A common design is one vault per application, environment and region, for example:

```text
Development application -> Development vault
UAT application         -> UAT vault
Production application  -> Production vault
```

Production does not share a vault or workload identity with Development. This limits blast radius and prevents a lower-environment deployment from reading Production secrets.

Important Key Vault controls include:

- Microsoft Entra authentication.
- Azure RBAC permission model.
- Least-privilege data-plane roles.
- Private endpoint and Private DNS for private workloads.
- Disabled or restricted public network access.
- Soft delete.
- Purge protection.
- Diagnostic settings sent to Log Analytics.
- Expiry and rotation notifications.
- Azure Policy to audit or enforce the required configuration.
- Resource locks where appropriate for operational deletion protection.

A resource lock is helpful against accidental management-plane deletion, but it is not a security boundary and does not replace RBAC, soft delete or purge protection.

### Why separate vaults?

Vault separation provides:

- Smaller impact if one application identity is compromised.
- Independent environment permissions.
- Independent network boundaries.
- Clearer operational ownership.
- Lower risk of one noisy application causing throttling for unrelated applications.
- Easier audit and access review.

I do not automatically create a separate vault for every individual secret. The boundary is based on application, environment, region, team ownership, availability and compliance requirements.

---

## 4. Authentication without stored credentials

My preference order is:

1. Use a platform feature that does not require an application password.
2. Use managed identity or Workload ID with short-lived tokens.
3. Use a certificate-backed identity only when federation/managed identity is unavailable.
4. Use a client secret only as a controlled legacy fallback with rotation.

Examples:

- An AKS application uses Microsoft Entra Workload ID.
- An Azure VM-based Jenkins agent uses managed identity.
- Azure DevOps uses a workload identity-federated service connection.
- GitHub Actions uses OIDC federation with Microsoft Entra ID.
- GitLab CI requests an OIDC ID token and exchanges it through a federated credential.

This removes long-lived Azure credentials from the CI/CD systems. The federated trust is restricted to expected repositories/projects, branches and protected environments. Receiving an OIDC token is not enough by itself; Microsoft Entra ID validates issuer, audience and subject claims, then Azure RBAC limits what the resulting identity can do.

---

## 5. Authorization and least privilege

Authentication identifies the caller. Authorization decides what it can do.

For each application, I create a dedicated workload identity and grant only the required Key Vault data-plane role. A runtime application that reads secrets should not be able to:

- Create new secrets.
- Delete or purge secrets.
- Change Key Vault networking.
- Change RBAC assignments.
- Read unrelated application secrets.

A typical runtime assignment is a read-only secrets role at the application vault or narrower approved scope. A rotation automation identity may be allowed to create a new secret version but is separate from the runtime reader. Administrators use time-bound privileged access where the organization supports it.

I avoid:

- Giving the application Key Vault Administrator.
- Assigning Owner or Contributor merely to read a secret.
- Using one identity for all microservices.
- Granting access at subscription scope when vault scope is enough.
- Giving a CI build job access to runtime application secrets.

Management-plane and data-plane permissions are different. Permission to view or manage the Key Vault Azure resource does not automatically mean permission to read secret values, and secret-reader permission should not provide the ability to change the vault resource.

---

## 6. AKS Workload ID

Each AKS application uses a dedicated Kubernetes service account mapped to a dedicated user-assigned managed identity.

The trust relationship includes:

```text
issuer  = AKS OIDC issuer URL
subject = system:serviceaccount:<namespace>:<service-account>
audience = api://AzureADTokenExchange
```

Because the namespace and service-account name are part of the subject, another service account does not automatically receive the same Azure identity.

### Representative ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  namespace: orders-prod
  annotations:
    azure.workload.identity/client-id: "<orders-managed-identity-client-id>"
```

The Pod template carries the Workload ID label:

```yaml
spec:
  template:
    metadata:
      labels:
        app: orders-api
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: orders-api
      containers:
        - name: orders-api
          image: <acr-name>.azurecr.io/orders-api@sha256:<approved-digest>
```

The identity client ID is not a password. The sensitive capability comes from the combination of the federated trust and the RBAC granted to that identity.

---

## 7. Two ways the application consumes Key Vault secrets

I choose between direct SDK retrieval and a CSI-mounted file according to the application's integration needs.

### Option A: Direct retrieval with the Azure SDK

For a Java application, the conceptual implementation is:

```java
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.azure.security.keyvault.secrets.SecretClient;
import com.azure.security.keyvault.secrets.SecretClientBuilder;

SecretClient client = new SecretClientBuilder()
    .vaultUrl(System.getenv("KEY_VAULT_URI"))
    .credential(new DefaultAzureCredentialBuilder().build())
    .buildClient();

String databasePassword = client
    .getSecret("orders-database-password")
    .getValue();
```

`KEY_VAULT_URI` is normal configuration, for example:

```text
https://<vault-name>.vault.azure.net/
```

In AKS, `DefaultAzureCredential` detects the Workload ID environment and projected token. On a developer machine, it can use an approved developer identity. Production does not fall back to an embedded client secret.

The application:

- Requests only the secret it requires.
- Never logs the value.
- Avoids exposing it in an exception or health endpoint.
- Caches it only for an appropriate short period.
- Handles Key Vault throttling with bounded exponential backoff.
- Defines how a rotated value is reloaded.
- Clears or limits sensitive values in memory where the language/runtime permits.

Whenever the dependent service supports passwordless Microsoft Entra authentication, I prefer direct identity authentication and eliminate the database/storage password entirely.

### Option B: Azure Key Vault provider for Secrets Store CSI Driver

For an application that expects a file, I use the Key Vault provider for the Secrets Store CSI Driver.

Representative `SecretProviderClass`:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: orders-key-vault
  namespace: orders-prod
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: "<orders-managed-identity-client-id>"
    keyvaultName: "<orders-production-vault-name>"
    tenantId: "<tenant-id>"
    objects: |
      array:
        - |
          objectName: orders-database-password
          objectType: secret
          objectAlias: database-password
          objectVersion: ""
```

Representative Pod volume:

```yaml
spec:
  template:
    metadata:
      labels:
        app: orders-api
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: orders-api
      containers:
        - name: orders-api
          image: <acr-name>.azurecr.io/orders-api@sha256:<approved-digest>
          volumeMounts:
            - name: application-secrets
              mountPath: /mnt/secrets-store
              readOnly: true
      volumes:
        - name: application-secrets
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: orders-key-vault
```

The application reads:

```text
/mnt/secrets-store/database-password
```

The secret is mounted into the Pod at runtime; it is not stored in the container image or committed Helm values.

### Rotation behavior with CSI

Enabling CSI autorotation updates mounted content after the configured polling behavior, but the application must still reload the changed file. Some applications watch the file; others require a controlled Pod restart.

Important points:

- A file mounted using Kubernetes `subPath` does not receive automatic updates.
- Environment variables do not dynamically change inside an already running process.
- Synchronizing CSI content into a Kubernetes Secret increases the number of places containing the secret and is used only when necessary.
- A base64-encoded Kubernetes Secret is not encrypted merely because it is base64.

I test the complete rotation flow in a lower environment before depending on it in Production.

---

## 8. Why I do not normally place secret values in Kubernetes Secrets

A Kubernetes Secret is an API object designed to hold sensitive data, but:

- Its manifest value is often only base64 encoded.
- Anyone who can read that Secret through Kubernetes RBAC can obtain the value.
- It may be copied into Git, Helm output, cluster backup or troubleshooting commands.
- Environment-variable consumers do not automatically reload a rotated value.

If a Kubernetes Secret is required by an integration, I:

- Enable and validate encryption at rest for Kubernetes secret data.
- Restrict Kubernetes RBAC.
- Avoid committing the manifest value.
- Prefer short-lived synchronization from Key Vault.
- Limit which namespace and service account can access it.
- Avoid displaying it through `kubectl`, logs or support bundles.
- Define rotation and restart behavior.

Direct Key Vault SDK access or a CSI file mount normally reduces unnecessary duplication.

---

## 9. Secret handling in Jenkins

For Azure access, Jenkins agents on Azure use managed identity wherever possible:

```groovy
stage('Azure Login') {
    steps {
        sh '''
            set -euo pipefail
            az login --identity --output none
        '''
    }
}
```

The managed identity receives only the Azure role needed by that agent/job. A pull-request agent does not receive Production access.

If a legacy external system requires a stored token, I use a folder-scoped Jenkins credential and bind it only around the exact command:

```groovy
withCredentials([
    string(
        credentialsId: 'orders-test-provider-token',
        variable: 'PROVIDER_TOKEN'
    )
]) {
    sh '''
        set +x
        ./scripts/run-authorized-test.sh
    '''
}
```

Important Jenkins controls:

- Keep the credential at the narrowest folder/item scope.
- Restrict who can create, update and use credentials.
- Use isolated agents for trusted jobs.
- Do not let untrusted code execute on an agent while another job exposes a secret.
- Use single-quoted Groovy strings so the shell, not Groovy, expands the environment variable.
- Disable command tracing around sensitive commands.
- Never echo, archive or place the value in a command result.
- Rotate the underlying credential and update its owner/expiry.

Jenkins masking is a safety feature, not a complete security boundary. A malicious pipeline can deliberately transform or exfiltrate a credential. Therefore, repository review, job authorization, agent isolation and least privilege are essential.

---

## 10. Secret handling in Azure DevOps

Azure access uses workload identity-federated Azure Resource Manager service connections. I create separate service connections for build, Development and Production and authorize only the required pipelines.

A pipeline references the connection by its non-secret name:

```yaml
- task: AzureCLI@2
  inputs:
    azureSubscription: azure-wif-orders-dev
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      set -euo pipefail
      az account show --output none
```

The pipeline receives short-lived federated access and does not contain a client secret.

If a legacy task genuinely needs a secret:

- Link a protected variable group to Azure Key Vault or use the approved Key Vault task.
- Scope the variable group to authorized pipelines.
- Use environment protections for Production.
- Map the secret only into the step that needs it.
- Do not print the variable.
- Do not pass secrets as command-line arguments when a safer input method exists.

Example of retrieving only an approved secret for a legacy step:

```yaml
- task: AzureKeyVault@2
  inputs:
    azureSubscription: azure-wif-orders-test
    KeyVaultName: <orders-test-vault-name>
    SecretsFilter: third-party-test-token
    RunAsPreJob: false

- bash: |
    set +x
    ./scripts/run-authorized-test.sh
  displayName: Run external integration test
  env:
    PROVIDER_TOKEN: $(third-party-test-token)
```

I avoid `SecretsFilter: '*'` because the job should retrieve only what it needs. I also avoid using pipeline secret variables as the normal method to deliver application runtime secrets to AKS.

---

## 11. Secret handling in GitHub Actions

GitHub Actions uses OIDC federation for Azure:

```yaml
permissions:
  contents: read
  id-token: write

steps:
  - name: Sign in to Azure
    uses: azure/login@v2
    with:
      client-id: ${{ vars.AZURE_CLIENT_ID }}
      tenant-id: ${{ vars.AZURE_TENANT_ID }}
      subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

The IDs are normal configuration. The job requests a short-lived OIDC token, and the Microsoft Entra federated credential trusts only the approved repository/branch or protected GitHub Environment subject.

For unavoidable non-Azure secrets:

- Prefer Environment secrets for environment-specific access.
- Restrict Production with Environment reviewers and deployment-branch rules.
- Limit organization-secret access to selected repositories.
- Reference the secret only in the required step.
- Pin third-party actions to reviewed commit SHAs.
- Do not expose secrets to untrusted pull-request code.
- Add derived sensitive values to masking where necessary, without treating masking as authorization.

Representative fallback:

```yaml
- name: Call approved external test service
  env:
    PROVIDER_TOKEN: ${{ secrets.PROVIDER_TOKEN }}
  run: |
    set +x
    ./scripts/run-authorized-test.sh
```

I do not pass a secret as an action input to an unreviewed action. An action running in the job can potentially access the job environment and workspace.

---

## 12. Secret handling in GitLab CI

GitLab deployment jobs request an OIDC ID token:

```yaml
deploy-development:
  environment:
    name: development
  id_tokens:
    AZURE_OIDC_TOKEN:
      aud: api://AzureADTokenExchange
  script:
    - >
      az login
      --service-principal
      --username "$AZURE_CLIENT_ID"
      --tenant "$AZURE_TENANT_ID"
      --federated-token "$AZURE_OIDC_TOKEN"
      --output none
```

The federated credential validates the GitLab issuer, audience, project/ref and environment-related claims as supported by the configured platform. Development and Production use separate environment-scoped identities.

For an unavoidable legacy secret, GitLab variables are:

- Masked where the value format supports it.
- Hidden where supported.
- Protected so they are available only to protected refs.
- Environment-scoped.
- Made available only to the required job.

Masked output does not protect against a malicious script. Protected branches, protected Environments, trusted runners, merge-request review and least-privilege external credentials remain necessary.

---

## 13. Terraform and Infrastructure as Code

Terraform manages:

- Key Vault resources.
- Private endpoints and Private DNS.
- Azure RBAC assignments.
- AKS Workload ID and federated identity resources.
- Diagnostic settings.
- Azure Policy assignments.
- Non-secret secret metadata where appropriate.

I avoid managing actual secret values through normal Terraform variables:

```hcl
# Avoid for ordinary application secret injection:
resource "azurerm_key_vault_secret" "database_password" {
  name         = "orders-database-password"
  value        = var.database_password
  key_vault_id = azurerm_key_vault.orders.id
}
```

Even if `var.database_password` is marked `sensitive`, Terraform normally needs the value in state to manage that resource. `sensitive = true` mainly redacts CLI/UI display; it does not remove the value from state.

The same concern applies to:

- Secret values in `.tfvars`.
- Secret outputs.
- Kubernetes Secret resources managed by Terraform.
- Provider configuration containing passwords.
- Generated plans and debug logs.

I provision the secure destination and identity permissions with Terraform, then populate or rotate the secret through an approved secret-management workflow that does not persist the value in Terraform state. If an organization deliberately manages a secret through Terraform, the state becomes a highly sensitive secret store and must be protected, audited and scoped accordingly.

The Terraform remote state backend still uses:

- Microsoft Entra authentication/managed identity.
- Restricted RBAC.
- Private networking where required.
- Encryption and versioning.
- Separate state per environment.
- No state-file download in normal workflows.

---

## 14. Build-time secrets

I do not use Docker `ARG` or `ENV` for credentials:

```dockerfile
# Unsafe patterns:
ARG API_TOKEN
ENV API_TOKEN=${API_TOKEN}
COPY production-certificate.pfx /app/
```

Build arguments, image history, cache, layers and logs can expose values. Deleting a file in a later layer does not reliably remove it from the earlier layer.

If an authorized image build must temporarily authenticate to a private dependency source, I use a BuildKit secret mount:

```dockerfile
# syntax=docker/dockerfile:1

RUN --mount=type=secret,id=package_token \
    /app/scripts/restore-private-dependency.sh \
    /run/secrets/package_token
```

Representative build:

```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=package_token,env=PACKAGE_TOKEN \
  --tag orders-service:<commit> \
  .
```

The script must not copy the secret into the output layer or log it. The CI job provides the secret only to this build step. Where possible, I instead use an identity-aware package repository and short-lived token.

---

## 15. Rotation strategy

Rotation is planned before the secret reaches Production.

For a dependency supporting two simultaneous credentials, I use a zero-downtime rotation:

```text
credential A active
-> create credential B
-> store B as a new Key Vault version
-> allow consumer to reload/restart safely
-> verify new authentication and business health
-> revoke credential A
-> monitor failures
-> close rotation evidence
```

For a single-password database:

1. Confirm backup/recovery and maintenance requirements.
2. Coordinate the database change and application update.
3. Create/set the new password through the authorized rotation process.
4. Store the new Key Vault version.
5. Reload/restart the consumer in a controlled rolling manner.
6. Verify connections and transactions.
7. Monitor authentication failures.

For certificates:

- Store them as Key Vault certificates rather than generic secrets when appropriate.
- Track expiry well before the last day.
- Automate issuance/renewal where supported.
- Validate hostname, chain and private-key access.
- Deploy/reload the certificate.
- Verify every listener and endpoint.

Rotation frequency depends on provider capability, risk and policy. Blindly rotating a value without proving consumer reload behavior can cause an outage.

### Version handling

Key Vault stores versions. Applications normally request the current version so rotation can move them forward. A pinned version can be useful for an explicitly controlled rollout, but it also prevents automatic adoption of the replacement.

If a rotation creates a functional problem and the old credential has **not** been compromised, the runbook may temporarily restore the known-good version while correcting the issue. If compromise is suspected, I never reactivate the exposed credential merely because rollback is convenient.

---

## 16. Expiration and preventive monitoring

I do not wait until an application fails because its secret expired.

Preventive controls include:

- Expiration metadata on secrets where supported.
- Alerts before certificate or secret expiry.
- An owner and escalation path.
- Rotation automation with success/failure reporting.
- Dashboards for upcoming expirations and orphaned items.
- Scheduled access reviews.
- Rotation tests in lower environments.

A rotation job is not successful only because it created a new Key Vault version. It must confirm that consumers adopted the new value and that the old value was revoked according to the procedure.

---

## 17. Logging and detection

Key Vault diagnostic settings send relevant logs and metrics to Log Analytics. I correlate these with:

- Microsoft Entra sign-in and audit logs.
- Azure Activity Log.
- AKS audit and workload logs.
- CI/CD deployment identity events.
- Application authentication failures.
- Defender for Cloud alerts.

I alert or investigate:

- Repeated denied secret access.
- A runtime identity reading unusual secret names.
- A sudden increase in secret reads.
- Access from an unexpected network or identity.
- Key Vault role assignments or access changes.
- Firewall, private endpoint or diagnostic-setting changes.
- Secret deletion, recovery or attempted purge.
- Secrets/certificates approaching expiry.
- Authentication failures after rotation.

Logs must show **who accessed which secret and when**, but they must not contain the secret value. Access to security logs is itself restricted and audited.

---

## 18. Private networking

For private AKS workloads, the Production vault normally uses:

```text
AKS subnet/workload
-> approved outbound path
-> Key Vault private endpoint
-> Private DNS resolution
```

I verify:

- The vault hostname resolves to the intended private address from the workload.
- Network Security Groups/firewall rules permit the required path.
- Public network access is disabled or restricted according to design.
- The private DNS zone is linked to the correct virtual networks.
- CI/CD or rotation automation has an approved private path when it must reach the vault.

A private endpoint does not authorize a caller. The Workload ID still needs the correct Key Vault RBAC role. Conversely, correct RBAC does not help if DNS or firewall routing blocks the connection.

---

## 19. Development and local access

Developers do not receive a copy of Production secrets for local testing.

Development uses:

- Separate Development Key Vault.
- Synthetic or masked test data.
- Developer Microsoft Entra identities.
- Time-bound, least-privilege access.
- Local environment files excluded from Git only for non-production developer values when approved.

For Java SDK access, `DefaultAzureCredential` can use the developer's authenticated Azure CLI/IDE identity locally and Workload ID in AKS. Both identities receive different RBAC and access different vaults.

`.gitignore` reduces accidental commits but is not a secret-management solution. A secret existing in an ignored plaintext file is still a local security risk and must follow the approved developer process.

---

## 20. Secret leak prevention

Preventive controls include:

- Pre-commit guidance/hooks.
- Pull-request secret scanning.
- CI repository and image scanning.
- Protected branches and peer review.
- `.dockerignore` and `.gitignore`.
- Log redaction and secure error handling.
- No shell tracing around sensitive commands.
- No secrets in tickets, chat, email or screenshots.
- No sensitive values in process arguments where a safer input channel exists.
- No Production secrets on pull-request runners.
- Short-lived tokens and least privilege so a leak has limited value.

I scan:

- Current source.
- Relevant Git history according to the incident/tooling process.
- Docker build context and image layers.
- Helm and Kubernetes manifests.
- Pipeline definitions and output.
- Terraform plans/state exposure.
- Published artifacts and support bundles.

The scanner is a detection layer. It does not make it acceptable to put a secret into source control.

---

## 21. What I do if a secret is leaked

If a credential is exposed, my first priority is to invalidate its capability, not merely hide the evidence.

The response is:

1. Start the security incident process and identify the affected credential.
2. Revoke, disable or rotate it immediately using the source system.
3. Restrict affected access and contain the compromised identity/workload where required.
4. Preserve relevant logs, commit IDs, pipeline runs and timestamps.
5. Identify every place the value could have been copied: Git history, artifacts, logs, images, caches, tickets and developer machines.
6. Review Key Vault, Microsoft Entra, Azure Activity and target-service access logs for misuse.
7. Deploy the replacement securely and verify consumers.
8. Remove the exposed value from visible source/history and artifacts through the approved process.
9. Determine impact and follow notification/compliance requirements.
10. Complete root-cause analysis and add controls preventing recurrence.

Deleting the latest Git commit does not revoke a credential. Rewriting Git history does not invalidate clones, forks, caches or logs. Rotation/revocation comes first.

---

## 22. Backup, deletion protection and recovery

Key Vault soft delete allows recovery of deleted vaults/objects during the configured retention period. Purge protection prevents permanent purge until that period ends.

I test:

- Recovery authorization.
- Recovery of an accidentally deleted secret/version where supported.
- Application behavior after recovery.
- Required regional/continuity design.
- Configuration recreation from Infrastructure as Code.

I avoid routinely exporting all Production secrets into a plaintext backup. Such an export can become a less secure shadow vault. Backup/recovery is designed from business requirements and Azure Key Vault capabilities, with access and restoration tested.

Purge permission is highly restricted and separated from normal administration.

---

## 23. Common mistakes I avoid

- Hardcoding a password in Java code or configuration.
- Committing a secret to Git and assuming later deletion makes it safe.
- Placing secrets in Docker `ARG`, `ENV`, layers or image labels.
- Storing clear-text secrets in Helm values.
- Treating base64 as encryption.
- Giving every Pod access to every secret in one shared vault.
- Using the same identity and vault for Development and Production.
- Giving a runtime application Key Vault Administrator.
- Storing application runtime secrets in pipeline variables by default.
- Giving pull-request jobs access to protected credentials.
- Printing a secret in logs or enabling shell debug tracing.
- Assuming secret masking prevents deliberate exfiltration.
- Passing secret values through Terraform and ignoring their presence in state.
- Enabling CSI rotation without confirming application reload behavior.
- Rotating a secret without revoking the old credential.
- Waiting until the expiry date to test certificate renewal.
- Assuming private networking replaces identity authorization.
- Using Key Vault as a high-volume configuration or business-data store.
- Restoring a known-compromised credential during rollback.

---

## 24. Troubleshooting secret-access failures

When an AKS application cannot retrieve a secret, I troubleshoot in layers:

### Identity

- Does the Pod use the expected service account?
- Is the `azure.workload.identity/use: "true"` label present?
- Does the service account contain the correct client-ID annotation?
- Does the federated identity subject exactly match namespace and service account?
- Are issuer and audience correct?

### Authorization

- Does the managed identity have the required Key Vault data-plane role?
- Is it assigned at the correct vault/resource scope?
- Has RBAC propagation completed?
- Is the application asking for the correct secret name and object type?

### Network and DNS

- Does the vault hostname resolve correctly inside the Pod?
- Can the Pod reach the private endpoint on HTTPS?
- Are firewall, route and NSG rules correct?
- Is the Private DNS zone linked to the AKS virtual network?

### CSI/application behavior

- Is the Secrets Store CSI driver/provider running?
- Does the `SecretProviderClass` exist in the same namespace as the Pod?
- Do Pod Events show mount or authentication errors?
- Is the file mounted at the expected path with appropriate permissions?
- Did the secret rotate while the application still holds the old cached value?

Useful non-secret checks include:

```bash
kubectl describe pod <pod-name> --namespace <namespace>

kubectl get serviceaccount <service-account> \
  --namespace <namespace> \
  --output yaml

kubectl get secretproviderclass \
  --namespace <namespace>

kubectl get events \
  --namespace <namespace> \
  --sort-by=.lastTimestamp

az keyvault show \
  --name <vault-name> \
  --query properties.publicNetworkAccess
```

I do not run a command that prints the secret value merely to prove access. I use identity, authorization, network, event and application evidence.

---

## Layered secret-management summary

| Layer | Project control |
| --- | --- |
| Elimination | Prefer Entra ID, managed identity and Workload ID |
| Storage | Application/environment-specific Azure Key Vault |
| Authentication | Short-lived federated or managed identity |
| Authorization | Dedicated identity and least-privilege Azure RBAC |
| Network | Private endpoint, Private DNS and restricted public access |
| AKS delivery | Direct SDK or read-only CSI-mounted file |
| CI/CD | Federation first; narrowly scoped secret binding only when unavoidable |
| IaC | Provision vault/RBAC/networking; avoid secret values in Terraform state |
| Rotation | New version/credential, consumer verification, old credential revocation |
| Detection | Key Vault, Entra and Activity logs with actionable alerts |
| Recovery | Soft delete, purge protection and tested recovery |
| Incident | Revoke first, investigate use, replace, clean copies and complete RCA |

---

## Concise interview answer

In my Azure project, I first avoid secrets wherever possible. AKS applications use Microsoft Entra Workload ID, Azure-hosted agents use managed identity, and Azure DevOps, GitHub Actions and GitLab use workload identity federation/OIDC. This gives them short-lived access without storing an Azure client secret.

For unavoidable values such as a third-party API token or legacy database password, I store them in an application- and environment-specific Azure Key Vault. Production Key Vault uses Azure RBAC, least privilege, private endpoint, Private DNS, soft delete, purge protection and diagnostic logs. Each application has its own workload identity and can read only its required secrets.

The AKS application either retrieves the secret directly with the Azure SDK and `DefaultAzureCredential`, or mounts it as a read-only file through the Key Vault provider for the Secrets Store CSI Driver. Secrets are never committed to Git, placed in Docker images, Helm values, normal pipeline YAML or Terraform state. Runtime secrets are not copied from the CI/CD tool into the application when Workload ID can retrieve them directly.

We maintain an owner, expiry and rotation process for every Production secret. Rotation creates a new credential/version, updates or reloads consumers, verifies business health and then revokes the old credential. Key Vault, Microsoft Entra and Azure Activity logs are monitored for denied access, unusual reads, role changes, deletion and upcoming expiry.

If a secret is leaked, I revoke or rotate it immediately, preserve and review logs, identify every copy, deploy the replacement, remove exposed artifacts/history and complete root-cause actions. Simply deleting it from Git is not considered remediation.
