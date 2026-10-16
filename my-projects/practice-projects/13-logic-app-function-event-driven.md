# Practice Project 13: Event-Driven Processing with Logic App, Azure Functions and Cosmos DB

> A hands-on guide to building a small event-driven pipeline: a file lands in Blob Storage, a Consumption Logic App picks it up and calls a Python Azure Function, and the Function validates, enriches and saves the data to Cosmos DB, all with managed identities and monitored with Application Insights.

## Key Concepts

### What you will build

- A **Storage account** with an `incoming` container where order files (JSON or CSV) are uploaded.
- A **Consumption Logic App** that triggers when a blob is added, reads its content and calls a Function.
- A **Python Azure Function** (v2 programming model, HTTP trigger) that parses the file, validates each record, adds extra fields, and writes documents to **Cosmos DB for NoSQL** through an **output binding** that uses a **managed identity** (no Cosmos keys).
- **Error handling** in the Logic App (Try/Catch scopes and retry policy).
- **Monitoring** with Logic App run history and **Application Insights** KQL.
- An **Event Grid** alternative design, with trade-offs.

The final result: you upload `orders-001.json`, and within about a minute the orders appear as documents in Cosmos DB, the Logic App run shows green, and App Insights shows the Function request.

### Architecture

```text
 User / system
     |
     | upload orders-001.json
     v
 +------------------------+      polls every 1 min       +------------------------------+
 | Storage account        |<-----------------------------| Logic App (Consumption)      |
 |  container: incoming   |  "When a blob is added or    |  system-assigned MI          |
 +------------------------+   modified (V2)" + "Get blob |  Try scope:                  |
                              content (V2)" via MI       |   - Get blob content (V2)    |
                                                         |   - Call Function (retry)    |
                                                         |  Catch scope: log + fail     |
                                                         +---------------+--------------+
                                                                         | HTTPS POST
                                                                         v
 +------------------------+   output binding (MI)       +------------------------------+
 | Cosmos DB for NoSQL    |<----------------------------| Function App (Python, Flex)  |
 |  db: ordersdb          |  role: Cosmos DB Built-in   |  process_blob (HTTP trigger) |
 |  container: orders     |  Data Contributor           |  system-assigned MI          |
 |  partition key:        |  (data-plane RBAC)          +---------------+--------------+
 |   /customerId          |                                             | telemetry
 +------------------------+                                             v
                                                         +------------------------------+
                                                         | Application Insights         |
                                                         +------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Blob Storage | Landing zone for incoming files | Cheap, simple, many producers can upload |
| Logic App (Consumption) | Orchestrates: trigger, read blob, call Function, handle errors | Low-code, built-in connectors, visual run history, pay per action |
| Azure Functions (Python v2) | Parses, validates and enriches data | Real code for business logic; scales automatically |
| Cosmos DB for NoSQL | Stores processed orders as JSON documents | Fast reads and writes, flexible schema |
| Managed identities | Logic App to Storage, Function to Cosmos | No keys or connection strings |
| Application Insights | Requests, logs, failures for the Function | Built-in Functions integration and KQL |
| Event Grid (alternative) | Push events on BlobCreated | Lower latency than polling |

### Prerequisites

- Azure subscription with Owner (or Contributor + User Access Administrator) on a resource group.
- Azure CLI 2.60 or later, and the `logic` extension (`az extension add --name logic`).
- Azure Functions Core Tools v4 (`func --version` shows `4.x`).
- Python 3.11 locally.
- **Cost warning**: Logic App Consumption charges per trigger poll and action (polling every minute adds up slowly even with no files). Cosmos DB serverless, Flex Consumption Functions and App Insights are low cost for a lab, but delete everything at the end.

### Folder structure

```text
event-driven-orders/
├── setup.sh
├── function-app/
│   ├── function_app.py
│   ├── host.json
│   ├── local.settings.json      # local only, not committed
│   └── requirements.txt
├── logic-app/
│   ├── empty-workflow.json
│   └── workflow.json
├── samples/
│   ├── orders-001.json
│   └── orders-002.csv
└── queries/
    └── monitoring.kql
```

### Step-by-step

#### Step 1: Set variables and create the resource group

```bash
RG=rg-eventdriven-lab
LOC=eastus
SUFFIX=$RANDOM
DATA_ST=stdata$SUFFIX          # storage for incoming files
FUNC_ST=stfunc$SUFFIX          # storage used by the Function App runtime
COSMOS=cosmos-orders-$SUFFIX
FUNC=func-orders-$SUFFIX
LA=la-orders-$SUFFIX
SUB_ID=$(az account show --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)

