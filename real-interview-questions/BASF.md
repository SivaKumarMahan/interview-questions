# BASF - Interview Questions

<details><summary>Q1. What are REST APIs, and how do we use them?</summary>

A REST API is a way for two applications to communicate with each other over HTTP or HTTPS.

In simple words, imagine you want to get information from Azure DevOps without opening the Azure DevOps portal. You can use a REST API to request that information programmatically.

For example, as a DevOps engineer, you can use REST APIs to:

- Retrieve Azure DevOps pipeline details.
- Trigger a pipeline automatically.
- Check a pipeline's execution status.
- Create work items in Azure Boards.
- Retrieve information about Azure resources.

### 1. How does a REST API work?

```
Client (Python script / Shell script / Postman)
        |
        |  HTTP request: GET, POST, PUT, PATCH or DELETE
        v
REST API endpoint
        |  Authenticates the request and processes it
        v
Application / Service
        |  Returns requested information or confirms an action
        v
HTTP response + JSON data
```

For example, you send a request to Azure DevOps asking for the latest pipeline runs. The API returns the results, usually in JSON format.

### 2. Important HTTP methods

| Method | Purpose | Example |
| --- | --- | --- |
| GET | Read information | Get pipeline status |
| POST | Create something or trigger an action | Trigger a pipeline |
| PUT | Replace or update a resource | Replace a resource representation |
| PATCH | Partially update a resource | Update a work item field |
| DELETE | Delete a resource | Delete a supported resource |

Remember: the API documentation defines which methods and operations are supported for each endpoint.

### 3. Practical example: Azure DevOps REST API

Suppose your interviewer asks:

> "How do you trigger an Azure DevOps pipeline using a REST API?"

You can use the Azure DevOps Pipelines Runs API.

**Step 1: Prepare the API URL**

```
POST https://dev.azure.com/ORGANIZATION/PROJECT/_apis/pipelines/PIPELINE_ID/runs?api-version=7.1
```

Replace:

- `ORGANIZATION` with your Azure DevOps organization.
- `PROJECT` with your project name.
- `PIPELINE_ID` with your pipeline ID.

**Step 2: Send the request using curl**

```bash
curl -X POST \
  "https://dev.azure.com/ORG/PROJECT/_apis/pipelines/12/runs?api-version=7.1" \
  -u ":$AZDO_PAT" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Here:

- `-X POST` sends a POST request.
- `-u ":$AZDO_PAT"` supplies a Personal Access Token (PAT) for authentication.
- `-H` sets the request content type.
- `-d '{}'` sends an empty JSON request body to run the pipeline with its default configuration.

The token must have the required pipeline permissions. For real projects, prefer Microsoft Entra ID-based authentication where supported, or use a securely stored, least-privilege token. Never hardcode credentials in scripts or commit them to Git.

Official reference: [Azure DevOps - Run Pipeline REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/run-pipeline).

### 4. How do you call a REST API from a shell script?

For example, to retrieve information from a public API:

```bash
#!/bin/bash

API_URL="https://jsonplaceholder.typicode.com/posts/1"

