# Azure: Identity Basics for DevOps (Entra ID, App Registrations, Service Principals, Managed Identities, Federated Credentials)

> A plain-English guide to the Azure identity pieces DevOps engineers use every day: Entra ID, app registrations, service principals, managed identities, federated credentials, workload identity, and Azure DevOps service connections, and how they fit together.

## Key Concepts

### The big picture in one analogy

Think of Azure as an office building:

- **Entra ID** is the security desk. It keeps the list of everyone allowed in and checks their ID cards.
- **Users** are employees who sign in with a password and MFA.
- **Apps and pipelines** are not people, but they also need an ID card. That card is a **service principal**.
- **A managed identity** is an ID card that Azure prints, renews, and keeps safe for you. You never see the secret.
- **A federated credential** is a trust rule: "If GitHub (or Azure DevOps, or Kubernetes) vouches for this job, let it in. No password needed."
- **Azure RBAC** is the list of which rooms each ID card can open (Reader, Contributor, Key Vault Secrets User, and so on).

Signing in (who are you?) is **authentication**, done by Entra ID. Permissions (what can you do?) is **authorization**, done by Azure RBAC.

### Microsoft Entra ID

Microsoft Entra ID is the new name for **Azure Active Directory (Azure AD)**. It is Microsoft's cloud identity service.

- A **tenant** is your organization's own copy of Entra ID. It has a **tenant ID** (a GUID).
- Every Azure subscription trusts exactly one tenant.
- The tenant holds **users**, **groups**, **app registrations**, **service principals**, and **managed identities**.
- Entra ID handles sign-in, MFA, and Conditional Access. It issues **tokens** (OAuth 2.0 / OpenID Connect) that apps send to Azure.

Entra ID is not the same as on-premises Active Directory. On-prem AD uses Kerberos and LDAP; Entra ID uses web protocols like OAuth and OIDC.

### App registration

An **app registration** is where you tell Entra ID "this application exists". It creates an **application object** with:

- An **Application (client) ID**: the app's username.
- **Credentials**: a client secret, a certificate, or federated credentials.
- **API permissions**: for example, permission to read users through Microsoft Graph.
- Redirect URIs and other sign-in settings, if humans log in to the app.

Think of the app registration as the **blueprint** of the app.

```bash
# Create an app registration (this also prints the appId)
az ad app create --display-name my-pipeline-app
```

### Service principal

A **service principal (SP)** is the **actual identity** of the app inside a tenant. It is what you give RBAC roles to and what signs in.

- App registration = the blueprint (one, in the home tenant).
- Service principal = the real ID card (one per tenant where the app is used).
- In the portal, service principals appear under **Enterprise applications**.

When you create an app registration in the portal, Azure creates the service principal for you automatically. With the CLI you often create it yourself:

```bash
APP_ID=$(az ad app create --display-name my-pipeline-app --query appId -o tsv)
az ad sp create --id "$APP_ID"

# Give it access to one resource group (least privilege)
az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope /subscriptions/<sub-id>/resourceGroups/rg-app-dev
```

A service principal can sign in with:

| Method | How it works | Risk |
| --- | --- | --- |
| Client secret | A password string | Can leak, expires, must be rotated |
| Certificate | A private key proves identity | Safer, but you still store and rotate it |
| Federated credential (OIDC) | Trusts a token from GitHub, Azure DevOps, Kubernetes, etc. | No secret at all. Best choice |

### Managed identity

A **managed identity** is a service principal that **Azure creates and manages for you**. You never see or rotate a secret. It only works for code running **inside Azure** (VMs, App Service, Functions, AKS, Container Apps, Data Factory, Databricks access connectors, and so on).

There are two types:

| Type | Lifecycle | Sharing | Good for |
| --- | --- | --- | --- |
| **System-assigned** | Created with the resource, deleted with it | One resource only | Simple cases: one VM or one Function App |
| **User-assigned** | A separate Azure resource you create | Can be attached to many resources | Shared identity, pre-created before the app, AKS workload identity, scale sets |

```bash
# System-assigned on a web app
az webapp identity assign -g rg-app -n my-webapp

# User-assigned, then attach it
az identity create -g rg-app -n id-orders-api
az webapp identity assign -g rg-app -n my-webapp \
  --identities /subscriptions/<sub-id>/resourceGroups/rg-app/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-orders-api
```

