# Deloitte LLP - Interview Questions (Part 2)

## Q1. Users suddenly get 502/504 errors even though all Pods show `1/1 Running`. How do you troubleshoot?

This is a classic Kubernetes troubleshooting scenario. The important point is:

Pods being `Running` and `1/1 Ready` does not mean the application is actually reachable end-to-end.

### Traffic flow

```
Internet
   |
   v
Azure Application Gateway
   |
   v
AKS Ingress
   |
   v
Kubernetes Service
   |
   v
Pods
   |
   v
Azure Database for PostgreSQL
```

If users suddenly get 502/504, I troubleshoot from the outside toward the backend, rather than assuming the Pods are the problem.

### What 502/504 usually means

**502 Bad Gateway**

Usually means a proxy/gateway received an invalid response or could not properly communicate with its backend.

**504 Gateway Timeout**

Usually means the gateway/proxy waited for the backend but didn't receive a response within the timeout.

So the problem could be anywhere between:

```
Application Gateway
        |
        v
     Ingress
        |
        v
     Service
        |
        v
       Pod
        |
        v
   Application
        |
        v
    PostgreSQL
```

### Step 1: Check Application Gateway

First check Azure Application Gateway health/backend pool.

Look for:

- Backend marked unhealthy
- Health probe failures
- Incorrect backend port
- HTTP/HTTPS mismatch
- TLS/certificate issues
- NSG/firewall problems
- Application Gateway timeout

If Application Gateway considers the AKS ingress backend unhealthy, users can get 502/504 even though Pods are perfectly healthy.

### Step 2: Check Ingress

```bash
kubectl get ingress -A
kubectl describe ingress payment-ingress
```

Check:

- Backend service name
- Backend service port
- Host/path rules
- TLS configuration
- Ingress controller events

Then check the ingress controller:

```bash
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx <ingress-pod>
```

Look for:

- `upstream timed out`
- `connection refused`
- `no live upstreams`
- `502`
- `504`

These messages are very useful.

### Step 3: Check the Service

```bash
kubectl get svc
kubectl describe svc payment-api
```

Then check endpoints:

```bash
kubectl get endpoints payment-api
```

or:

```bash
kubectl get endpointslices
```

This is critical.

You could have:

```
Pods:       1/1 Running
Service:    0 endpoints
```

In that situation, the Pods are running but the Service has nothing to send traffic to.

Check whether Service selectors match Pod labels.

For example:

```yaml
selector:
  app: payment-api
```

Pods should have:

```yaml
labels:
  app: payment-api
```

### Step 4: Test the Service directly

Don't immediately blame the ingress.

Run:

```bash
kubectl run test-pod --rm -it \
  --image=curlimages/curl -- sh
```

From inside the cluster:

```bash
curl http://payment-api:<port>
```

If this fails, the problem is probably between Service → Pod → Application.

If this works, move further outward and investigate the Ingress/Application Gateway.

### Step 5: Check the application inside the Pod

The Pod being `1/1 Running` only tells you that the container is running and the readiness probe is currently passing.

Check application logs:

```bash
kubectl logs payment-api-7d8f9c4d-x1a2
```

Look for:

- Database connection timeout
- Connection refused
- Too many connections
- Connection pool exhausted
- Application timeout
- OutOfMemory

### Step 6: Check PostgreSQL

Since the architecture includes Azure Database for PostgreSQL, test whether the application can reach it.

Check:

- PostgreSQL availability
- Connection limits
- CPU/memory
- Network connectivity
- Firewall rules
- Private Endpoint/DNS if applicable
- Connection pool exhaustion

For example, the application could be running:

```
Pod: Running
Readiness: Passing
Application: Running
Database connection: Broken
```

The application may then take too long to process requests, eventually causing a `504 Gateway Timeout`.

### Most important clue

If you see:

```
payment-api-7d8f9c4d-x1a2    1/1 Running
```

repeated across all Pods, that alone does not prove the application is healthy.

I would check this next:

```bash
kubectl get svc payment-api
kubectl get endpoints payment-api
kubectl describe ingress payment-ingress
kubectl logs -n ingress-nginx <ingress-controller-pod>
```

### Interview answer

> "I wouldn't assume the Pods are the issue just because they are Running and Ready. I would troubleshoot the request path from Application Gateway to Ingress, Service, Pods and finally PostgreSQL. First I would check Application Gateway backend health and probe failures. Then I would check Ingress configuration and controller logs for upstream timeout or connection-refused errors. Next I would verify that the Service has endpoints and that its selector matches the Pod labels. I would test the Service directly from inside the cluster. Finally, I would check application logs and PostgreSQL connectivity, connection limits and timeouts. A 502 generally points to a bad backend response or connectivity issue, while a 504 commonly indicates a backend timeout."

The key troubleshooting command here is `kubectl get endpoints payment-api`. A Pod can be Running while the Service has no usable endpoints.

---

## Q2. Write an Azure DevOps YAML pipeline for this application stack

**Application stack:**

1. React
2. Spring Boot
3. AKS
4. ACR

**Task:** Write Azure DevOps YAML.

**Expected (as given):**

```yaml
trigger:
- main

stages:
- Build
- Test
- SonarQube
- DockerBuild
- TrivyScan
- PushACR
- DeployDev
- Approval
- DeployProd
```

One correction to the expected answer: Azure DevOps stages need proper YAML objects. You cannot simply write `- Build`, `- Test`, etc. Each stage needs a `stage:` property.

### Full pipeline

