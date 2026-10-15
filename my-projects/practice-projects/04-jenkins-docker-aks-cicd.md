# Practice Project 4: Jenkins CI/CD Pipeline to Build, Push to ACR and Deploy to AKS

> This guide shows how to build a Jenkins pipeline that tests a small Flask app, builds a Docker image, pushes it to Azure Container Registry (ACR) and deploys it to Azure Kubernetes Service (AKS) using a separate build agent with a managed identity.

## Key Concepts

### What you will build

You will build a complete CI/CD flow driven by Jenkins:

- A **Jenkins controller** running as a Docker container on a small Azure VM. It only schedules jobs and stores configuration.
- A **Jenkins build agent** on a second Azure Ubuntu VM. It has Docker, Azure CLI, `kubectl` and `kubelogin` installed, and a **system-assigned managed identity**, so no Azure passwords are stored in Jenkins.
- An **ACR** registry for images and an **AKS** cluster with Microsoft Entra ID authentication and Azure RBAC.
- A **declarative Jenkinsfile** with stages: Checkout, Build, Test, Docker Build, Push, Deploy.
- A **GitHub webhook** so every push to `main` starts the pipeline automatically.

Final result: you push a commit to GitHub, Jenkins runs the pipeline, and a few minutes later `curl http://<external-ip>/` returns JSON with the new version (for example `"version": "15-a1b2c3d"`). If a deployment fails, Jenkins rolls back automatically with `kubectl rollout undo`.

### Architecture

```text
 Developer
    |  git push
    v
 GitHub repo ----(webhook: /github-webhook/)----> Jenkins controller (VM 1, Docker container)
                                                     |  schedules job over SSH
                                                     v
                                          Jenkins agent (VM 2, label: azure-docker)
                                          - Docker, Azure CLI, kubectl, kubelogin
                                          - System-assigned managed identity
                                                     |
               +-------------------------------------+-----------------------------+
               | az login --identity                 |                             |
               v                                     v                             v
        docker build + test              az acr login + docker push      az aks get-credentials
                                                     |                    kubelogin convert-kubeconfig -l msi
                                                     v                    kubectl apply / rollout status
                                         ACR (<acr-name>.azurecr.io)               |
                                                     ^                             v
                                                     |   AcrPull (--attach-acr)   AKS cluster
                                                     +---------------------- namespace: demo
                                                                             Deployment (2 pods)
                                                                             Service (LoadBalancer)
                                                                                   |
                                                                                   v
                                                                       Users: http://<external-ip>/
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Jenkins (LTS) | Runs the CI/CD pipeline defined in the Jenkinsfile | Widely used, very flexible, pipeline as code |
| Jenkins SSH agent | Runs the actual build steps on a separate VM | Keeps the controller safe and light |
| Docker | Builds and runs the app image, runs tests in a clean container | Same image runs in test and in AKS |
| Azure Container Registry | Stores the Docker images | Private registry with Entra ID auth, close to AKS |
| Azure Kubernetes Service | Runs the app containers | Managed Kubernetes, no control plane to maintain |
| Azure CLI | Logs in with managed identity, logs in to ACR, gets AKS credentials | Official CLI, supports `--identity` |
| kubectl | Applies manifests and checks rollout status | Standard Kubernetes CLI |
| kubelogin | Converts kubeconfig to use managed identity tokens | Required for Entra ID enabled AKS in non-interactive use |
| Managed identity | Gives the agent VM an Azure identity | No secrets to store or rotate |
| GitHub webhook | Triggers Jenkins on push | Faster and cheaper than polling |

### Prerequisites

- An Azure subscription where you are **Owner** (or Contributor + User Access Administrator). `--attach-acr` and role assignments need permission to create role assignments.
- A GitHub account and a repository for the app.
- On your laptop:
  - Azure CLI 2.60 or newer: `az version`
  - `kubectl` and `kubelogin`: `az aks install-cli`
  - Git and an SSH client
- Basic Linux and Docker knowledge.

Cost warning: this lab uses two small VMs, an AKS cluster with two nodes, a public load balancer and a Basic ACR. Expect a few US dollars per day. Stop VMs when not in use and delete everything at the end (see Clean up).

### Folder structure

```text
flask-jenkins-aks/
├── app.py                  # Flask application
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Test dependencies
├── tests/
│   └── test_app.py         # Unit tests
├── Dockerfile              # Container image definition
├── Jenkinsfile             # Declarative pipeline
└── k8s/
    ├── deployment.yaml     # Deployment with probes and resources
    └── service.yaml        # LoadBalancer Service
```

### Step-by-step

#### Step 1: Set variables and create the resource group

Use shell variables so every command uses the same names. ACR names must be globally unique and use only lowercase letters and numbers.

```bash
az login
az account set --subscription "<subscription-id>"

export LOCATION="eastus"
export RG="rg-jenkins-aks-lab"
export ACR="<acr-name>"            # example: acrjenkinslab12345
export AKS="aks-jenkins-lab"
export VNET="vnet-jenkins"
export SUBNET="snet-jenkins"

