# Accenture - Interview Questions

<details><summary>Q1. How do you integrate Trivy and SonarQube in CI/CD?</summary>

They check different things, so I use both:

| Tool | What it scans | Finds |
| --- | --- | --- |
| **SonarQube** | Source code (SAST) | Bugs, code smells, security hotspots, duplicate code, test coverage |
| **Trivy** | Dependencies, Docker images, IaC files, secrets | Known CVEs in OS packages and libraries, misconfigurations in Terraform/K8s YAML, hard-coded secrets |

### Where they sit in the pipeline

```text
Checkout
   |
Build + unit tests (coverage report)
   |
SonarQube analysis --> Quality Gate (fail pipeline if gate fails)
   |
Trivy fs / config scan (dependencies, Terraform, K8s YAML, secrets)
   |
Docker build (local image, NOT pushed yet)
   |
Trivy image scan --> fail on HIGH/CRITICAL
   |
Push to ACR --> Deploy
```

The key idea: **scan before you push**. A vulnerable image never reaches the registry.

### Setup (one time)

**SonarQube:**
1. Install the **SonarQube** extension from the Azure DevOps Marketplace.
2. In SonarQube: create the project and a token (**My Account > Security > Generate token**).
3. In Azure DevOps: **Project settings > Service connections > New > SonarQube**, paste server URL + token. Name it `sc-sonarqube`.
4. In SonarQube: set a **Quality Gate** (for example: coverage on new code >= 80%, no new critical bugs or vulnerabilities).

**Trivy:** nothing to configure on a server. It is a single binary installed on the agent (or baked into a self-hosted agent image).

### Azure DevOps pipeline (Spring Boot example)

```yaml
trigger:
  - main

variables:
  imageName: sivaacr.azurecr.io/siva-api
  tag: $(Build.BuildId)
  trivyVersion: v0.56.2

stages:
  - stage: CI
    jobs:
      - job: BuildScanPush
        pool: { vmImage: ubuntu-latest }
        steps:
          # ---------- SonarQube ----------
          - task: SonarQubePrepare@7
            inputs:
              SonarQube: sc-sonarqube
              scannerMode: other               # Maven runs the scanner
              extraProperties: |
                sonar.projectKey=siva-api
                sonar.qualitygate.wait=true    # fail the build if the Quality Gate fails

          - task: Maven@4
            displayName: Build, test, Sonar analysis
            inputs:
              mavenPomFile: pom.xml
              goals: clean verify
              publishJUnitResults: true
              testResultsFiles: "**/surefire-reports/TEST-*.xml"
              sonarQubeRunAnalysis: true
              javaHomeOption: JDKVersion
              jdkVersionOption: "1.17"

          - task: SonarQubePublish@7
            inputs:
              pollingTimeoutSec: "300"         # shows Quality Gate result on the run summary

          # ---------- Trivy ----------
          - script: |
              curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
                | sh -s -- -b /usr/local/bin $(trivyVersion)
              trivy --version
            displayName: Install Trivy (pinned version)

          - script: |
              trivy fs --scanners vuln,secret,misconfig \
                --severity HIGH,CRITICAL --exit-code 1 .
            displayName: Trivy - dependencies, secrets, IaC

          - task: Docker@2
            displayName: Docker build (no push yet)
            inputs:
              command: build
              containerRegistry: sc-acr-siva
              repository: siva-api
              tags: $(tag)

          - script: |
              trivy image --severity HIGH,CRITICAL --ignore-unfixed \
                --exit-code 1 --format table $(imageName):$(tag)
              trivy image --format json -o $(Build.ArtifactStagingDirectory)/trivy-image.json $(imageName):$(tag)
            displayName: Trivy - image scan

          - publish: $(Build.ArtifactStagingDirectory)/trivy-image.json
            artifact: trivy-report
            condition: always()                # keep the report even if the scan failed

          - task: Docker@2
            displayName: Push to ACR (only if scans passed)
            inputs:
              command: push
              containerRegistry: sc-acr-siva
              repository: siva-api
              tags: $(tag)
```

### Important Trivy options

| Option | Meaning |
| --- | --- |
| `--exit-code 1` | Return non-zero when findings exist, so the pipeline **fails** |
| `--severity HIGH,CRITICAL` | Only fail on serious issues |
| `--ignore-unfixed` | Skip CVEs that have no fix yet (you cannot act on them) |
| `.trivyignore` file | Accept a specific CVE with a reason (reviewed risk) |
| `trivy config ./terraform` | Scan only IaC misconfigurations |

Example `.trivyignore`:

```text
# Accepted by security team until 2026-12-31, not reachable in our code
CVE-2024-12345
```

### Local commands (to reproduce a pipeline failure)

```bash
trivy image --severity HIGH,CRITICAL sivaacr.azurecr.io/siva-api:1234
trivy fs .
trivy config ./terraform
```

### Interview answer

> "SonarQube does static code analysis and Trivy scans dependencies, IaC, secrets, and container images, so I use both. In Azure DevOps, I install the SonarQube extension and create a service connection. The pipeline runs SonarQubePrepare, then Maven runs the analysis with tests and coverage, and with `sonar.qualitygate.wait=true` the build fails if the Quality Gate fails. Then I install a pinned Trivy version on the agent, run `trivy fs` for dependencies, secrets, and Terraform misconfigurations, build the Docker image locally, and run `trivy image` with `--severity HIGH,CRITICAL --exit-code 1`. Only if all scans pass is the image pushed to ACR. Accepted risks go in `.trivyignore` with a reason, and the JSON report is published as an artifact."

