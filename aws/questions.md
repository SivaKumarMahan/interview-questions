## 1. A server is healthy and has network connectivity, but logs are not uploading to an S3 bucket. What do you investigate?

**Answer:**

I break the problem into pieces: is the log agent reading files correctly, is it authenticated, does it have permission on the bucket, and is the upload itself actually succeeding?

First I check the log agent. Is it reading the right path? Does it have permission on the files? Is it stuck behind a lock or a full spool disk? Are there any recent errors in its own logs?

Next I test the AWS identity directly. I run `aws sts get-caller-identity`, then try a small test upload to the exact bucket and prefix, without printing the credentials.

Common causes I look for: an expired or wrong credential, the wrong instance profile or region, a missing `s3:PutObject` permission, an explicit deny somewhere (bucket policy, SCP, or permissions boundary), a required object tag or ACL condition, a KMS key policy that's missing `kms:Encrypt` or `kms:GenerateDataKey`, Object Lock, a wrong prefix, clock skew, a failed multipart upload, or a storage-class/lifecycle rule getting in the way.

CloudTrail data events and S3's own server-side logs show whether AWS actually received the request and denied it, or never saw it at all.

Once I find the real cause, I fix that one thing — the policy, the key permission, the agent config, the disk space, or file ownership — and then confirm a new object actually lands, with the right encryption and metadata, and that downstream systems pick it up.

Going forward, I use an instance role that only has the permissions it needs, watch agent health and backlog metrics, set limits on any dead-letter or spool queue, and alert if uploads get too old or start failing.

## 2. How do you create an AWS Lambda function and publish its artifact safely?

**Answer:**

I define everything as code — the Lambda function, execution role, log group, event source, networking, environment variables, timeout, memory, concurrency, and alarms — using Terraform, CloudFormation/SAM, CDK, or a similar reviewed workflow.

The execution role only gets the specific API actions and resource ARNs it needs. The identity used to deploy is kept separate from the identity the function runs as.

CI installs locked dependencies, runs unit and security tests, builds a predictable ZIP or container image, generates an SBOM, scans it, calculates a digest, and stores it in a versioned artifact bucket or ECR.

Deployment then references that exact version or digest — it's immutable, meaning it never changes once it's created. It publishes a new Lambda version and shifts an alias over to it gradually, using weighted traffic.

Secrets come from a secrets manager at runtime, through the function's identity. They're never embedded in the ZIP file or left in plaintext environment variables.

I check that invocations work, look at logs and traces, and watch error rate, throttling, and duration. I also confirm dependency access, retries, the DLQ or destination, and that the function is idempotent — safe to run more than once without side effects. If something's wrong, rollback just moves the alias back to the last healthy version.

Keeping artifact history, recording provenance (where the artifact came from and how it was built), signing code where required, and reserving concurrency all help protect the release.

## 3. What do you use AWS CloudWatch and CloudTrail for in production?

**Answer:**

CloudWatch is where operational monitoring data lives: AWS service metrics, custom metrics, logs, dashboards, alarms, traces, synthetic checks, and event-driven actions.

I use it to watch EC2 and container resource usage, application signals, Lambda errors/duration/throttling, load balancer status and latency, and queue depth and age, and to run log queries. I build SLO dashboards and route alarms through SNS or incident tooling so they actually get acted on.

CloudTrail records AWS API activity — who or which role called an action, when, from where, against which resource, and whether it succeeded.

I centralize the organization's trails in a protected security account, turn on the right management and data events, encrypt and retain the logs, and alert on high-risk actions: policy changes, a trail getting disabled, public exposure, key changes, or an unusual role assumption.

During an incident I compare what CloudWatch shows against deployment or config changes and CloudTrail's API evidence. Neither tool replaces application tracing or full OS-level metrics. CloudTrail is an audit trail, not a real-time performance monitor.

## 4. An EC2 instance reaches 100% CPU. How do you investigate and recover it?

**Answer:**

First I check how long this has been happening, whether customers are actually affected, the instance status checks, the current load, any recent deploys, autoscaling activity, and — if it's a burstable (T-series) instance — whether it has run out of CPU credits.

