# Practice Project 6: Helm Microservices on AKS with GitHub Actions

> This guide shows how to package two Flask microservices (orders and payments) with one reusable Helm chart, deploy them to AKS in separate dev, staging and prod namespaces, and automate it with GitHub Actions using OIDC.

## Key Concepts

### What you will build

You will build and deploy two small services:

- **orders**: exposes `GET /orders` and `POST /orders`. When an order is created, it calls the payments service over cluster DNS (`http://payments`).
- **payments**: exposes `GET /payments` and `POST /payments/charge`. It reads a fake provider key from a Kubernetes Secret.

Both services are deployed with **one generic Helm chart** (`charts/microservice`) and different values files. Each environment is a namespace: `dev`, `staging`, `prod`. Traffic enters through the **AKS application routing add-on** (managed NGINX ingress) on paths `/orders` and `/payments`.

A **GitHub Actions** workflow:

1. Lints and renders the chart on every pull request.
2. On push to `main`, builds both images, tags them with the commit SHA and pushes to ACR.
3. Deploys to `dev` automatically, then to `staging`, then to `prod` after a manual approval.

Final result: `curl -X POST http://<ingress-ip>/orders -H "Host: dev.shop.example.com"` returns a new order with an approved payment, and `helm history orders -n prod` shows every release with its image tag.

### Architecture

```text
 GitHub repo (main)
     |
     v
 GitHub Actions ---- OIDC token ----> Microsoft Entra ID (federated credential)
     |                                        |
     | lint -> build (matrix) -> deploy-dev -> deploy-staging -> [approval] -> deploy-prod
     |            |                    |
     |            v                    v
     |   ACR <acr-name>.azurecr.io     helm upgrade --install (per service, per namespace)
     |   orders:<sha>                      |
     |   payments:<sha>                    v
     |            ^              +-------------------------- AKS cluster ---------------------------+
     |            | AcrPull      |  app-routing-system: NGINX (webapprouting.kubernetes.azure.com) |
     |            +--------------|          | Host: dev.shop.example.com                            |
     |                           |          |-- /orders   --> namespace dev: Service orders          |
     |                           |          |-- /payments --> namespace dev: Service payments        |
     |                           |                                                                   |
     |                           |  orders pod --(http://payments)--> payments Service (same ns)     |
     |                           |                                                                   |
     |                           |  namespaces: dev | staging | prod  (same chart, different values)  |
     |                           +-------------------------------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Flask + gunicorn | The two small HTTP services | Simple Python, production WSGI server |
| Docker | Builds one image per service | Standard container format |
| Azure Container Registry | Stores the images | Private, Entra ID auth, AKS can pull with `--attach-acr` |
| AKS | Runs the services | Managed Kubernetes |
| Application routing add-on | Managed NGINX ingress controller | No manual ingress-nginx install or upgrades |
| Helm 3 | Templates and releases the Kubernetes objects | Values per environment, release history, rollback |
| GitHub Actions | CI/CD workflows | Lives with the code, OIDC to Azure, environments with approvals |
| OIDC federated credentials | Azure login without a client secret | No long-lived secret in GitHub |
| GitHub environments | `dev`, `staging`, `prod` gates | Required reviewers and environment-scoped secrets |

### Prerequisites

- Azure subscription with Owner rights (needed for `--attach-acr` and role assignments).
- GitHub repository where you are admin (to create environments and secrets).
- Local tools:
  - Azure CLI 2.60+: `az version`
  - kubectl: `az aks install-cli`
  - Helm 3: `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash`, then `helm version`
  - Docker (only to test images locally)
- Python 3.12 if you want to run the apps locally.

Cost warning: AKS with two `Standard_D2s_v5` nodes, a public load balancer for the ingress, and a Basic ACR cost a few US dollars per day. Delete the resource group when you finish.

### Folder structure

```text
helm-microservices-aks/
├── services/
│   ├── orders/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── values.yaml            # service-specific Helm values
│   └── payments/
│       ├── app.py
│       ├── requirements.txt
│       ├── Dockerfile
│       └── values.yaml
├── charts/
│   └── microservice/              # one generic chart for all services
│       ├── Chart.yaml
│       ├── values.yaml            # safe defaults
│       ├── values-dev.yaml        # environment overrides
│       ├── values-staging.yaml
│       ├── values-prod.yaml
│       └── templates/
│           ├── _helpers.tpl
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           ├── configmap.yaml
│           ├── secret.yaml
│           └── NOTES.txt
└── .github/
    └── workflows/
        ├── ci-cd.yaml             # lint, build, call deploy per env
        └── deploy-env.yaml        # reusable deploy workflow
```

### Step-by-step

#### Step 1: Write the orders service

Orders creates an order and calls payments. The payments URL comes from an environment variable, which Helm sets from a ConfigMap.

```python
# services/orders/app.py
import os
import uuid

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments")
APP_ENV = os.getenv("APP_ENV", "local")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/orders")
def list_orders():
    return jsonify(service="orders", env=APP_ENV, orders=[])