az group create --name $RG --location $LOC
```

What this does:

- Storage account names must be 3-24 lowercase letters and digits, globally unique. That is why the names have no hyphens.
- Two storage accounts keep the data separate from the Function runtime storage. This is a good habit for security and clean permissions.

#### Step 2: Create the data storage account and container

```bash
az storage account create --name $DATA_ST --resource-group $RG --location $LOC \
  --sku Standard_LRS --kind StorageV2 \
  --allow-blob-public-access false --min-tls-version TLS1_2

DATA_ST_ID=$(az storage account show -n $DATA_ST -g $RG --query id -o tsv)

# Let yourself upload with Entra ID (no account keys)
az role assignment create --assignee-object-id $ME --assignee-principal-type User \
  --role "Storage Blob Data Contributor" --scope $DATA_ST_ID

az storage container create --account-name $DATA_ST --name incoming --auth-mode login
```

What this does:

- `--allow-blob-public-access false` stops anyone from making a container public.
- `--auth-mode login` uses your Entra ID login instead of account keys. It needs the data role above, which can take a minute or two to apply.

#### Step 3: Create Cosmos DB, database and container

```bash
az cosmosdb create --name $COSMOS --resource-group $RG \
  --locations regionName=$LOC failoverPriority=0 isZoneRedundant=false \
  --capabilities EnableServerless \
  --default-consistency-level Session

az cosmosdb sql database create --account-name $COSMOS --resource-group $RG --name ordersdb

az cosmosdb sql container create --account-name $COSMOS --resource-group $RG \
  --database-name ordersdb --name orders \
  --partition-key-path "/customerId"

COSMOS_ENDPOINT=$(az cosmosdb show -n $COSMOS -g $RG --query documentEndpoint -o tsv)
echo $COSMOS_ENDPOINT
```

What this does:

- **Serverless** bills per request unit (RU) used. It is ideal for spiky or low traffic labs. Provisioned throughput fits steady, predictable load.
- **Partition key `/customerId`**: queries such as "all orders for a customer" stay in one logical partition, and writes spread across many customers. A bad choice would be `/status` (few values, hot partitions) or `/createdDate` (all new writes hit one partition).
- The partition key cannot be changed later without moving the data to a new container. Choose it from your main query pattern.
- The Function's output binding writes into this existing container. It does not need permission to create containers.

Optional hardening: disable key-based auth so only Entra ID can access data:

```bash
az resource update --resource-type "Microsoft.DocumentDB/databaseAccounts" \
  --name $COSMOS --resource-group $RG --set properties.disableLocalAuth=true
```

#### Step 4: Create the Function App with a managed identity

```bash
az storage account create --name $FUNC_ST --resource-group $RG --location $LOC \
  --sku Standard_LRS --allow-blob-public-access false

az functionapp create --name $FUNC --resource-group $RG \
  --storage-account $FUNC_ST \
  --flexconsumption-location $LOC \
  --runtime python --runtime-version 3.11

az functionapp identity assign --name $FUNC --resource-group $RG
FUNC_PRINCIPAL_ID=$(az functionapp identity show -n $FUNC -g $RG --query principalId -o tsv)
```

What this does:

- **Flex Consumption** is the current serverless plan for Functions. It scales per function, supports VNet integration and always-ready instances.
- `az functionapp create` also creates an Application Insights resource by default and sets `APPLICATIONINSIGHTS_CONNECTION_STRING`. Check with `az functionapp config appsettings list`.
- The system-assigned identity is what the Function uses to talk to Cosmos DB.

#### Step 5: Grant the Function a Cosmos DB data-plane role

Cosmos DB has two separate RBAC systems. This is a very common interview topic.

| Plane | What it controls | How you assign |
| --- | --- | --- |
| Control plane (Azure RBAC) | Create accounts, databases, containers, change throughput, keys | `az role assignment create` (for example "DocumentDB Account Contributor") |
| Data plane (Cosmos DB native RBAC) | Read and write items, run queries | `az cosmosdb sql role assignment create` |

Azure RBAC roles like Contributor do **not** give access to items. Use the built-in data-plane role:

```bash
# 00000000-0000-0000-0000-000000000002 = Cosmos DB Built-in Data Contributor
# 00000000-0000-0000-0000-000000000001 = Cosmos DB Built-in Data Reader
az cosmosdb sql role assignment create \
  --account-name $COSMOS --resource-group $RG \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --principal-id $FUNC_PRINCIPAL_ID \
  --scope "/"