```yaml
trigger:
  - main

variables:
  acrName: 'myacr'
  imageName: 'payment-api'
  imageTag: '$(Build.BuildId)'
  aksDev: 'aks-dev'
  aksProd: 'aks-prod'
  namespace: 'payment'

stages:

# --------------------------------------------------
# 1. BUILD
# --------------------------------------------------
- stage: Build
  displayName: Build React and Spring Boot
  jobs:
  - job: Build
    steps:

    # React
    - task: NodeTool@0
      inputs:
        versionSpec: '18.x'

    - script: |
        cd frontend
        npm install
        npm run build
      displayName: Build React Application

    # Spring Boot
    - task: JavaToolInstaller@0
      inputs:
        versionSpec: '17'
        jdkArchitectureOption: 'x64'
        jdkSourceOption: 'PreInstalled'

    - script: |
        cd backend
        ./mvnw clean package -DskipTests
      displayName: Build Spring Boot Application


# --------------------------------------------------
# 2. TEST
# --------------------------------------------------
- stage: Test
  displayName: Run Tests
  dependsOn: Build
  jobs:
  - job: Test
    steps:

    - script: |
        cd backend
        ./mvnw test
      displayName: Run Spring Boot Tests

    - script: |
        cd frontend
        npm test -- --watchAll=false
      displayName: Run React Tests


# --------------------------------------------------
# 3. SONARQUBE
# --------------------------------------------------
- stage: SonarQube
  displayName: SonarQube Analysis
  dependsOn: Test
  jobs:
  - job: SonarQube
    steps:

    - task: SonarQubePrepare@7
      inputs:
        SonarQube: 'SonarQube-Service-Connection'
        scannerMode: 'cli'
        configMode: 'manual'
        cliProjectKey: 'payment-api'
        cliProjectName: 'payment-api'

    - script: |
        cd backend
        ./mvnw verify sonar:sonar
      displayName: Run SonarQube Scan

    - task: SonarQubePublish@7
      inputs:
        pollingTimeoutSec: '300'


# --------------------------------------------------
# 4. DOCKER BUILD
# --------------------------------------------------
- stage: DockerBuild
  displayName: Build Docker Image
  dependsOn: SonarQube
  jobs:
  - job: DockerBuild
    steps:

    - task: Docker@2
      displayName: Build Docker Image
      inputs:
        command: build
        repository: $(imageName)
        Dockerfile: 'backend/Dockerfile'
        tags: |
          $(imageTag)


# --------------------------------------------------
# 5. TRIVY SCAN
# --------------------------------------------------
- stage: TrivyScan
  displayName: Scan Docker Image
  dependsOn: DockerBuild
  jobs:
  - job: Trivy
    steps:

    - script: |
        trivy image \
          --severity HIGH,CRITICAL \
          --exit-code 1 \
          $(imageName):$(imageTag)
      displayName: Trivy Security Scan


# --------------------------------------------------
# 6. PUSH IMAGE TO ACR
# --------------------------------------------------
- stage: PushACR
  displayName: Push Image to ACR
  dependsOn: TrivyScan
  jobs:
  - job: Push
    steps:

    - task: Docker@2
      displayName: Login and Push to ACR
      inputs:
        command: buildAndPush
        repository: $(imageName)
        dockerfile: 'backend/Dockerfile'
        containerRegistry: 'ACR-Service-Connection'
        tags: |
          $(imageTag)


# --------------------------------------------------
# 7. DEPLOY TO DEV
# --------------------------------------------------
- stage: DeployDev
  displayName: Deploy to Development
  dependsOn: PushACR
  jobs:
  - deployment: DeployDev
    environment: 'Dev'
    strategy:
      runOnce:
        deploy:
          steps:

          - task: KubernetesManifest@1
            displayName: Deploy to AKS Dev
            inputs:
              action: deploy
              kubernetesServiceConnection: 'AKS-Dev-Service-Connection'
              namespace: $(namespace)
              manifests: |
                k8s/deployment.yaml
                k8s/service.yaml
              containers: |
                $(acrName).azurecr.io/$(imageName):$(imageTag)


# --------------------------------------------------
# 8. APPROVAL
# --------------------------------------------------
- stage: Approval
  displayName: Production Approval
  dependsOn: DeployDev
  jobs:
  - job: Approval
    pool: server
    steps:
    - task: ManualValidation@1
      inputs:
        notifyUsers: |
          devops-team@company.com
        instructions: |
          Please validate the Dev deployment.
          Approve to continue deployment to Production.
        onTimeout: 'reject'


# --------------------------------------------------
# 9. DEPLOY TO PROD
# --------------------------------------------------
- stage: DeployProd
  displayName: Deploy to Production
  dependsOn: Approval
  condition: succeeded()
  jobs:
  - deployment: DeployProd
    environment: 'Production'
    strategy:
      runOnce:
        deploy:
          steps:

          - task: KubernetesManifest@1
            displayName: Deploy to AKS Production
            inputs:
              action: deploy
              kubernetesServiceConnection: 'AKS-Prod-Service-Connection'
              namespace: $(namespace)
              manifests: |
                k8s/deployment.yaml
                k8s/service.yaml
              containers: |
                $(acrName).azurecr.io/$(imageName):$(imageTag)
```

### Simple flow

```
Developer
    |
    v
Git Push -> main
    |
    v
Build
 |-- React build
 |-- Spring Boot build
    |
    v
Test
 |-- React tests
 |-- Spring Boot tests
    |
    v
SonarQube
    |
    v
Docker Build
    |
    v
Trivy Security Scan
    |
    v
Push Docker Image
    |
    v
Azure Container Registry
    |
    v
Deploy to AKS Dev
    |
    v
Manual Approval
    |
    v
Deploy to AKS Production
```

### What each stage does

| Stage | Purpose |
|---|---|
| Build | Builds React and Spring Boot |
| Test | Runs application/unit tests |
| SonarQube | Checks code quality and vulnerabilities |
| DockerBuild | Creates the Spring Boot Docker image |
| TrivyScan | Scans the image for HIGH/CRITICAL vulnerabilities |
| PushACR | Pushes the image to Azure Container Registry |
| DeployDev | Deploys the image to AKS Dev |
| Approval | Waits for manual approval |
| DeployProd | Deploys the same validated image to AKS Prod |

### Important interview point

Don't say:

> "I build another Docker image for production."

That's bad practice.

Build once, scan once, push one immutable image, and promote the same image tag from Dev to Prod.

For example:

```
payment-api:125
       |
       v
     ACR
       |
       +----> AKS Dev
       |
       +----> AKS Prod
```

That gives you confidence that the exact artifact tested in Dev is the artifact deployed to Production.

---

## Q3. Identify every security problem in this pipeline snippet

**Given:**

```yaml
env:
  - name: DB_PASSWORD
    value: "MyProductionPassword123"

variables:
  azureSubscription: "prod-subscription"
```

There are several security problems here. The biggest one is the database password is hardcoded in plain text.

### Security issues

| # | Problem | Why it is dangerous | Better approach |
|---|---|---|---|
| 1 | Hardcoded DB password | Anyone with access to the YAML/repository can see it | Azure Key Vault / Kubernetes Secret |
| 2 | Production credential in source control | Git history can retain the password even after deleting it | Store secrets outside Git |
| 3 | Password passed as an environment variable | Environment variables can potentially be exposed through debugging, logs, process inspection, or application dumps | Use a secret mechanism such as Key Vault or Kubernetes Secrets |
| 4 | Password is not marked secret | Azure DevOps treats normal variables differently from secret variables | Use secret variables or, preferably, Key Vault |
| 5 | No secret rotation mechanism | Hardcoded credentials tend to remain unchanged for long periods | Use managed identity/Key Vault rotation |
| 6 | Production subscription identifier exposed | Not a password, but unnecessarily exposing environment/infrastructure information can help attackers | Use a properly secured service connection |
| 7 | Potential privilege issue with service connection | If `azureSubscription` has excessive permissions, compromise of the pipeline can become an Azure compromise | Apply least privilege/RBAC |
| 8 | No separation of application and deployment secrets | Application credentials and Azure authentication are being handled as ordinary configuration | Use Key Vault + service connections/managed identities |