</details>

---

<details><summary>Q2. After a deployment the application is not working fine. How will you troubleshoot?</summary>

I follow a fixed order: **understand the impact -> decide quickly whether to roll back -> find the root cause -> prevent it next time.**

### Step 1: Understand the problem

| Question | Why |
| --- | --- |
| What exactly is wrong? (down, 5xx errors, slow, one feature broken) | Tells you where to look |
| All users or some? One region or all? | Partial = one pod/node/zone or a feature flag |
| When did it start? Exactly after the deployment? | Confirms the deployment is the likely cause |
| What changed? (image, config, secret, DB migration, infra) | `git diff` / release notes / pipeline run |

### Step 2: If production users are affected, roll back first

Restore service first, investigate after.

```bash
# Kubernetes
kubectl rollout undo deployment/siva-api -n siva-prod
kubectl rollout status deployment/siva-api -n siva-prod

# App Service / Function App with slots: swap back
az webapp deployment slot swap -g rg-siva -n siva-web --slot staging --target-slot production

# Or redeploy the previous successful pipeline run (same image tag)
```

### Step 3: Check the deployment itself (Kubernetes example)

```bash
kubectl rollout status deployment/siva-api -n siva-prod
kubectl get pods -n siva-prod -o wide                 # CrashLoopBackOff? Pending? restarts?
kubectl describe pod <pod> -n siva-prod               # events, probe failures, OOMKilled, image pull errors
kubectl logs <pod> -n siva-prod --previous            # why it crashed
kubectl get events -n siva-prod --sort-by=.lastTimestamp
kubectl rollout history deployment/siva-api -n siva-prod
```

| What you see | Likely cause |
| --- | --- |
| `ImagePullBackOff` | Wrong tag, or AKS cannot pull from ACR |
| `CrashLoopBackOff` | App startup error, missing config/secret, OOMKilled |
| `Pending` | Not enough CPU/memory on nodes, PVC not bound |
| Running but `0/1 READY` | Readiness probe failing (wrong path/port, app not ready) |

### Step 4: Check traffic path and configuration

```bash
kubectl get endpoints siva-api -n siva-prod           # empty = selector or readiness problem
kubectl describe ingress siva-ingress -n siva-prod
kubectl get configmap,secret -n siva-prod
kubectl exec -it <pod> -n siva-prod -- env | grep DB_
kubectl exec -it <pod> -n siva-prod -- curl -s localhost:8080/actuator/health
```

Common config problems: new environment variable not added in prod, Key Vault secret missing or expired, wrong connection string, feature flag on.

### Step 5: Check dependencies

```bash
kubectl exec -it <pod> -n siva-prod -- nc -zv siva-sql.database.windows.net 1433
kubectl exec -it <pod> -n siva-prod -- nslookup siva-sql.database.windows.net
```

Database migration failed? Downstream API changed? Firewall/NSG/private endpoint blocking?

### Step 6: Use monitoring

| Tool | What to look at |
| --- | --- |
| Application Insights | Failed requests, exceptions, dependency failures, response time (compare before/after deploy time) |
| Container Insights / Log Analytics | Pod restarts, CPU/memory, container logs with KQL |
| Grafana / Prometheus | Error rate, latency, saturation dashboards |

```kusto
// Exceptions after the deployment, grouped by type
exceptions
| where timestamp > ago(1h)
| summarize count() by type, outerMessage
| order by count_ desc
```

### Step 7: Fix and prevent

- Fix the root cause and redeploy through the pipeline (no manual hot fixes in prod).
- Write an RCA: what happened, impact, root cause, fix, prevention.
- Prevention: readiness probes, smoke tests after deploy, canary or blue-green deployments, automatic rollback on failed health checks, config parity between environments.

### Interview answer

> "First, I understand the impact: what is broken, for which users, and whether it started exactly with the deployment. If production users are affected, I roll back first, using `kubectl rollout undo` or a slot swap, and investigate after. Then I check the rollout: pod status, `kubectl describe` for events and probe failures, and `kubectl logs --previous` for crash reasons. Next, I check the traffic path: Service endpoints and Ingress, then configuration such as environment variables, secrets, and connection strings, and dependencies like the database. In parallel, I use Application Insights and Grafana to compare errors and latency before and after the deployment. Finally, I fix the root cause through the pipeline, write an RCA, and add prevention like smoke tests or canary deployments."

</details>

---

<details><summary>Q3. What is Gateway API?</summary>

**Gateway API** is the official Kubernetes project that is the **next generation of Ingress**. It is a set of CRDs (`gateway.networking.k8s.io`) for routing traffic into (and within) the cluster, with more features and a clearer split of responsibilities than Ingress.

### Why it was created (Ingress limitations)

| Ingress problem | Gateway API answer |
| --- | --- |
| Only HTTP host/path routing | HTTP, HTTPS, gRPC, TCP, UDP, TLS routes |
| Advanced features need controller-specific **annotations** (not portable) | Header matching, traffic splitting, redirects, rewrites are part of the **standard spec** |
| One object mixes infra and app settings | Separate resources per **role** |
| Hard to share one load balancer safely across teams | Gateway in one namespace, routes in app namespaces, controlled by `allowedRoutes` |

