# Practice Project 5: Deploy a Containerized App to Azure Web App for Containers with GitHub Actions

> This guide shows how to run a container on Azure App Service (Linux), pull it from ACR with a managed identity, deploy it from GitHub Actions using OIDC, and add staging slots, autoscale, health checks and log streaming.

## Key Concepts

### What you will build

- A small Python (Flask + Gunicorn) web app packaged as a Docker image.
- An **Azure Container Registry (ACR)** with the admin user disabled.
- A **Linux App Service Plan** and a **Web App for Containers** that pulls the image from ACR using its **system-assigned managed identity** (no registry password).
- A **GitHub Actions** workflow that logs in to Azure with **OIDC**, builds and pushes the image to ACR, deploys it to a **staging slot**, smoke-tests it and **swaps** it into production.
- A **health check path**, **autoscale rules** on the plan, and **container log streaming**.

Final result: every push to `main` produces a new image tagged with the commit SHA. You open `https://<app-name>.azurewebsites.net` and see `{"message": "Hello from Web App for Containers", "version": "<sha>"}` with zero downtime between versions.

### Architecture

```text
 Developer --push--> GitHub repo (main)
                        |
                        v
                GitHub Actions workflow
                  1. azure/login@v2 (OIDC, no secret)
                  2. docker build + push  ------------->  ACR  (<acr>.azurecr.io/webapp:<sha>)
                  3. azure/webapps-deploy@v3 (slot: staging)        ^
                  4. curl staging /health                           | AcrPull (managed identity)
                  5. az webapp deployment slot swap                 |
                        |                                           |
                        v                                           |
   +---------------- App Service Plan (Linux, P0v3) ----------------+------+
   |   Web App  <app-name>                                                 |
   |     production slot  <---- swap ---->  staging slot                   |
   |     WEBSITES_PORT=8080, health check /health                          |
   |   Autoscale: CPU > 70% -> +1 instance, CPU < 30% -> -1 (min 1, max 3) |
   +-----------------------------------------------------------------------+
                        |
                        v
             Log stream (az webapp log tail) / Log Analytics (optional)
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Docker | Packages the app and its runtime into an image | Same image runs locally and in Azure |
| Azure Container Registry | Stores private images | Azure-native, supports managed identity pull and webhooks |
| App Service Plan (Linux) | Provides the compute (VMs) for the web app | You pay per plan, not per app; plan tier decides slots and autoscale |
| Web App for Containers | Runs the container with HTTPS, custom domains, slots | PaaS: no cluster to manage, unlike AKS |
| Managed identity | Lets the web app pull from ACR | No registry password stored in app settings |
| GitHub Actions | CI/CD pipeline | Lives next to the code; OIDC to Azure is built in |
| azure/login@v2 | Logs in to Azure with a federated token | No long-lived secrets in GitHub |
| azure/webapps-deploy@v3 | Points the web app (or slot) at the new image | Official action, supports `images:` and `slot-name:` |
| Azure Monitor autoscale | Adds and removes instances | Handles load spikes without manual work |

### Prerequisites

- Azure subscription with rights to create resources and role assignments (Owner, or Contributor + Role Based Access Control Administrator on the resource group).
- GitHub account and a new repository, for example `<owner>/webapp-containers`.
- Local tools:

```bash
# Azure CLI 2.60+ (older versions use different container flag names)
az version
az upgrade

# Docker Engine or Docker Desktop
docker --version

# Optional: GitHub CLI for setting secrets/variables
gh --version
```

- Cost warning: **P0v3** costs more than Basic but is needed for deployment slots and autoscale (Standard tier and above support both; Basic does not). Expect roughly a few dollars per day. ACR Basic adds a small daily charge. Delete everything when done.

### Folder structure

```text
webapp-containers/
|-- .github/
|   `-- workflows/
|       `-- deploy.yml
|-- app/
|   |-- app.py
|   `-- requirements.txt
|-- Dockerfile
|-- .dockerignore
`-- README.md
```

### Step-by-step

#### Step 1: Write the app

A tiny Flask app with a root endpoint and a `/health` endpoint. The version comes from an environment variable so you can see which image is live.

`app/app.py`:

```python
import os
from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        message="Hello from Web App for Containers",
        version=os.getenv("APP_VERSION", "local"),
        environment=os.getenv("APP_ENV", "unknown"),
    )


