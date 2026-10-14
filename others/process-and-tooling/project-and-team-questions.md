# About Your Project and Team

> The "tell me about your work" questions asked in almost every DevOps screening: project architecture, team size, how work arrives, who owns infrastructure, where services run, instance sizing, deployment and rollback strategies, and cost savings. Answers must match your resume; replace the examples with your own facts.

## Key Concepts

### How to answer these questions

- Be specific and consistent: the same numbers and tools as on your resume.
- Give **your** role ("I built", "I owned"), not only the team's.
- Keep each answer to 60–90 seconds, then stop and let the interviewer go deeper.
- Never invent numbers you can't explain. If asked "how did you measure it?", you need an answer.

## Interview Questions

<details><summary>Q1. [Basic] What is your project architecture?</summary>

**Answer:**

Describe it from code to production in one flow. Example (AWS):

```text
Developers ─► GitHub (PR + review) ─► Jenkins / GitHub Actions
   build ─► unit tests ─► SonarQube ─► Trivy ─► Docker image ─► ECR
   deploy ─► Helm / Argo CD ─► EKS (dev ─► qa ─► prod, approval before prod)
Infrastructure: Terraform (VPC, EKS, RDS, S3) with remote state and PR plans
Traffic: Route 53 ─► ALB (AWS Load Balancer Controller) ─► services in EKS
Monitoring: Prometheus + Grafana, logs in CloudWatch, alerts to Slack / PagerDuty
```

> "We run about 25 Java and Node.js microservices on EKS. Code is in GitHub; Jenkins builds, tests and scans every pull request, and pushes images to ECR. Deployments go through Helm charts, dev and QA automatically, and production after an approval. All infrastructure is Terraform with an S3 backend. We monitor with Prometheus and Grafana, keep logs in CloudWatch, and alert to Slack and PagerDuty. My part was the pipelines, the Terraform modules and the monitoring setup."

For an Azure project, swap in AKS, ACR, Azure DevOps or GitHub Actions, Key Vault and Azure Monitor.

</details>

<details><summary>Q2. [Basic] How many DevOps engineers are in your team, and how do you work with developers?</summary>

**Answer:**

Give the real number and the structure, for example:

> "We are five DevOps engineers supporting about eight development teams, roughly 60 developers. Two of us focus on the Kubernetes platform, two on CI/CD and tooling, and I handle infrastructure as code and monitoring. We have a weekly on-call rotation, join the developers' sprint planning when they need platform changes, and run a short weekly platform sync."

Mention collaboration: shared pipeline templates, documentation, office hours, and reviewing developers' Dockerfiles and Helm values.

</details>

<details><summary>Q3. [Basic] How do you receive work or tickets?</summary>

**Answer:**

> "Planned work comes as Jira stories in two-week sprints. Requests from developers, such as a new pipeline, a namespace or access, come through a Jira Service Management queue (or ServiceNow / Azure Boards in other companies) with a template so we get all the details. Incidents come from PagerDuty alerts and are tracked as incident tickets with a post-incident review. Production changes go through a change request with approval."

Mention prioritisation (incidents first, then blocked teams, then planned work) and SLAs if you had them.

</details>

<details><summary>Q4. [Basic] Who manages the infrastructure, and where are your microservices deployed?</summary>

**Answer:**

> "The DevOps or platform team owns the infrastructure, and everything is created through code: Terraform for cloud resources (VPC, EKS, databases, IAM), Ansible for the few VMs we still have, and Helm with Argo CD for Kubernetes resources. Nobody changes production in the console; changes go through pull requests with a plan review."

Where services run, depending on the project:

- **Kubernetes** (EKS or AKS) for most microservices.
- **ECS on Fargate** or **Azure Container Apps** for simpler services without a cluster to manage.
- **EC2 / VMs** for legacy or licensed software.
- **Lambda / Azure Functions** for event-driven tasks.

Explain why: for example, "Kubernetes because we have many services, need autoscaling and want one deployment model."

</details>

<details><summary>Q5. [Intermediate] Which instance types do you use, and how do you know they are sufficient?</summary>

**Answer:**

> "Our EKS worker nodes are mostly `m6i.xlarge` (4 vCPU, 16 GB) for general services, with a separate memory-optimised pool (`r6i.large`) for caching services. Dev uses smaller `t3.large` nodes."

How I decide and check:

- Start from the application's measured CPU and memory under load (load tests, Prometheus data), plus headroom of 20–30%.
- Watch utilisation, throttling, OOM kills and latency; for burstable `t3` instances also CPU credit balance, because they slow down when credits run out.
- Right-size with Compute Optimizer or Azure Advisor, and let the Cluster Autoscaler or Karpenter add nodes instead of over-sizing every node.
- Use Graviton (ARM) or Spot instances where workloads allow, to cut cost.

