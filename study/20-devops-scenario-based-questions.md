# 20 DevOps Scenario-Based Questions

Simple, interview-ready answers for common Kubernetes, Terraform, shell scripting, Jenkins, Docker, and CI/CD troubleshooting scenarios.

## 1. Kubernetes YAML Indentation

### The broken YAML

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
name: payment-api

spec:
replicas: 3
selector:
matchLabels:
app: payment

template:
metadata:
labels:
app: payment

spec:
containers:
- image: nginx
  ports:
  - containerPort: 80
```

### What is wrong

YAML uses indentation to show which fields belong to which parent. In this file, `name`, `spec`, `replicas`, `selector`, `matchLabels`, `app`, `template`, `labels`, and the inner `spec` are all written at column 0, so YAML cannot tell they belong under `metadata` or `spec`. On top of that:

- There is no `containers.name` field, only `image`.
- The Pod template `spec.containers` has no resource requests/limits.
- `selector.matchLabels` (`app: payment`) does not clearly match the Pod template labels because the indentation is broken, so Kubernetes cannot verify the Deployment can manage its own Pods.

### Corrected YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment
  template:
    metadata:
      labels:
        app: payment
    spec:
      containers:
        - name: payment-api
          image: nginx
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "250m"
              memory: "256Mi"
```

### Short interview answer

"The YAML is broken because every field is at the same indentation level, so the parser can't tell what's nested under `metadata` or `spec`. I'd re-indent it properly (2 spaces per level), add the missing `name` field under each container, and add resource requests/limits, which are missing but important for scheduling and stability."

## 2. Kubernetes Service Selector Mismatch

### The setup

Deployment Pods are labeled:

```yaml
labels:
  app: payment-api
```

But the Service selects:

```yaml
selector:
  app: payment
```

### What is wrong

The Service's `selector` (`app: payment`) does not match the Pod label (`app: payment-api`). A Service only sends traffic to Pods whose labels match its selector exactly (label values, not substrings). Since nothing matches, the Service has **zero endpoints**, so any request to it fails with a connection error.

There's a second issue: `targetPort: 8080` — this only works if the container actually listens on 8080. If the Deployment's container port is different, that's a second reason for failures even after the selector is fixed.

### How to troubleshoot

```bash
kubectl get pods --show-labels
kubectl describe svc payment-service
kubectl get endpoints payment-service
```

`kubectl get endpoints` is the fastest check — if it shows `<none>`, the selector doesn't match any Pod.

### Fix

```yaml
spec:
  selector:
    app: payment-api
  ports:
    - port: 80
      targetPort: 8080
```

### Short interview answer

"Services route traffic based on label selectors, and here the Service selector doesn't match the Pod labels, so it has no endpoints. I'd confirm with `kubectl get endpoints`, then fix the selector to match the actual Pod labels, and double-check `targetPort` matches the port the container listens on."

## 3. Pod Running but Application Unavailable (HTTP 503)

### The situation

All Pods show `Running` and `1/1` ready, but users get HTTP 503.

### Why "Running" doesn't mean "working"

`Running` only means the container process started — it says nothing about whether the app inside is actually healthy or accepting traffic correctly.

### Commands to troubleshoot, in order

```bash
# 1. Confirm the Service has real endpoints
kubectl get endpoints payment-service

# 2. Check readiness — Running pods can still be NotReady
kubectl get pods -o wide

# 3. Look at recent events (crashes, probe failures, scheduling issues)
kubectl describe pod payment-api-6d7f8c9d-x1a2

# 4. Check application logs for errors
kubectl logs payment-api-6d7f8c9d-x1a2
kubectl logs payment-api-6d7f8c9d-x1a2 --previous

# 5. Check if the Ingress/Gateway can reach the Service
kubectl describe ingress payment-ingress

# 6. Test directly from inside the cluster, bypassing Ingress
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  wget -qO- http://payment-service
```

503 from an Ingress/Gateway usually means the upstream Service has no healthy backend — even though Pods show `Running`, they might be failing readiness probes, or the app might be throwing errors on every request (e.g., a bad DB connection) while still staying "up."

### Short interview answer

"Running doesn't mean healthy. I'd check `kubectl get endpoints` first to see if the Service actually has backends, then check readiness state and pod events, then look at application logs, and finally test connectivity directly inside the cluster to isolate whether the problem is the app, the Service, or the Ingress."

## 4. CrashLoopBackOff Caused by OOMKilled

