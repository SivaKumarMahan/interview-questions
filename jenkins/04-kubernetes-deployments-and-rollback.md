# Jenkins: Kubernetes Deployments and Rollback

> Deploying from Jenkins to Kubernetes/AKS with Helm or GitOps, blue-green releases, and rolling back.

## Key Concepts

### Jenkins Deployment to Kubernetes

```text
Git push/webhook → Jenkins checkout → test and security gates
→ build one image (built once, never changed afterward) → scan/sign/push to registry
→ update Helm/GitOps desired state → rollout → smoke/SLO checks
→ promote or roll back → notify
```

The Jenkinsfile lives with the application code, and each build runs on a fresh, versioned agent that is thrown away afterward. Jenkins reaches the registry and the cluster using scoped credentials or a workload identity, never by hardcoding secrets into commands or letting them show up in logs.

Production deploys are locked down: only certain branches can trigger one, they go through the right environment, they need approval, and only a trusted, scanned artifact is allowed through.

For a direct Helm deployment, Jenkins takes the exact image digest that was built and tested, passes it into a reviewed Helm chart, and runs `helm upgrade --install --atomic --wait --timeout ...`. It then confirms the rollout with `kubectl rollout status` and runs an application smoke test.

With GitOps, Jenkins doesn't touch the cluster directly. It publishes the image and then opens or commits a change that updates the desired state in Git. Argo CD or Flux picks that up and reconciles the cluster, meaning it makes the live cluster match what Git says it should look like.

If a deployment fails, I save the Helm revision, the rendered manifest, the Kubernetes events and logs, and the application metrics before doing anything else. I stop the promotion, roll back to the last known-good artifact or revision, and confirm the rollback actually recovered the service. Only then do I dig into whether the real cause was the pipeline, the chart, a health probe, capacity, a permission, or the application itself — and fix that before retrying.

### Jenkins CI/CD Pipeline for AKS: Overview

This pipeline tests a Java application, checks code quality and security, builds one Docker image, deploys it to development, and then promotes the same image to production after approval.

### AKS Pipeline End-to-End Flow

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

### Example Declarative Pipeline for AKS

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

### What Each Part of the AKS Pipeline Does

#### Agent and tools

The `docker-azure` Jenkins agent must have Java, Maven, Docker, Azure CLI, Helm, kubectl, and Trivy available. The configured SonarQube Jenkins plugin supplies the scanner environment.

#### Pipeline options

- `disableConcurrentBuilds()` stops two runs of this job from deploying at the same time.
- `timestamps()` makes troubleshooting easier by adding times to log lines.
- The pipeline timeout prevents a stuck deployment from running forever.

#### Build, test, and quality checks

`mvn clean verify` compiles the code, runs tests, and creates the application package. SonarQube then checks code quality, bugs, duplication, and security issues. `waitForQualityGate` stops the pipeline if the project does not meet the configured quality rules. It requires the SonarQube webhook to be configured for Jenkins.

#### Security checks

OWASP Dependency-Check looks for known vulnerabilities in application dependencies. Trivy scans the final container image. A serious finding causes the pipeline to stop before the image is pushed or deployed.

#### Image promotion

The image is tagged with the Jenkins build number and pushed to ACR. Development and production use the exact same image tag. Production is not rebuilt, so the tested artifact is the artifact that is promoted.

#### Deployment and verification

Helm installs the application if it is new or upgrades it if it already exists. `--wait` and `kubectl rollout status` confirm that Kubernetes completed the rollout. Smoke tests check that the running application responds successfully.

### AKS Pipeline Production Improvements

- Use a Jenkins credential, workload identity, or managed identity instead of storing Azure credentials in the Jenkinsfile.
- Allow production deployment only from an approved branch or release tag.
- Add the Git commit SHA to the image tag or labels for traceability.
- Add secret scanning and Infrastructure-as-Code scanning when those files are present.
- Send success and failure notifications to Teams, Slack, or email.
- Store scan reports as Jenkins artifacts for auditing.
- Use canary or blue-green deployment when a normal rolling update is too risky.
- Consider GitOps: Jenkins updates the image tag in a deployment repository, and Argo CD deploys it instead of Jenkins running Helm directly.

