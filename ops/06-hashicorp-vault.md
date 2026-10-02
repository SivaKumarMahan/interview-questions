# Ops: HashiCorp Vault

> Vault secrets engines, auth methods, policies, leases, seal/unseal, Raft HA, Kubernetes integrations, audit devices, cloud secret manager comparison, and the BSL license change and OpenBao fork.

## Key Concepts

### What Vault Is

Vault is an identity-based secrets and encryption service. A client proves who it is with an **auth method**, gets a **token** with **policies** attached, and uses that token to read or generate secrets from a **secrets engine**. Everything is deny by default, and every request can be written to an **audit device**.

For the wider pipeline view (CI identity, rotation, leaked keys), see [DevSecOps](02-devsecops.md). For Kubernetes Secrets basics, see [Kubernetes security, RBAC, and secrets](../kubernetes/06-security-rbac-secrets.md).

The flow below is the same for every client: authenticate, get a token, use it, and the lease expires on its own.

```mermaid
flowchart LR
    C["Client<br/>Pod, CI job, EC2"] -->|"1. login with identity<br/>JWT, IAM, AppRole"| A["Auth method"]
    A -->|"2. token + policies"| C
    C -->|"3. read or generate"| S["Secrets engine<br/>KV, database, AWS, PKI"]
    S -->|"4. secret + lease"| C
    A & S --> AU["Audit device<br/>every request logged"]
```

### Secrets Engines

| Engine | What it does | Typical use |
| --- | --- | --- |
| **KV v2** | Stores static key/value secrets with versions, soft delete, and check-and-set | Third-party API keys you cannot make dynamic |
| **Database** | Creates a short-lived database user per request and drops it when the lease ends | App credentials for PostgreSQL, MySQL, and others |
| **AWS** | Issues IAM user keys, assumed-role, or federation-token credentials on demand | Short-lived AWS access for tools that cannot use native roles |
| **PKI** | Acts as a CA and issues short-lived X.509 certificates | Internal mTLS, often with cert-manager's Vault issuer |
| **Transit** | Encrypts, decrypts, signs, and rotates keys; the key never leaves Vault | "Encryption as a service" for app data |

```bash
vault secrets enable -path=secret kv-v2
vault kv put secret/payments/api key=abc123
vault kv get -version=1 secret/payments/api
```

### Auth Methods

- **Kubernetes:** a Pod sends its ServiceAccount JWT. Vault checks it with the Kubernetes `TokenReview` API and maps the ServiceAccount and namespace to a role.
- **AWS IAM:** the client signs an `sts:GetCallerIdentity` request. Vault forwards it to AWS STS and maps the returned IAM role ARN to a Vault role. No secret is stored on the client.
- **AppRole:** a RoleID plus a SecretID for machines with no platform identity. The SecretID must be delivered safely and should be short-lived or single-use.
- **JWT/OIDC:** humans log in through an IdP (OIDC), and CI jobs log in with their OIDC token (JWT), bound to claims such as repository and branch.

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

Vault starts **sealed**: data is encrypted and the root key is not in memory. With **Shamir** unseal, operators enter a threshold of key shares (for example 3 of 5). With **auto-unseal**, Vault asks a KMS or HSM (AWS KMS, Azure Key Vault, GCP KMS) to decrypt the root key at startup. Auto-unseal gives you **recovery keys**, which cannot decrypt data on their own.

**Integrated storage (Raft)** keeps data on the Vault nodes themselves. One node is the active leader. Standbys forward requests to the leader (Enterprise performance standbys can serve some reads). Five nodes across three AZs tolerate two node failures.

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

- **Auth methods** turn an identity (Kubernetes ServiceAccount, AWS IAM role, OIDC token) into a Vault token.
- **Policies** say which paths that token can touch.
- **Secrets engines** store or generate secrets (KV, database, AWS, PKI, transit).
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

