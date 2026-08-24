## 1. Explain Jenkins controller-agent architecture and how it enables distributed builds.

**Answer:**

The Jenkins controller holds the configuration, schedules jobs, evaluates pipelines, manages credentials and plugins, records build history, and hands out work. Agents are the machines that actually run the build steps.

An agent can be a static VM or a container/Pod that gets created just for one job and thrown away afterward.

```text
Git webhook → Jenkins controller → queue → labeled agent
                                   → build/test/scan → artifact registry
```

I label agents by what they can do, and use the pipeline `agent` directive so each workload lands on the right kind of machine. Agents that come from Kubernetes are especially clean: each one starts from an approved image, runs exactly one job, and disappears. That cuts down on configuration drift and stops secrets from lingering on disk.

For security, I don't run builds on the controller itself, I give credentials only the access they need, I isolate agents from each other, restrict network access, keep images and plugins patched, and keep trusted and untrusted workloads apart. I also watch queue length, how busy the executors are, agent connection failures, disk space, and overall controller health.

## 2. How would you build a CI/CD pipeline from scratch with zero downtime and rollback support?

**Answer:**

Before writing any pipeline code, I nail down the basics: where the source comes from, what the artifact is, which environments exist, who approves what, the availability target, whether the database changes are compatible, what counts as healthy, and how far back I can roll back. A representative Jenkinsfile flow looks like this:

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

Zero downtime isn't just pipeline syntax — it needs multiple replicas, readiness and startup probes, enough spare capacity during the rollout, graceful shutdown, database changes that work with both old and new code, and control over traffic. I also run smoke tests and watch error rate and latency as the rollout happens.

For rollback, I go back to the previous artifact or Helm revision — the one already built and tested, never rebuilt. Database changes follow an expand-migrate-contract approach, or fall back to a tested restore plan.

## 3. What does shift-left mean in DevOps?

**Answer:**

Shift-left means running quality, security, compliance, and operability checks earlier in development, while fixes are still cheap. That means local pre-commit checks, unit tests on every pull request, scanning dependencies/secrets/infrastructure code, threat modeling, and checking policy before deployment.

It doesn't mean dumping all the responsibility on developers, though. Platform and security teams still need to provide fast tools, approved templates, clear error messages, and a way to request an exception.

Runtime monitoring, dynamic security testing, patching, and incident response are still necessary — some risks only show up once the system is actually running.

I track how fast feedback comes back, how many defects still escape to production, how many false positives show up, how long fixes take, and how often developers just bypass the check. If a scan takes hours or produces findings nobody can act on, people will ignore it. Good shift-left controls are automated, focused on real risk, and fast.

## 4. How do you integrate SonarQube, Trivy, and Slack in a Jenkins quality pipeline?

**Answer:**

My order is: run tests and get coverage, run the SonarQube scan, check the quality gate, build the image, scan it with Trivy, publish it, then deploy. Slack just reports the result and links to the evidence — it isn't the control itself, the gates before it are.

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

Tokens live in Jenkins credentials, reports get kept, scanner versions are pinned, and any vulnerability exception needs an owner and an expiry date. I test this by deliberately failing the quality gate and confirming it actually blocks the image from being published.

## 5. How do you implement CI/CD approval workflows in Jenkins?

**Answer:**

I automate every objective gate first — tests, scans, policy checks, staging deployment, health checks — and only use `input` for a decision that genuinely needs a human to be accountable for it.

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

The approval screen shows the artifact version, the plan or diff, test results, risk, the change ticket, and the rollback plan. Jenkins authorization restricts who can approve, and production credentials aren't available before the deployment stage runs. Every approval gets logged.

For emergencies, I use a separate break-glass path that's still audited and gets a review afterward. I avoid approvals that just ask someone to click a button without giving them enough information to make a real decision.

## 6. What if a Jenkins controller crashes?

**Answer:**

First I figure out whether it's the process, the host, storage, the database, or the network that failed, and I make sure nobody starts a second, conflicting recovery attempt at the same time.

I save the logs, then restore the controller from a tested `JENKINS_HOME` backup or persistent storage, along with the version-controlled Jenkins Configuration as Code, the plugin version list, and the pipeline definitions.

Artifacts stay safe because they live in an external registry, not on the controller, and agents are disposable anyway. Before I let production deployments run again, I check credentials, plugins, webhooks, agents, the queue, and one non-production pipeline.

Standard Jenkins doesn't normally run as an active-active controller setup. I describe this as backup-and-restore, or a warm standby, with a measured recovery time and recovery point.

To prevent this in the future: monitor controller health, alert on disk space, regularly test that backups actually restore, keep the plugin list small, and keep configuration and pipelines in Git.

## 7. What if a Jenkins agent node goes offline?

**Answer:**

I check whether it's just one agent, or a whole label or pool, that's affected, and whether the jobs running on it are safe to just retry. In Jenkins, I look at the offline reason and the connection log.

On the agent itself, I check the process or container status, CPU/memory/disk, the Java version, DNS and network access to the controller, certificates, credentials, the clock, and workspace permissions.

