# Hands-on 2: Azure DevOps Pipeline with Terraform, Helm, ACR, and AKS

> Build one Azure DevOps pipeline that validates Terraform, estimates cost, checks code quality, plans infrastructure, and then lints, packages, pushes, and deploys a Helm chart from ACR to AKS behind an approval.

**Time:** about 2 hours. **Level:** Intermediate.

## What you practise

- Terraform `init`, `fmt`, `validate`, and `plan` in a pipeline
- Cost estimation with Infracost before infrastructure changes
- SonarQube code-quality checks with a quality gate
- Helm chart validation (`helm lint`, `helm template`), packaging, and versioning
- Pushing a Helm chart to Azure Container Registry as an OCI artifact and installing it from there
- `helm upgrade --install` on AKS, with an approval before deployment
- Serving custom HTML from a ConfigMap and validating it inside the Pod

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure subscription with an AKS cluster and an ACR | Deployment target and chart registry (created earlier with Terraform) |
| Azure DevOps project | Repository and pipeline |
| Azure Resource Manager service connection | Workload identity federation; access to the resource group, ACR, and AKS |
| SonarQube server and service connection | Code-quality stage |
| Infracost API key | Cost stage, stored as a secret pipeline variable |
| Environment `aks-dev` with an approval check | Approval before deployment |

## Pipeline flow

```text
Terraform init / fmt / validate
        |
        v
Infracost (cost estimate)
        |
        v
SonarQube (code quality + quality gate)
        |
        v
Terraform plan
        |
        v
Helm lint -> helm template -> helm package -> helm push (OCI) to ACR
        |
        v
Approval (environment check)
        |
        v
helm upgrade --install from ACR to AKS -> validate inside the Pod
```

## Repository layout

```text
.
├── terraform/            # AKS, ACR, networking
├── charts/myapp-chart/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── configmap.yaml
└── azure-pipelines.yml
```

## Steps

### 1. Serve custom HTML from a ConfigMap

`templates/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-html
data:
  index.html: |
    {{- .Values.html | nindent 4 }}
```

In `templates/deployment.yaml`, mount it over the nginx web root:

```yaml
          volumeMounts:
            - name: html
              mountPath: /usr/share/nginx/html
      volumes:
        - name: html
          configMap:
            name: {{ .Release.Name }}-html
```

`values.yaml`:

```yaml
image: nginx:1.27
html: |
  <h1>Deployed with Helm from ACR to AKS</h1>
```

Changing the page now only needs a values change, not a new image.

### 2. Validate the chart locally

```bash
helm lint charts/myapp-chart
helm template myapp charts/myapp-chart
```

### 3. Push the chart to ACR manually once

```bash
helm package charts/myapp-chart --version 0.1.1
# creates myapp-chart-0.1.1.tgz

az acr login --name myacr
helm push myapp-chart-0.1.1.tgz oci://myacr.azurecr.io/helm

az acr repository show-tags --name myacr --repository helm/myapp-chart -o table
helm pull oci://myacr.azurecr.io/helm/myapp-chart --version 0.1.1
```

`az acr login` also logs Helm in to the registry. If Docker is not installed (for example on some agents), log in with a token instead:

```bash
TOKEN=$(az acr login --name myacr --expose-token --query accessToken -o tsv)
helm registry login myacr.azurecr.io \
  --username 00000000-0000-0000-0000-000000000000 \
  --password "$TOKEN"
```

### 4. Create the pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

variables:
  azureSubscription: azure-wif-connection
  acrName: myacr
  aksResourceGroup: rg-aks-dev
  aksName: aks-dev
  chartPath: charts/myapp-chart
  chartVersion: 0.1.$(Build.BuildId)

