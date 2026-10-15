# Practice Project 8: Secure App Secrets with Key Vault and Managed Identity

> A hands-on guide to storing app secrets in Azure Key Vault and reading them from a Python app on App Service with a managed identity, so no password, key or connection string lives in code, config files or pipelines.

## Key Concepts

### What you will build

- An **Azure Key Vault** that uses **Azure RBAC** for data access, with soft delete and purge protection on.
- A small **Python Flask app** on **Azure App Service (Linux)** with a **system-assigned managed identity**.
- Two ways for the app to get a secret:
  1. **SDK way**: the app code calls Key Vault with `DefaultAzureCredential` and `SecretClient`.
  2. **No-code way**: App Service **Key Vault references** (`@Microsoft.KeyVault(...)`) inject the secret as an environment variable.
- **Audit logs** in Log Analytics that show every secret read, and who did it.

The final result: `https://<app-name>.azurewebsites.net/` shows that both methods loaded the secret (masked), and a KQL query shows the `SecretGet` calls made by the app's identity.

### Architecture

```text
  Developer laptop                         Azure
  +-------------------+        +-----------------------------------------------+
  | az login          |        |  Resource group rg-kv-lab                     |
  | (Secrets Officer) |--set-->|                                               |
  +-------------------+        |   +-------------------+   RBAC role:          |
                               |   | Key Vault         |   Key Vault Secrets   |
                               |   | kv-<unique>       |<--User (read only)----+
                               |   |  secret:          |                       |
                               |   |  db-password v1,v2|                       |
                               |   +---------+---------+                       |
                               |             | AuditEvent logs                 |
                               |             v                                 |
                               |   +-------------------+                       |
                               |   | Log Analytics     |                       |
                               |   +-------------------+                       |
                               |                                               |
                               |   +-------------------+                       |
   Browser ---- HTTPS -------->|   | App Service (B1)  |  system-assigned MI --+
                               |   |  Flask app        |  - SDK: SecretClient
                               |   |  app setting:     |  - @Microsoft.KeyVault(...)
                               |   +-------------------+                       |
                               +-----------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Azure Key Vault | Stores secrets with versions, soft delete and audit logs | Central, managed, HSM-backed secret store |
| Managed identity | Gives the app an Entra ID identity | Azure manages the credential; nothing to rotate or leak |
| Azure RBAC | Grants "Key Vault Secrets User" to the app | Same model as all other Azure access, scoped and auditable |
| azure-identity (`DefaultAzureCredential`) | Gets tokens in Azure and on your laptop | One code path for local dev and production |
| azure-keyvault-secrets (`SecretClient`) | Reads secrets from the vault | Official SDK |
| App Service Key Vault references | Injects secrets as app settings | No SDK code needed for simple cases |
| Log Analytics | Stores Key Vault audit logs | Answer "who read this secret and when" |

### Prerequisites

- Azure subscription with **Owner** or **User Access Administrator + Contributor** on a resource group (you need to create role assignments).
- Azure CLI 2.60 or later (`az version`). Run `az upgrade` if older.
- Python 3.11 or 3.12 for local testing.
- **Cost warning**: Key Vault Standard costs a few cents per 10,000 operations. App Service **B1** is billed per hour. Log Analytics is billed per GB ingested. Delete the resource group when done.

### Folder structure

```text
kv-managed-identity/
├── setup.sh
├── app/
│   ├── app.py
│   └── requirements.txt
└── queries/
    └── keyvault-audit.kql
```

### Step-by-step

#### Step 1: Set variables and create the resource group

Use variables so every command below can be copied as-is. Key Vault names are global, so add a random suffix.

```bash
RG=rg-kv-lab
LOC=eastus
SUFFIX=$RANDOM
KV=kv-lab-$SUFFIX
PLAN=plan-kv-lab
APP=app-kv-lab-$SUFFIX
LAW=law-kv-lab

