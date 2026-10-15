# Practice Project 12: Azure Function App (Python) Deployed with GitHub Actions

> This guide shows how to build a Python HTTP-triggered Azure Function with the v2 programming model, test it locally, host it on a Flex Consumption plan, deploy it with GitHub Actions using OIDC, and call it from a Logic App.

## Key Concepts

### What you will build

- A Python Function App using the **v2 programming model** (decorators in `function_app.py`, no `function.json` files).
- One **HTTP trigger** at `/api/hello` that returns `Hello from Azure Functions` (and greets you by name if you pass one).
- Local testing with **Azure Functions Core Tools**.
- Azure resources: a Storage account, a **Function App on the Flex Consumption plan** and **Application Insights**.
- A **GitHub Actions** workflow that logs in with **OIDC** (`azure/login@v2`) and deploys with `Azure/functions-action@v1`.
- Bonus: a **Logic App (Consumption)** that calls the function with an HTTP POST on a schedule.

Final result: you run `curl "https://<function-host>/api/hello?code=<function-key>&name=Sam"` and get `Hello from Azure Functions, Sam!`. Each push to `main` redeploys automatically, and every request shows up in Application Insights.

### Architecture

```text
 Developer --push--> GitHub (main)
                        |
                        v
               GitHub Actions workflow
                 setup-python 3.12 -> pip install -> tests
                 azure/login@v2 (OIDC)
                 Azure/functions-action@v1 (zip deploy, remote build)
                        |
                        v
 +------------------------- Resource group -----------------------------+
 |  Function App (Flex Consumption, Linux, Python 3.12)                  |
 |    function_app.py  ->  HTTP trigger  GET/POST /api/hello            |
 |    auth level: FUNCTION (needs ?code=<key> or x-functions-key)        |
 |          |                         |                                  |
 |          v                         v                                  |
 |  Storage account            Application Insights                      |
 |  (AzureWebJobsStorage,      (requests, traces, failures)              |
 |   deployment package)                                                 |
 |                                                                       |
 |  Logic App (Consumption)  --Recurrence--> HTTP POST /api/hello        |
 +-----------------------------------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Azure Functions | Runs the Python code on demand | Serverless: pay per execution, scales automatically |
| Python v2 programming model | Defines triggers with decorators | Simpler than v1 `function.json`; one file, code-first |
| Azure Functions Core Tools (`func`) | Creates the project and runs it locally | Same runtime as Azure, fast feedback loop |
| Azurite | Local emulator for Azure Storage | The Functions host needs a storage connection |
| Flex Consumption plan | Hosts the app in Azure | Newest serverless plan: fast scale, VNet support, scale to zero |
| Storage account | Host state, keys, deployment package | Required by every Function App |
| Application Insights | Logs, metrics, request traces | Built-in monitoring for Functions |
| GitHub Actions + `azure/login@v2` | CI/CD with OIDC | No publish profile or secret to manage |
| `Azure/functions-action@v1` | Deploys the code package | Official action, supports Flex and remote build |
| Logic App (Consumption) | Calls the function on a schedule | Low-code orchestration, common pairing with Functions |

### Prerequisites

- Azure subscription (Contributor + Role Based Access Control Administrator on a resource group, or Owner).
- GitHub account and a repo, for example `<owner>/func-hello-python`.
- Python **3.12** locally (match the version you deploy).
- Azure CLI 2.60+ (`az version`), Git, Node.js 18+ (for Azurite or the npm install of Core Tools).
- Install Azure Functions Core Tools v4:

```bash
# Ubuntu / Debian
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs 2>/dev/null)-prod $(lsb_release -cs 2>/dev/null) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update && sudo apt-get install -y azure-functions-core-tools-4

# macOS
brew tap azure/functions
brew install azure-functions-core-tools@4

# Any OS with Node.js
npm install -g azure-functions-core-tools@4 --unsafe-perm true

