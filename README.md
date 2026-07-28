# DevOps Interview Questions

This repository contains interview questions, short notes, detailed answers, scenarios, commands, and examples for DevOps, cloud, Kubernetes, CI/CD, security, networking, monitoring, and scripting.

## How to use this repository

Each topic normally contains some of these files:

- `summary.md` — learn the main ideas.
- `questions.md` — practise common interview questions.
- `scenario-questions.md` — practise troubleshooting and design situations.
- `notes.md` — review detailed commands and examples.
- `interview-round-notes.md` — prepare concise answers from real interview rounds.

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
| CI/CD | Continuous Integration and Continuous Delivery or Deployment |
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
| VPA | Vertical Pod Autoscaler |

## Interview tip

Use technical terms when the interviewer expects them, but explain them in plain language. For example:

> I make the script idempotent, which means it is safe to run again without creating duplicate users or resources.

This shows technical knowledge while keeping the answer clear.
