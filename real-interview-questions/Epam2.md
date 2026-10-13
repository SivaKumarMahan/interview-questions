# EPAM - Interview Questions (Part 2)

<details><summary>Q1. How have you used Azure Functions, Web Apps, and App Service in your CI/CD pipeline?</summary>

Azure App Service is the managed hosting platform. Azure Web Apps is an App Service workload used to host web applications and APIs. Azure Functions is a serverless service used to run event-driven or scheduled code.

### Azure Web App / App Service deployment flow

For a React frontend or Java Spring Boot API, the flow is:

```text
Developer push
      |
      v
Azure Repos or GitHub
      |
      v
CI: Build -> Unit tests -> SonarQube -> Package
      |
      v
CD: Dev -> QA -> UAT -> Production approval
      |
      v
Azure App Service
```

Implementation steps:

1. A code push triggers the Azure DevOps CI pipeline.
2. The pipeline installs dependencies, compiles the application, runs tests and code-quality checks, and publishes a versioned artifact.
3. The CD stages promote the same tested artifact through Dev, QA, UAT, and Production.
4. The deployment uses an Azure Resource Manager service connection with only the required permissions.
5. Environment-specific configuration is stored in App Service settings. Secrets are referenced from Azure Key Vault instead of being committed to the repository.
6. Production uses approvals, health checks, deployment slots where appropriate, and post-deployment validation.
7. Application Insights, Azure Monitor, and the application's health endpoint are used to verify the release.

For Spring Boot, App Service can run the JAR on a supported Java runtime or run a custom container. For a purely static React application, Azure Static Web Apps or Storage static website hosting may also be considered.

### Azure Functions deployment flow

For a Blob-triggered, HTTP-triggered, or timer-triggered function:

1. The function code is committed to Git.
2. The CI pipeline restores dependencies, builds the code, runs tests, and creates a deployment package.
3. The CD pipeline deploys that package to the target Function App.
4. Application settings and trigger connection configuration are supplied per environment, with secrets stored in Key Vault.
5. The trigger is tested and its execution is checked in Application Insights or Azure Monitor.

For example, a Blob-triggered function can process a file whenever it is uploaded to Storage. The pipeline deploys changes to the function code; the configured event trigger starts each execution.

### Simplified Azure DevOps YAML for Spring Boot

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - task: Maven@4
    inputs:
      mavenPomFile: pom.xml
      goals: clean package
      publishJUnitResults: true
      testResultsFiles: '**/surefire-reports/TEST-*.xml'

  - task: AzureWebApp@1
    inputs:
      azureSubscription: my-azure-service-connection
      appType: webAppLinux
      appName: my-springboot-app
      package: '$(System.DefaultWorkingDirectory)/**/target/*.jar'
```

In production, I separate build and deployment so that the same immutable artifact is promoted across environments. I also select the intended JAR explicitly and configure the required Java runtime.

### Azure Functions deployment task

```yaml
- task: AzureFunctionApp@2
  inputs:
    connectedServiceNameARM: my-azure-service-connection
    appType: functionAppLinux
    appName: my-blob-processor-func
    package: '$(Pipeline.Workspace)/drop/function.zip'
```

### Managing multiple environments

```text
Build and test (once)
      |
      v
Deploy to Dev
      |
      v
Deploy to QA
      |
      v
Manual approval
      |
      v
Deploy to Production
```

Each stage is a deployment job targeting an Azure DevOps environment (`dev`, `qa`, `prod`), with its own service connection, App Service or Function App settings, and Key Vault. The Production environment has an approval check.

### Interview answer

> "I use Azure DevOps pipelines to automate the build, testing, and deployment of applications hosted on Azure. For App Service, I build the application, run unit tests and code-quality checks, publish a versioned artifact, and deploy it to the Web App through an Azure service connection. I promote the same artifact through Dev, QA, UAT, and Production, with approval before Production. For Azure Functions, I build, test, package, and deploy the function code to a Function App; the function then executes through its configured HTTP, timer, Blob, or other trigger. I keep environment configuration outside the artifact, store secrets in Key Vault, and validate releases using health checks, Application Insights, and Azure Monitor."

</details>

---

<details><summary>Q2. Have you created a private Kubernetes cluster? How?</summary>

In a private AKS cluster, the Kubernetes API server is reachable only through a private IP address inside the virtual network instead of a public endpoint.

### 1. Plan the network

- Create an Azure VNet with separate subnets for AKS nodes, private endpoints, and the jumpbox or build agents.
- Configure NSGs and route tables to control traffic, for example sending egress through Azure Firewall.
- Make sure the address ranges do not overlap with peered or on-premises networks.

### 2. Create the private AKS cluster

- Enable the private cluster option when creating the cluster.
- Use a managed identity with the required permissions on the subnet and private DNS zone.
- Select the node subnet and network plugin.

```bash
az aks create \
  --resource-group my-rg \
  --name my-private-aks \
  --enable-private-cluster \
  --network-plugin azure \
  --vnet-subnet-id <aks-subnet-resource-id> \
  --enable-managed-identity \
  --enable-aad \
  --enable-azure-rbac \
  --generate-ssh-keys
```

By default, AKS creates a private DNS zone for the API server. When the organization uses custom or hub DNS, an existing zone can be supplied with `--private-dns-zone`.

### 3. Configure DNS and access

- Access the cluster from a jumpbox VM inside the VNet, or through VPN, ExpressRoute, or a peered network.
- Link the private DNS zone to every VNet that needs access so the API server hostname resolves to its private IP.
- Grant access through Microsoft Entra ID with Kubernetes RBAC or Azure RBAC.

### 4. Configure CI/CD deployment

- Use a self-hosted Azure DevOps agent (VM or VM Scale Set agent pool) inside the VNet or in a connected network.
- The agent must resolve and reach the private API server and have the required Azure and Kubernetes permissions.
- Deploy applications using Helm charts or Kubernetes YAML manifests.

### 5. Validate the cluster

```bash
az aks show \
  --resource-group my-rg \
  --name my-private-aks \
  --query apiServerAccessProfile
```

Then, from a machine with authorized network access:

```bash
az aks get-credentials \
  --resource-group my-rg \
  --name my-private-aks

kubectl get nodes
kubectl get pods -A
```

If the network, DNS, and permissions are configured correctly, these commands list the cluster's nodes and pods.

### Interview answer

> "Yes, I have worked with private AKS clusters in Azure. In a private cluster, the API server is reachable only through a private IP inside the VNet. I plan the VNet and subnets without overlapping address ranges, create the cluster with the private cluster option and a managed identity, and make sure the private DNS zone is linked so the API server name resolves to the private IP. Access is through a jumpbox, VPN, or ExpressRoute, controlled with Entra ID and RBAC. For CI/CD, I use a self-hosted Azure DevOps agent that has network access to the private API server, and I deploy with Helm or Kubernetes manifests. I validate it with `az aks get-credentials` and `kubectl get nodes` from an authorized machine."

### Follow-up questions

#### Can you access a private AKS cluster from your laptop?

Yes, if the laptop has connectivity to the VNet through VPN or another approved private network connection, with correct DNS resolution and authorization.

#### How does Azure DevOps deploy to private AKS?

Through a self-hosted agent running inside the VNet or in a connected network. The agent must resolve and reach the private API server and have the necessary Azure and Kubernetes permissions.

#### What happens if private DNS is not configured correctly?

The API server hostname will not resolve to the private IP, so `kubectl` commands and pipeline deployments fail even though the cluster itself is healthy.

#### What is the main advantage?

The Kubernetes control plane is not exposed to the public internet. Only authorized clients with private network connectivity and the required permissions can reach it.

</details>

---

<details><summary>Q3. Do we have autoscaling in Azure App Service? How do you use it?</summary>

Yes. Azure App Service can scale out by adding instances and scale in by removing them. The exact scaling features available depend on the App Service Plan tier.

### Metric-based autoscale

1. Open the **App Service Plan** in the Azure portal.
2. Select **Scale out (App Service Plan)**.
3. Choose **Custom autoscale**.
4. Add rules based on metrics such as CPU percentage, memory percentage, or HTTP queue length.
5. Set the minimum, default, and maximum number of instances.
6. Save the configuration and monitor the autoscale run history.

Example:

```text
Normal load        -> 2 instances
CPU > 70% (10 min) -> scale out by 1, up to a maximum of 4
CPU < 35% (15 min) -> scale in by 1, down to a minimum of 2
```

Use separate scale-out and scale-in thresholds to reduce oscillation. Also remember that every application in the same App Service Plan shares its compute instances.

Autoscaling changes the **number of instances** (horizontal scaling). Scaling up or down changes the **size or pricing tier** of the App Service Plan (vertical scaling).

### Interview answer

> "Yes, Azure App Service supports horizontal scaling. I configure autoscale on the App Service Plan with minimum, default, and maximum instance counts. For example, I can add an instance when average CPU remains above 70% for 10 minutes and remove one when CPU stays below 35% for 15 minutes. I configure cooldown periods, monitor autoscale history, and load-test the thresholds before Production. Scaling out adds instances, while scaling up changes the App Service Plan size or pricing tier."

</details>

---

<details><summary>Q4. What is the difference between Microsoft Entra ID and an app registration?</summary>

**Microsoft Entra ID** is Microsoft's identity and access management service. It manages users, groups, and application identities, and controls access to organizational resources.

An **app registration** is where an application is registered in Entra ID so it can authenticate users or access other services securely.

| Microsoft Entra ID | App registration |
| --- | --- |
| Identity and access management service | Registration of one application within Entra ID |
| Manages users, groups, and identities | Defines the application's identity and authentication settings |
| Controls access to organizational resources | Lets the application authenticate and request access |
| Example: an employee signs in to Azure | Example: a pipeline application authenticates to Azure |

### App registration versus service principal

Example: an Azure DevOps pipeline needs to deploy to Azure.

- **Microsoft Entra ID:** manages identities and authentication.
- **App registration:** defines the application's identity and authentication settings (client ID, credentials, redirect URIs, API permissions).
- **Service principal:** the instance of that application in a specific tenant; it is what receives access to Azure resources.
- **Azure RBAC:** assigns roles such as Reader or Contributor to the service principal at the required scope.

For better security, the Azure DevOps service connection can use **workload identity federation** instead of storing a client secret.

### Interview answer

> "Microsoft Entra ID is Microsoft's identity management service. It manages users, groups, and application identities. An app registration registers an application in Entra ID and configures how it authenticates. The service principal is that application's identity in the tenant, and that is what I grant Azure RBAC roles to. For example, when connecting Azure DevOps to Azure, I use a service principal with only the required permissions, and I prefer workload identity federation over storing a client secret."

</details>

---

<details><summary>Q5. How can you restrict users before their requests reach the application?</summary>

There are two kinds of restriction, and they are usually combined:

- **Identity-based:** only signed-in, authorized users (for example, one employee group) can reach the application. Done with **Microsoft Entra ID**.
- **Network-based:** only allowed networks, IPs, or countries can reach the application, and malicious traffic is blocked. Done with **access restrictions, Private Endpoints, Application Gateway / Front Door, and WAF**.

### Request flow

```text
User browser
     |
     v
