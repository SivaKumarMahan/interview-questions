# AWS: Compute, Storage, and Serverless

> Deploying to EC2, ECR with Terraform, S3 and EBS storage, Lambda, API Gateway, CloudFront request flows, and SES email signing.

## Key Concepts

### Deploying a Java application to EC2

A production deployment should be automated and repeatable, not manual:

1. Build and test the application with Maven or Gradle, scan dependencies, and publish an immutable version — one that never changes after it's created — of the JAR to an approved artifact store such as S3 or CodeArtifact.
2. Provision the VPC, private EC2 instances or Auto Scaling group, IAM instance profile, security groups, load balancer, target group, logging, alarms, and deployment permissions through Terraform.
3. Bake the supported Java runtime and agents into a versioned AMI, or install them through controlled bootstrap/configuration management. Don't compile the application on the production instance itself.
4. Use CodeDeploy, Systems Manager, an image refresh, or another controlled mechanism to download the exact artifact and verify its checksum. Pull configuration and secrets at runtime from Parameter Store or Secrets Manager, using the instance's role.
5. Run the JAR as a dedicated non-root user under `systemd`, with resource limits, a restart policy, structured logs, and a health endpoint.
6. Register only healthy instances with the load balancer, run smoke and application checks, monitor errors/latency/JVM and host signals, and shift traffic over gradually.
7. If a health gate fails, roll back to the previous artifact or instance version — both are immutable, so rolling back means switching to a known-good version rather than trying to undo changes in place. Keep evidence of what happened, and fix the underlying cause before retrying.

For day-to-day administration, prefer **Systems Manager Session Manager**, with access controlled by IAM and no inbound management port open at all.

If SSH is genuinely required, restrict TCP 22 to an approved source or bastion, use the correct AMI user with a protected key, verify the host key, and connect with `ssh -i <key.pem> <user>@<address>`.

Private instances need a private path in — a VPN, Direct Connect, a bastion, or Session Manager. A private IP address is never reachable directly from the public internet.

### Terraform and Amazon ECR

Terraform does not log Docker into ECR. The AWS provider authenticates to AWS on its own — preferably through a short-lived assumed role — and manages resources like `aws_ecr_repository`, lifecycle policies, encryption, repository policies, and related VPC endpoints.

A CI runner authenticates Docker separately, usually with `aws ecr get-login-password`, and then pushes an image tag or digest. Once pushed, that tag or digest doesn't change — if you need a new image, you push a new tag or digest rather than overwriting the old one.

EC2, ECS, and EKS workloads get narrowly scoped pull permissions through their own runtime IAM role. Creating the repository, publishing an image, and pulling an image are three separate authorization paths — keep them that way.

## Interview Questions

<details><summary>Q1. [Basic] What is Amazon S3, and which storage classes would you choose?</summary>

**Answer:**

S3 is highly durable object storage. Applications store objects in buckets, identified by keys, and you control them with policies, encryption, and lifecycle rules.

For storage class, I pick Standard for data accessed often, Intelligent-Tiering when access patterns are unpredictable, Standard-IA or One Zone-IA for infrequently accessed or easily re-creatable data, and Glacier Instant Retrieval, Flexible Retrieval, or Deep Archive as you go further into cold archival storage.

I weigh retrieval time, minimum storage duration, and availability trade-offs, and I use lifecycle rules to move objects automatically instead of doing it by hand. Versioning, blocking public access, KMS encryption where required, bucket policies scoped to only what's needed, and regularly testing restores are the baseline controls I'd expect.

</details>

<details><summary>Q2. [Basic] EBS versus S3: when would you use each?</summary>

**Answer:**

EBS is low-latency block storage attached to a single EC2 instance in one Availability Zone. It's a good fit for filesystems, boot volumes, and databases that need block-level access. S3 is regional object storage you access through an API — good for backups, static assets, logs, data lakes, and build artifacts.

EBS isn't a shared object store, and S3 isn't a mounted filesystem by default. The choice comes down to how the data is accessed, latency needs, whether it needs to be shared, durability, lifecycle management, and how you'd recover it.

</details>

<details><summary>Q3. [Basic] What is AWS Lambda, and where is it a good fit?</summary>

**Answer:**

Lambda runs short-lived, event-driven code without you managing any servers. It's a good fit for API handlers, scheduled jobs, processing objects, queues, or events, and automation — as long as the work can be stateless and idempotent, and it fits within Lambda's execution limits.

I set memory, timeout, and concurrency deliberately, give the execution role only the permissions it needs, keep dependencies small, store secrets outside the function, and monitor errors, duration, throttles, retries, and the DLQ or destination.

