# Repetitive Interview Questions

## Write a sample end-to-end pipeline and explain it

**Interviewer:** Can you write a sample CI/CD pipeline using Jenkins, Azure DevOps, GitHub Actions, or GitLab CI?

**Candidate:**

The syntax changes between tools, but the delivery flow stays the same:

```text
checkout
-> build and unit test
-> static analysis and Quality Gate
-> dependency scan
-> build image
-> image scan
-> push image
-> deploy to Development
-> verify and smoke test
-> Production approval
-> deploy the same image to Production
-> verify, smoke test, and monitor
```

The examples below are production-oriented but still use placeholders. They assume:

- The application has a working Dockerfile.
- The Helm chart exists in `helm/orders-api`.
- The build agent has Maven, Docker, Helm, Azure CLI, `kubectl`, Trivy, and `curl`.
- SonarQube and OWASP Dependency-Check are configured for the project.
- Registry and AKS access are configured through a protected identity.
- Production approval is restricted to authorized users.

I use placeholders such as `<acr-name>` and `<resource-group>` because these values differ by project.

## Common deployment command

All four examples eventually run a command like:

```bash
helm upgrade --install orders-api ./helm/orders-api \
  --namespace <namespace> \
  --create-namespace \
  --set image.repository=<registry>/orders-api \
  --set image.tag=<version> \
  --wait
```

The image version is unique, such as a Git commit or pipeline number. I do not use `latest`.

---

## Answer 1: Jenkins Declarative Pipeline

### `Jenkinsfile`

```groovy
pipeline {
  agent { label 'docker-azure' }

  options {
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
    timestamps()
    timeout(time: 60, unit: 'MINUTES')
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
    DEVELOPMENT_RESOURCE_GROUP = '<development-resource-group>'
    DEVELOPMENT_AKS_NAME = '<development-aks-name>'
    PRODUCTION_RESOURCE_GROUP = '<production-resource-group>'
    PRODUCTION_AKS_NAME = '<production-aks-name>'
    DEVELOPMENT_HEALTH_URL = 'https://orders-api-dev.example.com/actuator/health'
    PRODUCTION_HEALTH_URL = 'https://orders.example.com/actuator/health'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build and Unit Test') {
      steps {
        sh 'mvn -B clean verify'
      }
    }

    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv("${SONARQUBE_SERVER}") {
          sh '''
            mvn -B sonar:sonar \
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

    stage('Dependency Vulnerability Scan') {
      steps {
        sh '''
          mvn -B org.owasp:dependency-check-maven:check \
            -DfailBuildOnCVSS=7 \
            -Dformat=HTML
        '''
      }
    }

    stage('Build Image') {
      steps {
        sh 'docker build -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG .'
      }
    }

    stage('Scan Image') {
      steps {
        sh '''
          trivy image \
            --exit-code 1 \
            --severity HIGH,CRITICAL \
            $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
        '''
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
            --resource-group "$DEVELOPMENT_RESOURCE_GROUP" \
            --name "$DEVELOPMENT_AKS_NAME" \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace development \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=$IMAGE_TAG \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace development

          curl --fail --show-error --silent \
            --retry 10 --retry-delay 5 --retry-connrefused \
            $DEVELOPMENT_HEALTH_URL
        '''
      }
    }

    stage('Approve Production') {
      when {
        branch 'main'
      }
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
      when {
        branch 'main'
      }
      steps {
        sh '''
          az aks get-credentials \
            --resource-group "$PRODUCTION_RESOURCE_GROUP" \
            --name "$PRODUCTION_AKS_NAME" \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace production \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=$IMAGE_TAG \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace production

          curl --fail --show-error --silent \
            --retry 10 --retry-delay 5 --retry-connrefused \
            $PRODUCTION_HEALTH_URL
        '''
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'target/surefire-reports/*.xml'
      archiveArtifacts allowEmptyArchive: true,
        artifacts: 'target/dependency-check-report.html'
    }
    success {
      emailext subject: "SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
        body: "Build details: ${env.BUILD_URL}",
        to: 'devops-team@example.com'
    }
    failure {
      emailext subject: "FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
        body: "Build details: ${env.BUILD_URL}",
        to: 'devops-team@example.com'
    }
  }
}
```

### Pipeline flow

```text
Checkout
-> Build and unit test
-> SonarQube static analysis
-> Quality Gate
-> Dependency vulnerability scan
-> Build Docker image
-> Scan Docker image
-> Push image to ACR
-> Deploy to Development
-> Verify rollout and run a smoke test
-> Authorized Production approval
-> Deploy the same image to Production
-> Verify rollout and run a smoke test
-> Publish test results and notify the team
```