Azure Front Door or Application Gateway + WAF
     |  Blocks malicious requests (SQL injection, XSS, bots),
     |  geo/IP rules, rate limits
     v
App Service access restrictions
     |  Only traffic from the gateway (service tag / private endpoint) allowed
     v
App Service Authentication (Easy Auth) with Microsoft Entra ID
     |  Not signed in -> redirect to Entra sign-in
     |  Not in allowed group -> 401/403, request never reaches the code
     v
Application
     |  Checks roles for protected pages and operations
```

### For identity-based access to an App Service application

**Step 1: Enable App Service Authentication**

In the App Service, open **Authentication → Add identity provider → Microsoft**, and set **Restrict access** to **Require authentication** with unauthenticated requests redirected to sign-in (HTTP 302) or rejected (HTTP 401). Easy Auth runs in front of the application code, so unauthenticated users never reach it.

**Step 2: Allow only specific users or groups**

In **Entra ID → Enterprise applications → (the app) → Properties**, set **Assignment required = Yes**, then under **Users and groups** assign only the allowed group, for example `GRP-App-Employees`. Users who are not assigned are denied at sign-in.

**Step 3: Use roles inside the application**

Define app roles (for example `Reader`, `Admin`) in the app registration, assign them to groups, and have the application check the role claim before allowing protected pages or operations.

### For network-based restrictions

**Step 4: Put a gateway in front**

Route all traffic through **Application Gateway** (regional) or **Azure Front Door** (global), with WAF enabled.

**Step 5: Lock the App Service to the gateway**

- Add **App Service access restrictions** that allow only the Application Gateway subnet or the `AzureFrontDoor.Backend` service tag (with the Front Door ID header check), and deny everything else.
- Or disable public access and use a **Private Endpoint** so the App Service is reachable only from the VNet / gateway.
- For internal-only applications, allow only corporate IP ranges or VPN.

**Step 6: Add Conditional Access (optional)**

Use Entra **Conditional Access** to require MFA, compliant devices, or block sign-ins from certain locations.

### Role of WAF

WAF protects against malicious **traffic**: OWASP Top 10 attacks such as SQL injection and cross-site scripting, bad bots, and excessive requests (rate limiting). It can also block by IP or country with custom rules.

WAF does **not** know who the user is. It cannot allow "only employees" or check application roles; that is the job of Entra ID authentication and authorization.

### Important points

- To block users **before** requests reach the code, use Easy Auth or a gateway layer; in-app checks alone are too late.
- Restrict the App Service so users cannot bypass the gateway by calling the `*.azurewebsites.net` URL directly.
- The application must still validate roles for sensitive operations (defense in depth).

### Interview answer

> "I restrict users at two levels. For identity, I enable App Service Authentication with Microsoft Entra ID, so unauthenticated users are redirected to sign in before the request reaches the code. In the enterprise application, I turn on 'Assignment required' and assign only the allowed group, so other users are denied at sign-in, and the application checks app roles for protected operations. For the network, I put Application Gateway or Front Door with WAF in front to block malicious traffic and apply IP or geo rules, and I use access restrictions or a private endpoint so the App Service accepts traffic only from the gateway. WAF protects against attacks, but it doesn't know user identity, so it works together with Entra ID rather than replacing it."

</details>

---

<details><summary>Q6. How do you configure a private endpoint between an AKS backend application and a database?</summary>

If the backend runs in AKS and the database is an Azure PaaS database, I use a **Private Endpoint** so the application reaches the database over a private IP inside the VNet, without exposing the database to the internet. The same pattern applies to any backend (VM, App Service with VNet integration, Function App) and any supported PaaS service (Azure SQL, PostgreSQL, Cosmos DB, Storage, Key Vault, ACR).

Example: a Spring Boot application in AKS connecting to Azure Database for PostgreSQL.

### Request flow

```text
Spring Boot Pod (AKS)
        |
        | 1. Connects to mydb.postgres.database.azure.com
        v
Azure DNS / Private DNS zone (privatelink.postgres.database.azure.com)
        |
        | 2. Hostname resolves to private IP, e.g. 10.10.3.4
        v
Private Endpoint NIC (private-endpoint subnet)
        |
        | 3. TCP 5432 over the VNet / peering
        v
Azure Database for PostgreSQL (public access disabled)
```

The application keeps using the normal database hostname. Private DNS changes what that hostname resolves to, so traffic stays on the private network.

### Configuration steps

**Step 1: Create the private endpoint**

Create a private endpoint for the database in a dedicated subnet in the AKS VNet, or in a hub VNet that is peered with it.

```bash
az network private-endpoint create \
  --resource-group my-rg \
  --name pe-postgres \
  --vnet-name aks-vnet \
  --subnet private-endpoints \
  --private-connection-resource-id <postgres-server-resource-id> \
  --group-id postgresqlServer \
  --connection-name pe-postgres-conn
```

**Step 2: Configure private DNS**

Create the private DNS zone for that service, link it to the AKS VNet, and attach it to the private endpoint so the A record is created automatically.

```bash
az network private-dns zone create \
  --resource-group my-rg \
  --name privatelink.postgres.database.azure.com

az network private-dns link vnet create \
  --resource-group my-rg \
  --zone-name privatelink.postgres.database.azure.com \
  --name aks-vnet-link \
  --virtual-network aks-vnet \
  --registration-enabled false

az network private-endpoint dns-zone-group create \
  --resource-group my-rg \
  --endpoint-name pe-postgres \
  --name default \
  --private-dns-zone privatelink.postgres.database.azure.com \
  --zone-name postgres
```

Common zones:

| Service | Private DNS zone | Port |
| --- | --- | --- |
| Azure SQL Database | `privatelink.database.windows.net` | 1433 |
| PostgreSQL | `privatelink.postgres.database.azure.com` | 5432 |
| MySQL | `privatelink.mysql.database.azure.com` | 3306 |
| Key Vault | `privatelink.vaultcore.azure.net` | 443 |
| ACR | `privatelink.azurecr.io` | 443 |

If the company uses custom or hub DNS servers, they must forward to Azure DNS (168.63.129.16) or a DNS Private Resolver so the private zone is used.

**Step 3: Allow the network path**

- NSGs on the AKS subnet and private-endpoint subnet allow the database port.
- Route tables or Azure Firewall do not block or misroute the traffic.
- Kubernetes network policies allow egress from the backend pods to the database.

**Step 4: Configure the backend securely**

Store the database host, port, and username in the deployment configuration, and keep the password in Azure Key Vault (or use Entra ID authentication with Workload Identity where the database supports it).

**Step 5: Test from inside the cluster**

```bash
kubectl run net-test -it --rm --image=busybox -- sh
nslookup mydb.postgres.database.azure.com   # should return 10.x private IP
nc -zv mydb.postgres.database.azure.com 5432
```

Then check the application logs to confirm it connects successfully.

**Step 6: Disable public access**

After private connectivity is validated, disable public network access on the database.

### Important points

- A private endpoint alone does not guarantee connectivity. DNS, routing, NSGs, network policies, database firewall settings, and authentication must all be correct.
- The most common failure is DNS: if the hostname still resolves to a public IP, the connection fails once public access is disabled.
- Do not connect using the private IP directly; TLS certificates and connection strings expect the hostname.

### Interview answer

> "If my backend runs in AKS and the database is in Azure, I connect them through a private endpoint. I create the private endpoint for the database in a dedicated subnet in the AKS VNet or a peered hub VNet. I create the matching private DNS zone, such as `privatelink.postgres.database.azure.com`, link it to the AKS VNet, and attach it to the endpoint so the database hostname resolves to the private IP. I make sure NSGs, routing, and network policies allow the database port, and I keep the password in Key Vault. I test DNS and connectivity from a pod with `nslookup` and `nc`, then disable public access on the database. The application keeps using the normal hostname, but the traffic now stays on the private network."

</details>

---

<details><summary>Q7. How do you promote the same ACR image from Stage to Production?</summary>

Scenario: Stage and Production are in different resource groups, and there is only one Azure Container Registry. I build the image once and deploy the **same image** to both environments without rebuilding it.

### Promotion flow

```text
Azure DevOps CI
  Build -> Unit tests -> Docker build
        |
        v
ACR: myacr.azurecr.io/myapp:v1.2.0  (digest sha256:abc...)
        |
        v
Deploy to Stage AKS (rg-stage)
  Smoke tests / integration tests
        |
        v
Manual approval
        |
        v
Deploy SAME image to Production AKS (rg-prod)
  Health checks / monitoring
```

### Implementation

**Step 1: Build and push once**

The CI pipeline builds the image and pushes it to ACR with a unique, immutable tag such as the build number or Git commit SHA, never only `latest`.

```yaml
- task: Docker@2
  inputs:
    containerRegistry: acr-service-connection
    repository: myapp
    command: buildAndPush
    tags: |
      $(Build.BuildNumber)