## Interview Questions

### 1. How do you communicate with a Jenkins server and an Azure Kubernetes cluster?

**A:** To communicate with a Jenkins server and an Azure Kubernetes Service (AKS) cluster, you typically follow these steps:

#### Using Azure Service Principal

1. **Create a Service Principal**: First, you need to create a service principal in Azure that Jenkins can use to authenticate and interact with the AKS cluster. You can create a service principal using the Azure CLI with the following command:

```bash
az ad sp create-for-rbac --name jenkins-aks-sp --role contributor \
  --scopes /subscriptions/<SUB_ID>/resourceGroups/<RG_NAME>
```

The output will be similar to:

```json
{
  "appId": "<CLIENT_ID>",
  "password": "<CLIENT_SECRET>",
  "tenant": "<TENANT_ID>"
}
```

2. **Configure Jenkins Credentials**: In Jenkins, go to `Manage Jenkins` > `Manage Credentials` and add a new credential using the service principal details (client ID, client secret, tenant ID, and subscription ID).
3. **Install Azure CLI on Jenkins**: Ensure that the Azure CLI is installed on your Jenkins server so that it can interact with Azure resources.
4. **Authenticate Jenkins with Azure**: In your Jenkins pipeline, use the Azure CLI to log in using the service principal credentials. You can use the following command in a shell step:

```bash
az login --service-principal -u <CLIENT_ID> -p <CLIENT_SECRET> --tenant <TENANT_ID>
```

5. **Get AKS Credentials**: Use the Azure CLI to get the credentials for your AKS cluster. This will configure `kubectl` to communicate with the AKS cluster:

```bash
az aks get-credentials --resource-group <ResourceGroupName> --name <AKSClusterName>
```

6. **Use kubectl in Jenkins Pipeline**: Now you can use `kubectl` commands in your Jenkins pipeline to interact with the AKS cluster, such as deploying applications, scaling services, or managing resources.

#### Using Jenkins Kubernetes Plugin

1. **Install Kubernetes Plugin**: In Jenkins, install the Kubernetes plugin from the Jenkins plugin manager. This plugin allows Jenkins to dynamically create build agents in a Kubernetes cluster.
2. **Configure Kubernetes Cloud**: In Jenkins, go to `Manage Jenkins` > `Configure System` and add a new Kubernetes cloud. Provide the necessary details such as the Kubernetes API URL, credentials (you can use the service principal created earlier), and namespace.
3. **Define Pod Templates**: Create pod templates that define the containers and resources needed for your Jenkins build agents. You can specify the Docker images, resource limits, and other configurations.
4. **Use Jenkins Pipeline with Kubernetes**: In your Jenkins pipeline, you can specify the use of the Kubernetes cloud and pod templates to run your builds. This allows Jenkins to spin up build agents in the AKS cluster as needed.

#### Jenkins Pipeline Example

```groovy
pipeline {
  agent any

  environment {
    AZURE_CREDENTIALS = credentials('azure-service-principal')
    RESOURCE_GROUP = 'myResourceGroup'
    AKS_NAME = 'myAksCluster'
  }

  stages {
    stage('Authenticate to Azure') {
      steps {
        sh '''
          az login --service-principal \
            -u $AZURE_CREDENTIALS_USR \
            -p $AZURE_CREDENTIALS_PSW \
            --tenant <TENANT_ID>
        '''
      }
    }

    stage('Connect to AKS') {
      steps {
        sh 'az aks get-credentials -g $RESOURCE_GROUP -n $AKS_NAME --overwrite-existing'
      }
    }

    stage('Deploy to AKS') {
      steps {
        sh 'kubectl apply -f k8s/deployment.yaml'
      }
    }
  }
}
```

