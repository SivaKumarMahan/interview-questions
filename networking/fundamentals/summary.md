# Networking Fundamentals Interview Summary

## 1. Troubleshooting model

Trace the real request in layers instead of guessing:

```text
name resolution → source address and route → firewall/ACL/NAT
→ TCP or UDP reachability → TLS → proxy/load balancer
→ service listener → application and dependency response
```

The OSI model is a useful way to organize evidence: physical/link, IP routing, transport, TLS/session, and application protocol. A successful `ping` only proves an ICMP path works. It says nothing about DNS, the TCP port, TLS, authentication, or whether the application is healthy.

## 2. IP addressing, CIDR, and subnets

An IP address identifies a network interface. The prefix length says how many bits represent the network — for example `10.20.4.0/24`.

A host treats anything inside its own subnet as directly reachable and uses ARP or neighbor discovery to find it. Anything outside the subnet goes through a route, usually the default gateway. Overlapping address ranges cause routing ambiguity in peering, VPN, container, and multi-cloud setups.

For IPv4, a `/24` has 256 total addresses, a `/26` has 64, and a `/30` has 4. Traditional (non-cloud) subnetting usually counts 254, 62, and 2 of those as usable host addresses. Cloud providers reserve a few extra addresses in every subnet, though, so always check the platform's actual rules before assuming a number is usable.

Pick non-overlapping ranges with room to grow — for load balancers, private endpoints, Kubernetes nodes and pods, and hybrid connectivity. CIDR planning affects VPC/VNet peering, VPNs, routing, firewalls, and any future merger. It's hard to fix overlapping networks after they're already connected.

## 3. Routing and NAT

Routers pick the most specific route that matches. When troubleshooting, always check both the forward and return path — an outbound packet that's allowed can still fail because of asymmetric routing or a missing return route.

NAT rewrites the source or destination address of a packet. A cloud NAT gateway normally lets a private subnet reach the internet outbound, but it does not create any inbound access.

## 4. TCP, UDP, and ports

TCP is connection-oriented and delivers data in order and reliably. A TCP connection starts with the **SYN, SYN-ACK, ACK** handshake, and you can watch its connection states and retransmissions.

UDP is datagram-based, with no connection or delivery guarantee at the transport layer, which is why it suits DNS, streaming, and other latency-sensitive protocols. A listening port just proves a process has bound a socket — it doesn't mean every network hop or the application itself is healthy.

## 5. DNS

DNS maps names to records through a chain: local cache/resolver, then recursive resolvers, then authoritative servers. Learn to tell `NXDOMAIN` (a real negative answer) apart from a timeout (something upstream is broken or unreachable).

Check the record type being requested, search domains, split-horizon or private zones, TTL/cache, upstream forwarding, and whether UDP and TCP port 53 are actually allowed through. Confirm the address you resolved is really the endpoint you meant, before you start troubleshooting the service itself.

## 6. Firewalls, security groups, and ACLs

Stateful controls remember a connection once it's allowed, and automatically allow its return traffic. Stateless ACLs check inbound and outbound packets separately — including the ephemeral return ports — since they don't track connection state.

Write rules with least privilege: only the source, destination, protocol, and port that's actually needed. Don't open everything as a shortcut. Use flow logs, packet capture, and counters to prove exactly which rule or hop is dropping the traffic.

## 7. Load balancers and proxies

Layer-4 load balancers route TCP/UDP connections. Layer-7 proxies understand HTTP itself — host, path, headers, redirects, cookies. Check the listener, certificate/SNI, routing rule, target group/endpoint, health-probe path, backend port, whether the source IP is preserved, timeouts, and the actual application response.

A healthy load-balancer resource with unhealthy or wrong backends still fails users.

## 8. Useful investigation commands

```bash
ip -br address
ip route
ip route get <destination>
ss -lntup
dig <name>
curl -vk https://<host>/health
nc -vz <host> <port>
traceroute <host>
mtr <host>
tcpdump -ni any host <address> and port <port>
```

Run these tests from the actual affected source network, and compare against a path that's known to work. After a targeted fix, confirm the real application transaction succeeds, remove any temporary access you granted, keep monitoring errors and latency, and write down the preventive control you added.
