# Repetitive Interview Questions

## What rollback strategy do you follow if an issue occurs?

**Interviewer:** A Production deployment has caused errors. What rollback strategy do you follow?

**Candidate:**

A rollback means returning the application to the last known working version. My first goal is to stop the impact and restore service safely.

### Confirm the problem

I check whether the errors started after the latest deployment.

```bash
kubectl get pods -n <namespace>
kubectl rollout status deployment/<deployment-name> -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
```

I also check monitoring, user errors, and the deployment time.

### Pause the rollout

If the deployment is still progressing and the new Pods are unhealthy, I pause it:

```bash
kubectl rollout pause deployment/<deployment-name> -n <namespace>
```

This prevents more unhealthy Pods from replacing healthy ones while I investigate.

### Choose rollback or a new fix

I roll back when:

- Users are affected.
- The previous version is known to work.
- A safe fix cannot be tested immediately.

I deploy a new fixed version only when the correction is small, well understood, and fully tested.

### Roll back a Kubernetes Deployment

Check the rollout history:

```bash
kubectl rollout history deployment/<deployment-name> -n <namespace>
```

Roll back to the previous version:

```bash
kubectl rollout undo deployment/<deployment-name> -n <namespace>
```

Or roll back to a specific revision:

```bash
kubectl rollout undo deployment/<deployment-name> \
  --to-revision=<revision> \
  -n <namespace>
```

### Roll back a Helm release

The key Helm commands for deploy, check and rollback:

```bash
# Deploy: install if new, upgrade if it exists
helm upgrade --install orders-api ./helm/orders-api \
  -n production --create-namespace \
  -f values-prod.yaml \
  --set image.tag=1.4.2 \
  --wait --timeout 5m

# Check
helm list -n production
helm status orders-api -n production
helm history orders-api -n production
kubectl rollout status deployment/orders-api -n production
```

Check the Helm revisions:

```bash
helm history <release-name> -n <namespace>
```

```text
REVISION   STATUS       DESCRIPTION
1          superseded   Install complete
2          superseded   Upgrade complete
3          deployed     Upgrade complete   <- broken
```

Restore the last working revision:

```bash
helm rollback <release-name> <revision> -n <namespace>
```

`helm rollback orders-api 2` does not delete revision 3. It creates a new revision 4 with the content of revision 2, so the history stays auditable. Without a revision number, Helm goes back to the previous one.

If the app was deployed with Helm, I roll back with Helm, not with `kubectl rollout undo`. Helm restores the whole release (Deployment, ConfigMap, Service, values). `kubectl rollout undo` only changes the Deployment, and Helm's history then no longer matches the cluster.

I use a known image version such as `orders-api:1.4.1`; I do not rely on the changing `latest` tag.

#### Automatic rollback in the pipeline

```bash
helm upgrade --install orders-api ./helm/orders-api -n production \
  -f values-prod.yaml --set image.tag=$(Build.BuildId) \
  --atomic --timeout 5m
```

`--atomic` waits for the resources to become ready and rolls back by itself if they do not. In Helm 4, this flag is called `--rollback-on-failure`. Before deploying, the pipeline runs `helm lint` and `helm template` so a broken chart never reaches the cluster.

#### Deploy one specific version out of three

First I clarify which "version" is meant, because Helm has three:

| What | Example | Command |
| --- | --- | --- |
| Chart version (in the Helm repo or ACR) | `orders-api` chart `2.0.0` | `helm search repo orders-api --versions`, then `helm upgrade --install orders-api myrepo/orders-api --version 2.0.0 -n production` |
| Application image version | image `orders-api:2.0` | `helm upgrade --install orders-api ./chart --set image.tag=2.0` (or set it in the values file) |
| Earlier release revision on the cluster | revision 2 | `helm history orders-api`, then `helm rollback orders-api 2` |

For a chart stored in ACR as an OCI artifact:

```bash
helm upgrade --install orders-api oci://myacr.azurecr.io/helm/orders-api \
  --version 2.0.0 -n production
```

Remember:

- Chart version is in `Chart.yaml` `version`. App version is the image tag (`appVersion` is only a label).
- Immutable image tags (build ID or Git SHA) make every rollback point to a real image.
- Kubernetes keeps 10 old ReplicaSets by default (`revisionHistoryLimit`), and `helm upgrade` keeps 10 release revisions by default (`--history-max`). Enough history must exist to roll back to the last good version.

### Configuration rollback

If only a ConfigMap, Secret reference, or environment setting changed, I restore the last approved configuration from Git and redeploy it.

```bash
kubectl apply -f <previous-config-file>
```

Secret values are restored from the approved secret manager, not copied from chat messages or local files.

### Database changes