### Explanation

- `agent` selects a worker with Maven, Docker, Azure CLI, Helm, `kubectl`, Trivy, and network access to SonarQube.
- `skipDefaultCheckout(true)` prevents Jenkins from performing an implicit checkout before the explicit `Checkout` stage.
- `environment` defines values reused in the stages.
- `Build and Unit Test` compiles, packages, and tests the application. A failed test stops the pipeline.
- `SonarQube Analysis` checks code quality, bugs, vulnerabilities, duplication, and coverage.
- `waitForQualityGate` stops delivery when the SonarQube Quality Gate fails. The SonarQube server must have a webhook configured for Jenkins.
- OWASP Dependency-Check fails the build for dependency findings with a CVSS score of 7 or higher, while Trivy fails it for high or critical findings in the final container image.
- The immutable image is tagged with the Jenkins build number and pushed only after all pre-deployment checks pass.
- Helm deploys to Development first. `kubectl rollout status` and the health endpoint verify the release.
- The Production stages run only from `main`, and `input` pauses for an authorized approval.
- Production receives the exact image already tested in Development; Jenkins does not rebuild it.
- `post` publishes JUnit results and archives the dependency report even if a later stage fails. The sample uses the Jenkins Email Extension plugin; Slack or Teams can be used instead.

The Jenkins agent should use managed identity or credentials stored in Jenkins and retrieve application secrets from Azure Key Vault. Secrets must not be hardcoded in the `Jenkinsfile`. In a real project, pin scanner and Maven plugin versions, cache dependencies, publish the packaged artifact or software bill of materials (SBOM), and add secret and Infrastructure-as-Code scanning where applicable.

For safer Production releases, teams can replace direct `helm upgrade` commands with GitOps through Argo CD or Flux and use canary or blue-green deployment strategies. Image tags can also include the Git commit SHA for stronger traceability.

### One-minute interview answer

This Jenkins Declarative Pipeline checks out the source, builds it, and runs unit tests with Maven. It then performs SonarQube static analysis and blocks the pipeline if the Quality Gate fails. OWASP Dependency-Check scans application dependencies, and Trivy scans the Docker image for high and critical vulnerabilities before the image is pushed to Azure Container Registry. Jenkins deploys that immutable image to Development with Helm, verifies the Kubernetes rollout, and runs a health check. For the `main` branch, an authorized user approves promotion of the same tested image to Production, where Jenkins repeats the rollout and smoke checks. Finally, Jenkins publishes the JUnit reports and sends the configured success or failure notification.

---

## Answer 2: Azure DevOps Pipeline

### `azure-pipelines.yml`