### Best solution

For an Azure + AKS environment, I would avoid putting the password in YAML completely.

A better architecture is:

```
Azure DevOps Pipeline
        |
        | Managed Identity / Service Connection
        v
   Azure Key Vault
        |
        | DB password
        v
       AKS
        |
        v
   Spring Boot
        |
        v
Azure PostgreSQL
```

For example, Azure DevOps can retrieve the secret from Key Vault:

```yaml
- task: AzureKeyVault@2
  inputs:
    azureSubscription: 'prod-subscription'
    KeyVaultName: 'prod-keyvault'
    SecretsFilter: 'DB-PASSWORD'
```

Then the pipeline uses the secret without putting the actual password into the YAML.

For AKS, an even better production design is to use Azure Key Vault + Secrets Store CSI Driver / Workload Identity, so the application can retrieve the secret without storing the actual password in the Git repository or pipeline YAML.

### One important correction

`azureSubscription: "prod-subscription"` is not itself a secret. The security problem isn't that the subscription name appears in YAML.

The real concern is what service connection it refers to and what permissions that identity has.

### Interview answer

> "The primary security issue is the hardcoded production database password. It can be exposed through source control and Git history. I would move it to Azure Key Vault and access it using a secured Azure DevOps service connection or managed identity. I would also ensure the service connection follows least-privilege RBAC. I would avoid passing production credentials as normal environment variables and implement secret rotation. The subscription name itself isn't a secret, but the identity behind the service connection must be properly secured."

---

## Q4. A Pod is stuck in `CrashLoopBackOff` after a new deployment — how do you troubleshoot and fix it?

**Scenario:** A web application named `employee-portal` is deployed in the Kubernetes namespace `test`. It runs as a single Pod (`Deployment` name `employee-portal`, container port `8080`, expected replicas `1`).

After a new deployment, the application is not accessible. Running:

```bash
kubectl get pods -n test
```

shows:

```
NAME                                 READY   STATUS             RESTARTS   AGE
employee-portal-6d8f7c9b5-x4k2m      0/1     CrashLoopBackOff   4          5m
```

**As a DevOps engineer, explain:**

1. The commands you would use to check the Pod details and logs.
2. The information you would look for in the logs and Pod events.
3. The action you would take after identifying the problem.
4. How you would verify that the Pod and application are working after the fix.

For a `CrashLoopBackOff`, I would troubleshoot from Pod status → logs → events → root cause → fix → verification.

### 1. Check Pod details and logs

First, confirm the Pod status and identify why the container is restarting:

```bash
kubectl get pods -n test

kubectl describe pod employee-portal-6d8f7c9b5-x4k2m -n test

kubectl logs employee-portal-6d8f7c9b5-x4k2m -n test

kubectl logs employee-portal-6d8f7c9b5-x4k2m -n test --previous
```

`--previous` is important for `CrashLoopBackOff` because it shows logs from the previous crashed container.

### 2. Check logs and Pod events

In the logs, I would look for:

- Application startup errors
- Configuration or environment-variable issues
- Missing secrets/configuration
- Database connection failures
- Port/configuration errors
- Permission errors
- Application exceptions
- Out-of-memory errors

From `describe`, I would check the Events section for:

- `Failed`
- `BackOff`
- `OOMKilled`
- `FailedMount`
- `Unhealthy`
- Liveness probe failed
- Readiness probe failed

I would also check the container's exit code and termination reason.

```bash
kubectl get pod employee-portal-6d8f7c9b5-x4k2m -n test \
  -o jsonpath='{.status.containerStatuses[*].state.terminated}'
```

### 3. Fix the identified problem

The fix depends on the root cause.

For example:

- Wrong environment variable → Correct the Deployment/ConfigMap/Secret.
- Missing Secret → Create/fix the Secret reference.
- Application startup failure → Fix the application configuration/code and build a new image.
- OOMKilled → Review memory usage and adjust requests/limits if appropriate.
- Liveness probe failure → Correct the probe configuration or application health endpoint.
- Wrong image → Update the image to the correct version.

Then redeploy:

```bash
kubectl apply -f deployment.yaml -n test
```

Or, if only the image needs updating:

```bash
kubectl set image deployment/employee-portal \
  employee-portal=<new-image>:<tag> -n test
```

### 4. Verify the fix

Watch the rollout:

```bash
kubectl rollout status deployment/employee-portal -n test
```

Check the Pod:

```bash
kubectl get pods -n test
```

Expected:

```
READY   STATUS
1/1     Running
```

Check logs again:

```bash
kubectl logs deployment/employee-portal -n test
```

Then verify the Service and endpoints:

```bash
kubectl get svc -n test
kubectl get endpoints -n test
```

If the application is exposed through an Ingress, also check:

```bash
kubectl get ingress -n test
```

### Interview answer

> "I would first run `kubectl describe pod` and `kubectl logs --previous` because the Pod is in CrashLoopBackOff. I would check the container exit reason, application errors, configuration, secrets, probes, resource limits, and Pod events. Once I identify the root cause, I would fix the Deployment, ConfigMap, Secret, image, probe, or application as appropriate. Then I would monitor `kubectl rollout status`, confirm the Pod is 1/1 Running, check the logs, and finally verify the Service/Ingress and application connectivity."

---

## Q5. Write a prompt to ask an AI assistant to analyze a failing Jenkins Maven build

**Scenario (Prompt Writing exercise):** A Jenkins pipeline that builds a Java application is failing during the Maven build stage. The source code has been downloaded successfully, but the build stops because of compilation errors.

**Task:** As a DevOps engineer, write the prompt you would give an AI assistant to analyze the build failure and suggest solutions. The prompt should be clear and provide enough information for the AI to generate a useful response.

### Prompt

```
Analyze the following Jenkins Maven build failure. Identify the root cause of
the compilation errors, explain the errors clearly, and suggest specific fixes.
Consider possible issues with Java version, Maven dependencies, source code, or
build configuration. Provide the recommended solution and relevant Maven
commands to verify the fix.

Build stage: Maven
Build result: Compilation failed
Source code checkout: Successful
Error logs: [Paste the complete Maven compilation error logs here]
```

### Why this prompt works