Then I connect through SSM or SSH and run `uptime`, `top`, `ps`, and `pidstat`, along with application metrics, to figure out what's actually using the CPU: user time, system time, steal time, I/O wait, a runaway process, garbage collection, a traffic spike, a cron job, an agent, or possibly a compromise.

To stabilize things, I shift traffic away, scale out, rate-limit, stop a runaway process I've confirmed is safe to stop, or roll back a bad release. I avoid rebooting first unless the host is truly unrecoverable — a reboot destroys the evidence I need and often just moves the problem elsewhere.

If there's any sign of compromise, I isolate the host and start incident response instead of just restarting it.

The real fix might be profiling the application, improving a query or cache, setting resource limits, fixing a scheduled job, autoscaling on a better signal, choosing a different instance type, or general capacity planning.

Afterward I confirm latency, errors, and CPU actually recover under real load, and I add alerts for saturation — how close the resource is to its limit — plus credit exhaustion, queueing, and scaling failures.

## 5. How do EC2, EKS, ECS, and databases fit together, and how do you interact with an ECS service?

**Answer:**

EC2 gives you virtual machines. Those machines can run your own applications directly, act as ECS container instances, or serve as EKS worker nodes. ECS is AWS's own container orchestrator. EKS gives you a managed Kubernetes control plane instead.

Databases like RDS usually live in private subnets. They only accept traffic from the specific application security group, on the database port. Load balancers expose the services you actually want reachable. IAM roles for tasks, or for service accounts in EKS, give each workload its own identity.

For ECS, I use the AWS CLI or API — there's no concept of "logging into ECS":

```bash
aws ecs list-clusters
aws ecs list-services --cluster production
aws ecs describe-services --cluster production --services payments
aws ecs execute-command --cluster production --task <task-id> \
  --container payments --interactive --command '/bin/sh'
```

ECS Exec needs SSM integration, IAM authorization, and logging set up, and it only works against a running, supported task. I'd rather rely on logs and metrics than interactive access, and I never expose a database directly to the public internet.

I check DNS, security group references, TLS, credentials, connection pools, health checks, and how things fail across AZs.

## 6. Design a secure, scalable, highly available AWS architecture for a global SaaS product and explain regional failover.

**Answer:**

I start by understanding the tenancy model, data classification and residency requirements, expected traffic, SLOs, recovery targets (RTO/RPO), consistency needs, and compliance rules. Route 53 or Global Accelerator sends users to the nearest region's CloudFront, WAF, and load balancer or API endpoints.

Each region gets multiple AZs, private application subnets, autoscaled compute on ECS or EKS, controlled outbound traffic, its own workload identity, KMS encryption, centralized logs and security findings, and no databases exposed publicly.

Tenant isolation isn't just network boundaries — it's enforced in identity, authorization, data keys or partitions, quotas, and audit logging too.

How you handle data decides how failover works. DynamoDB Global Tables, or another datastore built for multiple regions, can give you active-active behavior. Relational databases usually use cross-region replicas with a single write region instead.

Object storage gets replicated wherever the recovery point objective requires it. Infrastructure and policy come from versioned infrastructure-as-code so they're reproducible. Secrets and certificates exist independently in each region, and dependencies have enough capacity in each region too.

During an actual outage: declare the incident, stop any risky deployments, confirm the failure and check replication lag, promote or fence the data according to the runbook, scale up the recovery region, verify transactions are working internally, then shift traffic over gradually using weighted routing. Avoiding a split-brain situation matters more than failing over quickly.

Afterward I watch errors, latency, data correctness, queue depth, and business metrics. I keep clear rollback criteria, and before failing back I reconcile — make actual state match desired state — the data. Regular game days are how you prove your real RTO and RPO, not just the numbers on paper.

## 7. What does email signing mean, and how would you implement it for an AWS-hosted email service?

**Answer:**

For email, signing usually means DKIM. The sending service signs selected headers and the body with a private key tied to the domain, and recipients verify that signature using a public key published in DNS.

With Amazon SES, I verify the domain, turn on Easy DKIM (or bring my own approved key), publish the CNAME/TXT records SES gives me, and wait for the domain to show as verified.

The private signing key stays managed and protected — applications never embed it directly.