az group create --name $RG --location $LOC
```

What this does:

- Key Vault names must be 3-24 characters, letters, digits and hyphens, and globally unique.
- `$RANDOM` gives a number so two people running this lab do not clash.

#### Step 2: Create the Key Vault with RBAC, soft delete and purge protection

```bash
az keyvault create \
  --name $KV \
  --resource-group $RG \
  --location $LOC \
  --sku standard \
  --enable-rbac-authorization true \
  --retention-days 7 \
  --enable-purge-protection true

KV_ID=$(az keyvault show --name $KV --query id -o tsv)
KV_URI=$(az keyvault show --name $KV --query properties.vaultUri -o tsv)
echo $KV_URI
```

What this does:

- `--enable-rbac-authorization true` makes the vault use **Azure RBAC** for data access instead of legacy **access policies**. In newer CLI versions this is already the default, but setting it makes the intent clear.
- **Soft delete** is always on for new vaults. Deleted secrets and vaults can be recovered for `--retention-days` (7 to 90 days).
- **Purge protection** blocks permanent deletion until the retention period ends, even for admins. It cannot be turned off later. For a lab, a 7-day retention keeps the vault name blocked only a short time.
- `vaultUri` looks like `https://kv-lab-12345.vault.azure.net/`.

#### Step 3: Give yourself permission to manage secrets

With RBAC vaults, being Owner of the subscription does **not** let you read or write secrets. Owner is a control-plane role. You need a data-plane role.

```bash
ME=$(az ad signed-in-user show --query id -o tsv)

az role assignment create \
  --assignee-object-id $ME \
  --assignee-principal-type User \
  --role "Key Vault Secrets Officer" \
  --scope $KV_ID
```

What this does:

- **Key Vault Secrets Officer** can create, update, delete and read secrets.
- Scope is the single vault, not the subscription. This follows least privilege.
- Role assignments can take a few minutes to apply. If the next step returns `Forbidden`, wait 1-5 minutes and retry.

#### Step 4: Add secrets

```bash
az keyvault secret set --vault-name $KV --name db-password --value "<placeholder-password-v1>"
az keyvault secret set --vault-name $KV --name api-key --value "<placeholder-api-key>" \
  --expires "2027-01-01T00:00:00Z" --content-type "text/plain" --tags owner=platform
```

What this does:

- Each `secret set` creates a **new version**. Old versions are kept.
- `--expires` sets an expiry date. Key Vault does not delete expired secrets, but it refuses to return them, and Event Grid can alert before expiry.
- Tip: avoid typing real secrets in shell history. Use `--file` or read from a prompt (`read -s VALUE`) for real values.

#### Step 5: Write the Flask app

The app reads one secret through the SDK and one through an environment variable that App Service fills from a Key Vault reference.

```python
# app/app.py
import os
import time

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from flask import Flask, jsonify

app = Flask(__name__)

VAULT_URL = os.environ["KEY_VAULT_URL"]          # e.g. https://kv-lab-12345.vault.azure.net/
CACHE_TTL_SECONDS = int(os.environ.get("SECRET_CACHE_TTL", "300"))

# Create the credential and client once and reuse them.
# DefaultAzureCredential uses the managed identity in Azure and az login locally.
credential = DefaultAzureCredential()
client = SecretClient(vault_url=VAULT_URL, credential=credential)

_cache: dict[str, tuple[str, float]] = {}


def get_secret(name: str) -> str:
    """Read a secret with a small in-memory cache to avoid throttling."""
    cached = _cache.get(name)
    if cached and time.time() - cached[1] < CACHE_TTL_SECONDS:
        return cached[0]
    value = client.get_secret(name).value
    _cache[name] = (value, time.time())
    return value


def mask(value: str | None) -> str:
    if not value:
        return "<not set>"
    return value[:2] + "****"


@app.get("/")
def index():
    sdk_value = get_secret("db-password")
    ref_value = os.environ.get("API_KEY")       # filled by a Key Vault reference
    return jsonify(
        sdk_secret_loaded=bool(sdk_value),
        sdk_secret_preview=mask(sdk_value),
        kv_reference_loaded=bool(ref_value) and not ref_value.startswith("@Microsoft.KeyVault"),
        kv_reference_preview=mask(ref_value),
    )


@app.get("/health")
def health():
    return "OK", 200
```

