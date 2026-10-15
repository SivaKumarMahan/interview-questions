# Practice Project 10: Deploy the Flask API to Azure Container Instances with GitHub Actions

> This guide shows how to run the Flask Docker image from Project 9 on Azure Container Instances (ACI), pull it from Azure Container Registry with a managed identity, and automate deploys from GitHub Actions using OIDC (no stored Azure passwords).

## Key Concepts

### What you will build

You will take the Flask API image from Project 9 and run it on Azure Container Instances. ACI runs a container in Azure without any VM or cluster for you to manage.

You will do it in two stages:

1. Manual: deploy the public Docker Hub image with `az container create` and get a public URL like `http://flask-<unique>.eastus.azurecontainer.io:8000/hello`.
2. Automated: on every push to `main`, GitHub Actions logs in to Azure with OIDC (OpenID Connect, a short-lived token, no client secret), builds the image, pushes it to Azure Container Registry (ACR), and updates the ACI container group. ACI pulls the image from ACR with a user-assigned managed identity, so no registry password is stored anywhere.

Final result: you push code, and about two minutes later `curl http://<fqdn>:8000/hello` shows the new version (the Git SHA).

### Architecture

```text
 git push (main)
      |
      v
 +---------------------------+   OIDC token (id-token: write)   +---------------------------+
 | GitHub Actions            | -------------------------------> | Microsoft Entra ID        |
 | 1. checkout               |   federated credential:          | App registration + SP     |
 | 2. azure/login@v2 (OIDC)  |   repo:<org>/<repo>:ref:         | role: Contributor on RG   |
 | 3. build + push to ACR    |   refs/heads/main                | role: AcrPush on ACR      |
 | 4. az container create    | <------------------------------- | (short-lived access token)|
 +---------------------------+                                  +---------------------------+
      |                    |
      | docker push        | az container create (ARM API)
      v                    v
 +---------------------+   pull with     +------------------------------------+
 | Azure Container     | <-------------- | Azure Container Instances          |
 | Registry (ACR)      |  managed        | container group: flask-aci         |
 | flask-api:<sha>     |  identity       | identity: id-flask-aci (AcrPull)   |
 +---------------------+  (AcrPull)      | public IP + DNS label, port 8000   |
                                         +------------------------------------+
                                                          ^
                                                          | HTTP :8000
                                                     End users / curl
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Azure Container Instances | Runs the Flask container with a public IP and DNS name | Fastest way to run a container in Azure; no VM or cluster |
| Azure Container Registry | Stores the private image | Private registry in Azure; works with managed identity and Entra ID RBAC |
| User-assigned managed identity | Lets ACI pull from ACR without a password | No secrets to store or rotate |
| Microsoft Entra ID app + federated credential | Lets GitHub Actions log in to Azure with OIDC | No long-lived client secret in GitHub |
| GitHub Actions | Builds, pushes, and deploys on every push | Built into GitHub; native OIDC support |
| `azure/login@v2` | Exchanges the GitHub OIDC token for an Azure token | Official action for Azure login |
| `docker/build-push-action@v6` | Builds and pushes the image with cache | Standard, fast, BuildKit based |
| Azure CLI (`az`) | Creates all resources and deploys ACI | Scriptable and preinstalled on GitHub runners |

### Prerequisites

- Completed Project 9 (Flask app with `app.py`, `requirements.txt`, `Dockerfile`, and an image on Docker Hub).
- An Azure subscription where you can create resources and role assignments (Owner, or Contributor plus User Access Administrator on the resource group). Creating an app registration in Entra ID also needs permission in your tenant.
- A GitHub repository with the Flask code.
- Local tools:

```bash
az --version          # Azure CLI 2.60+ recommended
az login
az account show --output table

# Optional: GitHub CLI to set secrets from the terminal
gh --version
gh auth login
```

Cost warning: ACI bills per second for the vCPU and memory of a running container group. A 1 vCPU / 1.5 GB container running all month costs tens of US dollars. ACR Basic tier has a small fixed daily charge. Delete everything when you finish (see Clean up), and check the Azure pricing page for current prices in your region.

### Folder structure

```text
flask-api/
├── .github/
│   └── workflows/
│       └── deploy-aci.yml     # build, push to ACR, deploy to ACI
├── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── infra/
    └── federated-credential.json   # used once during OIDC setup