func --version   # expect 4.x
```

- Install Azurite (storage emulator):

```bash
npm install -g azurite
```

- Cost warning: Flex Consumption and Consumption are cheap for a lab (free grants cover small usage), but Storage, Application Insights ingestion and the Logic App runs are billed. A recurrence every hour is fine; every second is not. Delete the resource group at the end.

### Folder structure

```text
func-hello-python/
|-- .github/
|   `-- workflows/
|       `-- deploy-function.yml
|-- tests/
|   `-- test_function_app.py
|-- .funcignore
|-- .gitignore
|-- function_app.py
|-- host.json
|-- local.settings.json      (NOT committed)
|-- requirements.txt
`-- logicapp/
    `-- workflow.json
```

### Step-by-step

#### Step 1: Create the project with Core Tools

```bash
mkdir func-hello-python && cd func-hello-python
python3.12 -m venv .venv
source .venv/bin/activate

func init . --python
```

What this does:

- The virtual environment keeps project packages separate from your system Python. Core Tools uses the active environment.
- `func init --python` creates `function_app.py`, `host.json`, `local.settings.json`, `requirements.txt`, `.funcignore` and `.gitignore`. Recent Core Tools versions use the **v2 model by default** (older versions needed `--model V2`).

#### Step 2: Write the HTTP function

Replace `function_app.py` with this:

```python
import json
import logging

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="hello", methods=["GET", "POST"])
def hello(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("hello function received a %s request", req.method)

    name = req.params.get("name")
    if not name:
        try:
            body = req.get_json()
        except ValueError:
            body = {}
        name = body.get("name") if isinstance(body, dict) else None

    message = "Hello from Azure Functions"
    if name:
        message = f"{message}, {name}!"

    return func.HttpResponse(
        json.dumps({"message": message}),
        status_code=200,
        mimetype="application/json",
    )
```

What this does:

- `func.FunctionApp(...)` is the v2 entry point. The host indexes decorated functions from this file.
- `http_auth_level=func.AuthLevel.FUNCTION` makes callers send a function key. You can override per function with `@app.route(..., auth_level=func.AuthLevel.ANONYMOUS)`.
- `@app.route(route="hello")` creates an **HTTP trigger** and an **HTTP output binding**. The URL is `/api/hello` because `api` is the default route prefix.
- It reads `name` from the query string first, then from a JSON body, so both GET and POST work.
- `logging.info` goes to the console locally and to Application Insights in Azure.

#### Step 3: Check host.json, requirements.txt and local.settings.json

`host.json` (generated, shown for reference):

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

`requirements.txt`:

```text
azure-functions
```

`local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true"
  }
}
```

What this does:

- `host.json` holds runtime settings for the whole app. The **extension bundle** brings in binding extensions (Storage, Service Bus, and so on) without you installing NuGet packages.
- `requirements.txt` lists Python packages. They are installed during build, either on the runner or in Azure (remote build).
- `local.settings.json` is used **only** by Core Tools locally. Its `Values` become environment variables, like App Settings in Azure. It often holds connection strings, so it is in `.gitignore` and **must not be committed**. In Azure you set the same values as App Settings (or Key Vault references).
- `UseDevelopmentStorage=true` points to Azurite.

Confirm `.gitignore` contains it:

```bash
grep -n "local.settings.json" .gitignore || echo "local.settings.json" >> .gitignore
```

#### Step 4: Run and test locally

```bash
# Terminal 1: storage emulator
azurite --silent --location ./.azurite --debug ./.azurite/debug.log

# Terminal 2: install packages and start the host
source .venv/bin/activate
pip install -r requirements.txt
func start
```

Expected output from `func start` (shortened):

```text
Functions:

        hello: [GET,POST] http://localhost:7071/api/hello
```

Test it:

```bash
curl -s "http://localhost:7071/api/hello"
# {"message": "Hello from Azure Functions"}

curl -s "http://localhost:7071/api/hello?name=Sam"
# {"message": "Hello from Azure Functions, Sam!"}

curl -s -X POST "http://localhost:7071/api/hello" \
  -H "Content-Type: application/json" -d '{"name":"Logic App"}'
# {"message": "Hello from Azure Functions, Logic App!"}
```

What this does:

- Locally, function keys are **not enforced**, so you do not need `?code=`.
- Add `.azurite` to `.gitignore` too.

#### Step 5: Add a unit test

v2 functions are plain Python, so you can unit test them by building an `HttpRequest`.

