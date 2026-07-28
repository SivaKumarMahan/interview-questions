# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## CI/CD & Automation

### 4.1 What are GitHub Actions?

A CI/CD platform built into GitHub that runs **workflows** (YAML in `.github/workflows/`) triggered by events (push, PR, schedule, manual). A workflow has **jobs** (run on runners) made of **steps**, and steps use reusable **actions** from the Marketplace.

It offers hosted or self-hosted runners, secrets, matrix builds, and reusable/composite workflows.

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

Native to GitHub (no extra server), config lives with the code (YAML, versioned, PR-reviewed), huge reusable-actions marketplace, generous hosted runners, easy matrix builds, low maintenance vs. running Jenkins, and OIDC-based keyless cloud auth. It lowers the barrier to CI/CD dramatically for teams already on GitHub.

### 4.4 Design a CI/CD pipeline for microservices on Kubernetes

- **Repo strategy:** per-service pipelines (mono-repo with path filters, or poly-repo). Build only what changed.
- **CI stage:** lint → unit tests → build container (multi-stage) → SAST + dependency scan → image scan (Trivy) → push immutable (not changed after creation) tag (git SHA) to registry.
- **CD stage (GitOps preferred):** update the desired state in a Git repo (Argo CD / Flux) rather than pushing from CI; the cluster reconciles (makes actual state match desired state). Or push via Helm/Kustomize from the pipeline.
- **Progressive delivery:** deploy to staging → automated tests → canary/blue-green to prod (Argo Rollouts / Flagger) with automated rollback on SLO breach.
- **Cross-cutting:** environment promotion, secrets from a vault, per-service versioning, observability hooks, and DB migration handling.

### 4.5 Zero-downtime deployments in Jenkins / GitHub Actions

- **Rolling update** (K8s default): new pods come up and pass readiness before old ones terminate; `maxUnavailable`/`maxSurge` tune it. Use PDBs.
- **Blue/Green:** stand up the new version alongside old, switch traffic (Service/ingress/LB) once healthy; instant rollback by switching back.
- **Canary:** shift a small % of traffic to the new version, watch metrics, ramp up gradually.
- **Key enablers regardless of tool:** readiness/liveness probes, graceful shutdown (SIGTERM handling + `preStop`), backward-compatible DB migrations (expand/contract), and health-gated promotion. The CI tool just orchestrates these; the pattern lives in the deploy target.

### 4.6 Blue/Green vs Canary — when to choose which

- **Blue/Green:** two full environments, cut traffic over all at once. **Choose when** you need instant rollback and can afford double capacity, and testing on a full parallel env matters (e.g. major releases). Downside: cost, and all users move at once.
- **Canary:** gradually route a small subset of traffic to the new version while monitoring. **Choose when** you want to limit scope of impact, validate against real production traffic, and roll changes progressively. Needs good metrics/automation. Downside: more complex routing, slower full rollout.
- Rule of thumb: canary for continuous, risk-managed delivery of high-traffic services; blue/green for big-bang releases needing an instant switch.

### 4.7 Manage parallel builds and artifacts in Jenkins / GitLab

- **Jenkins:** `parallel {}` stages in a declarative pipeline; multiple agents/executors; matrix builds; `stash`/`unstash` to pass files between stages; archive artifacts via `archiveArtifacts` or push to Nexus/Artifactory.
- **GitLab CI:** jobs in the same `stage` run in parallel; `parallel:` and `parallel:matrix:` fan-out; `artifacts:` pass outputs downstream, `cache:` for dependencies; `needs:` builds a DAG for faster, non-linear pipelines.
- **General:** use an artifact repository (Nexus/Artifactory/registry) as the source of truth, version artifacts immutably, and cache dependencies to speed builds.

### 4.8 Migrate pipelines from one CI/CD tool to another

1. **Inventory** existing pipelines: stages, secrets, triggers, plugins, integrations, agents.
2. **Map concepts:** e.g. Jenkins stages/`Jenkinsfile` → GitHub Actions jobs/YAML; shared libraries → reusable/composite workflows; credentials → GH secrets/OIDC.
3. **Migrate incrementally:** start with a low-risk service, run **both pipelines in parallel** to compare outputs, then cut over.
4. **Re-platform, don't lift-and-shift** anti-patterns; adopt the target tool's idioms (matrix, OIDC, caching).
5. **Handle secrets & artifacts:** migrate to the new secret store and artifact repo.
6. **Validate & decommission** old jobs after a bake-in period. Keep everything in version control.

### 4.9 How much experience do you have writing pipeline scripts? / end-to-end pipelines?

Frame with specifics: *"I've written declarative and scripted Jenkins pipelines (Groovy), GitHub Actions workflows, and GitLab CI.

End-to-end I've built: checkout → build (Maven/Docker) → unit tests → SonarQube (SAST) → dependency & image scan (OWASP/Trivy) → push to Nexus/ECR → deploy to K8s via Helm/Argo CD → smoke tests → Slack notification, with approvals for prod."* Name the tools and the flow.

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
