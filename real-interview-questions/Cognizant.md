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

<details><summary>Q9. In how many different ways can a pipeline run in GitHub Actions?</summary>

### Interview-style answer

In GitHub Actions, a workflow can start in many ways, depending on the triggers we set with the `on` keyword. The main ones are push, pull request, schedule, manual run, release, and triggers from other workflows or external systems.

### 1. Common ways to trigger a pipeline

| Trigger | When does it run? | Real-time example |
| --- | --- | --- |
| `push` | Code is pushed to a branch or tag | Build the application after a developer pushes code |
| `pull_request` | A pull request is opened, updated, or reopened | Run tests before merging |
| `schedule` | At set times, using cron (UTC) | Daily security scan |
| `workflow_dispatch` | Manually from the Actions UI, CLI, or API | Production deployment when approved |
| `release` | A release is published or created | Build and publish release artifacts |
| `workflow_run` | Another workflow finishes | Deploy after the CI workflow succeeds |
| `workflow_call` | Another workflow calls this reusable workflow | Reuse a standard build workflow across repositories |
| `repository_dispatch` | An external system sends an event through the API | Trigger a pipeline from another tool |
| `issue_comment` | A comment is added to an issue or pull request | Run a controlled test from a `/deploy` comment |

These are the common ones. GitHub Actions supports many more events.

### 2. Examples of the most common triggers

**A. Automatically on code push**

```yaml
on:
  push:
    branches:
      - main
```

**B. On a pull request**

```yaml
on:
  pull_request:
    branches:
      - main
```

This runs when a pull request targets `main`.

**C. On a schedule**

```yaml
on:
  schedule:
    - cron: '0 2 * * *'
```

This runs daily at 02:00 UTC.

**D. Manually**

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: Target environment
        type: choice
        options: [dev, qa, prod]
```

This adds the **Run workflow** button, with an optional input. You can also start it from the CLI: `gh workflow run deploy.yml -f environment=qa`.

**E. After another workflow finishes**

```yaml
on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types:
      - completed

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying"
```

`completed` also fires when CI fails, so check the `conclusion` before deploying.

**F. Several triggers together**

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### 3. Real-time DevOps example

For a Java application deployed to AKS:

- **Push to `main`:** build, test, scan, and publish the Docker image.
- **Pull request:** validate code and run tests.
- **Manual trigger:** deploy to production after approval.
- **Schedule:** regular dependency and security scans.
- **After CI completes:** start the deployment workflow only if CI succeeded.

**Gotcha:** events created by the default `GITHUB_TOKEN` (for example, a push made by a workflow) do **not** start new workflows, except `workflow_dispatch` and `repository_dispatch`. This prevents endless loops.

### Interview answer to remember

> "In GitHub Actions, workflows are triggered with the `on` keyword. The most common triggers are `push`, `pull_request`, `schedule`, and `workflow_dispatch`. Workflows can also run on releases, after another workflow completes, when called as a reusable workflow, or from external events through `repository_dispatch`. I use `push` for automatic builds, `pull_request` for validation before merging, and `workflow_dispatch` for controlled production deployments."

**Remember:** `on` defines **when** a workflow starts. Jobs and steps define **what** happens after it starts.

</details>

<details><summary>Q10. What resources have you used in Azure DevOps?</summary>

### Interview-style answer

> "In my project, I used Azure DevOps to manage source code, automate CI/CD pipelines, store packages, manage configuration, and track work. The main services I worked with are Azure Repos, Azure Pipelines, Azure Artifacts, and Azure Boards. Inside pipelines I also used service connections, agent pools, variable groups, environments, and templates."

### 1. Main Azure DevOps services

| Service | Purpose | Real-time example |
| --- | --- | --- |
| Azure Repos | Git repositories for source code | Developers push Java and React code; branch policies protect `main` |
| Azure Pipelines | Build, test, and deploy automation | Build Docker images and deploy to AKS |
| Azure Artifacts | Package feeds (Maven, npm, NuGet, Python) | Store internal Maven libraries and cache public packages via upstream sources |
| Azure Boards | Work items, sprints, and bugs | Track sprint tasks and production issues |
| Azure Test Plans | Manual and exploratory testing | QA team validates application features |

### 2. Other important Azure DevOps components

| Component | Purpose |
| --- | --- |
| Agent pools | Microsoft-hosted or self-hosted machines that run jobs |
| Service connections | Let pipelines authenticate to Azure, ACR, Kubernetes, SonarQube, and other services |
| Variable groups | Share configuration variables (and Key Vault secrets) across pipelines |
| Secure files | Store files such as certificates or signing keys securely |
| Library | Central place for variable groups and secure files |
| Environments | Deployment targets (for example `dev`, `prod`) with deployment history |
| Approvals and checks | Manual approval, branch control, business hours, and other gates before deploying |
| Pipeline templates | Reusable YAML steps, jobs, and stages |
| Branch policies | Require PR reviews, build validation, and linked work items before merging |
| Wiki and dashboards | Project documentation and team status views |

### 3. Real-time DevOps project example

A React frontend and Java Spring Boot backend deployed to AKS:

```text
Azure Repos (code + branch policies)
  -> Azure Pipelines: build, test, SonarQube scan
  -> Docker image pushed to Azure Container Registry
  -> Service connection + variable groups + Key Vault secrets
  -> Azure Pipelines deploys to AKS (dev -> qa -> prod environments)