@app.get("/health")
def health():
    return jsonify(status="ok"), 200
```

`app/requirements.txt`:

```text
flask==3.0.3
gunicorn==23.0.0
```

What this does:

- `/` returns JSON with the version, so after a swap you can confirm which build is serving traffic.
- `/health` is a cheap endpoint for App Service health checks and the pipeline smoke test.
- `APP_ENV` will be a **slot-specific** setting (staging vs production).

#### Step 2: Write the Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

ARG APP_VERSION=local
ENV APP_VERSION=${APP_VERSION}

RUN useradd --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "app:app"]
```

`.dockerignore`:

```text
.git
.github
__pycache__
*.pyc
.venv
```

What this does:

- Copying `requirements.txt` first lets Docker cache the `pip install` layer when only code changes.
- The app runs as a non-root user.
- It listens on **8080**, not 80, so you must tell App Service with `WEBSITES_PORT=8080`.
- `PYTHONUNBUFFERED=1` and `--access-logfile -` send logs to stdout, which App Service captures.

Test locally:

```bash
docker build -t webapp:local --build-arg APP_VERSION=local .
docker run --rm -p 8080:8080 webapp:local
# In another terminal:
curl -s http://localhost:8080/
curl -s http://localhost:8080/health
```

#### Step 3: Set variables and create the resource group and ACR

```bash
LOCATION=eastus
RG=rg-webapp-containers
ACR=acrwebappcont$RANDOM          # must be globally unique, alphanumeric
PLAN=plan-webapp-containers
APP=app-webapp-cont-$RANDOM       # must be globally unique
echo "ACR=$ACR APP=$APP"          # write these down

az group create --name $RG --location $LOCATION

az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled false

# Push a first image so the web app has something to run
az acr build --registry $ACR --image webapp:v1 --build-arg APP_VERSION=v1 .
```

What this does:

- `--admin-enabled false` keeps the shared admin password off. You will use managed identity instead.
- `az acr build` builds in Azure and pushes `webapp:v1`, so you do not need to `docker push` from your laptop.

#### Step 4: Create the App Service Plan

```bash
az appservice plan create \
  --resource-group $RG \
  --name $PLAN \
  --is-linux \
  --sku P0V3 \
  --number-of-workers 1
```

What this does:

- `--is-linux` is required for Linux containers. A plan is either Linux or Windows.
- **B1** works for a basic test (cheapest), but has no slots and no autoscale. **P0v3** supports slots, autoscale, and gives better price/performance than Standard.
- All apps in the plan share its instances. Scaling the plan scales every app in it.

#### Step 5: Create the Web App with a container image

Create the app with a public image first. The ACR image cannot be pulled yet because the app has no identity and no role.

```bash
az webapp create \
  --resource-group $RG \
  --plan $PLAN \
  --name $APP \
  --container-image-name mcr.microsoft.com/appsvc/staticsite:latest \
  --https-only true
```

What this does:

- `--container-image-name` is the current flag. Older CLI versions and many blog posts use `--deployment-container-image-name` (deprecated, still accepted for now with a warning).
- `--https-only true` redirects HTTP to HTTPS.
- Under the hood this sets `linuxFxVersion` to `DOCKER|<image>`.

#### Step 6: Let the web app pull from ACR with its managed identity

```bash
# 1. Turn on the system-assigned identity and capture its principal ID
PRINCIPAL_ID=$(az webapp identity assign --resource-group $RG --name $APP --query principalId -o tsv)

# 2. Give that identity AcrPull on the registry
ACR_ID=$(az acr show --name $ACR --query id -o tsv)
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope $ACR_ID

# 3. Tell App Service to use the managed identity for registry auth
az webapp config set --resource-group $RG --name $APP \
  --generic-configurations '{"acrUseManagedIdentityCreds": true}'

# 4. Point the app at the ACR image
az webapp config container set \
  --resource-group $RG \
  --name $APP \
  --container-image-name $ACR.azurecr.io/webapp:v1 \
  --container-registry-url https://$ACR.azurecr.io
```

