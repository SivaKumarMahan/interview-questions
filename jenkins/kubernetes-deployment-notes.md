# Jenkins Deployment to Kubernetes

```text
Git push/webhook → Jenkins checkout → test and security gates
→ build one image (built once, never changed afterward) → scan/sign/push to registry
→ update Helm/GitOps desired state → rollout → smoke/SLO checks
→ promote or roll back → notify
```

The Jenkinsfile lives with the application code, and each build runs on a fresh, versioned agent that is thrown away afterward. Jenkins reaches the registry and the cluster using scoped credentials or a workload identity, never by hardcoding secrets into commands or letting them show up in logs.

Production deploys are locked down: only certain branches can trigger one, they go through the right environment, they need approval, and only a trusted, scanned artifact is allowed through.

For a direct Helm deployment, Jenkins takes the exact image digest that was built and tested, passes it into a reviewed Helm chart, and runs `helm upgrade --install --atomic --wait --timeout ...`. It then confirms the rollout with `kubectl rollout status` and runs an application smoke test.

With GitOps, Jenkins doesn't touch the cluster directly. It publishes the image and then opens or commits a change that updates the desired state in Git. Argo CD or Flux picks that up and reconciles the cluster, meaning it makes the live cluster match what Git says it should look like.

If a deployment fails, I save the Helm revision, the rendered manifest, the Kubernetes events and logs, and the application metrics before doing anything else. I stop the promotion, roll back to the last known-good artifact or revision, and confirm the rollback actually recovered the service. Only then do I dig into whether the real cause was the pipeline, the chart, a health probe, capacity, a permission, or the application itself — and fix that before retrying.
