# Cognizant - Interview Questions

Real interview questions with simple, easy-to-read answers.

---

<details><summary>Q1. Have you done any automation to check deprecated versions in AKS?</summary>

### Interview-style answer

Yes. I automate the check for deprecated Kubernetes API versions and AKS cluster versions using Azure CLI and scanning tools.

In our project, we run applications on AKS and deploy them with Helm charts and Kubernetes YAML manifests. Before upgrading the cluster or deploying an application, we must make sure the Kubernetes version is supported and that our manifests do not use deprecated APIs.

I automate this in three ways.

### 1. Check the AKS Kubernetes version

Azure CLI shows the current cluster version and the versions you can upgrade to.

```bash
# Current Kubernetes version of the cluster
az aks show \
  --resource-group my-rg \
  --name my-aks \
  --query kubernetesVersion \
  -o tsv

# Available upgrade versions
az aks get-upgrades \
  --resource-group my-rg \
  --name my-aks \
  -o table
```

### 2. Check deprecated APIs in manifests and in the cluster

- **Pluto** scans Kubernetes YAML files and Helm templates for APIs that are deprecated or removed in a target Kubernetes version.
- **kubent (Kube No Trouble)** scans the resources already running in the live cluster.

```bash
# Scan YAML files against the target Kubernetes version
pluto detect-files -d k8s/ --target-versions k8s=v1.30.0

# Render a Helm chart and scan the output
helm template my-app ./charts/my-app | pluto detect - --target-versions k8s=v1.30.0

# Scan the live cluster
kubent
```

For example, if a manifest uses the old `extensions/v1beta1` API for an Ingress, the scan flags it so we replace it with `networking.k8s.io/v1`.

### 3. Integrate it into the CI/CD pipeline

I add this validation step to the Azure DevOps pipeline before deployment. If deprecated APIs are found, the pipeline fails or publishes a report, so the team fixes the manifests before upgrading or deploying.

The flow:

1. Azure DevOps pipeline starts.
2. Check the AKS version and available upgrades.
3. Scan YAML and Helm manifests with Pluto.
4. Publish a report or fail the validation.
5. Deploy only after the validation passes.

```yaml
- task: AzureCLI@2
  displayName: Check AKS version and deprecated APIs
  inputs:
    azureSubscription: sc-azure-dev
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az aks get-upgrades -g my-rg -n my-aks -o table
      helm template my-app ./charts/my-app | pluto detect - --target-versions k8s=v1.30.0
```

Pluto returns a non-zero exit code when it finds deprecated or removed APIs, so the step fails the pipeline automatically.

### Short answer to speak in the interview

> "Yes, I automate deprecated version checks in AKS using Azure CLI and tools like Pluto and kubent. Azure CLI shows the current Kubernetes version and the available upgrades. Pluto finds deprecated APIs in Kubernetes YAML files and Helm charts, and kubent checks what is already running in the cluster. I add these checks to the Azure DevOps pipeline so we catch compatibility issues before upgrading the AKS cluster or deploying the application. This prevents deployment failures during Kubernetes upgrades."

**Important:** Checking the AKS cluster version alone does not find every deprecated API. You also need to scan the manifests and, where needed, the live cluster resources. AKS itself also stops an upgrade if it detects recent use of APIs that are removed in the target version.

</details>

<details><summary>Q2. What is the difference between <code>run</code> and <code>uses</code> in GitHub Actions?</summary>

The main difference:

- `run` executes shell commands directly on the runner.
- `uses` runs a GitHub Action that already exists, either from the Marketplace or from your own repository.

### 1. `run` example

Use `run` to execute Linux commands, scripts, or build commands.

```yaml
steps:
  - name: Check current directory
    run: pwd

  - name: List files
    run: ls -la

  - name: Build Java application
    run: mvn clean package
```

**Real-time example:** in a CI pipeline, I use `run` to compile a Java application with Maven, run shell scripts, or run tests.

### 2. `uses` example

Use `uses` to call an existing GitHub Action.

