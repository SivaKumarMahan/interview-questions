# My Projects: Hands-On Azure DevOps Practice Projects

> Fifteen hands-on practice projects, from a simple Docker container to a full microservices platform on AKS, explained in simple words with goals, steps, and what each one teaches. Also includes short notes on Storage snapshots, Azure Policy, vulnerability scanning tools, and PodDisruptionBudgets.

## Key Concepts

These are **practice and lab projects** from my own learning plan, not resume projects. In an interview, call them "hands-on labs I built to practise X" and only describe the ones you actually built. Each project below has a short summary here and a full step-by-step guide (code, commands, troubleshooting, clean-up, and interview questions) in the [practice-projects](practice-projects/) folder. Mark your progress in the table and keep a GitHub link for each one you finish.

### Project list at a glance

| # | Project | Main tools | Level | Detailed guide | Built? |
| --- | --- | --- | --- | --- | --- |
| 1 | Dockerized Node.js app to an Azure VM | GitHub Actions, Docker Hub, Azure VM | Beginner | [Guide](practice-projects/01-nodejs-docker-azure-vm-github-actions.md) | `[Confirm]` |
| 2 | Web app and infrastructure with Azure DevOps | Azure Repos, YAML pipelines, Bicep | Intermediate | [Guide](practice-projects/02-azure-devops-bicep-web-app-and-infra.md) | `[Confirm]` |
| 3 | 3-tier architecture with Terraform | Terraform, Azure CLI, remote state | Intermediate | [Guide](practice-projects/03-terraform-3-tier-architecture.md) | `[Confirm]` |
| 3.1 | Modular Terraform with remote state | Terraform modules, Azure Storage backend | Intermediate | [Guide](practice-projects/03-1-terraform-modules-remote-state.md) | `[Confirm]` |
| 3.2 | Terraform CI/CD | GitHub Actions or Azure DevOps | Intermediate | [Guide](practice-projects/03-2-terraform-cicd-pipelines.md) | `[Confirm]` |
| 4 | Jenkins CI/CD to AKS | Jenkins, Docker, ACR, AKS | Intermediate | [Guide](practice-projects/04-jenkins-docker-aks-cicd.md) | `[Confirm]` |
| 5 | Container to Azure Web App for Containers | App Service, GitHub Actions | Beginner | [Guide](practice-projects/05-container-azure-web-app-for-containers.md) | `[Confirm]` |
| 6 | Microservices with Helm on AKS | Helm, AKS, Ingress, GitHub Actions | Advanced | [Guide](practice-projects/06-helm-microservices-aks.md) | `[Confirm]` |
| 7 | Azure VM configuration with Ansible | Ansible, `azure.azcollection` | Intermediate | [Guide](practice-projects/07-ansible-azure-vm-automation.md) | `[Confirm]` |
| 8 | Key Vault with managed identity | Key Vault, managed identity, Azure SDK | Intermediate | [Guide](practice-projects/08-key-vault-managed-identity.md) | `[Confirm]` |
| 9 | Containerize a Flask app | Docker, Docker Hub, Docker Compose | Beginner | [Guide](practice-projects/09-flask-app-docker.md) | `[Confirm]` |
| 10 | Flask app on Azure Container Instances | ACI, GitHub Actions | Beginner | [Guide](practice-projects/10-flask-app-azure-container-instances.md) | `[Confirm]` |
| 11 | Flask app on AKS provisioned by Terraform | Terraform, AKS, ACR, kubectl | Intermediate | [Guide](practice-projects/11-flask-app-aks-terraform.md) | `[Confirm]` |
| 12 | Azure Function App with GitHub Actions | Azure Functions, GitHub Actions | Beginner | [Guide](practice-projects/12-azure-function-app-github-actions.md) | `[Confirm]` |
| 13 | Logic App + Function event-driven flow | Logic Apps, Functions, Blob, Cosmos DB | Intermediate | [Guide](practice-projects/13-logic-app-function-event-driven.md) | `[Confirm]` |
| 14 | AKS observability | Azure Monitor, Log Analytics, KQL | Intermediate | [Guide](practice-projects/14-aks-observability-azure-monitor.md) | `[Confirm]` |
| 15 | Full microservices CI/CD platform | Terraform, Helm, GitHub Actions, AKS | Advanced | [Guide](practice-projects/15-full-microservices-platform-aks.md) | `[Confirm]` |

