## 1. Explain Jenkins controller-agent architecture and how it enables distributed builds.

**Answer:**

The Jenkins controller hosts configuration, schedules jobs, evaluates pipelines, manages credentials/plugins, records build metadata, and assigns work. Agents provide executors that actually run build steps.

Agents can be static VMs or ephemeral containers/Pods.

```text
Git webhook → Jenkins controller → queue → labeled agent
                                   → build/test/scan → artifact registry
```

I label agents by capability and use the pipeline `agent` directive so workloads run on the correct platform. Ephemeral Kubernetes agents start from approved images, process one workload, and disappear, reducing configuration drift and secret persistence.

Security measures include no builds on the controller, least-privilege (minimum required access) credentials, agent isolation, restricted network access, patched images/plugins, and separate trusted/untrusted workloads. I monitor queue length, executor use, agent connection failures, disk, and controller health.

## 2. How would you build a CI/CD pipeline from scratch with zero downtime and rollback support?

**Answer:**

I first define the source, artifact, environments, approval, availability target, database compatibility, health signals, and rollback limit. A representative Jenkinsfile flow is:

```groovy
pipeline {
  agent none
  stages {
    stage('CI') {
      parallel {
        stage('Test') { agent { label 'build' }; steps { sh 'npm ci && npm test' } }
        stage('Scan') { agent { label 'security' }; steps { sh 'trivy fs --exit-code 1 .' } }
      }
    }
    stage('Build and publish') {
      agent { label 'docker' }
      steps { sh 'docker build -t registry/app:$GIT_COMMIT . && docker push registry/app:$GIT_COMMIT' }
    }
    stage('Production approval') { steps { input 'Deploy approved artifact?' } }
    stage('Deploy') {
      agent { label 'deploy' }
      steps { sh 'helm upgrade --install app chart --set image.tag=$GIT_COMMIT --atomic --wait' }
    }
  }
}
```

Zero downtime requires multiple replicas, readiness/startup probes, capacity during rollout, graceful shutdown, compatible DB changes, and traffic control—not only pipeline syntax. I run smoke tests and monitor errors/latency.

Rollback uses the previous immutable (not changed after creation) artifact/Helm revision, while database changes use expand-migrate-contract or a tested restoration plan.

## 3. What does shift-left mean in DevOps?

**Answer:**

Shift-left means performing quality, security, compliance, and operability checks earlier in development, when fixes are cheaper. Examples include local pre-commit checks, pull-request unit tests, dependency/secret/IaC scanning, threat modeling, and policy validation before deployment.
It does not mean moving all responsibility to developers. Platform and security teams provide fast tools, approved templates, usable error messages, and an exception process.

Runtime monitoring, DAST, patching, and incident response still remain necessary—some risks appear only in a running system.

I measure feedback time, escaped defects, false positives, fix time, and developer bypasses. A scan that takes hours or produces unactionable findings will be ignored; good shift-left controls are automated, risk-based, and fast.

## 4. How do you integrate SonarQube, Trivy, and Slack in a Jenkins quality pipeline?

**Answer:**

My order is test/coverage → SonarQube scan → quality gate → image build → Trivy scan → publish → deploy. Slack reports result and links to evidence; it is not the control itself.

```groovy
stage('SonarQube') {
  steps {
    withSonarQubeEnv('sonarqube') { sh 'mvn verify sonar:sonar' }
    timeout(time: 10, unit: 'MINUTES') {
      waitForQualityGate abortPipeline: true
    }
  }
}
stage('Image scan') {
  steps { sh 'trivy image --severity HIGH,CRITICAL --exit-code 1 registry/app:$GIT_COMMIT' }
}
post {
  success { slackSend color: 'good', message: "SUCCESS ${env.JOB_NAME} #${env.BUILD_NUMBER} ${env.BUILD_URL}" }
  failure { slackSend color: 'danger', message: "FAILED ${env.JOB_NAME} #${env.BUILD_NUMBER} ${env.BUILD_URL}" }
}
```