```

Azure Boards tracks the related tasks and bugs, while environments with approvals and checks control production deployments.

### Interview answer to remember

> "In Azure DevOps, I mainly use Azure Repos for source control with branch policies, and Azure Pipelines for CI/CD. I also work with agent pools, service connections, variable groups, templates, environments, and approvals. For example, I configured a pipeline that builds a Java application, pushes a Docker image to ACR, and deploys it to AKS. Secrets come from Azure Key Vault through a variable group, and production deployments need approval on the environment."

**Interview tip:** if the interviewer asks which resources **you** used, talk only about the components you actually configured, and be ready with one real example for each.

</details>

<details><summary>Q11. How do you automate version upgrades in AKS?</summary>

### Interview-style answer

I automate AKS Kubernetes upgrades with Azure CLI inside Azure DevOps pipelines, and I also use AKS's built-in auto-upgrade with planned maintenance windows. Before upgrading, I check the current version, the available upgrades, deprecated APIs, and application compatibility.

An AKS upgrade has two parts:

- **Control plane upgrade:** upgrades the Kubernetes API server and other managed components.
- **Node pool upgrade:** upgrades the worker nodes where application Pods run.

For production, I use a controlled pipeline with validation, approval, upgrade, and post-upgrade health checks, not a blind automatic upgrade.

### Automation flow

```text
Scheduled or manual Azure DevOps pipeline
  -> Check available AKS versions and deprecated APIs
  -> Validate workloads, PDBs, and node pool surge settings
  -> Production approval
  -> Upgrade control plane, then node pools
  -> Validate nodes, Pods, Services, and application health
```

### 1. Check the current and available versions

```bash
# Current version
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

Choose a supported target version. AKS upgrades one **minor** version at a time (for example 1.29 to 1.30, then 1.30 to 1.31). You cannot skip minor versions.

### 2. Configure the upgrade strategy

Set node surge to reduce disruption:

```bash
az aks nodepool update \
  --resource-group my-rg \
  --cluster-name my-aks \
  --name nodepool1 \
  --max-surge 33%
```

`--max-surge` tells AKS how many extra nodes to add during the upgrade (a number like `1` or a percentage). More surge means a faster upgrade but needs more VM quota and subnet IPs.

Before upgrading, check:

- **PodDisruptionBudgets:** too strict a PDB (for example `maxUnavailable: 0`) blocks node drain.
- **Readiness probes** and at least 2 replicas for important apps.
- **Spare capacity:** VM quota and free IPs for surge nodes.
- **Deprecated APIs:** scan with Pluto or kubent (see Q1).

### 3. Upgrade AKS using Azure CLI