`tests/test_function_app.py`:

```python
import json

import azure.functions as func

from function_app import hello


def call(req):
    # In the v2 model the decorator wraps the function; build() returns the user function
    return hello.build().get_user_function()(req)


def test_hello_default():
    req = func.HttpRequest(method="GET", url="/api/hello", body=b"", params={})
    resp = call(req)
    assert resp.status_code == 200
    assert json.loads(resp.get_body())["message"] == "Hello from Azure Functions"


def test_hello_with_name():
    req = func.HttpRequest(method="GET", url="/api/hello", body=b"", params={"name": "Sam"})
    resp = call(req)
    assert json.loads(resp.get_body())["message"] == "Hello from Azure Functions, Sam!"
```

```bash
pip install pytest
python -m pytest -q
```

What this does:

- `hello.build().get_user_function()` gets the original function behind the decorator. This is the pattern shown in the Python v2 docs; if your `azure-functions` version differs, call the logic through a separate helper function instead.
- Tests run in CI before deployment, so a broken function never reaches Azure.

#### Step 6: Create the Azure resources (Flex Consumption)

```bash
LOCATION=eastus
RG=rg-func-hello
STORAGE=stfunchello$RANDOM        # 3-24 lowercase letters/numbers, globally unique
FUNCAPP=func-hello-$RANDOM        # globally unique
echo "STORAGE=$STORAGE FUNCAPP=$FUNCAPP"

az group create --name $RG --location $LOCATION

az storage account create \
  --name $STORAGE \
  --resource-group $RG \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false

# Check which regions support Flex Consumption
az functionapp list-flexconsumption-locations -o table

az functionapp create \
  --resource-group $RG \
  --name $FUNCAPP \
  --storage-account $STORAGE \
  --flexconsumption-location $LOCATION \
  --runtime python \
  --runtime-version 3.12
```

What this does:

- Every Function App needs a Storage account for keys, triggers state and (on Flex) the deployment package container.
- `--flexconsumption-location` creates the app on a **Flex Consumption** plan in that region. Optional flags include `--instance-memory 2048` and `--maximum-instance-count 40`.
- `--runtime python --runtime-version 3.12` sets the language stack. Flex Consumption is Linux only.
- An **Application Insights** resource is created and connected automatically (the `APPLICATIONINSIGHTS_CONNECTION_STRING` app setting). Use `--app-insights <name>` to reuse one, or `--disable-app-insights` to skip it.

Classic Consumption alternative (older plan, still widely used in interviews):

```bash
az functionapp create \
  --resource-group $RG \
  --name $FUNCAPP \
  --storage-account $STORAGE \
  --consumption-plan-location $LOCATION \
  --os-type Linux \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4
```

Note: Microsoft recommends Flex Consumption for new serverless Linux apps. Linux Consumption is a legacy option with an announced retirement and does not get new language versions, so check the supported Python versions in the docs before choosing it.

#### Step 7: Understand function keys and auth levels

```bash
# Function-level keys for the hello function
az functionapp function keys list -g $RG -n $FUNCAPP --function-name hello

# Host-level keys (work for all functions in the app)
az functionapp keys list -g $RG -n $FUNCAPP

# Create a named key for a specific caller (easy to revoke later)
az functionapp function keys set -g $RG -n $FUNCAPP --function-name hello \
  --key-name logicapp
```

What this does:

- **Auth levels**:
  - `ANONYMOUS`: no key needed.
  - `FUNCTION`: needs a function key for this function or a host key.
  - `ADMIN`: needs the master key (never give this out).
- The key is sent as `?code=<key>` or in the `x-functions-key` header. The header is better because URLs end up in logs.
- Keys are shared secrets, not identity. For real APIs, put **App Service Authentication (Easy Auth)** with Entra ID in front, or use API Management, and keep keys as an extra layer.
- `keys set` without `--key-value` generates a random value. Run the `keys list` command again to read it.

#### Step 8: Set up OIDC from GitHub to Azure