# Also give yourself data access, so you can check results and run the Function locally
az cosmosdb sql role assignment create \
  --account-name $COSMOS --resource-group $RG \
  --role-definition-id 00000000-0000-0000-0000-000000000002 \
  --principal-id $ME \
  --scope "/"
```

What this does:

- `--scope "/"` means the whole account. You can narrow it to `/dbs/ordersdb` or `/dbs/ordersdb/colls/orders`.
- These assignments do not show in the portal's normal **Access control (IAM)** blade. List them with `az cosmosdb sql role assignment list -a $COSMOS -g $RG`.

Now set the identity-based connection setting:

```bash
az functionapp config appsettings set --name $FUNC --resource-group $RG --settings \
  "CosmosDb__accountEndpoint=$COSMOS_ENDPOINT"
```

What this does:

- The binding's `connection="CosmosDb"` setting looks for `CosmosDb__accountEndpoint`. When it finds an endpoint instead of a connection string, it uses the managed identity (`DefaultAzureCredential` style). No key is stored anywhere.
- For a user-assigned identity, also add `CosmosDb__credential=managedidentity` and `CosmosDb__clientId=<client-id>`.

#### Step 6: Write the Function

File `function-app/host.json`:

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": { "isEnabled": true, "excludedTypes": "Request;Exception" }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

```text
# function-app/requirements.txt
azure-functions
```

```python
# function-app/function_app.py
import base64
import csv
import io
import json
import logging
from datetime import datetime, timezone

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

REQUIRED_FIELDS = ("orderId", "customerId", "amount")
TAX_RATE = 0.08


def parse_records(file_name: str, raw: str) -> list[dict]:
    """Return a list of dicts from JSON (array) or CSV text."""
    if file_name.lower().endswith(".csv"):
        return list(csv.DictReader(io.StringIO(raw)))
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def validate(record: dict) -> list[str]:
    errors = [f"missing {f}" for f in REQUIRED_FIELDS if not record.get(f)]
    try:
        if float(record.get("amount", 0)) <= 0:
            errors.append("amount must be > 0")
    except (TypeError, ValueError):
        errors.append("amount is not a number")
    return errors