Database rollback needs extra care because removing a column or table can lose data. I prefer backward-compatible changes:

1. Add the new database field.
2. Deploy code that can work with both old and new versions.
3. Move or update the data.
4. Remove the old field only in a later release.

If a database restore is required, I follow the tested backup and restore process and confirm the acceptable data-loss window with the owner.

### Infrastructure changes

For Terraform or Bicep, I revert the code to the last working version and review the plan before applying it.

```bash
terraform plan
terraform apply
```

I do not blindly reverse infrastructure changes because some resources may be deleted or recreated.

#### Terraform apply failed in the middle

Terraform has no automatic rollback. Resources created before the failure stay in Azure and in state. I do not delete everything and start again. I fix the cause and let Terraform continue.

```text
Read the exact error (pipeline log, TF_LOG=INFO if needed)
-> terraform state list / state show: what did Terraform record?
-> az resource show: what really exists in Azure?
-> fix the cause (SKU, quota, permission, name, dependency)
-> terraform plan: only the missing resources should appear
-> terraform apply -> plan again shows "No changes"
```

```bash
terraform state list
terraform state show azurerm_kubernetes_cluster.aks
terraform plan -out=tfplan
terraform apply tfplan
```

Special cases:

- **Resource exists in Azure but not in state.** Apply fails with "already exists". I import it instead of deleting it:

  ```hcl
  import {
    to = azurerm_storage_account.app
    id = "/subscriptions/<sub-id>/resourceGroups/rg-app/providers/Microsoft.Storage/storageAccounts/stapp001"
  }
  ```

  The `import` block (Terraform 1.5+) is reviewed in the plan. `terraform import <address> <id>` also works.
- **Resource is marked `tainted`.** It was created but failed later. The next apply replaces it. I check the plan first, and use `terraform untaint` only if the resource is actually fine.
- **State is locked** after the pipeline agent crashed. I confirm no other run is active, then run `terraform force-unlock <LOCK_ID>`. With the azurerm backend, the lock is a lease on the state blob.

Remember:

- I keep `DEBUG` logs off in CI. They are huge and can contain secrets.
- The state storage account has versioning and soft delete on, so I can restore an old state file if it is damaged.

#### Upgrading the AzureRM provider without breaking infrastructure

A provider upgrade is also a change that needs a rollback plan.

```text
Read the changelog and upgrade guide (breaking changes, removed arguments)
-> pin the new version, branch, terraform init -upgrade
-> commit the updated .terraform.lock.hcl
-> plan in Dev/QA: expect "No changes"; any replace/destroy needs an explanation
-> Production: same reviewed plan, manual approval
```

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.40.0" # example: allow patch updates only
    }
  }
}
```

```bash
terraform init -upgrade
terraform plan -out=tfplan
terraform apply tfplan
```

Remember:

- My rollback is the previous version pin and lock file in Git, plus a backup of the state file.
- Going back to an older provider does not undo infrastructure changes, and an older provider may not read state written by a newer one. So the safe moment to stop is at plan time, before apply.
- `lifecycle { prevent_destroy = true }` on critical resources (databases, Key Vault) blocks an accidental destroy in the plan.

### VM application or dependency updates

On VMs, I prepare the rollback before I update a dependency such as the .NET runtime, Java, IIS or a database driver.

```text
Check the supported version and release notes
-> test in Dev -> QA -> UAT
-> back up: VM snapshot or Azure Backup, config files, keep the old installer
-> change request with impact, downtime and rollback steps
-> update in the maintenance window, one VM at a time behind the load balancer
-> validate: service running, port open, logs, end-to-end test
-> if it fails: reinstall the previous version or restore the snapshot
```

Remember:

- OS patches go through Azure Update Manager. App dependencies go through Ansible, DSC or a pipeline, not manual installs.
- For new VMs, a golden image in Azure Compute Gallery already has the approved versions, so rollback can also mean redeploying the previous image version.

### Verify the rollback

After rollback, I verify:

```bash
kubectl rollout status deployment/<deployment-name> -n <namespace>
kubectl get pods -n <namespace>
kubectl get endpoints -n <namespace>
```

I also test the application through its external URL and confirm that error and latency metrics have returned to normal.

### Example

Suppose version `2.0` causes readiness failures and HTTP 502 errors. Version `1.9` was stable.

I pause the rollout, restore version `1.9`, wait for all Pods to become Ready, test the public API, and monitor it. I then fix and test version `2.0` before trying the deployment again.

### In short

I first confirm that the latest change caused the problem and pause the rollout. I restore the last known working application and configuration, verify the Pods and user request, and continue monitoring.

After recovery, I identify the cause, correct it, and improve tests or alerts so the same issue does not happen again.
