# Globant - Interview Questions

<details><summary>Q1. What is the use of a DaemonSet?</summary>

A **DaemonSet** makes sure that **one copy of a pod runs on every node** (or on every node that matches a selector). When a new node joins the cluster, the DaemonSet automatically starts a pod on it. When a node is removed, its pod is cleaned up.

### Where DaemonSets are used

| Use case | Example tool |
| --- | --- |
| Log collection from every node | Fluent Bit, Fluentd, Azure Monitor agent (`ama-logs`) |
| Node metrics | Prometheus `node-exporter` |
| Networking | `kube-proxy`, CNI plugins such as Azure CNI, Calico, Cilium |
| Storage | CSI node drivers (Azure Disk/File CSI) |
| Security | Defender for Containers sensor, Falco |

### Example: node-exporter on every node

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      tolerations:                 # also run on tainted nodes (e.g. system pool)
        - operator: Exists
      containers:
        - name: node-exporter
          image: prom/node-exporter:v1.8.2
          ports:
            - containerPort: 9100
```

Notice there is **no `replicas` field**. The number of pods = number of matching nodes.

### Useful commands

```bash
kubectl get daemonset -A                      # list all DaemonSets
kubectl get pods -n kube-system -o wide       # see one kube-proxy pod per node
kubectl rollout status ds/node-exporter -n monitoring
kubectl describe ds node-exporter -n monitoring
```

To run only on some nodes, add a `nodeSelector` (for example `agentpool: linuxpool`) in the pod template.

### Interview answer

> "A DaemonSet runs exactly one pod on every node, or on a selected group of nodes. It is used for node-level agents such as log collectors like Fluent Bit, monitoring agents like node-exporter, kube-proxy, CNI plugins, and CSI drivers. The main advantage is that when the cluster autoscaler adds a new node, the DaemonSet automatically places the agent on it, so we never miss logs or metrics from a node. It has no replica count; the number of pods follows the number of nodes."

</details>

---

<details><summary>Q2. Why use Bicep over ARM templates?</summary>

**Bicep** is a simpler language for Azure infrastructure. It is **not a replacement engine**: Bicep code is converted (transpiled) into an ARM JSON template, and Azure Resource Manager deploys it. So anything ARM can do, Bicep can do, but with much less code.

### Bicep vs ARM

| Point | ARM template (JSON) | Bicep |
| --- | --- | --- |
| Syntax | Long JSON, lots of brackets and `[concat()]` | Short, clean, readable |
| Lines of code | Large | Usually 2-3x smaller |
| References | `[resourceId(...)]`, manual `dependsOn` | `storage.id`, dependencies detected automatically |
| Modules | Linked/nested templates (need a URL or template spec) | Simple `module` keyword with a local file |
| Editor support | Limited | VS Code extension with IntelliSense, type checking, linting |
| New Azure features | Day 0 | Day 0 (same API versions) |
| State file | None | None (Azure itself is the state) |

### Same storage account, both ways

**ARM JSON:**

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "storageName": { "type": "string" }
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2023-01-01",
      "name": "[parameters('storageName')]",
      "location": "[resourceGroup().location]",
      "sku": { "name": "Standard_LRS" },
      "kind": "StorageV2"
    }
  ]
}
```

**Bicep:**

```bicep
param storageName string

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: resourceGroup().location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

output storageId string = storage.id
```

### Commands

```bash
# Preview changes (like terraform plan)
az deployment group what-if -g rg-siva --template-file main.bicep --parameters storageName=sivastore01

# Deploy
az deployment group create -g rg-siva --template-file main.bicep --parameters storageName=sivastore01

# Convert Bicep -> ARM JSON
az bicep build --file main.bicep

# Convert existing ARM JSON -> Bicep (migration)
az bicep decompile --file azuredeploy.json
```

### Interview answer

> "Bicep is a domain-specific language on top of ARM. It compiles to ARM JSON, so it supports every Azure resource on day zero, but the code is much shorter and easier to read. Dependencies are detected automatically when one resource references another, modules are simple local files, and the VS Code extension gives IntelliSense and validation. Like ARM, there is no state file to manage. I use `what-if` to preview changes and `az deployment group create` to deploy. For existing ARM templates, `az bicep decompile` helps migrate them."

</details>

---

<details><summary>Q3. How do you find the process ID if you want to kill a process?</summary>

### Step 1: Find the PID

| Command | What it does |
| --- | --- |
| `ps -ef \| grep nginx` | Lists all processes and filters by name |
| `pgrep -a nginx` | Prints PID and command line of matching processes |
| `pidof nginx` | Prints only PIDs of the exact program name |
| `ss -ltnp \| grep :8080` | Finds which process is listening on port 8080 |
| `lsof -i :8080` | Same, using lsof |
| `top` / `htop` | Interactive view, sorted by CPU/memory |

```bash
$ ps -ef | grep [n]ginx
root      1234     1  0 10:01 ?  00:00:00 nginx: master process
www-data  1235  1234  0 10:01 ?  00:00:00 nginx: worker process
```

The second column (`1234`) is the PID. The `[n]ginx` trick stops `grep` from matching itself.

### Step 2: Kill it

```bash
kill 1234          # sends SIGTERM (15): asks the process to stop gracefully
kill -9 1234       # sends SIGKILL (9): forces stop, use only if SIGTERM does not work
pkill nginx        # kill by name
killall nginx      # kill all processes with that exact name
```

Always try `kill` (SIGTERM) first so the application can close files and connections cleanly.

### Real example: port already in use

```bash
$ ss -ltnp | grep :8080
LISTEN 0 100 *:8080 *:* users:(("java",pid=4521,fd=12))

$ kill 4521
```

### Windows equivalent

```powershell
Get-Process -Name notepad          # find PID
Stop-Process -Id 4521 -Force       # kill
# or in cmd: tasklist | findstr notepad ; taskkill /PID 4521 /F
```

### Interview answer

> "I use `ps -ef | grep <name>` or `pgrep -a <name>` to get the PID. If I only know the port, I use `ss -ltnp` or `lsof -i :<port>`. Then I run `kill <PID>`, which sends SIGTERM for a graceful shutdown. Only if the process does not stop, I use `kill -9`, which forces it. I can also kill by name with `pkill`."

</details>

---

<details><summary>Q4. The IP is whitelisted in the VM's NSG with only an inbound rule; no outbound rule is set. Will ping work?</summary>

**Yes, ping from the whitelisted IP to the VM will work**, as long as the inbound rule allows **ICMP** (or `Any` protocol). There are two reasons:

1. **NSGs are stateful.** If an inbound request is allowed, the reply traffic for that same connection is automatically allowed back out. You do not need a matching outbound rule.
2. **Default outbound rules already exist.** Every NSG has default rules `AllowVnetOutBound` and `AllowInternetOutBound`, so outbound is open unless you add a deny rule.

### Flow

```text
Whitelisted IP 203.0.113.10
      |  ICMP Echo Request
      v
NSG inbound rule: Allow 203.0.113.10, protocol ICMP  --> allowed
      |
      v
     VM  --> ICMP Echo Reply goes back automatically (stateful)
```

### When ping will still fail

| Reason | Fix |
| --- | --- |
| Inbound rule allows only TCP (e.g. port 22) | Add rule with protocol `ICMP` (or `Any`) |
| Windows VM firewall blocks ICMP by default | Enable "File and Printer Sharing (Echo Request)" rule in Windows Firewall |
| Linux firewall (`iptables`/`ufw`/`firewalld`) drops ICMP | Allow ICMP in the OS firewall |
| VM has no public IP, or ping goes to a Load Balancer IP | Ping the instance public IP (Azure LB does not answer ICMP to its frontend in all cases) |
| An NSG is also on the subnet and does not allow it | Both subnet NSG and NIC NSG must allow the traffic |

### Command to add the rule

```bash
az network nsg rule create -g rg-siva --nsg-name nsg-siva-vm \
  -n Allow-ICMP-From-Office --priority 110 --direction Inbound \
  --access Allow --protocol Icmp \
  --source-address-prefixes 203.0.113.10 --destination-address-prefixes '*'
```

Check what is actually applied on the NIC:

```bash
az network nic list-effective-nsg -g rg-siva -n vm-siva-nic
```

### Interview answer

> "Yes, it will work. NSGs are stateful, so when inbound ICMP from the whitelisted IP is allowed, the echo reply is allowed back automatically without an outbound rule. Also, the default outbound rules allow VNet and Internet traffic anyway. If ping still fails, I check that the inbound rule is for ICMP and not just TCP, check the OS firewall, because Windows blocks ICMP by default, and check effective security rules, because both the subnet NSG and the NIC NSG must allow it."

</details>

---

<details><summary>Q5. How do you achieve high availability and scalability in Kubernetes?</summary>

**High availability (HA)** = the app keeps running when a pod, node, or zone fails.
**Scalability** = the app can grow and shrink with load.

### High availability

