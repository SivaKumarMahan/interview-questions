# Azure: Fundamentals and Architecture

> Cloud service models, the Well-Architected Framework, an end-to-end view of Azure architecture, AWS-to-Azure mapping, and a revision checklist.

## Key Concepts

### Final Interview Revision Checklist

Be ready to explain:

- The responsibility difference between IaaS, PaaS, and SaaS
- When to choose Web Apps, Functions, or Logic Apps
- How common Function triggers support event-driven design
- Queue Storage vs. Service Bus
- How Functions complement Data Factory and Power Platform
- Static website hosting and the purpose of Front Door
- Storage security using identity, network controls, SAS, and encryption
- Individual public IP addresses vs. public IP prefixes
- Key Vault management-plane vs. data-plane authorization
- Azure Policy `deny` vs. `audit`
- Resource-group move preparation and effects
- The five Well-Architected Framework pillars
- The monitoring service appropriate to each layer

For each topic, prepare a short definition, one real-world example, the main trade-off, and one alternative service.

### Screenshot Addendum: Azure Architecture at a Glance

Azure architecture should be explained as a business flow rather than a list of products:

1. Users arrive through DNS, Front Door or CDN for global routing, acceleration, and edge availability.
2. Entra ID, WAF, DDoS Protection, and Key Vault protect identity, traffic, and secrets.
3. API Management, Logic Apps, Service Bus, and Event Grid expose, orchestrate, and decouple integrations.
4. App Service, AKS, Functions, and Container Apps run applications with different control and scaling models.
5. Azure SQL, Cosmos DB, Blob Storage, and Data Lake store transactional, globally distributed, object, and analytical data.
6. Synapse, Databricks, Azure Machine Learning, and Azure OpenAI provide analytics and intelligent capabilities.
7. Azure Monitor, Application Insights, Log Analytics, Defender for Cloud, and Azure Policy provide operations, security, and governance.
8. GitHub, Azure DevOps, Terraform, and Bicep automate reviewed, repeatable delivery.

Architecture choices should be evaluated against the Azure Well-Architected pillars: reliability, security, cost optimization, operational excellence, and performance efficiency. Resource hierarchy flows from management groups to subscriptions, resource groups, and resources.

Identity should rest on Entra ID, RBAC, managed identities, MFA, and least privilege. Availability Zones protect against a single datacenter failing. Region pairs, replicated data, traffic failover, and tested runbooks are what actually protect against a regional disaster.

Storage redundancy options range from LRS and ZRS up to GRS, GZRS, and their read-access variants. Pick based on the actual durability, availability, residency, latency, and recovery requirements — not by defaulting to the most expensive option.

Cost controls include correct sizing, reservations or savings plans where applicable, autoscaling, lifecycle policies, budgets, and removal of confirmed unused resources.

### IaaS, PaaS, and SaaS

#### Infrastructure as a Service (IaaS)

The cloud provider manages the physical data center, hardware, networking, and virtualization. The customer manages the operating system, configuration, applications, and data.

- Best for: workloads that require OS-level control or custom infrastructure.
- Azure examples: Virtual Machines, Virtual Network, and Managed Disks.
- Analogy: renting virtual hardware in a cloud data center.

#### Platform as a Service (PaaS)

The provider also manages the operating system, runtime, patching, and much of the platform. Developers focus mainly on application code and data.

- Best for: application development without server administration.
- Azure examples: App Service, Azure SQL Database, and Azure Functions.
- Main benefit: faster development with less infrastructure maintenance.

#### Software as a Service (SaaS)

The provider delivers a complete application. Users configure and consume the software without managing the platform or infrastructure.

- Best for: ready-to-use business capabilities.
- Examples: Microsoft 365 and Dynamics 365.
- Trade-off: least infrastructure responsibility, but less low-level control.

**Interview summary:** IaaS gives the most control and management responsibility; SaaS gives the least. PaaS sits between them and is commonly used by application teams.

### Azure Well-Architected Framework

The framework helps teams balance five connected design pillars:

1. **Reliability** — Recover from failures and continue meeting business requirements.
   - Use Availability Zones, load balancing, backups, and disaster recovery.
   - Define recovery time and recovery point objectives.

2. **Security** — Protect identities, applications, infrastructure, and data.
   - Apply least privilege through RBAC — give each identity only the access it actually needs.
   - Store secrets and keys in Key Vault.
   - Use Defender for Cloud and Azure Policy to improve security posture.

3. **Cost Optimization** — Control spending while delivering the required business value.
   - Right-size resources and remove unused capacity.
   - Consider reservations and Spot VMs where appropriate.
   - Track spending with Cost Management and Billing.

