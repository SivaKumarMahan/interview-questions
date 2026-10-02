# Azure DevOps: Fundamentals and Platform Overview

> What Azure DevOps is, classic vs YAML pipelines, the end-to-end CI/CD flow, and working alongside GitHub Actions.

## Key Concepts

### End-to-End CI/CD Pipeline

1. A developer works through a feature branch and a pull request in Azure Repos or another Git provider. Branch policies require review, build validation, and the right checks.
2. Azure Pipelines restores dependencies, compiles the code, runs unit and integration tests, and runs static, dependency, secret, infrastructure-as-code, and container security checks.
3. The pipeline produces a versioned package or image that never changes once built, and publishes it to Azure Artifacts or Azure Container Registry with a clear link back to the commit it came from.
4. Deployment promotes that same artifact through Dev, Test, Staging/UAT, and Production. Configuration for each environment lives outside the artifact — the artifact itself never gets rebuilt.
5. Protected environments use checks like approval, policy, a change window, an exclusive lock, health evidence, and automated smoke tests. Blue-green, canary, or rolling deployment cuts down production risk where it's supported.
6. Azure Monitor, Log Analytics, and Application Insights confirm availability, errors, latency, dependency health, infrastructure health, and that real business transactions still work. If verification fails, promotion stops or a known rollback kicks in.

Deployment targets can include App Service, AKS, Functions, VMs, and hybrid infrastructure. Authenticate with workload federation or managed identity wherever you can, give each stage only the access it needs, protect production service connections, and keep pipeline and audit evidence around.

### GitHub Actions with Azure DevOps

GitHub Actions and Azure DevOps can work together when GitHub is where the code lives and Azure DevOps owns the controlled deployment. The split in responsibility needs to be explicit:

```text
GitHub pull request
  -> GitHub Actions: build, test and fast security checks
  -> publish a package or image digest that never changes
  -> Azure DevOps: consume that exact version
  -> deployment-environment approvals and checks
  -> deploy to AKS
  -> smoke tests and Azure Monitor verification
```

Azure Pipelines can also connect directly to a GitHub repository and handle both CI and CD itself. Running two separate automation systems only makes sense when it reflects real team ownership or a governance requirement — otherwise it just adds more authentication, traceability, and troubleshooting complexity than you need.

For a split pipeline like this:

- Publish the package to an artifact repository, or the image to Azure Container Registry. Never pass an unverified, mutable `latest` tag between the two systems.
- Record the commit SHA, the build run, the SBOM (the list of everything that went into the build), the scan result, and a fixed artifact version or digest that won't change later.
- Only trigger or authorize a deployment once the artifact actually exists — never rebuild it inside Azure DevOps.
- Use GitHub OIDC with an Azure workload identity, or an Azure DevOps workload-federated service connection, instead of a long-lived cloud credential.
- Restrict the GitHub connection, service connection, environment, and agent pool to only the pipelines that are authorized to use them.
- Send deployment status back to the source commit, so reviewers can trace the build and release evidence from there.

## Interview Questions

### 1. What is Azure DevOps?

**Answer:**

Azure DevOps is Microsoft's platform for the whole application lifecycle. Its main services are Azure Repos for source control, Pipelines for CI/CD, Boards for work tracking, Artifacts for packages, and Test Plans for test management.

A typical flow links a Board work item to a branch and a pull request, runs build, test, and security checks in Pipelines, publishes a versioned package or image, deploys through protected environments, and records evidence of the deployment. Azure DevOps can deploy to Azure or to other platforms just as easily.

I set up Entra-backed groups, access scoped to only what's needed, protected branches, workload-identity service connections, YAML templates, artifact retention, approvals, and audit logs. The real value here is being able to trace a change all the way from code to work item to build to artifact to release — not just running scripts.

### 2. What is the difference between Azure Pipelines classic release and YAML pipelines?

**Answer:**

Classic build and release pipelines are configured mostly through the UI. YAML pipelines live in the repository as code, which means they get code review, branching, templates, version history, and are easier to reuse.

Classic releases still show up in older systems, or where a team just prefers managing stages through the UI.

I prefer multi-stage YAML for new work. Changes to production logic go through pull-request review, and environment approvals and checks stay configured outside the YAML file itself, so a code change can't accidentally remove a safety gate.

When migrating, I inventory the tasks, variables, service connections, approvals, artifacts, schedules, and retention settings, rebuild them in YAML and templates, run both pipelines side by side safely, compare the artifacts and deployments they produce, then retire the old credentials once the cutover is done.
### 3. What frontend and backend applications have you worked on? Explain the end-to-end flow from commit to production.

