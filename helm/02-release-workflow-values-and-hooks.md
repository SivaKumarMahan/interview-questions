# Helm: Release Workflow, Values, and Hooks

> Creating, rendering, installing, upgrading, rolling back, testing, and uninstalling releases, plus values, templating, and lifecycle hooks.

## Key Concepts

### Create and Inspect a Chart

```bash
helm create mychart
helm lint ./mychart
helm show chart ./mychart
helm show values ./mychart
```

### Render and Validate Templates

```bash
helm template my-release ./mychart -f values-dev.yaml
helm install my-release ./mychart -f values-dev.yaml --dry-run --debug
```

Rendering locally is useful for reviewing generated manifests before they reach the cluster.

### Install and Upgrade

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

### Release History and Rollback

```bash
helm list --all-namespaces
helm status my-release
helm history my-release
helm rollback my-release <revision> --wait
helm get all my-release
```

### Test and Uninstall

```bash
helm test my-release
helm uninstall my-release
```

### Values and Templating

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

### Helm Hooks

Hooks are annotated Kubernetes resources executed at release lifecycle points such as `pre-install`, `post-install`, `pre-upgrade`, `post-upgrade`, and `pre-delete`.

Common uses include database migration Jobs, validation, backups, and cleanup. Define hook weights and deletion policies deliberately; hook resources are not managed exactly like ordinary release resources.

## Interview Questions

<details><summary>Q1. [Basic] How do you roll back a Helm release?</summary>

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

</details>

<details><summary>Q2. [Intermediate] How do you use Helm in Kubernetes? Explain charts, deployments, upgrades and the complete rollback procedure.</summary>

**Interviewer:** How are you using Helm in Kubernetes? Explain Helm charts, deployments, upgrades, and the complete rollback procedure.

**Candidate:**

I use Helm as the package manager for Kubernetes. Instead of maintaining large Kubernetes YAML files separately for every environment, I create a reusable Helm chart and pass environment-specific values through `values.yaml` or separate values files.

#### 1.1 Helm chart structure

A typical chart looks like this:

```
my-app/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── configmap.yaml
```

- **Chart.yaml** - chart name and version
- **values.yaml** - default configuration such as image, replicas, CPU, memory
- **templates/** - Kubernetes manifests containing Helm templating
- **templates/deployment.yaml** - creates the Kubernetes Deployment
- **templates/service.yaml** - creates the Service

For different environments, I normally maintain files like:

```
values-dev.yaml
values-qa.yaml
values-prod.yaml
```

#### 1.2 Helm deployment

First, I validate the chart:

```bash
helm lint ./my-app
```

Then I render the templates to check what Kubernetes YAML will actually be generated:

```bash
helm template my-app ./my-app -f values-prod.yaml
```

Then I install it:

```bash
helm install my-app ./my-app \
  -n production \
  --create-namespace \
  -f values-prod.yaml
```

I verify the release:

```bash
helm list -n production
helm status my-app -n production
```

Then I verify the Kubernetes resources:

```bash
kubectl get pods -n production
kubectl get deployment -n production
kubectl get svc -n production
```

#### 1.3 Helm upgrade

Suppose the application team releases version v2.

I update the image tag in `values-prod.yaml`:

```yaml
image:
  repository: myacr.azurecr.io/my-app
  tag: "v2"
```

Then I run:

```bash
helm upgrade my-app ./my-app \
  -n production \
  -f values-prod.yaml
```

I check the rollout:

```bash
kubectl rollout status deployment/my-app -n production
```

And check the Helm revision:

```bash
helm history my-app -n production
```

For example:

```
REVISION  STATUS
1         superseded
2         deployed
```

Each Helm upgrade creates a new release revision, which is important for rollback.

In CI/CD I normally combine install and upgrade into one idempotent command instead of branching on "does this release already exist":

```bash
helm upgrade --install my-app ./my-app \
  -n production \
  -f values-prod.yaml
```

For a quick one-off change without editing the values file, `--set` overrides a single value directly:

```bash
helm upgrade my-app ./my-app -n production --set image.tag=v2
```

#### 1.4 Complete Helm rollback procedure

Suppose revision 2 introduced a bad application version and the Pods are failing.

**Step 1: Check the application**

```bash
kubectl get pods -n production
kubectl describe pod <pod-name> -n production
kubectl logs <pod-name> -n production
```

**Step 2: Check Helm history**

```bash
helm history my-app -n production
```

Suppose I see:

```
REVISION  STATUS
1         superseded
2         superseded
3         deployed
```

I identify revision 2 as the last known good release.

**Step 3: Roll back**

```bash
helm rollback my-app 2 -n production
```

Helm creates a new revision based on revision 2. It does not simply delete the current revision.

I then check:

```bash
helm history my-app -n production
```

I might see:

```
REVISION  STATUS
1         superseded
2         superseded
3         superseded
4         deployed
```

Revision 4 is the rollback operation.

**Step 4: Verify Kubernetes rollout**

```bash
kubectl rollout status deployment/my-app -n production
```

Then:

```bash
kubectl get pods -n production
kubectl get deployment -n production
```

I also check the application logs and readiness probes to make sure the application is actually healthy.

**Step 5: Verify the Helm release**

```bash
helm status my-app -n production
```

If everything is healthy, I consider the rollback complete.

#### 1.5 Important interview point

I would not immediately roll back just because a Pod restarted. First I check whether the problem is actually related to the latest Helm release.

My flow is:

```
Helm Chart
    |
helm install
    |
Kubernetes Deployment
    |
helm upgrade
    |
New Helm Revision
    |
Application issue
    |
helm history
    |
Identify last known-good revision
    |
helm rollback
    |
Kubernetes rollout
    |
Verify Pods + Application
```

#### 1.6 Strong interview answer

> "In my projects, I use Helm to package Kubernetes resources into reusable charts. The chart contains Chart.yaml, values.yaml, and templates such as Deployment, Service, and Ingress. For deployment, I validate the chart using `helm lint` and `helm template`, then use `helm install` or `helm upgrade` with environment-specific values. Every upgrade creates a new Helm revision. If the latest deployment has an issue, I check `helm history`, identify the last known-good revision, and run `helm rollback <release> <revision>`. After rollback, I verify the Helm status, Kubernetes rollout, Pod health, logs, and application functionality."

#### 1.7 Best practices

- Separate values files per environment (`values-dev.yaml`, `values-qa.yaml`, `values-prod.yaml`) instead of branching logic inside templates.
- Keep secrets out of the chart where possible - reference an external secret manager (e.g. Azure Key Vault) rather than committing secret values to `values.yaml`.
- Version Helm charts, so a specific chart version can be pinned and rolled back independently of the application image tag.
- Always run `helm lint` before deploying.
- Use `helm upgrade --install` in CI/CD so the same command works for both first deploy and subsequent releases.
- Verify the rollout (`kubectl rollout status`) after every install/upgrade rather than assuming success from Helm's own exit code.
- Roll back immediately on a failed deployment rather than trying to hotfix forward under pressure.

</details>

<details><summary>Q3. [Intermediate] What are Helm hooks and how are they used?</summary>

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

</details>
