# Multi-Environment Helm Deployment

One chart version is promoted through Dev, Staging, and Production with separate reviewed values such as `values-dev.yaml`, `values-staging.yaml`, and `values-prod.yaml`. Values contain non-secret environment differences; secrets come from an external secret manager.

The pipeline validates and renders the chart, deploys the same immutable image digest to Dev, runs tests, then promotes the chart/image combination through protected environments and approvals. Each release has a distinct namespace and Helm release name, explicit timeout, history, and post-deployment health check.

```bash
helm lint ./chart
helm template app ./chart -f values-prod.yaml > rendered.yaml
helm upgrade --install app ./chart \
  --namespace app-prod --create-namespace \
  -f values-prod.yaml \
  --set-string image.digest="$IMAGE_DIGEST" \
  --atomic --wait --timeout 10m
```

This prevents overwritten values, manual environment drift, and untraceable releases. Rollback uses the previous known-good image/chart revision only after checking database and external configuration compatibility. GitOps can replace the direct Helm command while keeping the same promotion, policy, and verification principles.