### Project 1: Dockerized Node.js app to an Azure VM with GitHub Actions

**Full step-by-step guide:** [practice-projects/01-nodejs-docker-azure-vm-github-actions.md](practice-projects/01-nodejs-docker-azure-vm-github-actions.md)

**Goal:** every push builds a Docker image, pushes it to Docker Hub, and runs the new version on an Azure VM.

**Flow:**

```text
git push -> GitHub Actions: docker build -> docker push (Docker Hub)
         -> SSH to Azure VM -> docker pull -> docker stop old -> docker run new
```

**Steps:**

1. Write a small Node.js app and a `Dockerfile`.
2. Create an Ubuntu VM in Azure and install Docker. Open port 80 in the NSG.
3. Store `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, the VM IP, and an SSH private key as GitHub secrets.
4. In the workflow: `docker/login-action`, `docker/build-push-action`, then an SSH step that pulls and restarts the container.

**What it teaches:** CI/CD basics, image tagging (use the commit SHA, not only `latest`), secrets in GitHub, and simple deployment over SSH.

### Project 2: Azure DevOps with Repos, YAML pipelines, variable groups, and Bicep

**Full step-by-step guide:** [practice-projects/02-azure-devops-bicep-web-app-and-infra.md](practice-projects/02-azure-devops-bicep-web-app-and-infra.md)

**Goal:** deploy a web app **and** its infrastructure (VNet, Storage account, AKS) from Azure DevOps.

**Steps:**

1. Push code and Bicep files to **Azure Repos**.
2. Create an **Azure Resource Manager service connection** (workload identity federation).
3. Create **variable groups** per environment (`dev-config`, `prod-config`), linked to Key Vault for secrets.
4. Write a multi-stage YAML pipeline: **Build** > **Deploy infra** (`az deployment group create` with Bicep) > **Deploy app**.
5. Add an approval check on the production environment.

**What it teaches:** Azure DevOps end to end, Bicep, service connections, variable groups, environments, and approvals.

### Project 3: 3-tier architecture with Terraform

**Full step-by-step guide:** [practice-projects/03-terraform-3-tier-architecture.md](practice-projects/03-terraform-3-tier-architecture.md)

**Goal:** provision web, app, and database tiers with Terraform.

**What to build:**

- `main.tf`, `variables.tf`, `outputs.tf`, using the `azurerm` provider.
- **Remote state** in an Azure Storage account (`backend "azurerm"`), with state locking through blob leases.
- A **public subnet** for the web tier behind an **Azure Load Balancer** and a **VM Scale Set**.
- A **private subnet** for the database, with NSGs allowing only the app tier.
- Outputs: the load balancer public IP and URL.

```bash
terraform init
terraform plan -out tfplan
terraform apply tfplan
```

**Project 3.1** ([guide](practice-projects/03-1-terraform-modules-remote-state.md)): split the code into **modules** (`modules/network`, `modules/vm`) and call them from each environment.

**Project 3.2** ([guide](practice-projects/03-2-terraform-cicd-pipelines.md)): run Terraform from a pipeline: `fmt` and `validate` > `plan` on pull requests (post the plan as a comment) > `apply` on merge to `main`, after approval.

**What it teaches:** IaC, state management, modules, and safe Terraform workflows.

### Project 4: Jenkins CI/CD to AKS

**Full step-by-step guide:** [practice-projects/04-jenkins-docker-aks-cicd.md](practice-projects/04-jenkins-docker-aks-cicd.md)

**Goal:** a Jenkins pipeline that builds, tests, pushes to ACR, and deploys to AKS.

**Steps:**

1. Run Jenkins with an **agent on an Azure VM** that has Docker, Azure CLI, and kubectl.
2. Write a `Jenkinsfile` with stages: **Build** > **Test** > **Push** (`docker push` to ACR) > **Deploy** (`kubectl apply -f deployment.yaml -f service.yaml`).
3. Use a `LoadBalancer` Service so the app gets a public IP.
4. Store Azure and ACR credentials in **Jenkins credentials**, never in the Jenkinsfile.

**What it teaches:** declarative Jenkins pipelines, agents, ACR, and basic Kubernetes deployments.

### Project 5: Container to Azure Web App for Containers

**Full step-by-step guide:** [practice-projects/05-container-azure-web-app-for-containers.md](practice-projects/05-container-azure-web-app-for-containers.md)

**Goal:** run a container on App Service (PaaS) without managing servers or clusters.

**Steps:**

1. Create an **App Service Plan** (Linux) and a **Web App for Containers**.
2. GitHub Actions builds and pushes the image, then updates the Web App (`az webapp config container set`, or the `azure/webapps-deploy` action).
3. Configure **app settings** (environment variables), **scale out** rules, and **log streaming**.
4. Let the Web App pull from ACR using its **managed identity** (AcrPull role).

**What it teaches:** PaaS hosting, app settings, scaling, and deployment slots (add a staging slot and swap as a bonus).

### Project 6: Microservices with Helm on AKS

**Full step-by-step guide:** [practice-projects/06-helm-microservices-aks.md](practice-projects/06-helm-microservices-aks.md)

**Goal:** deploy two services (for example `orders` and `payments`, in Flask or Node.js) with Helm charts.

**Steps:**

1. Create a chart: `Chart.yaml`, `values.yaml`, and `templates/` (Deployment, Service, Ingress, ConfigMap, Secret).
2. Deploy with `helm upgrade --install`.
3. Expose both services through one **Ingress** (`/orders`, `/payments`).
4. Automate with GitHub Actions: build images > push to ACR > `helm upgrade --install`.
5. **Bonus:** one namespace per environment (`dev`, `staging`, `prod`) with `values-<env>.yaml`.

**What it teaches:** Helm templating, Ingress, ConfigMaps and Secrets, and multi-environment deployments.

### Project 7: Azure VM configuration with Ansible

**Full step-by-step guide:** [practice-projects/07-ansible-azure-vm-automation.md](practice-projects/07-ansible-azure-vm-automation.md)

**Goal:** provision and configure an Azure VM with Ansible.

**What to build:**

- A `main.yml` playbook using the **`azure.azcollection`** modules to create the VM.
- The **Azure dynamic inventory plugin** (`azure_rm.yml`) to find VMs by tag instead of a static host list.
- Roles to install and configure **Nginx** or **Apache** and copy the application files.

**What it teaches:** configuration management, idempotent playbooks, dynamic inventory, and how Ansible complements Terraform or Bicep.

### Project 8: Key Vault with managed identity

**Full step-by-step guide:** [practice-projects/08-key-vault-managed-identity.md](practice-projects/08-key-vault-managed-identity.md)

**Goal:** the application reads secrets from Key Vault with **no credentials anywhere**.

**Steps:**

1. Create a Key Vault (RBAC permission model) and add secrets with a setup script.
2. Turn on a **system-assigned or user-assigned managed identity** on the app (App Service, VM, or Function).
3. Give the identity the **Key Vault Secrets User** role. (The older way is a Key Vault **access policy**; RBAC is now recommended.)
4. In the app, read secrets with the Azure SDK (`DefaultAzureCredential` + `SecretClient`) or use **Key Vault references** in App Service settings.

**What it teaches:** secretless authentication, Key Vault RBAC, and secret rotation.

### Project 9: Containerize a Python Flask app

**Full step-by-step guide:** [practice-projects/09-flask-app-docker.md](practice-projects/09-flask-app-docker.md)

**Goal:** build, run, and publish a container locally.

**Steps:**

1. Write a Flask API with a `/hello` endpoint.
2. Write a `Dockerfile` (slim base image, non-root user) and a `.dockerignore`.
3. Build and run: `docker build -t flask-app .` and `docker run -p 5000:5000 flask-app`.
4. Tag and push to Docker Hub.
5. **Bonus:** a `docker-compose.yml` that adds **Redis** or **Postgres**.

**What it teaches:** image layers, caching, tagging, `.dockerignore`, and multi-container apps.

### Project 10: Flask app on Azure Container Instances (ACI)

**Full step-by-step guide:** [practice-projects/10-flask-app-azure-container-instances.md](practice-projects/10-flask-app-azure-container-instances.md)

**Goal:** run the container serverlessly, with no VM or cluster.

**Steps:**

1. Deploy with `az container create --image <image> --dns-name-label <name> --ports 5000`.
2. Automate with GitHub Actions: build > push > `az container create`.
3. Log in to Azure with **OIDC (workload identity federation)** instead of a service principal secret.

**What it teaches:** when to use ACI (simple jobs, quick tests) versus App Service or AKS.

### Project 11: Flask app on AKS provisioned by Terraform

**Full step-by-step guide:** [practice-projects/11-flask-app-aks-terraform.md](practice-projects/11-flask-app-aks-terraform.md)

**Goal:** Terraform creates the platform; kubectl deploys the app.

**Steps:**

1. Terraform creates **AKS** and **ACR**, and gives the AKS kubelet identity the **AcrPull** role on ACR (so no image pull secret is needed).
2. Build and push the image to ACR.
3. Apply `deployment.yaml` and `service.yaml`.
4. **Bonus:** a `LoadBalancer` Service for external access.

**What it teaches:** Terraform for AKS, ACR authentication, and kubectl basics.

### Project 12: Azure Function App with GitHub Actions

**Full step-by-step guide:** [practice-projects/12-azure-function-app-github-actions.md](practice-projects/12-azure-function-app-github-actions.md)

**Goal:** deploy a serverless function automatically.

**Steps:**

1. Create the project with `func init` and `func new` (HTTP trigger returning "Hello from Azure Functions").
2. Create the Function App in Azure.
3. Add `.github/workflows/deploy.yml` using `azure/functions-action@v1`.
4. **Bonus:** a Logic App that calls the function over HTTP.

**What it teaches:** serverless basics, triggers and bindings, and Function deployment.

### Project 13: Logic App and Function event-driven flow

**Full step-by-step guide:** [practice-projects/13-logic-app-function-event-driven.md](practice-projects/13-logic-app-function-event-driven.md)

**Goal:** process uploaded files automatically.

**Flow:**

```text
File uploaded to Blob Storage
  -> Logic App blob trigger
  -> HTTP call to Azure Function (processes the data)
  -> Function writes the result to Cosmos DB
