# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## CI/CD & Automation

### 4.1 What are GitHub Actions?

GitHub Actions is a CI/CD platform built into GitHub. It runs **workflows**, which are YAML files stored in `.github/workflows/`. A workflow starts when an event happens, such as a push, a pull request, a schedule, or a manual trigger.

A workflow contains **jobs**, and each job runs on a runner. A job is made up of **steps**, and steps can use reusable **actions** from the Marketplace.

GitHub Actions offers hosted or self-hosted runners, secrets management, matrix builds, and reusable or composite workflows.

### 4.2 Difference between GitHub Actions and Jenkins

| | GitHub Actions | Jenkins |
|---|---|---|
| Hosting | SaaS (hosted runners) or self-hosted | Self-managed server + agents |
| Config | YAML in repo | Groovy `Jenkinsfile` (or UI jobs) |
| Setup/maintenance | Minimal, no server to run | You maintain master, agents, plugins, updates |
| Ecosystem | Marketplace actions | Huge plugin ecosystem (also more CVE surface) |
| Integration | Native to GitHub | Tool-agnostic, works with any SCM |
| Scaling | GitHub-managed / self-hosted | You manage agent fleet |
| Best for | GitHub-hosted projects, quick start | Complex/legacy/on-prem, highly customized pipelines |

### 4.3 Why is GitHub Actions gaining popularity?

It's built into GitHub, so there's no extra server to run. The pipeline config lives with the code as YAML, so it's versioned and reviewed through pull requests. It has a huge marketplace of reusable actions and generous hosted runners, and matrix builds are easy to set up. It needs far less maintenance than running Jenkins yourself, and it supports OIDC, so cloud login doesn't need long-lived keys. For teams already on GitHub, this lowers the barrier to CI/CD a lot.

### 4.4 Design a CI/CD pipeline for microservices on Kubernetes

- **Repo strategy:** Give each service its own pipeline. Use a mono-repo with path filters, or separate repos per service — either way, only build what changed.
- **CI stage:** Lint, run unit tests, then build the container with a multi-stage Dockerfile. Run SAST and a dependency scan, then scan the image with Trivy. Push the image tagged with the Git SHA, so the tag never changes once it's pushed.
- **CD stage (GitOps preferred):** Instead of having CI push the change directly, update the desired state in a Git repo that Argo CD or Flux watches. The cluster then reconciles itself — meaning it keeps changing until it matches what's in Git. You can also push with Helm or Kustomize straight from the pipeline if you're not using GitOps.
- **Progressive delivery:** Deploy to staging, run automated tests, then roll out to production with canary or blue-green (Argo Rollouts or Flagger), with automatic rollback if an SLO is breached.
- **Cross-cutting concerns:** environment promotion, secrets pulled from a vault, per-service versioning, observability hooks, and a plan for handling database migrations.

### 4.5 Zero-downtime deployments in Jenkins / GitHub Actions

- **Rolling update** (the Kubernetes default): new pods come up and pass their readiness check before old pods are terminated. `maxUnavailable` and `maxSurge` control how aggressive this is. Use PodDisruptionBudgets too.
- **Blue/Green:** stand up the new version next to the old one, then switch traffic over once it's healthy. Rollback is instant — just switch back.
- **Canary:** send a small percentage of traffic to the new version, watch the metrics, then ramp up gradually.
- **What actually enables this, regardless of tool:** readiness and liveness probes, graceful shutdown (handling SIGTERM and using `preStop`), backward-compatible database migrations (the expand/contract pattern), and only promoting once health checks pass. The CI tool just triggers these steps — the real zero-downtime behavior lives in how the deployment target is set up.

### 4.6 Blue/Green vs Canary — when to choose which

- **Blue/Green:** you run two full environments and cut traffic over all at once. Choose this when you need an instant rollback and can afford double the capacity — for example, major releases where testing on a full parallel environment matters. Downside: cost, and all users move at the same time.
- **Canary:** you gradually shift a small slice of traffic to the new version while watching metrics. Choose this when you want to limit the blast radius, validate against real production traffic, and roll changes out gradually. It needs good metrics and automation to work well. Downside: more complex routing, and a slower full rollout.
- Rule of thumb: canary for continuous, risk-managed delivery of high-traffic services; blue-green for big-bang releases that need an instant switch.