def enrich(record: dict, source: str) -> dict:
    amount = round(float(record["amount"]), 2)
    return {
        "id": str(record["orderId"]),            # Cosmos document id
        "customerId": str(record["customerId"]), # partition key
        "amount": amount,
        "tax": round(amount * TAX_RATE, 2),
        "total": round(amount * (1 + TAX_RATE), 2),
        "currency": record.get("currency", "USD"),
        "sourceFile": source,
        "processedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


@app.function_name(name="process_blob")
@app.route(route="process", methods=["POST"])
@app.cosmos_db_output(
    arg_name="docs",
    database_name="ordersdb",
    container_name="orders",
    connection="CosmosDb",
)
def process_blob(req: func.HttpRequest, docs: func.Out[func.DocumentList]) -> func.HttpResponse:
    try:
        payload = req.get_json()
        file_name = payload["fileName"]
        raw = base64.b64decode(payload["contentBase64"]).decode("utf-8-sig")
        records = parse_records(file_name, raw)
    except (ValueError, KeyError) as exc:
        logging.warning("Bad request: %s", exc)
        return func.HttpResponse(json.dumps({"error": f"bad request: {exc}"}),
                                 status_code=400, mimetype="application/json")

    good, rejected = [], []
    for i, rec in enumerate(records):
        errs = validate(rec)
        if errs:
            rejected.append({"row": i, "errors": errs})
        else:
            good.append(func.Document.from_dict(enrich(rec, file_name)))

    if good:
        docs.set(func.DocumentList(good))

    logging.info("Processed file=%s saved=%d rejected=%d", file_name, len(good), len(rejected))
    body = {"file": file_name, "saved": len(good), "rejected": rejected}
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json")
```

What this does:

- `@app.route` creates an HTTP trigger at `/api/process`. `AuthLevel.FUNCTION` requires a function key (or you can add Entra ID auth later).
- `@app.cosmos_db_output` binds `docs` to the `orders` container. Setting `docs` writes all documents when the function returns. The binding **upserts**, so reprocessing the same file overwrites documents with the same `id` and partition key instead of creating duplicates. This makes the pipeline idempotent.
- The Logic App sends the file as base64 (`contentBase64`). Base64 is safe for any content type. `utf-8-sig` also removes a byte order mark that Excel-made CSV files often have.
- Bad rows are reported back, not saved. A 400 means the whole file was unreadable.
- Each document has `id` and `customerId`. Cosmos needs `id`, and the partition key value must be present.
- SDK alternative: use `azure-cosmos` with `CosmosClient(endpoint, credential=DefaultAzureCredential())` when you need queries, patch operations, transactional batches or custom retry logic.

#### Step 7: Run locally, then deploy

File `function-app/local.settings.json` (local only, never commit it):

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "CosmosDb__accountEndpoint": "https://<cosmos-account>.documents.azure.com:443/"
  }
}
```

```bash
cd function-app
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start     # needs Azurite for AzureWebJobsStorage, or point it to a real storage account

# In another terminal
CONTENT=$(base64 -w0 ../samples/orders-001.json)
curl -s -X POST http://localhost:7071/api/process \
  -H "Content-Type: application/json" \
  -d "{\"fileName\":\"orders-001.json\",\"contentBase64\":\"$CONTENT\"}"

# Deploy
func azure functionapp publish $FUNC
```

Sample data, `samples/orders-001.json`:

```json
[
  { "orderId": "1001", "customerId": "C-01", "amount": 25.50, "currency": "USD" },
  { "orderId": "1002", "customerId": "C-02", "amount": 99.00 },
  { "orderId": "1003", "customerId": "", "amount": 10 }
]
```

What this does:

- Locally, the identity-based Cosmos connection uses your `az login` account. That is why you gave yourself the data-plane role in Step 5.
- `func azure functionapp publish` builds the Python package remotely and deploys it.
- The sample has one invalid row (`1003` has no customer) so you can see validation working.

#### Step 8: Create the Logic App and give it access to Storage

```bash
cat > logic-app/empty-workflow.json <<'EOF'
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "triggers": {},
    "actions": {},
    "outputs": {}
  }
}
EOF

az logic workflow create --resource-group $RG --name $LA --location $LOC \
  --definition logic-app/empty-workflow.json

az logic workflow identity assign --resource-group $RG --name $LA --system-assigned
LA_PRINCIPAL_ID=$(az logic workflow show -g $RG -n $LA --query identity.principalId -o tsv)

az role assignment create --assignee-object-id $LA_PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Reader" --scope $DATA_ST_ID
```

What this does:

- Creates an empty Consumption workflow, then turns on its system-assigned identity.
- **Storage Blob Data Reader** is enough because the Logic App only reads blobs. Least privilege.
- If CLI options differ in your extension version, you can do the same in the portal: Logic App > **Identity** > **System assigned** > On.

#### Step 9: Build the workflow

In the portal, open the Logic App > **Logic app designer**:

1. Add trigger **Azure Blob Storage > When a blob is added or modified (properties only) (V2)**.
2. When asked for a connection, choose **Authentication type: Logic Apps Managed Identity** and enter the storage account name. Container: `/incoming`. Interval: 1 minute.
3. Add a **Scope** named `Try`. Inside it add **Get blob content (V2)** with blob path = the trigger's **Path** and **Infer content type: No**.
4. Inside `Try`, add **Azure Functions > Choose an Azure function** (the `process_blob` function), method POST, and the body below.
5. Add a second **Scope** named `Catch`. Set **Run after** to `Try` **has failed** and **has timed out**.

Then open **Code view**. The result should look like this (IDs shortened):

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
      "$connections": { "defaultValue": {}, "type": "Object" }
    },
    "triggers": {
      "When_a_blob_is_added_or_modified_(properties_only)_(V2)": {
        "type": "ApiConnection",
        "recurrence": { "frequency": "Minute", "interval": 1 },
        "splitOn": "@triggerBody()",
        "inputs": {
          "host": { "connection": { "name": "@parameters('$connections')['azureblob']['connectionId']" } },
          "method": "get",
          "path": "/v2/datasets/@{encodeURIComponent(encodeURIComponent('<storage-account-name>'))}/triggers/batch/onupdatedfile",
          "queries": {
            "folderId": "JTJmaW5jb21pbmc=",
            "maxFileCount": 10,
            "checkBothCreatedAndModifiedDateTime": false
          }
        },
        "metadata": { "JTJmaW5jb21pbmc=": "/incoming" }
      }
    },
    "actions": {
      "Try": {
        "type": "Scope",
        "runAfter": {},
        "actions": {
          "Get_blob_content_(V2)": {
            "type": "ApiConnection",
            "runAfter": {},
            "inputs": {
              "host": { "connection": { "name": "@parameters('$connections')['azureblob']['connectionId']" } },
              "method": "get",
              "path": "/v2/datasets/@{encodeURIComponent(encodeURIComponent('<storage-account-name>'))}/files/@{encodeURIComponent(encodeURIComponent(triggerBody()?['Path']))}/content",
              "queries": { "inferContentType": false }
            }
          },
          "Call_process_blob": {
            "type": "Function",
            "runAfter": { "Get_blob_content_(V2)": [ "Succeeded" ] },
            "inputs": {
              "function": {
                "id": "/subscriptions/<sub-id>/resourceGroups/rg-eventdriven-lab/providers/Microsoft.Web/sites/<func-app-name>/functions/process_blob"
              },
              "method": "POST",
              "headers": { "Content-Type": "application/json" },
              "body": {
                "fileName": "@{triggerBody()?['Name']}",
                "path": "@{triggerBody()?['Path']}",
                "contentBase64": "@{body('Get_blob_content_(V2)')?['$content']}"
              },
              "retryPolicy": {
                "type": "exponential",
                "count": 4,
                "interval": "PT10S",
                "minimumInterval": "PT5S",
                "maximumInterval": "PT1M"
              }
            }
          }
        }
      },
      "Catch": {
        "type": "Scope",
        "runAfter": { "Try": [ "Failed", "TimedOut" ] },
        "actions": {
          "Collect_errors": {
            "type": "Compose",
            "runAfter": {},
            "inputs": {
              "file": "@triggerBody()?['Path']",
              "tryResults": "@result('Try')"
            }
          },
          "Terminate_as_failed": {
            "type": "Terminate",
            "runAfter": { "Collect_errors": [ "Succeeded" ] },
            "inputs": {
              "runStatus": "Failed",
              "runError": { "code": "OrderFileFailed", "message": "Processing failed for @{triggerBody()?['Path']}" }
            }
          }
        }
      }
    },
    "outputs": {}
  },
  "parameters": {
    "$connections": {
      "value": {
        "azureblob": {
          "connectionId": "/subscriptions/<sub-id>/resourceGroups/rg-eventdriven-lab/providers/Microsoft.Web/connections/azureblob",
          "connectionName": "azureblob",
          "id": "/subscriptions/<sub-id>/providers/Microsoft.Web/locations/eastus/managedApis/azureblob",
          "connectionProperties": {
            "authentication": { "type": "ManagedServiceIdentity" }
          }
        }
      }
    }
  }
}
```

What this does:

- **Trigger**: polls the `incoming` folder every minute. `splitOn` starts one run per new blob, so each file gets its own run history and retries. `folderId` is the base64 form of `%2fincoming`; the designer generates it.
- **Dataset**: the designer writes the storage account name (managed identity connections) or `AccountNameFromSettings` (access key connections) in the path. Copy what your designer generates.
- **Get blob content (V2)** with `inferContentType: false` returns `{"$content-type": "application/octet-stream", "$content": "<base64>"}`, so `['$content']` is always base64, for JSON and CSV alike.
- **Function action**: Logic Apps fetches the function key for you, so the key is not stored in the workflow definition.
- **retryPolicy**: exponential retries for 408, 429 and 5xx responses and connection errors. A 400 from the Function is not retried, which is correct because bad data will not fix itself.
- **Try/Catch scopes**: `Catch` only runs when `Try` failed or timed out. `result('Try')` returns the status, inputs and outputs of each action inside the scope, which is ideal for an alert email or a dead-letter record. Add a **Filter array** action on `result('Try')` with `status` equal to `Failed` if you want only the failed actions.
- **Terminate as Failed** keeps the run marked as failed in history, so alerts and dashboards still count it.
- **connectionProperties.authentication: ManagedServiceIdentity** tells the blob connection to use the Logic App's identity. No storage key is saved in the connection.

Hardened option: use an **HTTP** action with managed identity instead of the function key. Enable App Service Authentication (Easy Auth) with Microsoft Entra on the Function App, allow the Logic App's identity, then:

```json
"Call_process_blob_http": {
  "type": "Http",
  "inputs": {
    "method": "POST",
    "uri": "https://<func-app-name>.azurewebsites.net/api/process",
    "body": { "fileName": "@{triggerBody()?['Name']}", "contentBase64": "@{body('Get_blob_content_(V2)')?['$content']}" },
    "authentication": { "type": "ManagedServiceIdentity", "audience": "api://<function-app-registration-client-id>" }
  },
  "runAfter": { "Get_blob_content_(V2)": [ "Succeeded" ] }
}
```

In that case set the Function's auth level to `ANONYMOUS`, because Easy Auth now protects it.

#### Step 10: Event Grid alternative

Polling has a delay (up to the interval) and you pay for every poll. **Event Grid** pushes a `Microsoft.Storage.BlobCreated` event within seconds.

```python
# Add to function_app.py: an Event Grid triggered function
@app.function_name(name="on_blob_created")
@app.event_grid_trigger(arg_name="event")
def on_blob_created(event: func.EventGridEvent):
    data = event.get_json()
    logging.info("BlobCreated: subject=%s url=%s", event.subject, data.get("url"))
    # Read the blob with azure-storage-blob + DefaultAzureCredential, then reuse
    # parse_records / validate / enrich and write with the Cosmos SDK.
