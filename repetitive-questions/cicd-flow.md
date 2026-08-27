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

          - task: AzureCLI@2
            displayName: Set AKS Context (Dev)
            inputs:
              azureSubscription: 'AKS-Dev-Service-Connection'
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                az aks get-credentials --resource-group myResourceGroup --name $(aksDev) --overwrite-existing

          - script: |
              helm upgrade --install payment-api ./helm/payment-api \
                --namespace $(namespace) \
                --create-namespace \
                --set image.repository=$(acrName).azurecr.io/$(imageName) \
                --set image.tag=$(imageTag) \
                --wait
            displayName: Helm Upgrade/Install to AKS Dev


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

          - task: AzureCLI@2
            displayName: Set AKS Context (Production)
            inputs:
              azureSubscription: 'AKS-Prod-Service-Connection'
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                az aks get-credentials --resource-group myResourceGroup --name $(aksProd) --overwrite-existing

          - script: |
              helm upgrade --install payment-api ./helm/payment-api \
                --namespace $(namespace) \
                --create-namespace \
                --set image.repository=$(acrName).azurecr.io/$(imageName) \
                --set image.tag=$(imageTag) \
                --wait
            displayName: Helm Upgrade/Install to AKS Production
```

### What this pipeline does, in simple words

A top-level `pool: vmImage: 'ubuntu-latest'` sets the default agent for every job. The Approval stage overrides it with `pool: server`, since manual validation runs on Azure DevOps's built-in agentless pool, not a VM.

Each `stage` runs only after the one before it finishes successfully, because of `dependsOn`. If one stage fails, the pipeline stops there and nothing later runs.

1. **Build** – Compiles both halves of the app: the React frontend (`npm install` + `npm run build`) and the Spring Boot backend (`./mvnw clean package`).
2. **Test** – Runs the backend unit tests (`./mvnw test`) and the frontend tests (`npm test`). This is separate from Build so test failures are easy to spot.
3. **SonarQube** – Scans the code for bugs, code smells, and coverage gaps, and publishes the results back to Azure DevOps.
4. **Docker Build** – Packages the backend into a Docker image, tagged with the Azure DevOps build ID (`$(Build.BuildId)`) so every image is unique and traceable back to a build.
5. **Trivy Scan** – Scans the built image for known vulnerabilities. `--exit-code 1` means the pipeline fails if a HIGH or CRITICAL issue is found, so a vulnerable image never moves forward.
6. **Push to ACR** – Only after the image passes the security scan, it is pushed to Azure Container Registry.
7. **Deploy to Dev** – First fetches AKS credentials with `az aks get-credentials`, then runs `helm upgrade --install` to deploy (or update) the `payment-api` chart on the Dev cluster, pointing at the image that was just pushed. `--wait` makes the step block until the rollout is healthy.
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
      - uses: azure/docker-login@v1
        with:
          login-server: ${{ env.ACR_NAME }}.azurecr.io
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      - run: |
          docker tag $IMAGE_NAME:$IMAGE_TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG
          docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

  deploy-dev:
    needs: push-acr
    runs-on: ubuntu-latest
    environment: Dev
    steps:
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
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
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
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

## Secrets

Passwords and tokens are stored in the CI/CD platform's protected secret store or in Azure Key Vault. They are not written directly in pipeline YAML or printed in logs.

Where possible, I use short-lived identity-based authentication instead of a saved username and password.

## Example

Suppose commit `a1b2c3` is merged into `main`. The pipeline tests it, builds `orders-api:a1b2c3`, scans it, and pushes it to the registry. That same image is deployed to Development and tested. After approval, it is promoted to Production and monitored.

## In short

My CI/CD flow starts with a pull request and automated checks. After merge, the pipeline builds and scans one versioned image, deploys it to a lower environment, and promotes the same image to Production after approval.

I verify the rollout and keep the previous Helm revision available for rollback.