- **States the context** — Jenkins, Maven, Java, and confirms checkout succeeded so the AI doesn't waste time suggesting checkout/source-control fixes.
- **Narrows the failure type** — explicitly says "compilation errors," not a generic "build failed," so the AI focuses on the right category of causes.
- **Lists likely root-cause categories** — Java version, dependencies, source code, build configuration — which steers the AI toward a structured diagnosis instead of a generic guess.
- **Asks for actionable output** — not just an explanation, but a specific fix plus Maven commands to verify it (e.g. `mvn -v`, `mvn dependency:tree`, `mvn clean compile`).
- **Leaves a placeholder for the actual logs** — the real error text is what the AI needs most; the prompt is built to be pasted along with it.

---

## Q6. What is NGINX?

Nginx is a high-performance web server and reverse proxy. In DevOps, it is commonly used to receive client requests and forward them to backend applications.

### Simple example

```
User
  |
  v
Nginx
  |
  +------> React frontend
  |
  +------> Spring Boot backend
```

The user sends a request to your application. Nginx receives it and decides where to send that request.

### What is Nginx used for?

**1. Web server**

It can serve static files such as:

- HTML
- CSS
- JavaScript
- Images

For example, a React production build can be served by Nginx.

**2. Reverse proxy**

Nginx can forward requests to backend applications:

```
Client
  |
  v
Nginx :80
  |
  v
Spring Boot :8080
```

For example:

```
/api/users  -> Spring Boot
/api/orders -> Spring Boot
```

**3. Load balancing**

Nginx can distribute requests across multiple backend servers:

```
             Nginx
            /  |  \
           /   |   \
       Pod-1 Pod-2 Pod-3
```

This improves availability and distributes traffic.

**4. SSL/TLS termination**

Nginx can handle HTTPS:

```
Client
  |
 HTTPS
  |
  v
Nginx
  |
 HTTP
  |
  v
Application
```

The client communicates securely with Nginx, while Nginx forwards the request to the backend.

**5. Routing**

Nginx can route requests based on URL, hostname, etc.

Example:

```
example.com/api -> Spring Boot
example.com/     -> React
```

### Nginx in Kubernetes

In Kubernetes, you commonly see Nginx as an Ingress Controller:

```
Internet
   |
   v
Azure Application Gateway
   |
   v
Nginx Ingress Controller
   |
   +------> payment-service
   |
   +------> order-service
   |
   +------> user-service
```

The Ingress Controller reads Kubernetes Ingress rules and routes traffic to the appropriate Services.

### Interview answer

> "Nginx is a lightweight, high-performance web server and reverse proxy. In DevOps, I mainly use it for serving static content, reverse proxying requests to backend applications, load balancing, SSL termination, and HTTP routing. In Kubernetes, Nginx can also be used as an Ingress Controller to route external traffic to different Kubernetes Services."

---

## Q7. How do you secure secrets in container images?

The key rule is: never put secrets inside the Docker image.

### Don't hardcode secrets in the Dockerfile

Avoid:

```dockerfile
ENV DB_PASSWORD=MyPassword123
```

Also avoid:

```dockerfile
COPY .env /app/.env
```

### Don't pass secrets during docker build

Avoid:

```bash
docker build --build-arg DB_PASSWORD=MyPassword123 .
```

Build arguments can potentially become visible in image history or build metadata.

### Inject secrets at runtime

The image should contain only the application.

```
Docker Image
    |
    | no passwords
    v
Container
    |
    +---- DB username/password injected at runtime
```

### Use a secret manager

In Azure, I would typically use Azure Key Vault.

```
Azure DevOps
     |
     v
Azure Key Vault
     |
     v
    AKS
     |
     v
Application Pod
     |
     v
PostgreSQL
```

**For AKS, use Workload Identity + Key Vault**

The Pod gets an Azure identity through Microsoft Entra Workload ID, and the application retrieves the required secret from Key Vault.

This is better than putting the secret directly in:

```yaml
env:
  - name: DB_PASSWORD
    value: "password123"
```

### If Kubernetes Secrets are used, protect them properly

Kubernetes Secrets are better than plain-text environment variables, but they are not automatically equivalent to a full secret-management solution. Enable encryption at rest and restrict RBAC access.

### Scan images and repositories

I would use tools such as Trivy, GitLeaks, or similar scanners to detect accidentally committed credentials.

### Rotate compromised secrets

If a password is accidentally committed or baked into an image, don't just delete the line. Rotate/revoke the credential, rebuild the image, and remove the compromised credential from wherever it was exposed.

### Interview answer

> "I never store secrets inside a container image. I keep the Docker image immutable and free of credentials, and inject secrets at runtime. In Azure and AKS, I prefer Azure Key Vault with Workload Identity and the Secrets Store CSI Driver. I also avoid Docker build arguments for sensitive values, scan the repository and images for leaked secrets, apply least-privilege RBAC, and rotate any credential that gets exposed."

---

## Q8. How do you manage credentials in Azure DevOps?

I keep credentials out of YAML entirely and rely on Azure DevOps's built-in secret handling.

### 1. Secret pipeline variables

```yaml
variables:
  - name: dbPassword
    value: $(DB_PASSWORD)
```

`DB_PASSWORD` is defined in the pipeline UI (or a variable group) and marked as **secret**. Azure DevOps automatically masks it in logs, and it can't be viewed again once saved — only replaced.

### 2. Variable groups linked to Azure Key Vault

Instead of storing secrets directly in Azure DevOps, I link a variable group to an Azure Key Vault:

```
Azure DevOps Library
      |
      v
Variable Group (linked to Key Vault)
      |
      v
   Azure Key Vault
      |
      +--> DB-PASSWORD
      +--> API-KEY
```

The pipeline references the variable group, and the actual secret value never has to be typed into Azure DevOps directly — it's fetched from Key Vault at run time.

```yaml
variables:
- group: 'prod-secrets'   # linked to Key Vault

steps:
- script: echo "Using secret without printing it"
  env:
    DB_PASSWORD: $(DB-PASSWORD)
```

### 3. Service connections instead of hardcoded credentials

For connecting to Azure, ACR, AKS, etc., I use a **service connection** (ideally backed by a managed identity or workload identity federation) rather than a stored username/password.

```yaml
- task: AzureCLI@2
  inputs:
    azureSubscription: 'Prod-Service-Connection'
    scriptType: bash
    inlineScript: |
      az account show
```

### 4. Secure files

For things like a `kubeconfig` or a certificate, I use the **Secure Files** library instead of committing them to the repo.

### What I avoid

- Printing secret variables with `echo $(secretVar)` — Azure DevOps masks known secret variables in logs, but it's still a bad habit and can leak through unusual formatting.
- Storing secrets as plain (non-secret) variables.
- Granting a service connection more permissions (RBAC) than the pipeline actually needs.

