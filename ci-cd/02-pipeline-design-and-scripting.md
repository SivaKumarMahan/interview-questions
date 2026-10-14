# CI/CD: Pipeline Design and Scripting

> Designing pipelines for microservices and monorepos, parallel builds, matrix builds and artifacts, example pipeline scripts, and migrating between CI/CD tools.

## Interview Questions

<details><summary>Q1. [Advanced] Design a CI/CD pipeline for microservices on Kubernetes <em>(asked in interview round)</em></summary>

- **Repo strategy:** Give each service its own pipeline. Use a mono-repo with path filters, or separate repos per service — either way, only build what changed.
- **CI stage:** Lint, run unit tests, then build the container with a multi-stage Dockerfile. Run SAST and a dependency scan, then scan the image with Trivy. Push the image tagged with the Git SHA, so the tag never changes once it's pushed.
- **CD stage (GitOps preferred):** Instead of having CI push the change directly, update the desired state in a Git repo that Argo CD or Flux watches. The cluster then reconciles itself — meaning it keeps changing until it matches what's in Git. You can also push with Helm or Kustomize straight from the pipeline if you're not using GitOps.
- **Progressive delivery:** Deploy to staging, run automated tests, then roll out to production with canary or blue-green (Argo Rollouts or Flagger), with automatic rollback if an SLO is breached.
- **Cross-cutting concerns:** environment promotion, secrets pulled from a vault, per-service versioning, observability hooks, and a plan for handling database migrations.

</details>

<details><summary>Q2. [Advanced] How do you design CI/CD pipelines for microservices? <em>(scenario)</em></summary>

**Answer:** Give each service a separate pipeline, build and push Docker images, deploy with Helm, and use shared monitoring and logging.

**Detailed interview approach:**
Each service gets its own pipeline, triggered independently based on which paths or repos changed, but all of them share versioned templates.

The flow builds once, runs unit, integration, contract, and security tests, produces a signed image and SBOM, publishes that digest without ever changing it, updates the deployment configuration, and promotes it through environments.

Contract and compatibility tests protect the boundaries between services. Canary or rolling rollout watches each service's SLOs and traces. Shared cache keys include lockfiles and tool versions, and parallelism is tuned to respect downstream capacity.

Platform-level controls standardize identity, secrets, policy, logging, and rollback, without coupling every service's release to the others. I track lead time, failures, queue time, and change-failure rate per service.

</details>

<details><summary>Q3. [Intermediate] How do you implement CI/CD for microservices? <em>(scenario)</em></summary>

**Answer:** Use a separate pipeline per microservice, containerize each one, deploy to Kubernetes with Helm or ArgoCD, and centralize monitoring.

**Detailed interview approach:**
Each service gets its own pipeline, triggered independently based on which paths or repos changed, but all of them share versioned templates.

The flow builds once, runs unit, integration, contract, and security tests, produces a signed image and SBOM, publishes that digest without ever changing it, updates the deployment configuration, and promotes it through environments.

Contract and compatibility tests protect the boundaries between services. Canary or rolling rollout watches each service's SLOs and traces. Shared cache keys include lockfiles and tool versions, and parallelism is tuned to respect downstream capacity.

Platform-level controls standardize identity, secrets, policy, logging, and rollback, without coupling every service's release to the others. I track lead time, failures, queue time, and change-failure rate per service.

</details>

<details><summary>Q4. [Advanced] How do you optimize CI/CD pipelines for monorepos? <em>(scenario)</em></summary>

**Answer:** Use change detection so jobs only run for the paths that changed, parallelize builds, cache dependencies, and modularize the pipelines. Mini-case: instead of rebuilding every service, we ran jobs only for changed directories, and build time dropped from an hour to twelve minutes.

**Detailed interview approach:**
Each service gets its own pipeline, triggered independently based on which paths or repos changed, but all of them share versioned templates.

The flow builds once, runs unit, integration, contract, and security tests, produces a signed image and SBOM, publishes that digest without ever changing it, updates the deployment configuration, and promotes it through environments.

Contract and compatibility tests protect the boundaries between services. Canary or rolling rollout watches each service's SLOs and traces. Shared cache keys include lockfiles and tool versions, and parallelism is tuned to respect downstream capacity.

Platform-level controls standardize identity, secrets, policy, logging, and rollback, without coupling every service's release to the others. I track lead time, failures, queue time, and change-failure rate per service.

