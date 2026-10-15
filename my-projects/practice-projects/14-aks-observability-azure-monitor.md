# Practice Project 14: AKS Observability with Azure Monitor

> A hands-on guide to monitoring an AKS cluster end to end with Container Insights, Managed Prometheus, Azure Managed Grafana, KQL queries, alert rules with Action Groups, and Application Insights tracing through OpenTelemetry.

## Key Concepts

### What you will build

- A **Log Analytics workspace** that stores AKS logs and inventory data (Container Insights).
- **Managed Prometheus** metrics stored in an **Azure Monitor workspace**, shown in **Azure Managed Grafana** dashboards.
- Cost-aware data collection: **ContainerLogV2** schema, namespace filtering and the **Basic** table plan option.
- A set of **KQL queries** for the problems you meet most: pods not running, crash loops, OOM kills, error logs, node health, CPU usage.
- **Alerts**: log search alerts, metric alerts and Prometheus alerts, all sending email through an **Action Group**.
- Bonus: **Application Insights** tracing for a Python app with the Azure Monitor OpenTelemetry distro.

The final result: you break some pods on purpose (crash loop, OOM, unschedulable), and you see them in KQL, in Grafana, and as alert emails in your inbox.

#### Metrics vs logs vs traces

| Signal | What it is | Example in AKS | Where it goes here | Best for |
| --- | --- | --- | --- | --- |
| Metrics | Numbers over time, cheap to store and query | Node CPU %, pod restarts, request rate | Managed Prometheus (Azure Monitor workspace), platform metrics | Dashboards, fast alerts, trends |
| Logs | Text or structured events with detail | Container stdout/stderr, Kubernetes events, pod inventory | Log Analytics (ContainerLogV2, KubeEvents, KubePodInventory) | Root cause, searching, audit |
| Traces | The path of one request across services, with timing per step | HTTP request -> API -> DB call | Application Insights (OpenTelemetry) | Finding slow or failing dependencies |

A simple way to remember it: **metrics tell you that something is wrong, logs tell you why, traces tell you where**.

### Architecture

```text
                         +---------------------- AKS cluster ----------------------+
                         |  Nodes                                                  |
                         |   ├─ ama-logs (DaemonSet)  -> stdout/stderr, events,    |
                         |   │                           inventory, perf           |
                         |   ├─ ama-metrics (Prometheus scraper) -> metrics        |
                         |   └─ app pods (Python + OpenTelemetry) -> traces        |
                         +-----------+-------------------+-----------------+-------+
                                     |                   |                 |
                     DCR (Container  |     DCR (Prom-    |                 | OTLP / exporter
                     Insights)       |     etheus)       |                 |
                                     v                   v                 v
                    +------------------------+ +----------------------+ +----------------------+
                    | Log Analytics          | | Azure Monitor        | | Application Insights |
                    | workspace (KQL)        | | workspace (PromQL)   | | (workspace-based)    |
                    +-----------+------------+ +----------+-----------+ +----------+-----------+
                                |                         |                        |
               log search alerts|          Prometheus     |  Grafana data source   |
               workbooks        |          alert rules    v                        |
                                |               +----------------------+           |
                                |               | Azure Managed Grafana|           |
                                |               +----------------------+           |
                                v                                                  v
                    +------------------------------------------------------------------+
                    | Azure Monitor Alerts  ->  Action Group (email / SMS / webhook)   |
                    +------------------------------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Container Insights (monitoring add-on) | Collects container logs, events, inventory and perf into Log Analytics | Native, managed agent, built-in workbooks |
| Log Analytics workspace | Stores logs; you query with KQL | One place to search and alert on logs |
| Managed Prometheus | Scrapes Prometheus metrics into an Azure Monitor workspace | No Prometheus servers to run or scale |
| Azure Managed Grafana | Dashboards over Prometheus and Log Analytics | Ready-made Kubernetes dashboards, Entra ID login |
| Azure Monitor alerts | Log search, metric and Prometheus alert rules | One alerting system for all signals |
| Action Groups | Who to notify and how | Reusable across all alert rules |
| Application Insights + OpenTelemetry | Request traces, dependencies, exceptions for apps | Vendor-neutral instrumentation, Azure backend |

### Prerequisites

- Azure subscription with Owner (or Contributor + User Access Administrator) on a resource group.
- Azure CLI 2.60 or later, plus extensions:

```bash
az extension add --name amg --upgrade                  # Azure Managed Grafana
az extension add --name application-insights --upgrade
az extension add --name alertsmanagement --upgrade     # Prometheus rule groups
az extension add --name scheduled-query --upgrade      # only if your CLI asks for it
```

- `kubectl` (`az aks install-cli`).
- Resource providers registered: `Microsoft.ContainerService`, `Microsoft.Insights`, `Microsoft.Monitor`, `Microsoft.Dashboard`, `Microsoft.AlertsManagement`, `Microsoft.OperationalInsights`.
- **Cost warning**: AKS nodes, Log Analytics ingestion (per GB), Managed Prometheus samples and Managed Grafana (Standard SKU per instance hour) all cost money. Log ingestion is usually the biggest monitoring cost. Delete everything when finished.

### Folder structure

```text
aks-observability/
├── setup.sh
├── dcr/
│   └── data-collection-settings.json
├── k8s/
│   ├── namespace.yaml
│   ├── crashloop-demo.yaml
│   ├── oom-demo.yaml
│   └── pending-demo.yaml
├── alerts/
│   └── prometheus-rules.json
├── queries/
│   └── aks-troubleshooting.kql
└── app/
    ├── app.py
    └── requirements.txt