For Kubernetes agents, I look at Pod events, image pulls, scheduling, resource quotas, the service account, and container logs. I replace an unhealthy agent rather than trying to fix it in place — but I save the evidence first, before replacing it.

I only reconnect once I've actually fixed the cause. I clean up any workspace that might be corrupted, rerun the stages that are safe to run more than once, and confirm the output is correct. Autoscaling, having more than one agent per label, health checks, and agent images that never change after they're built all stop a single bad host from blocking delivery.

## 8. How do you manage Jenkins pipelines as code?

**Answer:**

I keep the `Jenkinsfile` with the application code, so changes go through pull-request review and version history like anything else. Behavior that's common across projects lives in a versioned shared library:

```text
shared-library/
├── vars/
├── src/
└── resources/
```

That keeps the Jenkinsfile itself readable — it just declares the business stages — while the library functions implement the approved build, scan, and deployment patterns. For production, I pin the library to a specific version, test the library code itself, and write migration notes whenever a change would break existing pipelines.

Credentials are referenced by ID and scoped to the smallest block that needs them — never embedded directly in Groovy code. Controller-level settings are managed separately through Jenkins Configuration as Code.

I test pipeline changes in a sandbox or multibranch job first, and require reviewers on any change to the Jenkinsfile or shared library, because that code can reach production credentials.

## 9. Walk through a Jenkins CI/CD workflow you have operated and the stages in its Jenkinsfile.

**Answer:**

A typical multibranch pipeline starts from a reviewed Git change or a webhook.

`Checkout` records the commit. `Validate` runs formatting and linting. `Test` runs unit tests and publishes the reports. `Quality/Security` runs static analysis, dependency, secret, and policy checks. `Build` creates the package and a multi-stage container image. `Publish` pushes the image digest, which never changes after it's built, along with a software bill of materials, to the registry. `Deploy` then promotes that same digest through the lower environments before an approved, gradual rollout to production.
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

Production uses protected credentials, an approval step where required, health and SLO checks, and rollback to the last known-good digest. Shared libraries implement the controls that are common everywhere; the Jenkinsfile itself just shows what's specific to that service.

I keep the commit, test results, scan results, artifact digest, approval record, deployment record, and verification result as evidence for the release.

## 10. What are Jenkins shared libraries, and how do you write and use them safely?

**Answer:**

A shared library is versioned Groovy code and supporting files reused across Jenkinsfiles. Global steps go in `vars/`, classes go in `src/`, supporting files go in `resources/`, and tests live alongside the library.

A pipeline loads a pinned release with `@Library('company-pipeline@v3') _`, or an approved dynamic library configuration, then calls a simple step like `companyBuild()`.

I keep the Jenkinsfile itself readable and avoid burying every business decision inside the library. Library releases follow semantic versioning, go through pull-request review, have unit and pipeline tests, and come with changelogs and migration notes.

Production jobs pin a specific version rather than silently tracking `main`. Parameters get validated, shell arguments are handled safely, and credentials are only bound inside the smallest block that needs them.

Because a trusted library can bypass parts of the Groovy sandbox and reach credentials, I keep ownership and write access to it tightly restricted. I roll out a new version to a few jobs first, watch it, and keep the previous version around in case I need to roll back.

## 11. What is a webhook, and how do you use it in Jenkins pipelines?

**Answer:**

A webhook is an authenticated HTTP notification from GitHub, GitLab, or another system telling Jenkins that something happened — a push, a pull request, and so on. It saves Jenkins from having to constantly poll for changes, and it carries event details, but Jenkins still fetches the repository itself and checks the actual commit before it builds anything.

I set up a multibranch or organization job, register the Jenkins endpoint over HTTPS, check the provider's signature and secret and the event type, and restrict which sources can reach it where that's supported. Pull requests run tests and scans without any production credentials. A protected merge or tag is what's allowed to publish and trigger a deployment.

Branch discovery rules stop an untrusted fork from running trusted code that has access to secrets.

When something breaks, I check the provider's delivery history, DNS/TLS, the reverse proxy, the signature and secret, Jenkins logs, plugin configuration, event filters, and queue capacity. Webhook redelivery needs to be safe to run more than once, so a duplicate event doesn't trigger a duplicate release.

## 12. How do you separate CI and CD pipelines in Jenkins, and what triggers each one?

**Answer:**

CI belongs to the application repository and gets triggered by pull requests and commits. It compiles, tests, scans, builds, and publishes one artifact that never changes after that — it doesn't rebuild separately for each environment.

Once it succeeds, it records the artifact digest and can notify, or update, a deployment repository.

CD is a separate, protected job or a GitOps workflow. It gets triggered by an approved artifact promotion, a change to the deployment repository, a release tag, or a manual production approval — never by an arbitrary developer branch.

It deploys the exact digest it was given, applies the environment's configuration, runs health and business checks, and records or runs the rollback if needed.

Credentials and permissions are kept separate, so CI can never directly touch production.

Splitting things this way lets each pipeline retry and get approved independently without losing track of what happened. I pass digests and metadata between the two, not workspace files, and I can compare both pipelines by commit, artifact digest, change request, and deployment ID.