```bash
# Upgrade control plane and all node pools
az aks upgrade \
  --resource-group my-rg \
  --name my-aks \
  --kubernetes-version <target-version> \
  --yes

# Or upgrade in phases: control plane first...
az aks upgrade -g my-rg -n my-aks --kubernetes-version <target-version> --control-plane-only --yes

# ...then each node pool
az aks nodepool upgrade -g my-rg --cluster-name my-aks -n nodepool1 --kubernetes-version <target-version> --yes
```

Phased upgrades let you upgrade a system pool or a less critical pool first and check it before the rest.

### 4. Built-in AKS auto-upgrade

AKS can upgrade itself on a schedule:

```bash
# Auto-upgrade channel: none | patch | stable | rapid | node-image
az aks update -g my-rg -n my-aks --auto-upgrade-channel patch

# Node OS security updates
az aks update -g my-rg -n my-aks --node-os-upgrade-channel NodeImage

# Planned maintenance window: Sundays 00:00-04:00
az aks maintenanceconfiguration add \
  -g my-rg --cluster-name my-aks \
  --name aksManagedAutoUpgradeSchedule \
  --schedule-type Weekly --day-of-week Sunday \
  --interval-weeks 1 --start-time 00:00 --duration 4
```

A common pattern: `patch` auto-upgrade for safe patch versions in a maintenance window, and a pipeline with approval for **minor** version upgrades.

### 5. Automate it in Azure DevOps

The pipeline uses an Azure Resource Manager service connection with permission to upgrade the cluster.

```yaml
trigger: none

parameters:
  - name: targetVersion
    type: string

stages:
  - stage: Validate
    jobs:
      - job: CheckAKS
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: AzureCLI@2
            displayName: Check available AKS upgrades
            inputs:
              azureSubscription: 'azure-service-connection'
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                set -euo pipefail
                az aks show -g my-rg -n my-aks --query kubernetesVersion -o tsv
                az aks get-upgrades -g my-rg -n my-aks -o table

                # Fail if the target version is not an allowed upgrade
                az aks get-upgrades -g my-rg -n my-aks \
                  --query "controlPlaneProfile.upgrades[].kubernetesVersion" -o tsv \
                  | grep -qx '${{ parameters.targetVersion }}' \
                  || { echo "Target version not allowed"; exit 1; }

  - stage: Upgrade
    dependsOn: Validate
    jobs:
      - deployment: UpgradeAKS
        environment: 'production-aks'   # approval check configured here
        pool:
          vmImage: ubuntu-latest
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  displayName: Upgrade AKS
                  inputs:
                    azureSubscription: 'azure-service-connection'
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      set -euo pipefail
                      az aks upgrade \
                        --resource-group my-rg \
                        --name my-aks \
                        --kubernetes-version '${{ parameters.targetVersion }}' \
                        --yes
```

Configure an **approval check** on the `production-aks` environment so the upgrade stage waits for sign-off. Upgrade **dev first, then QA, then prod**, with time between them to catch problems.

### 6. Validate after the upgrade

```bash
kubectl get nodes
kubectl get pods -A
kubectl get deployments -A
kubectl get events -A --sort-by=.lastTimestamp
```

Then check application health with readiness checks, service endpoints, monitoring dashboards, and smoke tests.

If validation fails, stop further upgrades and investigate. **You cannot roll back an AKS control plane to an older version**, so the safe recovery plan is testing in lower environments first, backups (for example Velero or Azure Backup for AKS), and, for critical systems, a blue-green cluster upgrade (build a new cluster on the new version and switch traffic).

### Interview answer to remember

> "I automate AKS upgrades with Azure DevOps pipelines and Azure CLI. First I check the current version and available upgrades, scan for deprecated APIs, and check PodDisruptionBudgets and node pool surge capacity. After approval on the production environment, the pipeline upgrades the control plane and node pools, one minor version at a time. Then it validates node and Pod health and runs smoke tests. For patch versions and node OS images, I use AKS auto-upgrade channels with a planned maintenance window. I always go dev, then QA, then prod, because a control plane upgrade cannot be rolled back."

</details>

<details><summary>Q12. What are templates in Azure DevOps?</summary>

