# Azure Interview Preparation Summary

This guide consolidates the Azure summary notes into a topic-wise reading order. Start with cloud fundamentals, then move through compute, integration, storage, networking, security, governance, and operations.

## Contents

1. Cloud and architecture fundamentals
2. Application hosting and serverless compute
3. Integration and messaging
4. Storage and content delivery
5. Networking
6. Identity and security
7. Governance and resource management
8. Monitoring and operations
9. AWS-to-Azure service mapping

---

## 1. Cloud and Architecture Fundamentals

### 1.1 IaaS, PaaS, and SaaS

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

### 1.2 Azure Well-Architected Framework

The framework helps teams balance five connected design pillars:

1. **Reliability** — Recover from failures and continue meeting business requirements.
   - Use Availability Zones, load balancing, backups, and disaster recovery.
   - Define recovery time and recovery point objectives.

2. **Security** — Protect identities, applications, infrastructure, and data.
   - Apply least privilege with RBAC.
   - Store secrets and keys in Key Vault.
   - Use Defender for Cloud and Azure Policy to improve security posture.

3. **Cost Optimization** — Control spending while delivering the required business value.
   - Right-size resources and remove unused capacity.
   - Consider reservations and Spot VMs where appropriate.
   - Track spending with Cost Management and Billing.

4. **Operational Excellence** — Improve deployment, monitoring, and operational processes.
   - Use infrastructure as code with Bicep or ARM templates.
   - Centralize telemetry with Azure Monitor and Log Analytics.
   - Automate repeatable operational tasks.

5. **Performance Efficiency** — Meet demand efficiently as usage changes.
   - Use autoscaling for App Service, VM Scale Sets, and AKS.
   - Select suitable SKUs and review Azure Advisor recommendations.
   - Use caching and Azure Front Door for global content delivery.

**Interview summary:** Architecture decisions involve trade-offs. Improving one pillar can affect another, so design against business requirements rather than optimizing only one area.

---

## 2. Application Hosting and Serverless Compute

### 2.1 Azure App Service Web Apps

Azure Web Apps is a managed platform for building, deploying, and scaling web applications and APIs.

**Key capabilities**

- Supports common runtimes such as .NET, Java, Node.js, Python, and PHP.
- Supports deployment from GitHub, Azure DevOps, local Git, and other CI/CD systems.
- Provides custom domains, TLS, authentication integration, deployment slots, monitoring, scaling, and backups depending on the plan.
- Integrates with Visual Studio and Visual Studio Code.

**Common use cases**

- Business web applications and REST APIs
- E-commerce applications
- Blogs and content-management systems

**Interview summary:** Choose Web Apps when an HTTP application needs a continuously available managed hosting environment. Choose Functions when execution is primarily event-driven and can be broken into individual operations.

### 2.2 Azure Functions

Azure Functions is an event-driven compute service. A function runs code in response to an event without requiring the application team to manage servers.

**Good use cases**

- Lightweight APIs and webhooks
- Queue and event processing
- Scheduled background work
- File and image processing
- Data validation and transformation
- Small integration components

**Advantages**

- Automatic or elastic scaling, depending on the hosting plan
- Consumption-based options for intermittent workloads
- Fast development for small, event-focused components
- Native integration with many Azure services

**Considerations**

- Cold starts may affect latency on some hosting plans.
- Execution and timeout behavior depends on the chosen plan.
- Stateful or long-running workflows need an appropriate pattern, such as Durable Functions.
- Distributed functions require good logging, correlation, retries, and idempotency.

**Example flow:** A user uploads a photo to Blob Storage. A Function is triggered, validates or transforms the image, calls an API, and writes metadata to a database.

### 2.3 Common Azure Function Triggers

#### HTTP trigger

Runs when the function receives an HTTP request.

- Use for APIs, webhooks, and synchronous actions.
- Example: an HR application calls `/api/send-welcome-email` when an employee joins.

#### Timer trigger

Runs according to a schedule.

