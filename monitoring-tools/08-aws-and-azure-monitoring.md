# Monitoring Tools: AWS and Azure Monitoring

> CloudWatch and CloudTrail on AWS, and Azure Monitor, Log Analytics, KQL, Application Insights, alerts and diagnostic settings on Azure.

## Key Concepts

### CloudWatch

CloudWatch collects AWS service and custom metrics, logs, Logs Insights queries, alarms, dashboards, synthetic checks, and event-driven integrations.

Common signals to watch:

| Service | What to watch |
| --- | --- |
| EC2 | How close resources are to their limits, instance status checks |
| Lambda | Errors, duration, throttles |
| ALB | Latency, HTTP error rates |
| ECS / EKS | Service health |
| RDS | Capacity, connection count |
| SQS | Queue depth, message age |

Route actionable alarms through SNS or an incident-management platform, and actually test the full notification path — don't assume it works just because the alarm exists.

### CloudTrail

CloudTrail is an audit trail for AWS API activity. Each record shows the principal, the action, the time, the source, the target, and the result.

Best practice: centralize organization trails in a protected account, turn on the management and data events you actually need, encrypt and retain the logs, and alert on high-risk changes — things like policy changes, identity changes, logging being disabled, key changes, or a resource becoming publicly accessible.

### Using CloudWatch and CloudTrail Together

Compare a CloudWatch symptom, like a latency spike or an error rate increase, against deployment and configuration events, then confirm the cause with CloudTrail evidence of what actually changed. CloudTrail tells you what changed and who changed it; it isn't an application-performance monitor on its own.

### Diagnosing Missing S3 Log Uploads

1. Check the collector: is it reading the log path, and is there a backlog?
2. Check disk and spool health on the source host.
3. Confirm which AWS identity the collector is actually using.
4. Check `s3:PutObject` permission, and look for denies from the bucket policy, an SCP, or a permissions boundary.
5. If the bucket uses KMS, check the required encryption permissions.
6. Check region, prefix, and multipart upload errors.

CloudTrail data events and the collector's own metrics tell you whether AWS rejected the request or the collector never attempted one in the first place.

Once fixed, verify a fresh object lands with the correct encryption, and set up alerts on upload age and failure count so it doesn't go unnoticed again.

### Azure Monitor Overview

Azure Monitor is the umbrella platform for Azure metrics, logs, traces, alerts, workbooks, and integrations. Platform metrics give you numeric time series for each resource.

### Azure Monitor Core Building Blocks

| Component | What it does |
| --- | --- |
| Diagnostic settings | Route a resource's logs and metrics to Log Analytics, Storage, Event Hubs, or a partner tool |
| Log Analytics | Stores and queries log data using KQL (Kusto Query Language) |
| Application Insights | Captures application requests, dependencies, exceptions, traces, and availability tests, usually through OpenTelemetry |
| Alerts and action groups | Fire notifications or trigger automation when a condition is met |
| Workbooks | Build reusable dashboards and reports on top of the data above |

Workspace boundaries should reflect who needs access, data residency rules, retention requirements, ownership, and cost.

### Deploying Azure Monitoring Correctly

Data Collection Rules and diagnostic settings need to be deployed consistently, through IaC or Policy rather than by hand. After deployment, generate a known event and confirm it actually arrives. An enabled setting with no confirmed data flowing through it is not real monitoring.

### What a Good Azure Alert Looks Like

A production alert needs:

- A signal that matters to users
- A threshold or dynamic condition
- An evaluation window
- A severity level
- An owner
- An action group
- A linked runbook

Test both the firing notification and the resolved notification before you trust the alert.

### Investigating an Azure Incident

Start with the affected transaction. Compare Application Insights requests and dependencies against resource metrics, Log Analytics data, deployment markers, and Azure Activity Log changes. Confirm recovery by running the same transaction again.

### Monitoring Multiple AKS Clusters

For several AKS clusters, use:

- Azure Monitor container insights data where it's needed
- Azure Managed Prometheus, or self-managed Prometheus, for Kubernetes metrics
- Azure Managed Grafana, or Grafana, for shared views across clusters
- Centralized but access-controlled Log Analytics workspaces

Add cluster, subscription, region, and environment labels, but avoid high-cardinality dimensions — labels with too many unique values, such as raw user or request IDs, which drive up cost and slow down queries.

## Interview Questions

### 1. What is the difference between CloudWatch and CloudTrail?

**Answer:**

CloudWatch holds operational monitoring data: metrics, logs, dashboards, alarms, synthetic checks, and event integrations. CloudTrail records AWS API activity for audit and investigation.

In practice, I use CloudWatch to spot that latency or errors went up, then use CloudTrail to check whether a deployment role or an administrator changed the load balancer, a security policy, or a scaling setting around that same time.

CloudTrail isn't a substitute for application tracing, and CloudWatch alone doesn't give a full identity audit trail. In production, I use centralized, protected CloudTrail trails, turn on the data events that matter, enable encryption and retention, make sure CloudWatch alarms are actually actionable, and test that SNS or the incident tool really receives them.

### 2. How would you monitor an EC2 CPU incident?

**Answer:**