### Interview-style answer

In Azure DevOps, YAML **templates** let us reuse common pipeline code across many pipelines instead of copying it.

For example, if we have Dev, QA, UAT, and Production pipelines, we create one common build template and use it in all four. When the build steps change, we update the template once instead of every pipeline.

### 1. Types of templates

| Template type | Purpose | Example |
| --- | --- | --- |
| Step template | Reuses a group of steps | Build and test a Java application |
| Job template | Reuses a complete job | Build plus security scanning |
| Stage template | Reuses a whole stage | Deploy an application to an environment |
| Variable template | Reuses a set of variables | Common application configuration |
| Extends template | Defines the whole pipeline structure that others must follow | Enforce mandatory security scans in every pipeline |

### 2. Example: step template with parameters

**File:** `templates/build.yml`

```yaml
parameters:
  - name: mavenGoals
    type: string
    default: 'clean package'

steps:
  - script: mvn ${{ parameters.mavenGoals }}
    displayName: Build Java application

  - script: echo "Build completed"
    displayName: Verify build
```

**File:** `azure-pipelines.yml`

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - checkout: self

  - template: templates/build.yml
    parameters:
      mavenGoals: 'clean verify'
```

When the pipeline runs, Azure DevOps expands the template and runs its steps. Parameters make one template work for different services.

### 3. Example: variable template

**File:** `templates/dev-variables.yml`

```yaml
variables:
  environmentName: dev
  appName: myapp
```

```yaml
variables:
  - template: templates/dev-variables.yml

steps:
  - script: |
      echo "Environment: $(environmentName)"
      echo "Application: $(appName)"
```

### 4. Example: templates from a shared repository

Teams usually keep templates in a central repository and reference them from every service:

```yaml
resources:
  repositories:
    - repository: templates
      type: git
      name: Platform/pipeline-templates
      ref: refs/tags/v1.2.0   # pin a version

stages:
  - template: stages/build-and-deploy.yml@templates
    parameters:
      serviceName: orders-api
```

Pinning a tag means a template change does not break every pipeline at once.

### 5. How templates help in real projects

With many microservices on AKS, each service would otherwise repeat build, test, SonarQube scan, Docker build, and deploy steps.

```text
Shared Azure DevOps templates
  |-- Service A (Java API)
  |-- Service B (React UI)
  |-- Service C (Worker)
```

Benefits: less duplicate YAML, consistent builds and deployments, easier maintenance, and fewer mistakes. With **extends templates** plus a **required template check** on environments, you can also enforce that every production deployment goes through approved security steps.

### Interview answer to remember

> "In Azure DevOps, templates are reusable YAML files that stop us from duplicating pipeline code. There are step, job, stage, and variable templates, plus extends templates that enforce a standard pipeline structure. In a microservices project, I keep common templates for Maven build, Docker image creation, and Kubernetes deployment in a shared repository, pass parameters such as the service name, and reuse them across all pipelines. If the build process changes, I update the template once."

**Important:** templates are expanded when the pipeline is **compiled**, before it runs. They are different from **variable groups**, which store variables centrally in the Library and can hold secrets.

</details>

<details><summary>Q13. What is the use of <code>.tpl</code> and helper files (<code>_helpers.tpl</code>) in Helm?</summary>

In Helm, `_helpers.tpl` is used to define **reusable named templates** (small functions), which you call from your Kubernetes YAML templates.

### 1. What is `_helpers.tpl`?

`_helpers.tpl` is a file in the chart's `templates/` folder. It usually defines:

- Application name
- Full resource name
- Common labels
- Selector labels
- Service account name

**Main benefit:** define it once and reuse it everywhere, instead of repeating the same code in every YAML file.

### 2. Example Helm chart structure

```text
myapp/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    └── _helpers.tpl
```

**Step 1: Define helpers in `_helpers.tpl`**

```yaml
{{- define "myapp.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "myapp.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end -}}
```

`trunc 63` is used because Kubernetes names and labels have a 63-character limit.

**Step 2: Use them in `deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ include "myapp.fullname" . }}
  template:
    metadata:
      labels:
        app: {{ include "myapp.fullname" . }}