Also, the community `ingress-nginx` controller has been retired, which is pushing many teams to move to Gateway API.

### Main resources (role-oriented)

```text
GatewayClass   (Infra provider)   -> which controller: Envoy Gateway, Istio, NGINX Gateway Fabric, App Gateway for Containers
     |
Gateway        (Cluster operator) -> the load balancer: listeners, ports, TLS certificates
     |
HTTPRoute      (App developer)    -> routing rules: host, path, headers -> Services, with weights
     |
Service -> Pods
```

### Example

Install the CRDs (some managed controllers install them for you):

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml
kubectl get gatewayclass
```

**Gateway** (owned by the platform team):

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: siva-gateway
  namespace: infra
spec:
  gatewayClassName: eg                    # e.g. Envoy Gateway
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      hostname: "*.siva.com"
      tls:
        mode: Terminate
        certificateRefs:
          - name: siva-wildcard-tls
      allowedRoutes:
        namespaces:
          from: All
```

**HTTPRoute** (owned by the app team) with a **canary: 90% v1, 10% v2**:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: siva-api-route
  namespace: siva-prod
spec:
  parentRefs:
    - name: siva-gateway
      namespace: infra
  hostnames:
    - api.siva.com
  rules:
    - matches:
        - headers:
            - name: x-beta-user
              value: "true"
      backendRefs:
        - name: siva-api-v2
          port: 80
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: siva-api-v1
          port: 80
          weight: 90
        - name: siva-api-v2
          port: 80
          weight: 10
```

Beta users (header `x-beta-user: true`) always get v2; everyone else is split 90/10. With Ingress this needs vendor annotations.

### Commands

```bash
kubectl get gateway -A
kubectl describe gateway siva-gateway -n infra        # check Programmed/Accepted conditions and address
kubectl get httproute -A
kubectl describe httproute siva-api-route -n siva-prod  # Accepted / ResolvedRefs status
```

### On Azure

**Application Gateway for Containers (AGC)** is Azure's managed implementation of Gateway API for AKS. Istio (AKS add-on) and Envoy Gateway also support it.

### Interview answer

> "Gateway API is the Kubernetes successor to Ingress. It splits the configuration by role: the infrastructure provider defines a GatewayClass, the platform team creates a Gateway with listeners, ports, and TLS certificates, and application teams create HTTPRoutes in their own namespaces that attach to that Gateway. Unlike Ingress, features like header-based routing, weighted traffic splitting for canary releases, redirects, and gRPC or TCP routes are part of the standard, so we don't depend on controller-specific annotations. Implementations include Envoy Gateway, Istio, NGINX Gateway Fabric, and on AKS, Application Gateway for Containers."

</details>

---

<details><summary>Q4. What automations have you done? Please explain.</summary>

Interviewers want **real examples** with the **problem, what you built, tools, and the result**. Use this structure for each one:

```text
Problem -> What I automated -> Tools -> Result (time saved / errors reduced)
```

Pick 3-4 examples from your own work. The ones below are common DevOps automations you can adapt. **Replace the numbers with your real ones.**

### 1. Infrastructure provisioning with Terraform + pipeline

- **Problem:** Environments were created manually in the portal; Dev, QA, and Prod were different, and a new environment took days.
- **What I did:** Reusable Terraform modules (VNet, AKS, ACR, Key Vault, SQL, private endpoints), remote state in Azure Storage, and an Azure DevOps pipeline: `fmt` -> `validate` -> `tflint`/Trivy config scan -> `plan` -> approval -> `apply`.
- **Result:** A new environment takes under an hour with the same configuration everywhere, and every change is reviewed through a PR.

```yaml
- script: |
    terraform init -backend-config=env/$(env).backend.hcl
    terraform plan -var-file=env/$(env).tfvars -out=tfplan
  displayName: Terraform plan
```

### 2. Reusable CI/CD pipeline templates

- **Problem:** Each microservice had its own copy-pasted pipeline; fixes had to be repeated 20 times.
- **What I did:** Central YAML templates (build, Sonar, Trivy, Docker, deploy) in a shared repo; each service pipeline is ~15 lines.
- **Result:** One change in the template applies to all services; security scans are enforced everywhere.

```yaml
resources:
  repositories:
    - repository: templates
      type: git
      name: Platform/pipeline-templates

extends:
  template: microservice.yml@templates
  parameters:
    serviceName: siva-api
```

### 3. Cost saving: stop non-prod AKS and VMs at night

- **Problem:** Dev/QA clusters ran 24x7 but were used only in office hours.
- **What I did:** A scheduled pipeline (cron) stops the clusters in the evening and starts them in the morning.
- **Result:** Non-prod compute cost reduced significantly (state your real %).

```yaml
schedules:
  - cron: "30 14 * * 1-5"       # 20:00 IST = 14:30 UTC
    branches: { include: [main] }
    always: true

steps:
  - task: AzureCLI@2
    inputs:
      azureSubscription: sc-azure-nonprod
      scriptType: bash
      scriptLocation: inlineScript
      inlineScript: |
        az aks stop -g rg-siva-dev -n aks-siva-dev
        az vm deallocate --ids $(az vm list -g rg-siva-dev --query "[].id" -o tsv)
