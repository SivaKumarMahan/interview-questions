# AI Assistants for Terraform and AKS Work

> How to use an AI coding assistant in the terminal or IDE (for example Gemini CLI, Claude Code, or GitHub Copilot) for Terraform modules, AKS, and environment-based infrastructure (Dev, UAT, Prod), and how to explain it safely in an interview.

## One-line explanation

I use an AI assistant to draft, explain, and review Terraform and Kubernetes code faster, but every change still goes through `fmt`, `validate`, `plan`, security scanning, code review, and an approved pipeline, exactly like code written by hand.

## 30-second interview answer

> "I use AI assistants as a productivity tool for infrastructure work. For example, I ask it to scaffold a Terraform module for an AKS cluster with a managed identity, explain an existing module before I change it, help read a failing deployment's events and logs, or suggest improvements based on best practices. I treat the output as a draft: I review every line, pin provider versions, run fmt, validate, plan, and a security scan, and the change goes through a pull request and the normal pipeline with approvals. I never paste secrets, state files, or customer data into the tool."

## Where it helps

| Task | Example prompt | What I still check myself |
| --- | --- | --- |
| Scaffolding | "Create a Terraform module for an AKS cluster with a system-assigned managed identity, Azure CNI overlay, and a separate user node pool. Use azurerm 4.x and variables for everything environment-specific." | Provider version, argument names against the docs, defaults such as SKU and node size |
| Explaining code | "Explain what this Terraform module creates, its inputs and outputs, and what would be replaced if I change `vnet_subnet_id`." | That the explanation matches `terraform plan` |
| Troubleshooting | "My Deployment is in CrashLoopBackOff. Here are `kubectl describe` events and the last 50 log lines (secrets removed). What are the likely causes?" | Reproduce the cause; never apply a fix to Prod without a plan or review |
| Review and best practices | "Review this IaC for security and best practices: public exposure, missing tags, hardcoded values, missing lifecycle rules." | Compare with tfsec/Trivy or Checkov results and team standards |
| Environments | "Refactor this root module so Dev, UAT, and Prod use the same modules with separate tfvars and separate state." | State migration steps (`moved` blocks) and that the plan shows no unexpected replacements |
| Documentation | "Write a README for this module with inputs, outputs, and an example." | Accuracy of examples |

## How it fits the workflow

```text
Prompt (no secrets, no state, no customer data)
        |
        v
AI draft: module / manifest / fix suggestion
        |
        v
Engineer review: read every line, check docs, pin versions
        |
        v
terraform fmt -> validate -> plan   |   helm lint / kubectl --dry-run=server
        |
        v
Security scan (Trivy / tfsec / Checkov) + pull request review
        |
        v
Pipeline with approvals -> Dev -> UAT -> Prod
```

## Guardrails

- **No sensitive data in prompts:** no secrets, connection strings, `terraform.tfstate`, `.tfvars` with real values, kubeconfig files, or customer data. State files contain secrets in plain text.
- **Use approved tools only:** check the company policy on which AI tools are allowed and whether code is used for training.
- **Verify against documentation:** AI can invent arguments, use deprecated resources, or mix provider versions. `terraform validate` and the provider docs catch most of this.
- **The plan is the truth:** never trust a description of what a change does; read `terraform plan` and look for replace or destroy.
- **Least privilege for the assistant:** if the tool can run commands, do not give it credentials that can change Production.
- **Same review and pipeline as human code:** AI-written code gets no shortcut around pull requests, scans, or approvals.

## What to say about results

Be specific and honest. Good: "It cut the time to scaffold a new module set from about a day to a couple of hours, and I spent the saved time on review and testing." Avoid saying the AI "built the infrastructure"; you designed, reviewed, and deployed it.

TODO (Siva): add your real example: which tool, which task, and what you checked before merging.

## Interview questions

<details><summary>Q1. [Basic] How do you use AI tools in your DevOps work?</summary>

**Answer:**

As an assistant, not as an approver. I use it to scaffold Terraform modules and Helm charts, explain unfamiliar code, summarize logs and events while troubleshooting, and suggest best-practice improvements. Every output is reviewed, validated with `fmt`, `validate`, and `plan`, scanned, and merged through a pull request and the normal pipeline.

</details>

<details><summary>Q2. [Intermediate] What risks do you see with AI-generated Terraform, and how do you control them?</summary>

**Answer:**

It can invent or use deprecated arguments, choose insecure defaults (public network access, missing encryption, broad role assignments), or create changes that replace resources. I control this by pinning provider versions, running `terraform validate` and a security scanner, reading the plan for replacements and destroys, and requiring code review. I also keep secrets and state files out of prompts.

</details>

<details><summary>Q3. [Intermediate] A deployment to AKS is failing. How would you use an AI assistant to help, safely?</summary>

**Answer:**

I collect the facts first: `kubectl describe pod`, events, `kubectl logs --previous`, and the rollout status. I remove any secrets or customer data, then ask the assistant for likely causes and checks. I verify each suggestion myself in the cluster, and any fix goes through the normal pipeline instead of a manual change in Production.

</details>

<details><summary>Q4. [Advanced] How would you introduce AI assistants to a platform team without creating risk?</summary>

**Answer:**

Start with an approved tool and a short policy: what data may be shared, and that AI output follows the same review rules. Use it first for low-risk work such as documentation, tests, and module scaffolding in non-production. Keep the existing guardrails, such as branch policies, required scans, plan review, and environment approvals, so quality does not depend on the tool. Measure the effect (lead time, review comments, defects) before expanding.

</details>