```yaml
steps:
  - name: Checkout code
    uses: actions/checkout@v4

  - name: Set up Java
    uses: actions/setup-java@v4
    with:
      distribution: temurin
      java-version: '17'
```

**Real-time example:** before building a Java application, I use `actions/checkout` to download the repository code and `actions/setup-java` to install Java on the runner.

### Key differences

| Feature | `run` | `uses` |
| --- | --- | --- |
| Purpose | Executes shell commands | Executes an existing action |
| Examples | `mvn clean package`, `ls`, `pwd` | `actions/checkout@v4` |
| What it contains | Shell commands or scripts | A reference to an action |
| `with` inputs | Not used | Commonly used to pass inputs to the action |
| Typical use | Build, test, script execution | Checkout code, set up tools, upload artifacts |

A single step can have either `run` or `uses`, not both.

### 3. Real-time DevOps pipeline example

```yaml
name: Java CI Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout source code
        uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'

      - name: Build application
        run: mvn clean package
```

Here, `uses` gets the code and prepares the environment, and `run` executes the Maven build.

### Interview answer

> "In GitHub Actions, `run` executes shell commands or scripts directly on the runner, while `uses` calls an existing GitHub Action. For example, I use `actions/checkout` to get the source code and `actions/setup-java` to set up Java. Then I use `run: mvn clean package` to build the application. Both are used together in a typical CI/CD pipeline."

</details>

<details><summary>Q3. If I want my pipeline to run automatically in GitHub Actions, what should I do?</summary>

### Interview-style answer

In GitHub Actions, we use the `on` keyword to trigger a workflow automatically on events such as a code push, a pull request, or a schedule.

For example, to run the pipeline whenever a developer pushes code to the `main` branch, I configure the `push` trigger in the workflow YAML file.

### 1. Run automatically when code is pushed

Create the file `.github/workflows/ci.yml`:

```yaml
name: CI Pipeline

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build application
        run: echo "Building the application"
```

How it works:

1. A developer pushes code to the `main` branch.
2. GitHub detects the `push` event.
3. GitHub Actions starts the workflow automatically.
4. The runner checks out the code and runs the build step.

### 2. Other ways to trigger a pipeline

| Trigger | Purpose | Example |
| --- | --- | --- |
| `push` | Run when code is pushed | Developer pushes code to `main` |
| `pull_request` | Run when a PR is opened or updated | Developer creates a PR |
| `schedule` | Run at a set time | Daily security scan |
| `workflow_dispatch` | Run manually from GitHub | Engineer clicks **Run workflow** |

To run the pipeline daily at midnight UTC:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'
```

You can combine several triggers in one workflow:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### Interview answer to remember

> "To run a GitHub Actions pipeline automatically, I configure triggers with the `on` keyword in the workflow YAML file. I use `push` to trigger the pipeline whenever code is pushed to the `main` branch, and `pull_request` to validate code before merging. I can also use `schedule` for periodic jobs. In my DevOps workflow, the CI pipeline triggers on code changes and runs build, tests, and security scans automatically."

**Important:** the workflow file must be committed under `.github/workflows/` in the repository. Scheduled workflows use UTC, run only from the default branch, and can be delayed when GitHub is under high load.

</details>

<details><summary>Q4. What is the difference between a variable and a variable group in Azure DevOps?</summary>

The main difference: a **variable** stores a single value, while a **variable group** stores many variables together so several pipelines can reuse them.

### 1. Variable

A variable stores one value, such as an environment name, application name, or configuration setting.

```yaml
variables:
  environment: 'dev'
  appName: 'myapp'

steps:
  - script: |
      echo "Environment: $(environment)"
      echo "Application: $(appName)"
```

Here, `environment` and `appName` are defined directly in the pipeline YAML. You can also define variables in the pipeline settings (UI) in Azure DevOps.

### 2. Variable group

A variable group is a set of variables managed centrally in the Azure DevOps **Library**. Many pipelines can use the same group.

How to create one:

1. Go to **Pipelines > Library**.
2. Select **Variable groups**.
3. Click **+ Variable group**.
4. Give it a name, such as `dev-config`.
5. Add variables like `environment`, `appName`, and `apiUrl`.
6. Save the group and authorize the pipelines that need it.

```yaml
variables:
  - group: dev-config