```

`{{ include "myapp.fullname" . }}` calls the helper and inserts its output. If the release is `dev` and the chart is `myapp`, the name becomes `dev-myapp`. `nindent 4` adds a new line and indents the labels correctly.

**Check the output before installing:**

```bash
helm template dev ./myapp
helm lint ./myapp
```

### 3. Files in a chart

| File | Purpose |
| --- | --- |
| `_helpers.tpl` | Reusable named templates (helpers) |
| Other `_*.tpl` files | More reusable template logic, split by topic |
| `deployment.yaml` | The Kubernetes Deployment |
| `service.yaml` | The Kubernetes Service |
| `values.yaml` | Configurable values such as replicas, image, and ports |
| `Chart.yaml` | Chart name, version, and appVersion |

**Important:** the `.tpl` extension itself does not make a helper. The `define` and `include` functions give the reusable behavior. Files starting with `_` are **partials**: Helm does not render them as Kubernetes manifests.

### 4. `include` vs `template`, and the `tpl` function

- **`include`** returns the output as a string, so you can pipe it, for example `| nindent 4`. Prefer it.
- **`template`** inserts the output directly and cannot be piped.
- **`tpl`** is a different thing: a function that renders a **string from `values.yaml` as a template**. Example: `{{ tpl .Values.configTemplate . }}` lets a value contain `{{ .Release.Name }}`.

### 5. Interview-ready answer

> "In Helm, we use `_helpers.tpl` to define reusable named templates for things like the full resource name, common labels, and selector labels. We call them from `deployment.yaml`, `service.yaml`, and other templates with the `include` function. Files starting with an underscore are not rendered as manifests. This removes duplicate code, keeps names and labels consistent across all resources, and makes charts easier to maintain."

</details>

<details><summary>Q14. What is the use of <code>NOTES.txt</code> in Helm?</summary>

In Helm, `NOTES.txt` shows important information and instructions to the user **after a chart is installed or upgraded**. It lives in the chart's `templates/` folder.

### 1. Example Helm chart structure

```text
myapp/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── _helpers.tpl
    └── NOTES.txt
```

### 2. Example `NOTES.txt`

Suppose the application runs in AKS behind a Kubernetes Service.

**`templates/NOTES.txt`**

```text
{{ .Chart.Name }} was deployed as release "{{ .Release.Name }}" in namespace "{{ .Release.Namespace }}".

Check your application pods:
  kubectl get pods -n {{ .Release.Namespace }}

Check your services:
  kubectl get svc -n {{ .Release.Namespace }}

To access the application locally:
  kubectl port-forward svc/{{ include "myapp.fullname" . }} 8080:{{ .Values.service.port }} -n {{ .Release.Namespace }}
{{- if .Values.ingress.enabled }}

Application URL: https://{{ .Values.ingress.host }}
{{- end }}
```

Install the chart:

```bash
helm install myapp ./myapp
```

Helm prints the rendered `NOTES.txt` at the end of the output:

```text
NAME: myapp
STATUS: deployed
REVISION: 1
NOTES:
myapp was deployed as release "myapp" in namespace "default".

Check your application pods:
  kubectl get pods -n default
...
```

Because `NOTES.txt` is a template, it can use values, release information, helpers, and `if` conditions, as in the example above.

To see the notes again later:

```bash
helm status myapp
helm get notes myapp
```

### 3. Difference between `_helpers.tpl` and `NOTES.txt`

| File | Purpose |
| --- | --- |
| `_helpers.tpl` | Defines reusable named templates (helpers) |
| `NOTES.txt` | Shows post-install or post-upgrade instructions to the user |
| `deployment.yaml` | Defines the Kubernetes Deployment |
| `values.yaml` | Stores configurable chart values |

**Important:** `NOTES.txt` is only information. Helm does **not** run the commands written in it, and it does not create any Kubernetes resource. Only the parent chart's `NOTES.txt` is shown; notes from subcharts are not printed.

### Interview-ready answer

> "In Helm, `NOTES.txt` displays post-install or post-upgrade information, such as how to access the application, how to check Pods and Services, or the application URL. It is a template, so it can use values and release details like the namespace and release name. Helm only prints it; the commands in it are not executed. We can view it again with `helm status` or `helm get notes`."

</details>

<details><summary>Q15. If you want to use <code>dev-config.yaml</code>, how will you deploy it using Helm?</summary>

To deploy with `dev-config.yaml`, I pass it with the `-f` (or `--values`) option during install or upgrade.

### 1. Example folder structure

```text
myapp/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    └── service.yaml

