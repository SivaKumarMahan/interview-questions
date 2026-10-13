# Hands-on 3: Deploy a Helm Chart from ACR to AKS with Argo CD

> Install Argo CD on AKS, connect it to a private Helm chart stored in Azure Container Registry (OCI), create an Argo CD Application for a specific chart version, and sync it until it is Healthy and Synced.

**Time:** about 1 hour. **Level:** Intermediate.

## What you practise

- Packaging a versioned Helm chart (`0.1.1`) and pushing it to ACR as an OCI artifact
- Installing Argo CD on AKS and opening its web UI
- Giving Argo CD read-only credentials for a private OCI Helm repository
- Creating an Argo CD Application with chart version and target namespace
- Manual sync and checking health and sync status

## Prerequisites

| Item | Purpose |
| --- | --- |
| AKS cluster with `kubectl` access | Runs Argo CD and the application |
| Azure Container Registry | Stores the Helm chart |
| Azure CLI, Helm 3, kubectl | Commands in this lab |
| Argo CD CLI (optional) | Same steps from the command line |

## Flow

```text
helm package + helm push
        |
        v
ACR: oci://myacr.azurecr.io/helm/myapp-chart:0.1.1
        |
        | Argo CD repo-server pulls the chart with a scoped ACR token
        v
Argo CD Application (chart version 0.1.1, namespace myapp)
        |
        | Sync (manual)
        v
AKS: Deployment, Service, ... in namespace myapp
        |
        v
Status: Healthy + Synced
```

## Steps

### 1. Validate, package, and push the chart

```bash
helm lint ./myapp-chart
helm template myapp ./myapp-chart

helm package ./myapp-chart --version 0.1.1
az acr login --name myacr
helm push myapp-chart-0.1.1.tgz oci://myacr.azurecr.io/helm

az acr repository show-tags --name myacr --repository helm/myapp-chart -o table
```

### 2. Install Argo CD on AKS

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl get pods -n argocd -w
```

Wait until all Argo CD Pods are `Running`.

### 3. Open the Argo CD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443

# initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

Open `https://localhost:8080` and log in as `admin`. Change the password afterwards and delete the `argocd-initial-admin-secret` Secret. For a shared environment, expose Argo CD through an Ingress with TLS and SSO instead of port-forwarding.

### 4. Create read-only ACR credentials for Argo CD

Use a repository-scoped ACR token, so Argo CD can only read the chart:

```bash
az acr scope-map create \
  --name helm-chart-read \
  --registry myacr \
  --repository helm/myapp-chart content/read metadata/read

az acr token create \
  --name argocd-helm \
  --registry myacr \
  --scope-map helm-chart-read
```

The second command prints the token passwords. Store one securely; you need it in the next step.

### 5. Register the private OCI Helm repository in Argo CD

Declarative (preferred, can be kept in Git with a sealed or external secret):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: acr-helm-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  name: acr-helm
  type: helm
  url: myacr.azurecr.io/helm
  enableOCI: "true"
  username: argocd-helm
  password: <token-password>
```

Or with the CLI:

```bash
argocd login localhost:8080 --username admin --insecure
argocd repo add myacr.azurecr.io/helm \
  --type helm --name acr-helm --enable-oci \
  --username argocd-helm --password <token-password>
```

The repository URL has no `oci://` prefix; `enableOCI` tells Argo CD it is an OCI registry.

### 6. Create the Argo CD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: myacr.azurecr.io/helm
    chart: myapp-chart
    targetRevision: 0.1.1
    helm:
      valuesObject:
        replicaCount: 2
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
```

```bash
kubectl apply -f application.yaml
```

No `automated` sync policy is set, so the application appears as `OutOfSync` until it is synced manually.

### 7. Sync and verify

In the UI, open **myapp → SYNC → SYNCHRONIZE**, or:

```bash
argocd app sync myapp
argocd app get myapp
kubectl get all -n myapp
```

Expected result:

- Application health: **Healthy**
- Sync status: **Synced** to chart version `0.1.1`
- Pods `Running` in namespace `myapp`

### 8. Release a new version

Change the chart, package and push `0.1.2`, update `targetRevision: 0.1.2` (in Git, if the Application manifest is managed there), and sync again. To roll back, set `targetRevision` back to `0.1.1` or use **History and rollback** in the UI.

## Important points

- Argo CD only needs **read** access to the chart. The AKS nodes need `AcrPull` separately to pull the application **images** (`az aks update --attach-acr myacr`).
- For full GitOps, keep the Application manifest in Git, and enable `syncPolicy.automated` with `prune` and `selfHeal` after testing manual sync.
- ACR tokens expire if you set an expiry; rotate them and update the repository Secret.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `failed to fetch chart ... 401 Unauthorized` | Wrong token, or scope map does not include the repository | Check the scope map path `helm/myapp-chart` and the password |
| `chart not found` | `repoURL`, `chart`, or `targetRevision` does not match what was pushed | Compare with `az acr repository show-tags` |
| Application stays `Progressing` | Pods not ready | `kubectl describe pod -n myapp` and check probes and events |
| Pods in `ImagePullBackOff` | AKS cannot pull the application image | Attach ACR to AKS with `AcrPull` |
| `OutOfSync` right after sync | Fields changed by controllers or manual edits | Check the diff in the UI; use `ignoreDifferences` only for known fields |

## Clean up

```bash
argocd app delete myapp --yes      # or: kubectl delete application myapp -n argocd
kubectl delete namespace myapp
kubectl delete namespace argocd
az acr token delete --name argocd-helm --registry myacr --yes
az acr scope-map delete --name helm-chart-read --registry myacr --yes
```

## Interview questions

<details><summary>Q1. How does Argo CD deploy a Helm chart stored in ACR?</summary>

I push the packaged chart to ACR as an OCI artifact. In Argo CD, I register `myacr.azurecr.io/helm` as a Helm repository with `enableOCI` and read-only credentials. The Application points to that repository, the chart name, and a specific chart version (`targetRevision`), plus the destination cluster and namespace. Argo CD renders the chart with `helm template` and applies the result, then reports health and sync status.

</details>

<details><summary>Q2. What credentials does Argo CD need for a private ACR, and why use a scoped token?</summary>

Argo CD's repo-server only needs to read the chart. I create an ACR scope map with `content/read` and `metadata/read` on the chart repository, and a token for that scope map. This follows least privilege: if the credential leaks, it cannot push or read other repositories. Image pulls by AKS use the kubelet identity with `AcrPull`, which is separate.

</details>

<details><summary>Q3. What is the difference between Healthy and Synced in Argo CD?</summary>

**Synced** means the live resources match the desired state from the chart and values. **Healthy** means those resources are actually working, for example a Deployment has all replicas available. An application can be Synced but Degraded if the Pods crash, or OutOfSync but Healthy if someone changed a resource manually.

</details>

<details><summary>Q4. Manual sync or automated sync?</summary>

Manual sync is useful when first onboarding an application or for Production, where a person decides when to deploy. Automated sync with `prune` and `selfHeal` applies every change in Git automatically and reverts manual drift, which suits Dev and QA. Many teams use automated sync for lower environments and manual or PR-approved sync for Production.

</details>

<details><summary>Q5. How do you roll back with Argo CD?</summary>

The cleanest way is to revert the change in Git, for example set `targetRevision` back to the previous chart version, and let Argo CD sync. For an emergency, the UI or `argocd app rollback` can return to a previous synced revision, but automated sync must be paused or Argo CD will sync forward again.

</details>
