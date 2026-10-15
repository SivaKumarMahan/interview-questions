# Cognizant - Interview Questions

Real interview questions with simple, easy-to-read answers.

---

<details><summary>Q1. Have you done any automation to check deprecated versions in AKS?</summary>

### Interview-style answer

Yes. I automate the check for deprecated Kubernetes API versions and AKS cluster versions using Azure CLI and scanning tools.

In our project, we run applications on AKS and deploy them with Helm charts and Kubernetes YAML manifests. Before upgrading the cluster or deploying an application, we must make sure the Kubernetes version is supported and that our manifests do not use deprecated APIs.

I automate this in three ways.

### 1. Check the AKS Kubernetes version

Azure CLI shows the current cluster version and the versions you can upgrade to.

```bash
# Current Kubernetes version of the cluster
az aks show \
  --resource-group my-rg \
  --name my-aks \
  --query kubernetesVersion \
  -o tsv

# Available upgrade versions
az aks get-upgrades \
  --resource-group my-rg \
  --name my-aks \
  -o table
```

### 2. Check deprecated APIs in manifests and in the cluster

- **Pluto** scans Kubernetes YAML files and Helm templates for APIs that are deprecated or removed in a target Kubernetes version.
- **kubent (Kube No Trouble)** scans the resources already running in the live cluster.

```bash
# Scan YAML files against the target Kubernetes version
pluto detect-files -d k8s/ --target-versions k8s=v1.30.0

# Render a Helm chart and scan the output
helm template my-app ./charts/my-app | pluto detect - --target-versions k8s=v1.30.0

# Scan the live cluster
kubent
```

For example, if a manifest uses the old `extensions/v1beta1` API for an Ingress, the scan flags it so we replace it with `networking.k8s.io/v1`.

### 3. Integrate it into the CI/CD pipeline

I add this validation step to the Azure DevOps pipeline before deployment. If deprecated APIs are found, the pipeline fails or publishes a report, so the team fixes the manifests before upgrading or deploying.

The flow:

1. Azure DevOps pipeline starts.
2. Check the AKS version and available upgrades.
3. Scan YAML and Helm manifests with Pluto.
4. Publish a report or fail the validation.
5. Deploy only after the validation passes.

```yaml
- task: AzureCLI@2
  displayName: Check AKS version and deprecated APIs
  inputs:
    azureSubscription: sc-azure-dev
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az aks get-upgrades -g my-rg -n my-aks -o table
      helm template my-app ./charts/my-app | pluto detect - --target-versions k8s=v1.30.0
```

Pluto returns a non-zero exit code when it finds deprecated or removed APIs, so the step fails the pipeline automatically.

### Short answer to speak in the interview

> "Yes, I automate deprecated version checks in AKS using Azure CLI and tools like Pluto and kubent. Azure CLI shows the current Kubernetes version and the available upgrades. Pluto finds deprecated APIs in Kubernetes YAML files and Helm charts, and kubent checks what is already running in the cluster. I add these checks to the Azure DevOps pipeline so we catch compatibility issues before upgrading the AKS cluster or deploying the application. This prevents deployment failures during Kubernetes upgrades."

**Important:** Checking the AKS cluster version alone does not find every deprecated API. You also need to scan the manifests and, where needed, the live cluster resources. AKS itself also stops an upgrade if it detects recent use of APIs that are removed in the target version.

</details>

<details><summary>Q2. What is the difference between <code>run</code> and <code>uses</code> in GitHub Actions?</summary>

The main difference:

- `run` executes shell commands directly on the runner.
- `uses` runs a GitHub Action that already exists, either from the Marketplace or from your own repository.

### 1. `run` example

Use `run` to execute Linux commands, scripts, or build commands.

```yaml
steps:
  - name: Check current directory
    run: pwd

  - name: List files
    run: ls -la

  - name: Build Java application
    run: mvn clean package
```

**Real-time example:** in a CI pipeline, I use `run` to compile a Java application with Maven, run shell scripts, or run tests.

### 2. `uses` example

Use `uses` to call an existing GitHub Action.

```yaml
steps:
  - name: Checkout code
    uses: actions/checkout@v4

  - name: Set up Java
    uses: actions/setup-java@v4
    with:
      distribution: temurin
      java-version: '17'
```

**Real-time example:** before building a Java application, I use `actions/checkout` to download the repository code and `actions/setup-java` to install Java on the runner.

### Key differences

| Feature | `run` | `uses` |
| --- | --- | --- |
| Purpose | Executes shell commands | Executes an existing action |
| Examples | `mvn clean package`, `ls`, `pwd` | `actions/checkout@v4` |
| What it contains | Shell commands or scripts | A reference to an action |
| `with` inputs | Not used | Commonly used to pass inputs to the action |
| Typical use | Build, test, script execution | Checkout code, set up tools, upload artifacts |

A single step can have either `run` or `uses`, not both.

### 3. Real-time DevOps pipeline example

```yaml
name: Java CI Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout source code
        uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'

      - name: Build application
        run: mvn clean package
```

Here, `uses` gets the code and prepares the environment, and `run` executes the Maven build.

### Interview answer

> "In GitHub Actions, `run` executes shell commands or scripts directly on the runner, while `uses` calls an existing GitHub Action. For example, I use `actions/checkout` to get the source code and `actions/setup-java` to set up Java. Then I use `run: mvn clean package` to build the application. Both are used together in a typical CI/CD pipeline."

</details>

<details><summary>Q3. If I want my pipeline to run automatically in GitHub Actions, what should I do?</summary>

### Interview-style answer

In GitHub Actions, we use the `on` keyword to trigger a workflow automatically on events such as a code push, a pull request, or a schedule.

For example, to run the pipeline whenever a developer pushes code to the `main` branch, I configure the `push` trigger in the workflow YAML file.

### 1. Run automatically when code is pushed

Create the file `.github/workflows/ci.yml`:

```yaml
name: CI Pipeline

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build application
        run: echo "Building the application"
```

How it works:

1. A developer pushes code to the `main` branch.
2. GitHub detects the `push` event.
3. GitHub Actions starts the workflow automatically.
4. The runner checks out the code and runs the build step.

### 2. Other ways to trigger a pipeline

| Trigger | Purpose | Example |
| --- | --- | --- |
| `push` | Run when code is pushed | Developer pushes code to `main` |
| `pull_request` | Run when a PR is opened or updated | Developer creates a PR |
| `schedule` | Run at a set time | Daily security scan |
| `workflow_dispatch` | Run manually from GitHub | Engineer clicks **Run workflow** |

To run the pipeline daily at midnight UTC:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'
```

You can combine several triggers in one workflow:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### Interview answer to remember

> "To run a GitHub Actions pipeline automatically, I configure triggers with the `on` keyword in the workflow YAML file. I use `push` to trigger the pipeline whenever code is pushed to the `main` branch, and `pull_request` to validate code before merging. I can also use `schedule` for periodic jobs. In my DevOps workflow, the CI pipeline triggers on code changes and runs build, tests, and security scans automatically."

**Important:** the workflow file must be committed under `.github/workflows/` in the repository. Scheduled workflows use UTC, run only from the default branch, and can be delayed when GitHub is under high load.

</details>
