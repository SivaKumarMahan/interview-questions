# Hands-on 1: Build a Helm Chart from Scratch with Dev and Prod Values

> Replace copy-pasted Kubernetes YAML with one reusable Helm chart, then deploy it to two isolated environments (`app-dev` and `app-prod`) using separate values files.

**Time:** about 30 minutes. **Level:** Basic.

## What you practise

- Creating a chart by hand: `Chart.yaml`, `values.yaml`, and templates
- Replacing hardcoded values with Go templating such as `{{ .Values.name }}`
- One chart, many environments: `values-dev.yaml` and `values-prod.yaml`
- Installing separate releases into separate namespaces, then upgrading and rolling back

## Prerequisites

| Tool | Purpose |
| --- | --- |
| A Kubernetes cluster | AKS, kind, minikube, or Docker Desktop |
| kubectl | Check the deployed resources |
| Helm 3 | Build and deploy the chart |

## Flow

```text
myapp-chart/ (one chart)
     |
     |-- values-dev.yaml  --> helm install dev-release  --> namespace app-dev
     |
     '-- values-prod.yaml --> helm install prod-release --> namespace app-prod
```

## Steps

### 1. Create the chart structure

```bash
mkdir -p myapp-chart/templates
cd myapp-chart
touch Chart.yaml values.yaml values-dev.yaml values-prod.yaml
touch templates/pod.yaml templates/svc.yaml
```

```text
myapp-chart/
├── Chart.yaml          # chart name and version
├── values.yaml         # default values
├── values-dev.yaml     # Dev overrides
├── values-prod.yaml    # Prod overrides
└── templates/
    ├── pod.yaml        # templated Pod
    └── svc.yaml        # templated Service
```

`helm create myapp-chart` generates a full example chart, but building it by hand shows exactly what each file does.

### 2. Write `Chart.yaml`

```yaml
apiVersion: v2
name: myapp-chart
description: A simple chart for one web application
type: application
version: 0.1.0        # chart version, change it when the chart changes
appVersion: "1.27"    # version of the application inside
```

### 3. Write the default `values.yaml`

```yaml
name: myapp
image: nginx:1.27
port: 80
serviceType: ClusterIP
```

### 4. Template the Pod and Service

`templates/pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: {{ .Values.name }}
  labels:
    app: {{ .Values.name }}
    release: {{ .Release.Name }}
spec:
  containers:
    - name: {{ .Values.name }}
      image: {{ .Values.image }}
      ports:
        - containerPort: {{ .Values.port }}
```

`templates/svc.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Values.name }}-svc
  labels:
    release: {{ .Release.Name }}
spec:
  type: {{ .Values.serviceType }}
  selector:
    app: {{ .Values.name }}
  ports:
    - port: {{ .Values.port }}
      targetPort: {{ .Values.port }}
```

Nothing is hardcoded any more: every environment-specific value comes from `.Values`, and `.Release.Name` comes from the `helm install` command.

### 5. Create the environment values files

`values-dev.yaml`:

```yaml
name: myapp-dev
image: nginx:1.27
serviceType: ClusterIP
```

`values-prod.yaml`:

```yaml
name: myapp-prod
image: nginx:1.27
serviceType: LoadBalancer
```

Only the values that differ go in these files. Anything not set falls back to `values.yaml`.

### 6. Validate before deploying

```bash
cd ..
helm lint ./myapp-chart -f myapp-chart/values-dev.yaml
helm template dev-release ./myapp-chart -f myapp-chart/values-dev.yaml
helm template prod-release ./myapp-chart -f myapp-chart/values-prod.yaml
```

- `helm lint` checks the chart structure and template syntax.
- `helm template` renders the final YAML locally, so you can check that Dev and Prod produce different manifests.

### 7. Deploy Dev and Prod as separate releases

```bash
helm install dev-release ./myapp-chart \
  -f myapp-chart/values-dev.yaml \
  -n app-dev --create-namespace

helm install prod-release ./myapp-chart \
  -f myapp-chart/values-prod.yaml \
  -n app-prod --create-namespace
```

### 8. Verify

```bash
helm list -A
kubectl get pod,svc -n app-dev
kubectl get pod,svc -n app-prod

kubectl port-forward -n app-dev svc/myapp-dev-svc 8080:80
# in another terminal
curl http://localhost:8080
```

Expected: two releases (`dev-release` in `app-dev`, `prod-release` in `app-prod`), each with its own Pod and Service, and the nginx welcome page from the port-forward.

### 9. Upgrade and roll back

Change the Dev image in `values-dev.yaml` to `nginx:1.28`, then:

```bash
helm upgrade dev-release ./myapp-chart -f myapp-chart/values-dev.yaml -n app-dev
helm history dev-release -n app-dev
helm rollback dev-release 1 -n app-dev
```

Prod is not affected, because it is a separate release in a separate namespace.

## Important points

- Values precedence, lowest to highest: `values.yaml` → each `-f` file in order → `--set`.
- A bare Pod is used here to keep the lab small. In real projects, use a **Deployment** so Pods are recreated if they fail and rollouts are gradual. Some Pod fields (such as ports) cannot be changed in place, so an upgrade that changes them fails.
- Keep secrets out of values files; use Key Vault or Kubernetes Secrets.

## Clean up

```bash
helm uninstall dev-release -n app-dev
helm uninstall prod-release -n app-prod
kubectl delete namespace app-dev app-prod
```

## Interview questions

<details><summary>Q1. What problem does Helm solve?</summary>

Without Helm, each environment needs its own copy of the Kubernetes YAML, and the copies drift apart. Helm packages the YAML as templates in a versioned chart. Each environment supplies only its own values, and Helm tracks every install as a release with history, so upgrades and rollbacks are one command.

</details>

<details><summary>Q2. What is the difference between a chart and a release?</summary>

A chart is the package: templates, default values, and metadata. A release is one installed instance of that chart in a cluster, with a name and a revision history. The same chart can be installed many times as different releases, like `dev-release` and `prod-release` here.

</details>

<details><summary>Q3. How do you manage Dev and Prod with one chart?</summary>

I keep the templates the same and create one values file per environment, such as `values-dev.yaml` and `values-prod.yaml`, containing only what differs: image tag, replicas, resources, Service type, and hostnames. I deploy each environment as a separate release into its own namespace or cluster with `-f values-<env>.yaml`.

</details>

<details><summary>Q4. What is the difference between <code>helm lint</code>, <code>helm template</code>, and <code>--dry-run</code>?</summary>

`helm lint` checks the chart for structural and syntax problems. `helm template` renders the YAML locally without contacting the cluster. `helm install --dry-run` renders the YAML and also validates it against the cluster's API without creating anything.

</details>

<details><summary>Q5. How do you roll back a bad Helm release?</summary>

`helm history <release> -n <namespace>` shows the revisions, and `helm rollback <release> <revision> -n <namespace>` returns to a previous one. In pipelines, `helm upgrade --install --atomic --wait` rolls back automatically if the new release does not become healthy.

</details>
