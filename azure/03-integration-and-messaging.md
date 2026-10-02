# Azure: Integration and Messaging

> Functions vs Logic Apps, Queue Storage, and using Functions with Data Factory and Power Platform.

## Key Concepts

### Azure Functions vs. Logic Apps

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

### Azure Queue Storage

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

Design consumers to be idempotent, since a message can be delivered more than once. Use visibility timeouts, retry handling, and poison-message handling.

**Interview distinction:** Queue Storage is a good choice for straightforward queueing. Azure Service Bus is generally preferred when enterprise messaging features such as topics, subscriptions, sessions, transactions, duplicate detection, or dead-lettering are required.

### Azure Functions with Azure Data Factory

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

### Azure Functions with Power Platform

An HTTP-triggered Function can extend Power Apps and Power Automate with capabilities that are difficult to implement using low-code components alone.

Common uses include:

- Complex validation or business rules
- External API integration
- Data transformation
- AI or custom library calls

Power Apps can call the Function and use its response interactively. Power Automate can call it as one step in a wider workflow. Secure the endpoint with an appropriate identity and authorization model rather than exposing an anonymous production Function.