### What the describe output shows

```text
Last State:     Terminated
Reason:         OOMKilled
Exit Code:      137
```

### What this means

`OOMKilled` means the container tried to use more memory than its configured `resources.limits.memory`, so the kernel killed it. Kubernetes then restarts it, it hits the same memory limit again, and gets killed again — that's the crash loop. Exit code 137 = 128 + 9 (SIGKILL), confirming it was force-killed, not a normal app crash.

### What to check next

```bash
kubectl top pod payment-api        # actual memory usage vs limit
kubectl describe pod payment-api   # confirm limits and OOM events
kubectl logs payment-api --previous
```

Then decide:

- Is the limit just too low for normal usage? → Increase `resources.limits.memory`.
- Is the app leaking memory over time? → Fix the leak; increasing the limit only delays the crash.
- Did traffic or batch size spike? → Consider HPA or reducing per-request memory use.

### Short interview answer

"OOMKilled with exit code 137 means the container exceeded its memory limit and the kernel killed it, which causes the restart loop. I'd check actual memory usage with `kubectl top pod` versus the configured limit, look at the app logs for signs of a memory leak, and either raise the memory limit if it's genuinely under-provisioned or fix the leak if usage keeps climbing over time."

## 5. Kubernetes ImagePullBackOff

### The setup

```yaml
containers:
  - name: payment-api
    image: myacr.azurecr.io/payment-api:v25
```

Status: `ImagePullBackOff`

### Possible causes

1. **Tag doesn't exist** — `v25` was never pushed to the registry.
2. **Authentication failure** — the cluster has no (or an expired) `imagePullSecret` for a private ACR.
3. **Wrong registry name** — typo in `myacr.azurecr.io`.
4. **Network/firewall issue** — node can't reach the registry (private endpoint, NSG, DNS).
5. **ACR access not granted to AKS** — AKS's managed identity/kubelet identity was never given `AcrPull` role on that ACR.

### How to troubleshoot

```bash
kubectl describe pod payment-api        # shows the exact pull error message
az acr repository show-tags --name myacr --repository payment-api
az acr show --name myacr --query loginServer
az role assignment list --scope <acr-resource-id>
kubectl get secrets                     # check if an imagePullSecret exists
```

`kubectl describe pod` is the key command — the Events section shows the exact reason (`manifest unknown`, `unauthorized`, `no such host`, etc.), which tells you which of the causes above applies.

### Short interview answer

"ImagePullBackOff usually means the image tag doesn't exist, the registry credentials are missing or expired, or AKS's identity doesn't have `AcrPull` on that ACR. I'd start with `kubectl describe pod` to see the exact error message, then verify the tag exists in ACR and check the role assignment or imagePullSecret depending on what the error says."

## 6. Kubernetes Probes Killing a Slow-Starting App

### The setup

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5

readinessProbe:
  httpGet:
    path: /health
    port: 8080
```

App takes ~60 seconds to start, but the Pod keeps restarting.

### What is wrong

`initialDelaySeconds: 5` means Kubernetes starts checking `/health` after only 5 seconds. Since the app takes 60 seconds to be ready, the liveness probe fails repeatedly during startup. Kubernetes treats liveness failures as "the app is broken" and kills/restarts the container — so it never gets the chance to finish starting. This creates an endless restart loop for an app that was never actually broken.

### The fix

Use a **startupProbe** so the liveness/readiness probes don't even start checking until the app has actually finished booting:

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30
  periodSeconds: 2   # allows up to 60s (30 x 2) for startup

livenessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 5
  failureThreshold: 3
```

If a `startupProbe` isn't available/desired, a simpler (older) fix is to just raise `initialDelaySeconds` past the known startup time, e.g. `initialDelaySeconds: 75`, though this wastes time once the app becomes fast to start again in the future.

### Short interview answer

"The liveness probe starts checking too early — only 5 seconds in — for an app that needs 60 seconds to boot, so Kubernetes kills it mid-startup and it never becomes healthy. The correct fix is to add a `startupProbe` with enough attempts to cover the real startup time, so liveness and readiness checks only begin once the app has actually started."

## 7. Azure DevOps Pipeline Secret Exposure

### The pipeline

```yaml
variables:
  DB_USER: "admin"
  DB_PASSWORD: "Production@123"
  API_KEY: "abc123xyz"

steps:
- script: |
    echo "Deploying application"
    echo "DB Password: $(DB_PASSWORD)"
    echo "API Key: $(API_KEY)"
```

