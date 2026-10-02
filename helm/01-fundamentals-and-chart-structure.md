# Helm: Fundamentals and Chart Structure

> What Helm is, charts, releases, and repositories, the chart directory layout, Helm versus Operators, and a revision checklist.

## Key Concepts

### Interview Revision Checklist

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

### What Helm Is

Helm is a package manager for Kubernetes. It packages related Kubernetes manifests into reusable charts and manages installed chart instances as releases.

Helm helps teams:

- Deploy multiple Kubernetes resources with one command
- Reuse templates across applications and environments
- Override configuration without copying manifests
- Track release revisions
- Upgrade or roll back deployments
- Package and distribute application definitions

Helm does not replace Kubernetes. It renders Kubernetes YAML and submits it to the Kubernetes API.

### Chart, Release, and Repository

- **Chart:** A versioned package containing templates, default values, metadata, and optional dependencies.
- **Release:** One installed instance of a chart in a Kubernetes cluster.
- **Repository:** A location where packaged charts and their index are published.

The same chart can be installed more than once using different release names and values.

### Helm Chart Structure

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

### Helm vs. Kubernetes Operators

| Helm | Operator |
| --- | --- |
| Packages and renders resources | Runs a controller that continuously reconciles the cluster — keeping its actual state matched to the desired state |
| Strong for install, upgrade, and rollback | Strong for continuous application-specific operations |
| Usually reacts when a user or pipeline runs Helm | Continuously watches custom resources and cluster state |
| Suitable for most application deployments | Suitable for complex lifecycle automation such as databases |

They can be used together: Helm can install an Operator and its supporting resources.

## Interview Questions

### 1. What is Helm and how does it simplify Kubernetes deployments?

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

### 2. Explain the folder structure of a Helm chart and the purpose of each folder/file. What commands you use to deploy Helm charts?

**A:** A Helm chart has a specific folder structure that organizes the files and templates needed to deploy applications on Kubernetes. Here's an overview of the typical folder structure of a Helm chart:

```
mychart/
│
├── Chart.yaml
├── values.yaml
│
├── charts/
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── _helpers.tpl
│   ├── hpa.yaml
│   ├── NOTES.txt
│
└── .helmignore
```

Here's a brief explanation of each folder/file:

1. **`Chart.yaml`:** This file contains metadata about the chart, such as its name, version, description, and maintainers. It is essential for Helm to identify and manage the chart.
2. **`values.yaml`:** This file contains the default configuration values for the chart. Users can override these values when deploying the chart to customize the deployment.
3. **`charts/`:** This directory is used to store any dependent charts that your chart relies on. These dependencies can be other Helm charts that are packaged together with your main chart.
4. **`templates/`:** This directory contains the Kubernetes manifest templates that Helm uses to generate the final YAML files for deployment. These templates can include Deployments, Services, Ingresses, and other Kubernetes resources. The templates can use Go templating syntax to allow for dynamic configuration based on the values provided in `values.yaml` or during deployment.
   - **`deployment.yaml`:** Template for creating a Kubernetes Deployment resource.
   - **`service.yaml`:** Template for creating a Kubernetes Service resource.
   - **`ingress.yaml`:** Template for creating a Kubernetes Ingress resource.
   - **`_helpers.tpl`:** A file that contains helper template functions that can be reused across other templates.
   - **`hpa.yaml`:** Template for creating a Horizontal Pod Autoscaler resource.
   - **`NOTES.txt`:** A file that provides post-installation instructions or notes to the user after the chart is deployed.
5. **`.helmignore`:** This file specifies patterns for files and directories that should be ignored when packaging the chart. It works similarly to a `.gitignore` file.

To deploy Helm charts, you can use the following commands:

1. `helm install <release-name> <chart-path>`: This command installs a Helm chart into your Kubernetes cluster. Replace `<release-name>` with a name for your deployment and `<chart-path>` with the path to your chart.
2. `helm upgrade <release-name> <chart-path>`: This command upgrades an existing release with a new version of the chart.
3. `helm uninstall <release-name>`: This command removes a deployed Helm release from the cluster.
4. `helm repo add <repo-name> <repo-url>`: This command adds a Helm chart repository.
5. `helm repo update`: This command updates the local cache of chart repositories.
6. `helm list`: This command lists all the deployed Helm releases in the cluster.

Helm relies on the Kubernetes Deployment's own rolling update strategy. When you upgrade a release, Kubernetes rolls out the new pods and only terminates the old ones once the new ones are Ready — so there's no downtime in between.

### 3. Explain a basic Helm chart structure and the commands used to release it.

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
