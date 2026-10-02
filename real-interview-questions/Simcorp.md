# SimCorp Interview Questions

Real interview questions with simple, easy-to-read answers.

---

## 1. How did you upgrade the Kubernetes version?

For an interview, answer this as an **AKS Kubernetes upgrade**. Keep it practical and structured.

### Sample answer

> "In my project, we used **Azure Kubernetes Service (AKS)**. Before upgrading the Kubernetes version, I first checked the current cluster version and the supported upgrade versions.
>
> I reviewed the AKS release notes and checked whether our workloads, Helm charts, ingress controller, and other add-ons were compatible with the target version.
>
> Then I tested the upgrade in the lower environment first. I verified the application health, pod status, readiness/liveness probes, PDBs, resource requests and limits, and node capacity.
>
> After getting approval, we upgraded the cluster during a planned maintenance window. AKS performs a **rolling upgrade** of the nodes. It cordons and drains nodes and moves the workloads to other available nodes, so with proper replica configuration and PDBs, we can achieve zero or minimal downtime.
>
> After the upgrade, I verified the Kubernetes version, nodes, pods, services, ingress, application connectivity, and monitoring. I also checked the application logs and Azure Monitor/Prometheus dashboards.
>
> Finally, I performed smoke testing with the application team and monitored the cluster for some time to make sure there were no issues."

### Commands to mention

Check current version:

```bash
kubectl version
kubectl get nodes
```

For AKS, check available upgrades:

```bash
az aks get-upgrades \
  --resource-group <resource-group> \
  --name <aks-cluster>
```

Upgrade:

```bash
az aks upgrade \
  --resource-group <resource-group> \
  --name <aks-cluster> \
  --kubernetes-version <target-version>
```

Verify after upgrade:

```bash
kubectl get nodes
kubectl get pods -A
kubectl get deployments -A
kubectl get events -A
```

### If they ask: "How did you achieve zero downtime?"

> "We maintained multiple replicas, configured appropriate **PodDisruptionBudgets**, used **readiness probes**, and ensured sufficient **node capacity**. During the rolling node upgrade, workloads were rescheduled onto healthy nodes while traffic continued to go to the available pods."

### If they ask: "What challenges did you face?"

> "The main things I checked were deprecated Kubernetes APIs, incompatible Helm charts or ingress controllers, insufficient node capacity, PDBs preventing node draining, and workloads without proper readiness probes. We identified these in the lower environment before performing the production upgrade."

---

## 2. What challenges did you face while upgrading the Kubernetes version?

For an interview, give a realistic AKS example rather than listing ten generic problems.

### Sample answer

> "During one of our AKS upgrades, the main challenges were **compatibility** and **workload availability**.
>
> First, we checked for **deprecated Kubernetes APIs** because some older API versions are removed in newer Kubernetes releases. We reviewed our application manifests and Helm charts and updated them where required.
>
> Second, we had to make sure the **ingress controller and other Kubernetes add-ons** were compatible with the target version.
>
> Another challenge was **node draining**. Some pods could not be evicted immediately because of PodDisruptionBudgets or because the application didn't have enough replicas. We reviewed the PDB configuration and increased replicas where required.
>
> We also checked **node capacity** because during a rolling upgrade, workloads from a node being upgraded need to run on other available nodes.
>
> After the upgrade, we validated all nodes, pods, services and ingress, and checked application logs and monitoring dashboards. We also performed application smoke testing to confirm there was no functional impact."

### If the interviewer asks for one specific incident

> "One issue we faced was that a workload had a strict **PodDisruptionBudget allowing zero disruption**. During node drain, AKS couldn't evict the pod immediately. We identified this from the node drain events, reviewed the PDB configuration, and adjusted it to allow controlled disruption while maintaining application availability. After that, the node upgrade continued successfully."

### Key challenges to remember

| Challenge | Action |
|---|---|
| Deprecated APIs | Update manifests/Helm charts |
| Helm/add-on compatibility | Verify supported versions |
| PodDisruptionBudget | Can block node draining |
| Insufficient replicas | Risk of application downtime |
| Node capacity | Ensure workloads can be rescheduled |
| Readiness/liveness probes | Verify they work correctly after upgrade |
| Ingress/networking | Validate ingress controller and connectivity |
| Post-upgrade validation | Check nodes, pods, services, logs and application health |

> **Tip:** Don't say you faced all eight. Pick **one concrete problem**, explain how you detected it, fixed it, and validated the upgrade. That sounds much more credible.

---

## 3. What code tests/checks have you performed in CI/CD? (e.g., SonarQube, Trivy)

In an interview, explain it as **multiple quality and security checks** in the CI pipeline, not just SonarQube and Trivy.

### Sample answer

