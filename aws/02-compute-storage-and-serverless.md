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

### 1. What is Amazon S3, and which storage classes would you choose?

**Answer:**

S3 is highly durable object storage. Applications store objects in buckets, identified by keys, and you control them with policies, encryption, and lifecycle rules.

For storage class, I pick Standard for data accessed often, Intelligent-Tiering when access patterns are unpredictable, Standard-IA or One Zone-IA for infrequently accessed or easily re-creatable data, and Glacier Instant Retrieval, Flexible Retrieval, or Deep Archive as you go further into cold archival storage.

I weigh retrieval time, minimum storage duration, and availability trade-offs, and I use lifecycle rules to move objects automatically instead of doing it by hand. Versioning, blocking public access, KMS encryption where required, bucket policies scoped to only what's needed, and regularly testing restores are the baseline controls I'd expect.

### 2. EBS versus S3: when would you use each?

**Answer:**

EBS is low-latency block storage attached to a single EC2 instance in one Availability Zone. It's a good fit for filesystems, boot volumes, and databases that need block-level access. S3 is regional object storage you access through an API — good for backups, static assets, logs, data lakes, and build artifacts.

EBS isn't a shared object store, and S3 isn't a mounted filesystem by default. The choice comes down to how the data is accessed, latency needs, whether it needs to be shared, durability, lifecycle management, and how you'd recover it.

### 3. What is AWS Lambda, and where is it a good fit?

**Answer:**

Lambda runs short-lived, event-driven code without you managing any servers. It's a good fit for API handlers, scheduled jobs, processing objects, queues, or events, and automation — as long as the work can be stateless and idempotent, and it fits within Lambda's execution limits.

I set memory, timeout, and concurrency deliberately, give the execution role only the permissions it needs, keep dependencies small, store secrets outside the function, and monitor errors, duration, throttles, retries, and the DLQ or destination.

For long-running work, workloads that hold many connections, or anything needing a specialized runtime, containers or another compute service are usually a better fit.

### 4. How do you create an AWS Lambda function and publish its artifact safely?

**Answer:**

I define everything as code — the Lambda function, execution role, log group, event source, networking, environment variables, timeout, memory, concurrency, and alarms — using Terraform, CloudFormation/SAM, CDK, or a similar reviewed workflow.

The execution role only gets the specific API actions and resource ARNs it needs. The identity used to deploy is kept separate from the identity the function runs as.

CI installs locked dependencies, runs unit and security tests, builds a predictable ZIP or container image, generates an SBOM, scans it, calculates a digest, and stores it in a versioned artifact bucket or ECR.

Deployment then references that exact version or digest — it's immutable, meaning it never changes once it's created. It publishes a new Lambda version and shifts an alias over to it gradually, using weighted traffic.

Secrets come from a secrets manager at runtime, through the function's identity. They're never embedded in the ZIP file or left in plaintext environment variables.

I check that invocations work, look at logs and traces, and watch error rate, throttling, and duration. I also confirm dependency access, retries, the DLQ or destination, and that the function is idempotent — safe to run more than once without side effects. If something's wrong, rollback just moves the alias back to the last healthy version.

Keeping artifact history, recording provenance (where the artifact came from and how it was built), signing code where required, and reserving concurrency all help protect the release.

### 5. What is API Gateway, and when would you use it?

**Answer:**

API Gateway is a managed front door for APIs. It can expose REST, HTTP, or WebSocket APIs and route them to Lambda, other AWS services, VPC backends, or plain HTTP endpoints. It handles authentication and authorization, throttling, request validation and transformation, custom domains, stages, logging, and metrics.

I reach for it when those managed features actually add value. For a simple internal service or a conventional web app, an ALB or a direct endpoint can be simpler.

I scope backend permissions down to only what's needed, add WAF or auth where required, set quotas and rate limits, and make sure timeouts and error behavior are explicit and observable.

### 6. Explain a CloudFront + S3 + API Gateway + Lambda request flow.

**Answer:**

CloudFront is the public entry point. It serves cacheable static content from an S3 origin — normally locked down with Origin Access Control so the bucket itself isn't public — and forwards dynamic API requests on to API Gateway.

API Gateway authenticates and authorizes the request, validates it, then invokes Lambda using a resource policy or role that only allows that one invocation.

Lambda runs the business logic and reaches dependent services using its own role, scoped to only what it needs. The response travels back through API Gateway and CloudFront, subject to caching rules.

At each boundary I add TLS and a custom domain, WAF, logs and traces, cache invalidation or versioned assets, error handling, throttling, and alarms.

### 7. What does email signing mean, and how would you implement it for an AWS-hosted email service?

**Answer:**

For email, signing usually means DKIM. The sending service signs selected headers and the body with a private key tied to the domain, and recipients verify that signature using a public key published in DNS.

With Amazon SES, I verify the domain, turn on Easy DKIM (or bring my own approved key), publish the CNAME/TXT records SES gives me, and wait for the domain to show as verified.

The private signing key stays managed and protected — applications never embed it directly.

I also set up SPF to say which infrastructure is allowed to send mail, and DMARC to define alignment, reporting, and what happens when a message fails. I roll DMARC out carefully: start in monitor-only mode (`p=none`), review the reports to make sure legitimate senders pass, then move to quarantine or reject once I'm confident.

A custom MAIL FROM domain, proper bounce and complaint handling, suppression lists, an SES identity with only the permissions it needs, TLS, sending quotas, and CloudWatch/SNS events all help protect the sending reputation.

I test the DKIM/SPF/DMARC headers against real recipients, plan for key rotation, confirm subdomain ownership, and check how things behave on failure. Signing proves the domain sent the message and that it wasn't altered — it doesn't encrypt the content. For that you'd need S/MIME or PGP.