```

### Step-by-step

#### Step 1: Set variables and create a small AKS cluster

Skip the cluster creation if you already have one.

```bash
RG=rg-aks-obs-lab
LOC=eastus
AKS=aks-obs-lab
LAW=law-aks-obs
AMW=amw-aks-obs
GRAFANA=grafana-aks-obs-$RANDOM
AG=ag-aks-oncall
EMAIL="<your-email@example.com>"
ME=$(az ad signed-in-user show --query id -o tsv)

az group create --name $RG --location $LOC

az aks create --resource-group $RG --name $AKS \
  --node-count 2 --node-vm-size Standard_D2s_v5 \
  --enable-managed-identity --generate-ssh-keys

az aks get-credentials --resource-group $RG --name $AKS
AKS_ID=$(az aks show -g $RG -n $AKS --query id -o tsv)
kubectl get nodes
```

What this does:

- Creates a two-node cluster with a managed identity. Two nodes is enough to see per-node data.
- `get-credentials` writes the kubeconfig so `kubectl` works.

#### Step 2: Create the Log Analytics workspace

```bash
az monitor log-analytics workspace create \
  --resource-group $RG --workspace-name $LAW --location $LOC \
  --retention-time 30

LAW_ID=$(az monitor log-analytics workspace show -g $RG -n $LAW --query id -o tsv)
```

What this does:

- The workspace stores the Container Insights tables (`ContainerLogV2`, `KubePodInventory`, `KubeEvents`, `KubeNodeInventory`, `Perf`, `InsightsMetrics`, and more).
- 30 days of retention is included in the standard ingestion price for Analytics tables. Longer retention costs extra.
- In real environments, teams often use one shared workspace per environment or region instead of one per cluster.

#### Step 3: Enable Container Insights with cost-aware settings

Create a data collection settings file, `dcr/data-collection-settings.json`:

```json
{
  "interval": "1m",
  "namespaceFilteringMode": "Exclude",
  "namespaces": ["kube-system", "gatekeeper-system"],
  "enableContainerLogV2": true,
  "streams": [
    "Microsoft-ContainerLogV2",
    "Microsoft-KubeEvents",
    "Microsoft-KubePodInventory",
    "Microsoft-KubeNodeInventory",
    "Microsoft-Perf",
    "Microsoft-InsightsMetrics",
    "Microsoft-KubeServices",
    "Microsoft-ContainerInventory",
    "Microsoft-ContainerNodeInventory",
    "Microsoft-KubePVInventory"
  ]
}
```

Then enable the add-on:

```bash
az aks enable-addons --addon monitoring \
  --resource-group $RG --name $AKS \
  --workspace-resource-id $LAW_ID \
  --data-collection-settings dcr/data-collection-settings.json

kubectl get pods -n kube-system -l component=ama-logs
kubectl get ds -n kube-system | grep ama-logs
```

What this does:

- The `monitoring` add-on deploys the **Azure Monitor Agent** for containers (`ama-logs` pods) and creates a **data collection rule (DCR)** that says what to collect and where to send it. Current versions use managed identity authentication by default.
- `interval` controls how often inventory and perf data is collected. `5m` instead of `1m` cuts that data a lot.
- `namespaceFilteringMode: Exclude` with `kube-system` stops collecting data for noisy system namespaces. Keep them if you want to alert on system pod failures.
- `enableContainerLogV2: true` writes container logs to **ContainerLogV2**, the current schema. It includes `PodName`, `PodNamespace` and `ContainerName` directly, so queries do not need joins, and it supports the Basic plan.
- `streams` lists the tables to collect. Removing streams you never query is an easy saving.

#### Step 4: More cost controls

```bash
# Move container logs to the Basic plan (cheaper ingestion, limited query features)
az monitor log-analytics workspace table update \
  --resource-group $RG --workspace-name $LAW \
  --name ContainerLogV2 --plan Basic

# See which tables cost the most (last 7 days)
az monitor log-analytics query --workspace $(az monitor log-analytics workspace show -g $RG -n $LAW --query customerId -o tsv) \
  --analytics-query "Usage | where TimeGenerated > ago(7d) | where IsBillable == true | summarize GB = sum(Quantity) / 1024 by DataType | order by GB desc" -o table