For long-running work, workloads that hold many connections, or anything needing a specialized runtime, containers or another compute service are usually a better fit.

</details>

<details><summary>Q4. [Intermediate] How do you create an AWS Lambda function and publish its artifact safely?</summary>

**Answer:**

I define everything as code — the Lambda function, execution role, log group, event source, networking, environment variables, timeout, memory, concurrency, and alarms — using Terraform, CloudFormation/SAM, CDK, or a similar reviewed workflow.

The execution role only gets the specific API actions and resource ARNs it needs. The identity used to deploy is kept separate from the identity the function runs as.

CI installs locked dependencies, runs unit and security tests, builds a predictable ZIP or container image, generates an SBOM, scans it, calculates a digest, and stores it in a versioned artifact bucket or ECR.

Deployment then references that exact version or digest — it's immutable, meaning it never changes once it's created. It publishes a new Lambda version and shifts an alias over to it gradually, using weighted traffic.

Secrets come from a secrets manager at runtime, through the function's identity. They're never embedded in the ZIP file or left in plaintext environment variables.

I check that invocations work, look at logs and traces, and watch error rate, throttling, and duration. I also confirm dependency access, retries, the DLQ or destination, and that the function is idempotent — safe to run more than once without side effects. If something's wrong, rollback just moves the alias back to the last healthy version.

Keeping artifact history, recording provenance (where the artifact came from and how it was built), signing code where required, and reserving concurrency all help protect the release.

</details>

<details><summary>Q5. [Basic] What is API Gateway, and when would you use it?</summary>

**Answer:**

API Gateway is a managed front door for APIs. It can expose REST, HTTP, or WebSocket APIs and route them to Lambda, other AWS services, VPC backends, or plain HTTP endpoints. It handles authentication and authorization, throttling, request validation and transformation, custom domains, stages, logging, and metrics.

I reach for it when those managed features actually add value. For a simple internal service or a conventional web app, an ALB or a direct endpoint can be simpler.

I scope backend permissions down to only what's needed, add WAF or auth where required, set quotas and rate limits, and make sure timeouts and error behavior are explicit and observable.

</details>

<details><summary>Q6. [Intermediate] Explain a CloudFront + S3 + API Gateway + Lambda request flow.</summary>

**Answer:**

CloudFront is the public entry point. It serves cacheable static content from an S3 origin — normally locked down with Origin Access Control so the bucket itself isn't public — and forwards dynamic API requests on to API Gateway.

API Gateway authenticates and authorizes the request, validates it, then invokes Lambda using a resource policy or role that only allows that one invocation.

Lambda runs the business logic and reaches dependent services using its own role, scoped to only what it needs. The response travels back through API Gateway and CloudFront, subject to caching rules.

At each boundary I add TLS and a custom domain, WAF, logs and traces, cache invalidation or versioned assets, error handling, throttling, and alarms.

</details>

<details><summary>Q7. [Intermediate] What does email signing mean, and how would you implement it for an AWS-hosted email service?</summary>

**Answer:**

For email, signing usually means DKIM. The sending service signs selected headers and the body with a private key tied to the domain, and recipients verify that signature using a public key published in DNS.

With Amazon SES, I verify the domain, turn on Easy DKIM (or bring my own approved key), publish the CNAME/TXT records SES gives me, and wait for the domain to show as verified.

The private signing key stays managed and protected — applications never embed it directly.

I also set up SPF to say which infrastructure is allowed to send mail, and DMARC to define alignment, reporting, and what happens when a message fails. I roll DMARC out carefully: start in monitor-only mode (`p=none`), review the reports to make sure legitimate senders pass, then move to quarantine or reject once I'm confident.

A custom MAIL FROM domain, proper bounce and complaint handling, suppression lists, an SES identity with only the permissions it needs, TLS, sending quotas, and CloudWatch/SNS events all help protect the sending reputation.

I test the DKIM/SPF/DMARC headers against real recipients, plan for key rotation, confirm subdomain ownership, and check how things behave on failure. Signing proves the domain sent the message and that it wasn't altered — it doesn't encrypt the content. For that you'd need S/MIME or PGP.

</details>

<details><summary>Q8. [Intermediate] How would you configure AWS Lambda to automate operational tasks? <em>(asked in interview round)</em></summary>

**Answer:**

AWS Lambda runs code without servers, triggered by events or schedules. For operational automation, the usual pattern is: a trigger (EventBridge Scheduler for time-based jobs, an EventBridge rule for AWS events, S3 or SNS notifications), a small function with a least-privilege IAM role, logs in CloudWatch, and alerts on failures.