### Interview answer

> "I avoid putting credentials directly in YAML. For simple cases, I use secret pipeline variables, which Azure DevOps masks in logs. For shared or production secrets, I use variable groups linked to Azure Key Vault, so the actual value is fetched at runtime rather than stored in Azure DevOps. For connecting to Azure resources, I use service connections backed by managed identity or workload identity instead of stored credentials, and I make sure those connections follow least-privilege RBAC. Certificates or config files are handled through the Secure Files library rather than being committed to the repository."

---

## Q9. Explain in detail how Trivy is used to scan container images

For a DevOps interview, you should understand what Trivy scans, where it runs in the pipeline, what the output means, and what happens when vulnerabilities are found.

### 1. What is Trivy?

Trivy is an open-source security scanner commonly used in CI/CD pipelines.

It can scan:

- Container images
- Filesystems
- Git repositories
- Kubernetes configurations
- Infrastructure-as-Code files
- Dependencies
- Secrets and misconfigurations

For container images, the main purpose is to identify known vulnerabilities in OS packages and application dependencies.

For example, your image may be:

```
payment-api:v25
       |
       +-- Ubuntu/Debian packages
       +-- Java runtime
       +-- Spring Boot dependencies
       +-- Application libraries
```

Trivy examines these components and compares vulnerable package versions against vulnerability databases.

### 2. Where does Trivy fit in CI/CD?

For your Azure DevOps pipeline, I would use:

```
Developer
    |
    v
Git
    |
    v
Build
    |
    v
Unit Tests
    |
    v
SonarQube
    |
    v
Docker Build
    |
    v
Trivy Image Scan
    |
    +---- Vulnerability found ---> Pipeline FAIL
    |
    v
Push to ACR
    |
    v
Deploy to AKS
```

The important point is: scan the image before pushing/deploying it.

### 3. Build the Docker image

Suppose your Dockerfile is:

```dockerfile
FROM eclipse-temurin:17-jre

WORKDIR /app

COPY target/payment-api.jar app.jar

CMD ["java", "-jar", "app.jar"]
```

Build the image:

```bash
docker build -t payment-api:25 .
```

Now you have `payment-api:25`.

### 4. Run a basic Trivy scan

```bash
trivy image payment-api:25
```

Trivy analyzes the image and reports something like:

```
payment-api:25

Total: 15 vulnerabilities

+------------+----------+----------------+--------------+
| Library    | Severity | Installed Ver. | Fixed Ver.   |
+------------+----------+----------------+--------------+
| libssl     | HIGH     | 3.0.x          | 3.0.x        |
| curl       | MEDIUM   | 7.x            | 7.x          |
| openssl    | CRITICAL | 3.0.x          | 3.0.x        |
+------------+----------+----------------+--------------+
```

The exact output depends on the image and current vulnerability database.

### 5. Scan only HIGH and CRITICAL

In CI/CD, you normally don't want every low-severity issue to immediately stop the pipeline.

```bash
trivy image \
  --severity HIGH,CRITICAL \
  payment-api:25
```

This tells Trivy: show me HIGH and CRITICAL vulnerabilities.

### 6. Make the pipeline fail

This is one of the most important options for interviews.

```bash
trivy image \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  payment-api:25
```

`--exit-code 1` means: if vulnerabilities matching the selected severity are found, return exit code 1.

So the pipeline behaves like:

```
Trivy Scan
    |
    +---- No HIGH/CRITICAL
    |          |
    |          v
    |       Continue
    |
    +---- HIGH/CRITICAL found
               |
               v
          Exit code 1
               |
               v
          Pipeline fails
```

### 7. Why is exit-code important?

Consider:

```bash
trivy image --severity HIGH,CRITICAL payment-api:25
```

Trivy may print:

```
3 HIGH
1 CRITICAL
```

But the pipeline might continue unless you configure the command to fail based on the findings. That's why `--exit-code 1` is useful.

### 8. Example Azure DevOps stage

```yaml
- stage: TrivyScan
  displayName: Trivy Security Scan
  dependsOn: DockerBuild

  jobs:
  - job: Scan

    steps:
    - script: |
        trivy image \
          --severity HIGH,CRITICAL \
          --exit-code 1 \
          $(imageName):$(imageTag)
      displayName: Scan Docker Image
```

If Trivy finds HIGH or CRITICAL vulnerabilities, the stage fails.

### 9. Installing Trivy in Azure DevOps

One simple approach is to install it in the pipeline:

```yaml
- script: |
    sudo apt-get update
    sudo apt-get install -y wget

    wget -qO- https://aquasecurity.github.io/trivy-repo/deb/public.key \
      | gpg --dearmor \
      | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null

    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] \
      https://aquasecurity.github.io/trivy-repo/deb \
      generic main" \
      | sudo tee /etc/apt/sources.list.d/trivy.list

    sudo apt-get update
    sudo apt-get install -y trivy

    trivy --version
  displayName: Install Trivy
```

In a production environment, you can also use a prebuilt agent/container image containing Trivy instead of installing it on every run.

### 10. Scanning the image before ACR push

Suppose your pipeline does:

```
Docker Build
     |
     v
payment-api:125
     |
     v
Trivy
     |
     +---- FAIL
     |
     +---- PASS
            |
            v
           ACR
```

```bash
docker build -t payment-api:125 .

trivy image \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  payment-api:125
```

If successful:

```bash
docker tag payment-api:125 myacr.azurecr.io/payment-api:125
docker push myacr.azurecr.io/payment-api:125
```

This prevents vulnerable images from reaching ACR.

### 11. Can Trivy scan an image already in ACR?

Yes. You can authenticate to ACR and scan the image:

```bash
trivy image myacr.azurecr.io/payment-api:125
```

For example, ACR could hold `payment-api:123`, `payment-api:124`, `payment-api:125`.

However, I generally prefer:

```
Build -> Scan -> Push -> Deploy
```

rather than:

```
Build -> Push -> Scan -> Deploy
```

because you don't want to push an image that has already failed your security gate.

### 12. Trivy and application dependencies

Trivy isn't limited to OS packages. Depending on the image and ecosystem, it can detect vulnerabilities in application dependencies too.

For example, your Spring Boot application might contain Spring Framework, Jackson, Logback, Netty, Tomcat, and other Maven dependencies — a vulnerable dependency could be detected there as well.

So your image could have an OS vulnerability, a Java dependency vulnerability, and an application/library vulnerability simultaneously. This is why container scanning is useful even when the application itself builds successfully.

### 13. Trivy severity levels

The common severity levels are: `UNKNOWN`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

A typical company policy might be:

| Severity | Action |
|---|---|
| CRITICAL | Block deployment |
| HIGH | Block deployment |
| MEDIUM | Report / review |
| LOW | Monitor |

But this should be based on your organization's security policy. Don't blindly say "every vulnerability must fail the pipeline" — that can create unnecessary pipeline failures, especially when there is no available fix or the vulnerability isn't exploitable in your application's context.

### 14. What if a vulnerability has no fix?

Trivy may show something like:

```
Installed Version: 1.2.3
Fixed Version:     Not Available
```

That means there is currently no known fixed package version available in the vulnerability data. You shouldn't simply ignore it — you should investigate:

- Is the vulnerable package actually used?
- Is the vulnerable functionality reachable?
- Is there a newer base image?
- Can the dependency be upgraded?
- Is the package required?
- Is there a vendor mitigation?
- Does your security policy allow a documented exception?

### 15. Use an allowlist carefully

Sometimes organizations need to accept a known vulnerability temporarily. Trivy supports ignore files, e.g. `.trivyignore`, which can contain vulnerability IDs that have been reviewed and approved.

Bad practice — an undocumented `.trivyignore`:

```
CVE-xxxxx
CVE-yyyyy
CVE-zzzzz
```

A proper exception should have: vulnerability, reason, risk assessment, owner, approval, and an expiration/review date.

### 16. Generate a report

You can produce machine-readable output:

```bash
trivy image \
  --format json \
  --output trivy-report.json \
  payment-api:25
```

You can also generate other formats depending on your reporting requirements. This is useful for feeding console output, a JSON report, and a security dashboard.

### 17. Trivy can also scan for secrets

```bash
trivy fs .
```

This can scan the filesystem, and Trivy can identify potential secrets depending on the configured scanners. But I would not rely only on Trivy for secret detection — tools such as GitLeaks are also commonly used.

### 18. Trivy vs SonarQube

This is a common interview question. They solve different problems.

| Tool | Main purpose |
|---|---|
| SonarQube | Source-code quality and code-level security analysis |
| Trivy | Container/image vulnerabilities, dependencies, misconfigurations, secrets |
| Checkov | IaC security |
| GitLeaks | Secret detection |
| OWASP Dependency-Check | Dependency vulnerability scanning |

Your pipeline could therefore be:

```
Code
 |
 +--> SonarQube
 |
 +--> Tests
 |
 v
Docker Build
 |
 v
Trivy
 |
 v
ACR
 |
 v
AKS
```

### 19. Complete example for a React + Spring Boot application

For an application with React, Spring Boot, AKS, and ACR, I would structure the security part like this:

```
             Git
              |
              v
        Build React
              |
              v
      Build Spring Boot
              |
              v
            Tests
              |
              v
          SonarQube
              |
              v
         Docker Build
              |
              v
       Trivy Image Scan
              |
       +------+------+
       |             |
     FAIL           PASS
       |             |
   Stop pipeline     v
                    ACR
                     |
                     v
                    AKS
```

### 20. Strong interview answer

If the interviewer asks "How do you use Trivy to scan container images?", say:

> "After building the Docker image, I run Trivy against the local image before pushing it to ACR. I normally configure the scan to check HIGH and CRITICAL vulnerabilities and use `--exit-code 1` so the pipeline fails if those vulnerabilities are detected. I also generate a report for security tracking. If vulnerabilities are found, I check whether a fixed version is available and upgrade the base image or application dependency. If there is no fix, I assess the risk and follow the organization's exception process instead of blindly ignoring it. Only after the security gate passes do I push the image to ACR and deploy it to AKS."

The command to remember:

```bash
trivy image \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  payment-api:25
```

The key interview flow is: Build → Scan → Fail/Pass → Push → Deploy.

---

## Q10. How do you manage secrets in Kubernetes?

Kubernetes has a built-in `Secret` object, but by default it only base64-encodes the value — it is **not encrypted** unless you explicitly configure encryption at rest. So I treat native Secrets as a starting point, not the full solution.

### 1. Basic Kubernetes Secret

```bash
kubectl create secret generic db-secret \
  --from-literal=DB_PASSWORD='MyPassword123' \
  -n production
```

```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-secret
        key: DB_PASSWORD
```

I generally prefer mounting secrets as a **volume** rather than an environment variable where possible — env vars can be exposed more easily through `/proc`, crash dumps, or logging of the process environment.

### 2. Enable encryption at rest

By default, Secrets stored in etcd are only base64-encoded. For AKS/self-managed clusters, I make sure encryption at rest is enabled so the actual etcd data is encrypted, not just obfuscated.

### 3. Don't commit Secret manifests to Git

I never commit a raw `Secret` YAML with real values. Options I use instead:

- **Sealed Secrets** — encrypt the secret so it's safe to commit; only the cluster controller can decrypt it.
- **External Secrets Operator** — syncs secrets from an external store (Azure Key Vault, AWS Secrets Manager, HashiCorp Vault) into Kubernetes Secrets automatically.

### 4. Azure Key Vault + Secrets Store CSI Driver / Workload Identity (my preferred approach for AKS)

```
AKS Pod
   |
   | Workload Identity
   v
Azure Key Vault
   |
   v
Secret mounted as a volume (never stored as a K8s Secret object)
```

This avoids storing the secret in Kubernetes at all — the Pod retrieves it directly from Key Vault at runtime through a mounted volume.

### 5. RBAC

I restrict who/what can read Secrets:

```yaml
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
  resourceNames: ["db-secret"]
```

Only the specific ServiceAccounts/roles that need a Secret should have `get`/`list` access to it.

### 6. Rotation

Since credentials can be compromised, I use Key Vault's rotation capability combined with the CSI driver's periodic sync, rather than manually rotating and redeploying Secrets.

### Interview answer

> "Kubernetes Secrets are only base64-encoded by default, not encrypted, so I don't treat them as sufficient on their own. I enable encryption at rest for etcd, and I never commit raw Secret manifests to Git — I either use Sealed Secrets or, more commonly on AKS, the Azure Key Vault Secrets Store CSI Driver with Workload Identity, so the Pod retrieves secrets directly from Key Vault and they're never stored as plain Kubernetes Secret objects. I mount secrets as volumes rather than environment variables where possible, restrict access with RBAC scoped to specific secret names, and rely on Key Vault rotation instead of manually rotating and redeploying secrets."

---

## Q11. What `kubectl` commands do you use to check Ingress?