```text
# app/requirements.txt
flask==3.0.3
gunicorn==23.0.0
azure-identity>=1.17.0
azure-keyvault-secrets>=4.8.0
```

What this does:

- `DefaultAzureCredential` tries a chain of credentials: environment variables, workload identity, **managed identity**, then developer tools such as **Azure CLI**. The same code works on your laptop and in Azure.
- The client is created once at startup. Creating a new credential per request is slow and can hit token endpoint limits.
- The cache reduces calls. Key Vault has service limits per vault, and a busy app that reads secrets on every request can get HTTP 429 throttling.
- The app never prints the full secret. Do not log secret values.
- The `kv_reference_loaded` check detects a common failure: if the reference cannot be resolved, App Service passes the raw `@Microsoft.KeyVault(...)` string to the app.

#### Step 6: Run it locally with your own identity

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
az login
export KEY_VAULT_URL=$KV_URI
export API_KEY="local-test-value"
flask --app app run --port 8000
curl -s http://localhost:8000/
```

What this does:

- Locally there is no managed identity, so `DefaultAzureCredential` falls back to your `az login` session. You have **Key Vault Secrets Officer**, which includes read.
- No secret or client ID is put in a `.env` file.
- If you have several tenants, run `az login --tenant <tenant-id>`.

#### Step 7: Create the App Service and enable a system-assigned identity

```bash
az appservice plan create --name $PLAN --resource-group $RG --is-linux --sku B1

az webapp create --name $APP --resource-group $RG --plan $PLAN --runtime "PYTHON:3.12"

az webapp identity assign --name $APP --resource-group $RG

APP_PRINCIPAL_ID=$(az webapp identity show --name $APP --resource-group $RG --query principalId -o tsv)
echo $APP_PRINCIPAL_ID
```

What this does:

- `identity assign` with no options creates a **system-assigned** identity. It lives and dies with the web app.
- `principalId` is the object ID of the identity's service principal in Entra ID. You use it in role assignments.
- Check runtimes with `az webapp list-runtimes --os linux` if `PYTHON:3.12` is not available in your region.

#### Step 8: Grant the app read access to secrets

```bash
az role assignment create \
  --assignee-object-id $APP_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $KV_ID
```

To grant access to **one secret only**, use the secret's resource ID as the scope:

```bash
az role assignment create \
  --assignee-object-id $APP_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$KV_ID/secrets/db-password"
```

What this does:

- **Key Vault Secrets User** can only read secret values. It cannot list, create or delete them. This is the right role for apps.
- `--assignee-principal-type ServicePrincipal` avoids a Graph lookup and the replication delay errors that can happen with new identities.
- Secret-level scope is the tightest option. Use it when many apps share one vault. A common better design is one vault per app per environment.

#### Step 9: Configure app settings with a Key Vault reference

```bash
az webapp config appsettings set --name $APP --resource-group $RG --settings \
  KEY_VAULT_URL=$KV_URI \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  "API_KEY=@Microsoft.KeyVault(SecretUri=${KV_URI}secrets/api-key/)"

