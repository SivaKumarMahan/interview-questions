# Azure Services: Containers, Messaging, and Monitoring

> AKS microservices architecture, Azure Container Registry, Service Bus and Event Grid, and monitoring Azure services.

## Key Concepts

### AKS Microservices Architecture

**Core components:**

- **AKS cluster:** A managed Kubernetes control plane, with node pools sized and separated to match each workload's needs.
- **Virtual Network:** The private network boundary for nodes, Pods, private endpoints, and any controlled connection back to on-premises systems.
- **Azure Container Registry:** Private storage for container images that have been scanned and signed. AKS pulls them using managed identity and RBAC.
- **Ingress and Azure Load Balancer/Application Gateway:** Handles external entry, TLS termination, routing, health checks, and an optional web application firewall.
- **Azure Pipelines:** Builds, tests, and scans the code, publishes an image that won't change once tagged, and promotes releases that have passed review.
- **Helm:** Packages Kubernetes resources and environment-specific values, and keeps a versioned history so upgrades and rollbacks are possible.
- **Azure Monitor:** Collects monitoring data from the control plane, nodes, containers, applications, logs, metrics, and traces.

**Deployment flow:**

1. Provision the VNet, AKS, ACR, identity, private DNS, ingress, monitoring, and policies through reviewed infrastructure-as-code.
2. Build and scan each microservice image, then push its digest (a fixed, unchangeable reference to that exact image) to ACR.
3. Validate and deploy versioned Helm charts, with readiness and startup probes and realistic resource requests.
4. Send a small amount of traffic to the new version, run smoke and business tests, and watch errors, latency, how close resources are to their limits, and the health of dependencies.
5. Either promote gradually, or roll back the traffic and the release if the health checks fail.

A production setup also needs zone distribution, autoscaling, PodDisruptionBudgets, NetworkPolicies, workload identity, secrets pulled from an external store, backup and restore, certificate rotation, cost controls, and a regional recovery plan that's actually been tested.

## Interview Questions

### 1. What is Azure Container Registry?

**Answer:**

ACR is a private registry for container images and related artifacts. It supports repositories, geo-replication on the right tiers, build tasks, webhooks, retention and isolation features, and integration with Azure identity.

CI builds and scans an image, pushes it with a digest (a fixed reference that always points to that exact image) using workload identity, signs it, and deployments reference that digest directly. AKS pulls it through managed identity with the `AcrPull` role — nobody shares the registry's admin password.

I restrict public and network access where needed, apply repository permissions, retention rules, auditing, and a vulnerability-scanning workflow. When I see `ImagePullBackOff`, I check the image tag and digest, the registry login and role, network and private DNS settings, node architecture, and the pod's events.

### 2. What is Azure Service Bus?

**Answer:**

Service Bus is enterprise messaging built around queues and topics with subscriptions. It supports multiple consumers competing for work, publish-subscribe patterns, message locks, dead-letter queues, scheduled messages, duplicate detection, ordered sessions, and transactions in some scenarios.

A producer sends a durable message; a consumer picks it up under a lock, processes it in a way that's safe even if it runs twice, and marks it complete. On failure, the message is abandoned and retried, and after enough failed attempts it goes to the dead-letter queue. I keep an eye on active and dead-letter message counts, message age, throttling, and processing latency.

Managed identity and roles scoped to just sending or just receiving protect access. I choose Service Bus when messages genuinely need to be processed reliably — not just when I need to announce that something happened.

### 3. What is Azure Event Grid?

**Answer:**

Event Grid routes events from Azure or custom sources to handlers like Functions, Logic Apps, webhooks, Service Bus, or Event Hubs. It's built for fast, reactive fan-out with filtering, and it delivers each event at least once.

For example: a blob-created event triggers metadata processing and a notification. The handler validates the event, is written to tolerate being run twice, responds quickly, and relies on retries and a dead-letter destination for failures.

The event payload usually just describes what happened; the consumer goes and fetches the real data separately if it needs to.

I monitor delivery failures and dead-lettered events, and secure webhook validation and identity. Event Grid isn't a substitute for the richer guarantees of a real command queue.

### 4. What is the difference between Service Bus and Event Grid?

**Answer:**

Service Bus carries commands and messages that a consumer needs to reliably process from a queue or topic, with locks, completion tracking, dead-lettering, sessions, and richer broker features. Event Grid just announces that something happened, and routes that announcement quickly to subscribers with filtering and fan-out.

I use Service Bus for something like order processing, where each message needs controlled completion, retry, and ordering. I use Event Grid to tell several different handlers that a blob or resource just changed.

The two can work together: Event Grid spots an event and routes the important work into Service Bus for controlled processing.

I decide between them based on delivery guarantees, ordering, transactions, retention, throughput, how consumers are structured, retry behavior, and what the payload needs to carry.

### 5. How do you monitor Azure services?

**Answer:**

I turn on platform metrics, diagnostic settings pointed at Log Analytics, Event Hub, or Storage as needed, Application Insights or OpenTelemetry for application traces, alerts with action groups, workbooks, and whatever health signals the service itself provides.

Monitoring is driven by what actually matters to the business: availability, latency, errors, traffic, how close resources are to their limits, dependency failures, queue age, capacity, and security-relevant changes. Every alert has an owner, a runbook, and gets tested.

When investigating an issue, I pin down the time window and scope, compare the Activity Log and recent deployments against the metrics, follow a request through its dependencies using a correlation or trace ID, fix the immediate problem, then confirm the original user-facing transaction actually works again.

Retention, access control, sampling, how many unique label combinations get tracked, and ingestion cost all get designed deliberately — not left at whatever the defaults happen to be.