```

### 4. Certificate and secret expiry alerts

- **Problem:** An expired certificate caused an outage.
- **What I did:** A daily script checks Key Vault certificates and secrets, and posts to Teams if anything expires within 30 days.
- **Result:** No expiry-related outages since.

```bash
#!/bin/bash
VAULT="kv-siva-prod"
LIMIT=$(date -d "+30 days" +%s)

az keyvault certificate list --vault-name "$VAULT" \
  --query "[].{name:name, exp:attributes.expires}" -o tsv |
while read -r name exp; do
  if [[ -n "$exp" && $(date -d "$exp" +%s) -lt $LIMIT ]]; then
    curl -s -H "Content-Type: application/json" \
      -d "{\"text\":\"Certificate $name in $VAULT expires on $exp\"}" "$TEAMS_WEBHOOK_URL"
  fi
done
```

### 5. Linux housekeeping scripts

- **Problem:** Disks filled up with old logs, causing app failures.
- **What I did:** Cron script to delete logs older than N days and alert at 80% disk usage.

```bash
find /var/log/siva -type f -name "*.log" -mtime +15 -delete
USAGE=$(df / --output=pcent | tail -1 | tr -dc '0-9')
(( USAGE > 80 )) && echo "Disk usage ${USAGE}% on $(hostname)" | mail -s "Disk alert" ops@example.com
```

### Other ideas worth mentioning (if you have done them)

| Area | Automation |
| --- | --- |
| Access | Onboarding script: create Entra group, RBAC assignments, ADO permissions |
| Kubernetes | Helm charts + GitOps (Argo CD / Flux) for automatic sync |
| Security | Azure Policy assignments as code; auto-tagging resources |
| Releases | Automatic rollback when smoke tests fail after deploy |
| Reporting | Weekly cost / unused resource report (unattached disks, idle public IPs) |

### Interview answer

> "I have automated across infrastructure, CI/CD, and operations. For infrastructure, I built reusable Terraform modules with a pipeline that runs validation, a security scan, plan, approval, and apply, so new environments take about an hour instead of days and stay consistent. For CI/CD, I created shared YAML templates with build, SonarQube, Trivy, and deployment steps, so each microservice pipeline just extends the template. For cost, I added a scheduled pipeline that stops non-prod AKS clusters and VMs at night and starts them in the morning. And for operations, I wrote scripts that alert on Key Vault certificate expiry and clean up old logs. In each case, the goal was to remove manual, error-prone steps and make the process repeatable."

</details>

---

<details><summary>Q5. What observability tools have you used, and how?</summary>

Observability has three pillars. I map each one to a tool:

| Pillar | Question it answers | Tools I have used |
| --- | --- | --- |
| **Metrics** | Is something wrong? (CPU, error rate, latency) | Azure Monitor metrics, Prometheus, Grafana |
| **Logs** | What exactly happened? | Log Analytics (KQL), Container Insights, ELK/EFK, Splunk |
| **Traces** | Where in the request chain is it slow/failing? | Application Insights, OpenTelemetry |
| **Alerts** | Who needs to know now? | Azure Monitor alerts + action groups, Alertmanager, Teams/PagerDuty |

### Overall setup

```text
AKS pods / VMs / App Services
   |-- metrics --> Managed Prometheus  --> Azure Managed Grafana (dashboards)
   |-- logs    --> Container Insights  --> Log Analytics workspace (KQL)
   |-- traces  --> Application Insights (OpenTelemetry / Java agent)
                          |
                Azure Monitor alerts --> Action group --> Email / Teams / ITSM
```

### 1. Azure Monitor + Log Analytics + Container Insights

```bash
# Enable Container Insights (logs) and managed Prometheus (metrics) on AKS
az aks enable-addons -g rg-siva -n aks-siva -a monitoring \
  --workspace-resource-id <LOG_ANALYTICS_WORKSPACE_ID>
az aks update -g rg-siva -n aks-siva --enable-azure-monitor-metrics
```

Diagnostic settings send platform logs (Key Vault, App Gateway, SQL) to the same workspace.

KQL I use often:

```kusto
// Error logs from a namespace in the last hour
ContainerLogV2
| where TimeGenerated > ago(1h)
| where PodNamespace == "siva-prod" and LogMessage has "ERROR"
| project TimeGenerated, PodName, LogMessage
| order by TimeGenerated desc

// Pods restarting
KubePodInventory
| where TimeGenerated > ago(1h)
| summarize Restarts = max(PodRestartCount) by Name, Namespace
| where Restarts > 3
```

### 2. Application Insights (APM / traces)

For Java, attach the agent; no code change needed:

```dockerfile
COPY applicationinsights-agent-3.x.jar /app/ai-agent.jar
ENV APPLICATIONINSIGHTS_CONNECTION_STRING=""   # set from a Kubernetes Secret at runtime
ENTRYPOINT ["java", "-javaagent:/app/ai-agent.jar", "-jar", "/app/app.jar"]
```

It gives request rates, failures, response times, dependency calls (SQL, HTTP), exceptions, and the **application map** to see which service is slow.

```kusto
requests
| where timestamp > ago(30m)
| summarize failures = countif(success == false), p95 = percentile(duration, 95) by name
| order by failures desc
```

### 3. Prometheus + Grafana

- Apps expose `/metrics` (Spring Boot: `/actuator/prometheus`), scraped via ServiceMonitor.
- Grafana dashboards for the **golden signals**: latency, traffic, errors, saturation.

```promql
# Error rate %
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
  / sum(rate(http_server_requests_seconds_count[5m])) * 100