> "In our CI/CD pipeline, we performed different types of checks before deploying the application. The exact checks depended on the application, but our pipeline generally included code compilation, unit testing, code quality analysis, security scanning, Docker image scanning, and deployment validation.
>
> For **code quality**, we used **SonarQube** to check bugs, vulnerabilities, code smells, duplicated code, and code coverage. We configured a **quality gate**, and if the quality gate failed, the pipeline stopped.
>
> We also ran **unit tests** as part of the application build. For Java applications, we used Maven, for example `mvn test` or `mvn clean test`.
>
> For **container security**, after building the Docker image, we used **Trivy** to scan the image for vulnerabilities. If critical vulnerabilities crossed our configured threshold, the pipeline failed and the image was not pushed to ACR.
>
> We also performed **dependency/security checks** where required, checking third-party libraries for known vulnerabilities.
>
> After these checks passed, we pushed the image to **Azure Container Registry** and deployed it to **AKS**. After deployment, we performed health checks or smoke tests to verify that the application was running correctly."

### Typical pipeline

```
Developer Push / PR
        ↓
Checkout Code
        ↓
Build / Compile
        ↓
Unit Tests
        ↓
SonarQube Analysis
        ↓
SonarQube Quality Gate
        ↓
Dependency / Security Scan
        ↓
Docker Build
        ↓
Trivy Image Scan
        ↓
Push Image to ACR
        ↓
Deploy to AKS
        ↓
Smoke / Health Tests
```

### Examples you can mention

| Check | Tool | Purpose |
|---|---|---|
| Build/Compile | Maven / npm | Verify application builds successfully |
| Unit Testing | JUnit / Jest | Validate application functionality |
| Code Quality | SonarQube | Bugs, code smells, coverage, vulnerabilities |
| Dependency Scan | Trivy / Snyk | Identify vulnerable dependencies |
| Container Scan | Trivy | Scan Docker image vulnerabilities |
| IaC Scan | Checkov / tfsec | Find Terraform/IaC security issues |
| YAML Validation | kubectl / pipeline validation | Validate Kubernetes manifests |
| Docker Validation | Docker | Verify image builds correctly |
| Deployment Test | kubectl / Helm | Verify Kubernetes deployment |
| Smoke Test | curl / application tests | Verify application is accessible |

### If they ask: "What happens if Trivy finds a CRITICAL vulnerability?"

> "The Trivy scan returns a **non-zero exit code**, so the CI pipeline fails. We don't push that image to ACR or deploy it to AKS. We review the vulnerability, update the base image or dependency, rebuild the image, and run the scan again."

### One important distinction

Don't say SonarQube is only a security scanner. It is primarily used for **static code quality analysis**, although it also identifies certain security issues.

A strong interview sentence:

> "Our CI pipeline had quality gates at multiple levels: **unit tests** for functionality, **SonarQube** for code quality, **Trivy** for dependency and container vulnerabilities, and **post-deployment smoke tests** for application validation."

---

## 4. How many YAML pipelines do you have for each environment in Azure DevOps?

For an interview, don't give an unnecessarily large number. Explain the pipeline design and environment separation clearly.

### Sample answer

> "We followed a YAML-based CI/CD approach in Azure DevOps. We generally had **one main multi-stage YAML pipeline per application**, rather than creating a separate YAML pipeline for every environment.
>
> The same pipeline handled Development, QA, UAT, and Production through **separate stages**.
>
> For example:
>
> Build → Test → SonarQube → Docker Build → Trivy Scan → Push to ACR → Deploy Dev → Deploy QA → Deploy UAT → Approval → Deploy Production.
>
> We used **environment-specific variable groups** and **Azure DevOps Environments** for configuration and approvals. This avoided duplicating the same pipeline YAML for every environment."

### Example structure

```
azure-pipelines.yml
│
├── Build
├── Unit Test
├── SonarQube
├── Docker Build
├── Trivy Scan
├── Push to ACR
│
├── Deploy Dev
├── Deploy QA
├── Deploy UAT
└── Deploy Prod
        └── Approval
```

Environment mapping example:

```
Dev    → dev variable group  + dev AKS
QA     → qa variable group   + qa AKS
UAT    → uat variable group  + uat AKS
Prod   → prod variable group + prod AKS
```

### If they ask: "Did you have separate pipelines?"

> "For some applications or organizational requirements, we did have separate pipelines, but wherever possible we preferred a **single reusable multi-stage YAML pipeline**. We also used **YAML templates** for common build, security-scan, and deployment logic so that we didn't duplicate code across pipelines."

---

## 5. Where do you store your secrets?

For an Azure DevOps + AKS project, the answer is **Azure Key Vault**.

### Sample answer