```bash
GH_OWNER=<owner>
GH_REPO=func-hello-python

az identity create --resource-group $RG --name id-github-func
GH_CLIENT_ID=$(az identity show -g $RG -n id-github-func --query clientId -o tsv)
GH_PRINCIPAL_ID=$(az identity show -g $RG -n id-github-func --query principalId -o tsv)

az identity federated-credential create \
  --resource-group $RG \
  --identity-name id-github-func \
  --name github-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:$GH_OWNER/$GH_REPO:ref:refs/heads/main \
  --audiences api://AzureADTokenExchange

FUNC_ID=$(az functionapp show -g $RG -n $FUNCAPP --query id -o tsv)
az role assignment create \
  --assignee-object-id $GH_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Website Contributor" \
  --scope $FUNC_ID

gh secret set AZURE_CLIENT_ID --body "$GH_CLIENT_ID" --repo $GH_OWNER/$GH_REPO
gh secret set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)" --repo $GH_OWNER/$GH_REPO
gh secret set AZURE_SUBSCRIPTION_ID --body "$(az account show --query id -o tsv)" --repo $GH_OWNER/$GH_REPO
gh variable set FUNCTION_APP_NAME --body "$FUNCAPP" --repo $GH_OWNER/$GH_REPO
```

What this does:

- The managed identity is the deploy identity. The federated credential lets only the `main` branch of your repo use it.
- **Website Contributor** on just this Function App is enough to deploy code. If deployment fails with a permissions error on the deployment storage container, also grant **Storage Blob Data Contributor** on the storage account.
- No publish profile is downloaded. Publish profiles contain basic-auth credentials and many teams disable SCM basic auth entirely.

#### Step 9: Write the GitHub Actions workflow

`.github/workflows/deploy-function.yml`:

```yaml
name: deploy-function

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  PYTHON_VERSION: "3.12"
  PACKAGE_PATH: "."

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies and run tests
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pytest
          python -m pytest -q

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy to Azure Functions (Flex Consumption)
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ vars.FUNCTION_APP_NAME }}
          package: ${{ env.PACKAGE_PATH }}
          sku: flexconsumption
          remote-build: true
```

What this does:

- `id-token: write` lets the job get the OIDC token used by `azure/login@v2`.
- `setup-python` uses the same Python version as the Function App. Mismatched versions cause native packages to break.
- Tests run before login, so a failing test stops the job before anything touches Azure.
- `Azure/functions-action@v1` zips the folder (respecting `.funcignore`) and deploys it. With `sku: flexconsumption` and `remote-build: true`, Azure installs `requirements.txt` on Linux in the cloud, which avoids "works on my machine" problems with compiled packages.

**Option B: classic Consumption / Premium / Dedicated (Linux)**

Use either a remote build:

```yaml
      - name: Deploy (remote build)
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ vars.FUNCTION_APP_NAME }}
          package: .
          scm-do-build-during-deployment: true
          enable-oryx-build: true
```

or build the packages yourself into the folder the Python worker reads:

```yaml
      - name: Install packages into the deployment folder
        run: |
          pip install --target=".python_packages/lib/site-packages" -r requirements.txt

      - name: Deploy (prebuilt packages)
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ vars.FUNCTION_APP_NAME }}
          package: .
```

What this does:

- `scm-do-build-during-deployment` + `enable-oryx-build` ask the Kudu/Oryx build service to run `pip install` in Azure.
- `.python_packages/lib/site-packages` is the path the Functions Python worker adds to `sys.path`, so packages installed there are found at runtime. The runner must be Linux with the same Python version.
- Make sure `.funcignore` excludes `.venv`, `tests` and `.azurite` so the package stays small:

```text
.git*
.venv
.azurite
tests
__pycache__
local.settings.json
```

#### Step 10: Push and deploy

```bash
git init -b main
git add .
git commit -m "Python v2 HTTP function with GitHub Actions"
git remote add origin https://github.com/<owner>/func-hello-python.git
git push -u origin main

gh run watch --repo <owner>/func-hello-python
```

#### Step 11: Look at the function in Application Insights

```bash
az monitor app-insights component show -g $RG --app $FUNCAPP \
  --query "{name:name, connectionString:connectionString}" -o json
```

If the extension is missing, run `az extension add --name application-insights`. In the portal, open Application Insights -> **Logs** and run:

```kusto
requests
| where timestamp > ago(30m)
| where name == "hello"
| project timestamp, name, resultCode, duration, success
| order by timestamp desc
```

```kusto
traces
| where timestamp > ago(30m)
| where message has "hello function received"
| project timestamp, message, severityLevel
```

What this does:

- `requests` shows each invocation, its status code and duration. Spikes in `duration` on the first call after idle are cold starts.
- `traces` shows your `logging.info` lines.
- The Application Insights name usually matches the Function App name when created automatically. If not, use `az monitor app-insights component list -g $RG -o table`.

#### Step 12 (bonus): Call the function from a Logic App (Consumption)

A Logic App can call the function on a schedule or from another trigger. Here a Recurrence trigger sends a POST every hour.

`logicapp/workflow.json`:

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {},
    "triggers": {
      "Recurrence": {
        "type": "Recurrence",
        "recurrence": {
          "frequency": "Hour",
          "interval": 1
        }
      }
    },
    "actions": {
      "Call_hello_function": {
        "type": "Http",
        "runAfter": {},
        "inputs": {
          "method": "POST",
          "uri": "https://<function-host>/api/hello",
          "headers": {
            "Content-Type": "application/json",
            "x-functions-key": "<logicapp-function-key>"
          },
          "body": {
            "name": "Logic App"
          }
        }
      }
    },
    "outputs": {}
  }
}
```

```bash
az extension add --name logic

FUNC_HOST=$(az functionapp show -g $RG -n $FUNCAPP --query defaultHostName -o tsv)
FUNC_KEY=$(az functionapp function keys list -g $RG -n $FUNCAPP --function-name hello --query logicapp -o tsv)

# Fill placeholders into a temp copy (never commit the real key)
sed -e "s|<function-host>|$FUNC_HOST|" -e "s|<logicapp-function-key>|$FUNC_KEY|" \
  logicapp/workflow.json > /tmp/workflow.filled.json

az logic workflow create \
  --resource-group $RG \
  --location $LOCATION \
  --name la-call-hello \
  --definition /tmp/workflow.filled.json

rm /tmp/workflow.filled.json

# Run the trigger now instead of waiting an hour
SUB_ID=$(az account show --query id -o tsv)
az rest --method post \
  --url "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Logic/workflows/la-call-hello/triggers/Recurrence/run?api-version=2016-06-01"
```

What this does:

- The **Recurrence** trigger starts a run every hour. The **HTTP** action sends a POST with a JSON body to the function.
- The function key travels in the `x-functions-key` header. A named key (`logicapp`) can be revoked without affecting other callers.
- In the portal designer you can also use the built-in **Azure Functions** action, which lists the functions in your subscription and handles the key for you.
- Better security: enable a managed identity on the Logic App, turn on Entra ID authentication (Easy Auth) on the Function App, and set the HTTP action's **Authentication** to Managed identity. Then no key is stored in the workflow.

Check the run:

```bash
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Logic/workflows/la-call-hello/runs?api-version=2016-06-01" \
  --query "value[0].properties.status" -o tsv
# Expected: Succeeded
```

#### Step 13: Understand triggers vs bindings, cold start and hosting plans

**Triggers vs bindings**

- A **trigger** is what starts the function. Every function has exactly one trigger (HTTP, Timer, Queue, Blob, Event Grid, Service Bus, Cosmos DB, and so on).
- A **binding** connects the function to data declaratively. **Input bindings** read data (for example a blob) and **output bindings** write data (for example a queue message) without you writing SDK code. A function can have zero or more bindings.
- In this project, `@app.route` creates an HTTP trigger and an HTTP output binding (the response).

**Cold start**

- On scale-to-zero plans, when no instance is running, the first request must wait for an instance to be allocated, the runtime to start and your Python packages to load. That delay is a cold start (often one to several seconds for Python).
- Reduce it with: Flex Consumption **always-ready instances**, Premium plan **pre-warmed instances**, Dedicated plan with Always On, smaller dependency sets, and lazy imports.

**Hosting plans**

| Plan | Scale to zero | Cold start | Max timeout | VNet integration | OS | Typical use |
| --- | --- | --- | --- | --- | --- | --- |
| Flex Consumption | Yes | Yes, reduced with always-ready instances | Default 30 min, can be unbounded | Yes | Linux | Default choice for new serverless apps |
| Consumption (classic) | Yes | Yes | 5 min default, 10 min max | No | Windows; Linux is legacy | Existing apps, light or spiky workloads |
| Premium (Elastic Premium EP1-EP3) | No (min 1 instance) | No, pre-warmed instances | Default 30 min, can be unbounded | Yes | Windows and Linux | Steady load, low latency, long runs |
| Dedicated (App Service plan) | No | No with Always On | Unbounded with Always On | Yes (Standard+) | Windows and Linux | Reuse existing App Service capacity, predictable cost |

Note: HTTP-triggered functions must respond within about 230 seconds on every plan because of the front-end load balancer timeout. Use the Durable Functions async pattern for longer work.

### Verify it works

```bash
FUNC_HOST=$(az functionapp show -g $RG -n $FUNCAPP --query defaultHostName -o tsv)
FUNC_KEY=$(az functionapp function keys list -g $RG -n $FUNCAPP --function-name hello --query default -o tsv)