```

### 4. Centralised logs (ELK / Splunk)

- **EFK:** Fluent Bit DaemonSet on every node -> Elasticsearch -> Kibana.
- **Splunk:** Universal Forwarder on VMs, or the OpenTelemetry Collector on AKS sending to the Splunk HTTP Event Collector (HEC). Alerts are saved searches that email or post to Teams.

### 5. Alerts

| Alert | Condition |
| --- | --- |
| High CPU / memory | > 80% for 5 min |
| Error rate | 5xx > 5% for 5 min |
| Pod restarts | CrashLoopBackOff > 0 |
| Availability | App Insights availability test fails from 2+ locations |
| Certificate expiry | < 30 days |

I keep alerts **actionable** (every alert has an owner and a runbook) to avoid alert fatigue.

### Interview answer

> "I cover metrics, logs, and traces. On Azure, I enable Container Insights on AKS to send logs to a Log Analytics workspace and query them with KQL, and I use Managed Prometheus with Azure Managed Grafana for metrics dashboards on latency, traffic, errors, and saturation. For application performance, I use Application Insights with the Java agent, which gives request failures, dependency calls, exceptions, and the application map for distributed tracing. Platform services send diagnostic logs to the same workspace. I have also used EFK and Splunk for centralised logs. Alerts go through Azure Monitor action groups to email and Teams, and I keep them actionable with clear thresholds and runbooks."

</details>

---

<details><summary>Q6. Have you created SAML / SSO? How?</summary>

**SSO (Single Sign-On)** = log in once with your company account and access many apps.
**SAML 2.0** is one protocol to implement SSO (XML-based, common for enterprise apps). The other common one is **OpenID Connect (OIDC)**.

| Term | Meaning | Example |
| --- | --- | --- |
| **IdP** (Identity Provider) | Authenticates the user | Microsoft Entra ID, Okta, ADFS |
| **SP** (Service Provider) | The application | SonarQube, Grafana, Jenkins, ServiceNow |
| **Entity ID / Identifier** | Unique name of the app | `https://sonar.siva.com/saml` |
| **ACS / Reply URL** | Where the IdP posts the SAML response | `https://sonar.siva.com/oauth2/callback/saml` |
| **Assertion** | Signed XML with the user's identity and claims (email, name, groups) | |
| **Certificate** | Used by the SP to verify the IdP's signature | Downloaded from Entra ID |

### SAML login flow (SP-initiated)

```text
1. User opens https://sonar.siva.com
2. SonarQube (SP) redirects browser to Entra ID with a SAML AuthnRequest
3. User logs in to Entra ID (password + MFA, Conditional Access)
4. Entra ID sends a signed SAML assertion back via the browser (POST to the ACS URL)
5. SonarQube validates the signature with the Entra certificate, reads email/groups
6. User is logged in (no separate SonarQube password)
```

### Example: SSO for SonarQube with Microsoft Entra ID

**Part A: Entra ID (IdP side)**

1. **Entra ID > Enterprise applications > New application > Create your own application** -> name `SonarQube`, choose "Integrate any other application you don't find in the gallery".
2. **Single sign-on > SAML**.
3. **Basic SAML Configuration:**
   - Identifier (Entity ID): `sonarqube`
   - Reply URL (ACS): `https://sonar.siva.com/oauth2/callback/saml`
4. **Attributes & Claims:** keep `name`, `emailaddress`, and **add a group claim** (security groups) so roles can be mapped.
5. **SAML Certificates:** download **Certificate (Base64)**. Copy the **Login URL** and **Microsoft Entra Identifier**.
6. **Users and groups:** assign the groups allowed to use the app (e.g. `grp-sonar-users`, `grp-sonar-admins`).

**Part B: SonarQube (SP side)**

**Administration > Configuration > General Settings > Authentication > SAML:**

| Field | Value |
| --- | --- |
| Application ID | `sonarqube` (same as Entity ID) |
| Provider Name | `Microsoft Entra ID` |
| Provider ID | Microsoft Entra Identifier (`https://sts.windows.net/<tenant-id>/`) |
| SAML login URL | Login URL from Entra |
| Identity provider certificate | Content of the Base64 certificate |
| SAML user login / name / email attribute | Claim names from Entra (e.g. `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress`) |
| SAML group attribute | `http://schemas.microsoft.com/ws/2008/06/identity/claims/groups` |

Then create SonarQube groups with the same names (or object IDs) as the Entra groups to get role mapping, and test with **Enterprise app > Single sign-on > Test**.

### OIDC example (when the app supports it, e.g. Grafana)

App registration in Entra ID -> redirect URI `https://grafana.siva.com/login/azuread`, then in `grafana.ini`:

```ini
[auth.azuread]
enabled = true
client_id = <app-client-id>
client_secret = $__file{/etc/secrets/azuread_client_secret}
auth_url = https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize
token_url = https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
allowed_groups = <grafana-users-group-object-id>
role_attribute_path = contains(groups[*], '<admins-group-id>') && 'Admin' || 'Viewer'
```

### SAML vs OIDC

| | SAML 2.0 | OIDC |
| --- | --- | --- |
| Format | XML assertions | JSON (JWT tokens) |
| Best for | Enterprise web apps, older apps | Modern web, mobile, APIs |
| Setup in Entra | Enterprise application | App registration |

### Common issues