```

**Step 2: Deploy to Stage**

The Stage deployment uses that exact image reference:

```yaml
image: myacr.azurecr.io/myapp:v1.2.0
```

**Step 3: Validate Stage**

Run smoke tests and verify pod status, health endpoints, and logs.

**Step 4: Promote to Production after approval**

The Production stage (protected by an Azure DevOps environment approval) deploys the same image. Using the digest gives the strongest guarantee that Production runs exactly what was tested:

```yaml
image: myacr.azurecr.io/myapp@sha256:<digest-tested-in-stage>
```

**Step 5: Verify Production**

Check rollout status, pod health, application health, and Application Insights.

```bash
kubectl rollout status deployment/myapp -n prod
```

### Permissions and networking

- Different resource groups do not matter; ACR can serve clusters in any resource group or subscription in the same tenant.
- Grant **AcrPull** on the ACR to each cluster's kubelet managed identity:

```bash
az aks update --resource-group rg-stage --name aks-stage --attach-acr myacr
az aks update --resource-group rg-prod  --name aks-prod  --attach-acr myacr
```

- If ACR uses a private endpoint, both cluster VNets must reach it and resolve `privatelink.azurecr.io`.
- Optionally, enable tag locking (`az acr repository update --write-enabled false`) on released tags so they cannot be overwritten.

### Important points

- Never rebuild the image for Production; a rebuild can pull different base layers or dependencies.
- Configuration differences between Stage and Production belong in ConfigMaps, Key Vault, or Helm values, not in the image.

### Interview answer

> "If Stage and Production are in different resource groups but share one ACR, I build the Docker image once in CI and push it with a unique tag such as the build number. I deploy that image to Stage and run testing. After validation and approval, the Production stage deploys the same image, preferably by digest, so Production runs exactly what was tested. I grant AcrPull to both clusters' kubelet identities, usually with `az aks update --attach-acr`, and if ACR is private I make sure both VNets can reach its private endpoint. This promotes the tested artifact without rebuilding it and avoids differences between Stage and Production."

</details>

---

<details><summary>Q8. How does AKS connect to Azure Key Vault?</summary>

AKS connects to Key Vault using **Microsoft Entra Workload ID** for authentication and the **Azure Key Vault provider for the Secrets Store CSI Driver** to retrieve secrets. No client secret is stored in the cluster.

Example: a Spring Boot application in AKS needs the database password stored in Key Vault.

### Authentication and retrieval flow

```text
AKS Pod (serviceAccountName: myapp-sa)
        |
        | 1. Pod gets a Kubernetes service account token
        v
AKS OIDC issuer
        |
        | 2. Token exchanged via federated identity credential
        v
Microsoft Entra ID -> User-assigned managed identity
        |
        | 3. Access token for Key Vault (role: Key Vault Secrets User)
        v
Azure Key Vault
        |
        | 4. Secret returned to CSI driver
        v
Mounted as a file in the pod -> application reads it
```

### Configuration steps

**Step 1: Store secrets in Key Vault**

```text
Azure Key Vault (kv-myapp-prod)
    ├── db-username
    ├── db-password
    └── api-key
```

**Step 2: Enable Workload Identity and the CSI driver add-on on AKS**

```bash
az aks update \
  --resource-group my-rg \
  --name my-aks \
  --enable-oidc-issuer \
  --enable-workload-identity

az aks enable-addons \
  --resource-group my-rg \
  --name my-aks \
  --addons azure-keyvault-secrets-provider
```

**Step 3: Create the identity and trust the Kubernetes service account**

```bash
az identity create --resource-group my-rg --name id-myapp

OIDC_ISSUER=$(az aks show -g my-rg -n my-aks --query oidcIssuerProfile.issuerUrl -o tsv)

az identity federated-credential create \
  --name myapp-fic \
  --identity-name id-myapp \
  --resource-group my-rg \
  --issuer "$OIDC_ISSUER" \
  --subject system:serviceaccount:myapp-ns:myapp-sa \
  --audience api://AzureADTokenExchange
```

**Step 4: Grant least-privilege access on Key Vault**

```bash
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee <identity-client-id> \
  --scope <key-vault-resource-id>
```

**Step 5: Create the service account and SecretProviderClass, and mount it in the pod**

The service account is annotated with the identity's client ID, and the SecretProviderClass lists which secrets to fetch (full YAML in Q9).

### Important points

- Use Workload Identity instead of service principal secrets in Kubernetes YAML. (AAD Pod Identity is deprecated.)
- Assign only **Key Vault Secrets User**, scoped to the specific vault.
- If Key Vault public access is disabled, configure a private endpoint and `privatelink.vaultcore.azure.net` DNS for the AKS VNet.
- With rotation enabled, the mounted file is refreshed, but the application may still need to reload or restart its connection to use the new value.

### Interview answer

> "I connect AKS to Azure Key Vault using Microsoft Entra Workload ID and the Key Vault Secrets Store CSI Driver. I enable the OIDC issuer, Workload Identity, and the Key Vault secrets provider add-on on AKS. I create a user-assigned managed identity and a federated credential that trusts the application's Kubernetes service account. Then I give that identity only the Key Vault Secrets User role on the vault. A SecretProviderClass defines which secrets to retrieve, and when the pod starts, the CSI driver uses that identity to fetch the secrets and mount them as files. This way, no passwords or client secrets are stored in Kubernetes manifests."

</details>

---

<details><summary>Q9. You have secrets in Key Vault. How do they reach the Pods?</summary>

The **Secrets Store CSI Driver** fetches the secrets from Key Vault when the pod starts and mounts them as files inside the container. Optionally, they can also be synced into a Kubernetes Secret for use as environment variables.

### Secret delivery flow

```text
Azure Key Vault (db-password)
        |
        | 1. CSI driver authenticates with the pod's Workload Identity
        v
Secrets Store CSI Driver (on the node)
        |
        | 2. Reads SecretProviderClass, fetches listed secrets
        v
CSI volume mounted at /mnt/secrets-store
        |
        | 3. File: /mnt/secrets-store/db-password
        v
Application container reads the file
        |
        v
Connects to the database
```

If the secret cannot be fetched (wrong permission, DNS, or name), the pod stays in `ContainerCreating` and `kubectl describe pod` shows a mount error.

### Example configuration

**SecretProviderClass**

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: kv-myapp
  namespace: myapp-ns
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: "<identity-client-id>"
    keyvaultName: "kv-myapp-prod"
    tenantId: "<tenant-id>"
    objects: |
      array:
        - |
          objectName: db-password
          objectType: secret
  # Optional: also create a Kubernetes Secret for environment variables
  secretObjects:
    - secretName: myapp-db
      type: Opaque
      data:
        - objectName: db-password
          key: DB_PASSWORD
```

**Service account**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: myapp-ns
  annotations:
    azure.workload.identity/client-id: "<identity-client-id>"
```

**Deployment (pod template)**

```yaml
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: myapp-sa
      containers:
        - name: myapp
          image: myacr.azurecr.io/myapp:v1.2.0
          volumeMounts:
            - name: secrets-store
              mountPath: /mnt/secrets-store
              readOnly: true
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: myapp-db
                  key: DB_PASSWORD
      volumes:
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: kv-myapp
```

The synced Kubernetes Secret (`myapp-db`) exists only while at least one pod mounts the CSI volume.

### Important points

- A secret is not automatically available to every pod. The pod must mount the CSI volume and run with a service account whose identity has Key Vault access.
- Prefer reading the mounted file; syncing to a Kubernetes Secret stores the value in etcd as well.
- Rotation (`--enable-secret-rotation`) refreshes the mounted file, but environment variables only change after a pod restart.

### Interview answer

> "I use the Azure Key Vault Secrets Store CSI Driver. I configure Workload Identity and grant the identity read access to the secrets. I create a SecretProviderClass with the Key Vault name, tenant, identity client ID, and the list of secrets, and I reference it as a CSI volume in the pod spec with the annotated service account. When the pod starts, the CSI driver authenticates with Azure, fetches the secrets, and mounts them as files, for example `/mnt/secrets-store/db-password`, and the application reads that file. If the application needs environment variables, I also sync them into a Kubernetes Secret. This way, no credentials are hardcoded in Kubernetes YAML."

</details>

---

<details><summary>Q10. How do you organize Terraform modules so you can plan and apply multiple environments?</summary>

I separate **reusable modules** from **environment-specific configuration**. Each environment calls the same modules with its own values and has its own remote state, so a Dev change can never touch Prod state.

### Folder structure

```text
terraform/
├── modules/
│   ├── vnet/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── aks/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── keyvault/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── environments/
    ├── dev/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── versions.tf
    │   ├── backend.tf
    │   └── terraform.tfvars
    ├── qa/
    │   └── ... (same files)
    └── prod/
        └── ... (same files)
```

### How it works

**Step 1: Create reusable modules**

A module is written once and accepts inputs. For example, the VNet module takes the VNet name, address space, and subnets, and outputs the subnet IDs.

```hcl
# modules/vnet/variables.tf
variable "vnet_name"           { type = string }
variable "resource_group_name" { type = string }
variable "location"            { type = string }
variable "address_space"       { type = list(string) }
```

**Step 2: Call the module from each environment**

```hcl
# environments/dev/main.tf
module "vnet" {
  source              = "../../modules/vnet"
  vnet_name           = var.vnet_name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.address_space
}

module "aks" {
  source     = "../../modules/aks"
  subnet_id  = module.vnet.aks_subnet_id
  node_count = var.aks_node_count
}
```

```hcl
# environments/dev/terraform.tfvars
vnet_name           = "dev-vnet"
resource_group_name = "rg-dev"
location            = "eastus"
address_space       = ["10.1.0.0/16"]
aks_node_count      = 2
```

QA and Prod use the same `main.tf` pattern but different `terraform.tfvars` values (for example Prod: `10.3.0.0/16`, 5 nodes).

**Step 3: Keep separate state per environment**

```text
Azure Storage Account (companytfstate)
        |
        └── tfstate container
             ├── dev.tfstate
             ├── qa.tfstate
             └── prod.tfstate
```

`backend.tf` can contain an empty or partial `azurerm` backend block:

```hcl
terraform {
  backend "azurerm" {}
}
```

and the values are supplied per environment at `init` time:

```bash
terraform init \
  -backend-config="resource_group_name=tfstate-rg" \
  -backend-config="storage_account_name=companytfstate" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=dev.tfstate"
```

The Azure Storage backend provides state locking through blob leases. Protect the storage account with RBAC, versioning, and soft delete, and ideally keep Prod state in a separate storage account or subscription.

### Plan and apply commands

```bash
# Dev
cd environments/dev
terraform init -backend-config=...key=dev.tfstate
terraform plan -out=tfplan
terraform apply tfplan

# QA
cd ../qa
terraform init -backend-config=...key=qa.tfstate
terraform plan -out=tfplan
terraform apply tfplan