Example task: stop non-production EC2 instances tagged `AutoStop=true` every weekday at 8 PM.

**Flow:**

```text
EventBridge Scheduler (cron, with time zone)
        |
        | invokes (scheduler role: lambda:InvokeFunction)
        v
Lambda function (Python, execution role with least privilege)
        |
        | ec2:DescribeInstances, ec2:StopInstances (tag condition)
        v
EC2 instances tagged AutoStop=true
        |
        v
CloudWatch Logs + alarm on Errors --> SNS --> email / Slack
```

**Steps:**

**Step 1: Write the function**

```python
import os
import boto3

ec2 = boto3.client("ec2")
TAG_KEY = os.environ.get("TAG_KEY", "AutoStop")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def lambda_handler(event, context):
    paginator = ec2.get_paginator("describe_instances")
    ids = []
    for page in paginator.paginate(
        Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": ["true"]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    ):
        for reservation in page["Reservations"]:
            ids.extend(i["InstanceId"] for i in reservation["Instances"])

    if not ids:
        print("No running instances to stop")
        return {"stopped": []}

    if DRY_RUN:
        print(f"DRY_RUN: would stop {ids}")
        return {"would_stop": ids}

    ec2.stop_instances(InstanceIds=ids)
    print(f"Stopped {ids}")
    return {"stopped": ids}
```

**Step 2: Create a least-privilege execution role**

Attach `AWSLambdaBasicExecutionRole` for CloudWatch Logs, plus:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:DescribeInstances",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ec2:StopInstances",
      "Resource": "arn:aws:ec2:*:123456789012:instance/*",
      "Condition": {
        "StringEquals": { "aws:ResourceTag/AutoStop": "true" }
      }
    }
  ]
}
```

`DescribeInstances` does not support resource-level permissions, so it needs `"*"`; the stop action is limited by the tag.

**Step 3: Configure the function**

Runtime Python 3.12 or later, timeout around 60 seconds, memory 128 to 256 MB, environment variables `TAG_KEY` and `DRY_RUN`. Keep secrets in Secrets Manager or Parameter Store, not in environment variables.

**Step 4: Schedule it with EventBridge Scheduler**

```bash
aws scheduler create-schedule \
  --name stop-nonprod-ec2 \
  --schedule-expression "cron(0 20 ? * MON-FRI *)" \
  --schedule-expression-timezone "Asia/Kolkata" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{"Arn": "arn:aws:lambda:ap-south-1:123456789012:function:stop-nonprod-ec2",
             "RoleArn": "arn:aws:iam::123456789012:role/scheduler-invoke-lambda"}'