| Error | Fix |
| --- | --- |
| `AADSTS50011` reply URL mismatch | Reply URL in Entra must match the app's ACS URL exactly |
| Signature validation failed | Wrong or expired certificate on the SP side; re-download after rotation |
| User logs in but has no rights | Group claim missing or group names do not match |
| `AADSTS50105` user not assigned | Assign the user/group to the enterprise app |

Remember to track **SAML certificate expiry** (default 3 years) and rotate before it expires.

### Interview answer

> "Yes, I have configured SSO with Microsoft Entra ID, for example for SonarQube using SAML. In Entra ID, I created an enterprise application, chose SAML, and set the Identifier and the Reply URL, which is the app's ACS endpoint. I added a group claim, downloaded the Base64 certificate, and assigned only the required groups. On the SonarQube side, I entered the Entra login URL, the Entra identifier as provider ID, the certificate, and the attribute mappings for login, email, and groups, so Entra groups map to SonarQube permissions. The flow is: the app redirects to Entra ID, the user logs in with MFA, Entra posts a signed assertion to the ACS URL, and the app validates it. For modern apps like Grafana, I use OIDC with an app registration instead. I also monitor the SAML signing certificate expiry."

</details>

---

<details><summary>Q7. If you have EC2 and S3, how do you establish a connection between them?</summary>

Secure access has two parts, the same as VM to Storage Account in Azure:

| Part | AWS way | Why |
| --- | --- | --- |
| **Identity** (who is allowed) | **IAM role** attached to EC2 through an **instance profile** | No access keys stored on the server; temporary credentials rotate automatically |
| **Network** (how traffic travels) | **VPC gateway endpoint for S3** | Traffic stays on the AWS network, works from private subnets without a NAT gateway or internet |

```text
EC2 (private subnet, IAM role) --route table--> S3 Gateway Endpoint (vpce-xxxx) --> S3 bucket
                                                                           bucket policy: allow only via vpce-xxxx
```

**Never** run `aws configure` with access keys on an EC2 instance. Use a role.

### Step 1: IAM role for EC2

Trust policy (`trust.json`), which allows EC2 to use the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ec2.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

Permission policy (`s3-access.json`), least privilege on one bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::siva-app-bucket"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::siva-app-bucket/*"
    }
  ]
}
```

```bash
aws iam create-role --role-name ec2-siva-s3-role --assume-role-policy-document file://trust.json
aws iam put-role-policy --role-name ec2-siva-s3-role --policy-name s3-access --policy-document file://s3-access.json

# EC2 uses roles through an instance profile
aws iam create-instance-profile --instance-profile-name ec2-siva-s3-profile
aws iam add-role-to-instance-profile --instance-profile-name ec2-siva-s3-profile --role-name ec2-siva-s3-role

# Attach to a running instance
aws ec2 associate-iam-instance-profile --instance-id i-0abc123 \
  --iam-instance-profile Name=ec2-siva-s3-profile
```

### Step 2: VPC gateway endpoint for S3 (private network path)

```bash
aws ec2 create-vpc-endpoint --vpc-id vpc-0abc123 \
  --vpc-endpoint-type Gateway \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-0private123
```

A gateway endpoint for S3 is **free** and adds a route to S3 in the selected route tables. Use an **interface endpoint (PrivateLink)** instead if you need access from on-premises or peered networks.

### Step 3: Lock down the bucket

```bash
# Block all public access
aws s3api put-public-access-block --bucket siva-app-bucket \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Bucket policy that denies access unless it comes through the VPC endpoint:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyNotFromVpce",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::siva-app-bucket", "arn:aws:s3:::siva-app-bucket/*"],
    "Condition": { "StringNotEquals": { "aws:SourceVpce": "vpce-0abc123" } }
  }]
}
```

Be careful: this also blocks console and pipeline access from outside the VPC. Add exceptions for admin roles if needed.

Also enable default encryption (SSE-S3 or SSE-KMS) and require TLS (`aws:SecureTransport`).

### Step 4: Test from EC2

```bash
aws sts get-caller-identity                 # should show the assumed role ec2-siva-s3-role
aws s3 ls s3://siva-app-bucket
aws s3 cp /tmp/test.txt s3://siva-app-bucket/test.txt
```

Use **IMDSv2** (token-based metadata) on the instance so the role credentials are better protected.

### Terraform (short version)

```hcl
resource "aws_iam_role" "ec2_s3" {
  name               = "ec2-siva-s3-role"
  assume_role_policy = file("trust.json")
}

resource "aws_iam_role_policy" "s3_access" {
  role   = aws_iam_role.ec2_s3.id
  policy = file("s3-access.json")
}

resource "aws_iam_instance_profile" "ec2_s3" {
  name = "ec2-siva-s3-profile"
  role = aws_iam_role.ec2_s3.name
}