```

```bash
FUNC_ID=$(az functionapp show -n $FUNC -g $RG --query id -o tsv)

az eventgrid event-subscription create \
  --name orders-blob-created \
  --source-resource-id $DATA_ST_ID \
  --endpoint-type azurefunction \
  --endpoint "$FUNC_ID/functions/on_blob_created" \
  --included-event-types Microsoft.Storage.BlobCreated \
  --subject-begins-with /blobServices/default/containers/incoming/ \
  --subject-ends-with .json
```

| Design | Good | Not so good |
| --- | --- | --- |
| Logic App polling + Function | Visual flow, connectors, run history, easy to add steps (email, approvals) | Polling delay and cost, extra hop, per-action cost at high volume |
| Event Grid + Function | Near real-time, push based, cheap at scale, built-in retry and dead-letter | All logic in code, less visual, you build your own orchestration |
| Event Grid + Logic App | Push trigger with low-code steps | Still pays per action |

Also: the Flex Consumption plan supports only the **Event Grid source** for the blob trigger (`@app.blob_trigger(..., source="EventGrid")`), not the old polling blob trigger.

### Verify it works

```bash
# Upload a file
az storage blob upload --account-name $DATA_ST --container-name incoming \
  --name orders-001.json --file samples/orders-001.json --auth-mode login

