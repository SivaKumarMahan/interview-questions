# AWS Architecture Summary

## Production-Ready Three-Tier Web Architecture

Users resolve through **Route 53** and reach **CloudFront**, then **WAF/Shield**, then an **Application Load Balancer**. The VPC spans multiple Availability Zones, split into three layers:

| Layer | What lives there |
| --- | --- |
| Public subnets | Internet-facing load balancers and NAT gateways |
| Private application subnets | Autoscaled EC2/ECS/EKS workloads, with no direct inbound internet access |
| Isolated/private data subnets | RDS Multi-AZ and ElastiCache replication groups |

A cross-region read replica, or a replicated datastore, is set up separately if you need regional disaster recovery.

**Security groups** reference application tiers instead of opening broad CIDR ranges. The load balancer can reach the application port, and the application can reach only the specific database or cache port it needs — nothing wider than that.

**ACM** provides TLS certificates. **Secrets Manager** and **KMS** protect credentials and keys. **Systems Manager Session Manager** gives audited administrative access without needing public SSH.

**VPC endpoints** give private access to services like S3, DynamoDB, ECR, CloudWatch Logs, Secrets Manager, and Systems Manager. They cut down on NAT and internet dependency, and you can attach endpoint policies to them. Where outbound internet access is still needed, put one NAT gateway per Availability Zone, so one zone's traffic never depends on another zone's NAT gateway.

**S3** stores static artifacts and backups according to policy. **ECR** stores fixed, signed image versions. **CloudWatch** provides metrics, logs, and alarms. **CloudTrail** records API activity. **Config** checks configuration against policy. **Inspector** and **Security Hub** report security findings. **SNS** routes notifications. **SQS** separates producers from background workers. **AWS Backup** applies one central backup policy across services.

A typical **CI/CD flow** looks like: GitHub → GitHub Actions or CodeBuild → ECR → CodeDeploy (blue-green or instance refresh) → CloudWatch verification.

High availability comes down to a few things working together: compute and data spread across Availability Zones, autoscaling, health checks, backups that are actually tested, enough spare capacity in dependencies, and a clear plan for regional failover.

Cost optimization means right-sizing instances, autoscaling instead of over-provisioning, storage lifecycle rules, commitments (like Savings Plans) for steady demand, and tracking cost per transaction so you can see the impact of changes.

## EC2 High-CPU Investigation

Start with CloudWatch: CPU utilization, instance status checks, traffic, deployment and configuration history, and network/disk I/O. Install the CloudWatch Agent if you need memory or process-level metrics.

For burstable T-series instances, check the CPU credit balance and figure out whether sustained demand is burning through it.

On the host itself, find the responsible process and the type of pressure before you touch capacity:

```bash
top
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head
pidstat -u 1
```

Compare what you see against application and system logs, I/O wait, recent releases, scheduled jobs, and dependency latency. To stabilize things, use a safe rollback, a traffic shift, a rate limit, autoscaling, or terminate a process you've confirmed is safe to kill.

Then fix the actual root cause — inefficient code or a bad query, a background job, a capacity mismatch, the burst-credit model, or unexpected traffic — and confirm both user-facing latency/errors and CPU recover. Scaling out without diagnosing the cause just hides the problem and costs more.

## Deploying a Java application to EC2

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

## Terraform and Amazon ECR

Terraform does not log Docker into ECR. The AWS provider authenticates to AWS on its own — preferably through a short-lived assumed role — and manages resources like `aws_ecr_repository`, lifecycle policies, encryption, repository policies, and related VPC endpoints.

A CI runner authenticates Docker separately, usually with `aws ecr get-login-password`, and then pushes an image tag or digest. Once pushed, that tag or digest doesn't change — if you need a new image, you push a new tag or digest rather than overwriting the old one.

EC2, ECS, and EKS workloads get narrowly scoped pull permissions through their own runtime IAM role. Creating the repository, publishing an image, and pulling an image are three separate authorization paths — keep them that way.