| Technique | What it does |
| --- | --- |
| Multiple replicas | `replicas: 3` so one pod failure does not stop the app |
| Spread across nodes and zones | `topologySpreadConstraints` / pod anti-affinity, AKS node pools across zones 1, 2, 3 |
| Readiness and liveness probes | Send traffic only to healthy pods, restart stuck ones |
| PodDisruptionBudget (PDB) | Keeps a minimum number of pods running during upgrades and node drains |
| Rolling updates | `maxUnavailable: 0`, `maxSurge: 1` for zero-downtime deploys |
| Control plane HA | AKS Standard tier (uptime SLA) |
| Multi-region (DR) | Second cluster in another region behind Azure Front Door / Traffic Manager |

### Scalability

| Technique | Scales |
| --- | --- |
| HPA | Number of pods, based on CPU/memory/custom metrics |
| KEDA | Pods based on events (queue length, Kafka lag), even to zero |
| VPA | CPU/memory requests of each pod |
| Cluster Autoscaler | Number of nodes |

### Example manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: siva-api
spec:
  replicas: 3
  strategy:
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels: { app: siva-api }
  template:
    metadata:
      labels: { app: siva-api }
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels: { app: siva-api }
      containers:
        - name: api
          image: sivaacr.azurecr.io/siva-api:1.0.0
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits:   { memory: 512Mi }
          readinessProbe:
            httpGet: { path: /health/ready, port: 8080 }
          livenessProbe:
            httpGet: { path: /health/live, port: 8080 }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: siva-api-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels: { app: siva-api }
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: siva-api-hpa
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: siva-api }
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
```

HPA needs `resources.requests` to calculate utilization.

### Commands

```bash
# AKS cluster across 3 zones with cluster autoscaler
az aks create -g rg-siva -n aks-siva --zones 1 2 3 --node-count 3 \
  --enable-cluster-autoscaler --min-count 3 --max-count 10 --tier standard

kubectl get hpa
kubectl get pdb
kubectl get pods -o wide        # check pods are on different nodes
```

### Interview answer

> "For high availability, I run at least three replicas, spread them across nodes and availability zones with topology spread constraints, add readiness and liveness probes, and protect them during upgrades with a PodDisruptionBudget. Deployments use rolling updates with `maxUnavailable: 0`. On AKS, I use zone-redundant node pools and the Standard tier for the control-plane SLA, and for DR a second region behind Front Door. For scalability, HPA scales pods on CPU or custom metrics, KEDA for event-driven workloads, and the Cluster Autoscaler adds nodes when pods are pending."

</details>

---

<details><summary>Q6. How can you send metrics to Prometheus and Grafana?</summary>

Prometheus works on a **pull model**: it **scrapes** a `/metrics` HTTP endpoint every few seconds and stores the data. Grafana does not store metrics; it **queries Prometheus** and draws dashboards.

```text
App (/metrics) <-- scrape -- Prometheus (stores time series) <-- PromQL query -- Grafana (dashboards)
                                   |
                              Alertmanager (alerts)
```

### Step 1: Expose metrics from the app

| Source | How it exposes metrics |
| --- | --- |
| Spring Boot | `micrometer-registry-prometheus` -> `/actuator/prometheus` |
| Python / Node / Go | Prometheus client library -> `/metrics` |
| Linux VM / node | `node-exporter` on port 9100 |
| Kubernetes objects | `kube-state-metrics` |
| Short batch jobs | Push to **Pushgateway**, Prometheus scrapes the Pushgateway |

Spring Boot `application.yml`:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,prometheus
```

### Step 2: Tell Prometheus what to scrape

**On a VM (`prometheus.yml`):**

```yaml
scrape_configs:
  - job_name: "siva-app"
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["10.0.1.4:8080"]
  - job_name: "node"
    static_configs:
      - targets: ["10.0.1.4:9100"]
```

**On Kubernetes (with kube-prometheus-stack), use a ServiceMonitor:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: siva-app
  labels:
    release: monitoring          # must match the Helm release label
spec:
  selector:
    matchLabels:
      app: siva-app              # the Service label
  endpoints:
    - port: http
      path: /actuator/prometheus
      interval: 30s
```

### Step 3: Install Prometheus + Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Open Grafana locally
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
```

### Step 4: Grafana

1. Add Prometheus as a data source (already added by kube-prometheus-stack).
2. Import a dashboard (for example ID `1860` for Node Exporter Full) or build panels with PromQL:

```promql
rate(http_server_requests_seconds_count{job="siva-app"}[5m])
```

### Azure managed option

Azure Monitor **managed Prometheus** + **Azure Managed Grafana**: no Prometheus servers to run.

```bash
az aks update -g rg-siva -n aks-siva --enable-azure-monitor-metrics \
  --azure-monitor-workspace-resource-id <AMW_ID> --grafana-resource-id <GRAFANA_ID>
```

### Interview answer

> "Prometheus uses a pull model. First, the application exposes a `/metrics` endpoint, for Spring Boot through Micrometer at `/actuator/prometheus`, and node-exporter exposes VM metrics. Then Prometheus scrapes those endpoints, configured through `scrape_configs` on a VM or a ServiceMonitor in Kubernetes with kube-prometheus-stack. For short batch jobs, I push to the Pushgateway. Grafana uses Prometheus as a data source and shows dashboards with PromQL queries, and Alertmanager handles alerts. On AKS, I prefer Azure Managed Prometheus with Azure Managed Grafana to avoid running the monitoring stack ourselves."

</details>

---

<details><summary>Q7. How do you do deployments in a Function App? Zip file? How do you create a function?</summary>

### Part 1: Create a function locally (Azure Functions Core Tools)

```bash
func init siva-func --worker-runtime python      # create project
cd siva-func
func new --name HttpHello --template "HTTP trigger" --authlevel function
func start                                         # run locally at http://localhost:7071/api/HttpHello
```

### Part 2: Create the Function App in Azure

A Function App needs a **resource group**, a **storage account**, and a **hosting plan** (Consumption, Flex Consumption, Premium, or App Service plan).

```bash
az group create -n rg-siva -l eastus
az storage account create -n sivafuncstore01 -g rg-siva -l eastus --sku Standard_LRS

az functionapp create -g rg-siva -n siva-func-app \
  --storage-account sivafuncstore01 \
  --consumption-plan-location eastus \
  --runtime python --runtime-version 3.11 \
  --functions-version 4 --os-type Linux
```

### Part 3: Deployment options

| Method | When to use |
| --- | --- |
| `func azure functionapp publish` | Quick deploy from a developer machine |
| **Zip deploy** | Package the app as a zip and push it; most common in CI/CD |
| Run from package (`WEBSITE_RUN_FROM_PACKAGE=1`) | App runs directly from the zip; faster cold start, read-only files |
| Azure DevOps `AzureFunctionApp@2` task | Standard pipeline deployment (uses zip deploy internally) |
| Deployment slots | Deploy to `staging`, test, then swap to production with zero downtime |

**Yes, zip is the standard way.** Example:

```bash
# Option A: Core Tools
func azure functionapp publish siva-func-app

# Option B: Zip deploy
zip -r app.zip . -x ".venv/*" "local.settings.json"
az functionapp deployment source config-zip -g rg-siva -n siva-func-app --src app.zip
```

`local.settings.json` is only for local development. App settings in Azure are set with:

```bash
az functionapp config appsettings set -g rg-siva -n siva-func-app --settings "DB_URL=@Microsoft.KeyVault(SecretUri=https://kv-siva.vault.azure.net/secrets/db-url/)"
```

### Part 4: Azure DevOps pipeline

```yaml
stages:
  - stage: Build
    jobs:
      - job: Build
        pool: { vmImage: ubuntu-latest }
        steps:
          - script: pip install -r requirements.txt --target=".python_packages/lib/site-packages"
          - task: ArchiveFiles@2
            inputs:
              rootFolderOrFile: $(System.DefaultWorkingDirectory)
              includeRootFolder: false
              archiveType: zip
              archiveFile: $(Build.ArtifactStagingDirectory)/app.zip
          - publish: $(Build.ArtifactStagingDirectory)/app.zip
            artifact: drop

  - stage: Deploy
    dependsOn: Build
    jobs:
      - deployment: DeployFunc
        environment: siva-dev
        pool: { vmImage: ubuntu-latest }
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureFunctionApp@2
                  inputs:
                    connectedServiceNameARM: sc-azure-siva
                    appType: functionAppLinux
                    appName: siva-func-app
                    package: $(Pipeline.Workspace)/drop/app.zip
                    deploymentMethod: zipDeploy
```

### Interview answer

> "I create a function with Azure Functions Core Tools: `func init` for the project and `func new` with a trigger template such as HTTP trigger, and I test it locally with `func start`. In Azure, I create a storage account, a hosting plan, and the Function App with `az functionapp create`, usually through Terraform. For deployment, yes, I use zip deploy: the pipeline packages the code into a zip, publishes it as an artifact, and the `AzureFunctionApp@2` task deploys it, often with run-from-package. For production, I deploy to a staging slot and swap for zero downtime. Secrets come from Key Vault references in app settings, not from `local.settings.json`."