steps:
  - script: |
      echo "Environment: $(environment)"
      echo "Application: $(appName)"
```

Here, the pipeline reads the variables from the `dev-config` group.

### 3. Key differences

| Feature | Variable | Variable group |
| --- | --- | --- |
| Purpose | Stores one value | Stores a collection of variables |
| Location | YAML, pipeline UI, or other supported scopes | Azure DevOps Library |
| Reusability | Limited to where it is defined | Shared across many pipelines |
| Maintenance | Update it where it is defined | Update once, centrally |
| Secrets | Can be marked secret | Can hold secret variables |
| Key Vault integration | No | Can link to Azure Key Vault |
| Access control | Through the pipeline | Own security roles and pipeline permissions |

### 4. Real-time DevOps example

Suppose you have Dev, QA, and Production environments. Create one group per environment:

- `dev-config`: Dev URL and configuration values.
- `qa-config`: QA URL and configuration values.
- `prod-config`: Production URL and configuration values.

Then pick the right group in the pipeline:

```yaml
parameters:
  - name: environment
    type: string
    default: dev
    values:
      - dev
      - qa
      - prod

variables:
  - ${{ if eq(parameters.environment, 'dev') }}:
      - group: dev-config
  - ${{ if eq(parameters.environment, 'qa') }}:
      - group: qa-config
  - ${{ if eq(parameters.environment, 'prod') }}:
      - group: prod-config

steps:
  - script: echo "Deploying to $(environment)"
```

Each group must contain the variables the pipeline uses, and access to production groups should be restricted. When you mix groups and plain variables, use the list syntax (`- name: x` / `value: y`) for the plain variables.

For passwords, tokens, and connection strings, use secret variables or Azure Key Vault integration, and never print secret values in pipeline logs.

### Interview answer

> "In Azure DevOps, a variable stores one configuration value, while a variable group stores many variables in the Library and lets us reuse them across pipelines. For example, I define an application name directly in YAML, but for Dev, QA, and Production configuration I keep separate variable groups. When a value changes, I update the group once instead of editing many pipeline files. For sensitive information, I use secret variables or link the variable group to Azure Key Vault."

</details>

<details><summary>Q5. What is the difference between Microsoft-hosted and self-hosted agents? How do you set up a self-hosted agent?</summary>

### 1. Difference between Microsoft-hosted and self-hosted agents

In Azure DevOps, an **agent** is a machine that runs pipeline jobs, such as building applications, running tests, creating Docker images, and deploying to AKS.

| Feature | Microsoft-hosted agent | Self-hosted agent |
| --- | --- | --- |
| Infrastructure | Managed by Microsoft | Managed by our team |
| Setup | No installation | We install and configure the agent |
| Machine lifecycle | Fresh VM for every job | Machine is reused between jobs |
| Software | Standard preinstalled tools | We install the tools we need |
| Network access | Public internet; cannot reach private resources without extra setup | Can run inside our private network |
| Caching | No cache between runs | Docker layers and packages stay, so builds can be faster |
| Maintenance | Microsoft patches the VM | We patch and secure it |
| Cost | Paid per parallel job (a free tier exists) | VM cost plus maintenance effort |
| Best use case | Standard build and test pipelines | Private deployments and custom environments |

**Real-time example:** our application runs on a **private AKS cluster**.

- **Microsoft-hosted agent:** can build the application, but cannot reach the private AKS API endpoint.
- **Self-hosted agent:** we install the agent on an Azure VM inside the AKS VNet or a peered network. After configuring DNS, routing, permissions, and firewall rules, it can deploy to the private cluster.

**Managed DevOps Pools** are a middle option: Microsoft manages the agents, but they can run inside your own VNet.

### 2. Steps to set up a self-hosted agent (Ubuntu VM in Azure)

#### Step 1: Create a VM

1. In the Azure portal, go to **Virtual machines > Create**.
2. Select **Ubuntu Linux**.
3. Configure the VM size, networking, and SSH access.
4. Make sure the VM has outbound HTTPS (port 443) access to Azure DevOps. No inbound port is needed: the agent connects out to Azure DevOps.
5. Connect to the VM over SSH.

You can also use an existing Linux VM.

#### Step 2: Create an agent pool

1. In Azure DevOps, open **Organization settings > Agent pools**.
2. Click **Add pool**.
3. Select **Self-hosted**.
4. Name it `Linux-SelfHosted-Pool`.

The pool groups the agents that will run your pipeline jobs.

#### Step 3: Install prerequisites

```bash
sudo apt update
sudo apt install -y curl git tar gzip
```

Also install whatever your builds need, such as Docker, Java, Node.js, Azure CLI, kubectl, or Helm.

#### Step 4: Download the agent

1. Go to **Organization settings > Agent pools > Linux-SelfHosted-Pool > Agents > New agent**.
2. Select **Linux** and copy the download link for your architecture.
3. Download and extract it:

```bash
mkdir -p ~/myagent && cd ~/myagent
curl -LO <download-url-copied-from-azure-devops>
tar -xzf vsts-agent-linux-x64-*.tar.gz
```

Use the actual file name if it differs.

#### Step 5: Configure the agent

```bash
./config.sh
```

Enter the requested details:

- **Server URL:** `https://dev.azure.com/YOUR_ORGANIZATION`
- **Authentication:** a supported method, such as a PAT.
- **Agent pool:** `Linux-SelfHosted-Pool`
- **Agent name:** `ubuntu-agent-01`
- **Work folder:** accept the default `_work`, or choose another folder.