### 4.7 Manage parallel builds and artifacts in Jenkins / GitLab

- **Jenkins:** use `parallel {}` stages in a declarative pipeline, spread work across multiple agents or executors, and use matrix builds for combinations. Use `stash`/`unstash` to pass files between stages, and archive artifacts with `archiveArtifacts` or push them to Nexus or Artifactory.
- **GitLab CI:** jobs in the same `stage` run in parallel automatically. `parallel:` and `parallel:matrix:` fan a job out into many. `artifacts:` pass outputs to later jobs, `cache:` speeds up dependency installs, and `needs:` builds a DAG so jobs don't wait on unrelated stages.
- **In general:** use an artifact repository (Nexus, Artifactory, or a container registry) as the single source of truth, version artifacts so they never change once published, and cache dependencies to speed up builds.

### 4.8 Migrate pipelines from one CI/CD tool to another

1. **Inventory** the existing pipelines: stages, secrets, triggers, plugins, integrations, and agents.
2. **Map the concepts** across tools. For example, Jenkins stages and a `Jenkinsfile` map to GitHub Actions jobs and YAML. Shared libraries map to reusable or composite workflows. Credentials map to GitHub secrets or OIDC.
3. **Migrate incrementally.** Start with a low-risk service, run both pipelines in parallel to compare their output, then cut over.
4. **Re-platform instead of lifting and shifting.** Don't just copy old anti-patterns — use the target tool's own features, like matrix builds, OIDC, and caching.
5. **Handle secrets and artifacts** by migrating them to the new secret store and artifact repository.
6. **Validate, then decommission** the old jobs after a bake-in period. Keep everything under version control the whole way through.

### 4.9 How much experience do you have writing pipeline scripts? / end-to-end pipelines?

Answer with specifics: "I've written declarative and scripted Jenkins pipelines in Groovy, GitHub Actions workflows, and GitLab CI pipelines.

End-to-end, I've built pipelines that check out code, build it with Maven or Docker, run unit tests, run SonarQube for static analysis, scan dependencies and images with OWASP and Trivy, push to Nexus or ECR, deploy to Kubernetes with Helm or Argo CD, run smoke tests, and send a Slack notification — with a manual approval step before production."

Name the actual tools you've used and walk through the flow.

### 4.10 Write a pipeline script using Groovy (Jenkins) — example
```groovy
pipeline {
  agent any
  environment { IMAGE = "myapp:${env.BUILD_NUMBER}" }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Build')    { steps { sh 'mvn -B clean package' } }
    stage('Test')     { steps { sh 'mvn test' }
                        post { always { junit '**/target/surefire-reports/*.xml' } } }
    stage('SonarQube'){ steps { withSonarQubeEnv('sonar') { sh 'mvn sonar:sonar' } } }
    stage('Docker')   { steps { sh "docker build -t ${IMAGE} ." } }
    stage('Scan')     { steps { sh "trivy image --exit-code 1 --severity HIGH,CRITICAL ${IMAGE}" } }
    stage('Push')     { steps {
        withCredentials([usernamePassword(credentialsId:'ecr', usernameVariable:'U', passwordVariable:'P')]) {
          sh "echo $P | docker login -u $U --password-stdin <registry> && docker push ${IMAGE}"
        } } }
    stage('Deploy')   { steps { sh "helm upgrade --install myapp ./chart --set image.tag=${env.BUILD_NUMBER}" } }
  }
  post {
    success { slackSend channel: '#deploys', message: "✅ ${IMAGE} deployed" }
    failure { slackSend channel: '#deploys', message: "❌ Build ${env.BUILD_NUMBER} failed" }
  }
}
```

### 4.11 How do you create GitHub Actions? — example

Add YAML under `.github/workflows/`:
```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
jobs:
  build:
    runs-on: ubuntu-latest
    permissions: { id-token: write, contents: read }   # OIDC for keyless AWS auth
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm test
      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/gha-deploy
          aws-region: us-east-1
      - run: ./deploy.sh
```

---