```

### Step-by-step

#### Step 1: Set variables and create a resource group

Use shell variables so every command uses the same names. Some names must be globally unique (ACR name, DNS label).

```bash
LOCATION="eastus"
RG="<resource-group>"                    # for example rg-flask-aci-lab
ACR_NAME="<acrname>"                     # 5-50 lowercase letters/numbers, globally unique
ACI_NAME="flask-aci"
DNS_LABEL="flask-<unique-suffix>"        # unique within the region
IDENTITY_NAME="id-flask-aci"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Register the resource providers (one-time per subscription, safe to re-run)
az provider register --namespace Microsoft.ContainerInstance
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.ManagedIdentity

az group create --name "$RG" --location "$LOCATION"
```

What this does:

- Resource providers must be registered before you can create those resource types. New subscriptions often do not have `Microsoft.ContainerInstance` registered yet.
- Everything lives in one resource group, so cleanup is one command and the pipeline's permissions can be scoped to just this group.

#### Step 2: Quick manual deploy from Docker Hub

Before automating, prove the image runs on ACI. A public Docker Hub image needs no credentials.

```bash
az container create \
  --resource-group "$RG" \
  --name "$ACI_NAME" \
  --image docker.io/<your-dockerhub-username>/flask-api:1.0.0 \
  --os-type Linux \
  --cpu 1 \
  --memory 1.5 \
  --ports 8000 \
  --ip-address Public \
  --dns-name-label "$DNS_LABEL" \
  --restart-policy Always \
  --environment-variables APP_VERSION=1.0.0 GREETING_NAME=ACI
```

What this does:

- A "container group" is the ACI unit of deployment. It is like a Kubernetes pod: one or more containers that share an IP, network, and lifecycle. Here it has one container.
- `--image` uses the full registry path. Docker Hub images can be written as `<user>/flask-api:1.0.0` too, but the full form is clearer.
- `--os-type Linux` is the container OS. Newer Azure CLI versions may require this flag explicitly, so always pass it.
- `--cpu 1 --memory 1.5` reserves 1 vCPU and 1.5 GB RAM. You pay for what you reserve while it runs, not for what you use.
- `--ports 8000` opens the port Gunicorn listens on. ACI does not do port mapping, so the public port is the same as the container port.
- `--ip-address Public` and `--dns-name-label` give a public IP and a name like `flask-xyz.eastus.azurecontainer.io`. Use the DNS name, because the IP can change when the group restarts.
- `--restart-policy Always` restarts the container if it exits. Other values: `OnFailure` (for jobs that may fail) and `Never` (for run-once tasks).
- `--environment-variables` sets plain env vars. For secrets use `--secure-environment-variables`, which are hidden from `az container show` output.

Private Docker Hub repos need credentials (stored in the container group, so ACR with managed identity in Step 4 is preferred):

```bash
# Only if the Docker Hub repo is private
az container create ... \
  --registry-login-server index.docker.io \
  --registry-username <your-dockerhub-username> \
  --registry-password "<dockerhub-access-token>"
```

#### Step 3: Inspect, debug, and manage the container group

These are the commands you will use most when something goes wrong.

```bash
# State and URL
az container show -g "$RG" -n "$ACI_NAME" \
  --query "{state:instanceView.state, fqdn:ipAddress.fqdn, ip:ipAddress.ip, image:containers[0].image}" \
  -o table

# Container logs (stdout/stderr of Gunicorn)
az container logs -g "$RG" -n "$ACI_NAME"

# Stream live output and events (Ctrl+C to stop)
az container attach -g "$RG" -n "$ACI_NAME"

# Open a shell inside the running container
az container exec -g "$RG" -n "$ACI_NAME" --exec-command "/bin/bash"

# Events: image pull, start, restart, failures
az container show -g "$RG" -n "$ACI_NAME" --query "containers[0].instanceView.events" -o table

# Restart count and current state
az container show -g "$RG" -n "$ACI_NAME" \
  --query "containers[0].instanceView.{restarts:restartCount, current:currentState.state}" -o table

# Stop (stop billing, keep the definition), start again, restart
az container stop -g "$RG" -n "$ACI_NAME"
az container start -g "$RG" -n "$ACI_NAME"
az container restart -g "$RG" -n "$ACI_NAME"

