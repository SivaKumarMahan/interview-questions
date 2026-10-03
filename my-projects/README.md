# My Projects

> How to turn the projects on your resume into strong STAR answers for Senior and Lead DevOps interviews, with one template file per project to fill in.

## What These Files Are For

Interviewers at senior and lead level almost always ask "Tell me about a project you led" and then go deep with follow-up questions. These files are **templates**. They hold the structure and the likely follow-up questions; the real facts must come from you.

Each file matches one project or bullet on your resume. Lines marked **From resume:** repeat a claim that is already on your resume, so the interviewer may ask you to prove it. Every other place that needs your real story is marked `TODO (Siva):`. Nothing in these files is an invented fact about your work. Replace every TODO before you rely on a file in an interview.

## The STAR Format

| Letter | Meaning | What to say | Rough share of the answer |
| --- | --- | --- | --- |
| **S** | Situation | The context: the system, the team, the problem, why it mattered | ~15% |
| **T** | Task | Your specific responsibility and the goal or constraint | ~10% |
| **A** | Action | What **you** did, step by step, and why you chose that approach | ~55% |
| **R** | Result | The outcome, with numbers, plus what you learned | ~20% |

Most people spend too long on the Situation and rush the Action and Result. The Action is where the interviewer judges your skill. The Result is where they judge your impact.

A two-minute answer is usually right for the first telling. Let the interviewer pull you deeper with follow-up questions.

## Tips for Lead-Level Answers

- **Only use a headline number you can explain.** Your resume claims about 50% faster release lead time, about 25% lower cloud cost, about 40% fewer failed deployments, 99.9% availability on AKS, and more than 70% faster environment provisioning with Bicep. Use each one only in the project where it really came from, and only if you can say how it was measured: the definition, the data source, and the before and after periods. TODO (Siva): confirm the source and method for each number, and which project (if any) the 25% cost reduction belongs to.
- **Quantify results.** "Reduced alert noise by about 60%" beats "reduced alert noise". If you do not have an exact number, give an honest estimate and say it is an estimate. Good metrics: time saved per week, MTTD or MTTR change, cost per month, incidents per quarter, manual steps removed, adoption by number of teams.
- **Show trade-offs.** Say which options you considered and why you rejected them. "We considered X, but it needed Y, so we chose Z." This is what separates a lead answer from a senior engineer answer.
- **Be clear about your role vs the team.** Use "I" for what you did and "we" for what the team did. Interviewers listen for this. Do not take credit for others' work, and do not hide your own behind "we".
- **Show influence, not only implementation.** Who did you convince? Which teams adopted it? How did you handle disagreement?
- **Include what went wrong.** One honest problem and how you handled it makes the story believable.
- **End with the lesson.** "Next time I would ..." shows reflection.
- **Prepare the diagram.** Be ready to sketch the architecture on a whiteboard in under two minutes.

## How to Use the Project Files

1. **Fill in Situation, Task, Action, Result** in each file. Keep each section to a few bullets.
2. **Draw the real architecture.** Replace the placeholder Mermaid diagram with your real components.
3. **List the real tech stack** and be ready to explain why each piece was chosen.
4. **Answer every follow-up question** under Interview Questions in your own words. Use the hints to check your answer covers what interviewers look for.
5. **Practise out loud.** Time yourself: a two-minute version and a five-minute version.
6. **Check confidentiality.** Remove internal names, customer names, and anything under NDA. Describe systems generically if needed.

## Project Files

| # | Project | Resume bullet it maps to | File |
| --- | --- | --- | --- |
| 1 | AKS node pools and zero-downtime upgrades | AKS node pools, cluster autoscaler, rolling updates, and zero-downtime version upgrades with Bicep and Shell/Python; 99.9% availability | [01-aks-zero-downtime-upgrades.md](01-aks-zero-downtime-upgrades.md) |
| 2 | Docker, ACR, and Helm standards with Go-based RBAC automation | Standardised Docker, ACR, and Helm; Helm-based Kubernetes RBAC automation in Go across clusters | [02-helm-rbac-automation-go.md](02-helm-rbac-automation-go.md) |
| 3 | Least-privilege Azure RBAC and provisioning with Bicep | Bicep modules for custom roles and RBAC assignments replacing Owner and Contributor; Bicep automation of service connections and VMs; more than 70% faster provisioning | [03-bicep-least-privilege-rbac.md](03-bicep-least-privilege-rbac.md) |
| 4 | CI/CD pipelines with DevSecOps quality gates | CI/CD across Azure DevOps, GitHub Actions, GitLab CI, and Jenkins with SonarQube, Trivy, Checkov, secret scanning, Azure Policy, and branch policies; about 50% faster lead time and about 40% fewer failed deployments | [04-cicd-devsecops-quality-gates.md](04-cicd-devsecops-quality-gates.md) |
| 5 | VM Scale Set autoscaling and backup automation | VMSS autoscale with rolling upgrades and zones; Shell/Python backups with Recovery Services Vault, PostgreSQL backups, restore drills, and failure alerts | [05-vmss-autoscale-backup-automation.md](05-vmss-autoscale-backup-automation.md) |
| 6 | Azure monitoring, Prometheus and Grafana, and Splunk alerting | Azure Monitor metric and KQL log alerts, App Insights availability tests, Action Groups with severity routing; Prometheus and Grafana on AKS; Splunk integration | [06-azure-monitoring-and-splunk-alerting.md](06-azure-monitoring-and-splunk-alerting.md) |
| 7 | Azure Functions with Service Bus for document generation | Service Bus-triggered Azure Functions that process requests asynchronously and write documents to Storage | [07-azure-functions-service-bus-documents.md](07-azure-functions-service-bus-documents.md) |

TODO (Siva): for each project, note whether it was at Impressico (Jan 2025 to now) or Infosys (Mar 2021 to Dec 2024), so your timeline stays consistent when the interviewer asks.

See also: [Leadership](../leadership/01-architecture-decision-records.md) for how to structure behavioural answers about decisions, incidents, mentoring, and stakeholders.