What this does:

- `identity assign` creates a service principal tied to the web app's lifecycle.
- **AcrPull** is the least-privilege role for pulling images.
- `acrUseManagedIdentityCreds: true` is the switch that makes App Service use the identity instead of a username/password. Without it, pulls fail with 401.
- If you use a **user-assigned** identity instead, also set `{"acrUserManagedIdentityID": "<client-id>"}`.
- `az webapp config container set` flags were renamed in newer CLI versions: `--container-image-name` (old: `--docker-custom-image-name`), `--container-registry-url` (old: `--docker-registry-server-url`), `--container-registry-user` / `--container-registry-password` (old: `--docker-registry-server-user` / `--docker-registry-server-password`). Do not pass user/password when using managed identity.

#### Step 7: Configure app settings, port and health check

```bash
az webapp config appsettings set --resource-group $RG --name $APP --settings \
  WEBSITES_PORT=8080 \
  WEBSITES_ENABLE_APP_SERVICE_STORAGE=false \
  APP_VERSION=v1

# Slot-specific ("sticky") setting: stays with the slot during a swap
az webapp config appsettings set --resource-group $RG --name $APP \
  --slot-settings APP_ENV=production

# Health check: App Service pings this path on each instance
az webapp config set --resource-group $RG --name $APP \
  --generic-configurations '{"healthCheckPath": "/health"}'

# Keep the container warm
az webapp config set --resource-group $RG --name $APP --always-on true
```

What this does:

- `WEBSITES_PORT=8080` tells the App Service front end which container port to route to. Without it, App Service tries port 80 (or guesses from `EXPOSE`) and the site fails to start.
- `WEBSITES_ENABLE_APP_SERVICE_STORAGE=false` means `/home` is not mounted as shared persistent storage. Our app is stateless, so this avoids slow file I/O.
- App settings are injected as **environment variables** into the container.
- `--slot-settings` marks a setting as sticky to the slot. Normal `--settings` move with the code during a swap.
- With a health check path set, App Service removes an unhealthy instance from the load balancer after repeated failures (and replaces it after about an hour of failing). It only makes sense with 2+ instances.

#### Step 8: Turn on container logging and stream logs

```bash
az webapp log config --resource-group $RG --name $APP \
  --docker-container-logging filesystem

az webapp log tail --resource-group $RG --name $APP
```

What this does:

- `--docker-container-logging filesystem` saves container stdout/stderr to the App Service file system (kept for a short time and limited in size).
- `az webapp log tail` streams logs live. You should see Gunicorn startup lines and access logs. Press Ctrl+C to stop.
- For long-term logs, add a **Diagnostic setting** that sends `AppServiceConsoleLogs` and `AppServiceHTTPLogs` to a Log Analytics workspace.

Example Log Analytics query once diagnostics are on:

```kusto
AppServiceConsoleLogs
| where TimeGenerated > ago(30m)
| project TimeGenerated, ResultDescription
| order by TimeGenerated desc
```

#### Step 9: Create the staging slot

```bash
az webapp deployment slot create \
  --resource-group $RG \
  --name $APP \
  --slot staging \
  --configuration-source $APP

# The slot is a separate app with its OWN identity. Repeat the identity setup.
SLOT_PRINCIPAL_ID=$(az webapp identity assign --resource-group $RG --name $APP --slot staging \
  --query principalId -o tsv)

az role assignment create \
  --assignee-object-id $SLOT_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope $ACR_ID

az webapp config set --resource-group $RG --name $APP --slot staging \
  --generic-configurations '{"acrUseManagedIdentityCreds": true}'

# Sticky setting for the staging slot
az webapp config appsettings set --resource-group $RG --name $APP --slot staging \
  --slot-settings APP_ENV=staging

# Get the staging hostname
az webapp show --resource-group $RG --name $APP --slot staging --query defaultHostName -o tsv
```