resource "aws_instance" "app" {
  ami                  = var.ami_id
  instance_type        = "t3.micro"
  subnet_id            = var.private_subnet_id
  iam_instance_profile = aws_iam_instance_profile.ec2_s3.name

  metadata_options {
    http_tokens = "required"        # IMDSv2
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.us-east-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [var.private_route_table_id]
}
```

### AWS vs Azure

| | AWS | Azure |
| --- | --- | --- |
| Identity | IAM role + instance profile | Managed identity + RBAC role |
| Private network path | VPC gateway / interface endpoint | Service endpoint / private endpoint |
| Resource-side restriction | Bucket policy (`aws:SourceVpce`) | Storage firewall, disable public access |

### Interview answer

> "I connect them with an IAM role, not access keys. I create a role that EC2 can assume, attach a least-privilege policy for only that bucket, and attach the role to the instance through an instance profile, so the instance gets temporary credentials that rotate automatically. For the network, I create a VPC gateway endpoint for S3 on the private subnet's route table, so traffic stays inside AWS and no NAT or internet access is needed. On the bucket, I block public access, enable encryption, and add a bucket policy that only allows requests through that VPC endpoint. I test with `aws sts get-caller-identity` and `aws s3 ls` from the instance. It is the same idea as a managed identity plus a private endpoint in Azure."

</details>

---

<details><summary>Q8. The CPU of a VM / AKS is more than 100%. How do you troubleshoot or fix it using observability?</summary>

First, understand what "more than 100%" means:

| Where you see it | Meaning |
| --- | --- |
| `top` on Linux, per process | 100% = one full core. A process at 350% is using 3.5 cores (normal on multi-core) |
| Azure Monitor "Percentage CPU" (VM) | Whole VM, max 100% = all cores busy |
| `kubectl top pod` vs the pod's CPU limit | A pod cannot go above its limit; it gets **throttled** (slow), not killed |
| `kubectl top node` 100% | All cores of the node are busy; pods compete for CPU |

My approach: **Detect -> find the scope -> find the culprit -> mitigate -> fix the root cause.**

### Step 1: Detect (alert)

An Azure Monitor alert (CPU > 85% for 5 minutes) or a Grafana alert fires to Teams/email. Check **when** it started and whether it lines up with a deployment, a traffic spike, or a scheduled job.

### Step 2: Find the scope with dashboards

| Question | Where to look |
| --- | --- |
| One VM/node or all? | Azure Monitor metrics, VM insights, Container Insights > Nodes |
| One pod / deployment? | Container Insights > Containers, Grafana Kubernetes dashboards |
| Did traffic increase? | Application Insights request rate, ingress metrics |
| Is the app slow because of it? | App Insights response time and failures |

KQL: VMs with highest CPU (VM insights):

```kusto
InsightsMetrics
| where TimeGenerated > ago(1h)
| where Namespace == "Processor" and Name == "UtilizationPercentage"
| summarize avgCPU = avg(Val) by Computer, bin(TimeGenerated, 5m)
| order by avgCPU desc
```

PromQL: top pods by CPU, and throttling:

```promql
# CPU cores used per pod
topk(10, sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace, pod))

# % of time the container was throttled (hitting its CPU limit)
sum(rate(container_cpu_cfs_throttled_periods_total[5m])) by (pod)
  / sum(rate(container_cpu_cfs_periods_total[5m])) by (pod) * 100