# After 1-2 minutes, check Logic App runs
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Logic/workflows/$LA/runs?api-version=2016-06-01" \
  --query "value[].{run:name, status:properties.status, start:properties.startTime}" -o table
```

Expected output:

```text
Run                             Status     Start
------------------------------  ---------  ----------------------------
08584721...CU12                 Succeeded  2026-10-15T10:21:04.1234567Z
```

Check the documents in Cosmos DB (portal **Data Explorer**, or this script using your own identity):

```python
# check_cosmos.py  (pip install azure-cosmos azure-identity)
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

client = CosmosClient("https://<cosmos-account>.documents.azure.com:443/", DefaultAzureCredential())
container = client.get_database_client("ordersdb").get_container_client("orders")
for item in container.query_items("SELECT c.id, c.customerId, c.total FROM c", enable_cross_partition_query=True):
    print(item)
```

Expected output:

```text
{'id': '1001', 'customerId': 'C-01', 'total': 27.54}
{'id': '1002', 'customerId': 'C-02', 'total': 106.92}
```

Monitoring queries in Application Insights (**Logs**):

```kusto
// Function requests: volume, failures and latency
requests
| where timestamp > ago(1h)
| where operation_Name == "process_blob"
| summarize Calls = count(), Failed = countif(success == false), AvgMs = avg(duration)
    by bin(timestamp, 5m)
