# Repetitive Interview Questions

## Explain the end-to-end CI/CD workflow used in your project

**Interviewer:** Can you explain your complete CI/CD flow?

**Candidate:**

CI/CD automates the process from a code change to a safe deployment.

- **Continuous Integration (CI):** Build, test, scan, and package the application.
- **Continuous Delivery/Deployment (CD):** Deploy the approved application version to each environment.

```text
Developer pushes code
-> pull request checks
-> merge to main
-> build and test
-> security scan
-> build container image
-> push image to registry
-> deploy to Development
-> test
-> approval
-> deploy to Production
-> verify and monitor
```

### 1. Code change and pull request

The developer works on a short-lived feature branch and opens a pull request.

The pipeline checks:

- Unit tests.
- Code quality.
- Dependency and secret scanning.
- Application build.

The change is merged only after the checks and review pass.

### 2. Build one versioned image

After merge, the pipeline builds a container image.

```bash
docker build -t <registry>/orders-api:<version> .
docker push <registry>/orders-api:<version>
```

I use a unique version or commit ID, not `latest`. The same tested image is promoted to every environment.

### 3. Deploy to a lower environment

The pipeline deploys the image using Helm:

```bash
helm upgrade --install orders-api ./helm/orders-api \
  --namespace development \
  --set image.tag=<version> \
  --wait
```

It then runs a basic test to confirm that the application is reachable.

### 4. Production approval

Production deployment requires approval. The approver can see:

- Image version.
- Test and scan results.
- Change details.
- Rollback plan.

### 5. Deploy and verify

```bash
helm upgrade --install orders-api ./helm/orders-api \
  --namespace production \
  --set image.tag=<version> \
  --wait

kubectl rollout status deployment/orders-api -n production
```

After deployment, I check Pod readiness, logs, application response, error rate, and response time.

If the deployment fails, I restore the previous release:

```bash
helm rollback orders-api <revision> -n production
```

## Jenkins example

This mirrors the same nine stages as the Azure DevOps pipeline above, for the same React + Spring Boot app. Because a Jenkins declarative pipeline runs all stages on the same agent workspace by default, the image built in one stage is still there for later stages — no artifact hand-off is needed.

```groovy
pipeline {
  agent any

  environment {
    ACR_NAME   = 'myacr'
    IMAGE_NAME = 'payment-api'
    IMAGE_TAG  = "${env.BUILD_NUMBER}"
    AKS_DEV    = 'aks-dev'
    AKS_PROD   = 'aks-prod'
    NAMESPACE  = 'payment'
  }

  stages {

    stage('Build React and Spring Boot') {
      steps {
        dir('frontend') {
          sh 'npm install'
          sh 'npm run build'
        }
        dir('backend') {
          sh './mvnw clean package -DskipTests'
        }
      }
    }

    stage('Run Tests') {
      steps {
        dir('backend') {
          sh './mvnw test'
        }
        dir('frontend') {
          sh 'npm test -- --watchAll=false'
        }
      }
    }

    stage('SonarQube Analysis') {
      steps {
        dir('backend') {
          withSonarQubeEnv('SonarQube-Service-Connection') {
            sh './mvnw verify sonar:sonar -Dsonar.projectKey=payment-api'
          }
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -f backend/Dockerfile backend"
      }
    }

    stage('Trivy Security Scan') {
      steps {
        sh "trivy image --severity HIGH,CRITICAL --exit-code 1 ${IMAGE_NAME}:${IMAGE_TAG}"
      }
    }

    stage('Push Image to ACR') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'ACR-Credentials', usernameVariable: 'ACR_USER', passwordVariable: 'ACR_PASS')]) {
          sh """
            echo \$ACR_PASS | docker login ${ACR_NAME}.azurecr.io -u \$ACR_USER --password-stdin
            docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}
            docker push ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}
          """
        }
      }
    }

    stage('Deploy to Development') {
      steps {
        sh "az aks get-credentials --resource-group myResourceGroup --name ${AKS_DEV} --overwrite-existing"
        sh """
          helm upgrade --install payment-api ./helm/payment-api \
            --namespace ${NAMESPACE} \
            --create-namespace \
            --set image.repository=${ACR_NAME}.azurecr.io/${IMAGE_NAME} \
            --set image.tag=${IMAGE_TAG} \
            --wait
        """
      }
    }

    stage('Production Approval') {
      steps {
        timeout(time: 24, unit: 'HOURS') {
          input message: 'Approve deployment to Production?', submitter: 'devops-team'
        }
      }
    }

    stage('Deploy to Production') {
      steps {
        sh "az aks get-credentials --resource-group myResourceGroup --name ${AKS_PROD} --overwrite-existing"
        sh """
          helm upgrade --install payment-api ./helm/payment-api \
            --namespace ${NAMESPACE} \
            --create-namespace \
            --set image.repository=${ACR_NAME}.azurecr.io/${IMAGE_NAME} \
            --set image.tag=${IMAGE_TAG} \
            --wait
        """
      }
    }
  }
}
```