**Interviewer:** I am giving an interview for an Azure DevOps Engineer role. What applications have you used in frontend and backend? Give the end-to-end flow.

For an Azure DevOps Engineer interview, explain one realistic application architecture and then walk through the complete flow from developer commit to production.

#### 4.1 Example application

I would use a 3-tier application:

- **Frontend:** React.js
- **Backend:** .NET Core Web API
- **Database:** Azure SQL
- **Containerization:** Docker
- **Orchestration:** AKS
- **Ingress:** NGINX Ingress Controller
- **CI/CD:** Azure DevOps Pipelines
- **IaC:** Terraform
- **Secrets:** Azure Key Vault
- **Monitoring:** Azure Monitor + Application Insights + Prometheus/Grafana

#### 4.2 End-to-end architecture

The runtime flow is:

```
User -> DNS -> Application Gateway/Load Balancer -> Ingress -> Frontend -> Backend API -> Azure SQL
```

And the deployment flow is:

```
Developer -> Git -> Azure DevOps CI pipeline -> Build/Test -> Docker Image
   -> Azure Container Registry -> CD Pipeline -> AKS -> Production
```

#### 4.3 How I would explain it in an interview

> "In my project, we had a React-based frontend and a .NET Core Web API backend. Both applications were containerized using Docker and deployed into Azure Kubernetes Service. Azure SQL was used as the backend database.
>
> Developers pushed their code to Azure Repos. This triggered the Azure DevOps CI pipeline. The pipeline performed code checkout, dependency installation, unit testing, SonarQube/code-quality checks, Docker image build and security scanning. After successful validation, the images were pushed to Azure Container Registry.
>
> For deployment, we used Helm charts to deploy the frontend and backend into AKS. The CD pipeline retrieved the required image from ACR and performed a Helm upgrade. Kubernetes created or updated the pods using a rolling update strategy.
>
> External traffic came through DNS and the ingress layer. The ingress routed frontend and API traffic to the appropriate Kubernetes services. The frontend communicated with the backend through REST APIs, and the backend connected to Azure SQL.
>
> Application secrets such as database credentials and API keys were stored in Azure Key Vault rather than directly in the pipeline or Kubernetes manifests.
>
> We monitored the application using Azure Monitor and Application Insights, while Prometheus and Grafana were used for Kubernetes metrics and dashboards. If a deployment failed, we checked pipeline logs, Kubernetes events, pod status, container logs, readiness/liveness probes and ingress logs."

#### 4.4 Complete deployment flow

##### Step 1: Developer changes code

Developer works on:

```
Frontend
React.js
   |
   +-- src/
   +-- package.json
   +-- Dockerfile

Backend
.NET Core Web API
   |
   +-- Controllers/
   +-- Services/
   +-- appsettings.json
   +-- Dockerfile
```

Developer creates a feature branch:

```bash
git checkout -b feature/payment
```

After development:

```bash
git add .
git commit -m "Added payment functionality"
git push origin feature/payment
```

A Pull Request is created.

##### Step 2: Pull Request validation

Azure DevOps pipeline gets triggered.

Typical validations:

```
Checkout code
     |
Install dependencies
     |
Build
     |
Unit tests
     |
SonarQube
     |
Security scanning
     |
PR approval
```

Frontend:

```bash
npm install
npm test
npm run build
```

Backend:

```bash
dotnet restore
dotnet build
dotnet test
```

We can also run SonarQube, Checkov, Trivy or tfsec depending on what is being scanned.

##### Step 3: Docker image creation

After the code passes validation, we build Docker images.

For example:

```
frontend:v1.2.0
backend:v1.2.0
```

Frontend Docker image:

```
React application
      |
npm build
      |
Nginx
      |
Frontend Docker image
```

Backend:

```
.NET Core application
      |
dotnet publish
      |
.NET runtime
      |
Backend Docker image
```

I would normally use multi-stage Docker builds so the final image contains only what is required to run the application.

##### Step 4: Push images to ACR

The pipeline authenticates to Azure using an Azure DevOps Service Connection.

Then:

```bash
docker build -t myacr.azurecr.io/frontend:1.2.0 .
docker push myacr.azurecr.io/frontend:1.2.0
```

Similarly:

```bash
docker build -t myacr.azurecr.io/backend:1.2.0 .
docker push myacr.azurecr.io/backend:1.2.0
```

