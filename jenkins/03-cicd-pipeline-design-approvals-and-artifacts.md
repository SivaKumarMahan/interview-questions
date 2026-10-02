# Jenkins: CI/CD Pipeline Design, Approvals, and Artifacts

> Designing end-to-end pipelines, separating CI from CD, approval gates, and artifact handling.

## Key Concepts

### A Typical End-to-End Pipeline

A well-built pipeline usually does this, in order:

1. Checks out the exact commit.
2. Installs dependencies from a lock file, so builds are repeatable.
3. Builds the application and runs unit and integration tests.
4. Publishes the test reports.
5. Runs code quality, dependency, and image scans, and enforces a quality gate.
6. Builds and signs one artifact. That artifact never changes after it's built — it's built once and reused everywhere.
7. Pushes it to a registry.
8. Promotes that exact same artifact through each environment.

Lower environments like dev and staging usually deploy automatically. Production usually needs a protected approval step, health or SLO checks after deploy, and a rollback plan if something goes wrong.

Shared libraries hold reusable, reviewed pipeline logic, so the `Jenkinsfile` itself stays short and easy to read — it shows what the application does, not how every shared step works internally.

A CI job typically builds, tests, scans, and publishes. A separate CD or GitOps flow then updates the desired image version in Git, and Argo CD deploys it to Kubernetes from there. Prometheus and Grafana watch the result, and alerts go out through whatever notification system the team has approved (Slack, email, etc.).

## Interview Questions

<details><summary>Q1. [Advanced] How would you build a CI/CD pipeline from scratch with zero downtime and rollback support?</summary>

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

</details>

<details><summary>Q2. [Intermediate] How do you separate CI and CD pipelines in Jenkins, and what triggers each one?</summary>

**Answer:**

CI belongs to the application repository and gets triggered by pull requests and commits. It compiles, tests, scans, builds, and publishes one artifact that never changes after that — it doesn't rebuild separately for each environment.

Once it succeeds, it records the artifact digest and can notify, or update, a deployment repository.

CD is a separate, protected job or a GitOps workflow. It gets triggered by an approved artifact promotion, a change to the deployment repository, a release tag, or a manual production approval — never by an arbitrary developer branch.

It deploys the exact digest it was given, applies the environment's configuration, runs health and business checks, and records or runs the rollback if needed.

Credentials and permissions are kept separate, so CI can never directly touch production.

Splitting things this way lets each pipeline retry and get approved independently without losing track of what happened. I pass digests and metadata between the two, not workspace files, and I can compare both pipelines by commit, artifact digest, change request, and deployment ID.

</details>

<details><summary>Q3. [Intermediate] How do you implement CI/CD approval workflows in Jenkins?</summary>

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

</details>

<details><summary>Q4. [Intermediate] How do you implement CI/CD approval workflows in Jenkins? <em>(scenario)</em></summary>

**Answer:** Use Jenkins “input step” for manual approval → Or integrate with Jira/ServiceNow for change approvals before deploying to prod.

**Detailed interview approach:**
I put the approval step after automated build, test, security, policy, and deployment-plan checks have already passed. That way the approver is looking at the exact artifact that was built and never changed since, along with the commit, the target environment, the risk, the evidence, and the rollback plan.

In Jenkins this is usually a protected `input` step with a timeout and a named approver group. Enterprise change records can be checked through an API if needed.

The same build artifact gets promoted through environments — it's never rebuilt along the way. Production credentials only become available after approval, and the person who authored the change is not allowed to approve their own high-risk change.

I keep a record of who approved or rejected it, when, and what the deployment result was. An emergency bypass path exists, but it's limited, audited, and always followed by a review afterward.

</details>

<details><summary>Q5. [Basic] How does Jenkins handle artifacts?</summary>

**A:** Jenkins handles artifacts through its built-in artifact management system. When a build is executed, Jenkins can archive files generated during the build process, such as binaries, reports, or logs.

These archived artifacts are stored on the Jenkins server and can be accessed later for download or further processing.

To archive artifacts in Jenkins, you can use the `Archive the artifacts` post-build action in a freestyle project or the `archiveArtifacts` step in a pipeline. You specify the files to be archived using patterns (e.g., `**/target/*.jar` for Java projects).

In a Jenkins pipeline, you can archive artifacts like this:

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                // Build steps here
            }
        }
    }
    post {
        success {
            archiveArtifacts artifacts: '**/target/*.jar', fingerprint: true
        }
    }
}
```

In this example, after a successful build, Jenkins archives all JAR files located in the target directory. The `fingerprint: true` option enables tracking of the artifact across builds.

You can also retrieve and use these artifacts in subsequent build steps or jobs by using the `Copy Artifacts` plugin or by referencing them directly in your pipeline scripts.

```groovy
pipeline {
  agent any
  stages {
    stage('Build') {
      steps {
        sh 'mvn clean package'
      }
    }
    stage('Archive Artifacts') {
      steps {
        archiveArtifacts artifacts: 'target/*.jar', fingerprint: true
      }
    }
  }
}
```

In this example, after building the project with Maven, the resulting JAR files are archived for future use.

Artifacts are stored under `$JENKINS_HOME/jobs/<job-name>/builds/<build-number>/archive/`
The fingerprint tracks where an artifact came from and which downstream jobs use it.

For scalability, Jenkins can push artifacts to:

- Nexus Repository
- JFrog Artifactory
- AWS S3 / Azure Blob Storage
- Docker Registry (for container images)

Once archived, artifacts can be downloaded from the Jenkins web interface, used in subsequent build steps, or deployed to external repositories. Jenkins also provides plugins for integrating with artifact repositories like Nexus or Artifactory, allowing for more advanced artifact management and distribution.

</details>