dev-config.yaml
```

### 2. Deploy using Helm

```bash
# New deployment
helm install myapp ./myapp -f dev-config.yaml

# Existing deployment
helm upgrade myapp ./myapp -f dev-config.yaml

# One command for both (common in pipelines)
helm upgrade --install myapp ./myapp \
  -f dev-config.yaml \
  --namespace dev --create-namespace \
  --wait --atomic
```

- `myapp`: the Helm release name.
- `./myapp`: the chart folder.
- `-f dev-config.yaml`: the development values.
- `--wait`: waits until the Pods are ready.
- `--atomic`: rolls back automatically if the upgrade fails.

### 3. Example `dev-config.yaml`

```yaml
replicaCount: 2

image:
  repository: myregistry.azurecr.io/myapp
  tag: "v1"

service:
  type: ClusterIP
  port: 80
```

The chart templates must reference these values (for example `{{ .Values.replicaCount }}`) for them to change anything.

### 4. How values are merged

Helm combines values in this order; later ones win:

1. The chart's own `values.yaml` (defaults)
2. Each `-f` file, in the order given
3. `--set` values on the command line

```bash
helm upgrade --install myapp ./myapp \
  -f dev-config.yaml \
  --set image.tag=v2
```

Here, `image.tag` becomes `v2` even though `dev-config.yaml` says `v1`.

### 5. Check before and after deploying

```bash
# Preview the rendered YAML without deploying
helm template myapp ./myapp -f dev-config.yaml

# After deploying
helm list -n dev
helm get values myapp -n dev
kubectl get pods -n dev
kubectl get svc -n dev
```

### Interview-ready answer

> "To deploy with the development configuration, I run `helm install myapp ./myapp -f dev-config.yaml`, or `helm upgrade myapp ./myapp -f dev-config.yaml` if the release already exists. In pipelines I use `helm upgrade --install` with `--wait` and `--atomic`. Values in the `-f` file override the chart's default `values.yaml`, and `--set` overrides both. This lets me keep separate configuration files for Dev, QA, UAT, and Production without changing the chart."

**Note:** `dev-config.yaml` is a **values file**, not something Helm executes. Helm reads its values and uses them to render the chart templates.

</details>

<details><summary>Q16. If you have multiple environments, how do you write the templates so that only one environment is deployed?</summary>

With Dev, QA, UAT, and Prod, I keep **one chart** and **one values file per environment**, and pass only the required environment's file during deployment. The templates stay the same; only the values change. I do not write separate templates for each environment.

### 1. Folder structure

```text
myapp/
├── Chart.yaml
├── values.yaml          # common defaults
├── values-dev.yaml
├── values-qa.yaml
├── values-uat.yaml
├── values-prod.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── hpa.yaml
    └── _helpers.tpl
```

### 2. Configure each environment

**`values-dev.yaml`**

```yaml
environment: dev
replicaCount: 1
image:
  tag: "dev"
autoscaling:
  enabled: false