### What is wrong

1. **Secrets are hardcoded in plain text** directly in the YAML, which is normally stored in source control — anyone with repo read access can see the real password and API key.
2. **Secrets are printed to the build log** via `echo`. Even if these were pipeline secret variables, Azure DevOps only masks variables it *knows* are secret — and even then, log masking can be bypassed (e.g., by echoing partial characters), so printing secrets is a bad practice regardless.
3. Non-secret variables like `DB_USER` don't need protecting, but `DB_PASSWORD` and `API_KEY` clearly do and are treated the same as any other plain variable here.

### How to redesign it

- Store secrets in an **Azure Key Vault** and link them into the pipeline via a variable group, or mark them as **secret variables** in the pipeline UI/library (never in the YAML file itself).
- Never `echo` a secret value, even for debugging.

```yaml
variables:
  - group: payment-api-secrets   # variable group linked to Azure Key Vault

steps:
- script: |
    echo "Deploying application"
    ./deploy.sh
  env:
    DB_USER: $(DB_USER)
    DB_PASSWORD: $(DB_PASSWORD)
    API_KEY: $(API_KEY)
```

The script receives the secrets as environment variables at runtime without ever printing or committing them.

### Short interview answer

"There are two problems: real secrets are hardcoded directly in version-controlled YAML, and the script prints them to the build log where anyone with log access can read them. I'd move the secrets into Azure Key Vault, reference them through a linked variable group so they're marked secret and get masked, pass them into the script as environment variables, and remove the `echo` statements that print them entirely."

## 8. Terraform Hardcoded Credentials

### The code

```hcl
provider "azurerm" {
  features {}

  client_id       = "12345678"
  client_secret   = "super-secret-password"
  subscription_id = "abcdef"
  tenant_id       = "xyz"
}
```

### What is wrong

Hardcoding a service principal's `client_id`/`client_secret` directly in `.tf` files means the credentials end up in source control (and in Terraform state, which is even more sensitive). Anyone with repo access — or access to old commits — has standing production credentials.

### How to authenticate securely instead

**Option A — Environment variables (simplest, works locally and in CI):**

```hcl
provider "azurerm" {
  features {}
}
```

```bash
export ARM_CLIENT_ID="..."
export ARM_CLIENT_SECRET="..."
export ARM_SUBSCRIPTION_ID="..."
export ARM_TENANT_ID="..."
```

In Azure DevOps, these are supplied via a **Service Connection** (Azure Resource Manager), and the pipeline uses `AzureCLI@2` or the Terraform task, which injects credentials automatically without ever exposing them in the YAML.

**Option B — Workload Identity Federation / OIDC (preferred, no stored secret at all):**
Azure DevOps issues a short-lived OIDC token that Azure trusts via a federated credential, so there is no long-lived client secret to leak or rotate.

**Option C — Managed Identity** if running from an Azure agent (e.g., a self-hosted agent VM with a system-assigned identity).

### Short interview answer

"Hardcoded client secrets in Terraform files are a serious risk since they land in source control and in state. I'd remove them from the provider block entirely and authenticate through an Azure DevOps service connection using Workload Identity Federation (OIDC) where possible, or environment variables (`ARM_*`) backed by a Key Vault–stored secret otherwise — never committed to the repo."

## 9. Terraform Plan Shows Unexpected Changes for a One-Line Edit

### The situation

```hcl
sku = "Standard"
```

changed to:

```hcl
sku = "Premium"
```

but `terraform plan` shows 15 resources changing.

### Possible reasons

