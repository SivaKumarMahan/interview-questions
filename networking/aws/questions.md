# AWS Networking Interview Questions

### 1. How do you connect to an EC2 instance?

**Answer:**

Preferred access is private IP via VPN/bastion or AWS Systems Manager Session Manager, avoiding public SSH. If SSH is approved:

```bash
chmod 600 key.pem
ssh -i key.pem -o IdentitiesOnly=yes ec2-user@host
```

Username depends AMI. Network path requires route, security group/NACL/firewall port 22 and `sshd`. I verify host key, never share private key, and use short-lived/certificate/SSM access where possible.

**Failure steps:** DNS/IP, `nc -vz host 22`, SG/NACL/route, instance/`sshd` via SSM/console, `ssh -vvv`, user/key/`authorized_keys` permissions and auth logs. I do not open `0.0.0.0/0` as a shortcut.

---

### 2. What are the main components of an AWS VPC?

**Answer:**

A VPC is an isolated IP network with one or more non-overlapping CIDR blocks. Subnets divide it by availability zone and purpose.

Route tables determine the next hop; an Internet Gateway supports public IPv4/IPv6 paths, NAT Gateway provides IPv4 egress for private subnets, and an egress-only Internet Gateway handles outbound-only IPv6. Security groups are stateful controls on ENIs, while network ACLs are stateless subnet controls.

Real designs also include DNS settings and Route 53 private zones, Elastic Network Interfaces and addresses, VPC endpoints/PrivateLink, load balancers, flow logs, DHCP options, and connectivity through peering, Transit Gateway, VPN, or Direct Connect.

A subnet is "public" because its route table has an Internet Gateway route and the resource has a suitable public address—not because the subnet has an Internet Gateway attached to it.
For high availability I use multiple AZs, independent public/private subnets, least-privilege (minimum required access) routing and security, controlled egress, flow logs, and IP-capacity planning. I test forward and return paths and avoid overlapping CIDRs that block future connectivity.
---

### 3. How do you access an EC2 instance in a private subnet?

**Answer:**

My preferred option is AWS Systems Manager Session Manager using an instance profile and private SSM VPC endpoints or controlled egress. It avoids inbound SSH, provides IAM/MFA control and audit logs, and does not require distributing private keys.

Where SSH is required, I connect through corporate VPN/Direct Connect or an approved hardened bastion and use `ProxyJump`; the private instance security group allows port 22 only from the bastion security group or administration CIDR.

I verify the instance is healthy, the route and return path exist, NACLs permit the flow and ephemeral return ports, the security group is correct, DNS resolves privately, and `sshd`/host firewall and user key are valid. EC2 Instance Connect Endpoint is another controlled option where supported.
I never assign a public IP or open SSH to `0.0.0.0/0` merely to troubleshoot. Access is time-bound, least privilege (only the permissions needed), logged, and removed after recovery.

---

### 4. Why can't you attach an Internet Gateway directly to a public subnet?

**Answer:**

An Internet Gateway attaches to a VPC, not to an individual subnet. A subnet becomes public when its associated route table sends internet destinations such as `0.0.0.0/0` to that VPC's Internet Gateway and an instance/load balancer has a public IPv4/Elastic IP or appropriate IPv6 address.

Security groups and network ACLs must also allow the traffic.

This distinction matters because multiple public subnets across availability zones share the VPC attachment but have their own route-table associations.

A route alone does not translate a private IPv4 address into a public one, and an Internet Gateway does not create unsolicited access when the resource lacks a public address or its security policy denies traffic.
---

### 5. How can a server in a private subnet access the internet securely?

**Answer:**

For IPv4, the private subnet route table normally sends `0.0.0.0/0` to a NAT Gateway in a public subnet; that public subnet routes to the Internet Gateway.

I deploy NAT capacity per AZ for availability and to avoid cross-AZ dependency/cost, and I confirm the server's security group, NACLs, DNS, return path, and NAT health.

A self-managed NAT instance is possible but requires explicit HA, patching, forwarding, and source/destination-check design.

For AWS services I prefer gateway or interface VPC endpoints so traffic need not traverse public internet or NAT. Egress firewall/proxy, DNS policy, allowlists, TLS validation, flow logs, and least-privilege (minimum required access) endpoint policies limit destinations.

IPv6 uses an egress-only Internet Gateway for outbound-initiated access.

During troubleshooting I test DNS, `ip route`, TCP/TLS, NAT metrics, route associations, flow logs, and the destination response from the affected subnet rather than only from a public bastion.