curl -s "$API_URL"
```

This sends a GET request and prints the JSON response.

Example output:

```json
{
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat",
  "body": "quia et suscipit..."
}
```

You can use `jq` to extract a specific field:

```bash
curl -s "$API_URL" | jq -r '.title'
```

This prints only the title from the JSON response.

### 5. Where do DevOps engineers use REST APIs?

- **Azure DevOps:** Trigger pipelines, check build status, and manage work items.
- **Azure Resource Manager:** Create, update, or retrieve Azure resources through supported APIs.
- **GitHub:** Retrieve repository information and trigger supported workflow operations.
- **Monitoring tools:** Retrieve alerts, metrics, or incident information.
- **Automation scripts:** Connect multiple systems and automate repetitive tasks.

### 6. Common interview follow-up questions

**Q: How do you test a REST API?**

I use Postman or curl to send requests. I verify the HTTP status code, response body, authentication, headers, and error messages.

**Q: What are common HTTP status codes?**

| Code | Meaning |
| --- | --- |
| 200 | Request successful |
| 201 | Resource created |
| 400 | Bad request |
| 401 | Authentication required or invalid |
| 403 | Access denied |
| 404 | Resource not found |
| 429 | Too many requests |
| 500 | Internal server error |

**Q: What is JSON?**

JSON is a common data format used to send and receive structured information through REST APIs. It contains key-value pairs and can represent objects and arrays.

### Interview-ready answer

> "REST APIs allow different applications and services to communicate over HTTP or HTTPS. They use methods such as GET, POST, PUT, PATCH, and DELETE to retrieve or modify resources. In my DevOps work, I can use REST APIs with curl or Python to trigger Azure DevOps pipelines, retrieve their status, and automate deployment activities. I handle authentication securely, process JSON responses, and check HTTP status codes to verify whether the request succeeded."

</details>

<details><summary>Q2. What are the types of Azure Repos in Azure DevOps?</summary>

In Azure DevOps, there are two types of version control repositories:

1. Git repositories
2. TFVC (Team Foundation Version Control)

### 1. Git Repository

Git is a distributed version control system. Every developer can have a local copy of the repository and its history.

**Features:**

- Supports branches and pull requests.
- Supports merging and code reviews.
- Integrates with CI/CD pipelines.
- Commonly used for modern DevOps projects.

**Example:** In my project, developers push code to Azure Repos Git, create pull requests, and trigger Azure Pipelines to build and deploy applications to AKS.

```bash
git clone https://dev.azure.com/ORG/PROJECT/_git/MYREPO
git checkout -b feature/login
git add .
git commit -m "Added login feature"
git push origin feature/login
```

### 2. TFVC Repository

TFVC stands for Team Foundation Version Control. It is a centralized version control system where the server maintains the version history.

**Features:**

- Centralized source control.
- Supports check-in and check-out workflows.
- Supports file locking to prevent conflicting edits.
- Often found in older or legacy projects.

### Difference between Git and TFVC

| Feature | Git | TFVC |
| --- | --- | --- |
| Type | Distributed | Centralized |
| Local repository | Full repository history | Typically workspace-based |
| Branching | Lightweight and commonly used | Supported, but generally more centralized |
| Offline work | Extensive support | More limited |
| Pull requests | Supported in Azure Repos | Not supported in the same Git pull-request workflow |
| Common usage | Modern DevOps projects | Legacy projects |

### Interview-ready answer

> "Azure Repos supports two types of version control: Git and TFVC. Git is distributed and supports branching, pull requests, and modern CI/CD workflows. TFVC is centralized and is commonly used in legacy projects. In my DevOps projects, I generally use Git repositories to manage source code and integrate them with Azure Pipelines for automated builds and deployments."

</details>

<details><summary>Q3. What is the use of Azure Boards?</summary>

Azure Boards is a work management tool in Azure DevOps used to plan, track, and manage project tasks, bugs, and user stories.

In simple words, it helps the team know what work needs to be done, who is responsible for it, and what the current status is.

### 1. Main features of Azure Boards

| Feature | Use |
| --- | --- |
| Work Items | Track tasks, bugs, user stories, and features. |
| Backlogs | Maintain and prioritize upcoming work. |
| Boards | Track work through stages such as To Do, In Progress, and Done. |
| Sprints | Plan work for a specific period in Agile development. |
| Queries | Filter and find work items based on assigned user, status, priority, etc. |
| Dashboards and reports | Monitor progress and team performance. |

### 2. Real-time DevOps example

Suppose your team is deploying a Java Spring Boot application to AKS.

| Work item type | Example |
| --- | --- |
| User Story | Deploy the application to AKS using CI/CD. |
| Task | Create the Azure DevOps YAML pipeline. |
| Bug | Fix the `ImagePullBackOff` issue in AKS. |

The team assigns these work items to engineers and tracks their progress on the board:

```
To Do → In Progress → Done
```

This helps the DevOps team coordinate deployments, track issues, and deliver work within sprint timelines.

### 3. How does Azure Boards integrate with CI/CD?

Azure Boards can be linked with Azure Repos and Azure Pipelines.

For example:

1. A developer creates a user story or task in Azure Boards.
2. The developer links the work item to a Git commit or pull request.
3. The code change triggers an Azure Pipeline.
4. The team tracks the related development work and deployment progress.

This improves traceability between requirements, code changes, and builds or releases. Linking work items does not automatically mean a deployment is successful; pipeline status and deployment results must also be checked.

### Interview-ready answer

> "Azure Boards is used to manage and track project work in Azure DevOps. We use it to create user stories, tasks, bugs, and features, plan sprints, assign work to team members, and track progress. In my DevOps project, I can use Azure Boards to track pipeline development tasks, AKS deployment activities, and production issues. It also integrates with Azure Repos and Azure Pipelines, helping us maintain traceability throughout the development lifecycle."

</details>

<details><summary>Q4. What are the differences between application-side and network-side shell scripting?</summary>

In DevOps, shell scripting is used on both the application side and the network side, but the purpose is different.

- **Application-side scripting:** Checks and manages application processes, logs, deployments, and performance.
- **Network-side scripting:** Checks connectivity, DNS resolution, ports, routes, and network availability.

### 1. Key differences

| Area | Application-side scripting | Network-side scripting |
| --- | --- | --- |
| Main purpose | Ensure the application is running correctly | Ensure network connectivity is working |
| What we check | Processes, logs, CPU, memory, application health | IP addresses, DNS, ports, routes, connectivity |
| Common commands | `ps`, `grep`, `tail`, `curl`, `systemctl` | `ping`, `curl`, `nc`, `dig`, `ip route` |
| Common issues | Application crash, memory leak, service failure | DNS failure, blocked port, routing issue |
| Example | Restart a failed Nginx service | Check whether a server's port 443 is reachable |

### 2. Application-side shell scripting example

**Scenario:** You want to check whether Nginx is running and restart it if it is stopped.

```bash
#!/bin/bash

