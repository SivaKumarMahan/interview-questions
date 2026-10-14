# AWS: Architecture and High Availability

> How core AWS services fit together into secure, scalable, multi-AZ and multi-region architectures, including autoscaling, load balancing, DNS routing, and backup.

## Key Concepts

### Production-Ready Three-Tier Web Architecture

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

## Interview Questions

<details><summary>Q1. [Basic] How do EC2, EKS, ECS, and databases fit together, and how do you interact with an ECS service?</summary>

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

</details>

<details><summary>Q2. [Advanced] Design a secure, scalable, highly available AWS architecture for a global SaaS product and explain regional failover.</summary>

**Answer:**

I start by understanding the tenancy model, data classification and residency requirements, expected traffic, SLOs, recovery targets (RTO/RPO), consistency needs, and compliance rules. Route 53 or Global Accelerator sends users to the nearest region's CloudFront, WAF, and load balancer or API endpoints.

Each region gets multiple AZs, private application subnets, autoscaled compute on ECS or EKS, controlled outbound traffic, its own workload identity, KMS encryption, centralized logs and security findings, and no databases exposed publicly.

Tenant isolation isn't just network boundaries — it's enforced in identity, authorization, data keys or partitions, quotas, and audit logging too.

How you handle data decides how failover works. DynamoDB Global Tables, or another datastore built for multiple regions, can give you active-active behavior. Relational databases usually use cross-region replicas with a single write region instead.

Object storage gets replicated wherever the recovery point objective requires it. Infrastructure and policy come from versioned infrastructure-as-code so they're reproducible. Secrets and certificates exist independently in each region, and dependencies have enough capacity in each region too.

During an actual outage: declare the incident, stop any risky deployments, confirm the failure and check replication lag, promote or fence the data according to the runbook, scale up the recovery region, verify transactions are working internally, then shift traffic over gradually using weighted routing. Avoiding a split-brain situation matters more than failing over quickly.

Afterward I watch errors, latency, data correctness, queue depth, and business metrics. I keep clear rollback criteria, and before failing back I reconcile — make actual state match desired state — the data. Regular game days are how you prove your real RTO and RPO, not just the numbers on paper.

</details>

<details><summary>Q3. [Advanced] Design a highly available, scalable microservices architecture on AWS (auto-scaling + DR) <em>(asked in interview round)</em></summary>

- Default to **multi-AZ**; add **multi-region** for disaster recovery.
- **Ingress path:** Route 53 (with health checks, latency-based or failover routing) → CloudFront/WAF → ALB.
- **Compute:** EKS or ECS Fargate, with HPA and Cluster Autoscaler/Karpenter spread across AZs. Keep services stateless.
- **Data:** Aurora Multi-AZ with a cross-region replica, DynamoDB global tables, and ElastiCache. Handle anything async through SQS, SNS, or Kafka.
- **DR strategy:** Pick one based on your recovery targets — backup-and-restore, pilot light, warm standby, or active-active. Define how much downtime and data loss you can tolerate (RTO/RPO), automate the failover, replicate both data and infrastructure code to the DR region, and actually test failover on a regular schedule.
- **Observability and resilience:** Centralize logs, metrics, and traces. Add circuit breakers and retries, pod disruption budgets, and keep infrastructure defined in Terraform so it's reproducible.

</details>

<details><summary>Q4. [Advanced] Design an auto-scaling strategy for a high-traffic app <em>(asked in interview round)</em></summary>

- **Compute:** Use Auto Scaling Groups for EC2, or HPA plus Cluster Autoscaler/Karpenter for EKS. Put an ALB or NLB in front, spread across multiple AZs.
- **Scaling policies:** Start with target-tracking as the baseline — for example, keep CPU near 60%, or track ALB requests per target. Add step scaling for sudden bursts, scheduled scaling for predictable peaks, and predictive scaling for known daily patterns.
- **Keep the app tier stateless** so instances are disposable. Store sessions in Redis or DynamoDB instead of on the instance.
- **Downstream:** Scale the data layer too — RDS read replicas or Aurora Auto Scaling, DynamoDB on-demand. Add CloudFront plus caching, and use SQS to absorb traffic spikes.
- **Guardrails:** Set min/max bounds, use warm pools so scale-out is fast, add health checks, and set cost alarms.

</details>

<details><summary>Q5. [Basic] What is the difference between an ALB and an NLB?</summary>

**Answer:**

An Application Load Balancer works at Layer 7 — it understands HTTP/HTTPS and can route by host, path, header, or method, terminate TLS, and integrate with web-focused controls. A Network Load Balancer works at Layer 4 — it forwards TCP/UDP/TLS with very high performance and static IP support, but doesn't understand HTTP.

I use an ALB for web applications and APIs, and an NLB for non-HTTP protocols, very low-latency TCP/UDP, when I need to preserve the client's IP address, or when I need a static IP. Either way, you still need healthy targets, sensible timeouts, security groups where relevant, observability, and a design that spans multiple AZs.

</details>

<details><summary>Q6. [Intermediate] How do Route 53 routing policies reduce latency or improve availability?</summary>