The stages run in order — if any stage fails, the pipeline stops and later stages don't run. `input` in the **Production Approval** stage is Jenkins's equivalent of Azure DevOps's `ManualValidation@1`: it pauses the pipeline and waits for a named approver, and `timeout` auto-rejects it if nobody responds in 24 hours. Registry and cluster credentials come from the Jenkins credential store (`withCredentials`), not hardcoded values.

## Azure DevOps example

This is a more complete, real-world pipeline for a React + Spring Boot application. It builds both parts of the app, runs tests, checks code quality, builds and scans a Docker image, pushes it to Azure Container Registry (ACR), and then deploys to AKS Dev and AKS Production with a manual approval gate in between.

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

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

    - script: |
        docker build -t $(imageName):$(imageTag) -f backend/Dockerfile backend
        docker save $(imageName):$(imageTag) -o $(Build.ArtifactStagingDirectory)/image.tar
      displayName: Build and Save Docker Image

    - publish: $(Build.ArtifactStagingDirectory)/image.tar
      artifact: docker-image


# --------------------------------------------------
# 5. TRIVY SCAN
# --------------------------------------------------
- stage: TrivyScan
  displayName: Scan Docker Image
  dependsOn: DockerBuild
  jobs:
  - job: Trivy
    steps:
    - checkout: none
    - download: current
      artifact: docker-image

    - script: |
        docker load -i $(Pipeline.Workspace)/docker-image/image.tar
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
    - checkout: none
    - download: current
      artifact: docker-image

    - script: |
        docker load -i $(Pipeline.Workspace)/docker-image/image.tar
        docker tag $(imageName):$(imageTag) $(acrName).azurecr.io/$(imageName):$(imageTag)
      displayName: Load and Tag the Scanned Image

    - task: Docker@2
      displayName: Login to ACR
      inputs:
        command: login
        containerRegistry: 'ACR-Service-Connection'

    - task: Docker@2
      displayName: Push to ACR
      inputs:
        command: push
        containerRegistry: 'ACR-Service-Connection'
        repository: $(imageName)
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
          - checkout: self    # deployment jobs do not check out code by default

          - task: AzureCLI@2
            displayName: Helm Upgrade/Install to AKS Dev
            inputs:
              azureSubscription: 'AKS-Dev-Service-Connection'
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                az aks get-credentials --resource-group myResourceGroup --name $(aksDev) --overwrite-existing

                helm upgrade --install payment-api ./helm/payment-api \
                  --namespace $(namespace) \
                  --create-namespace \
                  --set image.repository=$(acrName).azurecr.io/$(imageName) \
                  --set image.tag=$(imageTag) \
                  --wait


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
          - checkout: self    # deployment jobs do not check out code by default

          - task: AzureCLI@2
            displayName: Helm Upgrade/Install to AKS Production
            inputs:
              azureSubscription: 'AKS-Prod-Service-Connection'
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                az aks get-credentials --resource-group myResourceGroup --name $(aksProd) --overwrite-existing

                helm upgrade --install payment-api ./helm/payment-api \
                  --namespace $(namespace) \
                  --create-namespace \
                  --set image.repository=$(acrName).azurecr.io/$(imageName) \
                  --set image.tag=$(imageTag) \
                  --wait
