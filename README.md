# DevOps Interview Questions

This repository contains interview questions, short notes, detailed answers, scenarios, commands, and examples for DevOps, cloud, Kubernetes, CI/CD, GitOps, security, networking, monitoring, and scripting.

## How this repository is organized

Each tool or subject has its own folder, split **by topic** into 2–10 numbered files:

```text
kubernetes/
├── 01-architecture-and-fundamentals.md
├── 02-workloads-and-pod-lifecycle.md
├── ...
└── 09-observability-backup-dr.md
```

- **Numbers give the study order.** `01` is the fundamentals, and the last files cover troubleshooting, production, and advanced topics.
- **Every file has the same layout:**
  - a one-line scope at the top saying what the file covers
  - `## Key Concepts`: the main ideas, explanations, commands, and examples
  - `## Interview Questions`: numbered questions with answers, with related questions next to each other
- **Tags show where a question came from:**
  - *(asked in interview round)*: the question was asked in a real interview
  - *(scenario)*: a troubleshooting or design situation

To revise one topic, open its file and read Key Concepts first, then practise the questions.

## Topic index

### Containers, orchestration, and GitOps

| Folder | Files | Topics |
| --- | --- | --- |
| [docker](docker/) | 6 | Fundamentals, Dockerfiles, image optimization and multi-stage builds, networking/volumes/Compose, security and CI/CD, troubleshooting |
| [kubernetes](kubernetes/) | 9 | Architecture, workloads and Pod lifecycle, networking and traffic, storage and StatefulSets, scheduling/resources/autoscaling, security and RBAC, deployments and upgrades, troubleshooting, observability/backup/DR |
| [helm](helm/) | 4 | Chart structure, releases/values/hooks, multi-environment and reusable charts, security/CI/CD/troubleshooting |
| [gitops](gitops/) | 2 | GitOps fundamentals (push vs. pull, drift, rollback, GitOps at scale), Argo CD |

### CI/CD, source control, and artifacts

| Folder | Files | Topics |
| --- | --- | --- |
| [ci-cd](ci-cd/) | 7 | Fundamentals and tooling, pipeline design, environments and approvals, deployment strategies and rollback, security, runners and performance, troubleshooting |
| [jenkins](jenkins/) | 9 | Architecture, pipeline as code and shared libraries, pipeline design, Kubernetes deployments, SCM triggers, credentials and security, agents and HA, performance, troubleshooting |
| [github-actions](github-actions/) | 3 | Workflows, cross-repository triggers, end-to-end pipelines, security and troubleshooting |
| [gitlab](gitlab/) | 3 | Repositories and collaboration, CI/CD pipelines, secrets/deployments/troubleshooting |
| [azure-devops](azure-devops/) | 6 | Platform overview, Azure Repos and branching, pipeline design and templates, deployments and approvals, security and secrets, troubleshooting |
| [git](git/) | 4 | Daily workflow, branching strategies and releases, pull requests and merge conflicts, recovery and troubleshooting |
| [artifact-repositories](artifact-repositories/) | 8 | Repository selection, Azure Artifacts/Artifactory/GitHub Packages, Nexus, versioning and promotion, signing and access control, HA and backup, troubleshooting |
| [testing-tools](testing-tools/) | 3 | Pipeline testing and quality gates, security scanning and supply chain, Checkov |

### Infrastructure as Code and configuration

| Folder | Files | Topics |
| --- | --- | --- |
| [terraform](terraform/) | 10 | Workflow, variables/functions/meta-arguments, state and backends, modules, environments and workspaces, providers and multi-cloud, lifecycle, drift and import, CI/CD/testing/security, troubleshooting |
| [bicep](bicep/) | 3 | Structure, deployment scopes/environments/secrets, validation and troubleshooting |
| [ansible](ansible/) | 8 | Setup, inventory, ad hoc commands and modules, playbooks, variables/loops/conditions, roles and Galaxy, Vault and production practices, debugging |
| [yaml](yaml/) | 4 | Syntax, worked examples, common mistakes and validation, YAML in DevOps tools |

### Cloud

| Folder | Files | Topics |
| --- | --- | --- |
| [aws](aws/) | 4 | Architecture and HA, compute/storage/serverless, networking/security/IAM, monitoring and troubleshooting |
| [azure](azure/) | 6 | Architecture, compute and app hosting (VMs, App Service, Functions, ACR, AKS), integration and messaging (Service Bus, Event Grid), storage/networking/reliability, identity/Key Vault/governance, automation/monitoring/cost |

### Operating systems and scripting

