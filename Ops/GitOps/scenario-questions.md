## 1. How do you implement GitOps for both apps and infra while preventing config drift?

**Answer:** Keep declarative manifests and Helm charts in Git; use ArgoCD/Flux to auto-sync clusters; set automated drift detection and auto-revert policies; require PRs for changes and enforce branch protections.

Mini-case: After a manual hotfix caused drift in prod, ArgoCD alerted and auto-reverted to Git state; we then applied the change via PR so the fix was auditable.
**Detailed interview approach:**
Git holds reviewed desired configuration and immutable (not changed after creation) versions; Argo CD or Flux continuously compares and reconciles (makes actual state match desired state) it.

I separate environment permissions/repositories, require branch protection and policy/security checks, and give the controller only the cluster scope it needs.

A manual emergency change may temporarily stop sync, but is immediately captured through a pull request; otherwise reconciliation (making actual state match desired state) will correctly remove it. Rollback is a Git revert to the last known-good commit, followed by sync and health/SLO verification.

Secrets use an external secret or encrypted-secret workflow, not plaintext Git. Sync failures, drift, controller access, and audit events are monitored, and destructive pruning has explicit safeguards.

## 2. How do you implement GitOps rollback?

**Answer:** Revert commit in Git → ArgoCD/Flux auto-syncs cluster back → Ensures declarative rollback.

**Detailed interview approach:**
I use a Deployment strategy with realistic readiness/startup probes, graceful shutdown, and enough capacity. `maxUnavailable` and `maxSurge` are selected from the replica count and availability target; setting zero unavailable is useful only when the cluster can host the surge.

I deploy an immutable (not changed after creation) image digest, watch `kubectl rollout status`, Pod events, error rate, latency, and business checks, and pause if the new ReplicaSet is unhealthy. A rollback uses `kubectl rollout undo deployment/<name>` or a Git revert in GitOps, followed by verification.

PodDisruptionBudgets, multiple zones, backward-compatible configuration/database changes, and tested rollback make the update genuinely low-risk.

## 3. How do you implement GitOps in DevOps workflows?

**Answer:** Use ArgoCD/Flux → Keep infra/app configs in Git → Sync automatically with Kubernetes → Rollback by reverting Git commit.

**Detailed interview approach:**
Git holds reviewed desired configuration and immutable (not changed after creation) versions; Argo CD or Flux continuously compares and reconciles (makes actual state match desired state) it.

I separate environment permissions/repositories, require branch protection and policy/security checks, and give the controller only the cluster scope it needs.

A manual emergency change may temporarily stop sync, but is immediately captured through a pull request; otherwise reconciliation (making actual state match desired state) will correctly remove it. Rollback is a Git revert to the last known-good commit, followed by sync and health/SLO verification.

Secrets use an external secret or encrypted-secret workflow, not plaintext Git. Sync failures, drift, controller access, and audit events are monitored, and destructive pruning has explicit safeguards.

