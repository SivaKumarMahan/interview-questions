# Scenario-Based Content Routing

The former `scenario-based` collection was reviewed and distributed by primary topic. Scenario answers remain separate from the curated core questions in a `scenario-questions.txt` file within each destination.

## Question Distribution

| Destination | Unique questions |
| --- | ---: |
| Kubernetes | 65 |
| Terraform | 50 |
| Jenkins | 29 |
| Cross-cloud and networking | 17 |
| Monitoring and observability | 14 |
| Generic CI/CD | 12 |
| DevSecOps | 11 |
| SRE | 9 |
| Testing tools | 7 |
| Azure DevOps | 7 |
| Docker | 5 |
| Databases | 5 |
| FinOps | 4 |
| GitOps | 3 |
| Artifact repositories | 3 |
| Linux | 3 |
| Helm | 1 |
| General platform scenarios | 1 |

The source contained 256 numbered questions. Normalized exact-question comparison produced 246 unique questions and 10 exact duplicates. The duplicate copies had identical answer blocks, so they were consolidated without losing a distinct answer.

## Supporting-File Distribution

- `interview-round-notes-organized.md` → split by its 13 major sections into Linux, Docker, Kubernetes, CI/CD, Git, Terraform, AWS, monitoring, DevSecOps, SRE, coding challenges, behavioral, and process/tooling `interview-round-notes.md` files.
- `notes.txt` → SonarQube/Trivy/Jenkins quality flow under `testing-tools`, Azure database connectivity under `azure-services`, and webhook behavior under `CI/CD`.
- `notes1.txt` → Docker installation under `ansible`, learning and collaboration under `Others/behavioral`, Nginx/network troubleshooting under `networking/proxies-and-load-balancing`, dynamic typing under `python`, and Jenkins-to-Kubernetes deployment under `jenkins`. Kubernetes scaling content is represented in the detailed Kubernetes scenario answers.
- `notes2.txt` → its Terraform secret/state, reusable pipeline, ALB/NLB, and IRSA material was matched to existing detailed Terraform, CI/CD, AWS, and Kubernetes coverage; the unique load-balancer comparison was retained in `networking/aws/load-balancer-notes.md`.
- `summary.txt` → Key Vault rotation into AKS under `azure-services` and multi-environment Helm deployment under `helm`.
- `terraform-kubernetes-linux-notes.txt` → matched against existing detailed Terraform Enterprise/state, Kubernetes operations, and Linux command answers; no shorter duplicate was added.
- `secrets-team-collaboration-notes.txt` → secret, token, Terraform requirement, DNS, Pod-networking, and latency prompts were matched to existing detailed topic answers, including the new `networking` topic folders. Unique collaboration and SQL-performance prompts were answered under `Others/behavioral` and `Others/databases`.

Unsafe or obsolete examples were corrected during distribution. Examples include enforcing a failing Trivy exit code, keeping credentials out of Jenkinsfiles, using signed Docker repositories in Ansible, and avoiding scheduled rotation as the only Key Vault synchronization mechanism.