> "We stored sensitive information such as database passwords, API keys, tokens, and certificates in **Azure Key Vault** rather than keeping them directly in the YAML pipeline or source code.
>
> Azure DevOps accessed Key Vault securely through a **service connection or managed identity**, depending on the setup. In the pipeline, we retrieved the required secrets at runtime and passed them to the deployment without hardcoding them.
>
> For AKS workloads, we could also use the **Azure Key Vault CSI Driver** to mount secrets into pods when required.
>
> Access to Key Vault was controlled using **Azure RBAC**, and we followed least-privilege access. We also enabled features such as **soft delete** and **purge protection** to protect secrets from accidental deletion."

### Simple architecture

```
Azure DevOps Pipeline
        |
        | Managed Identity / Service Connection
        ↓
   Azure Key Vault
        |
        | Secret
        ↓
    AKS Deployment
        |
        ↓
       Pod
```

### Examples of secrets

```
DB_USERNAME
DB_PASSWORD
API_KEY
CLIENT_SECRET
CERTIFICATE
CONNECTION_STRING
```

### If they ask: "Did you store secrets in Azure DevOps?"

> "We avoided storing actual secret values directly in YAML. For **non-sensitive configuration**, we used variable groups. For **sensitive values**, we preferred Azure Key Vault and retrieved them securely during the pipeline or application runtime."

### If they ask: "How does AKS access Key Vault?"

> "We used a **User Assigned Managed Identity** with the required Key Vault permissions. For workloads that needed secrets inside the pod, we used the **Azure Key Vault CSI Driver**. This avoided putting credentials directly inside Kubernetes Secrets or application configuration."

> **Remember:** Kubernetes Secrets are not automatically secure just because they are called Secrets. They are only **base64-encoded** by default, so for sensitive production credentials, integrating AKS with Key Vault is a better approach.

---

## 6. Will there be downtime when you rotate secrets in Key Vault?

Not necessarily. Secret rotation in Azure Key Vault itself does not cause application downtime. The impact depends on **how the application consumes the secret**.

### Sample answer

> "No, rotating a secret in Azure Key Vault does not by itself cause downtime. The important point is how the application retrieves the secret.
>
> If the application **reads the secret dynamically at runtime**, the new value can be picked up without restarting the application.
>
> If the secret is **loaded only during application startup**, then we need to restart or redeploy the pods to pick up the new value. In AKS, we can avoid downtime by using multiple replicas and performing a **rolling restart**.
>
> We also make sure the new secret is validated before removing or invalidating the old secret, so that the application continues working during the rotation."

### Example with AKS + Key Vault CSI Driver

```
Old Secret
    ↓
Key Vault
    ↓
AKS Pod
    ↓
Rotate Secret
    ↓
New Secret
    ↓
CSI Driver updates mounted secret
```

> **Important detail:** Updating the mounted secret does not necessarily mean the application immediately uses the new value. If the application reads the secret only once at startup, you still need an application reload/restart.

### Safe production rotation

```
1. Create new secret/version
          ↓
2. Verify new credential
          ↓
3. Update Key Vault
          ↓
4. Refresh/reload application
          ↓
5. Validate application
          ↓
6. Disable old credential
```

For AKS, use multiple replicas + rolling restart if the application needs a restart:

```bash
kubectl rollout restart deployment <deployment-name>
kubectl rollout status deployment <deployment-name>
```

### Short interview answer

> "Key Vault secret rotation itself doesn't cause downtime. If the application needs a restart to consume the new secret, we use multiple replicas and a rolling restart so traffic continues to be served by healthy pods."

---

## 7. Dev, QA, UAT are in one RG & subscription; Pre-Prod and Prod are in another RG & subscription, but both subscriptions are in the same region. How will you achieve disaster recovery?

The key issue: **separate subscriptions and resource groups in the same region are not, by themselves, disaster recovery.** If the entire Azure region goes down, both environments can be affected.

### Sample answer

> "If Dev, QA and UAT are in one subscription and resource group, and Pre-Prod and Production are in another subscription and resource group, but both subscriptions are in the same Azure region, I would not consider that a complete DR setup.
>
> For disaster recovery, I would keep Production in the **primary region** and create the DR environment in a **different Azure region**. The DR resources can be in a separate subscription and resource group as well.
>
> For AKS, I would have a **secondary AKS cluster** in the DR region with the required networking, ACR access, Key Vault integration, ingress, monitoring and application configuration.
>
> For the database and persistent data, I would configure the appropriate Azure-native replication or backup mechanism, such as **geo-replication** or **geo-redundant backups**, depending on the database technology.
>
> We would also replicate or make available container images, secrets/configuration and infrastructure definitions in the DR region.
>
> During a regional disaster, we would deploy or activate the application in the DR region, switch DNS or traffic through **Azure Front Door / Traffic Manager**, validate the application, and then restore normal traffic after the primary region is recovered."

### Architecture

