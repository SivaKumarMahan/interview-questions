# Jenkins Deployment to Kubernetes

```text
Git push/webhook → Jenkins checkout → test and security gates
→ build one immutable image → scan/sign/push registry
→ update Helm/GitOps desired state → rollout → smoke/SLO checks
→ promote or roll back → notify
```

The Jenkinsfile is stored with the application and uses a versioned ephemeral agent. Registry and cluster/cloud access come from scoped credentials or workload identity; they are not embedded in commands or logs. Production deploy is restricted by branch, environment, approval, and artifact trust.

For a direct Helm deployment, Jenkins passes the immutable image digest into a reviewed chart and runs `helm upgrade --install --atomic --wait --timeout ...`, followed by `kubectl rollout status` and an application smoke test. With GitOps, Jenkins publishes the image and opens or commits a desired-state change while Argo CD or Flux performs the cluster reconciliation.

If deployment fails, I preserve the Helm revision, rendered manifest, Kubernetes Events/logs, and application metrics. I stop promotion, roll back to the previous compatible artifact/revision, verify recovery, and correct the pipeline, chart, probe, capacity, permission, or application cause before retrying.