```

**`values-prod.yaml`**

```yaml
environment: prod
replicaCount: 3
image:
  tag: "v1.0.0"
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
```

### 3. Use the values in the templates

**`templates/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    environment: {{ include "myapp.environment" . | quote }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      app: {{ include "myapp.fullname" . }}
  template:
    metadata:
      labels:
        app: {{ include "myapp.fullname" . }}
    spec:
      containers:
        - name: myapp
          image: "myregistry.azurecr.io/myapp:{{ .Values.image.tag }}"
```

`replicas` is skipped when HPA is enabled, so Helm and HPA do not fight over the replica count.

### 4. Create a resource only in some environments

Use an `if` condition around the whole file. **`templates/hpa.yaml`**:

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "myapp.fullname" . }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "myapp.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
{{- end }}
```

With `values-dev.yaml`, no HPA is created. With `values-prod.yaml`, it is. Prefer **feature flags** like `autoscaling.enabled` over `if eq .Values.environment "prod"`, because flags keep the templates simple and let you turn a feature on in QA without changing the chart.

### 5. Use `_helpers.tpl` for common logic

```yaml
{{- define "myapp.environment" -}}
{{- required "environment is required: pass -f values-<env>.yaml" .Values.environment -}}
{{- end -}}
```

The helper reads the environment from the selected values file. `required` makes the deployment **fail** with a clear message if someone forgets to pass an environment file.

### 6. Deploy only one environment

```bash
# Dev
helm upgrade --install myapp-dev ./myapp \
  -f ./myapp/values-dev.yaml \
  --namespace dev --create-namespace

# QA
helm upgrade --install myapp-qa ./myapp \
  -f ./myapp/values-qa.yaml \
  --namespace qa --create-namespace

# Production
helm upgrade --install myapp-prod ./myapp \
  -f ./myapp/values-prod.yaml \
  --namespace prod --create-namespace
```

Each command deploys only that environment's configuration. Separate release names and namespaces keep the environments isolated. The chart's `values.yaml` still applies as the base, and the environment file overrides it.

In a pipeline, the environment is a parameter, so the same step deploys any environment:

```bash
helm upgrade --install "myapp-${ENV}" ./myapp \
  -f "./myapp/values-${ENV}.yaml" \
  --namespace "${ENV}" --create-namespace --wait --atomic
```

### Interview-ready answer

> "I keep one Helm chart and separate values files for Dev, QA, UAT, and Production. I deploy one environment by passing only its values file with `-f`, using a separate release name and namespace per environment. The templates read values for replicas, image tags, and settings. For resources needed only in some environments, such as an HPA in production, I wrap the template in an `if` on a flag like `autoscaling.enabled`. I use `_helpers.tpl` for shared logic, for example a helper that uses `required` so the deployment fails if no environment is passed."

</details>

<details><summary>Q17. What do you know about Azure Front Door?</summary>

### Interview answer

Azure Front Door is a **global Layer 7 (HTTP/HTTPS) load balancer and CDN** from Microsoft Azure. It improves performance, availability, and security by sending each user request to the best available backend across regions.

In simple words: if your application runs in several Azure regions, Front Door gives users **one global entry point** and sends them to a healthy region close to them.

### 1. How does Azure Front Door work?

Example: the application runs in **East US** and **West Europe**.

```text
Users worldwide
      |
Azure Front Door (Microsoft edge locations)
  global routing · HTTPS · WAF · caching
      |
      |-- East US      -> AKS / App Service
      |-- West Europe  -> AKS / App Service
```

Request flow:

1. The user opens the application through the Front Door URL or a custom domain.
2. Front Door receives the request at the nearest Microsoft edge location.
3. It checks routing rules, origin health, and the routing method.
4. It forwards the request to a suitable healthy origin over Microsoft's network.
5. If a region becomes unhealthy, the health probes detect it and Front Door sends traffic to another healthy region.

### 2. Key features

| Feature | Purpose |
| --- | --- |
| Global load balancing | Routes requests across origins in different regions |
| Routing methods | Latency (closest), priority (active-passive), weighted (for example 90/10), session affinity |
| Health probes | Check origin health and route away from unhealthy origins |
| WAF (Web Application Firewall) | Blocks attacks such as SQL injection and cross-site scripting; rate limiting and geo-filtering |
| TLS termination | Handles HTTPS at the edge, with free managed certificates for custom domains; use HTTPS to the origin too |
| Caching (CDN) | Caches static content close to users to reduce latency and origin load |
| URL-based routing | For example `/api/*` to the API origin and `/images/*` to a storage origin |
| Rules engine | Redirects, header changes, URL rewrites |
| Private Link origins (Premium) | Connects to origins privately, so they need no public endpoint |

**Tiers:** **Standard** (CDN, routing, basic WAF custom rules) and **Premium** (adds managed WAF rule sets, bot protection, and Private Link origins). The older **Front Door (classic)** tier is being retired; new setups should use Standard or Premium.

### 3. Front Door vs Application Gateway vs Load Balancer vs Traffic Manager

| Service | Scope | Layer | Main use |
| --- | --- | --- | --- |
| Azure Front Door | Global | Layer 7 | Global HTTP/S routing, acceleration, caching, WAF, failover |
| Traffic Manager | Global | DNS | DNS-based routing for any protocol; does not proxy traffic |
| Application Gateway | Regional | Layer 7 | Regional HTTP/S routing, TLS termination, WAF, AKS ingress |
| Azure Load Balancer | Regional | Layer 4 | TCP/UDP load balancing |

In an AKS architecture:

- **Front Door:** sends global users to the right regional application.
- **Application Gateway or an ingress controller:** routes HTTP/S traffic inside the region to the AKS Services.
- **Load Balancer:** distributes TCP/UDP traffic to nodes (AKS creates one for `LoadBalancer` Services).

You do not always need all of them; it depends on the requirements.

### 4. Real-time DevOps scenario

**Interviewer:** "Your application runs in East US and West Europe. East US goes down. How do you handle it?"

**Answer:**

1. Deploy the application in both regions.
2. Create a Front Door **origin group** containing both regional endpoints.
3. Configure **health probes** against a real health endpoint, for example `/health`.
4. Set **priority**: East US = 1, West Europe = 2, so West Europe is the backup (or use latency routing for active-active).
5. When East US fails its probes, Front Door sends requests to West Europe automatically.
6. Monitor origin health, error rates, latency, and WAF logs with Azure Monitor and diagnostic logs.

Front Door handles **traffic** failover only. The database, storage, secrets, and other dependencies must also be designed for disaster recovery (for example geo-replication and failover groups). Front Door alone does not make the application recover.

```bash
az afd profile create -g rg-app --profile-name afd-app --sku Premium_AzureFrontDoor
az afd endpoint create -g rg-app --profile-name afd-app --endpoint-name app-endpoint --enabled-state Enabled
az afd origin-group create -g rg-app --profile-name afd-app --origin-group-name og-app \
  --probe-request-type GET --probe-protocol Https --probe-path /health \
  --probe-interval-in-seconds 30 \
  --sample-size 4 --successful-samples-required 3 --additional-latency-in-milliseconds 50
az afd origin create -g rg-app --profile-name afd-app --origin-group-name og-app \
  --origin-name eastus --host-name app-eastus.example.com --origin-host-header app-eastus.example.com \
  --priority 1 --weight 1000 --enabled-state Enabled --http-port 80 --https-port 443
```

### 5. Security tip: lock the origins to Front Door

Users could bypass Front Door (and its WAF) by calling the origin directly. To prevent this:

- Allow only the `AzureFrontDoor.Backend` service tag in the origin's NSG or access restrictions, **and** check the `X-Azure-FDID` header matches your Front Door ID.
- Or, on the Premium tier, use **Private Link** origins so the backend has no public endpoint at all.

### 6. When would you use Azure Front Door?

- Users access the application from many countries.
- The application runs in multiple Azure regions.
- You need global routing and regional failover.
- You want one global HTTPS entry point with WAF protection.
- You want caching to speed up static content.

For a single-region internal application, Front Door is usually not needed; Application Gateway is enough.

### Interview-ready answer

> "Azure Front Door is a global Layer 7 load balancer and CDN in Azure. It receives HTTP and HTTPS traffic at Microsoft's edge locations and routes it to the best healthy backend using health probes and routing methods such as latency, priority, or weighted. It provides global load balancing, caching, TLS termination, WAF protection, and regional failover. In my architecture, I use Front Door as the global entry point for an application deployed in multiple regions, with Application Gateway or an AKS ingress controller handling traffic inside each region. I lock the origins so they accept traffic only from Front Door."

</details>