```

What this does:

- The **Basic** plan costs much less per GB, but queries are charged per GB scanned, retention for interactive queries is short, and most alert rules need the **Analytics** plan. Use Basic only for logs you search rarely, and keep Analytics if you alert on `ContainerLogV2`.
- The `Usage` table shows billable GB per table. In AKS, `ContainerLogV2` (app logs) and `Perf`/`InsightsMetrics` are usually the top items.
- Other tips: reduce app log verbosity (no debug logs in production), filter namespaces, set a **daily cap** on the workspace for labs, and use commitment tiers for large volumes.

#### Step 5: Enable Managed Prometheus and Managed Grafana

```bash
# Azure Monitor workspace (stores Prometheus metrics)
az monitor account create --name $AMW --resource-group $RG --location $LOC
AMW_ID=$(az monitor account show -n $AMW -g $RG --query id -o tsv)

# Azure Managed Grafana
az grafana create --name $GRAFANA --resource-group $RG --location $LOC
GRAFANA_ID=$(az grafana show -n $GRAFANA -g $RG --query id -o tsv)

# Let yourself log in as Grafana admin
az role assignment create --assignee-object-id $ME --assignee-principal-type User \
  --role "Grafana Admin" --scope $GRAFANA_ID

# Turn on Prometheus metrics collection and link Grafana
az aks update --resource-group $RG --name $AKS \
  --enable-azure-monitor-metrics \
  --azure-monitor-workspace-resource-id $AMW_ID \
  --grafana-resource-id $GRAFANA_ID

kubectl get pods -n kube-system | grep ama-metrics
```

What this does:

- `--enable-azure-monitor-metrics` deploys the `ama-metrics` pods. They scrape kubelet, cAdvisor, kube-state-metrics and node-exporter targets with a default, cost-friendly set of metrics.
- `--grafana-resource-id` adds the Azure Monitor workspace as a Prometheus data source in Grafana and imports ready-made Kubernetes dashboards. It also grants the Grafana managed identity **Monitoring Data Reader** on the workspace.
- If the Grafana data source shows permission errors, assign it yourself:

```bash
GRAFANA_MI=$(az grafana show -n $GRAFANA -g $RG --query identity.principalId -o tsv)
az role assignment create --assignee-object-id $GRAFANA_MI --assignee-principal-type ServicePrincipal \
  --role "Monitoring Data Reader" --scope $AMW_ID
```

Open Grafana:

```bash
az grafana show -n $GRAFANA -g $RG --query properties.endpoint -o tsv
```

Go to **Dashboards > Azure Managed Prometheus** and open **Kubernetes / Compute Resources / Cluster**.

#### Step 6: Deploy broken workloads to create signals

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: obs-demo
---
# k8s/crashloop-demo.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crashloop-demo
  namespace: obs-demo
spec:
  replicas: 1
  selector:
    matchLabels: { app: crashloop-demo }
  template:
    metadata:
      labels: { app: crashloop-demo }
    spec:
      containers:
        - name: app
          image: busybox:1.36
          command: ["sh", "-c", "echo 'ERROR: cannot connect to database'; sleep 5; exit 1"]
          resources:
            requests: { cpu: 10m, memory: 16Mi }
            limits: { memory: 32Mi }
---
# k8s/oom-demo.yaml
apiVersion: v1
kind: Pod
metadata:
  name: oom-demo
  namespace: obs-demo
spec:
  containers:
    - name: stress
      image: polinux/stress
      command: ["stress"]
      args: ["--vm", "1", "--vm-bytes", "150M", "--vm-hang", "1"]
      resources:
        requests: { memory: 50Mi }
        limits: { memory: 100Mi }
---
# k8s/pending-demo.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pending-demo
  namespace: obs-demo
spec:
  containers:
    - name: big
      image: nginx:1.27
      resources:
        requests: { cpu: "64", memory: 1Gi }
```

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
kubectl get pods -n obs-demo -w
```

What this does:

- `crashloop-demo` prints an error log line and exits, so it goes into **CrashLoopBackOff** and Kubernetes emits **BackOff** events.
- `oom-demo` uses more memory than its limit, so the kernel kills it and the container status shows **OOMKilled**.
- `pending-demo` asks for 64 CPUs, so it stays **Pending** with a **FailedScheduling** event.
- Data shows up in Log Analytics after about 5-10 minutes.

#### Step 7: Troubleshoot with KQL

Run these in the AKS cluster > **Monitoring > Logs**, or in the workspace. Save them in `queries/aks-troubleshooting.kql`.

```kusto
// 1. Pods that are not Running or Succeeded (latest state per pod)
KubePodInventory
| where TimeGenerated > ago(30m)
| summarize arg_max(TimeGenerated, *) by ClusterName, Namespace, Name
| where PodStatus !in ("Running", "Succeeded")
| project TimeGenerated, ClusterName, Namespace, Name, PodStatus, ContainerStatusReason, ContainerRestartCount
| order by Namespace asc, Name asc
```

```kusto
// 2. Pods with restarts or OOM kills in the last hour
KubePodInventory
| where TimeGenerated > ago(1h)
| where ContainerRestartCount > 0 or ContainerLastStatus has "OOMKilled"
| summarize Restarts = max(ContainerRestartCount),
            OOMKillRows = countif(ContainerLastStatus has "OOMKilled")
    by Namespace, Name, ContainerName
