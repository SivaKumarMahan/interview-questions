# Jenkinsfile and Jenkins CLI Cheatcode

## Declarative Jenkinsfile skeleton

```groovy
pipeline {
  agent none
  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
  parameters {
    choice(name: 'ENVIRONMENT', choices: ['dev', 'stage'], description: 'Target')
  }
  stages {
    stage('Checkout') {
      agent { label 'linux' }
      steps { checkout scm }
    }
    stage('Build and Test') {
      agent { label 'maven' }
      steps { sh 'mvn -B verify' }
      post { always { junit 'target/surefire-reports/*.xml' } }
    }
    stage('Publish') {
      when { branch 'main' }
      agent { label 'docker' }
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'registry',
          usernameVariable: 'REGISTRY_USER',
          passwordVariable: 'REGISTRY_PASSWORD'
        )]) {
          sh '''
            set +x
            printf '%s' "$REGISTRY_PASSWORD" | docker login registry.example \
              --username "$REGISTRY_USER" --password-stdin
            docker build -t registry.example/app:${GIT_COMMIT} .
            docker push registry.example/app:${GIT_COMMIT}
          '''
        }
      }
    }
  }
  post {
    always { deleteDir() }
  }
}
```

Prefer short-lived registry/cloud identity where supported. Do not interpolate secrets in Groovy strings.

## Service commands

```bash
systemctl status jenkins
systemctl start jenkins
systemctl stop jenkins
systemctl restart jenkins
journalctl -u jenkins --since '30 minutes ago'
```

## Troubleshooting order

```text
Jenkinsfile syntax → first failed stage → command exit code/test report
→ agent label/health/workspace → tool/dependency versions
→ credentials/permissions → DNS/proxy/registry → disk/memory/executors
→ recent plugin/shared-library/controller change
```
