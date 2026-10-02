# CI/CD: Environments, Promotion, and Approvals

> Multi-environment pipelines, configuration consistency and drift, promoting builds between environments, and release approvals.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you build a Jenkins pipeline for multi-environment deployment?</summary>

**Answer:**

I build the artifact once, publish it, and keep it immutable. Environment configuration lives outside the artifact and gets parameterized in. Stages are: checkout, test, scan, publish, deploy and test to dev, approve and test in staging, then approve and deploy to production.

Environment credentials and values stay separate from each other and are protected. Shared pipeline libraries hold the common logic, while each application repo just supplies its own version and config. Production deploys the exact same digest that was already tested in staging.

I use environment locks, concurrency limits, timeouts, smoke tests, monitoring, and rollback to the previous artifact. Database changes follow the expand/migrate/contract pattern so they stay backward compatible.

If one environment fails, promotion to the next stops, and I keep the evidence and artifacts around for investigation.

</details>

<details><summary>Q2. [Intermediate] How do you implement multi-environment CI/CD while preventing configuration drift?</summary>

**Answer:**

I build one artifact and promote that same digest through Dev, QA, UAT, and Production. Environment differences are explicit, schema-validated values stored in version control or an approved config/secret service — never copied pipeline logic or manually edited servers.

Reusable pipeline templates and infrastructure modules give everyone one shared process, and protected environment files hold only the justified differences.

Infrastructure and application config both go through plan/diff checks, GitOps reconciliation where it fits — meaning the actual state is automatically brought back in line with the desired state — and scheduled drift detection. Production gets stronger approval and credentials, but it never runs a different, untested script.

Secrets are referenced by identity and path, never copied between environments. Database and feature changes stay backward compatible throughout the promotion.

Before deploying, I compare desired state against live state. Afterward, I record the artifact, config commit, infrastructure version, and policy results, and run smoke tests. Break-glass changes expire and have to be reconciled back into code.

This makes drift visible, without pretending every environment has identical capacity or integrations.

</details>

<details><summary>Q3. [Intermediate] How do you ensure consistency between environments (Dev, QA, Prod)? <em>(scenario)</em></summary>

**Answer:** Use Terraform workspaces or separate variable files, use Helm values for Kubernetes, and keep infrastructure-as-code in Git.

**Detailed interview approach:**
I use the same versioned application artifact, pipeline template, Terraform modules, and Helm chart across every environment. Only reviewed configuration, capacity, endpoints, and credentials differ between them. Each environment keeps separate state and identity, and configuration follows a typed, validated schema with defaults.

Promotion moves the same digest forward instead of rebuilding it, and staging mirrors production's topology and integrations closely enough to expose upgrade risk. Scheduled Terraform plans and GitOps reconciliation — meaning the actual state gets automatically brought back in line with the desired state — catch drift.

I compare rendered manifests and plans between stages, run smoke and contract tests, and document any intentional differences. Secrets come from environment-specific vault scopes, never from copied files.

This makes any difference in production explainable instead of accidental.

</details>

<details><summary>Q4. [Intermediate] How do you manage different environments (Dev, QA, Staging, Production) in your application deployment pipeline? <em>(scenario)</em></summary>

**Answer:** Use separate Terraform workspace states per environment, environment-specific `.tfvars` files, dedicated EKS clusters, ArgoCD per environment, and separate prod and non-prod AWS accounts.

**Detailed interview approach:**
I manage environments with Terraform, using separate workspace states for each one.

The `/terraform` directory has environment-specific `.tfvars` files — `dev.tfvars`, `staging.tfvars`, `prod.tfvars` — and each environment gets its own dedicated EKS cluster, provisioned through Terraform.

For application deployments, ArgoCD uses environment-specific application manifests stored in Git, and GitHub Actions workflows trigger the right Terraform workspace based on the branch.

Production and non-production live in separate AWS accounts for strong isolation, with Terraform managing cross-account access where it's needed.

</details>

<details><summary>Q5. [Intermediate] How do you ensure that configurations are appropriately handled across environments? <em>(scenario)</em></summary>

**Answer:** Combine Terraform variables with Kubernetes ConfigMaps and Secrets, use environment-specific `.tfvars` and Helm values files, store secrets in Vault and inject them at deploy time, and let ArgoCD enforce the desired state.

**Detailed interview approach:**
I combine Terraform variables with Kubernetes ConfigMaps and Secrets. Each environment has its own `.tfvars` file defining its infrastructure parameters.

For Kubernetes, I keep base Helm charts with environment-specific values files in the GitOps repo.

Sensitive configuration lives in HashiCorp Vault and gets injected at deploy time through the Vault Kubernetes integration. GitHub Actions validates configuration syntax before applying it, and ArgoCD makes sure the deployed configuration matches what's in Git.

Terraform outputs expose the infrastructure values that applications need, and ArgoCD consumes those during deployment.

</details>

<details><summary>Q6. [Intermediate] What strategies do you use to promote code from one environment to another? <em>(scenario)</em></summary>

**Answer:** Use branch-based promotion — `feature/*` goes to dev, `develop` goes to staging, `main` goes to prod. Build one SHA-tagged image and promote that exact image everywhere. Use ArgoCD application sets, protected-branch approvals, and a manual sync step for production.

**Detailed interview approach:**
I follow a Git branching strategy: `feature/*` branches deploy to dev, `develop` deploys to staging, and `main` deploys to production. GitHub Actions workflows trigger based on these branch patterns.

Every build creates one container image tagged with the Git SHA. That exact image gets promoted across environments — it's never rebuilt.

ArgoCD is set up with environment-specific application sets that deploy these images, based on environment variables defined in overlays.

Merges to protected branches require approval in GitHub, and ArgoCD sync for production requires manual approval through RBAC policies.

</details>

<details><summary>Q7. [Intermediate] How do you implement release approvals in CI/CD? <em>(scenario)</em></summary>

**Answer:** Use a Jenkins input step or Azure DevOps approval gates, and require manager or lead approval before deploying to production.

**Detailed interview approach:**
I place the approval step after the automated build, test, security, policy, and deployment-plan checks, so the approver sees the exact artifact, commit, target environment, risk, evidence, and rollback plan — and that artifact never changes once built.

In Jenkins, this is often a protected `input` step with a timeout and a named approver group. Enterprise change records can be verified through an API too.

The same build gets promoted rather than rebuilt. Production credentials only become available after approval, and separation of duties stops the author from approving their own high-risk change.

Approval, rejection, identity, timestamp, and deployment result all get retained. Any emergency bypass is limited, audited, and followed by a review.

</details>

<details><summary>Q8. [Basic] Is it acceptable to deploy a critical banking application directly to production without automated testing because the developer is confident and time is limited? (True or False)</summary>

**Answer:**

False. Confidence isn't evidence, and time pressure actually increases the need for controlled risk, not less.

A critical banking change needs traceability, separation of duties, security and regulatory controls, repeatable tests, an approved artifact, a rollback plan, and post-deployment verification. Deploying untested code directly can cause financial loss, data-integrity problems, security exposure, and a change nobody can audit afterward.

For a genuine emergency, I'd use an approved break-glass process instead: define the incident and the smallest safe change, get it peer-reviewed, run the fastest relevant automated checks, back up affected state, deploy it as a canary or in a tightly scoped way, prepare the rollback, record who authorized it, and monitor real business transactions.

Any lower-priority tests that got skipped run immediately afterward, and the emergency path itself gets reviewed.

Emergency governance can move faster — but it's still governance, not the absence of it.

</details>
