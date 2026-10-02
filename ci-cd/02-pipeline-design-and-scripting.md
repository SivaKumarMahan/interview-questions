# CI/CD: Pipeline Design and Scripting

> Designing pipelines for microservices and monorepos, parallel builds, matrix builds and artifacts, example pipeline scripts, and migrating between CI/CD tools.

## Interview Questions

### 1. Design a CI/CD pipeline for microservices on Kubernetes *(asked in interview round)*

- **Repo strategy:** Give each service its own pipeline. Use a mono-repo with path filters, or separate repos per service — either way, only build what changed.
- **CI stage:** Lint, run unit tests, then build the container with a multi-stage Dockerfile. Run SAST and a dependency scan, then scan the image with Trivy. Push the image tagged with the Git SHA, so the tag never changes once it's pushed.
- **CD stage (GitOps preferred):** Instead of having CI push the change directly, update the desired state in a Git repo that Argo CD or Flux watches. The cluster then reconciles itself — meaning it keeps changing until it matches what's in Git. You can also push with Helm or Kustomize straight from the pipeline if you're not using GitOps.
- **Progressive delivery:** Deploy to staging, run automated tests, then roll out to production with canary or blue-green (Argo Rollouts or Flagger), with automatic rollback if an SLO is breached.
- **Cross-cutting concerns:** environment promotion, secrets pulled from a vault, per-service versioning, observability hooks, and a plan for handling database migrations.

### 2. How do you design CI/CD pipelines for microservices? *(scenario)*

**Answer:** Give each service a separate pipeline, build and push Docker images, deploy with Helm, and use shared monitoring and logging.

**Detailed interview approach:**
Each service gets its own pipeline, triggered independently based on which paths or repos changed, but all of them share versioned templates.

The flow builds once, runs unit, integration, contract, and security tests, produces a signed image and SBOM, publishes that digest without ever changing it, updates the deployment configuration, and promotes it through environments.

Contract and compatibility tests protect the boundaries between services. Canary or rolling rollout watches each service's SLOs and traces. Shared cache keys include lockfiles and tool versions, and parallelism is tuned to respect downstream capacity.

Platform-level controls standardize identity, secrets, policy, logging, and rollback, without coupling every service's release to the others. I track lead time, failures, queue time, and change-failure rate per service.

### 3. How do you implement CI/CD for microservices? *(scenario)*

**Answer:** Use a separate pipeline per microservice, containerize each one, deploy to Kubernetes with Helm or ArgoCD, and centralize monitoring.

**Detailed interview approach:**
Each service gets its own pipeline, triggered independently based on which paths or repos changed, but all of them share versioned templates.

The flow builds once, runs unit, integration, contract, and security tests, produces a signed image and SBOM, publishes that digest without ever changing it, updates the deployment configuration, and promotes it through environments.

Contract and compatibility tests protect the boundaries between services. Canary or rolling rollout watches each service's SLOs and traces. Shared cache keys include lockfiles and tool versions, and parallelism is tuned to respect downstream capacity.

Platform-level controls standardize identity, secrets, policy, logging, and rollback, without coupling every service's release to the others. I track lead time, failures, queue time, and change-failure rate per service.

### 4. How do you optimize CI/CD pipelines for monorepos? *(scenario)*

**Answer:** Use change detection so jobs only run for the paths that changed, parallelize builds, cache dependencies, and modularize the pipelines. Mini-case: instead of rebuilding every service, we ran jobs only for changed directories, and build time dropped from an hour to twelve minutes.

**Detailed interview approach:**
Each service gets its own pipeline, triggered independently based on which paths or repos changed, but all of them share versioned templates.

The flow builds once, runs unit, integration, contract, and security tests, produces a signed image and SBOM, publishes that digest without ever changing it, updates the deployment configuration, and promotes it through environments.

Contract and compatibility tests protect the boundaries between services. Canary or rolling rollout watches each service's SLOs and traces. Shared cache keys include lockfiles and tool versions, and parallelism is tuned to respect downstream capacity.

