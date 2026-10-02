# AWS: Networking, Security, and IAM

> NAT gateways, security groups vs NACLs, IAM roles and users, secure S3 access, and IAM and secrets best practices.

## Key Concepts

### Internet Gateway vs. NAT Gateway

An **Internet Gateway (IGW)** attaches to a VPC and gives it a route target for internet traffic. A resource in a public subnet is only actually reachable from the internet if routing, a public IPv4/IPv6 address, security groups, network ACLs, and the service itself all allow it.

Typical public endpoints are internet-facing load balancers and deliberately exposed bastion hosts.

A **NAT Gateway** does source NAT for outbound IPv4 connections from private subnets. Private instances route their internet-bound traffic to the NAT Gateway, which reaches the internet through an IGW.

It does not accept unsolicited inbound connections back to those private instances. Design NAT Gateway placement and routing per Availability Zone, so you avoid depending on another AZ and paying its cross-AZ cost.

```text
Public workload: public subnet route -> IGW -> internet
Private egress:  private subnet route -> NAT Gateway -> IGW -> internet
```

Use **VPC endpoints** for supported AWS services when private access, tighter policy control, availability, or avoiding NAT cost makes it worthwhile. When troubleshooting, check the subnet route table, the NAT/IGW association, whether the address is public or private, the security group, the stateless network ACL's return ports, DNS resolution, and flow logs.

Having an IGW or NAT resource in place doesn't by itself prove that end-to-end connectivity actually works.

### Application Load Balancer vs. Network Load Balancer

An Application Load Balancer works at Layer 7, for HTTP/HTTPS. It understands hosts, paths, headers, methods, redirects, and WebSockets, checks target health, and can integrate with WAF and authentication.

I pick it for web applications, APIs, ingress-style routing, and cases where several services sit behind one endpoint.

A Network Load Balancer works at Layer 4, for TCP, TLS, and UDP. It's built for very high throughput and low latency, preserves the client's source IP in supported modes, and gives you static IP addresses or Elastic IPs.

I pick it for non-HTTP protocols, when clients need a fixed IP to allow-list, or when a workload specifically needs Layer-4 behavior.

Other things that factor into the choice: where TLS terminates, target type, cross-zone load balancing and its cost, health checks, idle connection timeouts, whether clients need to see the real source IP, security groups, whether the load balancer is internal or internet-facing, logging/metrics, and how it behaves if a zone fails.

To troubleshoot, I trace the path in order: DNS → listener → rule → target group → target health and port → security group/NACL/route → application response. A healthy load-balancer resource doesn't mean the application behind it is actually reachable.

### AWS Network Security

- **Networking:** private subnets for workloads, tight security groups that reference other security groups, NACLs, VPC endpoints, WAF and Shield at the edge, encryption in transit (TLS) and at rest (KMS), and flow logs plus GuardDuty and CloudTrail for detecting problems.

## Interview Questions

<details><summary>Q1. [Basic] What are the main components of an AWS VPC?</summary>

**Answer:**

A VPC is an isolated network with one or more non-overlapping CIDR blocks. Subnets divide it up by availability zone and purpose.

Route tables decide the next hop for traffic. An Internet Gateway provides a path for public IPv4/IPv6 traffic. A NAT Gateway gives private subnets IPv4 outbound access. An egress-only Internet Gateway handles outbound-only IPv6. Security groups are stateful controls on network interfaces, while network ACLs are stateless controls at the subnet level.

Real-world designs also need DNS settings and Route 53 private zones, Elastic Network Interfaces and addresses, VPC endpoints/PrivateLink, load balancers, flow logs, DHCP options, and connectivity through peering, Transit Gateway, VPN, or Direct Connect.

A subnet is "public" because its route table sends traffic to an Internet Gateway and the resource in it has a public address — not simply because an Internet Gateway happens to exist somewhere in the VPC.

