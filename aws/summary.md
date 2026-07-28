# AWS Architecture Summary

## Production-Ready Three-Tier Web Architecture

Users resolve through **Route 53** and reach **CloudFront**, **WAF/Shield** controls, and an **Application Load Balancer**. The VPC spans multiple Availability Zones:

- **Public subnets** host internet-facing load balancers and NAT gateways where required.
- **Private application subnets** host autoscaled EC2/ECS/EKS workloads with no direct inbound internet access.
- **Isolated/private data subnets** host RDS Multi-AZ and ElastiCache replication groups. A cross-region read replica or replicated datastore is designed separately for regional DR.

**Security groups** reference application tiers instead of opening broad CIDR ranges: the edge or load balancer can reach the application port, and the application can reach only the required database or cache port. **ACM** provides TLS certificates; **Secrets Manager** and **KMS** protect credentials and keys; **Systems Manager Session Manager** provides audited administration without public SSH.

**VPC endpoints** provide private access to services such as S3, DynamoDB, ECR, CloudWatch Logs, Secrets Manager, and Systems Manager. They reduce dependence on NAT or internet access and can apply endpoint policies. When outbound internet access is required, a NAT gateway per availability zone avoids depending on another zone.

**S3** stores static artifacts and backups according to policy. **ECR** stores fixed, signed image versions. **CloudWatch** provides metrics, logs, and alarms, while **CloudTrail** records API activity. **Config** checks configuration, **Inspector** and **Security Hub** report security findings, **SNS** routes notifications, **SQS** separates producers from background workers, and **AWS Backup** applies a central backup policy.

A **CI/CD flow** can use GitHub -> GitHub Actions or CodeBuild -> ECR -> CodeDeploy blue-green or instance refresh -> CloudWatch verification. High availability needs compute and data across availability zones, autoscaling, health checks, tested backups, enough dependency capacity, and a clear regional failover process.

Cost optimization includes right-sizing, autoscaling, storage lifecycle, commitments for stable demand, and measurable cost per service transaction.

## EC2 High-CPU Investigation

Start with CloudWatch CPU utilization, instance status checks, traffic, deployment/configuration history, network and disk I/O; install the CloudWatch Agent if memory or process-level metrics are required.

For burstable T-series instances, inspect CPU credit balance and determine whether sustained demand is exhausting credits.
On the host, identify the responsible process and the type of pressure before changing capacity:

```bash
top
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head
pidstat -u 1
```

Compare process behavior with application/system logs, I/O wait, recent releases, scheduled jobs and dependency latency. Stabilize through a safe rollback, traffic shift, rate limit, autoscaling or termination of a confirmed nonessential runaway process.

Then fix the root cause—inefficient code/query, background job, capacity mismatch, burst-credit model or unexpected traffic—and verify user latency/errors as well as CPU. Scaling without that diagnosis can hide the fault and increase cost.

## Deploying a Java application to EC2

A production deployment should be automated and repeatable:

1. Build and test the application with Maven or Gradle, scan dependencies, and publish an immutable (not changed after creation) JAR/version to an approved artifact store such as S3 or CodeArtifact.
2. Provision the VPC, private EC2 instances or Auto Scaling group, IAM instance profile, security groups, load balancer, target group, logging, alarms, and deployment permissions through Terraform.
3. Bake the supported Java runtime and agents into a versioned AMI, or install them through controlled bootstrap/configuration management. Do not compile the application on the production instance.
4. Use CodeDeploy, Systems Manager, an image refresh, or another controlled deployment mechanism to download the exact artifact and its checksum. Retrieve configuration and secrets at runtime through Parameter Store or Secrets Manager using the instance role.
5. Run the JAR as a dedicated non-root user under `systemd`, with resource limits, restart policy, structured logs, and a health endpoint.
6. Register only healthy instances with the load balancer, run smoke and application checks, monitor errors/latency/JVM and host signals, and shift traffic gradually.
7. Roll back to the previous artifact or immutable (not changed after creation) instance version when health gates fail. Retain deployment evidence and fix the cause before retrying.

For administration, prefer **Systems Manager Session Manager** with IAM-controlled access and no inbound management port.

If SSH is explicitly required, restrict TCP 22 to an approved source or bastion, use the correct AMI user and protected key, verify the host key, and connect with `ssh -i <key.pem> <user>@<address>`.

Private instances need a private path such as VPN, Direct Connect, bastion, or Session Manager; a private IP is not reachable directly from the public internet.

## Terraform and Amazon ECR

Terraform does not log Docker into ECR. The AWS provider authenticates to AWS—preferably through a short-lived assumed role—and manages resources such as `aws_ecr_repository`, lifecycle policies, encryption, repository policies, and related VPC endpoints.

A CI runner authenticates Docker separately, normally with `aws ecr get-login-password`, then pushes an immutable (not changed after creation) tag or digest.

EC2/ECS/EKS workloads receive narrowly scoped pull permissions through their runtime IAM role; repository creation, image publishing, and image pulling are separate authorization paths.