```yaml
trigger:
  batch: true
  branches:
    include:
      - main

pr:
  branches:
    include:
      - main

variables:
  imageRepository: orders-api
  imageTag: $(Build.SourceVersion)
  registryServer: <acr-name>.azurecr.io
  developmentResourceGroup: <development-resource-group>
  developmentAksName: <development-aks-name>
  productionResourceGroup: <production-resource-group>
  productionAksName: <production-aks-name>
  developmentHealthUrl: https://orders-api-dev.example.com/actuator/health
  productionHealthUrl: https://orders.example.com/actuator/health

stages:
  - stage: Quality
    displayName: Build, test, and analyze
    jobs:
      - job: QualityChecks
        pool:
          vmImage: ubuntu-latest
        steps:
          - checkout: self
            fetchDepth: 0

          - task: SonarQubePrepare@7
            displayName: Prepare SonarQube analysis
            inputs:
              SonarQube: <sonarqube-service-connection>
              scannerMode: other
              extraProperties: |
                sonar.projectKey=orders-api
                sonar.projectName=orders-api
                sonar.qualitygate.wait=true
                sonar.qualitygate.timeout=600

          - task: Maven@4
            displayName: Build, unit test, and run SonarQube analysis
            inputs:
              mavenPomFile: pom.xml
              goals: clean verify
              options: -B
              publishJUnitResults: false
              sonarQubeRunAnalysis: true

          - task: SonarQubePublish@7
            displayName: Publish Quality Gate
            inputs:
              pollingTimeoutSec: "600"

          - script: |
              mvn -B org.owasp:dependency-check-maven:check \
                -DfailBuildOnCVSS=7 \
                -Dformat=HTML
            displayName: Scan dependencies

          - task: PublishTestResults@2
            condition: always()
            inputs:
              testResultsFormat: JUnit
              testResultsFiles: target/surefire-reports/*.xml
              failTaskOnFailedTests: true

          - task: PublishPipelineArtifact@1
            condition: always()
            continueOnError: true
            inputs:
              targetPath: target/dependency-check-report.html
              artifact: dependency-check-report

  - stage: Build
    displayName: Build, scan, and push image
    dependsOn: Quality
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - job: BuildImage
        pool:
          vmImage: ubuntu-latest
        steps:
          - checkout: self

          - task: Docker@2
            displayName: Build image
            inputs:
              containerRegistry: <acr-service-connection>
              repository: $(imageRepository)
              command: build
              Dockerfile: Dockerfile
              tags: $(imageTag)

          - script: |
              docker run --rm \
                -v /var/run/docker.sock:/var/run/docker.sock \
                "aquasec/trivy:<approved-version>" image \
                --exit-code 1 \
                --severity HIGH,CRITICAL \
                $(registryServer)/$(imageRepository):$(imageTag)
            displayName: Scan image

          - task: Docker@2
            displayName: Push image
            inputs:
              containerRegistry: <acr-service-connection>
              repository: $(imageRepository)
              command: push
              tags: $(imageTag)

  - stage: Development
    dependsOn: Build
    jobs:
      - deployment: DeployDevelopment
        environment: development
        pool:
          vmImage: ubuntu-latest
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: AzureCLI@2
                  displayName: Deploy and verify Development
                  inputs:
                    azureSubscription: <development-service-connection>
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials \
                        --resource-group "$(developmentResourceGroup)" \
                        --name "$(developmentAksName)" \
                        --overwrite-existing

                      helm upgrade --install orders-api ./helm/orders-api \
                        --namespace development \
                        --create-namespace \
                        --set image.repository=$(registryServer)/$(imageRepository) \
                        --set image.tag=$(imageTag) \
                        --wait

                      kubectl rollout status deployment/orders-api \
                        --namespace development

                      curl --fail --show-error --silent \
                        --retry 10 --retry-delay 5 --retry-connrefused \
                        $(developmentHealthUrl)

  - stage: Production
    dependsOn: Development
    condition: succeeded()
    jobs:
      - deployment: DeployProduction
        environment: production
        pool:
          vmImage: ubuntu-latest
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: AzureCLI@2
                  displayName: Deploy and verify Production
                  inputs:
                    azureSubscription: <production-service-connection>
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials \
                        --resource-group "$(productionResourceGroup)" \
                        --name "$(productionAksName)" \
                        --overwrite-existing

                      helm upgrade --install orders-api ./helm/orders-api \
                        --namespace production \
                        --create-namespace \
                        --set image.repository=$(registryServer)/$(imageRepository) \
                        --set image.tag=$(imageTag) \
                        --wait

                      kubectl rollout status deployment/orders-api \
                        --namespace production

                      curl --fail --show-error --silent \
                        --retry 10 --retry-delay 5 --retry-connrefused \
                        $(productionHealthUrl)
```

### Pipeline flow

```text
Build and unit test
-> SonarQube analysis and blocking Quality Gate
-> Dependency vulnerability scan
-> Build and scan the image
-> Push the image to ACR
-> Deploy and smoke-test Development
-> Protected Production Environment approval
-> Deploy and smoke-test the same image in Production
-> Publish reports and notify the team
```

### Explanation

- `trigger.batch` prevents queued changes from creating overlapping `main` runs, while `pr` validates pull requests.
- `fetchDepth: 0` gives SonarQube the Git history required for accurate issue attribution.
- `SonarQubePrepare`, Maven analysis, and `SonarQubePublish` submit the analysis and expose the Quality Gate in the build summary. Waiting for the gate makes a failure stop the pipeline.
- OWASP Dependency-Check fails for findings with a CVSS score of 7 or higher and publishes its HTML report.
- The Docker image is scanned with Trivy before `Docker@2` pushes it to ACR.
- Build and deployment stages run only after a successful Quality stage and only for `main`.
- Deployment jobs record the environment history, verify the Kubernetes rollout, and call the application health endpoint.
- Approval and an exclusive-lock check should be configured on the protected `production` Environment in Azure DevOps.
- Separate workload-identity service connections should isolate Development, Production, and ACR permissions.
- Azure DevOps notification subscriptions or service hooks can send results to email, Teams, or Slack without embedding notification secrets in YAML.

