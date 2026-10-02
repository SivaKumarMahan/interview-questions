# Jenkins: Source Control Integration and Triggers

> Connecting Jenkins to Git and GitHub, webhooks, and how builds get triggered.

## Key Concepts

### Agents and Git Integration

Treat every Jenkins agent as an isolated execution environment. Static agents can connect over SSH. Inbound agents connect using a supported agent protocol with their own authentication.

For untrusted or variable workloads, prefer ephemeral agents that only get the access they actually need, and never run builds on the controller itself. Keep an eye on agent capacity, disk space, workspace cleanup, tool versions, and connection failures.

Git integration needs a narrowly scoped credential or a GitHub App, branch protection, webhook signature validation, and a clearly defined ref to check out. `git pull` fetches changes and merges them in one step. In automation, it's better to run an explicit `fetch` and then a reviewed merge or rebase, so the behavior stays predictable.

A revert adds a new commit that undoes a prior commit. It's generally safer than rewriting history on a shared, protected branch.

## Interview Questions

<details><summary>Q1. [Basic] What is a webhook, and how do you use it in Jenkins pipelines?</summary>

**Answer:**

A webhook is an authenticated HTTP notification from GitHub, GitLab, or another system telling Jenkins that something happened — a push, a pull request, and so on. It saves Jenkins from having to constantly poll for changes, and it carries event details, but Jenkins still fetches the repository itself and checks the actual commit before it builds anything.

I set up a multibranch or organization job, register the Jenkins endpoint over HTTPS, check the provider's signature and secret and the event type, and restrict which sources can reach it where that's supported. Pull requests run tests and scans without any production credentials. A protected merge or tag is what's allowed to publish and trigger a deployment.

Branch discovery rules stop an untrusted fork from running trusted code that has access to secrets.

When something breaks, I check the provider's delivery history, DNS/TLS, the reverse proxy, the signature and secret, Jenkins logs, plugin configuration, event filters, and queue capacity. Webhook redelivery needs to be safe to run more than once, so a duplicate event doesn't trigger a duplicate release.

</details>

<details><summary>Q2. [Intermediate] How do you integrate GitHub Enterprise with Jenkins securely?</summary>

**Answer:**

I set the GitHub Enterprise Server URL and trusted CA in Jenkins' GitHub/branch-source integration, then create an organization folder or multibranch pipeline that discovers repositories and pull requests on its own.

GitHub sends signed HTTPS webhooks to Jenkins. Jenkins fetches the exact commit itself and reports the check result back to the pull request.

Repository discovery and event filters stop an arbitrary repository or an untrusted fork from running a privileged job.

For authentication, I use a GitHub App where it's supported, because it gives repository-scoped permissions and short-lived installation tokens. A narrowly scoped service account or deploy key is the fallback.

Secrets live in Jenkins credentials and are only bound for the step that needs them. Production deployment credentials are never available to pull-request jobs. TLS, the proxy/firewall, and host-key trust are all set up explicitly.

I require branch protection and Jenkins status checks, protect changes to the Jenkinsfile and shared library with code owners, and log the webhook, checkout, build, and deployment identity for every run.

When troubleshooting, I check the webhook delivery history and signature, DNS/TLS/proxy, GitHub API rate limits, the app's installation permissions, branch discovery, the Jenkins queue, and commit-status permissions.

</details>

<details><summary>Q3. [Intermediate] How do you integrate Jenkins with GitHub? <em>(scenario)</em></summary>

**Answer:** Configure GitHub webhook → Connect Jenkins job to repo → Trigger builds automatically on code push/PR.

**Detailed interview approach:**
I keep a declarative `Jenkinsfile` in the application repository, so pipeline changes go through the same review and history as any other code change.

Behavior that's shared and well-tested — checkout, quality checks, security scans, publishing artifacts, deployment, notifications — lives in a versioned Jenkins Shared Library. Each service repository passes in explicit inputs rather than copying Groovy code around.

Multibranch jobs discover branches and pull requests through authenticated GitHub webhooks and report status back to the commit. I pin tool and agent image versions, protect the library and main branches, sandbox untrusted pull requests, and keep GitHub and Jenkins credentials tightly scoped.

I test a shared library upgrade in a sample pipeline before rolling it out by version. I limit manual UI edits and replays, or reconcile them back into Git, so everything stays auditable.

</details>

<details><summary>Q4. [Intermediate] How does Jenkins + GitHub integration work end to end?</summary>

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

</details>