# Prod
cd ../prod
terraform init -backend-config=...key=prod.tfstate
terraform plan -out=tfplan
# review the plan and get approval, then:
terraform apply tfplan
```

Applying the saved `tfplan` guarantees Terraform applies exactly the reviewed changes instead of calculating a new plan. If the code or infrastructure changes after the plan was created, regenerate and review it.

In CI/CD, the same commands run in separate pipeline stages (Dev → QA → Prod), with a manual approval on the Prod environment.

### Important points

- Reuse modules to avoid copying infrastructure code between environments.
- Keep separate state files, and use separate subscriptions or resource groups per environment where required.
- Pin module versions (Git tag or registry version) when modules live in a separate repository, so a module change doesn't reach Prod untested.
- An alternative is **Terraform workspaces**, but separate folders make environment differences and backends more explicit, which is safer for Prod.

### Interview answer

> "I organize Terraform with a `modules` folder and separate environment folders for Dev, QA, and Prod. The modules folder contains reusable components like VNet, AKS, and Key Vault. Each environment folder calls those modules and passes its own values through `terraform.tfvars`. Each environment also has its own remote state file in Azure Storage, configured through the azurerm backend with a different key such as `dev.tfstate` or `prod.tfstate`. To deploy, I go to the environment folder, run `terraform init` with that environment's backend config, run `terraform plan -out=tfplan`, review it, and apply the saved plan. In the pipeline, each environment is a separate stage, and Production needs manual approval. This lets me reuse code while keeping each environment's configuration and state isolated."

</details>

---

<details><summary>Q11. Have you used AI services in Azure? What are they?</summary>

Azure offers several AI services. The main ones are Azure OpenAI, Azure AI Foundry, Azure AI Search, Document Intelligence, Vision, Speech, and Language.

| Service | What it does | Example |
| --- | --- | --- |
| Azure OpenAI | Provides generative AI models (GPT family, embeddings) through a secure Azure endpoint | Chatbots, code assistants, summarization |
| Azure AI Foundry | Platform to build, evaluate, deploy, and manage AI applications and agents | Enterprise AI assistant |
| Azure AI Search | Indexes and searches documents and company data, including vector search for RAG | Answering questions from internal documentation |
| Azure AI Document Intelligence | Extracts text, key-value pairs, and tables from documents | Reading invoices and PDFs |
| Azure AI Vision | Analyzes images and video, OCR | Identifying objects in images |
| Azure AI Speech | Speech-to-text, text-to-speech, translation | Voice-based applications |
| Azure AI Language | Text analysis | Sentiment analysis, key phrase extraction, PII detection |

### DevOps use case

Example: automatically summarize CI/CD pipeline failures and suggest a fix.

```text
Azure DevOps pipeline fails
        |
        v
Failure step collects the error logs
        |
        v
Mask secrets / remove sensitive data
        |
        v
Azure OpenAI (private endpoint, Managed Identity auth)
        |
        v
Summary of root cause + suggested fix
        |
        v
Posted to Teams channel or as a work item comment
```

Other DevOps uses:

- Summarizing application errors from Log Analytics or Application Insights during an incident.
- A RAG chatbot over runbooks and wiki pages using Azure AI Search plus Azure OpenAI.
- Reviewing pull requests or Terraform plans and explaining the changes.

How I would deploy it securely:

- Create the Azure OpenAI resource and model deployment with Terraform.
- Disable public network access and use a private endpoint.
- Authenticate with Managed Identity (role: *Cognitive Services OpenAI User*) instead of API keys.
- Never send passwords, tokens, or sensitive production data to the model; mask them first.
- Monitor usage, token quotas, and cost.

### Interview answer

> "I am familiar with Azure AI services such as Azure OpenAI, Azure AI Foundry, Azure AI Search, Document Intelligence, and Vision. Azure OpenAI provides generative models for chatbots, summarization, and log analysis. AI Search indexes company documents so an assistant can answer from internal data, and Document Intelligence extracts data from PDFs and invoices. From a DevOps perspective, one useful case is sending a failed pipeline's logs, after masking secrets, to Azure OpenAI to summarize the root cause and suggest a fix, then posting it to Teams. I would deploy it with Terraform, use a private endpoint and Managed Identity instead of API keys, and make sure no sensitive data is sent to the model."

Describe only what you have actually used. If you know these services but haven't implemented them in production, say that you understand them and how you would apply them.

</details>

---

<details><summary>Q12. How do you create an Azure DevOps pipeline using Terraform?</summary>

I use an Azure DevOps YAML pipeline that validates the Terraform code, creates a plan, and applies that exact plan only after review and approval. State is stored remotely in Azure Storage, and authentication uses a service connection with workload identity federation.

### Pipeline flow

```text
Developer pushes Terraform code (main.tf, variables.tf, *.tfvars)
        |
        v
Azure Repos / GitHub
        |
        v
Stage 1: Validate & Plan
  terraform init (remote backend)
  terraform fmt -check
  terraform validate
  terraform plan -out=tfplan  -> publish tfplan as artifact
        |
        v
Approval (Azure DevOps Environment check)
  Reviewer reads the plan output
        |
        v
Stage 2: Apply
  terraform init
  terraform apply tfplan
        |
        v
Azure resources created / updated
```

### Implementation steps

**Step 1: Store Terraform code in Git**

Keep `main.tf`, `variables.tf`, `versions.tf`, and per-environment `.tfvars` in Azure Repos, with branch policies so changes go through pull requests.

**Step 2: Configure authentication**

Create an **Azure Resource Manager service connection** using **workload identity federation**, so no client secret is stored. Grant its service principal only the roles it needs (for example Contributor on the target resource group, plus Storage Blob Data Contributor on the state container). Use separate service connections for non-prod and prod.

**Step 3: Configure remote state**

Create a storage account and container for state (for example `tfstate-rg / companytfstate / tfstate`) with versioning and soft delete. Each environment uses its own key: `dev.tfstate`, `qa.tfstate`, `prod.tfstate`.

**Step 4: Create the environment with approvals**

In **Pipelines → Environments**, create `prod` and add an **Approvals and checks → Approvals** rule with the required reviewers.

**Step 5: Create the YAML pipeline**

Stage 1 runs `init`, `fmt -check`, `validate`, and `plan`, and publishes the plan. Stage 2 is a deployment job targeting the `prod` environment, so it waits for approval and then applies the saved plan.

### Example multi-stage YAML

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    include:
      - terraform/*

pool:
  vmImage: ubuntu-latest

variables:
  tfDir: '$(System.DefaultWorkingDirectory)/terraform/environments/prod'

stages:
  - stage: Plan
    jobs:
      - job: TerraformPlan
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: '1.9.8'

          - task: TerraformTask@5
            displayName: Terraform Init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: $(tfDir)
              backendServiceArm: prod-terraform-wif
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: prod.tfstate

          - script: terraform fmt -check -recursive
            displayName: Terraform Format Check
            workingDirectory: $(tfDir)

          - task: TerraformTask@5
            displayName: Terraform Validate
            inputs:
              provider: azurerm
              command: validate
              workingDirectory: $(tfDir)

          - task: TerraformTask@5
            displayName: Terraform Plan
            inputs:
              provider: azurerm
              command: plan
              workingDirectory: $(tfDir)
              environmentServiceNameAzureRM: prod-terraform-wif
              commandOptions: '-out=tfplan -input=false'

          - publish: $(tfDir)/tfplan
            artifact: tfplan

  - stage: Apply
    dependsOn: Plan
    condition: succeeded()
    jobs:
      - deployment: TerraformApply
        environment: prod          # approval check configured on this environment
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self

                - download: current
                  artifact: tfplan

                - task: TerraformInstaller@1
                  inputs:
                    terraformVersion: '1.9.8'

                - task: TerraformTask@5
                  displayName: Terraform Init
                  inputs:
                    provider: azurerm
                    command: init
                    workingDirectory: $(tfDir)
                    backendServiceArm: prod-terraform-wif
                    backendAzureRmResourceGroupName: tfstate-rg
                    backendAzureRmStorageAccountName: companytfstate
                    backendAzureRmContainerName: tfstate
                    backendAzureRmKey: prod.tfstate

                - task: TerraformTask@5
                  displayName: Terraform Apply
                  inputs:
                    provider: azurerm
                    command: apply
                    workingDirectory: $(tfDir)
                    environmentServiceNameAzureRM: prod-terraform-wif
                    commandOptions: '$(Pipeline.Workspace)/tfplan/tfplan'
```

Notes:

- `TerraformTask@5` comes from the Microsoft DevLabs Terraform extension; use the version installed in your organization.
- A deployment job does not check out code automatically, so `checkout: self` is needed before re-running `init`.
- The plan file can contain sensitive values, so restrict who can read pipeline artifacts.
- If anything changed between plan and apply, Terraform rejects the stale plan; re-run the pipeline to create a new plan.

### Dev, QA, and Production

```text
Terraform pipeline
   |
   ├── Dev   -> dev.tfstate   -> Plan -> Apply (automatic)
   |
   ├── QA    -> qa.tfstate    -> Plan -> Apply (automatic or approval)
   |
   └── Prod  -> prod.tfstate  -> Plan -> Approval -> Apply
```

Each environment uses its own working directory or `.tfvars`, its own state key, and its own service connection (often a different subscription). The same stage template can be reused for every environment with parameters.

### Interview answer

> "I integrate Terraform with Azure DevOps using a multi-stage YAML pipeline. The Terraform code is in Azure Repos, and the pipeline authenticates through an Azure Resource Manager service connection using workload identity federation, so no secrets are stored. State is kept in Azure Storage with a separate key per environment. The first stage runs `terraform init`, `fmt -check`, `validate`, and `plan -out=tfplan`, and publishes the plan as an artifact. The apply stage is a deployment job targeting an Azure DevOps environment with an approval check, so a reviewer checks the plan before it continues, and then the pipeline applies exactly that saved plan. Dev, QA, and Prod each have their own state file, variables, and service connection, and Production always requires approval."

</details>

---

<details><summary>Q13. How does a pipeline run automatically in Azure DevOps?</summary>

A pipeline runs automatically through **triggers**. Azure DevOps supports four main types: CI triggers, pull request triggers, scheduled triggers, and pipeline completion (resource) triggers.

```text
Code push to branch     -> CI trigger
Pull request created    -> PR trigger / branch policy build validation
Time of day             -> Scheduled trigger
Another pipeline ends   -> Pipeline completion trigger
```

### Option 1: CI trigger

The pipeline runs whenever code is pushed to the listed branches.

```yaml
trigger:
  branches:
    include:
      - main
      - develop
  paths:
    exclude:
      - docs/*
```

```text
Developer pushes code
        |
        v
main or develop branch
        |
        v
Azure DevOps detects the change
        |
        v
Pipeline runs automatically
```

If no `trigger` section exists, a YAML pipeline runs on every branch by default. Use `trigger: none` to disable CI.

