# Azure: Compute and Application Hosting

> App Service, Azure Functions and triggers, virtual machines and scale sets, and running microservices on AKS.

## Key Concepts

### Azure App Service Web Apps

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

### Azure Functions

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
- Distributed functions need good logging, correlation, retries, and idempotency — meaning it's safe to run the same operation more than once.

**Example flow:** A user uploads a photo to Blob Storage. A Function is triggered, validates or transforms the image, calls an API, and writes metadata to a database.

### Common Azure Function Triggers

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

### When Serverless Is a Good Fit

Use serverless for event-driven systems, variable or intermittent workloads, automation, small APIs, and independently scalable processing steps.

Consider another hosting model when workloads require consistently low latency, long-running processes, extensive local state, or predictable sustained compute where another pricing model is more economical.

### Azure Functions and Virtual Machines

**Azure Functions** is event-driven serverless compute. Common triggers are HTTP, timer, Blob, queue, and Event Grid.

It's a strong fit for short-lived APIs, automation, scheduled work, notifications, and event processing. Choose the plan, timeout, memory, concurrency, retry and dead-letter behavior, identity, secret access, and observability deliberately — don't just take the defaults.

It's not automatically the best fit for anything long-running, stateful, or connection-heavy.

**Azure Virtual Machines** give you operating-system control, for legacy applications, custom software, migration workloads, self-managed tools, and development environments.

They need patching, image management, endpoint protection, backup, monitoring, least-privilege access, and capacity planning.

Use private IPs by default, and reach VMs through Azure Bastion or controlled just-in-time administration instead of exposing RDP or SSH publicly. Use VM Scale Sets when you're scaling identical instances horizontally.

A VM that's just stopped can still cost you in compute charges. **Stopped (deallocated)** actually releases that compute allocation — though disks and other attached resources still cost money on their own.

### Virtual Machine Scale Sets

VM Scale Sets run a group of identically configured VMs, and tie into load balancing, health checks, autoscale, and rolling upgrades. Scaling out adds instances once demand crosses a threshold you've set; scaling in removes the extra capacity once things settle down.

A production setup needs minimum, maximum, and default capacity, health probes, a zone or fault-domain strategy, instance repair, graceful termination, image versioning, health gates during rolling upgrades, and enough time for the application to actually start up.

Autoscaling won't fix inefficient code or an overloaded database. Check end-to-end latency, queue depth, dependency limits, and cost after scaling, not just before. For events you can predict, scheduled scaling can add capacity ahead of the traffic instead of reacting to it.

### AKS Microservices Reference Architecture

An Azure microservices platform can use Azure DevOps to build, test, scan, and publish container images to Azure Container Registry (ACR). Each image is immutable — once published, it never changes; a new version just gets a new tag. AKS pulls those images using a managed identity or workload identity with the narrow `AcrPull` permission.

Helm packages the Kubernetes manifests and environment values. A deployment pipeline or GitOps controller then promotes that same chart and image digest through each environment.

```text
developer -> Azure DevOps CI -> ACR
                              -> Helm/GitOps -> AKS
internet -> Front Door/WAF or Application Gateway -> AKS ingress/Gateway -> Services -> Pods
Pods -> Key Vault / Cosmos DB / Redis / Service Bus through private networking
Pods -> Azure Monitor, Log Analytics and Application Insights
```

Use an AKS-supported CNI and data-plane configuration and enforce NetworkPolicy, but check what Cilium and policy features are actually supported for the AKS version you're running.

Keep secrets in Key Vault and pull them in through workload identity, the CSI driver, or an approved external-secrets pattern. Don't store long-lived cloud credentials in Helm values.

A production design also needs resource requests and limits, probes, autoscaling, PodDisruptionBudgets, an image-signing and scanning policy, RBAC, backup and recovery, and a rollback path that's actually been tested.

## Interview Questions

### 1. How do you deploy applications to Azure Kubernetes Service?

**Answer:**

My delivery flow:

1. Build and test the application.
2. Create a minimal container image, generate an SBOM (a list of everything that went into the image), and scan it.
3. Push a digest — a fixed reference to that exact image — to Azure Container Registry.
4. Deploy to AKS using Helm, plain manifests, or GitOps with Flux or Argo CD.
5. Use workload identity and the Key Vault CSI driver for Azure access and secrets.
6. Set requests and limits, probes, Pod security, NetworkPolicy, horizontal autoscaling, and a PodDisruptionBudget.
7. Wait for the rollout, run smoke tests, and watch for errors and latency.

If a rollout fails, I check `kubectl describe`, the events, current and previous logs, whether the image pulled, configuration, probes, scheduling, and dependencies. If user impact is growing, I roll back the traffic or the release, keep the evidence, fix it in a lower environment, then redeploy a fresh, unchanged version.

### 2. How do you resize an Azure VM, and does it require a reboot?

**Answer:**

In the portal, select the VM, open **Size** under Availability + scale, pick a compatible size, and apply it — the same thing can be done through the CLI or infrastructure-as-code. A resize normally restarts the VM.

If the size you want isn't available on the current hardware cluster, Azure may need to stop and deallocate the VM first, which releases any dynamic public IP unless it's set up as static.

Before resizing, I check the application's maintenance windows, disk and network compatibility, availability-set or zone constraints, capacity, cost, backups, and how to roll back if needed.

### 3. Can an OS disk be removed from an Azure VM?

**Answer:**

You can't just detach the OS disk from a running VM the way you'd detach an ordinary data disk. Azure supports an OS-disk swap for a stopped VM in supported scenarios, and you can build a replacement VM from a managed-disk snapshot or image.

I take an application-consistent backup first, confirm what the actual recovery goal is, and use the documented swap or rebuild process rather than attempting a destructive detach.

### 4. Are you charged for an Azure VM that is stopped but not deallocated?

**Answer:**

Yes. A VM that's stopped from inside the guest OS, or that shows as **Stopped**, can still hold onto its compute allocation and keep incurring compute charges. **Stopped (deallocated)** actually releases that allocation and stops the compute charges — though managed disks, snapshots, public IPs, and other attached resources can still cost money.

I use scheduled deallocation for non-production workloads, and I check the actual power state and the cost of anything still attached, rather than assuming "stopped" means "not costing anything."