| order by timestamp desc
```

```kusto
// Processing log lines written by the function
traces
| where timestamp > ago(1h)
| where message startswith "Processed file="
| project timestamp, message, operation_Id
```

```kusto
// Exceptions with the failing operation
exceptions
| where timestamp > ago(24h)
| project timestamp, operation_Name, type, outerMessage, operation_Id
```

If you send Logic App diagnostic settings to Log Analytics (category `WorkflowRuntime`), you can query failed actions:

```kusto
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.LOGIC"
| where Category == "WorkflowRuntime"
| where status_s == "Failed"
| project TimeGenerated, resource_workflowName_s, resource_actionName_s, resource_runId_s, code_s
| order by TimeGenerated desc
```

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Logic App trigger never fires | Wrong folder, or file older than the trigger's last check | Check container path `/incoming`; upload a new file |
| Trigger or Get blob returns 403 | Logic App identity missing the data role, or storage firewall | Assign Storage Blob Data Reader; for locked-down storage see [the secured storage scenario](../resume-projects/08-logic-app-secured-storage-access.md) |
| Function returns 401 | Missing key or Easy Auth audience mismatch | Use the Azure Functions action, or fix the `audience` value |
| Function returns 400 | Body format wrong, or `$content` missing | Set Infer content type to No; check the body in run history |
| Function logs `Forbidden ... RBAC` for Cosmos | Data-plane role missing (Azure RBAC Contributor is not enough) | `az cosmosdb sql role assignment create` with the Data Contributor role |
| Function fails at startup with binding errors | Wrong setting name | Must be `CosmosDb__accountEndpoint` (double underscore) to match `connection="CosmosDb"` |
| Documents missing or overwritten | Same `id` and partition key | Expected: the binding upserts; use unique ids |
| `Partition key ... does not match` | Document lacks `customerId` | Validate partition key value before writing |
| Same file processed twice | Blob modified after upload | Expected with "added or modified"; idempotent upsert keeps data correct |
| Nothing in App Insights | Connection string not set, or delay | Check `APPLICATIONINSIGHTS_CONNECTION_STRING`; wait 2-5 minutes |

### Clean up

```bash
az eventgrid event-subscription delete --name orders-blob-created --source-resource-id $DATA_ST_ID 2>/dev/null
az group delete --name $RG --yes --no-wait
```

Also delete or disable the Logic App early if you keep the group, because the trigger polls every minute:

```bash
az logic workflow update --resource-group $RG --name $LA --state Disabled
```

### Next improvements

- Move processed files to `processed/` and failed files to `failed/` containers (or use blob index tags).
- Send rejected rows to a Service Bus dead-letter queue or a Storage table for review.
- Protect the Function with Easy Auth and call it with the Logic App's managed identity.
- Lock down storage, Cosmos and the Function with private endpoints and VNet integration.
- Define everything in Bicep or Terraform, including the API connection and role assignments.
- Add an alert on Logic App failed runs and Function failure rate, routed to an Action Group.
- For large files, pass only the blob URL and let the Function stream the blob with the SDK.

### How to explain this project in an interview

> "This was a practice project to build an event-driven pipeline with no secrets. Files land in a Blob container. A Consumption Logic App triggers on new blobs, reads the content with its managed identity and calls a Python Azure Function. The Function, written in the v2 programming model, parses JSON or CSV, validates each record, enriches it with tax and timestamps, and writes to Cosmos DB through an output binding. The binding uses an identity-based connection, so the Function has the Cosmos DB Built-in Data Contributor data-plane role and no keys. I picked customerId as the partition key based on the main query pattern. The Logic App uses Try and Catch scopes and an exponential retry policy, and the binding upserts by id, so retries are safe. I monitored with Logic App run history and App Insights KQL. I also compared it with an Event Grid BlobCreated trigger, which is faster and cheaper at scale but less visual."

Points that impress interviewers:

- You know Cosmos DB data-plane RBAC is separate from Azure RBAC, and how to assign it.
- You designed for idempotency (upsert by `id`) so retries and duplicate events are safe.
- You can explain polling vs push (Logic App trigger vs Event Grid) with real trade-offs.
- You justified the partition key from the access pattern.

## Interview Questions

<details><summary>Q1. [Basic] When would you choose a Logic App instead of an Azure Function?</summary>

**Answer:**

- **Logic App**: orchestration and integration. Many built-in connectors (Office 365, SAP, Service Bus, SFTP), visual designer, run history per step, approvals and long-running workflows. Little or no code.
- **Function**: custom logic in code, complex parsing, heavy computation, fine control over performance and testing.

They work well together: the Logic App orchestrates, the Function does the business logic, as in this project.

</details>

<details><summary>Q2. [Basic] What is the difference between Logic Apps Consumption and Standard?</summary>

**Answer:**

| Consumption | Standard |
| --- | --- |
| Multi-tenant, one workflow per resource | Single-tenant, many workflows per app |
| Pay per trigger and action execution | Pay for the hosting plan |
| No VNet integration | VNet integration and private endpoints |
| Managed (API) connectors | Built-in connectors run in-process plus managed connectors |

Choose Standard for private networking, high volume, or local development with VS Code.

</details>

<details><summary>Q3. [Basic] How do you choose a partition key in Cosmos DB?</summary>

**Answer:**

Choose a property that:

- Has many distinct values (high cardinality), so data and load spread evenly.
- Appears in most queries as a filter, so queries hit one partition.
- Spreads writes, so no single hot partition gets all traffic.

`/customerId` works for "orders by customer". Bad choices: `/status` or a date (few values or all new writes in one partition). The key cannot be changed in place, so pick it from the access pattern. Hierarchical partition keys help when one tenant is very large.

</details>

<details><summary>Q4. [Intermediate] Explain control-plane vs data-plane RBAC in Cosmos DB.</summary>

**Answer:**

- **Control plane** uses Azure RBAC (`az role assignment create`): manage accounts, databases, containers, throughput, keys.
- **Data plane** uses Cosmos DB native RBAC (`az cosmosdb sql role assignment create`): read and write items and run queries. Built-in roles: Data Reader (`...0001`) and Data Contributor (`...0002`).

A Contributor on the account can manage it but cannot read items with Entra ID. Data-plane role assignments do not appear in the portal IAM blade. With `disableLocalAuth=true`, keys stop working and only data-plane RBAC grants access.

</details>

<details><summary>Q5. [Intermediate] How does an identity-based connection for a Functions binding work?</summary>

**Answer:**

Instead of a connection string setting, you provide settings with a common prefix and a double underscore. For Cosmos DB: `CosmosDb__accountEndpoint`. The binding sees an endpoint, not a connection string, and gets a token from the managed identity. For a user-assigned identity, add `CosmosDb__credential=managedidentity` and `CosmosDb__clientId`. The identity also needs the right data role. This needs the newer extension versions (Cosmos DB extension 4.x, included in extension bundle 4.x).

</details>

<details><summary>Q6. [Intermediate] How do you handle errors in a Logic App workflow?</summary>

**Answer:**

- **Retry policy** on actions (default, fixed, exponential, none) for transient errors (408, 429, 5xx).
- **Run after** settings: an action can run when the previous one Succeeded, Failed, Skipped or TimedOut.
- **Scopes** as Try/Catch/Finally: put actions in a `Try` scope, add a `Catch` scope that runs after `Try` failed or timed out, and use `result('Try')` to get error details.
- **Terminate** with `Failed` to keep the run marked as failed.
- Alerts on failed runs through diagnostic settings and Azure Monitor.

</details>

<details><summary>Q7. [Intermediate] Polling trigger vs Event Grid: what are the trade-offs?</summary>

**Answer:**

Polling (Logic App blob trigger): simple, works with low-code, but has a delay up to the interval and costs per poll even when idle. Event Grid: push based, near real-time, cheap per event, has retries with dead-lettering and filtering by subject. It needs a reachable endpoint and gives at-least-once delivery, so handlers must be idempotent. For high volume or low latency, Event Grid is better. For low-code orchestration with modest volume, the Logic App trigger is fine.

</details>

<details><summary>Q8. [Advanced] The same file is processed twice and creates duplicate data. How do you fix it? <em>(scenario)</em></summary>

**Answer:**

Duplicates are normal in event-driven systems: triggers fire on "added or modified", Event Grid is at-least-once, and retries can repeat a call. Fix it with **idempotency**:

- Use a deterministic document `id` (for example the business `orderId`) and **upsert**, so a repeat overwrites instead of inserting.
- Track processed files (blob name + ETag) in a table and skip known ones.
- Move processed files to another container after success.
- Avoid retry storms by not retrying 4xx errors.

</details>

<details><summary>Q9. [Advanced] The Logic App fails with 403 on <code>Get blob content</code> after the security team enabled the storage firewall. What do you do? <em>(scenario)</em></summary>

**Answer:**

A Consumption Logic App runs in shared infrastructure without VNet integration, so VNet rules do not cover it, and IP rules fail when both are in the same region. Options:

- Keep the managed identity connection and add a **resource instance rule** on the storage firewall for this Logic App (`Microsoft.Logic/workflows`), with the Storage Blob Data Reader role.
- Or move to **Logic Apps Standard** with VNet integration and private endpoints.

The full walkthrough is in [the secured storage scenario](../resume-projects/08-logic-app-secured-storage-access.md).

</details>

<details><summary>Q10. [Advanced] How would you monitor this pipeline end to end? <em>(scenario)</em></summary>

**Answer:**

- **Logic App**: diagnostic settings to Log Analytics (`WorkflowRuntime`), alert on failed runs (metric `RunsFailed` or KQL).
- **Function**: Application Insights requests, failures, dependencies and custom log lines; alert on failure rate and duration.
- **Cosmos DB**: metrics for 429 (throttled) requests and RU consumption.
- **Correlation**: pass the blob name or a correlation ID from the Logic App to the Function and log it, so one file can be traced across systems.
- **Business check**: a scheduled query that compares files uploaded vs documents written.

</details>
