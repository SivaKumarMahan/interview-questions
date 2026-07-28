# Azure Detailed Interview Notes

### Q: What is the difference between a SaaS application and an enterprise application?

**A:** A **SaaS (Software as a Service)** application is a cloud-based software solution that is hosted and managed by a third-party provider, allowing users to access it over the internet without needing to install or maintain it on their own infrastructure.

Examples include Microsoft 365, Google Workspace, and Salesforce.
An **enterprise application**, on the other hand, is a software solution designed to meet the specific needs of an organization. These applications are often more complex and may be hosted on-premises or in the cloud.

They are typically used for business processes such as ERP (Enterprise Resource Planning), CRM (Customer Relationship Management), and supply chain management. Examples include SAP, Oracle E-Business Suite, and Microsoft Dynamics.

- A SaaS application is cloud-hosted and managed by a third-party provider — users simply subscribe and access it through a browser.
- In contrast, an enterprise application is developed or managed internally by a company, often hosted on its own infrastructure, and tailored for its business processes.
- SaaS focuses on ease of use and scalability, while enterprise applications focus on deep customization and integration with internal systems.

## Azure Reliability, Storage, and Operations Notes

Use Availability Zones to tolerate a datacenter failure within a region; use multi-region architecture, data replication and tested failover for regional disaster recovery. Region pairs are an Azure planning concept, not an automatic guarantee that every workload replicates or fails over.

Recovery design begins with application RTO/RPO, data consistency and dependency capacity.

Azure Blob Storage is object storage. Choose the access tier from actual access and recovery needs: Hot for frequent access, Cool for infrequent access with minimum-retention/retrieval trade-offs, and Archive for long-term offline data that must be rehydrated before use.

Azure Files provides managed SMB/NFS file shares; managed disks provide block storage for VM workloads. Use private endpoints, encryption, RBAC and backup/lifecycle policies where required.

Azure Monitor collects metrics, logs and alerts; Application Insights provides application request/dependency monitoring data; Log Analytics stores and queries logs with KQL; Azure Service Health communicates Azure service incidents and planned maintenance.

Azure Advisor makes recommendation categories such as reliability, security, performance, cost and operational excellence, but recommendations still need workload-specific review before change.
NSGs are stateful Layer-3/4 allow/deny rules on subnets or NICs. Azure Firewall is a centralized managed firewall service.

Application Gateway is a Layer-7 HTTP(S) load balancer and can run WAF policy. Use each according to the traffic boundary and verify effective route/rule behavior instead of assuming that adding all three creates a correct design.

---