stages:
  - stage: Validate
    jobs:
      - job: TerraformValidate
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: '1.9.8'
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: terraform
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: dev.tfstate
          - script: terraform fmt -check -recursive
            displayName: Terraform fmt
            workingDirectory: terraform
          - task: TerraformTask@5
            displayName: Terraform validate
            inputs:
              provider: azurerm
              command: validate
              workingDirectory: terraform

  - stage: Cost
    dependsOn: Validate
    jobs:
      - job: Infracost
        steps:
          - script: |
              curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh
              infracost breakdown --path terraform --format table
            displayName: Infracost breakdown
            env:
              INFRACOST_API_KEY: $(INFRACOST_API_KEY)

  - stage: CodeQuality
    dependsOn: Validate
    jobs:
      - job: SonarQube
        steps:
          - task: SonarQubePrepare@7
            inputs:
              SonarQube: sonarqube-connection
              scannerMode: cli
              configMode: manual
              cliProjectKey: myapp
              cliSources: .
              extraProperties: |
                sonar.qualitygate.wait=true
          - task: SonarQubeAnalyze@7
          - task: SonarQubePublish@7
            inputs:
              pollingTimeoutSec: '300'

  - stage: Plan
    dependsOn:
      - Cost
      - CodeQuality
    jobs:
      - job: TerraformPlan
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: '1.9.8'
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: terraform
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: dev.tfstate
          - task: TerraformTask@5
            displayName: Terraform plan
            inputs:
              provider: azurerm
              command: plan
              workingDirectory: terraform
              environmentServiceNameAzureRM: $(azureSubscription)
              commandOptions: '-out=tfplan -input=false'

  - stage: HelmPackage
    dependsOn: Plan
    jobs:
      - job: Helm
        steps:
          - task: HelmInstaller@1
            inputs:
              helmVersionToInstall: '3.16.3'
          - script: |
              helm lint $(chartPath)
              helm template myapp $(chartPath) > /dev/null
              helm package $(chartPath) --version $(chartVersion)
            displayName: Helm lint, template, package
          - task: AzureCLI@2
            displayName: Push chart to ACR
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                TOKEN=$(az acr login --name $(acrName) --expose-token --query accessToken -o tsv)
                helm registry login $(acrName).azurecr.io \
                  --username 00000000-0000-0000-0000-000000000000 --password "$TOKEN"
                helm push myapp-chart-$(chartVersion).tgz oci://$(acrName).azurecr.io/helm

  - stage: DeployDev
    dependsOn: HelmPackage
    jobs:
      - deployment: DeployToAKS
        environment: aks-dev            # approval check configured here
        strategy:
          runOnce:
            deploy:
              steps:
                - task: HelmInstaller@1
                  inputs:
                    helmVersionToInstall: '3.16.3'
                - task: AzureCLI@2
                  displayName: Helm upgrade --install from ACR
                  inputs:
                    azureSubscription: $(azureSubscription)
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials -g $(aksResourceGroup) -n $(aksName) --overwrite-existing
                      kubelogin convert-kubeconfig -l azurecli
                      TOKEN=$(az acr login --name $(acrName) --expose-token --query accessToken -o tsv)
                      helm registry login $(acrName).azurecr.io \
                        --username 00000000-0000-0000-0000-000000000000 --password "$TOKEN"
                      helm upgrade --install myapp oci://$(acrName).azurecr.io/helm/myapp-chart \
                        --version $(chartVersion) \
                        -n myapp --create-namespace \
                        --wait --atomic --timeout 5m
                      kubectl rollout status deployment/myapp -n myapp
                      kubectl exec -n myapp deploy/myapp -- cat /usr/share/nginx/html/index.html
```

Notes:

- `kubelogin convert-kubeconfig -l azurecli` is needed when the AKS cluster uses Microsoft Entra ID authentication; the hosted agent already has `kubelogin`.
- The chart version uses the build ID, so every pipeline run publishes a new, unique chart version.
- This pipeline stops at `terraform plan`. If it also changes infrastructure, add a Terraform apply stage after an approval, before the Helm deployment.

### 5. Validate the deployment

```bash
helm list -n myapp
kubectl get pods,svc -n myapp
kubectl exec -n myapp deploy/myapp -- cat /usr/share/nginx/html/index.html
kubectl port-forward -n myapp svc/myapp 8080:80
curl http://localhost:8080
```

Expected: the release shows `deployed`, the Pod is `Running`, and the page returns the custom HTML from the ConfigMap.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `helm push` returns 401 | Not logged in to ACR, or the service connection lacks `AcrPush` | Log in with the token; grant `AcrPush` |
| `Error: chart not found` during install | Wrong OCI path or version | Check with `az acr repository show-tags` |
| Pods in `ImagePullBackOff` | AKS cannot pull the app image | Attach ACR to AKS (`az aks update --attach-acr`) |
| `kubectl` asks for interactive login | Entra-integrated AKS | Run `kubelogin convert-kubeconfig -l azurecli` |
| Page does not change after a values update | Pods do not restart on ConfigMap change | Add a checksum annotation of the ConfigMap to the Pod template |

## Interview questions

<details><summary>Q1. Why store Helm charts in ACR instead of in the Git repository only?</summary>

ACR stores each packaged chart as an immutable, versioned OCI artifact next to the container images, with the same Entra ID authentication and private networking. The pipeline deploys a specific chart version (`--version 0.1.42`), so every environment installs exactly the same tested package, and I can see and roll back to any published version.

</details>

<details><summary>Q2. What is the order of checks in your pipeline, and why?</summary>

Fast, cheap checks run first: Terraform `fmt` and `validate` fail in seconds. Then the cost estimate and SonarQube quality gate, so expensive or low-quality changes stop early. Then `terraform plan` shows the exact infrastructure change. Only then is the Helm chart linted, rendered, packaged, and pushed, and the deployment to AKS waits for approval.

</details>

<details><summary>Q3. What does <code>helm upgrade --install --atomic --wait</code> do?</summary>

`--install` installs the release if it does not exist, otherwise upgrades it, so the same command works for the first and every later deployment. `--wait` waits until the resources are ready. `--atomic` rolls back automatically if the upgrade fails or times out, so a broken release does not stay deployed.

</details>

<details><summary>Q4. Why use a ConfigMap for the HTML instead of baking it into the image?</summary>

Configuration and content change more often than the application. Keeping them in a ConfigMap, driven by Helm values, lets each environment have its own content without building a new image. The same image is promoted across environments, and only the values change.

</details>

<details><summary>Q5. How do you estimate infrastructure cost in the pipeline?</summary>

I run Infracost on the Terraform code or the plan JSON. It prints the monthly cost of the resources and the difference from the current state, so reviewers see the cost impact before approving. A policy can fail the pipeline if the increase is over a threshold.

</details>