```
                 PRIMARY REGION
        ┌─────────────────────────┐
        │ Prod Subscription       │
        │                         │
Users → │ Front Door / DNS        │
        │        ↓                │
        │      AKS                │
        │        ↓                │
        │    Database             │
        └─────────────────────────┘
                  │
                  │ Replication
                  ↓
                 DR REGION
        ┌─────────────────────────┐
        │ DR Subscription         │
        │                         │
        │      AKS                │
        │        ↓                │
        │  Replicated Database    │
        │                         │
        └─────────────────────────┘
```

### What about the current same-region setup?

> "The separate subscriptions give us **administrative and security isolation**, but they don't protect us from a **regional outage** because both are in the same region. For true regional DR, I would introduce a secondary region."

### HA vs DR

**High Availability:**

```
Same region
Multiple AZs / nodes / replicas
        ↓
Protects against component or zone failure
```

**Disaster Recovery:**

```
Primary Region
       ↓
Secondary Region
       ↓
Protects against regional disaster
```

> **Note:** You don't necessarily need Dev/QA/UAT duplicated in the DR region. DR requirements are normally focused on **Production and its critical dependencies**. The exact DR design should be based on the application's **RTO and RPO**.

---

## 8. What production issue did you resolve recently? How? (Memory leak in pods)

For an interview, present this as a real incident flow: **detection → investigation → root cause → immediate fix → permanent fix → prevention**.

### Sample answer

> "Recently, we had a production issue where some application pods were continuously consuming memory. Initially, the pods were running normally, but their memory usage gradually increased and eventually they were getting restarted with **OOMKilled**.
>
> We first detected the issue through our **monitoring alerts**. I checked the pod status and saw that the affected pods were restarting.
>
> I used `kubectl describe pod` and checked the container termination reason. It showed **OOMKilled**. Then I checked the pod's memory usage and application logs to understand whether there was an application-level issue.
>
> We compared the memory usage over time and found that memory was **continuously increasing instead of being released**. This indicated a possible memory leak in the application.
>
> As an **immediate mitigation**, we increased the number of replicas and adjusted the memory limit based on the application's actual usage. This reduced the impact on users while we investigated the root cause.
>
> We then worked with the **development team** to analyze the application and identified the memory leak. They fixed the code and provided a new application build.
>
> We deployed the fixed version through our CI/CD pipeline and monitored memory utilization after deployment. The memory usage remained stable and the pods stopped getting restarted.
>
> As a **preventive measure**, we improved memory monitoring and alerts and reviewed the application's resource requests and limits."

### Commands to mention

Check pod status:

```bash
kubectl get pods -n <namespace>
```

Check why the pod restarted:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:

```
Reason: OOMKilled
Exit Code: 137
```

Check current resource usage:

```bash
kubectl top pod -n <namespace>
```

Check previous container logs:

```bash
kubectl logs <pod-name> -n <namespace> --previous
```

Check deployment:

```bash
kubectl get deployment <deployment-name> -n <namespace>
```

### If they ask: "How did you prove it was a memory leak?"

> "We monitored the memory usage over time. The memory consumption continuously increased after each request cycle and was not coming back down. Eventually it reached the container memory limit and Kubernetes terminated the container with OOMKilled. After the development team fixed the application, we deployed the new version and observed that memory usage stabilized. That confirmed the application-level memory leak was the root cause."

> **Important:** Don't say "I fixed the memory leak by increasing the memory limit." That's not a real fix. Increasing the limit is only a **temporary mitigation**. The permanent solution is identifying and **fixing the application memory leak**.

---

## 9. How do you secure your Terraform state file?

### Sample answer

> "We never store the Terraform state file locally or commit it to Git. We use a **remote backend**, typically an **Azure Storage Account**, to store the state centrally.
>
> The storage account is secured using **Azure AD/RBAC** rather than sharing storage account keys. Only the required DevOps pipeline identity and authorized engineers have access to the state container.
>
> We also enable **encryption at rest**, **soft delete/versioning** where appropriate, and restrict network access using **private endpoints or firewall rules**.
>
> Terraform state can contain sensitive information, so we make sure the state storage has strict access control. We also protect the state from concurrent modifications using **Terraform state locking**.
>
> Finally, we keep the backend configuration separate from application code and make sure `.tfstate` and `.tfstate.backup` are included in `.gitignore` so they aren't accidentally committed."

### Typical Azure setup

```
Azure DevOps Pipeline
        |
        | Managed Identity / Service Principal
        ↓
Azure Storage Account
        |
        └── tfstate container
                |
                └── terraform.tfstate
```

### Important points to mention

| Point | Why |
|---|---|
| Remote backend | Azure Storage Account instead of local state |
| RBAC | Restrict who can read/write state |
| Encryption at rest | Protects stored data |
| Private Endpoint / firewall | Restrict network access |
| State locking | Prevents concurrent Terraform operations |
| Versioning / soft delete | Recovery from accidental changes/deletion |
| `.gitignore` | Never commit `.tfstate` to Git |
| No manual edits | Don't manually edit the state file |