az webapp config set --name $APP --resource-group $RG \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app"
```

The two supported reference formats (each with an optional version):

```text
@Microsoft.KeyVault(SecretUri=https://<vault-name>.vault.azure.net/secrets/<secret-name>/)
@Microsoft.KeyVault(SecretUri=https://<vault-name>.vault.azure.net/secrets/<secret-name>/<version>)
@Microsoft.KeyVault(VaultName=<vault-name>;SecretName=<secret-name>)
@Microsoft.KeyVault(VaultName=<vault-name>;SecretName=<secret-name>;SecretVersion=<version>)
```

What this does:

- App Service resolves the reference with the app's managed identity and exposes the value as the `API_KEY` environment variable. The app code does not need the Key Vault SDK for this value.
- A reference **without a version** follows the latest version. App Service re-fetches it within 24 hours, or immediately when app settings change or you trigger a refresh.
- A reference **with a version** is pinned and never changes until you update the setting.
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` makes App Service run `pip install` during zip deploy.
- The Gunicorn startup command tells App Service to serve `app` from `app.py`.

#### Step 10: Deploy the app

```bash
cd app
zip -r ../app.zip app.py requirements.txt
cd ..
az webapp deploy --name $APP --resource-group $RG --src-path app.zip --type zip
```

What this does:

- `az webapp deploy` uploads the zip and Oryx builds it (installs dependencies) on the server.
- Nothing secret is in the zip. The vault URL is not a secret, but keeping it in settings makes the same build work in every environment.

#### Step 11: Variant with a user-assigned identity

A **user-assigned** identity is a separate Azure resource. Use it when several apps share one identity, when you want the identity and its role assignments created before the app (for example in IaC), or when apps are often recreated.

```bash
UAMI=id-kv-lab
az identity create --name $UAMI --resource-group $RG
UAMI_ID=$(az identity show -n $UAMI -g $RG --query id -o tsv)
UAMI_CLIENT_ID=$(az identity show -n $UAMI -g $RG --query clientId -o tsv)
UAMI_PRINCIPAL_ID=$(az identity show -n $UAMI -g $RG --query principalId -o tsv)

az role assignment create --assignee-object-id $UAMI_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope $KV_ID

az webapp identity assign --name $APP --resource-group $RG --identities $UAMI_ID

# Tell the SDK which identity to use
az webapp config appsettings set --name $APP --resource-group $RG \
  --settings AZURE_CLIENT_ID=$UAMI_CLIENT_ID

# Tell Key Vault references which identity to use
az webapp update --name $APP --resource-group $RG --set keyVaultReferenceIdentity=$UAMI_ID
```

What this does:

- When an app has more than one identity, `DefaultAzureCredential` reads `AZURE_CLIENT_ID` to pick the user-assigned one. In code you can also use `ManagedIdentityCredential(client_id=...)`.
- Key Vault references use the system-assigned identity by default. `keyVaultReferenceIdentity` switches them to the user-assigned identity.
- The `clientId` is not a secret. It is just an identifier.

#### Step 12: Turn on audit logs

```bash
az monitor log-analytics workspace create --resource-group $RG --workspace-name $LAW
LAW_ID=$(az monitor log-analytics workspace show -g $RG -n $LAW --query id -o tsv)

az monitor diagnostic-settings create \
  --name kv-audit \
  --resource $KV_ID \
  --workspace $LAW_ID \
  --logs '[{"category":"AuditEvent","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]'
```

What this does:

- `AuditEvent` logs every data-plane call: who (identity), what (operation), result, client IP and time.
- By default these logs go to the `AzureDiagnostics` table. If you add `--export-to-resource-specific true`, they go to the resource-specific `AZKVAuditLogs` table instead, which has cleaner columns.
- Logs appear after 5-15 minutes.

Example audit queries:

```kusto
// Who read which secret in the last 24 hours
AzureDiagnostics
| where TimeGenerated > ago(24h)
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where OperationName == "SecretGet"
| project TimeGenerated, Resource, OperationName, ResultSignature,
          httpStatusCode_d, CallerIPAddress, identity_claim_appid_g, requestUri_s
| order by TimeGenerated desc
```

```kusto
// Denied requests (403) - often a missing role assignment or firewall block
AzureDiagnostics
| where TimeGenerated > ago(24h)
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where httpStatusCode_d == 403
| summarize Failures = count() by OperationName, CallerIPAddress, identity_claim_appid_g, bin(TimeGenerated, 1h)
```

```kusto
// Throttled requests (429) - add caching if you see these
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where httpStatusCode_d == 429
| summarize count() by bin(TimeGenerated, 5m), Resource
```

Note: in `AzureDiagnostics` the identity of a managed identity usually shows as an app ID (`identity_claim_appid_g`). Compare it with `az ad sp show --id <principal-id> --query appId`.

#### Step 13: Rotate a secret

```bash
# Create a new version
az keyvault secret set --vault-name $KV --name db-password --value "<placeholder-password-v2>"

# List versions
az keyvault secret list-versions --vault-name $KV --name db-password \
  --query "[].{id:id, enabled:attributes.enabled, created:attributes.created}" -o table

# Disable an old version after the app has switched
az keyvault secret set-attributes --vault-name $KV --name db-password \
  --version <old-version-id> --enabled false
```

What this does:

- A new version becomes the "current" version immediately. Code calling `get_secret("db-password")` without a version gets it after its cache expires (5 minutes in this app).
- Key Vault references without a version pick it up within 24 hours, or right away after a restart or settings change.
- Safe rotation for a database password: create the new password in the database first, keep both valid, update Key Vault, wait for apps to pick it up, then remove the old password.
- Key Vault can raise `SecretNearExpiry` and `SecretNewVersionCreated` events through Event Grid. A Function can use these to automate rotation.
- Better still: avoid the secret completely. Many services (Azure SQL, Storage, Service Bus, Cosmos DB) accept Entra ID tokens from a managed identity directly.

#### Step 14: Networking (production note)

For production, close the public endpoint:

```bash
# Example only - needs a VNet, subnet and private DNS zone privatelink.vaultcore.azure.net
az network private-endpoint create \
  --name pe-kv --resource-group $RG \
  --vnet-name <vnet-name> --subnet <subnet-name> \
  --private-connection-resource-id $KV_ID \
  --group-id vault --connection-name kv-conn

az keyvault update --name $KV --resource-group $RG --public-network-access Disabled
```

What this does:

- A **private endpoint** gives the vault a private IP in your VNet. The private DNS zone `privatelink.vaultcore.azure.net` makes the normal vault name resolve to that IP.
- The App Service must then use **VNet integration** to reach the private endpoint.
- Alternative: keep public access but set the **firewall** to "selected networks" with allowed IPs or VNets (`az keyvault network-rule add`, `--default-action Deny`), and decide whether to allow trusted Microsoft services.
- Do this after the lab works. If you lock it down first, your laptop and the CLI will get `Forbidden` errors.

### Verify it works

```bash
curl -s https://$APP.azurewebsites.net/ | python3 -m json.tool
```

Expected output:

```json
{
    "kv_reference_loaded": true,
    "kv_reference_preview": "<p****",
    "sdk_secret_loaded": true,
    "sdk_secret_preview": "<p****"
}
```

Other checks:

```bash
# Role assignments on the vault
az role assignment list --scope $KV_ID -o table

# The app identity exists
az webapp identity show -n $APP -g $RG

# No secret values stored in app settings (only the reference string)
az webapp config appsettings list -n $APP -g $RG --query "[?name=='API_KEY'].value" -o tsv
```

The last command should print `@Microsoft.KeyVault(SecretUri=...)`, not the secret. In the portal, **Environment variables** shows a green "Key vault Reference" status when it resolves.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `Forbidden ... does not have secrets get permission` or `ForbiddenByRbac` | Missing data-plane role, or role not applied yet | Assign "Key Vault Secrets User"; wait a few minutes |
| You are Owner but cannot add secrets | Owner is control plane only on RBAC vaults | Assign yourself "Key Vault Secrets Officer" |
| App shows the raw `@Microsoft.KeyVault(...)` string | Reference could not resolve | Check identity, role, URI spelling (trailing slash), firewall; check status in the portal |
| `DefaultAzureCredential failed to retrieve a token` locally | Not logged in, or wrong tenant | `az login --tenant <tenant-id>` |
| Works with system identity, fails after adding user-assigned | SDK picks the wrong identity | Set `AZURE_CLIENT_ID`; set `keyVaultReferenceIdentity` |
| `ForbiddenByFirewall` / `ForbiddenByConnection` | Vault firewall or public access disabled | Add private endpoint + VNet integration, or allow the IP/VNet |
| HTTP 429 throttling | Reading secrets on every request | Cache values, read at startup, use references |
| `VaultAlreadyExists` / name conflict after delete | Soft-deleted vault still holds the name | `az keyvault list-deleted`, then recover or wait (purge is blocked with purge protection) |
| App does not see the new secret version | Cache or pinned version | Wait for TTL, restart app, remove version from URI |

### Clean up

```bash
az group delete --name $RG --yes --no-wait
```

The vault stays in a soft-deleted state for the retention period (7 days in this lab). Because purge protection is on, `az keyvault purge` will be refused until that period ends. That is expected and shows the feature works. Check with:

```bash
az keyvault list-deleted --query "[].{name:name, scheduledPurge:properties.scheduledPurgeDate}" -o table
```

If you repeat the lab without purge protection, you can purge right away with `az keyvault purge --name $KV`.

### Next improvements

- Replace the database password completely with Entra ID auth (managed identity to Azure SQL or PostgreSQL).
- Automate rotation with Event Grid `SecretNearExpiry` events and a Function.
- Add a private endpoint and disable public network access.
- Build everything with Bicep or Terraform, including role assignments, and deploy with an OIDC pipeline.
- Add Azure Policy: require RBAC mode, purge protection, private link and diagnostic settings on all vaults.
- Alert on unusual `SecretGet` volume or repeated 403s with a log search alert.

### How to explain this project in an interview

> "This was a hands-on lab to remove credentials from an application completely. I created a Key Vault in RBAC mode with soft delete and purge protection. I gave myself Key Vault Secrets Officer to add secrets, and gave the app's system-assigned managed identity only Key Vault Secrets User at the vault scope, and also tried secret-level scope. The Flask app on App Service uses DefaultAzureCredential and SecretClient, so the same code uses my az login locally and the managed identity in Azure. I cached secret values to avoid throttling. I also used App Service Key Vault references so a setting becomes an environment variable with no SDK code. I tested a user-assigned identity with AZURE_CLIENT_ID and keyVaultReferenceIdentity. Finally I sent AuditEvent logs to Log Analytics and wrote KQL to see who read each secret and which calls were denied. I also practiced rotating a secret through versions."

Points that impress interviewers:

- You know the difference between control-plane roles (Owner, Contributor) and data-plane roles (Secrets User, Secrets Officer).
- You can explain `DefaultAzureCredential` and why the same code works locally and in Azure.
- You understand rotation, versions, caching and how Key Vault references refresh.
- You mention the next step: removing secrets altogether with Entra ID auth to downstream services.

## Interview Questions

<details><summary>Q1. [Basic] What is a managed identity, and what is the difference between system-assigned and user-assigned?</summary>

**Answer:**

A managed identity is an Entra ID identity that Azure creates and manages for a resource. Azure handles the credential and rotates it. Your code asks the local identity endpoint for a token. There is no secret to store.

| System-assigned | User-assigned |
| --- | --- |
| Tied to one resource | Separate Azure resource |
| Deleted with the resource | Lives until you delete it |
| One per resource | Can be shared by many resources |
| Good for simple, single apps | Good for IaC pre-creation, shared access, apps that are recreated often |

With a user-assigned identity you usually set `AZURE_CLIENT_ID` so the SDK knows which identity to use.

</details>

<details><summary>Q2. [Basic] Access policies or Azure RBAC for Key Vault: which do you choose and why?</summary>

**Answer:**

Choose **Azure RBAC**. It is the recommended model and the default for new vaults in current tooling.

- RBAC uses the same role assignments, PIM, and Azure Policy as the rest of Azure.
- It supports scope at vault level or a single secret, key or certificate.
- Access policies are vault-wide only, and anyone with Contributor on the vault can change access policies and grant themselves data access. With RBAC, assigning roles needs Owner or User Access Administrator.
- Access policies have a limit of 1024 entries per vault.

</details>

<details><summary>Q3. [Basic] What do soft delete and purge protection do?</summary>

**Answer:**

- **Soft delete** keeps deleted vaults and objects recoverable for 7-90 days. It is always on for new vaults.
- **Purge protection** stops anyone, including admins, from permanently deleting (purging) a vault or object before the retention period ends. Once enabled it cannot be disabled.

Together they protect against accidental deletion and against an attacker or insider who tries to destroy keys and secrets. A side effect: the vault name stays reserved until it is purged.

</details>

<details><summary>Q4. [Intermediate] How does <code>DefaultAzureCredential</code> work, and what are the risks of using it in production?</summary>

**Answer:**

It tries a chain of credential types in order: environment variables (service principal), workload identity, managed identity, then developer tools such as Azure CLI, Azure PowerShell and Azure Developer CLI. The first one that returns a token wins.

Benefits: one code path for local and cloud.

Risks and tips:

- It can pick an unexpected credential (for example env vars left on a VM). In production you can use `ManagedIdentityCredential` directly, or set `AZURE_TOKEN_CREDENTIALS` to limit the chain in newer SDK versions.
- Probing many credentials adds startup latency.
- Create the credential once and reuse it.

</details>

<details><summary>Q5. [Intermediate] Compare App Service Key Vault references with reading secrets in code through the SDK.</summary>

**Answer:**

| Key Vault references | SDK in code |
| --- | --- |
| No code changes; value appears as an env var | Needs `azure-identity` and `azure-keyvault-secrets` |
| Refresh within 24 hours or on restart/config change | You control refresh and caching |
| Works only on App Service, Functions, Logic Apps Standard, Container Apps (similar feature) | Works anywhere |
| Status visible in portal | You handle errors |

Use references for simple config secrets. Use the SDK when you need fast rotation, many secrets, or certificates and keys.

</details>

<details><summary>Q6. [Intermediate] How do you rotate a secret without downtime?</summary>

**Answer:**

1. Create the new credential in the target system while the old one still works (two valid passwords or two keys, like Storage key1/key2).
2. Write it to Key Vault as a new version of the same secret.
3. Apps pick it up: SDK cache expiry, or a versionless Key Vault reference refresh or restart.
4. Confirm in audit logs and app metrics that the new version is used.
5. Revoke the old credential and disable the old version.

Automate with Event Grid `SecretNearExpiry` and a Function. Best option: remove the secret by using Entra ID auth with managed identity.

</details>

<details><summary>Q7. [Intermediate] The app returns 403 when reading a secret. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

1. Read the error text: `ForbiddenByRbac` means a missing role, `ForbiddenByFirewall` or `ForbiddenByConnection` means network.
2. Confirm which identity is calling: `az webapp identity show`, and check `AZURE_CLIENT_ID` if the app has several identities.
3. `az role assignment list --scope <vault-id> --assignee <principal-id>`: is "Key Vault Secrets User" there at the right scope?
4. Check the vault is in RBAC mode (`enableRbacAuthorization`). If it uses access policies, RBAC roles have no effect.
5. Check the `AzureDiagnostics` audit log for the denied call, its caller and IP.
6. Wait a few minutes after new role assignments; propagation is not instant.

</details>

<details><summary>Q8. [Advanced] How would you design Key Vault for many apps and several environments? <em>(scenario)</em></summary>

**Answer:**

- **One vault per app per environment** (for example `kv-orders-prod`). This limits blast radius, keeps RBAC simple and spreads throttling limits.
- Each app gets its own managed identity with **Key Vault Secrets User** on its own vault only.
- Humans get access through PIM (just-in-time) roles, not permanent ones.
- Private endpoints, public access disabled, purge protection on, diagnostics to a central Log Analytics workspace.
- Azure Policy enforces these settings.
- Everything is created by IaC through an OIDC-authenticated pipeline.

</details>

<details><summary>Q9. [Advanced] What is the difference between control-plane and data-plane access in Key Vault?</summary>

**Answer:**

- **Control plane** (management.azure.com): create or delete the vault, change networking, diagnostic settings, tags. Roles: Owner, Contributor, Key Vault Contributor.
- **Data plane** (`<vault>.vault.azure.net`): read and write secrets, keys and certificates. Roles: Key Vault Administrator, Secrets Officer, Secrets User, Crypto User, and others.

A Contributor on an RBAC vault cannot read secrets. This separation is why platform admins can manage the vault without seeing app secrets.

</details>
