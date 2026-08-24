# Azure Services Interview Questions

---

### 1. What are Azure Virtual Machines?

**Answer:**

Azure VMs are infrastructure-as-a-service compute. Azure runs the physical hardware and the hypervisor; I manage the guest OS, patches, software, configuration, identity, disks, and recovery of the workload itself. VMs attach network interfaces to a VNet and use managed disks for storage.

I reach for VMs when I need legacy software, control over the OS or kernel, an unsupported runtime, or a straightforward lift-and-shift. In production I use Availability Zones or sets as needed, load balancing, backups, monitoring, patch management, managed identity, and infrastructure-as-code. A single VM is a single point of failure.

When something's wrong, I start with Azure's own resource and boot diagnostics and the Activity Log, then move into guest-level CPU, memory, disk, network, and service logs. I always separate "Azure itself has a problem" from "the OS or app has a problem" before I reach for a reboot.

---

### 2. How do you secure Azure Virtual Machines?

**Answer:**

I keep VMs private and reach them through Bastion, VPN, ExpressRoute, or another controlled jump path. I never expose RDP or SSH to the open internet. Network security groups and firewalls only allow the traffic that's actually needed. Signing in through Entra with managed identity, plus RBAC scoped to the minimum needed, cuts down on stored credentials.

I use hardened images, keep patches and updates current, encrypt disks, turn on Secure Boot and vTPM where supported, run endpoint protection or Defender, scan for vulnerabilities, take backups, and send logs somewhere central. Secrets come from Key Vault, not from the VM itself.

I watch for privileged sign-ins, changes to network security group rules, new public IPs, malware alerts, and patch compliance. I also test that recovery actually works.

If I suspect a VM has been compromised, I cut off its network access, preserve evidence following the incident procedure, rotate any credentials it could reach, rebuild from a trusted image, and investigate properly — I don't just reboot it and hope.

---

### 3. What is an Azure Storage Account?

**Answer:**

A Storage Account is Azure's namespace, security, and configuration boundary for Blob, Files, Queue, and Table services, depending on the account type. It controls region, redundancy, performance tier, networking, encryption, identity and RBAC, lifecycle rules, and protection settings.

I pick general-purpose v2 in most cases, choose LRS, ZRS, or GRS based on what failure and recovery-point needs the workload actually has, turn off public or anonymous access unless it's genuinely required, prefer Entra ID and managed identity over keys, enforce HTTPS, use private endpoints or firewalls, and turn on logs, soft delete, versioning, or lifecycle rules depending on the workload.

I keep an eye on capacity, transactions, latency, availability, throttling, and data leaving the account. Recovery features and backup get chosen per service — replication by itself doesn't protect against every kind of deletion or corruption.

---

### 4. What is Azure Blob Storage?

**Answer:**

Blob Storage is object storage for unstructured data — images, logs, backups, build artifacts, static content, data-lake files, that kind of thing. Containers hold block, append, or page blobs, and access tiers let you trade retrieval speed and cost against storage cost.