| order by Restarts desc
```

```kusto
// 3. Error log lines by pod (ContainerLogV2)
ContainerLogV2
| where TimeGenerated > ago(1h)
| where LogLevel in~ ("error", "critical") or tostring(LogMessage) has_any ("error", "exception", "fatal")
| summarize Errors = count(), Sample = take_any(tostring(LogMessage)) by PodNamespace, PodName, ContainerName
| top 20 by Errors desc
```

```kusto
// 4. Node status and versions (latest per node)
KubeNodeInventory
| where TimeGenerated > ago(30m)
| summarize arg_max(TimeGenerated, *) by Computer
| project Computer, Status, KubeletVersion, ClusterName, LastSeen = TimeGenerated
```

```kusto
// 5. Node CPU % over time (Perf)
let capacity = Perf
    | where TimeGenerated > ago(1h)
    | where ObjectName == "K8SNode" and CounterName == "cpuCapacityNanoCores"
    | summarize CapacityNanoCores = max(CounterValue) by Computer;
Perf
| where TimeGenerated > ago(1h)
| where ObjectName == "K8SNode" and CounterName == "cpuUsageNanoCores"
| summarize UsageNanoCores = avg(CounterValue) by Computer, bin(TimeGenerated, 5m)
| join kind=inner capacity on Computer
| extend CpuPercent = round(100.0 * UsageNanoCores / CapacityNanoCores, 1)
| project TimeGenerated, Computer, CpuPercent
| render timechart
```

```kusto
// 6. Top containers by memory working set (Perf)
Perf
| where TimeGenerated > ago(30m)
| where ObjectName == "K8SContainer" and CounterName == "memoryWorkingSetBytes"
| summarize AvgMB = avg(CounterValue) / 1024 / 1024 by InstanceName
| top 10 by AvgMB desc
```

```kusto
// 7. Node disk usage (InsightsMetrics)
InsightsMetrics
| where TimeGenerated > ago(30m)
| where Namespace == "container.azm.ms/disk" and Name == "used_percent"
| extend Tags = todynamic(Tags)
| summarize UsedPercent = max(Val) by Computer, Device = tostring(Tags.device)
| order by UsedPercent desc
```

```kusto
// 8. Warning events by reason (BackOff, FailedScheduling, Unhealthy, ...)
KubeEvents
| where TimeGenerated > ago(1h)
| where KubeEventType == "Warning"
| where Reason in ("BackOff", "FailedScheduling", "Unhealthy", "FailedMount", "Evicted", "OOMKilling", "FailedCreatePodSandBox")
| summarize Events = count(), LastSeen = max(TimeGenerated), Message = take_any(Message)
    by Namespace, ObjectKind, Name, Reason
| order by LastSeen desc
```

What this does:

- `summarize arg_max(TimeGenerated, *) by ...` keeps only the latest row per pod or node. Inventory tables write a new snapshot every interval, so without this you count the same pod many times.
- `ContainerStatusReason` shows values like `CrashLoopBackOff` or `ImagePullBackOff`. `ContainerLastStatus` holds the last termination reason, such as `OOMKilled`.
- **OOMKilled** is a container termination reason, not a normal Kubernetes event reason. Look for it in pod status. The `OOMKilling` event, when present, comes from the node.
- `Perf` stores counters in nanocores and bytes. Divide by capacity to get a percentage.
- In `ContainerLogV2`, `LogMessage` is dynamic (it can be JSON), so `tostring()` makes text search safe.

#### Step 8: Create an Action Group

```bash
az monitor action-group create \
  --resource-group $RG --name $AG --short-name aksoncall \
  --action email oncall-email "$EMAIL"

AG_ID=$(az monitor action-group show -g $RG -n $AG --query id -o tsv)
```

What this does:

- An Action Group is a reusable list of receivers: email, SMS, push, voice, webhook, Logic App, Function, ITSM, Event Hub.
- `--short-name` must be 12 characters or fewer. It appears in SMS and email.
- Every alert rule below points to this Action Group, so changing the on-call email is one change.

#### Step 9: Log search alert rules

```bash
az monitor scheduled-query create \
  --resource-group $RG --name "aks-pods-not-running" \
  --scopes $LAW_ID \
  --condition "count 'NotRunning' > 0" \
  --condition-query NotRunning="KubePodInventory | where ClusterName == '$AKS' | summarize arg_max(TimeGenerated, *) by Namespace, Name | where PodStatus in ('Pending', 'Failed', 'Unknown')" \
  --evaluation-frequency 5m --window-size 15m \
  --severity 2 \
  --action-groups $AG_ID \
  --description "One or more pods are Pending, Failed or Unknown"