</details>

<details><summary>Q5. [Intermediate] Manage parallel builds and artifacts in Jenkins / GitLab <em>(asked in interview round)</em></summary>

- **Jenkins:** use `parallel {}` stages in a declarative pipeline, spread work across multiple agents or executors, and use matrix builds for combinations. Use `stash`/`unstash` to pass files between stages, and archive artifacts with `archiveArtifacts` or push them to Nexus or Artifactory.
- **GitLab CI:** jobs in the same `stage` run in parallel automatically. `parallel:` and `parallel:matrix:` fan a job out into many. `artifacts:` pass outputs to later jobs, `cache:` speeds up dependency installs, and `needs:` builds a DAG so jobs don't wait on unrelated stages.
- **In general:** use an artifact repository (Nexus, Artifactory, or a container registry) as the single source of truth, version artifacts so they never change once published, and cache dependencies to speed up builds.

</details>

<details><summary>Q6. [Intermediate] How do you manage parallel builds and artifacts?</summary>

**Answer:**

Independent tests and services run in parallel with explicit dependencies between them. Each job writes to its own workspace and uses fixed version identifiers, so outputs can't overwrite each other.

A fan-in job collects the reports and decides whether publication is allowed.

Artifacts carry checksums, a version or commit reference, a retention policy, and access controls. I publish once and promote that same artifact — I don't rebuild it per environment. Cache is kept separate and disposable.

Concurrency limits protect shared test systems and deployment environments. I test partial job failure, missing artifacts, retries, and cancellation. Monitoring queue time and duration shows whether parallelism is actually helping, or just moving the bottleneck downstream.

</details>

<details><summary>Q7. [Intermediate] How do matrix builds, caching, and concurrency limits help pipelines?</summary>

**Answer:**

Matrix builds test every supported combination of OS, runtime, and version in parallel. Caching avoids re-downloading the same dependencies every run. Concurrency limits stop unsafe parallel deployments or duplicate workflow runs on the same branch.

Cache keys include the dependency lock file and platform details. A build still has to work correctly with an empty cache, and untrusted branches shouldn't be able to poison a protected cache.

Artifacts and caches are different things: artifacts are versioned deliverables, caches are disposable speed optimizations.

For deployment, I only let one job be active per environment at a time, and I cancel outdated non-production runs. I track speed improvement, cache hit rate, runner cost, and flakiness, so optimizing for speed doesn't quietly reduce test coverage or reliability.

</details>

<details><summary>Q8. [Intermediate] Write a pipeline script using Groovy (Jenkins) — example <em>(asked in interview round)</em></summary>

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

</details>

<details><summary>Q9. [Intermediate] How do you create GitHub Actions? — example <em>(asked in interview round)</em></summary>

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

</details>

<details><summary>Q10. [Advanced] Migrate pipelines from one CI/CD tool to another <em>(asked in interview round)</em></summary>

1. **Inventory** the existing pipelines: stages, secrets, triggers, plugins, integrations, and agents.
2. **Map the concepts** across tools. For example, Jenkins stages and a `Jenkinsfile` map to GitHub Actions jobs and YAML. Shared libraries map to reusable or composite workflows. Credentials map to GitHub secrets or OIDC.
3. **Migrate incrementally.** Start with a low-risk service, run both pipelines in parallel to compare their output, then cut over.
4. **Re-platform instead of lifting and shifting.** Don't just copy old anti-patterns — use the target tool's own features, like matrix builds, OIDC, and caching.
5. **Handle secrets and artifacts** by migrating them to the new secret store and artifact repository.
6. **Validate, then decommission** the old jobs after a bake-in period. Keep everything under version control the whole way through.

</details>

<details><summary>Q11. [Advanced] How do you migrate pipelines from one CI/CD tool to another?</summary>

**Answer:**

I inventory triggers, stages, runners, plugins, variables, secrets, artifacts, approvals, schedules, retention rules, and integrations. I separate the portable scripts from tool-specific syntax and map each control to the target platform.

I build one representative pipeline first, migrate secrets securely, recreate the protected environments and identities, then run the old and new pipelines in parallel — without letting both deploy to production. I compare artifact checksums, test results, duration, permissions, and audit evidence between them.

Cutover happens in a freeze or change window, with owner communication, a rollback plan to the old pipeline, and monitoring. I only decommission the old credentials and runners after things have run stably and any retention requirements are met.