If you use a PAT, give it only the **Agent Pools (Read & manage)** scope and handle it securely. It is only needed during configuration. Never commit it to Git or print it in logs.

#### Step 6: Install the agent as a service

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

The agent now runs in the background and picks up jobs even after you disconnect from SSH, and it starts again after a reboot.

#### Step 7: Verify the agent

Go to **Organization settings > Agent pools > Linux-SelfHosted-Pool > Agents**. You should see `ubuntu-agent-01` with the status **Online**.

#### Step 8: Use the agent in a pipeline

```yaml
trigger:
  - main

pool:
  name: Linux-SelfHosted-Pool

steps:
  - script: |
      echo "Running on self-hosted agent"
      hostname
      uname -a
    displayName: Verify agent
```

When a developer pushes code to `main`, Azure DevOps runs the job on your self-hosted agent.

### 3. Real-time project example

Project with Azure DevOps, Docker, ACR, and a private AKS cluster:

1. A developer pushes code to Azure Repos.
2. Azure DevOps triggers the pipeline.
3. The self-hosted agent builds the application.
4. It builds a Docker image and pushes it to ACR.
5. It connects to the private AKS API and deploys the application.

For this to work, the VM needs the right tools, network access, and permissions. Running the agent inside the same VNet helps with networking, but it does **not** give access to AKS by itself; the deployment identity still needs RBAC on the cluster.

### 4. Interview answer to remember

> "I use Microsoft-hosted agents for standard build and test jobs because Microsoft manages the machines. For self-hosted agents, we manage the VM, install the tools, and configure the agent pool ourselves. To set one up, I create a Linux VM, create an agent pool in Azure DevOps, download the agent, run `config.sh`, and install it as a service with `svc.sh`. Then I reference that pool in the pipeline YAML. For example, to deploy to a private AKS cluster, a self-hosted agent inside the connected private network can do the deployment with the right permissions."

**Security point:** treat self-hosted agents as sensitive infrastructure. Patch the VM, restrict which pipelines can use the pool, use least-privilege deployment identities, clean the work folder between runs, and never run untrusted pull-request code on an agent that has production access.

</details>

<details><summary>Q6. Where do you store your secrets, and how do you integrate them with the pipeline?</summary>

### 1. Where do you store secrets?