```

The scheduler role only needs `lambda:InvokeFunction` on this function.

**Step 5: Monitor and handle failures**

- CloudWatch alarm on the function's `Errors` and `Throttles` metrics, sent to SNS.
- Configure retries and a dead-letter queue on the schedule target for failed invocations.
- Make the function idempotent, because it can be retried.

**Step 6: Deploy as code**

Define the function, roles, schedule and alarms in Terraform, AWS SAM or CDK and deploy through CI/CD, not through the console.

**Important points:**

- EventBridge Scheduler is preferred over older EventBridge scheduled rules for new jobs because it supports time zones, one-time schedules, retries and a DLQ.
- Lambda has a 15-minute maximum runtime; for longer jobs use Step Functions, ECS tasks or Systems Manager Automation.
- Start with a `DRY_RUN` flag in non-production and test with sample events.
- For event-driven automation (for example, reacting to a security group change), use an EventBridge rule on CloudTrail events instead of a schedule.

See also: [aws/02](../aws/02-compute-storage-and-serverless.md).

**Interview-ready answer:**

> "I write a small, idempotent function, usually in Python with `boto3`, that performs one operational task, for example stopping tagged non-production EC2 instances. I give it an execution role with least privilege, such as stop permission limited by a tag condition, plus CloudWatch Logs access. For time-based jobs I trigger it with EventBridge Scheduler using a cron expression and a time zone, and for event-driven tasks I use an EventBridge rule. I set a sensible timeout, keep secrets in Secrets Manager or Parameter Store, and add a dry-run flag for testing. I monitor errors with CloudWatch alarms to SNS and configure retries with a dead-letter queue. Everything is deployed with Terraform through the pipeline."

</details>

<details><summary>Q9. [Intermediate] Where have you used AWS Lambda in your projects, and what problem did it solve? <em>(asked in interview round)</em></summary>

**Answer:**

This is an experience question, so answer with a real example using the STAR format (situation, task, action, result). If most of your work is on Azure, say so and describe the equivalent work with Azure Functions, then explain how you would do it with Lambda. Do not claim AWS projects you did not do.

**Structure:**

```text
Situation : what was the manual or risky process?
Task      : what had to be automated?
Action    : trigger + Lambda + permissions + monitoring
Result    : time, cost or risk reduced (use real numbers or describe qualitatively)
```

**Common real-world use cases:**

| Use case | Trigger | What Lambda does |
| --- | --- | --- |
| Cost saving | EventBridge Scheduler | Stop or start non-production EC2 or RDS outside office hours |
| Snapshot hygiene | Daily schedule | Delete EBS snapshots or AMIs older than the retention period |
| Alert enrichment | CloudWatch alarm to SNS | Format the alarm and post it to Slack or Teams with context |
| File processing | S3 `ObjectCreated` event | Validate, transform or move uploaded files |
| Compliance | EventBridge rule on CloudTrail | Detect a public S3 bucket or open security group and notify or fix it |
| Certificate or key expiry | Daily schedule | Check expiry dates and alert before they expire |

**Example answer (adapt to your real project):**

> "In one project, development and QA EC2 instances were left running at night and on weekends, which was increasing the monthly bill. I wrote a Python Lambda function that stops instances tagged `AutoStop=true` at 8 PM on weekdays, and a second schedule starts them in the morning, both triggered by EventBridge Scheduler. The execution role only allowed stopping and starting instances with that tag. I added CloudWatch alarms on function errors to SNS and deployed everything with Terraform. As a result, non-production compute cost dropped by around `<X>%` and nobody had to remember to stop machines manually."

If your experience is on Azure:

> "Most of my serverless work has been with Azure Functions, which is the Azure equivalent of Lambda. I used a timer-triggered function to `<task>`, with a managed identity limited to the resources it needed. The same design maps directly to AWS: EventBridge Scheduler as the trigger, Lambda for the code, and an IAM role with least privilege."

**Important points:**

- Pick one example and go deep: trigger, code language, IAM, error handling, deployment and the outcome.
- Be ready for follow-ups: timeouts, cold starts, retries, idempotency, how you tested it, and how you deployed it.
- Mention limits you designed around, such as the 15-minute timeout or concurrency.

See also: [aws/02](../aws/02-compute-storage-and-serverless.md).

**Interview-ready answer:**

> "I used Lambda mainly for operational automation. One example is stopping non-production EC2 instances outside office hours: EventBridge Scheduler triggers a Python function that stops instances tagged for auto-stop, using an IAM role restricted by that tag. I also used Lambda to forward CloudWatch alarms from SNS to our chat channel with useful context, which made alerts easier to act on. Both were deployed with Terraform and monitored with CloudWatch alarms on errors. The main benefit was reducing manual work and non-production cost, and it removed the risk of someone forgetting to shut down resources."

</details>

<details><summary>Q10. [Basic] What is Amazon Redshift? <em>(asked in interview round)</em></summary>

**Answer:**

Amazon Redshift is AWS's fully managed, petabyte-scale **data warehouse** for analytics (`OLAP`). It stores data in **columnar** format and uses **massively parallel processing (MPP)**, so complex SQL queries over very large datasets run fast. It is used for reporting, BI dashboards and analytics, not for transactional application workloads (use RDS or Aurora for those).

**Key features:**

- **Columnar storage and compression:** reads only the columns a query needs.
- **MPP architecture:** a leader node plans the query; compute nodes process slices of data in parallel.
- **Deployment options:**
  - **Provisioned clusters:** you choose node type and count (RA3 nodes separate compute from managed storage).
  - **Redshift Serverless:** no cluster to manage; capacity scales automatically and you pay for compute used (`RPU`-hours).
- **Redshift Spectrum:** query data directly in S3 (Parquet, ORC, CSV) without loading it.
- Standard SQL, works with BI tools (`QuickSight`, Power BI, `Tableau`).
- Concurrency scaling, materialized views, data sharing, encryption with KMS, VPC isolation.

**Flow:**

```text
Sources (RDS, apps, logs, S3)
        |
        | ETL/ELT (Glue, COPY, zero-ETL, Kinesis)
        v
Amazon Redshift (columnar, MPP)  <---- Spectrum ----> S3 data lake
        |
        v
BI tools / dashboards / analysts (SQL)
```

**Example:**

```sql
COPY sales
FROM 's3://my-bucket/sales/2026/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftS3Read'
FORMAT AS PARQUET;

