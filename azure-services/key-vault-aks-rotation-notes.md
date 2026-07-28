# Azure Key Vault Secret Rotation for AKS

Preferred design: use the Azure Key Vault provider for the Secrets Store CSI Driver with AKS workload identity. The Pod mounts authorized values from Key Vault and the driver can poll for a new secret version.

This avoids making Terraform or a CI pipeline the long-term owner of rotating secret values.

Important details:

- Give the Kubernetes ServiceAccount/workload identity permission to only the required Key Vault objects.
- Use private Key Vault connectivity and DNS where required.
- Decide whether the application rereads the mounted file or requires a controlled Pod restart.
- Monitor mount/rotation errors and test rotation with both old and new application connections.
- If synchronization to a Kubernetes Secret is required, remember it creates another stored copy that needs encryption, RBAC, audit, and rotation handling.

An event-driven alternative uses a Key Vault rotation event through Event Grid to an Azure Function or automation workflow, which updates the approved target and triggers a safe rollout.

It must be idempotent (safe to run more than once), least privilege (only the permissions needed), logged, retried with dead-letter handling, and verified.
A scheduled pipeline is simpler but can leave stale values until the next run and should not be scheduled “every three months” as the only response to a secret that may rotate early.

Argo CD does not automatically observe a Key Vault version change unless an external-secrets or encrypted desired-state process presents that change to Git/Kubernetes.