1. **The SKU change forces replacement of a dependent resource**, and other resources reference attributes of that resource (e.g., an ID that changes when it's recreated), cascading the diff outward.
2. **State drift** — someone changed resources manually in the Azure portal/CLI, so Terraform's state no longer matches real infrastructure, and `plan` is now reconciling many unrelated differences at once, not just the SKU change.
3. **A module or provider version was upgraded** around the same time, changing default values or attribute names it manages, so `plan` shows changes across all resources built from that module.
4. **Someone else merged unrelated changes** into the same branch/state that hadn't been applied yet.
5. **A shared variable or `for_each`/`count` value changed indirectly** (e.g., a computed variable used across many resources), so a "small" edit ripples widely.

### Troubleshooting approach

```bash
terraform plan -out=tfplan
terraform show -json tfplan | jq '.resource_changes[] | {address, change: .change.actions}'
git log -p <file>              # confirm only the intended line changed
terraform state list
terraform plan -target=<resource>   # isolate the change to just the SKU resource
```

Compare the plan's "before/after" values resource by resource to see whether the extra changes are genuinely caused by the SKU change (cascading dependency) or are unrelated drift.

### Short interview answer

"A one-line SKU change causing 15 resources to change usually means either that SKU forces a resource replacement whose ID/attributes other resources depend on, or there's state drift from manual changes outside Terraform. I'd run `terraform plan -out` and inspect the JSON output per resource to see exactly what's changing and why, and use `-target` to isolate whether it's a real dependency chain or unrelated drift that needs a `terraform refresh`/import to reconcile."

## 10. Terraform State Conflict from Two Simultaneous Pipelines

### The situation

Pipeline A and Pipeline B both run `terraform apply` against the same Azure infrastructure at the same time.

### What can go wrong

- **State corruption** — both pipelines try to write to the same state file at once, and whichever writes last can overwrite the other's changes, silently losing work.
- **Conflicting real-world changes** — both plans were calculated against the same "before" state, so both may try to create/modify/delete the same resource, causing Azure API errors or duplicate resources.
- **Partial applies** — if Pipeline A is mid-apply (some resources changed, others not) when Pipeline B starts planning, B's plan is based on an inconsistent, half-updated state.

### How to prevent it

1. **Use a remote backend with state locking** — Azure Storage backend supports locking via blob leases automatically:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstateacct"
    container_name       = "tfstate"
    key                  = "payment-api.tfstate"
  }
}
```

With this, the second `apply` will block/fail with a "state locked" error until the first finishes, instead of running concurrently.

2. **Serialize pipeline runs** — in Azure DevOps, use `resources.pipelines` triggers or a pipeline-level lock (e.g., an exclusive lock resource / environment approval gate) so only one Terraform pipeline can run against a given environment at a time.
3. **Separate state per environment/component** so unrelated pipelines aren't even touching the same state file.

### Short interview answer

"Running two `terraform apply`s against the same state at the same time risks state corruption and conflicting resource changes. The fix is to use a remote backend that supports locking — like the `azurerm` backend on Azure Storage, which uses blob leases — so the second pipeline is blocked until the first finishes, combined with pipeline-level concurrency control so only one deployment can run per environment at a time."

## 11. Shell Script for 500 Servers

### The script

```bash
#!/bin/bash

for server in $(cat servers.txt)
do
    ssh $server "df -h"
    ssh $server "systemctl status nginx"
done
```

### Problems

1. **Fully sequential** — with 500 servers, this runs one SSH connection at a time; if each takes even a few seconds, the whole run takes a very long time.
2. **No error handling** — if a server is unreachable, the script just moves to the next one with no logging of the failure, no exit code check, and no summary of failures.
3. **Unquoted variable** (`$server`) — breaks on any hostname with spaces or unexpected characters, and is generally unsafe shell practice.
4. **Two separate SSH connections per server** — doubles connection overhead; both commands could run in one SSH session.
5. **No timeout** — a single unreachable/hanging server can block the whole script indefinitely (no `ConnectTimeout`).
6. **No parallelism control** — running all 500 at once could also overwhelm the network/local machine, so unlimited parallelism isn't safe either.

### Improved version for production

```bash
#!/bin/bash
set -uo pipefail

SERVERS_FILE="servers.txt"
MAX_PARALLEL=20
TIMEOUT=10

check_server() {
    local server="$1"
    if ! ssh -o ConnectTimeout="$TIMEOUT" -o BatchMode=yes "$server" \
        "df -h && systemctl status nginx" > "logs/${server}.log" 2>&1; then
        echo "FAILED: $server"
    else
        echo "OK: $server"
    fi
}
export -f check_server
export TIMEOUT

mkdir -p logs

xargs -a "$SERVERS_FILE" -P "$MAX_PARALLEL" -I{} bash -c 'check_server "$@"' _ {}
```

Key improvements:
- `xargs -P` runs checks in parallel with a controlled limit (20 at a time), instead of one at a time.
- `-o ConnectTimeout` prevents one dead server from hanging the whole run.
- Each server's output is logged to its own file for later review.
- Success/failure is printed per server instead of silently continuing.

### Short interview answer

"With 500 servers, running SSH sequentially is far too slow and has no error handling — a hung or unreachable server can block everything indefinitely. I'd add `ConnectTimeout` to fail fast on unreachable hosts, run checks in parallel with a controlled concurrency limit using something like `xargs -P`, log each server's output to its own file, and print a clear success/failure summary instead of silently continuing past errors."

## 12. Shell Script Error Handling

### The script

```bash
#!/bin/bash