Tokens live in Jenkins credentials, reports are retained, scanners are pinned, and vulnerability exceptions require owner/expiry. I test that a deliberately failing quality gate blocks image publication.

## 5. How do you implement CI/CD approval workflows in Jenkins?

**Answer:**

I automate objective gates first—tests, scans, policy, staging deployment, and health checks—then use `input` only for a decision that requires accountable authorization.

```groovy
stage('Production approval') {
  options { timeout(time: 2, unit: 'HOURS') }
  steps {
    input message: 'Promote tested artifact to production?',
          ok: 'Deploy',
          submitter: 'production-approvers'
  }
}
```

The approval displays artifact version, plan/diff, test results, risk, change ticket, and rollback plan. Jenkins authorization restricts approvers, and production credentials are unavailable before the deployment stage. Approval is logged.

For emergencies I use a separate audited break-glass path with post-incident review. I avoid approvals that merely ask someone to click without enough evidence.

## 6. What if a Jenkins controller crashes?

**Answer:**

I first determine whether the process, host, storage, database, or network failed and stop duplicate recovery attempts.

I preserve logs, then restore the controller from tested `JENKINS_HOME` backup/persistent storage plus version-controlled Jenkins Configuration as Code, plugin lock/version list, and pipeline definitions.
Artifacts remain in an external registry, and agents are disposable. I validate credentials, plugins, webhooks, agents, queue, and a non-production pipeline before enabling production deployments.

Standard Jenkins is not normally an active-active controller. I describe the solution as backup/restore or warm standby with a measured RTO/RPO.

Prevention includes controller health monitoring, disk alerts, regular backup restore tests, minimized plugins, and configuration/pipelines in Git.

## 7. What if a Jenkins agent node goes offline?

**Answer:**

I check whether one agent or an entire label/pool is affected and whether jobs are safe to retry. In Jenkins I inspect the offline reason and connection log.

On the agent I check process/container status, CPU/memory/disk, Java version, DNS/network to the controller, certificates, credentials, clock, and workspace permissions.

For Kubernetes agents I inspect Pod events, image pulls, scheduling, resource quota, ServiceAccount, and container logs. I replace an unhealthy ephemeral agent rather than repairing it in place, but preserve evidence first.

I reconnect only after fixing the cause, clean potentially corrupted workspaces, rerun idempotent (safe to run more than once) stages, and verify output. Autoscaling, multiple agents per label, health checks, and immutable (not changed after creation) agent images prevent one host from blocking delivery.

## 8. How do you manage Jenkins pipelines as code?

**Answer:**

I store a `Jenkinsfile` with the application so changes follow pull-request review and version history. Common behavior lives in a versioned shared library:

```text
shared-library/
├── vars/
├── src/
└── resources/
```

The Jenkinsfile remains readable and declares business stages; library functions implement approved build, scan, and deployment patterns. I pin library versions for production, test library code, and provide migration notes for breaking changes.

Credentials are referenced by ID and scoped to the smallest block; they are never embedded in Groovy. Jenkins Configuration as Code manages controller settings separately.

I test pipeline changes in a sandbox/multibranch job and protect Jenkinsfile/shared-library modifications with required reviewers because pipeline code can access delivery credentials.

## 9. Walk through a Jenkins CI/CD workflow you have operated and the stages in its Jenkinsfile.

**Answer:**

A representative multibranch pipeline starts on a reviewed Git change or webhook.

`Checkout` records the commit; `Validate` runs formatting and linting; `Test` runs unit tests and publishes reports; `Quality/Security` runs SAST, dependency, secret, and policy checks; `Build` creates the package and multi-stage container image; `Publish` pushes an immutable (not changed after creation) digest and SBOM to the registry; and `Deploy` promotes that digest through lower environments before an approved progressive production rollout.
```groovy
pipeline {
  agent none
  stages {
    stage('Test') { agent { label 'maven' }; steps { sh 'mvn -B test' } }
    stage('Image') { agent { label 'docker' }; steps { sh 'docker build -t app:${GIT_COMMIT} .' } }
    stage('Deploy') { steps { build job: 'deploy-app', parameters: [string(name: 'VERSION', value: env.GIT_COMMIT)] } }
  }
  post { always { junit allowEmptyResults: true, testResults: '**/surefire-reports/*.xml' } }
}
```