What this does:

- `--configuration-source $APP` copies app settings and container config from production to the new slot.
- A slot has its own hostname (classic format `<app>-staging.azurewebsites.net`; apps created with unique default hostnames get a longer name, so always read `defaultHostName`).
- Slots get **separate system-assigned identities**. Forgetting AcrPull on the slot identity is the most common slot pull failure.
- During a swap, App Service first applies the target slot's sticky settings to the source slot and warms it up, then switches routing. Users get no downtime.

#### Step 10: Set up OIDC from GitHub to Azure

Use a user-assigned managed identity as the GitHub deploy identity, with a federated credential for your repo's `main` branch.

```bash
GH_OWNER=<owner>
GH_REPO=webapp-containers

az identity create --resource-group $RG --name id-github-webapp
GH_CLIENT_ID=$(az identity show -g $RG -n id-github-webapp --query clientId -o tsv)
GH_PRINCIPAL_ID=$(az identity show -g $RG -n id-github-webapp --query principalId -o tsv)

az identity federated-credential create \
  --resource-group $RG \
  --identity-name id-github-webapp \
  --name github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:$GH_OWNER/$GH_REPO:ref:refs/heads/main \
  --audiences api://AzureADTokenExchange

# Least privilege: push images and manage only this web app
az role assignment create --assignee-object-id $GH_PRINCIPAL_ID --assignee-principal-type ServicePrincipal \
  --role AcrPush --scope $ACR_ID

APP_ID=$(az webapp show -g $RG -n $APP --query id -o tsv)
az role assignment create --assignee-object-id $GH_PRINCIPAL_ID --assignee-principal-type ServicePrincipal \
  --role "Website Contributor" --scope $APP_ID

# Store identifiers in GitHub (these are IDs, not secrets, but keep them as secrets or variables)
gh secret set AZURE_CLIENT_ID --body "$GH_CLIENT_ID" --repo $GH_OWNER/$GH_REPO
gh secret set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)" --repo $GH_OWNER/$GH_REPO
gh secret set AZURE_SUBSCRIPTION_ID --body "$(az account show --query id -o tsv)" --repo $GH_OWNER/$GH_REPO
gh variable set ACR_NAME --body "$ACR" --repo $GH_OWNER/$GH_REPO
gh variable set WEBAPP_NAME --body "$APP" --repo $GH_OWNER/$GH_REPO
gh variable set RESOURCE_GROUP --body "$RG" --repo $GH_OWNER/$GH_REPO
```

What this does:

- The federated credential trusts tokens from GitHub only when the subject is exactly `repo:<owner>/<repo>:ref:refs/heads/main`. A fork or another branch cannot log in.
- If your job uses a GitHub **environment** (for example `environment: production`), the subject becomes `repo:<owner>/<repo>:environment:production`. Create a matching credential.
- **AcrPush** lets the workflow push images. **Website Contributor** on the app lets it change container config and swap slots (slots are child resources, so they inherit it).
- No client secret is created anywhere.

#### Step 11: Write the GitHub Actions workflow

`.github/workflows/deploy.yml`:

```yaml
name: build-and-deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write   # needed for OIDC
  contents: read

env:
  IMAGE_NAME: webapp

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Build and push image to ACR
        run: |
          az acr login --name ${{ vars.ACR_NAME }}
          IMAGE=${{ vars.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker build --build-arg APP_VERSION=${{ github.sha }} -t "$IMAGE" .
          docker push "$IMAGE"

      - name: Deploy to staging slot
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ vars.WEBAPP_NAME }}
          slot-name: staging
          images: ${{ vars.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Smoke test staging
        run: |
          HOST=$(az webapp show -g ${{ vars.RESOURCE_GROUP }} -n ${{ vars.WEBAPP_NAME }} \
                 --slot staging --query defaultHostName -o tsv)
          for i in $(seq 1 30); do
            BODY=$(curl -fsS "https://$HOST/" || true)
            if echo "$BODY" | grep -q "${{ github.sha }}"; then
              echo "Staging is serving the new version"; exit 0
            fi
            echo "Waiting for staging ($i/30)..."; sleep 10
          done
          echo "Staging never served the new version"; exit 1

      - name: Swap staging into production
        run: |
          az webapp deployment slot swap \
            --resource-group ${{ vars.RESOURCE_GROUP }} \
            --name ${{ vars.WEBAPP_NAME }} \
            --slot staging \
            --target-slot production

      - name: Azure logout
        if: always()
        run: az logout
```

What this does:

- `permissions: id-token: write` lets the job request an OIDC token from GitHub. Without it, `azure/login` fails.
- `azure/login@v2` with `client-id`, `tenant-id`, `subscription-id` and no `client-secret` uses OIDC.
- `az acr login` gets a short-lived ACR token from your Azure login, so `docker push` works with no registry password.
- The image tag is the commit SHA. Never deploy `latest` in a pipeline: you cannot tell what is running, and rollback is unclear.
- `azure/webapps-deploy@v3` with `images:` updates the container config of the **staging** slot only.
- The smoke test waits until staging returns the new SHA, so you never swap an old or broken build.
- The swap warms up staging with production's sticky settings, then switches traffic. To roll back, swap again.

Alternative: build in ACR instead of on the runner:

```yaml
      - name: Build in ACR
        run: |
          az acr build --registry ${{ vars.ACR_NAME }} \
            --image ${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --build-arg APP_VERSION=${{ github.sha }} .
```

#### Step 12: Push and watch the first run

```bash
git init -b main
git add .
git commit -m "Web App for Containers with GitHub Actions"
git remote add origin https://github.com/<owner>/webapp-containers.git
git push -u origin main

gh run watch --repo <owner>/webapp-containers
```

#### Step 13: Add autoscale rules

Autoscale belongs to the **App Service Plan**, not the web app.

```bash
PLAN_ID=$(az appservice plan show -g $RG -n $PLAN --query id -o tsv)

az monitor autoscale create \
  --resource-group $RG \
  --resource $PLAN_ID \
  --name autoscale-webapp \
  --min-count 1 \
  --max-count 3 \
  --count 1

# Scale out: +1 instance when average CPU > 70% over 5 minutes
az monitor autoscale rule create \
  --resource-group $RG \
  --autoscale-name autoscale-webapp \
  --condition "CpuPercentage > 70 avg 5m" \
  --scale out 1 \
  --cooldown 5

# Scale in: -1 instance when average CPU < 30% over 10 minutes
az monitor autoscale rule create \
  --resource-group $RG \
  --autoscale-name autoscale-webapp \
  --condition "CpuPercentage < 30 avg 10m" \
  --scale in 1 \
  --cooldown 10

az monitor autoscale show -g $RG -n autoscale-webapp --query "{min:profiles[0].capacity.minimum,max:profiles[0].capacity.maximum,rules:length(profiles[0].rules)}"
```

What this does:

- `--resource $PLAN_ID` passes the full resource ID, so you do not need `--resource-type`.
- `CpuPercentage` is the plan-level CPU metric. `MemoryPercentage` and `HttpQueueLength` are other common choices.
- Always pair a scale-out rule with a scale-in rule, and make the scale-in threshold clearly lower to avoid "flapping" (scaling out and in repeatedly).
- `--cooldown` (minutes) waits after a scale action before evaluating again.
- Newer Premium v3 plans also support **automatic scaling** (platform-managed, HTTP-based) as an alternative to rule-based autoscale.

#### Step 14 (alternative): Continuous deployment with an ACR webhook

If you do not want GitHub to call Azure, App Service can redeploy itself when a tag is pushed to ACR.