az group create --name "$RG" --location "$LOCATION"
```

What this does:

- `az account set` makes sure you work in the right subscription.
- All resources go into one resource group, so cleanup is one command.

#### Step 2: Create ACR and AKS

Create the registry first, then the cluster with `--attach-acr`. This gives the AKS kubelet identity the `AcrPull` role, so nodes can pull images without an image pull secret.

```bash
az acr create \
  --resource-group "$RG" \
  --name "$ACR" \
  --sku Basic

az aks create \
  --resource-group "$RG" \
  --name "$AKS" \
  --location "$LOCATION" \
  --tier free \
  --node-count 2 \
  --node-vm-size Standard_D2s_v5 \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --enable-aad \
  --enable-azure-rbac \
  --attach-acr "$ACR" \
  --generate-ssh-keys
```

What this does:

- `--sku Basic` is the cheapest ACR tier, fine for a lab.
- `--network-plugin azure --network-plugin-mode overlay` uses Azure CNI Overlay, so pods get IPs from a private overlay range and do not use up VNet IPs.
- `--enable-aad --enable-azure-rbac` turns on Microsoft Entra ID login and lets you use Azure role assignments for Kubernetes permissions.
- `--attach-acr` creates an `AcrPull` role assignment for the cluster's kubelet identity on the registry.

#### Step 3: Give yourself admin access and create the namespace

With Azure RBAC for Kubernetes, even a subscription Owner has no permission inside the cluster until a data-plane role is assigned.

```bash
AKS_ID=$(az aks show -g "$RG" -n "$AKS" --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)

az role assignment create \
  --assignee "$ME" \
  --role "Azure Kubernetes Service RBAC Cluster Admin" \
  --scope "$AKS_ID"

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubelogin convert-kubeconfig -l azurecli

kubectl create namespace demo
kubectl get nodes
```

What this does:

- Assigns you cluster admin through Azure RBAC. Role assignments can take 2-5 minutes to take effect; retry if you get `Forbidden`.
- `kubelogin convert-kubeconfig -l azurecli` makes `kubectl` reuse your `az login` session instead of opening a browser.
- Creates the `demo` namespace where Jenkins will deploy.

#### Step 4: Create the network and the Jenkins controller VM

The controller runs the Jenkins UI. It needs a public IP so GitHub can send webhooks. The agent will be in the same VNet without a public IP.

```bash
az network vnet create \
  -g "$RG" -n "$VNET" \
  --address-prefixes 10.10.0.0/16 \
  --subnet-name "$SUBNET" \
  --subnet-prefixes 10.10.1.0/24

az vm create \
  -g "$RG" -n vm-jenkins-controller \
  --image Ubuntu2404 \
  --size Standard_B2ms \
  --vnet-name "$VNET" --subnet "$SUBNET" \
  --admin-username azureuser \
  --generate-ssh-keys