In code, use `DefaultAzureCredential` from the Azure SDK. It finds the managed identity automatically, so there are no secrets in config files.

### Federated credentials (workload identity federation)

A **federated credential** is a trust rule on an app registration or a user-assigned managed identity. It says: "Accept a token from this **issuer**, for this **subject**, and swap it for an Entra ID token."

It has three main fields:

- **Issuer:** who creates the token. Example: `https://token.actions.githubusercontent.com` for GitHub Actions.
- **Subject:** exactly which job or workload. Example: `repo:my-org/my-repo:environment:prod`.
- **Audience:** usually `api://AzureADTokenExchange`.

How the login works, step by step:

1. The pipeline asks its own platform (GitHub, Azure DevOps, Kubernetes) for a short-lived OIDC token.
2. It sends that token to Entra ID.
3. Entra ID checks the issuer, subject, and audience against the federated credential.
4. If they match, Entra ID returns an Azure access token, valid for about an hour.

Nothing long-lived is stored anywhere, so there is nothing to leak or rotate. One app or managed identity can have up to 20 federated credentials.

```bash
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-prod",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:my-org/my-repo:environment:prod",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

GitHub Actions workflow using it:

```yaml
permissions:
  id-token: write   # lets the job request an OIDC token
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: prod
    steps:
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: az group list -o table
```

Client ID, tenant ID, and subscription ID are not secrets. They are like a username; without a matching token they are useless.

### Workload identity

"Workload identity" is used in two related ways:

- **Workload identity (general):** any non-human identity, meaning service principals and managed identities.
- **Microsoft Entra Workload ID for AKS:** lets a **Kubernetes Pod** get Azure tokens using federated credentials. It replaces the deprecated **AAD Pod Identity**.

How AKS workload identity works:

1. Enable the **OIDC issuer** and **workload identity** on the cluster.
2. Create a **user-assigned managed identity** and give it RBAC (for example, Key Vault Secrets User).
3. Add a **federated credential** on that identity. Issuer = the cluster's OIDC issuer URL. Subject = `system:serviceaccount:<namespace>:<service-account-name>`.
4. Create the Kubernetes **ServiceAccount** with the identity's client ID, and label the Pod.

```bash
az aks update -g rg-aks -n aks-prod --enable-oidc-issuer --enable-workload-identity
ISSUER=$(az aks show -g rg-aks -n aks-prod --query oidcIssuerProfile.issuerUrl -o tsv)

az identity federated-credential create \
  --name orders-api \
  --identity-name id-orders-api \
  --resource-group rg-app \
  --issuer "$ISSUER" \
  --subject system:serviceaccount:orders:orders-api-sa \
  --audiences api://AzureADTokenExchange
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api-sa
  namespace: orders
  annotations:
    azure.workload.identity/client-id: "<managed-identity-client-id>"
---
apiVersion: v1
kind: Pod
metadata:
  name: orders-api
  namespace: orders
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: orders-api-sa
  containers:
    - name: app
      image: myacr.azurecr.io/orders-api:1.0.0
```

### Azure DevOps service connection

A **service connection** is a saved, named connection in an Azure DevOps project that lets pipelines reach an outside system. For Azure, the type is **Azure Resource Manager**. Behind it there is always an identity, usually a service principal or a managed identity.

Ways to authenticate an Azure Resource Manager service connection:

| Option | What it uses | Recommendation |
| --- | --- | --- |
| **Workload identity federation** (automatic or manual) | App registration or user-assigned managed identity + federated credential | Recommended. No secret |
| Service principal with secret | App registration + client secret | Legacy. Secret expires and can leak |
| Managed identity | The managed identity of a self-hosted agent VM | Only for self-hosted agents running in Azure |

```yaml
steps:
  - task: AzureCLI@2
    inputs:
      azureSubscription: sc-azure-prod   # name of the service connection
      scriptType: bash
      scriptLocation: inlineScript
      inlineScript: az group list -o table