</details>

<details><summary>Q12. [Intermediate] Walk me through your CI/CD pipeline. <em>(asked in interview round)</em></summary>

**Answer:**

My pipeline follows **build once, deploy many**: every commit is built, tested and scanned once, the artifact is an immutable container image, and that same image is promoted through dev, staging and production using GitOps.

**Pipeline flow:**

```text
Developer -> feature branch -> Pull Request
        |
        v
PR checks (required): build, unit tests, lint, SonarQube quality gate,
                      dependency/secret scan, terraform plan (if infra)
        |
        v
Merge to main
        |
        v
CI: build -> tests -> SonarQube -> Docker build -> Trivy scan
    -> push image to ECR (tag = git SHA) -> sign / SBOM
        |
        v
Update Helm values in GitOps repo (dev) -> Argo CD sync -> EKS dev
        |
        v
Automated integration / smoke tests
        |
        v
Promote same image tag to staging -> tests -> manual approval
        |
        v
Production: canary or blue/green (Argo Rollouts) -> monitor -> full rollout
        |
        v
Rollback: revert GitOps commit / Argo Rollouts abort
```

**Example (GitHub Actions excerpt):**

```yaml
name: ci
on:
  push:
    branches: [main]
permissions:
  id-token: write     # OIDC to AWS, no long-lived keys
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
      - run: mvn -B verify sonar:sonar -Dsonar.qualitygate.wait=true
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::111122223333:role/github-ci
          aws-region: us-east-1
      - id: ecr
        uses: aws-actions/amazon-ecr-login@v2
      - run: docker build -t ${{ steps.ecr.outputs.registry }}/orders:${{ github.sha }} .
      - run: |
          trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed \
            ${{ steps.ecr.outputs.registry }}/orders:${{ github.sha }}
      - run: docker push ${{ steps.ecr.outputs.registry }}/orders:${{ github.sha }}
```

A follow-up job (or a tool like Argo CD Image Updater) updates the image tag in the GitOps repository, and Argo CD deploys it.

**Important points:**

- Immutable tags (git SHA), never `latest`, so the exact image is traceable and rollback is a tag change.
- OIDC federation instead of stored cloud keys; secrets in Secrets Manager/External Secrets.
- Separate approvals and environments for production; audit trail via Git history.
- Post-deployment verification with metrics and automatic rollback on error-rate increase.

See also: [CI/CD flow](../repetitive-questions/cicd-flow.md), [Pipeline design and scripting](../ci-cd/02-pipeline-design-and-scripting.md), [Deployment strategies and rollback](../ci-cd/04-deployment-strategies-and-rollback.md).

**Interview-ready answer:**

> "Developers work on short-lived feature branches and open a pull request, where required checks run: build, unit tests, linting, the SonarQube quality gate and dependency and secret scanning. After merge to main, the pipeline builds the app, runs tests, builds the Docker image, scans it with Trivy and pushes it to ECR tagged with the commit SHA, authenticating to AWS with OIDC instead of stored keys. Deployment is GitOps: the pipeline updates the image tag in the Helm values of the environment repository and Argo CD syncs it to EKS. The same image moves from dev to staging and, after tests and an approval, to production using a canary rollout. If metrics degrade, we roll back by reverting the GitOps commit or aborting the rollout."

</details>

<details><summary>Q13. [Intermediate] Explain your actual CI/CD work: commit, build, test, security scan, image push and Kubernetes deployment. <em>(asked in interview round)</em></summary>

**Answer:**

My pipeline follows a "build once, deploy many" model. GitHub Actions builds and tests the code, scans the image, pushes it to Amazon ECR using short-lived credentials from GitHub OIDC, and then updates the Helm values in a GitOps repository. Argo CD running in EKS syncs the change into the cluster. No long-lived AWS keys are stored in GitHub.

**End-to-end flow:**

```text
Developer push / pull request
        |
        v
GitHub Actions (CI)
  |-- checkout, lint, unit tests
  |-- SAST / dependency scan
  |-- docker build (tag = git SHA)
  |-- Trivy image scan (fail on HIGH / CRITICAL)
  |-- OIDC --> assume IAM role --> login to ECR --> push image
  |-- update image tag in GitOps repo (Helm values) / open PR for prod
        v
Argo CD (CD, inside EKS)
  |-- detects the Git change --> helm template --> applies to cluster
  |-- rolling update or Argo Rollouts canary
  |-- health checks; auto rollback by reverting Git
        v
Prometheus / Grafana verify error rate and latency
```

