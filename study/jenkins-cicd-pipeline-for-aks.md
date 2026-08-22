# Jenkins CI/CD Pipeline for AKS

This pipeline tests a Java application, checks code quality and security, builds one Docker image, deploys it to development, and then promotes the same image to production after approval.

## End-to-End Flow

```text
Git checkout
    ↓
Compile and unit test
    ↓
SonarQube analysis and quality gate
    ↓
Dependency vulnerability scan
    ↓
Build and scan Docker image
    ↓
Push image to Azure Container Registry
    ↓
Deploy to development AKS with Helm
    ↓
Verify rollout and run smoke test
    ↓
Manual production approval
    ↓
Deploy the same image to production
    ↓
Verify rollout and run smoke test
```

## Example Declarative Pipeline

```groovy
pipeline {
    agent { label 'docker-azure' }

    options {
        disableConcurrentBuilds()
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

        stage('Dependency Scan') {
            steps {
                sh 'mvn -B org.owasp:dependency-check-maven:check'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG .'
            }
        }

        stage('Scan Docker Image') {
            steps {
                sh '''
                    trivy image --exit-code 1 \
                      --severity HIGH,CRITICAL \
                      $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
        }

        stage('Push Image to ACR') {
            steps {
                sh '''
                    az acr login --name $ACR_NAME
                    docker push $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                '''
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
                      --wait \
                      --timeout 10m

                    kubectl rollout status deployment/orders-api \
                      --namespace development \
                      --timeout=10m
                '''
            }
        }

        stage('Development Smoke Test') {
            steps {
                sh 'curl --fail --retry 5 http://orders-api-dev/actuator/health'
            }
        }

        stage('Approve Production') {
            input {
                message 'Deploy this tested image to production?'
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
                      --wait \
                      --timeout 10m

                    kubectl rollout status deployment/orders-api \
                      --namespace production \
                      --timeout=10m
                '''
            }
        }

        stage('Production Smoke Test') {
            steps {
                sh 'curl --fail --retry 5 https://orders.company.com/actuator/health'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true,
                  testResults: 'target/surefire-reports/*.xml'
        }
        success {
            echo 'Build and deployment succeeded'
        }
        failure {
            echo 'Build or deployment failed'
        }
    }
}
```

## What Each Part Does

### Agent and tools

The `docker-azure` Jenkins agent must have Java, Maven, Docker, Azure CLI, Helm, kubectl, and Trivy available. The configured SonarQube Jenkins plugin supplies the scanner environment.

### Pipeline options

- `disableConcurrentBuilds()` stops two runs of this job from deploying at the same time.
- `timestamps()` makes troubleshooting easier by adding times to log lines.
- The pipeline timeout prevents a stuck deployment from running forever.

### Build, test, and quality checks

`mvn clean verify` compiles the code, runs tests, and creates the application package. SonarQube then checks code quality, bugs, duplication, and security issues. `waitForQualityGate` stops the pipeline if the project does not meet the configured quality rules. It requires the SonarQube webhook to be configured for Jenkins.

### Security checks

OWASP Dependency-Check looks for known vulnerabilities in application dependencies. Trivy scans the final container image. A serious finding causes the pipeline to stop before the image is pushed or deployed.

### Image promotion

The image is tagged with the Jenkins build number and pushed to ACR. Development and production use the exact same image tag. Production is not rebuilt, so the tested artifact is the artifact that is promoted.

### Deployment and verification

Helm installs the application if it is new or upgrades it if it already exists. `--wait` and `kubectl rollout status` confirm that Kubernetes completed the rollout. Smoke tests check that the running application responds successfully.

## Production Improvements

- Use a Jenkins credential, workload identity, or managed identity instead of storing Azure credentials in the Jenkinsfile.
- Allow production deployment only from an approved branch or release tag.
- Add the Git commit SHA to the image tag or labels for traceability.
- Add secret scanning and Infrastructure-as-Code scanning when those files are present.
- Send success and failure notifications to Teams, Slack, or email.
- Store scan reports as Jenkins artifacts for auditing.
- Use canary or blue-green deployment when a normal rolling update is too risky.
- Consider GitOps: Jenkins updates the image tag in a deployment repository, and Argo CD deploys it instead of Jenkins running Helm directly.

## Short Interview Answer

This Jenkins pipeline checks out the code, builds and tests it with Maven, runs SonarQube analysis and a quality gate, scans dependencies and the Docker image, and pushes the image to ACR. It deploys the image to development AKS with Helm, verifies it with rollout and smoke tests, pauses for approval, and promotes the same tested image to production. Credentials should come from secure identity or secret management rather than being hardcoded.
