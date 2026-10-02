# YAML: YAML in DevOps

> How YAML is used in Kubernetes manifests, CI/CD pipelines such as GitHub Actions, and environment-specific configuration.

## Key Concepts

### Real-World Application: GitHub Actions Workflow

```yaml
name: Build and Test Application

# Trigger on push to main branch
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

# Jobs to run
jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'

    - name: Install dependencies
      run: npm install

    - name: Run tests
      run: npm test

    - name: Build application
      run: npm run build
```

## Interview Questions

### 1. How is YAML used in Kubernetes?

**Answer:**

Kubernetes YAML describes API objects and their desired state. The main fields are `apiVersion`, `kind`, `metadata`, and `spec`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: example/api:1.0.0
          ports:
            - containerPort: 8080
```

I validate it with a schema tool and `kubectl apply --dry-run=server -f deployment.yaml`. After applying it for real, I check rollout status, the Pods, events, and the Service endpoint.

I store manifests in Git, review changes, pin images, and keep secrets outside plaintext YAML.

### 2. How is YAML used in CI/CD?

**Answer:**

CI/CD YAML defines triggers, stages, jobs, dependencies, variables, artifacts, environments, and deployment rules. The syntax is always YAML, but each platform has its own schema on top of it.

A safe setup runs CI on every pull request, and restricts production deployment to protected branches or environments.

I keep build and deployment jobs separate. I build one artifact and reuse it everywhere rather than rebuilding per environment, since rebuilding risks producing a slightly different artifact each time. I use secret references instead of raw values, pin external tasks and actions to a specific version, and add timeouts and rollback checks.
I validate using the platform's linter and a test branch. A YAML parser only proves the file parses correctly — it says nothing about whether the job permissions, conditions, or deployment logic are actually right.

### 3. How do you manage environment-specific YAML?

**Answer:**

I keep a common base and store only differences per environment. The mechanism depends on the tool:

- Helm: one chart with `values-dev.yaml`, `values-stage.yaml`, and `values-prod.yaml`
- Kustomize: a base plus environment overlays
- CI/CD: reusable templates plus protected environment variables
- Applications: base configuration plus external configuration/secret references

I do not duplicate entire manifests because fixes then drift between environments. Secrets stay in a secret manager.

CI renders the final configuration, validates schemas and policies, displays a reviewable diff, and promotes the same application version. After deployment I verify the environment received the intended values without exposing sensitive output.
