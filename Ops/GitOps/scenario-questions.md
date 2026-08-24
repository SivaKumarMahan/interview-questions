## 1. How do you implement GitOps for both apps and infra while preventing config drift?

**Answer:** Keep declarative manifests and Helm charts in Git, use Argo CD or Flux to auto-sync clusters, set up automated drift detection with auto-revert, and require pull requests plus branch protection for any change.

Mini-case: after a manual hotfix caused drift in production, Argo CD detected it and auto-reverted to the Git state. We then applied the same fix properly through a pull request, so it stayed auditable.
**Detailed interview approach:**
Git holds the reviewed desired configuration, and every version in it stays unchanged once committed. Argo CD or Flux continuously compares that with the live cluster and reconciles any difference — meaning it makes the actual state match Git.

I keep environment permissions and repositories separate, require branch protection and policy/security checks, and give the controller only the cluster scope it actually needs.

A manual emergency change might pause sync temporarily, but it has to be captured back into a pull request right away. Otherwise, the next reconciliation will correctly undo it, since Git is the source of truth. Rollback just means reverting Git to the last known-good commit, then syncing and checking health and SLOs.

Secrets go through an external-secrets or encrypted-secret workflow — never as plaintext in Git. I monitor sync failures, drift, controller access, and audit events, and destructive pruning has explicit safeguards so a deletion in Git can't silently wipe out something important.

## 2. How do you implement GitOps rollback?

**Answer:** Revert the commit in Git, and Argo CD or Flux automatically syncs the cluster back — that's the whole rollback.

**Detailed interview approach:**
I use a deployment strategy with realistic readiness and startup probes, graceful shutdown, and enough spare capacity. I pick `maxUnavailable` and `maxSurge` based on the replica count and availability target — setting zero unavailable only makes sense if the cluster can actually host the extra surge capacity.

I deploy a specific image digest that won't change underneath me, watch `kubectl rollout status`, pod events, error rate, latency, and business checks, and pause if the new ReplicaSet looks unhealthy. To roll back, I use `kubectl rollout undo deployment/<name>`, or in GitOps, a Git revert — then I verify it worked.

PodDisruptionBudgets, spreading across multiple zones, backward-compatible config and database changes, and a tested rollback path are what make the update genuinely low-risk.

## 3. How do you implement GitOps in DevOps workflows?

**Answer:** Use Argo CD or Flux, keep infra and app configs in Git, sync automatically with Kubernetes, and roll back by reverting the Git commit.

**Detailed interview approach:**
Git holds the reviewed desired configuration, and every version in it stays unchanged once committed. Argo CD or Flux continuously compares that with the live cluster and reconciles any difference — meaning it makes the actual state match Git.

I keep environment permissions and repositories separate, require branch protection and policy/security checks, and give the controller only the cluster scope it actually needs.

A manual emergency change might pause sync temporarily, but it has to be captured back into a pull request right away. Otherwise, the next reconciliation will correctly undo it, since Git is the source of truth. Rollback just means reverting Git to the last known-good commit, then syncing and checking health and SLOs.

Secrets go through an external-secrets or encrypted-secret workflow — never as plaintext in Git. I monitor sync failures, drift, controller access, and audit events, and destructive pruning has explicit safeguards so a deletion in Git can't silently wipe out something important.