This example demonstrates how to authenticate to Azure, connect to an AKS cluster, and deploy a Kubernetes manifest using Jenkins. Adjust the pipeline stages and steps according to your specific requirements.

### 2. Walk through a Jenkins CI/CD pipeline that deploys to AKS.

This Jenkins pipeline checks out the code, builds and tests it with Maven, runs SonarQube analysis and a quality gate, scans dependencies and the Docker image, and pushes the image to ACR. It deploys the image to development AKS with Helm, verifies it with rollout and smoke tests, pauses for approval, and promotes the same tested image to production. Credentials should come from secure identity or secret management rather than being hardcoded.

### 3. Which applications and deployment tools do you pair with Jenkins pipelines?

**Answer:**

I pick tools based on the workload, instead of forcing Jenkins to be the deployment engine for everything. Jenkins can build and test Java/Maven, Node, Python, and .NET services, package them as images that don't change after they're built, and store them in ECR, ACR, JFrog, Nexus, or another approved registry.

For Kubernetes, delivery goes through Helm plus Argo CD or Flux, or a controlled `kubectl` step. Cloud infrastructure uses Terraform. VM configuration uses Ansible. Serverless deployment uses a provider framework or infrastructure-as-code.

Jenkins orchestrates the tests, policy checks, artifact publication, approvals, and promotion. Each tool gets its own identity, scoped to only what it needs, and short-lived.

I pass artifact digests and versioned manifests between stages, then check application health, logs, metrics, and a real transaction. This keeps Jenkins swappable later on, and avoids giant imperative scripts that hide what state the deployment is actually in.

### 4. Write a basic Jenkins pipeline that builds, pushes to ACR and deploys to AKS with Helm.

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

### 5. How do you explain the basic Jenkins AKS pipeline stage by stage in an interview?

Explain it stage by stage instead of reading the code line by line.

**Agent**

```groovy
agent { label 'docker-azure' }
```

- The pipeline runs on a Jenkins agent named `docker-azure`.
- This agent should have Docker, Azure CLI, Helm, kubectl, and Maven installed.

**Options**

- `disableConcurrentBuilds()` prevents multiple builds of the same job from running simultaneously.
- `timestamps()` adds timestamps to Jenkins logs for easier troubleshooting.

**Environment variables**

These variables are reused throughout the pipeline.

```
ACR Name = myacr
Registry = myacr.azurecr.io
Image    = orders-api
Tag      = Jenkins Build Number (for example, 105)
```

Final Docker image:

```
myacr.azurecr.io/orders-api:105
```

**Checkout stage** - Jenkins pulls the latest application source code from the Git repository configured for the job.

**Test stage** - `mvn -B clean verify` cleans previous builds, compiles the application and runs unit tests. If any test fails, the pipeline stops here.

**Build Docker image**

```bash
docker build -t myacr.azurecr.io/orders-api:105 .
```

**Push image to ACR** - login to Azure Container Registry, then push the Docker image. The image `myacr.azurecr.io/orders-api:105` is now stored in ACR.

**Deploy to Development AKS** - `az aks get-credentials` downloads the Kubernetes credentials so Jenkins can access the Development AKS cluster. `helm upgrade --install` deploys or upgrades the application using the Helm chart. `kubectl rollout status` waits until the deployment completes successfully.

**Manual approval** - the pipeline pauses. Only users in the `production-approvers` group can approve. This is a common production safety check.

**Deploy to Production** - exactly the same process as Development, except it connects to the Production AKS cluster, deploys to the production namespace, and uses the same Docker image that was tested in Development. This ensures the exact tested artifact is promoted to Production.

**Post section** - `junit` publishes JUnit test reports in Jenkins. Even if the build fails, Jenkins still displays the test results.

**Overall flow**