SERVICE="nginx"

if systemctl is-active --quiet "$SERVICE"; then
    echo "$SERVICE is running"
else
    echo "$SERVICE is stopped. Restarting..."
    sudo systemctl restart "$SERVICE"
fi
```

What this script does:

- Checks whether Nginx is active.
- If it is running, prints a success message.
- If it is stopped, attempts to restart the service.

**Real-time use:** You can use similar checks in server-maintenance scripts or monitoring automation.

**Note:** This checks the service status, not whether the application is actually serving requests successfully. An HTTP health check is useful for that.

### 3. Network-side shell scripting example

**Scenario:** You want to check whether an application server is reachable on HTTPS port 443.

```bash
#!/bin/bash

HOST="myapp.example.com"
PORT=443

if nc -z -w 3 "$HOST" "$PORT"; then
    echo "Network connection successful"
else
    echo "Cannot connect to $HOST on port $PORT"
fi
```

What this script does:

- Attempts to connect to the specified host on port 443.
- Waits up to three seconds.
- Reports whether the TCP connection succeeded.

**Real-time use:** This helps investigate firewall rules, security groups/NSGs, routing, and service availability. A successful TCP connection does not necessarily mean the HTTPS application is healthy.

### 4. How to troubleshoot in a real-time scenario

Suppose your application is not accessible.

```
User cannot access application
        |
        v