cp /backup/app.tar.gz /tmp/
tar -xzf /tmp/app.tar.gz
systemctl restart nginx

echo "Deployment successful"
```

### What happens with the current script?

If:

```bash
cp /backup/app.tar.gz /tmp/
```

fails, the script continues executing by default.

So the flow is:

```text
cp fails
  ↓
tar -xzf /tmp/app.tar.gz
  ↓
systemctl restart nginx
  ↓
echo "Deployment successful"
```

The `tar` command may also fail because the archive wasn't copied, but the script still continues.

Worst case, `systemctl restart nginx` could restart the service using an old or partially updated deployment, and the script still prints:

```text
Deployment successful
```

That's incorrect.

### Simple fix: `set -e`

```bash
#!/bin/bash
set -e

cp /backup/app.tar.gz /tmp/
tar -xzf /tmp/app.tar.gz
systemctl restart nginx

echo "Deployment successful"
```

Now:

```text
cp fails
  ↓
Script exits
  ↓
tar is NOT executed
  ↓
nginx is NOT restarted
  ↓
"Deployment successful" is NOT printed
```

This is the basic answer expected in an interview.

### Better production version

```bash
#!/bin/bash
set -euo pipefail

cp /backup/app.tar.gz /tmp/
tar -xzf /tmp/app.tar.gz
systemctl restart nginx

echo "Deployment successful"
```

### What does `set -euo pipefail` mean?

**`set -e`** — Exit when a command fails.
`cp file /tmp/` fails → script exits.

**`set -u`** — Treat undefined variables as errors.
For example: `echo "$APP_VERSION"` — if `APP_VERSION` was never defined, the script fails instead of silently continuing.

**`set -o pipefail`** — Normally, in `command1 | command2`, the exit status is usually based on the last command. With `pipefail`, the pipeline fails if an earlier command fails.

### Add explicit error handling

```bash
#!/bin/bash
set -euo pipefail

echo "Starting deployment..."

if ! cp /backup/app.tar.gz /tmp/app.tar.gz; then
    echo "ERROR: Failed to copy application archive"
    exit 1
fi

if ! tar -xzf /tmp/app.tar.gz -C /opt/app; then
    echo "ERROR: Failed to extract application archive"
    exit 1
fi

if ! systemctl restart nginx; then
    echo "ERROR: Failed to restart nginx"
    exit 1
fi

echo "Deployment successful"
```

This gives you a clear failure point.

### One important interview detail

Don't blindly say "`set -e` makes every Bash script fail safely." Bash has some contexts where `set -e` behaves differently, particularly around conditions, `&&`, `||`, `if`, loops, and pipelines.

For critical deployment automation, combine `set -euo pipefail` with explicit checks around important operations.

### Strong interview answer

"By default, Bash does not stop when a command fails. If `cp` fails, the script continues to `tar`, then potentially restarts nginx, and finally prints 'Deployment successful'. That's dangerous because the deployment could be incomplete. I would use `set -euo pipefail` so unexpected command failures stop the script, and for critical deployment steps I would also use explicit error handling with `if ! command; then ... exit 1; fi` so the failure is clearly logged."

### Remember

Without error handling: `cp fails → script continues` ❌
With `set -e`: `cp fails → script stops` ✅
Production: `set -euo pipefail` + explicit checks for critical operations

## 13. Shell Script Disk Monitoring Bug

### The script

```bash
DISK=$(df -h / | awk 'NR==2 {print $5}')

if [ $DISK -gt 80 ]; then
    echo "Disk usage is high"
fi
```

### The bug

`df -h` prints the usage column with a `%` sign, e.g. `85%`. So `$DISK` holds the string `85%`, not the number `85`. The comparison:

```bash
[ 85% -gt 80 ]
```

fails with an "integer expression expected" error, because `-gt` needs a plain integer, not a string with a `%` at the end.

### The fix

Strip the `%` sign before comparing, and avoid `-h` (human-readable units like `1.2G` also break numeric comparisons) — use plain block output instead:

```bash
DISK=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$DISK" -gt 80 ]; then
    echo "Disk usage is high"