**Answer:**

Latency-based routing sends users to whichever healthy AWS region responds fastest. Weighted routing lets you shift traffic gradually. Failover routing gives you active-passive recovery. Geolocation or geoproximity routing handles location or data-residency needs. Multivalue answers return several healthy records at once. Simple routing is just a single record with no logic.

I pick the policy based on the traffic pattern, how consistent the data needs to be, and the failover design. I set up health checks where they're needed, keep TTLs realistic, and actually test that failover works.

DNS routing on its own doesn't replicate data, and it doesn't prevent a split-brain situation.

</details>

<details><summary>Q7. [Intermediate] How do you back up and restore an EC2 workload?</summary>

**Answer:**

I make sure the application can be recovered — I don't treat a single running instance as the only copy of anything. Infrastructure gets rebuilt from infrastructure-as-code. Data gets backed up at the database or application level. EBS volumes get scheduled, encrypted snapshots, with retention rules and cross-account or cross-region copies when needed.

An AMI can preserve a tested machine image, but it's not a substitute for backing up application data properly. A restore runbook launches or rebuilds the instance, restores the data, checks security settings, DNS, and secrets, and confirms the application actually works end to end.

I test restores regularly against the recovery time and recovery point targets we've agreed on.

</details>

<details><summary>Q8. [Advanced] Design a highly available 3-tier architecture. <em>(asked in interview round)</em></summary>

**Answer:**

A highly available 3-tier design spreads **every tier across at least two (preferably three) Availability Zones**, puts only the load balancer in public subnets, and uses managed services for failover.

**Architecture:**

```text
                         Users
                           |
                     Route 53 (DNS, health checks)
                           |
                 CloudFront + AWS WAF (+ Shield)
                           |
   ================== VPC 10.0.0.0/16 ===========================
   |        AZ-a                 AZ-b                 AZ-c       |
   |  Public subnet         Public subnet         Public subnet  |
   |  [External ALB node]   [External ALB node]   [ALB node]     |
   |  [NAT Gateway]         [NAT Gateway]         [NAT Gateway]  |
   |        |                     |                     |        |
   |  Private web subnet    Private web subnet    Private web    |
   |  [Web EC2 / ASG]       [Web EC2 / ASG]       [Web EC2]      |
   |        |                     |                     |        |
   |          ------ Internal ALB (all AZs) ------               |
   |        |                     |                     |        |
   |  Private app subnet    Private app subnet    Private app    |
   |  [App EC2 / ASG]       [App EC2 / ASG]       [App EC2]      |
   |        |                     |                     |        |
   |  Private DB subnet     Private DB subnet     Private DB     |
   |  [RDS primary]   --sync-->  [RDS standby]    [ElastiCache]  |
   ===============================================================
        S3 (static assets, backups) via VPC gateway endpoint
```

**Design steps:**

1. **VPC and subnets**: one VPC, three AZs, and in each AZ a public subnet, a private web/app subnet and a private database subnet.
2. **Edge**: Route 53 alias to CloudFront; AWS WAF for OWASP rules and rate limiting; ACM certificates.
3. **Presentation tier**: internet-facing ALB in public subnets; web servers (or static frontend from S3 + CloudFront) in private subnets in an Auto Scaling group across AZs.
4. **Application tier**: internal ALB in front of an app Auto Scaling group (or EKS/ECS services) spread across AZs.
5. **Data tier**: RDS Multi-AZ (or Aurora with replicas in other AZs), ElastiCache with Multi-AZ automatic failover, S3 for objects.
6. **Outbound**: one NAT Gateway per AZ, with each private route table pointing to the NAT in the same AZ; VPC endpoints for S3, ECR, Secrets Manager.
7. **Security**: security groups chained (ALB SG → web SG → app SG → DB SG), Secrets Manager for credentials, KMS encryption, IAM roles for instances.
8. **Operations**: CloudWatch alarms and dashboards, centralized logs, AWS Backup, IaC (Terraform), and a DR plan (cross-Region snapshots or pilot light) based on RTO/RPO.

**Example: security group chain (Terraform excerpt):**

```hcl
resource "aws_security_group_rule" "app_from_web" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.app.id
  source_security_group_id = aws_security_group.web.id
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id
}
```

**Important points:**

- High availability means no single point of failure per AZ: load balancer, compute, NAT and database all span AZs.
- Size for N-1: if one of three AZs fails, the remaining two must handle peak load.
- Multi-AZ protects against an AZ failure, not a Region failure; multi-Region DR is a separate decision based on RTO/RPO and cost.
- Keep the app stateless (sessions in ElastiCache/DynamoDB) so any instance can serve any request.

See also: [Three-tier architecture](../repetitive-questions/three-tier-architecture.md), [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md).

**Interview-ready answer:**

