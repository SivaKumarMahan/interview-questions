# Argo CD Cheatcode

## Applications

```bash
argocd login <server> --sso
argocd app list
argocd app get <app>
argocd app diff <app>
argocd app sync <app>
argocd app wait <app> --health --sync
argocd app history <app>
argocd app rollback <app> <history-id>
argocd app delete <app>
argocd repo list
argocd repo add <repo-url> --ssh-private-key-path <protected-key-path>
```

Prefer a reviewed Git revert for auditable rollback and validate application health afterward. Manual sync/rollback should not create long-term divergence from Git.

## Example Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payments
  namespace: argocd
spec:
  project: payments
  source:
    repoURL: ssh://git@example/release-config.git
    targetRevision: main
    path: apps/payments
  destination:
    server: https://kubernetes.default.svc
    namespace: payments
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

Prune can delete live objects removed from Git. Protect repositories, projects, sync windows, critical resources, and production changes.

## Installation reminder

Use the current official installation manifest or Helm chart pinned to an approved version, not an unpinned `stable` URL copied from a screenshot. Configure TLS, SSO/RBAC, repository credentials, backups, network policy, and external access before production use.