### If they ask: "Can Terraform state contain secrets?"

> "Yes. Terraform state can contain sensitive values depending on the resources being managed. Marking a variable as `sensitive = true` mainly prevents it from being displayed in CLI output; it **does not remove the value from the state file**. Therefore, protecting the backend itself is critical."

---

## 10. Basic database (SQL) queries

For a DevOps interview, these are the basic SQL queries you should be comfortable with.

### 1. Select all records

```sql
SELECT * FROM employees;
```

### 2. Select specific columns

```sql
SELECT name, salary
FROM employees;
```

### 3. WHERE condition

```sql
SELECT *
FROM employees
WHERE department = 'IT';
```

### 4. AND / OR

```sql
SELECT *
FROM employees
WHERE department = 'IT'
AND salary > 50000;
```

```sql
SELECT *
FROM employees
WHERE department = 'IT'
OR department = 'HR';
```

### 5. ORDER BY

Highest salary first:

```sql
SELECT *
FROM employees
ORDER BY salary DESC;
```

Lowest salary first:

```sql
SELECT *
FROM employees
ORDER BY salary ASC;
```

### 6. DISTINCT

```sql
SELECT DISTINCT department
FROM employees;
```

### 7. COUNT

```sql
SELECT COUNT(*)
FROM employees;
```

Count employees in IT:

```sql
SELECT COUNT(*)
FROM employees
WHERE department = 'IT';
```

### 8. GROUP BY

Count employees by department:

```sql
SELECT department, COUNT(*)
FROM employees
GROUP BY department;
```

### 9. HAVING

Departments with more than 5 employees:

```sql
SELECT department, COUNT(*)
FROM employees
GROUP BY department
HAVING COUNT(*) > 5;
```

### 10. LIKE

Names starting with A:

```sql
SELECT *
FROM employees
WHERE name LIKE 'A%';
```

Names containing k:

```sql
SELECT *
FROM employees
WHERE name LIKE '%k%';
```

### 11. BETWEEN

```sql
SELECT *
FROM employees
WHERE salary BETWEEN 50000 AND 100000;
```

### 12. IN

```sql
SELECT *
FROM employees
WHERE department IN ('IT', 'HR', 'Finance');
```

### 13. NULL

```sql
SELECT *
FROM employees
WHERE manager_id IS NULL;
```

Not null:

```sql
SELECT *
FROM employees
WHERE manager_id IS NOT NULL;
```

### 14. INSERT

```sql
INSERT INTO employees
(name, department, salary)
VALUES
('Siva', 'IT', 80000);
```

### 15. UPDATE

```sql
UPDATE employees
SET salary = 90000
WHERE name = 'Siva';
```

> Always use `WHERE` with `UPDATE` unless you intentionally want to update every row.

### 16. DELETE

```sql
DELETE FROM employees
WHERE name = 'Siva';
```

> Again, without `WHERE`, you can delete every row.

### 17. INNER JOIN

Suppose:

```
employees
---------
id
name
department_id

departments
-----------
id
department_name
```

Query:

```sql
SELECT e.name, d.department_name
FROM employees e
INNER JOIN departments d
ON e.department_id = d.id;
```

### 18. LEFT JOIN

```sql
SELECT e.name, d.department_name
FROM employees e
LEFT JOIN departments d
ON e.department_id = d.id;
```

Returns all employees, even if they don't have a matching department.

### 19. MAX / MIN / AVG / SUM

```sql
SELECT MAX(salary) FROM employees;
SELECT MIN(salary) FROM employees;
SELECT AVG(salary) FROM employees;
SELECT SUM(salary) FROM employees;
```

### 20. Second highest salary

A common interview question:

```sql
SELECT MAX(salary)
FROM employees
WHERE salary < (
    SELECT MAX(salary)
    FROM employees
);
```

### Practice topics

Be ready to write queries or explain:

- Find duplicate records
- Find second/third highest salary
- Count records by department
- Find employees without a manager
- Find employees whose salary is greater than the average
- INNER JOIN vs LEFT JOIN
- DELETE vs TRUNCATE vs DROP
- Primary key vs foreign key
- Indexes
- WHERE vs HAVING
- UNION vs UNION ALL
- Basic SELECT, INSERT, UPDATE, DELETE

---

## 11. Details about PostgreSQL database

For a DevOps interview, you don't need to go deep into PostgreSQL internals unless the role specifically asks for DBA skills. Focus on **architecture, connectivity, backup/restore, HA, monitoring, and troubleshooting**.

### PostgreSQL basics

PostgreSQL is an **open-source relational database management system**. It uses SQL and is commonly used as the backend database for web applications, APIs, and microservices.

Typical architecture:

```
Application / Microservice
          |
          | TCP 5432
          ↓
   PostgreSQL Server
          |
    ┌─────┴─────┐
    ↓           ↓
 Database     Database
    |
  Schema
    |
  Tables
    |
   Rows
```

### Important terms

| Term | Meaning |
|---|---|
| Database | A logical container for tables, views, functions, etc. |
| Schema | A namespace inside a database used to organize objects |
| Table | Stores structured data in rows and columns |
| Primary Key | Uniquely identifies a row |
| Foreign Key | Creates a relationship between tables |

```
PostgreSQL
   └── Database
        └── Schema
             └── Tables
```

### Default PostgreSQL port

PostgreSQL normally listens on **5432**.

```
Application → PostgreSQL:5432
```

In Azure, you might have:

```
AKS Pod
   ↓
Private DNS
   ↓
Azure Database for PostgreSQL
   ↓
Port 5432
```

### Basic PostgreSQL commands

Connect to PostgreSQL:

```bash
psql -h <hostname> -U <username> -d <database>

# Example
psql -h postgres.example.com -U appuser -d myapp
```

`psql` meta-commands:

| Command | Purpose |
|---|---|
| `\l` | List databases |
| `\c myapp` | Connect to a database |
| `\dt` | List tables |
| `\d employees` | Describe a table |
| `\dn` | List schemas |
| `\q` | Exit |

### Basic SQL

Create table:

```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    department VARCHAR(50),
    salary NUMERIC(10,2)
);
```

Insert:

```sql
INSERT INTO employees
(name, department, salary)
VALUES
('Siva', 'IT', 80000);
```

Select:

```sql
SELECT * FROM employees;
```

Update:

```sql
UPDATE employees
SET salary = 90000
WHERE id = 1;
```

Delete:

```sql
DELETE FROM employees
WHERE id = 1;
```

### Backup and restore

This is important for a DevOps interview.

Plain SQL backup with `pg_dump`:

```bash
pg_dump -h <host> -U <user> -d <database> > backup.sql
```

Restore:

```bash
psql -h <host> -U <user> -d <database> < backup.sql
```

Custom-format backup:

```bash
pg_dump -Fc -h <host> -U <user> -d <database> -f backup.dump
```

Restore:

```bash
pg_restore -h <host> -U <user> -d <database> backup.dump
```

### High availability

PostgreSQL can be configured with a **primary and standby/replica** architecture.

```
              Application
                   |
                   ↓
             Primary DB
                   |
             Replication
                   ↓
             Standby DB
```

If the primary fails, a standby can be promoted depending on the HA setup.

For **Azure Database for PostgreSQL**, Azure provides managed capabilities for backups, high availability, and other operational features depending on the service/tier.

### Troubleshooting (502 / 504 from an app that uses PostgreSQL)

Troubleshoot in this order:

1. Check application pods:

   ```bash
   kubectl get pods -n <namespace>
   ```

2. Check application logs:

   ```bash
   kubectl logs <pod-name> -n <namespace>
   ```

   Look for:

   ```
   connection refused
   connection timeout
   authentication failed
   too many connections
   connection pool exhausted
   ```

3. Test DNS from the pod:

   ```bash
   kubectl exec -it <pod-name> -n <namespace> -- nslookup <postgres-host>
   ```

4. Test port connectivity:

   ```bash
   kubectl exec -it <pod-name> -n <namespace> -- nc -zv <postgres-host> 5432
   ```

5. Check PostgreSQL connectivity:

   ```bash
   psql -h <postgres-host> -U <username> -d <database>
   ```

6. Check Azure networking:

   ```
   AKS subnet
      ↓
   NSG / Firewall
      ↓
   Private Endpoint
      ↓
   Private DNS
      ↓
   PostgreSQL
   ```

A DNS problem, firewall restriction, NSG rule, private endpoint issue, or incorrect credentials can prevent connectivity.

### Connection pool

Applications usually don't create a brand-new database connection for every request. They use a **connection pool**.

```
100 application requests
        ↓
   Connection Pool
        ↓
   10 DB connections
        ↓
   PostgreSQL
```

If the pool is exhausted, the application may show errors such as:

```
Connection pool exhausted
Timeout waiting for connection
```

You should check:

- Maximum pool size
- Connection timeout
- Idle connections
- PostgreSQL `max_connections`
- Application replica count

> **Common production problem:** setting the pool too high on every pod.
>
> `20 pods × 50 DB connections = potentially 1000 connections`, while PostgreSQL may only allow a much smaller number.

### Useful monitoring queries

Check active connections:

```sql
SELECT count(*)
FROM pg_stat_activity;
```

See current connections:

```sql
SELECT pid, usename, datname, client_addr, state
FROM pg_stat_activity;
```

Find long-running queries:

```sql
SELECT pid,
       now() - query_start AS duration,
       query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
```

