# Repetitive Interview Questions

## Write a sample end-to-end pipeline through deployment using Jenkins, Azure DevOps, GitHub Actions and GitLab CI, and explain it

### Detailed answer

I have worked with Jenkins, Azure DevOps, GitHub Actions and GitLab CI. I do not say that one application is normally deployed by all four tools at the same time. These are four implementations of the **same delivery design**, and in an interview I present the implementation for the tool being discussed.

The representative project is:

```text
Java 21 Spring Boot service
-> Maven build and tests
-> code/dependency/secret checks
-> multi-stage Docker build
-> container vulnerability scan
-> Azure Container Registry
-> Helm deployment to Azure Kubernetes Service
-> Development verification
-> protected Production approval
-> Production verification and monitoring
```

The samples deliberately follow these principles:

- Pull requests validate code but cannot deploy to Production.
- Only an approved merge to `main` publishes an image.
- The image is tagged with the Git commit and its immutable ACR digest is captured.
- The image is built once; Development and Production receive the same digest.
- Azure access uses managed identity or workload identity federation rather than a stored password.
- Deployment identities have environment-specific, least-privilege RBAC.
- Production approval is protected by the CI/CD platform and organization policy.
- Helm uses `--atomic` and `--wait`, and the pipeline also performs an application smoke test.
- Runtime secrets come from Azure Key Vault through AKS Workload ID; they are not pipeline artifacts.

These are representative templates. Organization names, resource names, environment URLs, tool versions, identity IDs and scan policy must be replaced with reviewed project values.

---

## Common repository structure

All four examples assume this layout:

```text
orders-service/
├── src/
├── pom.xml
├── Dockerfile
├── Jenkinsfile
├── azure-pipelines.yml
├── .gitlab-ci.yml
├── .github/
│   └── workflows/
│       └── delivery.yml
└── helm/
    └── orders-service/
        ├── Chart.yaml
        ├── values.yaml
        ├── values-dev.yaml
        ├── values-prod.yaml
        └── templates/
            ├── deployment.yaml
            └── service.yaml
```

The Helm chart accepts an image repository and digest:

```yaml
# values.yaml
image:
  repository: ""
  digest: ""

replicaCount: 2
```

The Deployment template renders:

```yaml
image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
```

Using the digest is important. A tag such as a Git SHA is readable and traceable, but a registry tag can theoretically be moved. The digest identifies the exact image content that passed the scan and was deployed.

---

# Answer 1: Jenkins Declarative Pipeline

The `Jenkinsfile` is stored in the application repository. A multibranch pipeline automatically discovers pull-request and branch pipelines.

This example assumes:

- The Jenkins agent label `azure-ci-agent` has Java, Maven, Docker, Trivy, Azure CLI, Helm and `kubectl`.
- The agent runs on controlled Azure infrastructure with a managed identity.
- The managed identity can push only to the required ACR repository and deploy only to the required AKS resources.
- A Jenkins folder/role called `release-managers` is allowed to approve Production.
- Branch protection requires a successful Jenkins check before merge.

## Sample `Jenkinsfile`

```groovy
pipeline {
    agent {
        label 'azure-ci-agent'
    }

    options {
        timestamps()
        ansiColor('xterm')
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        skipDefaultCheckout(true)
    }

    environment {
        APP_NAME           = 'orders-service'
        IMAGE_REPOSITORY   = 'orders-service'
        ACR_NAME           = 'contosoacr'
        ACR_LOGIN_SERVER   = 'contosoacr.azurecr.io'

        DEV_RESOURCE_GROUP = 'rg-orders-dev'
        DEV_AKS_CLUSTER    = 'aks-orders-dev'
        DEV_NAMESPACE      = 'orders-dev'
        DEV_URL            = 'https://orders-dev.example.com'

        PROD_RESOURCE_GROUP = 'rg-orders-prod'
        PROD_AKS_CLUSTER    = 'aks-orders-prod'
        PROD_NAMESPACE      = 'orders-prod'
        PROD_URL            = 'https://orders.example.com'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHA = sh(
                        script: 'git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                    env.IMAGE_TAG = env.GIT_SHA
                    currentBuild.displayName = "#${BUILD_NUMBER}-${GIT_SHA}"
                }
            }
        }

        stage('Validate and Test') {
            steps {
                sh '''
                    set -euo pipefail
                    mvn -B clean verify
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true,
                          testResults: 'target/surefire-reports/*.xml'
                    archiveArtifacts allowEmptyArchive: true,
                                     artifacts: 'target/*.jar'
                }
            }
        }

        stage('Security Checks') {
            parallel {
                stage('Repository Scan') {
                    steps {
                        sh '''
                            set -euo pipefail
                            trivy fs \
                              --scanners vuln,secret,misconfig \
                              --severity HIGH,CRITICAL \
                              --exit-code 1 \
                              .
                        '''
                    }
                }

                stage('Quality Gate') {
                    steps {
                        sh '''
                            set -euo pipefail
                            mvn -B sonar:sonar
                        '''
                    }
                }
            }
        }

        stage('Build, Scan and Push Image') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    set -euo pipefail

                    az login --identity --output none
                    az acr login --name "$ACR_NAME"

                    docker build \
                      --pull \
                      --label "org.opencontainers.image.revision=$GIT_SHA" \
                      --tag "$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG" \
                      .

                    trivy image \
                      --severity HIGH,CRITICAL \
                      --exit-code 1 \
                      "$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG"

                    docker push \
                      "$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG"
                '''

                script {
                    env.IMAGE_DIGEST = sh(
                        script: '''
                            az acr repository show \
                              --name "$ACR_NAME" \
                              --image "$IMAGE_REPOSITORY:$IMAGE_TAG" \
                              --query digest \
                              --output tsv
                        ''',
                        returnStdout: true
                    ).trim()

                    if (!env.IMAGE_DIGEST.startsWith('sha256:')) {
                        error('ACR did not return a valid image digest')
                    }
                }

                writeFile file: 'release.env',
                          text: """IMAGE_TAG=${env.IMAGE_TAG}
IMAGE_DIGEST=${env.IMAGE_DIGEST}
GIT_SHA=${env.GIT_SHA}
"""

                archiveArtifacts artifacts: 'release.env',
                                 fingerprint: true
            }
        }

        stage('Deploy Development') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    set -euo pipefail

                    az aks get-credentials \
                      --resource-group "$DEV_RESOURCE_GROUP" \
                      --name "$DEV_AKS_CLUSTER" \
                      --overwrite-existing

                    helm upgrade --install "$APP_NAME" \
                      ./helm/orders-service \
                      --namespace "$DEV_NAMESPACE" \
                      --create-namespace \
                      --values ./helm/orders-service/values-dev.yaml \
                      --set-string image.repository="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY" \
                      --set-string image.digest="$IMAGE_DIGEST" \
                      --atomic \
                      --wait \
                      --timeout 10m

                    kubectl rollout status \
                      "deployment/$APP_NAME" \
                      --namespace "$DEV_NAMESPACE" \
                      --timeout 5m
                '''
            }
        }

        stage('Verify Development') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    set -euo pipefail
                    curl --fail \
                      --silent \
                      --show-error \
                      --retry 5 \
                      --retry-all-errors \
                      "$DEV_URL/actuator/health/readiness"
                '''
            }
        }

        stage('Approve Production') {
            when {
                branch 'main'
            }
            steps {
                script {
                    env.APPROVED_BY = input(
                        message: 'Promote the verified image digest to Production?',
                        ok: 'Deploy',
                        submitter: 'release-managers',
                        submitterParameter: 'APPROVED_BY'
                    )
                }
                echo "Production deployment approved by ${APPROVED_BY}"
            }
        }

        stage('Deploy Production') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    set -euo pipefail

                    az aks get-credentials \
                      --resource-group "$PROD_RESOURCE_GROUP" \
                      --name "$PROD_AKS_CLUSTER" \
                      --overwrite-existing

                    helm upgrade --install "$APP_NAME" \
                      ./helm/orders-service \
                      --namespace "$PROD_NAMESPACE" \
                      --values ./helm/orders-service/values-prod.yaml \
                      --set-string image.repository="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY" \
                      --set-string image.digest="$IMAGE_DIGEST" \
                      --atomic \
                      --wait \
                      --timeout 15m

                    kubectl rollout status \
                      "deployment/$APP_NAME" \
                      --namespace "$PROD_NAMESPACE" \
                      --timeout 10m
                '''
            }
        }

        stage('Verify Production') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    set -euo pipefail
                    curl --fail \
                      --silent \
                      --show-error \
                      --retry 10 \
                      --retry-all-errors \
                      "$PROD_URL/actuator/health/readiness"
                '''
            }
        }
    }

    post {
        success {
            echo "Released ${APP_NAME}@${IMAGE_DIGEST}"
        }
        failure {
            echo 'Pipeline failed. Review tests, scan reports, rollout status and application telemetry.'
        }
        always {
            cleanWs(deleteDirs: true)
        }
    }
}
```