4. **Operational Excellence** — Improve deployment, monitoring, and operational processes.
   - Use infrastructure as code with Bicep or ARM templates.
   - Centralize monitoring data with Azure Monitor and Log Analytics.
   - Automate repeatable operational tasks.

5. **Performance Efficiency** — Meet demand efficiently as usage changes.
   - Use autoscaling for App Service, VM Scale Sets, and AKS.
   - Select suitable SKUs and review Azure Advisor recommendations.
   - Use caching and Azure Front Door for global content delivery.

**Interview summary:** Architecture decisions involve trade-offs. Improving one pillar can affect another, so design against business requirements rather than optimizing only one area.

### AWS-to-Azure Service Mapping

These are conceptual comparisons, not always exact feature-for-feature equivalents.

| Category | AWS | Azure |
| --- | --- | --- |
| Virtual machines | EC2 | Azure Virtual Machines |
| Serverless functions | Lambda | Azure Functions |
| Managed Kubernetes | EKS | AKS |
| Object storage | S3 | Blob Storage |
| Block storage | EBS | Managed Disks |
| Managed file shares | EFS | Azure Files |
| Managed relational databases | RDS | Azure SQL Database / Azure Database services |
| Globally distributed NoSQL | DynamoDB | Cosmos DB |
| Private cloud network | VPC | Virtual Network |
| DNS hosting | Route 53 | Azure DNS |
| Content delivery / global edge | CloudFront | Azure Front Door |
| Workforce identity | IAM Identity Center | Microsoft Entra ID |
| Resource authorization | IAM policies and roles | Azure RBAC |
| Metrics and logs | CloudWatch | Azure Monitor |
| CI/CD | CodePipeline | Azure Pipelines / GitHub Actions |

## Interview Questions

<details><summary>Q1. [Basic] What is Microsoft Azure?</summary>

**Answer:**

Microsoft Azure is a cloud platform that offers compute, networking, storage, databases, identity, integration, security, monitoring, analytics, and DevOps services. It supports public cloud, hybrid, and multi-cloud setups through services like Azure Arc.

A simple application flow looks like this: users hit Azure Front Door, traffic goes to App Service or AKS, the workload uses managed identity to read Key Vault and reach Azure SQL, and monitoring data flows to Azure Monitor and Application Insights.

Azure organizes things using tenants for identity, management groups and subscriptions for governance and billing, resource groups for grouping resources by lifecycle, and regions or availability zones for where things physically run.

In an interview, I try to describe the actual services, the availability target, the security model, day-to-day operations, and cost controls — not just say "Azure hosts applications."

</details>

<details><summary>Q2. [Basic] What is the difference between IaaS, PaaS, and serverless in Azure?</summary>

**Answer:**

- **IaaS:** Azure manages the physical hardware and virtualization; I manage the VM's OS, patches, middleware, application, and data. Example: Azure Virtual Machines.
- **PaaS:** Azure also manages the OS and runtime; I focus on the application, its configuration, identity, and data. Examples: App Service and Azure SQL Database.
- **Serverless:** Code or workflows run in response to events and scale based on demand. Examples: Azure Functions and Logic Apps.

I pick IaaS for legacy software or when I need OS-level control, PaaS for managed web and database platforms, and Functions for event-driven tasks.

I weigh compliance, how much runtime control I need, scaling, latency and cold start, how long execution can run, networking, operational effort, and steady-state cost. "Serverless" doesn't mean there are no servers — it just means Azure runs them instead of you.

</details>

<details><summary>Q3. [Basic] What is the difference between a SaaS application and an enterprise application?</summary>

**A:** A **SaaS (Software as a Service)** application is cloud-based software that's hosted and run by a third-party provider. Users access it over the internet without installing or maintaining anything themselves.

Examples include Microsoft 365, Google Workspace, and Salesforce.

An **enterprise application** is different — it's built to meet one organization's specific needs. These tend to be more complex, and they can be hosted on-premises or in the cloud.

They're typically used for core business processes like ERP (Enterprise Resource Planning), CRM (Customer Relationship Management), and supply chain management. Examples include SAP, Oracle E-Business Suite, and Microsoft Dynamics.

- A SaaS application is hosted and managed by a third party — you just subscribe and use it through a browser.
- An enterprise application, by contrast, is developed or managed internally, often on the company's own infrastructure, and built around its specific processes.
- SaaS is about ease of use and scaling quickly. Enterprise applications are about deep customization and tying into internal systems.

</details>
