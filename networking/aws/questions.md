# AWS Networking Interview Questions

### 1. How do you connect to an EC2 instance?

**Answer:**

My preferred way is over the private IP, through a VPN or bastion, or with AWS Systems Manager Session Manager — I avoid public SSH when I can. If SSH is approved:

```bash
chmod 600 key.pem
ssh -i key.pem -o IdentitiesOnly=yes ec2-user@host
```

The username depends on the AMI. The network path needs a route, and the security group/NACL/firewall needs to allow port 22, with `sshd` running on the instance. I check the host key, never share the private key, and use short-lived, certificate-based, or SSM access wherever possible.

**Failure steps:** check DNS/IP, run `nc -vz host 22`, check the security group/NACL/route, confirm the instance and `sshd` are up (via SSM or the console), run `ssh -vvv` for verbose output, and check user/key/`authorized_keys` permissions and the auth logs. I don't open `0.0.0.0/0` as a shortcut.

---

### 2. What are the main components of an AWS VPC?

**Answer:**

A VPC is an isolated network with one or more non-overlapping CIDR blocks. Subnets divide it up by availability zone and purpose.

Route tables decide the next hop for traffic. An Internet Gateway provides a path for public IPv4/IPv6 traffic. A NAT Gateway gives private subnets IPv4 outbound access. An egress-only Internet Gateway handles outbound-only IPv6. Security groups are stateful controls on network interfaces, while network ACLs are stateless controls at the subnet level.

Real-world designs also need DNS settings and Route 53 private zones, Elastic Network Interfaces and addresses, VPC endpoints/PrivateLink, load balancers, flow logs, DHCP options, and connectivity through peering, Transit Gateway, VPN, or Direct Connect.

A subnet is "public" because its route table sends traffic to an Internet Gateway and the resource in it has a public address — not simply because an Internet Gateway happens to exist somewhere in the VPC.

For high availability, I use multiple AZs, keep public and private subnets independent, apply least-privilege routing and security (giving only the access that's needed), control egress, turn on flow logs, and plan IP capacity ahead of time. I test both the forward and return paths, and avoid overlapping CIDRs that would block future connectivity.

---

### 3. How do you access an EC2 instance in a private subnet?

**Answer:**

My preferred option is AWS Systems Manager Session Manager, using an instance profile and either private SSM VPC endpoints or controlled egress. It avoids inbound SSH entirely, gives IAM/MFA control and audit logs, and doesn't require distributing private keys.

Where SSH is genuinely required, I connect through a corporate VPN/Direct Connect or an approved hardened bastion, using `ProxyJump`. The private instance's security group only allows port 22 from the bastion's security group or a specific admin CIDR.

I check the instance is healthy, the route and return path exist, NACLs allow the flow and the ephemeral return ports, the security group is correct, DNS resolves privately, and `sshd`/the host firewall and the user's key are valid. EC2 Instance Connect Endpoint is another controlled option where it's supported.

I never assign a public IP or open SSH to `0.0.0.0/0` just to troubleshoot. Access should be time-bound, least-privilege, logged, and removed once the issue is resolved.

---

### 4. Why can't you attach an Internet Gateway directly to a public subnet?

**Answer:**

An Internet Gateway attaches to the VPC as a whole, not to an individual subnet. A subnet becomes "public" when its route table sends internet-bound traffic (like `0.0.0.0/0`) to that Internet Gateway, and an instance or load balancer in it has a public IPv4/Elastic IP or the right IPv6 address.

Security groups and network ACLs still need to allow the traffic too.

This matters because several public subnets across different availability zones can all share the same VPC-level attachment while each has its own separate route-table association.

A route by itself doesn't translate a private IPv4 address into a public one. And an Internet Gateway doesn't create unsolicited access on its own — if the resource has no public address, or its security rules deny the traffic, the traffic still won't get through.

---

### 5. How can a server in a private subnet access the internet securely?

**Answer:**

For IPv4, the private subnet's route table normally sends `0.0.0.0/0` to a NAT Gateway sitting in a public subnet, and that public subnet in turn routes to the Internet Gateway.

I deploy a NAT Gateway per AZ, both for availability and to avoid cross-AZ traffic and its extra cost, and I check the server's security group, NACLs, DNS, the return path, and the NAT Gateway's health.

A self-managed NAT instance is possible, but it needs its own HA design, patching, packet forwarding, and source/destination-check setup.

For talking to other AWS services, I prefer gateway or interface VPC endpoints, so that traffic never has to cross the public internet or go through NAT at all. An egress firewall or proxy, DNS policy, allow-lists, TLS validation, flow logs, and least-privilege endpoint policies all help limit where traffic can actually go.

IPv6 uses an egress-only Internet Gateway for outbound-initiated access.

When troubleshooting, I test DNS, `ip route`, TCP/TLS, NAT Gateway metrics, route table associations, flow logs, and the actual response from the destination — testing from the affected subnet itself, not just from a public bastion.