```bash
# List all Ingress resources across all namespaces
kubectl get ingress -A

# List Ingress resources in a specific namespace
kubectl get ingress -n production

# Detailed view — backend, rules, TLS, and recent events
kubectl describe ingress payment-ingress -n production

# Check which Ingress class is configured
kubectl get ingressclass

# Check the Ingress controller Pods themselves
kubectl get pods -n ingress-nginx

# Check the Ingress controller logs for upstream/routing errors
kubectl logs -n ingress-nginx <ingress-controller-pod>

# Check events related to Ingress (useful for TLS/cert issues too)
kubectl get events -n production --sort-by=.lastTimestamp

# Confirm the backend Service the Ingress points to actually has endpoints
kubectl get endpoints payment-api -n production
```

### What I check in the output

- **`kubectl describe ingress`** — backend service name/port, host and path rules, TLS secret, and an Events section for routing failures.
- **`kubectl get ingressclass`** — confirms the Ingress is actually being picked up by a controller (a missing/wrong `ingressClassName` means no controller processes it at all).
- **Ingress controller logs** — for messages like `upstream timed out`, `connection refused`, or `no live upstreams`, which point to a backend Service/Pod problem rather than the Ingress config itself.

### Interview answer

> "To check Ingress, I start with `kubectl get ingress -A` to see what's configured, then `kubectl describe ingress <name> -n <namespace>` to check the backend service, path rules, TLS configuration, and any events. I confirm the Ingress class is correctly picked up with `kubectl get ingressclass`, and if traffic still isn't routing, I check the Ingress controller Pods and logs directly with `kubectl get pods -n ingress-nginx` and `kubectl logs`. I also verify the backend Service has actual endpoints with `kubectl get endpoints`, since an Ingress pointing at a Service with zero endpoints will fail even if the Ingress config itself is correct."

---

## Q12. You manage 500 Linux VMs. Write a Bash script that checks disk, memory, and Nginx status, generates a CSV report, handles unreachable servers, and reports only unhealthy ones.

**Task:**

- Checks disk utilization
- Checks memory utilization
- Checks if the nginx service is running
- Generates a CSV report
- Handles server-unreachable scenarios
- Reports only the unhealthy servers

For 500 Linux VMs, I would use SSH + Bash from a central management server. The script checks each server, writes a CSV report, and separately records only unhealthy servers.

### Bash script

```bash
#!/bin/bash

SERVERS_FILE="servers.txt"
REPORT="server_health_report_$(date +%Y%m%d_%H%M%S).csv"
UNHEALTHY="unhealthy_servers_$(date +%Y%m%d_%H%M%S).csv"

# Thresholds
DISK_THRESHOLD=80
MEMORY_THRESHOLD=80

# CSV headers
echo "Server,Status,Disk_Usage,Memory_Usage,Nginx_Status,Reason" > "$REPORT"
echo "Server,Disk_Usage,Memory_Usage,Nginx_Status,Reason" > "$UNHEALTHY"

while read -r SERVER
do
    # Skip empty lines and comments
    [[ -z "$SERVER" || "$SERVER" =~ ^# ]] && continue

    echo "Checking $SERVER..."

    # Check SSH connectivity
    if ! ssh -o ConnectTimeout=5 \
            -o BatchMode=yes \
            "$SERVER" "echo connected" &>/dev/null
    then
        echo "$SERVER,UNREACHABLE,N/A,N/A,N/A,SSH connection failed" >> "$REPORT"
        echo "$SERVER,N/A,N/A,N/A,SSH connection failed" >> "$UNHEALTHY"
        continue
    fi

    # Collect disk usage
    DISK=$(ssh "$SERVER" \
        "df -P / | awk 'NR==2 {gsub(/%/,\"\",\$5); print \$5}'")

    # Collect memory usage
    MEMORY=$(ssh "$SERVER" \
        "free | awk '/Mem:/ {printf \"%.0f\", \$3/\$2*100}'")

    # Check nginx
    NGINX=$(ssh "$SERVER" \
        "systemctl is-active nginx 2>/dev/null || echo inactive")

    REASONS=""

    # Check disk
    if [ "$DISK" -ge "$DISK_THRESHOLD" ]; then
        REASONS="Disk usage ${DISK}%"
    fi

    # Check memory
    if [ "$MEMORY" -ge "$MEMORY_THRESHOLD" ]; then
        [ -n "$REASONS" ] && REASONS="$REASONS; "
        REASONS="${REASONS}Memory usage ${MEMORY}%"
    fi

    # Check nginx
    if [ "$NGINX" != "active" ]; then
        [ -n "$REASONS" ] && REASONS="$REASONS; "
        REASONS="${REASONS}Nginx is not running"
    fi

    # Determine server health
    if [ -n "$REASONS" ]; then
        STATUS="UNHEALTHY"
    else
        STATUS="HEALTHY"
        REASONS="None"
    fi

    # Write complete report
    echo "$SERVER,$STATUS,${DISK}%,${MEMORY}%,$NGINX,\"$REASONS\"" >> "$REPORT"

    # Write only unhealthy servers
    if [ "$STATUS" = "UNHEALTHY" ]; then
        echo "$SERVER,${DISK}%,${MEMORY}%,$NGINX,\"$REASONS\"" >> "$UNHEALTHY"
    fi

done < "$SERVERS_FILE"

echo
echo "Health check completed."
echo "Complete report : $REPORT"
echo "Unhealthy report : $UNHEALTHY"
```

`servers.txt`:

```
server01
server02
server03
server04
server05
```

For 500 servers, this file would contain all 500 hostnames or IP addresses.

### Example output

Complete CSV:

```
Server,Status,Disk_Usage,Memory_Usage,Nginx_Status,Reason
server01,HEALTHY,45%,52%,active,"None"
server02,UNHEALTHY,91%,60%,active,"Disk usage 91%"
server03,UNHEALTHY,55%,88%,active,"Memory usage 88%"
server04,UNHEALTHY,40%,50%,inactive,"Nginx is not running"
server05,UNREACHABLE,N/A,N/A,N/A,"SSH connection failed"
```

Unhealthy CSV:

```
Server,Disk_Usage,Memory_Usage,Nginx_Status,Reason
server02,91%,60%,active,"Disk usage 91%"
server03,55%,88%,active,"Memory usage 88%"
server04,40%,50%,inactive,"Nginx is not running"
server05,N/A,N/A,N/A,"SSH connection failed"
```

### Simple explanation

The flow is:

```
500 servers
     |
     v
Read server name
     |
     v
Check SSH connectivity
     |
     +---- Failed ---> UNREACHABLE
     |
     v
Check disk usage
     |
     v
Check memory usage
     |
     v
Check nginx service
     |
     v
Compare with thresholds
     |
     +---- Everything OK ---> HEALTHY
     |
     +---- Any issue -------> UNHEALTHY
                              |
                              v
                     Add to unhealthy CSV
```

**1. Disk utilization**

```bash
df -P / | awk ...
```