# Without a key: should be rejected
curl -s -o /dev/null -w "%{http_code}\n" "https://$FUNC_HOST/api/hello"
# Expected: 401

# With a key in the header
curl -s "https://$FUNC_HOST/api/hello?name=Sam" -H "x-functions-key: $FUNC_KEY"
# Expected: {"message": "Hello from Azure Functions, Sam!"}

# POST
curl -s -X POST "https://$FUNC_HOST/api/hello" -H "x-functions-key: $FUNC_KEY" \
  -H "Content-Type: application/json" -d '{"name":"CI"}'
# Expected: {"message": "Hello from Azure Functions, CI!"}

# Function is listed
az functionapp function list -g $RG -n $FUNCAPP --query "[].name" -o tsv
# Expected: <funcapp>/hello

# Runtime settings
az functionapp show -g $RG -n $FUNCAPP --query "{state:state,host:defaultHostName}"
```

Also confirm the GitHub Actions run is green and Application Insights `requests` shows your calls.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `func start` says "No job functions found" | Wrong folder, syntax error, or v1/v2 mix | Run from the project root; check `function_app.py` imports; run `python -c "import function_app"` |
| Local start fails connecting to storage | Azurite not running | Start Azurite, or for HTTP-only testing set `AzureWebJobsStorage` to a real storage connection string |
| `ModuleNotFoundError` in Azure | Packages not installed during deploy | Use `remote-build: true` (Flex) or `scm-do-build-during-deployment` / `.python_packages` (other plans) |
| Function list is empty in portal after deploy | Indexing error at startup, Python version mismatch | Check Application Insights `traces` and `exceptions`; match Python versions |
| 401 Unauthorized | Missing or wrong function key | Send `x-functions-key` or `?code=`; check the key belongs to this function or is a host key |
| `azure/login` OIDC fails | Missing `id-token: write` or subject mismatch | Add permissions; align federated credential subject with branch/environment |
| Deploy fails with 403 on storage | Deploy identity cannot write to the Flex deployment container | Grant Storage Blob Data Contributor on the storage account to the deploy identity |
| `--flexconsumption-location` not recognized | Old Azure CLI | `az upgrade` |
| First request slow (several seconds) | Cold start | Configure always-ready instances (Flex) or use Premium |
| Logic App run fails with 401 | Wrong key or placeholder not replaced | Re-read the key, update the HTTP action headers |

### Clean up

```bash
az group delete --name $RG --yes --no-wait