```

Good practices for service connections:

- One connection per environment (dev, test, prod), each scoped to its own resource group or subscription.
- Do not tick **Grant access permission to all pipelines** for production connections. Approve pipelines one by one.
- Add **approvals and checks** (for example, a manual approval or branch control) on production connections.
- Convert old secret-based connections to workload identity federation.

### How everything fits together

```text
Microsoft Entra tenant
├── Users and groups ............................ humans
├── App registration (application object) ....... blueprint: client ID, permissions
│     ├── Credentials: secret | certificate | federated credential
│     └── Service principal (Enterprise app) ..... the real identity that gets RBAC
└── Managed identity ............................. service principal managed by Azure
      ├── System-assigned (tied to one resource)
      └── User-assigned (separate resource)
            └── Federated credential ............. trust GitHub / Azure DevOps / AKS tokens

Azure DevOps service connection ──uses──> service principal or managed identity
GitHub Actions azure/login      ──uses──> federated credential on an app or managed identity
AKS Pod (workload identity)     ──uses──> federated credential on a user-assigned managed identity
Azure RBAC role assignment      ──gives──> permissions on a scope to any of the above
```

### Quick comparison

| Term | One-line meaning |
| --- | --- |
| Entra ID | Microsoft's cloud identity service (formerly Azure AD) |
| Tenant | Your organization's instance of Entra ID |
| App registration | The definition (blueprint) of an app in Entra ID |
| Service principal | The identity of that app inside a tenant; gets RBAC roles |
| Enterprise application | The portal's name for a service principal |
| Managed identity | A service principal whose credentials Azure handles for you |
| Federated credential | A trust rule that accepts an external OIDC token instead of a secret |
| Workload identity federation | The login flow that uses federated credentials |
| Workload ID (AKS) | Pods getting Azure tokens through federated credentials |
| Service connection | Azure DevOps' saved link to Azure, backed by an SP or managed identity |
| API permissions | What an app can do in Microsoft Graph and other APIs |
| Azure RBAC roles | What an identity can do on Azure resources |

## Interview Questions

<details><summary>Q1. [Basic] What is Microsoft Entra ID, and is it the same as Active Directory?</summary>

**Answer:**

Microsoft Entra ID is the new name for Azure Active Directory. It is Microsoft's cloud identity service: it stores users, groups, and app identities, handles sign-in and MFA, and issues OAuth/OIDC tokens. It is not the same as on-premises Active Directory Domain Services, which uses Kerberos, LDAP, and domain-joined machines. Many companies sync on-prem AD users into Entra ID with **Entra Connect**.

</details>

<details><summary>Q2. [Basic] What is the difference between an app registration and a service principal?</summary>

**Answer:**

- The **app registration** (application object) is the global definition of the app: client ID, credentials, API permissions. It lives in the home tenant.
- The **service principal** is the local identity of that app in a tenant. It is what signs in and what gets RBAC roles.

Simple rule: app registration = blueprint, service principal = the real ID card. A multi-tenant app has one app registration but one service principal in each tenant that uses it. In the portal, service principals are listed under **Enterprise applications**.

</details>

<details><summary>Q3. [Basic] What is a managed identity, and what are the two types?</summary>

**Answer:**

A managed identity is an identity for an Azure resource where Azure creates and rotates the credentials for you. Your code gets tokens without storing any secret.

- **System-assigned:** created with one resource and deleted with it.
- **User-assigned:** a standalone resource that you can attach to many resources, and that survives when they are deleted.

</details>

<details><summary>Q4. [Basic] When would you choose a service principal instead of a managed identity?</summary>

**Answer:**

Use a **managed identity** whenever the code runs inside Azure and the service supports it. Use a **service principal** (app registration) when:

- The workload runs **outside Azure**, for example on-prem servers or another cloud, and cannot use federation.
- You need **Microsoft Graph API permissions** with admin consent for a multi-tenant app or a user-facing app with sign-in.
- The tool only supports client ID plus secret or certificate.

For CI/CD outside Azure (GitHub Actions, Azure DevOps hosted agents), use either an app registration or a user-assigned managed identity **with a federated credential**, so there is still no secret.

</details>

<details><summary>Q5. [Basic] What is a federated credential?</summary>

**Answer:**

A federated credential is a trust rule on an app registration or user-assigned managed identity. It says: "If a token comes from this **issuer**, for this **subject**, with this **audience**, accept it and give back an Entra ID token." The external platform (GitHub, Azure DevOps, Kubernetes) creates a short-lived OIDC token, Entra ID checks it, and returns an Azure token. No secret is stored anywhere.

</details>

<details><summary>Q6. [Basic] What is an Azure DevOps service connection?</summary>

**Answer:**

It is a named, saved connection in an Azure DevOps project that pipelines use to talk to an external system. For Azure it is the **Azure Resource Manager** type, backed by a service principal or managed identity. Pipelines refer to it by name, for example `azureSubscription: sc-azure-prod`, so the credentials never appear in the YAML.

</details>

<details><summary>Q7. [Basic] What is the difference between Entra ID roles, API permissions, and Azure RBAC roles?</summary>

**Answer:**

- **Azure RBAC roles** (Owner, Contributor, Reader, Key Vault Secrets User): what you can do on **Azure resources** such as VMs and storage accounts.
- **Entra ID roles** (Global Administrator, Application Administrator): what you can do **inside Entra ID**, such as creating users or app registrations.
- **API permissions** (for example, Microsoft Graph `User.Read.All`): what an **app** can call in an API. Application permissions usually need **admin consent**.

A pipeline that deploys resources needs Azure RBAC. A pipeline that creates app registrations also needs Entra ID permissions.

</details>

<details><summary>Q8. [Intermediate] How do you set up GitHub Actions to deploy to Azure without storing a secret?</summary>

**Answer:**

1. Create an app registration (or a user-assigned managed identity).
2. Add a federated credential with issuer `https://token.actions.githubusercontent.com` and a subject such as `repo:my-org/my-repo:environment:prod`.
3. Give the identity an RBAC role on only the resource group it needs.
4. Store the client ID, tenant ID, and subscription ID as GitHub variables (they are not secrets).
5. In the workflow, add `permissions: id-token: write` and use `azure/login` with those three IDs.