SELECT region, SUM(amount) AS revenue
FROM sales
WHERE sale_date >= '2026-01-01'
GROUP BY region
ORDER BY revenue DESC;
```

**Important points:**

- Redshift is `OLAP` (analytics), RDS/Aurora is `OLTP` (transactions).
- Use `COPY` from S3 for bulk loads; avoid many single-row inserts.
- Choose distribution and sort keys (or let automatic table optimization handle them) for performance.
- Serverless suits variable or unpredictable workloads; provisioned suits steady, predictable workloads.

**Interview-ready answer:**

> "Amazon Redshift is a fully managed, petabyte-scale data warehouse on AWS for analytics. It stores data in columnar format and uses massively parallel processing, so large analytical SQL queries run quickly. I can run it as a provisioned cluster or as Redshift Serverless, where capacity scales automatically and I pay for usage. With Redshift Spectrum I can query data directly in S3 without loading it. Data is usually loaded from S3 using the `COPY` command or through Glue or zero-ETL integrations, and BI tools like `QuickSight` or Power BI connect to it. I would use it for reporting and analytics, not as the transactional database of an application."

</details>

<details><summary>Q11. [Basic] What is AWS Snowball? <em>(asked in interview round)</em></summary>

**Answer:**

AWS Snowball is a **physical data transfer device** that AWS ships to your site. You copy large volumes of data onto it locally and ship it back, and AWS imports the data into Amazon S3. It is used when moving tens or hundreds of terabytes over the network would take too long or cost too much, or for sites with limited connectivity.

**Key points:**

- **Snowball Edge** devices come in storage-optimized and compute-optimized options; they can also run EC2 instances and Lambda functions locally for edge computing.
- Data is encrypted with keys managed in AWS KMS, and the device is tamper-resistant; AWS erases the device after import.
- Jobs are created in the AWS Snow Family console; the data is copied using the Snowball client or the S3-compatible interface.
- **Availability has changed:** AWS has restricted new Snowball orders for new customers and points customers to alternatives. Check current availability in the AWS documentation before recommending it.

**Alternatives:**

| Need | Service |
|------|---------|
| Online transfer over the network | AWS DataSync |
| Physical high-speed upload at an AWS location | AWS Data Transfer Terminal |
| Dedicated private network link | AWS Direct Connect |
| Hybrid file access | AWS Storage Gateway |

**Flow:**

```text
Create job in console -> AWS ships device -> connect to local network
        |
        v
Copy data (encrypted) -> ship back -> AWS imports into S3 -> device wiped
```

**Example (copy data to the device):**

```bash
# Using the S3-compatible endpoint on a Snowball Edge device
aws s3 cp /data/archive s3://my-import-bucket/archive \
  --recursive --endpoint-url https://192.168.1.50:8443 --profile snowball
```

**Important points:**

- Rule of thumb: if the network transfer would take more than about a week, consider offline transfer.
- It is for bulk one-time or periodic migration, not continuous sync.
- Today, DataSync is often the first choice for online migration.

**Interview-ready answer:**

> "AWS Snowball is a physical, rugged and encrypted device that AWS ships to my data centre. I copy large amounts of data onto it locally, ship it back, and AWS imports the data into S3. It is useful when moving tens or hundreds of terabytes over the network would take weeks or the site has poor connectivity. Snowball Edge devices can also run compute locally for edge workloads. AWS has restricted new Snowball orders, so I would check current availability and also consider alternatives like AWS DataSync for online transfer or AWS Data Transfer Terminal for physical upload at an AWS location."

</details>

<details><summary>Q12. [Basic] What are SNS and SQS? <em>(asked in interview round)</em></summary>

**Answer:**

Both are AWS managed messaging services used to decouple applications.

- **Amazon SNS (Simple Notification Service)** is **pub/sub (push)**: a publisher sends a message to a topic, and SNS pushes a copy to every subscriber (SQS queues, Lambda, HTTP/S endpoints, email, SMS).
- **Amazon SQS (Simple Queue Service)** is a **message queue (pull)**: producers send messages to a queue, and consumers poll and process them, then delete them. Each message is processed by one consumer.

**Comparison:**

| | SNS | SQS |
|--|-----|-----|
| Model | Pub/sub, push | Queue, pull (polling) |
| Delivery | One message to many subscribers | One message to one consumer |
| Persistence | No storage; delivers immediately (retries) | Stores messages up to 14 days (default 4 days) |
| Types | Standard, FIFO topics | Standard, FIFO queues |
| Use case | Fan-out notifications, alerts | Buffering, background jobs, load levelling |

**Fan-out pattern:**

```text
Order service
     |
     v