```bash
vault write database/config/orders \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@orders-db:5432/orders" \
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

**How to verify:** `vault list sys/leases/lookup/database/creds/orders-ro/` and check the DB role list.

</details>

<details><summary>Q4. [Intermediate] How does a Pod on Kubernetes authenticate to Vault without any stored secret?</summary>

**Answer:**

I use the Kubernetes auth method. The Pod already has a projected ServiceAccount token. Vault validates that token with the cluster's TokenReview API and maps the ServiceAccount name and namespace to a Vault role and policy.

```bash
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

**Pitfalls:** binding to `*` namespaces, sharing the `default` ServiceAccount across apps, and a Vault outside the cluster that cannot reach the API server for TokenReview. For a remote cluster, Vault needs the cluster CA and a reviewer JWT, or it can use the client's own JWT as the reviewer token.

</details>

<details><summary>Q5. [Intermediate] How do you let a GitHub Actions or GitLab CI job read secrets from Vault with no long-lived token?</summary>

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

**Pitfalls:** binding only on `repository` lets any branch or fork-triggered workflow deploy to prod. Bind `ref`, and environment where the platform provides it. Always set `bound_audiences`.

TODO (Siva): add which CI system you actually used with Vault (or Azure DevOps with a cloud secret manager) and how jobs authenticated.

</details>

<details><summary>Q6. [Intermediate] Explain leases, renewal, TTL, and max TTL. Why did my app lose access after a few days?</summary>

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

<details><summary>Q7. [Intermediate] What do seal and unseal mean, and why use auto-unseal with AWS KMS?</summary>

**Answer:**

Vault's storage is encrypted with an encryption key, which is protected by a root key. While sealed, Vault cannot decrypt anything and refuses requests. Unsealing puts the root key back in memory.

With Shamir, someone must enter key shares after every restart. That breaks autoscaling and slows incident recovery. With auto-unseal, Vault calls AWS KMS to decrypt the root key at boot:

```hcl
seal "awskms" {
  region     = "eu-west-1"
  kms_key_id = "alias/vault-unseal"
}
```

**Verify:** `vault status` shows `Sealed false` and `Recovery Seal true`.

**Trade-offs:** the KMS key becomes critical. Deleting it, losing the IAM permission, or a region outage can stop Vault from starting. Protect it with a key policy, deletion protection, and CloudTrail alerts on `Decrypt` from unexpected principals. Recovery keys are still needed for operations like generating a root token, so store them split between people.

</details>

<details><summary>Q8. [Advanced] Design a highly available Vault cluster on AWS with integrated Raft storage. <em>(scenario)</em></summary>

**Answer:**

- **Topology:** five Vault nodes across three AZs (2-2-1), integrated Raft storage on encrypted EBS, auto-unseal with KMS, and an internal NLB or ALB that health-checks `/v1/sys/health` so only the active node takes writes.
- **Quorum:** Raft needs a majority. Five nodes tolerate two failures; three tolerate one. Even numbers add cost without extra tolerance.
- **Autopilot:** enable dead-server cleanup and server stabilization so a replaced node joins cleanly.
- **TLS everywhere:** client to Vault and node to node for Raft.
- **Backups:** scheduled `vault operator raft snapshot save` to an S3 bucket with versioning and Object Lock. Test restore into an isolated cluster.
- **DR beyond one region:** DR and performance replication are Enterprise features. On Community or OpenBao, plan snapshot-based restore in a second region and accept a higher RPO and RTO.

```bash
vault operator raft list-peers
vault operator raft autopilot state
vault operator raft snapshot save /tmp/vault-$(date +%F).snap
```

**Pitfalls:** putting Vault on the same Kubernetes cluster it protects (chicken and egg during a cluster outage), no tested restore, and losing quorum after replacing two nodes at once in a rolling AMI update.

</details>

<details><summary>Q9. [Intermediate] Vault Agent Injector vs Vault Secrets Operator vs CSI provider: which do you choose?</summary>

