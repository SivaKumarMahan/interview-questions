# Repetitive Interview Questions

## Write a sample end-to-end pipeline and explain it

**Interviewer:** Can you write a sample CI/CD pipeline using Jenkins, Azure DevOps, GitHub Actions, or GitLab CI?

**Candidate:**

The syntax changes between tools, but the delivery flow stays the same:

```text
checkout
-> test
-> build image
-> push image
-> deploy to Development
-> verify
-> Production approval
-> deploy the same image to Production
-> verify and monitor
```

The examples below are intentionally small. They assume:

- The application has a working Dockerfile.
- The Helm chart exists in `helm/orders-api`.
- The build agent has Docker, Helm, Azure CLI, and `kubectl`.
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

### Explanation

- `agent` selects a worker that has the required tools.
- `environment` defines values reused in the stages.
- `Test` stops the pipeline if Maven tests fail.
- The image is tagged with the Jenkins build number.
- Development deployment happens before Production.
- `input` pauses for an authorized Production approval.
- `post` publishes test results even when a later stage fails.

The Jenkins agent should use managed identity or protected credentials. Secrets should not be written directly in the `Jenkinsfile`.

---

## Answer 2: Azure DevOps Pipeline

### `azure-pipelines.yml`

```yaml
trigger:
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

stages:
  - stage: Test
    jobs:
      - job: UnitTests
        pool:
          vmImage: ubuntu-latest
        steps:
          - checkout: self
          - script: mvn -B clean verify
            displayName: Run tests
          - task: PublishTestResults@2
            condition: always()
            inputs:
              testResultsFormat: JUnit
              testResultsFiles: target/surefire-reports/*.xml

  - stage: Build
    dependsOn: Test
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - job: BuildImage
        pool:
          vmImage: ubuntu-latest
        steps:
          - checkout: self
          - task: Docker@2
            displayName: Build and push image
            inputs:
              containerRegistry: <acr-service-connection>
              repository: $(imageRepository)
              command: buildAndPush
              Dockerfile: Dockerfile
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
                  inputs:
                    azureSubscription: <development-service-connection>
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials \
                        --resource-group <development-resource-group> \
                        --name <development-aks-name> \
                        --overwrite-existing

                      helm upgrade --install orders-api ./helm/orders-api \
                        --namespace development \
                        --create-namespace \
                        --set image.repository=$(registryServer)/$(imageRepository) \
                        --set image.tag=$(imageTag) \
                        --wait

                      kubectl rollout status deployment/orders-api \
                        --namespace development

  - stage: Production
    dependsOn: Development
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
                  inputs:
                    azureSubscription: <production-service-connection>
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      az aks get-credentials \
                        --resource-group <production-resource-group> \
                        --name <production-aks-name> \
                        --overwrite-existing

                      helm upgrade --install orders-api ./helm/orders-api \
                        --namespace production \
                        --create-namespace \
                        --set image.repository=$(registryServer)/$(imageRepository) \
                        --set image.tag=$(imageTag) \
                        --wait

                      kubectl rollout status deployment/orders-api \
                        --namespace production
```

### Explanation

- `trigger` runs the pipeline for changes to `main`.
- `pr` runs validation for pull requests.
- Stages run in order because of `dependsOn`.
- `Docker@2` builds and pushes the image.
- A deployment job records which environment received the release.
- Production approval is configured on the protected `production` Environment in Azure DevOps, outside editable pipeline YAML.
- Separate service connections can keep Development and Production permissions apart.

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
  id-token: write

