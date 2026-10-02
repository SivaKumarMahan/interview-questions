# Jenkins: Pipeline as Code and Shared Libraries

> Jenkinsfiles, reusable jobs, shared libraries, post actions, and keeping job configuration out of the UI.

## Key Concepts

### Reusable Jobs, Triggers, and Post Actions

Avoid copying job configuration between jobs in the UI. Use versioned Jenkinsfiles, shared libraries, Job DSL, or Configuration as Code instead. Parameterized or multibranch Pipelines cut down on duplication, while permissions and production credentials still stay specific to each environment.

`$JENKINS_HOME` stores the controller's configuration, build metadata, and plugin data. Back it up regularly and actually test that you can restore it — don't treat it as a place to store build artifacts.

Git webhooks are the preferred way to trigger a build, because they fire on the actual event instead of polling. Validate the webhook signature, use TLS, and restrict who can hit the endpoint. Poll SCM and periodic cron triggers are fallback options — they use up capacity by checking on a schedule instead of reacting to a real push. Jenkins cron has its own syntax, and you should spread jobs out with `H` so they don't all fire at the same minute.

A failed Pipeline can be restarted from a specific stage, but only when that stage is safe to rerun and the artifacts or inputs it needs still exist. This is a convenience, not a substitute for actually designing your deployment to be safe to run more than once.

Declarative Pipeline `post` conditions — `success`, `failure`, `unstable`, `changed`, and `always` — run after the Pipeline or stage finishes. Use them for notifications, publishing reports, and light cleanup. Make sure cleanup doesn't break if an earlier stage never got far enough to create every resource it normally would.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you manage Jenkins pipelines as code?</summary>

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

</details>

<details><summary>Q2. [Basic] Where do you write a Jenkins Declarative Pipeline?</summary>

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

</details>

<details><summary>Q3. [Intermediate] How do you manage Jenkins pipelines as code? <em>(scenario)</em></summary>

**Answer:** Use Jenkinsfile (declarative pipeline) → Store in Git → Version control changes → Reuse shared libraries.

**Detailed interview approach:**
I keep a declarative `Jenkinsfile` in the application repository, so pipeline changes go through the same review and history as any other code change.

Behavior that's shared and well-tested — checkout, quality checks, security scans, publishing artifacts, deployment, notifications — lives in a versioned Jenkins Shared Library. Each service repository passes in explicit inputs rather than copying Groovy code around.

Multibranch jobs discover branches and pull requests through authenticated GitHub webhooks and report status back to the commit. I pin tool and agent image versions, protect the library and main branches, sandbox untrusted pull requests, and keep GitHub and Jenkins credentials tightly scoped.

I test a shared library upgrade in a sample pipeline before rolling it out by version. I limit manual UI edits and replays, or reconcile them back into Git, so everything stays auditable.

</details>

<details><summary>Q4. [Intermediate] Walk through a Jenkins CI/CD workflow you have operated and the stages in its Jenkinsfile.</summary>

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

</details>

<details><summary>Q5. [Basic] Jenkins Declarative Pipeline Missing Structure</summary>

#### The pipeline