MY_IP=$(curl -s https://api.ipify.org)

az network nsg rule create \
  -g "$RG" --nsg-name vm-jenkins-controllerNSG \
  -n allow-jenkins-ui --priority 1010 \
  --source-address-prefixes "$MY_IP/32" \
  --destination-port-ranges 8080 \
  --protocol Tcp --access Allow
```

What this does:

- `Ubuntu2404` is the Ubuntu 24.04 LTS image alias.
- The NSG rule opens port 8080 only to your IP. For GitHub webhooks, also add the `hooks` IP ranges from `https://api.github.com/meta`, or use a reverse proxy with HTTPS in front of Jenkins.
- `az vm create` names the NSG `<vm-name>NSG` by default. Check with `az network nsg list -g "$RG" -o table` if the name differs.

#### Step 5: Run the Jenkins controller in Docker

SSH to the controller VM, install Docker and start the official Jenkins LTS image with a named volume, so data survives container restarts.

```bash
CONTROLLER_IP=$(az vm show -d -g "$RG" -n vm-jenkins-controller --query publicIps -o tsv)
ssh azureuser@"$CONTROLLER_IP"

# On the controller VM
curl -fsSL https://get.docker.com | sudo sh
sudo docker volume create jenkins_home
sudo docker run -d --name jenkins --restart unless-stopped \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  jenkins/jenkins:lts-jdk21

sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

What this does:

- `jenkins/jenkins:lts-jdk21` is the Long Term Support image on Java 21.
- Port 8080 is the web UI. Port 50000 is only needed for inbound (JNLP) agents; you can skip it if you only use SSH agents.
- The last command prints the one-time unlock password. Open `http://<controller-ip>:8080`, paste it, choose "Install suggested plugins" and create an admin user.

#### Step 6: Install the required plugins

You can install plugins in **Manage Jenkins > Plugins > Available plugins**, or from the command line.

```bash
sudo docker exec jenkins jenkins-plugin-cli --plugins \
  workflow-aggregator \
  workflow-multibranch \
  git \
  github-branch-source \
  credentials-binding \
  docker-workflow \
  ssh-slaves \
  junit \
  azure-credentials

sudo docker restart jenkins
```

What this does:

| Plugin ID | Plugin name | Why it is needed |
| --- | --- | --- |
| `workflow-aggregator` | Pipeline | Declarative and scripted pipelines |
| `workflow-multibranch` | Pipeline: Multibranch | One job that discovers all branches and PRs |
| `git` | Git | `checkout scm` from Git repositories |
| `github-branch-source` | GitHub Branch Source | GitHub multibranch source and webhook handling |
| `credentials-binding` | Credentials Binding | `withCredentials` to inject secrets safely |
| `docker-workflow` | Docker Pipeline | `docker.build()` and `docker.image()` steps (optional here, we use `sh docker ...`) |
| `ssh-slaves` | SSH Build Agents | Launch agents over SSH |
| `junit` | JUnit | Show test results in the build page |
| `azure-credentials` | Azure Credentials (optional) | Store a service principal if you do not use managed identity |

#### Step 7: Stop builds on the controller

The controller holds all credentials and job configuration. A build runs any code in the repository, so a malicious or buggy build on the controller can read secrets or break Jenkins.

Go to **Manage Jenkins > Nodes > Built-In Node > Configure** and set **Number of executors** to `0`.

What this does:

- Jobs can no longer run on the controller, only on agents.
- The controller stays fast and stable because heavy Docker builds use the agent's CPU and disk.
- If an agent is compromised or full, you replace the agent VM, not your whole Jenkins.

#### Step 8: Create the build agent VM with a managed identity

The agent has no public IP. It gets a system-assigned managed identity, which Azure CLI can use with `az login --identity`.

```bash
az vm create \
  -g "$RG" -n vm-jenkins-agent \
  --image Ubuntu2404 \
  --size Standard_D2s_v5 \
  --vnet-name "$VNET" --subnet "$SUBNET" \
  --public-ip-address "" \
  --nsg "" \
  --assign-identity \
  --admin-username azureuser \
  --generate-ssh-keys

AGENT_IP=$(az vm show -d -g "$RG" -n vm-jenkins-agent --query privateIps -o tsv)
AGENT_PRINCIPAL_ID=$(az vm show -g "$RG" -n vm-jenkins-agent --query identity.principalId -o tsv)
echo "$AGENT_IP $AGENT_PRINCIPAL_ID"
```

What this does:

- `--public-ip-address ""` means the agent is reachable only inside the VNet.
- `--nsg ""` skips the per-NIC NSG; the agent has no public exposure anyway. In a real setup, attach an NSG to the subnet.
- `--assign-identity` without a value creates a system-assigned managed identity.
- `AGENT_PRINCIPAL_ID` is the identity's object ID, used for role assignments in the next step.

#### Step 9: Grant the agent identity access to ACR and AKS

Give the identity only what the pipeline needs: push images, get cluster credentials, and write resources in the `demo` namespace.

```bash
ACR_ID=$(az acr show -n "$ACR" --query id -o tsv)
AKS_ID=$(az aks show -g "$RG" -n "$AKS" --query id -o tsv)

az role assignment create --assignee-object-id "$AGENT_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role AcrPush --scope "$ACR_ID"

az role assignment create --assignee-object-id "$AGENT_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Azure Kubernetes Service Cluster User Role" --scope "$AKS_ID"

az role assignment create --assignee-object-id "$AGENT_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Azure Kubernetes Service RBAC Writer" \
  --scope "$AKS_ID/namespaces/demo"
```

What this does:

- `AcrPush` allows pull and push of images. It does not allow deleting the registry.
- `Azure Kubernetes Service Cluster User Role` allows `az aks get-credentials` (download the user kubeconfig). It gives no rights inside Kubernetes by itself.
- `Azure Kubernetes Service RBAC Writer` scoped to `/namespaces/demo` allows creating and updating Deployments and Services only in that namespace. This is least privilege.
- If your cluster uses Kubernetes RBAC instead of Azure RBAC, create a `RoleBinding` for the identity's object ID instead of the third assignment.

#### Step 10: Install tools on the agent

SSH to the agent through the controller (jump host) and install Java (needed by the Jenkins agent process), Docker, Azure CLI, kubectl and kubelogin.

```bash
ssh -J azureuser@"$CONTROLLER_IP" azureuser@"$AGENT_IP"

# On the agent VM
sudo apt-get update
sudo apt-get install -y openjdk-21-jre-headless git curl ca-certificates

curl -fsSL https://get.docker.com | sudo sh
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
sudo az aks install-cli

sudo useradd -m -s /bin/bash jenkins
sudo usermod -aG docker jenkins
sudo mkdir -p /home/jenkins/.ssh /home/jenkins/agent
sudo chown -R jenkins:jenkins /home/jenkins

java -version && docker --version && az version -o table && kubectl version --client && kubelogin --version
```

What this does:

- Java 21 runs the `agent.jar` that Jenkins copies over SSH.
- `az aks install-cli` installs both `kubectl` and `kubelogin` into `/usr/local/bin`.
- The `jenkins` user is in the `docker` group, so builds can run `docker` without `sudo`. Note: docker group membership is effectively root on that VM, which is another reason to keep builds off the controller.

#### Step 11: Connect the agent to Jenkins over SSH

Create a key pair for the controller to log in as the `jenkins` user on the agent.

```bash
# On your laptop
ssh-keygen -t ed25519 -f ./jenkins_agent_key -N "" -C "jenkins-agent"

# Copy the public key to the agent
cat jenkins_agent_key.pub | ssh -J azureuser@"$CONTROLLER_IP" azureuser@"$AGENT_IP" \
  "sudo tee /home/jenkins/.ssh/authorized_keys >/dev/null && \
   sudo chown jenkins:jenkins /home/jenkins/.ssh/authorized_keys && \
   sudo chmod 600 /home/jenkins/.ssh/authorized_keys"
```

Then in Jenkins:

1. **Manage Jenkins > Credentials > System > Global > Add Credentials**
   - Kind: `SSH Username with private key`
   - ID: `agent-ssh-key`
   - Username: `jenkins`
   - Private key: paste the content of `jenkins_agent_key`
2. **Manage Jenkins > Nodes > New Node**
   - Name: `azure-agent-1`, type: Permanent Agent
   - Number of executors: `2`
   - Remote root directory: `/home/jenkins/agent`
   - Labels: `azure-docker`
   - Usage: "Only build jobs with label expressions matching this node"
   - Launch method: "Launch agents via SSH", Host: `<agent-private-ip>`, Credentials: `agent-ssh-key`
   - Host Key Verification Strategy: "Manually trusted key Verification Strategy" (lab) or "Known hosts file" (better)
3. Save. The node log should end with `Agent successfully connected and online`.

What this does:

- The private key lives only in Jenkins credentials (encrypted on disk), not in the repository.
- The label `azure-docker` is what the Jenkinsfile uses in `agent { label 'azure-docker' }`.
- Alternative: an **inbound agent** (the agent connects out to the controller on port 50000 or WebSocket). Use that when the controller cannot reach the agent, for example agents behind a firewall.

#### Step 12: Write the Flask app, tests and Dockerfile

A small app with a health endpoint for Kubernetes probes.

```python
# app.py
import os

from flask import Flask, jsonify

app = Flask(__name__)
VERSION = os.getenv("APP_VERSION", "dev")


@app.get("/")
def index():
    return jsonify(message="Hello from Jenkins and AKS", version=VERSION)


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")
```

```python
# tests/test_app.py
from app import app


def test_index_returns_message():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.get_json()


def test_healthz():
    client = app.test_client()
    assert client.get("/healthz").get_json() == {"status": "ok"}
```

```text
# requirements.txt
flask==3.1.0
gunicorn==23.0.0
```

```text
# requirements-dev.txt
pytest==8.3.4
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd --create-home --uid 10001 appuser
USER 10001

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

What this does:

- `gunicorn` is a production WSGI server; the Flask dev server is not meant for production.
- The image runs as a non-root user (UID 10001), which matches `runAsNonRoot` in the Deployment.
- Copying `requirements.txt` before `app.py` lets Docker cache the dependency layer.

#### Step 13: Write the Kubernetes manifests

The Deployment uses placeholders that the pipeline replaces with the real image and tag.

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-demo
  labels:
    app: flask-demo
spec:
  replicas: 2
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: flask-demo
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app: flask-demo
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
        - name: flask-demo
          image: IMAGE_PLACEHOLDER
          ports:
            - containerPort: 5000
          env:
            - name: APP_VERSION
              value: "TAG_PLACEHOLDER"
          readinessProbe:
            httpGet:
              path: /healthz
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: 5000
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: flask-demo
  labels:
    app: flask-demo
spec:
  type: LoadBalancer
  selector:
    app: flask-demo
  ports:
    - name: http
      port: 80
      targetPort: 5000
```

What this does:

- `replicas: 2` plus `maxUnavailable: 0` means there is always at least two ready pods during a rollout.
- The readiness probe keeps traffic away from a pod until `/healthz` answers. The liveness probe restarts a stuck container.
- Requests help the scheduler place pods; limits stop one pod from using the whole node.
- `type: LoadBalancer` asks AKS to create an Azure public load balancer IP on port 80.

#### Step 14: Write the Jenkinsfile

This is the full declarative pipeline. Replace `<acr-name>` and resource names with yours.

```groovy
pipeline {
    agent { label 'azure-docker' }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    environment {
        ACR_NAME         = '<acr-name>'
        ACR_LOGIN_SERVER = '<acr-name>.azurecr.io'
        IMAGE_NAME       = 'flask-demo'
        RESOURCE_GROUP   = 'rg-jenkins-aks-lab'
        AKS_NAME         = 'aks-jenkins-lab'
        K8S_NAMESPACE    = 'demo'
        // Keep Azure CLI and kubectl config inside this build's workspace
        AZURE_CONFIG_DIR = "${WORKSPACE}/.azure"
        KUBECONFIG       = "${WORKSPACE}/.kube/config"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    def shortSha = sh(script: 'git rev-parse --short=7 HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG  = "${env.BUILD_NUMBER}-${shortSha}"
                    env.FULL_IMAGE = "${env.ACR_LOGIN_SERVER}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                }
                echo "Building image ${env.FULL_IMAGE}"
            }
        }

        stage('Build') {
            steps {
                sh '''
                    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
                      -e PYTHONPYCACHEPREFIX=/tmp/pycache \
                      -v "$WORKSPACE":/src -w /src python:3.12-slim \
                      sh -c "pip install --quiet --user -r requirements.txt && python -m compileall -q app.py"
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    mkdir -p reports
                    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
                      -e PYTHONDONTWRITEBYTECODE=1 \
                      -v "$WORKSPACE":/src -w /src python:3.12-slim \
                      sh -c "pip install --quiet --user -r requirements.txt -r requirements-dev.txt && \
                             python -m pytest -q -p no:cacheprovider --junitxml=reports/junit.xml tests"
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build --pull -t "$FULL_IMAGE" -t "$ACR_LOGIN_SERVER/$IMAGE_NAME:latest" .'
            }
        }

        stage('Push') {
            when { branch 'main' }
            steps {
                sh '''
                    az login --identity --output none
                    az acr login --name "$ACR_NAME"
                    docker push "$FULL_IMAGE"
                    docker push "$ACR_LOGIN_SERVER/$IMAGE_NAME:latest"
                '''
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh '''
                    az aks get-credentials \
                      --resource-group "$RESOURCE_GROUP" \
                      --name "$AKS_NAME" \
                      --file "$KUBECONFIG" \
                      --overwrite-existing
                    kubelogin convert-kubeconfig -l msi --kubeconfig "$KUBECONFIG"

                    sed -i "s|IMAGE_PLACEHOLDER|$FULL_IMAGE|g; s|TAG_PLACEHOLDER|$IMAGE_TAG|g" k8s/deployment.yaml
                    kubectl apply -n "$K8S_NAMESPACE" -f k8s/
                    kubectl rollout status deployment/flask-demo -n "$K8S_NAMESPACE" --timeout=180s
                '''
            }
            post {
                failure {
                    echo 'Rollout failed. Rolling back to the previous ReplicaSet.'
                    sh 'kubectl rollout undo deployment/flask-demo -n "$K8S_NAMESPACE" || true'
                }
            }
        }
    }

    post {
        success {
            echo "Deployed ${env.FULL_IMAGE}"
        }
        failure {
            echo 'Pipeline failed. Check the stage logs above.'
        }
        always {
            sh '''
                docker rmi "$FULL_IMAGE" "$ACR_LOGIN_SERVER/$IMAGE_NAME:latest" 2>/dev/null || true
                docker image prune -f || true
            '''
            deleteDir()
        }
    }
}
```

What this does:

- `agent { label 'azure-docker' }` runs every stage on the agent VM, never on the controller.
- `options`:
  - `timeout` kills a stuck build after 30 minutes.
  - `buildDiscarder` keeps only the last 20 builds, so the controller disk does not fill up.
  - `disableConcurrentBuilds` stops two deployments of the same branch from racing each other.
  - `skipDefaultCheckout(true)` lets the explicit `Checkout` stage control checkout.
- `environment`: `AZURE_CONFIG_DIR` and `KUBECONFIG` point into the workspace, so tokens and kubeconfig from one build are not shared with other builds and are deleted by `deleteDir()`.
- Image tag `BUILD_NUMBER-shortSHA` (for example `15-a1b2c3d`) is unique and traceable back to both the Jenkins build and the Git commit. `latest` is pushed only for convenience; the cluster always uses the unique tag.
- Build and Test run inside a `python:3.12-slim` container with the agent's UID, so the agent needs no Python install and no root-owned files are left in the workspace.
- `when { branch 'main' }` means feature branches and PRs only build and test; only `main` pushes and deploys. This works in a **multibranch** job, where `BRANCH_NAME` is set.
- `az login --identity` uses the VM's managed identity. No secret is stored in Jenkins.
- `kubelogin convert-kubeconfig -l msi` rewrites the kubeconfig to get Entra ID tokens from the managed identity. Without it, `kubectl` would try an interactive device login and hang. `-l azurecli` also works because we already ran `az login --identity`.
- `sed` swaps the placeholders, then `kubectl apply` creates or updates the objects. Alternative for an existing Deployment: `kubectl set image deployment/flask-demo flask-demo="$FULL_IMAGE" -n demo`. `apply` is better because the YAML stays the source of truth.
- `kubectl rollout status` waits until the new pods are ready, so the build fails if the new version never becomes healthy.
- The Deploy stage `post { failure }` runs `kubectl rollout undo` to go back to the previous working version.
- Global `post { always }` removes local images and the workspace, so the agent disk does not fill up.

If you prefer a service principal instead of managed identity, store the client ID and secret as a "Username with password" credential (ID `azure-sp`) and replace the login line:

```groovy
withCredentials([usernamePassword(credentialsId: 'azure-sp',
                                  usernameVariable: 'AZ_CLIENT_ID',
                                  passwordVariable: 'AZ_CLIENT_SECRET')]) {
    sh 'az login --service-principal -u "$AZ_CLIENT_ID" -p "$AZ_CLIENT_SECRET" --tenant "<tenant-id>" --output none'
}
```

Managed identity is better: nothing to rotate, nothing to leak, and it only works from that VM.

#### Step 15: Push the code and create a multibranch pipeline

```bash
git init
git add .
git commit -m "Flask app with Jenkins pipeline"
git branch -M main
git remote add origin https://github.com/<your-user>/flask-jenkins-aks.git
git push -u origin main
```

In Jenkins: **New Item > Multibranch Pipeline**, name `flask-jenkins-aks`.

- Branch Sources: **GitHub**. Add a credential (a GitHub App is best; a fine-grained personal access token stored as "Username with password" is fine for a lab). Repository URL: your repo.
- Build Configuration: by Jenkinsfile, Script Path `Jenkinsfile`.
- Save. Jenkins scans the repo and creates one child job per branch that has a Jenkinsfile, plus one per pull request.

What this does:

- A **multibranch pipeline** discovers branches and PRs automatically. Each branch runs the same Jenkinsfile, and `BRANCH_NAME` tells the pipeline which branch it is, which is why `when { branch 'main' }` works.
- A simple **Pipeline** job builds only one branch. In that case remove the `when` conditions or use a parameter.

#### Step 16: Add the GitHub webhook

In GitHub: **Repository > Settings > Webhooks > Add webhook**.

```text
Payload URL:   http://<controller-ip>:8080/github-webhook/
Content type:  application/json
Events:        Pushes and Pull requests
```

What this does:

- GitHub calls Jenkins on each push, and the GitHub Branch Source plugin triggers the matching branch job. No polling is needed.
- The trailing slash in `/github-webhook/` matters.
- For a single Pipeline job, enable "GitHub hook trigger for GITScm polling" in the job, or add `triggers { githubPush() }` to the Jenkinsfile.
- In production, put Jenkins behind HTTPS and set a webhook secret.

### Verify it works

Push a change and watch the build in Jenkins. Then check the cluster from your laptop.

```bash
kubectl get deploy,pods,svc -n demo
```

Expected output (names and IPs will differ):

```text
NAME                         READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/flask-demo   2/2     2            2           3m

NAME                              READY   STATUS    RESTARTS   AGE
pod/flask-demo-6d9f7c8b5d-4xk2p   1/1     Running   0          3m
pod/flask-demo-6d9f7c8b5d-9hv7m   1/1     Running   0          3m

NAME                 TYPE           CLUSTER-IP    EXTERNAL-IP     PORT(S)        AGE
service/flask-demo   LoadBalancer   10.0.85.120   20.81.112.45    80:31234/TCP   3m
```

```bash
EXTERNAL_IP=$(kubectl get svc flask-demo -n demo -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl "http://$EXTERNAL_IP/"
```

```text
{"message":"Hello from Jenkins and AKS","version":"15-a1b2c3d"}
```

Check the image in ACR and the rollout history:

```bash
az acr repository show-tags -n "$ACR" --repository flask-demo -o table
kubectl rollout history deployment/flask-demo -n demo
```

Test a rollback manually:

```bash
kubectl rollout undo deployment/flask-demo -n demo                  # go back one revision
kubectl rollout undo deployment/flask-demo -n demo --to-revision=2  # go to a specific revision
kubectl rollout status deployment/flask-demo -n demo
```

Note: a manual `rollout undo` is a quick fix. The next pipeline run will deploy `main` again, so also revert the bad commit in Git.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Build stays "Waiting for next available executor" | No online agent with label `azure-docker`, or controller has 0 executors | Check the node is online and the label matches exactly |
| Agent fails to connect: `Host key verification failed` | Host key strategy is "Known hosts" but the key is not in known_hosts | Add the host key, or use "Manually trusted" for the lab |
| `permission denied while trying to connect to the Docker daemon socket` | `jenkins` user not in `docker` group, or agent not reconnected after the change | `sudo usermod -aG docker jenkins`, then disconnect and relaunch the agent |
| `az login --identity` fails with `Identity not found` | VM has no managed identity | `az vm identity assign -g <rg> -n vm-jenkins-agent` |
| `unauthorized: authentication required` on `docker push` | Missing `AcrPush` role or role not yet propagated | Check `az role assignment list --assignee <principal-id>`; wait a few minutes |
| `kubectl` hangs asking for device login | kubeconfig not converted | Run `kubelogin convert-kubeconfig -l msi` (or `-l azurecli`) |
| `Forbidden: ... cannot create resource "deployments"` | Identity has no Kubernetes RBAC role in the namespace | Assign `Azure Kubernetes Service RBAC Writer` at `<aks-id>/namespaces/demo` |
| Pods in `ImagePullBackOff` | AKS cannot pull from ACR, or wrong image name | `az aks check-acr -g <rg> -n <aks> --acr <acr>.azurecr.io`; re-run `az aks update --attach-acr` |
| `rollout status` times out | Readiness probe failing, app crash, wrong port | `kubectl describe pod` and `kubectl logs` for the new pod |
| Deploy stage skipped | Job is not multibranch, so `BRANCH_NAME` is empty | Use a multibranch job, or remove `when { branch 'main' }` |
| Webhook shows red X in GitHub | Port 8080 blocked or wrong URL | Allow GitHub hook IPs in the NSG; use `/github-webhook/` with trailing slash |
| `deleteDir` fails with permission denied | Files created as root by a container | Run containers with `--user "$(id -u):$(id -g)"` as in the Jenkinsfile |

### Clean up

```bash
az group delete --name "$RG" --yes --no-wait

# AKS creates a second "node resource group" (MC_...). It is deleted with the cluster,
# but confirm after a few minutes:
az group list --query "[?starts_with(name, 'MC_rg-jenkins-aks-lab')].name" -o tsv

# Remove local kubeconfig context
kubectl config delete-context "$AKS"
```

To pause instead of delete:

```bash
az vm deallocate -g "$RG" -n vm-jenkins-agent
az vm deallocate -g "$RG" -n vm-jenkins-controller
az aks stop -g "$RG" -n "$AKS"
```

### Next improvements

- Put Jenkins behind HTTPS (Application Gateway or NGINX with a certificate) and add a webhook secret.
- Use Jenkins Configuration as Code (JCasC) so plugins, nodes and credentials are defined in Git.
- Use ephemeral agents (Azure VM Agents plugin or Kubernetes plugin pods) instead of one long-lived VM.
- Scan the image with Trivy before push and fail on critical CVEs.
- Move manifests to Helm or Kustomize and use a GitOps tool (Argo CD or Flux) for the deploy step.
- Add a manual `input` approval stage before a production namespace.
- Use a user-assigned managed identity so the identity survives VM rebuilds.
- Add a shared library for common pipeline steps used by many repositories.

### How to explain this project in an interview

> "As a hands-on practice project, I built a Jenkins pipeline that deploys a small Flask app to AKS. Jenkins runs as a controller with zero executors, and builds run on a separate Ubuntu agent VM connected over SSH. The agent has Docker, Azure CLI, kubectl and kubelogin, plus a system-assigned managed identity. I gave that identity only AcrPush on the registry, Cluster User Role on AKS, and RBAC Writer scoped to one namespace, so there are no secrets in Jenkins at all. The pipeline checks out code, runs pytest inside a Python container, builds the image tagged with the build number and short commit SHA, pushes it with az acr login, and deploys with kubectl apply. kubectl rollout status gates the build, and if the rollout fails, a post-failure block runs rollout undo. It is a multibranch job triggered by a GitHub webhook, so feature branches only build and test, and only main deploys."

Points that impress interviewers:

- You know why builds should not run on the controller and set controller executors to 0.
- You used managed identity with least-privilege, namespace-scoped roles instead of a stored service principal secret.
- You used immutable, traceable image tags and `rollout status` to fail the pipeline on unhealthy deployments.
- You isolated `AZURE_CONFIG_DIR` and `KUBECONFIG` per workspace and cleaned up images and workspace in `post { always }`.

## Interview Questions

<details><summary>Q1. [Basic] Why should builds not run on the Jenkins controller?</summary>

**Answer:**

The controller stores all job configuration, credentials and the encryption keys for those credentials. A build runs whatever code is in the repository, so a build on the controller can read `$JENKINS_HOME`, steal secrets or crash Jenkins. Heavy builds also use the controller's CPU, memory and disk, which makes the UI and scheduling slow for everyone. Best practice is to set the built-in node's executors to 0 and run all builds on agents. Agents are easy to replace if they get dirty or compromised.

</details>

<details><summary>Q2. [Basic] What is the difference between a Pipeline job and a Multibranch Pipeline job?</summary>

**Answer:**

A Pipeline job builds one configured branch (or one script). A Multibranch Pipeline job scans a repository and creates a child job for every branch and pull request that contains a Jenkinsfile. Each child job sets `BRANCH_NAME` (and `CHANGE_ID` for PRs), so the Jenkinsfile can use `when { branch 'main' }` to deploy only from `main` while still building and testing every branch. Multibranch jobs are also cleaned up automatically when branches are deleted.

</details>

<details><summary>Q3. [Basic] Why tag images with <code>BUILD_NUMBER</code> and the Git commit instead of only <code>latest</code>?</summary>

**Answer:**

`latest` is mutable. If the Deployment uses `latest`, Kubernetes may not pull the new image, you cannot tell which code is running, and rollback is unreliable because the old image was overwritten. A tag like `15-a1b2c3d` is unique: it maps to Jenkins build 15 and commit `a1b2c3d`. Changing the tag in the Deployment also changes the pod template, which triggers a real rolling update and creates a revision you can roll back to.

</details>

<details><summary>Q4. [Intermediate] How does the agent authenticate to ACR and AKS without storing secrets?</summary>

**Answer:**

The agent VM has a system-assigned managed identity. In the pipeline, `az login --identity` gets a token from the Azure Instance Metadata Service. `az acr login` then exchanges that token for a registry token and configures Docker. For AKS, `az aks get-credentials` downloads a kubeconfig (needs Cluster User Role), and `kubelogin convert-kubeconfig -l msi` makes `kubectl` request Entra ID tokens using the same managed identity. Kubernetes permissions come from an Azure RBAC role such as `Azure Kubernetes Service RBAC Writer` scoped to the namespace. No password or client secret is stored anywhere.

</details>

<details><summary>Q5. [Intermediate] What do <code>timeout</code>, <code>buildDiscarder</code> and <code>disableConcurrentBuilds</code> protect against?</summary>

**Answer:**

- `timeout` aborts a hung build (for example a stuck `rollout status` or network call), so it does not hold an executor forever.
- `buildDiscarder(logRotator(...))` deletes old builds and logs, so `$JENKINS_HOME` does not fill the controller disk.
- `disableConcurrentBuilds` stops two builds of the same branch from running at once. Without it, two deploys could race and an older commit could finish last and overwrite the newer one.

</details>

<details><summary>Q6. [Intermediate] The pipeline is green, but users still see the old version. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

1. Check what image the Deployment uses: `kubectl get deploy flask-demo -n demo -o jsonpath='{.spec.template.spec.containers[0].image}'`. If it still has `IMAGE_PLACEHOLDER` or an old tag, the `sed` or apply step did not change it.
2. Confirm the correct namespace and cluster were targeted (`KUBECONFIG`, `-n demo`).
3. Check `kubectl rollout status` and `kubectl get rs -n demo` to see whether new pods are ready.
4. If the image tag is reused (like `latest`), Kubernetes may not pull a new image; use unique tags.
5. Check the Service selector matches the new pod labels and that no cache or CDN is in front.
6. Make sure the build actually ran the Deploy stage: in a non-multibranch job, `when { branch 'main' }` skips it.

</details>

<details><summary>Q7. [Intermediate] How do you roll back a bad deployment in this setup?</summary>

**Answer:**

There are three layers:

- Automatic: the Deploy stage has `post { failure { kubectl rollout undo ... } }`, so if `rollout status` fails, Kubernetes goes back to the previous ReplicaSet.
- Manual quick fix: `kubectl rollout history deployment/flask-demo -n demo`, then `kubectl rollout undo deployment/flask-demo -n demo --to-revision=<n>`.
- Permanent fix: revert the bad commit in Git so the next pipeline run does not redeploy it. You can also add a parameter to the job to redeploy a known good image tag from ACR without rebuilding.

</details>

<details><summary>Q8. [Advanced] Builds fail randomly with "no space left on device" on the agent. What do you do? <em>(scenario)</em></summary>

**Answer:**

Docker images and build cache are the usual cause. Short term: `docker system df` to see usage, then `docker image prune -af` and `docker builder prune -af`, and clean old workspaces in `/home/jenkins/agent/workspace`. Long term: remove images in `post { always }`, use `deleteDir()`, schedule a nightly prune job, give the agent a bigger OS disk, and set a disk-space threshold on the node so Jenkins takes it offline before it fills. The best fix is ephemeral agents (new VM or pod per build), so there is no state to accumulate.

</details>

<details><summary>Q9. [Advanced] How would you add a production deployment with approval to this pipeline? <em>(scenario)</em></summary>

**Answer:**

Add a stage after deploying to a test namespace:

```groovy
stage('Approve Prod') {
    when { branch 'main' }
    steps {
        timeout(time: 1, unit: 'HOURS') {
            input message: "Deploy ${env.IMAGE_TAG} to prod?", submitter: 'release-managers'
        }
    }
}
```

Then a `Deploy Prod` stage that applies the same image tag (no rebuild) to the prod namespace or prod cluster. Use a different managed identity or agent label for prod, with roles only on the prod cluster, so a dev pipeline cannot touch prod. Put the `input` outside any `agent` block in real pipelines, so an executor is not held while waiting.

</details>

<details><summary>Q10. [Advanced] SSH agent versus inbound agent: when would you choose each?</summary>

**Answer:**

With an **SSH agent**, the controller connects to the agent on port 22 and starts `agent.jar`. It is simple when the controller can reach the agent, as in a shared VNet. With an **inbound agent**, the agent starts `agent.jar` itself and connects out to the controller over TCP port 50000 or WebSocket over HTTPS. Choose inbound when agents are behind NAT or a firewall, run on Windows, or run as containers that cannot accept SSH. For dynamic scaling, use cloud plugins (Kubernetes plugin or Azure VM Agents) that create agents on demand and delete them after the build.

</details>