@app.post("/orders")
def create_order():
    body = request.get_json(silent=True) or {}
    order_id = str(uuid.uuid4())
    try:
        resp = requests.post(
            f"{PAYMENTS_URL}/payments/charge",
            json={"order_id": order_id, "amount": body.get("amount", 10)},
            timeout=3,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return jsonify(order_id=order_id, status="payment_failed", error=str(exc)), 502
    return jsonify(order_id=order_id, status="created", payment=resp.json()), 201
```

```text
# services/orders/requirements.txt
flask==3.1.0
gunicorn==23.0.0
requests==2.32.3
```

What this does:

- `PAYMENTS_URL` defaults to `http://payments`. Inside the same namespace, the Service name `payments` resolves through cluster DNS to `payments.<namespace>.svc.cluster.local`.
- A 3-second `timeout` stops orders from hanging if payments is slow.
- `/healthz` is used by Kubernetes probes.

#### Step 2: Write the payments service

```python
# services/payments/app.py
import os

from flask import Flask, jsonify, request

app = Flask(__name__)
APP_ENV = os.getenv("APP_ENV", "local")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/payments")
def info():
    # Never return the key itself, only whether it is configured
    return jsonify(
        service="payments",
        env=APP_ENV,
        provider_key_configured=bool(os.getenv("PAYMENT_PROVIDER_KEY")),
    )


@app.post("/payments/charge")
def charge():
    body = request.get_json(silent=True) or {}
    return jsonify(order_id=body.get("order_id"), amount=body.get("amount"), status="approved")
```

```text
# services/payments/requirements.txt
flask==3.1.0
gunicorn==23.0.0
```

What this does:

- `PAYMENT_PROVIDER_KEY` comes from a Kubernetes Secret. The app only reports whether it exists.
- The routes start with `/payments`, so the ingress can forward the path as is. No URL rewrite is needed.

#### Step 3: Write the Dockerfiles

Both services use the same pattern. Here is the orders Dockerfile; the payments one is identical.

```dockerfile
# services/orders/Dockerfile  (copy the same file to services/payments/Dockerfile)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

RUN useradd --create-home --uid 10001 appuser
USER 10001

EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
```

What this does:

- Runs as non-root UID 10001, so `runAsNonRoot: true` in the pod passes.
- Listens on port 8080, which the chart uses as `containerPort`.

#### Step 4: Create ACR and AKS with the application routing add-on

```bash
az login
export LOCATION="eastus"
export RG="rg-helm-lab"
export ACR="<acr-name>"          # globally unique, lowercase letters and numbers
export AKS="aks-helm-lab"

az group create -n "$RG" -l "$LOCATION"
az acr create -g "$RG" -n "$ACR" --sku Basic

az aks create \
  --resource-group "$RG" \
  --name "$AKS" \
  --tier free \
  --node-count 2 \
  --node-vm-size Standard_D2s_v5 \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --enable-app-routing \
  --attach-acr "$ACR" \
  --generate-ssh-keys

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl get pods -n app-routing-system
```

What this does:

- `--enable-app-routing` installs a managed NGINX ingress controller in the `app-routing-system` namespace with the IngressClass `webapprouting.kubernetes.azure.com`. On an existing cluster use `az aks approuting enable -g "$RG" -n "$AKS"`.
- `--attach-acr` grants `AcrPull` to the kubelet identity, so pods can pull images without pull secrets.
- This cluster uses local accounts and Kubernetes RBAC to keep the lab simple. See Next improvements for Entra ID and Azure RBAC.
- Note: the upstream ingress-nginx project has been retired, and Microsoft is moving AKS ingress toward the Gateway API. The add-on still works for this lab, but check the current AKS docs before using it for new production systems.

#### Step 5: Create the Helm chart and trim it

`helm create` gives a working chart with many extras. Keep the structure, remove what you do not need, and write the templates below.

```bash
mkdir -p charts && cd charts
helm create microservice
rm -rf microservice/templates/tests \
       microservice/templates/hpa.yaml \
       microservice/templates/serviceaccount.yaml \
       microservice/templates/httproute.yaml
cd ..
```

What this does:

- `helm create` scaffolds `Chart.yaml`, `values.yaml`, `templates/` and `_helpers.tpl`.
- Removing unused templates keeps the chart small and easy to read. You can add an HPA back later. (`httproute.yaml` only exists in newer Helm versions; `rm -rf` ignores it if missing.)

**Design choice: one generic chart reused per service.**

| Option | How it works | Pros | Cons |
| --- | --- | --- | --- |
| Umbrella chart with `range` | One chart, `values.yaml` has `services: [orders, payments]`, templates loop with `range` | One release, one command | One release for everything: a bad payments change rolls back orders too; values file gets big |
| Generic chart reused per service (chosen) | One chart, installed twice as releases `orders` and `payments`, each with its own values | Independent releases, history and rollback per service; same templates everywhere | Two `helm upgrade` commands (a loop in CI handles it) |

This guide uses the generic chart because each microservice should be deployed and rolled back independently. That is the main reason to have microservices.

#### Step 6: Write Chart.yaml and the default values.yaml

```yaml
# charts/microservice/Chart.yaml
apiVersion: v2
name: microservice
description: Generic chart for a small HTTP microservice
type: application
version: 0.1.0
appVersion: "1.0.0"
```

```yaml
# charts/microservice/values.yaml
nameOverride: ""

replicaCount: 1

image:
  repository: ""
  tag: ""
  pullPolicy: IfNotPresent

containerPort: 8080

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  className: webapprouting.kubernetes.azure.com
  host: ""
  path: /

probes:
  path: /healthz

# Non-secret settings, rendered into a ConfigMap and loaded as env vars
config: {}

# Secret settings, rendered into a Secret. Pass real values at deploy time, never commit them.
secrets: {}

resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 250m
    memory: 256Mi
```

What this does:

- `version` is the chart version (change it when templates change). `appVersion` is a default app version, used only if `image.tag` is empty.
- Every setting has a safe default. Service files and environment files override only what differs.

#### Step 7: Write the environment values files

Environment files hold settings that differ between dev, staging and prod.

```yaml
# charts/microservice/values-dev.yaml
replicaCount: 1
ingress:
  host: dev.shop.example.com
config:
  APP_ENV: dev
  LOG_LEVEL: debug
```

```yaml
# charts/microservice/values-staging.yaml
replicaCount: 2
ingress:
  host: staging.shop.example.com
config:
  APP_ENV: staging
  LOG_LEVEL: info
```

```yaml
# charts/microservice/values-prod.yaml
replicaCount: 3
ingress:
  host: shop.example.com
config:
  APP_ENV: prod
  LOG_LEVEL: warning
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

What this does:

- Each environment uses a different host, so the same paths `/orders` and `/payments` can exist in all three namespaces on the same ingress controller without conflict.
- `example.com` is a reserved test domain. You test with a `Host` header, so no DNS setup is needed.

#### Step 8: Write the service values files

Service files hold settings that are the same in every environment for that service.

```yaml
# services/orders/values.yaml
image:
  repository: <acr-name>.azurecr.io/orders
ingress:
  enabled: true
  path: /orders
config:
  PAYMENTS_URL: "http://payments"
```

```yaml
# services/payments/values.yaml
image:
  repository: <acr-name>.azurecr.io/payments
ingress:
  enabled: true
  path: /payments
```

What this does:

- Helm merges maps from all `-f` files. Later files win on conflicts, and `--set` wins over all files. So `config` ends up with `APP_ENV`, `LOG_LEVEL` and `PAYMENTS_URL` together.
- The merge order used later is: chart `values.yaml` < `values-<env>.yaml` < `services/<svc>/values.yaml` < `--set`.

#### Step 9: Write _helpers.tpl

Helpers keep names and labels consistent across all templates.

```yaml
{{/* charts/microservice/templates/_helpers.tpl */}}

{{- define "microservice.name" -}}
{{- default .Release.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "microservice.selectorLabels" -}}
app.kubernetes.io/name: {{ include "microservice.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "microservice.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{ include "microservice.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | trunc 63 | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "microservice.image" -}}
{{- $repo := required "image.repository is required" .Values.image.repository -}}
{{- printf "%s:%s" $repo (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}
```

What this does:

- `microservice.name` uses the release name, so installing the release `payments` creates a Service called `payments`. That is exactly the DNS name orders calls.
- Selector labels are a small, stable subset. They must never change after the first install, because a Deployment's selector is immutable.
- `required` makes `helm template` fail with a clear message if the image repository is missing.

#### Step 10: Write the Deployment and Service templates

```yaml
# charts/microservice/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "microservice.name" . }}
  labels:
    {{- include "microservice.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "microservice.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "microservice.selectorLabels" . | nindent 8 }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
        - name: {{ include "microservice.name" . }}
          image: {{ include "microservice.image" . | quote }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.containerPort }}
          envFrom:
            - configMapRef:
                name: {{ include "microservice.name" . }}
            {{- if .Values.secrets }}
            - secretRef:
                name: {{ include "microservice.name" . }}
            {{- end }}
          readinessProbe:
            httpGet:
              path: {{ .Values.probes.path }}
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: {{ .Values.probes.path }}
              port: http
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

```yaml
# charts/microservice/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "microservice.name" . }}
  labels:
    {{- include "microservice.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    {{- include "microservice.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
```

What this does:

- `nindent` adds a newline and the right indentation, so included labels are valid YAML.
- The `checksum/config` and `checksum/secret` annotations change when the ConfigMap or Secret content changes. That changes the pod template, so Kubernetes restarts pods and they pick up new env values. Without this, a config change alone would not restart pods.
- `envFrom` loads every ConfigMap key (and Secret key, if any) as environment variables.
- The Service listens on port 80 and forwards to the named container port `http` (8080). So orders can call `http://payments` without a port.

#### Step 11: Write the ConfigMap and Secret templates

```yaml
# charts/microservice/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "microservice.name" . }}
  labels:
    {{- include "microservice.labels" . | nindent 4 }}
data:
  {{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
```

```yaml
# charts/microservice/templates/secret.yaml
{{- if .Values.secrets }}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "microservice.name" . }}
  labels:
    {{- include "microservice.labels" . | nindent 4 }}
type: Opaque
stringData:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
{{- end }}
```

What this does:

- `quote` makes every value a string, because ConfigMap and Secret data must be strings (`"3"`, not `3`).
- The Secret is created only if `secrets` has keys.
- Important: a Secret created from Helm values is stored in the Helm release record (itself a Kubernetes Secret) and is only base64-encoded. It is acceptable for a lab. In production, use the **Azure Key Vault provider for Secrets Store CSI Driver** (AKS add-on `azure-keyvault-secrets-provider`) or **External Secrets Operator** with workload identity, so secret values never pass through Helm or CI.

#### Step 12: Write the Ingress template and NOTES.txt

```yaml
# charts/microservice/templates/ingress.yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "microservice.name" . }}
  labels:
    {{- include "microservice.labels" . | nindent 4 }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - http:
        paths:
          - path: {{ .Values.ingress.path }}
            pathType: Prefix
            backend:
              service:
                name: {{ include "microservice.name" . }}
                port:
                  number: {{ .Values.service.port }}
      {{- with .Values.ingress.host }}
      host: {{ . | quote }}
      {{- end }}
{{- end }}
```

```text
{{- /* charts/microservice/templates/NOTES.txt */}}
{{ include "microservice.name" . }} is deployed in namespace {{ .Release.Namespace }}.

Image: {{ include "microservice.image" . }}
In-cluster URL: http://{{ include "microservice.name" . }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.service.port }}
{{- if .Values.ingress.enabled }}

External path: {{ .Values.ingress.path }} (host: {{ .Values.ingress.host | default "any" }})
Get the ingress IP:
  kubectl get svc nginx -n app-routing-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
{{- end }}
```

What this does:

- `ingressClassName: webapprouting.kubernetes.azure.com` tells the application routing NGINX controller to handle this Ingress.
- Each service release creates its own Ingress with one path. NGINX merges rules for the same host, so `/orders` and `/payments` both work on `dev.shop.example.com`.
- `pathType: Prefix` matches `/orders` and everything under it, such as `/orders/123`.
- `NOTES.txt` is printed after `helm install` or `helm upgrade`, giving the user quick next steps.

#### Step 13: Lint, render and install manually once

Always test the chart locally before CI. Build and push images once by hand so the first install has something to pull.

```bash
# Build and push images (ACR Tasks builds in Azure, no local Docker needed)
az acr build -r "$ACR" -t orders:manual   services/orders
az acr build -r "$ACR" -t payments:manual services/payments

# Lint and render
helm lint charts/microservice \
  -f charts/microservice/values-dev.yaml -f services/orders/values.yaml --set image.tag=manual

helm template orders charts/microservice \
  -f charts/microservice/values-dev.yaml -f services/orders/values.yaml --set image.tag=manual

# Install payments first, then orders
for svc in payments orders; do
  helm upgrade --install "$svc" charts/microservice \
    --namespace dev --create-namespace \
    -f charts/microservice/values-dev.yaml \
    -f "services/$svc/values.yaml" \
    --set image.repository="$ACR.azurecr.io/$svc" \
    --set image.tag=manual \
    --set-string secrets.PAYMENT_PROVIDER_KEY=dev-dummy-key \
    --atomic --wait --timeout 5m
done

helm list -n dev
```

What this does:

- `helm lint` checks chart structure and template errors. `helm template` prints the final YAML so you can read exactly what will be applied.
- `upgrade --install` installs if the release does not exist, or upgrades if it does. One command for first and later deploys.
- `--create-namespace` creates `dev` if missing.
- `--wait` waits until pods are ready. `--atomic` rolls back automatically if the upgrade fails or times out.
- In this manual loop both services get the dummy secret; in CI only payments gets it.
- Note: Helm 4 renames `--atomic` to `--rollback-on-failure`. This guide pins Helm 3, where `--atomic` is correct.

#### Step 14: Set up OIDC from GitHub to Azure

Create an app registration with federated credentials. GitHub gets a short-lived token per run; no client secret exists.

```bash
APP_ID=$(az ad app create --display-name gh-helm-microservices --query appId -o tsv)
az ad sp create --id "$APP_ID"
SP_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

REPO="<github-org>/<repo-name>"

for subject in "ref:refs/heads/main" "environment:dev" "environment:staging" "environment:prod"; do
  name=$(echo "$subject" | tr ':/' '--')
  az ad app federated-credential create --id "$APP_ID" --parameters "{
    \"name\": \"$name\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$REPO:$subject\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
done

ACR_ID=$(az acr show -n "$ACR" --query id -o tsv)
AKS_ID=$(az aks show -g "$RG" -n "$AKS" --query id -o tsv)

az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
  --role AcrPush --scope "$ACR_ID"
az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
  --role "Azure Kubernetes Service Cluster User Role" --scope "$AKS_ID"

echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)"
echo "AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)"
```

What this does:

- The `subject` must match the token GitHub sends. A job without an environment on `main` sends `repo:<org>/<repo>:ref:refs/heads/main`. A job with `environment: prod` sends `repo:<org>/<repo>:environment:prod`. You need one federated credential per subject.
- `AcrPush` lets CI push images. `Cluster User Role` lets CI download the kubeconfig.
- On a local-accounts cluster, the user kubeconfig has full cluster access. For least privilege, use Entra ID with Azure RBAC and namespace-scoped roles (see Next improvements).

In GitHub, add repository secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (these are identifiers, not passwords). Create environments **dev**, **staging** and **prod** under **Settings > Environments**. On **prod**, add required reviewers and restrict deployment branches to `main`. Add an environment secret `PAYMENT_PROVIDER_KEY` in each environment.

#### Step 15: Write the main CI/CD workflow

```yaml
# .github/workflows/ci-cd.yaml
name: ci-cd

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  ACR_NAME: <acr-name>
  HELM_VERSION: v3.17.0

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: azure/setup-helm@v4
        with:
          version: ${{ env.HELM_VERSION }}

      - name: Lint and render chart for every service and environment
        run: |
          for svc in orders payments; do
            for env in dev staging prod; do
              args="-f charts/microservice/values-$env.yaml -f services/$svc/values.yaml --set image.tag=ci"
              helm lint charts/microservice $args
              helm template "$svc" charts/microservice $args > /dev/null
            done
          done

  build:
    needs: lint
    if: github.event_name != 'pull_request'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [orders, payments]
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Build and push image
        run: |
          IMAGE="$ACR_NAME.azurecr.io/${{ matrix.service }}:${{ github.sha }}"
          az acr login --name "$ACR_NAME"
          docker build -t "$IMAGE" "services/${{ matrix.service }}"
          docker push "$IMAGE"

  deploy-dev:
    needs: build
    uses: ./.github/workflows/deploy-env.yaml
    with:
      environment: dev
      image-tag: ${{ github.sha }}
    secrets: inherit

  deploy-staging:
    needs: deploy-dev
    uses: ./.github/workflows/deploy-env.yaml
    with:
      environment: staging
      image-tag: ${{ github.sha }}
    secrets: inherit

  deploy-prod:
    needs: deploy-staging
    uses: ./.github/workflows/deploy-env.yaml
    with:
      environment: prod
      image-tag: ${{ github.sha }}
    secrets: inherit
```

What this does:

- `permissions: id-token: write` lets the job request an OIDC token. Without it, `azure/login` fails.
- Pull requests run only `lint`, because `build` has `if: github.event_name != 'pull_request'` and the deploy jobs need `build`.
- The `build` matrix builds orders and payments in parallel. Images are tagged with `github.sha`, so every commit has a unique, traceable image.
- `az acr login` + `docker build/push` needs only `AcrPush`. The alternative `az acr build` runs the build in Azure but needs broader rights on the registry (for example Contributor), because it schedules an ACR Task.
- The three deploy jobs reuse one workflow. They run in order: dev, then staging, then prod. Prod waits for the reviewers configured on the `prod` environment.
- The same image tag is promoted through all environments. Nothing is rebuilt for prod.

#### Step 16: Write the reusable deploy workflow

```yaml
# .github/workflows/deploy-env.yaml
name: deploy-env

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      image-tag:
        required: true
        type: string

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    concurrency:
      group: deploy-${{ inputs.environment }}
      cancel-in-progress: false
    env:
      ACR_NAME: <acr-name>
      RESOURCE_GROUP: rg-helm-lab
      CLUSTER_NAME: aks-helm-lab
      NAMESPACE: ${{ inputs.environment }}
      IMAGE_TAG: ${{ inputs.image-tag }}
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - uses: azure/setup-helm@v4
        with:
          version: v3.17.0

      - uses: azure/aks-set-context@v4
        with:
          resource-group: ${{ env.RESOURCE_GROUP }}
          cluster-name: ${{ env.CLUSTER_NAME }}

      - name: Deploy payments, then orders
        env:
          PAYMENT_PROVIDER_KEY: ${{ secrets.PAYMENT_PROVIDER_KEY }}
        run: |
          for svc in payments orders; do
            extra=()
            if [ "$svc" = "payments" ]; then
              extra+=(--set-string "secrets.PAYMENT_PROVIDER_KEY=$PAYMENT_PROVIDER_KEY")
            fi
            helm upgrade --install "$svc" charts/microservice \
              --namespace "$NAMESPACE" --create-namespace \
              -f "charts/microservice/values-$NAMESPACE.yaml" \
              -f "services/$svc/values.yaml" \
              --set image.repository="$ACR_NAME.azurecr.io/$svc" \
              --set image.tag="$IMAGE_TAG" \
              "${extra[@]}" \
              --atomic --wait --timeout 5m
          done

      - name: Show release status
        run: |
          helm list -n "$NAMESPACE"
          kubectl get pods,svc,ingress -n "$NAMESPACE"
```

What this does:

- `environment: ${{ inputs.environment }}` connects the job to the GitHub environment. That enables approvals, environment secrets and the matching OIDC subject.
- `concurrency` makes sure only one deploy runs per environment at a time; a second one waits instead of cancelling a running Helm upgrade halfway.
- `azure/aks-set-context@v4` writes a kubeconfig for the cluster, which both `kubectl` and `helm` use. The CLI alternative is `az aks get-credentials -g "$RESOURCE_GROUP" -n "$CLUSTER_NAME"`.
- Payments is deployed first, so orders can reach it as soon as it starts.
- `--set image.tag="$IMAGE_TAG"` passes the commit SHA. `--atomic` rolls the release back if pods do not become ready within 5 minutes, which fails the job and stops promotion to the next environment.
- `--set-string` keeps the secret as a string. GitHub masks the secret value in logs.

#### Step 17: Push and watch the pipeline

```bash
git add .
git commit -m "Helm chart and CI/CD for orders and payments"
git push origin main
```

What this does:

- The workflow runs lint, build, then deploy-dev and deploy-staging automatically.
- `deploy-prod` shows "Waiting for review". A reviewer approves it in the Actions run page, and then it deploys the same image tag to `prod`.

### Verify it works

```bash
kubectl get pods,svc,ingress -n dev
```

Expected output (names, IPs and ages will differ):

```text
NAME                            READY   STATUS    RESTARTS   AGE
pod/orders-7c9d8f6b8d-q2l8k     1/1     Running   0          2m
pod/payments-5f6b9c7d4b-x7mzp   1/1     Running   0          2m

NAME               TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/orders     ClusterIP   10.0.120.15    <none>        80/TCP    2m
service/payments   ClusterIP   10.0.44.201    <none>        80/TCP    2m

NAME                                 CLASS                                HOSTS                  ADDRESS        PORTS   AGE
ingress.networking.k8s.io/orders     webapprouting.kubernetes.azure.com   dev.shop.example.com   20.62.150.10   80      2m
ingress.networking.k8s.io/payments   webapprouting.kubernetes.azure.com   dev.shop.example.com   20.62.150.10   80      2m
```

Call the services through the ingress:

```bash
INGRESS_IP=$(kubectl get svc nginx -n app-routing-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl -s -H "Host: dev.shop.example.com" "http://$INGRESS_IP/payments"
curl -s -X POST -H "Host: dev.shop.example.com" -H "Content-Type: application/json" \
  -d '{"amount": 25}' "http://$INGRESS_IP/orders"
```

```text
{"env":"dev","provider_key_configured":true,"service":"payments"}
{"order_id":"5b0e...","payment":{"amount":25,"order_id":"5b0e...","status":"approved"},"status":"created"}
```

Check service-to-service DNS from inside the cluster:

```bash
kubectl run dns-test -n dev --rm -it --image=busybox:1.36 --restart=Never -- \
  wget -qO- --post-data='{"order_id":"t1","amount":1}' --header='Content-Type: application/json' \
  http://payments/payments/charge
```

Check Helm history and roll back:

```bash
helm history orders -n dev
```

```text
REVISION  UPDATED                   STATUS      CHART               APP VERSION  DESCRIPTION
1         Thu Oct 15 10:02:11 2026  superseded  microservice-0.1.0  1.0.0        Install complete
2         Thu Oct 15 10:30:45 2026  deployed    microservice-0.1.0  1.0.0        Upgrade complete
```

```bash
helm rollback orders 1 -n dev --wait
helm history orders -n dev        # a new revision 3 appears, a copy of revision 1
helm get values orders -n dev     # shows the values used by the current revision
```

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `azure/login` fails with `AADSTS700213: No matching federated identity record found` | Federated credential subject does not match the job | Add a credential for `environment:<name>` or `ref:refs/heads/main` exactly as the job runs |
| `Unable to get ACTIONS_ID_TOKEN_REQUEST_URL` | Missing `id-token: write` permission | Add `permissions: id-token: write` at workflow level (caller and reusable workflow) |
| Pods `ImagePullBackOff` | Wrong repository or tag, or ACR not attached | `kubectl describe pod`; `az aks check-acr -g <rg> -n <aks> --acr <acr>.azurecr.io` |
| `Error: UPGRADE FAILED: another operation (install/upgrade/rollback) is in progress` | A previous Helm run was killed mid-way | `helm history <rel> -n <ns>`; `helm rollback <rel> <last-good> -n <ns>` |
| `helm upgrade` fails with `spec.selector: field is immutable` | Selector labels changed between chart versions | Keep selector labels stable; if needed, uninstall and reinstall the release |
| Ingress has no ADDRESS | App routing add-on not enabled, or wrong `ingressClassName` | `az aks approuting enable`; use `webapprouting.kubernetes.azure.com` |
| 404 from NGINX | Missing `Host` header, or path does not match | Send `-H "Host: dev.shop.example.com"`; check `kubectl describe ingress` |
| Orders returns 502 `payment_failed` | Payments not ready, wrong `PAYMENTS_URL`, or different namespace | Check payments pods; use `http://payments` in the same namespace |
| Config change did not reach pods | Pods not restarted | Keep the `checksum/config` annotation in the pod template |
| `--atomic` timed out and rolled back | Readiness probe failing or image crash | `kubectl logs` and `kubectl describe pod` on the failing pod; fix and redeploy |

### Clean up

```bash
helm uninstall orders payments -n dev
helm uninstall orders payments -n staging
helm uninstall orders payments -n prod

az group delete -n rg-helm-lab --yes --no-wait

# Remove the app registration used by GitHub Actions
az ad app delete --id "$APP_ID"
```

### Next improvements

- Enable Entra ID with Azure RBAC on AKS and give the CI identity `Azure Kubernetes Service RBAC Writer` only on the target namespace (pre-create namespaces and drop `--create-namespace`). Use `azure/use-kubelogin@v1` and `use-kubelogin: 'true'` in `aks-set-context`.
- Replace Helm-managed Secrets with Key Vault CSI driver or External Secrets Operator and workload identity.
- Use separate AKS clusters (or at least separate node pools) for prod.
- Add a HorizontalPodAutoscaler and a PodDisruptionBudget to the chart.
- Package the chart and push it to ACR as an OCI artifact: `helm push microservice-0.1.0.tgz oci://<acr-name>.azurecr.io/helm`.
- Add NetworkPolicies so only orders can call payments.
- Add `helm-unittest` tests and `kubeconform` schema validation in the lint job.
- Move to GitOps (Argo CD or Flux) so the cluster pulls desired state from Git.
- Plan the migration from NGINX ingress to Gateway API.

### How to explain this project in an interview

> "As a practice project, I deployed two Flask microservices, orders and payments, to AKS with Helm and GitHub Actions. I wrote one generic Helm chart and installed it once per service, because each service should have its own release history and rollback. Values are layered: chart defaults, then an environment file for dev, staging or prod, then a service file, and finally the image tag from the commit SHA with --set. Each environment is its own namespace, and traffic comes in through the AKS application routing add-on with paths /orders and /payments. Orders calls payments by its Service name over cluster DNS. The pipeline uses OIDC to log in to Azure, so there are no client secrets in GitHub. It lints and renders the chart on PRs, builds both images in a matrix, then deploys dev, staging and prod with helm upgrade --install --atomic --wait. Prod needs approval through a GitHub environment, and the same image is promoted without a rebuild."

Points that impress interviewers:

- You can explain why you chose a generic chart per service over an umbrella chart.
- You use `--atomic --wait`, `helm history` and `helm rollback`, and the checksum annotation to restart pods on config changes.
- You used OIDC federated credentials and know the subject must match the branch or environment.
- You know Helm-managed Secrets are not truly secret and can name Key Vault CSI or External Secrets as the fix.

## Interview Questions

<details><summary>Q1. [Basic] What does <code>helm upgrade --install --atomic --wait</code> do?</summary>

**Answer:**

`upgrade --install` installs the release if it does not exist, otherwise upgrades it, so the same command works for the first and every later deploy. `--wait` makes Helm wait until Deployments have ready pods (and Services and other resources are ready) before marking the release successful. `--atomic` implies `--wait` and, if the upgrade fails or times out, automatically rolls back to the previous revision. In CI this means a failed deploy leaves the old version running and fails the job. In Helm 4 the flag is renamed to `--rollback-on-failure`.

</details>

<details><summary>Q2. [Basic] How does the orders service find the payments service?</summary>

**Answer:**

Through Kubernetes DNS. The payments release creates a Service named `payments`. CoreDNS creates the record `payments.<namespace>.svc.cluster.local`. Pods in the same namespace can use the short name `payments` because the namespace is in their DNS search path. The Service forwards port 80 to container port 8080 on ready payments pods. To call a service in another namespace, use `payments.<other-namespace>` or the full name.

</details>

<details><summary>Q3. [Basic] In what order are Helm values applied?</summary>

**Answer:**

From lowest to highest priority: the chart's `values.yaml`, then each `-f` file in the order given (later files win), then `--set`, `--set-string` and `--set-file` flags. Maps are merged deeply, so `config` keys from different files are combined. Lists are replaced, not merged. In this project: chart defaults, then `values-<env>.yaml`, then `services/<svc>/values.yaml`, then `--set image.tag=<sha>`.

</details>

<details><summary>Q4. [Intermediate] Why use one generic chart per service instead of an umbrella chart with <code>range</code>?</summary>

**Answer:**

With an umbrella chart, all services are one release. A failed upgrade of payments rolls back orders too, `helm history` mixes changes from all services, and teams cannot deploy independently. With a generic chart installed once per service, each service has its own release, history, and rollback, while still sharing the same tested templates. The umbrella approach can make sense for a tightly coupled set of components that are always released together, such as a product bundle with fixed versions.

</details>

<details><summary>Q5. [Intermediate] You changed a value in the ConfigMap, Helm upgrade succeeded, but the app still uses the old value. Why? <em>(scenario)</em></summary>

**Answer:**

Environment variables from a ConfigMap are read only when the container starts. Updating the ConfigMap does not restart pods, and the Deployment's pod template did not change, so Kubernetes did nothing. The fix is the checksum annotation in the pod template: `checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}`. When the ConfigMap content changes, the hash changes, the pod template changes, and a rolling restart happens. A quick manual fix is `kubectl rollout restart deployment/<name> -n <ns>`.

</details>

<details><summary>Q6. [Intermediate] How does the workflow log in to Azure without a client secret?</summary>

**Answer:**

It uses OpenID Connect. The job has `permissions: id-token: write`, so GitHub issues a signed, short-lived token with claims like `repo:<org>/<repo>:environment:prod`. `azure/login@v2` sends this token to Microsoft Entra ID. The app registration has a federated credential that trusts the GitHub issuer and that exact subject, so Entra ID returns an Azure access token. Nothing long-lived is stored in GitHub; `AZURE_CLIENT_ID`, tenant and subscription IDs are identifiers, not secrets. Because the subject includes the environment, you can trust prod deployments only from the `prod` environment.

</details>

<details><summary>Q7. [Intermediate] A deploy to prod went wrong. How do you roll back? <em>(scenario)</em></summary>

**Answer:**

First check what happened: `helm history orders -n prod` and `kubectl get pods -n prod`. If `--atomic` already rolled back, the old version is running and you only need to fix the code. If the release succeeded but the app is broken, run `helm rollback orders <last-good-revision> -n prod --wait`. This creates a new revision that is a copy of the old one. Then revert the commit in Git or redeploy a known good SHA through the pipeline, so Git and the cluster agree again. Because images are tagged by SHA and are immutable, the old image is still in ACR.

</details>

<details><summary>Q8. [Advanced] Why is putting secrets in Helm values not ideal, and what would you use instead?</summary>

**Answer:**

Values passed with `--set` or a values file are stored in the Helm release record, which is a Kubernetes Secret in the namespace, only base64-encoded. Anyone who can read Secrets or run `helm get values` sees them. They also pass through CI logs and runners. Better options on AKS: the Azure Key Vault provider for Secrets Store CSI Driver, which mounts Key Vault secrets into pods (and can sync to a Kubernetes Secret), or External Secrets Operator, which syncs Key Vault secrets into Kubernetes Secrets. Both should use workload identity to access Key Vault, so no credentials are needed at all.

</details>

<details><summary>Q9. [Advanced] <code>helm upgrade</code> fails with "another operation (install/upgrade/rollback) is in progress". What happened and how do you fix it? <em>(scenario)</em></summary>

**Answer:**

A previous Helm command was interrupted (cancelled CI job, runner lost, timeout without `--atomic`), leaving the latest release revision in `pending-install`, `pending-upgrade` or `pending-rollback` status. Helm blocks new operations to avoid conflicts. Check with `helm history <release> -n <ns>`. Fix by rolling back to the last `deployed` revision: `helm rollback <release> <revision> -n <ns>`. If it was the first install, `helm uninstall` and install again. To prevent it, use `concurrency` in GitHub Actions with `cancel-in-progress: false` and always use `--atomic` with a timeout.

</details>

<details><summary>Q10. [Advanced] How would you make this setup production-grade for security and isolation? <em>(scenario)</em></summary>

**Answer:**

- Separate prod into its own AKS cluster and subscription, or at least its own node pool.
- Enable Entra ID with Azure RBAC on AKS, disable local accounts, and give each environment's CI identity only namespace-scoped roles.
- Use separate federated credentials and identities per environment, so the dev identity cannot deploy to prod.
- Add NetworkPolicies so only orders can call payments, and only the ingress can reach orders.
- Use Key Vault CSI or External Secrets with workload identity for secrets.
- Scan images (Trivy or Defender for Containers), sign them, and enforce policies with Azure Policy or Kyverno.
- Add PodDisruptionBudgets, HPAs, and topology spread constraints for availability.

</details>