SNS topic "order-created"
     |------------------|-------------------|
     v                  v                   v
SQS: billing-queue  SQS: shipping-queue  Lambda: send email
     |                  |
Billing workers     Shipping workers
```

**Example:**

```bash
aws sns publish --topic-arn arn:aws:sns:eu-west-1:123456789012:order-created \
  --message '{"orderId": 101}'

aws sqs receive-message --queue-url https://sqs.eu-west-1.amazonaws.com/123456789012/billing-queue \
  --wait-time-seconds 20          # long polling
aws sqs delete-message --queue-url <queue-url> --receipt-handle <handle>
```

**Important points:**

- SNS + SQS fan-out gives both broadcast and durable, independent processing per consumer.
- Configure a **dead-letter queue** for messages that fail repeatedly.
- **Visibility timeout** hides a message while one consumer processes it; set it longer than processing time.
- Standard queues are at-least-once with best-effort ordering, so consumers should be idempotent; use FIFO for strict ordering and deduplication.

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md).

**Interview-ready answer:**

> "SNS and SQS are AWS managed messaging services for decoupling applications. SNS is publish/subscribe: a publisher sends a message to a topic and SNS pushes it to all subscribers, such as SQS queues, Lambda functions, HTTP endpoints or email. SQS is a queue: messages are stored until a consumer polls, processes and deletes them, so it is good for buffering and background jobs. A common pattern is fan-out, where one SNS topic sends each event to several SQS queues so each service processes it independently. I always add a dead-letter queue, tune the visibility timeout, and make consumers idempotent because standard queues can deliver a message more than once."

</details>

<details><summary>Q13. [Intermediate] 10,000 files land in S3 every day and the cost keeps rising. What is your action plan? <em>(asked in interview round)</em></summary>

**Answer:**

10,000 files a day is about 3.65 million objects a year. Cost rises steadily because **nothing is ever deleted or moved to cheaper storage**, and often because of hidden items like old versions, incomplete multipart uploads and request charges. My plan is: **measure, then apply lifecycle rules, then reduce request and object overhead.**

**Step 1: Find where the cost comes from:**

- **Cost Explorer**: filter Service = S3 and group by **Usage type** to split storage (`TimedStorage-ByteHrs`), requests (`Requests-Tier1` for PUT/LIST, `Requests-Tier2` for GET), data transfer, and retrieval.
- **S3 Storage Lens**: bytes and object count per bucket/prefix, non-current version bytes, incomplete multipart upload bytes, average object size. Advanced metrics add activity data.
- **S3 Inventory** + Athena for a per-prefix and per-age breakdown.
- Check if **versioning** is on, if **replication** doubles storage, and who reads the data (lots of GETs or LISTs from an application or crawler).

**Step 2: Lifecycle rules:**

```json
{
  "Rules": [
    {
      "ID": "daily-files",
      "Status": "Enabled",
      "Filter": { "Prefix": "incoming/" },
      "Transitions": [
        { "Days": 30, "StorageClass": "STANDARD_IA" },
        { "Days": 90, "StorageClass": "GLACIER_IR" },
        { "Days": 180, "StorageClass": "DEEP_ARCHIVE" }
      ],
      "Expiration": { "Days": 730 },
      "NoncurrentVersionExpiration": { "NoncurrentDays": 30, "NewerNoncurrentVersions": 3 },
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }
  ]
}
```

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-ingest-bucket --lifecycle-configuration file://lifecycle.json
```

- **Expiration**: delete data after the retention period agreed with the business or compliance team.
- **Non-current versions**: on versioned buckets, old versions are billed in full until expired.
- **Incomplete multipart uploads**: invisible in normal listings but billed.
- If access patterns are unknown, use **S3 Intelligent-Tiering** instead of fixed transitions.

**Step 3: Watch the small-object trap:**

| Storage class | Minimum billable size | Minimum storage duration |
| --- | --- | --- |
| Standard | None | None |
| Standard-IA / One Zone-IA | 128 KB | 30 days |
| Glacier Instant Retrieval | 128 KB | 90 days |
| Glacier Flexible Retrieval | 40 KB metadata overhead per object | 90 days |
| Glacier Deep Archive | 40 KB metadata overhead per object | 180 days |
| Intelligent-Tiering | Objects under 128 KB are not auto-tiered (stay in Frequent Access) | None; monthly per-object monitoring fee |

- Lifecycle **transition requests are charged per object**; moving millions of tiny files can cost more than it saves. By default, lifecycle no longer transitions objects smaller than 128 KB.
- Deleting IA/Glacier objects before the minimum duration is billed for the remaining days.