```

**Bonus:** Application Insights to monitor each run. For a locked-down Storage account, see [08-logic-app-secured-storage-access.md](08-logic-app-secured-storage-access.md).

**What it teaches:** event-driven design, Logic App connectors, and Function integration.

### Project 14: AKS observability with Azure Monitor

**Full step-by-step guide:** [practice-projects/14-aks-observability-azure-monitor.md](practice-projects/14-aks-observability-azure-monitor.md)

**Goal:** see AKS health and logs in one place.

**Steps:**

1. Enable **Container Insights** and connect AKS to a **Log Analytics workspace**.
2. Run KQL queries, for example:

```kusto
KubePodInventory
| where PodStatus != "Running" and PodStatus != "Succeeded"
| summarize count() by Namespace, PodStatus
```

3. Create **alerts** (node CPU, Pod restarts, failed Pods) with an **Action Group**.
4. Build a **Workbook** or dashboard.
5. **Bonus:** Application Insights for app-level tracing; Managed Prometheus and Grafana for metrics.

**What it teaches:** monitoring, KQL, and alerting.

### Project 15: Full microservices CI/CD platform on AKS

**Full step-by-step guide:** [practice-projects/15-full-microservices-platform-aks.md](practice-projects/15-full-microservices-platform-aks.md)

**Goal:** combine everything into one enterprise-style setup.

```text
Terraform        -> AKS, ACR, Log Analytics, Key Vault
GitHub Actions   -> build Docker images, scan, push to ACR
Helm             -> deploy to AKS with per-environment values
Azure Monitor    -> logs and metrics
Function App     -> background events, processed asynchronously
```

**Deliverables:** `main.tf` (infrastructure), a `helm/` chart, `.github/workflows/ci-cd.yml`, a Python service, a Function App, and AKS + ACR + Key Vault + Log Analytics fully connected.

**What it teaches:** end-to-end cloud-native delivery, GitOps-style workflows, observability, and automation. This is the best one to walk through in an interview because it touches every tool.

### Quick notes

#### How do you take snapshots in a Storage account?

A **blob snapshot** is a read-only copy of a blob at a point in time.

```bash
az storage blob snapshot --account-name stdemo --container-name data --name report.json --auth-mode login
```

- Portal: open the blob > **Snapshots** > **Create snapshot**.
- For protection without manual snapshots, turn on **blob versioning** (every overwrite keeps the old version) and **soft delete** for blobs and containers.
- For **Azure Files**, take **share snapshots**, or use **Azure Backup** for scheduled snapshots and retention.
- Use **lifecycle management** rules to delete old snapshots and versions, so they do not grow storage costs.

#### What is Azure Policy?

Azure Policy checks that resources follow your rules **whoever creates them**. Examples: only allowed regions, Storage accounts must block public access, every resource needs an `owner` tag. Effects include **Deny** (block), **Audit** (report), **Modify** (fix tags), and **DeployIfNotExists** (add missing settings, such as diagnostic logs). Policies are grouped into **initiatives** and assigned at a management group, subscription, or resource group. RBAC controls **who** can act; Policy controls **what** resources may look like.

#### Vulnerability scanning tools

| Area | Tools |
| --- | --- |
| Azure | Microsoft Defender for Cloud, Defender for Containers (scans ACR images and running AKS workloads), Azure Policy |
| Docker images | Trivy (Aqua Security), Docker Scout (replaced the older `docker scan` Snyk integration), Snyk |
| Kubernetes | kube-bench (CIS benchmark checks, Aqua Security), Trivy for Kubernetes, Kubescape. kube-hunter is no longer maintained |
| IaC | Checkov, tfsec (now part of Trivy) |

#### PodDisruptionBudget (PDB)

A PDB keeps a minimum number of Pods running during **voluntary disruptions**, such as node drains during an AKS upgrade or scale-down.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: webapp-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: webapp
```

