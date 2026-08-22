# Argo CD GitOps Workflow

GitOps means storing the desired Kubernetes configuration in Git and using a controller such as Argo CD to keep the cluster matched with that configuration.

## End-to-End Flow

```text
Developer pushes application code
        ↓
CI runs tests and security scans
        ↓
CI builds and pushes a container image
        ↓
CI updates the image tag in the GitOps repository
        ↓
The change is reviewed and merged
        ↓
Argo CD notices the Git change
        ↓
Argo CD compares Git with the cluster
        ↓
Argo CD synchronizes Kubernetes
        ↓
Kubernetes performs the rollout
```

## Example Release

Assume the application currently uses:

```yaml
image: myapp:v1
replicas: 3
```

The developer pushes a change. The CI pipeline:

1. Runs unit tests and security scans.
2. Builds `myapp:v2`.
3. Pushes the image to a container registry.
4. Changes the image tag in the GitOps repository from `v1` to `v2`.
5. Opens a pull request or commits through an approved automation process.

After the change is merged, Argo CD detects that Git specifies `v2` while the cluster still runs `v1`. It applies the new configuration through the Kubernetes API. Kubernetes creates the new pods, waits for them to become ready, and removes the old pods during a rolling update.

## Who Commits the Image Change?

Argo CD does not normally write deployment changes back to Git. The CI pipeline or a separate image-automation tool updates the GitOps repository.

The automation uses a bot or service account with limited permission. A simple CI example is:

```bash
git clone https://github.com/company/gitops-repo.git
cd gitops-repo

yq -i '.image.tag = "v2"' environments/dev/values.yaml

git add environments/dev/values.yaml
git commit -m "Deploy myapp v2 to development"
git push origin main
```

Teams can use `yq`, Kustomize, or a Helm values editor instead of a broad text replacement. For production, a pull request and approval are safer than pushing directly to the main branch.

## Why Use Separate Repositories?

### Application repository

- Application source code
- Tests
- Dockerfile
- CI pipeline definition

### GitOps repository

- Kubernetes manifests
- Helm values or charts
- Kustomize bases and overlays
- Environment-specific configuration

This separation gives deployment configuration its own permissions, history, reviews, and promotion process. A single repository can also work when the team prefers that structure.

## Desired State, Drift, and Self-Healing

Git is the desired state. The live cluster is the actual state.

If Git says `replicas: 3` and an administrator manually scales the Deployment to 10, Argo CD reports the application as out of sync. If automatic sync and self-healing are enabled, it changes the cluster back to three replicas.

This makes Git the source of truth. Emergency manual changes should therefore be recorded in Git, or Argo CD may reverse them.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| CI system | Test, scan, build, push the image, and propose or make the manifest change |
| Git | Store and review the desired state and its history |
| Argo CD | Compare Git with Kubernetes and reconcile differences |
| Kubernetes | Schedule pods and run the application rollout |

## What Argo CD Can Manage

Argo CD is designed for Kubernetes and can deploy:

- Kubernetes YAML manifests
- Helm charts
- Kustomize applications
- Jsonnet output
- Custom Resources used by operators

It does not directly create a VM, virtual network, S3 bucket, or Azure SQL database through a cloud provider API. Terraform, OpenTofu, Bicep, Pulumi, or CloudFormation are normally used for that work.

Argo CD can manage cloud infrastructure indirectly. For example, it can deploy Crossplane Custom Resources to Kubernetes, and the Crossplane controllers can then create the cloud resources. In that design, Argo CD still talks only to Kubernetes.

## Short Interview Answer

CI tests the code, builds and pushes the image, and updates its tag in the GitOps repository. Argo CD watches that repository and continuously compares the desired state in Git with the actual Kubernetes state. When they differ, it synchronizes the cluster. Argo CD is Kubernetes-focused; it can manage non-Kubernetes infrastructure only indirectly through Kubernetes controllers such as Crossplane.