Production uses protected credentials, approval where required, health/SLO checks, and rollback to the last known-good digest. Shared libraries implement common controls; the Jenkinsfile shows service-specific intent.

I retain commit, tests, scans, artifact digest, approval, deployment, and verification as release evidence.

## 10. What are Jenkins shared libraries, and how do you write and use them safely?

**Answer:**

A shared library is versioned Groovy code and resources reused across Jenkinsfiles. Global steps live in `vars/`, classes in `src/`, supporting files in `resources/`, and tests alongside the library.

A pipeline loads a pinned release using `@Library('company-pipeline@v3') _` or an approved dynamic library configuration, then calls a simple step such as `companyBuild()`.

I keep the Jenkinsfile readable and avoid hiding every business decision in the library. Library releases use semantic versions, pull-request review, unit/pipeline tests, changelogs, and migration guidance.

Production jobs pin a version instead of silently following `main`. Parameters are validated, shell arguments are safely handled, and credentials are bound only inside the smallest required block.

Because trusted libraries can bypass parts of the Groovy sandbox and access credentials, ownership and write access are highly restricted. I canary a new version with selected jobs, monitor it, and retain the prior library version for rollback.

## 11. What is a webhook, and how do you use it in Jenkins pipelines?

**Answer:**

A webhook is an authenticated HTTP notification from GitHub, GitLab, or another system that tells Jenkins an event occurred, such as a push or pull request. It avoids constant polling and includes event metadata; Jenkins still fetches the repository and verifies the actual commit before building.
I configure a multibranch or organization job, register the Jenkins endpoint through HTTPS, validate the provider signature/secret and event type, and restrict source access where supported. Pull requests run tests and scans without production credentials; a protected merge or tag can publish and invoke deployment.

Branch discovery rules prevent arbitrary forks from executing trusted code with secrets.

For failures I check provider delivery history/status, DNS/TLS, reverse proxy, signature/secret, Jenkins logs, plugin configuration, event filters, and queue capacity. Webhook redelivery must be idempotent (safe to run more than once) so duplicate events do not duplicate a release.

## 12. How do you separate CI and CD pipelines in Jenkins, and what triggers each one?

**Answer:**

CI is owned by the application repository and triggered by pull requests and commits. It compiles, tests, scans, builds, and publishes an immutable (not changed after creation) artifact, but it does not rebuild for each environment.

On success it records the artifact digest and can notify or update a deployment repository.

CD is a separate protected job or GitOps workflow triggered by an approved artifact promotion, deployment-repository change, release tag, or manual production approval—not by an arbitrary developer branch.

It deploys the supplied digest, applies environment configuration, runs health/business checks, and records or executes rollback.

Credentials and permissions are separated so CI cannot directly change production.

This separation permits independent retries and approvals without losing traceability. I pass immutable (not changed after creation) metadata, not workspace files, and compare both pipelines by commit, artifact digest, change request, and deployment ID.

## 13. A Jenkins pipeline fails although the application works locally. How do you troubleshoot it?

**Answer:**

I identify the first failing stage and preserve its exact console error, test report, agent label, container image, environment, and commit.

I compare Java/Node/Python and build-tool versions, lockfiles, case-sensitive paths, locale/timezone, clean workspace, environment variables, credentials, network/proxy/CA trust, resource limits, and services available locally but missing in CI.
I reproduce in the same agent container with the same noninteractive command rather than changing Jenkins until the failure is understood.

Common causes include uncommitted local files, cached dependencies, tests depending on order/time, unavailable private registries, incorrect file permissions, or secrets scoped to a different branch.

Temporary debug output must not reveal credentials.