# Optional: remove GitHub secrets and variables
gh secret delete AZURE_CLIENT_ID --repo <owner>/func-hello-python
gh secret delete AZURE_TENANT_ID --repo <owner>/func-hello-python
gh secret delete AZURE_SUBSCRIPTION_ID --repo <owner>/func-hello-python
gh variable delete FUNCTION_APP_NAME --repo <owner>/func-hello-python
```

This removes the Function App, its plan, Storage, Application Insights, the Logic App and the deploy identity.

### Next improvements

- Define the Function App, storage and roles in Bicep, using managed identity for `AzureWebJobsStorage` (`AzureWebJobsStorage__accountName`) instead of a connection string.
- Turn on Entra ID authentication (Easy Auth) and let the Logic App call with its managed identity.
- Add a second function with a Queue or Service Bus trigger and an output binding to see bindings in action.
- Configure always-ready instances on Flex Consumption to reduce cold starts for the HTTP function.
- Add a staging environment with a second Function App and a GitHub environment with required reviewers.
- Add alerts in Azure Monitor on failure rate and duration.
- Put Azure API Management in front for rate limiting and a stable public API.

### How to explain this project in an interview

> "This was a hands-on practice project to learn serverless on Azure with a proper pipeline. I wrote a Python HTTP function with the v2 programming model, so the trigger is just a decorator in function_app.py, and tested it locally with Core Tools and Azurite. local.settings.json stays out of Git because it can hold connection strings. In Azure I created a Storage account and a Function App on the Flex Consumption plan with Python 3.12 and Application Insights. The function uses function-level auth, so callers need a key in the x-functions-key header. GitHub Actions runs the unit tests, logs in to Azure with OIDC using a managed identity with a federated credential, and deploys with the functions action using remote build, so packages are built on Linux in Azure. As a bonus, a Consumption Logic App calls the function on a schedule with an HTTP POST."

Points that impress interviewers:

- You can explain triggers vs bindings and name the plan differences (timeouts, cold start, VNet, scale to zero).
- You know function keys are shared secrets and suggest Easy Auth with managed identity for service-to-service calls.
- You understand why remote build matters for Python native packages, and the `.python_packages/lib/site-packages` alternative.
- You use OIDC instead of publish profiles, and scope the deploy identity to just the Function App.

## Interview Questions

<details><summary>Q1. [Basic] What is the difference between a trigger and a binding in Azure Functions?</summary>

**Answer:**

A **trigger** starts the function and provides the input event. Each function has exactly one trigger, such as HTTP, Timer, Queue Storage, Service Bus, Event Grid or Blob. A **binding** is a declarative connection to another service. Input bindings read data and pass it as a parameter; output bindings write data from your return value or an output parameter. Bindings are optional and you can have several. For example, a Service Bus trigger with a Cosmos DB output binding reads a message and writes a document without any SDK code.

</details>

<details><summary>Q2. [Basic] What is the Python v2 programming model?</summary>

**Answer:**

In the v1 model, each function had its own folder with `__init__.py` and a `function.json` describing triggers and bindings. In the v2 model, functions are defined in code with decorators on a `func.FunctionApp()` object, for example `@app.route(route="hello")`, `@app.timer_trigger(...)` or `@app.queue_output(...)`. It is code-first, easier to read and test, and supports Blueprints to split functions across files. The host finds functions by indexing the decorated code at startup.

</details>

<details><summary>Q3. [Basic] Why should <code>local.settings.json</code> not be committed?</summary>

**Answer:**

It is the local equivalent of App Settings and often contains connection strings, keys and other secrets. It is only read by Core Tools on your machine; Azure never uses it. That is why `func init` adds it to `.gitignore`. In Azure you set the same values as App Settings, ideally as Key Vault references or identity-based connections (for example `AzureWebJobsStorage__accountName`) so no secret is stored at all. Teams often commit a `local.settings.sample.json` with placeholder values.

</details>

<details><summary>Q4. [Intermediate] Compare Flex Consumption, Consumption, Premium and Dedicated plans.</summary>

**Answer:**

- **Flex Consumption**: serverless, Linux, scale to zero, fast per-function scaling, VNet integration, configurable instance memory, optional always-ready instances; default timeout 30 minutes and can be unbounded. Recommended for new serverless apps.
- **Consumption (classic)**: serverless, scale to zero, 5-minute default and 10-minute max timeout, no VNet integration; Linux Consumption is legacy.
- **Premium**: always at least one warm instance plus pre-warmed buffers, no cold start, VNet, bigger instances, long timeouts; you pay for minimum instances all the time.
- **Dedicated (App Service plan)**: runs on VMs you already pay for; predictable cost; needs Always On; scaling is the plan's autoscale.

Pick based on latency needs, networking, run duration and cost model.

</details>

<details><summary>Q5. [Intermediate] What is a cold start, and how do you reduce it?</summary>

**Answer:**

When a scale-to-zero app has no running instance, the first request waits for the platform to allocate an instance, start the Functions host and the Python worker, and import your packages. This can take a few seconds. Ways to reduce it: Flex Consumption always-ready instances, Premium plan pre-warmed instances, Dedicated plan with Always On, fewer and lighter dependencies, lazy imports inside the function, and avoiding heavy work at module import time. A Timer trigger "keep-warm" ping is a hack and does not help when the app scales out to new instances.

</details>

<details><summary>Q6. [Intermediate] After deployment the portal shows no functions, but it worked locally. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

This usually means the host failed to index `function_app.py`. Steps:

1. Check Application Insights `exceptions` and `traces` (or the Log stream) for import errors such as `ModuleNotFoundError`.
2. Confirm packages were installed: remote build enabled (`remote-build: true` on Flex, or `scm-do-build-during-deployment` on other plans), or packages placed in `.python_packages/lib/site-packages`.
3. Confirm the Python version in Azure matches the one you built with.
4. Confirm `function_app.py` and `host.json` are at the root of the deployed package and not excluded by `.funcignore`.
5. Confirm `FUNCTIONS_WORKER_RUNTIME=python` is set (on classic plans).
6. Restart the app and check again.

</details>

<details><summary>Q7. [Intermediate] What are the HTTP auth levels, and are function keys enough for security?</summary>

**Answer:**

`ANONYMOUS` needs no key, `FUNCTION` needs a function key or host key, and `ADMIN` needs the master key. Keys are passed as `?code=` or `x-functions-key`. Keys are shared secrets: they do not identify the caller, are easy to leak in URLs and logs, and need rotation. For production, add **App Service Authentication** with Entra ID so callers present tokens (users or managed identities), or put **API Management** in front with OAuth validation, rate limits and IP restrictions. Private endpoints can remove public exposure entirely.

</details>

<details><summary>Q8. [Advanced] How does the GitHub Actions deployment authenticate without a publish profile, and what permissions does it need? <em>(scenario)</em></summary>

**Answer:**

The workflow has `permissions: id-token: write`, so GitHub issues an OIDC token with a subject like `repo:<owner>/<repo>:ref:refs/heads/main`. `azure/login@v2` exchanges it for an Entra ID token because a user-assigned managed identity (or app registration) has a federated credential with that issuer, subject and audience `api://AzureADTokenExchange`. `Azure/functions-action@v1` then deploys using that Azure login. The identity needs **Website Contributor** (or Contributor) on the Function App. On Flex Consumption, if deployment storage uses identity-based access, the deploying identity may also need **Storage Blob Data Contributor** on the deployment storage account. No publish profile means you can disable SCM basic auth entirely.