```
Developer
      |
      v
Git Repository
      |
      v
Jenkins Checkout
      |
      v
Maven Build & Unit Tests
      |
      v
Docker Build
      |
      v
Push Image to Azure Container Registry (ACR)
      |
      v
Deploy to Development AKS (Helm)
      |
      v
Verify Rollout
      |
      v
Manual Approval
      |
      v
Deploy to Production AKS (Helm)
      |
      v
Verify Rollout
      |
      v
Publish Test Reports
```

**Interview explanation (1-minute answer)**

> "This is a Jenkins Declarative Pipeline that automates the complete CI/CD process. It first checks out the code from Git, builds and tests the application using Maven, then creates a Docker image and pushes it to Azure Container Registry. Next, it deploys the image to the Development AKS cluster using Helm and verifies the rollout. After successful testing, the pipeline pauses for manual approval before promoting the same Docker image to the Production AKS cluster. Finally, it publishes the JUnit test reports. Using the same image for both environments ensures consistency and avoids environment-specific build differences."

### 6. What is a basic Jenkins pipeline missing for production-grade CI/CD?

For a production-grade DevOps pipeline, the basic pipeline is missing a few important stages:

1. Checkout
2. Dependency download / cache (optional)
3. Compile
4. Unit tests
5. **SonarQube static code analysis**
6. **Quality gate validation**
7. Package application
8. **Dependency vulnerability scan** (OWASP Dependency Check or Snyk)
9. Build Docker image
10. **Docker image vulnerability scan** (Trivy / Grype)
11. Push image to Azure Container Registry
12. Deploy to Development
13. **Smoke tests / API health check**
14. Manual approval
15. Deploy to Production
16. Rollout verification
17. **Post-deployment smoke test**
18. Publish test reports
19. **Notifications** (Email / Slack / Teams)

This is the typical enterprise CI/CD flow.

### 7. Write an enterprise Jenkins pipeline for AKS with SonarQube and quality gates.

```groovy
pipeline {
    agent { label 'docker-azure' }

    options {
        disableConcurrentBuilds()
        timestamps()
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

        stage('Compile') {
            steps {
                sh 'mvn clean compile'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'mvn test'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh '''
                    mvn sonar:sonar \
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

        stage('Package') {
            steps {
                sh 'mvn package -DskipTests'
            }
        }

        stage('Dependency Vulnerability Scan') {
            steps {
                sh '''
                mvn org.owasp:dependency-check-maven:check
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                docker build \
                -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG .
                '''
            }
        }

        stage('Docker Image Scan') {
            steps {
                sh '''
                trivy image \
                --exit-code 1 \
                --severity HIGH,CRITICAL \
                $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
        }

        stage('Push to ACR') {
            steps {
                sh '''
                az acr login --name $ACR_NAME

                docker push \
                $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
                '''
            }
        }

        stage('Deploy Development') {
            steps {
                sh '''
                az aks get-credentials \
                --resource-group <dev-rg> \
                --name <dev-aks> \
                --overwrite-existing

                helm upgrade --install orders-api ./helm/orders-api \
                --namespace development \
                --create-namespace \
                --set image.repository=$REGISTRY/$IMAGE_NAME \
                --set image.tag=$IMAGE_TAG \
                --wait
                '''
            }
        }

        stage('Verify Rollout') {
            steps {
                sh '''
                kubectl rollout status deployment/orders-api \
                -n development
                '''
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                curl -f http://orders-api-dev/actuator/health
                '''
            }
        }

        stage('Production Approval') {
            input {
                message 'Deploy to Production?'
                ok 'Deploy'
                submitter 'production-approvers'
            }
            steps {
                echo "Approved"
            }
        }

        stage('Deploy Production') {
            steps {
                sh '''
                az aks get-credentials \
                --resource-group <prod-rg> \
                --name <prod-aks> \
                --overwrite-existing

                helm upgrade --install orders-api ./helm/orders-api \
                --namespace production \
                --create-namespace \
                --set image.repository=$REGISTRY/$IMAGE_NAME \
                --set image.tag=$IMAGE_TAG \
                --wait
                '''
            }
        }

        stage('Verify Production Rollout') {
            steps {
                sh '''
                kubectl rollout status deployment/orders-api \
                -n production
                '''
            }
        }

        stage('Production Smoke Test') {
            steps {
                sh '''
                curl -f https://orders.company.com/actuator/health
                '''
            }
        }

    }

    post {

        always {
            junit 'target/surefire-reports/*.xml'
        }

        success {
            echo 'Deployment Successful'
        }

        failure {
            echo 'Deployment Failed'
        }
    }
}
```

