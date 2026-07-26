## 1. A server is healthy and has network connectivity, but logs are not uploading to an S3 bucket. What do you investigate?

**Answer:**

I separate source collection, authentication/authorization, S3 policy, encryption, and object-upload behavior. First I confirm the log agent/process is reading the correct path, has permission on the files, is not stuck behind a lock or full spool disk, and is producing current errors. I test the same configured AWS identity with `aws sts get-caller-identity` and a small upload to the exact bucket and prefix without printing credentials.

Common causes include an expired/static credential, wrong instance profile or region, missing `s3:PutObject`, an explicit deny in bucket policy/SCP/permissions boundary, required object tags or ACL conditions, KMS key policy missing `kms:Encrypt`/`GenerateDataKey`, Object Lock, wrong prefix, clock skew, multipart-upload failure, or storage-class/lifecycle expectations. CloudTrail data events and S3 server-side evidence show whether AWS received and denied a request.

I correct the narrow policy, key permission, agent configuration, disk/spool, or file ownership issue and verify a new object, encryption, metadata, and downstream consumption. I prefer an instance role with least privilege, agent health/backlog metrics, dead-letter/spool limits, and alerts on upload age and errors.

## 2. How do you create an AWS Lambda function and publish its artifact safely?

**Answer:**

I define Lambda, execution role, log group, event source, networking, environment references, timeout, memory, concurrency, alarms, and permissions through Terraform, CloudFormation/SAM, CDK, or another reviewed IaC workflow. The execution role gets only the API actions and resource ARNs required; deployment identity and runtime identity are separate.

CI installs locked dependencies, runs unit/security tests, creates a deterministic ZIP or container image, generates an SBOM, scans it, calculates a digest, and stores it in a versioned artifact bucket or ECR. Deployment references that immutable version/digest, publishes a Lambda version, and moves an alias gradually using weighted traffic. Secrets are fetched through a secret manager and identity, not embedded in ZIP files or environment plaintext.

I validate invocation, logs/traces, error/throttle/duration, dependency access, retries, DLQ/destination, and idempotency. Rollback moves the alias to the last healthy version. Artifact retention, signatures/provenance, code signing where required, and reserved concurrency protect the release.

## 3. What do you use AWS CloudWatch and CloudTrail for in production?

**Answer:**

CloudWatch is operational telemetry: AWS service and custom metrics, logs, dashboards, alarms, traces, synthetic checks, and event-driven actions. I use it for EC2/container resource and application signals, Lambda errors/duration/throttling, load-balancer status and latency, queue depth/age, log queries, SLO dashboards, and actionable alarms routed through SNS or incident tooling.

CloudTrail records AWS API activity: who or which role called an action, when, from where, against which resource, and whether it succeeded. I centralize organization trails in a protected security account, enable appropriate management and selected data events, encrypt and retain logs, and alert on high-risk actions such as policy changes, trail disabling, public exposure, key changes, or unusual role assumptions.

For an incident I correlate a CloudWatch symptom with deployment/config events and CloudTrail API evidence. Neither tool replaces application tracing or all OS metrics, and CloudTrail is an audit source rather than a real-time performance monitor.

## 4. An EC2 instance reaches 100% CPU. How do you investigate and recover it?

**Answer:**

I confirm duration, customer impact, instance status checks, load, recent deploys, autoscaling activity, and whether a burstable instance exhausted CPU credits. From SSM/console or SSH I use `uptime`, `top`, `ps`, `pidstat`, and application/runtime metrics to identify user CPU, system CPU, steal time, I/O wait, a runaway process, garbage collection, traffic spike, cron job, agent, or possible compromise.

I stabilize safely by shifting traffic, scaling out, rate-limiting, stopping a proven nonessential runaway job, or rolling back a bad release. I do not reboot first unless the host is unrecoverable because that destroys useful process evidence and may only move load elsewhere. Security signs lead to isolation and incident response rather than simple restart.

The permanent fix may be application profiling, query/cache improvement, resource limits, corrected scheduled work, autoscaling on useful demand signals, a suitable instance family, or capacity planning. I verify latency/error and CPU recover under load and add alerts for saturation, credits, queueing, and scaling failure.

## 5. How do EC2, EKS, ECS, and databases fit together, and how do you interact with an ECS service?

**Answer:**

EC2 provides virtual machines and can back self-managed applications, ECS container instances, or EKS worker nodes. ECS is AWS container orchestration; EKS provides a managed Kubernetes control plane. Databases such as RDS normally live in private subnets and accept traffic only from the exact application security group on the database port. Load balancers expose selected services; IAM roles for tasks or service accounts provide workload identity.

For ECS I use the AWS CLI/API rather than “logging into ECS”:

