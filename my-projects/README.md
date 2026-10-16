# My Projects

> How to turn the projects on your resume into strong STAR answers for Senior and Lead DevOps interviews, with one template file per project to fill in.

## What These Files Are For

Interviewers at senior and lead level almost always ask "Tell me about a project you led" and then go deep with follow-up questions. These files hold the structure, the likely follow-up questions, and a draft answer for each one.

Each file matches one project or bullet on your resume. Lines marked **From resume:** repeat a claim that is already on your resume, so the interviewer may ask you to prove it. The rest is a draft built from the resume: it describes how this kind of work is normally done with the tools you list. Details that only you can know, such as counts, versions, before and after numbers, and specific incidents, are marked `[Confirm: …]`. Check every draft line against what really happened, and replace each `[Confirm: …]` before you rely on a file in an interview.

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

- **Only use a headline number you can explain.** Your resume claims about 50% faster release lead time, about 25% lower cloud cost, about 40% fewer failed deployments, 99.9% availability on AKS, and more than 70% faster environment provisioning with Bicep. Use each one only in the project where it really came from, and only if you can say how it was measured: the definition, the data source, and the before and after periods.

  | Number | Where the resume puts it | Project file | How to back it up |
  | --- | --- | --- | --- |
  | ~50% faster release lead time | Impressico, CI/CD bullet | [04](resume-projects/04-cicd-devsecops-quality-gates.md) | Commit-to-production time from pipeline run history, before vs after. `[Confirm: periods compared]` |
  | ~40% fewer failed deployments | Key Achievements only | [04](resume-projects/04-cicd-devsecops-quality-gates.md) | Failed or rolled-back production deployments per month. `[Confirm: which employer and project]` |
  | 99.9% availability | Impressico, AKS bullet | [01](resume-projects/01-aks-zero-downtime-upgrades.md) | Availability tests or request success rate over 30 days. `[Confirm: SLI and tool]` |
  | >70% faster environment provisioning | Infosys, Bicep provisioning bullet | [03](resume-projects/03-bicep-least-privilege-rbac.md) | Ticket-to-ready time for a new environment, manual vs Bicep. `[Confirm: before and after times]` |
  | ~25% lower cloud cost | Infosys, Terraform/Bicep provisioning bullet; Key Achievements says "estimated" and credits right-sizing and lifecycle cleanup | None of the 7 files; use it as a side result of the IaC work in [03](resume-projects/03-bicep-least-privilege-rbac.md) or [05](resume-projects/05-vmss-autoscale-backup-automation.md) | Azure Cost Management, monthly spend before vs after, normalised for growth. Call it an estimate, as the resume does. `[Confirm: scope and period]` |
- **Quantify results.** "Reduced alert noise by about 60%" beats "reduced alert noise". If you do not have an exact number, give an honest estimate and say it is an estimate. Good metrics: time saved per week, MTTD or MTTR change, cost per month, incidents per quarter, manual steps removed, adoption by number of teams.
- **Show trade-offs.** Say which options you considered and why you rejected them. "We considered X, but it needed Y, so we chose Z." This is what separates a lead answer from a senior engineer answer.
- **Be clear about your role vs the team.** Use "I" for what you did and "we" for what the team did. Interviewers listen for this. Do not take credit for others' work, and do not hide your own behind "we".
- **Show influence, not only implementation.** Who did you convince? Which teams adopted it? How did you handle disagreement?
- **Include what went wrong.** One honest problem and how you handled it makes the story believable.
- **End with the lesson.** "Next time I would ..." shows reflection.
- **Prepare the diagram.** Be ready to sketch the architecture on a whiteboard in under two minutes.

## How to Use the Project Files

1. **Check the STAR draft** in each file against what really happened. Change anything that is not true, and replace each `[Confirm: …]`.
2. **Check the architecture diagram.** It is a draft from the resume; remove anything that did not exist and add what is missing.
3. **Check the tech stack** and be ready to explain why each piece was chosen.
4. **Rewrite each follow-up answer in your own words.** Use the hints to check your answer covers what interviewers look for.
5. **Practise out loud.** Time yourself: a two-minute version and a five-minute version.
6. **Check confidentiality.** Remove internal names, customer names, and anything under NDA. Describe systems generically if needed.

## Project Files