## Jenkins explanation

### `pipeline`, `agent`, `options` and `environment`

- `pipeline {}` is the required top-level Declarative Pipeline block.
- `agent` selects a controlled Jenkins worker. Builds should not execute on the Jenkins controller.
- `options` applies operational controls. `disableConcurrentBuilds()` prevents two releases of this job from changing the same environment simultaneously.
- `timeout` prevents an indefinitely stuck build.
- `buildDiscarder` limits old run retention according to the example policy.
- `environment` contains normal configuration, not passwords.

In a larger implementation, I use different agents and managed identities for build, Development deployment and Production deployment. That creates a stronger separation than one identity with access to all environments. The concise sample uses one agent so the pipeline flow remains readable.

### Checkout and version

`checkout scm` checks out the exact multibranch revision. The short Git SHA becomes the image tag and is also written to the OCI image metadata. This gives traceability from running Pod to ACR image, Jenkins run and source commit.

### Test reports in `post`

The Maven stage uses `post { always { ... } }` so Jenkins attempts to publish JUnit results even if a test fails. Test evidence is therefore visible rather than hidden in raw console output.

### Parallel security checks

Repository scanning and the quality analysis are independent, so Declarative Pipeline runs them in parallel. The example expects Sonar authentication to be configured securely on the agent or through a reviewed Jenkins integration; a token must not be written directly in the Jenkinsfile.

### Branch condition

`when { branch 'main' }` means pull requests and feature branches can compile, test and scan, but only the trusted main branch can publish or deploy.

### Image digest

After the push, the pipeline asks ACR for the digest and rejects an invalid result. It archives `release.env` as release evidence. The digest, not a rebuilt tag, is supplied to Helm.

### Development and Production

Development deployment is automatic. `helm upgrade --install` is idempotent, `--wait` waits for resources and `--atomic` rolls back the Helm release if the operation fails or times out.

The smoke test verifies the application through its reachable endpoint. A successful Helm command alone does not prove that a business API works.

The Production `input` step restricts approval to the configured release group and records the approver. It is placed inside `steps` so the main-branch `when` condition is evaluated before Jenkins requests approval. In a mature Jenkins platform, authorization, change record checks and a separate Production identity are also enforced outside the repository-controlled Jenkinsfile.

### Jenkins `post`

The final `post` block runs after the stages. It produces a release/failure message and cleans the workspace. Real notifications call the approved email, Teams or incident integration through a Shared Library and avoid including secrets.

---

# Answer 2: Azure DevOps multi-stage YAML

The pipeline file is `azure-pipelines.yml`.

This example assumes:

- `azure-wif-build`, `azure-wif-dev` and `azure-wif-prod` are Azure Resource Manager service connections using workload identity federation.
- The identities have separate ACR, Development and Production permissions.
- Azure DevOps Environments `orders-development` and `orders-production` already exist.
- Required Production approvals, branch control and exclusive lock checks are configured on `orders-production` by the environment owner, outside the YAML.
- The private agent image contains Docker, Trivy, Helm, `kubectl`, Azure CLI, Java and Maven.