| Folder | Files | Topics |
| --- | --- | --- |
| [linux](linux/) | 9 | Fundamentals, files and text processing, users/permissions/SSH, processes and services, disks and filesystems, networking, packages, logs, performance troubleshooting |
| [windows](windows/) | 3 | Administration and patching, logs and troubleshooting, networking and remote access |
| [shell-scripting](shell-scripting/) | 2 | Bash fundamentals and error handling, automation scripts in practice |
| [python](python/) | 5 | Fundamentals, functions and classes, automation/APIs/data, logging with Loguru, coding challenges |

### Observability, operations, and networking

| Folder | Files | Topics |
| --- | --- | --- |
| [monitoring-tools](monitoring-tools/) | 10 | Observability and APM, Prometheus, Grafana and Alertmanager, logging, host monitoring, Kubernetes, databases, AWS and Azure, CI/CD and IaC, FinOps |
| [ops](ops/) | 5 | Operations overview, DevSecOps, SRE, FinOps, AIOps |
| [networking](networking/) | 4 subfolders | Networking fundamentals (including a common ports reference), proxies and load balancing, network security, multi-cloud networking. Tool-specific networking lives in each tool's folder. |

## Other folders

| Folder | What it contains |
| --- | --- |
| [cheatcodes](cheatcodes/) | Quick command cheat-sheets per tool: kubectl, Docker, Git, Terraform, Ansible, Argo CD, Jenkins, GitHub Actions, AWS CLI, Linux, shell, TLS |
| [repetitive-questions](repetitive-questions/) | Questions asked again and again across interviews: CI/CD flow, branching, rollback, zero-downtime deployment, secrets, sample pipelines and Dockerfiles, production issues |
| [real-interview-questions](real-interview-questions/) | Question sets from real interviews at specific companies |
| [managerial-round](managerial-round/) | Managerial-round questions and company background |
| [ai](ai/) | AI-assisted DevOps project ideas: code review, cloud cost, Kubernetes agent and upgrades, Terraform drift detection |
| [others](others/) | Behavioral, microservices, databases, cloud, coding challenges, general scenarios, and interview preparation notes |

## How to structure an answer

You do not need to memorize every sentence. For each answer, remember this simple structure:

```text
What it is
-> why it is used
-> small example
-> how to verify it
-> common problem or limitation
```

For a troubleshooting question, use:

```text
understand the impact
-> check Events, logs, and metrics
-> identify the cause
-> restore the service
-> verify the user request
-> prevent the issue from happening again
```

## Common technical terms in simple words

| Term | Simple meaning |
| --- | --- |
| Artifact | A file produced by a build, such as a JAR, ZIP, package, or container image |
| Backoff | Waiting longer between each retry |
| Blast radius | The number of users, services, or resources that a failure can affect |
| Cardinality | The number of unique metric label combinations; too many can increase monitoring cost and memory use |
| Drift | A difference between the configuration in code and the real system |
| Failure domain | A group of resources that can fail together, such as one availability zone |
| GitOps | Using a Git repository as the source of truth for deployments; a controller such as Argo CD keeps the cluster matching Git |
| Idempotent | Safe to run more than once without creating unwanted extra changes |
| Immutable | Not changed after creation; publish a new version instead of editing the old one |
| Least privilege | Giving only the permissions needed for the task |
| Reconciliation | Making the real system match the desired configuration |
| Saturation | How close CPU, memory, disk, connections, or another resource is to its limit |
| Telemetry | Monitoring data such as metrics, logs, and traces |

## Common abbreviations

| Abbreviation | Meaning |
| --- | --- |
| ACR | Azure Container Registry |
| AKS | Azure Kubernetes Service |
| APM | Application Performance Monitoring |
| CI/CD | Continuous Integration and Continuous Delivery or Deployment |
| EKS | Amazon Elastic Kubernetes Service |
| HPA | Horizontal Pod Autoscaler |
| IaC | Infrastructure as Code |
| mTLS | Mutual TLS; both sides verify each other's certificate |
| OIDC | OpenID Connect; often used by CI/CD to obtain short-lived cloud access |
| PDB | PodDisruptionBudget |
| PVC | PersistentVolumeClaim |
| RBAC | Role-Based Access Control |
| RPO | Recovery Point Objective; the maximum acceptable data-loss period |
| RTO | Recovery Time Objective; the target time to restore a service |
| SAST | Static Application Security Testing; scans source or compiled code |
| SBOM | Software Bill of Materials; a list of components in an artifact |
| SLO | Service Level Objective; the reliability target for a service |
| SRE | Site Reliability Engineering |
| VPA | Vertical Pod Autoscaler |

## Interview tip

Use technical terms when the interviewer expects them, but explain them in plain language. For example:

> I make the script idempotent, which means it is safe to run again without creating duplicate users or resources.

This shows technical knowledge while keeping the answer clear.