### Option 2: Pull request trigger

The pipeline validates the code when a PR is created or updated, before it is merged.

- **GitHub / Bitbucket repositories:** use the `pr:` section in YAML.

```yaml
pr:
  branches:
    include:
      - main
```

- **Azure Repos Git:** the `pr:` YAML section is ignored. Configure **Branch policies → Build validation** on `main` and select the pipeline. The PR then cannot complete until the build succeeds.

### Option 3: Scheduled trigger

```yaml
schedules:
  - cron: "30 2 * * *"
    displayName: Daily pipeline
    branches:
      include:
        - main
    always: true
```

Cron times are in **UTC**: `30 2 * * *` is 02:30 UTC, which is 08:00 AM IST. `always: true` runs even if there were no code changes. Typical uses are nightly builds, security scans, and Terraform drift checks.

### Option 4: Pipeline completion trigger

A CD pipeline starts automatically when the CI pipeline finishes successfully.

```yaml
resources:
  pipelines:
    - pipeline: ci              # alias used in this pipeline
      source: myapp-ci          # name of the CI pipeline
      trigger:
        branches:
          include:
            - main
```

```text
CI pipeline: build -> test -> publish artifact
        |
        v
CD pipeline triggered
        |
        v
Download artifact -> Deploy to Dev
```

### Important points

If a pipeline does not run automatically, I check that:

- The YAML file exists on the branch that was pushed, and its `trigger` includes that branch and path.
- The pipeline is not disabled or paused, and the trigger is not overridden in the pipeline's UI settings.
- For Azure Repos PRs, build validation is configured in the branch policy.
- For scheduled triggers, the schedule is defined on the branch listed in `branches` and the time is calculated in UTC.

### Interview answer

> "In Azure DevOps, pipelines run automatically through triggers defined in the YAML. A CI trigger with `main` under `trigger` runs the pipeline on every push to main, and I use path filters to avoid unnecessary runs. For pull requests, I use the `pr` section with GitHub, and with Azure Repos I configure build validation in the branch policy so a PR can't be merged until the build passes. Scheduled triggers use cron in UTC for nightly builds or scans, and pipeline completion triggers start the CD pipeline automatically after the CI pipeline publishes its artifact. I choose the trigger based on the requirement."

</details>

---

<details><summary>Q14. Have you added manual validation to an Azure DevOps pipeline?</summary>

Yes. I add manual validation so the pipeline pauses and waits for a person to approve before a risky step, most commonly before Terraform apply or a Production deployment. There are two ways to do it.

### Manual validation flow

```text
Code pushed to Git
       |
       v
Build and test / Terraform plan
       |
       v
Manual validation (pipeline paused, approvers notified)
       |
   Approved?
   /       \
 Yes        No / timeout
  |           |
  v           v
Terraform   Run stops
apply /     (rejected)
deploy to
Production
```

### Option 1: ManualValidation task

The `ManualValidation@1` task must run in an **agentless job** (`pool: server`).

```yaml
jobs:
  - job: TerraformPlan
    pool:
      vmImage: ubuntu-latest
    steps:
      - script: echo "Terraform plan completed"

  - job: ManualApproval
    dependsOn: TerraformPlan
    pool: server
    timeoutInMinutes: 1440          # job timeout must be longer than the task timeout
    steps:
      - task: ManualValidation@1
        timeoutInMinutes: 1380
        inputs:
          notifyUsers: 'platform-team@company.com'
          approvers: 'platform-team@company.com'
          allowApproversToApproveTheirOwnRuns: false
          instructions: 'Review the Terraform plan output before the Production apply.'
          onTimeout: 'reject'

  - job: TerraformApply
    dependsOn: ManualApproval
    pool:
      vmImage: ubuntu-latest
    steps:
      - script: echo "terraform apply tfplan"
```

The apply job depends on `ManualApproval`, so it runs only if the reviewer approves.

### Option 2: Environment approvals and checks (preferred for Production)

1. Go to **Pipelines → Environments → prod → Approvals and checks**.
2. Add **Approvals** with the required users or group, and optionally **Business hours**, **Branch control** (only `main` can deploy), or **Required template** checks.
3. In YAML, use a deployment job that targets the environment:

```yaml
- deployment: DeployProd
  environment: prod
  strategy:
    runOnce:
      deploy:
        steps:
          - script: echo "Deploying to Production"
```

These checks are configured outside the YAML, so a developer cannot remove the approval by editing the pipeline file.

| | ManualValidation task | Environment approvals |
| --- | --- | --- |
| Where configured | In the pipeline YAML | On the Azure DevOps environment |
| Can be removed by editing YAML | Yes | No |
| Typical use | Pause mid-stage to review output (for example a plan) | Gate every deployment to an environment |

### When I use it

- Before applying Terraform changes to Production.
- Before deploying a new application version to Production.
- After QA deployment, before promoting the release.
- When infrastructure changes need a human review.

### Interview answer

> "Yes. After Terraform generates a plan, I pause the pipeline with the ManualValidation task in an agentless job. The approvers get a notification, review the plan, and approve or reject it, and if it times out it is rejected. Only after approval does the apply job run. For Production deployments, I prefer approvals and checks on the Azure DevOps environment, because they're configured outside the YAML and can't be bypassed by changing the pipeline file. I can also add branch control so only the main branch can deploy to Production."

</details>

---

<details><summary>Q15. Can you build Splunk from scratch?</summary>

Splunk is not built like an application; it is **deployed and configured**. Building it from scratch means installing the Splunk components, onboarding logs, setting up indexes and retention, and creating dashboards, alerts, and access control.

### Architecture

```text
Applications / Linux & Windows servers / AKS
        |
        |  Universal Forwarder (port 9997)  or  HTTP Event Collector (HEC, port 8088)
        v
Indexer(s)            -> parse, index, and store data
        |
        v
Search Head           -> searches (SPL), dashboards, alerts, reports
        |
        v
Email / Teams / ServiceNow notifications
```

| Component | Purpose |
| --- | --- |
| Universal Forwarder | Lightweight agent on servers that collects and sends logs |
| Heavy Forwarder (optional) | Parses or filters data before sending |
| HTTP Event Collector (HEC) | Token-based HTTP endpoint for applications and Kubernetes collectors |
| Indexer | Stores and indexes data; can be clustered for high availability |
| Search Head | UI for searches, dashboards, alerts |
| Deployment Server / Cluster Manager | Centrally manages forwarder configs / indexer cluster |

For a small or test environment, all roles can run on a single Splunk Enterprise instance. Many companies use **Splunk Cloud**, where Splunk manages indexers and search heads and we only handle data onboarding and use cases.

### Step 1: Install the Splunk components

Install Splunk Enterprise on the indexer and search head servers (or use Splunk Cloud), enable receiving on port 9997 on the indexers, and install the Universal Forwarder on source servers.

### Step 2: Configure log collection

**Servers (Universal Forwarder `inputs.conf`):**

```ini
[monitor:///var/log/messages]
index = linux_os
sourcetype = syslog

[monitor:///opt/myapp/logs/application.log]
index = application_logs
sourcetype = myapp:log
```

Windows servers collect Event Viewer logs through `WinEventLog` inputs.

**AKS:** deploy the **Splunk OpenTelemetry Collector for Kubernetes** (Helm chart) or Fluent Bit as a DaemonSet. It reads container logs from each node and sends them, with namespace/pod metadata, to Splunk through HEC. (Splunk Connect for Kubernetes is deprecated in favor of the OpenTelemetry Collector.)

### Step 3: Configure indexes and retention

```ini
# indexes.conf
[application_logs]
homePath   = $SPLUNK_DB/application_logs/db
coldPath   = $SPLUNK_DB/application_logs/colddb
thawedPath = $SPLUNK_DB/application_logs/thaweddb
frozenTimePeriodInSecs = 7776000     # 90 days
```

Use separate indexes per environment or data type (for example `aks_prod`, `aks_nonprod`) so retention and access can be controlled separately.

### Step 4: Create dashboards and alerts

Dashboard panels: error count, HTTP 5xx rate, response time, pod restarts, top exceptions.

Example alert search:

```spl
index=aks_prod sourcetype=myapp:log status>=500
| stats count by service
| where count > 100
```

Schedule it every 5 minutes; when it returns results, trigger an email, Teams webhook, or ServiceNow incident.

### Step 5: Secure Splunk

- Role-based access: users only see the indexes for their applications.
- TLS between forwarders and indexers, and HTTPS for the web UI and HEC.
- HEC tokens stored securely (for example in Key Vault), one token per source.
- Integrate login with SSO (SAML with Microsoft Entra ID).

### Important points

- Plan license capacity (daily ingest volume) and storage before onboarding everything.
- Filter noisy logs at the source to control cost.
- Be honest about scope: if Splunk already existed, say you **integrated** applications and infrastructure with Splunk and built dashboards and alerts, rather than that you built it from scratch.

### Interview answer

> "Splunk isn't built like an application; it's deployed and configured. I would set up the components based on the size: Universal Forwarders on servers, indexers to store and index the data, and a search head for searches and dashboards, or use Splunk Cloud. I configure inputs to collect OS and application logs, and for AKS I deploy the Splunk OpenTelemetry Collector as a DaemonSet that sends container logs through the HTTP Event Collector. I create indexes per environment with retention policies, build dashboards for errors, latency, and pod restarts, and create alerts, for example when HTTP 500 errors exceed a threshold in five minutes, that notify Teams or email. Finally, I secure it with role-based access per index, TLS between components, and SSO."

</details>

---

<details><summary>Q16. How have you integrated AKS and application logs with Splunk?</summary>

In AKS, I run a log collector as a **DaemonSet** (one pod per node). It reads every container's stdout/stderr log files on that node, adds Kubernetes metadata, and sends the logs to Splunk over HTTPS through the **HTTP Event Collector (HEC)**. I use the **Splunk OpenTelemetry Collector for Kubernetes** or **Fluent Bit**.

### Log flow

```text
Spring Boot application (AKS pod)
        |
        | 1. Writes logs to stdout / stderr (JSON format)
        v
Node: /var/log/containers/*.log  (written by the container runtime)
        |
        | 2. DaemonSet collector reads the files
        v
Splunk OTel Collector / Fluent Bit
        |  adds namespace, pod, container, cluster name
        |  buffers and retries if Splunk is unavailable
        |
        | 3. HTTPS + HEC token  (port 8088, or 443 for Splunk Cloud)
        v
Splunk HEC -> Index (aks_prod / aks_nonprod)
        |
        v
Search, dashboards, and alerts
```

