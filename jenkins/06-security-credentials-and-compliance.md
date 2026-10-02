# Jenkins: Security, Credentials, and Compliance

> Shift-left quality and security gates, compliance checks, credential handling, secret masking, and access control.

## Interview Questions

<details><summary>Q1. [Basic] What does shift-left mean in DevOps?</summary>

**Answer:**

Shift-left means running quality, security, compliance, and operability checks earlier in development, while fixes are still cheap. That means local pre-commit checks, unit tests on every pull request, scanning dependencies/secrets/infrastructure code, threat modeling, and checking policy before deployment.

It doesn't mean dumping all the responsibility on developers, though. Platform and security teams still need to provide fast tools, approved templates, clear error messages, and a way to request an exception.

Runtime monitoring, dynamic security testing, patching, and incident response are still necessary — some risks only show up once the system is actually running.

I track how fast feedback comes back, how many defects still escape to production, how many false positives show up, how long fixes take, and how often developers just bypass the check. If a scan takes hours or produces findings nobody can act on, people will ignore it. Good shift-left controls are automated, focused on real risk, and fast.

</details>

<details><summary>Q2. [Intermediate] How do you integrate SonarQube, Trivy, and Slack in a Jenkins quality pipeline?</summary>

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

</details>

<details><summary>Q3. [Intermediate] How do you implement compliance checks in Jenkins? <em>(scenario)</em></summary>

**Answer:** Add compliance scan stage (e.g., Checkov, OPA), fail builds on violations, and generate compliance reports automatically. Mini-case: A Jenkins job blocked deployment because S3 buckets were public — policy-as code ensured compliance.

**Detailed interview approach:**
I protect the whole path from source code to production: branch protection and review, pinned dependency/action/plugin versions, isolated build runners that get thrown away after each job, and short-lived identities that only get the access they need. On top of that I run static analysis, dependency, secret, infrastructure-as-code, and container scans, generate a software bill of materials, and sign artifacts with proof of where they came from and how they were built. Registries are protected, and deployment checks verify all of this before letting anything through.

Each finding has an agreed severity and time limit to fix it, plus a time-limited exception process, so the gates are strict but still usable.

If I suspect something was compromised, I stop any promotion in progress, revoke the runner and signing credentials, isolate the affected artifacts, save evidence for the audit, rebuild from a trusted source and runner, and verify signatures again before deploying anything.

Regular patching, restricting outbound network access, keeping audit logs, and practicing recovery drills cover the things a scanner can't catch on its own.

</details>

<details><summary>Q4. [Intermediate] How do you handle Jenkins credentials securely? <em>(scenario)</em></summary>

**Answer:** Store in Jenkins Credentials Manager → Inject at runtime → Rotate periodically → Integrate with Vault/Key Vault.

**Detailed interview approach:**
I secure the Jenkins UI itself with single sign-on and multi-factor login, role-based authorization, CSRF protection, TLS, and a private controller with patched core and plugins. I never run builds directly on the controller.

Credentials live in the Jenkins credential store or an external vault, scoped to the smallest folder or job that actually needs them. Pipelines pull them in with `withCredentials`, avoid turning on shell tracing, and never paste secrets directly into command lines or build artifacts.

Agents are short-lived, isolated, run as non-root where possible, and get a short-lived cloud identity instead of a long-lived key. If a secret still ends up in a log, masking isn't enough on its own. I treat it as a real exposure: revoke and rotate the secret, restrict or delete the logs that captured it where policy allows, check who accessed it, and fix the step that printed it.

I also back up configuration and plugins regularly, and test that the backups actually restore.

</details>

<details><summary>Q5. [Intermediate] Jenkins Pipeline Security</summary>

#### The pipeline

```groovy
pipeline {
    agent any

    stages {
        stage('Deploy') {
            steps {
                sh '''
                    export DB_PASSWORD="Prod123"
                    ./deploy.sh
                '''
            }
        }
    }
}
```

#### Security issues

1. **Hardcoded credential in the Jenkinsfile** — `Prod123` is in plain text in source control, visible to anyone with repo read access, and preserved forever in git history even if later removed.
2. **Printed in Jenkins console logs** — depending on how `deploy.sh` uses the variable, it can easily end up echoed to the build console, which many users can view.
3. **`agent any`** — runs on any available agent, including potentially untrusted or shared agents, without restricting where sensitive credentials are used.
4. **No credential rotation/central management** — changing the password means editing and redeploying the Jenkinsfile.

#### Secure fix — use Jenkins Credentials

```groovy
pipeline {
    agent any

    environment {
        DB_PASSWORD = credentials('db-password-prod')
    }

    stages {
        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

The secret `db-password-prod` is stored in Jenkins' built-in Credentials store (or backed by a vault plugin), Jenkins automatically masks it in console output, and it's injected as an environment variable at runtime — never written in the Jenkinsfile itself.

#### Short interview answer

"The password is hardcoded directly in the Jenkinsfile, which means it's stored in plain text in version control and could leak into build logs. I'd store it in Jenkins Credentials (or an external vault) and reference it with `credentials('db-password-prod')` in the `environment` block, so Jenkins injects it at runtime and automatically masks it in the console output, instead of it ever appearing in source code."

</details>

<details><summary>Q6. [Intermediate] How do you secure Jenkins pipeline logs containing secrets? <em>(scenario)</em></summary>

**Answer:** Mask credentials with Jenkins plugins → Store secrets in vaults → Disable console echo for sensitive vars.

**Detailed interview approach:**
I secure the Jenkins UI itself with single sign-on and multi-factor login, role-based authorization, CSRF protection, TLS, and a private controller with patched core and plugins. I never run builds directly on the controller.

Credentials live in the Jenkins credential store or an external vault, scoped to the smallest folder or job that actually needs them. Pipelines pull them in with `withCredentials`, avoid turning on shell tracing, and never paste secrets directly into command lines or build artifacts.

Agents are short-lived, isolated, run as non-root where possible, and get a short-lived cloud identity instead of a long-lived key. If a secret still ends up in a log, masking isn't enough on its own. I treat it as a real exposure: revoke and rotate the secret, restrict or delete the logs that captured it where policy allows, check who accessed it, and fix the step that printed it.

I also back up configuration and plugins regularly, and test that the backups actually restore.

</details>

<details><summary>Q7. [Intermediate] How do you secure Jenkins from unauthorized access? <em>(scenario)</em></summary>

**Answer:** Enable RBAC → Integrate with LDAP/SSO → Restrict anonymous access → Enable audit logs → Run Jenkins behind reverse proxy (NGINX).

**Detailed interview approach:**
I secure the Jenkins UI itself with single sign-on and multi-factor login, role-based authorization, CSRF protection, TLS, and a private controller with patched core and plugins. I never run builds directly on the controller.

Credentials live in the Jenkins credential store or an external vault, scoped to the smallest folder or job that actually needs them. Pipelines pull them in with `withCredentials`, avoid turning on shell tracing, and never paste secrets directly into command lines or build artifacts.

Agents are short-lived, isolated, run as non-root where possible, and get a short-lived cloud identity instead of a long-lived key. If a secret still ends up in a log, masking isn't enough on its own. I treat it as a real exposure: revoke and rotate the secret, restrict or delete the logs that captured it where policy allows, check who accessed it, and fix the step that printed it.

I also back up configuration and plugins regularly, and test that the backups actually restore.

</details>