I also set up SPF to say which infrastructure is allowed to send mail, and DMARC to define alignment, reporting, and what happens when a message fails. I roll DMARC out carefully: start in monitor-only mode (`p=none`), review the reports to make sure legitimate senders pass, then move to quarantine or reject once I'm confident.

A custom MAIL FROM domain, proper bounce and complaint handling, suppression lists, an SES identity with only the permissions it needs, TLS, sending quotas, and CloudWatch/SNS events all help protect the sending reputation.

I test the DKIM/SPF/DMARC headers against real recipients, plan for key rotation, confirm subdomain ownership, and check how things behave on failure. Signing proves the domain sent the message and that it wasn't altered — it doesn't encrypt the content. For that you'd need S/MIME or PGP.

## 8. What is Amazon S3, and which storage classes would you choose?

**Answer:**

S3 is highly durable object storage. Applications store objects in buckets, identified by keys, and you control them with policies, encryption, and lifecycle rules.

For storage class, I pick Standard for data accessed often, Intelligent-Tiering when access patterns are unpredictable, Standard-IA or One Zone-IA for infrequently accessed or easily re-creatable data, and Glacier Instant Retrieval, Flexible Retrieval, or Deep Archive as you go further into cold archival storage.

I weigh retrieval time, minimum storage duration, and availability trade-offs, and I use lifecycle rules to move objects automatically instead of doing it by hand. Versioning, blocking public access, KMS encryption where required, bucket policies scoped to only what's needed, and regularly testing restores are the baseline controls I'd expect.

## 9. What is the difference between a security group and a network ACL?

**Answer:**

A security group is a stateful, allow-only firewall attached to a resource's network interface. Return traffic is automatically allowed, and rules can reference another security group.

A network ACL is a stateless boundary at the subnet level. It has ordered allow and deny rules, and you have to explicitly allow both inbound and outbound return traffic.

I use security groups for the normal application traffic path, scoped to only what's needed, and NACLs for coarse subnet-level guardrails or when I need an explicit deny. When troubleshooting, I check route tables, both directions of traffic, ephemeral ports, and the actual network interface or subnet involved — not just open everything up with `0.0.0.0/0`.

## 10. IAM role versus IAM user: when do you use each?

**Answer:**

An IAM role hands out temporary credentials to a workload, or to a federated human identity, and it can be assumed with narrowly scoped permissions. An IAM user is a long-lived AWS identity — it's really a legacy option now, only for the rare case where federation or roles genuinely don't work.

I use roles for EC2, Lambda, ECS/EKS workloads, CI, and human access through SSO. I require MFA and give every role only the permissions it needs. I avoid static access keys, rotate any I can't avoid, and review CloudTrail logs along with permission boundaries and SCPs.

## 11. How do you back up and restore an EC2 workload?

**Answer:**

I make sure the application can be recovered — I don't treat a single running instance as the only copy of anything. Infrastructure gets rebuilt from infrastructure-as-code. Data gets backed up at the database or application level. EBS volumes get scheduled, encrypted snapshots, with retention rules and cross-account or cross-region copies when needed.

An AMI can preserve a tested machine image, but it's not a substitute for backing up application data properly. A restore runbook launches or rebuilds the instance, restores the data, checks security settings, DNS, and secrets, and confirms the application actually works end to end.

I test restores regularly against the recovery time and recovery point targets we've agreed on.

## 12. EBS versus S3: when would you use each?

**Answer:**

EBS is low-latency block storage attached to a single EC2 instance in one Availability Zone. It's a good fit for filesystems, boot volumes, and databases that need block-level access. S3 is regional object storage you access through an API — good for backups, static assets, logs, data lakes, and build artifacts.

EBS isn't a shared object store, and S3 isn't a mounted filesystem by default. The choice comes down to how the data is accessed, latency needs, whether it needs to be shared, durability, lifecycle management, and how you'd recover it.

## 13. What is a NAT Gateway, and where is it deployed?

**Answer:**

A NAT Gateway lets workloads in a private subnet make outbound IPv4 connections without accepting unsolicited traffic from the internet. It sits in a public subnet with an Elastic IP and a route to an Internet Gateway. Private subnet route tables send `0.0.0.0/0` traffic to it.