### Step 1: Configure application logging

Configure the Spring Boot application to write logs to **stdout/stderr**, not to files inside the container, preferably in **JSON** format so fields like `level`, `traceId`, and `message` are searchable in Splunk. JSON also keeps Java stack traces as one event instead of many lines.

### Step 2: Configure HEC in Splunk

1. In Splunk, go to **Settings → Data inputs → HTTP Event Collector → New Token**.
2. Allow only the target indexes, for example `aks_prod` and `aks_nonprod`.
3. Make sure SSL is enabled for HEC.
4. Note the HEC URL, for example `https://splunk.company.com:8088/services/collector` (Splunk Cloud: `https://http-inputs-<stack>.splunkcloud.com:443/services/collector`).

### Step 3: Store the HEC token securely

Store the token in Azure Key Vault and deliver it to the cluster as a Kubernetes Secret (for example, through the Key Vault CSI driver sync, see Q9). Never commit it to Git or Helm values files.

```bash
kubectl create namespace splunk
kubectl create secret generic splunk-otel-collector \
  -n splunk \
  --from-literal=splunk_platform_hec_token=<token-from-key-vault>
```

### Step 4: Deploy the collector with Helm

```yaml
# values.yaml
clusterName: aks-prod
splunkPlatform:
  endpoint: https://splunk.company.com:8088/services/collector
  index: aks_prod
  insecureSkipVerify: false
secret:
  create: false
  name: splunk-otel-collector
```

```bash
helm repo add splunk-otel-collector-chart https://signalfx.github.io/splunk-otel-collector-chart
helm upgrade --install splunk-otel-collector \
  splunk-otel-collector-chart/splunk-otel-collector \
  -n splunk -f values.yaml
```

I deploy this through the Azure DevOps pipeline like any other Helm release.

**Fluent Bit alternative:** use the `kubernetes` filter for metadata and the `splunk` output plugin:

```ini
[OUTPUT]
    Name          splunk
    Match         kube.*
    Host          splunk.company.com
    Port          8088
    Splunk_Token  ${SPLUNK_HEC_TOKEN}
    TLS           On
    TLS.Verify    On
```

### Step 5: Allow network access

If AKS egress goes through Azure Firewall or an NSG, allow outbound HTTPS from the AKS nodes to the Splunk HEC endpoint on port 8088 (or 443).

### Step 6: Verify the logs in Splunk

```spl
index=aks_prod k8s.namespace.name="production" k8s.pod.name="myapp-*"
| sort - _time
```

(Field names depend on the collector; Fluent Bit uses `kubernetes.namespace_name`.) Then I create dashboards for error counts, HTTP 5xx, and pod restarts, and alerts that notify Teams or email.

### Important points

- Logs go to stdout/stderr; the collector reads them from the node, so the application does not need any Splunk library.
- Enable buffering and retries so a temporary Splunk outage doesn't lose logs.
- Keep TLS verification on in Production.
- Filter noisy namespaces (for example `kube-system` debug logs) at the collector to reduce Splunk license usage.
- Use separate indexes per environment so retention and access can be controlled separately.

### Interview answer

> "I integrate AKS with Splunk using the Splunk OpenTelemetry Collector, or Fluent Bit, deployed as a DaemonSet. The Spring Boot application writes JSON logs to stdout, the container runtime writes them to the node, and the collector on each node reads them, adds metadata like namespace, pod, and cluster name, and sends them to Splunk's HTTP Event Collector over HTTPS. On the Splunk side, I create a HEC token restricted to the right indexes, and the token is stored in Key Vault and delivered to the cluster as a Kubernetes Secret, never in Git. I deploy the collector with Helm through the pipeline, allow outbound traffic to the HEC endpoint, and enable buffering and retries. Finally, I verify the logs in Splunk by index and namespace and build dashboards and alerts on them."

</details>

---

<details><summary>Q17. How do application logs from AKS go to Azure Monitor?</summary>

There are two paths, and they are usually used together:

- **Container logs (stdout/stderr):** collected by the **Azure Monitor Agent** through **Container Insights** and stored in a **Log Analytics workspace** (table `ContainerLogV2`).
- **Application telemetry** (requests, exceptions, dependencies, response times, traces): sent by **Application Insights** instrumentation to the same workspace (tables `AppRequests`, `AppExceptions`, `AppDependencies`, `AppTraces`).

### Log flow

```text
Spring Boot application (AKS pod)
     |                                   |
     | stdout / stderr                   | Application Insights Java agent
     v                                   |  (requests, exceptions, dependencies)
Azure Monitor Agent (DaemonSet)          |
  via Container Insights + DCR           |
     |                                   |
     v                                   v
Log Analytics workspace  <------  Application Insights (workspace-based)
  ContainerLogV2, KubePodInventory        AppRequests, AppExceptions, ...
     |
     v
Azure Monitor: KQL queries, workbooks, alert rules -> action group (email / Teams)
```

### Step 1: Create a Log Analytics workspace

Create a workspace (usually one per environment or a shared one per region) and set the retention period.

### Step 2: Enable Container Insights on AKS

```bash
az aks enable-addons \
  --resource-group my-rg \
  --name my-aks \
  --addons monitoring \
  --workspace-resource-id <log-analytics-workspace-id>
```

This deploys the Azure Monitor Agent as a DaemonSet and creates a **data collection rule (DCR)** that defines what is collected. In the DCR (or the Container Insights settings), I:

- Make sure the **ContainerLogV2** schema is used.
- Select which namespaces to collect or exclude (for example exclude `kube-system`) to control cost.
- Choose the collection frequency and cost preset.

In Terraform, the same is done with the `oms_agent` block on `azurerm_kubernetes_cluster` plus a data collection rule.

### Step 3: Configure application logging

The Spring Boot application writes logs to **stdout/stderr**, ideally in JSON format. The agent collects them automatically; no code change is needed for container logs.

### Step 4: Add Application Insights for application telemetry

For request duration, exceptions, and dependency calls, I attach the **Application Insights Java agent** (no code change):

```yaml
env:
  - name: JAVA_TOOL_OPTIONS
    value: "-javaagent:/agents/applicationinsights-agent-3.x.jar"
  - name: APPLICATIONINSIGHTS_CONNECTION_STRING
    valueFrom:
      secretKeyRef:
        name: appinsights
        key: connection-string
```

The agent also forwards Logback/Log4j log statements to `AppTraces`, with an operation ID that links each log line to its request.

### Step 5: Query the logs with KQL

```kusto
ContainerLogV2
| where TimeGenerated > ago(1h)
| where PodNamespace == "production"
| where LogMessage contains "ERROR"
| project TimeGenerated, PodName, ContainerName, LogMessage
| order by TimeGenerated desc
```

### Step 6: Configure alerts

Create a **log search alert rule** on a query (for example, more than 50 ERROR lines in 5 minutes, or any pod in CrashLoopBackOff), and connect it to an **action group** that sends email, Teams, or creates a ServiceNow incident.

### Important points

- The Azure Monitor Agent collects only what the DCR is configured to collect.
- Container logs and Application Insights telemetry serve different purposes: container logs show what the application printed, Application Insights shows request-level performance and failures.
- Control cost by excluding noisy namespaces, using the Basic logs plan for verbose tables, and setting retention.

### Interview answer

> "For AKS, I enable Container Insights and connect the cluster to a Log Analytics workspace. This deploys the Azure Monitor Agent as a DaemonSet, and a data collection rule defines what it collects. I configure ContainerLogV2 and exclude noisy namespaces like kube-system. The application writes logs to stdout and stderr, and the agent collects them into the ContainerLogV2 table, where I query them with KQL. For request duration, exceptions, and dependency failures, I attach the Application Insights Java agent with the connection string from a secret, and that telemetry goes to the same workspace. Then I create log search alert rules with action groups to notify the team about errors or pod failures."

</details>

---

<details><summary>Q18. How do Azure Monitor, Application Insights, and Log Analytics work together?</summary>

**Azure Monitor** is the overall monitoring platform. **Application Insights** is the part of Azure Monitor that collects application-level telemetry. The **Log Analytics workspace** is where the log data is stored and queried with KQL. Alerts, workbooks, and dashboards in Azure Monitor work on top of that data.

### Architecture

```text
Application (AKS / App Service / Functions)
        |                                   |
        | Application Insights agent         | stdout/stderr, node and pod data
        | or OpenTelemetry                   | (AKS: Azure Monitor Agent + Container Insights)
        v                                   |
Application Insights (workspace-based)       |
  requests, exceptions, dependencies,        |
  traces, availability tests                 |
        |                                   |
        v                                   v
            Log Analytics workspace
  AppRequests, AppExceptions, AppDependencies, AppTraces,
  ContainerLogV2, KubePodInventory, ...
                     |
                     v
             Azure Monitor
  KQL queries, workbooks, dashboards,
  alert rules -> action groups (email / Teams / ServiceNow)
```

### Integration steps

**Step 1: Create a Log Analytics workspace**

Create the workspace that will store logs, and set its retention and access control.

**Step 2: Create workspace-based Application Insights**

Create the Application Insights resource and link it to that workspace. Its telemetry is then stored in the workspace tables (`AppRequests`, `AppExceptions`, and so on), so it can be queried together with infrastructure logs.

**Step 3: Instrument the application**

For Spring Boot, attach the Application Insights Java agent (or Azure Monitor OpenTelemetry distro) and set `APPLICATIONINSIGHTS_CONNECTION_STRING` from a secret. This collects incoming requests, exceptions, response times, dependency calls (database, HTTP, Service Bus), and application logs.

**Step 4: Enable Container Insights for AKS**

Enable the monitoring add-on with the same workspace, and configure the data collection rule so the Azure Monitor Agent collects the required container logs (`ContainerLogV2`) and Kubernetes inventory data.

**Step 5: Create alerts and dashboards**

Use Application Insights views (Failures, Performance, Application Map) for application troubleshooting, KQL in the workspace to correlate data across tables, and Azure Monitor alert rules with action groups for notification.

### Example: application returns HTTP 500 errors

```text
User request fails (HTTP 500)
        |
        v
Application Insights records the failed request + exception
        |
        v
Stored in Log Analytics workspace (AppRequests, AppExceptions)
        |
        v
Azure Monitor alert rule (failed requests > threshold)
        |
        v
Action group notifies the support team
        |
        v
Engineer uses the operation ID to find the related exception,
dependency failure, and container log lines
```