env:
  REGISTRY: <acr-name>.azurecr.io
  IMAGE_NAME: orders-api

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
          cache: maven
      - run: mvn -B clean verify

  build:
    if: github.event_name == 'push'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: az acr login --name <acr-name>
      - run: docker build -t $REGISTRY/$IMAGE_NAME:${{ github.sha }} .
      - run: docker push $REGISTRY/$IMAGE_NAME:${{ github.sha }}

  development:
    needs: build
    runs-on: ubuntu-latest
    environment: development
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: |
          az aks get-credentials \
            --resource-group <development-resource-group> \
            --name <development-aks-name> \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace development \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=${{ github.sha }} \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace development

  production:
    needs: development
    runs-on: ubuntu-latest
    environment: production
    concurrency: production
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - run: |
          az aks get-credentials \
            --resource-group <production-resource-group> \
            --name <production-aks-name> \
            --overwrite-existing

          helm upgrade --install orders-api ./helm/orders-api \
            --namespace production \
            --create-namespace \
            --set image.repository=$REGISTRY/$IMAGE_NAME \
            --set image.tag=${{ github.sha }} \
            --wait

          kubectl rollout status deployment/orders-api \
            --namespace production
```

### Explanation

- Pull requests run only the test job.
- A merge to `main` also builds, pushes, and deploys the image.
- `needs` defines the job order.
- OpenID Connect lets GitHub obtain short-lived Azure access instead of storing an Azure client secret.
- Required reviewers are configured on the GitHub `production` Environment.
- `concurrency: production` prevents overlapping Production deployments.
- The Git commit SHA identifies the image promoted to both environments.

For extra security, third-party actions can be pinned to full commit SHAs.

---

## Answer 4: GitLab CI/CD

### `.gitlab-ci.yml`

```yaml
stages:
  - test
  - build
  - development
  - production

variables:
  REGISTRY: <acr-name>.azurecr.io
  IMAGE_NAME: orders-api
  IMAGE_TAG: $CI_COMMIT_SHA

test:
  stage: test
  script:
    - mvn -B clean verify
  artifacts:
    when: always
    reports:
      junit:
        - target/surefire-reports/*.xml

build_image:
  stage: build
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  script:
    - az acr login --name <acr-name>
    - docker build -t "$REGISTRY/$IMAGE_NAME:$IMAGE_TAG" .
    - docker push "$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"

deploy_development:
  stage: development
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  environment:
    name: development
  script:
    - >
      az aks get-credentials
      --resource-group <development-resource-group>
      --name <development-aks-name>
      --overwrite-existing
    - >
      helm upgrade --install orders-api ./helm/orders-api
      --namespace development
      --create-namespace
      --set image.repository="$REGISTRY/$IMAGE_NAME"
      --set image.tag="$IMAGE_TAG"
      --wait
    - kubectl rollout status deployment/orders-api --namespace development

deploy_production:
  stage: production
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
      --resource-group <production-resource-group>
      --name <production-aks-name>
      --overwrite-existing
    - >
      helm upgrade --install orders-api ./helm/orders-api
      --namespace production
      --create-namespace
      --set image.repository="$REGISTRY/$IMAGE_NAME"
      --set image.tag="$IMAGE_TAG"
      --wait
    - kubectl rollout status deployment/orders-api --namespace production
```

### Explanation

- `stages` defines the delivery order.
- `rules` limits image publishing and deployment to the default branch.
- Test reports remain available even if tests fail.
- `when: manual` creates the Production approval action.
- A protected Production Environment limits who can approve and deploy.
- `resource_group` prevents two Production deployments from running at the same time.
- The same commit-tagged image goes to Development and Production.

The runner should use a protected short-lived Azure identity. Production variables and runners must not be available to untrusted merge-request code.

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

Suppose commit `a1b2c3` is merged into `main`. The pipeline runs tests, builds `orders-api:a1b2c3`, and pushes it to ACR.

It deploys that image to Development and verifies the rollout. After approval, the same image is deployed to Production.

If verification fails, the pipeline stops and the team can restore the previous Helm revision.

## In short

Jenkins, Azure DevOps, GitHub Actions, and GitLab use different syntax, but my process is the same: test the code, build and scan one versioned image, deploy it to Development, obtain Production approval, promote the same image, and verify the rollout.

Identities and secrets are protected, and the previous Helm revision remains available for rollback.
