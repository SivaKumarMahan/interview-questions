# Repetitive Interview Questions

## What branching strategy do you follow, and how does it ensure safe Production deployments?

### Detailed answer

In my project, we follow **trunk-based development with short-lived feature branches**. The protected `main` branch is our single source of truth and must always remain releasable. We do not maintain long-lived `dev`, `qa` and `prod` code branches because those branches eventually diverge and make it difficult to confirm which code is running in each environment.

Our basic flow is:

```text
work item
-> short-lived feature/* or bugfix/* branch
-> pull request
-> review + CI quality/security gates
-> protected main branch
-> build one immutable artifact
-> deploy to Dev
-> promote the same artifact to QA/UAT
-> Production approval
-> promote to Production
-> create release tag
```

The branches and references have clear purposes:

| Branch/reference | Purpose | Deployment access |
| --- | --- | --- |
| `main` | Reviewed and releasable source of truth | Can start the controlled release workflow |
| `feature/<work-item>-<description>` | Short-lived feature development | PR validation only |
| `bugfix/<work-item>-<description>` | Normal defect correction | PR validation only |
| `hotfix/<incident>-<description>` | Urgent fix based on the current Production version | Isolated validation, then the normal protected release path |
| `release/<version>` | Optional, temporary stabilization branch when a coordinated release window requires it | QA/UAT only until approved |
| `vX.Y.Z` tag | Immutable marker for an approved Production release | Maps to the released artifact digest |

### 1. Starting development

Every change begins with an approved work item or defect. The developer updates the local `main` branch and creates a short-lived branch:

```bash
git switch main
git pull --ff-only
git switch -c feature/PROJ-123-add-payment-validation
```

The branch should contain one logical change and normally live for hours or a few days, not several weeks. Small branches reduce merge conflicts, make reviews easier and limit the amount of untested code waiting outside `main`.

For incomplete features that must be integrated gradually, we use **feature flags**. The code can be merged while the user-facing behavior remains disabled. Feature flags have an owner and removal date so they do not become permanent technical debt.

### 2. Pull request validation

Developers cannot push directly to `main`. They raise a pull request, and branch protection requires:

- At least the required number of independent reviewers.
- CODEOWNERS review for pipeline, Helm, Terraform, security or other sensitive files.
- Successful compilation and unit/integration tests.
- SonarQube or an approved code-quality gate.
- Secret, dependency, container, IaC and Kubernetes policy scanning.
- Resolution of review comments and merge conflicts.
- A linked work item and meaningful change description where required.
- A current branch; stale approvals are dismissed when important new commits are pushed.

The pull-request pipeline has no Production credentials. Code from an untrusted branch can compile and run tests, but it cannot push an approved release image, change AKS Production, read Production secrets or approve its own deployment.

### 3. Merging safely into `main`

After approval and successful checks, we use a consistent merge policy—normally squash merge for a focused feature or rebase/fast-forward where the organization requires a linear history. We do not mix merge styles without a reason.

The merge records the pull request, work item, reviewers and CI evidence. A final CI pipeline runs against the exact merged commit because the merge result can differ from the source branch that was initially tested.

`main` is protected through:

- No direct push or force-push.
- No branch deletion.
- Required status checks.
- Required reviewers and separation of duties.
- Restricted permission to modify branch policies.
- Signed commits or tags where organizational policy requires them.
- Audit logs and notifications for policy changes or bypasses.

Administrators do not bypass these controls for convenience. Emergency access is time-bound, audited and followed by review.

### 4. Build once and identify the release

When a commit is accepted into `main`, the CI pipeline:

1. Checks out the exact merge commit.
2. Builds and tests the Java application.
3. Produces the versioned JAR.
4. Builds and scans the Docker image.
5. Pushes it to Azure Container Registry.
6. Records the Git commit, image tag and immutable image digest.

For example:

```text
source commit: 8f2c9d1
image tag:     payments:8f2c9d1
image digest:  sha256:<immutable-digest>
```

The digest—not a mutable tag such as `latest`—is the actual release identity. We build the image once and promote the same digest through Dev, QA/UAT and Production. We do not rebuild from separate environment branches, because separate builds could contain different dependencies or base-image content even when the source appears identical.

### 5. Environment promotion

Branches control how code enters the delivery system; **environments are controlled by deployment permissions and approvals**, not by maintaining different copies of the source code.

The promotion flow is:

```text
main commit
-> ACR image digest
-> Dev deployment and automated tests
-> QA deployment and integration/regression tests
-> UAT and business validation
-> authorized Production approval
-> Production deployment and observation
```