Applications use the SDK or REST API with managed identity and roles scoped to just the data they need. I use lifecycle rules to move data to cheaper tiers or delete it on a schedule, immutable storage (which can't be altered or deleted before its retention period ends) for regulated data that must be retained, and versioning or soft delete for recovery.

Large uploads go in blocks, with retries designed to be safe even if the same block gets uploaded twice.

I choose Blob over Azure Files when the workload fits object access over HTTP; Files is the better fit for SMB or NFS shares. Monitoring covers request errors, latency, capacity, throttling, and outbound data.

---

### 5. How do you secure Azure Storage?

**Answer:**

I stack several layers of protection rather than relying on one setting. I turn off anonymous blob access, restrict or disable public network access, use private endpoints and private DNS, require HTTPS for all transfers, prefer Entra managed identities and data-level RBAC over account keys, protect and rotate any keys that are still in use, and issue SAS tokens that are short-lived and carry only the permissions they need.

Azure encrypts data at rest by default. I add customer-managed keys or infrastructure-level encryption when the requirement calls for it. I also turn on Defender and logging, use versioning, soft delete, or immutability where it makes sense, and apply policies that stop insecure settings from being created in the first place.

I test that allowed access actually works and denied access actually fails. If there's an exposure, I lock down access, revoke SAS tokens or rotate keys, keep the logs, check what was downloaded or changed, restore data if needed, and fix the underlying policy or architecture.

---

### 6. What is Azure Key Vault?

**Answer:**

Key Vault stores secrets, cryptographic keys, and certificates. Management-plane permissions control the vault's configuration; data-plane permissions control access to what's stored inside it. A subscription Owner doesn't automatically get to read secrets — those are two separate permission systems.

Applications use managed identity with a narrow role, like Key Vault Secrets User. I turn on soft delete and purge protection, enable logging, assign clear ownership for rotation and expiry, and use private networking where it's needed. I never let a secret's value get printed out through a pipeline or an infrastructure-as-code run.

When troubleshooting, I check the identity making the request, whether the vault uses RBAC or the older access-policy model, the role and its scope, whether the role assignment has actually propagated yet, the object's version and state, the token's audience, firewall and private DNS settings, and the audit logs. I test rotation with the actual consumers of the secret, not just in isolation.

---

### 7. What is Azure Managed Identity?

**Answer:**

Managed Identity gives an Azure resource its own Entra identity. A system-assigned identity lives and dies with that one resource; a user-assigned identity is independent and can be reused across resources. Azure manages the credentials behind the scenes, and the workload just requests short-lived tokens.

For example: a Function has a user-assigned identity that's been granted Blob Data Reader on one container and Key Vault Secrets User on one vault. The code uses `DefaultAzureCredential`, and there's no client secret sitting in configuration anywhere.

I scope roles as narrowly as I can, and I use separate identities when workloads need different levels of access. When access fails, I check which identity is attached, whether the right principal or client ID was selected, the token's audience, the RBAC role and its scope, whether the assignment has propagated, and any network restrictions.

---

### 8. What is Microsoft Entra ID?

**Answer:**

Microsoft Entra ID is Microsoft's cloud identity service. It handles users, groups, applications and service principals, managed identities, devices, authentication, Conditional Access, and tokens.

It's a different system from Azure RBAC: Entra ID authenticates who someone is, while Azure RBAC decides what they're allowed to do to Azure resources.

I use groups instead of assigning access to individual users, turn on MFA and Conditional Access, use Privileged Identity Management for privileged roles, prefer workload identity over stored secrets, run access reviews, keep break-glass accounts ready, and watch sign-in and audit logs.

When authentication fails, I check the tenant, the identity's state, credentials or federation, Conditional Access rules, the token's audience and scopes, consent, and the sign-in logs. Once authentication is confirmed, authorization failures point me to roles and policies instead.

---

### 9. What is Azure Container Registry?

**Answer:**

ACR is a private registry for container images and related artifacts. It supports repositories, geo-replication on the right tiers, build tasks, webhooks, retention and isolation features, and integration with Azure identity.

CI builds and scans an image, pushes it with a digest (a fixed reference that always points to that exact image) using workload identity, signs it, and deployments reference that digest directly. AKS pulls it through managed identity with the `AcrPull` role — nobody shares the registry's admin password.

I restrict public and network access where needed, apply repository permissions, retention rules, auditing, and a vulnerability-scanning workflow. When I see `ImagePullBackOff`, I check the image tag and digest, the registry login and role, network and private DNS settings, node architecture, and the pod's events.

---

### 10. What is Azure App Service?

**Answer:**

App Service is a managed platform for hosting web apps and APIs. Azure runs the OS and runtime; teams deploy their code or container and configure the plan, scaling, domains and TLS, identity, networking, diagnostics, and application behavior.

In production I use multiple instances or zones where they're available, a health check, autoscale, managed identity with Key Vault references, VNet integration or private endpoints as needed, deployment slots, and Application Insights.

I deploy to a slot, warm it up and test it, then swap it into production — keeping database changes backward-compatible so the swap doesn't break anything. When something fails, I check deployment logs, app logs, instance health, configuration, identity, DNS and networking, dependencies, and platform metrics before I roll back or swap.

---

### 11. What are Azure Functions?

**Answer:**

Azure Functions runs code in response to events — HTTP requests, timers, queues, blobs, Event Grid, Service Bus, and more. Bindings handle a lot of the input and output plumbing for you. The hosting plan you pick determines scaling, cold-start behavior, networking, run duration, and cost.

For example: a blob upload triggers a Function that validates and processes it, writes a status to a database, and sends failures to a dead-letter path. Because events can be delivered more than once, the function is written so that running it twice causes no harm, and any external calls it makes use limited retries and correlation IDs.

I configure managed identity, Key Vault access, Application Insights, timeouts, concurrency, alerts, and failure handling. Durable Functions is the right tool when the workflow needs orchestration or state.

---

### 12. What is Azure SQL Database?

**Answer:**

Azure SQL Database is a managed, SQL Server-compatible database. Azure handles platform patching, backups, and built-in availability; I manage schema, queries and indexes, users, data protection, performance tier, networking, recovery policy, and how resilient the application is to hiccups.

I use Entra authentication or managed identity, a firewall or private endpoint, TLS, auditing and Defender, access scoped to only what's needed, and monitoring. Point-in-time restore and geo-replication or failover groups get chosen based on how much data loss and downtime the business can actually tolerate.

When the database is slow, I look at query performance, wait stats, blocking, CPU and IO, the connection pool, indexes and query plans, and any recent changes. Scaling up can help in the moment, but it doesn't replace actually fixing the query or the root cause.

---

### 13. What is Azure Service Bus?

**Answer:**

Service Bus is enterprise messaging built around queues and topics with subscriptions. It supports multiple consumers competing for work, publish-subscribe patterns, message locks, dead-letter queues, scheduled messages, duplicate detection, ordered sessions, and transactions in some scenarios.

A producer sends a durable message; a consumer picks it up under a lock, processes it in a way that's safe even if it runs twice, and marks it complete. On failure, the message is abandoned and retried, and after enough failed attempts it goes to the dead-letter queue. I keep an eye on active and dead-letter message counts, message age, throttling, and processing latency.

Managed identity and roles scoped to just sending or just receiving protect access. I choose Service Bus when messages genuinely need to be processed reliably — not just when I need to announce that something happened.

---

### 14. What is Azure Event Grid?

**Answer:**

Event Grid routes events from Azure or custom sources to handlers like Functions, Logic Apps, webhooks, Service Bus, or Event Hubs. It's built for fast, reactive fan-out with filtering, and it delivers each event at least once.

For example: a blob-created event triggers metadata processing and a notification. The handler validates the event, is written to tolerate being run twice, responds quickly, and relies on retries and a dead-letter destination for failures.

The event payload usually just describes what happened; the consumer goes and fetches the real data separately if it needs to.

I monitor delivery failures and dead-lettered events, and secure webhook validation and identity. Event Grid isn't a substitute for the richer guarantees of a real command queue.

---

### 15. What is Azure Policy?

**Answer:**

Azure Policy checks resource configuration against rules at whatever scope you assign it. Depending on the policy's effect, it can audit, deny, modify, append to, or deploy required settings. Initiatives group related policies together, and exemptions document any approved exceptions.

For example: audit storage accounts for public access, deploy diagnostic settings automatically, then deny new insecure storage accounts once the existing ones are fixed. I roll out audit mode first, look at false positives and the impact on existing resources, fix what needs fixing, then switch to enforcement. Policies and their assignments are version-controlled like code.

I test both compliant and non-compliant deployments, watch the compliance trend, and require exceptions to have an owner, a justification, and an expiry date. Policy is about governance — RBAC is what actually controls who can act.

---

### 16. What is the difference between Service Bus and Event Grid?

**Answer:**

Service Bus carries commands and messages that a consumer needs to reliably process from a queue or topic, with locks, completion tracking, dead-lettering, sessions, and richer broker features. Event Grid just announces that something happened, and routes that announcement quickly to subscribers with filtering and fan-out.

I use Service Bus for something like order processing, where each message needs controlled completion, retry, and ordering. I use Event Grid to tell several different handlers that a blob or resource just changed.

The two can work together: Event Grid spots an event and routes the important work into Service Bus for controlled processing.

I decide between them based on delivery guarantees, ordering, transactions, retention, throughput, how consumers are structured, retry behavior, and what the payload needs to carry.

---

### 17. What is the difference between App Service and Azure Functions?

**Answer:**

App Service hosts a web app or API that runs continuously, with its own application process and plan. Functions organizes code around triggers and events, and can scale execution up or down based on those events. Both are managed platforms, and they share some capabilities and plans under the hood.

I choose App Service for a full web application or API that needs to always be on, with routing, slots, and longer-lived requests. I choose Functions for queue, timer, blob, or event handlers, or a small API where scaling by trigger makes sense.

I weigh cold start, run duration, state, networking, runtime, throughput, and cost.

An architecture can use both at once: App Service serves the API, while queue-triggered Functions handle the asynchronous work behind it.

---

### 18. How do you use Key Vault with App Service or Functions?

**Answer:**

I turn on managed identity, grant it a narrow Key Vault data role, set up network access and private DNS, then use a Key Vault reference in app settings, or access it directly through the SDK with `DefaultAzureCredential`.

The app setting holds a reference URI, not the actual secret value. I plan out how refresh and rotation should behave, and I avoid pinning to a specific secret version if I want rotation to happen automatically, unless controlled versioning is actually the goal.

I test startup and rotation, both allowed and denied identities, slot-specific identity and settings, and how the app behaves on failure. When troubleshooting, I check the reference's status, which identity got selected, the role and its scope, whether RBAC has propagated, the vault's network settings, DNS, the secret's expiry and state, and the logs.

No secret value ever gets printed in diagnostics.

---

### 19. How do you monitor Azure services?

**Answer:**

I turn on platform metrics, diagnostic settings pointed at Log Analytics, Event Hub, or Storage as needed, Application Insights or OpenTelemetry for application traces, alerts with action groups, workbooks, and whatever health signals the service itself provides.

Monitoring is driven by what actually matters to the business: availability, latency, errors, traffic, how close resources are to their limits, dependency failures, queue age, capacity, and security-relevant changes. Every alert has an owner, a runbook, and gets tested.

When investigating an issue, I pin down the time window and scope, compare the Activity Log and recent deployments against the metrics, follow a request through its dependencies using a correlation or trace ID, fix the immediate problem, then confirm the original user-facing transaction actually works again.

Retention, access control, sampling, how many unique label combinations get tracked, and ingestion cost all get designed deliberately — not left at whatever the defaults happen to be.
