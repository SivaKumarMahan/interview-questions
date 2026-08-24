# Multi-Environment Helm Deployment

The idea is simple: one chart version gets promoted through Dev, Staging, and Production, with a separate, reviewed values file for each — `values-dev.yaml`, `values-staging.yaml`, `values-prod.yaml`. Those files only hold non-secret differences between environments; actual secrets come from an external secret manager.

The pipeline validates and renders the chart, deploys the exact same image build to Dev, runs tests, and only then promotes that same chart-and-image combination through the later environments, each behind its own approval.

Every release gets its own namespace and Helm release name, an explicit timeout, a history you can look back at, and a health check after it deploys.

```bash
helm lint ./chart
helm template app ./chart -f values-prod.yaml > rendered.yaml
helm upgrade --install app ./chart \
  --namespace app-prod --create-namespace \
  -f values-prod.yaml \
  --set-string image.digest="$IMAGE_DIGEST" \
  --atomic --wait --timeout 10m
```

This setup stops values from getting silently overwritten, stops environments from drifting apart, and keeps every release traceable back to what was actually deployed. If a rollback is needed, I go back to the last known-good image and chart combination — but only after checking that the database and any external configuration are still compatible with that older version.

GitOps can replace running the Helm command directly, while keeping the same promotion steps, policy checks, and verification.