Each environment has separate Helm values, Azure identities, RBAC scope, Key Vault access and AKS namespace or cluster boundaries. Configuration changes are reviewed and versioned, but secrets stay in Azure Key Vault and are retrieved through managed identity/workload identity.

The deployment record links:

- Work item and pull request.
- Git commit and release tag.
- Test, quality and security reports.
- ACR image digest.
- Configuration and Helm chart version.
- Environment, approver and deployment time.
- Verification and rollback result.

### 6. Production safety controls

A merge to `main` does not automatically mean uncontrolled Production deployment. Production is protected by several independent controls:

1. **Protected environment:** Only the release pipeline and approved release identities can modify Production.
2. **Approval:** The person who authored the change cannot be the only Production approver.
3. **Artifact promotion:** Production receives the exact digest already tested in lower environments.
4. **Serialized deployment:** Only one pipeline can deploy to Production at a time.
5. **Deployment strategy:** AKS uses a controlled rolling, canary or blue-green rollout based on risk.
6. **Workload readiness:** Multiple replicas, readiness/startup probes, PodDisruptionBudgets, resource capacity and graceful termination protect availability.
7. **Automated verification:** Smoke tests and a real application transaction run after deployment.
8. **Observability gate:** Azure Monitor, Log Analytics, Application Insights, Prometheus and Grafana check errors, latency, saturation, JVM health and business signals.
9. **Rollback:** The previous known-good ACR digest and Helm revision remain available for immediate rollback when safe.
10. **Database safety:** Schema changes use backward-compatible expand/migrate/contract steps because rolling back application code cannot undo a destructive database migration.

After successful Production verification, we create an immutable release tag such as `v2.4.0` on the exact released commit and record its mapping to the ACR digest.

### 7. Optional release branches

For most services, we release directly from protected `main`. If a regulated release requires a longer UAT or change-freeze period, we create a temporary `release/<version>` branch from a known `main` commit.

Only release-blocking fixes are accepted into that branch. Every fix still requires a pull request and full validation, and it is also applied back to `main` so the histories do not diverge. After Production deployment and tagging, the release branch is deleted.

We do not use the release branch to rebuild a different Production image. The exact release-candidate commit produces one immutable image, and the digest that passes QA/UAT is the digest promoted to Production.

### 8. Hotfix workflow

For a critical Production incident:

1. Confirm the current Production tag, commit and ACR digest.
2. Create `hotfix/<incident>-<description>` from that exact source version.
3. Make the smallest safe correction.
4. Run unit, integration, security and regression checks.
5. Require expedited but independent review—never skip review entirely.
6. Build one new immutable image and deploy it to an isolated or representative environment.
7. Promote it through the protected Production workflow with incident/change approval.
8. Verify user recovery and monitoring signals.
9. Merge the correction into `main` so it is not lost from future releases.
10. Create a new patch tag, document the incident and complete the RCA.

If rollback is safer than a code fix, we first restore the previous known-good digest and stabilize the service. We do not make untracked changes directly in Production.

### How this strategy ensures safe Production deployments

This strategy is safe because it combines several controls rather than relying on a branch name:

- Short-lived branches reduce drift and merge risk.
- Pull requests provide peer review and traceability.
- Automated checks prevent known bad changes from entering `main`.
- Protected branches prevent direct or unauthorized changes.
- Untrusted PR pipelines cannot access Production credentials.
- One immutable image is tested and promoted across environments.
- Environment approvals and RBAC separate code merge permission from deployment permission.
- Progressive AKS rollout and health gates limit blast radius.
- Release tags and ACR digests show exactly what is running.
- Monitoring and a tested rollback path protect users after deployment.
- Hotfixes return to `main`, preventing fixes from disappearing in the next release.

### Concise interview version

I follow trunk-based development with short-lived `feature`, `bugfix` and `hotfix` branches. Developers cannot push directly to `main`; every change goes through a pull request with peer review, required tests, SonarQube and security gates. After merge, we build the Java application and Docker image once, push it to Azure Container Registry and record the immutable digest.

We deploy that same digest to AKS in Dev, QA/UAT and Production instead of rebuilding from environment-specific branches. Production has a protected environment, independent approval, serialized deployment, least-privilege Azure identity, rolling or canary rollout, smoke tests, Azure Monitor/Application Insights health gates and rollback to the previous digest. We tag the exact successful Production commit, and any hotfix starts from the Production version and is merged back into `main`. This gives us code review, artifact traceability, separation of duties and a tested recovery path.