I fix the build definition, dependency pinning, test isolation, agent image, or pipeline configuration; rerun from a clean environment; and confirm the same artifact passes subsequent stages. Hermetic builds, committed wrappers/lockfiles, standardized build images, and local CI commands prevent recurrence.

## 14. Which applications and deployment tools do you pair with Jenkins pipelines?

**Answer:**

I choose tools from the workload rather than forcing Jenkins to be the deployment engine. Java/Maven, Node, Python, and .NET services can be built and tested by Jenkins, packaged as immutable (not changed after creation) images, and stored in ECR, ACR, JFrog, Nexus, or another approved registry.

Kubernetes delivery uses Helm plus Argo CD/Flux or a controlled `kubectl` step; cloud infrastructure uses Terraform; VM configuration uses Ansible; serverless deployment uses a provider framework or IaC.

Jenkins orchestrates tests, policy, artifact publication, approvals, and promotion. Tool-specific identities are least privilege (only the permissions needed) and short lived.

I pass artifact digests and versioned manifests between stages, then verify application health, logs, metrics, and a real transaction. This keeps Jenkins replaceable and avoids large imperative scripts that hide deployment state.

## 15. How do you integrate GitHub Enterprise with Jenkins securely?

**Answer:**

I configure the GitHub Enterprise Server URL and trusted CA in the supported Jenkins GitHub/branch-source integration, then create an organization folder or multibranch pipeline that discovers repositories and pull requests.

GitHub sends signed HTTPS webhooks to Jenkins; Jenkins fetches the exact commit and reports checks back to the pull request.

Repository discovery and event filters prevent arbitrary repositories or untrusted forks from running privileged jobs.

Authentication uses a GitHub App where supported because it provides repository-scoped permissions and short-lived installation tokens. A narrowly scoped service identity or deploy key is the fallback.

Secrets live in Jenkins credentials, are bound only for the required step, and production deployment credentials are unavailable to pull-request jobs. TLS, proxy/firewall, and host-key trust are explicitly configured.

I require branch protection and Jenkins status checks, protect Jenkinsfile/shared-library changes with code owners, and log webhook, checkout, build, and deployment identity.

Troubleshooting covers webhook delivery history/signature, DNS/TLS/proxy, GitHub API rate limits, app installation permissions, branch discovery, Jenkins queue, and commit-status permissions.

## 13. Freestyle job versus Pipeline: what is the difference?

**Answer:**

A Freestyle job is configured mainly in the Jenkins UI and is useful for a simple, isolated task, but its configuration is harder to review, version and reuse.

A Pipeline defines delivery stages as code in a `Jenkinsfile`; it supports code review, durable execution, parallelism, shared libraries, credentials binding, approvals and repeatable promotion.

I prefer Declarative Pipeline for conventional CI/CD because its structure and validation are clearer; Scripted Pipeline is more flexible but needs stronger code discipline.

## 14. What are Jenkins plugins, and how do you manage them safely?

**Answer:**

Plugins extend Jenkins for SCM, credentials, agents, pipelines, test reports, artifact repositories, cloud provisioning and notifications.

Each plugin is executable code with compatibility and supply-chain risk, so I install only supported plugins, pin and test versions in a non-production controller, monitor security advisories, remove unused plugins, back up configuration and plan restart/rollback.

I avoid installing a plugin simply because a pipeline can call it; a CLI, API or shared-library integration can be safer and easier to govern.

## 15. Ten Jenkins jobs have nearly the same configuration. How do you manage them?

**Answer:**

I avoid ten independently edited UI jobs. Where one workflow varies only by environment, component or target, I use a single parameterized Pipeline and a versioned `Jenkinsfile`.

For genuinely separate jobs, I generate them with Job DSL or Jenkins Configuration as Code and put shared logic in a reviewed shared library. Multibranch Pipelines are appropriate when each repository or branch owns its own pipeline.

Parameters and templates reduce duplication, but production credentials and permissions must remain separated; a generic job must not let an untrusted parameter choose a privileged deployment target.