The `SonarQubePrepare@7` and `SonarQubePublish@7` tasks require the SonarQube Azure DevOps extension and a configured service connection. Pin task and scanner versions according to the versions approved by the organization.

### One-minute interview answer

This Azure DevOps pipeline builds and tests the Maven application, submits SonarQube analysis, and blocks delivery when the Quality Gate fails. It also scans dependencies with OWASP Dependency-Check. For successful `main` builds, it creates one commit-tagged Docker image, scans it with Trivy, and pushes it to ACR. Deployment jobs promote that same image through Development and the protected Production Environment, verifying both the Kubernetes rollout and application health. Production checks enforce authorized approval and prevent unsafe concurrent releases, while test and security reports remain available in the pipeline.

---

## Answer 3: GitHub Actions

### `.github/workflows/delivery.yml`

```yaml
name: delivery

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

permissions:
  contents: read

env:
  ACR_NAME: <acr-name>
  REGISTRY: <acr-name>.azurecr.io
  IMAGE_NAME: orders-api
  DEVELOPMENT_RESOURCE_GROUP: <development-resource-group>
  DEVELOPMENT_AKS_NAME: <development-aks-name>
  PRODUCTION_RESOURCE_GROUP: <production-resource-group>
  PRODUCTION_AKS_NAME: <production-aks-name>
  DEVELOPMENT_HEALTH_URL: https://orders-api-dev.example.com/actuator/health
  PRODUCTION_HEALTH_URL: https://orders.example.com/actuator/health

jobs:
  quality:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
          cache: maven

      - name: Build, unit test, analyze, and wait for Quality Gate
        env:
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        run: |
          mvn -B clean verify sonar:sonar \
            -Dsonar.projectKey=orders-api \
            -Dsonar.host.url="$SONAR_HOST_URL" \
            -Dsonar.token="$SONAR_TOKEN" \
            -Dsonar.qualitygate.wait=true \
            -Dsonar.qualitygate.timeout=600

      - name: Scan dependencies
        run: |
          mvn -B org.owasp:dependency-check-maven:check \
            -DfailBuildOnCVSS=7 \
            -Dformat=HTML

      - name: Publish unit-test and dependency reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: quality-reports
          path: |
            target/surefire-reports/*.xml
            target/dependency-check-report.html
          if-no-files-found: ignore

  build:
    if: github.event_name == 'push'
    needs: quality
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t $REGISTRY/$IMAGE_NAME:${{ github.sha }} .

      - name: Scan image
        run: |
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            "aquasec/trivy:<approved-version>" image \
            --exit-code 1 \
            --severity HIGH,CRITICAL \
            $REGISTRY/$IMAGE_NAME:${{ github.sha }}

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Push image to ACR
        run: |
          az acr login --name "$ACR_NAME"
          docker push $REGISTRY/$IMAGE_NAME:${{ github.sha }}

  development:
    needs: build
    runs-on: ubuntu-latest
    environment: development
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: |
          az aks get-credentials \
            --resource-group "$DEVELOPMENT_RESOURCE_GROUP" \
            --name "$DEVELOPMENT_AKS_NAME" \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace development \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=${{ github.sha }} \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace development

          curl --fail --show-error --silent \
            --retry 10 --retry-delay 5 --retry-connrefused \
            "$DEVELOPMENT_HEALTH_URL"

  production:
    needs: development
    runs-on: ubuntu-latest
    environment: production
    concurrency: production
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: |
          az aks get-credentials \
            --resource-group "$PRODUCTION_RESOURCE_GROUP" \
            --name "$PRODUCTION_AKS_NAME" \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace production \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=${{ github.sha }} \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace production

          curl --fail --show-error --silent \
            --retry 10 --retry-delay 5 --retry-connrefused \
            "$PRODUCTION_HEALTH_URL"
```

### Pipeline flow

```text
Build and unit test
-> SonarQube analysis and blocking Quality Gate
-> Dependency vulnerability scan
-> Build and scan the image
-> Push the image to ACR
-> Deploy and smoke-test Development
-> Required Production Environment review
-> Deploy and smoke-test the same image in Production
-> Retain reports and notify the team
```

### Explanation