> "I store sensitive information such as passwords, access tokens, database credentials, and connection strings in **Azure Key Vault**. I integrate Key Vault with Azure DevOps pipelines, so the pipeline reads secrets securely at deployment time without hardcoding them in YAML or storing them in Git."

Azure DevOps also supports **secret variables** and **variable groups** in the Library. For production, I prefer Azure Key Vault because it gives central secret management, access control, auditing, and secret rotation.

### 2. How do you integrate Azure Key Vault with Azure DevOps?

The flow:

```text
Azure DevOps pipeline
  -> Azure Resource Manager service connection
  -> Microsoft Entra ID authentication + Key Vault permissions (RBAC)
  -> Azure Key Vault returns the allowed secrets to the pipeline
```

#### Step 1: Create secrets in Azure Key Vault

1. Create or open an Azure Key Vault.
2. Go to **Objects > Secrets**.
3. Create secrets such as `db-password`, `api-token`, and `connection-string`.

Never put real secret values in pipeline YAML.

#### Step 2: Create a service connection

1. In Azure DevOps, go to **Project settings > Service connections**.
2. Select **New service connection > Azure Resource Manager**.
3. Choose **Workload identity federation** for authentication, so there is no stored password.
4. Select the subscription and save.

#### Step 3: Grant Key Vault permissions

Give the service connection's identity permission to **read** secrets. With the Azure RBAC permission model, assign the **Key Vault Secrets User** role on the vault. Also make sure the vault's firewall allows the pipeline agent to reach it (for a private vault, use a self-hosted agent inside the network).

```bash
az role assignment create \
  --assignee <service-connection-app-id> \
  --role "Key Vault Secrets User" \
  --scope $(az keyvault show -n kv-prod --query id -o tsv)
```

#### Step 4: Link Key Vault to a variable group

1. Go to **Pipelines > Library > Variable groups**.
2. Create a group, for example `prod-secrets`.
3. Turn on **Link secrets from an Azure key vault as variables**.
4. Select the service connection and the Key Vault.
5. Add the secrets you need and save.
6. Authorize only the pipelines that need access.

The variable group stores **references** to the secrets, not their values. Azure DevOps fetches the latest values from Key Vault every time the pipeline runs.

#### Step 5: Use the variable group in YAML

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

variables:
  - group: prod-secrets

steps:
  - script: ./deploy.sh
    displayName: Deploy application
    env:
      DB_PASSWORD: $(db-password)
      API_TOKEN: $(api-token)
```

`db-password` and `api-token` are the secret names in the variable group. Secret variables are **not** passed to scripts automatically, so you map them explicitly with `env`. Azure DevOps masks them as `***` in logs.

Do not `echo` secrets or pass them as command-line arguments, where they can appear in process lists or logs.

**Alternative:** instead of a linked variable group, use the `AzureKeyVault@2` task to fetch secrets inside one job:

```yaml
- task: AzureKeyVault@2
  inputs:
    azureSubscription: sc-azure-prod
    KeyVaultName: kv-prod
    SecretsFilter: 'db-password,api-token'
    RunAsPreJob: false
```

### 3. What happens if a secret changes in Key Vault?

Suppose the database password changes:

- Key Vault holds the new value.
- A linked variable group reads secrets at pipeline run time, so the **next** run gets the new value.
- A pipeline or application that is **already running** does not refresh a value it has already loaded.
- If an application needs the new password, restart or refresh the workload, or use a refresh mechanism such as Key Vault references in App Service or the Secrets Store CSI driver with rotation in AKS.

### 4. Interview answer to remember

> "I store sensitive information such as database passwords, API tokens, and connection strings in Azure Key Vault. I create an Azure Resource Manager service connection with workload identity federation, give its identity the Key Vault Secrets User role, and link the vault to a variable group in the Azure DevOps Library. Then I reference that variable group in the pipeline YAML and map the secrets to environment variables for the scripts that need them. This keeps secrets out of the repository, gives central access control and rotation, and I make sure secrets are never printed in pipeline logs."

**Key distinction:** the **service connection** lets the pipeline log in to Azure, **Key Vault** stores the secrets, and the **variable group** makes selected Key Vault secrets available to the pipeline.

</details>

<details><summary>Q7. What is Ingress, and what is the main configuration in an Ingress?</summary>

### 1. What is Ingress in Kubernetes?

Ingress is a Kubernetes resource that manages **external HTTP and HTTPS access** to applications running inside the cluster.

For example, suppose we run two applications in AKS:

- **Frontend:** React application
- **Backend:** Java Spring Boot application

Instead of exposing each one separately with its own public IP, we use one Ingress to route requests to the right Kubernetes Service based on the **hostname** or **URL path**.

```text
User / Browser
      |