</details>

---

<details><summary>Q8. Your build stage has warnings. It must deploy to Dev but not to Prod. How do you do it in an Azure YAML multi-stage pipeline?</summary>

When a stage finishes with warnings, its result is **`SucceededWithIssues`** (not `Succeeded`).

- The default condition `succeeded()` is **true** for both `Succeeded` and `SucceededWithIssues`. So **Dev** deploys.
- For **Prod**, add a condition that checks the Build result is exactly `Succeeded`. So Prod is **skipped** when there are warnings.

### Possible stage results

| Result | Meaning |
| --- | --- |
| `Succeeded` | Clean, no warnings |
| `SucceededWithIssues` | Passed, but with warnings or a step with `continueOnError: true` failed |
| `Failed` | Failed |
| `Canceled` / `Skipped` | Canceled or not run |

### Pipeline

```yaml
trigger:
  - main

stages:
  - stage: Build
    jobs:
      - job: Build
        pool: { vmImage: ubuntu-latest }
        steps:
          - script: mvn -B clean package
            displayName: Build

          - script: mvn -B checkstyle:check
            displayName: Lint (warnings allowed)
            continueOnError: true          # failure here -> SucceededWithIssues

  - stage: DeployDev
    dependsOn: Build
    condition: succeeded()                # true for Succeeded AND SucceededWithIssues
    jobs:
      - deployment: Dev
        environment: siva-dev
        pool: { vmImage: ubuntu-latest }
        strategy:
          runOnce:
            deploy:
              steps:
                - script: echo "Deploying to Dev"

  - stage: DeployProd
    dependsOn:
      - Build
      - DeployDev
    condition: |
      and(
        succeeded(),
        eq(dependencies.Build.result, 'Succeeded')
      )
    jobs:
      - deployment: Prod
        environment: siva-prod              # add approvals on this environment
        pool: { vmImage: ubuntu-latest }
        strategy:
          runOnce:
            deploy:
              steps:
                - script: echo "Deploying to Prod"
```

To mark a run as "with warnings" from your own script:

```bash
echo "##vso[task.logissue type=warning]Deprecated API used"
echo "##vso[task.complete result=SucceededWithIssues;]"
```

### Result

| Build result | Dev | Prod |
| --- | --- | --- |
| `Succeeded` | Deploys | Deploys (after approval) |
| `SucceededWithIssues` | Deploys | **Skipped** |
| `Failed` | Skipped | Skipped |

### Interview answer

> "When a build has warnings, the stage result is `SucceededWithIssues`. The default `succeeded()` condition treats that as success, so the Dev stage runs normally. For the Prod stage, I add `dependsOn: [Build, DeployDev]` and the condition `and(succeeded(), eq(dependencies.Build.result, 'Succeeded'))`. So Prod only runs when the build was completely clean. On top of that, the Prod environment has approvals and checks."

</details>

---

<details><summary>Q9. Shell script: delete logs older than 30 days in the siva folder that are larger than 500 MB. Do you need rm -rf? Is <code>find /var/siva -type f -name *.log -size 500M -mtime +30 -delete</code> correct?</summary>

**No, you do not need `rm -rf`.** `find ... -delete` deletes the matching files itself. `-r` is only for directories, and we only want files (`-type f`).

The command is **almost** right, but has two mistakes:

| Part | Problem | Correct |
| --- | --- | --- |
| `-name *.log` | Without quotes, the shell may expand `*.log` before `find` sees it | `-name "*.log"` |
| `-size 500M` | Means **exactly** 500 MB (rounded), not greater | `-size +500M` |
| `-mtime +30` | Correct: modified **more than** 30 days ago | Keep it |

### Correct command

```bash
# 1. Dry run first: only list what would be deleted
find /var/siva -type f -name "*.log" -size +500M -mtime +30 -print

# 2. Delete
find /var/siva -type f -name "*.log" -size +500M -mtime +30 -delete
```

### Quick reference

| Option | Meaning |
| --- | --- |
| `-mtime +30` | Older than 30 days |
| `-mtime -30` | Modified within the last 30 days |
| `-size +500M` | Bigger than 500 MB |
| `-size -500M` | Smaller than 500 MB |
| `-maxdepth 1` | Do not go into sub-folders |

### Script version (with logging)

```bash
#!/bin/bash
set -euo pipefail

LOG_DIR="/var/siva"
DAYS=30
SIZE="+500M"
REPORT="/var/log/siva-cleanup.log"

if [[ ! -d "$LOG_DIR" ]]; then
  echo "$(date) ERROR: $LOG_DIR not found" >> "$REPORT"
  exit 1
fi

echo "$(date) Starting cleanup in $LOG_DIR" >> "$REPORT"

find "$LOG_DIR" -type f -name "*.log" -size "$SIZE" -mtime +"$DAYS" -print -delete >> "$REPORT"

echo "$(date) Cleanup done" >> "$REPORT"
```

Schedule it daily at 2 AM with cron:

```bash
crontab -e
0 2 * * * /opt/scripts/siva-cleanup.sh
```

If a process still has the file open, deleting it does not free disk space until the process restarts. Check with `lsof +L1`. For log files that are still being written, use `truncate -s 0 file.log` or `logrotate` instead.

### Interview answer

> "I don't need `rm -rf`, because `find` with `-delete` removes the matching files directly, and `-r` is only for directories. The command needs two fixes: quote the pattern as `"*.log"` so the shell does not expand it, and use `-size +500M`, because `500M` without the plus means exactly 500 MB. So it becomes `find /var/siva -type f -name "*.log" -size +500M -mtime +30 -delete`. I always run it with `-print` first as a dry run, and then schedule the script with cron or use logrotate."

</details>

---

<details><summary>Q10. If you have Deployment and StatefulSet, why do you need a DaemonSet?</summary>

Each controller solves a different problem. Deployment and StatefulSet decide **how many** pods run; a DaemonSet decides **one pod per node**.

| | Deployment | StatefulSet | DaemonSet |
| --- | --- | --- | --- |
| Pod count | `replicas: N` | `replicas: N` | One per node (automatic) |
| Placement | Anywhere the scheduler chooses | Anywhere the scheduler chooses | Every node (or selected nodes) |
| Pod names | Random (`api-7d9f-xk2p`) | Stable (`db-0`, `db-1`) | Per node |
| Storage | Usually shared/none | Own PVC per pod | Usually `hostPath` to read node files |
| Example | Web API, frontend | MySQL, Kafka, Redis | Fluent Bit, node-exporter, kube-proxy |

### Why a Deployment cannot replace it

Suppose you have **5 nodes** and need a log agent on each one.

- Deployment with `replicas: 5`: the scheduler might put 2 pods on node-1 and none on node-4. Logs from node-4 are lost.
- Cluster autoscaler adds node-6: the Deployment does nothing. Node-6 has no agent.
- DaemonSet: exactly one pod on each of the 5 nodes, and node-6 gets one automatically.

```bash
kubectl get nodes                        # 3 nodes
kubectl get ds -n kube-system            # DESIRED = 3, CURRENT = 3
# scale node pool to 4
az aks nodepool scale -g rg-siva --cluster-name aks-siva -n nodepool1 --node-count 4
kubectl get ds -n kube-system            # DESIRED = 4, CURRENT = 4
```

### Interview answer

> "Deployment and StatefulSet run a fixed number of replicas wherever the scheduler places them. A Deployment is for stateless apps, a StatefulSet for apps that need stable names and their own storage. Neither guarantees one pod on each node. Node-level agents such as log collectors, node-exporter, kube-proxy, and CSI drivers must run on every node, including new nodes added by the autoscaler. A DaemonSet guarantees exactly that, so it is a different use case, not a duplicate."

</details>

---

<details><summary>Q11. How can you send alerts from Azure Monitor?</summary>

An Azure Monitor alert has three parts:

```text
Scope (what to watch) + Condition (when to fire) --> Alert rule --> Action group (who/how to notify)
```

| Part | Examples |
| --- | --- |
| Scope | VM, AKS cluster, App Service, Log Analytics workspace |
| Signal type | **Metric** (CPU > 80%), **Log** (KQL query), **Activity log** (VM deleted), **Service health** |
| Action group | Email, SMS, voice, Azure app push, webhook (Teams/Slack), Logic App, Azure Function, ITSM, Automation runbook |
| Severity | Sev 0 (critical) to Sev 4 (verbose) |

### Step 1: Create an action group

```bash
az monitor action-group create -g rg-siva -n ag-siva-oncall --short-name sivaoncall \
  --action email siva siva@example.com \
  --action webhook teams https://example.webhook.office.com/xxxx
```

### Step 2: Create a metric alert (CPU > 80% for 5 minutes)