```

### Step 3a: Find the culprit on a VM

```bash
top                                   # press P to sort by CPU, 1 to see each core
ps aux --sort=-%cpu | head -10        # top CPU processes
top -H -p <PID>                       # threads inside that process
pidstat -u 5 3                        # CPU per process over time (sysstat)
uptime                                # load average vs number of cores (nproc)
```

For a Java app, find the hot thread:

```bash
top -H -p 4521                        # hot thread id, e.g. 4602
printf '%x\n' 4602                    # -> 11fa (hex)
jstack 4521 | grep -A 20 'nid=0x11fa' # what that thread is doing
```

### Step 3b: Find the culprit on AKS

```bash
kubectl top nodes
kubectl top pods -A --sort-by=cpu | head -15
kubectl top pod <pod> -n siva-prod --containers
kubectl describe node <node>                       # "Allocated resources": requests vs capacity
kubectl get pod <pod> -n siva-prod -o jsonpath='{.spec.containers[*].resources}'
kubectl get hpa -n siva-prod                       # is HPA at maxReplicas already?
```

Then use **Application Insights** for that service: which requests or dependencies are slow, exceptions in loops, and the **profiler** to see which code methods use CPU.

### Step 4: Mitigate quickly

| Situation | Quick action |
| --- | --- |
| Real traffic increase on AKS | Scale out: `kubectl scale deploy/siva-api --replicas=6`, or raise HPA `maxReplicas` |
| All nodes full | Cluster autoscaler / `az aks nodepool scale` |
| Single VM overloaded | Resize: `az vm resize -g rg-siva -n vm-siva --size Standard_D4s_v5`, or scale out the VMSS |
| Bad release (CPU jumped right after deploy) | Roll back: `kubectl rollout undo deploy/siva-api` |
| Runaway process / stuck job | Restart it after collecting a thread dump |

### Step 5: Fix the root cause

| Root cause | Permanent fix |
| --- | --- |
| Code issue (infinite loop, heavy regex, N+1 queries) | Fix code, add a load test in the pipeline |
| Java high GC (memory pressure shows as CPU) | Tune heap / memory limits, fix memory leak |
| Wrong requests/limits, constant throttling | Right-size from metrics (VPA in recommendation mode) |
| No autoscaling | HPA on CPU, VMSS autoscale, cluster autoscaler |
| Noisy neighbour pods | Separate node pools, proper requests, ResourceQuota per namespace |
| Batch job at peak hours | Reschedule the job, or run it on its own node pool |

Then write an RCA and tune the alert thresholds.

### Interview answer

> "First, I clarify the metric: in `top`, over 100% just means more than one core, while VM-level 100% means all cores are busy, and in Kubernetes a pod hitting its CPU limit gets throttled. I start from the alert and dashboards: Azure Monitor and VM insights for VMs, Container Insights and Grafana for AKS, to see whether it is one node, one pod, or everything, and whether it lines up with a deployment or a traffic spike. Then I find the culprit: `top`, `ps --sort=-%cpu`, and `top -H` with `jstack` for Java threads on a VM, and `kubectl top nodes` and `kubectl top pods --sort-by=cpu` plus throttling metrics in Prometheus on AKS. Application Insights and its profiler show which requests or code paths use the CPU. To mitigate, I scale out, resize, or roll back a bad release. Then I fix the root cause, for example code issues, GC tuning, right-sizing requests and limits, or adding HPA and autoscaling, and I write an RCA."

</details>

---

<details><summary>Q9. You ran terraform plan and see one resource being destroyed. What will you do?</summary>

**Stop. Do not apply.** A destroy in a plan is a red flag until you know exactly why it is there, especially for stateful resources like databases, storage accounts, or Key Vaults.

### Step 1: Read the plan carefully

```text
- destroy                     -> resource will be deleted completely
-/+ destroy and then create   -> replacement (look for "# forces replacement")
+/- create then destroy       -> replacement with create_before_destroy
```

```text
  # azurerm_storage_account.sa will be destroyed
  # (because azurerm_storage_account.sa is not in configuration)
  - resource "azurerm_storage_account" "sa" {
```

Terraform usually tells you the reason in brackets, for example "not in configuration", "index [2] is out of range", or the attribute marked `# forces replacement`.

```bash
terraform plan -out=tfplan
terraform show tfplan | grep -B2 -A10 "will be destroyed"
```

### Step 2: Find the reason

| Reason | How to check | Fix |
| --- | --- | --- |
| **Wrong environment**: wrong workspace, backend, or `.tfvars` | `terraform workspace show`, check `-var-file` and backend config | Run with the correct workspace / var file |
| **Resource renamed** or moved into a module | Old address destroyed, new address created | `moved` block or `terraform state mv` |
| **`count` index shifted** (item removed from the middle of a list) | `[2]` destroyed, others changed | Switch to `for_each` with stable keys + `moved` blocks |
| **ForceNew attribute changed** (name, location, SKU tier) | `# forces replacement` | Revert the change, or `lifecycle { ignore_changes = [...] }` |
| **Resource removed from code** (by mistake or in a merge) | `git log -p`, `git diff main` | Restore the code |
| **Drift**: someone changed it in the portal | `terraform plan -refresh-only` | Align code with reality or revert the manual change |
| **Provider upgrade** changed behaviour | Lock file `.terraform.lock.hcl` changed | Pin the provider version, read the upgrade guide |
| **Intended**: you really want it gone | Confirmed with the team | Back up data, get approval, then apply |

### Step 3: Fix without destroying (examples)

**Renamed resource:**

```hcl
moved {
  from = azurerm_storage_account.sa
  to   = azurerm_storage_account.logs
}
```

**Stop managing it in Terraform, but keep it in Azure** (Terraform 1.7+):

```hcl
removed {
  from = azurerm_storage_account.old

  lifecycle {
    destroy = false
  }
}
```

(Older versions: `terraform state rm azurerm_storage_account.old`.)

**Ignore a change that forces replacement:**

```hcl
lifecycle {
  ignore_changes = [tags["CreatedOn"]]
}
```

**Protect critical resources permanently:**

```hcl
lifecycle {
  prevent_destroy = true      # plan fails instead of destroying it
}
```

Also add an Azure **resource lock** (`CanNotDelete`) on production data resources:

```bash
az lock create -g rg-siva-prod -n lock-no-delete --lock-type CanNotDelete
```

### Step 4: Re-run the plan

```bash
terraform plan -out=tfplan        # expect: 0 to destroy
```

### Step 5: Guard it in the pipeline

Fail (or require extra approval) automatically when a plan contains a delete:

```bash
terraform plan -out=tfplan
DESTROYS=$(terraform show -json tfplan | jq '[.resource_changes[] | select(.change.actions | index("delete"))] | length')

if [ "$DESTROYS" -gt 0 ]; then
  echo "##vso[task.logissue type=error]Plan wants to destroy $DESTROYS resource(s). Review required."
  terraform show -json tfplan | jq -r '.resource_changes[] | select(.change.actions | index("delete")) | .address'
  exit 1
fi
```

Always `apply` the **saved plan file** (`terraform apply tfplan`) so what gets applied is exactly what was reviewed.

### Interview answer

> "I stop and do not apply. First, I read the plan to see whether it is a pure destroy or a replacement and what reason Terraform gives, such as 'not in configuration' or an attribute marked 'forces replacement'. Then I find the cause: wrong workspace or tfvars, a renamed resource or one moved into a module, a shifted `count` index, a ForceNew attribute change, code removed in a merge, drift, or a provider upgrade. Depending on the cause, I fix it with a `moved` block, `ignore_changes`, a `removed` block with `destroy = false` to keep the resource, or by restoring the code, and I re-run the plan until it shows zero destroys. If the destroy is really intended, I back up the data and get approval first. To prevent accidents, I use `prevent_destroy` and resource locks on critical resources, and the pipeline checks the plan JSON and blocks any plan with deletes until someone reviews it."

</details>
