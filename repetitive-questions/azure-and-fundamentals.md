# Repetitive Interview Questions: Azure Services and Fundamentals

> Short, common questions that do not belong to one tool: VM vs container, Pod IPs, a quick brief on Azure Batch, Entra ID, and Azure Monitor, Entra ID vs app registration vs service principal, Azure AI services, and the SQL queries a DevOps engineer should know.

## VM vs container

**Interviewer:** What is the difference between a VM and a container?

**Candidate:**

A **VM** virtualizes the **hardware**. Each VM has its own full operating system. A **container** virtualizes the **operating system**. All containers on a host share the host's kernel and package only the app and its libraries.

```text
VM                                  Container
--------------------------          --------------------------
App A      | App B                  App A      | App B
Libraries  | Libraries              Libraries  | Libraries
Guest OS   | Guest OS               Container runtime (containerd)
Hypervisor (Hyper-V, KVM)           Host OS kernel (shared)
Physical server                     Host OS
                                    Physical server or VM
```

| | VM | Container |
| --- | --- | --- |
| What is virtualized | Hardware | Operating system |
| Operating system | Own guest OS | Shares the host kernel |
| Size | Gigabytes | Megabytes |
| Start time | Minutes | Seconds or less |
| Isolation | Strong (separate kernel) | Lighter (namespaces and cgroups) |
| OS mix | Any OS on any host | Linux containers need a Linux kernel; Windows containers need Windows |
| Managed by | Hypervisor | Container runtime, usually orchestrated by Kubernetes |

### When I use which

- **VMs:** legacy apps that need a full OS, Windows services, software that needs kernel changes, or workloads that need strong isolation. In Azure: Virtual Machines and VM Scale Sets.
- **Containers:** microservices, CI build agents, apps that need fast scaling and the same image in every environment. In Azure: AKS, Container Apps, App Service for containers, ACI.

### Remember

- Containers usually run **on** VMs. In AKS, every node is a VM, and Pods run on those VMs.
- Containers start fast because there is no OS to boot. The process starts directly on the shared kernel.
- When a container needs stronger isolation, AKS **Pod Sandboxing** (Kata Containers) gives each Pod its own lightweight VM kernel.

**In one line:** "A VM carries its own operating system, so it is heavier but more isolated. A container shares the host kernel, so it is small and starts in seconds. In my work, AKS nodes are VMs and the applications run as containers on them."

## Are Pod IPs static or dynamic?

**Interviewer:** What are static and dynamic IPs for Pods?

**Candidate:**

Pod IPs are **dynamic**. When a Pod is deleted or rescheduled, the new Pod usually gets a new IP. So applications must never depend on a Pod IP.

```text
Before:  orders-7f9c-abcde  -> 10.244.1.6
Pod restarts on another node
After:   orders-7f9c-xyz12  -> 10.244.2.10
```

What I use instead, depending on what needs to stay stable:

| Need | Use |
| --- | --- |
| A stable address for a group of Pods inside the cluster | **Service** (ClusterIP and DNS name such as `orders.orders.svc.cluster.local`) |
| A stable name for each Pod (databases, Kafka) | **StatefulSet + headless Service**: `kafka-0.kafka.ns.svc.cluster.local`. The name is stable, but the IP can still change. |
| A fixed public or private IP for incoming traffic | **LoadBalancer Service** with a pre-created static IP in Azure, or Application Gateway / Ingress with a static IP |
| A fixed outbound IP (a partner allows only one IP) | **NAT Gateway** or a static outbound IP on the AKS load balancer. All Pods leave through it. |

Example: a LoadBalancer Service using a static public IP created beforehand:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: orders-public
  annotations:
    service.beta.kubernetes.io/azure-pip-name: pip-orders-prod
    service.beta.kubernetes.io/azure-load-balancer-resource-group: rg-network-prod
spec:
  type: LoadBalancer
  selector:
    app: orders
  ports:
    - port: 443
      targetPort: 8443
