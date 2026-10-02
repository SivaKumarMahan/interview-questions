# Azure DevOps: Pipeline Design, Variables, and Templates

> Multi-stage YAML pipelines, service connections, variables and variable groups, templates, and Terraform/Helm/AKS delivery pipelines.

## Key Concepts

### End-to-End Terraform, Azure DevOps, Helm, and AKS Pipeline

**Project flow:**

1. **Terraform** provisions the resource group, virtual network, Azure Container Registry, AKS cluster, Key Vault, identities, and the role assignments they need. State is stored in an encrypted, locked remote backend.
2. **Azure Pipelines** runs Terraform formatting, validation, security checks, plan review, approval, and apply, using a workload-identity service connection.
3. A **Node.js application** gets installed, linted, unit-tested, and packaged.
4. The pipeline builds a minimal container image, scans it, and publishes it to ACR with a digest — a fixed reference that always points to that exact image and never changes. It also records where the artifact came from and how it was built.
5. **Helm** deploys that same image to AKS, with environment-specific values, readiness and liveness probes, resource requests, and `--atomic --wait` so a bad rollout gets rolled back automatically.
6. **Post-deployment checks** confirm Pods are healthy, LoadBalancer or Ingress routing works, the application is healthy, and logs and monitoring look normal. Production promotion stops or rolls back when any of these health checks fail.

The main areas I had to dig into on this project were Terraform state and lock handling, ACR authentication, the Azure service connection's identity and RBAC, Helm's rendering and release history, Kubernetes Events, and rollout health.

The main design rule underneath all of it: **build the artifact once, and promote that exact same version through every environment**, rather than rebuilding it for each one.

### Terraform Delivery with Azure DevOps

A Terraform pipeline should run from reviewed Git code, using a protected Azure Resource Manager service connection — ideally workload identity federation, with a narrowly scoped service principal only when that's really necessary.

A self-hosted agent makes sense when it needs to reach private endpoints or private Azure APIs, but it has to be patched, isolated, and monitored, and it should never run untrusted pull-request code with production credentials attached.

```text
pull request -> fmt/validate -> tfsec/Checkov -> plan artifact -> review
protected environment -> approval -> apply saved plan -> smoke test -> audit evidence
```

Keep Terraform modules reusable, and keep Dev, QA, and Production separate by state, identity, approval, subscription or resource scope, and policy — not just by swapping variable files. Use an encrypted, versioned remote state backend with locking, and never keep state or service-principal secrets in the repository.

Publish the plan for review, apply that exact reviewed plan, and hold onto the pipeline logs, deployment metadata, and rollback or recovery instructions.

## Interview Questions

### 1. How do you design a multi-stage Azure Pipeline?

**Answer:**

I build one artifact that never changes once built, then promote that same artifact through each stage:

```yaml
stages:
- stage: CI
  jobs:
  - job: TestBuildScan
    pool: { vmImage: ubuntu-latest }
    steps:
    - checkout: self
    - script: npm ci && npm test
    - script: docker build -t $(imageRepo):$(Build.SourceVersion) .

- stage: Deploy_Staging
  dependsOn: CI
  jobs:
  - deployment: Deploy
    environment: staging
    strategy:
      runOnce:
        deploy:
          steps:
          - script: ./deploy.sh staging $(Build.SourceVersion)
```

In a real pipeline, CI also scans the image and publishes it, staging runs smoke and integration tests, and production adds environment checks, approval, monitoring, and rollback. Templates standardize the jobs, but each environment's values and identities stay isolated from the others.

I set timeouts, concurrency or exclusive locks, artifact retention, and make sure ownership of each stage is clear.

### 2. What are service connections in Azure DevOps?

**Answer:**

A service connection stores how Azure Pipelines authenticates to something external — Azure, Kubernetes, GitHub, or a registry. I prefer Azure Resource Manager connections that use workload identity federation, so there's no long-lived client secret sitting around.

I scope the identity to the smallest subscription, resource group, or resource role it needs, authorize it only for the pipelines that should use it, and keep non-production separate from production. Creating and using a connection is audited, ownership is documented, and connections nobody's using anymore get removed.

If authentication fails, I check that the connection is verified, the tenant and subscription, the federated credential's subject, which pipelines are authorized to use it, the role and its scope, whether RBAC has propagated, the target's network or firewall, and whether the agent can even reach it. I test one allowed and one denied operation to actually prove least privilege is working.

### 3. How do you use variables and variable groups in Azure Pipelines?

**Answer:**

Variables hold reusable values. Variable groups share those values across pipelines and can link straight to Key Vault. Templates and parameters are better for decisions that need to be typed and fixed at compile time; variables are just runtime strings.

```yaml
variables:
- group: app-prod-nonsecret
- name: imageTag
  value: $(Build.SourceVersion)
```

I keep non-secret configuration in reviewed files or groups, and put actual secrets in Key Vault or protected secret variables. Production groups are authorized only for the pipelines that need them.

I avoid ever echoing a secret, and I know masking output is a safety net, not a real guarantee.

I also document how precedence works, since template, pipeline, stage, job, and queue-time values can all override each other. Reading the rendered pipeline and its logs helps track down an unexpected value without printing anything sensitive.

### 4. What is a pipeline template in Azure DevOps?

**Answer:**

Templates are reusable YAML for stages, jobs, steps, or variables. They cut down on duplication and give teams an approved pattern for building, scanning, and deploying.

```yaml
# templates/test.yml
parameters:
- name: nodeVersion
  type: string
  default: '20'

steps:
- task: NodeTool@0
  inputs: { versionSpec: '${{ parameters.nodeVersion }}' }
- script: npm ci && npm test
```

I keep templates in a controlled repository, pin to a specific ref or tag, use typed parameters, document the inputs, and test changes against the teams actually using them. Breaking changes get proper versioning and migration guidance.

Templates should standardize the important controls, but not hide pipeline behavior so deeply that the team using it can't troubleshoot it themselves.
