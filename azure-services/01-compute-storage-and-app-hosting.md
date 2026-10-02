# Azure Services: Compute, Storage, and Application Hosting

> Virtual machines, storage accounts and Blob Storage, App Service, Azure Functions, and Azure SQL Database.

## Interview Questions

### 1. What are Azure Virtual Machines?

**Answer:**

Azure VMs are infrastructure-as-a-service compute. Azure runs the physical hardware and the hypervisor; I manage the guest OS, patches, software, configuration, identity, disks, and recovery of the workload itself. VMs attach network interfaces to a VNet and use managed disks for storage.

I reach for VMs when I need legacy software, control over the OS or kernel, an unsupported runtime, or a straightforward lift-and-shift. In production I use Availability Zones or sets as needed, load balancing, backups, monitoring, patch management, managed identity, and infrastructure-as-code. A single VM is a single point of failure.

When something's wrong, I start with Azure's own resource and boot diagnostics and the Activity Log, then move into guest-level CPU, memory, disk, network, and service logs. I always separate "Azure itself has a problem" from "the OS or app has a problem" before I reach for a reboot.

### 2. How do you secure Azure Virtual Machines?

**Answer:**

I keep VMs private and reach them through Bastion, VPN, ExpressRoute, or another controlled jump path. I never expose RDP or SSH to the open internet. Network security groups and firewalls only allow the traffic that's actually needed. Signing in through Entra with managed identity, plus RBAC scoped to the minimum needed, cuts down on stored credentials.

I use hardened images, keep patches and updates current, encrypt disks, turn on Secure Boot and vTPM where supported, run endpoint protection or Defender, scan for vulnerabilities, take backups, and send logs somewhere central. Secrets come from Key Vault, not from the VM itself.

I watch for privileged sign-ins, changes to network security group rules, new public IPs, malware alerts, and patch compliance. I also test that recovery actually works.

If I suspect a VM has been compromised, I cut off its network access, preserve evidence following the incident procedure, rotate any credentials it could reach, rebuild from a trusted image, and investigate properly — I don't just reboot it and hope.

### 3. What is an Azure Storage Account?

**Answer:**

A Storage Account is Azure's namespace, security, and configuration boundary for Blob, Files, Queue, and Table services, depending on the account type. It controls region, redundancy, performance tier, networking, encryption, identity and RBAC, lifecycle rules, and protection settings.

I pick general-purpose v2 in most cases, choose LRS, ZRS, or GRS based on what failure and recovery-point needs the workload actually has, turn off public or anonymous access unless it's genuinely required, prefer Entra ID and managed identity over keys, enforce HTTPS, use private endpoints or firewalls, and turn on logs, soft delete, versioning, or lifecycle rules depending on the workload.

I keep an eye on capacity, transactions, latency, availability, throttling, and data leaving the account. Recovery features and backup get chosen per service — replication by itself doesn't protect against every kind of deletion or corruption.

### 4. What is Azure Blob Storage?

**Answer:**

Blob Storage is object storage for unstructured data — images, logs, backups, build artifacts, static content, data-lake files, that kind of thing. Containers hold block, append, or page blobs, and access tiers let you trade retrieval speed and cost against storage cost.