Ingress Controller (NGINX, or Application Gateway)
      |
      |-- /      -> frontend-service -> React Pods
      |-- /api   -> backend-service  -> Java Pods
```

**Important:** Ingress is only the routing configuration. An **Ingress Controller** reads those rules and actually handles the traffic. Creating an Ingress resource without a controller does nothing.

### 2. What are the main configurations in Ingress?

| Configuration | Purpose | Example |
| --- | --- | --- |
| `ingressClassName` | Selects which Ingress Controller handles this Ingress | `nginx` |
| `rules` | Host- and path-based routing rules | `/api` to the backend |
| `host` | The domain name to match | `app.example.com` |
| `paths` | URL paths and how to match them (`pathType`) | `/api`, `/` |
| `backend` | Target Service and port | `backend-service:8080` |
| `tls` | Enables HTTPS using a TLS Secret | `app-tls-secret` |
| Annotations | Controller-specific behavior | HTTP-to-HTTPS redirect, timeouts, body size, rewrites |

### 3. Example Ingress YAML

This routes `/` to the frontend Service and `/api` to the backend Service.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
spec:
  ingressClassName: nginx

  tls:
    - hosts:
        - app.example.com
      secretName: app-tls-secret

  rules:
    - host: app.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 8080

          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

How it works:

- **apiVersion:** `networking.k8s.io/v1` is the current Ingress API (the old `extensions/v1beta1` is removed).
- **ingressClassName:** selects the Ingress Controller.
- **host:** matches requests for `app.example.com`.
- **path:** `/api` goes to the backend, `/` goes to the frontend. When several paths match, the longest one wins, so `/api/orders` goes to the backend.
- **pathType:** `Prefix` matches the path and everything under it; `Exact` matches only that exact path.
- **backend:** the Kubernetes Service name and port.
- **tls:** enables HTTPS using the certificate stored in `app-tls-secret`.

The Services and the TLS Secret must be in the **same namespace** as the Ingress, and a working controller must be installed.

```bash
kubectl get ingress -A
kubectl describe ingress app-ingress
kubectl get ingressclass
```

### 4. What is the difference between Ingress and Ingress Controller?

- **Ingress:** the rules that say where traffic should go.
- **Ingress Controller:** the component (a reverse proxy running in the cluster) that reads those rules and routes the traffic.

For example, I write an Ingress YAML to route `/api` to my Java backend. The NGINX Ingress Controller reads that configuration and does the routing.

Common controllers in AKS:

- **Application routing add-on:** a managed NGINX controller from AKS.
- **Application Gateway Ingress Controller (AGIC)** or **Application Gateway for Containers:** uses Azure Application Gateway, with WAF support.
- **Self-installed NGINX or Traefik** via Helm.

Note: **Gateway API** is the newer Kubernetes standard that is replacing Ingress over time, and the community `ingress-nginx` project has been retired. For new AKS setups, prefer a managed option such as the application routing add-on or Application Gateway for Containers.

### 5. Interview answer to remember

> "Ingress exposes applications running inside Kubernetes over HTTP or HTTPS through a single entry point. Its main configurations are the hostname, path-based routing rules, backend Service and port, Ingress class, TLS settings, and controller-specific annotations. For example, in my AKS project I route `/` to the React frontend and `/api` to the Java Spring Boot backend. The Ingress Controller processes these rules and forwards requests to the matching Services."

</details>

<details><summary>Q8. How do you autoscale in AKS? What commands do you use?</summary>

### Interview-style answer

In AKS, I use two main types of autoscaling:

- **Horizontal Pod Autoscaler (HPA):** increases or decreases the number of **Pods** based on CPU, memory, or custom metrics.
- **Cluster Autoscaler:** increases or decreases the number of **worker nodes** based on Pods that cannot be scheduled and on unused capacity.

When traffic increases, HPA adds Pods. If the nodes do not have enough capacity for those Pods, Cluster Autoscaler adds more nodes.

Other options:

- **Vertical Pod Autoscaler (VPA):** recommends or adjusts a Pod's CPU and memory requests.
- **KEDA (AKS add-on):** scales Pods on events, such as Service Bus queue length or Kafka lag, and can scale to zero.

### Autoscaling flow

```text
Application traffic increases
  -> HPA increases Pod replicas
  -> New Pods stay Pending if nodes lack capacity
  -> Cluster Autoscaler adds worker nodes
  -> Pending Pods are scheduled on the new nodes