During a drain, Kubernetes evicts Pods only while at least one `app: webapp` Pod stays available. Run at least **two replicas**; with one replica and `minAvailable: 1`, the drain can never evict the Pod and the upgrade gets stuck.

## Interview Questions

<details><summary>Q1. [Basic] Tell me about a hands-on project you built to learn DevOps tools.</summary>

**Answer:**

Pick the project you know best, ideally Project 15 or Project 6, and use STAR:

- **Situation:** I wanted hands-on practice with the full Azure cloud-native stack.
- **Task:** build a microservices app with infrastructure, CI/CD, and monitoring fully automated.
- **Action:** Terraform for AKS, ACR, Key Vault, and Log Analytics; GitHub Actions to build, scan, and push images; Helm to deploy with per-environment values; Azure Monitor for logs and alerts.
- **Result:** one `git push` builds and deploys the app to AKS with no manual steps. `[Confirm: your repo link and what you learned or would improve]`

</details>

<details><summary>Q2. [Intermediate] Why would you choose ACI, App Service, or AKS for a container?</summary>

**Answer:**

- **ACI:** a single container or a short job, no scaling rules, quickest to start. Good for tests and batch tasks.
- **App Service (Web App for Containers):** web apps and APIs that need custom domains, TLS, autoscale, and deployment slots, without managing Kubernetes.
- **AKS:** many microservices, advanced networking, service-to-service traffic, Helm, and full control over scaling and deployments. More power, more work.