```

### Remember

- Where the Pod IP comes from depends on the network plugin. With **Azure CNI Overlay**, Pods get IPs from a private overlay range. With classic **Azure CNI**, Pods get IPs directly from the VNet subnet, so the subnet must be large enough.
- `spec.loadBalancerIP` is deprecated. Use the Azure annotations shown above.
- Firewalls and NSGs should never allow single Pod IPs. Allow the subnet, the Service, or the NAT Gateway IP.

## Give a brief on Azure Batch, Microsoft Entra ID, and Azure Monitor

**Interviewer:** Explain Azure Batch, Entra ID, and Azure Monitor in short.

**Candidate:**

| Service | What it is | One example |
| --- | --- | --- |
| **Azure Batch** | Runs large parallel or HPC jobs on a pool of VMs that Azure creates, scales, and removes for you | Render thousands of video frames, run simulations, process millions of files overnight |
| **Microsoft Entra ID** (formerly Azure AD) | Cloud identity and access service: users, groups, apps, sign-in, MFA, Conditional Access, managed identities | Engineers sign in with MFA; a pipeline logs in to Azure with workload identity federation |
| **Azure Monitor** | Collects metrics and logs from Azure resources and apps, and alerts on them | CPU alert on a VM Scale Set, KQL alert on failed backup jobs, Application Insights for app performance |

### Azure Batch in a little more detail

```text
Create a Batch account
-> create a pool (VM size, OS image, autoscale formula, Spot VMs to save cost)
-> submit a job with many tasks
-> Batch spreads the tasks across the pool VMs
-> results are written to Blob Storage
-> the pool scales down to zero when the work is done
```

When not to use Batch: for small or container-based jobs, **Container Apps jobs**, **AKS Jobs**, or **Azure Functions** are often simpler.

### Microsoft Entra ID in a little more detail

- **Authentication:** who are you (password, MFA, passkey, certificate, federated token).
- **Authorization for Azure resources:** Azure RBAC roles assigned to Entra ID users, groups, and identities.
- **Identities for workloads:** app registrations, service principals, and managed identities, so apps and pipelines do not need stored passwords.
- **Security controls:** Conditional Access (for example, block sign-in from unknown countries), Privileged Identity Management (just-in-time admin access).

### Azure Monitor in a little more detail

```text
Metrics (numbers over time)       -> Azure Monitor Metrics
Logs (events, KQL)                -> Log Analytics workspace
Application telemetry             -> Application Insights (stored in Log Analytics)
Prometheus metrics (AKS)          -> Azure Monitor workspace
All of the above                  -> alert rules -> Action Groups -> email, Teams, on-call
```

See [tool-integrations.md](tool-integrations.md) for how applications, AKS, and Splunk connect to Azure Monitor.

## What is the difference between Entra ID, an app registration, and a service principal?

**Interviewer:** What is the difference between Microsoft Entra ID and an app registration?

**Candidate:**

**Entra ID** is the whole identity service, the directory. An **app registration** is one application's **definition** inside it. A **service principal** is that application's **identity in a tenant**, and it is what gets permissions.

```text
Microsoft Entra ID (the tenant / directory)
-> App registration "deploy-pipeline"   (the blueprint: client ID, credentials, API permissions)
   -> Service principal                 (the identity that signs in and gets roles)
      -> Azure RBAC role, for example Contributor on rg-app-prod
```

| Term | What it is | Example |
| --- | --- | --- |
| Microsoft Entra ID | The identity service for users, groups, and apps | The company tenant |
| App registration | The global definition of an app: client ID, secrets or certificates, federated credentials, redirect URIs, API permissions | "deploy-pipeline" registered by the platform team |
| Service principal (enterprise application) | The app's instance in a tenant. Roles and sign-in logs belong to it. | The identity that gets Contributor on a resource group |
| Managed identity | A special service principal that Azure creates and rotates for you. No app registration and no secret to manage. | A Function App reading Key Vault |

### Which one I choose

```text
Does the code run inside Azure (VM, AKS, App Service, Functions)?
  yes -> managed identity
  no  -> is it a pipeline that supports OIDC (Azure DevOps, GitHub Actions, GitLab)?
           yes -> app registration (or user-assigned managed identity) + federated credential, no secret
           no  -> app registration + certificate or secret stored in Key Vault, rotated
```

### Remember

- Roles are given to the **service principal**, not to the app registration.
- An **API permission** (for example Microsoft Graph `User.Read.All`) is different from an **Azure RBAC role** (for example Contributor). One is access to an API, the other is access to Azure resources.
- A client secret has an expiry date. Expired secrets are a common cause of pipelines suddenly failing with `AADSTS7000222`. Federated credentials avoid this.

## Have you used AI services in Azure?

**Interviewer:** Have you used AI services in Azure? What are they?

**Candidate:**

Be honest here. If you have only explored them, say so, and explain how you would use and secure them as a DevOps engineer.

| Service | What it does | Example |
| --- | --- | --- |
| **Azure OpenAI** (Foundry Models) | GPT and embedding models behind a private Azure endpoint | Chat assistant, summarizing logs, explaining Terraform plans |
| **Microsoft Foundry** (formerly Azure AI Foundry) | Platform to build, evaluate, deploy, and monitor AI apps and agents | An internal support assistant |
| **Azure AI Search** | Search and vector search over company documents, used for RAG | A chatbot that answers from runbooks and wiki pages |
| **Document Intelligence** | Extracts text, fields, and tables from PDFs and forms | Reading invoices |
| **Vision, Speech, Language** | Images and OCR; speech to text and back; sentiment, PII detection, summarization | Masking personal data in text |

### A DevOps use case

```text
Pipeline fails
-> a final step collects the error log
-> secrets and personal data are masked
-> the log is sent to Azure OpenAI over a private endpoint, using a managed identity
-> the model returns a short root cause and a suggested fix
-> the summary is posted to Teams or added to the work item
```

### How I would run it securely

- Create the resource and model deployment with Terraform or Bicep, like any other infrastructure.
- Turn off public network access and use a **private endpoint**.
- Use **managed identity** with the **Cognitive Services OpenAI User** role instead of API keys.
- Never send passwords, tokens, or customer data to the model. Mask them first.
- Watch token quotas and cost in Azure Monitor, and set budgets.
- A person reviews the AI suggestion before anything changes in production.

## Which basic SQL queries should a DevOps engineer know?

**Interviewer:** Can you write some basic database queries?

**Candidate:**

I am not a DBA, but I use SQL to check data after deployments, run migrations through the pipeline, and troubleshoot PostgreSQL. The examples use a simple `employees` table.

### Read and filter

```sql
SELECT * FROM employees;                                    -- all rows (avoid on big tables)