```bash
VM_ID=$(az vm show -g rg-siva -n vm-siva --query id -o tsv)

az monitor metrics alert create -g rg-siva -n alert-vm-high-cpu \
  --scopes "$VM_ID" \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m --evaluation-frequency 1m \
  --severity 2 \
  --action ag-siva-oncall \
  --description "CPU above 80% on vm-siva"
```

### Step 3 (optional): Log alert with KQL

Example query for a log search alert on AKS (pods in CrashLoopBackOff):

```kusto
KubePodInventory
| where ContainerStatusReason == "CrashLoopBackOff"
| summarize count() by Name, Namespace
```

Create it in **Monitor > Alerts > Create > Alert rule**, choose the Log Analytics workspace, paste the query, set "Number of results > 0", and attach `ag-siva-oncall`.

### Good practice

- Use **alert processing rules** to mute alerts during maintenance windows.
- Define alerts in Terraform/Bicep so every environment gets the same alerts.
- Avoid noisy alerts: use proper thresholds and windows.

### Interview answer

> "In Azure Monitor, I create an alert rule with a scope, a condition, and an action group. The condition can be a metric, such as CPU above 80% for 5 minutes, a log query in KQL, or an activity log event, such as a resource being deleted. The action group defines the notification: email, SMS, a webhook to Teams or Slack, a Logic App, or an ITSM tool like ServiceNow. I create these with the CLI or Terraform so all environments are consistent, and I use alert processing rules to suppress alerts during maintenance."

</details>

---

<details><summary>Q12. How do you send alerts from the Azure DevOps pipeline itself? Cron?</summary>

There are three common ways to alert, plus cron (scheduled triggers) to **run** the pipeline on a schedule.

### Option 1: Built-in notifications (no code)

**Project settings > Notifications > New subscription > Build > "A build fails"**. Choose the team, a group, or a custom email address. Users can also set personal ones under **User settings > Notifications**.

### Option 2: Service hooks / Teams app

- **Project settings > Service hooks > Microsoft Teams / Slack / Webhook**, event "Build completed" or "Run state changed", filtered by status = failed.
- Or install the **Azure Pipelines app in Teams** and run `@Azure Pipelines subscribe <pipeline URL>` in the channel.

### Option 3: A step in the YAML that runs only on failure

```yaml
steps:
  - script: ./deploy.sh
    displayName: Deploy

  - script: |
      curl -H "Content-Type: application/json" -d '{
        "text": "Pipeline $(Build.DefinitionName) #$(Build.BuildNumber) FAILED on $(Build.SourceBranchName). $(System.CollectionUri)$(System.TeamProject)/_build/results?buildId=$(Build.BuildId)"
      }' "$(TEAMS_WEBHOOK_URL)"
    displayName: Notify Teams on failure
    condition: failed()
```

`TEAMS_WEBHOOK_URL` is stored as a secret variable or in a variable group linked to Key Vault.

### Cron: scheduled pipeline runs

```yaml
schedules:
  - cron: "0 2 * * 1-5"          # 02:00 UTC, Monday to Friday
    displayName: Nightly build
    branches:
      include:
        - main
    always: true                  # run even if there are no new commits
```

| Cron field | Value here |
| --- | --- |
| Minute | `0` |
| Hour | `2` |
| Day of month | `*` |
| Month | `*` |
| Day of week | `1-5` (Mon-Fri) |

Cron times in Azure DevOps are in **UTC**. A nightly scheduled run + a `condition: failed()` notification step = automatic daily health check with alerts.

### Interview answer

> "Inside Azure DevOps, I use notification subscriptions for build failures to email the team, and service hooks or the Azure Pipelines Teams app to post to a channel. For custom messages, I add a final step with `condition: failed()` that calls a Teams or Slack webhook with the pipeline name and run link; the webhook URL is a secret variable. To run pipelines on a schedule, I use the `schedules` block with a cron expression, which is in UTC, with `always: true` if it must run even without new commits."

</details>

---

<details><summary>Q13. What is the difference between a service endpoint and a private endpoint?</summary>

Both let a VNet reach a PaaS service (Storage, SQL, Key Vault) securely, but they work differently.

| | Service endpoint | Private endpoint |
| --- | --- | --- |
| How it works | Extends the subnet identity to the service over the Azure backbone | Creates a **NIC with a private IP** from your subnet for the service |
| Service IP | Service keeps its **public IP** | Service gets a **private IP** (e.g. `10.0.2.5`) |
| Public endpoint | Still exists; firewall allows only your subnet | Can be fully disabled |
| Access from on-prem (VPN/ExpressRoute) / peered VNets | No | **Yes** |
| DNS changes | None | Needs a private DNS zone (e.g. `privatelink.blob.core.windows.net`) |
| Scope | Whole service type (all storage accounts) from that subnet | One specific resource (one storage account) |
| Data exfiltration protection | Weaker | Stronger |
| Cost | Free | Paid (per hour + per GB) |

### Diagram

```text
Service endpoint:
VM (10.0.1.4) --Azure backbone--> sivastore.blob.core.windows.net (public IP, firewall allows subnet)

Private endpoint:
VM (10.0.1.4) --VNet--> 10.0.2.5 (PE NIC) --> sivastore (public access disabled)
                DNS: sivastore.blob.core.windows.net -> sivastore.privatelink.blob.core.windows.net -> 10.0.2.5
```

### Commands

**Service endpoint:**

```bash
az network vnet subnet update -g rg-siva --vnet-name vnet-siva -n snet-app \
  --service-endpoints Microsoft.Storage

az storage account network-rule add -g rg-siva --account-name sivastore01 \
  --vnet-name vnet-siva --subnet snet-app
az storage account update -g rg-siva -n sivastore01 --default-action Deny
```

**Private endpoint:**

```bash
SA_ID=$(az storage account show -g rg-siva -n sivastore01 --query id -o tsv)

az network private-endpoint create -g rg-siva -n pe-sivastore-blob \
  --vnet-name vnet-siva --subnet snet-pe \
  --private-connection-resource-id "$SA_ID" --group-id blob \
  --connection-name sivastore-blob-conn
```

Then link a private DNS zone (see Q20).

Check from the VM:

```bash
nslookup sivastore01.blob.core.windows.net    # private endpoint -> returns 10.0.x.x
```

### Interview answer

> "A service endpoint keeps the service's public IP but sends traffic from my subnet over the Azure backbone, and the service firewall allows only that subnet. It is free and simple, but it does not work from on-premises or peered networks, and the public endpoint still exists. A private endpoint puts a NIC with a private IP from my VNet in front of one specific resource, so I can disable public access completely, and it works from on-premises and peered VNets. It needs a private DNS zone and has a small cost. For production and sensitive data, I prefer private endpoints."

</details>

---

<details><summary>Q14. A user opens https://siva.com. How does the traffic flow to the container in the pod?</summary>

### End-to-end flow (AKS example)

```text
1. Browser: https://siva.com
       |
2. DNS (Azure DNS / GoDaddy): siva.com -> 20.10.30.40 (public IP)
       |
3. Azure Load Balancer or Application Gateway (WAF) on 20.10.30.40:443
       |
4. Ingress controller pod (NGINX / AGIC)  -> TLS terminated with cert from a Secret / Key Vault
       |  matches Ingress rule: host siva.com, path /
5. Service "siva-web" (ClusterIP 10.0.150.20:80)
       |  kube-proxy (iptables/IPVS) picks one healthy endpoint
6. Pod IP 10.244.1.15:8080   (only pods passing the readiness probe)
       |
7. Container listening on port 8080
```

### Step by step

| Step | Component | What happens |
| --- | --- | --- |
| 1 | Browser | Starts HTTPS request |
| 2 | DNS | Resolves `siva.com` to the public IP of the load balancer / App Gateway |
| 3 | Load balancer / App Gateway | Receives traffic on 443; App Gateway can apply WAF rules |
| 4 | Ingress controller | Terminates TLS, reads `Host` and path, finds the matching Ingress rule |
| 5 | Service | Stable virtual IP and DNS name in front of the pods (selects pods by labels) |
| 6 | kube-proxy / Endpoints | Load-balances to one ready pod IP |
| 7 | Container | `targetPort` 8080 of the container receives the request; response returns the same way |

### The YAML that makes it work

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: siva-ingress
spec:
  ingressClassName: nginx
  tls:
    - hosts: [siva.com]
      secretName: siva-tls
  rules:
    - host: siva.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: siva-web
                port:
                  number: 80
---
apiVersion: v1
kind: Service
metadata:
  name: siva-web
spec:
  type: ClusterIP
  selector:
    app: siva-web            # must match pod labels
  ports:
    - port: 80
      targetPort: 8080       # container port