Applications use the SDK or REST API with managed identity and roles scoped to just the data they need. I use lifecycle rules to move data to cheaper tiers or delete it on a schedule, immutable storage (which can't be altered or deleted before its retention period ends) for regulated data that must be retained, and versioning or soft delete for recovery.

Large uploads go in blocks, with retries designed to be safe even if the same block gets uploaded twice.

I choose Blob over Azure Files when the workload fits object access over HTTP; Files is the better fit for SMB or NFS shares. Monitoring covers request errors, latency, capacity, throttling, and outbound data.

### 5. How do you secure Azure Storage?

**Answer:**

I stack several layers of protection rather than relying on one setting. I turn off anonymous blob access, restrict or disable public network access, use private endpoints and private DNS, require HTTPS for all transfers, prefer Entra managed identities and data-level RBAC over account keys, protect and rotate any keys that are still in use, and issue SAS tokens that are short-lived and carry only the permissions they need.

Azure encrypts data at rest by default. I add customer-managed keys or infrastructure-level encryption when the requirement calls for it. I also turn on Defender and logging, use versioning, soft delete, or immutability where it makes sense, and apply policies that stop insecure settings from being created in the first place.

I test that allowed access actually works and denied access actually fails. If there's an exposure, I lock down access, revoke SAS tokens or rotate keys, keep the logs, check what was downloaded or changed, restore data if needed, and fix the underlying policy or architecture.

### 6. What is Azure App Service?

**Answer:**

App Service is a managed platform for hosting web apps and APIs. Azure runs the OS and runtime; teams deploy their code or container and configure the plan, scaling, domains and TLS, identity, networking, diagnostics, and application behavior.

In production I use multiple instances or zones where they're available, a health check, autoscale, managed identity with Key Vault references, VNet integration or private endpoints as needed, deployment slots, and Application Insights.

I deploy to a slot, warm it up and test it, then swap it into production — keeping database changes backward-compatible so the swap doesn't break anything. When something fails, I check deployment logs, app logs, instance health, configuration, identity, DNS and networking, dependencies, and platform metrics before I roll back or swap.

### 7. What is the difference between App Service, App Service Plan and Web App?

This is one of the most common Azure interview questions. Many people confuse these three terms because they are closely related.

Think of it like an apartment building:

- **App Service Plan** = the building (CPU, RAM, OS, pricing tier)
- **Web App** = your apartment (your application)
- **App Service** = the overall Azure platform that hosts web applications, APIs, mobile backends, etc.

#### 18.1 Azure App Service

App Service is Microsoft's PaaS (Platform as a Service) offering for hosting web applications. It provides everything required to run an application without managing servers.

It includes features like:

- Auto scaling
- Load balancing
- SSL certificates
- Deployment slots
- Authentication
- Custom domains
- Backup and restore
- Monitoring
- CI/CD integration

So App Service is the service itself.

Instead of creating VMs, installing IIS or Nginx, configuring networking, and maintaining the OS, Azure App Service handles all of that.

#### 18.2 App Service Plan

The App Service Plan defines the infrastructure on which your applications run.

It decides:

- CPU
- RAM
- OS (Windows / Linux)
- Region
- Pricing tier
- Number of instances
- Scaling

Think of it as: *"How much hardware do I want?"*

Example:

```
App Service Plan

Premium V3
Linux
East US
4 CPUs
16 GB RAM
```

Every Web App inside this plan shares these resources.

**One App Service Plan can host multiple apps**

```
App Service Plan
Premium V3
Linux
4 CPU
16 GB RAM

        |
        +-- Web App A
        +-- Web App B
        +-- API App
        +-- Function App (Premium)
```

All these applications share the same compute resources.

#### 18.3 Web App

A Web App is the actual application you deploy.

Examples:

- Company website
- React application
- Angular application
- ASP.NET application
- Node.js application
- Java application
- Python Flask application

When you open:

```
https://mycompany.azurewebsites.net
```

you're accessing a Web App.

#### 18.4 Real-world example

Suppose your company has three applications: Customer Portal, Admin Portal and a REST API.

You create:

```
App Service Plan
Premium V3
8 GB RAM
Linux

        |
        +-- Customer Portal (Web App)
        +-- Admin Portal (Web App)
        +-- Orders API (Web App)
```

All three apps run on the same App Service Plan and share the same compute resources.

**If one app uses high CPU?**

```
Customer Portal
CPU = 90%
```

Since all apps share the same App Service Plan:

- Admin Portal performance may degrade.
- API performance may also degrade.

That's why production workloads often use separate App Service Plans for critical applications.

#### 18.5 Common follow-up questions

**Can one App Service Plan have apps from different subscriptions?**

No. Apps in an App Service Plan must belong to the same subscription.

**Can multiple App Service Plans exist?**

Yes.

```
Development Plan
B1

Testing Plan
S1

Production Plan
Premium V3
```

Each plan has different resources and pricing.

**Can two Web Apps share one App Service Plan?**

Yes. Multiple Web Apps can share a single App Service Plan, and they share the underlying compute resources (CPU, memory, and storage). This is cost-effective, but heavy resource usage by one app can affect the others.

#### 18.6 Scaling

**Scale Up** - increase VM size.

```
B1
 |
S1
 |
P1V3
 |
P2V3
```

More CPU and RAM.

**Scale Out** - increase the number of instances.

```
Instance 1
Instance 2
Instance 3
```

Azure's load balancer distributes traffic across them.

#### 18.7 Quick comparison

| Feature | App Service | App Service Plan | Web App |
|---|---|---|---|
| What is it? | Azure hosting platform | Compute resources | Your application |
| Contains | Web Apps, API Apps, etc. | CPU, RAM, OS, pricing | Application code |
| Billing | Through the plan | Yes | No separate compute charge |
| Scaling | Supported | Defines scale | Uses the plan's resources |
| Multiple apps? | Yes | Yes | One application |

#### 18.8 Easy way to remember

Imagine renting office space:

- **App Service** = the business park that provides facilities and management.
- **App Service Plan** = the office building you rent (size, capacity, cost).
- **Web App** = your company's office operating inside that building.

The building determines how much space and power you have, while your office is the actual business running inside it.

### 8. What are Azure Functions?

**Answer:**

Azure Functions runs code in response to events — HTTP requests, timers, queues, blobs, Event Grid, Service Bus, and more. Bindings handle a lot of the input and output plumbing for you. The hosting plan you pick determines scaling, cold-start behavior, networking, run duration, and cost.

For example: a blob upload triggers a Function that validates and processes it, writes a status to a database, and sends failures to a dead-letter path. Because events can be delivered more than once, the function is written so that running it twice causes no harm, and any external calls it makes use limited retries and correlation IDs.

I configure managed identity, Key Vault access, Application Insights, timeouts, concurrency, alerts, and failure handling. Durable Functions is the right tool when the workflow needs orchestration or state.

### 9. What is the difference between App Service and Azure Functions?

**Answer:**

App Service hosts a web app or API that runs continuously, with its own application process and plan. Functions organizes code around triggers and events, and can scale execution up or down based on those events. Both are managed platforms, and they share some capabilities and plans under the hood.

I choose App Service for a full web application or API that needs to always be on, with routing, slots, and longer-lived requests. I choose Functions for queue, timer, blob, or event handlers, or a small API where scaling by trigger makes sense.

I weigh cold start, run duration, state, networking, runtime, throughput, and cost.

An architecture can use both at once: App Service serves the API, while queue-triggered Functions handle the asynchronous work behind it.

### 10. What is Azure SQL Database?

**Answer:**

Azure SQL Database is a managed, SQL Server-compatible database. Azure handles platform patching, backups, and built-in availability; I manage schema, queries and indexes, users, data protection, performance tier, networking, recovery policy, and how resilient the application is to hiccups.

I use Entra authentication or managed identity, a firewall or private endpoint, TLS, auditing and Defender, access scoped to only what's needed, and monitoring. Point-in-time restore and geo-replication or failover groups get chosen based on how much data loss and downtime the business can actually tolerate.

When the database is slow, I look at query performance, wait stats, blocking, CPU and IO, the connection pool, indexes and query plans, and any recent changes. Scaling up can help in the moment, but it doesn't replace actually fixing the query or the root cause.