```bash
# Enable CD on the web app and get its webhook URL
CI_CD_URL=$(az webapp deployment container config --enable-cd true \
  --resource-group $RG --name $APP --query CI_CD_URL -o tsv)

# Create an ACR webhook that calls it on push of webapp:latest
az acr webhook create \
  --registry $ACR \
  --name webappcd \
  --actions push \
  --scope webapp:latest \
  --uri "$CI_CD_URL"
```

What this does:

- When `webapp:latest` is pushed, ACR calls the App Service SCM endpoint, which pulls the image and restarts the app.
- Trade-offs: it relies on a mutable `latest` tag, there is no smoke test or swap step, and the webhook URL contains deployment credentials (basic auth for SCM must be enabled). The GitHub Actions flow above is more controlled; the webhook is fine for simple dev environments.

### Verify it works

```bash
HOST=$(az webapp show -g $RG -n $APP --query defaultHostName -o tsv)

curl -s https://$HOST/
# Expected: {"environment":"production","message":"Hello from Web App for Containers","version":"<commit-sha>"}

curl -s https://$HOST/health
# Expected: {"status":"ok"}

# Staging shows the previous version after a swap (it holds the old production build)
curl -s https://$(az webapp show -g $RG -n $APP --slot staging --query defaultHostName -o tsv)/
# Expected: "environment":"staging"

# Container config uses ACR and managed identity
az webapp config show -g $RG -n $APP --query "{image:linuxFxVersion,mi:acrUseManagedIdentityCreds,health:healthCheckPath}"
# Expected: {"health": "/health", "image": "DOCKER|<acr>.azurecr.io/webapp:<sha>", "mi": true}

# Image tags in ACR
az acr repository show-tags --name $ACR --repository webapp -o table

# Slots
az webapp deployment slot list -g $RG -n $APP --query "[].name" -o tsv
# Expected: staging
```

Load test to see autoscale (optional, takes 10+ minutes):

```bash
# Simple loop; for real tests use Azure Load Testing or a tool like hey/k6
for i in $(seq 1 5000); do curl -s -o /dev/null https://$HOST/ & done; wait
az monitor autoscale show -g $RG -n autoscale-webapp -o table
az appservice plan show -g $RG -n $PLAN --query sku.capacity
```

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Site shows "Application Error"; log says container did not respond to HTTP pings on port 80 | App listens on 8080, App Service expects 80 | Set `WEBSITES_PORT=8080` |
| `ImagePullFailure` / unauthorized pulling from ACR | `acrUseManagedIdentityCreds` not set, or AcrPull missing | Run Step 6 again; check role assignment on the ACR scope |
| Production works but staging cannot pull | Slot has its own identity without AcrPull | Assign identity and AcrPull for the slot (Step 9) |
| `AADSTS70021: No matching federated identity record` in `azure/login` | Subject mismatch (branch, environment, or PR) | Match the credential subject to how the job runs (`ref:refs/heads/main` or `environment:<name>`) |
| `azure/login` error about missing `ACTIONS_ID_TOKEN_REQUEST_URL` | Workflow lacks `id-token: write` | Add `permissions: id-token: write` |
| `unknown flag --docker-custom-image-name` or deprecation warnings | CLI version uses new flag names | Use `--container-image-name` / `--container-registry-url`; upgrade CLI |
| `az webapp deployment slot create` fails | Plan tier is Basic or Free | Scale the plan to Standard, Premium v3 or higher |
| After swap, app uses wrong config | Setting should have been sticky | Mark it with `--slot-settings` |
| Old version still served after deploy | Container restart still in progress | Wait, check `az webapp log tail`; the smoke test loop handles this |
| Autoscale never triggers | Thresholds never reached, or plan at max count | Check metrics in the portal; review min/max and rule durations |

### Clean up

```bash
az group delete --name $RG --yes --no-wait

# Optional: remove GitHub secrets/variables
gh secret delete AZURE_CLIENT_ID --repo <owner>/webapp-containers
gh secret delete AZURE_TENANT_ID --repo <owner>/webapp-containers
gh secret delete AZURE_SUBSCRIPTION_ID --repo <owner>/webapp-containers
```