```

### Debug commands (follow the path)

```bash
nslookup siva.com                               # DNS -> public IP?
kubectl get svc -n ingress-nginx                # ingress controller EXTERNAL-IP matches?
kubectl describe ingress siva-ingress           # host/path/backend correct?
kubectl get endpoints siva-web                  # empty = selector/labels or readiness problem
kubectl get pods -l app=siva-web -o wide
kubectl port-forward svc/siva-web 8080:80       # test the service directly
```

### Interview answer

> "The browser resolves `siva.com` through DNS to the public IP of the Azure Load Balancer or Application Gateway. The request reaches the ingress controller, such as NGINX or AGIC, which terminates TLS and matches the host and path to an Ingress rule. The Ingress forwards to a ClusterIP Service, which selects pods by label, and kube-proxy load-balances to one ready pod IP. Finally, the request reaches the container's `targetPort`, for example 8080. To troubleshoot, I follow the same path: DNS, ingress external IP, Ingress rules, Service endpoints, and pod readiness."

</details>

---

<details><summary>Q15. What is the main reason behind a CrashLoopBackOff issue?</summary>

**CrashLoopBackOff** means: the container **starts, then exits (crashes), and Kubernetes keeps restarting it**, waiting longer each time (10s, 20s, 40s ... up to 5 minutes). It is a **symptom**; the real reason is why the container exits.

### Main reasons

| Reason | How to recognise it |
| --- | --- |
| Application error at startup (exception, bad config) | `kubectl logs --previous` shows a stack trace; exit code `1` |
| Missing env var / ConfigMap / Secret / wrong connection string | Logs: "DB_URL not set", "connection refused" |
| Wrong command or entrypoint | Exit code `127` (command not found) or `126` |
| Out of memory | `Reason: OOMKilled`, exit code `137` |
| Liveness probe fails (too early or wrong path/port) | Events: "Liveness probe failed", container killed |
| Dependency not ready (DB, other service) | App exits because it cannot connect |
| Container has no long-running process | Process finishes, exit code `0`, restarts again |
| Permission issues (read-only FS, non-root user) | Logs: "permission denied" |

### Troubleshooting steps

```bash
kubectl get pods                                  # STATUS: CrashLoopBackOff, RESTARTS: 7
kubectl describe pod siva-api-6c8d9-abcde         # check Last State, Reason, Exit Code, Events
kubectl logs siva-api-6c8d9-abcde --previous      # logs from the crashed container
kubectl get events --sort-by=.lastTimestamp
kubectl get pod siva-api-6c8d9-abcde -o yaml | grep -A5 lastState
```

Example `describe` output:

```text
Last State:     Terminated
  Reason:       OOMKilled
  Exit Code:    137
```

Fix here: increase the memory limit or fix the memory leak.

### Common fixes

- Fix the app config / add the missing Secret or ConfigMap.
- Correct `command` / `args` in the manifest.
- Increase `resources.limits.memory` if OOMKilled.
- Add a `startupProbe` or increase `initialDelaySeconds` for slow-starting apps (e.g. Java).
- Debug the image by running a shell: `kubectl run debug --rm -it --image=<image> -- sh`.

### Interview answer

> "CrashLoopBackOff means the container keeps starting and crashing, and Kubernetes restarts it with an increasing back-off delay. The most common reason is the application itself failing at startup, for example because of a missing environment variable, Secret, or ConfigMap, a wrong database connection, or a wrong command. Other reasons are OOMKilled with exit code 137, or a liveness probe that kills a slow-starting app. I troubleshoot with `kubectl logs --previous` to see why it crashed and `kubectl describe pod` to check the exit code, reason, and events."

</details>

---

<details><summary>Q16. Your terraform plan is clean, but terraform apply is failing. What might be the reason?</summary>

`terraform plan` mostly **reads** state and calls read APIs. It does **not** actually create anything, so Azure only checks many things during `apply`, when the real create/update API is called.

### Common reasons

| Reason | Example error |
| --- | --- |
| **Permissions**: the identity can read but not write | `AuthorizationFailed ... does not have authorization to perform action 'Microsoft.Network/virtualNetworks/write'` |
| **Azure Policy** denies the resource | `RequestDisallowedByPolicy` (e.g. location not allowed, missing tag) |
| **Resource already exists** outside Terraform state | `A resource with the ID ... already exists - to be managed via Terraform this resource needs to be imported` |
| **Globally unique name** already taken | Storage account / Key Vault / web app name in use |
| **Quota / capacity** limits | `QuotaExceeded` for vCPUs, or the VM size is not available in that region/zone |
| **Resource lock** (`CanNotDelete` / `ReadOnly`) | Update or delete blocked |
| **Soft-deleted resource** with the same name | Key Vault or API Management in soft-delete state |
| **Drift / race**: something changed between plan and apply | Someone edited it in the portal, or another pipeline ran |
| **State lock** held by another run | `Error acquiring the state lock` |
| **Values only known at apply time** are invalid | Generated name too long, invalid combination |
| **Dependency timing** | Role assignment not propagated yet, private DNS not ready |
| **Expired credentials / token** during a long apply | Service principal secret expired |

### How I troubleshoot

```bash
# Use a saved plan so apply does exactly what was reviewed
terraform plan -out=tfplan
terraform apply tfplan

# More detail
export TF_LOG=DEBUG
terraform apply tfplan

# Resource exists outside state -> import it
terraform import azurerm_resource_group.rg /subscriptions/<sub-id>/resourceGroups/rg-siva

# Check locks and permissions
az lock list -g rg-siva -o table
az role assignment list --assignee <sp-app-id> -o table

# Stuck state lock (only if no other run is active)
terraform force-unlock <LOCK_ID>
```

### Interview answer

> "Plan only reads state and calls read APIs, so many checks happen only during apply, when Azure actually processes the create or update. The common reasons are: the pipeline's service principal has read but not write permissions, Azure Policy denies the resource, the resource already exists outside the state and needs to be imported, a globally unique name is taken, subscription quota is exceeded, or there is a resource lock or a soft-deleted Key Vault. Drift between plan and apply can also cause it. I read the exact error, enable `TF_LOG=DEBUG` if needed, and always apply a saved plan file so the apply matches what was reviewed."

</details>

---

<details><summary>Q17. What is the difference between a task and a job in an Azure YAML pipeline?</summary>

### Hierarchy

```text
Pipeline
 └── Stage   (e.g. Build, DeployDev, DeployProd)
      └── Job   (runs on ONE agent)
           └── Step  (task or script, runs one after another)
```

| | Task | Job |
| --- | --- | --- |
| What it is | A single unit of work (a step) | A group of steps |
| Runs on | Inside a job | **One agent** (fresh VM for Microsoft-hosted) |
| Order | Steps run **sequentially** | Jobs run in **parallel** by default (use `dependsOn` to order) |
| Examples | `Docker@2`, `AzureCLI@2`, `script:` | `job: Build`, `deployment: DeployProd` |
| Shares files? | Yes, steps in the same job share the workspace | No, jobs share data only through artifacts or output variables |

`script:`, `bash:`, and `pwsh:` are shortcuts for script tasks.

### Example

```yaml
stages:
  - stage: CI
    jobs:
      - job: Build                      # JOB 1
        pool: { vmImage: ubuntu-latest }
        steps:
          - task: Maven@4               # TASK
            inputs:
              mavenPomFile: pom.xml
              goals: package
          - script: echo "Build done"   # TASK (script shortcut)

      - job: Lint                       # JOB 2 runs in parallel with Build
        pool: { vmImage: ubuntu-latest }
        steps:
          - script: npm run lint

      - job: Report                     # JOB 3 waits for both
        dependsOn: [Build, Lint]
        pool: { vmImage: ubuntu-latest }
        steps:
          - script: echo "All checks passed"