- Use for cleanup, synchronization, reporting, and recurring maintenance.
- Example: synchronize data from an external API to SQL every night.

#### Queue trigger

Runs when a message is available in an Azure Storage Queue.

- Use for asynchronous background processing.
- Example: process an invoice message and send a billing email.

#### Blob trigger

Runs when a blob is created or updated in a monitored container.

- Image/video processing: generate thumbnails, compress, or transcode.
- Data ingestion: process uploaded CSV or JSON files.
- Document processing: run OCR or extract invoice fields.
- Backup or replication: copy new files to another location.
- Event automation: generate alerts or start downstream work.

**Combined onboarding example**

1. An HTTP-triggered Function accepts a new employee request.
2. It places a message in a welcome-email queue.
3. A queue-triggered Function sends the email asynchronously.
4. A timer-triggered Function checks incomplete onboarding tasks nightly.

### 2.4 When Serverless Is a Good Fit

Use serverless for event-driven systems, variable or intermittent workloads, automation, small APIs, and independently scalable processing steps.

Consider another hosting model when workloads require consistently low latency, long-running processes, extensive local state, or predictable sustained compute where another pricing model is more economical.

---

## 3. Integration and Messaging

### 3.1 Azure Functions vs. Logic Apps

Both services support serverless and event-driven solutions, but they solve different problems.

| Requirement | Better starting point |
| --- | --- |
| Custom algorithms, validation, or transformations | Azure Functions |
| Low-code workflow and system integration | Logic Apps |
| Built-in connectors to SaaS and enterprise systems | Logic Apps |
| Lightweight API or background code | Azure Functions |
| Orchestration that also needs custom code | Logic Apps plus Functions |

**Azure Functions: the code engine**

- Developer-focused and code-first
- Suitable for custom logic and data processing
- Commonly triggered by HTTP, queues, timers, blobs, or events

**Logic Apps: the workflow engine**

- Designer-driven and connector-focused
- Suitable for business workflows, system integration, scheduling, and orchestration
- Can connect Azure services, SaaS products, and on-premises systems

**Order-to-invoice example:** A Logic App receives an order, calls Dynamics 365, writes to SQL, and sends a Teams notification. It calls an Azure Function when it needs custom discount calculations or tax-rule validation.

**File-processing example:** A file arrives in Blob Storage, a Logic App starts the workflow, a Function validates and transforms the file, and the Logic App stores the result and sends a notification.

### 3.2 Azure Queue Storage

Queue Storage provides simple, durable message queues for asynchronous communication between application components.

**Why use it?**

- Decouples producers from consumers
- Smooths traffic spikes
- Supports asynchronous processing
- Scales with storage workloads
- Is simple and cost-effective for basic queueing scenarios

**Basic flow**

1. A producer adds a message to the queue.
2. Azure stores the message in the storage account.
3. A consumer retrieves and processes it.
4. The consumer deletes the message after successful processing.

Design consumers to be idempotent because a message can be delivered more than once. Use visibility timeouts, retry handling, and poison-message handling.

**Interview distinction:** Queue Storage is a good choice for straightforward queueing. Azure Service Bus is generally preferred when enterprise messaging features such as topics, subscriptions, sessions, transactions, duplicate detection, or dead-lettering are required.

### 3.3 Azure Functions with Azure Data Factory

Data Factory and Functions work well together when a data pipeline needs custom API or transformation logic.

**Example pipeline**

1. Data Factory schedules and orchestrates the load.
2. A Function handles complex authentication and calls the external API.
3. The Function parses, validates, and reshapes JSON or CSV data.
4. Credentials are obtained securely through Key Vault or managed identity.
5. Data is written to Blob Storage/Data Lake or returned for the next pipeline step.
6. Data Factory continues loading into services such as Synapse or Databricks.
7. Application Insights monitors Function execution while Data Factory monitors the overall pipeline.

For .NET implementations, reuse `HttpClient` rather than creating a new client for every request. Also plan for API throttling, retries, pagination, and timeouts.

