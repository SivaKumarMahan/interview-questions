# SonarQube, Trivy, and Notifications in Jenkins

The quality flow should fail before publishing or deploying an unacceptable artifact:

```text
checkout → unit tests → SonarQube analysis → quality gate
         → image build → Trivy scan → sign/publish → deploy → notify
```

Required setup:

- Configure the SonarQube server and token in Jenkins; keep the token in Credentials, not the repository.
- Install/configure the SonarQube Scanner and notification integration, or call notification webhooks through protected credentials.
- Install a pinned Trivy version in the agent image rather than downloading an unverified binary during every build.
- Agree on quality-gate and vulnerability policy, including severity, fix availability, expiry for exceptions, and report retention.

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

Unlike the original draft, Trivy returns a failing exit code for policy violations, secrets are not embedded in the Jenkinsfile, and publication happens only after both gates pass. In production I also generate an SBOM, sign the image digest, archive access-controlled reports, and verify the signature at deployment.