az monitor scheduled-query create \
  --resource-group $RG --name "aks-crashloop-or-oom" \
  --scopes $LAW_ID \
  --condition "count 'BadPods' > 0" \
  --condition-query BadPods="KubePodInventory | where ClusterName == '$AKS' | where ContainerStatusReason == 'CrashLoopBackOff' or ContainerLastStatus has 'OOMKilled' | distinct Namespace, Name" \
  --evaluation-frequency 5m --window-size 15m \
  --severity 2 \
  --action-groups $AG_ID \
  --description "Containers in CrashLoopBackOff or OOMKilled"

az monitor scheduled-query list -g $RG -o table
```

What this does:

- `--scopes` is the Log Analytics workspace that holds the data.
- `--condition "count 'NotRunning' > 0"` fires when the query named `NotRunning` returns at least one row.
- `--window-size 15m` is the time range the query looks at; `--evaluation-frequency 5m` is how often it runs.
- Severity 0 is critical, 4 is verbose. Use 0-1 for "wake someone up" and 2-3 for working hours.
- Log alerts on the 1-minute frequency cost more; 5 minutes is a good default.
- Tip: add `--mute-actions-duration` or rely on stateful alerts (`--auto-mitigate`) to avoid repeat emails while a problem stays open.

#### Step 10: Metric alerts and recommended alerts

AKS publishes platform metrics that alert fast and cheaply:

```bash
az monitor metrics alert create \
  --resource-group $RG --name "aks-node-cpu-high" \
  --scopes $AKS_ID \
  --condition "avg node_cpu_usage_percentage > 80" \
  --window-size 15m --evaluation-frequency 5m \
  --severity 2 --action $AG_ID \
  --description "Average node CPU above 80% for 15 minutes"

az monitor metrics alert create \
  --resource-group $RG --name "aks-node-memory-high" \
  --scopes $AKS_ID \
  --condition "avg node_memory_working_set_percentage > 85" \
  --window-size 15m --evaluation-frequency 5m \
  --severity 2 --action $AG_ID \
  --description "Average node memory working set above 85%"
```

What this does:

- Metric alerts evaluate near real time and cost less than log alerts.
- `node_cpu_usage_percentage` and `node_memory_working_set_percentage` are AKS platform metrics, no agent needed.
- List metric names with `az monitor metrics list-definitions --resource $AKS_ID -o table`.

**Recommended alerts**: in the portal, open the cluster > **Alerts** > **Set up recommendations** (or **Monitoring > Insights > Recommended alerts**). This creates a starter set of Prometheus alert rules (node, pod and cluster level) wired to an Action Group of your choice.

#### Step 11: Prometheus alert rules (PromQL)

Prometheus alert rules live in a **rule group** linked to the Azure Monitor workspace and the cluster. Save this as `alerts/prometheus-rules.json`:

```json
[
  {
    "alert": "KubePodCrashLooping",
    "expression": "max_over_time(kube_pod_container_status_waiting_reason{reason=\"CrashLoopBackOff\", job=\"kube-state-metrics\"}[5m]) >= 1",
    "for": "PT15M",
    "severity": 3,
    "labels": { "team": "platform" },
    "annotations": { "description": "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping" },
    "actions": [ { "actionGroupId": "<action-group-resource-id>" } ],
    "enabled": true
  },
  {
    "alert": "KubeContainerOOMKilled",
    "expression": "sum by (cluster, namespace, pod, container) (kube_pod_container_status_last_terminated_reason{reason=\"OOMKilled\"}) > 0",
    "for": "PT5M",
    "severity": 3,
    "labels": { "team": "platform" },
    "annotations": { "description": "Container {{ $labels.container }} in {{ $labels.namespace }}/{{ $labels.pod }} was OOMKilled" },
    "actions": [ { "actionGroupId": "<action-group-resource-id>" } ],
    "enabled": true
  }
]
```

```bash
sed -i "s#<action-group-resource-id>#$AG_ID#g" alerts/prometheus-rules.json

az alerts-management prometheus-rule-group create \
  --name aks-obs-lab-pod-alerts \
  --resource-group $RG --location $LOC \
  --cluster-name $AKS \
  --scopes $AMW_ID $AKS_ID \
  --interval PT1M \
  --enabled true \
  --description "Pod level alerts for $AKS" \
  --rules @alerts/prometheus-rules.json