# Delete the Docker Hub based group (we recreate it from ACR next)
az container delete -g "$RG" -n "$ACI_NAME" --yes
```

What this does:

- `az container logs` shows the container's stdout. Because the image sets `PYTHONUNBUFFERED=1`, Gunicorn and app logs show up here.
- `az container attach` streams startup events and output. Good for watching a pull or crash loop live.
- `az container exec` works like `docker exec`. It needs a shell in the image (the slim image has `bash`).
- `stop` deallocates the group so you stop paying for compute. The public IP may change after `start`, the DNS name does not.
- We delete the group because the next step changes how the image is pulled (identity settings are easier to set on a fresh group).

#### Step 4: Create ACR and a managed identity for pulls

Store the image in a private ACR and let ACI pull it with a user-assigned managed identity. No admin user and no password.

```bash
# Private registry, admin user disabled (the default)
az acr create \
  --resource-group "$RG" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled false

ACR_ID=$(az acr show -n "$ACR_NAME" --query id -o tsv)
ACR_LOGIN_SERVER=$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)   # <acrname>.azurecr.io

# User-assigned managed identity for the container group
az identity create --resource-group "$RG" --name "$IDENTITY_NAME"

IDENTITY_ID=$(az identity show -g "$RG" -n "$IDENTITY_NAME" --query id -o tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show -g "$RG" -n "$IDENTITY_NAME" --query principalId -o tsv)

# Allow the identity to pull images from this registry only
az role assignment create \
  --assignee-object-id "$IDENTITY_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope "$ACR_ID"
```

What this does:

- `--admin-enabled false` keeps the shared admin username and password off. Admin credentials are one shared secret with full push/pull rights, so avoid them.
- A user-assigned identity is a standalone Azure resource. It exists before the container group, so you can grant it `AcrPull` first. (A system-assigned identity is created with the group, which is too late for the first image pull.)
- `AcrPull` is the least-privilege role for pulling. The scope is just this registry.
- `--assignee-object-id` with `--assignee-principal-type` avoids a Graph lookup and works right after creating the identity.

Push the image to ACR once by hand and test the identity-based pull:

```bash
az acr login --name "$ACR_NAME"
docker tag <your-dockerhub-username>/flask-api:1.0.0 "$ACR_LOGIN_SERVER/flask-api:1.0.0"
docker push "$ACR_LOGIN_SERVER/flask-api:1.0.0"

# Or build in Azure without local Docker:
# az acr build --registry "$ACR_NAME" --image flask-api:1.0.0 .

az container create \
  --resource-group "$RG" \
  --name "$ACI_NAME" \
  --image "$ACR_LOGIN_SERVER/flask-api:1.0.0" \
  --acr-identity "$IDENTITY_ID" \
  --assign-identity "$IDENTITY_ID" \
  --os-type Linux \
  --cpu 1 \
  --memory 1.5 \
  --ports 8000 \
  --ip-address Public \
  --dns-name-label "$DNS_LABEL" \
  --restart-policy Always \
  --environment-variables APP_VERSION=1.0.0
```

What this does:

- `--assign-identity` attaches the user-assigned identity to the container group.
- `--acr-identity` tells ACI to use that identity when pulling from ACR, instead of a username and password.
- Role assignments can take a minute or two to take effect. If the pull fails with an authorization error, wait and retry.

#### Step 5: Set up OIDC for GitHub Actions (federated credential)

GitHub Actions will log in to Azure with OIDC. GitHub issues a signed token for each job, and Entra ID trusts it only if the subject matches your repo and branch. No client secret is stored.

```bash
GH_ORG="<your-github-org-or-username>"
GH_REPO="<your-repo-name>"

# 1) App registration
APP_ID=$(az ad app create --display-name "gh-${GH_REPO}-aci-deploy" --query appId -o tsv)

# 2) Service principal for the app (the identity that gets roles)
az ad sp create --id "$APP_ID"
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

# 3) Federated credential: trust only the main branch of this repo
mkdir -p infra
cat > infra/federated-credential.json <<EOF
{
  "name": "github-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:${GH_ORG}/${GH_REPO}:ref:refs/heads/main",
  "description": "GitHub Actions deploys from main",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

az ad app federated-credential create --id "$APP_ID" --parameters infra/federated-credential.json

# 4) Roles: Contributor on the resource group only, AcrPush on the registry
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}"

az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPush \
  --scope "$ACR_ID"

echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
```

What this does:

- `az ad app create` creates the app registration. Its `appId` is the client ID used by `azure/login`.
- `az ad sp create` creates the service principal in your tenant. Role assignments are given to the service principal.
- The federated credential's `subject` must match the token GitHub sends exactly. `repo:<org>/<repo>:ref:refs/heads/main` means "only workflows running on the main branch of this repo". A feature branch or a fork cannot get a token.
- `audiences` must be `api://AzureADTokenExchange`, which is what `azure/login` requests by default.
- `Contributor` is scoped to the resource group, not the subscription. The pipeline can manage ACI there but cannot touch anything else. Contributor also covers using the managed identity, because the identity lives in the same resource group.
- `AcrPush` lets the pipeline push images to this registry (it includes pull).

Important: if your job uses `environment: production`, GitHub sends the subject `repo:<org>/<repo>:environment:production` instead of the branch subject. Then you must create a federated credential with that subject. Pull requests use `repo:<org>/<repo>:pull_request`.

#### Step 6: Add GitHub secrets and variables

The three IDs are not passwords, but storing them as secrets keeps them out of logs. Names and settings go into variables.

| Name | Type | Value |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | Secret | `appId` of the app registration |
| `AZURE_TENANT_ID` | Secret | Your Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Secret | Your subscription ID |
| `AZURE_RESOURCE_GROUP` | Variable | `<resource-group>` |
| `ACR_NAME` | Variable | `<acrname>` |
| `ACI_DNS_LABEL` | Variable | `flask-<unique-suffix>` |

```bash
gh secret set AZURE_CLIENT_ID --body "$APP_ID"
gh secret set AZURE_TENANT_ID --body "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID"
gh variable set AZURE_RESOURCE_GROUP --body "$RG"
gh variable set ACR_NAME --body "$ACR_NAME"
gh variable set ACI_DNS_LABEL --body "$DNS_LABEL"
```

Notice there is no `AZURE_CLIENT_SECRET` and no registry password. That is the whole point of OIDC plus managed identity.

#### Step 7: Write the GitHub Actions workflow

`.github/workflows/deploy-aci.yml`:

```yaml
name: Deploy Flask to ACI

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write   # required to request the OIDC token
  contents: read    # required for actions/checkout

concurrency:
  group: aci-deploy
  cancel-in-progress: false

env:
  RESOURCE_GROUP: ${{ vars.AZURE_RESOURCE_GROUP }}
  ACR_NAME: ${{ vars.ACR_NAME }}
  DNS_LABEL: ${{ vars.ACI_DNS_LABEL }}
  ACI_NAME: flask-aci
  IMAGE_NAME: flask-api
  IDENTITY_NAME: id-flask-aci

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Log in to ACR
        run: az acr login --name "$ACR_NAME"

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push image to ACR
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to Azure Container Instances
        run: |
          IDENTITY_ID=$(az identity show -g "$RESOURCE_GROUP" -n "$IDENTITY_NAME" --query id -o tsv)

          az container create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$ACI_NAME" \
            --image "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${GITHUB_SHA}" \
            --acr-identity "$IDENTITY_ID" \
            --assign-identity "$IDENTITY_ID" \
            --os-type Linux \
            --cpu 1 \
            --memory 1.5 \
            --ports 8000 \
            --ip-address Public \
            --dns-name-label "$DNS_LABEL" \
            --restart-policy Always \
            --environment-variables APP_VERSION="$GITHUB_SHA" GREETING_NAME=ACI \
            --output none

      - name: Smoke test
        run: |
          FQDN=$(az container show -g "$RESOURCE_GROUP" -n "$ACI_NAME" --query ipAddress.fqdn -o tsv)
          echo "App URL: http://${FQDN}:8000/hello"
          for i in $(seq 1 20); do
            if curl -fsS "http://${FQDN}:8000/health"; then
              echo
              curl -fsS "http://${FQDN}:8000/hello"
              exit 0
            fi
            echo "Waiting for container... ($i)"
            sleep 6
          done
          echo "Health check failed. Recent logs:"
          az container logs -g "$RESOURCE_GROUP" -n "$ACI_NAME" || true
          exit 1

      - name: Azure logout
        if: always()
        run: |
          az logout || true
          az cache purge || true
          az account clear || true
```

What this does:

- `permissions: id-token: write` lets the job request a GitHub OIDC token. Without it, `azure/login` fails with an error about the ID token.
- `azure/login@v2` with `client-id`, `tenant-id`, and `subscription-id` (and no `client-secret`) uses OIDC automatically. The Azure token lasts about an hour, which is plenty for one job.
- `az acr login` uses the Azure login to get a short-lived ACR token and writes it to Docker's credential config, so the build step can push.
- The image is tagged with the full commit SHA (immutable, traceable) and `latest`. ACI deploys the SHA tag.
- `cache-from/cache-to: type=gha` reuses Docker layers between runs, so builds after the first are fast.
- `az container create` with the same name updates the existing group. Changing the image or environment variables restarts the container with the new settings. Some properties (such as OS type, and in some cases CPU or memory) cannot be changed in place; for those, delete the group first.
- The smoke test waits for `/health`, prints `/hello`, and fails the workflow with logs if the app never becomes healthy.
- The logout step clears cached credentials. It matters more on self-hosted runners.

Rollback: run the same `az container create` command with an older SHA tag. You can list tags with:

```bash
az acr repository show-tags --name "$ACR_NAME" --repository flask-api --orderby time_desc --output table
```

#### Step 8: Push and watch

```bash
git add .
git commit -m "Add ACI deploy workflow with OIDC"
git push origin main
```

Open the Actions tab. The `Azure login (OIDC)` step should say it logged in using OIDC, and the `Smoke test` step should print the `/hello` response.

#### Step 9: Choose ACI vs App Service vs AKS

ACI is great for some jobs and a poor fit for others. Interviewers often ask you to compare.

| Need | Azure Container Instances | Azure App Service (containers) | Azure Kubernetes Service |
| --- | --- | --- | --- |
| Best for | Single containers, batch jobs, CI agents, quick demos, burst work | Web apps and APIs with HTTPS, custom domains, slots | Many microservices, complex networking, platform teams |
| Autoscaling | No | Yes (scale out rules, automatic scaling) | Yes (HPA, cluster autoscaler, KEDA) |
| HTTPS and custom domain | Not built in (add a sidecar proxy or Application Gateway) | Built in, managed certificates | Ingress controller plus cert-manager |
| Zero-downtime deploys | No (container restarts) | Yes, deployment slots with swap | Yes, rolling updates |
| Billing | Per second of vCPU and memory while running | Per App Service plan (always on) | Per node VM (plus optional paid tiers) |
| Ops effort | Very low | Low | High |
| Start-up | Seconds to about a minute | Minutes for a plan, fast after | Minutes for a cluster |

Also consider Azure Container Apps: serverless containers with autoscaling (including scale to zero), revisions, HTTPS ingress, and Dapr/KEDA built in. For a web API that needs autoscaling but not full Kubernetes, Container Apps is often the better choice than ACI.

Simple rule of thumb:

- Run-to-completion task or a quick single container: ACI.
- A standard web app or API: App Service or Container Apps.
- Many services and you need Kubernetes features: AKS.

#### Step 10: Know the ACI limitations

- No autoscaling. One container group is a fixed size. To scale, you create more groups yourself and put a load balancer in front.
- No built-in load balancer across groups and no zero-downtime update. An update restarts the container, so there is a short outage.
- No HTTPS on the public endpoint out of the box. Use a sidecar (for example Caddy) in the same group, or put Application Gateway in front.
- Public IP can change after stop/start or some updates. Always use the DNS label FQDN.
- Restart policy is per group: `Always`, `OnFailure`, or `Never`. A web server should use `Always`.
- Cost is per second for reserved vCPU and memory, so a 24/7 container can cost more than a small App Service plan. ACI is cheapest for short or bursty workloads.
- Resource limits per container group and per region (vCPU, memory, GPU availability) apply. Check the ACI quotas page.
- Storage: you can mount Azure Files for persistence, but there is no local persistent disk. Container filesystem changes are lost on restart.
- Private networking (VNet injection) is supported, but some features (like public DNS labels) do not apply inside a VNet.

### Verify it works

```bash
FQDN=$(az container show -g "$RG" -n "$ACI_NAME" --query ipAddress.fqdn -o tsv)
echo "$FQDN"
curl -s "http://${FQDN}:8000/hello"
```

Expected output (version is the Git SHA from the last deploy):

