# GitOps: Push and Pull Deployment Models

## 1. Push-based deployment

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

## 2. Pull-based deployment

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

## 3. Choosing between them

I choose based on security boundaries, auditability, network reachability, rollback needs, who owns operations, and what the workload actually needs. A common production setup uses CI for build, test, scanning, signing, and publishing the artifact, then GitOps for deployment and correcting drift.

Rollback in GitOps is usually a reviewed Git revert to the last known-good image or configuration, followed by reconciliation and a health check. Any emergency manual change has to be captured back into Git, or the controller will correctly treat it as drift and undo it.

---

## Argo CD Architecture and Workflow

**Argo CD** is a pull-based GitOps continuous-delivery controller for Kubernetes.

It's made up of a few pieces: the API server handles the UI, CLI, authentication, and RBAC; the repository server fetches Git/Helm/Kustomize content and renders the manifests; the application controller compares the desired state with the live state and reconciles any difference; Redis caches state; Dex or an external OIDC provider can add SSO; and `ApplicationSet` generates multiple Applications at once.

An application's sync state is either **Synced** or **OutOfSync**, and its health state is one of **Healthy**, **Progressing**, **Degraded**, **Missing**, **Unknown**, or **Suspended**. Automatic sync can also enable self-heal and pruning, but pruning needs protection — deleting an object from Git will delete it from the cluster too.

Argo CD renders Helm templates itself; it doesn't run releases by calling `helm install` inside the cluster.

The end-to-end flow looks like this: a developer makes a change, CI tests, scans, builds, and signs an image, the registry stores that image (the digest never changes after this point), the reviewed GitOps repository gets its manifests or chart values updated, Argo CD detects the commit, compares it to the live state and syncs, Kubernetes reconciles the difference, and then health and SLOs get verified.

Rollback is either a Git revert or a controlled Argo CD rollback, followed by verification.

Public repositories don't need credentials, but you still want to verify where the content came from. Private repositories should use a scoped deploy key, a GitHub App, or a token stored in Argo CD's protected secret mechanism.