**How to verify:** run `az account show` in the job. If login fails with `AADSTS70021: No matching federated identity record found`, the subject in the token does not match the federated credential (for example, wrong branch, or the job uses an environment but the credential expects a branch).

</details>

<details><summary>Q9. [Intermediate] How do you create a service connection using workload identity federation in Azure DevOps?</summary>

**Answer:**

1. Go to **Project settings > Service connections > New > Azure Resource Manager**.
2. Choose **Workload identity federation**.
3. **Automatic:** Azure DevOps creates the app registration, the federated credential, and the role assignment for you. You need permission to create apps in Entra ID and to assign roles.
4. **Manual:** you create the app registration or user-assigned managed identity yourself, copy the **issuer** and **subject** shown by Azure DevOps into a federated credential, and assign the RBAC role yourself. Use this when your account cannot create app registrations.
5. Lock it down: do not grant access to all pipelines, and add approvals and checks for production.

</details>

<details><summary>Q10. [Intermediate] A pipeline that worked for a year suddenly fails to log in to Azure. What do you check? <em>(scenario)</em></summary>

**Answer:**

1. **Expired client secret.** This is the most common cause with secret-based service principals (`AADSTS7000222: The provided client secret keys are expired`). Check **App registration > Certificates & secrets**.
2. **Role assignment removed** or scope changed. Check with `az role assignment list --assignee <app-id> --all -o table`.
3. **App or service principal deleted or disabled** in Entra ID.
4. **Federated credential subject mismatch**, for example after renaming the repo, branch, environment, or service connection.
5. **Conditional Access** policy now blocking workload identities.

Long-term fix: move to workload identity federation so there is no secret to expire.

</details>

<details><summary>Q11. [Intermediate] How does an App Service read secrets from Key Vault using a managed identity?</summary>

**Answer:**

1. Enable a managed identity on the App Service: `az webapp identity assign -g rg-app -n my-webapp`.
2. Give that identity the **Key Vault Secrets User** role on the vault (RBAC permission model).
3. Either use a Key Vault reference in app settings, `@Microsoft.KeyVault(SecretUri=https://kv-app.vault.azure.net/secrets/DbPassword/)`, or read it in code with `DefaultAzureCredential` and `SecretClient`.

No connection string or secret is stored in the app config.

</details>

<details><summary>Q12. [Intermediate] System-assigned or user-assigned managed identity: which do you prefer and why?</summary>

**Answer:**

- **System-assigned** is simplest for a single resource, and it cleans up automatically when the resource is deleted.
- **User-assigned** is better when many resources share the same access, when you want to create the identity and its RBAC **before** the resource (so the app works on first start), when resources are recreated often (scale sets, blue-green), and for **AKS workload identity** and **federated credentials**, which only user-assigned identities support.