**Step 4: Reduce object count and request cost:**

- **Aggregate** small files (hourly/daily batches, Parquet, compressed `tar`/`gz`) before archiving; fewer, larger objects are cheaper to store, transition and query.
- **Compress** text/JSON/CSV data (often 70–90% smaller).
- Avoid frequent full `LIST` scans; use S3 Inventory or event notifications instead.
- Put CloudFront in front of frequently downloaded content; use a **gateway endpoint** so EC2 access doesn't go through NAT.

**Step 5: Prevent regression:**

- Tag buckets by owner/cost center and enable cost allocation tags.
- AWS Budgets and Cost Anomaly Detection on S3.
- Lifecycle policy as part of the Terraform bucket module, so every new bucket has one.

```text
Measure (Cost Explorer by usage type, Storage Lens, Inventory)
   -> Lifecycle: transition + expiration + non-current + abort MPU
   -> Check small objects / minimum duration before transitioning
   -> Aggregate + compress, reduce LIST/GET, endpoints/CloudFront
   -> Budgets + anomaly detection + IaC defaults
```

See also: [AWS compute, storage and serverless (S3 storage classes)](../aws/02-compute-storage-and-serverless.md), [Monitoring cost and FinOps](../monitoring-tools/10-monitoring-cost-finops.md).

**Interview-ready answer:**

> "First I find out what part of S3 is growing, by grouping S3 costs by usage type in Cost Explorer and looking at Storage Lens for each bucket and prefix, including non-current versions and incomplete multipart uploads. Usually the cause is that files are never deleted or moved, so I add lifecycle rules: transition to Standard-IA or Glacier after the agreed access period, expire data after the retention period, expire old versions and abort incomplete multipart uploads after seven days. If access patterns are unpredictable, I use Intelligent-Tiering. I check object sizes first, because IA and Glacier have minimum size, minimum duration and per-object transition charges, so for tiny files I aggregate and compress them before archiving. Finally I add budgets, anomaly alerts and a default lifecycle policy in our Terraform bucket module so the growth doesn't come back."

</details>

<details><summary>Q14. [Intermediate] Which RDS engine did you work with, and what are your daily database tasks? <em>(asked in interview round)</em></summary>

**Answer:**

> Note: this is a template. Replace the engine, versions and examples with what you actually did. Interviewers usually follow up on details, so only mention tasks you can explain.

As a DevOps engineer I am not the application DBA, but I own the **platform** side of RDS: provisioning with Terraform, backups, monitoring, upgrades, access and performance triage together with developers. Example below is for RDS for PostgreSQL (MySQL equivalents in brackets).

**Daily and weekly tasks:**

| Area | What I do |
| --- | --- |
| Provisioning | Create and change instances through Terraform: instance class, storage type (`gp3`), Multi-AZ, subnet groups, security groups, KMS encryption |
| Backups | Verify automated backups and retention (for example 7 to 35 days), take manual snapshots before releases or upgrades, copy snapshots to a DR region, test restores |
| Parameter groups | Custom DB parameter groups, for example `log_min_duration_statement`, `max_connections`, `work_mem` (MySQL: `slow_query_log`, `long_query_time`); know which need a reboot |
| Monitoring | CloudWatch metrics: `CPUUtilization`, `FreeableMemory`, `FreeStorageSpace`, `DatabaseConnections`, `ReadLatency`, `WriteLatency`, `ReplicaLag`; Performance Insights / Database Insights for top SQL and wait events; Enhanced Monitoring for OS metrics |
| Alerts | CloudWatch alarms to SNS or Slack for storage, CPU, connections and replica lag |
| Slow queries | Publish PostgreSQL logs (MySQL slow query log) to CloudWatch Logs and share the top queries with developers, suggest indexes |
| Upgrades | Apply minor version upgrades in the maintenance window (or auto minor version upgrade), plan major upgrades with a snapshot and testing in staging (or Blue/Green Deployments for RDS) |
| Access | Create application users with least privilege, manage the master password in Secrets Manager with rotation, IAM database authentication for engineers |
| Storage | Storage autoscaling with a maximum threshold; watch `FreeStorageSpace` |
| Security | Encryption at rest with KMS, TLS enforced (`rds.force_ssl=1`), no public access, audit logs if required |
| Cost | Right-size instance classes, use Reserved Instances for steady production, stop non-production instances out of hours |

**Example: common commands:**