```

### What this pipeline does, in simple words

A top-level `pool: vmImage: 'ubuntu-latest'` sets the default agent for every job. The Approval stage overrides it with `pool: server`, since manual validation runs on Azure DevOps's built-in agentless pool, not a VM.

Each `stage` runs only after the one before it finishes successfully, because of `dependsOn`. If one stage fails, the pipeline stops there and nothing later runs.

Each stage can get a fresh Microsoft-hosted agent, so files from one stage are not on the next agent. That is why the image is saved as a pipeline artifact and downloaded later, and why the deployment jobs run `checkout: self` before using the Helm chart.

1. **Build** – Compiles both halves of the app: the React frontend (`npm install` + `npm run build`) and the Spring Boot backend (`./mvnw clean package`).
2. **Test** – Runs the backend unit tests (`./mvnw test`) and the frontend tests (`npm test`). This is separate from Build so test failures are easy to spot.
3. **SonarQube** – Scans the code for bugs, code smells, and coverage gaps, and publishes the results back to Azure DevOps.
4. **Docker Build** – Packages the backend into a Docker image, tagged with the Azure DevOps build ID (`$(Build.BuildId)`) so every image is unique and traceable back to a build. `docker save` stores it as `image.tar`, published as the `docker-image` artifact.
5. **Trivy Scan** – Downloads and loads that exact image, then scans it for known vulnerabilities. `--exit-code 1` means the pipeline fails if a HIGH or CRITICAL issue is found, so a vulnerable image never moves forward.
6. **Push to ACR** – Only after the image passes the security scan, the same scanned image is loaded, tagged, and pushed to Azure Container Registry. It is not rebuilt here (`buildAndPush` would build a new image that was never scanned).
7. **Deploy to Dev** – Checks out the repo for the Helm chart, fetches AKS credentials with `az aks get-credentials`, then (in the same Azure CLI step) runs `helm upgrade --install` to deploy (or update) the `payment-api` chart on the Dev cluster, pointing at the image that was just pushed. `--wait` makes the step block until the rollout is healthy.
8. **Approval** – A manual gate. It pauses the pipeline and emails the DevOps team; someone must approve before Production deployment can start. If nobody responds in time, `onTimeout: 'reject'` stops the pipeline.
9. **Deploy to Prod** – Runs only after approval, and repeats the same `az aks get-credentials` + `helm upgrade --install` pattern against the Production cluster, using the exact same image tag. This matters: it's not a rebuild, it's the same tested artifact that went to Dev.

The key idea, like in the simpler example above: build one image, scan it, and promote that same image through Dev and then Production, with a human approval step protecting Production.

## GitHub Actions example

Same nine stages again, now as GitHub Actions jobs. Unlike Jenkins, each job in GitHub Actions runs on a fresh runner with its own filesystem, so the Docker image built in one job isn't automatically visible to the next. The pipeline below builds the image once, saves it as a workflow artifact, and later jobs download and reuse that same file — so Trivy and ACR are checking and pushing the exact same image, not rebuilding it.

```yaml
name: payment-api-cicd

on:
  push:
    branches: [main]

env:
  ACR_NAME: myacr
  IMAGE_NAME: payment-api
  IMAGE_TAG: ${{ github.run_number }}
  AKS_DEV: aks-dev
  AKS_PROD: aks-prod
  NAMESPACE: payment

permissions:
  id-token: write   # needed for OIDC login to Azure
  contents: read

jobs:

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: |
          cd frontend
          npm install
          npm run build

      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - run: |
          cd backend
          ./mvnw clean package -DskipTests

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          cd backend
          ./mvnw test
      - run: |
          cd frontend
          npm test -- --watchAll=false

  sonarqube:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          cd backend
          ./mvnw verify sonar:sonar -Dsonar.projectKey=payment-api
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

  docker-build:
    needs: sonarqube
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t $IMAGE_NAME:$IMAGE_TAG -f backend/Dockerfile backend
      - run: docker save $IMAGE_NAME:$IMAGE_TAG -o image.tar
      - uses: actions/upload-artifact@v4
        with:
          name: docker-image
          path: image.tar

  trivy-scan:
    needs: docker-build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: docker-image
      - run: docker load -i image.tar
      - run: trivy image --severity HIGH,CRITICAL --exit-code 1 $IMAGE_NAME:$IMAGE_TAG

  push-acr:
    needs: trivy-scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: docker-image
      - run: docker load -i image.tar
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: az acr login --name $ACR_NAME
      - run: |
          docker tag $IMAGE_NAME:$IMAGE_TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG
          docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

  deploy-dev:
    needs: push-acr
    runs-on: ubuntu-latest
    environment: Dev
    steps:
      - uses: actions/checkout@v4   # needed for ./helm/payment-api
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: az aks get-credentials --resource-group myResourceGroup --name $AKS_DEV --overwrite-existing
      - run: |
          helm upgrade --install payment-api ./helm/payment-api \
            --namespace $NAMESPACE \
            --create-namespace \
            --set image.repository=$ACR_NAME.azurecr.io/$IMAGE_NAME \
            --set image.tag=$IMAGE_TAG \
            --wait

  deploy-prod:
    needs: deploy-dev
    runs-on: ubuntu-latest
    environment: Production
    steps:
      - uses: actions/checkout@v4   # needed for ./helm/payment-api
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: az aks get-credentials --resource-group myResourceGroup --name $AKS_PROD --overwrite-existing
      - run: |
          helm upgrade --install payment-api ./helm/payment-api \
            --namespace $NAMESPACE \
            --create-namespace \
            --set image.repository=$ACR_NAME.azurecr.io/$IMAGE_NAME \
            --set image.tag=$IMAGE_TAG \
            --wait