## Sample `azure-pipelines.yml`

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
  appName: orders-service
  imageRepository: orders-service
  acrName: contosoacr
  acrLoginServer: contosoacr.azurecr.io

  devResourceGroup: rg-orders-dev
  devAksCluster: aks-orders-dev
  devNamespace: orders-dev
  devUrl: https://orders-dev.example.com

  prodResourceGroup: rg-orders-prod
  prodAksCluster: aks-orders-prod
  prodNamespace: orders-prod
  prodUrl: https://orders.example.com

stages:
  - stage: Validate
    displayName: Validate, test and scan
    jobs:
      - job: ApplicationChecks
        displayName: Application checks
        pool:
          name: azure-ci-agents
        steps:
          - checkout: self
            clean: true
            fetchDepth: 1

          - bash: |
              set -euo pipefail
              mvn -B clean verify
            displayName: Maven build and tests

          - task: PublishTestResults@2
            displayName: Publish JUnit results
            condition: always()
            inputs:
              testResultsFormat: JUnit
              testResultsFiles: target/surefire-reports/*.xml
              failTaskOnFailedTests: true

          - bash: |
              set -euo pipefail
              trivy fs \
                --scanners vuln,secret,misconfig \
                --severity HIGH,CRITICAL \
                --exit-code 1 \
                .
            displayName: Repository security scan

  - stage: Publish
    displayName: Build, scan and publish image
    dependsOn: Validate
    condition: |
      and(
        succeeded(),
        eq(variables['Build.SourceBranch'], 'refs/heads/main')
      )
    jobs:
      - job: PublishImage
        displayName: Publish immutable image
        pool:
          name: azure-ci-agents
        steps:
          - checkout: self
            clean: true
            fetchDepth: 1

          - task: AzureCLI@2
            displayName: Build, scan and push to ACR
            inputs:
              azureSubscription: azure-wif-build
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                set -euo pipefail

                imageTag="$(Build.SourceVersion)"
                imageReference="$(acrLoginServer)/$(imageRepository):${imageTag}"

                az acr login --name "$(acrName)"

                docker build \
                  --pull \
                  --label "org.opencontainers.image.revision=$(Build.SourceVersion)" \
                  --tag "${imageReference}" \
                  .

                trivy image \
                  --severity HIGH,CRITICAL \
                  --exit-code 1 \
                  "${imageReference}"

                docker push "${imageReference}"

                digest="$(
                  az acr repository show \
                    --name "$(acrName)" \
                    --image "$(imageRepository):${imageTag}" \
                    --query digest \
                    --output tsv
                )"

                case "${digest}" in
                  sha256:*) ;;
                  *) echo "ACR did not return a valid digest" >&2; exit 1 ;;
                esac

                echo "##vso[task.setvariable variable=ImageDigest;isOutput=true]${digest}"
                echo "##vso[task.setvariable variable=ImageTag;isOutput=true]${imageTag}"
            name: capture

  - stage: DeployDevelopment
    displayName: Deploy and verify Development
    dependsOn: Publish
    variables:
      imageDigest: $[ stageDependencies.Publish.PublishImage.outputs['capture.ImageDigest'] ]
    jobs:
      - deployment: DeployDev
        displayName: Deploy Development
        pool:
          name: azure-ci-agents
        environment: orders-development
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                  clean: true

                - task: AzureCLI@2
                  displayName: Helm deploy to Development AKS
                  inputs:
                    azureSubscription: azure-wif-dev
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      set -euo pipefail

                      az aks get-credentials \
                        --resource-group "$(devResourceGroup)" \
                        --name "$(devAksCluster)" \
                        --overwrite-existing

                      helm upgrade --install "$(appName)" \
                        ./helm/orders-service \
                        --namespace "$(devNamespace)" \
                        --create-namespace \
                        --values ./helm/orders-service/values-dev.yaml \
                        --set-string image.repository="$(acrLoginServer)/$(imageRepository)" \
                        --set-string image.digest="$(imageDigest)" \
                        --atomic \
                        --wait \
                        --timeout 10m

                      kubectl rollout status \
                        "deployment/$(appName)" \
                        --namespace "$(devNamespace)" \
                        --timeout 5m

                      curl --fail \
                        --silent \
                        --show-error \
                        --retry 5 \
                        --retry-all-errors \
                        "$(devUrl)/actuator/health/readiness"

  - stage: DeployProduction
    displayName: Deploy and verify Production
    dependsOn:
      - Publish
      - DeployDevelopment
    condition: succeeded()
    variables:
      imageDigest: $[ stageDependencies.Publish.PublishImage.outputs['capture.ImageDigest'] ]
    jobs:
      - deployment: DeployProd
        displayName: Deploy Production
        pool:
          name: azure-ci-agents
        environment: orders-production
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                  clean: true

                - task: AzureCLI@2
                  displayName: Helm deploy to Production AKS
                  inputs:
                    azureSubscription: azure-wif-prod
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      set -euo pipefail

                      az aks get-credentials \
                        --resource-group "$(prodResourceGroup)" \
                        --name "$(prodAksCluster)" \
                        --overwrite-existing

                      helm upgrade --install "$(appName)" \
                        ./helm/orders-service \
                        --namespace "$(prodNamespace)" \
                        --values ./helm/orders-service/values-prod.yaml \
                        --set-string image.repository="$(acrLoginServer)/$(imageRepository)" \
                        --set-string image.digest="$(imageDigest)" \
                        --atomic \
                        --wait \
                        --timeout 15m

                      kubectl rollout status \
                        "deployment/$(appName)" \
                        --namespace "$(prodNamespace)" \
                        --timeout 10m

                      curl --fail \
                        --silent \
                        --show-error \
                        --retry 10 \
                        --retry-all-errors \
                        "$(prodUrl)/actuator/health/readiness"
```

## Azure DevOps explanation

### `trigger` and `pr`

- `trigger` starts CI when code is pushed or merged to `main`.
- `pr` runs validation for a pull request targeting `main` when the repository provider supports YAML PR triggers.
- The Publish stage has an additional main-branch condition, so a pull-request pipeline cannot publish or deploy.

For Azure Repos Git, I configure the YAML pipeline as a required build-validation branch policy because Azure Repos PR validation is controlled by branch policy rather than the YAML `pr` trigger. Branch policies must also require reviewers. YAML conditions complement repository protection; they do not replace it.

### Variables

The top-level variables contain ordinary resource names and URLs. Sensitive values must not be committed here. Workload identity-federated service connections avoid a stored client secret.

### Stages, jobs, tasks and steps

Azure DevOps hierarchy is:

```text
pipeline
-> stage
-> job or deployment job
-> task/script step
```

Stages establish major boundaries. Jobs can run on different agents. Tasks such as `AzureCLI@2` are versioned Azure DevOps task integrations, while `bash` runs a shell script.

### Output variable

The named `capture` step marks `ImageDigest` as `isOutput=true`. Later stages read it through `stageDependencies`. This is how the exact ACR digest moves forward without rebuilding the image.

The digest is release metadata, not a secret.

### Deployment jobs and Environments

A `deployment` job records deployment history against an Azure DevOps Environment. The environment owner configures Production approvals and checks outside YAML, which prevents an application-repository change from simply deleting its own approval requirement.

I configure:

- Required Production approvers.
- Branch control.
- Exclusive lock to serialize deployment.
- Change-window or business-hours checks where required.
- Optional monitoring/query gates according to organizational policy.

The Development and Production jobs use different workload identity-federated service connections and therefore different Azure permissions.

### Why no manual approval task inside YAML?

Production approval is configured on the protected `orders-production` Environment. This is stronger governance because the control belongs to the environment owner rather than only to the application repository.

---

# Answer 3: GitHub Actions YAML

The workflow is stored in `.github/workflows/delivery.yml`.

This example assumes:

- GitHub Environments `development` and `production` exist.
- Each Environment contains non-secret Azure identity variables appropriate to that environment.
- The Production Environment requires authorized reviewers and restricts deployment branches.
- Microsoft Entra federated credentials trust the exact repository and Environment claims.
- The self-hosted runner labels identify controlled, ephemeral Azure runners with Java, Maven, Docker, Trivy, Azure CLI, Helm and `kubectl`.
- Third-party actions are pinned to reviewed commit SHAs in the real workflow.

## Sample `.github/workflows/delivery.yml`

```yaml
name: Orders service delivery

on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

env:
  APP_NAME: orders-service
  IMAGE_REPOSITORY: orders-service
  ACR_NAME: contosoacr
  ACR_LOGIN_SERVER: contosoacr.azurecr.io

jobs:
  validate:
    name: Validate, test and scan
    runs-on:
      - self-hosted
      - linux
      - azure-ci
    timeout-minutes: 20
    steps:
      - name: Checkout exact revision
        uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
          cache: maven

      - name: Maven build and tests
        run: |
          set -euo pipefail
          mvn -B clean verify

      - name: Repository security scan
        run: |
          set -euo pipefail
          trivy fs \
            --scanners vuln,secret,misconfig \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            .

      - name: Upload test evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: junit-${{ github.sha }}
          path: target/surefire-reports/
          if-no-files-found: warn
          retention-days: 14

  publish:
    name: Build, scan and publish image
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    needs:
      - validate
    runs-on:
      - self-hosted
      - linux
      - azure-ci
    timeout-minutes: 25
    permissions:
      contents: read
      id-token: write
    outputs:
      image-digest: ${{ steps.capture.outputs.digest }}
      image-tag: ${{ steps.capture.outputs.tag }}
    steps:
      - name: Checkout exact revision
        uses: actions/checkout@v4

      - name: Sign in to Azure using OIDC
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_BUILD_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Build and scan image
        env:
          IMAGE_TAG: ${{ github.sha }}
        run: |
          set -euo pipefail

          az acr login --name "$ACR_NAME"

          docker build \
            --pull \
            --label "org.opencontainers.image.revision=$GITHUB_SHA" \
            --tag "$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG" \
            .

          trivy image \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            "$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG"

      - name: Push image and capture digest
        id: capture
        env:
          IMAGE_TAG: ${{ github.sha }}
        run: |
          set -euo pipefail

          docker push \
            "$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG"

          digest="$(
            az acr repository show \
              --name "$ACR_NAME" \
              --image "$IMAGE_REPOSITORY:$IMAGE_TAG" \
              --query digest \
              --output tsv
          )"

          case "$digest" in
            sha256:*) ;;
            *) echo "ACR did not return a valid digest" >&2; exit 1 ;;
          esac

          echo "digest=$digest" >> "$GITHUB_OUTPUT"
          echo "tag=$IMAGE_TAG" >> "$GITHUB_OUTPUT"

      - name: Write release summary
        run: |
          {
            echo "### Published image"
            echo
            echo "\`$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY@${{ steps.capture.outputs.digest }}\`"
          } >> "$GITHUB_STEP_SUMMARY"

  deploy-development:
    name: Deploy Development
    needs:
      - publish
    runs-on:
      - self-hosted
      - linux
      - azure-deploy
    timeout-minutes: 20
    environment:
      name: development
      url: https://orders-dev.example.com
    concurrency:
      group: orders-development
      cancel-in-progress: false
    permissions:
      contents: read
      id-token: write
    steps:
      - name: Checkout Helm chart
        uses: actions/checkout@v4

      - name: Sign in to Azure using Development identity
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy and verify Development
        env:
          IMAGE_DIGEST: ${{ needs.publish.outputs.image-digest }}
          RESOURCE_GROUP: rg-orders-dev
          AKS_CLUSTER: aks-orders-dev
          NAMESPACE: orders-dev
          ENVIRONMENT_URL: https://orders-dev.example.com
        run: |
          set -euo pipefail

          az aks get-credentials \
            --resource-group "$RESOURCE_GROUP" \
            --name "$AKS_CLUSTER" \
            --overwrite-existing

          helm upgrade --install "$APP_NAME" \
            ./helm/orders-service \
            --namespace "$NAMESPACE" \
            --create-namespace \
            --values ./helm/orders-service/values-dev.yaml \
            --set-string image.repository="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY" \
            --set-string image.digest="$IMAGE_DIGEST" \
            --atomic \
            --wait \
            --timeout 10m

          kubectl rollout status \
            "deployment/$APP_NAME" \
            --namespace "$NAMESPACE" \
            --timeout 5m

          curl --fail \
            --silent \
            --show-error \
            --retry 5 \
            --retry-all-errors \
            "$ENVIRONMENT_URL/actuator/health/readiness"

  deploy-production:
    name: Deploy Production
    needs:
      - publish
      - deploy-development
    runs-on:
      - self-hosted
      - linux
      - azure-deploy
    timeout-minutes: 25
    environment:
      name: production
      url: https://orders.example.com
    concurrency:
      group: orders-production
      cancel-in-progress: false
    permissions:
      contents: read
      id-token: write
    steps:
      - name: Checkout Helm chart
        uses: actions/checkout@v4

      - name: Sign in to Azure using Production identity
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy and verify Production
        env:
          IMAGE_DIGEST: ${{ needs.publish.outputs.image-digest }}
          RESOURCE_GROUP: rg-orders-prod
          AKS_CLUSTER: aks-orders-prod
          NAMESPACE: orders-prod
          ENVIRONMENT_URL: https://orders.example.com
        run: |
          set -euo pipefail

          az aks get-credentials \
            --resource-group "$RESOURCE_GROUP" \
            --name "$AKS_CLUSTER" \
            --overwrite-existing

          helm upgrade --install "$APP_NAME" \
            ./helm/orders-service \
            --namespace "$NAMESPACE" \
            --values ./helm/orders-service/values-prod.yaml \
            --set-string image.repository="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY" \
            --set-string image.digest="$IMAGE_DIGEST" \
            --atomic \
            --wait \
            --timeout 15m

          kubectl rollout status \
            "deployment/$APP_NAME" \
            --namespace "$NAMESPACE" \
            --timeout 10m

          curl --fail \
            --silent \
            --show-error \
            --retry 10 \
            --retry-all-errors \
            "$ENVIRONMENT_URL/actuator/health/readiness"
```

## GitHub Actions explanation

### Events

- `pull_request` validates proposed changes.
- `push` to `main` validates, publishes and deploys.
- `workflow_dispatch` allows an authorized manual run, but branch and Environment rules still apply.

### Default and job-level permissions

The workflow defaults to `contents: read`. Only jobs that authenticate to Azure receive `id-token: write`. This permission lets the job request an OIDC token; it does not itself grant Azure access. Microsoft Entra ID validates the federated subject and grants the configured identity's Azure RBAC permissions.

### `needs` and outputs

`needs` creates the dependency graph:

```text
validate
-> publish
-> deploy-development
-> deploy-production
```

The `capture` step writes the digest to `$GITHUB_OUTPUT`. The publish job exposes it as a job output, and both deployment jobs consume it. No environment rebuilds the image.

### GitHub Environments

The `environment` field records deployment history and activates environment-specific variables/protection rules. The `production` Environment requires reviewers and restricts allowed branches. The federated Azure credential also trusts the Production Environment subject, adding an identity boundary.

### Concurrency

The `concurrency` group ensures only one deployment for that application/environment executes at a time. `cancel-in-progress: false` avoids abruptly terminating an active deployment when a newer commit arrives.

### Actions pinning

Readable major tags are shown for interview clarity. In a controlled Production repository, I pin third-party actions to reviewed full commit SHAs and use dependency automation to propose updates. This reduces the risk of a mutable upstream tag changing unexpectedly.

### Pull-request security

The publish job explicitly excludes pull-request events. Production identity permissions are available only in the protected Production job. I do not use a pattern that runs untrusted pull-request code with write credentials.

---

# Answer 4: GitLab CI YAML

The pipeline is stored in `.gitlab-ci.yml`.

This example assumes:

- `azure-ci` and `azure-deploy` are protected, controlled runner tags.
- Required tools are installed on the corresponding shell runners.
- GitLab environment-scoped variables provide `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID`.
- Microsoft Entra federated credentials trust the exact GitLab project, protected ref and environment claims.
- `production` is a protected GitLab Environment with authorized deployers.
- Main-branch merges require merge-request approval and successful pipeline checks.

## Sample `.gitlab-ci.yml`

```yaml
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - when: never

stages:
  - validate
  - publish
  - deploy-development
  - deploy-production

variables:
  APP_NAME: orders-service
  IMAGE_REPOSITORY: orders-service
  ACR_NAME: contosoacr
  ACR_LOGIN_SERVER: contosoacr.azurecr.io
  MAVEN_OPTS: "-Dmaven.repo.local=.m2/repository"

default:
  interruptible: true
  retry:
    max: 1
    when:
      - runner_system_failure
      - stuck_or_timeout_failure

validate:
  stage: validate
  image: maven:3.9.9-eclipse-temurin-21
  tags:
    - container-runner
  cache:
    key:
      files:
        - pom.xml
    paths:
      - .m2/repository/
  script:
    - set -euo pipefail
    - mvn -B clean verify
  artifacts:
    when: always
    expire_in: 14 days
    reports:
      junit:
        - target/surefire-reports/*.xml
    paths:
      - target/surefire-reports/

repository-scan:
  stage: validate
  image:
    name: aquasec/trivy:0.65.0
    entrypoint:
      - ""
  tags:
    - container-runner
  script:
    - >
      trivy fs
      --scanners vuln,secret,misconfig
      --severity HIGH,CRITICAL
      --exit-code 1
      .

publish-image:
  stage: publish
  tags:
    - azure-ci
  needs:
    - job: validate
      artifacts: false
    - job: repository-scan
      artifacts: false
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
  id_tokens:
    AZURE_OIDC_TOKEN:
      aud: api://AzureADTokenExchange
  script:
    - set -euo pipefail
    - >
      az login
      --service-principal
      --username "$AZURE_CLIENT_ID"
      --tenant "$AZURE_TENANT_ID"
      --federated-token "$AZURE_OIDC_TOKEN"
      --output none
    - az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    - az acr login --name "$ACR_NAME"
    - export IMAGE_TAG="$CI_COMMIT_SHA"
    - export IMAGE_REFERENCE="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY:$IMAGE_TAG"
    - >
      docker build
      --pull
      --label "org.opencontainers.image.revision=$CI_COMMIT_SHA"
      --tag "$IMAGE_REFERENCE"
      .
    - >
      trivy image
      --severity HIGH,CRITICAL
      --exit-code 1
      "$IMAGE_REFERENCE"
    - docker push "$IMAGE_REFERENCE"
    - >
      export IMAGE_DIGEST="$(
        az acr repository show
        --name "$ACR_NAME"
        --image "$IMAGE_REPOSITORY:$IMAGE_TAG"
        --query digest
        --output tsv
      )"
    - >
      case "$IMAGE_DIGEST" in
        sha256:*) ;;
        *) echo "ACR did not return a valid digest" >&2; exit 1 ;;
      esac
    - printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG" > release.env
    - printf 'IMAGE_DIGEST=%s\n' "$IMAGE_DIGEST" >> release.env
  artifacts:
    expire_in: 7 days
    reports:
      dotenv: release.env
    paths:
      - release.env

deploy-development:
  stage: deploy-development
  tags:
    - azure-deploy
  needs:
    - job: publish-image
      artifacts: true
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
  environment:
    name: development
    url: https://orders-dev.example.com
  resource_group: orders-development
  interruptible: false
  id_tokens:
    AZURE_OIDC_TOKEN:
      aud: api://AzureADTokenExchange
  variables:
    RESOURCE_GROUP: rg-orders-dev
    AKS_CLUSTER: aks-orders-dev
    NAMESPACE: orders-dev
    ENVIRONMENT_URL: https://orders-dev.example.com
  script:
    - set -euo pipefail
    - >
      az login
      --service-principal
      --username "$AZURE_CLIENT_ID"
      --tenant "$AZURE_TENANT_ID"
      --federated-token "$AZURE_OIDC_TOKEN"
      --output none
    - az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    - >
      az aks get-credentials
      --resource-group "$RESOURCE_GROUP"
      --name "$AKS_CLUSTER"
      --overwrite-existing
    - >
      helm upgrade --install "$APP_NAME"
      ./helm/orders-service
      --namespace "$NAMESPACE"
      --create-namespace
      --values ./helm/orders-service/values-dev.yaml
      --set-string image.repository="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY"
      --set-string image.digest="$IMAGE_DIGEST"
      --atomic
      --wait
      --timeout 10m
    - >
      kubectl rollout status
      "deployment/$APP_NAME"
      --namespace "$NAMESPACE"
      --timeout 5m
    - >
      curl --fail
      --silent
      --show-error
      --retry 5
      --retry-all-errors
      "$ENVIRONMENT_URL/actuator/health/readiness"

deploy-production:
  stage: deploy-production
  tags:
    - azure-deploy
  needs:
    - job: publish-image
      artifacts: true
    - job: deploy-development
      artifacts: false
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: manual
      allow_failure: false
  manual_confirmation: Promote the verified image digest to Production?
  environment:
    name: production
    url: https://orders.example.com
  resource_group: orders-production
  interruptible: false
  id_tokens:
    AZURE_OIDC_TOKEN:
      aud: api://AzureADTokenExchange
  variables:
    RESOURCE_GROUP: rg-orders-prod
    AKS_CLUSTER: aks-orders-prod
    NAMESPACE: orders-prod
    ENVIRONMENT_URL: https://orders.example.com
  script:
    - set -euo pipefail
    - >
      az login
      --service-principal
      --username "$AZURE_CLIENT_ID"
      --tenant "$AZURE_TENANT_ID"
      --federated-token "$AZURE_OIDC_TOKEN"
      --output none
    - az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    - >
      az aks get-credentials
      --resource-group "$RESOURCE_GROUP"
      --name "$AKS_CLUSTER"
      --overwrite-existing
    - >
      helm upgrade --install "$APP_NAME"
      ./helm/orders-service
      --namespace "$NAMESPACE"
      --values ./helm/orders-service/values-prod.yaml
      --set-string image.repository="$ACR_LOGIN_SERVER/$IMAGE_REPOSITORY"
      --set-string image.digest="$IMAGE_DIGEST"
      --atomic
      --wait
      --timeout 15m
    - >
      kubectl rollout status
      "deployment/$APP_NAME"
      --namespace "$NAMESPACE"
      --timeout 10m
    - >
      curl --fail
      --silent
      --show-error
      --retry 10
      --retry-all-errors
      "$ENVIRONMENT_URL/actuator/health/readiness"
```

## GitLab CI explanation

### `workflow: rules`

Workflow rules create pipelines only for merge requests and the default branch. This avoids unnecessary or duplicate pipeline types.

Job-level rules further restrict publish and deployment jobs to the default branch. Merge requests can validate but cannot publish or deploy.

### Stages and `needs`

Stages show the high-level order, while `needs` defines exact job dependencies and allows a directed acyclic graph. The publish job waits for both validation jobs, and Production waits for the image plus successful Development deployment.

### Cache versus artifacts

- The Maven cache is a disposable performance optimization.
- JUnit results are report artifacts and test evidence.
- `release.env` is a dotenv artifact containing the immutable image tag/digest passed to deployment jobs.
- The release artifact must not be replaced with an unverified cache.

### OIDC `id_tokens`

GitLab creates `AZURE_OIDC_TOKEN` for only the jobs that request it. Azure CLI exchanges it for temporary access through a Microsoft Entra federated credential. There is no stored Azure client secret.

The identity variables are environment-scoped, so Development and Production can use different client IDs, subscriptions and RBAC. The federated credential must narrowly trust the expected project, protected branch and environment claims.

### Environment and manual deployment

`environment` records deployment history. `production` is additionally protected in GitLab settings. `when: manual` creates the approval action, `allow_failure: false` makes it blocking, and `manual_confirmation` clearly states what the approver is authorizing.

### `resource_group`

`resource_group` serializes deployments for an application/environment. `interruptible: false` prevents GitLab from canceling a deployment job halfway through simply because a newer pipeline starts.

The default validation jobs remain interruptible, so superseded validation work can be canceled safely.

---

# Explanation of the common end-to-end flow

## 1. Trigger and checkout

A pull request triggers validation. Branch protection requires:

- Required reviewers.
- Resolved review comments.
- Successful build, tests and security checks.
- Additional ownership review for Dockerfile, Helm and pipeline changes.

After merge, the main-branch pipeline checks out the exact merge commit. The full commit SHA is used as the image tag and OCI revision label.

## 2. Compile, unit tests and package

Maven `clean verify`:

- Removes the previous build output.
- Resolves declared dependencies.
- Compiles the Java source.
- Runs unit tests and configured verification plugins.
- Produces the JAR.

The CI/CD system publishes JUnit results even if a test fails. A red test stops the pipeline.

For a large project, I run independent unit, integration, quality and security jobs in parallel where safe, while keeping the dependency graph explicit.

## 3. Security and quality gates

The templates show Trivy as a compact example for vulnerability, secret, misconfiguration and image scanning. A full project can also include:

- SonarQube or the approved SAST/quality platform.
- Software-composition analysis.
- Dedicated secret scanning.
- Checkov or an approved IaC/Kubernetes scanner.
- SBOM generation.
- Image signing and admission verification.
- Authorized DAST in a deployed non-production environment.

Critical policy failures stop publication. An exception requires a risk owner, justification, compensating control and expiry; it is not implemented by changing `exit-code 1` to a warning without approval.

## 4. Build the container image

The Dockerfile uses a multi-stage build:

```text
Maven/JDK build stage
-> compile and test
-> copy only the JAR
-> JRE runtime stage
-> non-root application process
```

`docker build --pull` checks for an updated base associated with the pinned tag. For exact reproducibility and controlled updates, the organization can pin the base digest and use dependency automation to submit reviewed digest changes.

## 5. Scan before push

The locally built image is scanned before publication. High/Critical policy findings fail the pipeline.

Registry/runtime scanning remains necessary because a vulnerability can be disclosed after the original build. If an active image becomes vulnerable, I rebuild from the patched base/dependencies, retest and redeploy rather than modifying the running container.

## 6. Authenticate and push to ACR

The tools use:

- Jenkins managed identity on an Azure-hosted agent.
- Azure DevOps workload identity-federated service connections.
- GitHub Actions OIDC federation with Microsoft Entra ID.
- GitLab OIDC ID tokens federated with Microsoft Entra ID.

These methods provide short-lived access. Build identities can push to the required ACR repository but do not receive unrestricted Production administration.

After pushing, the pipeline queries ACR and stores:

```text
repository = contosoacr.azurecr.io/orders-service
tag        = exact Git commit
digest     = sha256:<immutable-content-digest>
```

## 7. Deploy automatically to Development

The deployment identity obtains user credentials for the target AKS cluster through Azure authentication. It does not use `--admin`.

Helm supplies:

- A version-controlled chart.
- Environment-specific non-secret values.
- The image repository.
- The approved image digest.

The application uses AKS Workload ID to retrieve runtime secrets from Azure Key Vault. The pipeline does not render clear-text secrets into Helm command output.

## 8. Verify Development

I verify several levels:

1. Helm operation completed.
2. Kubernetes Deployment rollout completed.
3. Pods became Ready.
4. The externally reachable readiness or smoke endpoint succeeded.
5. Important API/business smoke tests succeeded.
6. Error rate, latency and saturation remained acceptable.

A green deployment command without application verification is not sufficient.

## 9. Approve Production

Production uses a platform protection mechanism:

| Platform | Production control |
| --- | --- |
| Jenkins | Restricted `input` plus Jenkins RBAC and preferably a separate Production identity |
| Azure DevOps | Approvals/checks on the protected Environment |
| GitHub Actions | Required reviewers and deployment-branch rules on the GitHub Environment |
| GitLab CI | Blocking manual job plus protected Environment and protected runners |

Approval must show the release identity, test/scan evidence, change record, target environment and rollback plan. The requester should not casually self-approve where separation of duties is required.

## 10. Deploy the same digest to Production

Production consumes the same ACR digest tested in Development. The pipeline does not rerun `docker build`.

The Kubernetes strategy normally includes:

- Multiple replicas.
- Rolling update with appropriate `maxUnavailable` and `maxSurge`.
- Startup and readiness probes.
- Graceful `SIGTERM` handling and termination grace period.
- PodDisruptionBudget.
- Adequate cluster capacity.
- Backward-compatible database change sequencing.

`helm --atomic` protects against Helm operation/rollout failure, but external smoke or business-metric failures may require an explicit rollback:

```bash
helm history orders-service --namespace orders-prod

helm rollback orders-service <known-good-revision> \
  --namespace orders-prod \
  --wait \
  --timeout 15m
```

The operator selects a verified known-good revision. A destructive database migration requires a separate tested recovery or roll-forward plan; application rollback alone may be unsafe.

## 11. Observe and close

After Production deployment, I observe:

- HTTP success/error rate.
- Latency percentiles.
- Pod restarts and readiness.
- CPU, memory and JVM behavior.
- Dependency/database health.
- Application Insights traces and exceptions.
- A real business transaction.

Azure Monitor, Log Analytics, Application Insights, Prometheus and Grafana provide the relevant signals. The pipeline or release record retains the commit, tests, scan results, image digest, environment, approver, Helm revision and verification result.

---

# Key syntax comparison

| Concept | Jenkins | Azure DevOps | GitHub Actions | GitLab CI |
| --- | --- | --- | --- | --- |
| Pipeline file | `Jenkinsfile` | `azure-pipelines.yml` | `.github/workflows/*.yml` | `.gitlab-ci.yml` |
| Main grouping | `stage` | `stage` | `job` | `stage` and job |
| Execution unit | `steps` on an agent | job/task/step on an agent | steps on a runner | script in a runner job |
| Dependency | Stage order/`parallel` | `dependsOn` | `needs` | `needs` |
| Condition | `when` | `condition` | `if` | `rules` |
| Output passing | environment/file/stash/artifact | output variable/artifact | step/job output/artifact | dotenv/report artifact |
| Cloud identity | Managed identity/credential integration | Federated service connection | OIDC with `id-token: write` | OIDC through `id_tokens` |
| Deployment record | Pipeline/build metadata | Environment deployment job | GitHub Environment | GitLab Environment |
| Production approval | Restricted `input` | Environment approval/check | Environment required reviewer | Protected Environment/manual job |
| Concurrency | `disableConcurrentBuilds` or lock | Exclusive lock check | `concurrency` | `resource_group` |
| Always-run cleanup | `post { always }` | `condition: always()` | `if: always()` | `after_script`/artifact policy |

---

# Common interviewer follow-up questions

## Why use pipeline as code?

Pipeline code is versioned, peer-reviewed, traceable and reproducible. A change to build or deployment behavior follows the same pull-request controls as application code. Sensitive environment protections still remain outside repository control.

## Why build only once?

Rebuilding for each environment can produce different dependencies or base layers. By building, testing and scanning once, then promoting the same digest, I know Production receives the artifact that passed earlier gates.

## Why do you use both a tag and digest?

The Git SHA tag is human-readable and traceable. The digest is immutable content identity. Helm deploys the digest, while logs and ACR records retain the readable tag.

## How are credentials managed?

I prefer short-lived identity:

- Managed identity for Azure-hosted Jenkins agents.
- Workload identity federation for Azure DevOps service connections.
- OIDC federation for GitHub Actions and GitLab.
- AKS Workload ID for the running application.

Azure Key Vault holds application secrets. Secrets are not committed to YAML/Groovy, printed in logs or stored in the container image.

## How does the pipeline behave for a pull request?

It checks out the proposed revision, builds, tests and scans. It has read-only/minimal permissions and cannot publish an image or deploy. Repository branch protection prevents merge until required checks and reviews pass.

## How do you prevent concurrent Production deployments?

- Jenkins disables concurrent runs or uses a lockable environment resource.
- Azure DevOps uses an exclusive lock Environment check.
- GitHub Actions uses a Production concurrency group.
- GitLab uses a Production `resource_group`.

I do not automatically cancel an already running Production deployment because interruption can leave a release in an unclear state.

## How do you roll back?

Helm `--atomic` rolls back a failed Helm operation. If post-deployment health degrades, I stop promotion, inspect the release and restore the verified previous Helm revision/image digest. Database changes are backward-compatible and have their own roll-forward/recovery plan.

## Why use `set -euo pipefail`?

- `-e` stops on a failed command.
- `-u` treats an unset variable as an error.
- `pipefail` makes a pipeline fail if an earlier piped command fails.

It reduces silent shell failures but does not replace explicit validation, retries for transient operations and clear error handling.

## Why use private/self-hosted agents?

They can provide controlled network access to private AKS/ACR endpoints and a standardized, scanned toolchain. They must be patched, isolated and preferably ephemeral. Untrusted pull-request jobs are separated from privileged deployment agents.

## Why not run Terraform in every application pipeline?

Infrastructure has a different blast radius, ownership and approval path. I use a separate Terraform/Bicep pipeline for networks, AKS, ACR, Key Vault and shared services. The application pipeline deploys into the approved platform.

## What happens if the smoke test fails after Helm succeeds?

The pipeline marks the release failed, stops further promotion and collects application/Kubernetes evidence. For Production, the runbook determines whether to roll back the Helm revision, disable new traffic or roll forward. The pipeline then verifies the restored business health.

## How do you make the pipeline reusable?

- Jenkins uses reviewed Shared Libraries.
- Azure DevOps uses YAML templates.
- GitHub Actions uses reusable workflows and composite actions.
- GitLab uses `include`, `extends` and centrally reviewed CI components/templates.

Reusable logic is versioned and pinned. Application repositories provide only approved parameters rather than unrestricted commands.

---

# Common mistakes I avoid

- Putting Azure client secrets directly in pipeline files.
- Allowing pull-request pipelines to use Production identities.
- Rebuilding a different image for every environment.
- Deploying `latest` instead of an approved digest.
- Giving one pipeline identity unrestricted access to every subscription.
- Treating a successful `kubectl` or Helm command as complete application verification.
- Keeping Production approval only in editable repository YAML when the platform supports protected Environments.
- Running builds on the Jenkins controller.
- Running privileged, long-lived runners for untrusted code.
- Printing tokens or rendered secret values in debug logs.
- Ignoring test/security reports while allowing the pipeline to continue.
- Canceling an active Production deployment without checking release state.
- Automatically retrying deterministic test failures.
- Rolling back application code without evaluating database compatibility.
- Running unrestricted infrastructure changes inside every application release.

---

# Concise interview answer

My end-to-end flow is the same across Jenkins, Azure DevOps, GitHub Actions and GitLab CI; only the pipeline syntax and platform controls change.

A pull request triggers checkout, Maven build, unit tests, code-quality and security scans. It cannot publish or deploy. After an approved merge to `main`, the pipeline builds a multi-stage non-root Docker image, scans it, tags it with the Git commit and pushes it to Azure Container Registry using managed identity or workload identity federation. It then captures the immutable ACR digest.

The pipeline deploys that digest automatically to the Development AKS cluster using Helm, waits for the rollout and runs readiness and API smoke tests. After the required Production approval, it promotes the **same digest** to Production using a separate least-privilege identity. Helm uses `--atomic` and `--wait`, and the deployment uses multiple replicas, readiness probes and graceful shutdown for safe rollout.

Finally, I verify application health through Azure Monitor, Log Analytics, Application Insights, Prometheus and Grafana. The release record contains the commit, tests, scan results, image digest, approver, Helm revision and verification result. If a gate fails, promotion stops and I restore the known-good Helm revision when rollback is safe.

In Jenkins this is implemented with a Declarative `Jenkinsfile`, stages, `when`, `parallel`, `input` and `post`. Azure DevOps uses stages, deployment jobs, federated service connections and Environment approvals. GitHub Actions uses jobs, `needs`, OIDC, protected Environments and concurrency. GitLab CI uses stages, `needs`, OIDC `id_tokens`, protected Environments, a blocking manual job and `resource_group`.
