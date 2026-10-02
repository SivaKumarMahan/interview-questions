# Ops: Operations Practices Overview

> How DevOps, GitOps, MLOps and AIOps relate, a learning path across them, AgentOps, and managing a large Kubernetes fleet.

## Key Concepts

### DevOps, GitOps, MLOps, and AIOps Compared

DevOps, GitOps, MLOps, and AIOps all rely on automation, feedback, measurement, version control, security, and continuous learning. Each one solves a different problem in the lifecycle.

| Practice | Primary focus | Typical work |
| --- | --- | --- |
| **DevOps** | Software delivery and operations | CI/CD, IaC, configuration, observability, collaboration, reliability |
| **GitOps** | Declarative infrastructure/application delivery | Git as the source of truth, pull-based reconciliation (making the live system match Git), drift detection, policy, rollback |
| **MLOps** | Machine-learning lifecycle | Data/versioning, training pipelines, registry, deployment, monitoring, drift and retraining |
| **AIOps** | Intelligent IT operations | Event correlation, anomaly detection, root-cause help, forecasting, noise reduction, safe automated fixes |

DevOps builds reliable delivery. MLOps extends those same practices to data and models: it adds feature and data lineage, experiment tracking, a model registry, serving, drift and bias detection, and retraining.

AIOps applies analytics and machine learning to operational monitoring data so teams can detect and prioritize issues faster. It has to explain its evidence clearly, ask a human before any risky action, take feedback, and limit what it can automate on its own. GitOps keeps the declared state versioned and continuously reconciled against the live system.

A practical learning path: start with Linux, networking, Git, cloud, security, SQL/Python, CI/CD, containers, Kubernetes, and Terraform/Ansible, then add monitoring and logging. From there, add data pipelines and model lifecycle work for MLOps, and statistics, event correlation, and automation guardrails for AIOps.

None of these practices replaces another. Together they cover building, delivering, operating, learning, and improving.

### AgentOps

Running AI agents in production takes more than just calling an LLM. **AgentOps** covers multi-step and tool-calling workflows, scheduling, retries, state and memory, observability, evaluation, cost, security, and human approval.

An orchestration platform can run branches and retries on Kubernetes and keep track of workflow state, but production also needs prompt and tool versioning, trace correlation, redaction of sensitive data, permission boundaries, quality evaluation, timeout and budget limits, a safe fallback, and an auditable approval path.

Python, Kubernetes, and an orchestrator such as Flyte make a solid open-source learning stack. The architecture matters more than any one tool.

### Managing a Large Kubernetes Fleet

Once you're running tens or hundreds of clusters, treat them as a managed fleet rather than one-off installs:

- **Cluster API** or a cloud fleet service standardizes how clusters get created, upgraded, and retired across accounts, subscriptions, regions, and environments.
- **Terraform** manages cloud and cluster infrastructure through reviewed modules, with separate state per team and blast radius.
- **Argo CD** or **Flux** deploys versioned desired state. **Helm** or **Kustomize** provides reusable application packaging.
- **Vault** or an external-secrets system injects secrets so plaintext values never get committed.
- A **service mesh** is worth adopting only when its mTLS, policy, and traffic-control benefits outweigh the extra operational cost.
- **Central metrics, logs, traces, dashboards, and alert routing** give fleet-wide visibility while still keeping each cluster isolated.

Fleet operations also need a version-skew policy, upgrade rings, admission policy, tenant isolation, capacity and cost reporting, tested backup and restore, and a break-glass process. The goal is repeatable control with a small blast radius per change, not one highly privileged system that can touch every cluster with no safeguards.
### Teams bots, Adaptive Cards and dashboard visualization (ChatOps)

A cluster of related concepts that shows up in "build a status dashboard/bot" style questions: chat apps, micro frontends, the Teams Bot Framework, Adaptive Cards, and the difference between D3.js and Highcharts for the visualization layer.

**Chat apps** - applications where users communicate through messages, such as Microsoft Teams, Slack, or an internal chat application. In a DevOps context, they're commonly used as the front door for ChatOps - checking deployment status, triggering pipelines, or getting alerts without leaving the chat tool.

**Micro frontends** - a way to split a large frontend application into smaller, independently developed and deployed frontend applications, each typically owned by a different team.

```
Employee Portal
 ├── Profile
 ├── Payroll
 ├── Leave Management
 └── Reports
```

Different teams can own and deploy each section independently instead of shipping one large frontend as a single unit.

**Teams Bot Framework** - used to build bots that users interact with directly inside Microsoft Teams.

```
User: Check production deployment
Bot:  Production deployment is successful.
      Version: v2.4.1
      Status: Running
```

**Adaptive Cards** - JSON-based UI cards used by Teams bots to display structured information and interactive buttons inside a Teams conversation, instead of plain text.

```
Production Deployment
Status: Successful
Version: v2.4.1
Environment: Production
[View Logs] [Rollback]
```

**D3.js vs Highcharts** - both are JavaScript charting libraries, but they solve different problems:

| Library | Strength |
| --- | --- |
| D3.js | More flexible and customizable - you build the visualization from primitives (SVG, scales, axes) |
| Highcharts | Easier for standard business charts (bar, line, pie) with less code and built-in interactivity |

D3.js is the right choice when a dashboard needs a custom or unusual visualization; Highcharts is the right choice when the requirement is common business charts delivered quickly.

**Azure Web Apps** - Azure App Service Web Apps, used to host web applications and APIs without managing the underlying VMs directly. Supports .NET, Node.js, Python, Java, and PHP.

**Putting it together** - a Teams-integrated deployment-status dashboard could look like:

```
User
  |
  v
Microsoft Teams
  |
  v
Teams Bot
  |
  v
Python API
  |
  v
Azure Web App / Database / APIs
  |
  v
Data
  |
  v
D3.js / Highcharts
  |
  v
Web Dashboard
```

The bot handles the conversational interface and Adaptive Cards inside Teams, a Python API on Azure App Service does the backend work (querying deployment/pipeline state), and a web dashboard renders the same data visually using D3.js or Highcharts depending on how custom the charts need to be.