fi
```

`df -P` gives POSIX-standard single-line output (avoids line-wrapping issues with very long device names), and `tr -d '%'` removes the percent sign so `$DISK` is a clean integer.

### Short interview answer

"The bug is that `df -h` includes a `%` sign in the usage field, so the variable holds something like `85%`, and comparing that with `-gt` in a numeric test fails or behaves unexpectedly. The fix is to strip the `%` character with `tr -d '%'` before the comparison, and use `df -P` instead of `-h` for reliable single-line, script-friendly output."

## 14. Jenkins Pipeline Security

### The pipeline

```groovy
pipeline {
    agent any

    stages {
        stage('Deploy') {
            steps {
                sh '''
                    export DB_PASSWORD="Prod123"
                    ./deploy.sh
                '''
            }
        }
    }
}
```

### Security issues

1. **Hardcoded credential in the Jenkinsfile** — `Prod123` is in plain text in source control, visible to anyone with repo read access, and preserved forever in git history even if later removed.
2. **Printed in Jenkins console logs** — depending on how `deploy.sh` uses the variable, it can easily end up echoed to the build console, which many users can view.
3. **`agent any`** — runs on any available agent, including potentially untrusted or shared agents, without restricting where sensitive credentials are used.
4. **No credential rotation/central management** — changing the password means editing and redeploying the Jenkinsfile.

### Secure fix — use Jenkins Credentials

```groovy
pipeline {
    agent any

    environment {
        DB_PASSWORD = credentials('db-password-prod')
    }

    stages {
        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

The secret `db-password-prod` is stored in Jenkins' built-in Credentials store (or backed by a vault plugin), Jenkins automatically masks it in console output, and it's injected as an environment variable at runtime — never written in the Jenkinsfile itself.

### Short interview answer

"The password is hardcoded directly in the Jenkinsfile, which means it's stored in plain text in version control and could leak into build logs. I'd store it in Jenkins Credentials (or an external vault) and reference it with `credentials('db-password-prod')` in the `environment` block, so Jenkins injects it at runtime and automatically masks it in the console output, instead of it ever appearing in source code."

## 15. Jenkins Declarative Pipeline Missing Structure

### The pipeline

```groovy
pipeline {
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }

        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

### What is missing or incorrect

1. **No `agent` block** — a declarative pipeline requires a top-level `agent` (e.g., `agent any` or a specific label); without it, the pipeline won't even validate/run.
2. **No `post` block** — there's no cleanup, notification, or failure handling (e.g., sending a Slack/email alert on failure, archiving artifacts, cleaning workspace).
3. **No test stage** — going straight from `Build` to `Deploy` skips running automated tests, which is risky for production deployments.
4. **No `options`** — things like `timeout()`, `retry()`, or `disableConcurrentBuilds()` are missing, so a hung build could run forever or two deploys could overlap.
5. **Deploy has no gate/approval** — going straight to deploy after build with no manual approval or environment check is risky for production pipelines.

### Corrected structure

```groovy
pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }

        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }

        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully'
        }
        failure {
            echo 'Pipeline failed - notifying team'
        }
        always {
            cleanWs()
        }
    }
}
```

### Short interview answer

"This pipeline is missing the required top-level `agent`, has no test stage before deploying, and has no `post` block for failure notifications or cleanup. I'd add `agent any`, insert a `Test` stage between build and deploy, add `options` like a timeout and `disableConcurrentBuilds`, and add a `post` block to handle success/failure notifications and workspace cleanup."

## 16. Dockerfile Security, Reliability, and Optimization

### The Dockerfile

```dockerfile
FROM ubuntu:latest

RUN apt-get update
RUN apt-get install -y openjdk-17-jdk

COPY . /app

ENV DB_PASSWORD=Production123

WORKDIR /app

CMD ["java", "-jar", "app.jar"]
```

### Problems

**Security:**
- `ENV DB_PASSWORD=Production123` bakes a real secret into the image layers — anyone who can pull or inspect the image (`docker history`) can see it.
- `ubuntu:latest` is an unpinned, mutable tag — the image can silently change over time, breaking reproducibility and potentially introducing vulnerabilities.
- No non-root user — the container runs as `root` by default, which is a bigger blast radius if the app is compromised.
- Installs the full JDK (includes compilers/dev tools) instead of just a JRE, growing the attack surface unnecessarily.

**Reliability:**
- `RUN apt-get update` on its own line, separate from `apt-get install`, can use a stale cached layer for `update` while installing a newer package list — a classic Docker caching pitfall. They should be combined in one `RUN`.
- No version pinning for `openjdk-17-jdk` — install could silently pull a different patch version between builds.
- `COPY . /app` copies everything, including potentially unnecessary files (`.git`, local configs, secrets) — no `.dockerignore` mentioned.

**Image size / optimization:**
- `ubuntu:latest` + full JDK is a large base; no multi-stage build to strip build-time dependencies from the final image.

### Corrected Dockerfile

```dockerfile
FROM eclipse-temurin:17-jre-jammy

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