```json
{"hostname":"<container-hostname>","message":"Hello, ACI!","version":"3f2a9c1e8b7d..."}
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://${FQDN}:8000/health"
```

Expected output:

```text
200
```

```bash
az container show -g "$RG" -n "$ACI_NAME" \
  --query "{state:instanceView.state, image:containers[0].image, identity:identity.type}" -o table
```

Expected output:

```text
State    Image                                         Identity
-------  --------------------------------------------  ------------
Running  <acrname>.azurecr.io/flask-api:3f2a9c1e8b7d...  UserAssigned
```

Check that no secrets are used for the registry:

```bash
az container show -g "$RG" -n "$ACI_NAME" --query "imageRegistryCredentials" -o json
```

Expected output shows the ACR server with an `identity` field and no username or password.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `The subscription is not registered to use namespace 'Microsoft.ContainerInstance'` | Provider not registered | `az provider register --namespace Microsoft.ContainerInstance` and wait until `Registered` |
| `azure/login`: `AADSTS70021: No matching federated identity record found` | Federated credential subject does not match the token | Check `repo:<org>/<repo>:ref:refs/heads/main`; if the job uses `environment:`, add a credential with the environment subject |
| `azure/login` error about missing ID token or `ACTIONS_ID_TOKEN_REQUEST_URL` | Missing `permissions: id-token: write` | Add the `permissions` block at workflow or job level |
| `AuthorizationFailed` on `az container create` | Service principal lacks a role on the RG | Assign `Contributor` scoped to the resource group; wait 1-2 minutes |
| ACI state `Waiting` with event `Failed to pull image` / unauthorized | Identity missing `AcrPull`, or `--acr-identity` not set | Assign `AcrPull` on the ACR to the managed identity; pass both `--assign-identity` and `--acr-identity` |
| `unauthorized: authentication required` on push in the workflow | Pipeline identity cannot push | Assign `AcrPush` to the service principal on the ACR; run `az acr login` before the build |
| `DNS name label ... is not available` | Label already used in the region | Pick a more unique `--dns-name-label` |
| Container keeps restarting (`restartCount` grows) | App crashes at start, or wrong command | `az container logs` and `az container attach`; check the image runs locally with `docker run` |
| `curl` times out but state is `Running` | Wrong port in `--ports`, or app bound to `127.0.0.1` | Match `--ports` to the Gunicorn port; bind Gunicorn to `0.0.0.0` |
| Update fails: property cannot be updated | Changing a property that ACI cannot update in place | `az container delete` then `az container create` |
| `exec format error` in logs | Image built for ARM | Build with `--platform linux/amd64` (GitHub runners are amd64 by default) |

### Clean up

```bash
# Deletes ACI, ACR, and the managed identity
az group delete --name "$RG" --yes --no-wait

# Delete the app registration (also removes its service principal and federated credentials)
az ad app delete --id "$APP_ID"

# Confirm
az group exists --name "$RG"
```

Also remove the GitHub secrets and variables, or disable the workflow, so the next push does not fail trying to deploy to resources that no longer exist.

Role assignments scoped to the deleted resource group are removed with it.

### Next improvements

- Add HTTPS: run a Caddy sidecar container in the same group (deploy with YAML: `az container create --file aci.yaml`), or put Application Gateway in front.
- Move to Azure Container Apps for autoscaling, revisions, traffic splitting, and built-in HTTPS.
- Define the infrastructure (ACR, identity, ACI, role assignments) in Bicep or Terraform and deploy it from the pipeline.
- Read secrets from Azure Key Vault and pass them with `--secure-environment-variables`, or let the app read Key Vault with its managed identity.
- Send logs to a Log Analytics workspace (`--log-analytics-workspace`) and add an alert on restarts.
- Add a test job and an image scan (Trivy or Microsoft Defender for Containers) before deploy.
- Add a manual approval with a GitHub Environment (and a matching federated credential subject).
- Use ACR Tasks or a retention policy to clean up old image tags.

### How to explain this project in an interview

> "As a hands-on lab, I deployed a containerized Flask API to Azure Container Instances and automated it with GitHub Actions. First I deployed the Docker Hub image manually with az container create to understand the options: CPU and memory, ports, DNS label, and restart policy. Then I moved the image to a private Azure Container Registry with the admin user disabled, and gave the container group a user-assigned managed identity with only AcrPull, so ACI pulls without any password. For the pipeline, I set up OIDC: an Entra ID app registration with a federated credential that only trusts the main branch of my repo, and a service principal with Contributor scoped to just the resource group plus AcrPush on the registry. The workflow logs in with azure/login, builds and pushes a SHA-tagged image, updates the container group, and runs a health check. I also compared ACI with App Service, Container Apps, and AKS, since ACI has no autoscaling or zero-downtime deploys."

