# AWS Networking Interview Notes

### 7.3 Design a VPC with subnets, security groups; explain networking (production)

- **VPC** with a planned CIDR (e.g. `10.0.0.0/16`), spanning **at least 2 AZs** for high availability.
- **Subnets per AZ:** public (ALB/NAT), private-app (compute), private-data (RDS) — a 3-tier layout.
- **Routing:** public subnets route to the Internet Gateway; private subnets route to a **NAT Gateway** for outbound-only access (one per AZ, for HA). DB subnets get no internet route at all.
- **Security groups (stateful, per-instance):** the ALB's security group allows port 443 from the internet; the app's security group allows traffic **from the ALB's security group**; the DB's security group allows port 5432 **from the app's security group**. Reference other security groups, not raw CIDR ranges.
- **NACLs (stateless, per-subnet):** a coarser allow/deny layer on top of security groups.
- **Add-ons:** VPC endpoints (S3/ECR) to keep that traffic off the public internet, flow logs for auditing, and multi-AZ everywhere.

## AWS Network Security

- **Networking:** private subnets for workloads, tight security groups that reference other security groups, NACLs, VPC endpoints, WAF and Shield at the edge, encryption in transit (TLS) and at rest (KMS), and flow logs plus GuardDuty and CloudTrail for detecting problems.