```

### 1. Configure HPA to autoscale Pods

The Deployment must have **CPU requests**, because HPA calculates utilization as a percentage of the request. AKS installs Metrics Server by default.

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

Create an HPA for the `myapp` Deployment:

```bash
kubectl autoscale deployment myapp \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

This keeps between 2 and 10 replicas and targets an average CPU usage of 70% of the requested CPU.

The same HPA in YAML (better for GitOps and Helm):

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

Check the autoscaler:

```bash
kubectl get hpa
kubectl describe hpa myapp
kubectl top pods
kubectl get pods -w
```

If `TARGETS` shows `<unknown>`, check that Metrics Server is running (`kubectl get pods -n kube-system | grep metrics-server`) and that the Pods have CPU requests.

### 2. Configure Cluster Autoscaler to scale nodes

For an existing node pool:

```bash
az aks nodepool update \
  --resource-group my-rg \
  --cluster-name my-aks \
  --name nodepool1 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 5
```

The node pool can now scale between 2 and 5 nodes.

Change the limits later:

```bash
az aks nodepool update \
  --resource-group my-rg \
  --cluster-name my-aks \
  --name nodepool1 \
  --update-cluster-autoscaler \
  --min-count 2 \
  --max-count 8
```

Check the nodes and node pool settings:

```bash
kubectl get nodes

az aks nodepool show \
  --resource-group my-rg \
  --cluster-name my-aks \
  --name nodepool1 \
  --query "{count:count, autoscaling:enableAutoScaling, min:minCount, max:maxCount}" \
  -o table
```

You can also enable it when creating the cluster with `az aks create ... --enable-cluster-autoscaler --min-count 2 --max-count 5`.

### 3. How do you troubleshoot autoscaling?

```bash
kubectl get hpa
kubectl describe hpa myapp
kubectl get pods
kubectl describe pod <pending-pod>
kubectl get nodes
kubectl get events --sort-by=.lastTimestamp
```

Common problems:

- **HPA shows `<unknown>`:** no CPU requests, or Metrics Server is not working.
- **Pods stay Pending, no new nodes:** the node pool has reached `max-count`, the subscription vCPU quota is used up, the subnet has no free IPs, or the Pod's node selector or taints do not match the pool.
- **Nodes do not scale down:** Pods without a controller, Pods with local storage, or a strict PodDisruptionBudget block node removal.

### Interview answer to remember

> "In AKS, I use HPA to scale application Pods based on CPU or memory, and Cluster Autoscaler to scale worker nodes when Pods cannot be scheduled. For example, I configure HPA to keep 2 to 10 replicas at 70% CPU, and Cluster Autoscaler to scale the node pool between 2 and 5 nodes. I check the behavior with `kubectl get hpa`, `kubectl get pods`, and `kubectl get nodes`. For event-driven workloads, I use the KEDA add-on."

**Key point:** HPA scales **Pods**. Cluster Autoscaler scales **nodes**. They work together but solve different problems.

</details>
