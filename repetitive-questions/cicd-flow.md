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

```groovy
pipeline {
  agent any

  stages {
    stage('Build and Test') {
      steps {
        sh 'mvn clean test'
      }
    }

    stage('Build Image') {
      steps {
        sh 'docker build -t $IMAGE_NAME:$BUILD_NUMBER .'
      }
    }

    stage('Push Image') {
      steps {
        sh 'docker push $IMAGE_NAME:$BUILD_NUMBER'
      }
    }

    stage('Deploy') {
      steps {
        sh 'helm upgrade --install orders-api ./helm/orders-api --set image.tag=$BUILD_NUMBER --wait'
      }
    }
  }
}
```

The stages run in order. If testing or image creation fails, deployment does not start. Registry and cluster credentials should come from the Jenkins credential store.

## Azure DevOps example

```yaml
trigger:
  - main

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        steps:
          - script: mvn clean test
            displayName: Test
          - script: docker build -t $(imageName):$(Build.BuildId) .
            displayName: Build image
          - script: docker push $(imageName):$(Build.BuildId)
            displayName: Push image

  - stage: Deploy
    dependsOn: Build
    jobs:
      - deployment: DeployToAKS
        environment: production
        strategy:
          runOnce:
            deploy:
              steps:
                - script: |
                    helm upgrade --install orders-api ./helm/orders-api \
                      --set image.tag=$(Build.BuildId) \
                      --wait
```

The `Build` stage creates the image. The `Deploy` stage runs only after it succeeds. Azure DevOps Environments can hold the Production approval.

## GitHub Actions example

```yaml
name: delivery

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: mvn clean test
      - run: docker build -t $IMAGE_NAME:${{ github.sha }} .
      - run: docker push $IMAGE_NAME:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - run: |
          helm upgrade --install orders-api ./helm/orders-api \
            --set image.tag=${{ github.sha }} \
            --wait
```

The deployment job waits for the build job. A protected GitHub Environment can require approval before the Production job starts.

## GitLab CI/CD example

```yaml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - mvn clean test

build_image:
  stage: build
  script:
    - docker build -t "$IMAGE_NAME:$CI_COMMIT_SHA" .
    - docker push "$IMAGE_NAME:$CI_COMMIT_SHA"

deploy_production:
  stage: deploy
  when: manual
  script:
    - >
      helm upgrade --install orders-api ./helm/orders-api
      --set image.tag="$CI_COMMIT_SHA"
      --wait
```

GitLab runs the stages in order. `when: manual` adds a simple Production approval step.

## Secrets

Passwords and tokens are stored in the CI/CD platform's protected secret store or in Azure Key Vault. They are not written directly in pipeline YAML or printed in logs.

Where possible, I use short-lived identity-based authentication instead of a saved username and password.

## Example

Suppose commit `a1b2c3` is merged into `main`. The pipeline tests it, builds `orders-api:a1b2c3`, scans it, and pushes it to the registry. That same image is deployed to Development and tested. After approval, it is promoted to Production and monitored.

## In short

My CI/CD flow starts with a pull request and automated checks. After merge, the pipeline builds and scans one versioned image, deploys it to a lower environment, and promotes the same image to Production after approval.

I verify the rollout and keep the previous Helm revision available for rollback.