COPY --chown=appuser:appgroup target/app.jar /app/app.jar

USER appuser

CMD ["java", "-jar", "app.jar"]
```

The `DB_PASSWORD` should never be baked into the image — it should be injected at runtime via `docker run -e DB_PASSWORD=...` (sourced from a secrets manager), or via Kubernetes Secrets if deployed there.

### Short interview answer

"There are three categories of problems here: security — a real secret baked into the image via `ENV`, and the container running as root; reliability — `apt-get update` and `install` split into separate `RUN` layers, which can install against a stale package index, plus an unpinned `ubuntu:latest` base; and size — using a full JDK and Ubuntu base instead of a slim JRE image. I'd switch to a pinned, JRE-only base image, add a non-root user, remove the hardcoded secret and inject it at runtime instead, and combine related `RUN` steps."

## 17. Docker Image Optimization for a React App

### The Dockerfile

```dockerfile
FROM node:18

WORKDIR /app

COPY . .

RUN npm install
RUN npm run build

CMD ["npm", "start"]
```

### Problems

1. **Ships the entire Node toolchain** (`node:18` full image, ~1GB+) into production, even though a built React app is just static HTML/CSS/JS files that don't need Node at runtime at all.
2. **No multi-stage build** — build-time dependencies (devDependencies, build tools, source files) all end up in the final image.
3. **`COPY . .` before `npm install`** breaks Docker layer caching — any source code change invalidates the cache for `npm install`, forcing a full reinstall on every build even when `package.json` didn't change.
4. **`npm start`** typically runs a dev server (e.g., `react-scripts start`), which is not meant for production — it's slower and not optimized for serving static files at scale.

### Optimized multi-stage Dockerfile

```dockerfile
# --- Build stage ---
FROM node:18 AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Production stage ---
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Improvements:
- **Multi-stage build**: Node is only used to build the static files; the final image is just `nginx:alpine` (a few MB) serving static content — no Node, no source code, no `node_modules` in production.
- **Better layer caching**: copying `package*.json` first means `npm ci` only re-runs when dependencies actually change, not on every source edit.
- **`npm ci` instead of `npm install`**: faster, reproducible installs based on `package-lock.json`.
- **Nginx serves static files properly** with production-grade performance instead of a Node dev server.

### Short interview answer

"A built React app is just static files, so shipping the full Node image to run `npm start` is unnecessarily large and uses a dev server not meant for production. I'd use a multi-stage build — build the app in a `node` stage with `npm ci`, then copy only the compiled `build` output into a lightweight `nginx:alpine` stage to actually serve it. I'd also copy `package.json` before the rest of the source so Docker can cache the dependency install layer properly."

## 18. Application Gateway → AKS → PostgreSQL: HTTP 502/504 with Healthy Pods

### The architecture

```text
Internet
   |
Azure Application Gateway
   |
AKS Ingress
   |
Service
   |
Pods
   |
PostgreSQL
```

Pods show `1/1 Running`, but users get HTTP 502/504.

### Why healthy pods don't rule this out

502/504 are gateway-level errors — they mean something *in front of* the app failed to get a valid/timely response, which can happen even if the Pods themselves are running fine. The problem could be at any hop in the chain.

### Troubleshooting approach, layer by layer

**1. Application Gateway layer**
```bash
az network application-gateway show-backend-health \
  --resource-group <rg> --name <appgw-name>
```
Check if App Gateway considers the backend pool healthy. A 502 often means App Gateway couldn't reach its configured backend (misconfigured health probe path, backend pool pointing to the wrong target, or an expired/mismatched TLS cert on the backend).

**2. Ingress / Service layer**
```bash
kubectl get ingress
kubectl describe ingress payment-ingress
kubectl get endpoints payment-service
kubectl logs -n <ingress-namespace> <ingress-controller-pod>
```
Confirm the Ingress is correctly routing to the Service, and the Service has healthy endpoints.