| # | Project | Employer | Resume bullet it maps to | File |
| --- | --- | --- | --- | --- |
| 1 | AKS node pools and zero-downtime upgrades | Impressico | AKS node pools, cluster autoscaler, rolling updates, and zero-downtime version upgrades with Bicep and Shell/Python; 99.9% availability | [01-aks-zero-downtime-upgrades.md](resume-projects/01-aks-zero-downtime-upgrades.md) |
| 2 | Docker, ACR, and Helm standards with Go-based RBAC automation | Impressico | Standardised Docker, ACR, and Helm; Helm-based Kubernetes RBAC automation in Go across clusters | [02-helm-rbac-automation-go.md](resume-projects/02-helm-rbac-automation-go.md) |
| 3 | Least-privilege Azure RBAC and provisioning with Bicep | Infosys (custom roles continued at Impressico) | Bicep modules for custom roles and RBAC assignments replacing Owner and Contributor; Bicep automation of service connections and VMs; more than 70% faster provisioning | [03-bicep-least-privilege-rbac.md](resume-projects/03-bicep-least-privilege-rbac.md) |
| 4 | CI/CD pipelines with DevSecOps quality gates | Impressico (Jenkins and Classic Release pipelines at Infosys) | CI/CD across Azure DevOps, GitHub Actions, GitLab CI, and Jenkins with SonarQube, Trivy, Checkov, secret scanning, Azure Policy, and branch policies; about 50% faster lead time and about 40% fewer failed deployments | [04-cicd-devsecops-quality-gates.md](resume-projects/04-cicd-devsecops-quality-gates.md) |
| 5 | VM Scale Set autoscaling and backup automation | Infosys | VMSS autoscale with rolling upgrades and zones; Shell/Python backups with Recovery Services Vault, PostgreSQL backups, restore drills, and failure alerts | [05-vmss-autoscale-backup-automation.md](resume-projects/05-vmss-autoscale-backup-automation.md) |
| 6 | Azure monitoring, Prometheus and Grafana, and Splunk alerting | Infosys (Azure Monitor, Splunk); Impressico (Prometheus, Grafana) | Azure Monitor metric and KQL log alerts, App Insights availability tests, Action Groups with severity routing; Prometheus and Grafana on AKS; Splunk integration | [06-azure-monitoring-and-splunk-alerting.md](resume-projects/06-azure-monitoring-and-splunk-alerting.md) |
| 7 | Azure Functions with Service Bus for document generation | Infosys | Service Bus-triggered Azure Functions that process requests asynchronously and write documents to Storage | [07-azure-functions-service-bus-documents.md](resume-projects/07-azure-functions-service-bus-documents.md) |

Employers come from the resume: Impressico Business Solutions (Jan 2025 to now) and Infosys (Mar 2021 to Dec 2024). Keep the same employer for each project every time you tell the story, so your timeline stays consistent when the interviewer asks.

## Hands-On Scenarios and Practice Projects

These come from personal notes and labs, not from resume bullets. Use them only for work you actually did, and say clearly when something was a lab.

| # | Topic | File |
| --- | --- | --- |
| 8 | Consumption Logic App reading a firewall-protected Storage account (managed identity + resource instance rule) | [08-logic-app-secured-storage-access.md](resume-projects/08-logic-app-secured-storage-access.md) |
| 9 | Fifteen hands-on practice projects, plus notes on Storage snapshots, Azure Policy, vulnerability scanners, and PDBs | [09-hands-on-practice-projects.md](resume-projects/09-hands-on-practice-projects.md) |

## Real Project Write-Ups

Detailed notes from real project work live in the separate [my-projects](https://github.com/SivaKumarMahan/my-projects) repo. Use them as source material for the STAR answers above:

- [Project 1](https://github.com/SivaKumarMahan/my-projects/blob/main/real-projects/project1/README.md): Warehouse Management System on AKS (Azure, AKS, Bicep Deployment Stacks, Azure DevOps, Helm)
- [Project 2](https://github.com/SivaKumarMahan/my-projects/blob/main/real-projects/project2/README.md): AWS platform and operations automation (AWS, OpenTofu, GitHub Actions, ECS, Ansible, Databricks)
- [Project 3](https://github.com/SivaKumarMahan/my-projects/blob/main/real-projects/project3/README.md): AI news and contracts platform (Azure Bicep, Jenkins + SonarQube, Azure DevOps, Terraform, AWS CDK, CloudFormation)
