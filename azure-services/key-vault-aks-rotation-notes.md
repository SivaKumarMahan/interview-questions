# Azure Key Vault Secret Rotation for AKS

My preferred design: use the Azure Key Vault provider for the Secrets Store CSI Driver, paired with AKS workload identity. The Pod mounts values straight from Key Vault, and the driver can poll for a new secret version on its own.

This keeps Terraform or a CI pipeline from becoming the long-term owner of rotating secret values — that job stays with Key Vault and the driver.

A few things matter here:

- Give the Kubernetes ServiceAccount and workload identity access to only the specific Key Vault objects they need, nothing broader.
- Use private Key Vault connectivity and DNS where that's required.
- Decide up front whether the application rereads the mounted file on its own, or needs a controlled Pod restart to pick up the change.
- Watch for mount and rotation errors, and actually test a rotation with both the old and new application connections still active.
- If you also sync the value into a Kubernetes Secret, remember that's another stored copy of the data. It needs its own encryption, RBAC, audit trail, and rotation handling.

An event-driven alternative: a Key Vault rotation event goes through Event Grid to an Azure Function or automation workflow, which updates the approved target and kicks off a safe rollout.

Whatever runs that workflow needs to be safe to run more than once, scoped to only the access it needs, logged, retried with dead-letter handling for failures, and verified afterward. A scheduled pipeline is simpler to build, but it can leave stale values sitting around until the next run — so don't rely on "runs every three months" as your only answer for a secret that might need to rotate early.

One more thing: Argo CD won't notice a Key Vault version change on its own. Something else — an external-secrets process, or an encrypted desired-state update — has to bring that change into Git or Kubernetes before Argo CD can act on it.