```

Each job waits for the one before it via `needs`. There's no separate "Approval" job here — GitHub Actions handles that through the `environment: Production` protection rule on `deploy-prod`: if that environment is configured in the repo settings with required reviewers, the job pauses and waits for someone to approve it before running, the same effect as the manual validation step in the other two pipelines.

Azure login uses OIDC (a federated credential on an Entra ID app or user-assigned managed identity), so no client secret or ACR password is stored in GitHub. The deploy jobs run `actions/checkout` because each job starts on an empty runner and needs the Helm chart from the repo.

## Secrets

Passwords and tokens are stored in the CI/CD platform's protected secret store or in Azure Key Vault. They are not written directly in pipeline YAML or printed in logs.

Where possible, I use short-lived identity-based authentication instead of a saved username and password.

## Example

Suppose commit `a1b2c3` is merged into `main`. The pipeline tests it, builds `orders-api:a1b2c3`, scans it, and pushes it to the registry. That same image is deployed to Development and tested. After approval, it is promoted to Production and monitored.

## In short

My CI/CD flow starts with a pull request and automated checks. After merge, the pipeline builds and scans one versioned image, deploys it to a lower environment, and promotes the same image to Production after approval.

I verify the rollout and keep the previous Helm revision available for rollback.

---

## What is the correct order of the DevOps lifecycle?

**Interviewer:** When using DevOps for product development, what is the correct sequence?

**Candidate:**

The DevOps loop is:

```text
Plan -> Code (commit to Git) -> Build -> Test -> Release -> Deploy -> Operate -> Monitor -> back to Plan
```

In a multiple-choice question, map each option to these words. "Commit code to source control" is Code, "Build the package" is Build, "Bring the product into operation" is Operate. Deploy always comes before Operate.

If the given options do not start with commit, pick the option that keeps Build -> Test -> Release -> Deploy -> Operate in order. In one real interview question, the accepted answer was:

```text
Build -> Test and integrate -> Commit -> Release -> Deploy to production -> Operate
```

### Same flow in AWS tools

A related question asked for the correct AWS DevOps tool order:

```text
CodePipeline (orchestrates) -> CodeCommit (source) -> CodeBuild (build and test) -> CodeDeploy (deploy)
```

The Azure equivalent is Azure Pipelines -> Azure Repos -> build job -> deployment job.

Remember:

- CloudWatch and X-Ray are monitoring and tracing tools. They are not steps in the build-and-deploy chain.
- AWS stopped onboarding new CodeCommit customers in 2024, so new AWS projects usually keep the code in GitHub or GitLab and connect it to CodePipeline.

## How does a pipeline run automatically in Azure DevOps?

**Interviewer:** How does a pipeline start without anyone clicking Run?

**Candidate:**

Through triggers. There are four types:

```text
Push to a branch          -> CI trigger
Pull request              -> PR trigger or branch policy build validation
Time of day               -> Scheduled trigger
Another pipeline finishes -> Pipeline completion (resource) trigger
```

```yaml
# CI trigger with a path filter
trigger:
  branches:
    include: [main]
  paths:
    exclude: [docs/*]

# Nightly run (cron is in UTC)
schedules:
  - cron: "30 2 * * *"        # 02:30 UTC = 08:00 IST
    displayName: Nightly scan
    branches:
      include: [main]
    always: true              # run even when nothing changed

# Start this CD pipeline when the CI pipeline finishes
resources:
  pipelines:
    - pipeline: ci
      source: payment-api-ci
      trigger:
        branches:
          include: [main]
```

Remember:

- With no `trigger` block, a YAML pipeline runs on every push to every branch. `trigger: none` turns CI off.
- The `pr:` block works for GitHub and Bitbucket. For **Azure Repos**, it is ignored. I add the pipeline under **Branch policies -> Build validation** on `main` instead.
- If a pipeline does not trigger, I check: the YAML exists on that branch, the branch and path filters match, the pipeline is not disabled, and the trigger is not overridden in the UI settings.

## What is an Azure DevOps Service Connection?

**Interviewer:** What is a service connection used for?

**Candidate:**

A service connection stores how a pipeline authenticates to an outside system. The YAML only uses its name, so no credentials are in the pipeline file.

Common types:

- **Azure Resource Manager** - deploy to an Azure subscription or resource group.
- **Docker Registry** - log in to ACR or Docker Hub.
- **Kubernetes** - connect to a cluster.
- **GitHub**, **SonarQube**, generic and others.

```yaml
- task: AzureCLI@2
  inputs:
    azureSubscription: 'prod-arm-wif'    # the service connection name
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: az group list -o table
```

For Azure, I create Azure Resource Manager connections with **workload identity federation**. The pipeline gets a short-lived token, so there is no client secret to store or rotate. I automated service connection setup with Bicep, so every new project got the same configuration.

Remember:

- One connection per environment. The Dev connection cannot touch Production.
- Give its identity only the roles it needs, at the smallest scope (for example Contributor on one resource group, AcrPush on the registry).
- Do not grant it to all pipelines. Use **pipeline permissions** and add **approvals and checks** on the Production connection.

## What are Environments in GitLab and Azure DevOps?

**Interviewer:** What is the purpose of GitLab Environments in CI/CD?

**Candidate:**

An environment represents a place where the application is deployed, such as development, staging, or production. It is not about access control for runners or regions.

The CI/CD tool uses it to:

- Track which version is deployed where, and the deployment history.
- Show the environment status and a link to the deployed app.
- Protect important environments with approvals.
- Roll back to an earlier deployment.

```yaml
# GitLab
deploy_production:
  stage: deploy
  script: ./deploy.sh production
  environment:
    name: production
    url: https://orders.example.com
  when: manual
```

The same idea exists in other tools:

```text
GitLab         -> environment: + protected environments (required approvals)
Azure DevOps   -> deployment job with environment: + approvals and checks
GitHub Actions -> environment: + required reviewers
```

## How do you avoid duplicating YAML across Azure DevOps pipelines?

**Interviewer:** Dev, QA, and Prod have the same deployment steps. How do you avoid copying them?

**Candidate:**

I use **templates with parameters**. The logic is written once and each environment passes its own values.

```text
azure-pipelines.yml
templates/
  build.yml
  security-scan.yml
  helm-deploy.yml
```

`templates/helm-deploy.yml`:

```yaml
parameters:
  - name: environment
    type: string
  - name: serviceConnection
    type: string
  - name: aksName
    type: string

stages:
  - stage: Deploy_${{ parameters.environment }}
    jobs:
      - deployment: Deploy
        environment: ${{ parameters.environment }}
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: AzureCLI@2
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials -g rg-${{ parameters.environment }} -n ${{ parameters.aksName }} --overwrite-existing
                      helm upgrade --install payment-api ./helm/payment-api --set image.tag=$(Build.BuildId) --wait
```

`azure-pipelines.yml`:

```yaml
stages:
  - template: templates/helm-deploy.yml
    parameters: { environment: dev,  serviceConnection: dev-arm-wif,  aksName: aks-dev }
  - template: templates/helm-deploy.yml
    parameters: { environment: prod, serviceConnection: prod-arm-wif, aksName: aks-prod }
```

Template levels:

- **Step template** - a few repeated steps.
- **Job template** - a whole job.
- **Stage template** - a whole environment deployment.
- **Variable template** - shared variables.

For many repositories, I keep the templates in one central repo and reference them:

```yaml
resources:
  repositories:
    - repository: templates
      type: git
      name: Platform/pipeline-templates
      ref: refs/tags/v1.4.0      # pin a version

stages:
  - template: stages/helm-deploy.yml@templates
    parameters: { environment: dev, serviceConnection: dev-arm-wif, aksName: aks-dev }
```

Remember:

- Pin the template repo to a tag so a template change does not break every pipeline at once.
- `extends` templates plus the **Required template** check on an environment force every Production deployment to use the approved template (with its security scans).

## How many YAML pipelines do you have per environment?

**Interviewer:** Do you create one pipeline for each environment?

**Candidate:**

No. Usually I have **one multi-stage YAML pipeline per application**. Each environment is a stage.

```text
azure-pipelines.yml
  Build -> Test -> SonarQube -> Docker build -> Trivy -> Push to ACR
  -> Deploy Dev -> Deploy QA -> Deploy UAT -> Approval -> Deploy Prod
```

Each stage gets its own settings:

```text
Dev  -> dev variable group  + dev service connection  + aks-dev
QA   -> qa variable group   + qa service connection   + aks-qa
Prod -> prod variable group + prod service connection + aks-prod + approval
```

The deploy logic is a shared stage template, so adding an environment is a few lines, not a copied file.

Remember:

- Some teams split CI and CD into two pipelines connected by a pipeline completion trigger. That is fine. Still, it is not one pipeline per environment.
- Terraform often has its own pipeline, separate from the application pipeline.

## How do you use multiple agents in a YAML pipeline?

**Interviewer:** How do you run work on multiple agents?

**Candidate:**

**One job runs on one agent.** To use more agents, I split the work into more jobs. Jobs without `dependsOn` between them run in parallel, if the organization has enough parallel jobs.

```yaml
jobs:
  - job: Backend
    pool:
      vmImage: ubuntu-latest
    steps:
      - script: ./mvnw clean package

  - job: Frontend
    pool:
      vmImage: ubuntu-latest
    steps:
      - script: npm ci && npm run build

  - job: WindowsBuild
    pool:
      name: windows-self-hosted        # a self-hosted pool
    steps:
      - powershell: .\build.ps1

  - job: Package
    dependsOn: [Backend, Frontend]     # waits for both, may run on another agent
    pool:
      vmImage: ubuntu-latest
    steps:
      - script: echo "package"
```

```text
Agent 1: Backend   \
                     -> Agent 3: Package
Agent 2: Frontend  /
Agent 4: WindowsBuild (self-hosted pool)
```

Remember:

- Each job can pick its own pool: Microsoft-hosted, self-hosted, or a scale set pool. Use `demands` to choose agents with specific tools.
- Jobs do not share files. Pass outputs with pipeline artifacts.
- `strategy: matrix` or `parallel` creates many copies of one job, for example to test on several Node or Java versions.
- `pool: server` is an agentless job, used for `ManualValidation@1` and similar tasks.

## How do you add manual validation to an Azure DevOps pipeline?

**Interviewer:** Have you added a manual approval to a pipeline?

**Candidate:**

Yes. There are two ways.

**1. `ManualValidation@1` task** - pauses in the middle of a run, for example after a Terraform plan. It must be in an agentless job.

```yaml
- job: ReviewPlan
  dependsOn: TerraformPlan
  pool: server
  timeoutInMinutes: 1440               # longer than the task timeout
  steps:
    - task: ManualValidation@1
      timeoutInMinutes: 1380
      inputs:
        approvers: 'platform-team@company.com'
        notifyUsers: 'platform-team@company.com'
        instructions: 'Review the Terraform plan before apply.'
        allowApproversToApproveTheirOwnRuns: false
        onTimeout: 'reject'
```

**2. Environment approvals and checks** - preferred for Production. In **Pipelines -> Environments -> prod -> Approvals and checks**, I add Approvals, Branch control (only `main`), Business hours, or Exclusive lock. Any deployment job with `environment: prod` waits for them.

```text
ManualValidation task  -> lives in YAML, a developer can delete it
Environment approval   -> lives on the environment, cannot be removed by editing YAML
```

Remember:

- I use the task to review output in the middle of a run, and environment approvals to gate every Production deployment.
- The Jenkins equivalent is `input`. The GitHub equivalent is an environment with required reviewers.

## How do you promote the same ACR image from Stage to Production?

**Interviewer:** Stage and Production are in different resource groups and share one ACR. How do you deploy the same image?

**Candidate:**

I build and push the image **once**, then deploy that same reference to Stage and later to Production. I never rebuild for Production.

```text
CI: build -> scan -> push myacr.azurecr.io/payment-api:1.4.2 (digest sha256:abc...)
-> Deploy Stage (rg-stage) -> smoke tests
-> Approval
-> Deploy Prod (rg-prod) with the same tag, or better, the same digest
```

```yaml
image: myacr.azurecr.io/payment-api@sha256:<digest-tested-in-stage>
```

Both clusters need pull access. Resource groups do not matter.

```bash
az aks update -g rg-stage -n aks-stage --attach-acr myacr
az aks update -g rg-prod  -n aks-prod  --attach-acr myacr
```

`--attach-acr` gives the cluster's kubelet identity the **AcrPull** role.

Remember:

- A digest is fixed. A tag can be overwritten. I can lock a released image with `az acr repository update --image payment-api:1.4.2 --write-enabled false`.
- If ACR has a private endpoint, both cluster VNets must reach it and resolve `privatelink.azurecr.io`.
- Environment differences go in Helm values, ConfigMaps, or Key Vault, never in the image.
- With two registries (for example a separate Production ACR), I copy the tested image with `az acr import` instead of rebuilding.

## What code checks do you run in CI/CD?

**Interviewer:** What checks have you added, like SonarQube and Trivy?

**Candidate:**

I add checks at several levels. Each one can stop the pipeline.

| Check | Tool | Stops the pipeline when |
| --- | --- | --- |
| Build | Maven, npm | Code does not compile |
| Unit tests | JUnit, Jest | A test fails |
| Code quality | SonarQube Quality Gate | Bugs, low coverage, duplications, new vulnerabilities |
| Dependencies | OWASP Dependency-Check, Trivy, Snyk, `npm audit` | A known vulnerable library is used |
| Secrets | Gitleaks | A password or key is committed |
| Dockerfile | Hadolint | Bad Dockerfile practices |
| Container image | Trivy | HIGH or CRITICAL CVEs |
| IaC | `terraform validate`, TFLint, Checkov, Trivy config | Insecure or invalid infrastructure |
| Kubernetes manifests | kubeconform, `helm lint` | Invalid manifests |
| After deploy | `kubectl rollout status`, `curl` health check | The app is not healthy |

```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 myacr.azurecr.io/payment-api:1.4.2
```

If Trivy finds a CRITICAL issue, the exit code is non-zero, so the job fails. The image is not pushed and not deployed. We update the base image or library, rebuild, and scan again.

Remember:

- SonarQube is mainly a code quality tool. It finds some security issues, but it is not a container or dependency scanner.
- In my project, adding SonarQube, Trivy, and Checkov gates stopped vulnerable code, images, and IaC from reaching Production.

## How have you used Azure App Service and Azure Functions in CI/CD?

**Interviewer:** How do Web Apps, App Service, and Functions fit in your pipelines?

**Candidate:**

- **App Service** is the managed hosting platform.
- **Web App** is an App Service app that hosts a website or API.
- **Function App** runs event-driven code (HTTP, timer, Blob, Service Bus triggers). It can run on an App Service plan or a serverless plan such as Flex Consumption.

The flow is the same as for AKS, only the target changes:

```text
Push -> build -> unit tests -> SonarQube -> package once (zip or jar) -> publish artifact
-> Deploy Dev -> Deploy QA -> Approval -> Deploy Prod (staging slot -> swap)
```

```yaml
- task: AzureWebApp@1
  inputs:
    azureSubscription: prod-arm-wif
    appType: webAppLinux
    appName: payment-web-prod
    deployToSlotOrASE: true
    resourceGroupName: rg-prod
    slotName: staging
    package: $(Pipeline.Workspace)/drop/app.jar

- task: AzureAppServiceManage@0
  inputs:
    azureSubscription: prod-arm-wif
    Action: Swap Slots
    WebAppName: payment-web-prod
    ResourceGroupName: rg-prod
    SourceSlot: staging

- task: AzureFunctionApp@2
  inputs:
    connectedServiceNameARM: prod-arm-wif
    appType: functionAppLinux
    appName: doc-generator-func-prod
    package: $(Pipeline.Workspace)/drop/function.zip
```

I built Azure Functions triggered by Service Bus messages that generated documents into a Storage account. The pipeline deployed the function code. The Service Bus trigger then started each run.

Remember:

- Deploy to a **staging slot**, warm it up and test it, then **swap**. Rollback is swapping back.
- App settings are per environment. Secrets use Key Vault references (`@Microsoft.KeyVault(SecretUri=...)`) and the app's managed identity.
- I verify the release with the health endpoint, Application Insights, and Azure Monitor alerts.

## A unit test fails in the pipeline. How do you help the developer?

**Interviewer:** If there is an issue with unit testing, how will you assist the developer?

**Candidate:**

I do not just send the failure back and say "please fix it." I find out **whose problem it is** first, give the developer clear evidence, and own the part that belongs to DevOps.

```text
Unit test fails in CI
-> read the test report and stack trace
-> does it also fail locally, on the same commit?
   yes -> code or test logic -> developer fixes, I share the evidence
   no  -> environment or pipeline -> I fix it
-> re-run the full test suite
-> pipeline continues only when all tests pass
```

| Failure type | Typical signs | Who fixes it |
| --- | --- | --- |
| Code bug | Fails locally and in CI with the same assertion | Developer |
| Test bug or test data | Wrong expected value, test depends on order or current date | Developer, I point to the cause |
| Flaky test | Passes on re-run with no code change | Developer marks or fixes it; I track flaky tests |
| Environment | Different JDK or Node version, missing env variable, time zone, no network to a dependency | DevOps |
| Pipeline | Wrong working directory, stale cache, wrong agent image, test DB not started | DevOps |

What I give the developer:

- The failing test name, the error, and the stack trace, plus the commit and pipeline run link.
- The exact command and tool versions the pipeline used, so they can reproduce it (for example `mvn -B test -Dtest=PaymentServiceTest`).
- What changed recently: their commit, a dependency update, or an agent image change.

Remember:

- Publish test results (`PublishTestResults@2` in Azure DevOps, `junit` in Jenkins, test reports in GitLab and GitHub). The **Tests** tab shows the failing test and its history, so nobody has to dig through logs.
- Never skip tests (`-DskipTests`) to get a release out. Fix the test or quarantine a known flaky one with a ticket.
- Pin tool versions in the agent image, so "works on my machine" does not happen because of a different JDK.

## Write a prompt for an AI assistant to analyze a failing build

**Interviewer:** A Jenkins Maven build fails with compilation errors after a successful checkout. Write the prompt you would give an AI assistant.

**Candidate:**

A good prompt gives **context, the exact error, what I already know, and the output I want**. It never includes secrets.

```text
You are helping me debug a failing Jenkins pipeline.

Context:
- Java Spring Boot application, built with Maven in a Jenkins Declarative Pipeline.
- Agent image: maven:3.9-eclipse-temurin-17. pom.xml sets maven.compiler.release=17.
- Git checkout succeeded. The build fails in the "mvn -B clean package" stage with compilation errors.
- The last successful build was commit <old-sha>. The failing build is commit <new-sha>.

Error log (secrets and internal hostnames removed):
<paste the first error and about 30 lines around it, not the whole log>

Changes between the two commits:
<paste git diff --stat, and the pom.xml diff if there is one>

What I want:
1. The most likely root cause, and why.
2. Other possible causes, in order of likelihood (Java version, dependency versions, generated code, source code).
3. The exact fix, as a code or pom.xml change.
4. Maven commands to confirm the fix locally (for example mvn -v, mvn dependency:tree, mvn -B clean compile).
If you are not sure, say what extra information you need instead of guessing.
```

Why this works:

- **Context narrows the search.** Saying checkout succeeded and naming the Java and Maven versions stops generic answers.
- **The first error matters most.** Later compiler errors are often caused by the first one.
- **The diff between the good and bad commit** is usually where the cause is.
- **A clear output format** gives a fix and a way to verify it, not just an explanation.
- **Remove secrets** (tokens, passwords, internal URLs) before pasting anything into an AI tool, and follow the company's AI usage policy.

I check the AI's answer myself before changing anything. It is a fast first opinion, not the final answer.