</details>

<details><summary>Q9. [Advanced] An HTTP function must process a job that takes 15 minutes. How do you design it? <em>(scenario)</em></summary>

**Answer:**

Do not keep the HTTP request open: the front-end load balancer times out HTTP requests after about 230 seconds regardless of plan. Instead:

- Use **Durable Functions** with the async HTTP API pattern: the HTTP starter function starts an orchestration and returns `202 Accepted` with a status URL; the client polls it.
- Or have the HTTP function put a message on a queue (Storage Queue or Service Bus output binding) and return `202`, and a queue-triggered function does the work.

Then choose a plan whose execution timeout covers 15 minutes: Flex Consumption, Premium or Dedicated (classic Consumption stops at 10 minutes). Make the worker idempotent so retries are safe.

</details>

<details><summary>Q10. [Basic] Why does a Function App need a Storage account?</summary>

**Answer:**

The Functions host uses `AzureWebJobsStorage` for internal state: function keys, timer trigger schedule state and singleton locks, blob trigger receipts, and Durable Functions state. On Flex Consumption it also stores the deployment package in a blob container. If the storage account is deleted, firewalled without the right network setup, or the connection is wrong, the app fails to start. Best practice is identity-based connections (`AzureWebJobsStorage__accountName` plus Storage Blob, Queue and Table data roles) instead of a connection string.

</details>
