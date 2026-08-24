# AWS Networking Summary

## Internet Gateway vs. NAT Gateway

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