**Answer:**

| | Agent Injector | Vault Secrets Operator | CSI provider |
| --- | --- | --- | --- |
| Delivery | Files in a shared volume | Native Kubernetes Secret | Volume mounted at Pod start |
| Extra per Pod | Sidecar and init container | Nothing (one operator) | Nothing (DaemonSet driver) |
| Secret stored in etcd | No | Yes | Only if you enable sync |
| Rotation | Agent renews and re-renders | Operator re-syncs, can roll Deployments | Optional rotation polling |

My default is **VSO** when apps already read env vars or Kubernetes Secrets, because it is simple and has no sidecars. I make sure etcd encryption and RBAC on Secrets are tight. I use **Agent Injector** when the secret must never land in etcd, or I need templating and lease renewal of dynamic credentials inside the Pod. I use **CSI** when the cluster already uses the Secrets Store CSI driver for several providers.

Whichever I choose, the app must handle a changed file or a restart. Otherwise rotation just causes outages.

</details>

<details><summary>Q10. [Advanced] How do you set up audit devices, and how do you use them in a suspected secret leak? <em>(scenario)</em></summary>

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

<details><summary>Q11. [Advanced] When do you choose Vault over AWS Secrets Manager or Azure Key Vault?</summary>

**Answer:**

| | Vault / OpenBao | AWS Secrets Manager | Azure Key Vault |
| --- | --- | --- | --- |
| Operations | You run it (or pay for HCP Vault) | Fully managed | Fully managed |
| Identity | Many auth methods, any cloud or on-prem | IAM | Entra ID, managed identity |
| Dynamic secrets | Many engines (DB, cloud, PKI, SSH) | Rotation through Lambda functions | Rotation through Event Grid or functions |
| Encryption as a service | Transit engine | KMS (separate service) | Keys and HSM in the same vault |
| Native integrations | Kubernetes, CI, Terraform | ECS, Lambda, RDS, EKS | AKS, App Service, Azure DevOps |

On a mostly-AWS stack like ECS Fargate, I prefer **Secrets Manager or SSM Parameter Store**, because the task definition can inject them natively through the execution role and there is no cluster to patch. Vault earns its cost when I need multi-cloud or on-prem coverage, true dynamic credentials across many systems, an internal PKI, transit encryption, or one policy and audit model across clouds.

The hidden cost of Vault is people: upgrades, unseal key custody, backups, HA, and on-call for a tier-zero system.

TODO (Siva): add which secret store your team actually used (for example SSM Parameter Store for ECS) and why.

</details>

<details><summary>Q12. [Advanced] Your company asks whether to stay on Vault after the BSL change or move to OpenBao. How do you answer? <em>(scenario)</em></summary>

**Answer:**

First I separate facts from fear. BSL 1.1 lets you use Vault internally in production. The restriction is on offering a product that competes with HashiCorp. Each release converts to MPL 2.0 after four years. So most end-user companies are not breaking the license by self-hosting Vault. Legal should confirm for our case, especially if we sell a platform or managed service.

Then I compare on real criteria:

- **Features:** Vault Enterprise has replication, namespaces, HSM support, and Sentinel. OpenBao has added some features of its own (for example namespaces), but the two products are drifting apart.
- **Support and roadmap:** IBM owns HashiCorp since February 2025. OpenBao is governed by the community under the OpenSSF.
- **Compatibility:** OpenBao forked from Vault 1.14.x. Clients, the Terraform provider, and plugins mostly work, but I test auth methods, secrets engines, Agent or VSO equivalents, and storage migration in staging.
- **Cost:** Enterprise licensing vs the cost of running and supporting the fork ourselves.

If we use Community features only and want an OSI license, OpenBao is a reasonable path with a staged migration. If we depend on Enterprise features or vendor support, staying on Vault is fine. Either way, keep apps coupled to a standard interface (files, env, Kubernetes Secrets) so the backend can change later.

</details>