Points that impress interviewers:

- There are zero long-lived secrets: OIDC for the pipeline and managed identity for image pulls.
- You know the federated credential subject format and how it changes for environments and pull requests.
- Roles follow least privilege: RG-scoped Contributor, registry-scoped AcrPush and AcrPull.
- You can explain clearly when ACI is the wrong tool and what to pick instead.

## Interview Questions

<details><summary>Q1. [Basic] What is Azure Container Instances, and what is a container group?</summary>

**Answer:**

Azure Container Instances (ACI) is a serverless way to run containers in Azure. You give it an image, CPU, memory, and ports, and it runs the container in seconds. You do not manage VMs, an OS, or a cluster.

A container group is the deployment unit in ACI. It holds one or more containers that are scheduled on the same host and share:

- One IP address and DNS label.
- Port space (containers in the group talk over `localhost`).
- Lifecycle and restart policy.
- Optional volumes (for example Azure Files).

It is similar to a Kubernetes pod. Multi-container groups are useful for sidecars like a TLS proxy or log shipper.

</details>

<details><summary>Q2. [Basic] What are the ACI restart policies and when do you use each?</summary>

**Answer:**

- `Always` (default): restart the container whenever it exits. Use for long-running services like a web API.
- `OnFailure`: restart only if the process exits with a non-zero code. Use for batch jobs that should retry on error but stop when done.
- `Never`: run once and stop. Use for one-off tasks, for example a database migration or a report job.

With `OnFailure` or `Never`, billing stops when the container group stops, which makes ACI good for jobs.

</details>

<details><summary>Q3. [Intermediate] How does GitHub Actions log in to Azure with OIDC, and why is it better than a client secret?</summary>

**Answer:**

Flow:

1. The workflow has `permissions: id-token: write`, so the job can request a signed JWT from GitHub's OIDC provider (`https://token.actions.githubusercontent.com`).
2. The token contains claims such as the repo, branch, and environment. The `sub` claim looks like `repo:<org>/<repo>:ref:refs/heads/main`.
3. `azure/login@v2` sends this token to Microsoft Entra ID.
4. Entra ID checks it against the federated credential on the app registration: issuer, subject, and audience (`api://AzureADTokenExchange`) must match.
5. Entra ID returns a short-lived Azure access token. The job uses it for `az` commands.

Why it is better:

- No long-lived secret is stored in GitHub, so nothing to leak or rotate.
- Trust is limited to a specific repo and branch (or environment).
- Tokens expire quickly.

</details>

<details><summary>Q4. [Intermediate] Your workflow fails at <code>azure/login</code> with "No matching federated identity record found". How do you fix it? <em>(scenario)</em></summary>

**Answer:**

The subject in GitHub's token does not match any federated credential on the app.

Check:

1. List the credentials: `az ad app federated-credential list --id <app-id> -o table` and look at `subject`.
2. Compare with what the workflow sends:
   - Push to main: `repo:<org>/<repo>:ref:refs/heads/main`
   - Job with `environment: production`: `repo:<org>/<repo>:environment:production`
   - Pull request: `repo:<org>/<repo>:pull_request`
   - Tag: `repo:<org>/<repo>:ref:refs/tags/<tag>`
3. Check spelling and case of org and repo, and that the repo was not renamed or transferred.
4. Check `issuer` is `https://token.actions.githubusercontent.com` and audience is `api://AzureADTokenExchange`.

Fix: add a federated credential with the correct subject. Each app can have several credentials, for example one for main and one for the production environment.

</details>

<details><summary>Q5. [Intermediate] Why use a user-assigned managed identity for pulling from ACR instead of the ACR admin user?</summary>

**Answer:**

ACR admin user problems:

- It is one shared username and password with full push and pull rights.
- The password is stored in the container group definition and must be rotated by hand.
- No per-workload auditing.

User-assigned managed identity benefits:

- No password at all. Azure handles tokens.
- Least privilege: grant only `AcrPull` on one registry.
- You can create it and assign the role before the container group exists, so the first pull works. A system-assigned identity is created together with the group, which is too late for the first pull.
- Can be reused by several container groups and audited in Entra ID sign-in logs.

In ACI you use it with `--assign-identity <identity-id> --acr-identity <identity-id>`.

</details>

<details><summary>Q6. [Intermediate] The ACI container group stays in <code>Waiting</code> and never starts. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

1. Look at events: `az container show -g <rg> -n <name> --query "containers[0].instanceView.events" -o table`. Most issues show here.
2. Image pull errors:
   - `unauthorized` or `failed to pull`: the identity lacks `AcrPull`, `--acr-identity` is missing, or the image name or tag is wrong. Check with `az acr repository show-tags`.
   - Docker Hub `toomanyrequests`: rate limits. Use ACR.
3. Crash loop: `az container logs` and `az container attach`. The process may exit at startup, for example a missing env var or wrong `CMD`.
4. Wrong platform: `exec format error` means an ARM image on amd64.
5. Capacity: rarely the region has no capacity for the requested size. Try a smaller size or another region.

Reproduce locally with `docker run` on the same image tag to separate app problems from platform problems.

</details>

<details><summary>Q7. [Intermediate] Why scope the pipeline's Contributor role to the resource group and not the subscription?</summary>

**Answer:**

Least privilege. The pipeline only needs to manage resources in this one resource group. If the GitHub repo, a workflow, or a third-party action is compromised, the attacker gets only what the identity can do.

- Subscription-scoped Contributor could create or delete anything in the subscription, including other teams' resources.
- Resource group scope limits the blast radius to this project.

Even tighter options: a custom role with only `Microsoft.ContainerInstance/*` and the identity assign action, plus `AcrPush` on just the registry. Contributor also cannot assign roles, which is good: the pipeline cannot give itself more rights.

</details>

<details><summary>Q8. [Advanced] Your team wants this API to autoscale and have zero-downtime deploys. Would you stay on ACI? <em>(scenario)</em></summary>

**Answer:**

No. ACI has no autoscaling and updates restart the container, so there is downtime. You would have to build scaling and load balancing yourself with several container groups and Application Gateway, which is a lot of work.

Better options:

- Azure Container Apps: HTTP-based autoscaling (including scale to zero), revisions with traffic splitting for blue-green or canary, built-in HTTPS ingress, managed identity pulls from ACR. Closest to "ACI plus scaling".
- App Service for Containers: deployment slots with swap, autoscale rules, managed certificates. Good for classic web apps.
- AKS: if you have many services or need Kubernetes features and have the skills to operate it.

The pipeline changes little: OIDC login, build and push to ACR stay the same; only the deploy command changes (for example `az containerapp update --image ...`).

</details>

<details><summary>Q9. [Advanced] How would you add HTTPS to the ACI deployment?</summary>

**Answer:**

ACI does not provide TLS on its public endpoint. Options:

1. Sidecar reverse proxy in the same container group: run Caddy (automatic Let's Encrypt certificates) or Nginx alongside the Flask container. Caddy listens on 80/443 and forwards to `localhost:8000`. Expose only 80 and 443. Multi-container groups are defined in a YAML file and deployed with `az container create --file aci.yaml`. Use an Azure Files volume to keep certificates across restarts.
2. Application Gateway (or Front Door) in front: terminate TLS there with a Key Vault certificate, and route to the ACI group (often deployed into a VNet with a private IP). Adds WAF too.
3. Move to Container Apps or App Service, which include managed HTTPS.

For anything beyond a lab, option 2 or 3 is cleaner than managing certificates yourself.

</details>

<details><summary>Q10. [Advanced] How do you pass secrets to an ACI container securely?</summary>

**Answer:**

Options from simple to best:

- `--secure-environment-variables KEY=value`: the values are not shown in `az container show` or the portal. But the value still has to come from somewhere, such as a pipeline secret.
- Secret volumes: mount secrets as files in the container (YAML deployment with a `secret` volume). They are stored on tmpfs, not disk.
- Azure Key Vault with managed identity: the app uses the container group's managed identity to read secrets from Key Vault at runtime (for example with the Azure SDK `DefaultAzureCredential`). No secret is in the pipeline or the container definition, and you can rotate centrally.

Never put secrets in the image, in plain `--environment-variables`, or in the workflow file.

</details>