```groovy
pipeline {
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }

        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

#### What is missing or incorrect

1. **No `agent` block** — a declarative pipeline requires a top-level `agent` (e.g., `agent any` or a specific label); without it, the pipeline won't even validate/run.
2. **No `post` block** — there's no cleanup, notification, or failure handling (e.g., sending a Slack/email alert on failure, archiving artifacts, cleaning workspace).
3. **No test stage** — going straight from `Build` to `Deploy` skips running automated tests, which is risky for production deployments.
4. **No `options`** — things like `timeout()`, `retry()`, or `disableConcurrentBuilds()` are missing, so a hung build could run forever or two deploys could overlap.
5. **Deploy has no gate/approval** — going straight to deploy after build with no manual approval or environment check is risky for production pipelines.

#### Corrected structure

```groovy
pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }

        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }

        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully'
        }
        failure {
            echo 'Pipeline failed - notifying team'
        }
        always {
            cleanWs()
        }
    }
}
```

#### Short interview answer

"This pipeline is missing the required top-level `agent`, has no test stage before deploying, and has no `post` block for failure notifications or cleanup. I'd add `agent any`, insert a `Test` stage between build and deploy, add `options` like a timeout and `disableConcurrentBuilds`, and add a `post` block to handle success/failure notifications and workspace cleanup."

</details>

<details><summary>Q6. [Intermediate] What are Jenkins shared libraries, and how do you write and use them safely?</summary>

**Answer:**

A shared library is versioned Groovy code and supporting files reused across Jenkinsfiles. Global steps go in `vars/`, classes go in `src/`, supporting files go in `resources/`, and tests live alongside the library.

A pipeline loads a pinned release with `@Library('company-pipeline@v3') _`, or an approved dynamic library configuration, then calls a simple step like `companyBuild()`.

I keep the Jenkinsfile itself readable and avoid burying every business decision inside the library. Library releases follow semantic versioning, go through pull-request review, have unit and pipeline tests, and come with changelogs and migration notes.

Production jobs pin a specific version rather than silently tracking `main`. Parameters get validated, shell arguments are handled safely, and credentials are only bound inside the smallest block that needs them.

Because a trusted library can bypass parts of the Groovy sandbox and reach credentials, I keep ownership and write access to it tightly restricted. I roll out a new version to a few jobs first, watch it, and keep the previous version around in case I need to roll back.

</details>

<details><summary>Q7. [Intermediate] How do you use Jenkins shared libraries? Explain their typical structure and how they are integrated into their Jenkinsfiles?</summary>

In our Jenkins setup, we use **Shared Libraries** to centralize and reuse pipeline logic across multiple projects.
The library is a separate Git repository with a standard structure — `vars/` for global scripts, `src/` for Groovy classes, and `resources/` for templates.
In the `Jenkinsfile`, we import it using `@Library('my-shared-lib')` and call shared steps like `buildApp()` or `deployApp()`.
This ensures consistency, reduces duplication, and makes maintenance easier — if we update a function in the shared library, it's automatically reflected across all pipelines.

**A:** Jenkins Shared Libraries are a powerful way to reuse code across multiple Jenkins pipelines. They allow you to define common functions, classes, and variables in a centralized repository, which can then be imported and used in your Jenkinsfiles.

This promotes code reuse, maintainability, and consistency across your CI/CD pipelines.

#### Typical Structure of Jenkins Shared Libraries

A typical Jenkins Shared Library has the following structure:

```text
(root)
├── vars/
│   ├── myFunction.groovy
│   └── anotherFunction.groovy
├── src/
│   └── com/example/
│       └── MyClass.groovy
├── resources/
│   └── myTemplate.txt
└── README.md
```

1. **`vars/`**: This directory contains global variables and functions that can be called directly from Jenkinsfiles. Each Groovy file in this directory defines a function or variable.
2. **`src/`**: This directory contains Groovy classes organized in packages. You can define more complex logic here, which can be instantiated and used in your Jenkinsfiles.
3. **`resources/`**: This directory contains static resources like templates or configuration files that can be loaded in your shared library code.
4. **`README.md`**: A documentation file that explains how to use the shared library.

#### Integrating Shared Libraries into Jenkinsfiles

To use a Jenkins Shared Library in your Jenkinsfile, you need to declare it at the top of your Jenkinsfile using the `@Library` annotation. Here's how you can do it:

```groovy
@Library('my-shared-library') _  // Import the shared library
pipeline {
    agent any

    stages {
        stage('Example Stage') {
            steps {
                // Call a function from the shared library
                myFunction()

                // Instantiate and use a class from the shared library
                script {
                    def myClassInstance = new com.example.MyClass()
                    myClassInstance.doSomething()
                }
            }
        }
    }
}
```

In this example:

1. The `@Library('my-shared-library') _` line imports the shared library named `'my-shared-library'`.
2. You can then call functions defined in the `vars/` directory directly, such as `myFunction()`.
3. You can also instantiate classes defined in the `src/` directory, like `com.example.MyClass`, and call their methods.

By using Jenkins Shared Libraries, you can streamline your Jenkins pipelines, reduce duplication, and ensure that best practices are consistently applied across your CI/CD processes.

</details>

<details><summary>Q8. [Intermediate] Ten Jenkins jobs have nearly the same configuration. How do you manage them?</summary>

**Answer:**

I avoid maintaining ten separately-edited UI jobs. If one workflow just varies by environment, component, or target, I replace all of them with a single parameterized Pipeline backed by one versioned `Jenkinsfile`.

For jobs that are genuinely different, I generate them with Job DSL or Jenkins Configuration as Code, and put the shared logic in a reviewed shared library. Multibranch Pipelines make sense when each repository or branch really does own its own pipeline.

Parameters and templates cut down on duplication, but production credentials and permissions still need to stay separate — a generic job should never let an untrusted parameter pick a privileged deployment target.

</details>

<details><summary>Q9. [Intermediate] You have 30 CI/CD pipelines and need to add one environment variable to all of them. How do you avoid updating each pipeline manually?</summary>

**Interviewer:** You have 30 CI/CD pipelines and need to add one environment variable to all of them. How would you avoid updating each pipeline manually?

**Candidate:**

I would avoid duplicating the variable across 30 pipelines. I would centralize the configuration.

If I'm using Jenkins, my preferred approach is a Jenkins Shared Library or a centrally managed configuration.

For example, instead of defining:

```groovy
environment {
    APP_ENV = 'production'
}
```

in every Jenkinsfile, I can define the common environment variable in the shared library or global configuration and let all pipelines consume it.

#### 2.1 Jenkins Shared Library approach

I could have a common pipeline function:

```groovy
def call() {
    pipeline {
        agent any

        environment {
            APP_ENV = 'production'
        }

        stages {
            stage('Build') {
                steps {
                    sh 'echo $APP_ENV'
                }
            }
        }
    }
}
```

Then the individual pipelines use the shared library rather than maintaining the common configuration themselves.

#### 2.2 If using Azure DevOps

I would use a Variable Group:

```
Variable Group
      |
30 Pipelines
      |
APP_ENV = production
```

All pipelines reference the same Variable Group. If I change the variable there, all pipelines get the updated value.

#### 2.3 Interview summary

> "I would not update 30 pipelines individually. I would centralize common environment variables. In Jenkins, I would use a Shared Library or centralized Jenkins configuration. In Azure DevOps, I would use a Variable Group. This gives us one place to maintain the variable and prevents configuration drift across pipelines."

</details>