> "I build one VPC across three Availability Zones, with public, private app and private database subnets in each AZ. Route 53 points to CloudFront with WAF, which forwards to an internet-facing ALB in the public subnets. The web and application tiers run in Auto Scaling groups or EKS in private subnets across all AZs, with an internal ALB between them. The data tier is RDS Multi-AZ or Aurora, plus ElastiCache with automatic failover, and S3 for static content and backups. Each AZ has its own NAT Gateway, security groups only allow traffic from the tier above, and secrets live in Secrets Manager. I size capacity so the remaining AZs can handle peak load if one fails, and everything is built with Terraform and monitored with CloudWatch."

</details>

<details><summary>Q9. [Intermediate] Which AWS services make it highly available? <em>(asked in interview round)</em></summary>

**Answer:**

High availability comes from services that are **multi-AZ by design** or that you **configure across AZs**, plus health checks that route around failures.

| Layer | Service | How it provides HA |
| --- | --- | --- |
| DNS | Route 53 | Health checks and failover/latency/weighted routing; 100% availability SLA |
| Edge | CloudFront, AWS WAF, Shield | Global edge network, origin failover, DDoS protection |
| Load balancing | ALB / NLB | Nodes in every enabled AZ, health checks, cross-zone load balancing |
| Compute | EC2 Auto Scaling | Replaces unhealthy instances, balances across AZs |
| Containers | EKS / ECS | Managed control plane across AZs; nodes/tasks spread across AZs |
| Serverless | Lambda, API Gateway, Fargate | Multi-AZ managed by AWS |
| Database | RDS Multi-AZ, Aurora, DynamoDB | Synchronous standby and automatic failover; Aurora stores 6 copies across 3 AZs; DynamoDB is multi-AZ by default (Global Tables for multi-Region) |
| Cache | ElastiCache (Multi-AZ with auto failover) | Replica promoted on primary failure |
| Storage | S3, EFS | Data stored across multiple AZs (except One Zone classes) |
| Network | NAT Gateway per AZ, Transit Gateway | Zonal redundancy |
| Recovery | AWS Backup, cross-Region replication, Elastic Disaster Recovery | Restore and DR |
| Monitoring | CloudWatch, Route 53 health checks | Detect failures and trigger alarms/automation |

**Example: check RDS failover and ASG spread:**

```bash
aws rds describe-db-instances --db-instance-identifier prod-db \
  --query "DBInstances[0].[MultiAZ,AvailabilityZone,SecondaryAvailabilityZone]"

aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names app-asg \
  --query "AutoScalingGroups[0].[AvailabilityZones,HealthCheckType]"

# Controlled failover test (causes a short outage, run in a maintenance window)
aws rds reboot-db-instance --db-instance-identifier prod-db --force-failover
```

**Important points:**

- A service is only HA if you configure it that way: an ASG in one subnet or a Single-AZ RDS is still a single point of failure.
- EBS volumes and EC2 instances are zonal.
- Test failover (RDS reboot with failover, AWS Fault Injection Service) instead of assuming it works.

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md).

**Interview-ready answer:**

> "For DNS I use Route 53 with health checks, and CloudFront, WAF and Shield at the edge. The ALB runs in multiple AZs and only sends traffic to healthy targets. EC2 Auto Scaling groups or EKS node groups span several AZs and replace failed instances. For data, RDS Multi-AZ or Aurora gives automatic failover, ElastiCache uses Multi-AZ replication, and S3 and DynamoDB are multi-AZ by default. I put one NAT Gateway in each AZ and use AWS Backup plus cross-Region copies for DR. I also remember that most of these are only highly available if configured across AZs, so I verify the configuration and test failover regularly."

</details>

<details><summary>Q10. [Basic] Where do you place the web server, app server and database: public or private subnet? <em>(asked in interview round)</em></summary>

**Answer:**

In a modern design, **only the internet-facing load balancer (and NAT Gateways) go in public subnets**. Web servers, app servers and databases all go in **private subnets**.

| Component | Subnet | Reason |
| --- | --- | --- |
| Internet-facing ALB | Public | Needs a route to the Internet Gateway to receive internet traffic |
| NAT Gateway | Public | Needs the Internet Gateway for outbound traffic |
| Web servers | Private | Reached only through the ALB; no public IPs |
| App servers | Private | Reached only from the web tier or internal ALB |
| Database (RDS) | Private (isolated DB subnet) | No internet route at all; only the app SG can connect |
| Bastion | Avoid; use SSM Session Manager | No inbound SSH needed |

```text
Internet -> IGW -> ALB (public) -> Web (private) -> Internal ALB -> App (private) -> RDS (private DB subnet)
                                     |                                  |
                                     +---- outbound via NAT GW (public) -+
```

**Example: RDS in private DB subnets with no public access:**

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name prod-db-subnets \
  --db-subnet-group-description "Private DB subnets" \
  --subnet-ids subnet-db-a subnet-db-b subnet-db-c

aws rds modify-db-instance --db-instance-identifier prod-db \
  --no-publicly-accessible --apply-immediately