```

What this does:

- `expression` is PromQL evaluated against the Azure Monitor workspace every `interval`.
- `for: PT15M` means the condition must stay true for 15 minutes before firing, which removes noise from short blips.
- `kube_pod_container_status_waiting_reason` and `kube_pod_container_status_last_terminated_reason` come from kube-state-metrics, which Managed Prometheus scrapes by default.
- If the CLI shape changes in your version, check `az alerts-management prometheus-rule-group create --help`, or deploy the same rule group with Bicep/ARM (`Microsoft.AlertsManagement/prometheusRuleGroups`).

#### Step 12: Workbooks and dashboards

- **Container Insights views**: cluster > **Monitoring > Insights** shows Cluster, Nodes, Controllers and Containers tabs with live data.
- **Workbooks**: cluster > **Monitoring > Workbooks** has built-in reports such as Deployments, Workload details, Kubelet, Node disk capacity, Node network and Persistent volume details. Use **Edit** to add your own KQL (for example query 8 above) and save a copy.
- **Grafana**: the Azure Managed Prometheus folder includes Kubernetes compute resources dashboards (cluster, namespace, node, pod), kubelet and networking. Add a Log Analytics panel with the Azure Monitor data source to mix metrics and logs on one dashboard.
- **Azure dashboards**: pin any KQL chart from **Logs** to a shared Azure dashboard for a quick NOC view.

#### Step 13 (Bonus): Application Insights tracing with OpenTelemetry

Create a workspace-based Application Insights resource:

```bash
az monitor app-insights component create --app ai-aks-obs --location $LOC \
  --resource-group $RG --workspace $LAW_ID
AI_CONN=$(az monitor app-insights component show --app ai-aks-obs -g $RG --query connectionString -o tsv)
kubectl create secret generic appinsights -n obs-demo \
  --from-literal=APPLICATIONINSIGHTS_CONNECTION_STRING="$AI_CONN"
```

A small Flask app:

```python
# app/app.py
import logging
import time

from azure.monitor.opentelemetry import configure_azure_monitor

# Configure BEFORE importing Flask, so auto-instrumentation can hook into it.
# Reads APPLICATIONINSIGHTS_CONNECTION_STRING from the environment.
configure_azure_monitor(logger_name="orders")

from flask import Flask  # noqa: E402
from opentelemetry import trace  # noqa: E402
import requests  # noqa: E402

app = Flask(__name__)
tracer = trace.get_tracer(__name__)
log = logging.getLogger("orders")


@app.get("/orders/<order_id>")
def get_order(order_id: str):
    with tracer.start_as_current_span("load-order") as span:
        span.set_attribute("order.id", order_id)
        time.sleep(0.05)                                   # pretend DB call
        requests.get("https://example.com", timeout=5)     # traced as a dependency
    log.info("Order %s returned", order_id)
    return {"orderId": order_id, "status": "shipped"}


@app.get("/fail")
def fail():
    raise RuntimeError("demo failure")                     # appears in exceptions
```

```text
# app/requirements.txt
flask==3.0.3
requests==2.32.3
azure-monitor-opentelemetry>=1.6.0
```

Inject the connection string in the Deployment:

```yaml
envFrom:
  - secretRef:
      name: appinsights
env:
  - name: OTEL_SERVICE_NAME
    value: orders-api
