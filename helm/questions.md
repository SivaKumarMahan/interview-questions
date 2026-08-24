## 1. What is Helm and how does it simplify Kubernetes deployments?

**Answer:**

Helm is a package manager and release-management tool for Kubernetes. A chart packages up templates, default values, metadata, and dependencies. When you install a chart, Helm renders it into Kubernetes manifests and creates a named "release" whose history it tracks.

Instead of keeping separate copies of Deployment, Service, Ingress, HPA, and ConfigMap files for every environment, I keep one chart and override just the values that need to change:

```bash
helm lint ./chart
helm template orders ./chart -f values-prod.yaml
helm upgrade --install orders ./chart \
  -n orders --create-namespace \
  -f values-prod.yaml --atomic --wait --timeout 5m
```

I check the rendered YAML and policies, pin chart and image versions, watch the rollout and application health, and keep enough history to roll back. Helm's job is packaging and configuration — Kubernetes itself still does the actual rollout and self-healing.

## 2. How do you manage secrets in Helm charts?

**Answer:**

I never store plaintext secrets in `values.yaml`, in Git, inside a packaged chart, or in `--set` command history. Helm stores release data inside the cluster, so just calling a value "secret" in a template doesn't actually protect it.

My preferred approach is External Secrets Operator or the Secrets Store CSI Driver, backed by Vault, Key Vault, or a cloud secret manager. Workloads authenticate using their own identity, and Kubernetes only ever sees a mounted value or a synced Secret when it's actually needed.

If encrypted values in Git are acceptable for a project, I use SOPS or helm-secrets, with the encryption keys kept outside Git entirely. I restrict RBAC access to Secrets and Helm's release data, make sure CI logs never print rendered values, test that rotation actually works, and confirm that a namespace or service account without permission genuinely can't read the secret.

## 3. How do you roll back a Helm release?

**Answer:**

First I check why the release failed, and whether rolling back is even safe given any database or schema changes that happened since.

```bash
helm status orders -n orders
helm history orders -n orders
kubectl get events -n orders --sort-by=.metadata.creationTimestamp
helm rollback orders 7 -n orders --wait --timeout 5m
```

After rolling back, I check the Deployment status, the pods, Service endpoints, run smoke tests, and watch error rate and latency, along with anything that depends on the data. `helm upgrade --atomic --wait` can automatically undo a failed upgrade, but it can't undo an incompatible database migration or some other external side effect — that has to be handled separately.

I keep the failed revision's logs and rendered manifests around for the post-mortem, fix the chart, test the fix in a lower environment, and then ship a new version — rather than repeatedly retrying the same broken release in production.

## 4. What are Helm hooks and how are they used?

**Answer:**

Hooks are ordinary Kubernetes resources with a special annotation that tells Helm to run them at a specific point in the release lifecycle — `pre-install`, `post-install`, `pre-upgrade`, `pre-delete`, and so on. Common examples are a migration Job, a validation check, a backup, or a cleanup step.

```yaml
metadata:
  annotations:
    "helm.sh/hook": pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

I make hook Jobs safe to run more than once (idempotent), give them a timeout, use a tightly scoped ServiceAccount, and set a clear cleanup policy. A failing hook can block the whole release, so I check the Job, its pod logs, events, and the hook resource itself when something goes wrong.

Anything as critical as a database migration needs its own explicit compatibility and recovery plan — you shouldn't assume a Helm rollback will undo it for you.

## 5. How do you handle multi-environment deployments using Helm?

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

## 6. Explain a basic Helm chart structure and the commands used to release it.

**Answer:**

A chart has `Chart.yaml` for metadata, a default `values.yaml`, templates under `templates/`, and optionally a values schema, tests, dependencies, and documentation. `_helpers.tpl` holds reusable names and labels; templates should render valid Kubernetes objects without hiding important behavior of the workload.

```bash
helm create payments
helm dependency update ./payments
helm lint ./payments
helm template payments ./payments -f values-dev.yaml
helm upgrade --install payments ./payments \
  --namespace payments --create-namespace \
  --values values-prod.yaml --atomic --wait
helm history payments -n payments
helm rollback payments <revision> -n payments
```

CI validates the values schema, renders every supported environment, runs Kubernetes schema and policy checks, packages a versioned chart, and signs and publishes it. Production then deploys that exact same chart and image that were already tested, and verifies the rollout, probes, logs, metrics, and a real transaction afterward.

## 7. How do you sign and verify Helm charts?

**Answer:**

For a classic chart repository, I package and sign the chart with a protected OpenPGP key, using `helm package --sign --key <name> --keyring <ring>`. I publish both the `.tgz` and its `.prov` file — a record of where the chart came from and how it was built — and verify it with `helm verify`.

Key identity, expiry, rotation, and access are all managed centrally. CI gets short-lived access to sign, rather than a developer's own exported private key.

For OCI registries, I prefer signing the chart's fixed digest with a supply-chain tool like Cosign, and enforcing that signature in CI or through admission policy. I also keep track of the source commit, the build workflow's identity, an SBOM and provenance record where relevant, and the registry's audit logs.

Signing proves who — or which workflow — produced an unmodified artifact. It doesn't prove the chart is actually safe. Linting, template and schema validation, security and policy checks, review, and a controlled promotion process are all still needed on top of signing.