Step 1: Network check  -->  Step 2: Application check  -->  Step 3: Check logs
```

**Step 1: Network check.** Check DNS resolution and TCP connectivity.

```bash
nslookup myapp.example.com
nc -zv myapp.example.com 443
```

**Step 2: Application check.** Check whether the service is running and returning an HTTP response.

```bash
systemctl status nginx
curl -I http://localhost
```

**Step 3: Check logs.** Identify application or web-server errors.

```bash
sudo journalctl -u nginx --since "10 minutes ago"
sudo tail -n 100 /var/log/nginx/error.log
```

### Interview-ready answer

> "Application-side shell scripting is used to automate application health checks, service restarts, log analysis, deployments, and resource monitoring. Network-side shell scripting is used to automate DNS checks, port connectivity, routing checks, and server reachability. For example, I use `systemctl` and `curl` to check application health, while I use `nslookup`, `nc`, and `ip route` to troubleshoot network connectivity. In real-time incidents, I check both sides to identify whether the problem is caused by the application or the network."

</details>

<details><summary>Q5. How do you do rollback in your project?</summary>

For a DevOps interview, you can explain rollback based on your Azure DevOps CI/CD pipeline and AKS deployments.

### 1. How do you perform rollback in your project?

**Interview-ready answer:**

> "In my project, we use Azure DevOps pipelines to deploy applications to AKS using Docker images and Helm charts. If a new deployment causes issues in production, such as application errors, failed health checks, or increased error rates, I first identify the problematic release. Then I roll back to the last known stable version, verify the application health, and monitor the logs to ensure the issue is resolved.
>
> We also maintain versioned Docker images and Helm releases so we can restore the previous application version quickly."

### 2. Rollback process in AKS using Helm

```
1. New version deployed   -->  Application v2.0
2. Issue detected         -->  Pods failing, errors, or health checks failing
3. Roll back              -->  Restore the last known good Helm release
4. Verify                 -->  Pods, endpoints, logs, and application health
```

**Step 1: Check Helm release history**

```bash
helm history myapp -n prod
```

Example:

```
REVISION  STATUS       DESCRIPTION
1         superseded   Install complete
2         superseded   Upgrade complete
3         deployed     Upgrade complete
```

Suppose revision 3 introduced the issue and revision 2 was stable.

**Step 2: Roll back to the previous stable version**

```bash
helm rollback myapp 2 -n prod
```

This tells Helm to create a new release revision using the configuration and resources from revision 2.

**Step 3: Verify the rollback**

```bash
kubectl rollout status deployment/myapp -n prod
kubectl get pods -n prod
kubectl get events -n prod --sort-by=.metadata.creationTimestamp
kubectl logs deployment/myapp -n prod --tail=100
```

Also verify the application's health endpoint and monitor error rates.

### 3. What if you use kubectl instead of Helm?

If the deployment is managed directly by Kubernetes, you can use:

```bash
kubectl rollout history deployment/myapp -n prod
kubectl rollout undo deployment/myapp -n prod
kubectl rollout status deployment/myapp -n prod
```

This rolls back the Deployment's pod template to a previous revision. If Helm manages the application, prefer `helm rollback` so the release history and Helm-managed resources remain consistent.

### 4. How do you roll back through Azure DevOps?

In my CI/CD pipeline, I would:

1. Detect the failure through deployment checks, monitoring, or smoke tests.
2. Stop further promotion to production.
3. Run a rollback stage that uses the previous stable Helm release revision.
4. Verify pod readiness, service connectivity, and application health.
5. Notify the team and investigate the root cause.

For example, a rollback stage might execute:

```bash
helm rollback myapp 2 -n prod --wait --timeout 5m
```

The revision should be selected from verified release history, not hardcoded blindly in a reusable production pipeline.

### 5. Important interview follow-up: What about database changes?

Application rollback does not automatically reverse database schema or data changes. I use backward-compatible database migrations whenever possible, and plan a separate recovery strategy for destructive schema or data changes.

### Strong closing statement for the interview

> "My preferred rollback approach in AKS is Helm rollback because we maintain release history. I roll back to the last known stable revision, validate pod and application health, and monitor the service. I also ensure database changes are backward-compatible because rolling back the application alone may not restore the database."

</details>

<details><summary>Q6. What is the deployment strategy you follow?</summary>

For your Azure DevOps and AKS project, you can explain that you follow a Rolling Deployment strategy by default, with approvals and validation before production deployment. The strategy can vary depending on the application's availability and risk requirements.

### 1. Interview-ready answer

> "In my project, we use Azure DevOps CI/CD pipelines to deploy containerized applications to AKS using Helm charts.
>
> We follow a rolling deployment strategy for regular releases. Kubernetes gradually replaces old pods with new pods while keeping the application available. We configure readiness and liveness probes, resource requests and limits, and deployment parameters to ensure a safe rollout.
>
> Our pipeline includes build, testing, SonarQube analysis, Docker image creation, Trivy vulnerability scanning, pushing the image to Azure Container Registry, and deployment to the required environment.
>
> We deploy to lower environments first, validate the application, and use approval gates before production. After production deployment, we check pod status, application health, logs, and monitoring alerts. If the new release causes issues, we roll back to the last stable Helm revision."

### 2. Deployment strategies you should know

| Strategy | How it works | Best for |
| --- | --- | --- |
| Rolling deployment | Gradually replaces old pods with new pods. | Regular AKS releases with minimal downtime. |
| Blue-Green deployment | Runs two environments. After validating the new environment, traffic switches from the old environment to the new one. | Fast traffic switching and easier application rollback, when both environments are ready. |
| Canary deployment | Releases the new version to a small portion of traffic first, then increases traffic if the release is healthy. | High-risk changes where you want to limit initial user impact. |

### 3. How do you implement rolling deployment in AKS?

In your Kubernetes Deployment YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myregistry.azurecr.io/myapp:v2
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
```

