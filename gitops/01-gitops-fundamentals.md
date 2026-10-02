# GitOps: Fundamentals and Workflows

> Push vs. pull deployment, implementing GitOps for apps and infrastructure, drift prevention, rollback, Terraform with GitOps, and GitOps at scale.

## Key Concepts

### Push-based deployment

In a push model, the CI/CD system logs into the target environment and sends the change directly — for example, by running `helm upgrade` or `kubectl apply` against a Kubernetes cluster.

**Advantages:**

- The pipeline can inject the exact image version it just built.
- Helm deployments and one-off migration steps are straightforward.
- Secrets can stay in the CI/CD secret store instead of Git.

**Trade-offs:**

- The CI/CD system needs network access and write permission to the cluster.
- Cluster credentials and configuration become part of the delivery system's security boundary.
- Deployment behavior is tied to how the pipeline is written.

I secure this model with short-lived workload identity, a deployment `ServiceAccount` that has only the access it needs, protected environments, approval and policy gates, artifacts that don't change after they're built, and verification after every deployment.

### Pull-based deployment

In a pull model, an in-cluster GitOps controller such as **Argo CD** or **Flux** reads the desired state from Git and continuously reconciles the cluster to match it — meaning it keeps correcting the live cluster until it looks like what's in Git.

CI builds and publishes an artifact, then updates the desired version in the configuration repository. It never needs direct write access to the cluster.

**Advantages:**

- Git gives you a reviewable desired state and a full deployment history.
- The controller continuously detects and fixes drift on its own.
- External CI systems don't need broad cluster credentials.
- One GitOps platform can manage multiple clusters and tenants with clear repository and project boundaries.

**Trade-offs:**

- Secret delivery needs extra design — something like External Secrets Operator, Vault, SOPS, or Sealed Secrets. Plaintext secrets must never be committed.
- Controller, repository, and multi-tenant permissions need careful isolation.
- A bad commit to the desired state keeps getting reapplied until it's reverted or sync is paused.

### Choosing between push and pull

I choose based on security boundaries, auditability, network reachability, rollback needs, who owns operations, and what the workload actually needs. A common production setup uses CI for build, test, scanning, signing, and publishing the artifact, then GitOps for deployment and correcting drift.

Rollback in GitOps is usually a reviewed Git revert to the last known-good image or configuration, followed by reconciliation and a health check. Any emergency manual change has to be captured back into Git, or the controller will correctly treat it as drift and undo it.

## Interview Questions

### 1. How do you implement GitOps in DevOps workflows? *(scenario)*

**Answer:** Use Argo CD or Flux, keep infra and app configs in Git, sync automatically with Kubernetes, and roll back by reverting the Git commit.

**Detailed interview approach:**
Git holds the reviewed desired configuration, and every version in it stays unchanged once committed. Argo CD or Flux continuously compares that with the live cluster and reconciles any difference — meaning it makes the actual state match Git.

I keep environment permissions and repositories separate, require branch protection and policy/security checks, and give the controller only the cluster scope it actually needs.

A manual emergency change might pause sync temporarily, but it has to be captured back into a pull request right away. Otherwise, the next reconciliation will correctly undo it, since Git is the source of truth. Rollback just means reverting Git to the last known-good commit, then syncing and checking health and SLOs.

Secrets go through an external-secrets or encrypted-secret workflow — never as plaintext in Git. I monitor sync failures, drift, controller access, and audit events, and destructive pruning has explicit safeguards so a deletion in Git can't silently wipe out something important.

### 2. How do you implement GitOps for both apps and infra while preventing config drift? *(scenario)*

**Answer:** Keep declarative manifests and Helm charts in Git, use Argo CD or Flux to auto-sync clusters, set up automated drift detection with auto-revert, and require pull requests plus branch protection for any change.

Mini-case: after a manual hotfix caused drift in production, Argo CD detected it and auto-reverted to the Git state. We then applied the same fix properly through a pull request, so it stayed auditable.
**Detailed interview approach:**
Git holds the reviewed desired configuration, and every version in it stays unchanged once committed. Argo CD or Flux continuously compares that with the live cluster and reconciles any difference — meaning it makes the actual state match Git.

I keep environment permissions and repositories separate, require branch protection and policy/security checks, and give the controller only the cluster scope it actually needs.

A manual emergency change might pause sync temporarily, but it has to be captured back into a pull request right away. Otherwise, the next reconciliation will correctly undo it, since Git is the source of truth. Rollback just means reverting Git to the last known-good commit, then syncing and checking health and SLOs.

Secrets go through an external-secrets or encrypted-secret workflow — never as plaintext in Git. I monitor sync failures, drift, controller access, and audit events, and destructive pruning has explicit safeguards so a deletion in Git can't silently wipe out something important.

### 3. How do you implement GitOps rollback? *(scenario)*

**Answer:** Revert the commit in Git, and Argo CD or Flux automatically syncs the cluster back — that's the whole rollback.

**Detailed interview approach:**
I use a deployment strategy with realistic readiness and startup probes, graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and availability target — setting zero unavailable only makes sense if the cluster can actually host the extra surge capacity.

I deploy a specific image digest that won't change underneath me, watch `kubectl rollout status`, pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. To roll back, I use `kubectl rollout undo deployment/<name>`, or in GitOps, a Git revert — then I verify it worked.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible config and database changes, and a tested rollback path are what make the update genuinely low-risk.
### 4. How do you run a GitOps workflow with Terraform?

#### The idea

Git is the source of truth. Nothing is applied by hand.

#### Flow

```text
Pull request  -> plan + checks, posted for review
Merge to main -> apply with approval
Nightly job   -> drift plan, alert if the cloud differs from Git
```

#### GitHub Actions example

```yaml
name: terraform

on:
  pull_request:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - uses: hashicorp/setup-terraform@v3

      - run: terraform init
      - run: terraform plan -out=tfplan

      - name: Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply tfplan
```

#### Drift job

```bash
terraform plan -detailed-exitcode || \
  gh issue create --title "Infrastructure drift detected"
```

#### Tools

Atlantis and Spacelift do this pull-request workflow for you, including plan comments and approval before apply.

#### Interview answer

"Git holds the desired state and nothing is applied by hand. A pull request triggers plan and policy checks and posts the result for review, and merging to main triggers the apply with approval. A nightly drift job compares reality with Git and opens an issue if they differ. Tools like Atlantis or Spacelift give this workflow out of the box with plan comments and approvals."

### 5. How would you design a GitOps workflow for more than 20 teams with independent release cycles?

**Answer:**

I separate platform configuration from application delivery. A platform team owns the cluster add-ons, admission policy, namespaces, common charts, and the GitOps controllers themselves.

Each application team owns its own scoped repository or directory. Argo CD Projects, or Flux's own tenancy rules, restrict which repositories, namespaces, clusters, and resource kinds each team can touch, so one team can't alter another team's workloads or the cluster-wide controls.

The flow looks like this: commit, CI tests and scans it, it becomes an immutable signed image, a pull request updates the digest or chart version, policy and the owner review it, GitOps reconciles the cluster, and then progressive health checks confirm it's actually working.

Teams release independently within their own application boundaries. Promotion just moves the same tested artifact forward instead of rebuilding it for each environment.

ApplicationSets, or generated configuration, cut down on repetition without collapsing everything into one giant shared values file.

I add branch protection, CODEOWNERS, schema and policy tests, external secret references, sync ordering for dependencies, safe pruning, and rollback through a Git revert. Dashboards track sync health, drift, controller permissions, rollout SLOs, and how long reconciliation actually takes.

Break-glass changes are time-limited and get captured back into Git immediately.