</details>

<details><summary>Q3. [Intermediate] Why use remote state in Terraform, and how do you store it in Azure?</summary>

**Answer:**

Remote state lets the whole team and the pipeline share one state file, and it prevents two people applying at the same time. In Azure, use the `azurerm` backend: a Storage account and container hold the state file, and blob leases provide locking. Protect it with RBAC, versioning or soft delete, and no public access, because the state can contain secrets.

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstate001"
    container_name       = "tfstate"
    key                  = "dev/app.tfstate"
    use_azuread_auth     = true
  }
}
```

</details>

<details><summary>Q4. [Intermediate] How does AKS pull images from ACR without a password?</summary>

**Answer:**

Give the AKS **kubelet managed identity** the **AcrPull** role on the registry. The easy way is `az aks update -g rg -n aks --attach-acr <acr-name>`; in Terraform, create an `azurerm_role_assignment` for the kubelet identity's object ID. No image pull secret is needed.

</details>

<details><summary>Q5. [Advanced] An AKS upgrade is stuck draining a node. What do you check?</summary>

**Answer:**

1. **PodDisruptionBudgets:** `kubectl get pdb -A`. A PDB with `ALLOWED DISRUPTIONS` of 0 blocks eviction, usually because the deployment has only one replica or Pods are not Ready.
2. **Pod status:** Pods stuck terminating, or Pods that cannot start on the new node (Pending because of resources, taints, or node selectors).
3. **Events:** `kubectl get events -A --sort-by=.lastTimestamp`.

Fix: scale the deployment to at least two replicas, or temporarily relax the PDB, then continue the upgrade. Long term, every important workload should have two or more replicas and a sensible PDB.

</details>
