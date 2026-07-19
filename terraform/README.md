# Terraform Interview Topics

Legend: ✅ covered · — not covered

Terraform detailed notes are consolidated in `notes.txt`. The former `notes1.txt` prompts are covered with complete answers in `questions.txt` and `notes.txt`.

| Topic | `summary.txt` | `questions.txt` | `notes.txt` |
| --- | :---: | :---: | :---: |
| Terraform workflow: init, plan, and apply | ✅ | ✅ | ✅ |
| Resources and data sources | ✅ | ✅ | ✅ |
| Variables, outputs, and locals | ✅ | ✅ | ✅ |
| Terraform modules | ✅ | ✅ | ✅ |
| Providers and version locking | ✅ | ✅ | ✅ |
| Backends and remote state | ✅ | ✅ | ✅ |
| State locking, backup, and recovery | ✅ | ✅ | ✅ |
| State security and secrets | ✅ | ✅ | ✅ |
| Workspaces and environment isolation | ✅ | ✅ | ✅ |
| Importing existing resources | — | ✅ | ✅ |
| Drift detection and remediation | — | ✅ | ✅ |
| Resource dependencies | — | ✅ | ✅ |
| `count` vs. `for_each` | — | ✅ | — |
| Lifecycle rules and deletion protection | — | ✅ | ✅ |
| Taint, replace, and resource recreation | — | ✅ | — |
| Terraform testing and policy compliance | — | ✅ | ✅ |
| CI/CD and approval workflows | ✅ | ✅ | ✅ |
| Multi-environment deployments | ✅ | ✅ | ✅ |
| Multi-region and multi-cloud design | — | ✅ | ✅ |
| Large-state and performance optimization | — | ✅ | ✅ |
| Terraform troubleshooting | — | ✅ | ✅ |
| Terraform Enterprise architecture | ✅ | ✅ | — |
| Sentinel, RBAC, audit logs, and private registry | ✅ | ✅ | — |
| Infrastructure requirements gathering | — | ✅ | — |

## Coverage Gaps

### Questions or notes not yet covered as dedicated summary topics

- Importing existing resources
- Drift detection and remediation
- Resource dependencies
- `count` vs. `for_each`
- Lifecycle rules and deletion protection
- Taint, replace, and resource recreation
- Terraform testing and policy compliance
- Multi-region and multi-cloud design
- Large-state and performance optimization
- Terraform troubleshooting
- Infrastructure requirements gathering

## Distributed Scenario Material

- `scenario-questions.txt` contains 50 detailed scenario answers.
- Terraform state, drift, security, modules, policy, CI/CD, performance, import, and recovery scenarios.
- Terraform questions whose primary subject is network design are maintained in [`networking/terraform`](../networking/terraform/README.md).
