# Testing Tools: Pipeline Testing and Quality Gates

> Test types and stages in CI/CD, automating unit/integration/end-to-end tests, and enforcing code quality with SonarQube, Trivy and notifications in Jenkins.

## Key Concepts

### SonarQube, Trivy, and Notifications in Jenkins

The quality flow should fail before publishing or deploying an unacceptable artifact:

```text
checkout → unit tests → SonarQube analysis → quality gate
         → image build → Trivy scan → sign/publish → deploy → notify
```

Required setup:

- Configure the SonarQube server and token in Jenkins. Keep the token in Credentials, not the repository.
- Install and configure the SonarQube Scanner and notification integration, or call notification webhooks through protected credentials.
- Install a pinned Trivy version in the agent image, rather than downloading an unverified binary on every build.
- Agree on a quality-gate and vulnerability policy up front. Cover severity, fix availability, how long exceptions last, and how long reports are kept.

Example pipeline stages:

```groovy
pipeline {
  agent { label 'ephemeral-linux' }

  environment {
    IMAGE = "registry.example.com/team/app:${BUILD_NUMBER}"
  }

  stages {
    stage('Checkout and Test') {
      steps {
        checkout scm
        sh 'npm ci && npm test'
      }
    }

    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv('sonarqube-production') {
          sh 'sonar-scanner -Dsonar.projectKey=team-app'
        }
      }
    }

    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    stage('Build and Scan Image') {
      steps {
        sh 'docker build --pull --tag "$IMAGE" .'
        sh 'trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed "$IMAGE"'
      }
    }

    stage('Publish') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'registry-credentials',
          usernameVariable: 'REGISTRY_USER',
          passwordVariable: 'REGISTRY_PASSWORD'
        )]) {
          sh 'printf %s "$REGISTRY_PASSWORD" | docker login registry.example.com --username "$REGISTRY_USER" --password-stdin'
          sh 'docker push "$IMAGE"'
        }
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: '**/test-results/*.xml'
      deleteDir()
    }
    success {
      slackSend color: 'good', message: "SUCCESS: ${JOB_NAME} #${BUILD_NUMBER}"
    }
    failure {
      slackSend color: 'danger', message: "FAILED: ${JOB_NAME} #${BUILD_NUMBER} — ${BUILD_URL}"
    }
  }
}
```

Unlike the original draft, Trivy now returns a failing exit code for policy violations. Secrets are no longer embedded in the Jenkinsfile. Publication only happens after both the quality gate and the scan pass.

In production I also generate an SBOM (a software bill of materials — a list of what's inside the image), sign the image digest, archive access-controlled reports, and verify the signature at deployment.

## Interview Questions

<details><summary>Q1. [Intermediate] What types of testing do you include in your CI/CD pipeline, and at what stages do they run? <em>(scenario)</em></summary>

**Answer:** Unit tests on every commit with coverage → Trivy image scan after build → integration tests in dev → `terraform plan` validation → e2e (Cypress) + performance (k6) in staging → post-deploy smoke tests → required PR checks + ArgoCD health gates.
**Detailed interview approach:**
The GitHub Actions workflow includes multiple testing stages. Unit tests run on every commit using language-specific frameworks with coverage enforcement.

After building container images, I conduct security scanning with Trivy. For deployments to dev, the pipeline runs integration tests against the deployed APIs.

Terraform plan validation runs before any infrastructure changes are applied. In staging, I execute end-to-end tests with Cypress and performance tests using k6.

Post-deployment smoke tests verify core functionality in every environment. Each test stage is a required check in GitHub pull requests, and failures block promotion to higher environments.

ArgoCD's health checks provide an additional validation layer after deployment.

</details>

<details><summary>Q2. [Intermediate] How do you automate unit, integration, and end-to-end tests in your pipeline? <em>(scenario)</em></summary>

**Answer:** GitHub Actions automates all layers → unit tests in build stage → integration tests against dev EKS via OIDC → Cypress e2e against staging → artifacts uploaded → ArgoCD readiness gates → failed tests auto-create issues.

**Detailed interview approach:**
GitHub Actions workflows automate all testing. Unit tests run in the build stage, triggered on every push, using workspace-mounted volumes for test reports and coverage data.

Integration tests run after deploying to the dev EKS cluster. GitHub Actions uses OIDC-based access to invoke tests against the deployed endpoints.

End-to-end tests with Cypress run in dedicated GitHub Actions runners with browser capabilities, targeting staging after deployment. Test results and artifacts get uploaded for review.

ArgoCD deployments include readiness gates that verify system health before the deployment completes. Failed tests in GitHub Actions automatically create an issue for developers, with a link to the run and its logs.

</details>

<details><summary>Q3. [Intermediate] How do you ensure integration tests work across different environments? <em>(scenario)</em></summary>

**Answer:** Tests read config from env vars/Terraform outputs → Kubernetes Jobs seed fixtures → Wiremock for external dependencies → env-specific databases via Terraform + migrations → cleanup jobs → ArgoCD keeps consistent app state.

**Detailed interview approach:**
I structure integration tests to read configuration from environment variables injected by GitHub Actions workflows. Each test job pulls environment-specific endpoints from Terraform outputs and EKS service discovery.

Test data is managed through Kubernetes Jobs that seed test fixtures before test execution.

For external dependencies, I use Wiremock containers deployed alongside the application to give consistent responses. Database tests run against environment-specific databases provisioned by Terraform, with migrations applied to keep the schema compatible.

After tests complete, cleanup jobs remove test data, and ArgoCD ensures consistent application state across environments, making integration tests reliable across the pipeline.

</details>

<details><summary>Q4. [Intermediate] How do you enforce code quality checks before merging in CI/CD? <em>(scenario)</em></summary>

**Answer:** Add mandatory linting, unit tests, SonarQube scans in Jenkins/GitHub Actions → Fail build if checks don’t pass → Protect main branch with approval rules.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

</details>
