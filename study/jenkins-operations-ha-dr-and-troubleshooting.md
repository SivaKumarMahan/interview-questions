# Jenkins Operations - HA, DR, and Troubleshooting

Operational Jenkins topics that go beyond writing a pipeline: high availability, disaster recovery, a runbook for the most common failure scenarios, GitHub integration specifics, pipeline optimization techniques, and where a Declarative Pipeline should actually live.

For the AKS deployment pipeline itself (checkout → build → Docker → deploy → approval), see [jenkins-cicd-pipeline-for-aks.md](jenkins-cicd-pipeline-for-aks.md).

## Contents

1. [Jenkins High Availability](#1-jenkins-high-availability)
2. [Jenkins troubleshooting runbook](#2-jenkins-troubleshooting-runbook)
3. [Jenkins Disaster Recovery](#3-jenkins-disaster-recovery)
4. [Jenkins + GitHub integration](#4-jenkins--github-integration)
5. [Jenkins pipeline optimization](#5-jenkins-pipeline-optimization)
6. [Where to write a Declarative Pipeline](#6-where-to-write-a-declarative-pipeline)

---

## 1. Jenkins High Availability

Standard Jenkins does not provide active-active controller clustering like some other clustered platforms. Don't say "run two Jenkins masters against the same `JENKINS_HOME`" - that's not how Jenkins works, and doing it risks corrupting state.

A good Jenkins HA/DR design instead focuses on:

- Reliable Jenkins controller infrastructure
- Durable Jenkins state
- Backups
- Multiple build agents
- Monitoring
- Disaster recovery

```
Users
  |
  v
Load Balancer / DNS
  |
  v
Jenkins Controller
  |
  v
Durable Jenkins storage
  |
  v
Jenkins Agents
```

`JENKINS_HOME` contains all the critical Jenkins state:

```
jobs/
plugins/
credentials/
users/
nodes/
secrets/
config.xml
```

Use durable storage for `JENKINS_HOME` and take regular backups. Do **not** run multiple active controllers against the same `JENKINS_HOME` - only one controller process should own it at a time.

Use multiple agents so a single agent failure doesn't stop builds:

```
Controller
  ├── Agent 1
  ├── Agent 2
  └── Agent 3
```

If one agent fails, Jenkins can schedule builds on another. Combine this with Pipeline as Code (Jenkinsfiles stored in Git) so the pipeline definition itself isn't a single point of failure either.

Monitor:

- Jenkins availability
- CPU/memory
- Disk
- Executor utilization
- Queue length
- Agent availability
- Build failures
- Jenkins logs

**Key interview point:** Jenkins HA is not "multiple active controllers." Think controller resilience + durable state + redundant agents + backup/DR.

---

## 2. Jenkins troubleshooting runbook

### A. Slow Jenkins pipeline

```
Pipeline slow
  |
  v
Check Stage View
  |
  v
Identify slow stage
  |
  v
Check agent availability
  |
  v
Check CPU / Memory / Disk
  |
  v
Check build logs
  |
  v
Check external dependencies
  |
  v
Optimize bottleneck
```

Check each stage in turn - checkout, build, unit tests, Docker build, security scan, deployment - and whether Maven/npm/PyPI/Docker registry/SonarQube performance is the actual bottleneck. Useful commands: `top`, `free -m`, `df -h`, `iostat`.

**Interview answer:** first use Stage View or Blue Ocean to identify the slow stage, then check logs and the agent's CPU/memory/disk/network. Check external dependencies - if repeated dependency downloads are the issue, add caching; if the agent is overloaded, move the build or increase capacity.

### B. Jenkins pipeline stuck in queue

```
Build queued
  |
  v
Check queue reason
  |
  v
Check available agents
  |
  v
Check labels
  |
  v
Check executors
  |
  v
Check agent connectivity
  |
  v
Check resource constraints
```

Common causes: no suitable agent, a required label doesn't exist, matching agents are offline, or all executors are busy.

**Interview answer:** check the queue item's reason, whether a suitable agent is online, whether it has a free executor, and whether the label in the pipeline matches an available agent.

### C. Jenkins job stuck on "Waiting for Executor"

Meaning: Jenkins has no suitable executor available right now.

Check: required label, matching agent, agent online status, free executor.

Fix: add another agent, increase executor count carefully, free stuck builds, correct labels, bring agents online.

**Don't blindly increase executors.** If a VM has 2 CPUs and 4 GB RAM, 10 heavy executors will make builds slower, not faster - executors share the same finite CPU/memory.

### D. Jenkins Out of Memory

First determine *where* the OOM is happening:

- Jenkins controller JVM
- Build agent
- Individual build process

Useful checks:

```bash
ps -ef | grep jenkins
free -m
dmesg | grep -i "out of memory"
```

Look for:

```
java.lang.OutOfMemoryError: Java heap space
java.lang.OutOfMemoryError: Metaspace
```

Common causes: too many concurrent builds, large pipelines, memory-heavy Maven/Gradle builds, large Docker builds, too many plugins, memory leaks, too many executors.

Fix: increase JVM heap appropriately (e.g. `-Xms2g -Xmx4g`), move builds to agents, reduce concurrency, tune build-tool memory, remove unnecessary plugins, restart only as a temporary mitigation.

**Don't just keep increasing heap if the underlying workload is wrong** - that treats the symptom, not the cause.

### E. Jenkins jobs failing randomly

"Random" failures are usually caused by nondeterministic external conditions, not truly random code.

Compare a successful build against a failed one: same agent? same tool version? same dependency versions? same time of day? same environment? same network dependency?

Check: agent disconnects, CPU/memory exhaustion, disk full, Docker registry timeout, Maven repository timeout, Git failures, Azure API timeouts, race conditions, shared workspace/files, shared Docker tags/resources.

Useful: `df -h`, `free -m`, `uptime`, `dmesg`.

**Strong approach:** compare successful and failed builds, identify the common pattern, reproduce the failure, and fix the underlying issue rather than repeatedly rerunning the job and hoping it passes.

### F. Jenkins jobs failing due to missing dependencies

Identify which dependency is missing, e.g.:

```
npm: command not found
mvn: command not found
python: command not found
docker: command not found
```

Check the agent:

```bash
which java
which git
which docker
which python
which mvn
```

Check versions:

```bash
java -version
git --version
docker --version
python --version
mvn --version
```

Common causes: dependency not installed, incorrect `PATH`, wrong tool version, a Jenkins tool-configuration problem, a Docker socket permission issue, or an agent that was recreated without the required tools.

Better long-term solutions: Jenkins tool configuration (auto-install), Docker-based agents, Kubernetes dynamic agents, prebuilt agent images - so "what's installed on this agent" stops being a manual, driftable state.

### G. Jenkins plugin failures

```
Plugin failure
  |
  v
Check Jenkins logs
  |
  v
Identify plugin
  |
  v
Check plugin version
  |
  v
Check dependencies
  |
  v
Check Jenkins/Java compatibility
  |
  v
Rollback/update plugin
  |
  v
Restart Jenkins if required
```

Look for: `Failed Loading Plugin`, `NoSuchMethodError`, `ClassNotFoundException`, `UnsupportedClassVersionError`.

If the failure started after a Jenkins/plugin/Java upgrade, compare against the previous known-good versions. Test plugin upgrades in a non-production Jenkins instance first.

---

## 3. Jenkins Disaster Recovery

DR means that if the Jenkins controller or its infrastructure is lost, Jenkins can be restored quickly enough to continue CI/CD. The core principle: **`JENKINS_HOME` is critical state.**

```
Primary Region
  |
  v
Jenkins Controller
  |
  v
JENKINS_HOME
  ├── Backup Storage
  └── Agents
```

Backup storage can be Azure Blob Storage or another durable external store - do **not** keep the only backup on the Jenkins server itself.

What to back up: job configurations, pipeline configurations (if not already in Git), Jenkins configuration, credentials and secrets, plugin information, user configuration, node/agent configuration, and any other required Jenkins metadata.

Use: automated backups, external storage, a separate-region copy where appropriate, retention policies, immutability where required, and periodic restore testing.

**RPO (Recovery Point Objective)** - how much data loss is acceptable. Example: RPO = 1 hour means the recovery point should be no more than roughly an hour old.

**RTO (Recovery Time Objective)** - how quickly Jenkins needs to be restored. Example: RTO = 2 hours means Jenkins should be back up within 2 hours.

Make Jenkins reproducible so recovery isn't just "restore a tarball": Jenkins Configuration as Code, Terraform/Bicep for the infrastructure, Ansible for host configuration, and Jenkinsfiles in Git for the pipelines themselves.

Recovery flow:

```
Jenkins Primary Failed
  |
  v
Declare DR
  |
  v
Provision new Jenkins infrastructure
  |
  v
Install Jenkins
  |
  v
Restore Jenkins data/configuration
  |
  v
Restore required secrets
  |
  v
Connect agents
  |
  v
Run smoke test
  |
  v
Resume CI/CD
```

Test the DR process periodically - an untested backup is not a verified recovery path.

**HA vs DR:** HA minimizes downtime from an infrastructure failure (agents/controller resilience while things are still mostly working). DR restores Jenkins after a major failure or total loss.

---

## 4. Jenkins + GitHub integration

```
Developer
  |
  v
GitHub Repository
  |
  v
Webhook
  |
  v
Jenkins
  |
  v
Jenkinsfile
  |
  v
Checkout -> Build -> Test -> Scan -> Docker Build
  |
  v
Registry
  |
  v
Deployment
```

**Authenticating to GitHub** - configure repository access in Jenkins using one of:

- GitHub App
- Personal Access Token
- SSH key

For production, a **GitHub App is generally preferable** to a personal developer token because its permissions can be scoped precisely (specific repos, specific permissions) and it isn't tied to one person's account.

**Setting up the job:**

```
Jenkins Dashboard -> New Item -> Pipeline
```

For production:

```
Pipeline
  -> Definition: Pipeline script from SCM
  -> SCM: Git
  -> Repository: <GitHub repository>
  -> Credentials
  -> Branch
  -> Script Path: Jenkinsfile
```

**Multibranch Pipeline** is preferred for real projects - Jenkins automatically discovers branches that contain a Jenkinsfile, so you don't manually create a job per branch.

```
main
develop
feature/login
feature/payment
```

**PR flow:**

```
Developer creates PR
  |
  v
GitHub webhook
  |
  v
Jenkins
  |
  v
Checkout PR
  |
  v
Build
  |
  v
Unit tests
  |
  v
SonarQube/security scan
  |
  v
Result reported to GitHub
  |
  v
Branch protection can require successful checks
```

Branch protection rules in GitHub can require the Jenkins check to pass before a PR is mergeable, turning the pipeline into an actual merge gate rather than just a notification.

**Don't hardcode credentials:**

```groovy
// Bad
sh "docker login -u admin -p MyPassword"
```

Use Jenkins Credentials (or an external secret manager) instead, and reference the credential ID rather than the literal secret.

**Direction matters:**

- **GitHub → Jenkins:** webhooks, source checkout, PR/branch events, build triggering.
- **Jenkins → GitHub:** build status, PR checks, API operations (e.g. posting a commit status).

---

## 5. Jenkins pipeline optimization

Main goals: reduce build time, avoid unnecessary work, use resources efficiently, improve reliability. Always identify the bottleneck first, using Stage View and logs, rather than optimizing blind:

```
Checkout      -> 30 sec
Build         -> 3 min
Unit tests    -> 8 min
SonarQube     -> 2 min
Docker build  -> 10 min
```

**1. Parallel stages** - run independent stages concurrently instead of serially:

```groovy
stage('Validation') {
    parallel {
        stage('Unit Tests') {
            steps {
                sh 'mvn test'
            }
        }
        stage('Security Scan') {
            steps {
                sh './security-scan.sh'
            }
        }
    }
}
```

**2. Caching** - Maven, npm, Python packages, Docker layers. Avoids re-downloading the same dependencies on every build.

**3. Avoid unnecessary builds** based on branch type:

```
Feature branch -> build/test
PR             -> build/test/scan
main           -> full CI/CD/deployment
```

**4. Dedicated/lightweight agents** - don't run builds on the controller itself.

**5. Docker optimization:**

- Multi-stage builds
- Smaller base images where appropriate
- `.dockerignore`
- Layer caching
- BuildKit/build cache

**6. Conditional stages** - skip stages that don't apply to this branch:

```groovy
stage('Deploy Production') {
    when {
        branch 'main'
    }
    steps {
        sh './deploy.sh'
    }
}
```

**7. Optimize Git** - shallow clone, sparse checkout where appropriate, Git mirrors/caching for large repositories:

```bash
git clone --depth 1 <repository>
```

**8. Control executors based on actual CPU/memory.** More executors does not automatically mean better performance - see the OOM/executor-tuning notes above.

**9. Use artifact repositories** such as ACR, Nexus, or Artifactory. Build once and deploy the same artifact to higher environments, rather than rebuilding per environment.

**10. Fail fast** - order stages so cheap/likely-to-fail checks run before expensive ones:

```
Checkout -> Lint -> Unit tests -> Build -> Security scan -> Docker build -> Deploy
```

**11. Clean workspaces carefully:**

```groovy
post {
    always {
        cleanWs()
    }
}
```

Don't destroy useful caches unnecessarily - a workspace clean that also wipes a dependency cache defeats the point of caching in the first place.

**Key five interview points:** parallel execution + caching + conditional stages + optimized agents + Docker optimization.

---

## 6. Where to write a Declarative Pipeline

**Quick/test method** - write it directly in the Jenkins UI:

```
Jenkins Dashboard -> New Item -> Pipeline -> OK
  -> Pipeline -> Definition -> Pipeline script
```

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Building application'
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying application'
            }
        }
    }
}
```

**Recommended real-project approach** - store a `Jenkinsfile` in Git alongside the application:

```
my-application/
├── src/
├── Dockerfile
└── Jenkinsfile
```

Then configure the job to read it from source control:

```
Jenkins Dashboard -> New Item -> Pipeline
  -> Pipeline
  -> Definition: Pipeline script from SCM
  -> SCM: Git
  -> Repository
  -> Credentials
  -> Branch
  -> Script Path: Jenkinsfile
```

**Interview answer:** for a quick test, write it directly as a Pipeline script in the UI. For real projects, use "Pipeline script from SCM" so the Jenkinsfile is version-controlled, reviewable, and travels with the application code.