First I check the basics in CloudWatch: how long the high CPU has lasted, whether customers are actually affected, instance status checks, autoscaling activity, any recent deployments or config changes, and CPU credit exhaustion if it's a burstable instance type.

Then on the host itself, I compare load average, user versus system CPU time, CPU steal, I/O wait, and the top processes.

To stabilize things, I shift traffic away, scale out, roll back a bad deployment, or stop a runaway job once I've confirmed it's safe to stop. I avoid rebooting before I've captured evidence of what was happening.

The real fix depends on what I find. It could be profiling the code, fixing a slow query or cache, correcting a scheduled job, improving autoscaling triggers, or moving to a better-suited instance type.

Afterward, I confirm user-facing latency and error rates are back to normal under load, and I set up alerts for CPU running close to its limit, credit exhaustion, request queueing, and failed scaling events.

### 3. Logs are not uploading from a healthy EC2 instance to S3. How do you investigate?

**Answer:**

First I confirm the log collector is actually reading current files, that its local spool disk is healthy, and that it attempted an upload at all.

Then I check permissions. I run `aws sts get-caller-identity` to see which role the instance is actually using, and check the target bucket, region, and prefix. I look for `s3:PutObject` permission, any explicit denies coming from the bucket policy, an SCP, or a permissions boundary, and the KMS `Encrypt`/`GenerateDataKey` permissions if the bucket uses KMS encryption. I also check required tags or conditions, clock skew, and multipart upload failures.

I look at the collector's own error logs and at CloudTrail data events for that bucket, without ever printing credentials to the screen.

Once I find the real cause, I fix that one thing: the collector, the IAM policy, the KMS permission, the path, or the storage config. Then I verify a fresh object lands with the right encryption and metadata, and that downstream consumers pick it up.

To stop it recurring, I use instance or task roles instead of long-lived keys, keep permissions scoped to only what's needed, and alert on collector backlog, upload age, and error counts.

### 4. How do you monitor Azure resources in production?

**Answer:**

I start with the user journey and the service's goals. Then I use Azure Monitor metrics, resource diagnostic settings, Log Analytics, Application Insights, the Activity Log, alerts with action groups, and workbooks.

I watch availability, latency, errors, traffic, saturation (how close a resource is to its limit), dependency failures, queue age, and capacity — not just VM CPU.

For an incident, I fix the time window and scope first. Then I compare healthy and unhealthy traffic, check deployment and Activity Log changes, follow Application Insights dependencies, and query the relevant resource logs. I fix the confirmed cause and confirm recovery using the original transaction.

Monitoring is deployed through IaC or Policy. Access and retention are controlled, and alert delivery is tested regularly.

### 5. What are Azure diagnostic settings?

**Answer:**

Diagnostic settings route a resource's supported log and metric categories to Log Analytics, Storage, Event Hubs, or a partner tool. Categories differ by resource type, so nothing is enabled everywhere by default.

I choose destinations based on query needs, SIEM requirements, archiving, retention, and cost. I deploy settings consistently, trigger a known event, and check that the resource ID, timestamp, and fields show up correctly at the destination. I also alert on ingestion gaps and lock down the destination against unauthorized deletion.

### 6. What are Log Analytics and KQL?

**Answer:**

Log Analytics is the Azure Monitor tool for querying workspace log tables. KQL, or Kusto Query Language, is a read-only pipeline language you use to filter data, select columns, parse fields, summarize results, and join tables.

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| summarize Requests=count(),
            Failures=countif(Success == false),
            P95=percentile(DurationMs, 95)
  by bin(TimeGenerated, 5m)
```

I scope the time range and resource early. I confirm the right table and schema with a known event, and I avoid expensive broad joins. Once a query is proven, I turn it into a saved function, a workbook, or an alert. Workspace design also covers region, RBAC, retention, data residency, and ingestion cost.

### 7. What is Application Insights, and how would you investigate a slow API?

**Answer:**

Application Insights captures requests, dependencies, exceptions, traces, availability tests, and distributed correlation through SDK or OpenTelemetry instrumentation.

To investigate a slow API, I compare P50/P95/P99 latency, failure rate, and deployment markers. I pick out slow traces and separate application processing time from SQL, cache, or external dependency time.

I verify the suspected dependency using its own metrics and logs before I change capacity or code.

I also set up sampling, filter out sensitive data, configure trace propagation and retention, and run meaningful synthetic tests. After a rollback, a query fix, or another change, I repeat the same transaction and confirm that latency, errors, and dependency health have recovered.

### 8. How do you create and validate an Azure Monitor alert?

**Answer:**

I pick a resource and an actionable metric or log signal. Then I set a threshold or dynamic condition, an evaluation frequency and window, a severity, and an action group. Log alerts use a KQL query, tested against historical and known data.

The notification should include the environment, resource, observed value, owner, dashboard, and runbook.

I deploy the alert through Bicep, Terraform, or Policy. I trigger a safe test condition to confirm the notification fires and creates an incident, then confirm it resolves correctly. Alert processing rules handle planned maintenance windows.

I track noise and missed incidents, and tune the rule over time rather than leaving an untested portal configuration in place.
