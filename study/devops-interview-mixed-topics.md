# DevOps Interview - Mixed Topics

Collected interview questions and answers across Helm, CI/CD, Terraform, Kubernetes, Docker, monitoring and Python.

## Contents

1. [Helm - charts, deployments, upgrades and rollback](#1-helm---charts-deployments-upgrades-and-rollback)
2. [Adding one env variable to 30 pipelines](#2-adding-one-env-variable-to-30-pipelines)
3. [PR has one change but terraform plan shows many changes](#3-pr-has-one-change-but-terraform-plan-shows-many-changes)
4. [Frontend and backend applications - end to end flow](#4-frontend-and-backend-applications---end-to-end-flow)
5. [Ingress and DNS in Kubernetes](#5-ingress-and-dns-in-kubernetes)
6. [NetworkPolicy](#6-networkpolicy)
7. [Alerts in Prometheus and Grafana](#7-alerts-in-prometheus-and-grafana)
8. [Python - list, tuple, dictionary, set](#8-python---list-tuple-dictionary-set)
9. [Python - sample programs](#9-python---sample-programs)
10. [Terraform workspaces across environments](#10-terraform-workspaces-across-environments)
11. [Docker network types](#11-docker-network-types)
12. [ConfigMap, Secret, ServiceAccount, Namespace](#12-configmap-secret-serviceaccount-namespace)
13. [Kubernetes Service types](#13-kubernetes-service-types)
14. [Terraform drift and anomaly](#14-terraform-drift-and-anomaly)
15. [Organizing a Terraform project for multiple environments](#15-organizing-a-terraform-project-for-multiple-environments)
16. [TFLint](#16-tflint)
17. [tfsec, Checkov, Trivy](#17-tfsec-checkov-trivy)
18. [App Service vs App Service Plan vs Web App](#18-app-service-vs-app-service-plan-vs-web-app)
19. [Dockerfile - COPY vs ADD, CMD vs ENTRYPOINT](#19-dockerfile---copy-vs-add-cmd-vs-entrypoint)
20. [Jenkins pipeline for AKS - basic and enterprise version](#20-jenkins-pipeline-for-aks---basic-and-enterprise-version)
21. [Teams bots, Adaptive Cards and dashboard visualization](#21-teams-bots-adaptive-cards-and-dashboard-visualization)

---

## 1. Helm - charts, deployments, upgrades and rollback

**Interviewer:** How are you using Helm in Kubernetes? Explain Helm charts, deployments, upgrades, and the complete rollback procedure.

**Candidate:**

I use Helm as the package manager for Kubernetes. Instead of maintaining large Kubernetes YAML files separately for every environment, I create a reusable Helm chart and pass environment-specific values through `values.yaml` or separate values files.

### 1.1 Helm chart structure

A typical chart looks like this:

```
my-app/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── configmap.yaml
```

- **Chart.yaml** - chart name and version
- **values.yaml** - default configuration such as image, replicas, CPU, memory
- **templates/** - Kubernetes manifests containing Helm templating
- **templates/deployment.yaml** - creates the Kubernetes Deployment
- **templates/service.yaml** - creates the Service

For different environments, I normally maintain files like:

```
values-dev.yaml
values-qa.yaml
values-prod.yaml
```

### 1.2 Helm deployment

First, I validate the chart:

```bash
helm lint ./my-app
```

Then I render the templates to check what Kubernetes YAML will actually be generated:

```bash
helm template my-app ./my-app -f values-prod.yaml
```

Then I install it:

```bash
helm install my-app ./my-app \
  -n production \
  --create-namespace \
  -f values-prod.yaml
```

I verify the release:

```bash
helm list -n production
helm status my-app -n production
```

Then I verify the Kubernetes resources:

```bash
kubectl get pods -n production
kubectl get deployment -n production
kubectl get svc -n production
```

### 1.3 Helm upgrade

Suppose the application team releases version v2.

I update the image tag in `values-prod.yaml`:

```yaml
image:
  repository: myacr.azurecr.io/my-app
  tag: "v2"
```

Then I run:

```bash
helm upgrade my-app ./my-app \
  -n production \
  -f values-prod.yaml
```

I check the rollout:

```bash
kubectl rollout status deployment/my-app -n production
```

And check the Helm revision:

```bash
helm history my-app -n production
```

For example:

```
REVISION  STATUS
1         superseded
2         deployed
```

Each Helm upgrade creates a new release revision, which is important for rollback.

In CI/CD I normally combine install and upgrade into one idempotent command instead of branching on "does this release already exist":

```bash
helm upgrade --install my-app ./my-app \
  -n production \
  -f values-prod.yaml
```

For a quick one-off change without editing the values file, `--set` overrides a single value directly:

```bash
helm upgrade my-app ./my-app -n production --set image.tag=v2
```

### 1.4 Complete Helm rollback procedure

Suppose revision 2 introduced a bad application version and the Pods are failing.

**Step 1: Check the application**

```bash
kubectl get pods -n production
kubectl describe pod <pod-name> -n production
kubectl logs <pod-name> -n production
```

**Step 2: Check Helm history**

```bash
helm history my-app -n production
```

Suppose I see:

```
REVISION  STATUS
1         superseded
2         superseded
3         deployed
```

I identify revision 2 as the last known good release.

**Step 3: Roll back**

```bash
helm rollback my-app 2 -n production
```

Helm creates a new revision based on revision 2. It does not simply delete the current revision.

I then check:

```bash
helm history my-app -n production
```

I might see:

```
REVISION  STATUS
1         superseded
2         superseded
3         superseded
4         deployed
```

Revision 4 is the rollback operation.

**Step 4: Verify Kubernetes rollout**

```bash
kubectl rollout status deployment/my-app -n production
```

Then:

```bash
kubectl get pods -n production
kubectl get deployment -n production
```

I also check the application logs and readiness probes to make sure the application is actually healthy.

**Step 5: Verify the Helm release**

```bash
helm status my-app -n production
```

If everything is healthy, I consider the rollback complete.

### 1.5 Important interview point

I would not immediately roll back just because a Pod restarted. First I check whether the problem is actually related to the latest Helm release.

My flow is:

```
Helm Chart
    |
helm install
    |
Kubernetes Deployment
    |
helm upgrade
    |
New Helm Revision
    |
Application issue
    |
helm history
    |
Identify last known-good revision
    |
helm rollback
    |
Kubernetes rollout
    |
Verify Pods + Application
```

### 1.6 Strong interview answer

> "In my projects, I use Helm to package Kubernetes resources into reusable charts. The chart contains Chart.yaml, values.yaml, and templates such as Deployment, Service, and Ingress. For deployment, I validate the chart using `helm lint` and `helm template`, then use `helm install` or `helm upgrade` with environment-specific values. Every upgrade creates a new Helm revision. If the latest deployment has an issue, I check `helm history`, identify the last known-good revision, and run `helm rollback <release> <revision>`. After rollback, I verify the Helm status, Kubernetes rollout, Pod health, logs, and application functionality."

### 1.7 Best practices

- Separate values files per environment (`values-dev.yaml`, `values-qa.yaml`, `values-prod.yaml`) instead of branching logic inside templates.
- Keep secrets out of the chart where possible - reference an external secret manager (e.g. Azure Key Vault) rather than committing secret values to `values.yaml`.
- Version Helm charts, so a specific chart version can be pinned and rolled back independently of the application image tag.
- Always run `helm lint` before deploying.
- Use `helm upgrade --install` in CI/CD so the same command works for both first deploy and subsequent releases.
- Verify the rollout (`kubectl rollout status`) after every install/upgrade rather than assuming success from Helm's own exit code.
- Roll back immediately on a failed deployment rather than trying to hotfix forward under pressure.

---

## 2. Adding one env variable to 30 pipelines

**Interviewer:** You have 30 CI/CD pipelines and need to add one environment variable to all of them. How would you avoid updating each pipeline manually?

**Candidate:**

I would avoid duplicating the variable across 30 pipelines. I would centralize the configuration.

If I'm using Jenkins, my preferred approach is a Jenkins Shared Library or a centrally managed configuration.

For example, instead of defining:

```groovy
environment {
    APP_ENV = 'production'
}
```

in every Jenkinsfile, I can define the common environment variable in the shared library or global configuration and let all pipelines consume it.

### 2.1 Jenkins Shared Library approach

I could have a common pipeline function:

```groovy
def call() {
    pipeline {
        agent any

        environment {
            APP_ENV = 'production'
        }

        stages {
            stage('Build') {
                steps {
                    sh 'echo $APP_ENV'
                }
            }
        }
    }
}
```

Then the individual pipelines use the shared library rather than maintaining the common configuration themselves.

### 2.2 If using Azure DevOps

I would use a Variable Group:

```
Variable Group
      |
30 Pipelines
      |
APP_ENV = production
```

All pipelines reference the same Variable Group. If I change the variable there, all pipelines get the updated value.

### 2.3 Interview summary

> "I would not update 30 pipelines individually. I would centralize common environment variables. In Jenkins, I would use a Shared Library or centralized Jenkins configuration. In Azure DevOps, I would use a Variable Group. This gives us one place to maintain the variable and prevents configuration drift across pipelines."

---

## 3. PR has one change but terraform plan shows many changes

**Interviewer:** If a PR contains only one change, but `terraform plan` shows multiple changes, how would you troubleshoot it?

**Candidate:**

First, I would not assume Terraform is wrong. I would check whether the additional changes are caused by state drift, provider changes, dependencies, or the Terraform configuration itself.

### 3.1 Check the PR diff

First I verify exactly what changed:

```bash
git diff main...HEAD
```

I want to confirm there isn't an indirect change in a module, variable, `.tfvars` file, or shared configuration.

### 3.2 Check the Terraform plan

```bash
terraform plan
```

I carefully classify the changes:

```
+     -> resource creation
-     -> resource destruction
~     -> resource modification
-/+   -> resource replacement
```

Then I identify which resources are changing unexpectedly.

### 3.3 Check for Terraform state drift

Someone may have manually changed the Azure resource outside Terraform.

I would refresh the state and compare:

```bash
terraform plan -refresh-only
```

If this shows unexpected changes, I know there is likely infrastructure drift.

### 3.4 Check Terraform state

I verify whether Terraform's state matches the actual resources:

```bash
terraform state list
terraform state show <resource>
```

I also check whether resources were renamed, moved, imported, or deleted outside Terraform.

### 3.5 Check provider and module versions

A provider upgrade can change how Terraform interprets a resource.

```bash
terraform providers
```

I would also check `.terraform.lock.hcl` and recent changes to modules.

### 3.6 Check dependencies

One small change can legitimately affect multiple resources.

For example:

```
VNet change
   |
Subnet
   |
Private Endpoint
   |
AKS configuration
```

So I check the dependency relationship before assuming the extra changes are unexpected.

### 3.7 Check variables and environment

I verify that the PR pipeline is using the correct:

- `.tfvars`
- Environment variables
- Backend
- Workspace / state
- Terraform version
- Provider version

A very common issue is running the plan against the wrong state or environment.

### 3.8 Check the plan again

After finding and fixing the root cause:

```bash
terraform plan
```

I expect the plan to contain only the intended change.

### 3.9 Strong interview answer

> "If one PR change produces multiple Terraform changes, I first review the plan and classify the unexpected changes. Then I check the Git diff, state drift using `terraform plan -refresh-only`, Terraform state, provider and module versions, dependencies, and whether the pipeline is using the correct backend and variables. A common reason is infrastructure drift or a provider/module change. I don't blindly apply the plan until I understand why every unexpected resource is changing."

---

## 4. Frontend and backend applications - end to end flow

**Interviewer:** I am giving an interview for an Azure DevOps Engineer role. What applications have you used in frontend and backend? Give the end-to-end flow.

For an Azure DevOps Engineer interview, explain one realistic application architecture and then walk through the complete flow from developer commit to production.

### 4.1 Example application

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

### 4.2 End-to-end architecture

The runtime flow is:

```
User -> DNS -> Application Gateway/Load Balancer -> Ingress -> Frontend -> Backend API -> Azure SQL
```

And the deployment flow is:

```
Developer -> Git -> Azure DevOps CI pipeline -> Build/Test -> Docker Image
   -> Azure Container Registry -> CD Pipeline -> AKS -> Production
```

### 4.3 How I would explain it in an interview

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

### 4.4 Complete deployment flow

#### Step 1: Developer changes code

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

#### Step 2: Pull Request validation

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

#### Step 3: Docker image creation

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

#### Step 4: Push images to ACR

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

#### Step 5: CD pipeline deploys to AKS

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

#### Step 6: Kubernetes deployment

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

#### Step 7: User request flow

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

#### Step 8: Where Key Vault comes in

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

#### Step 9: Monitoring

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

### 4.5 If interviewer asks "What applications have you worked on?"

Don't just say:

> "I worked on React and .NET."

Say:

> "I worked on a web-based three-tier application. The frontend was React.js, the backend was .NET Core REST APIs, and Azure SQL was used as the database. From the DevOps side, I was responsible for Git-based source control, Azure DevOps CI/CD, Docker image creation, ACR, AKS deployments using Helm, Terraform for infrastructure, Key Vault for secrets, and Azure Monitor/Application Insights for monitoring."

Then immediately explain:

> "The end-to-end flow was developer commit -> PR -> CI validation -> Docker build -> security/code-quality checks -> ACR -> CD pipeline -> Helm deployment -> AKS -> Ingress -> frontend/backend -> Azure SQL -> monitoring."

That answer gives the interviewer both application knowledge and actual DevOps ownership, which is what they usually look for in an Azure DevOps interview.

### 4.6 Additional enterprise elements worth mentioning

For a more enterprise-scale version of the same architecture:

- **Azure Front Door** in front of Application Gateway for global routing/CDN, when the application serves multiple regions.
- **TDE (Transparent Data Encryption)** on Azure SQL for encryption at rest.
- **Redis** as a caching layer between the backend and the database to reduce database load.
- **GZRS (Geo-Zone-Redundant Storage)** for the storage tier when both zone and region redundancy are required.

---

## 5. Ingress and DNS in Kubernetes

**Key points:**

- Ingress defines HTTP/HTTPS routing rules and requires an Ingress controller.
- CoreDNS provides cluster DNS.
- Troubleshoot routing from the inside out: Pod readiness, endpoint slices, Service selectors and ports, DNS, Ingress rules/controller, then load balancer and firewall.

### 5.1 What is Ingress?

- Ingress manages external HTTP/HTTPS access to applications running inside the Kubernetes cluster.
- Instead of exposing every application with a separate LoadBalancer, Ingress lets you route traffic based on the host name or URL path.
- Ingress itself is just a set of routing rules. To enforce those rules, you need an **Ingress Controller** such as NGINX Ingress Controller, Azure Application Gateway Ingress Controller (AGIC), or Traefik.

### 5.2 What is DNS (CoreDNS)?

- Kubernetes uses CoreDNS as its internal DNS server.
- It allows Pods and Services to communicate using names instead of IP addresses.
- For example, a Pod can access a Service using `orders-service.default.svc.cluster.local` instead of remembering its IP.

### 5.3 How do you troubleshoot routing issues?

I troubleshoot from the inside out, starting with the application and moving toward the user.

**1. Check Pod health** - verify Pods are running and Ready.

```bash
kubectl get pods
```

**2. Check EndpointSlices** - ensure the Service has healthy backend endpoints.

```bash
kubectl get endpointslices
```

**3. Check the Service** - verify the selector matches the Pods, and confirm `port` and `targetPort` are correct.

```bash
kubectl describe svc <service-name>
```

**4. Check DNS** - verify the Service name resolves correctly.

```bash
nslookup <service-name>
dig <service-name>
```

**5. Check Ingress** - verify host, path, and backend Service configuration, and make sure the Ingress Controller is running.

```bash
kubectl describe ingress <ingress-name>
```

**6. Check the external Load Balancer and firewall** - verify the Load Balancer is healthy, and check NSG/firewall rules and DNS records if traffic is coming from outside the cluster.

### 5.3.1 When the Service specifically isn't reachable from *outside* the cluster

The steps above cover routing in general. When the specific complaint is "works inside the cluster, not from outside," add these:

**Test from inside the cluster first** - before blaming the Ingress/Load Balancer, confirm the Service itself works from inside the cluster using a temporary debug Pod:

```bash
kubectl run test-pod --rm -it --image=curlimages/curl -- sh
curl http://<service-name>:<port>
```

If this fails, the problem is between Service and Pod/Application - the Ingress and Load Balancer aren't the issue yet. If it succeeds, move outward.

**Confirm the Load Balancer actually has an external IP:**

```bash
kubectl get svc <ingress-controller-service> -n ingress-nginx
```

A `<pending>` `EXTERNAL-IP` means the cloud load balancer was never provisioned - that alone explains total external unreachability.

**Confirm the external DNS record points at that Load Balancer IP**, and that the required ports are actually open - normally `80` and `443` - on the NSG/firewall in front of it.

**Finally, review both the application logs and the Ingress Controller logs** - not just its config - since a config that looks correct can still be failing at the connection/upstream level.

### 5.4 Interview summary

> "Ingress controls external HTTP/HTTPS routing to Kubernetes Services, while CoreDNS provides internal name resolution. When troubleshooting, I start from the application by checking Pod readiness, then EndpointSlices, Service selectors and ports, DNS resolution, Ingress rules and controller, and finally the external Load Balancer and firewall."

---

## 6. NetworkPolicy

NetworkPolicy restricts Pod ingress and egress when supported by the CNI plugin.

- With no selecting policy, traffic is allowed by default.
- A policy isolates a selected Pod only for the directions listed in `policyTypes` or inferred from its rules.
- To deny all egress, select the Pods, include `Egress` in `policyTypes`, and provide no allowed egress rules.
- Use default-deny policies and add explicit allows for DNS and required application flows.

---

## 7. Alerts in Prometheus and Grafana

You can configure alerts in both Prometheus and Grafana, but they serve slightly different purposes.

### 7.1 Prometheus alerting (recommended)

Prometheus uses Alertmanager for alerting.

Flow:

```
Prometheus -> Alert Rules -> Alertmanager -> Email/Slack/Teams/PagerDuty
```

Example alerts:

- CPU > 80% for 5 minutes
- Memory > 80%
- Pod in CrashLoopBackOff
- Node NotReady
- Disk usage > 90%
- Deployment replicas unavailable

Prometheus continuously evaluates alert rules written in PromQL. When a condition is met, it sends the alert to Alertmanager, which handles routing, grouping, silencing, and notifications.

### 7.2 Grafana alerting

Grafana can also create alerts based on data from Prometheus (or other data sources).

Example:

- High application response time
- HTTP 5xx error rate
- Dashboard panel threshold exceeded

Grafana sends notifications directly to Email, Microsoft Teams, Slack, PagerDuty or Webhooks.

### 7.3 Which one should you use?

- **Prometheus + Alertmanager:** best for infrastructure and Kubernetes alerts. It is the standard choice in production.
- **Grafana:** best for dashboard-based alerts and when you have multiple data sources besides Prometheus.

### 7.4 Interview answer

> "Alerts can be configured in both Prometheus and Grafana. In production, I typically use Prometheus Alertmanager for Kubernetes and infrastructure alerts because it evaluates PromQL rules and provides features like grouping, routing, and silencing before sending notifications to Teams, Slack, or email. Grafana also supports alerting, and I mainly use it for dashboard-based or application-level alerts. Both integrate well with Prometheus, but Alertmanager is generally the preferred solution for Kubernetes monitoring."

---

## 8. Python - list, tuple, dictionary, set

### 8.1 List

Ordered, mutable (can be changed), allows duplicates.

```python
fruits = ["apple", "banana", "apple"]

fruits.append("orange")
print(fruits)
# ['apple', 'banana', 'apple', 'orange']
```

### 8.2 Tuple

Ordered, immutable (cannot be changed), allows duplicates.

```python
colors = ("red", "green", "blue")

print(colors[0])
# red
```

Trying to modify it:

```python
colors[0] = "black"   # Error
```

### 8.3 Dictionary

Stores data as key-value pairs. Mutable. Keys must be unique.

```python
employee = {
    "name": "Siva",
    "age": 28,
    "city": "Hyderabad"
}

print(employee["name"])
# Siva

employee["age"] = 29
```

### 8.4 Set

Unordered. Does not allow duplicates. Mutable.

```python
numbers = {1, 2, 3, 2, 1}

print(numbers)
# {1, 2, 3}

numbers.add(4)
print(numbers)
# {1, 2, 3, 4}
```

### 8.5 Interview summary

| Data Type | Ordered | Mutable | Duplicates | Example |
|---|---|---|---|---|
| List | Yes | Yes | Yes | `["a", "b", "a"]` |
| Tuple | Yes | No | Yes | `("a", "b", "a")` |
| Dictionary | Yes | Yes | Keys No, Values Yes | `{"name": "Siva"}` |
| Set | No | Yes | No | `{1, 2, 3}` |

### 8.6 One-line interview answer

- **List:** ordered, mutable, allows duplicates.
- **Tuple:** ordered, immutable, allows duplicates.
- **Dictionary:** stores data in key-value pairs with unique keys.
- **Set:** unordered collection of unique elements.

---

## 9. Python - sample programs

The most commonly asked Python coding questions in DevOps interview rounds.

### 9.1 Fibonacci series

```python
n = 10
a, b = 0, 1

for i in range(n):
    print(a, end=" ")
    a, b = b, a + b
```

Output:

```
0 1 1 2 3 5 8 13 21 34
```

### 9.2 Check prime number

```python
num = 17

if num > 1:
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            print("Not Prime")
            break
    else:
        print("Prime")
else:
    print("Not Prime")
```

### 9.3 Swap two numbers

Using a temporary variable:

```python
a = 10
b = 20

temp = a
a = b
b = temp

print(a, b)
```

The Python way:

```python
a = 10
b = 20

a, b = b, a

print(a, b)
```

### 9.4 Reverse a string

```python
text = "DevOps"

print(text[::-1])
```

Output:

```
spOveD
```

### 9.5 Reverse a number

```python
num = 12345
rev = 0

while num > 0:
    digit = num % 10
    rev = rev * 10 + digit
    num //= 10

print(rev)
```

### 9.6 Factorial

```python
num = 5
fact = 1

for i in range(1, num + 1):
    fact *= i

print(fact)
```

Output:

```
120
```

### 9.7 Palindrome number

```python
num = 121
temp = num
rev = 0

while temp > 0:
    digit = temp % 10
    rev = rev * 10 + digit
    temp //= 10

if num == rev:
    print("Palindrome")
else:
    print("Not Palindrome")
```

### 9.8 Count vowels

```python
text = "Hello World"

count = 0

for ch in text.lower():
    if ch in "aeiou":
        count += 1

print(count)
```

### 9.9 Find largest number

```python
numbers = [10, 45, 23, 89, 67]

print(max(numbers))
```

### 9.10 Remove duplicates

```python
numbers = [1, 2, 2, 3, 4, 4, 5]

unique = list(set(numbers))

print(unique)
```

### 9.11 Count frequency of characters

```python
text = "banana"

freq = {}

for ch in text:
    freq[ch] = freq.get(ch, 0) + 1

print(freq)
```

Output:

```
{'b': 1, 'a': 3, 'n': 2}
```

### 9.12 Check even or odd

```python
num = 18

if num % 2 == 0:
    print("Even")
else:
    print("Odd")
```

### 9.13 Find maximum in a list (without max())

```python
numbers = [5, 9, 2, 14, 7]

largest = numbers[0]

for n in numbers:
    if n > largest:
        largest = n

print(largest)
```

### 9.14 Sum of list elements

```python
numbers = [10, 20, 30, 40]

print(sum(numbers))
```

### 9.15 Print multiplication table

```python
num = 5

for i in range(1, 11):
    print(f"{num} x {i} = {num * i}")
```

### 9.16 Armstrong number

A number equal to the sum of its own digits, each raised to the power of the digit count (e.g. `153 = 1³ + 5³ + 3³`).

```python
num = 153
digits = str(num)
power = len(digits)

total = sum(int(d) ** power for d in digits)

if total == num:
    print("Armstrong number")
else:
    print("Not an Armstrong number")
```

### 9.17 Most common interview programs

1. Fibonacci series
2. Prime number
3. Factorial
4. Palindrome
5. Reverse string
6. Reverse number
7. Swap two numbers
8. Even / odd
9. Largest number
10. Remove duplicates
11. Count vowels
12. Character frequency
13. Multiplication table
14. Sum of list elements
15. Armstrong number

These cover most of the basic Python coding questions asked in DevOps, Azure DevOps, and SRE interviews.

---

## 10. Terraform workspaces across environments

**Interviewer:** How do you manage multiple Terraform workspaces across environments?

In most production environments, I prefer separate state files and separate directories for each environment rather than relying only on Terraform workspaces.

For example:

```
terraform/
├── envs/
│   ├── dev/
│   ├── test/
│   └── prod/
└── modules/
    ├── network/
    ├── aks/
    └── sql/
```

Each environment has:

- Its own remote backend (separate state file)
- Its own `terraform.tfvars`
- Its own pipeline
- Separate access permissions

This reduces the risk of accidentally applying changes to the wrong environment.

I use Terraform workspaces only when the infrastructure is almost identical and the only difference is configuration values, such as creating temporary environments or feature branches.

When using workspaces, I create and switch them like this:

```bash
terraform workspace new dev
terraform workspace new test
terraform workspace new prod

terraform workspace select dev
terraform plan
terraform apply
```

I can also reference the current workspace inside the code:

```hcl
resource "azurerm_resource_group" "rg" {
  name = "rg-${terraform.workspace}"
}
```

### 10.1 Best practices I follow

- Keep a separate remote state for each environment.
- Use modules so infrastructure code is reusable.
- Store environment-specific values in `.tfvars` files.
- Protect production with approval gates in the CI/CD pipeline.
- Lock the state using the Azure Storage backend to prevent concurrent updates.
- Use the same Terraform version and provider versions across environments.

### 10.2 Short interview conclusion

> "For production environments, I prefer separate directories and separate remote state files for dev, test, and prod because it's safer and provides better isolation. I use Terraform workspaces only for nearly identical environments or temporary deployments where only configuration values change."

---

## 11. Docker network types

Docker provides several network drivers that define how containers communicate with each other and the outside world.

### 11.1 Bridge network (most common)

This is the default network created by Docker.

- Containers on the same bridge network can communicate with each other.
- External access is provided using port mapping (`-p`).
- Best suited for standalone applications running on a single host.

```bash
docker network create my-bridge

docker run -d --network my-bridge nginx
```

**Use case:** web applications, APIs, databases running on a single Docker host.

### 11.2 Host network

The container shares the host's network stack.

- No separate container IP.
- No NAT or port mapping required.
- Better network performance.
- Only one service can use a given port on the host.

```bash
docker run --network host nginx
```

**Use case:** high-performance networking applications.

### 11.3 None network

The container has no network connectivity.

- No internet access.
- No communication with other containers.

```bash
docker run --network none nginx
```

**Use case:** secure batch jobs or isolated containers.

### 11.4 Overlay network

Used when containers run on multiple Docker hosts.

- Enables communication across different hosts.
- Commonly used with Docker Swarm.

```bash
docker network create -d overlay my-overlay
```

**Use case:** multi-host container deployments.

### 11.5 Macvlan network

Assigns a unique MAC and IP address to each container.

- Containers appear as physical devices on the network.
- Communicate directly with the LAN.

**Use case:** legacy applications requiring direct network access.

### 11.6 Which one do you use?

> "In my projects, I primarily use the Bridge network because most of our Docker containers run on a single host during development or in CI/CD pipelines. It provides isolated networking, and I expose only the required ports using `-p`. For Kubernetes deployments, I don't manage Docker networking directly because Kubernetes uses its own Container Network Interface (CNI) plugins such as Azure CNI or Calico to handle pod networking."

### 11.7 Follow-up: how do containers communicate on a bridge network?

Containers connected to the same bridge network can communicate using container names because Docker provides an internal DNS service.

```bash
docker network create app-network

docker run -d --name db --network app-network mysql

docker run -d --name web --network app-network nginx
```

The web container can connect to the database using:

```
db:3306
```

instead of using an IP address.

### 11.8 Quick summary

| Network Type | Description | Typical Use |
|---|---|---|
| Bridge | Default isolated network on one host | Most commonly used |
| Host | Shares host network | High-performance apps |
| None | No networking | Isolated containers |
| Overlay | Multi-host networking | Docker Swarm |
| Macvlan | Container gets its own MAC/IP | Legacy or direct LAN access |

### 11.9 Short interview conclusion

> "Docker supports Bridge, Host, None, Overlay, and Macvlan networks. I mostly use the Bridge network for standalone containers because it provides secure communication between containers on the same host while allowing controlled external access through port mapping. For Kubernetes environments, networking is managed by the cluster's CNI plugin rather than Docker network drivers."

---

## 12. ConfigMap, Secret, ServiceAccount, Namespace

**Quick definitions:**

- **ConfigMap:** non-sensitive configuration.
- **Secret:** sensitive data; base64 encoding is not encryption.
- **ServiceAccount:** workload identity within the Kubernetes API.
- **Namespace:** logical isolation and scope for namespaced resources.

### 12.1 What is a ConfigMap?

> "A ConfigMap is used to store non-sensitive configuration data separately from the application. This allows us to change configuration without rebuilding the container image."

Examples of data stored in a ConfigMap:

- Application URLs
- Port numbers
- Feature flags
- Environment names
- Log levels

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
```

The application can consume this as environment variables, mounted files, or command-line arguments.

### 12.2 What is a Secret?

> "A Secret stores sensitive information such as passwords, API keys, database credentials, and certificates. Kubernetes stores Secret values as Base64-encoded data, but Base64 is only an encoding mechanism, not encryption. For stronger security, Secrets should be encrypted at rest and integrated with external secret managers like Azure Key Vault or HashiCorp Vault."

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQ=
```

The pod can consume the Secret as environment variables or mounted files.

**Follow-up: Is a Kubernetes Secret encrypted?**

> "By default, Secret values are Base64 encoded, which is not secure because anyone can decode them. In production, we enable encryption at rest in etcd and often integrate Kubernetes with Azure Key Vault or another external secrets manager."

### 12.3 What is a ServiceAccount?

> "A ServiceAccount provides an identity for a pod when it communicates with the Kubernetes API. Instead of using a user's credentials, applications running inside pods use a ServiceAccount to authenticate and authorize API requests."

Examples:

- Reading ConfigMaps
- Listing Pods
- Accessing Secrets (if permitted)
- Interacting with the Kubernetes API

A ServiceAccount works together with RBAC (Role and RoleBinding) to define what actions the pod is allowed to perform.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
```

Assign it to a pod:

```yaml
spec:
  serviceAccountName: app-sa
```

**Follow-up: Why not use the default ServiceAccount?**

> "The default ServiceAccount often has broader permissions than required. Following the principle of least privilege, I create dedicated ServiceAccounts with only the permissions the application needs."

### 12.4 What is a Namespace?

> "A Namespace is a logical partition within a Kubernetes cluster. It isolates resources, allowing multiple teams or environments to share the same cluster without resource name conflicts."

For example:

```
Cluster
│
├── dev
│     ├── pods
│     ├── services
│
├── test
│     ├── pods
│     ├── services
│
└── prod
      ├── pods
      ├── services
```

Each namespace can have its own Pods, Services, ConfigMaps, Secrets, resource quotas and RBAC policies.

**Follow-up: Can two namespaces have pods with the same name?**

Yes.

```
dev/nginx
prod/nginx
```

These are different resources because they belong to different namespaces.

### 12.5 Difference table

| Resource | Purpose | Contains |
|---|---|---|
| ConfigMap | Store non-sensitive configuration | URLs, ports, feature flags |
| Secret | Store sensitive data | Passwords, API keys, certificates |
| ServiceAccount | Identity for pods | Authentication to Kubernetes API |
| Namespace | Logical isolation | Groups and isolates resources |

### 12.6 One-line interview summary

- **ConfigMap** -> stores non-sensitive configuration.
- **Secret** -> stores sensitive data; Base64 encoding is not encryption.
- **ServiceAccount** -> provides a pod's identity to access the Kubernetes API.
- **Namespace** -> logically isolates resources within a cluster for different teams or environments.

---

## 13. Kubernetes Service types

**Quick definitions:**

- **ClusterIP:** stable internal virtual IP; the default Service type.
- **NodePort:** exposes a port on every node and forwards to the Service.
- **LoadBalancer:** requests an external or internal cloud load balancer.
- **ExternalName:** returns a configured external DNS name.
- **Headless Service:** uses `clusterIP: None` for direct endpoint discovery.
- `port` is the Service port, `targetPort` is the destination Pod port, and `nodePort` is the optional port exposed on cluster nodes.

### 13.1 ClusterIP Service

> "ClusterIP is the default Kubernetes Service type. It exposes an application only inside the cluster using a stable virtual IP. Other pods can access the application through the Service, but it isn't reachable from outside the cluster."

```
Pod A ----> ClusterIP Service ----> Pod B
```

**Use cases:** database services, internal APIs, backend microservices.

### 13.2 NodePort Service

> "NodePort exposes the application on a fixed port on every Kubernetes node. Traffic received on that port is forwarded to the Service and then to the target pods."

```
Client
   |
NodeIP:30080
   |
NodePort Service
   |
Pods
```

```yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080
```

**Use cases:** testing, development environments, labs.

### 13.3 LoadBalancer Service

> "A LoadBalancer Service creates a cloud load balancer in providers like Azure, AWS, or GCP. It exposes the application externally and distributes traffic across healthy pods."

```
Internet
    |
Azure Load Balancer
    |
Kubernetes Service
    |
Pods
```

**Use case:** production web applications and APIs.

### 13.4 ExternalName Service

> "ExternalName doesn't create a proxy or load balance traffic. Instead, it maps a Kubernetes Service to an external DNS name using a DNS CNAME record."

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  type: ExternalName
  externalName: mysql.company.com
```

Applications connect to:

```
mysql.default.svc.cluster.local
```

which resolves to:

```
mysql.company.com
```

**Use case:** accessing external databases or third-party services without changing application code.

### 13.5 Headless Service

> "A Headless Service is created by setting `clusterIP: None`. Kubernetes doesn't assign a virtual IP. Instead, DNS returns the IP addresses of the individual pods, allowing clients to communicate directly with them."

```yaml
spec:
  clusterIP: None
```

```
Headless Service
        |
DNS
        |
Pod-0
Pod-1
Pod-2
```

**Use cases:** StatefulSets, databases, Kafka, Cassandra, Elasticsearch.

### 13.6 Difference between port, targetPort and nodePort

```yaml
ports:
- port: 80
  targetPort: 8080
  nodePort: 30080
```

- **port** -> the port exposed by the Kubernetes Service.
- **targetPort** -> the port on which the container inside the pod is listening.
- **nodePort** -> the port opened on every Kubernetes node (used only with NodePort or LoadBalancer Services).

Flow:

```
Client
   |
NodeIP:30080 (nodePort)
   |
Service:80 (port)
   |
Pod:8080 (targetPort)
```

### 13.7 Follow-up: which Service type do you use in AKS?

> "For internal communication between microservices, I use ClusterIP because it keeps services accessible only within the cluster. For production applications that need internet access, I use LoadBalancer, which provisions an Azure Load Balancer automatically. I rarely use NodePort in production because it exposes ports directly on every node and is mainly useful for testing or when an external load balancer isn't available."

### 13.8 Quick comparison

| Service Type | Accessible From | Common Use |
|---|---|---|
| ClusterIP | Inside the cluster only | Internal microservices |
| NodePort | External via NodeIP:Port | Development and testing |
| LoadBalancer | Internet or internal cloud load balancer | Production applications |
| ExternalName | External DNS name | External databases or APIs |
| Headless | Direct pod IPs via DNS | StatefulSets and databases |

### 13.9 One-line interview summary

- **ClusterIP** -> internal communication within the cluster.
- **NodePort** -> exposes the application on a port of every node.
- **LoadBalancer** -> creates a cloud load balancer for external access.
- **ExternalName** -> maps a Service to an external DNS name.
- **Headless Service** -> no virtual IP; DNS returns individual pod IPs for direct access.

---

## 14. Terraform drift and anomaly

### 14.1 What is Terraform drift?

Terraform drift occurs when the actual infrastructure is different from what is stored in the Terraform state file because someone or something changed the infrastructure outside Terraform.

**Example**

Suppose Terraform creates an Azure VM with:

```
VM Size: Standard_B2s
Public IP: Enabled
```

Later, an administrator logs into the Azure Portal and changes the VM size to `Standard_D2s_v3`.

Now:

```
Terraform state  -> Standard_B2s
Actual Azure resource -> Standard_D2s_v3
```

This difference is called Terraform drift.

**How do you detect drift?**

```bash
terraform plan
```

Terraform compares:

- Configuration (`.tf` files)
- State file
- Actual cloud infrastructure

If differences exist, Terraform shows them in the plan.

**How do you fix drift?**

There are three options:

1. **Accept the manual change** - update the Terraform code to match the actual infrastructure.
2. **Revert the manual change** - run `terraform apply`. Terraform changes the infrastructure back to the desired state.
3. **Import unmanaged resources** - if a resource was created manually, run `terraform import` to add it to Terraform state.

**Best practices**

- Never make manual changes in production.
- Use Terraform as the single source of truth.
- Store the state remotely.
- Review `terraform plan` before every deployment.

### 14.2 What is Terraform anomaly?

Terraform does not have an official concept called "Terraform anomaly."

In interviews, "anomaly" usually means unexpected or abnormal behaviour during Terraform execution.

Examples include:

**State file corruption** - the state file becomes inconsistent or damaged.

**Partial deployment** - Terraform creates some resources but fails before completing all resources.

```
VM created
NSG created
Load Balancer creation failed
```

**State drift** - infrastructure changes outside Terraform.

**Dependency issues** - Terraform tries to create resources in the wrong order because dependencies are missing.

**Provider / API issues** - cloud provider returns errors such as rate limiting, timeout, authentication failure or network interruption.

**Real-world example**

Suppose Terraform creates:

```
Resource Group  ok
ACR             ok
Key Vault       ok
AKS             failed (Quota exceeded)
```

Now the deployment is incomplete. This is an anomalous situation because the infrastructure is only partially provisioned.

You would investigate using:

```bash
terraform plan
terraform state list
terraform state show <resource>
terraform refresh   # older versions
terraform apply
```

### 14.3 Interview summary (30-second answer)

> "Terraform drift occurs when the actual infrastructure differs from Terraform's state because of manual or external changes. We usually detect it using `terraform plan` and either update the code or run `terraform apply` to bring the infrastructure back to the desired state.
>
> Terraform anomaly is not an official Terraform term. It generally refers to unexpected situations such as state corruption, partial deployments, provider failures, dependency issues, or infrastructure inconsistencies that require investigation and correction."

---

## 15. Organizing a Terraform project for multiple environments

### 15.1 Modules

A module is a reusable collection of Terraform resources. Instead of writing the same code multiple times, we create modules and reuse them.

```
modules/
├── network/
├── aks/
├── acr/
├── keyvault/
└── monitoring/
```

Each module has:

```
main.tf
variables.tf
outputs.tf
```

Example root configuration:

```hcl
module "network" {
  source = "./modules/network"

  vnet_name = "prod-vnet"
}
```

**Benefits**

- Reusable code
- Easier maintenance
- Consistent deployments
- Smaller and cleaner root configuration

In production, modules are usually versioned using Git tags or a Terraform Registry, so teams can safely upgrade versions.

### 15.2 Environments

Different environments should have separate state files.

```
terraform/

modules/

envs/
├── dev/
│   ├── main.tf
│   ├── backend.tf
│   └── terraform.tfvars
│
├── staging/
│   ├── main.tf
│   ├── backend.tf
│   └── terraform.tfvars
│
└── prod/
    ├── main.tf
    ├── backend.tf
    └── terraform.tfvars
```

Each environment has its own backend, its own state and its own variables. This prevents accidental changes across environments.

### 15.3 Why not use Workspaces?

Terraform Workspaces let you manage multiple environments from the same configuration.

```bash
terraform workspace new dev
terraform workspace new prod
```

The active workspace is selected with:

```bash
terraform workspace select prod
```

Although convenient, many teams avoid workspaces for production because:

- It's easy to select the wrong workspace.
- All workspaces share the same backend configuration.
- Environment differences become hidden in code using `terraform.workspace`.
- Access control and permissions are harder to separate.

For production, separate directories and separate state files are usually safer and easier to manage.

### 15.4 Layer the state

Instead of storing everything in one state file, split infrastructure into layers.

```
State 1
Network
- Resource Group
- VNet
- Subnets

State 2
AKS
- Cluster
- Node Pools

State 3
Applications
- Helm Releases
- Kubernetes Resources

State 4
Monitoring
- Log Analytics
- Alerts
```

**Benefits:**

- Smaller blast radius if something goes wrong.
- Faster Terraform operations.
- Teams can work independently.
- Reduced merge conflicts.

### 15.5 Remote state

Each environment should have its own remote backend.

```
Development
dev.tfstate

Staging
staging.tfstate

Production
prod.tfstate
```

In Azure, these state files are typically stored in an Azure Storage Account with blob leases providing state locking.

### 15.6 CI/CD pipeline

Avoid running `terraform apply` directly from a developer's laptop.

Typical workflow:

```
Developer
      |
      v
Git Feature Branch
      |
      v
Pull Request
      |
      v
Pipeline
   |
   +-- terraform fmt
   +-- terraform validate
   +-- tflint
   +-- terraform plan
      |
Code Review
      |
Merge
      |
      v
Pipeline
      |
terraform apply
```

This ensures code is reviewed, plans are visible before deployment, and changes are applied consistently.

### 15.7 Additional best practices

- Use remote state with state locking.
- Keep root modules thin; put most logic into reusable modules.
- Pin provider and module versions to avoid unexpected upgrades.
- Run `terraform fmt`, `terraform validate`, and `tflint` in CI.
- Split infrastructure into multiple state files for better isolation.
- Use pull requests with `terraform plan`, and only run `terraform apply` after approval and merge.

### 15.8 Interview answer (1-2 minutes)

> "I organize Terraform using reusable modules for components like networking, AKS, ACR, and monitoring. The root configuration simply composes these modules and passes environment-specific variables. For environments such as development, staging, and production, I prefer separate directories with their own backend configuration, state file, and terraform.tfvars rather than relying on workspaces. This provides better isolation, clearer permissions, and reduces the risk of deploying to the wrong environment. I also split infrastructure into multiple state files, such as networking, AKS, and applications, to reduce the impact of changes and allow teams to work independently. Finally, all Terraform changes go through a CI/CD pipeline that runs terraform fmt, terraform validate, tflint, and terraform plan during pull requests, with terraform apply executed only after review and approval."

---

## 16. TFLint

### 16.1 What is TFLint?

TFLint is a static analysis and linting tool for Terraform. It analyzes Terraform code before deployment and identifies issues such as configuration mistakes, best practice violations, deprecated syntax, and cloud provider-specific problems.

It helps catch errors early, before you run `terraform apply`.

### 16.2 Why do we use TFLint?

Terraform itself checks syntax with:

```bash
terraform validate
```

But `terraform validate` does not detect many best practice issues.

TFLint provides additional checks, such as:

- Unused variables
- Unused data sources
- Invalid instance types (AWS) or SKUs (Azure)
- Deprecated arguments
- Naming convention issues
- Missing required tags (with custom rules)

### 16.3 Example

Suppose you write:

```hcl
resource "azurerm_linux_virtual_machine" "vm" {
  size = "Standard_XYZ"
}
```

`terraform validate` may pass because the syntax is correct.

When you run:

```bash
tflint
```

TFLint can detect that `Standard_XYZ` is not a valid Azure VM size (with the Azure plugin enabled).

### 16.4 Installation

```bash
brew install tflint      # macOS
```

or

```bash
choco install tflint     # Windows
```

### 16.5 Common commands

Initialize plugins:

```bash
tflint --init
```

Run lint checks:

```bash
tflint
```

Lint a specific directory:

```bash
tflint ./terraform
```

### 16.6 CI/CD pipeline integration

A typical pipeline includes:

```
Git Push
    |
    v
terraform fmt -check
    |
terraform validate
    |
tflint
    |
terraform plan
    |
Approval
    |
terraform apply
```

If TFLint finds issues, the pipeline fails, preventing low-quality Terraform code from being deployed.

### 16.7 terraform validate vs TFLint

| Feature | terraform validate | TFLint |
|---|---|---|
| Syntax validation | Yes | No |
| Checks resource configuration | Basic | Advanced |
| Finds best practice issues | No | Yes |
| Provider-specific validation | Limited | Yes |
| CI/CD integration | Yes | Yes |

### 16.8 Interview answer (30 seconds)

> "TFLint is a linting tool for Terraform that performs static analysis on Terraform code. While `terraform validate` checks syntax and configuration validity, TFLint goes further by identifying best practice violations, deprecated arguments, unused variables, and provider-specific configuration issues. We typically run TFLint in our CI/CD pipeline before `terraform plan` so that configuration problems are caught early and only high-quality Infrastructure as Code is deployed."

---

## 17. tfsec, Checkov, Trivy

These are all Infrastructure as Code (IaC) security scanning tools, but they have different purposes.

### 17.1 tfsec

tfsec scans Terraform code for security misconfigurations before deployment. It checks whether your infrastructure follows security best practices.

**Examples of issues it detects**

- Storage Account allows public access.
- Security Group exposes SSH (port 22) to the internet.
- Azure Key Vault has public network access enabled.
- Encryption is not enabled.
- Logging is disabled.

Run:

```bash
tfsec .
```

### 17.2 Checkov

Checkov is a policy-as-code security scanner developed by Bridgecrew (Palo Alto Networks). It scans multiple Infrastructure as Code frameworks, not just Terraform.

It supports:

- Terraform
- Kubernetes YAML
- Helm Charts
- CloudFormation
- ARM Templates
- Bicep
- Dockerfiles

**Example**

Suppose your AKS cluster doesn't have RBAC enabled or your Storage Account allows public access.

Running:

```bash
checkov -d .
```

reports these security issues before deployment.

**Why use it?**

- Broader support than tfsec.
- Large library of built-in security policies.
- Can enforce compliance standards like CIS benchmarks.

### 17.3 Trivy

Trivy is a vulnerability scanner developed by Aqua Security.

Unlike tfsec and Checkov, Trivy focuses on container images, filesystems, Kubernetes clusters, and also supports IaC scanning.

It checks:

- Docker images for known CVEs.
- Kubernetes manifests.
- Terraform files.
- Secrets accidentally committed to code.
- Open-source dependencies.

**Example**

Scan a Docker image:

```bash
trivy image myacr.azurecr.io/orders-api:v1
```

It reports vulnerabilities such as Critical, High, Medium and Low. This helps prevent deploying vulnerable images.

### 17.4 Comparison

| Tool | Primary Purpose | Supports |
|---|---|---|
| tfsec | Terraform security scanning | Terraform |
| Checkov | Multi-IaC security and compliance | Terraform, Kubernetes, Helm, CloudFormation, ARM, Bicep, Dockerfile |
| Trivy | Vulnerability scanning | Container images, filesystems, Kubernetes clusters, IaC, secrets, dependencies |

### 17.5 Interview answer

> "tfsec and Checkov are Infrastructure as Code security scanners that check Terraform code for misconfigurations before deployment, such as public storage accounts or open security groups. Checkov supports more frameworks than tfsec, including Kubernetes, Helm and Dockerfiles, and can enforce compliance standards like CIS. Trivy is different - it is mainly a vulnerability scanner for container images, and it also scans filesystems, Kubernetes clusters, IaC files and committed secrets. In a pipeline, I run tfsec or Checkov on the Terraform code and Trivy on the built Docker image before pushing it to ACR."

---

## 18. App Service vs App Service Plan vs Web App

This is one of the most common Azure interview questions. Many people confuse these three terms because they are closely related.

Think of it like an apartment building:

- **App Service Plan** = the building (CPU, RAM, OS, pricing tier)
- **Web App** = your apartment (your application)
- **App Service** = the overall Azure platform that hosts web applications, APIs, mobile backends, etc.

### 18.1 Azure App Service

App Service is Microsoft's PaaS (Platform as a Service) offering for hosting web applications. It provides everything required to run an application without managing servers.

It includes features like:

- Auto scaling
- Load balancing
- SSL certificates
- Deployment slots
- Authentication
- Custom domains
- Backup and restore
- Monitoring
- CI/CD integration

So App Service is the service itself.

Instead of creating VMs, installing IIS or Nginx, configuring networking, and maintaining the OS, Azure App Service handles all of that.

### 18.2 App Service Plan

The App Service Plan defines the infrastructure on which your applications run.

It decides:

- CPU
- RAM
- OS (Windows / Linux)
- Region
- Pricing tier
- Number of instances
- Scaling

Think of it as: *"How much hardware do I want?"*

Example:

```
App Service Plan

Premium V3
Linux
East US
4 CPUs
16 GB RAM
```

Every Web App inside this plan shares these resources.

**One App Service Plan can host multiple apps**

```
App Service Plan
Premium V3
Linux
4 CPU
16 GB RAM

        |
        +-- Web App A
        +-- Web App B
        +-- API App
        +-- Function App (Premium)
```

All these applications share the same compute resources.

### 18.3 Web App

A Web App is the actual application you deploy.

Examples:

- Company website
- React application
- Angular application
- ASP.NET application
- Node.js application
- Java application
- Python Flask application

When you open:

```
https://mycompany.azurewebsites.net
```

you're accessing a Web App.

### 18.4 Real-world example

Suppose your company has three applications: Customer Portal, Admin Portal and a REST API.

You create:

```
App Service Plan
Premium V3
8 GB RAM
Linux

        |
        +-- Customer Portal (Web App)
        +-- Admin Portal (Web App)
        +-- Orders API (Web App)
```

All three apps run on the same App Service Plan and share the same compute resources.

**If one app uses high CPU?**

```
Customer Portal
CPU = 90%
```

Since all apps share the same App Service Plan:

- Admin Portal performance may degrade.
- API performance may also degrade.

That's why production workloads often use separate App Service Plans for critical applications.

### 18.5 Common follow-up questions

**Can one App Service Plan have apps from different subscriptions?**

No. Apps in an App Service Plan must belong to the same subscription.

**Can multiple App Service Plans exist?**

Yes.

```
Development Plan
B1

Testing Plan
S1

Production Plan
Premium V3
```

Each plan has different resources and pricing.

**Can two Web Apps share one App Service Plan?**

Yes. Multiple Web Apps can share a single App Service Plan, and they share the underlying compute resources (CPU, memory, and storage). This is cost-effective, but heavy resource usage by one app can affect the others.

### 18.6 Scaling

**Scale Up** - increase VM size.

```
B1
 |
S1
 |
P1V3
 |
P2V3
```

More CPU and RAM.

**Scale Out** - increase the number of instances.

```
Instance 1
Instance 2
Instance 3
```

Azure's load balancer distributes traffic across them.

### 18.7 Quick comparison

| Feature | App Service | App Service Plan | Web App |
|---|---|---|---|
| What is it? | Azure hosting platform | Compute resources | Your application |
| Contains | Web Apps, API Apps, etc. | CPU, RAM, OS, pricing | Application code |
| Billing | Through the plan | Yes | No separate compute charge |
| Scaling | Supported | Defines scale | Uses the plan's resources |
| Multiple apps? | Yes | Yes | One application |

### 18.8 Easy way to remember

Imagine renting office space:

- **App Service** = the business park that provides facilities and management.
- **App Service Plan** = the office building you rent (size, capacity, cost).
- **Web App** = your company's office operating inside that building.

The building determines how much space and power you have, while your office is the actual business running inside it.

---

## 19. Dockerfile - COPY vs ADD, CMD vs ENTRYPOINT

These are two of the most frequently asked Docker interview questions.

### 19.1 COPY vs ADD

Both `COPY` and `ADD` copy files from the host machine into the Docker image. The difference is that `ADD` has extra features, while `COPY` simply copies files.

| Feature | COPY | ADD |
|---|---|---|
| Copy local files | Yes | Yes |
| Copy directories | Yes | Yes |
| Extract local tar files automatically | No | Yes |
| Download files from URL | No | Yes |
| Recommended for most cases | Yes | No |

**COPY**

Simply copies files or folders.

```dockerfile
COPY app.py /app/
```

Copies:

```
Host
 └── app.py

   |
   v

Container
 └── /app/app.py
```

Nothing else happens.

**ADD**

`ADD` can do everything `COPY` does, plus:

*1. Automatically extract tar files*

```dockerfile
ADD project.tar.gz /app/
```

Instead of copying the archive `project.tar.gz`, Docker extracts it automatically.

Result:

```
/app/
    src/
    config/
    images/
```

*2. Download from URL*

```dockerfile
ADD https://example.com/file.txt /tmp/
```

Docker downloads the file into the image. This is rarely recommended because it makes builds less predictable.

**Which one should you use?**

Use `COPY` by default.

Use `ADD` only when you specifically need:

- Automatic extraction of local tar archives.
- Its extra functionality (though downloading via `RUN curl` or `wget` is usually preferred for better control).

**Interview answer**

> "COPY simply copies files and directories into the image. ADD has additional features like automatically extracting local tar archives and supporting URL sources. In production, I prefer COPY because it is simpler, more predictable, and follows Docker best practices."

### 19.2 CMD vs ENTRYPOINT

This is about how a container starts.

**CMD**

CMD provides the default command.

```dockerfile
FROM ubuntu

CMD ["echo", "Hello World"]
```

Running:

```bash
docker run myimage
```

Output:

```
Hello World
```

You can override CMD:

```bash
docker run myimage ls
```

Output:

```
bin
etc
home
tmp
```

The `echo` command is replaced by `ls`.

**ENTRYPOINT**

ENTRYPOINT defines the main executable of the container.

```dockerfile
FROM ubuntu

ENTRYPOINT ["echo"]
```

Run:

```bash
docker run myimage Hello
```

Output:

```
Hello
```

Docker appends the supplied arguments to the ENTRYPOINT command.

Trying:

```bash
docker run myimage ls
```

produces:

```
ls
```

because Docker runs `echo ls`.

**CMD + ENTRYPOINT together**

This is the most common pattern.

```dockerfile
FROM ubuntu

ENTRYPOINT ["echo"]

CMD ["Hello"]
```

Run:

```bash
docker run myimage
```

Output:

```
Hello
```

Run:

```bash
docker run myimage Docker
```

Output:

```
Docker
```

Docker executes `ENTRYPOINT + CMD`, or, if arguments are provided, `ENTRYPOINT + user arguments`.

**Real production example**

```dockerfile
FROM eclipse-temurin:21

COPY app.jar app.jar

ENTRYPOINT ["java", "-jar", "app.jar"]
```

Run:

```bash
docker run myapp
```

Docker executes:

```
java -jar app.jar
```

If you need to pass JVM arguments:

```bash
docker run myapp --spring.profiles.active=prod
```

Docker executes:

```
java -jar app.jar --spring.profiles.active=prod
```

**When to use which?**

Use CMD when:

- You want to provide a default command.
- Users should be able to replace it easily.

```dockerfile
CMD ["python", "app.py"]
```

Use ENTRYPOINT when:

- The container should always run a specific application.
- Users may pass additional arguments to that application.

```dockerfile
ENTRYPOINT ["nginx", "-g", "daemon off;"]
```

**Quick comparison**

| Feature | CMD | ENTRYPOINT |
|---|---|---|
| Purpose | Default command | Main executable |
| Can be overridden by `docker run` arguments? | Yes | No (unless `--entrypoint` is used) |
| Receives runtime arguments | No - replaced by them | Yes - appends them |
| Typical use | Default behaviour | Fixed application startup |

### 19.3 Interview answer

> "**COPY vs ADD:** COPY only copies files and directories and is the preferred choice for most Dockerfiles because it's simple and predictable. ADD provides extra features like extracting local tar archives automatically and supporting URL sources, so I use it only when those features are required.
>
> **CMD vs ENTRYPOINT:** CMD defines the default command that can be overridden when starting the container. ENTRYPOINT defines the container's main executable and is intended to always run. A common production pattern is to use ENTRYPOINT for the application (for example, `java -jar app.jar`) and CMD to provide default arguments that users can override."

---

## 20. Jenkins pipeline for AKS - basic and enterprise version

### 20.1 Basic pipeline

```groovy
pipeline {
  agent { label 'docker-azure' }

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  environment {
    ACR_NAME = '<acr-name>'
    REGISTRY = '<acr-name>.azurecr.io'
    IMAGE_NAME = 'orders-api'
    IMAGE_TAG = "${BUILD_NUMBER}"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Test') {
      steps {
        sh 'mvn -B clean verify'
      }
    }

    stage('Build Image') {
      steps {
        sh 'docker build -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG .'
      }
    }

    stage('Push Image') {
      steps {
        sh 'az acr login --name $ACR_NAME'
        sh 'docker push $REGISTRY/$IMAGE_NAME:$IMAGE_TAG'
      }
    }

    stage('Deploy Development') {
      steps {
        sh '''
          az aks get-credentials \
            --resource-group <development-resource-group> \
            --name <development-aks-name> \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace development \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=$IMAGE_TAG \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace development
        '''
      }
    }

    stage('Approve Production') {
      input {
        message 'Deploy this tested image to Production?'
        ok 'Deploy'
        submitter 'production-approvers'
      }
      steps {
        echo 'Production deployment approved'
      }
    }

    stage('Deploy Production') {
      steps {
        sh '''
          az aks get-credentials \
            --resource-group <production-resource-group> \
            --name <production-aks-name> \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace production \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=$IMAGE_TAG \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace production
        '''
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'target/surefire-reports/*.xml'
    }
  }
}
```

### 20.2 How to explain it in an interview

Explain it stage by stage instead of reading the code line by line.

**Agent**

```groovy
agent { label 'docker-azure' }
```

- The pipeline runs on a Jenkins agent named `docker-azure`.
- This agent should have Docker, Azure CLI, Helm, kubectl, and Maven installed.

**Options**

- `disableConcurrentBuilds()` prevents multiple builds of the same job from running simultaneously.
- `timestamps()` adds timestamps to Jenkins logs for easier troubleshooting.

**Environment variables**

These variables are reused throughout the pipeline.

```
ACR Name = myacr
Registry = myacr.azurecr.io
Image    = orders-api
Tag      = Jenkins Build Number (for example, 105)
```

Final Docker image:

```
myacr.azurecr.io/orders-api:105
```

**Checkout stage** - Jenkins pulls the latest application source code from the Git repository configured for the job.

**Test stage** - `mvn -B clean verify` cleans previous builds, compiles the application and runs unit tests. If any test fails, the pipeline stops here.

**Build Docker image**

```bash
docker build -t myacr.azurecr.io/orders-api:105 .
```

**Push image to ACR** - login to Azure Container Registry, then push the Docker image. The image `myacr.azurecr.io/orders-api:105` is now stored in ACR.

**Deploy to Development AKS** - `az aks get-credentials` downloads the Kubernetes credentials so Jenkins can access the Development AKS cluster. `helm upgrade --install` deploys or upgrades the application using the Helm chart. `kubectl rollout status` waits until the deployment completes successfully.

**Manual approval** - the pipeline pauses. Only users in the `production-approvers` group can approve. This is a common production safety check.

**Deploy to Production** - exactly the same process as Development, except it connects to the Production AKS cluster, deploys to the production namespace, and uses the same Docker image that was tested in Development. This ensures the exact tested artifact is promoted to Production.

**Post section** - `junit` publishes JUnit test reports in Jenkins. Even if the build fails, Jenkins still displays the test results.

**Overall flow**

```
Developer
      |
      v
Git Repository
      |
      v
Jenkins Checkout
      |
      v
Maven Build & Unit Tests
      |
      v
Docker Build
      |
      v
Push Image to Azure Container Registry (ACR)
      |
      v
Deploy to Development AKS (Helm)
      |
      v
Verify Rollout
      |
      v
Manual Approval
      |
      v
Deploy to Production AKS (Helm)
      |
      v
Verify Rollout
      |
      v
Publish Test Reports
```

**Interview explanation (1-minute answer)**

> "This is a Jenkins Declarative Pipeline that automates the complete CI/CD process. It first checks out the code from Git, builds and tests the application using Maven, then creates a Docker image and pushes it to Azure Container Registry. Next, it deploys the image to the Development AKS cluster using Helm and verifies the rollout. After successful testing, the pipeline pauses for manual approval before promoting the same Docker image to the Production AKS cluster. Finally, it publishes the JUnit test reports. Using the same image for both environments ensures consistency and avoids environment-specific build differences."

### 20.3 What the basic pipeline is missing

For a production-grade DevOps pipeline, the basic pipeline is missing a few important stages:

1. Checkout
2. Dependency download / cache (optional)
3. Compile
4. Unit tests
5. **SonarQube static code analysis**
6. **Quality gate validation**
7. Package application
8. **Dependency vulnerability scan** (OWASP Dependency Check or Snyk)
9. Build Docker image
10. **Docker image vulnerability scan** (Trivy / Grype)
11. Push image to Azure Container Registry
12. Deploy to Development
13. **Smoke tests / API health check**
14. Manual approval
15. Deploy to Production
16. Rollout verification
17. **Post-deployment smoke test**
18. Publish test reports
19. **Notifications** (Email / Slack / Teams)

This is the typical enterprise CI/CD flow.

### 20.4 Enterprise Jenkins pipeline (with SonarQube and quality gates)

```groovy
pipeline {
    agent { label 'docker-azure' }

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    tools {
        maven 'Maven3'
    }

    environment {
        ACR_NAME = '<acr-name>'
        REGISTRY = '<acr-name>.azurecr.io'
        IMAGE_NAME = 'orders-api'
        IMAGE_TAG = "${BUILD_NUMBER}"

        SONARQUBE_SERVER = 'SonarQube'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Compile') {
            steps {
                sh 'mvn clean compile'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'mvn test'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh '''
                    mvn sonar:sonar \
                      -Dsonar.projectKey=orders-api \
                      -Dsonar.projectName=orders-api
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Package') {
            steps {
                sh 'mvn package -DskipTests'
            }
        }

        stage('Dependency Vulnerability Scan') {
            steps {
                sh '''
                mvn org.owasp:dependency-check-maven:check
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                docker build \
                -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG .
                '''
            }
        }

        stage('Docker Image Scan') {
            steps {
                sh '''
                trivy image \
                --exit-code 1 \
                --severity HIGH,CRITICAL \
                $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
        }

        stage('Push to ACR') {
            steps {
                sh '''
                az acr login --name $ACR_NAME

                docker push \
                $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
        }

        stage('Deploy Development') {
            steps {
                sh '''
                az aks get-credentials \
                --resource-group <dev-rg> \
                --name <dev-aks> \
                --overwrite-existing

                helm upgrade --install orders-api ./helm/orders-api \
                --namespace development \
                --create-namespace \
                --set image.repository=$REGISTRY/$IMAGE_NAME \
                --set image.tag=$IMAGE_TAG \
                --wait
                '''
            }
        }

        stage('Verify Rollout') {
            steps {
                sh '''
                kubectl rollout status deployment/orders-api \
                -n development
                '''
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                curl -f http://orders-api-dev/actuator/health
                '''
            }
        }

        stage('Production Approval') {
            input {
                message 'Deploy to Production?'
                ok 'Deploy'
                submitter 'production-approvers'
            }
            steps {
                echo "Approved"
            }
        }

        stage('Deploy Production') {
            steps {
                sh '''
                az aks get-credentials \
                --resource-group <prod-rg> \
                --name <prod-aks> \
                --overwrite-existing

                helm upgrade --install orders-api ./helm/orders-api \
                --namespace production \
                --create-namespace \
                --set image.repository=$REGISTRY/$IMAGE_NAME \
                --set image.tag=$IMAGE_TAG \
                --wait
                '''
            }
        }

        stage('Verify Production Rollout') {
            steps {
                sh '''
                kubectl rollout status deployment/orders-api \
                -n production
                '''
            }
        }

        stage('Production Smoke Test') {
            steps {
                sh '''
                curl -f https://orders.company.com/actuator/health
                '''
            }
        }

    }

    post {

        always {
            junit 'target/surefire-reports/*.xml'
        }

        success {
            echo 'Deployment Successful'
        }

        failure {
            echo 'Deployment Failed'
        }
    }
}
```

### 20.5 Additional enterprise improvements

If you're targeting senior DevOps or Azure DevOps interviews, you can also mention these practices:

- **Secrets management:** retrieve credentials from Azure Key Vault instead of hardcoding them.
- **Branch strategy:** deploy to production only from the main branch, with feature branches deploying to development or test environments.
- **Image tagging:** tag images with both the build number and the Git commit SHA (for example, `105` and `a1b2c3d`) to improve traceability.
- **Artifact repository:** publish JAR/WAR artifacts to repositories like Nexus or Artifactory before building container images.
- **GitOps deployment:** instead of Jenkins running `helm upgrade` directly, update the Helm values in a GitOps repository and let tools like Argo CD or Flux CD synchronize the changes to AKS.
- **Security scanning:** add secret scanning (Gitleaks), container configuration scanning (Trivy), and Infrastructure-as-Code scanning (Checkov or tfsec) as part of the pipeline.
- **Notifications:** send build and deployment status to Microsoft Teams, Slack, or email.
- **Progressive delivery:** use blue-green or canary deployments for production releases to minimize risk.

This version is much closer to what you'll see in enterprise environments and is suitable for discussing in DevOps interviews.

---

## 21. Teams bots, Adaptive Cards and dashboard visualization

A cluster of related concepts that shows up in "build a status dashboard/bot" style questions: chat apps, micro frontends, the Teams Bot Framework, Adaptive Cards, and the difference between D3.js and Highcharts for the visualization layer.

**Chat apps** - applications where users communicate through messages, such as Microsoft Teams, Slack, or an internal chat application. In a DevOps context, they're commonly used as the front door for ChatOps - checking deployment status, triggering pipelines, or getting alerts without leaving the chat tool.

**Micro frontends** - a way to split a large frontend application into smaller, independently developed and deployed frontend applications, each typically owned by a different team.

```
Employee Portal
 ├── Profile
 ├── Payroll
 ├── Leave Management
 └── Reports
```

Different teams can own and deploy each section independently instead of shipping one large frontend as a single unit.

**Teams Bot Framework** - used to build bots that users interact with directly inside Microsoft Teams.

```
User: Check production deployment
Bot:  Production deployment is successful.
      Version: v2.4.1
      Status: Running
```

**Adaptive Cards** - JSON-based UI cards used by Teams bots to display structured information and interactive buttons inside a Teams conversation, instead of plain text.

```
Production Deployment
Status: Successful
Version: v2.4.1
Environment: Production
[View Logs] [Rollback]
```

**D3.js vs Highcharts** - both are JavaScript charting libraries, but they solve different problems:

| Library | Strength |
| --- | --- |
| D3.js | More flexible and customizable - you build the visualization from primitives (SVG, scales, axes) |
| Highcharts | Easier for standard business charts (bar, line, pie) with less code and built-in interactivity |

D3.js is the right choice when a dashboard needs a custom or unusual visualization; Highcharts is the right choice when the requirement is common business charts delivered quickly.

**Azure Web Apps** - Azure App Service Web Apps, used to host web applications and APIs without managing the underlying VMs directly. Supports .NET, Node.js, Python, Java, and PHP.

**Putting it together** - a Teams-integrated deployment-status dashboard could look like:

```
User
  |
  v
Microsoft Teams
  |
  v
Teams Bot
  |
  v
Python API
  |
  v
Azure Web App / Database / APIs
  |
  v
Data
  |
  v
D3.js / Highcharts
  |
  v
Web Dashboard
```

The bot handles the conversational interface and Adaptive Cards inside Teams, a Python API on Azure App Service does the backend work (querying deployment/pipeline state), and a web dashboard renders the same data visually using D3.js or Highcharts depending on how custom the charts need to be.
