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

Check the Helm revisions:

```bash
helm history <release-name> -n <namespace>
```

Restore the last working revision:

```bash
helm rollback <release-name> <revision> -n <namespace>
```

I use a known image version such as `orders-api:1.4.1`; I do not rely on the changing `latest` tag.

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