- Pull requests run the quality and security checks, while a push to `main` also publishes and deploys the image.
- `fetch-depth: 0` supplies the Git history needed by SonarQube.
- `sonar.qualitygate.wait=true` makes a failed Quality Gate fail the job instead of merely displaying a result.
- OWASP Dependency-Check gates high-risk dependencies, and the reports are retained as a workflow artifact.
- Trivy scans the locally built image before Azure authentication and before the push to ACR.
- `needs` defines the job order.
- Job-scoped `id-token: write` lets only deployment-related jobs obtain short-lived Azure access through OpenID Connect.
- Required reviewers and protected secrets are configured on the GitHub `production` Environment.
- `concurrency: production` prevents overlapping Production deployments.
- Both environments verify the Kubernetes rollout and application health for the same commit-SHA image.
- GitHub's built-in Actions notifications can be supplemented with an organization-approved Teams, Slack, or email integration.

Forked pull requests do not receive repository secrets, so organizations should use SonarQube's recommended fork policy and never expose credentials to untrusted code. Pin actions and the Trivy container to reviewed immutable versions or digests rather than leaving version placeholders in a real workflow.

### One-minute interview answer

This GitHub Actions workflow builds and tests the Maven application, sends the results to SonarQube, and waits for the Quality Gate. It also blocks high-risk dependency findings. A successful push to `main` builds a commit-tagged Docker image, scans it with Trivy, authenticates to Azure through OpenID Connect, and pushes it to ACR. The workflow deploys the same image to Development, verifies the rollout and health endpoint, and then pauses at the protected Production Environment for a required review. After approval it performs the same checks in Production, while concurrency prevents overlapping Production deployments.

---

## Answer 4: GitLab CI/CD

### `.gitlab-ci.yml`

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

stages:
  - quality
  - security
  - build
  - development
  - production

variables:
  ACR_NAME: <acr-name>
  REGISTRY: <acr-name>.azurecr.io
  IMAGE_NAME: orders-api
  IMAGE_TAG: $CI_COMMIT_SHA
  GIT_DEPTH: "0"
  MAVEN_OPTS: -Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository
  SONAR_USER_HOME: $CI_PROJECT_DIR/.sonar
  DEVELOPMENT_RESOURCE_GROUP: <development-resource-group>
  DEVELOPMENT_AKS_NAME: <development-aks-name>
  PRODUCTION_RESOURCE_GROUP: <production-resource-group>
  PRODUCTION_AKS_NAME: <production-aks-name>
  DEVELOPMENT_HEALTH_URL: https://orders-api-dev.example.com/actuator/health
  PRODUCTION_HEALTH_URL: https://orders.example.com/actuator/health