Check database sizes:

```sql
SELECT datname,
       pg_size_pretty(pg_database_size(datname))
FROM pg_database;
```

### Indexes

Indexes improve query performance.

```sql
CREATE INDEX idx_employee_department
ON employees(department);
```

> Don't create indexes blindly. Indexes consume storage and can add overhead to `INSERT`, `UPDATE`, and `DELETE`.

### PostgreSQL vs MySQL

| PostgreSQL | MySQL |
|---|---|
| Open-source relational DB | Open-source relational DB |
| Strong SQL compliance | Widely used relational DB |
| Advanced data types/features | Generally simpler to operate |
| Strong support for complex queries | Common for web applications |
| Excellent extensibility | Large ecosystem |

> Don't claim that one is universally "better." The choice depends on application requirements.

### Most important PostgreSQL topics for a DevOps interview

- PostgreSQL architecture
- Port 5432
- Database/schema/table
- Users and permissions
- Backup and restore
- HA and replication
- Connection pooling
- `pg_stat_activity`
- Indexes and slow queries
- AKS → PostgreSQL connectivity
- Private Endpoint and Private DNS
- Firewall/network troubleshooting
- Azure PostgreSQL monitoring
- RPO/RTO and DR

---

## 12. Application is running in AKS, but it cannot connect to PostgreSQL. How will you troubleshoot it?

For an interview, answer this in a **layer-by-layer troubleshooting sequence**. Don't immediately assume PostgreSQL itself is down.

### Sample answer

> "If an application running in AKS cannot connect to PostgreSQL, I troubleshoot from the **application layer down to the database layer**.
>
> First, I check whether the application pods are running and look at the **application logs** for the exact error, such as connection timeout, connection refused, authentication failure, or DNS resolution failure.
>
> Next, I verify the **PostgreSQL hostname and port** in the application configuration. PostgreSQL normally uses port 5432.
>
> Then I test **DNS resolution** from inside the AKS pod to make sure the PostgreSQL hostname resolves to the expected IP address.
>
> After that, I test **network connectivity** from the pod to port 5432. If DNS works but port 5432 is unreachable, I investigate the network path, such as NSGs, firewall rules, Private Endpoint, routing, or NetworkPolicy.
>
> If network connectivity is working, I test **PostgreSQL authentication** using the same credentials and database name. I check whether the user has permission to access the database.
>
> Then I check **PostgreSQL itself**. I verify whether the database is available, whether there are too many connections, and whether there are any resource or service issues.
>
> Finally, after identifying and fixing the issue, I restart or redeploy the application only if required and perform an **end-to-end connectivity test**."

### Troubleshooting flow

```
AKS Pod
   |
   | 1. Application logs
   ↓
Configuration
   |
   | 2. Hostname / Port / Credentials
   ↓
DNS
   |
   | 3. Does PostgreSQL hostname resolve?
   ↓
Network
   |
   | 4. Can pod reach TCP 5432?
   ↓
Private Endpoint / NSG / Firewall / NetworkPolicy
   |
   | 5. Is traffic allowed?
   ↓
PostgreSQL
   |
   | 6. Authentication / permissions
   ↓
Database health
   |
   | 7. Connections / resources / queries
   ↓
Application
```

### Step 1: Check pods and logs

```bash
kubectl get pods -n <namespace>
kubectl logs <pod-name> -n <namespace>
```

Look for errors such as:

```
connection timed out
connection refused
password authentication failed
could not translate host name
too many connections
```

### Step 2: Verify configuration

Check how the application gets its DB configuration:

```
DB_HOST
DB_PORT
DB_NAME
DB_USERNAME
DB_PASSWORD
```

For example:

```
DB_HOST=postgres.example.com
DB_PORT=5432
```

> Don't print the actual password in logs.

### Step 3: Test DNS from the pod

```bash
kubectl exec -it <pod-name> -n <namespace> -- nslookup <postgres-host>
```

If DNS fails, investigate the Private DNS Zone, DNS configuration, or the hostname.

### Step 4: Test port 5432

```bash
kubectl exec -it <pod-name> -n <namespace> -- nc -zv <postgres-host> 5432
```

If it fails, investigate this network path:

```
AKS
 ↓
NSG
 ↓
Route
 ↓
Private Endpoint / Firewall
 ↓
PostgreSQL
```

### Step 5: Test the actual PostgreSQL connection

If `psql` is available:

```bash
psql -h <postgres-host> \
     -p 5432 \
     -U <username> \
     -d <database>
```

This helps distinguish **network connectivity** problems from **authentication/database** problems.

### Step 6: Check PostgreSQL

Check active connections:

```sql
SELECT count(*)
FROM pg_stat_activity;
```

Check connection details:

```sql
SELECT pid, usename, datname, client_addr, state
FROM pg_stat_activity;
```

Also check:

- PostgreSQL service/instance health
- `max_connections`
- CPU and memory
- Storage
- Firewall rules
- Database/user permissions
- Long-running queries

### Step 7: If Azure Private Endpoint is used

This is particularly important in an AKS + Azure PostgreSQL architecture.

```
AKS
 ↓
Private DNS
 ↓
PostgreSQL FQDN
 ↓
Private IP
 ↓
Private Endpoint
 ↓
Azure PostgreSQL
```

Verify that the PostgreSQL hostname resolves to the **private IP**, not an unexpected public IP.

### Strong closing statement

> "I don't start by restarting the pods. First I identify whether the problem is **application configuration, DNS, network connectivity, authentication, or PostgreSQL health**. Once I isolate the layer causing the failure, I fix that specific issue and then validate end-to-end connectivity."

---

## 13. What types of applications are used in the frontend and backend? (Frontend: React.js, Backend: Java Spring Boot)

### Sample answer

> "In our application, we used **React.js for the frontend** and **Java Spring Boot for the backend**.
>
> React.js is used to build the user interface that users interact with through the browser. It communicates with the backend through **REST APIs**.
>
> The Spring Boot backend contains the **business logic** and exposes REST APIs. It handles authentication, request processing, database operations, and communication with other services.
>
> Our backend services communicate with the **PostgreSQL** database for storing and retrieving application data.
>
> We containerized both frontend and backend applications using **Docker** and deployed them as **separate workloads in AKS**."

### Overall architecture

```
                    End User
                       |
                       ↓
                  Web Browser
                       |
                       ↓
                  React.js
                 Frontend
                       |
                  REST API
                       ↓
              Java Spring Boot
                  Backend
                       |
              ┌────────┴────────┐
              ↓                 ↓
        PostgreSQL         Other APIs/
          Database         Microservices
```

### Technologies you can mention

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React.js | User interface |
| Backend | Java Spring Boot | REST APIs and business logic |
| Database | PostgreSQL | Application data |
| Container | Docker | Package applications |
| Orchestration | Kubernetes / AKS | Run and manage containers |
| API | REST | Frontend-backend communication |
| Build | Maven | Build Java application |
| CI/CD | Azure DevOps | Build, test and deployment |
| Container Registry | Azure Container Registry | Store Docker images |
| Ingress | Application Gateway / Ingress | Route external traffic |

### If they ask: "How does a user request flow through your application?"

> "The user accesses the application through the browser. The request reaches the frontend, which is hosted in our AKS environment. When the frontend needs data, it makes a **REST API call** to the Spring Boot backend. The backend processes the request and communicates with PostgreSQL or another required microservice. The response is then returned to the frontend and displayed to the user."

```
User
 ↓
Application Gateway / Ingress
 ↓
React.js Pod
 ↓
Spring Boot API
 ↓
PostgreSQL
 ↓
Spring Boot
 ↓
React.js
 ↓
User
```

> This answer works well for a DevOps Engineer interview because it connects the application stack directly to the Kubernetes and Azure infrastructure you're expected to manage.

---

## 14. Did you provide RCA to clients?

For an interview, answer with a **specific incident** and a clear **RCA structure**.

### Sample answer

> "Yes, whenever we had a significant production incident that impacted the client, we prepared and shared an **RCA**.
>
> For example, we had an incident where application pods were getting **OOMKilled** because their memory usage was continuously increasing. We first mitigated the issue by increasing replicas and ensuring the application remained available. Then we analyzed the pod metrics, logs, and application behavior and identified a **memory leak** in the application.
>
> We documented the incident with the **impact, timeline, root cause, immediate resolution, permanent fix, and preventive actions**. After the development team fixed the memory leak, we deployed the new version and monitored the pods to confirm that memory usage was stable.
>
> We then shared the RCA with the client and discussed the preventive actions with them."

### Typical RCA format

```
1. Incident Summary
2. Business / Application Impact
3. Incident Timeline
4. Detection
5. Immediate Mitigation
6. Root Cause
7. Permanent Resolution
8. Preventive / Corrective Actions
9. Monitoring Improvements
```

### Example

| Section | Example |
|---|---|
| Incident | Application pods restarted |
| Impact | Some requests were affected |
| Detection | Memory alert + pod restart |
| Immediate action | Increased replicas / stabilized workload |
| Root cause | Application memory leak |
| Permanent fix | Code fix + new application version |
| Validation | Memory usage remained stable |
| Prevention | Memory alerts and resource review |

### If they ask: "How did you communicate the RCA to the client?"

> "We first validated the technical root cause internally. Then we prepared a clear RCA **without unnecessary technical jargon**, explained the business impact, what caused the issue, what we did to resolve it, and what actions we were taking to prevent recurrence. We reviewed it with the client in a meeting or shared the documented RCA through the agreed communication channel."