For resilience, I deploy one NAT Gateway per Availability Zone, and route each private subnet to the NAT Gateway in its own zone. Where possible, I use VPC endpoints for AWS services like S3 instead, to cut cost and reduce the dependency on internet access altogether.

## 14. What is API Gateway, and when would you use it?

**Answer:**

API Gateway is a managed front door for APIs. It can expose REST, HTTP, or WebSocket APIs and route them to Lambda, other AWS services, VPC backends, or plain HTTP endpoints. It handles authentication and authorization, throttling, request validation and transformation, custom domains, stages, logging, and metrics.

I reach for it when those managed features actually add value. For a simple internal service or a conventional web app, an ALB or a direct endpoint can be simpler.

I scope backend permissions down to only what's needed, add WAF or auth where required, set quotas and rate limits, and make sure timeouts and error behavior are explicit and observable.

## 15. Explain a CloudFront + S3 + API Gateway + Lambda request flow.

**Answer:**

CloudFront is the public entry point. It serves cacheable static content from an S3 origin — normally locked down with Origin Access Control so the bucket itself isn't public — and forwards dynamic API requests on to API Gateway.

API Gateway authenticates and authorizes the request, validates it, then invokes Lambda using a resource policy or role that only allows that one invocation.

Lambda runs the business logic and reaches dependent services using its own role, scoped to only what it needs. The response travels back through API Gateway and CloudFront, subject to caching rules.

At each boundary I add TLS and a custom domain, WAF, logs and traces, cache invalidation or versioned assets, error handling, throttling, and alarms.

## 16. What is AWS Lambda, and where is it a good fit?

**Answer:**

Lambda runs short-lived, event-driven code without you managing any servers. It's a good fit for API handlers, scheduled jobs, processing objects, queues, or events, and automation — as long as the work can be stateless and idempotent, and it fits within Lambda's execution limits.

I set memory, timeout, and concurrency deliberately, give the execution role only the permissions it needs, keep dependencies small, store secrets outside the function, and monitor errors, duration, throttles, retries, and the DLQ or destination.

For long-running work, workloads that hold many connections, or anything needing a specialized runtime, containers or another compute service are usually a better fit.

## 17. How do you grant an application access to an S3 bucket safely?

**Answer:**

I attach an IAM role to the workload — an EC2 instance profile, ECS task role, Lambda execution role, or EKS workload identity — and give it only the actions and prefix it actually needs. For example, `s3:GetObject` on `arn:aws:s3:::reports-bucket/approved/*`, and `s3:ListBucket` restricted by `s3:prefix`.

The bucket policy, IAM policy, permission boundary, SCP, VPC endpoint policy, and KMS key policy all have to allow the access — and an explicit deny anywhere wins over all of them.

I keep Block Public Access turned on unless there's a deliberate reason to serve public content, require TLS and encryption, audit CloudTrail data events where it matters, and test both an allowed operation and a denied one to make sure the policy actually works as intended.

## 18. What is the difference between an ALB and an NLB?

**Answer:**

An Application Load Balancer works at Layer 7 — it understands HTTP/HTTPS and can route by host, path, header, or method, terminate TLS, and integrate with web-focused controls. A Network Load Balancer works at Layer 4 — it forwards TCP/UDP/TLS with very high performance and static IP support, but doesn't understand HTTP.

I use an ALB for web applications and APIs, and an NLB for non-HTTP protocols, very low-latency TCP/UDP, when I need to preserve the client's IP address, or when I need a static IP. Either way, you still need healthy targets, sensible timeouts, security groups where relevant, observability, and a design that spans multiple AZs.

## 19. How do Route 53 routing policies reduce latency or improve availability?

**Answer:**

Latency-based routing sends users to whichever healthy AWS region responds fastest. Weighted routing lets you shift traffic gradually. Failover routing gives you active-passive recovery. Geolocation or geoproximity routing handles location or data-residency needs. Multivalue answers return several healthy records at once. Simple routing is just a single record with no logic.

I pick the policy based on the traffic pattern, how consistent the data needs to be, and the failover design. I set up health checks where they're needed, keep TTLs realistic, and actually test that failover works.

DNS routing on its own doesn't replicate data, and it doesn't prevent a split-brain situation.