Now ACR contains:

```
ACR
 ├── frontend
 │    ├── 1.1.0
 │    └── 1.2.0
 │
 └── backend
      ├── 1.1.0
      └── 1.2.0
```

##### Step 5: CD pipeline deploys to AKS

The CD pipeline picks the approved image version. We use Helm.

```
Helm Chart
 ├── Chart.yaml
 ├── values.yaml
 └── templates/
      ├── deployment.yaml
      ├── service.yaml
      └── ingress.yaml
```

The pipeline executes something like:

```bash
helm upgrade --install frontend ./helm/frontend \
  --set image.tag=1.2.0 \
  -n production
```

And:

```bash
helm upgrade --install backend ./helm/backend \
  --set image.tag=1.2.0 \
  -n production
```

##### Step 6: Kubernetes deployment

AKS receives the deployment.

For backend:

```
Deployment
     |
     +---- Pod 1
     +---- Pod 2
     +---- Pod 3
```

The Service provides stable networking:

```
Backend Service
      |
      +---- Pod 1
      +---- Pod 2
      +---- Pod 3
```

If we deploy a new version, Kubernetes performs a rolling update.

```
Old Pods
v1.1
v1.1
v1.1

       |
New Pods created
v1.2
v1.2

       |
Old Pods terminated

       |
v1.2
v1.2
v1.2
```

Readiness probes make sure traffic is sent only to healthy pods.

##### Step 7: User request flow

The user accesses:

```
https://myapp.com
```

Flow:

```
User
  |
DNS
  |
Azure Application Gateway / Load Balancer
  |
NGINX Ingress Controller
  |
Frontend Service
  |
Frontend Pods
```

The React frontend calls:

```
https://myapp.com/api/orders
```

Ingress routes `/api` traffic to the backend:

```
Ingress
   |
   +-- /       -> Frontend Service
   |
   +-- /api    -> Backend Service
```

Then:

```
Backend Pod
    |
Azure SQL
```

So the complete runtime flow is:

```
User
 |
DNS
 |
Application Gateway
 |
Ingress Controller
 |
Frontend Service
 |
React Pod
 |
REST API
 |
Backend Service
 |
.NET Core Pod
 |
Azure SQL
```

##### Step 8: Where Key Vault comes in

We don't hardcode things like:

```
DB_PASSWORD
API_KEY
CONNECTION_STRING
```

Instead:

```
Azure Key Vault
       |
AKS / Workload Identity
       |
Backend Pod
```

The application retrieves the required secrets securely.

For Azure DevOps authentication to Azure resources, I would use an appropriate service connection, preferably with managed identity / workload identity where the architecture supports it.

##### Step 9: Monitoring

For application monitoring:

```
Frontend
Backend
   |
Application Insights
   |
Azure Monitor
```

For Kubernetes:

```
AKS
 |
Prometheus
 |
Grafana
```

We monitor:

- CPU / memory
- Pod restarts
- Node health
- API response time
- HTTP 4xx / 5xx
- Application exceptions
- Availability
- Container logs

Alerts can notify the team when thresholds are breached.

#### 4.5 If interviewer asks "What applications have you worked on?"

Don't just say:

> "I worked on React and .NET."

Say:

> "I worked on a web-based three-tier application. The frontend was React.js, the backend was .NET Core REST APIs, and Azure SQL was used as the database. From the DevOps side, I was responsible for Git-based source control, Azure DevOps CI/CD, Docker image creation, ACR, AKS deployments using Helm, Terraform for infrastructure, Key Vault for secrets, and Azure Monitor/Application Insights for monitoring."

Then immediately explain:

> "The end-to-end flow was developer commit -> PR -> CI validation -> Docker build -> security/code-quality checks -> ACR -> CD pipeline -> Helm deployment -> AKS -> Ingress -> frontend/backend -> Azure SQL -> monitoring."

That answer gives the interviewer both application knowledge and actual DevOps ownership, which is what they usually look for in an Azure DevOps interview.

#### 4.6 Additional enterprise elements worth mentioning

For a more enterprise-scale version of the same architecture:

- **Azure Front Door** in front of Application Gateway for global routing/CDN, when the application serves multiple regions.
- **TDE (Transparent Data Encryption)** on Azure SQL for encryption at rest.
- **Redis** as a caching layer between the backend and the database to reduce database load.
- **GZRS (Geo-Zone-Redundant Storage)** for the storage tier when both zone and region redundancy are required.