Example exception query:

```kusto
AppExceptions
| where TimeGenerated > ago(1h)
| project TimeGenerated, AppRoleName, ExceptionType, OuterMessage, OperationId
| order by TimeGenerated desc
```

Example request query:

```kusto
AppRequests
| where TimeGenerated > ago(1h)
| where Success == false
| summarize FailedRequests = count() by AppRoleName, ResultCode
| order by FailedRequests desc
```

### Important distinctions

| Component | Main purpose | Example data |
| --- | --- | --- |
| Azure Monitor | Overall monitoring, analysis, visualization, and alerting platform | Metrics, logs, traces, alerts, and workbooks |
| Application Insights | Application performance monitoring and distributed tracing | Requests, dependencies, exceptions, traces, and availability |
| Log Analytics workspace | Log and trace data store with KQL query capability | `ContainerLogV2`, `AppRequests`, `AppExceptions`, and `AppDependencies` |
| Azure Monitor workspace | A different resource currently used primarily for managed Prometheus metrics | Prometheus time-series metrics |

Connecting Application Insights to a workspace does not automatically instrument the application or collect every application log. The application must be instrumented, the logging bridge or OpenTelemetry pipeline must be configured where required, and Container Insights collection settings must explicitly include the desired AKS logs.

### Interview answer

> "Azure Monitor is the overall observability platform. Application Insights provides application performance monitoring, and a workspace-based Application Insights resource stores its telemetry in a linked Log Analytics workspace. I instrument the application to collect requests, exceptions, dependencies, latency, and traces. Separately, I enable Container Insights on AKS so the Azure Monitor Agent sends configured container logs and Kubernetes data to the workspace. I use Application Insights for application troubleshooting, KQL and workbooks to correlate data across tables, and Azure Monitor alert rules with action groups for notification. Simply linking Application Insights to a workspace is not enough—the application instrumentation and AKS data collection must both be configured."

</details>

---

<details><summary>Q19. Which plan is used for Azure App Service?</summary>

An **App Service Plan** defines the compute resources that a Web App runs on: region, operating system, CPU, memory, pricing tier, instance count, and scaling capability. The App Service is where the application runs; the App Service Plan provides the underlying compute.

### App Service Plan tiers

| Tier | Typical usage |
| --- | --- |
| Free (F1) | Learning and testing |
| Shared (D1) | Basic development and testing (Windows only) |
| Basic (B1, B2, B3) | Small applications with dedicated compute; manual scale only |
| Standard (S1, S2, S3) | Production applications; supports autoscale and deployment slots |
| Premium (P0v3, P1v3, P1mv3, etc.) | High-performance production workloads with more slots and faster scaling |
| Isolated (I1v2, etc. on App Service Environment) | Enterprise workloads that need full network isolation |

Exact features, limits, and SKU availability depend on the tier and region.

### Which plan in Production?

- **Standard:** Suitable for many regular production applications.
- **Premium v3:** Suitable for applications that need more compute, more instances, VNet integration at scale, or faster autoscale.
- **Isolated:** Used when the application must run in a dedicated, network-isolated App Service Environment.

For Dev and QA, a lower-cost Basic or Standard plan is usually enough. Multiple Web Apps can share one plan, but they also share its compute instances, so a noisy application can affect the others.

### Interview answer

> "I use an Azure App Service Plan to define the CPU, memory, pricing tier, and scaling capacity for my web application. For development, we use a lower-cost plan. For production, we generally choose Standard or Premium v3 based on traffic, performance, and availability requirements, and Isolated when network isolation is required. On Standard and above, I configure autoscaling to add or remove instances based on CPU or request load. The App Service is where the application runs; the plan provides the compute underneath it."

</details>

---

<details><summary>Q20. What are Web App deployment slots?</summary>

Deployment slots are separate live environments within the same Azure App Service, each with its own host name. They let us deploy and test a new version before making it live.

```text
Azure App Service (Web App)
 |
 |-- Production slot  -> serves live users (v1)
 |
 |-- Staging slot     -> deploy and test the new version (v2)
                |
                v
          Slot swap: Staging <-> Production
```

### How it works in a CI/CD pipeline

1. A developer pushes code to Git.
2. Azure DevOps builds the application and runs tests.
3. The pipeline deploys the new version to the **Staging** slot.
4. Smoke tests and validation run against the Staging slot URL.
5. After approval, the pipeline swaps Staging with Production.
6. The new version becomes live, and the previous production version moves to Staging, which makes rollback a swap back.

```yaml
- task: AzureWebApp@1
  inputs:
    azureSubscription: my-azure-service-connection
    appType: webAppLinux
    appName: my-springboot-app
    deployToSlotOrASE: true
    resourceGroupName: my-rg
    slotName: staging
    package: '$(Pipeline.Workspace)/drop/app.jar'

- task: AzureAppServiceManage@0
  inputs:
    azureSubscription: my-azure-service-connection
    Action: Swap Slots
    WebAppName: my-springboot-app
    ResourceGroupName: my-rg
    SourceSlot: staging
```

### Why use deployment slots?

- **Minimal downtime:** The swap warms up the instances before switching traffic.
- **Pre-production testing:** Validate changes in the real hosting environment before users see them.
- **Easy rollback:** Swap back if the new release has issues.
- **Safer releases:** Verify the application before switching production traffic.

Deployment slots are available in Standard, Premium, and Isolated tiers. Settings marked as **deployment slot settings** stay with their slot during a swap; for example, a Staging database connection string should not move to Production.

### Interview answer

> "I use deployment slots in Azure App Service to deploy a new version without immediately affecting live users. The Azure DevOps pipeline deploys the application to the Staging slot, and I run smoke tests against it. Once it is validated and approved, I swap Staging with Production. The previous version moves to Staging, so rollback is just another swap. I mark environment-specific values as slot settings so they don't move during the swap."

</details>

---

<details><summary>Q21. Why use Blue-Green deployment instead of Canary deployment?</summary>

Both strategies release a new version safely. The main difference is **how traffic reaches the new version**.

| | Blue-Green | Canary |
| --- | --- | --- |
| Environments | Two full environments: Blue (current) and Green (new) | One environment with old and new versions side by side |
| Traffic | Switched all at once after validation | Shifted gradually (for example 5% -> 25% -> 100%) |
| Testing | Full validation in Green before any user traffic | Validation with a small slice of real production traffic |
| Rollback | Switch traffic back to Blue | Route traffic away from the new version |
| Cost | Needs capacity for two full environments during the release | Lower duplicate capacity, but needs traffic splitting and strong monitoring |

### When to choose Blue-Green

- **Quick switch:** Redirect all traffic to the new environment after testing.
- **Simple rollback:** Switch traffic back to the previous environment.
- **Full validation first:** Test the complete application before it receives production traffic.
- **No need for gradual exposure:** The release can go live as a whole rather than to a small user group first.

Canary is the better choice when the change is risky, behavior under real traffic is hard to reproduce in testing, and the team has good metrics and alerting to decide whether to continue the rollout.

### Example using Azure App Service

1. Version v1 serves users in the Production slot (Blue).
2. Deploy v2 to the Staging slot (Green).
3. Run smoke tests and validate the application.
4. Swap Staging and Production.
5. If v2 has an issue, swap back, provided the previous version and its configuration are still usable.

App Service can also route a percentage of traffic to a slot (**Traffic % / testing in production**), which is a simple way to run a canary-style release with the same slots.

Blue-Green does not automatically guarantee zero downtime. The result depends on application startup, health checks, slot settings, and **database compatibility**: schema changes must be backward compatible so that rolling back the application does not break against the new schema.

### Interview answer

> "I choose Blue-Green deployment when I need a simple, fast release with an easy rollback. In Azure App Service, I deploy the new version to the Staging slot, run smoke tests, and swap it with Production after approval. If any issue occurs, I swap back. Canary is more suitable when I want to expose the new version gradually to a small percentage of users and monitor real production traffic before increasing the rollout. Blue-Green switches traffic between environments; Canary gradually increases traffic to the new version. Neither is always better—it depends on the application's risk, traffic, and release requirements."

</details>

---

<details><summary>Q22. A new AzureRM provider version was just released. How do you use it for deployment without breaking existing infrastructure?</summary>

The goal is to test the new provider version safely, review the Terraform plan, and avoid unexpected changes to existing resources.

### Step-by-step approach

**1. Review the release**

Read the AzureRM provider changelog and upgrade guide, confirm that the new version supports the required resource or feature, and note any breaking changes or deprecated arguments.

**2. Pin the provider version**