What do these settings mean?

- `replicas: 3`: runs three pod replicas.
- `maxSurge: 1`: allows one extra pod above the desired replica count during the rollout.
- `maxUnavailable: 0`: Kubernetes should not intentionally reduce the number of available replicas below the desired count during the rollout.
- `readinessProbe`: helps prevent traffic from being sent to a pod until it is ready.

These settings support availability, but they don't guarantee zero downtime by themselves. The application, health probes, capacity, and traffic routing must also be configured correctly.

To monitor the deployment:

```bash
kubectl rollout status deployment/myapp -n prod
kubectl get pods -n prod
```

To undo a problematic rollout:

```bash
kubectl rollout undo deployment/myapp -n prod
```

If Helm manages the release, use the appropriate `helm rollback` command instead.

### 4. What if the interviewer asks, "Why not Blue-Green?"

You can answer:

> "Rolling deployment is suitable for our regular releases because it gradually replaces pods without requiring two complete application environments. For a high-risk release where we need to validate the new version before sending production traffic, I would consider Blue-Green or Canary deployment. The choice depends on application criticality, infrastructure cost, and rollback requirements."

</details>

<details><summary>Q7. What do CI and CD represent? What is the difference between Continuous Delivery and Continuous Deployment?</summary>

### 1. What do CI and CD represent?

**CI = Continuous Integration**

Developers frequently merge code changes into a shared repository. Every change can automatically trigger a pipeline to build the application and run tests to detect issues early.

**CD = Continuous Delivery or Continuous Deployment**

Both automate the process of getting tested code ready for release or deployed to production, but there is one important difference.

### 2. Difference between Continuous Delivery and Continuous Deployment

| Feature | Continuous Delivery | Continuous Deployment |
| --- | --- | --- |
| Build and testing | Automated | Automated |
| Deployment to lower environments | Automated | Automated |
| Production deployment | Requires manual approval or a release decision | Automatically happens after all required checks pass |
| Human intervention | Before production release | Not required for routine production releases |
| Main goal | Keep code ready for production | Automatically release every qualifying change to production |

**Example using Azure DevOps**

```
Continuous Delivery:
Code --> Build --> Test --> Stage --> Manual production approval --> Deploy to Production

Continuous Deployment:
Code --> Build --> Test --> Stage --> Automatic production deployment (after all required checks pass)
```

### 3. Real-time DevOps example

Suppose you are deploying a Java Spring Boot application to AKS using Azure DevOps.

Your pipeline stages are:

1. Developer pushes code to Azure Repos.
2. Pipeline builds the application using Maven.
3. SonarQube checks code quality.
4. Docker image is built and scanned using Trivy.
5. Image is pushed to Azure Container Registry (ACR).
6. Application is deployed to Dev and QA.
7. Production release follows one of these approaches:
   - **Continuous Delivery:** Wait for the required production approval, then deploy.
   - **Continuous Deployment:** Automatically deploy after all required tests and checks pass, without a routine manual release approval.

### 4. Interview-ready answer

> "CI stands for Continuous Integration, where developers frequently merge code and automated pipelines build and test the changes. CD can mean Continuous Delivery or Continuous Deployment. In Continuous Delivery, the application is always ready for production, but production deployment requires a manual release decision or approval. In Continuous Deployment, every change that passes the required automated checks is deployed to production automatically."

**Easy way to remember:**

- **Continuous Delivery:** Ready for production; approval before release.
- **Continuous Deployment:** Automatically released to production after passing checks.

</details>