**Example: GitHub Actions workflow:**

```yaml
name: build-and-deploy

on:
  push:
    branches: [main]

permissions:
  id-token: write     # required for OIDC
  contents: read

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: orders-api

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Unit tests
        run: |
          pip install -r requirements.txt
          pytest -q

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-ecr-push
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build image
        run: |
          docker build -t ${{ steps.ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }} .

      - name: Trivy scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ steps.ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          ignore-unfixed: true
          exit-code: "1"

      - name: Push image
        run: docker push ${{ steps.ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}

  update-gitops:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: my-org/gitops-config
          token: ${{ secrets.GITOPS_TOKEN }}
      - name: Bump image tag for dev
        run: |
          yq -i '.image.tag = "${{ github.sha }}"' apps/orders-api/values-dev.yaml
          git config user.name "ci-bot"
          git config user.email "ci-bot@users.noreply.github.com"
          git commit -am "orders-api: deploy ${{ github.sha }} to dev"
          git push
```

The IAM role trust policy allows only this repository and branch:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
    "StringLike": { "token.actions.githubusercontent.com:sub": "repo:my-org/orders-api:ref:refs/heads/main" }
  }
}
```

**Promotion to production:**

- The same image digest is promoted from dev to staging to prod; only Helm values change.
- Production changes go through a pull request on the GitOps repo with approval, or a GitHub Environment with required reviewers.
- Rollback: revert the Git commit, and Argo CD syncs the previous tag.

**Important points:**

- OIDC removes static AWS keys; scope the trust policy `sub` claim to the repository and branch or environment.
- Tag images with the Git SHA (immutable tags enabled in ECR), never only `latest`.
- Pin third-party actions to a release or commit SHA.
- Enable ECR scan on push as a second layer and sign images (for example with `cosign`) if required.

See also: [GitHub Actions end-to-end pipelines and security](../github-actions/03-end-to-end-pipelines-security-and-troubleshooting.md) and [CI/CD pipeline design](../ci-cd/02-pipeline-design-and-scripting.md).

**Interview-ready answer:**

> "When a developer pushes to main, GitHub Actions runs linting and unit tests, builds the Docker image tagged with the Git SHA and scans it with Trivy, failing the build on critical or high vulnerabilities. The workflow authenticates to AWS with GitHub OIDC, assuming an IAM role that trusts only our repository and branch, so there are no stored access keys. It logs in to ECR and pushes the image, then updates the image tag in our GitOps repository. Argo CD in EKS detects the change and deploys the Helm chart with a rolling update or a canary. Production promotion uses the same image through an approved pull request, and rollback is a Git revert."

</details>

<details><summary>Q14. [Advanced] How do you design a CI/CD pipeline for microservices running in Kubernetes? <em>(asked in interview round)</em></summary>

**Answer:**

Each microservice gets its own pipeline triggered by changes to its own path or repository, so one service can ship without rebuilding the others. CI produces one immutable, signed image per commit; CD promotes that same image through environments, ideally through GitOps.

| Stage | What happens |
| --- | --- |
| Build and test | Lint, unit tests, SAST, dependency scan |
| Package | Multi-stage Docker build, tag with the Git SHA, generate SBOM, sign |
| Publish | Push to a private registry (ECR, ACR, Artifactory) |
| Deploy | Update the Helm values or Kustomize overlay in a GitOps repo; Argo CD or Flux syncs |
| Verify | Smoke tests, canary analysis, automatic rollback on failed health checks |

```yaml
# GitHub Actions: build only when this service changes
on:
  push:
    branches: [main]
    paths: ["services/orders/**"]
```

**Interview-ready answer:**

> I give every microservice an independent pipeline triggered by path filters, so teams release on their own cadence. CI builds one immutable image tagged with the commit SHA, scans and signs it, and pushes it to a private registry. CD never rebuilds; it promotes the same digest by updating a GitOps repo that Argo CD syncs to each cluster. Production uses canary or blue/green with health-based automatic rollback, and approvals sit in front of the production promotion.

See also: [CI/CD pipeline for microservices on Kubernetes](../ci-cd/02-pipeline-design-and-scripting.md), [GitOps fundamentals](../gitops/01-gitops-fundamentals.md)

</details>