### 8. What additional enterprise improvements can you add to a Jenkins AKS pipeline?

If you're targeting senior DevOps or Azure DevOps interviews, you can also mention these practices:

- **Secrets management:** retrieve credentials from Azure Key Vault instead of hardcoding them.
- **Branch strategy:** deploy to production only from the main branch, with feature branches deploying to development or test environments.
- **Image tagging:** tag images with both the build number and the Git commit SHA (for example, `105` and `a1b2c3d`) to improve traceability.
- **Artifact repository:** publish JAR/WAR artifacts to repositories like Nexus or Artifactory before building container images.
- **GitOps deployment:** instead of Jenkins running `helm upgrade` directly, update the Helm values in a GitOps repository and let tools like Argo CD or Flux CD synchronize the changes to AKS.
- **Security scanning:** add secret scanning (Gitleaks), container configuration scanning (Trivy), and Infrastructure-as-Code scanning (Checkov or tfsec) as part of the pipeline.
- **Notifications:** send build and deployment status to Microsoft Teams, Slack, or email.
- **Progressive delivery:** use blue-green or canary deployments for production releases to minimize risk.

This version is much closer to what you'll see in enterprise environments and is suitable for discussing in DevOps interviews.

### 9. How do you perform blue-green deployment using Jenkins + Kubernetes? *(scenario)*

**Answer:** Jenkins pipeline deploys Green → Run tests → Switch traffic to Green (via service or ingress) → Keep Blue as rollback option.

**Detailed interview approach:**
I deploy one artifact that never changes after it's built, using a strategy that matches the risk: rolling updates for routine stateless changes, canary releases when I want to expose the change gradually and watch metrics, or blue-green when I need to switch traffic instantly.

The pipeline runs prechecks, deploys to a small or no-traffic target first, runs readiness and real business smoke tests, then gradually shifts more traffic over while watching error rate, latency, resource saturation, and the SLO/error budget.

If any of those thresholds are breached, it stops sending traffic and rolls back to the previous artifact or config. Database changes need to expand first and contract later, in separate steps, because rolling back the application can't undo a destructive schema change. Afterward I confirm the service actually recovered, record what happened, and improve whichever test or guard should have caught the problem earlier.

### 10. How do you roll back in Jenkins if a deployment causes issues? *(scenario)*

**Answer:** Keep artifact versioning → Redeploy the last stable build from Jenkins → Or trigger rollback pipeline.

**Detailed interview approach:**
The pipeline keeps a record of the last known-good artifact and its exact digest, plus the deployment configuration that went with it.

If health checks or SLOs fail after a deploy, the pipeline stops promoting and triggers the platform's own rollback — a Helm rollback, a Kubernetes rollout undo, or a traffic switch — rather than rebuilding from an old branch.

I confirm readiness, error rate, latency, and that a real business transaction still works, then send a notification with the failed commit and the recovery result. Database and schema changes have to stay backward-compatible, because rolling back the application alone can't undo a schema change.

Automatic rollback has a timeout and a manual fallback in case it doesn't finish cleanly. Once things are stable, I preserve the evidence and fix whatever test, health probe, configuration, or capacity guard should have caught the problem first.