For high availability, I use multiple AZs, keep public and private subnets independent, apply least-privilege routing and security (giving only the access that's needed), control egress, turn on flow logs, and plan IP capacity ahead of time. I test both the forward and return paths, and avoid overlapping CIDRs that would block future connectivity.

</details>

<details><summary>Q2. [Advanced] Design a VPC with subnets, security groups; explain networking (production) <em>(asked in interview round)</em></summary>

- **VPC** with a planned CIDR (e.g. `10.0.0.0/16`), spanning **at least 2 AZs** for high availability.
- **Subnets per AZ:** public (ALB/NAT), private-app (compute), private-data (RDS) — a 3-tier layout.
- **Routing:** public subnets route to the Internet Gateway; private subnets route to a **NAT Gateway** for outbound-only access (one per AZ, for HA). DB subnets get no internet route at all.
- **Security groups (stateful, per-instance):** the ALB's security group allows port 443 from the internet; the app's security group allows traffic **from the ALB's security group**; the DB's security group allows port 5432 **from the app's security group**. Reference other security groups, not raw CIDR ranges.
- **NACLs (stateless, per-subnet):** a coarser allow/deny layer on top of security groups.
- **Add-ons:** VPC endpoints (S3/ECR) to keep that traffic off the public internet, flow logs for auditing, and multi-AZ everywhere.

</details>

<details><summary>Q3. [Basic] Why can't you attach an Internet Gateway directly to a public subnet?</summary>

**Answer:**

An Internet Gateway attaches to the VPC as a whole, not to an individual subnet. A subnet becomes "public" when its route table sends internet-bound traffic (like `0.0.0.0/0`) to that Internet Gateway, and an instance or load balancer in it has a public IPv4/Elastic IP or the right IPv6 address.

Security groups and network ACLs still need to allow the traffic too.

This matters because several public subnets across different availability zones can all share the same VPC-level attachment while each has its own separate route-table association.

A route by itself doesn't translate a private IPv4 address into a public one. And an Internet Gateway doesn't create unsolicited access on its own — if the resource has no public address, or its security rules deny the traffic, the traffic still won't get through.

</details>

<details><summary>Q4. [Basic] How can a server in a private subnet access the internet securely?</summary>

**Answer:**

For IPv4, the private subnet's route table normally sends `0.0.0.0/0` to a NAT Gateway sitting in a public subnet, and that public subnet in turn routes to the Internet Gateway.

I deploy a NAT Gateway per AZ, both for availability and to avoid cross-AZ traffic and its extra cost, and I check the server's security group, NACLs, DNS, the return path, and the NAT Gateway's health.

A self-managed NAT instance is possible, but it needs its own HA design, patching, packet forwarding, and source/destination-check setup.

For talking to other AWS services, I prefer gateway or interface VPC endpoints, so that traffic never has to cross the public internet or go through NAT at all. An egress firewall or proxy, DNS policy, allow-lists, TLS validation, flow logs, and least-privilege endpoint policies all help limit where traffic can actually go.

IPv6 uses an egress-only Internet Gateway for outbound-initiated access.

When troubleshooting, I test DNS, `ip route`, TCP/TLS, NAT Gateway metrics, route table associations, flow logs, and the actual response from the destination — testing from the affected subnet itself, not just from a public bastion.

</details>

<details><summary>Q5. [Basic] What is a NAT Gateway, and where is it deployed?</summary>

**Answer:**

A NAT Gateway lets workloads in a private subnet make outbound IPv4 connections without accepting unsolicited traffic from the internet. It sits in a public subnet with an Elastic IP and a route to an Internet Gateway. Private subnet route tables send `0.0.0.0/0` traffic to it.

For resilience, I deploy one NAT Gateway per Availability Zone, and route each private subnet to the NAT Gateway in its own zone. Where possible, I use VPC endpoints for AWS services like S3 instead, to cut cost and reduce the dependency on internet access altogether.

</details>

<details><summary>Q6. [Basic] What is the difference between a security group and a network ACL?</summary>

**Answer:**

A security group is a stateful, allow-only firewall attached to a resource's network interface. Return traffic is automatically allowed, and rules can reference another security group.

A network ACL is a stateless boundary at the subnet level. It has ordered allow and deny rules, and you have to explicitly allow both inbound and outbound return traffic.

I use security groups for the normal application traffic path, scoped to only what's needed, and NACLs for coarse subnet-level guardrails or when I need an explicit deny. When troubleshooting, I check route tables, both directions of traffic, ephemeral ports, and the actual network interface or subnet involved — not just open everything up with `0.0.0.0/0`.

</details>

<details><summary>Q7. [Basic] How do you connect to an EC2 instance?</summary>

**Answer:**

My preferred way is over the private IP, through a VPN or bastion, or with AWS Systems Manager Session Manager — I avoid public SSH when I can. If SSH is approved:

```bash
chmod 600 key.pem
ssh -i key.pem -o IdentitiesOnly=yes ec2-user@host
```

The username depends on the AMI. The network path needs a route, and the security group/NACL/firewall needs to allow port 22, with `sshd` running on the instance. I check the host key, never share the private key, and use short-lived, certificate-based, or SSM access wherever possible.

**Failure steps:** check DNS/IP, run `nc -vz host 22`, check the security group/NACL/route, confirm the instance and `sshd` are up (via SSM or the console), run `ssh -vvv` for verbose output, and check user/key/`authorized_keys` permissions and the auth logs. I don't open `0.0.0.0/0` as a shortcut.

</details>

<details><summary>Q8. [Intermediate] How do you access an EC2 instance in a private subnet?</summary>

**Answer:**

My preferred option is AWS Systems Manager Session Manager, using an instance profile and either private SSM VPC endpoints or controlled egress. It avoids inbound SSH entirely, gives IAM/MFA control and audit logs, and doesn't require distributing private keys.

Where SSH is genuinely required, I connect through a corporate VPN/Direct Connect or an approved hardened bastion, using `ProxyJump`. The private instance's security group only allows port 22 from the bastion's security group or a specific admin CIDR.

I check the instance is healthy, the route and return path exist, NACLs allow the flow and the ephemeral return ports, the security group is correct, DNS resolves privately, and `sshd`/the host firewall and the user's key are valid. EC2 Instance Connect Endpoint is another controlled option where it's supported.

I never assign a public IP or open SSH to `0.0.0.0/0` just to troubleshoot. Access should be time-bound, least-privilege, logged, and removed once the issue is resolved.

</details>

<details><summary>Q9. [Basic] IAM role versus IAM user: when do you use each?</summary>

**Answer:**

An IAM role hands out temporary credentials to a workload, or to a federated human identity, and it can be assumed with narrowly scoped permissions. An IAM user is a long-lived AWS identity — it's really a legacy option now, only for the rare case where federation or roles genuinely don't work.

I use roles for EC2, Lambda, ECS/EKS workloads, CI, and human access through SSO. I require MFA and give every role only the permissions it needs. I avoid static access keys, rotate any I can't avoid, and review CloudTrail logs along with permission boundaries and SCPs.

</details>

<details><summary>Q10. [Intermediate] Security best practices for AWS IAM and secrets <em>(asked in interview round)</em></summary>

- **IAM:** Give every identity only the permissions it needs, nothing more. Prefer roles over long-lived keys. Use IAM roles for service accounts (IRSA) in EKS and OIDC for CI. Require MFA for humans. Avoid wildcard `*` policies. Use permission boundaries and SCPs in AWS Organizations. Rotate any access key you can't avoid using, and audit access with IAM Access Analyzer.
- **Secrets:** Keep them in Secrets Manager or SSM Parameter Store, never in code. Log and monitor everything.

</details>

<details><summary>Q11. [Intermediate] How do you grant an application access to an S3 bucket safely?</summary>

**Answer:**

I attach an IAM role to the workload — an EC2 instance profile, ECS task role, Lambda execution role, or EKS workload identity — and give it only the actions and prefix it actually needs. For example, `s3:GetObject` on `arn:aws:s3:::reports-bucket/approved/*`, and `s3:ListBucket` restricted by `s3:prefix`.

The bucket policy, IAM policy, permission boundary, SCP, VPC endpoint policy, and KMS key policy all have to allow the access — and an explicit deny anywhere wins over all of them.

I keep Block Public Access turned on unless there's a deliberate reason to serve public content, require TLS and encryption, audit CloudTrail data events where it matters, and test both an allowed operation and a denied one to make sure the policy actually works as intended.

</details>

<details><summary>Q12. [Intermediate] Secure an S3 bucket used for static website hosting <em>(asked in interview round)</em></summary>

- **Don't make the bucket public.** Serve it through CloudFront with Origin Access Control (OAC). Keep Block Public Access turned on, and only let CloudFront read from the bucket, through a bucket policy.
- **Force HTTPS.** Enforce it with a bucket policy condition (`aws:SecureTransport`), plus a CloudFront redirect-to-HTTPS rule and an ACM certificate.
- **Encrypt data at rest** (SSE-S3 or SSE-KMS), turn on **versioning** so you can recover from mistakes, and turn on **logging** (CloudTrail data events or S3 server access logs).
- Add **WAF** on CloudFront. Give IAM only the permissions it actually needs, and disable ACLs (bucket-owner-enforced). Nothing but the static assets should be reachable, and nothing should be writable from the public internet.

</details>