quality:
  stage: quality
  cache:
    key: maven-sonar
    paths:
      - .m2/repository
      - .sonar/cache
  script:
    - >
      mvn -B clean verify sonar:sonar
      -Dsonar.projectKey=orders-api
      -Dsonar.qualitygate.wait=true
      -Dsonar.qualitygate.timeout=600
  artifacts:
    when: always
    paths:
      - target/site/jacoco/
    reports:
      junit:
        - target/surefire-reports/*.xml

dependency_scan:
  stage: security
  needs:
    - quality
  script:
    - >
      mvn -B org.owasp:dependency-check-maven:check
      -DfailBuildOnCVSS=7
      -Dformat=HTML
  artifacts:
    when: always
    paths:
      - target/dependency-check-report.html

build_scan_push:
  stage: build
  needs:
    - quality
    - dependency_scan
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  script:
    - docker build -t "$REGISTRY/$IMAGE_NAME:$IMAGE_TAG" .
    - >
      docker run --rm
      -v /var/run/docker.sock:/var/run/docker.sock
      "aquasec/trivy:<approved-version>" image
      --exit-code 1
      --severity HIGH,CRITICAL
      "$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    - az acr login --name "$ACR_NAME"
    - docker push "$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

deploy_development:
  stage: development
  needs:
    - build_scan_push
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  environment:
    name: development
  script:
    - >
      az aks get-credentials
      --resource-group "$DEVELOPMENT_RESOURCE_GROUP"
      --name "$DEVELOPMENT_AKS_NAME"
      --overwrite-existing
    - >
      helm upgrade --install orders-api ./helm/orders-api
      --namespace development
      --create-namespace
      --set image.repository="$REGISTRY/$IMAGE_NAME"
      --set image.tag="$IMAGE_TAG"
      --wait
    - kubectl rollout status deployment/orders-api --namespace development
    - >
      curl --fail --show-error --silent
      --retry 10 --retry-delay 5 --retry-connrefused
      "$DEVELOPMENT_HEALTH_URL"

deploy_production:
  stage: production
  needs:
    - deploy_development
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  environment:
    name: production
  resource_group: production
  when: manual
  allow_failure: false
  script:
    - >
      az aks get-credentials
      --resource-group "$PRODUCTION_RESOURCE_GROUP"
      --name "$PRODUCTION_AKS_NAME"
      --overwrite-existing
    - >
      helm upgrade --install orders-api ./helm/orders-api
      --namespace production
      --create-namespace
      --set image.repository="$REGISTRY/$IMAGE_NAME"
      --set image.tag="$IMAGE_TAG"
      --wait
    - kubectl rollout status deployment/orders-api --namespace production
    - >
      curl --fail --show-error --silent
      --retry 10 --retry-delay 5 --retry-connrefused
      "$PRODUCTION_HEALTH_URL"
```

### Pipeline flow

```text
Build and unit test
-> SonarQube analysis and blocking Quality Gate
-> Dependency vulnerability scan
-> Build and scan the image
-> Push the image to ACR
-> Deploy and smoke-test Development
-> Protected manual Production approval
-> Deploy and smoke-test the same image in Production
-> Retain reports and notify the team
```

### Explanation

- `workflow.rules` creates pipelines for merge requests and the default branch without creating redundant feature-branch pipelines.
- `GIT_DEPTH: "0"` provides complete Git history to SonarQube.
- `sonar.qualitygate.wait=true` makes the SonarQube job block the pipeline when the Quality Gate fails.
- OWASP Dependency-Check fails on dependency findings with a CVSS score of 7 or higher and retains the HTML report.
- The image is built once, scanned with Trivy, and pushed only from the default branch after all gates pass.
- `needs` defines the dependency graph and prevents later jobs from running after a failed quality or security check.
- Test, coverage, and security reports remain available even when their jobs fail.
- Development and Production deployments verify both the Kubernetes rollout and the application health endpoint.
- `when: manual` creates the Production approval action.
- A protected Production Environment limits who can approve and deploy.
- `resource_group` prevents two Production deployments from running at the same time.
- The same commit-tagged image goes to Development and Production.

The runner should use a protected short-lived Azure identity. Store `SONAR_TOKEN` and `SONAR_HOST_URL` as masked CI/CD variables, and never expose Production variables or runners to untrusted merge-request code. GitLab integrations can send pipeline results to email, Teams, or Slack without hardcoding webhook secrets in the file.

### One-minute interview answer

This GitLab pipeline runs for merge requests and the default branch. It builds and tests the Maven project, performs SonarQube analysis, waits for the Quality Gate, and scans dependencies with OWASP Dependency-Check. On the default branch, it builds one commit-tagged container, blocks high and critical Trivy findings, and pushes the image to ACR. GitLab then deploys the same image to Development and verifies both rollout and health. Production is a protected manual job, and its resource group prevents concurrent releases. Test, coverage, and security reports are retained for troubleshooting and audit.

---

## Security checks

A real project normally adds:

```text
source-code scan
dependency scan
secret scan
container-image scan
infrastructure scan
```

A serious finding stops the release. Security tokens are stored in the platform's protected secret store or replaced with identity-based access.

## Build once and promote

The most important rule is to build the image once.

```text
orders-api:a1b2c3
-> Development
-> Production approval
-> Production
```

Rebuilding for Production could produce a different image from the one that was tested.

## Rollback

Check the release history:

```bash
helm history orders-api -n production
```

Restore a known working revision:

```bash
helm rollback orders-api <revision> \
  --namespace production \
  --wait
```

Application rollback must be compatible with any database change.

## Common mistakes I avoid

- Putting passwords directly in pipeline files.
- Allowing pull-request jobs to use Production credentials.
- Deploying the `latest` image tag.
- Rebuilding a different image for Production.
- Skipping tests because the image built successfully.
- Treating a successful Helm command as full application verification.
- Allowing overlapping Production deployments.
- Rolling back code without checking database compatibility.

## Example

Suppose commit `a1b2c3` is merged into `main`. The pipeline runs tests, passes the SonarQube and dependency gates, builds and scans `orders-api:a1b2c3`, and pushes it to ACR.

It deploys that image to Development and verifies the rollout and health endpoint. After approval, the same image is deployed and verified in Production.

If verification fails, the pipeline stops and the team can restore the previous Helm revision.

## In short

Jenkins, Azure DevOps, GitHub Actions, and GitLab use different syntax, but my process is the same: test the code, enforce quality and security gates, build and scan one versioned image, deploy and smoke-test it in Development, obtain Production approval, and promote and verify the same image.

Identities and secrets are protected, and the previous Helm revision remains available for rollback.