```

What this does:

- `configure_azure_monitor()` sets up OpenTelemetry tracing, metrics and logs with the Azure Monitor exporter, and auto-instruments Flask, `requests` and other common libraries.
- Each HTTP request becomes a **request** in App Insights; the outbound call becomes a **dependency**; the custom span shows as a step in the end-to-end transaction view.
- `OTEL_SERVICE_NAME` sets the cloud role name, which names the node on the **Application Map**.
- Because it is OpenTelemetry, you can later send the same telemetry to another backend by changing the exporter, not the code.

Query traces:

```kusto
requests
| where timestamp > ago(1h)
| where cloud_RoleName == "orders-api"
| summarize Count = count(), Failed = countif(success == false), P95ms = percentile(duration, 95) by name
```

### Verify it works

```bash
kubectl get pods -n obs-demo
```

```text
NAME                              READY   STATUS             RESTARTS      AGE
crashloop-demo-6d9f8c7b5d-x2k8p   0/1     CrashLoopBackOff   5 (40s ago)   6m
oom-demo                          0/1     OOMKilled          4 (60s ago)   6m
pending-demo                      0/1     Pending            0             6m
```

Then check:

- KQL query 1 returns `pending-demo` (Pending) and the crash looping pod; query 2 shows `oom-demo` with restarts and `OOMKillRows` above 0; query 8 shows `BackOff` and `FailedScheduling`.
- Query 3 shows `ERROR: cannot connect to database` from `crashloop-demo`.
- Within 10-20 minutes you receive alert emails for `aks-pods-not-running` and `aks-crashloop-or-oom`, and (after the `for` period) the Prometheus alerts.
- Check the rules exist and are enabled, then open **Monitor > Alerts** in the portal to see fired alerts and their state (Fired / Resolved):

```bash
az monitor scheduled-query list -g $RG --query "[].{name:name, enabled:enabled, severity:severity}" -o table
az monitor metrics alert list -g $RG --query "[].{name:name, enabled:enabled}" -o table
```

- In Grafana, the **Kubernetes / Compute Resources / Namespace (Pods)** dashboard for `obs-demo` shows the restarts and memory.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| No data in `ContainerLogV2` | V2 not enabled, wrong workspace, or wait time | Check DCR settings, `enableContainerLogV2`, wait 10 minutes |
| `ama-logs` pods CrashLoop or missing | Add-on failed, egress blocked | `kubectl logs -n kube-system <ama-logs-pod>`; allow required outbound endpoints |
| Grafana dashboards empty | Grafana MI lacks Monitoring Data Reader on the AMW | Assign the role; check the Prometheus data source |
| Cannot open Grafana | No Grafana role for your user | Assign Grafana Admin / Editor / Viewer |
| Log alert never fires | Query returns nothing for the window, or table on Basic plan | Test query with the same window; keep alert tables on Analytics |
| Too many alert emails | Stateless alerts, short frequency | Use auto-mitigate, longer windows, `for` periods, alert processing rules |
| Log Analytics bill is high | Verbose app logs, 1-minute interval, all namespaces | Filter namespaces, `5m` interval, Basic plan, reduce log level |
| `scheduled-query` command not found | Old CLI | `az upgrade` or `az extension add --name scheduled-query` |
| No traces in App Insights | `configure_azure_monitor` after Flask import, or missing connection string | Configure first; check env var in the pod |

### Clean up

```bash
kubectl delete namespace obs-demo
az group delete --name $RG --yes --no-wait
```

This deletes the cluster, workspaces, Grafana, alert rules and Action Group in the group. The AKS node resource group (`MC_...`) is deleted with the cluster.

### Next improvements

- Define the whole setup with Bicep or Terraform (DCRs, alert rules, Action Groups, Grafana).
- Add **alert processing rules** to suppress alerts during maintenance windows.
- Route Action Groups to a webhook for Teams, PagerDuty or an ITSM tool.
- Scrape app metrics with Managed Prometheus `PodMonitor`/`ServiceMonitor` custom resources.
- Add SLO-based alerts (error rate and latency burn rate) instead of only resource alerts.
- Enable control plane diagnostic logs (`kube-audit-admin`, `kube-apiserver`) to resource-specific tables for security auditing.
- Correlate traces and logs in App Insights with `operation_Id`.

### How to explain this project in an interview

> "This was a hands-on lab to build full observability for AKS with Azure-native tools. I enabled Container Insights with a data collection rule that uses the ContainerLogV2 schema, excludes noisy namespaces and collects only the tables I need, and I looked at the Usage table to understand cost. I turned on Managed Prometheus into an Azure Monitor workspace and linked Azure Managed Grafana for dashboards. Then I deployed broken pods on purpose: a crash loop, an OOM kill and an unschedulable pod, and wrote KQL against KubePodInventory, KubeEvents and ContainerLogV2 to find each one. For alerting I created an Action Group, log search alerts for pods not running and crash loops, metric alerts for node CPU and memory, and PromQL rules for CrashLoopBackOff. As a bonus I added App Insights tracing with the OpenTelemetry distro to a small Flask app, so I could explain how metrics, logs and traces work together."

Points that impress interviewers:

- You can explain metrics vs logs vs traces and which Azure service stores each.
- You talk about cost: ContainerLogV2, Basic plan, namespace filtering, collection interval.
- You reproduced real failures and proved alerts fire, instead of only enabling features.
- You know when to use a metric alert vs a log alert vs a Prometheus alert.

## Interview Questions

<details><summary>Q1. [Basic] What is the difference between metrics, logs and traces?</summary>

**Answer:**

- **Metrics**: numeric values over time (CPU %, request rate). Cheap, fast, good for dashboards and alerts.
- **Logs**: detailed events (container output, Kubernetes events). Good for root cause.
- **Traces**: the path of one request through services with timing per step. Good for finding where latency or errors come from.

In AKS on Azure: metrics go to Managed Prometheus or platform metrics, logs to Log Analytics, traces to Application Insights.

</details>

<details><summary>Q2. [Basic] What does Container Insights collect, and where does it store it?</summary>

**Answer:**

The monitoring add-on runs the Azure Monitor Agent (`ama-logs`) on each node. It collects container stdout/stderr (`ContainerLogV2`), Kubernetes events (`KubeEvents`), inventory (`KubePodInventory`, `KubeNodeInventory`, `KubeServices`), and performance data (`Perf`, `InsightsMetrics`). A data collection rule controls what is collected, and the data lands in a Log Analytics workspace where you query it with KQL.

</details>

<details><summary>Q3. [Basic] What is an Action Group?</summary>

**Answer:**

A reusable set of notification receivers and actions that alert rules call when they fire: email, SMS, voice, push, webhook, Logic App, Function, Automation runbook, ITSM, Event Hub. Many alert rules can share one Action Group, so on-call changes happen in one place.

</details>

<details><summary>Q4. [Intermediate] Why use ContainerLogV2 instead of the old ContainerLog table?</summary>

**Answer:**

- It includes `PodName`, `PodNamespace` and `ContainerName` directly, so you do not need to join with `KubePodInventory`.
- It parses JSON logs into a dynamic `LogMessage` and adds `LogLevel`.
- It supports the **Basic** logs plan for lower ingestion cost.
- Multi-line log support is available.

It is the default for new deployments and the recommended schema.

</details>

<details><summary>Q5. [Intermediate] When do you use a metric alert, a log search alert or a Prometheus alert?</summary>

**Answer:**

| Type | Use when | Notes |
| --- | --- | --- |
| Metric alert | Platform metrics like node CPU/memory | Near real-time, cheap, simple thresholds |
| Log search alert | You need KQL logic, joins or text search (pod status, error logs) | More flexible, more delay and cost |
| Prometheus alert | You already use PromQL and kube-state-metrics, or want community rules | Evaluated on the Azure Monitor workspace |

Use metric or Prometheus alerts for fast resource signals, log alerts for detailed conditions.

</details>

<details><summary>Q6. [Intermediate] The Log Analytics bill for your AKS clusters doubled. How do you find and reduce the cost? <em>(scenario)</em></summary>

**Answer:**

1. Query the `Usage` table to find which tables grew (`summarize sum(Quantity) by DataType`).
2. If `ContainerLogV2` grew, find the noisy pods: `ContainerLogV2 | summarize count() by PodNamespace, PodName`.
3. Fix at the source: lower app log level, stop debug logs, remove health-check logging.
4. Tune the DCR: exclude namespaces, raise the collection interval to 5 minutes, drop unused streams.
5. Move rarely queried logs to the **Basic** plan; use a commitment tier for steady volume.
6. Add a daily cap for non-production workspaces and an alert on ingestion volume.

</details>

<details><summary>Q7. [Intermediate] A pod keeps restarting. How do you investigate with Azure Monitor? <em>(scenario)</em></summary>

**Answer:**

1. `KubePodInventory`: check `ContainerStatusReason` (CrashLoopBackOff, ImagePullBackOff) and `ContainerLastStatus` (OOMKilled, Error, exit code).
2. `KubeEvents`: look for `BackOff`, `Unhealthy` (failing probes), `FailedMount`.
3. `ContainerLogV2`: read the last log lines from that pod before it died.
4. Memory and CPU: `Perf` for `memoryWorkingSetBytes` vs the limit; Grafana pod dashboards.
5. Fix: raise limits if OOM, fix probes if they kill healthy pods, fix config or dependencies if the app exits on start.

</details>

<details><summary>Q8. [Advanced] How do Managed Prometheus and Managed Grafana fit together, and why use them instead of self-hosted Prometheus?</summary>

**Answer:**

- `ama-metrics` pods in the cluster scrape targets and send samples to an **Azure Monitor workspace** (managed, long retention, highly available).
- **Azure Managed Grafana** reads from that workspace with its managed identity (Monitoring Data Reader) and ships Kubernetes dashboards.
- **Prometheus rule groups** evaluate alert and recording rules on the workspace.

Benefits over self-hosted: no Prometheus servers to scale, no storage to manage, multi-cluster queries in one workspace, Entra ID login and RBAC for Grafana. Trade-offs: cost per sample ingested, and less control over every scrape setting (custom scrape configs are done through ConfigMaps or PodMonitor/ServiceMonitor CRDs).

</details>

<details><summary>Q9. [Advanced] Your team gets so many alerts that people ignore them. How do you fix alert fatigue? <em>(scenario)</em></summary>

**Answer:**

- Alert on **symptoms users feel** (error rate, latency, availability) and SLO burn rate, not on every resource blip.
- Use `for` periods and longer windows so short spikes do not fire.
- Use stateful alerts with auto-resolve so one problem sends one notification.
- Set severities properly and route only Sev 0-1 to paging; others go to a channel or ticket.
- Use **alert processing rules** to suppress alerts during maintenance.
- Review alerts regularly: delete rules nobody acts on, and make every alert link to a runbook.

</details>

<details><summary>Q10. [Advanced] How does OpenTelemetry with the Azure Monitor distro work, and why use it?</summary>

**Answer:**

The Azure Monitor OpenTelemetry distro (`azure-monitor-opentelemetry` for Python) bundles the OpenTelemetry SDK, common instrumentations (Flask, Django, requests, database clients) and the Azure Monitor exporter. One call, `configure_azure_monitor()`, reads the connection string and starts sending requests, dependencies, exceptions, logs and metrics to Application Insights. Benefits: vendor-neutral APIs, W3C trace context propagation across services, and the same instrumentation can export elsewhere later. Set `OTEL_SERVICE_NAME` so each service shows correctly on the Application Map.

</details>
