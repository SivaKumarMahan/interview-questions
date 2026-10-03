# Ops: HashiCorp Vault

> Vault secrets engines (including Azure), auth methods (Azure managed identity, AKS, AppRole, OIDC), policies, leases, seal and auto-unseal with Azure Key Vault, Raft HA, Kubernetes integrations, audit devices, Vault vs Azure Key Vault, and the BSL license change and OpenBao fork.

## Key Concepts

### What Vault Is

Vault is an identity-based secrets and encryption service. A client proves who it is with an **auth method**, gets a **token** with **policies** attached, and uses that token to read or generate secrets from a **secrets engine**. Everything is deny by default, and every request can be written to an **audit device**.

For the wider pipeline view (CI identity, rotation, leaked keys), see [DevSecOps](02-devsecops.md). For Kubernetes Secrets basics, see [Kubernetes security, RBAC, and secrets](../kubernetes/06-security-rbac-secrets.md).

The flow below is the same for every client: authenticate, get a token, use it, and the lease expires on its own.

```mermaid
flowchart LR
    C["Client<br/>AKS Pod, CI job, Azure VM"] -->|"1. login with identity<br/>JWT, managed identity, AppRole"| A["Auth method"]
    A -->|"2. token + policies"| C
    C -->|"3. read or generate"| S["Secrets engine<br/>KV, database, Azure, PKI"]
    S -->|"4. secret + lease"| C
    A & S --> AU["Audit device<br/>every request logged"]
```

### Secrets Engines

| Engine | What it does | Typical use |
| --- | --- | --- |
| **KV v2** | Stores static key/value secrets with versions, soft delete, and check-and-set | Third-party API keys you cannot make dynamic |
| **Database** | Creates a short-lived database user per request and drops it when the lease ends | App credentials for Azure Database for PostgreSQL Flexible Server, MySQL, and others |
| **Azure** | Creates a dynamic Entra ID service principal with Azure role assignments, or adds a short-lived password to an existing one | Short-lived Azure access for tools that cannot use a managed identity |
| **PKI** | Acts as a CA and issues short-lived X.509 certificates | Internal mTLS, often with cert-manager's Vault issuer |
| **Transit** | Encrypts, decrypts, signs, and rotates keys; the key never leaves Vault | "Encryption as a service" for app data |

```bash
vault secrets enable -path=secret kv-v2
vault kv put secret/payments/api key=abc123
vault kv get -version=1 secret/payments/api
```

### Auth Methods

- **Azure:** an Azure VM, VM Scale Set, or other resource with a **managed identity** gets an Entra ID access token from the Instance Metadata Service (IMDS) and sends it to Vault. Vault checks the token signature, issuer, and audience, then checks the role bindings (service principal IDs, groups, subscription, resource group, scale set). No secret is stored on the client.
- **Kubernetes (AKS):** a Pod sends its ServiceAccount JWT. Vault checks it with the Kubernetes `TokenReview` API and maps the ServiceAccount and namespace to a role.
- **AppRole:** a RoleID plus a SecretID for machines with no platform identity. The SecretID must be delivered safely and should be short-lived or single-use.
- **JWT/OIDC:** humans log in through Entra ID (OIDC), and CI jobs (GitHub Actions, GitLab CI, or Azure DevOps) log in with their OIDC token (JWT), bound to claims such as repository, branch, or service connection.

```bash
# On an Azure VM with a managed identity
vault auth enable azure
vault write auth/azure/config \
  tenant_id="$TENANT_ID" resource="https://management.azure.com/"
vault write auth/azure/role/reports-vm \
  bound_service_principal_ids="$MI_PRINCIPAL_ID" \
  bound_subscription_ids="$SUB_ID" bound_resource_groups="rg-reports-prod" \
  token_policies=reports-read token_ttl=30m

JWT=$(curl -s -H Metadata:true \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F" \
  | jq -r .access_token)
vault write auth/azure/login role=reports-vm jwt="$JWT" \
  subscription_id="$SUB_ID" resource_group_name="rg-reports-prod" vm_name="vm-reports-01"
```

### Policies, Tokens, and Leases

Policies are HCL rules on paths with capabilities (`read`, `create`, `update`, `delete`, `list`, `sudo`, `deny`). A token carries policies and a TTL. Dynamic secrets carry a **lease** with a TTL and max TTL. Clients renew the lease, or Vault revokes the secret when it expires. Revoking a parent token revokes its child tokens and their leases.