In IaC-heavy setups, user-assigned identities are common because role assignments do not have to be recreated each time a resource is replaced.

</details>

<details><summary>Q13. [Intermediate] How does a Pod in AKS get access to Azure resources?</summary>

**Answer:**

Use **Microsoft Entra Workload ID**:

1. Enable the OIDC issuer and workload identity on the cluster.
2. Create a user-assigned managed identity and give it RBAC on the target resource.
3. Add a federated credential: issuer = cluster OIDC issuer URL, subject = `system:serviceaccount:<namespace>:<sa-name>`.
4. Annotate the ServiceAccount with `azure.workload.identity/client-id` and label the Pod `azure.workload.identity/use: "true"`.

The webhook injects a projected token into the Pod, and the Azure SDK swaps it for an Azure token. AAD Pod Identity is deprecated; do not use it for new work.

</details>

<details><summary>Q14. [Intermediate] An AKS Pod using workload identity gets "403 Forbidden" from Key Vault. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

A 403 means **login worked but permission is missing**:

1. Check the role assignment on the vault for the managed identity's principal ID.
2. Check the vault uses the **RBAC** permission model; if it uses access policies, add an access policy instead.
3. Check Key Vault networking: firewall or private endpoint may block the AKS subnet.
4. Wait a few minutes after a new role assignment; it can take time to apply.

If the error is a **401 or token error** instead, check the federated credential subject (namespace and service account name), the ServiceAccount annotation, the Pod label, and that the Pod was restarted after the changes.

</details>

<details><summary>Q15. [Advanced] How would you design CI/CD identities for dev, test, and prod with least privilege?</summary>

**Answer:**

- **One identity per environment** (user-assigned managed identity or app registration), never one identity for everything.
- **Federated credentials only**, no secrets. Bind each to a specific subject, for example GitHub `environment:prod` or a specific Azure DevOps service connection.
- **RBAC at the smallest scope**: resource group, not subscription. Use **Contributor** for deploy, and avoid **Owner** or **User Access Administrator** unless the pipeline must assign roles. If it must, use **Role Based Access Control Administrator** with a condition that limits which roles it can assign.
- **Protect prod**: GitHub environment protection rules, or Azure DevOps approvals and checks on the prod service connection.
- **Separate identities for runtime and deploy**: the app's managed identity reads Key Vault; the pipeline identity deploys infrastructure.
- **Audit**: review Entra sign-in logs for service principals and remove unused identities and role assignments.

</details>

<details><summary>Q16. [Advanced] Why is workload identity federation safer than a client secret? Are there any risks left?</summary>

**Answer:**

Safer because:

- No long-lived secret is stored in a pipeline, so nothing can leak from logs, variables, or a laptop.
- Tokens are short-lived (minutes to about an hour).
- The trust is tied to a specific issuer and subject, so only that repo, branch, environment, or service account can log in.

Risks that remain:

- **Too broad a subject**, for example trusting any branch or pull requests, lets untrusted code log in. Prefer environment-based subjects for prod.
- **Too much RBAC**: a federated identity with Owner on a subscription is still dangerous.
- **Whoever can change the workflow or pipeline** on a trusted branch can use the identity, so branch protection and code review still matter.

</details>

<details><summary>Q17. [Advanced] A security audit finds 40 service principals with client secrets. How would you clean this up? <em>(scenario)</em></summary>

**Answer:**

1. **Inventory:** list apps with secrets and their expiry dates, for example `az ad app list --all --query "[?passwordCredentials[0]].{name:displayName, appId:appId}"`, and check sign-in logs to see which are still used.
2. **Delete unused** apps and their role assignments.
3. **Migrate by type:**
   - Code running in Azure: switch to **managed identities**.
   - GitHub Actions, Azure DevOps, AKS, other OIDC platforms: switch to **federated credentials**. In Azure DevOps, convert existing service connections to workload identity federation.
   - Truly external systems with no OIDC: use **certificates** stored in Key Vault, with short expiry and auto-rotation.
4. **Prevent it coming back:** restrict who can create app registrations, use an Entra **app management policy** to block or limit secret lifetimes, and alert on expiring credentials.

</details>
