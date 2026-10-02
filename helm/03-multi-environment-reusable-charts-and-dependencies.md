# Helm: Multi-Environment Deployments, Reusable Charts, and Dependencies

> Promoting one chart across environments, shared and umbrella charts, chart repositories and OCI registries, and worked project examples.

## Key Concepts

### Multi-Environment Deployments

Keep one reusable chart and maintain environment-specific value files:

```text
values.yaml
values-dev.yaml
values-stage.yaml
values-prod.yaml
```

```bash
helm upgrade --install app ./chart -f values.yaml -f values-prod.yaml
```

Later values files override earlier ones. Command-line `--set` values have high precedence, but large or important configurations are easier to review in version-controlled values files.

Recommended practices:

- Keep the chart logic common across environments.
- Store only non-secret environment configuration in values files.
- Pin chart, dependency, and container-image versions.
- Promote a tested version instead of editing production independently.
- Run linting, rendering, schema validation, and policy checks in CI.

### Multi-Environment Helm Deployment

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

### Shared Charts for Multiple Microservices

A library or reusable application chart can standardize labels, probes, security contexts, and deployment patterns. Each service supplies its own values.

```yaml
services:
  orders:
    resources:
      requests: { cpu: 200m, memory: 256Mi }
  payments:
    resources:
      requests: { cpu: 500m, memory: 512Mi }
  default:
    resources:
      requests: { cpu: 100m, memory: 128Mi }
```

Avoid one large chart with excessive conditionals when services have very different lifecycles. Separate charts or a library chart can preserve independent ownership and releases.

### Dependencies and Umbrella Charts

An umbrella chart groups multiple child charts as dependencies and provides one entry point for deploying an application stack.

```yaml
# Chart.yaml
apiVersion: v2
name: shop
version: 1.0.0
dependencies:
  - name: frontend
    version: 1.2.0
    repository: file://charts/frontend
  - name: backend
    version: 2.1.0
    repository: file://charts/backend
  - name: postgresql
    version: 15.5.0
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
```

```bash
helm dependency update ./shop
helm dependency build ./shop
```

Umbrella charts provide coordinated versioning and installation. The trade-off is tighter release coupling, so independently deployed microservices may be better managed as separate releases through GitOps.

### Chart Repositories and OCI Registries

Traditional repository commands:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo nginx
helm pull bitnami/nginx
helm package ./mychart
```

Helm can also store charts in OCI-compatible registries:

```bash
helm registry login <registry>
helm push mychart-1.0.0.tgz oci://<registry>/charts
helm pull oci://<registry>/charts/mychart --version 1.0.0
```

### Project Example: Full-stack To-Do application

- Containerize the frontend and backend separately, and publish each one to Azure Container Registry under a fixed image digest that never changes.
- Use one reusable chart, or a small number of clearly separated charts, for Deployments, Services, ConfigMaps, external secrets, probes, resource limits, and Ingress.
- Keep Dev, QA, and Production values separate, while reusing the same chart version across all of them.
- Validate with `helm lint`, `helm template`, and a server-side dry run before running `helm upgrade --install`.
- Use `--atomic --wait --timeout 5m`, then check the rollout status and run a business-level smoke test.
- Roll back to a known Helm revision only after checking that any database or external dependency changes are backward-compatible with it.

### Project Example: Node.js To-Do application

The chart exposes the application through a Service and includes startup/readiness/liveness probes so Kubernetes does not send traffic before the application is ready. A NodePort can be used for learning, but production normally uses Ingress or a LoadBalancer with TLS, authentication, and controlled network exposure.

### Project Example: Jenkins on Kubernetes

Jenkins can be installed from a chart with persistent storage for the controller and ephemeral Kubernetes agents for builds.

PersistentVolume backup, plugin/version pinning, credentials, security context, resource limits, controller recovery, and chart upgrade tests must be planned before treating this as a production installation.

### Project Example: Helmfile

Helmfile coordinates multiple Helm releases and their environment values declaratively. I use it when several related releases need to be installed in a known order, while still pinning chart versions, keeping secrets separate, reviewing rendered changes, and verifying each release.

For keeping a cluster's actual state continuously matched to its desired state across many clusters, a GitOps tool like Argo CD or Flux is often a better fit than running Helmfile by hand.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you handle multi-environment deployments using Helm?</summary>

**Answer:**

I keep one versioned chart and a separate, non-secret values file per environment:

```text
values.yaml
values-dev.yaml
values-stage.yaml
values-prod.yaml
```

CI lints the chart, validates its values against a schema, renders every supported environment, runs Kubernetes schema and policy checks, and packages a fixed chart version.

That same application image and chart version get promoted through dev, staging, and production — only the approved values differ between them. Production requires an approval, uses `--atomic --wait`, runs smoke tests, is monitored, and has a documented rollback path. Secrets are always referenced from outside the chart, never stored in it.

I avoid copying whole charts per environment, because fixes then have to be made in multiple places and drift apart. Where a lot of applications share the same pattern, I use a versioned library or base chart, but still let each service set its own resource limits, probes, and scaling.

</details>