```hcl
path "secret/data/payments/*" {
  capabilities = ["read"]
}
path "database/creds/payments-ro" {
  capabilities = ["read"]
}
```

### Seal, Unseal, and HA

Vault starts **sealed**: data is encrypted and the root key is not in memory. With **Shamir** unseal, operators enter a threshold of key shares (for example 3 of 5). With **auto-unseal**, Vault asks a cloud key service or HSM (for example an Azure Key Vault key, or an HSM through PKCS#11 in Vault Enterprise) to decrypt the root key at startup. Auto-unseal gives you **recovery keys**, which cannot decrypt data on their own.

**Integrated storage (Raft)** keeps data on the Vault nodes themselves. One node is the active leader. Standbys forward requests to the leader (Enterprise performance standbys can serve some reads). Five nodes across three Azure availability zones tolerate two node failures.

```hcl
storage "raft" {
  path    = "/opt/vault/data"
  node_id = "vault-1"
  retry_join {
    leader_api_addr = "https://vault-2.vault.internal:8200"
  }
  retry_join {
    leader_api_addr = "https://vault-3.vault.internal:8200"
  }
}
api_addr     = "https://vault-1.vault.internal:8200"
cluster_addr = "https://vault-1.vault.internal:8201"
```

Raft replaces an external storage backend such as Consul, so there is one less system to run. Older setups used the Azure Blob storage backend, but it has no HA support, so Raft is the normal choice today.

### Kubernetes Integrations

| Option | How it works | Pick it when |
| --- | --- | --- |
| **Vault Agent Injector** | Mutating webhook adds an Agent sidecar that logs in and renders secrets to a shared volume | You want files, templates, and lease renewal without app changes |
| **Vault Secrets Operator (VSO)** | Operator syncs Vault secrets into native Kubernetes Secrets and can restart Deployments on change | Apps already read Kubernetes Secrets or env vars |
| **Secrets Store CSI provider** | CSI driver mounts secrets as a volume at Pod start | You already use the CSI driver for several secret backends |

### Licensing: BSL and OpenBao

On 10 August 2023 HashiCorp moved future releases of Vault, Terraform, and its other core products from MPL 2.0 to the **Business Source License 1.1**. BSL allows internal production use but restricts offering a competing product, so it is not an OSI open-source license. IBM completed its acquisition of HashiCorp on 27 February 2025.

**OpenBao** is a community fork of Vault 1.14.x under MPL 2.0. It was announced under the Linux Foundation in December 2023 and joined the OpenSSF as a sandbox project in June 2025. Its API and CLI started compatible with Vault, but the two are drifting apart, so test before you switch.

## Interview Questions

<details><summary>Q1. [Basic] What problem does Vault solve, and what are its main building blocks?</summary>

**Answer:**

Vault removes static, long-lived secrets from code, config, and CI variables. Instead, each workload proves its identity and gets only the secrets its policy allows, ideally with a short lifetime.

The building blocks are:

- **Auth methods** turn an identity (Kubernetes ServiceAccount, Azure managed identity, OIDC token) into a Vault token.
- **Policies** say which paths that token can touch.
- **Secrets engines** store or generate secrets (KV, database, Azure, PKI, transit).
- **Leases** give every dynamic secret an expiry and support renewal and revocation.
- **Audit devices** log every request and response, with secret values HMAC-hashed.

**How to verify:** `vault status` shows seal state and HA mode. `vault token lookup` shows the policies and TTL on your current token.

</details>

<details><summary>Q2. [Basic] What is the difference between KV v1 and KV v2, and why does the API path look different?</summary>

**Answer:**

KV v1 stores one value per path with no history. KV v2 keeps versions, supports soft delete and undelete, `destroy` for permanent removal, check-and-set to stop lost updates, and metadata such as `max_versions`.

The pitfall is the path. The CLI hides it, but the API and policies use `secret/data/<path>` for values and `secret/metadata/<path>` for listing and deleting history:

```bash
vault kv put secret/app/db password=s3cret         # CLI path
vault kv rollback -version=2 secret/app/db
curl -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/app/db
```

A policy written as `path "secret/app/*"` silently matches nothing on KV v2. It must be `secret/data/app/*` (and `secret/metadata/app/*` if the client needs to list).

</details>

<details><summary>Q3. [Intermediate] How do dynamic database credentials work, and what can go wrong?</summary>

**Answer:**

Vault holds one privileged connection to the database. When an app reads `database/creds/<role>`, Vault runs the role's creation SQL, returns a unique username and password, and attaches a lease. When the lease expires or is revoked, Vault runs the revocation SQL and drops the user.

The example uses Azure Database for PostgreSQL Flexible Server. The server requires TLS by default, so the connection URL sets `sslmode=require`.

```bash
vault write database/config/orders \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@pg-orders-prod.postgres.database.azure.com:5432/orders?sslmode=require" \
  allowed_roles="orders-ro" username="vault_admin" password="..."
vault write database/roles/orders-ro db_name=orders default_ttl=1h max_ttl=24h \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";"
vault read database/creds/orders-ro
vault write -f database/config/orders/rotate-root   # Vault now owns the admin password
```

**Pitfalls:**

- The app must reload credentials before `max_ttl`. Connection pools that keep old connections fail when the user is dropped.
- Many Pods times short TTLs means many DB users and lease churn. Watch lease count.
- Objects created by a dynamic user belong to that user. Grant through a group role so ownership survives.
- Use **static roles** when an app or legacy system needs a fixed username with a rotated password.
- **Flexible Server specifics:** there is no superuser. Create a dedicated `vault_admin` login with `CREATEROLE` from the server admin account, and do not give Vault the server admin itself. If the server uses private access (VNet integration or a Private Endpoint), Vault must run in a network that can reach it and resolve the private DNS zone.
- **Alternative:** for apps that run on Azure, Microsoft Entra authentication on Flexible Server lets the app connect with its managed identity token and no password at all. Vault adds value when you also need the same pattern on-premises or in other databases.

**How to verify:** `vault list sys/leases/lookup/database/creds/orders-ro/` and check the DB role list (`\du` in `psql`).

</details>

<details><summary>Q4. [Intermediate] How does the Vault Azure secrets engine issue short-lived Azure credentials?</summary>

**Answer:**

The Azure secrets engine creates Entra ID service principals on demand. Each read of `azure/creds/<role>` creates a new application and service principal (named with a `vault-` prefix), assigns the Azure roles listed in the Vault role, and returns a `client_id` and `client_secret` with a lease. When the lease ends, Vault deletes the service principal and its role assignments.

```bash
vault secrets enable azure
vault write azure/config \
  subscription_id="$SUB_ID" tenant_id="$TENANT_ID" \
  client_id="$VAULT_SP_CLIENT_ID" client_secret="$VAULT_SP_SECRET"
vault write azure/roles/rg-reader ttl=1h max_ttl=8h azure_roles=- <<EOF
[
  {
    "role_name": "Reader",
    "scope": "/subscriptions/$SUB_ID/resourceGroups/rg-reports-prod"
  }
]
EOF
vault read azure/creds/rg-reader
```

If Vault runs on an Azure VM with a managed identity, you can leave out `client_secret` in `azure/config`. For an existing service principal, set `application_object_id` on the role. Vault then adds and removes short-lived passwords on that app instead of creating new ones.

**Permissions Vault itself needs:**

- Microsoft Graph application permissions `Application.ReadWrite.OwnedBy` and `GroupMember.ReadWrite.All` for dynamic service principals.
- An Azure role that can create role assignments (for example User Access Administrator) at the scopes you use. Keep that scope as small as possible, because Vault becomes a powerful identity.

**Pitfalls:**

- Entra ID and role assignments replicate with a delay. A brand-new credential can fail for a short time, so tools need a retry.
- Azure roles are assigned once, when the service principal is created. Changing the Vault role does not update credentials that already exist.
- Issue time grows with the number of role assignments.
- Prefer a managed identity or workload identity federation for anything that runs on Azure or in a CI system that supports OIDC. Use this engine for tools that cannot use those options.

</details>

<details><summary>Q5. [Intermediate] How does a Pod on AKS authenticate to Vault without any stored secret?</summary>

**Answer:**

I use the Kubernetes auth method. The Pod already has a projected ServiceAccount token. Vault validates that token with the cluster's TokenReview API and maps the ServiceAccount name and namespace to a Vault role and policy.

```bash
K8S_API=$(az aks show -g rg-aks-prod -n aks-prod --query fqdn -o tsv)
vault auth enable kubernetes
vault write auth/kubernetes/config kubernetes_host="https://$K8S_API:443"
vault write auth/kubernetes/role/payments \
  bound_service_account_names=payments \
  bound_service_account_namespaces=payments-prod \
  token_policies=payments-read token_ttl=20m
```

Then I pick a delivery method: Vault Agent Injector annotations for file templates, or Vault Secrets Operator to sync into a Kubernetes Secret.

```yaml
annotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "payments"
  vault.hashicorp.com/agent-inject-secret-db: "database/creds/payments-ro"
```

**Pitfalls:** binding to `*` namespaces, sharing the `default` ServiceAccount across apps, and a Vault outside the cluster that cannot reach the API server for TokenReview. For a remote cluster, Vault needs the cluster CA and a reviewer JWT, or it can use the client's own JWT as the reviewer token. With a private AKS cluster, Vault must sit in a peered VNet that can resolve the API server's private DNS zone.

If Vault cannot reach the API server at all, another option is the JWT auth method pointed at the AKS OIDC issuer (`az aks show --query oidcIssuerProfile.issuerUrl`). Vault then checks ServiceAccount tokens offline with the issuer's public keys. The trade-off is that a deleted ServiceAccount is not detected until its token expires.

</details>

<details><summary>Q6. [Intermediate] How do you let a GitHub Actions, GitLab CI, or Azure DevOps job read secrets from Vault with no long-lived token?</summary>

**Answer:**

The CI platform issues an OIDC JWT for each job. Vault's JWT auth method trusts the platform's issuer and checks claims, so only a specific repo and branch can get the role.

```bash
vault auth enable jwt
vault write auth/jwt/config oidc_discovery_url="https://token.actions.githubusercontent.com" \
  bound_issuer="https://token.actions.githubusercontent.com"
vault write auth/jwt/role/deploy-prod role_type=jwt user_claim=repository \
  bound_audiences="https://vault.example.internal" \
  bound_claims_type=glob \
  bound_claims='{"repository":"my-org/payments","ref":"refs/heads/main"}' \
  token_policies=deploy-prod token_ttl=10m
```

The job requests `id-token: write`, logs in, reads only what that stage needs, and the token dies in minutes. Pull-request jobs get a different role with no production access.

**Azure DevOps:** a pipeline that uses a workload identity federation service connection signs in to Entra ID as that service principal with no stored secret. The job can then get an Entra access token (`az account get-access-token --resource <vault-auth-resource>`) and log in through Vault's Azure auth method, with the role bound to that service principal's object ID through `bound_service_principal_ids`. In many Azure-only setups the simpler choice is to skip Vault and link the pipeline to Azure Key Vault (the `AzureKeyVault@2` task or a variable group linked to Key Vault).

**Pitfalls:** binding only on `repository` lets any branch or fork-triggered workflow deploy to prod. Bind `ref`, and environment where the platform provides it. Always set `bound_audiences`. In Azure DevOps, use one service connection per environment, and protect the production one with approvals and checks.

TODO (Siva): add which CI system you actually used with Vault (or Azure DevOps with Key Vault) and how jobs authenticated.

</details>

<details><summary>Q7. [Intermediate] Explain leases, renewal, TTL, and max TTL. Why did my app lose access after a few days?</summary>

**Answer:**

Every dynamic secret and every non-root token has a lease. The TTL is how long it lives before renewal. Renewal extends it, but never beyond **max TTL**, counted from creation. After max TTL the client must log in again or fetch a new secret.

```bash
vault lease renew database/creds/orders-ro/<lease_id>
vault token lookup                # ttl, creation_ttl, explicit_max_ttl
vault lease revoke -prefix database/creds/orders-ro/   # incident: kill all creds for a role
```

The usual cause of "works for days, then fails" is an app that read a secret once at startup, renewed it, and hit max TTL (the system default max TTL is 768h, 32 days). The fix is to let Vault Agent or VSO handle renewal and re-fetch, and to make the app reload credentials from file or restart on change.

Revoking a parent token also revokes every child token and lease it created, which is useful in an incident and dangerous if a shared token is revoked by mistake.

</details>

<details><summary>Q8. [Intermediate] What do seal and unseal mean, and why use auto-unseal with Azure Key Vault?</summary>

**Answer:**

Vault's storage is encrypted with an encryption key, which is protected by a root key. While sealed, Vault cannot decrypt anything and refuses requests. Unsealing puts the root key back in memory.

With Shamir, someone must enter key shares after every restart. That breaks autoscaling and slows incident recovery. With auto-unseal, Vault calls Azure Key Vault to unwrap the root key at boot. When Vault runs on Azure VMs or a VM Scale Set with a **managed identity**, you leave out `client_id` and `client_secret`, so no Azure credential is stored on disk:

```hcl
seal "azurekeyvault" {
  tenant_id  = "00000000-0000-0000-0000-000000000000"
  vault_name = "kv-vault-unseal-prod"
  key_name   = "vault-unseal"
}
```

```bash
# Give the Vault nodes' managed identity crypto rights on the key (get, wrap, unwrap)
az role assignment create --assignee-object-id "$VAULT_MI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Crypto User" \
  --scope "$(az keyvault show -n kv-vault-unseal-prod --query id -o tsv)/keys/vault-unseal"
```

The scope here is the single key. The Key Vault must use the Azure RBAC permission model; with legacy access policies, grant the `get`, `wrapKey`, and `unwrapKey` key permissions instead. The values can also come from environment variables such as `AZURE_TENANT_ID`, `VAULT_AZUREKEYVAULT_VAULT_NAME`, and `VAULT_AZUREKEYVAULT_KEY_NAME`.

**Verify:** `vault status` shows `Sealed false`, `Recovery Seal true`, and `Seal Type azurekeyvault`.

**Trade-offs:** the Key Vault key becomes critical. Deleting it, losing the role assignment, a Key Vault firewall rule that blocks the Vault subnet, or a regional outage can stop Vault from starting. Turn on soft delete and **purge protection**, put a delete lock on the resource group, use a Private Endpoint, and send Key Vault diagnostic logs to Log Analytics with a KQL alert on key operations from unexpected identities. Recovery keys are still needed for operations like generating a root token, so store them split between people.

</details>

<details><summary>Q9. [Advanced] Design a highly available Vault cluster on Azure with integrated Raft storage. <em>(scenario)</em></summary>

**Answer:**

- **Topology:** five Vault nodes across three Azure availability zones (2-2-1), as VMs or a VM Scale Set in a private subnet. Integrated Raft storage on Premium SSD managed disks (encrypted at rest by default). Auto-unseal with Azure Key Vault through the nodes' managed identity. An internal Standard Azure Load Balancer with an HTTPS health probe on `/v1/sys/health`. The active node returns 200 and standbys return 429, so only the active node gets traffic.
- **Quorum:** Raft needs a majority. Five nodes tolerate two failures; three tolerate one. Even numbers add cost without extra tolerance.
- **Autopilot:** enable dead-server cleanup and server stabilization so a replaced node joins cleanly.
- **TLS everywhere:** client to Vault and node to node for Raft.
- **Network:** NSGs allow only the app subnets and the AKS node subnet on port 8200, and node-to-node traffic on 8201. Use Private Endpoints for the Key Vault and the backup Storage account.
- **Backups:** scheduled `vault operator raft snapshot save`, uploaded to a Blob Storage container with versioning, soft delete, and an immutability policy, using the node's managed identity (`az storage blob upload --auth-mode login`). Test restore into an isolated cluster.
- **DR beyond one region:** DR and performance replication are Enterprise features. On Community or OpenBao, plan snapshot-based restore in a second region and accept a higher RPO and RTO. The DR cluster must be able to use the same unseal key, so plan how that Key Vault key is available in the second region (a Key Vault backup can only be restored in the same Azure geography).

```bash
vault operator raft list-peers
vault operator raft autopilot state
vault operator raft snapshot save /tmp/vault-$(date +%F).snap
az storage blob upload --auth-mode login --account-name stvaultbackupprod \
  --container-name raft-snapshots --file /tmp/vault-$(date +%F).snap --name vault-$(date +%F).snap
```

**Pitfalls:** putting Vault on the same Kubernetes cluster it protects (chicken and egg during a cluster outage), no tested restore, and losing quorum after replacing two nodes at once during a VM Scale Set image upgrade. Set the rolling upgrade policy to one instance per batch and wait for Autopilot to report the new node healthy.

</details>

<details><summary>Q10. [Intermediate] Vault Agent Injector vs Vault Secrets Operator vs CSI provider: which do you choose?</summary>

**Answer:**

| | Agent Injector | Vault Secrets Operator | CSI provider |
| --- | --- | --- | --- |
| Delivery | Files in a shared volume | Native Kubernetes Secret | Volume mounted at Pod start |
| Extra per Pod | Sidecar and init container | Nothing (one operator) | Nothing (DaemonSet driver) |
| Secret stored in etcd | No | Yes | Only if you enable sync |
| Rotation | Agent renews and re-renders | Operator re-syncs, can roll Deployments | Optional rotation polling |

My default is **VSO** when apps already read env vars or Kubernetes Secrets, because it is simple and has no sidecars. I make sure etcd encryption and RBAC on Secrets are tight. I use **Agent Injector** when the secret must never land in etcd, or I need templating and lease renewal of dynamic credentials inside the Pod. I use **CSI** when the cluster already uses the Secrets Store CSI driver for several providers. On AKS that is common, because the `azure-keyvault-secrets-provider` add-on already runs the driver for Azure Key Vault.

Whichever I choose, the app must handle a changed file or a restart. Otherwise rotation just causes outages.

</details>

<details><summary>Q11. [Advanced] How do you set up audit devices, and how do you use them in a suspected secret leak? <em>(scenario)</em></summary>

**Answer:**

Enable at least two audit devices, for example file plus socket or syslog shipped to the SIEM. If Vault cannot write to **any** enabled audit device, it stops serving requests. That is a safety feature, so monitor disk space and the log pipeline.

```bash
vault audit enable file file_path=/var/log/vault/audit.log
vault audit enable -path=syslog syslog tag=vault facility=AUTH
vault audit list -detailed
```

Secret values are HMAC-SHA256 hashed in the log. In an incident I can check whether a known leaked value was served:

```bash
vault write sys/audit-hash/file input="the-leaked-value"
```

**Incident flow:** find the hash in the audit log, identify the `auth.display_name`, policies, and source IP, revoke the token tree and the leases (`vault lease revoke -prefix ...`), rotate the underlying static secret or DB root, and tighten the policy or auth role binding that allowed it. Ship audit logs to Splunk and alert on root token use, policy changes, and auth failures.

</details>

<details><summary>Q12. [Advanced] When do you choose Vault over Azure Key Vault?</summary>

**Answer:**

| | Vault / OpenBao | Azure Key Vault |
| --- | --- | --- |
| Operations | You run it (or pay for HCP Vault) | Fully managed, SLA backed |
| Identity | Many auth methods, any cloud or on-prem | Entra ID, managed identity, Azure RBAC |
| Dynamic secrets | Many engines (database, Azure, PKI, SSH) | None; static secrets with expiry dates. Rotation through Event Grid events and an Azure Function |
| Keys and certificates | Transit engine, PKI engine (internal CA) | Keys (HSM-backed in Premium or Managed HSM), certificates with auto-renewal from supported CAs |
| Native integrations | Kubernetes, CI systems, Terraform | AKS Secrets Store CSI add-on, App Service and Functions Key Vault references, Azure DevOps variable groups, Bicep `getSecret()` |
| Audit | Audit devices you ship to a SIEM | Diagnostic settings to Log Analytics, queried with KQL |

On an Azure-only stack (AKS, App Service, Functions, Azure DevOps), I prefer **Azure Key Vault plus managed identities**. There is no cluster to run, apps read secrets with their own identity, and Microsoft Entra authentication on Azure SQL or PostgreSQL Flexible Server can remove many database passwords completely. Vault earns its cost when I need on-prem or multi-cloud coverage, true dynamic credentials across many systems, an internal PKI with short-lived certificates, transit encryption, or one policy and audit model across environments.

The hidden cost of Vault is people: upgrades, unseal key custody, backups, HA, and on-call for a tier-zero system.

TODO (Siva): add how your team used Azure Key Vault and managed identities (for example with AKS, App Service, or Azure DevOps) and whether Vault was ever considered.

</details>

<details><summary>Q13. [Advanced] Your company asks whether to stay on Vault after the BSL change or move to OpenBao. How do you answer? <em>(scenario)</em></summary>

**Answer:**

First I separate facts from fear. BSL 1.1 lets you use Vault internally in production. The restriction is on offering a product that competes with HashiCorp. Each release converts to MPL 2.0 after four years. So most end-user companies are not breaking the license by self-hosting Vault. Legal should confirm for our case, especially if we sell a platform or managed service.

Then I compare on real criteria:

- **Features:** Vault Enterprise has replication, namespaces, HSM support, and Sentinel. OpenBao has added some features of its own (for example namespaces), but the two products are drifting apart.
- **Support and roadmap:** IBM owns HashiCorp since February 2025. OpenBao is governed by the community under the OpenSSF.
- **Compatibility:** OpenBao forked from Vault 1.14.x. Clients, the Terraform provider, and plugins mostly work, but I test auth methods, secrets engines, Agent or VSO equivalents, and storage migration in staging.
- **Cost:** Enterprise licensing vs the cost of running and supporting the fork ourselves.

If we use Community features only and want an OSI license, OpenBao is a reasonable path with a staged migration. If we depend on Enterprise features or vendor support, staying on Vault is fine. Either way, keep apps coupled to a standard interface (files, env, Kubernetes Secrets) so the backend can change later.

</details>
