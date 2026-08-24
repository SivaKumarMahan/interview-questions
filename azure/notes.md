# Azure Detailed Interview Notes

### Q: What is the difference between a SaaS application and an enterprise application?

**A:** A **SaaS (Software as a Service)** application is cloud-based software that's hosted and run by a third-party provider. Users access it over the internet without installing or maintaining anything themselves.

Examples include Microsoft 365, Google Workspace, and Salesforce.

An **enterprise application** is different — it's built to meet one organization's specific needs. These tend to be more complex, and they can be hosted on-premises or in the cloud.

They're typically used for core business processes like ERP (Enterprise Resource Planning), CRM (Customer Relationship Management), and supply chain management. Examples include SAP, Oracle E-Business Suite, and Microsoft Dynamics.

- A SaaS application is hosted and managed by a third party — you just subscribe and use it through a browser.
- An enterprise application, by contrast, is developed or managed internally, often on the company's own infrastructure, and built around its specific processes.
- SaaS is about ease of use and scaling quickly. Enterprise applications are about deep customization and tying into internal systems.

## Azure Reliability, Storage, and Operations Notes

Use Availability Zones to survive a single datacenter failing within a region. For a whole region going down, you need a multi-region setup, data replication, and failover that's actually been tested. Region pairs are just an Azure planning concept — they don't automatically mean every workload replicates or fails over on its own.

Recovery design starts with the application's recovery time and recovery point objectives, data consistency needs, and how much capacity the dependencies actually have.

Azure Blob Storage is object storage. Pick the access tier based on how the data is actually used: Hot for data accessed often, Cool for data accessed rarely (with tradeoffs around minimum retention and retrieval cost), and Archive for long-term data that needs to be brought back online before it can be used.

Azure Files gives you managed SMB or NFS file shares; managed disks give you block storage for VMs. Use private endpoints, encryption, RBAC, and backup or lifecycle policies wherever they're needed.

Azure Monitor collects metrics, logs, and alerts. Application Insights covers application-level request and dependency monitoring. Log Analytics stores and lets you query logs with KQL. Azure Service Health tells you about Azure's own incidents and planned maintenance.

Azure Advisor gives recommendations across reliability, security, performance, cost, and operational excellence — but each one still needs a workload-specific review before you act on it.

Network security groups are stateful allow/deny rules at Layer 3/4, applied to subnets or network interfaces. Azure Firewall is a centralized, managed firewall service.

Application Gateway is a Layer-7 HTTP(S) load balancer, and it can run a web application firewall policy too. Pick the right one for the traffic boundary you're actually protecting, and check the effective routes and rules directly — don't assume that stacking all three together automatically gives you a correct design.

---