Deleting the resource group removes the plan, app, slot, ACR, autoscale setting and the GitHub deploy identity (with its federated credential).

### Next improvements

- Define everything (plan, app, slot, ACR, roles, autoscale) in Bicep or Terraform instead of CLI.
- Add a GitHub **environment** `production` with required reviewers before the swap step.
- Use **swap with preview** (multi-phase swap) or **traffic routing** (`az webapp traffic-routing set --distribution staging=10`) for canary testing.
- Send logs to Log Analytics and add Application Insights with the OpenTelemetry distro.
- Lock down: VNet integration, private endpoint for the app, ACR Premium with private endpoint, `ftpsState: Disabled`, and disable SCM basic auth.
- Scan the image (Microsoft Defender for Containers, Trivy) in the workflow before pushing.
- Try the newer **sidecar** (sitecontainers) model for adding an OpenTelemetry collector next to the app.

### How to explain this project in an interview

> "This was a practice project to learn App Service for containers end to end. I packaged a small Flask app in a Docker image that listens on 8080, pushed it to ACR, and ran it on a Linux App Service plan. Instead of the ACR admin password, the web app pulls with its system-assigned managed identity, which has AcrPull on the registry. The GitHub Actions workflow logs in to Azure with OIDC through a federated credential, so there are no secrets in GitHub. It builds the image tagged with the commit SHA, deploys it to a staging slot with webapps-deploy, smoke-tests the staging URL until it returns the new SHA, and then swaps staging into production, which gives zero downtime and an easy rollback. I also configured WEBSITES_PORT, a health check path, slot-sticky settings, CPU-based autoscale on the plan, and log streaming for troubleshooting."

Points that impress interviewers:

- You know slots have separate managed identities and need their own AcrPull.
- You can explain sticky vs non-sticky settings and what happens during a swap (warm-up first, then routing switch).
- You tag images with the commit SHA and smoke-test before swapping, instead of deploying `latest`.
- You know autoscale and slots depend on the plan tier, and that autoscale is set on the plan.

## Interview Questions

<details><summary>Q1. [Basic] What is the difference between an App Service Plan and a Web App?</summary>

**Answer:**

The **App Service Plan** is the compute: region, OS (Linux or Windows), pricing tier (B1, S1, P0v3, and so on) and number of instances. You pay for the plan. A **Web App** is an application that runs on a plan. Many web apps can share one plan and its instances. Scaling the plan out (more instances) or up (bigger tier) affects every app in it. Features like deployment slots, autoscale and VNet integration depend on the plan tier.

</details>

<details><summary>Q2. [Basic] Why is <code>WEBSITES_PORT</code> needed?</summary>

**Answer:**

App Service's front end forwards traffic to the container on a port. By default it uses port 80 (and in some cases tries to detect it from `EXPOSE`). If the app listens on another port, for example 8080, the platform's startup "ping" fails and the container is restarted with "didn't respond to HTTP pings". Setting the app setting `WEBSITES_PORT=8080` tells App Service which port to use. It only applies to custom containers.

</details>

<details><summary>Q3. [Intermediate] How does a Web App pull a private image from ACR without a password?</summary>

**Answer:**

Enable a managed identity on the web app (system- or user-assigned), give that identity **AcrPull** on the registry, and set the site config `acrUseManagedIdentityCreds` to `true` (plus `acrUserManagedIdentityID` with the client ID if it is a user-assigned identity). App Service then gets a token for the registry using the identity. The registry admin user can stay disabled, and there are no `DOCKER_REGISTRY_SERVER_PASSWORD` settings to leak or rotate. Remember that each slot needs the same setup.

</details>

<details><summary>Q4. [Intermediate] What happens during a slot swap, and what are slot-specific settings?</summary>

**Answer:**

During a swap from staging to production, App Service:

1. Applies production's slot-specific (sticky) settings and connection strings to the staging instances, which restarts them.
2. Warms them up by sending requests to the root (or to custom warm-up paths set with `WEBSITE_SWAP_WARMUP_PING_PATH`) and waits for them to respond.
3. Switches the routing rules so production traffic goes to the warmed instances, and the old production code moves to the staging slot.

Sticky settings (set with `--slot-settings`) stay with the slot, for example `APP_ENV` or a connection string to a staging database. Non-sticky settings move with the code. Rollback is just swapping again.

</details>

<details><summary>Q5. [Intermediate] A deployment from GitHub Actions fails at <code>azure/login</code> with "No matching federated identity record found". How do you troubleshoot it? <em>(scenario)</em></summary>

**Answer:**

The token's subject claim does not match any federated credential. Check how the job runs:

- Push to main: `repo:<owner>/<repo>:ref:refs/heads/main`.
- Job with `environment: production`: `repo:<owner>/<repo>:environment:production` (environment wins over branch).
- Pull request: `repo:<owner>/<repo>:pull_request`.
- Tag: `repo:<owner>/<repo>:ref:refs/tags/<tag>`.

Also confirm the issuer is `https://token.actions.githubusercontent.com`, the audience is `api://AzureADTokenExchange`, the client ID secret points to the right identity, and owner/repo names match exactly (case and renames matter). Then add a credential that matches, or use a flexible federated credential if your tenant supports it.

</details>

<details><summary>Q6. [Intermediate] When would you choose Web App for Containers instead of AKS or Azure Container Apps?</summary>

**Answer:**

Web App for Containers is a good fit for a few HTTP web apps or APIs that need HTTPS, custom domains, slots, easy auth and simple autoscale, with no cluster to operate. **Azure Container Apps** fits microservices, event-driven scaling with KEDA, scale to zero, Dapr, and jobs. **AKS** fits when you need full Kubernetes control: custom operators, service mesh, many teams sharing a platform, or special networking. A good answer mentions team skills and operational cost: App Service has the least to manage, AKS the most.

</details>

<details><summary>Q7. [Advanced] The site is slow and returns 503 errors at peak hours. What do you check and change? <em>(scenario)</em></summary>

**Answer:**

1. Plan metrics: CPU, memory and HTTP queue length. If they are high, the plan is too small.
2. Autoscale: is it configured, did it hit `max-count`, are rule durations too long to react, is cooldown too long?
3. Health check: are instances being removed as unhealthy, leaving fewer to serve traffic?
4. App level: Gunicorn worker count and timeouts, slow dependencies (check Application Insights dependency calls), connection pool limits, SNAT port exhaustion on outbound calls.
5. Other apps on the same plan stealing resources.

Fixes: scale up to a bigger SKU, scale out with tuned rules (scale earlier, for example CPU > 60% over 5 minutes), enable Always On, tune workers, reuse HTTP connections, move noisy apps to another plan, and consider automatic scaling on Premium v3.

</details>

<details><summary>Q8. [Advanced] How would you roll back a bad release in this setup? <em>(scenario)</em></summary>

**Answer:**

Because the previous production build sits in the staging slot after a swap, the fastest rollback is to swap again: `az webapp deployment slot swap -g <rg> -n <app> --slot staging --target-slot production`. This takes seconds and includes warm-up. If staging has already been overwritten, redeploy the previous image tag (the old commit SHA) with `azure/webapps-deploy` or `az webapp config container set --container-image-name <acr>.azurecr.io/webapp:<old-sha>`. Immutable SHA tags make this reliable. After rollback, fix forward through the normal pipeline.

</details>

<details><summary>Q9. [Basic] What does the health check feature do in App Service?</summary>

**Answer:**

You set a path such as `/health`. App Service calls it on every instance about once a minute. If an instance keeps failing (non-2xx responses, after a configurable number of failed pings), it is removed from the load balancer rotation, so users do not hit it. If it stays unhealthy for a long time (about an hour), the platform replaces it. It needs at least two instances to be useful, and the endpoint should be cheap but should check critical dependencies carefully, so one slow downstream does not mark all instances unhealthy at once.

</details>