</details>

<details><summary>Q6. [Basic] Which deployment and rollback strategies have you used?</summary>

**Answer:**

| Strategy | How it works | When |
| --- | --- | --- |
| Rolling update | Replace Pods gradually (`maxSurge`, `maxUnavailable`) | Default for most stateless services |
| Blue-green | Run the new version beside the old, switch traffic at once | Risky releases that need an instant rollback |
| Canary | Send a small percentage of traffic to the new version, increase while metrics are healthy | High-traffic services (Argo Rollouts, Flagger, a service mesh) |
| Recreate | Stop the old version, start the new one | Apps that cannot run two versions at the same time |

Rollback options: `helm rollback`, `kubectl rollout undo`, Argo CD sync to the previous Git commit (or `git revert`), switching traffic back in blue-green, redeploying the previous image tag, or a previous AMI or launch template version for VMs. For Terraform there is no automatic rollback: you revert the code and apply again. Database changes need backward-compatible migrations so the application can be rolled back.

See [rollback strategy](../../repetitive-questions/rollback-strategy.md) and [zero-downtime deployment](../../repetitive-questions/zero-downtime-deployment.md).

</details>

<details><summary>Q7. [Intermediate] Your resume says you reduced cost by 40%. How did you do it?</summary>

**Answer:**

Break the number into concrete actions and explain how you measured it. Example:

> "Our monthly AWS bill was about $50,000. Over three months we brought it to about $30,000, measured in Cost Explorer with cost-allocation tags per team:
>
> - Moved stateless workloads to Spot instances through Karpenter, with on-demand fallback (the biggest saving, about 15%).
> - Right-sized over-provisioned node groups and Pod requests based on Prometheus data.
> - Scaled dev and QA to zero at night and at weekends.
> - Deleted unused EBS volumes, old snapshots and idle load balancers found by Terraform drift checks and Trusted Advisor.
> - Added S3 lifecycle policies to move old logs to Infrequent Access and Glacier.
> - Bought a Compute Savings Plan for the steady baseline."

Also say how you kept it from growing back: budgets and alerts, a weekly cost review, and Infracost in pull requests. If you cannot explain a percentage this way, use a smaller number you can defend.

</details>

<details><summary>Q8. [Basic] Tell me about yourself and your experience as a DevOps Engineer. <em>(asked in interview round)</em></summary>

**Answer:**

This is a template. Adapt the projects, tools and numbers to what you actually did, and only quote metrics you can explain. Placeholders such as `<X>%` are there for you to fill in with real figures.

**Structure to follow (about 90 seconds):**

```text
Current role and total experience
        |
        v
Previous company: what you built and operated
        |
        v
Current company: scope, ownership, key improvements
        |
        v
Strengths (CI/CD, IaC, Kubernetes, monitoring)
        |
        v
Why this role / what you want next
```

1. **Who you are**: role, years of experience, main cloud and tools.
2. **Previous experience**: one or two concrete things you built or improved.
3. **Current role**: what you own today and one recent improvement.
4. **Way of working**: automation first, security, reliability, collaboration.
5. **Close**: link your experience to the role you are interviewing for.

**Example answer:**

> "I am a DevOps Engineer with about five years of experience, mainly on Azure, Kubernetes and infrastructure as code.
>
> I started at Infosys in March 2021 and worked there until December 2024. I built and maintained Azure DevOps pipelines for application teams, provisioned Azure infrastructure with Terraform using reusable modules and remote state, and supported AKS workloads, including deployments, scaling and day-to-day troubleshooting.
>
> Since January 2025 I have been working at Impressico. Here I own CI/CD with Azure DevOps and GitHub Actions, package applications with Helm, and deploy them to AKS across dev, stage and production with approval gates. I also set up monitoring with Prometheus and Grafana and use Splunk for log search and alerting, which helped the team detect issues earlier and reduce manual deployment effort by around `<X>%`.
>
> I like automating repetitive work, keeping infrastructure in code, and making pipelines secure and repeatable. I am now looking for a role where I can work on larger-scale cloud platforms, including AWS, and keep growing on Kubernetes and platform engineering."

**Important points:**

- Keep it to 60 to 90 seconds; the interviewer will dig into whatever you mention, so mention only what you can defend.
- Name tools in the context of a problem you solved, not as a list.
- If the role is AWS-heavy and your experience is mostly Azure, say so honestly and map concepts (AKS to EKS, Azure Functions to Lambda, Azure Monitor to CloudWatch).
- End with a sentence that hands the conversation back, for example a project you are happy to go deeper on.

</details>