```

### Job types

| Type | Use |
| --- | --- |
| `job` | Normal build/test work |
| `deployment` | Deploys to an `environment` (history, approvals, strategies like `runOnce`, `rolling`, `canary`) |
| Agentless (`pool: server`) | Waits, manual validation, REST calls; no agent needed |

### Interview answer

> "A task is a single step, like `Docker@2`, `AzureCLI@2`, or a script, and it runs inside a job. A job is a group of steps that runs on one agent; the steps run one after another and share the same workspace. Jobs in a stage run in parallel by default unless I add `dependsOn`, and they share data only through artifacts or output variables. Stages group jobs. For deployments, I use a deployment job, which targets an environment with approvals and deployment history."

</details>

---

<details><summary>Q18. You need to update one parameter in Terraform, but the plan shows it will recreate the resource. How can you avoid recreating it?</summary>

First, **find why** Terraform wants to replace it. The plan tells you:

```text
# azurerm_storage_account.sa must be replaced
-/+ resource "azurerm_storage_account" "sa" {
      ~ account_replication_type = "LRS" -> "ZRS"
      ~ name                     = "sivastore01" -> "sivastore02" # forces replacement
```

The attribute marked **`# forces replacement`** is the cause. Then choose the right fix:

| Cause | Fix without recreating |
| --- | --- |
| You **renamed the resource block** or moved it into a module | `moved` block (or `terraform state mv`) |
| Changed `count` to `for_each`, or list order changed (indexes shifted) | `moved` blocks for each address |
| The attribute is ForceNew in Azure (e.g. `name`, `location`, VM `admin_username`) but you only need Terraform to stop touching it | `lifecycle { ignore_changes = [...] }` |
| The change can be done in place in Azure but not by the provider (rare) | Change it with `az` CLI / portal, then update the code to match, or ignore it |
| Provider upgrade changed defaults | Set the old value explicitly in code |
| Protect against accidental destroy | `lifecycle { prevent_destroy = true }` (blocks the plan, does not avoid it) |

### Fix 1: `moved` block (resource address changed)

```hcl
# Old: resource "azurerm_storage_account" "sa" {...}
# New name in code:
resource "azurerm_storage_account" "logs" {
  name = "sivastore01"
  # ...
}

moved {
  from = azurerm_storage_account.sa
  to   = azurerm_storage_account.logs
}
```

Or with the CLI:

```bash
terraform state mv azurerm_storage_account.sa azurerm_storage_account.logs
```

### Fix 2: `ignore_changes`

```hcl
resource "azurerm_linux_virtual_machine" "vm" {
  # ...
  custom_data = base64encode(file("init.sh"))

  lifecycle {
    ignore_changes = [custom_data, tags["CreatedOn"]]
  }
}
```

### Fix 3: `prevent_destroy` as a safety net

```hcl
lifecycle {
  prevent_destroy = true      # plan fails instead of deleting a critical resource
}
```

### Verify

```bash
terraform plan        # expect "~ update in-place" or "No changes", NOT "-/+ must be replaced"
```

If the attribute truly can only be set at creation time (e.g. storage account name), the cloud does not allow an in-place change. Then you plan a migration: create the new resource, move the data, and switch over.

### Interview answer

> "First I read the plan to see which attribute shows `forces replacement`. If the replacement happens only because I renamed the resource or moved it into a module, I add a `moved` block or use `terraform state mv`, and then it is a no-op. If the attribute is ForceNew in Azure but I don't actually need Terraform to change it, I use `lifecycle { ignore_changes = [...] }`. For critical resources, I add `prevent_destroy` so a replacement fails the plan. If the property really can only be set at creation time, like a storage account name, recreation cannot be avoided, so I plan a proper migration."

</details>

---

<details><summary>Q19. What is the use of Docker Compose and multi-stage Docker builds?</summary>

They solve different problems:

| | Docker Compose | Multi-stage Dockerfile |
| --- | --- | --- |
| Purpose | **Run several containers together** (app + DB + cache) | **Build a small, secure image** |
| File | `docker-compose.yml` / `compose.yaml` | `Dockerfile` with multiple `FROM` |
| Used for | Local development, testing, simple single-host setups | Every production image |

### Docker Compose example

```yaml
services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      DB_HOST: db
      REDIS_HOST: cache
    depends_on:
      - db
      - cache

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: example
    volumes:
      - dbdata:/var/lib/postgresql/data

  cache:
    image: redis:7

volumes:
  dbdata:
```

```bash
docker compose up -d          # start everything
docker compose ps             # status
docker compose logs -f api    # logs
docker compose down -v        # stop and remove (and volumes)
```

All services share one network, so `api` reaches the database using the hostname `db`.

### Multi-stage Dockerfile example (Spring Boot)

```dockerfile
# Stage 1: build (has Maven + JDK, large)
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -B dependency:go-offline          # cached layer
COPY src ./src
RUN mvn -B package -DskipTests

# Stage 2: runtime (only JRE + jar, small)
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build /app/target/*.jar app.jar
USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

| | Single-stage | Multi-stage |
| --- | --- | --- |
| Image size | ~700 MB (Maven + JDK + source) | ~200 MB (JRE + jar) |
| Attack surface | Build tools and source code inside | Only what is needed to run |
| Build speed | Less caching | Better layer caching |

(Sizes are typical values; they depend on the base images.)

```bash
docker build -t sivaacr.azurecr.io/siva-api:1.0.0 .
docker images | grep siva-api
```

### Interview answer

> "Docker Compose is for running multiple related containers together with one YAML file, for example an API, Postgres, and Redis for local development or testing, with `docker compose up`. A multi-stage Dockerfile is for building images: the first stage uses a heavy image with Maven and the JDK to compile, and the final stage copies only the jar into a small JRE image. That makes the image much smaller and more secure, because build tools and source code are not shipped. In production, Kubernetes replaces Compose, but multi-stage builds are used for every image."

</details>

---

<details><summary>Q20. Your VM needs to access a storage account. How do you establish a secure connection?</summary>

Secure access has two parts: **network** (how traffic travels) and **identity** (who is allowed). Use both.

```text
VM (managed identity) --private IP--> Private endpoint --> Storage account (public access disabled)
                           RBAC: Storage Blob Data Reader
```

### Step 1: Network - private endpoint + private DNS

```bash
SA_ID=$(az storage account show -g rg-siva -n sivastore01 --query id -o tsv)

# Private endpoint in the VM's VNet
az network private-endpoint create -g rg-siva -n pe-sivastore-blob \
  --vnet-name vnet-siva --subnet snet-pe \
  --private-connection-resource-id "$SA_ID" --group-id blob \
  --connection-name sivastore-blob-conn

# Private DNS zone so the storage name resolves to the private IP
az network private-dns zone create -g rg-siva -n privatelink.blob.core.windows.net
az network private-dns link vnet create -g rg-siva -n link-vnet-siva \
  --zone-name privatelink.blob.core.windows.net --virtual-network vnet-siva --registration-enabled false
az network private-endpoint dns-zone-group create -g rg-siva \
  --endpoint-name pe-sivastore-blob -n default \
  --private-dns-zone privatelink.blob.core.windows.net --zone-name blob

# Block public access
az storage account update -g rg-siva -n sivastore01 --public-network-access Disabled
```

A cheaper alternative is a **service endpoint** on the VM subnet (see Q13).

### Step 2: Identity - managed identity + RBAC (no keys)

```bash
# Enable system-assigned managed identity on the VM
az vm identity assign -g rg-siva -n vm-siva
PRINCIPAL_ID=$(az vm show -g rg-siva -n vm-siva --query identity.principalId -o tsv)

# Give it data access on the storage account
az role assignment create --assignee "$PRINCIPAL_ID" \
  --role "Storage Blob Data Reader" --scope "$SA_ID"

# Turn off account keys (Shared Key) so only Entra ID auth works
az storage account update -g rg-siva -n sivastore01 --allow-shared-key-access false
```

### Step 3: Test from the VM

```bash
nslookup sivastore01.blob.core.windows.net      # should return 10.0.x.x
az login --identity
az storage blob list --account-name sivastore01 -c data --auth-mode login -o table
```

### Extra hardening

- `--min-tls-version TLS1_2` and `--https-only true` on the storage account.
- NSG on the private endpoint subnet if needed.
- Diagnostic logs on the storage account to see who accessed what.

### Interview answer

> "I secure both the network and the identity. For the network, I create a private endpoint for the blob service in the VM's VNet, link the `privatelink.blob.core.windows.net` private DNS zone so the storage name resolves to a private IP, and disable public network access. For identity, I enable a managed identity on the VM and give it an RBAC role like Storage Blob Data Reader on the storage account, and I disable shared key access, so there are no keys or SAS tokens in code. I verify with `nslookup` that it resolves to a private IP and with `az login --identity` that access works."

</details>

---

<details><summary>Q21. How do you use WAF? How do you integrate WAF with Application Gateway?</summary>

**WAF (Web Application Firewall)** inspects HTTP/HTTPS requests and blocks common attacks such as **SQL injection, cross-site scripting (XSS)**, and other OWASP Top 10 attacks, plus bad bots. In Azure, WAF runs on **Application Gateway** (regional) or **Azure Front Door** (global).

```text
User --> Application Gateway (WAF_v2 + WAF policy) --> Backend (VM / App Service / AKS)
               |
          Blocked request -> 403 Forbidden, logged in Log Analytics
```

### Key concepts

| Concept | Meaning |
| --- | --- |
| SKU | Application Gateway must be **WAF_v2** |
| WAF policy | Separate resource holding the settings; attached to the gateway, a listener, or a path |
| Managed rules | Microsoft-managed rule sets: OWASP CRS 3.2 / Default Rule Set (DRS), Bot Manager |
| Custom rules | Your own rules: block an IP range, geo-block, rate limiting, match a header |
| Mode | **Detection** = only log; **Prevention** = log and block |
| Exclusions | Skip a rule for a specific field to fix false positives |

### Step 1: Create a WAF policy

```bash
az network application-gateway waf-policy create -g rg-siva -n wafpol-siva \
  --type OWASP --version 3.2

# Start in Detection, move to Prevention after tuning
az network application-gateway waf-policy policy-setting update -g rg-siva \
  --policy-name wafpol-siva --state Enabled --mode Detection
```

### Step 2: Add a custom rule (block an IP range)

```bash
az network application-gateway waf-policy custom-rule create -g rg-siva \
  --policy-name wafpol-siva -n BlockBadIPs --priority 10 \
  --rule-type MatchRule --action Block

az network application-gateway waf-policy custom-rule match-condition add -g rg-siva \
  --policy-name wafpol-siva -n BlockBadIPs \
  --match-variables RemoteAddr --operator IPMatch --values 198.51.100.0/24
```

### Step 3: Attach the policy to Application Gateway

```bash
POLICY_ID=$(az network application-gateway waf-policy show -g rg-siva -n wafpol-siva --query id -o tsv)

az network application-gateway create -g rg-siva -n agw-siva \
  --sku WAF_v2 --capacity 2 \
  --vnet-name vnet-siva --subnet snet-agw \
  --public-ip-address pip-agw-siva \
  --servers 10.0.1.4 10.0.1.5 \
  --waf-policy "$POLICY_ID" --priority 100
```

**Terraform:**

```hcl
resource "azurerm_web_application_firewall_policy" "waf" {
  name                = "wafpol-siva"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  policy_settings {
    enabled = true
    mode    = "Prevention"
  }

  managed_rules {
    managed_rule_set {
      type    = "OWASP"
      version = "3.2"
    }
  }
}

resource "azurerm_application_gateway" "agw" {
  # ... sku { name = "WAF_v2", tier = "WAF_v2" }, listeners, backends ...
  firewall_policy_id = azurerm_web_application_firewall_policy.waf.id
}
```

### Step 4: Monitor and tune

Enable diagnostic settings to Log Analytics, then check what was blocked:

```kusto
AzureDiagnostics
| where Category == "ApplicationGatewayFirewallLog"
| where action_s == "Blocked" or action_s == "Matched"
| project TimeGenerated, clientIp_s, requestUri_s, ruleId_s, Message
```

Add exclusions for false positives, then switch the policy to **Prevention**.

### Interview answer

> "I deploy Application Gateway with the WAF_v2 SKU and create a separate WAF policy with the OWASP 3.2 or Microsoft Default Rule Set, which protects against SQL injection, XSS, and other OWASP Top 10 attacks. I add custom rules for things like IP blocking, geo-filtering, or rate limiting, and attach the policy to the gateway, or to a specific listener if different sites need different rules. I start in Detection mode, send the firewall logs to Log Analytics, tune false positives with exclusions, and then switch to Prevention mode. Everything is defined in Terraform."

</details>

---

<details><summary>Q22. Which ps commands do you use in shell scripts?</summary>

`ps` shows running processes. In scripts it is mostly used to **check if something is running**, **find PIDs**, and **find top CPU/memory consumers**.

### Common ps commands

| Command | Use |
| --- | --- |
| `ps -ef` | All processes, full format (UID, PID, PPID, start time, command) |
| `ps aux` | All processes with %CPU, %MEM |
| `ps -ef \| grep [n]ginx` | Find a process by name (bracket avoids matching grep itself) |
| `ps aux --sort=-%cpu \| head -5` | Top 5 CPU consumers |
| `ps aux --sort=-%mem \| head -5` | Top 5 memory consumers |
| `ps -p 1234 -o pid,ppid,%cpu,%mem,etime,cmd` | Details of one PID, custom columns |
| `ps -u siva` | Processes of user `siva` |
| `ps -eLf` | Show threads |
| `ps -ef --forest` | Process tree (parent/child) |

Related helpers: `pgrep -f <pattern>` (just PIDs), `pkill`, `pidof`, `top -b -n 1` (batch mode for scripts).

### Script 1: Restart a service if it is not running

```bash
#!/bin/bash
SERVICE="nginx"

if pgrep -x "$SERVICE" > /dev/null; then
  echo "$(date) $SERVICE is running"
else
  echo "$(date) $SERVICE is down, restarting..."
  sudo systemctl restart "$SERVICE"
fi
```

### Script 2: Alert on high CPU processes

```bash
#!/bin/bash
THRESHOLD=80

ps -eo pid,comm,%cpu --sort=-%cpu --no-headers | head -5 | while read -r pid cmd cpu; do
  if (( ${cpu%.*} > THRESHOLD )); then
    echo "$(date) High CPU: $cmd (PID $pid) using ${cpu}%"
  fi
done
```

### Script 3: Kill processes running longer than 1 hour

```bash
#!/bin/bash
# etimes = elapsed time in seconds
ps -eo pid,etimes,comm --no-headers | awk '$3=="java" && $2 > 3600 {print $1}' | while read -r pid; do
  echo "Killing long-running java PID $pid"
  kill "$pid"
done
```

### Interview answer

> "In scripts, I use `ps -ef` or `ps aux` to list processes, `ps aux --sort=-%cpu | head` or `--sort=-%mem` to find the top resource consumers, and `ps -p <pid> -o pid,%cpu,%mem,etime,cmd` with custom columns for a specific process. Custom output with `-o` and `--no-headers` is easy to parse with `awk`. To check if a service is running, I prefer `pgrep -x`, because it returns just the PID and a clean exit code. For example, I have a script that restarts a service with systemctl if `pgrep` finds it is not running."

</details>

---

<details><summary>Q23. Write a multi-stage Azure YAML pipeline.</summary>

A complete pipeline: **Build and test -> Docker image to ACR -> Deploy to Dev AKS -> Deploy to Prod AKS (with approval)**.

```text
Build (Maven + tests) --> Docker (build + push to ACR) --> DeployDev --> DeployProd (approval)
```

### Prerequisites

| Item | Name in example |
| --- | --- |
| ACR service connection (Docker registry) | `sc-acr-siva` |
| Kubernetes service connections | `sc-aks-dev`, `sc-aks-prod` |
| Environments | `siva-dev`, `siva-prod` (add **Approvals and checks** on `siva-prod`) |
| Manifests in repo | `k8s/deployment.yaml`, `k8s/service.yaml` |

### azure-pipelines.yml

```yaml
trigger:
  branches:
    include:
      - main

pr:
  - main

variables:
  imageRepository: siva-api
  containerRegistry: sivaacr.azurecr.io
  tag: $(Build.BuildId)
  vmImage: ubuntu-latest

stages:
  # ---------- Stage 1: Build & Test ----------
  - stage: Build
    displayName: Build and test
    jobs:
      - job: Build
        pool: { vmImage: $(vmImage) }
        steps:
          - task: Maven@4
            displayName: Maven package + unit tests
            inputs:
              mavenPomFile: pom.xml
              goals: clean package
              publishJUnitResults: true
              testResultsFiles: "**/surefire-reports/TEST-*.xml"
              javaHomeOption: JDKVersion
              jdkVersionOption: "1.17"

          - publish: k8s
            artifact: manifests
            displayName: Publish K8s manifests

  # ---------- Stage 2: Docker build & push ----------
  - stage: Docker
    displayName: Build and push image
    dependsOn: Build
    condition: and(succeeded(), ne(variables['Build.Reason'], 'PullRequest'))
    jobs:
      - job: Docker
        pool: { vmImage: $(vmImage) }
        steps:
          - task: Docker@2
            displayName: Build and push
            inputs:
              command: buildAndPush
              containerRegistry: sc-acr-siva
              repository: $(imageRepository)
              dockerfile: Dockerfile
              tags: |
                $(tag)
                latest

  # ---------- Stage 3: Deploy to Dev ----------
  - stage: DeployDev
    displayName: Deploy to Dev
    dependsOn: Docker
    jobs:
      - deployment: DeployDev
        environment: siva-dev
        pool: { vmImage: $(vmImage) }
        strategy:
          runOnce:
            deploy:
              steps:
                - task: KubernetesManifest@1
                  displayName: Deploy to AKS Dev
                  inputs:
                    action: deploy
                    connectionType: kubernetesServiceConnection
                    kubernetesServiceConnection: sc-aks-dev
                    namespace: siva-dev
                    manifests: |
                      $(Pipeline.Workspace)/manifests/deployment.yaml
                      $(Pipeline.Workspace)/manifests/service.yaml
                    containers: $(containerRegistry)/$(imageRepository):$(tag)

  # ---------- Stage 4: Deploy to Prod ----------
  - stage: DeployProd
    displayName: Deploy to Prod
    dependsOn: DeployDev
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployProd
        environment: siva-prod          # approval configured on this environment
        pool: { vmImage: $(vmImage) }
        strategy:
          runOnce:
            deploy:
              steps:
                - task: KubernetesManifest@1
                  displayName: Deploy to AKS Prod
                  inputs:
                    action: deploy
                    connectionType: kubernetesServiceConnection
                    kubernetesServiceConnection: sc-aks-prod
                    namespace: siva-prod
                    manifests: |
                      $(Pipeline.Workspace)/manifests/deployment.yaml
                      $(Pipeline.Workspace)/manifests/service.yaml
                    containers: $(containerRegistry)/$(imageRepository):$(tag)
```

### Key points to explain

| Feature | Where |
| --- | --- |
| Stages run in order using `dependsOn` | Build -> Docker -> DeployDev -> DeployProd |
| PRs only build and test | `ne(variables['Build.Reason'], 'PullRequest')` on Docker stage |
| Build once, deploy the same image everywhere | Same `$(tag)` used for Dev and Prod |
| Deployment jobs auto-download artifacts | Manifests available at `$(Pipeline.Workspace)/manifests` |
| Approvals | Set on the `siva-prod` environment, not in YAML |
| Prod only from `main` | Condition on `Build.SourceBranch` |
| `containers:` input | Replaces the image in the manifest with the exact tag |

### Interview answer

> "My multi-stage pipeline has four stages. Build runs Maven with unit tests and publishes the Kubernetes manifests as an artifact. The Docker stage builds the image once and pushes it to ACR with the build ID as tag, and it is skipped for pull requests. DeployDev uses a deployment job targeting the `siva-dev` environment and the KubernetesManifest task to deploy that exact image tag. DeployProd depends on Dev, runs only from the main branch, and targets the `siva-prod` environment, which has approvals and checks configured. So the same tested image is promoted from Dev to Prod."

</details>

---

<details><summary>Q24. What is needed to create a VM? If all prerequisites already exist, what is defined in the VM's resource block?</summary>

### Prerequisites (dependencies)

| Resource | Why it is needed |
| --- | --- |
| Resource group | Container for all resources |
| Virtual network + subnet | The VM's network |
| Network security group | Firewall rules (on subnet or NIC) |
| Public IP (optional) | Only if direct internet access is needed; prefer Bastion |
| **Network interface (NIC)** | Connects the VM to the subnet; **mandatory** |
| SSH key / password (in Key Vault) | Admin login |
| Optional | Availability zone/set, managed identity, data disks, boot diagnostics storage, Log Analytics |

```text
Resource Group
  └── VNet ── Subnet ── NSG
                 └── NIC (+ optional Public IP)
                       └── VM  (OS disk created with the VM)
```

### What goes in the VM resource block

| Argument | Example |
| --- | --- |
| `name`, `resource_group_name`, `location` | `vm-siva`, `rg-siva`, `eastus` |
| `size` | `Standard_B2s` |
| `admin_username` + auth | `admin_ssh_key` (Linux) or `admin_password` |
| `network_interface_ids` | ID of the existing NIC |
| `os_disk` | caching, storage type (`Premium_LRS`), size |
| `source_image_reference` (or `source_image_id`) | Publisher / offer / sku / version |
| Optional | `zone`, `identity`, `custom_data` (cloud-init), `boot_diagnostics`, `tags` |

### Terraform example (prerequisites already exist)

```hcl
data "azurerm_network_interface" "nic" {
  name                = "nic-vm-siva"
  resource_group_name = "rg-siva"
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                = "vm-siva"
  resource_group_name = "rg-siva"
  location            = "eastus"
  size                = "Standard_B2s"
  zone                = "1"

  admin_username                  = "azureuser"
  disable_password_authentication = true
  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  network_interface_ids = [data.azurerm_network_interface.nic.id]

  os_disk {
    name                 = "osdisk-vm-siva"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  custom_data = base64encode(file("cloud-init.yaml"))

  boot_diagnostics {}              # managed storage account

  tags = {
    env   = "dev"
    owner = "siva"
  }
}
```

### Same with Azure CLI

```bash
az vm create -g rg-siva -n vm-siva \
  --image Ubuntu2404 --size Standard_B2s --zone 1 \
  --nics nic-vm-siva \
  --admin-username azureuser --ssh-key-values ~/.ssh/id_rsa.pub \
  --os-disk-size-gb 64 --storage-sku Premium_LRS \
  --assign-identity
```

Data disks are separate resources: `azurerm_managed_disk` + `azurerm_virtual_machine_data_disk_attachment`.

### Interview answer

> "To create a VM, I need a resource group, a VNet and subnet, an NSG, a network interface, optionally a public IP (I prefer Bastion instead), and SSH keys stored in Key Vault. If those already exist, the VM resource block itself only defines the VM: name, resource group, location, size, admin username with an SSH key, the existing NIC ID in `network_interface_ids`, the `os_disk` settings, and the `source_image_reference`. Optionally, I add a zone, a managed identity, cloud-init through `custom_data`, boot diagnostics, and tags. Data disks are separate resources attached to the VM."

</details>

---

<details><summary>Q25. After one pipeline runs, another pipeline should run in Azure DevOps. How do you achieve it?</summary>

The standard way is a **pipeline completion trigger**: the second (downstream) pipeline declares the first (upstream) pipeline as a **pipeline resource** with a `trigger`. When the upstream pipeline finishes successfully, Azure DevOps starts the downstream one automatically.

```text
siva-ci (build, test, publish artifact)  --completes successfully-->  siva-cd (deploy, uses siva-ci's artifact)
```

### Options

| Option | How | When to use |
| --- | --- | --- |
| **Pipeline resource trigger** (YAML) | `resources.pipelines` with `trigger` in the downstream pipeline | Recommended; separate CI and CD pipelines |
| Classic build completion trigger | Downstream pipeline > Edit > **Triggers** > Build completion | Classic (UI) pipelines |
| Call it from the upstream pipeline | `az pipelines run` or REST API in the last step | Need to pass parameters, or trigger conditionally |
| One multi-stage pipeline | Put both as stages with `dependsOn` | Same team and repo; simplest if separation is not needed |

### Option 1: Pipeline resource trigger (recommended)

**Upstream pipeline `siva-ci` (`azure-pipelines-ci.yml`):** builds and publishes an artifact.

```yaml
trigger:
  - main

pool: { vmImage: ubuntu-latest }

steps:
  - script: mvn -B clean package
  - publish: target
    artifact: drop
```

**Downstream pipeline `siva-cd` (`azure-pipelines-cd.yml`):** runs automatically after `siva-ci`.

```yaml
trigger: none                      # no trigger on code commits, only on siva-ci completion

resources:
  pipelines:
    - pipeline: ci                 # alias used inside this YAML
      source: siva-ci              # exact name of the upstream pipeline in Azure DevOps
      # project: OtherProject      # only if the upstream pipeline is in another project
      trigger:
        branches:
          include:
            - main                 # only when siva-ci ran on main
        # stages:                  # optional: trigger after a specific stage finishes
        #   - Build

pool: { vmImage: ubuntu-latest }

steps:
  - download: ci                   # download artifacts from the triggering siva-ci run
    artifact: drop

  - script: |
      echo "Triggered by siva-ci run: $(resources.pipeline.ci.runName)"
      echo "Run ID: $(resources.pipeline.ci.runID)"
      echo "Branch: $(resources.pipeline.ci.sourceBranch)"
      ls $(Pipeline.Workspace)/ci/drop
    displayName: Show upstream run details
```

Key points:
- `source` is the pipeline **name** as shown in Azure DevOps, not the YAML file name.
- The downstream run fires only when the upstream run **completes successfully**. If `siva-ci` fails, `siva-cd` does not start.
- The trigger settings are read from the downstream YAML on its **default branch**, so merge the `resources` block to `main` before testing.
- `download: ci` gets the artifact from the exact run that triggered it, so CD deploys exactly what CI built.

### Option 2: Trigger it from the upstream pipeline (CLI)

Useful when you want to pass parameters or trigger only on some condition.

```yaml
- script: |
    az pipelines run --name siva-cd --branch main \
      --org $(System.CollectionUri) --project "$(System.TeamProject)" \
      --parameters env=dev
  displayName: Start siva-cd
  env:
    AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)
```

The project's build service account needs the **Queue builds** permission on `siva-cd` (Pipelines > siva-cd > Manage security).

### Option 3: Classic UI

Downstream pipeline > **Edit** > **...** > **Triggers** > **Build completion** > **Add** > select `siva-ci` and the branch filter.

### Verify

- Run `siva-ci`. After it succeeds, `siva-cd` starts automatically.
- In the `siva-cd` run summary, the reason shows it was triggered by `siva-ci`.

### Interview answer

> "I use a pipeline completion trigger. In the second pipeline, I add a `resources.pipelines` entry with the first pipeline as `source` and a `trigger` with a branch filter, and I set `trigger: none` so it does not also run on code commits. When the first pipeline completes successfully on main, Azure DevOps automatically starts the second one, and with `download` it uses the artifact from that exact run, so CD deploys exactly what CI built. If I need to pass parameters or trigger conditionally, I call `az pipelines run` from the first pipeline using the System.AccessToken. For classic pipelines, I use the build completion trigger in the Triggers tab. If both belong to the same team, a single multi-stage pipeline with `dependsOn` is often simpler."

</details>
