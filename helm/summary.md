# Helm Interview Preparation Summary

## 1. Helm Fundamentals

### 1.1 What Helm Is

Helm is a package manager for Kubernetes. It packages related Kubernetes manifests into reusable charts and manages installed chart instances as releases.

Helm helps teams:

- Deploy multiple Kubernetes resources with one command
- Reuse templates across applications and environments
- Override configuration without copying manifests
- Track release revisions
- Upgrade or roll back deployments
- Package and distribute application definitions

Helm does not replace Kubernetes. It renders Kubernetes YAML and submits it to the Kubernetes API.

### 1.2 Chart, Release, and Repository

- **Chart:** A versioned package containing templates, default values, metadata, and optional dependencies.
- **Release:** One installed instance of a chart in a Kubernetes cluster.
- **Repository:** A location where packaged charts and their index are published.

The same chart can be installed more than once using different release names and values.

## 2. Helm Chart Structure

```text
mychart/
├── Chart.yaml
├── values.yaml
├── values.schema.json
├── charts/
├── crds/
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── _helpers.tpl
│   ├── NOTES.txt
│   └── tests/
├── .helmignore
├── LICENSE
└── README.md
```

| Path | Purpose |
| --- | --- |
| `Chart.yaml` | Chart metadata, chart version, application version, and dependencies |
| `values.yaml` | Default configuration values consumed by templates |
| `values.schema.json` | Optional schema used to validate supplied values |
| `charts/` | Downloaded or packaged chart dependencies |
| `crds/` | Custom Resource Definitions installed before normal templates |
| `templates/` | Go-templated Kubernetes manifests |
| `_helpers.tpl` | Reusable named templates and helper functions |
| `NOTES.txt` | Instructions displayed after install or upgrade |
| `templates/tests/` | Optional resources used by `helm test` |
| `.helmignore` | Files excluded when packaging the chart |
| `LICENSE` | Chart licensing information |
| `README.md` | Chart usage and configuration documentation |

`Chart.yaml` uses `version` for the chart package and `appVersion` as informational metadata about the packaged application version.

## 3. Standard Helm Workflow

### 3.1 Create and Inspect a Chart

```bash
helm create mychart
helm lint ./mychart
helm show chart ./mychart
helm show values ./mychart
```

### 3.2 Render and Validate Templates

```bash
helm template my-release ./mychart -f values-dev.yaml
helm install my-release ./mychart -f values-dev.yaml --dry-run --debug
```

Rendering locally is useful for reviewing generated manifests before they reach the cluster.

### 3.3 Install and Upgrade

```bash
helm upgrade --install my-release ./mychart \
  --namespace my-app \
  --create-namespace \
  -f values-prod.yaml \
  --wait \
  --atomic
```

- `upgrade --install` makes the command usable for both first deployment and later updates.
- `--wait` waits for supported resources to become ready.
- `--atomic` removes a failed install or rolls back a failed upgrade and implies `--wait`.

Kubernetes controllers perform the underlying rollout. Helm waits or rolls back according to the selected flags; Helm itself does not guarantee zero downtime.

### 3.4 Release History and Rollback

```bash
helm list --all-namespaces
helm status my-release
helm history my-release
helm rollback my-release <revision> --wait
helm get all my-release
```

### 3.5 Test and Uninstall

```bash
helm test my-release
helm uninstall my-release
```

## 4. Values and Templating

Templates use values to generate environment-specific Kubernetes manifests.

```yaml
# values.yaml
replicaCount: 2

image:
  repository: example/app
  tag: "1.0.0"

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

```yaml
# templates/deployment.yaml
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

Common template objects include `.Values`, `.Chart`, `.Release`, `.Capabilities`, and `.Files`.

Use helpers in `_helpers.tpl` for consistent names, labels, and repeated template logic. Use `required`, `default`, `quote`, `toYaml`, `include`, `tpl`, and indentation functions carefully.

## 5. Multi-Environment Deployments

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

## 6. Shared Charts for Multiple Microservices

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

## 7. Dependencies and Umbrella Charts

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

## 8. Chart Repositories and OCI Registries

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

## 9. Helm Hooks

Hooks are annotated Kubernetes resources executed at release lifecycle points such as `pre-install`, `post-install`, `pre-upgrade`, `post-upgrade`, and `pre-delete`.

Common uses include database migration Jobs, validation, backups, and cleanup. Define hook weights and deletion policies deliberately; hook resources are not managed exactly like ordinary release resources.

## 10. Security

### 10.1 Secrets

Do not commit plaintext secrets to `values.yaml`. Prefer a dedicated secret-management workflow such as:

- External Secrets Operator
- Secrets Store CSI Driver
- HashiCorp Vault
- Azure Key Vault or AWS Secrets Manager
- Sealed Secrets
- SOPS with an approved Helm integration

Remember that rendered manifests and release data can expose values. Restrict cluster access, CI logs, artifacts, and Helm release information.

### 10.2 Chart Signing and Provenance

Helm can generate a provenance file — a record of where a chart came from and how it was built — and verify charts using GPG signatures.

```bash
helm package ./mychart --sign --key <key-id> --keyring <keyring-path>
helm verify mychart-1.0.0.tgz
```

For charts published to OCI registries, signing is often handled instead with a supply-chain tool such as Sigstore Cosign, depending on the organization's delivery standard.

## 11. Helm vs. Kubernetes Operators

| Helm | Operator |
| --- | --- |
| Packages and renders resources | Runs a controller that continuously reconciles the cluster — keeping its actual state matched to the desired state |
| Strong for install, upgrade, and rollback | Strong for continuous application-specific operations |
| Usually reacts when a user or pipeline runs Helm | Continuously watches custom resources and cluster state |
| Suitable for most application deployments | Suitable for complex lifecycle automation such as databases |

They can be used together: Helm can install an Operator and its supporting resources.

## 12. CI/CD and GitOps

A typical CI pipeline:

1. Lints the chart.
2. Validates values and renders templates.
3. Scans images and generated manifests.
4. Packages and publishes a fixed chart version that won't change afterward.
5. Promotes the version after approval.

In a push model, a pipeline runs Helm against the cluster directly. In a pull-based GitOps model, Flux or Argo CD watches Git or OCI sources instead, and continuously reconciles the cluster to match the declared release.

GitOps improves drift detection and avoids giving a central CI system broad cluster credentials.

Helm commonly participates in EKS/AKS delivery with Terraform for infrastructure, Jenkins or another CI system for builds, Argo CD/Flux for deployment, and Prometheus/Grafana/AppDynamics for observability.

## 13. Monitoring and Troubleshooting

Useful checks:

```bash
helm lint ./mychart
helm template my-release ./mychart --debug
helm status my-release
helm history my-release
helm get values my-release --all
helm get manifest my-release
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl describe pod <pod>
kubectl logs <pod> --previous
```

Common causes of failure: invalid rendered YAML, missing values, an attempt to change a field that can't be changed after creation, a failed hook, a failed readiness probe, insufficient resources, an image-pull error, an RBAC restriction, or a dependency-version conflict.

## 14. Interview Revision Checklist

- Helm chart, release, repository, and revision
- Chart directory structure
- Values precedence and Go templating
- Install, upgrade, rollback, test, and uninstall
- `--wait`, `--atomic`, and dry runs
- Multi-environment values management
- Reusable charts and per-service configuration
- Dependencies and umbrella charts
- Repositories and OCI registries
- Hooks and lifecycle behavior
- Secret management and chart signing
- Helm vs. Operators
- CI/CD, GitOps, monitoring, and troubleshooting