```

**Important points:**

- A subnet is "public" only because its route table has `0.0.0.0/0` to an Internet Gateway.
- Older designs put web servers in the public subnet with public IPs; that increases attack surface and isn't needed when an ALB is in front.
- Database subnets usually have no route to a NAT Gateway at all.
- Use SSM Session Manager instead of SSH bastions.

See also: [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md), [Three-tier architecture](../repetitive-questions/three-tier-architecture.md).

**Interview-ready answer:**

> "Only the internet-facing load balancer and the NAT Gateways go in public subnets. The web servers sit in private subnets behind the ALB, the app servers in private subnets behind an internal ALB, and the database in isolated private database subnets with no internet route. Security groups only allow traffic from the tier directly above, so the database accepts connections only from the app tier. None of the instances have public IPs, and for admin access I use SSM Session Manager instead of a bastion host. This keeps the attack surface to just the load balancer."

</details>

<details><summary>Q11. [Intermediate] Explain the complete traffic flow. <em>(asked in interview round)</em></summary>

**Answer:**

I explain both directions: an **inbound user request** down through the tiers and back, and **outbound traffic** from private servers.

**Inbound request flow:**

```text
1. User types app.example.com
        |
2. DNS: Route 53 returns CloudFront (alias record)
        |
3. CloudFront edge location: TLS termination, WAF rules, cache
   - static content (/static/*) -> served from cache or S3 origin (OAC)
   - dynamic (/api/*)           -> forwarded to ALB origin
        |
4. Internet Gateway -> internet-facing ALB (public subnets, AZ-a/b/c)
   - HTTPS listener (ACM cert), listener rules, target group health checks
        |
5. Web tier instance (private subnet) -- SG allows only ALB SG
        |
6. Internal ALB -> App tier instance/Pod (private subnet) -- SG allows only web SG
        |
7. App reads cache (ElastiCache); on miss queries RDS primary (DB subnet)
   - SG on RDS allows only app SG on 5432/3306
        |
8. Response travels back: RDS -> App -> Web -> ALB -> CloudFront -> User
```

**Outbound flow (private instance calling the internet):**

```text
App instance (10.0.11.25, private subnet AZ-a)
   -> route table: 0.0.0.0/0 -> NAT Gateway in public subnet AZ-a
   -> NAT translates source to its Elastic IP
   -> route table of public subnet: 0.0.0.0/0 -> Internet Gateway
   -> external API
Calls to S3 go through the S3 gateway endpoint instead of NAT.
```

**Controls at each hop:**

| Hop | Control |
| --- | --- |
| DNS | Route 53 health checks / failover |
| Edge | WAF, Shield, CloudFront cache behaviors, geo restriction |
| Public subnet | NACL, ALB security group (443 from `0.0.0.0/0` or CloudFront prefix list) |
| Each tier | Security groups referencing the previous tier's SG |
| Database | Private DB subnet, no internet route, encryption, IAM/Secrets Manager credentials |
| Observability | ALB access logs, VPC Flow Logs, CloudFront logs, X-Ray/OpenTelemetry traces |

**Example: verify the path:**

```bash
dig +short app.example.com                                    # CloudFront
curl -sI https://app.example.com/api/health | grep -i x-cache # Miss/Hit from CloudFront
aws elbv2 describe-target-health --target-group-arn <tg-arn>  # healthy targets per AZ
```

**Important points:**

- Security groups are stateful, so return traffic is allowed automatically; NACLs are stateless and need ephemeral port rules.
- Restricting the ALB to the CloudFront managed prefix list prevents bypassing WAF.
- The ALB sends to targets in all enabled AZs; cross-zone load balancing is on by default for ALB.

See also: [Three-tier architecture](../repetitive-questions/three-tier-architecture.md), [AWS networking, security and IAM](../aws/03-networking-security-and-iam.md).

**Interview-ready answer:**

> "The user resolves the domain through Route 53, which points to CloudFront. CloudFront terminates TLS, applies WAF rules, serves cached and static content from S3, and forwards dynamic requests to the internet-facing ALB in the public subnets. The ALB health-checks its targets and sends the request to a web instance in a private subnet, which calls the app tier through an internal ALB. The app checks ElastiCache and then RDS in the isolated database subnets, and the response goes back along the same path. Each tier's security group only allows the tier above it. Outbound calls from private instances go through the NAT Gateway in the same AZ and the Internet Gateway, while S3 traffic uses a gateway endpoint."

</details>

<details><summary>Q12. [Advanced] How would you add a new Availability Zone? <em>(asked in interview round)</em></summary>

**Answer:**

Adding an AZ means **extending every tier** into the new AZ: networking first, then load balancer, compute and data, and finally validating that traffic is balanced. I do it through IaC so all environments stay consistent.

**Steps:**

1. **Check IP space**: confirm the VPC CIDR has room for new subnets; if not, add a secondary CIDR.
2. **Create subnets** in the new AZ (for example `us-east-1c`): public, private app, private DB, with the same tags (for EKS: `kubernetes.io/role/elb` and `kubernetes.io/role/internal-elb`).
3. **Routing**: create a NAT Gateway in the new public subnet, a private route table pointing to it, and associate the new subnets; add the new route tables to gateway endpoints (S3/DynamoDB) and the new subnets to interface endpoints.
4. **NACLs and security groups**: SGs are VPC-wide, so usually no change; update NACLs or any CIDR-based rules.
5. **Load balancers**: enable the new AZ on the external and internal ALB by adding the new public/private subnets.
6. **Compute**: add the new private subnet to the Auto Scaling group (`VPCZoneIdentifier`); the ASG rebalances instances across AZs. For EKS, add the subnet to node groups or Karpenter `EC2NodeClass` subnet selectors.
7. **Data tier**: add the new DB subnet to the DB subnet group; place an Aurora reader or ElastiCache replica in the new AZ.
8. **Capacity**: raise ASG min/desired so each AZ has enough capacity for N-1.
9. **Validate**: target health per AZ, traffic distribution, failover test, monitoring dashboards updated.

```text
VPC CIDR check
   -> new subnets (public / app / db) in AZ-c
   -> NAT GW + route table in AZ-c, endpoints updated
   -> ALB: enable AZ-c subnets
   -> ASG / EKS node groups: add AZ-c subnet
   -> DB subnet group + replica in AZ-c
   -> validate target health and failover
```

**Example (Terraform):**

```hcl
variable "azs" {
  default = ["us-east-1a", "us-east-1b", "us-east-1c"]   # added us-east-1c
}

resource "aws_subnet" "private_app" {
  for_each          = toset(var.azs)
  vpc_id            = aws_vpc.main.id
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 10 + index(var.azs, each.value))
}

resource "aws_autoscaling_group" "app" {
  vpc_zone_identifier = [for s in aws_subnet.private_app : s.id]
  min_size            = 3
  max_size            = 12
  health_check_type   = "ELB"
  # ...
}
```

Using `for_each` over AZs means adding an AZ is a one-line change and existing subnets are not recreated (with `count`, reordering the list can force replacement).

**Important points:**

- ASG AZ rebalancing terminates and launches instances; make sure the app handles it (connection draining, lifecycle hooks).
- An RDS Multi-AZ instance has one standby; the new AZ helps only if the DB subnet group includes it. Aurora lets you add a reader there.
- Existing EBS volumes and StatefulSet PVCs stay in their original AZ.
- Run `terraform plan` and review that nothing existing is destroyed.

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md).

**Interview-ready answer:**

> "I extend each tier into the new AZ through Terraform. First I make sure the VPC has free CIDR space, then create public, app and database subnets in the new AZ with the right tags. I add a NAT Gateway and route table for that AZ and update VPC endpoints. Then I enable the new subnets on the external and internal ALBs, add the private subnet to the Auto Scaling group or EKS node groups so instances rebalance, and add the database subnet to the DB subnet group, with an Aurora reader or cache replica there if needed. I use `for_each` keyed by AZ so existing subnets aren't recreated, review the plan carefully, and finally validate target health, traffic distribution and failover."

</details>

<details><summary>Q13. [Intermediate] How would you configure Auto Scaling for high scalability? <em>(asked in interview round)</em></summary>

**Answer:**

I use an **Auto Scaling group across multiple AZs**, created from a **launch template**, with **ELB health checks**, and a combination of scaling policies: **target tracking** as the main policy, **predictive or scheduled** scaling for known patterns, and **warm pools** if instances take long to start.

**Building blocks:**

| Component | Configuration |
| --- | --- |
| Launch template | AMI, instance type(s), IAM role, user data, IMDSv2, versioned |
| ASG placement | Subnets in 2–3 AZs; capacity rebalancing |
| Instance mix | Mixed instances policy (several types, On-Demand base + Spot) |
| Health checks | `HealthCheckType=ELB` with a grace period so failed app health replaces instances |
| Target tracking | Keep average CPU at 50–60% or `ALBRequestCountPerTarget` at a target |
| Step scaling | Bigger jumps for bigger alarm breaches |
| Scheduled scaling | Known events (business hours, sales) |
| Predictive scaling | ML forecast from 14 days of history, launches capacity ahead of daily patterns |
| Warm pool | Pre-initialized stopped/hibernated instances to cut scale-out time |
| Lifecycle hooks | Bootstrapping or draining before termination |
| Instance refresh | Rolling AMI updates with minimum healthy percentage |

```text
CloudWatch metrics (CPU, RequestCountPerTarget)
        |
        v
Scaling policies: target tracking + predictive + scheduled
        |
        v
ASG (min 3 / desired 6 / max 30) across AZ-a, AZ-b, AZ-c
        |
        +--> launch from template (warm pool first)
        +--> register in ALB target group, ELB health check
        +--> scale in: deregistration delay, lifecycle hook, termination policy
```

**Example (AWS CLI):**

```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name app-asg \
  --launch-template "LaunchTemplateName=app-lt,Version=\$Latest" \
  --min-size 3 --max-size 30 --desired-capacity 6 \
  --vpc-zone-identifier "subnet-app-a,subnet-app-b,subnet-app-c" \
  --target-group-arns arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/app-tg/abc123 \
  --health-check-type ELB --health-check-grace-period 120

# Target tracking on requests per target
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name app-asg \
  --policy-name req-per-target \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/prod-alb/1234567890abcdef/targetgroup/app-tg/abc123"
    },
    "TargetValue": 1000
  }'

# Warm pool to reduce scale-out latency
aws autoscaling put-warm-pool --auto-scaling-group-name app-asg \
  --pool-state Stopped --min-size 2
```

**Important points:**

- Set min capacity so that losing one AZ still leaves enough instances (N-1).
- Fast scale-out depends on boot time: bake AMIs (Packer) instead of long user data scripts, and use warm pools.
- Scale on the metric that reflects load: request count or queue depth is often better than CPU.
- Don't forget limits: service quotas, subnet IP space, and downstream capacity (database connections).
- For Kubernetes, the same idea applies with HPA plus Cluster Autoscaler or Karpenter.

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md), [Scheduling, resources and autoscaling](../kubernetes/05-scheduling-resources-autoscaling.md).

**Interview-ready answer:**

> "I create the Auto Scaling group from a versioned launch template and spread it across at least three AZs, attached to the ALB target group with ELB health checks so unhealthy application instances are replaced. My main policy is target tracking, for example keeping requests per target or CPU around 60%, and I add predictive or scheduled scaling for known daily peaks and events. To scale out faster I use pre-baked AMIs and a warm pool, and I use a mixed instances policy with On-Demand plus Spot for cost. Minimum capacity is sized so the group survives losing an AZ. I also check quotas, subnet IPs and database connection limits, because scaling the web tier only helps if the dependencies can keep up."

</details>

<details><summary>Q14. [Intermediate] If you receive 10,000 requests, how does traffic flow through your architecture? <em>(asked in interview round)</em></summary>

**Answer:**

The 10,000 requests are spread at every layer: DNS and the CDN absorb and cache what they can, the load balancer distributes the rest across AZs and healthy targets, the application tier scales horizontally, and the data tier is protected by caching, connection pooling and read replicas.

**End-to-end flow:**

```text
10,000 client requests
        |
1. Route 53  -> resolves app.example.com to CloudFront (latency/failover routing)
        |
2. CloudFront edge locations (+ AWS WAF, Shield)
   - TLS terminated near the user
   - WAF blocks bad bots / rate-limits abusive IPs
   - Static and cacheable responses served from edge (e.g. 60-70% of requests)
        |
   ~3,000-4,000 dynamic requests
        |
3. Application Load Balancer (public subnets, AZ-a / AZ-b / AZ-c)
   - Listener rules: /api/* -> api target group, /* -> web target group
   - Health checks; cross-zone balancing; round robin or least outstanding requests
        |
4. Targets in private subnets
   - EC2 Auto Scaling group  OR  EKS: ALB -> Pods (AWS Load Balancer Controller, IP targets)
   - Each instance/Pod handles a share, e.g. 3,500 / 12 Pods ~ 290 each
        |
5. Application tier
   - Reads: ElastiCache (Redis) first -> cache hits return in ms
   - Writes / cache misses: RDS Proxy -> RDS Multi-AZ primary
   - Read-heavy queries: Aurora / RDS read replicas
   - Slow or async work: SQS -> worker Pods/Lambda
        |
6. Response returns: DB -> app -> ALB -> CloudFront (caches if allowed) -> user
```

**What happens as the load grows:**

| Layer | Scaling behavior |
| --- | --- |
| Route 53 / CloudFront | Global, scales automatically |
| WAF | Rate-based rules per IP protect the origin |
| ALB | Scales automatically; for sudden huge spikes, consider ALB pre-warming / LCU reservation |
| EC2 ASG | Target tracking on `ALBRequestCountPerTarget` or CPU adds instances across AZs |
| EKS | HPA adds Pods; Karpenter/Cluster Autoscaler adds nodes |
| Database | RDS Proxy pools connections; caching and read replicas reduce load; Aurora Serverless v2 or replica auto scaling for reads |
| Async | SQS buffers bursts so workers process at a steady rate |

**Example: EKS ingress for the API tier:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:111122223333:certificate/abc-123
    alb.ingress.kubernetes.io/healthcheck-path: /health/ready
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:111122223333:regional/webacl/api-waf/xyz
spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 80
```

With HPA on the `api` Deployment and Karpenter for nodes, a burst first increases Pods on existing nodes and then adds nodes in the AZs where Pods are Pending.

**Important points:**

- The numbers above are illustrative; the real split depends on cache hit ratio and request mix.
- The weakest link is usually the database (connections, locks), not the web tier; caching, RDS Proxy and async queues protect it.
- Readiness probes and ALB health checks ensure new instances/Pods only receive traffic once ready, and connection draining protects in-flight requests on scale-in.
- Observe the flow with CloudFront and ALB metrics (request count, 5xx, target response time), X-Ray/OpenTelemetry traces and RDS Performance Insights.

See also: [Three-tier architecture](../repetitive-questions/three-tier-architecture.md), [Kubernetes networking and traffic](../kubernetes/03-networking-and-traffic.md).

**Interview-ready answer:**

> "The requests first hit Route 53, which resolves our domain to CloudFront. At the edge, WAF filters malicious traffic and rate-limits abusive clients, and CloudFront serves cached and static content, so only the dynamic share reaches the origin. That goes to an ALB spread across three AZs, which routes by path to healthy targets: EC2 instances in an Auto Scaling group, or Pods in EKS using IP targets. The application reads from ElastiCache first and goes to RDS through RDS Proxy for writes and cache misses, with read replicas for heavy reads and SQS for asynchronous work. As load grows, target tracking or HPA adds instances or Pods, Karpenter adds nodes, and the database is protected by caching and connection pooling. Then the response returns along the same path, and we monitor it with ALB metrics, traces and database insights."

</details>

<details><summary>Q15. [Intermediate] How do you make RDS highly available? <em>(asked in interview round)</em></summary>

**Answer:**

High availability for RDS means surviving an instance or Availability Zone failure automatically. The main tool is **Multi-AZ**. Read replicas help with read scaling and disaster recovery but are not automatic HA by themselves. Backups and cross-region copies cover data loss and region failure.

**Options:**

| Option | How it works | Failover | Readable standby? |
| --- | --- | --- | --- |
| Multi-AZ DB instance | One primary plus one synchronous standby in another AZ | Automatic, typically 60 to 120 seconds; endpoint DNS moves to the standby | No |
| Multi-AZ DB cluster (MySQL, PostgreSQL) | One writer plus two readable standbys in three AZs, semi-synchronous replication | Automatic, typically under 35 seconds | Yes, through the reader endpoint |
| Read replicas | Asynchronous copies, same or different region | **Manual** promotion; possible data loss from lag | Yes |
| Aurora | Storage replicated six ways across three AZs; up to 15 replicas | Automatic, promotes a replica, usually about 30 seconds or less | Yes |

**Failover flow (Multi-AZ instance):**

```text
Clients --> mydb.abc123.us-east-1.rds.amazonaws.com (CNAME)
                   |
                   v
            Primary (AZ-a)  ==sync replication==>  Standby (AZ-b)
                   X  failure / AZ outage / reboot with failover / instance class change
                   |
            RDS flips the DNS record to the standby; standby becomes primary
                   |
Clients reconnect to the same endpoint --> new primary (AZ-b)
                   |
            RDS creates a new standby in another AZ
```

**Full HA and DR checklist:**

1. Enable Multi-AZ (or Multi-AZ DB cluster) for production.
2. Use a DB subnet group spanning at least two (or three) AZs.
3. Applications connect by endpoint name, use short DNS TTL caching and retry logic; RDS Proxy can reduce failover impact by holding connections.
4. Automated backups with point-in-time recovery (PITR), retention up to 35 days; restore creates a **new** instance.
5. Cross-region snapshot copy or cross-region automated backup replication, or a cross-region read replica for faster regional DR.
6. Deletion protection on, and a final snapshot on delete.
7. Monitoring: CloudWatch alarms and RDS event subscriptions for failover, plus `ReplicaLag` for replicas.
8. Test failover regularly.

**Example:**

```bash
# Convert to Multi-AZ (applied in maintenance window unless --apply-immediately)
aws rds modify-db-instance --db-instance-identifier orders-prod --multi-az --apply-immediately

# Test failover
aws rds reboot-db-instance --db-instance-identifier orders-prod --force-failover

# Subscribe to failover events
aws rds create-event-subscription --subscription-name rds-failover \
  --sns-topic-arn arn:aws:sns:us-east-1:123456789012:db-alerts \
  --source-type db-instance --event-categories failover availability
```

```hcl
resource "aws_db_instance" "orders" {
  identifier                = "orders-prod"
  engine                    = "postgres"
  instance_class            = "db.r6g.large"
  multi_az                  = true
  db_subnet_group_name      = aws_db_subnet_group.private.name
  backup_retention_period   = 14
  deletion_protection       = true
  storage_encrypted         = true
  manage_master_user_password = true
  # other required arguments omitted
}
```

**Important points:**

- A Multi-AZ instance standby cannot serve reads; use a Multi-AZ DB cluster, Aurora or read replicas for that.
- Read replicas are asynchronous; promotion is manual and may lose recent writes.
- Multi-AZ protects against AZ failure, not against bad data or accidental deletes; that is what PITR and snapshots are for.

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md).

**Interview-ready answer:**

> "For production I enable Multi-AZ, which keeps a synchronous standby in another Availability Zone. If the primary or its AZ fails, RDS automatically flips the endpoint DNS to the standby, usually within one to two minutes, and applications reconnect to the same endpoint with retry logic. Where I need faster failover and readable standbys, I use a Multi-AZ DB cluster or Aurora. Read replicas I use for read scaling and cross-region DR, but they are asynchronous and need manual promotion, so they are not HA by themselves. On top of that I enable automated backups with point-in-time recovery, copy snapshots to another region, turn on deletion protection, subscribe to failover events and test failover regularly."

</details>

<details><summary>Q16. [Advanced] How do you design highly available, auto-scalable infrastructure on AWS/Azure/GCP? <em>(asked in interview round)</em></summary>

**Answer:**

High availability means no single point of failure, and auto-scaling means capacity follows demand automatically. I design in layers and spread every layer across at least two (preferably three) availability zones.

**Design:**

```text
Users
  |
  v
DNS (Route 53 / Azure Front Door / Cloud DNS) + CDN + WAF
  |
  v
Load balancer (ALB / Application Gateway / Cloud Load Balancing) - multi-AZ
  |
  v
Compute in 3 AZs: Auto Scaling Group / VM Scale Set / Managed Instance Group
or Kubernetes (EKS / AKS / GKE) with HPA + Cluster Autoscaler or Karpenter
  |
  v
Stateless app; sessions in Redis; files in object storage
  |
  v
Managed database: Multi-AZ RDS/Aurora, Azure SQL zone-redundant, Cloud SQL HA
read replicas + automated backups + cross-region copies
```

**Steps:**

1. **Multi-AZ everywhere**: subnets, load balancers, compute and databases in at least two or three zones.
2. **Stateless compute**: keep state in managed services so any instance can be replaced.
3. **Auto-scaling**: scale on meaningful signals (CPU, request count per target, queue depth); set min capacity to survive a zone loss.
4. **Health checks**: the load balancer and scaling group replace unhealthy instances automatically.
5. **Managed, replicated data**: Multi-AZ databases, replicated storage, backups and point-in-time recovery.
6. **Decoupling**: queues (SQS, Service Bus, Pub/Sub) absorb spikes and isolate failures.
7. **Everything as code**: Terraform modules, immutable images, so environments can be rebuilt quickly.
8. **Multi-region** only when the RTO/RPO or regulation requires it; it adds cost and complexity.

**Example: AWS target tracking:**

```hcl
resource "aws_autoscaling_policy" "cpu" {
  name                   = "cpu-target-60"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"
  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 60
  }
}
```

**Important points:**

- N+1 per zone: with three zones, size so that two zones can carry peak load.
- Scaling takes minutes; use warm pools, pre-scaling for known events, or over-provision slightly.
- Test failure: terminate instances, fail over the database, and run game days.

See also: [AWS architecture and high availability](../aws/01-architecture-and-high-availability.md), [Azure VM scale sets and autoscale](../azure/08-vm-scale-sets-and-autoscale.md), [Three-tier architecture](../repetitive-questions/three-tier-architecture.md), [Scheduling, resources and autoscaling](../kubernetes/05-scheduling-resources-autoscaling.md)

**Interview-ready answer:**

> "I spread every layer across at least two, ideally three, availability zones, so a zone failure does not take the service down. Traffic enters through DNS, a CDN and WAF, then a zone-redundant load balancer in front of an Auto Scaling Group, VM Scale Set or Kubernetes cluster. The application is stateless, with sessions in Redis and files in object storage, so instances can be replaced or scaled freely. Scaling uses target tracking on CPU or request count, with minimum capacity sized to survive losing a zone. The database is a managed Multi-AZ service with backups and point-in-time recovery, and queues absorb spikes. Everything is defined in Terraform, and we regularly test failover so we know the design actually works."

</details>

<details><summary>Q17. [Advanced] Auto-scaling strategy in AWS for high-traffic apps. <em>(asked in interview round)</em></summary>

**Answer:**

Scale every tier, scale on the right signals, and keep the data tier from becoming the bottleneck.

| Tier | Approach |
| --- | --- |
| Edge | CloudFront caching, AWS WAF, Route 53 |
| Load balancing | ALB across at least three Availability Zones |
| Compute | EC2 Auto Scaling group with target tracking, or ECS / EKS with HPA plus Karpenter |
| Data | Aurora read replicas and Aurora Serverless v2, DynamoDB on-demand, ElastiCache |
| Async | SQS queues to absorb spikes; scale workers on queue depth |

Use target tracking on CPU or `ALBRequestCountPerTarget`, scheduled or predictive scaling for known peaks, warm pools for slow start-up, and load test to validate limits and service quotas.

```bash
aws autoscaling put-scaling-policy --auto-scaling-group-name web-asg \
  --policy-name rps-target --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ALBRequestCountPerTarget","ResourceLabel":"app/web/abc/targetgroup/web/def"},"TargetValue":800}'
```

**Interview-ready answer:**

> I design scaling per tier. CloudFront absorbs static and cacheable traffic, an ALB spreads requests across three AZs, and the compute layer uses target tracking on request count per target or CPU, plus scheduled or predictive scaling for known peaks. On EKS that is HPA for Pods and Karpenter for nodes. Spikes that do not need a synchronous answer go through SQS, and the data tier uses caching, read replicas or serverless capacity so it does not become the bottleneck. I validate it all with load tests and check service quotas in advance.

See also: [Design an auto-scaling strategy for a high-traffic app](../aws/01-architecture-and-high-availability.md), [Kubernetes autoscaling](../kubernetes/05-scheduling-resources-autoscaling.md)

</details>