## 13. A Jenkins pipeline fails although the application works locally. How do you troubleshoot it?

**Answer:**

I find the first stage that actually failed and save its exact console error, test report, agent label, container image, environment, and commit.

Then I compare things that often differ between a laptop and CI: the Java/Node/Python and build-tool versions, lockfiles, case-sensitive file paths, locale and timezone, a clean workspace versus a dirty one, environment variables, credentials, network/proxy/CA trust, resource limits, and any service that's available locally but missing in CI.

I reproduce the failure in the same agent container, running the same non-interactive command, instead of poking at Jenkins settings before I actually understand the failure.

Common causes: uncommitted local files, cached dependencies that hide a real problem, tests that depend on order or timing, a private registry CI can't reach, wrong file permissions, or secrets that are scoped to a different branch.

Any temporary debug output I add has to avoid printing credentials.

Once I find it, I fix the build definition, dependency pinning, test isolation, agent image, or pipeline configuration, rerun from a clean environment, and confirm the same artifact passes every later stage. Hermetic builds, committed lockfiles and wrapper scripts, standardized build images, and being able to run the same CI commands locally all help stop this from happening again.

## 14. Which applications and deployment tools do you pair with Jenkins pipelines?

**Answer:**

I pick tools based on the workload, instead of forcing Jenkins to be the deployment engine for everything. Jenkins can build and test Java/Maven, Node, Python, and .NET services, package them as images that don't change after they're built, and store them in ECR, ACR, JFrog, Nexus, or another approved registry.

For Kubernetes, delivery goes through Helm plus Argo CD or Flux, or a controlled `kubectl` step. Cloud infrastructure uses Terraform. VM configuration uses Ansible. Serverless deployment uses a provider framework or infrastructure-as-code.

Jenkins orchestrates the tests, policy checks, artifact publication, approvals, and promotion. Each tool gets its own identity, scoped to only what it needs, and short-lived.

I pass artifact digests and versioned manifests between stages, then check application health, logs, metrics, and a real transaction. This keeps Jenkins swappable later on, and avoids giant imperative scripts that hide what state the deployment is actually in.

## 15. How do you integrate GitHub Enterprise with Jenkins securely?

**Answer:**

I set the GitHub Enterprise Server URL and trusted CA in Jenkins' GitHub/branch-source integration, then create an organization folder or multibranch pipeline that discovers repositories and pull requests on its own.

GitHub sends signed HTTPS webhooks to Jenkins. Jenkins fetches the exact commit itself and reports the check result back to the pull request.

Repository discovery and event filters stop an arbitrary repository or an untrusted fork from running a privileged job.

For authentication, I use a GitHub App where it's supported, because it gives repository-scoped permissions and short-lived installation tokens. A narrowly scoped service account or deploy key is the fallback.

Secrets live in Jenkins credentials and are only bound for the step that needs them. Production deployment credentials are never available to pull-request jobs. TLS, the proxy/firewall, and host-key trust are all set up explicitly.

I require branch protection and Jenkins status checks, protect changes to the Jenkinsfile and shared library with code owners, and log the webhook, checkout, build, and deployment identity for every run.

When troubleshooting, I check the webhook delivery history and signature, DNS/TLS/proxy, GitHub API rate limits, the app's installation permissions, branch discovery, the Jenkins queue, and commit-status permissions.

## 13. Freestyle job versus Pipeline: what is the difference?

**Answer:**

A Freestyle job is configured mostly through the Jenkins UI. It's fine for a simple, one-off task, but its configuration is harder to review, version, and reuse.

A Pipeline defines every delivery stage as code in a `Jenkinsfile`. That means code review, durable execution, parallel stages, shared libraries, credential binding, approvals, and a repeatable promotion process.

I prefer Declarative Pipeline for normal CI/CD work because its structure and built-in validation are clearer. Scripted Pipeline is more flexible, but it needs a lot more discipline to keep readable.

## 14. What are Jenkins plugins, and how do you manage them safely?

**Answer:**

Plugins extend Jenkins to work with source control, credentials, agents, pipelines, test reports, artifact repositories, cloud provisioning, and notifications.

Every plugin is code that runs inside Jenkins, so it carries real compatibility and supply-chain risk. I only install supported plugins, pin and test versions on a non-production controller first, watch for security advisories, remove plugins nobody uses, back up configuration, and have a plan to restart or roll back.

I try not to install a plugin just because a pipeline could call it — a CLI, an API, or a shared-library integration is often safer and easier to govern.

## 15. Ten Jenkins jobs have nearly the same configuration. How do you manage them?

**Answer:**

I avoid maintaining ten separately-edited UI jobs. If one workflow just varies by environment, component, or target, I replace all of them with a single parameterized Pipeline backed by one versioned `Jenkinsfile`.

For jobs that are genuinely different, I generate them with Job DSL or Jenkins Configuration as Code, and put the shared logic in a reviewed shared library. Multibranch Pipelines make sense when each repository or branch really does own its own pipeline.

Parameters and templates cut down on duplication, but production credentials and permissions still need to stay separate — a generic job should never let an untrusted parameter pick a privileged deployment target.