```bash
aws ecs list-clusters
aws ecs list-services --cluster production
aws ecs describe-services --cluster production --services payments
aws ecs execute-command --cluster production --task <task-id> \
  --container payments --interactive --command '/bin/sh'
```

ECS Exec requires SSM integration, IAM authorization, logging, and a running supported task. I prefer logs/metrics over interactive access and never open a database publicly. I validate DNS, security-group references, TLS, credentials, connection pools, health checks, and failure behavior across AZs.

## 6. Design a secure, scalable, highly available AWS architecture for a global SaaS product and explain regional failover.

**Answer:**

I begin with tenancy, data classification/residency, traffic, SLO, RTO/RPO, consistency, and compliance. Route 53 or Global Accelerator directs users to regional CloudFront/WAF and load-balancer/API endpoints. Each region has multiple AZs, private application subnets, autoscaled ECS/EKS/compute, controlled egress, workload identity, KMS encryption, centralized logs/security findings, and no public databases. Tenant isolation is enforced in identity, authorization, data keys/partitions, quotas, and audit—not only network boundaries.

Data architecture determines failover. DynamoDB Global Tables or a supported multi-region datastore can provide active-active behavior; relational systems may use cross-region replicas with one write region. Object data uses replication where RPO requires it. Infrastructure and policy are reproducible from versioned IaC, secrets and certificates exist independently in each region, and dependencies have regional capacity.

During an outage I declare the incident, stop risky deployments, confirm the failure and replication lag, promote or fence data according to the runbook, scale the recovery region, verify internal transactions, then shift weighted traffic gradually. Preventing split brain is more important than a fast DNS change. I monitor errors, latency, data correctness, queues, and business outcomes, retain rollback criteria, and reconcile data before failing back. Regular game days prove actual RTO/RPO.

## 7. What does email signing mean, and how would you implement it for an AWS-hosted email service?

**Answer:**

For internet email, signing normally means DKIM: the sending service signs selected headers/body with a domain private key, and recipients verify it using a public key published in DNS. With Amazon SES I verify the domain, enable Easy DKIM or bring an approved key, publish the provided CNAME/TXT records, and wait for verified status. The private signing material remains managed/protected; applications do not embed it.

I also configure SPF to authorize sending infrastructure and DMARC to define alignment, reporting, and policy. DMARC is introduced with monitoring (`p=none`), analysis of legitimate senders, then quarantine/reject when alignment is proven. A custom MAIL FROM domain, bounce/complaint handling, suppression lists, least-privilege SES identity, TLS, quotas, and CloudWatch/SNS events protect delivery reputation.

I test DKIM/SPF/DMARC headers with real recipients, key rotation, subdomain ownership, and failure behavior. Email signing proves domain authorization and message integrity; it does not encrypt the email content—S/MIME or PGP addresses end-to-end message signing/encryption where required.

## 8. What is Amazon S3, and which storage classes would you choose?

**Answer:**

S3 is highly durable object storage: applications store objects in buckets using keys, policies, encryption and lifecycle rules. I choose Standard for frequent access; Intelligent-Tiering for uncertain patterns; Standard-IA or One Zone-IA for infrequent/re-creatable data; and Glacier Instant Retrieval, Flexible Retrieval or Deep Archive for increasingly cold archives. I account for retrieval, minimum-duration and availability trade-offs, and use lifecycle rules rather than manually moving objects. Versioning, block-public-access, KMS where required, least-privilege bucket policies and restore testing are baseline controls.

## 9. What is the difference between a security group and a network ACL?

**Answer:**

A security group is a stateful, allow-only virtual firewall attached to an ENI/resource; return traffic is automatically allowed and rules can reference another security group. A network ACL is a stateless subnet boundary with ordered allow and deny rules; both inbound and outbound return traffic must be allowed explicitly. I use security groups for the normal least-privilege application path and NACLs for coarse subnet guardrails or explicit deny requirements. I troubleshoot by checking route tables, both directions, ephemeral ports and the actual ENI/subnet—not by opening `0.0.0.0/0`.

## 10. IAM role versus IAM user: when do you use each?

**Answer:**

An IAM role supplies temporary credentials to a workload or a federated human identity and can be assumed with narrowly scoped permissions. An IAM user is a long-lived AWS principal; it is a legacy fit only for exceptional cases where federation or roles cannot be used. I use roles for EC2, Lambda, ECS/EKS workloads, CI and human access through SSO, with MFA and least privilege. I avoid static access keys, rotate any unavoidable key, and review CloudTrail evidence and permission boundaries/SCPs.

## 11. How do you back up and restore an EC2 workload?

**Answer:**