**3. Pod / application layer**
```bash
kubectl logs <pod> --tail=100
kubectl top pod
```
A 504 (timeout) often means the app is alive but responding too slowly — check CPU throttling (`resources.limits.cpu` too low), thread pool exhaustion, or slow downstream calls.

**4. Database layer**
```bash
kubectl exec -it <pod> -- pg_isready -h <postgres-host>
```
Check PostgreSQL connection pool exhaustion, slow queries, or network latency/connectivity from AKS to PostgreSQL (especially if PostgreSQL is behind a private endpoint/VNet peering — check NSGs and DNS resolution).

**5. Timeouts across layers**
Confirm that App Gateway's request timeout, the Ingress controller's proxy timeout, and any app-level timeout to PostgreSQL are all consistent — a common 504 cause is App Gateway timing out *before* a legitimately slow backend (e.g., a slow DB query) finishes.

### Short interview answer

"502/504 with healthy pods means the problem isn't the container process itself — it's somewhere in the request path or the app is too slow to respond. I'd work through the chain in order: check Application Gateway's backend health and probe config, confirm the Ingress and Service actually have healthy endpoints, check the pod's CPU/memory and logs for slow responses, and then check PostgreSQL for connection pool exhaustion or slow queries — also comparing timeout settings across App Gateway, Ingress, and the app, since a mismatched timeout is a very common cause of 504s."

## 19. CI/CD Pipeline Failing at the Trivy Security Scan

### The pipeline

```text
Build → Test → SonarQube → Docker Build → Trivy Scan → Push ACR → Deploy Dev → Approval → Deploy Prod
```

Trivy stage fails with:

```text
CRITICAL vulnerabilities found
Exit code: 1
```

### What I would do next

**I would not bypass Trivy and deploy anyway.** A CRITICAL vulnerability finding exists specifically to block deployment of known, exploitable weaknesses — pushing past it defeats the purpose of having the scan in the pipeline at all, and could ship a real security hole to production.

Instead:

1. **Review the actual findings** — Trivy's report names the specific CVEs, the affected package, and the severity. Not all "CRITICAL" findings are equally urgent (e.g., a CVE in a library function the app never calls is lower real-world risk than one in an internet-facing component).
2. **Check if a fixed version exists** — often the fix is simply updating a base image or dependency to a patched version.
3. **Rebuild and rescan** after the fix to confirm the vulnerability is resolved.
4. **If there's a genuine false positive or accepted risk** (e.g., the vulnerable code path is unreachable, or it's a transitive dependency with no fix available yet), document a formal exception/waiver with the security team's sign-off, and use Trivy's `.trivyignore` mechanism to suppress that specific CVE with a comment explaining why — not to silence the whole scan.
5. **Escalate the timeline** if the fix will take time — communicate the delay rather than silently skipping the gate.

```bash
# example: targeted, documented ignore (not a blanket bypass)
# .trivyignore
CVE-2023-XXXXX  # accepted risk: unreachable code path, tracked in JIRA-1234, review by 2026-09-01
```

### Short interview answer

"I would not bypass a CRITICAL finding just to keep the pipeline moving — that's exactly the scenario the scan exists to prevent. I'd look at the actual CVE details to see if a patched base image or dependency version is available, fix and rescan, and only if there's a genuine false positive or an accepted, time-boxed risk would I use a targeted `.trivyignore` entry with sign-off and a tracking ticket — never a blanket bypass of the whole Trivy stage."

## 20. Azure DevOps Pipeline Not Triggering for Feature Branches

### The YAML

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - script: echo "Build started"
```

A developer pushes to `feature/payment-api`, but the pipeline doesn't run.

### Is this expected?

**Yes.** The `trigger` section explicitly lists only `main`, so Azure DevOps only creates a CI run automatically for pushes to `main`. Pushing to any other branch, including `feature/payment-api`, simply doesn't match the trigger and is correctly skipped — this isn't a bug.

### Fix — trigger on both `main` and `feature/*`

```yaml
trigger:
  branches:
    include:
      - main
      - feature/*

pool:
  vmImage: ubuntu-latest

steps:
  - script: echo "Build started"
```

Using `branches: include:` (instead of the short list form) is required once you need wildcard patterns like `feature/*`.

### Short interview answer

"Yes, this is expected — the trigger only lists `main`, so pushes to any other branch, including `feature/payment-api`, are correctly ignored by design, not a bug. To make it trigger for both, I'd rewrite the trigger using the `branches: include:` form with both `main` and `feature/*` listed, since wildcard patterns require that expanded syntax instead of the short list form."