In `versions.tf`, specify the version explicitly instead of letting Terraform pick an unexpected one:

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.5.0" # Example version only
    }
  }
}
```

Commit the `.terraform.lock.hcl` file so every pipeline run uses the same provider build. Don't assume the newest version is automatically safe.

**3. Test in a lower environment**

- Create a separate branch for the upgrade.
- Run `terraform init -upgrade` to select the new version, and review the changes to `.terraform.lock.hcl`.
- Test against Dev or QA, or an isolated test resource, first.

**4. Validate before deployment**

```bash
terraform fmt -check
terraform validate
terraform plan -out=tfplan
```

Review the plan carefully. Check whether any existing resources will be modified, **replaced**, or **destroyed** unexpectedly. A provider upgrade alone should normally produce no changes; any diff needs an explanation before continuing.

**5. Deploy with approval**

If the plan is as expected, apply the saved plan:

```bash
terraform apply tfplan
```

For Production, use a manual approval stage in Azure DevOps and apply the same reviewed plan artifact.

**6. Prepare rollback and recovery**

- Back up the Terraform state; enable versioning or soft delete on the state storage account.
- Keep the previous provider version and lock file available.
- Use `lifecycle { prevent_destroy = true }` on critical resources.
- If problems occur, stop further deployments and assess the state and infrastructure before reverting the provider version.

Downgrading the provider does not automatically reverse infrastructure changes, and a state file written by a newer provider version is not guaranteed to work with an older one. Test the rollback procedure before the Production upgrade.

### Interview answer

> "If a new AzureRM provider version is released, I don't upgrade it directly in Production. First, I check the changelog and breaking changes, pin the version in Terraform, and test it on a separate branch in Dev or QA. I run `terraform init -upgrade`, commit the updated lock file, validate the configuration, and generate a plan. I carefully review any replacements or deletions, and I apply only the reviewed plan after testing and approval. I also back up the Terraform state and keep the previous version available for recovery. This lets me adopt the new provider while minimizing the risk of breaking existing infrastructure."

</details>

---

<details><summary>Q23. Instead of SonarQube and Trivy, what commercial (non-open-source) tools can you use as CI/CD checks?</summary>

Yes, there are several commercial tools. They usually add enterprise support, a central dashboard across all projects, policy management, and better reporting. I explain them by the type of check they replace:

- **SAST (code security):** finds vulnerabilities in our own source code.
- **SCA (dependencies):** finds vulnerable or badly licensed open-source libraries.
- **Container image scanning:** finds vulnerabilities in the Docker image (OS packages and libraries).
- **IaC scanning:** finds misconfigurations in Terraform, Kubernetes YAML, and Helm charts.
- **DAST:** tests the running application from the outside.

### Commercial tools

| Tool | Main purpose | Where in the pipeline |
| --- | --- | --- |
| Checkmarx One | SAST, SCA, IaC, API security | Code security stage |
| Veracode | SAST, DAST, SCA | Build stage and post-deployment (DAST) |
| Snyk | Code, open-source dependencies, containers, IaC | Build and image scanning |
| Mend.io | Open-source dependency and license risk | Dependency scanning |
| Black Duck (Coverity, Black Duck SCA) | Static analysis and open-source risk | Code analysis stage |
| Prisma Cloud (Palo Alto) | Container, IaC, and cloud security posture | Image scanning, IaC, runtime |
| JFrog Xray | Artifact, dependency, and container vulnerabilities | Artifact repository and release stages |
| Aqua Security / Wiz | Container and cloud security | Image scanning and runtime |
| GitHub Advanced Security for Azure DevOps | Code scanning (CodeQL), dependency scanning, secret scanning | Built into Azure Repos / Pipelines |
| Microsoft Defender for Cloud | ACR image scanning, DevOps security posture, runtime protection for AKS | Registry and cluster |

Features and licensing depend on the product edition and subscription.

### Which tool replaces which?

| Existing tool | Commercial alternative |
| --- | --- |
| SonarQube (code quality and security) | Checkmarx One, Veracode, Coverity, GitHub Advanced Security (CodeQL) |
| Trivy (container image scanning) | Prisma Cloud, JFrog Xray, Snyk Container, Aqua, Defender for Containers |
| Trivy / Checkov (Terraform and IaC scanning) | Prisma Cloud, Snyk IaC, Checkmarx One |
| OWASP Dependency-Check (dependency scanning) | Mend.io, Snyk Open Source, Black Duck SCA, JFrog Xray |

These are alternatives, not exact one-to-one replacements. For example, SonarQube is mainly about code quality (bugs, code smells, coverage), while Checkmarx and Veracode focus on security, so some teams keep SonarQube for quality and add a commercial tool for security.

### How I use them in an Azure DevOps pipeline

```text
Code checkout
      |
      v
Build and unit tests
      |
      v
SAST + SCA (Checkmarx One / Snyk / GitHub Advanced Security)
      |  fail on Critical/High findings
      v
Docker build
      |
      v
Image scan (Prisma Cloud / JFrog Xray / Snyk Container)
      |  fail if the image violates the policy
      v
Push to ACR (Defender for Cloud keeps scanning the registry)
      |
      v
Approval -> Deploy to AKS
      |
      v
DAST (Veracode) against the deployed test environment
```

Example with the Snyk extension:

```yaml
- task: SnykSecurityScan@1
  displayName: Snyk dependency scan
  inputs:
    serviceConnectionEndpoint: snyk-connection
    testType: app
    severityThreshold: high
    failOnIssues: true

- task: SnykSecurityScan@1
  displayName: Snyk container scan
  inputs:
    serviceConnectionEndpoint: snyk-connection
    testType: container
    dockerImageName: myacr.azurecr.io/myapp:$(Build.BuildNumber)
    severityThreshold: high
    failOnIssues: true
```

Example with GitHub Advanced Security for Azure DevOps:

```yaml
- task: AdvancedSecurity-Codeql-Init@1
  inputs:
    languages: java
- task: AdvancedSecurity-Codeql-Autobuild@1
- task: AdvancedSecurity-Dependency-Scanning@1
- task: AdvancedSecurity-Codeql-Analyze@1
```

### Important points

- Define the **policy** (for example, fail on Critical and High, allow Medium with a ticket) so the gate is consistent across teams.
- Store tool tokens in service connections or Key Vault, not in YAML.
- Scan the image again in the registry, because new vulnerabilities are published after the build.
- Handle false positives through the tool's suppression or exception process with an expiry date, not by disabling the check.

### Interview answer

> "Yes. Apart from SonarQube and Trivy, I can use commercial tools depending on the organization's requirements. For code security, I can use Checkmarx One, Veracode, or GitHub Advanced Security for Azure DevOps with CodeQL. For dependencies, Snyk or Mend.io. For container images and Terraform, Prisma Cloud, JFrog Xray, or Snyk Container and IaC. Microsoft Defender for Cloud can also keep scanning images in ACR. In Azure DevOps, I add these scans as pipeline stages: code and dependency scanning after the build, and image scanning after the Docker build and before pushing to ACR. I define severity thresholds, so if a scan finds a critical vulnerability that violates the policy, the pipeline fails and the build doesn't reach Production."

If the interviewer asks for just two names, Checkmarx One and Prisma Cloud are good examples. Mention them as tools you know how to integrate, and claim hands-on experience only for the ones you have actually used.

</details>

---

<details><summary>Q24. If you have a private network (VNet), subnet, and private endpoint, how does the request flow?</summary>

A **VNet** is the private network, a **subnet** divides it into smaller ranges, and a **private endpoint** is a network interface with a private IP from a subnet that connects to one specific Azure service (for example Azure SQL Database) through **Azure Private Link**.

Example: an application in an AKS pod connects to Azure SQL Database through a private endpoint. (Q6 covers how to set this up step by step.)

### Request flow

```text
AKS Pod (snet-aks, 10.0.1.0/24)
     |
     | 1. Connects to myserver.database.windows.net:1433
     v
DNS resolution (Azure DNS 168.63.129.16 or custom DNS forwarding to it)
     |   myserver.database.windows.net
     |     -> CNAME myserver.privatelink.database.windows.net
     |     -> A record 10.0.2.5   (Private DNS zone privatelink.database.windows.net,
     |                             linked to the VNet)
     v
VNet routing (same VNet, or peered hub-spoke VNet)
     |   Route tables / NSGs / firewall checked on the way
     | 2. TCP 1433 to 10.0.2.5
     v
Private endpoint NIC (snet-private-endpoints, 10.0.2.5)
     |
     | 3. Azure Private Link (Microsoft backbone, never the internet)
     v
Azure SQL Database (public network access disabled)
     |
     | 4. Authentication (Entra ID / managed identity or SQL login) and database permissions
     v
Response returns the same private path to the pod
```

The application keeps using the normal hostname. Only DNS changes, which is why DNS is the most important part.

### Step-by-step explanation

**Step 1: The application sends a request**

The pod connects to `myserver.database.windows.net` on port 1433. It does not use the IP address directly, because TLS certificates and connection strings expect the hostname.

**Step 2: DNS returns the private IP**

The public name has a CNAME to `myserver.privatelink.database.windows.net`. Because the private DNS zone `privatelink.database.windows.net` is linked to the VNet, that name resolves to the private endpoint IP `10.0.2.5` instead of a public IP. With custom DNS servers (common in hub-spoke), they must forward to Azure DNS (168.63.129.16) or an Azure DNS Private Resolver.

**Step 3: Traffic is routed inside the private network**

The packet goes to `10.0.2.5` through the VNet, or through VNet peering if the private endpoint is in a hub VNet. User-defined routes, NSGs, and Azure Firewall may inspect it on the way. NSG rules on the private endpoint subnet only apply if network policies are enabled on that subnet.

**Step 4: The private endpoint forwards to the service**

The private endpoint passes the traffic over Private Link to that one SQL server. The traffic never leaves the Microsoft network, and public network access on the server can be disabled.

**Step 5: The service authenticates the request**

The connection succeeds only if authentication (preferably Entra ID with a managed identity) and database permissions are correct. Network access alone does not grant data access.

### What to configure

| Component | What to configure |
| --- | --- |
| VNet and subnets | Separate subnets for the application and for private endpoints, with no overlapping ranges across peered networks |
| Private endpoint | Created for the target resource and sub-resource (for example `sqlServer`) in the private endpoint subnet |
| Private DNS zone | `privatelink.database.windows.net` linked to every VNet that needs to resolve it, with a DNS zone group on the endpoint so the A record is managed automatically |
| Routing and security | Route tables, NSGs (with network policies enabled), and firewall rules allow the port, for example TCP 1433 |
| Service settings | Public network access disabled after private connectivity is tested |
| Authentication | Managed identity or credentials from Key Vault, and database permissions |

### How to verify

```bash
# From inside the pod or a VM in the VNet
nslookup myserver.database.windows.net     # must return 10.0.2.5, not a public IP
nc -zv myserver.database.windows.net 1433   # port reachable
```

If `nslookup` returns a public IP, the private DNS zone is not linked to the VNet, or the custom DNS server is not forwarding to Azure DNS.

### Important points

- A private endpoint does not guarantee connectivity on its own. DNS, routing, NSGs, firewall rules, service settings, and authentication must all be correct.
- The most common failure is DNS: the hostname still resolves to the public IP, so the connection fails once public access is disabled.
- A private endpoint is for **inbound** access to a specific service instance. It is different from a **service endpoint**, which keeps the service's public IP but allows traffic only from selected subnets.

### Interview answer

> "When an application in the VNet calls a private Azure service, it uses the normal hostname. DNS resolves that hostname through the CNAME to the privatelink name, and the private DNS zone linked to the VNet returns the private endpoint's private IP. The traffic then goes through the VNet, or a peered VNet, using the configured routes, NSGs, and firewall rules, and reaches the private endpoint NIC in its subnet. Azure Private Link carries it to the service over the Microsoft backbone, so the service's public endpoint can be disabled. Finally, the service checks authentication and permissions. When I troubleshoot, I first check that `nslookup` returns the private IP, then the port with `nc`, then NSGs and routes, and then authentication."

</details>

---

## Important interview tip

Describe only the work you actually performed. If you supported an existing private AKS cluster or App Service pipeline rather than creating it end to end, say so clearly and explain the parts you configured, operated, or troubleshot.