**Interview summary:** Data Factory is the orchestration layer; Functions supply custom code where built-in activities are not sufficient.

### 3.4 Azure Functions with Power Platform

An HTTP-triggered Function can extend Power Apps and Power Automate with capabilities that are difficult to implement using low-code components alone.

Common uses include:

- Complex validation or business rules
- External API integration
- Data transformation
- AI or custom library calls

Power Apps can call the Function and use its response interactively. Power Automate can call it as one step in a wider workflow. Secure the endpoint with an appropriate identity and authorization model rather than exposing an anonymous production Function.

---

## 4. Storage and Content Delivery

### 4.1 Hosting a Static Website in Azure Storage

Azure Storage can host static HTML, CSS, JavaScript, and media files without a web server or VM.

**Setup**

1. Create a general-purpose v2 storage account.
2. Open **Storage account > Data management > Static website**.
3. Enable the feature.
4. Configure an index document such as `index.html` and an error document such as `error.html`.
5. Upload website files to the automatically created `$web` container.
6. Test the primary web endpoint and a missing path to verify error handling.
7. Monitor storage metrics and logs as required.

**Benefits**

- No web server administration
- Low-cost hosting for static content
- Simple deployment
- Integration with Azure Front Door for custom domains, edge delivery, security, and global performance

**Limitations:** Storage static websites do not execute server-side application code. Use an API or Functions for dynamic behavior.

### 4.2 Azure Front Door

Detailed Azure Front Door coverage has moved to `networking/azure/summary.md`.

### 4.3 Securing Azure Storage Accounts

Use defense in depth rather than relying on one setting.

1. **Prevent anonymous blob access** unless the workload explicitly requires public content.
2. **Restrict public network access** to selected networks, or disable it when private access is sufficient.
3. **Use private endpoints** to give a storage service a private IP address in a VNet.
4. **Use service endpoints when appropriate** to restrict the public storage endpoint to selected subnets. Unlike a private endpoint, the service still uses its public endpoint.
5. **Enforce secure transfer** so clients use HTTPS or supported secure protocols.
6. **Prefer Microsoft Entra ID and managed identities** over account keys.
7. **Use SAS tokens carefully**: grant minimal permissions, use short expiry times, require HTTPS, and prefer user-delegation SAS for Blob Storage when possible.
8. **Protect account keys** and rotate them if they must be used.
9. **Use encryption at rest** with Microsoft-managed keys or customer-managed keys where required.
10. **Consider infrastructure encryption** when compliance requires an additional encryption layer.
11. **Use Defender for Storage** for threat detection where the risk and cost justify it.
12. **Enable diagnostic settings, logging, soft delete, versioning, and recovery features** according to the workload's protection requirements.

---

## 5. Networking

Azure networking coverage has moved to `networking/azure/summary.md`.

---

## 6. Identity and Security

### 6.1 Key Vault: Management Plane vs. Data Plane

A subscription Owner does not automatically receive permission to read or change secrets, keys, and certificates in every Key Vault.

- **Management plane:** Create or delete the vault, configure networking, and manage resource settings and role assignments.
- **Data plane:** Read, create, update, or delete the keys, secrets, and certificates stored inside the vault.

The Owner role provides broad management-plane permissions, including the ability to assign access, but it is not itself a Key Vault data-plane role.

#### When using Azure RBAC

Assign a suitable data-plane role at the narrowest practical scope:

| Role | Typical access |
| --- | --- |
| Key Vault Administrator | Manage keys, secrets, and certificates; does not manage RBAC assignments |
| Key Vault Crypto Officer | Create and manage keys |
| Key Vault Secrets Officer | Create and manage secrets |
| Key Vault Certificates Officer | Create and manage certificates |
| Key Vault Secrets User | Read secret values |

#### When using vault access policies

Add an access policy that explicitly grants the required key, secret, or certificate operations.

Check the configured model under **Key Vault > Settings > Access configuration**. Apply least privilege and prefer managed identities for applications.

---

## 7. Governance and Resource Management

### 7.1 Azure Policy: Restricting Snapshot SKUs