Platform-level controls standardize identity, secrets, policy, logging, and rollback, without coupling every service's release to the others. I track lead time, failures, queue time, and change-failure rate per service.

### 5. Manage parallel builds and artifacts in Jenkins / GitLab *(asked in interview round)*

- **Jenkins:** use `parallel {}` stages in a declarative pipeline, spread work across multiple agents or executors, and use matrix builds for combinations. Use `stash`/`unstash` to pass files between stages, and archive artifacts with `archiveArtifacts` or push them to Nexus or Artifactory.
- **GitLab CI:** jobs in the same `stage` run in parallel automatically. `parallel:` and `parallel:matrix:` fan a job out into many. `artifacts:` pass outputs to later jobs, `cache:` speeds up dependency installs, and `needs:` builds a DAG so jobs don't wait on unrelated stages.
- **In general:** use an artifact repository (Nexus, Artifactory, or a container registry) as the single source of truth, version artifacts so they never change once published, and cache dependencies to speed up builds.

### 6. How do you manage parallel builds and artifacts?

**Answer:**

Independent tests and services run in parallel with explicit dependencies between them. Each job writes to its own workspace and uses fixed version identifiers, so outputs can't overwrite each other.

A fan-in job collects the reports and decides whether publication is allowed.

Artifacts carry checksums, a version or commit reference, a retention policy, and access controls. I publish once and promote that same artifact — I don't rebuild it per environment. Cache is kept separate and disposable.

Concurrency limits protect shared test systems and deployment environments. I test partial job failure, missing artifacts, retries, and cancellation. Monitoring queue time and duration shows whether parallelism is actually helping, or just moving the bottleneck downstream.

### 7. How do matrix builds, caching, and concurrency limits help pipelines?

**Answer:**

Matrix builds test every supported combination of OS, runtime, and version in parallel. Caching avoids re-downloading the same dependencies every run. Concurrency limits stop unsafe parallel deployments or duplicate workflow runs on the same branch.

Cache keys include the dependency lock file and platform details. A build still has to work correctly with an empty cache, and untrusted branches shouldn't be able to poison a protected cache.

Artifacts and caches are different things: artifacts are versioned deliverables, caches are disposable speed optimizations.

For deployment, I only let one job be active per environment at a time, and I cancel outdated non-production runs. I track speed improvement, cache hit rate, runner cost, and flakiness, so optimizing for speed doesn't quietly reduce test coverage or reliability.

### 8. Write a pipeline script using Groovy (Jenkins) — example *(asked in interview round)*

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

### 9. How do you create GitHub Actions? — example *(asked in interview round)*

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

### 10. Migrate pipelines from one CI/CD tool to another *(asked in interview round)*

1. **Inventory** the existing pipelines: stages, secrets, triggers, plugins, integrations, and agents.
2. **Map the concepts** across tools. For example, Jenkins stages and a `Jenkinsfile` map to GitHub Actions jobs and YAML. Shared libraries map to reusable or composite workflows. Credentials map to GitHub secrets or OIDC.
3. **Migrate incrementally.** Start with a low-risk service, run both pipelines in parallel to compare their output, then cut over.
4. **Re-platform instead of lifting and shifting.** Don't just copy old anti-patterns — use the target tool's own features, like matrix builds, OIDC, and caching.
5. **Handle secrets and artifacts** by migrating them to the new secret store and artifact repository.
6. **Validate, then decommission** the old jobs after a bake-in period. Keep everything under version control the whole way through.

### 11. How do you migrate pipelines from one CI/CD tool to another?

**Answer:**

I inventory triggers, stages, runners, plugins, variables, secrets, artifacts, approvals, schedules, retention rules, and integrations. I separate the portable scripts from tool-specific syntax and map each control to the target platform.

I build one representative pipeline first, migrate secrets securely, recreate the protected environments and identities, then run the old and new pipelines in parallel — without letting both deploy to production. I compare artifact checksums, test results, duration, permissions, and audit evidence between them.

Cutover happens in a freeze or change window, with owner communication, a rollback plan to the old pipeline, and monitoring. I only decommission the old credentials and runners after things have run stably and any retention requirements are met.