I make the application recoverable rather than treating a running instance as the only copy. Infrastructure is recreated from IaC; data is backed up from the database/application and EBS volumes use scheduled, encrypted snapshots with retention and cross-account/region copies when required. An AMI can preserve a tested machine image but is not a substitute for application-consistent data backups. A restore runbook launches or rebuilds the instance, restores data, validates security/DNS/secrets and proves the application transaction. I regularly test restores against stated RTO/RPO.

## 12. EBS versus S3: when would you use each?

**Answer:**

EBS is low-latency block storage attached to an EC2 instance in one Availability Zone; it suits filesystems, boot volumes and databases that need block semantics. S3 is regional object storage accessed through its API; it suits backups, static assets, logs, data lakes and artifacts. EBS is not a shared object store, and S3 is not a mounted POSIX disk by default. I choose based on access semantics, latency, sharing, durability, lifecycle and recovery needs.

## 13. What is a NAT Gateway, and where is it deployed?

**Answer:**

A NAT Gateway lets private-subnet workloads initiate outbound IPv4 connections without accepting unsolicited inbound internet traffic. It is deployed in a public subnet with an Elastic IP and a route to an Internet Gateway; private subnet route tables send `0.0.0.0/0` to the NAT Gateway. For resilience, I deploy one per Availability Zone and route each private subnet to its local NAT Gateway. I use VPC endpoints for AWS services such as S3 where possible to reduce cost and internet dependency.

## 14. What is API Gateway, and when would you use it?

**Answer:**

API Gateway is a managed API front door that can expose REST, HTTP or WebSocket APIs and route them to Lambda, AWS services, VPC backends or other HTTP endpoints. It can provide authentication/authorization, throttling, request validation/transformation, custom domains, stages, logging and metrics. I use it when those managed API capabilities fit the service boundary; an ALB or direct service endpoint can be simpler for an internal or conventional web workload. I configure least-privilege backend permissions, WAF/auth as required, quotas/rate limits, observability and explicit timeout/error behavior.

## 15. Explain a CloudFront + S3 + API Gateway + Lambda request flow.

**Answer:**

CloudFront is the public edge entry point. It serves cacheable static paths from an S3 origin—normally protected by Origin Access Control so the bucket is not public—and forwards dynamic API paths to API Gateway. API Gateway authenticates/authorizes and validates the request, then invokes Lambda with a resource policy/role that permits only that invocation. Lambda executes business logic and reads dependent services with its own least-privilege role; the response returns through API Gateway and CloudFront, subject to caching rules. I add TLS/custom domain, WAF, logs/traces, cache invalidation/versioned assets, error handling, throttling and alarms at each boundary.

## 16. What is AWS Lambda, and where is it a good fit?

**Answer:**

Lambda runs short-lived, event-driven code without managing servers. It is well suited to API handlers, scheduled work, object/queue/event processing and automation that can be stateless, idempotent and bounded by Lambda execution limits. I set memory/timeout/concurrency intentionally, use an execution role with minimum permissions, keep dependencies small, store secrets externally, and monitor errors, duration, throttles, retries and DLQ/destinations. For long-running, highly connection-heavy or specialized-runtime workloads, containers or compute services may be a better fit.

## 17. How do you grant an application access to an S3 bucket safely?

**Answer:**

I attach a least-privilege IAM role to the workload (EC2 instance profile, ECS task role, Lambda execution role or EKS workload identity), then allow only the required actions and prefix—for example `s3:GetObject` on `arn:aws:s3:::reports-bucket/approved/*` and `s3:ListBucket` constrained by `s3:prefix`. Bucket policy, IAM policy, permission boundary, SCP, VPC endpoint policy and KMS key policy must all permit the access; an explicit deny wins. I keep Block Public Access enabled unless there is a deliberate public-content design, require TLS/encryption, audit CloudTrail data events as appropriate and test both an allowed and denied operation.

## 18. What is the difference between an ALB and an NLB?

**Answer:**

An Application Load Balancer is Layer 7: it understands HTTP/HTTPS and can route by host, path, header or method, terminate TLS and integrate with web-oriented controls. A Network Load Balancer is Layer 4: it forwards TCP/UDP/TLS with very high performance and static IP options, but has less HTTP awareness. I choose ALB for web applications and APIs; NLB for non-HTTP protocols, low-latency TCP/UDP, preserved client addressing or static-IP requirements. Both still require healthy targets, timeouts, security groups where applicable, observability and multi-AZ design.

## 19. How do Route 53 routing policies reduce latency or improve availability?

**Answer:**

Latency-based routing directs DNS answers toward the lowest-latency healthy AWS region; weighted routing supports gradual traffic shifts; failover routing provides active-passive recovery; geolocation/geoproximity supports location or residency needs; multivalue answers return several healthy records; and simple routing is a basic single-record choice. I choose the policy from the traffic, data-consistency and failover design, configure health checks where needed, keep TTLs realistic and test recovery. DNS routing alone does not replicate data or prevent split brain.