```bash
# Manual snapshot before a release
aws rds create-db-snapshot --db-instance-identifier orders-prod \
  --db-snapshot-identifier orders-prod-pre-release-2026-10-14

# Check pending maintenance
aws rds describe-pending-maintenance-actions

# Download recent PostgreSQL log
aws rds download-db-log-file-portion --db-instance-identifier orders-prod \
  --log-file-name error/postgresql.log.2026-10-14-10 --output text | tail
```

```sql
-- Top queries by total time (needs pg_stat_statements)
SELECT query, calls, round(total_exec_time) AS total_ms, round(mean_exec_time) AS mean_ms
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

See also: [database monitoring](../monitoring-tools/07-database-monitoring.md) and [AWS monitoring and troubleshooting](../aws/04-monitoring-and-troubleshooting.md).

**Interview-ready answer:**

> "I mainly worked with RDS for PostgreSQL, and also MySQL on one project. My role is the platform side: I provision instances with Terraform, including Multi-AZ, encryption, parameter groups and security groups. Day to day I watch CloudWatch alarms and Performance Insights for CPU, connections, storage and slow queries, and I share the top SQL with developers when latency rises. I make sure automated backups and retention are correct, take manual snapshots before releases and upgrades, and copy snapshots to our DR region. I apply minor version upgrades in maintenance windows, manage users and secrets in Secrets Manager, and keep storage autoscaling enabled with a maximum limit."

</details>

<details><summary>Q15. [Basic] How is S3 used in your project: logs, artifacts, backups and Terraform state? <em>(asked in interview round)</em></summary>

**Answer:**

S3 is our central storage for anything that is not a live database: build artifacts, application and access logs, backups and exports, and the Terraform remote state. Every bucket follows the same baseline: Block Public Access on, encryption, versioning where data must be recoverable, lifecycle rules for cost, and least-privilege bucket policies.

**Typical buckets:**

```text
company-tfstate-prod        Terraform state (versioning, SSE-KMS, use_lockfile)
company-artifacts           Build outputs, Helm charts, Lambda zips (versioning)
company-logs                ALB / CloudFront / VPC Flow Logs / CloudTrail (lifecycle to Glacier, Object Lock if needed)
company-backups             DB dumps, Velero EKS backups (versioning, cross-region replication)
company-static-site         Frontend assets behind CloudFront (Origin Access Control, not public)
```

**Terraform state backend:**

Since Terraform 1.10 the S3 backend supports **native state locking** with `use_lockfile = true` (generally available from 1.11). Terraform writes a `.tflock` object next to the state using S3 conditional writes, so a DynamoDB table is no longer needed; the `dynamodb_table` argument is deprecated.

```hcl
terraform {
  required_version = ">= 1.11"

  backend "s3" {
    bucket       = "company-tfstate-prod"
    key          = "eks/prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    kms_key_id   = "alias/terraform-state"
    use_lockfile = true
  }
}
```

The state bucket itself:

```hcl
resource "aws_s3_bucket" "state" {
  bucket = "company-tfstate-prod"
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.state.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**Lifecycle example for logs:**

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "log-retention"
    status = "Enabled"
    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration {
      days = 365
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
```

**Important points:**

- Versioning on the state bucket lets me recover a previous state file after corruption or a bad apply.
- The CI role needs `s3:GetObject`, `s3:PutObject` and `s3:DeleteObject` on the state key and its `.tflock` object, plus `s3:ListBucket` on the bucket.
- New buckets have Block Public Access on and ACLs disabled (Bucket owner enforced) by default; keep it that way and serve public content through CloudFront with Origin Access Control.
- Use S3 gateway VPC endpoints so EKS and EC2 reach S3 without NAT gateway charges.
- Object Lock (WORM) for compliance logs and backups that must not be deleted.

See also: [Terraform state and backends](../terraform/03-state-and-backends.md) and [AWS compute, storage and serverless](../aws/02-compute-storage-and-serverless.md).

**Interview-ready answer:**

> "In my project S3 holds four kinds of data: Terraform state, build artifacts, logs, and backups. The Terraform state lives in a dedicated bucket with versioning, KMS encryption and Block Public Access, and since Terraform 1.10 we use the S3 backend with `use_lockfile = true`, so locking uses a lock file in S3 instead of a DynamoDB table. Artifacts such as Helm charts and Lambda packages are versioned, while ALB, CloudTrail and VPC Flow Logs go to a log bucket with lifecycle rules that move data to Infrequent Access and Glacier and expire it after a year. Database dumps and Velero backups of EKS go to a backup bucket with cross-region replication. Access is controlled with IAM roles and bucket policies, and traffic from the VPC uses an S3 gateway endpoint."

</details>