Checks the root filesystem `/`. If disk usage is 80% or higher, the server is marked unhealthy.

**2. Memory utilization**

```bash
free | awk ...
```

Calculates used memory as a percentage. If memory is 80% or higher, it is considered unhealthy.

**3. Nginx**

```bash
systemctl is-active nginx
```

Returns `active` when Nginx is running. Anything else means Nginx is unhealthy.

**4. Unreachable server**

Before running the checks, we test SSH:

```bash
ssh -o ConnectTimeout=5 ...
```

If SSH fails, we don't waste time running the other commands. The server is marked `UNREACHABLE`.

**5. CSV report**

The script generates two files:

```
server_health_report_*.csv  -> all servers
unhealthy_servers_*.csv     -> only unhealthy/unreachable servers
```

### Understanding the SSH connectivity check in detail

This part of the script specifically checks whether a Linux VM is reachable over SSH before doing the disk, memory, and Nginx checks.

**1. The actual SSH command**

```bash
ssh "$SERVER" "echo connected"
```

It tries to connect to the server and execute `echo connected`. If the connection works, SSH returns exit code `0`. If it fails, SSH returns a non-zero exit code.

**2. What does `!` mean?**

```bash
if ! ssh ...
```

`!` means NOT.

Normally, `if ssh server01 ...` means "if SSH succeeds, execute `then`." But `if ! ssh server01 ...` means "if SSH fails, execute `then`." So here we are specifically handling the failure scenario.

**3. `ConnectTimeout=5`**

```
-o ConnectTimeout=5
```

This tells SSH to wait a maximum of 5 seconds while trying to establish the connection. Without a timeout, an unreachable server could potentially cause the script to wait much longer. For 500 servers, this is important.

**4. `BatchMode=yes`**

```
-o BatchMode=yes
```

This prevents SSH from asking for interactive input such as `Enter passphrase:`, `Are you sure you want to continue connecting?`, or `Password:`. For automation, we don't want the script to stop and wait for someone to type something. Ideally, SSH keys are already configured:

```
Management Server
       |
       | SSH key
       v
    server01
    server02
    server03
```

**5. Why `echo connected`?**

```bash
"$SERVER" "echo connected"
```

Suppose `SERVER="server01"`. This becomes `ssh server01 "echo connected"`. If SSH works, the remote server executes `echo connected` and returns successfully. We're not actually interested in the word `connected` — we're using the command to verify that SSH connection + remote command execution are working.

**6. What does `&>/dev/null` mean?**

```
&>/dev/null
```

It suppresses both standard output and standard error. For example, instead of displaying `ssh: connect to host server01 port 22: Connection timed out`, nothing is displayed. We only care about the exit status because the `if` statement checks whether SSH succeeded or failed.

**7. The `then` section**

If SSH fails:

```bash
then
    echo "$SERVER,UNREACHABLE,N/A,N/A,N/A,SSH connection failed" >> "$REPORT"
    echo "$SERVER,N/A,N/A,N/A,SSH connection failed" >> "$UNHEALTHY"
    continue
fi
```

Suppose `SERVER=server05` and server05 is unreachable. The complete report gets:

```
server05,UNREACHABLE,N/A,N/A,N/A,SSH connection failed
```

And the unhealthy report gets:

```
server05,N/A,N/A,N/A,SSH connection failed
```

We use `N/A` because we couldn't connect to the server, so we cannot check disk, memory, or Nginx.

**8. Why `continue`?**

```bash
continue
```

Once SSH fails, there is no point executing `df`, `free`, or `systemctl is-active nginx`, because those commands need to run on the remote server. `continue` means: stop processing this server and move to the next server in `servers.txt`.

For example:

```
server01 -> SSH OK     -> check everything
server02 -> SSH OK     -> check everything
server03 -> SSH FAILED -> mark unreachable -> skip -> server04
server04 -> SSH OK     -> check everything
```

### Interview explanation

If they ask "How would you handle 500 servers?", don't say you would manually SSH into each server.

Say:

> "I would maintain the server list in a file and run a centralized Bash health-check script using SSH. The script checks connectivity first, then disk, memory, and Nginx status. I would define thresholds such as 80% for disk and memory. The script generates a CSV containing the health status of all servers and a separate report containing only unhealthy or unreachable servers. For 500 servers, I would further optimize it by running the checks in parallel rather than sequentially."

That last point is important. The script above is sequential, so for a real 500-VM environment, parallel SSH using `xargs -P`, GNU Parallel, or Ansible would be better.

If SSH fails specifically, the shorter version of the answer is:

> "First, I perform an SSH connectivity check with a 5-second timeout. I use BatchMode so the script doesn't wait for interactive input. If SSH fails, I mark the server as UNREACHABLE in the CSV, add it to the unhealthy report, and use `continue` to skip the remaining health checks and move to the next server."

---

## Q13. Kubernetes YAML Challenge — find and fix what's broken

**Given (broken YAML):**

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
name: app

spec:
replicas: 3

template:
metadata:
labels:
app: app

spec:
containers:
- image: nginx
```

The YAML is broken mainly because the indentation is incorrect. Kubernetes YAML is indentation-sensitive.

### Fixed YAML

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: app

spec:
  replicas: 3

  selector:
    matchLabels:
      app: app

  template:
    metadata:
      labels:
        app: app

    spec:
      containers:
        - name: app
          image: nginx
```

### What was wrong?

**1. `metadata.name` indentation**

Broken:

```yaml
metadata:
name: app
```

Correct:

```yaml
metadata:
  name: app
```

`name` belongs under `metadata`.

**2. `template.metadata` indentation**

Broken:

```yaml
template:
metadata:
labels:
app: app
```

Correct:

```yaml
template:
  metadata:
    labels:
      app: app
```

Each child level needs proper indentation.

**3. Missing `selector`**

For a Deployment, you should define:

```yaml
selector:
  matchLabels:
    app: app
```

The selector must match the pod template labels:

```yaml
labels:
  app: app
```

So Kubernetes knows which Pods belong to this Deployment.

**4. Container needs a name**

Broken:

```yaml
containers:
- image: nginx
```

Better:

```yaml
containers:
  - name: app
    image: nginx
```

A container in a Pod specification requires a container name.

### Easy way to remember the hierarchy

```
Deployment
 ├── metadata
 │    └── name
 │
 └── spec
      ├── replicas
      ├── selector
      │    └── matchLabels
      │
      └── template
           ├── metadata
           │    └── labels
           │
           └── spec
                └── containers
                     ├── name
                     └── image
```

### Interview answer

> "For an interview, the three things I'd immediately look for are: YAML indentation, the Deployment selector matching the Pod labels, and the container name and image being present."