Azure Policy can enforce or report configuration rules at scale. For example, an organization can require managed-disk snapshots in Central India to use `Standard_LRS`.

- `deny` blocks a non-compliant create or update request.
- `audit` allows the request but marks the resource non-compliant.

Example policy rule:

```json
{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Compute/snapshots"
      },
      {
        "field": "location",
        "equals": "centralindia"
      },
      {
        "field": "Microsoft.Compute/snapshots/sku.name",
        "notEquals": "Standard_LRS"
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}
```

**Expected behavior**

- With `deny`, `Standard_LRS` passes and a disallowed SKU is rejected.
- With `audit`, a disallowed SKU can be created but appears as non-compliant.

Test policies in a non-production scope first. Review aliases, exemptions, existing resources, and remediation requirements before broad assignment.

### 7.2 Moving Resources Between Resource Groups

Azure can move many resource types between resource groups, but support and dependencies vary by service.

**What happens during a move**

- Azure validates that the resources and dependencies support the move.
- The source and destination resource groups are locked against write operations for part of the move.
- Existing workloads usually continue to run, but control-plane changes are temporarily blocked.
- Resource IDs change because the resource-group segment changes.

**Preparation checklist**

1. Confirm that every resource type supports the intended move.
2. Identify and include required dependent resources.
3. Check resource locks, policies, quotas, and destination permissions.
4. Save resource IDs and review anything that stores them explicitly, such as scripts, dashboards, or external automation.
5. Validate the move before execution.
6. Avoid simultaneous changes to either resource group.
7. Verify monitoring, permissions, automation, and application behavior afterward.

**Interview summary:** A resource-group move is primarily a control-plane operation and normally does not move the resource's physical region. Do not promise zero impact without checking the specific services and dependencies.

---

## 8. Monitoring and Operations

Use monitoring at both the component and workflow level:

- **Azure Monitor:** common platform for metrics, logs, alerts, and dashboards.
- **Log Analytics workspace:** query and analyze collected logs with KQL.
- **Application Insights:** application performance monitoring, requests, dependencies, exceptions, traces, and distributed transaction views.
- **Network Watcher:** network topology, diagnostics, connection monitoring, packet capture, and flow-related analysis.
- **Service-specific monitoring:** Data Factory pipeline runs, Function executions, Storage metrics, and Front Door health/caching metrics.

Operationally mature systems should include structured logs, correlation IDs, useful alerts, retry visibility, dashboards, runbooks, and tested incident procedures.

---

## 9. AWS-to-Azure Service Mapping

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

---

## Final Interview Revision Checklist

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

## Screenshot Addendum: Azure Architecture at a Glance

Azure architecture should be explained as a business flow rather than a list of products:

1. Users arrive through DNS, Front Door or CDN for global routing, acceleration, and edge availability.
2. Entra ID, WAF, DDoS Protection, and Key Vault protect identity, traffic, and secrets.
3. API Management, Logic Apps, Service Bus, and Event Grid expose, orchestrate, and decouple integrations.
4. App Service, AKS, Functions, and Container Apps run applications with different control and scaling models.
5. Azure SQL, Cosmos DB, Blob Storage, and Data Lake store transactional, globally distributed, object, and analytical data.
6. Synapse, Databricks, Azure Machine Learning, and Azure OpenAI provide analytics and intelligent capabilities.
7. Azure Monitor, Application Insights, Log Analytics, Defender for Cloud, and Azure Policy provide operations, security, and governance.
8. GitHub, Azure DevOps, Terraform, and Bicep automate reviewed, repeatable delivery.

Architecture choices should be evaluated against the Azure Well-Architected pillars: reliability, security, cost optimization, operational excellence, and performance efficiency. Resource hierarchy flows from management groups to subscriptions, resource groups, and resources. Identity should use Entra ID, RBAC, managed identities, MFA, and least privilege. Availability Zones protect against datacenter failure, while region pairs, replicated data, traffic failover, and tested runbooks address regional disaster recovery.