SELECT name, salary FROM employees;                         -- only some columns

SELECT * FROM employees WHERE department = 'IT' AND salary > 50000;

SELECT * FROM employees WHERE department IN ('IT', 'HR');

SELECT * FROM employees WHERE name LIKE 'A%';               -- names starting with A

SELECT * FROM employees WHERE manager_id IS NULL;           -- NULL needs IS NULL, not = NULL
```

### Sort, limit, and count

```sql
SELECT * FROM employees ORDER BY salary DESC LIMIT 5;       -- top 5 salaries

SELECT DISTINCT department FROM employees;

SELECT COUNT(*) FROM employees WHERE department = 'IT';
```

### Group

```sql
SELECT department, COUNT(*) AS staff, AVG(salary) AS avg_salary
FROM employees
GROUP BY department
HAVING COUNT(*) > 5                                         -- HAVING filters groups, WHERE filters rows
ORDER BY staff DESC;
```

### Join two tables

```sql
-- INNER JOIN: only employees that have a matching department
SELECT e.name, d.department_name
FROM employees e
JOIN departments d ON d.id = e.department_id;

-- LEFT JOIN: all employees, even those without a department
SELECT e.name, d.department_name
FROM employees e
LEFT JOIN departments d ON d.id = e.department_id;
```

### Change data

```sql
INSERT INTO employees (name, department, salary) VALUES ('Ravi', 'IT', 60000);

UPDATE employees SET salary = salary * 1.10 WHERE department = 'IT';

DELETE FROM employees WHERE id = 42;
```

Always run `UPDATE` and `DELETE` with a `WHERE` clause, and inside a transaction when possible:

```sql
BEGIN;
UPDATE employees SET department = 'Platform' WHERE department = 'DevOps';
-- check the row count, then:
COMMIT;      -- or ROLLBACK;
```

### Second-highest salary (a common trick question)

```sql
SELECT MAX(salary) FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);
```

### PostgreSQL queries I use for troubleshooting

```sql
-- Who is connected, and what are they running?
SELECT pid, usename, application_name, client_addr, state, query_start, left(query, 80) AS query
FROM pg_stat_activity
WHERE datname = current_database();

-- How many connections, by state? (too many "idle" = connection leak or no pooling)
SELECT state, COUNT(*) FROM pg_stat_activity GROUP BY state;

-- Queries running longer than 5 minutes
SELECT pid, now() - query_start AS runtime, left(query, 80) AS query
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 minutes';

-- Stop one stuck query (cancel first; terminate only if cancel does not work)
SELECT pg_cancel_backend(12345);
SELECT pg_terminate_backend(12345);

-- Database and table sizes
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;

-- Max connections allowed
SHOW max_connections;
```

### Remember

- `WHERE` filters rows before grouping. `HAVING` filters after `GROUP BY`.
- `COUNT(*)` counts rows. `COUNT(column)` skips NULLs.
- Schema changes go through **migration tools** (Flyway, Liquibase) in the pipeline, not manual SQL in production.
- On Azure Database for PostgreSQL Flexible Server, **PgBouncer** is built in. Turn it on when many Pods open many connections.

## Quick answers

| Question | Short answer |
| --- | --- |
| VM vs container? | A VM has its own OS (heavier, stronger isolation); a container shares the host kernel (small, starts in seconds). |
| Are Pod IPs static? | No. Use a Service or DNS name; StatefulSet + headless Service for stable names; NAT Gateway for a fixed outbound IP. |
| Azure Batch? | Managed pools of VMs for large parallel jobs; scales up for the job and down after. |
| Entra ID? | Microsoft's cloud identity service: users, groups, apps, MFA, Conditional Access, managed identities. |
| Azure Monitor? | Metrics, logs (Log Analytics), Application Insights, and alerts through Action Groups. |
| App registration vs service principal? | The registration is the app's definition; the service principal is its identity in the tenant and receives the roles. |
| Managed identity? | A service principal that Azure manages, with no secret, for code running in Azure. |
| Azure AI services? | Azure OpenAI, Microsoft Foundry, AI Search, Document Intelligence, Vision, Speech, Language. Secure them with private endpoints and managed identity. |
| WHERE vs HAVING? | WHERE filters rows; HAVING filters groups after GROUP BY. |
| Check DB connections in PostgreSQL? | `pg_stat_activity`, grouped by state. |