Storage redundancy choices range from LRS and ZRS to GRS, GZRS, and read-access variants. Choose from the durability, availability, residency, latency, and recovery requirements rather than selecting the most expensive option automatically. Cost controls include correct sizing, reservations or savings plans where applicable, autoscaling, lifecycle policies, budgets, and removal of confirmed unused resources.

## Notes Addendum: Enterprise Azure Design

### Landing Zone design areas

An Azure Landing Zone is a governed platform blueprint, not merely a collection of VNets and subnets. Its design covers tenant and resource organization, identity and access, network topology and hybrid connectivity, security and governance, management and monitoring, business continuity, cost, and platform automation. Management groups and subscriptions establish policy, ownership, billing, and blast-radius boundaries; shared platform subscriptions can host connectivity, identity, and management capabilities while application teams own workload subscriptions.

### Entra ID, RBAC, and scope

Microsoft Entra ID authenticates users, groups, service principals, and managed identities. Azure RBAC authorizes actions against Azure resources. Entra directory roles such as Global Administrator govern directory capabilities; Azure roles such as Owner, Contributor, and Reader govern resource scopes. They are different permission systems.

Azure resource scope inherits downward:

```text
management group -> subscription -> resource group -> resource
```

Apply the rule **right principal, right role, right scope**. Prefer groups and managed identities, least privilege, time-bound privileged access, separation of duties, access reviews, and diagnostic logs. `Owner` includes role assignment capability; `Contributor` manages resources but cannot grant Azure RBAC access by default; `Reader` is view-only. Avoid broad permanent assignments when a resource-group or resource scope is sufficient.

### Azure Policy governance

Azure Policy evaluates resources against organizational rules. Effects can audit, deny, modify supported properties, deploy required configuration, or mark non-compliance. Initiatives group policies into a baseline and assignments at management-group scope can inherit across subscriptions. Common controls include allowed regions or SKUs, mandatory tags, diagnostic settings, encryption, private networking, and security baselines.

Policy rollout should begin with inventory and audit, assess exemptions and remediation impact, then move to enforcement through change control. Policy is not a replacement for RBAC: RBAC controls who may act, while Policy constrains which resource states are acceptable.

### Virtual Machine Scale Sets

VM Scale Sets run similarly configured VMs and integrate with load balancing, health, autoscale, and rolling upgrades. Scale-out adds instances when demand crosses a controlled threshold; scale-in removes excess capacity after stabilization. Production configuration includes minimum/maximum/default capacity, health probes, zones or fault-domain strategy, instance repair, graceful termination, image versioning, rolling-upgrade health gates, and application startup time.

Autoscaling does not cure inefficient code or an overloaded database. Verify end-to-end latency, queue depth, dependency limits, and cost after scaling. For predictable events, scheduled scaling can add capacity before traffic arrives.

### Resilient multi-region application

A multi-region Azure application can use Front Door as the global entry point and regional Application Gateway/WAF or another regional ingress in each deployment. Separate web, application, data, and management boundaries; use private endpoints, Key Vault, Firewall, Policy, Monitor, and tested backup/failover according to requirements. Data replication and failover semantics determine the real recovery point and recovery time; deploying compute in two regions alone does not provide disaster recovery. Regularly test regional traffic failover, dependency capacity, DNS/TLS, data recovery, and operational runbooks.

### Azure three-tier blueprint and automation

A typical Azure three-tier design uses Front Door for global entry, Application Gateway/WAF for regional Layer-7 routing, and App Service, VM Scale Sets, containers, or AKS for the presentation tier. The application tier runs on a separately secured service or compute boundary and can use an internal load balancer, Service Bus, and Redis to decouple work and reduce latency. Azure SQL, Cosmos DB, or Storage services form the data tier through private connectivity, managed identity, encryption, backup, and tested recovery. Terraform modules, Azure CLI where appropriate, Git-based review, and CI/CD make the Dev, Test, and Production environments repeatable; environment separation must also include state, identity, approval, policy, and network boundaries.
