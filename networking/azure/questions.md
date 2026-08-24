# Azure Networking Interview Questions

### 1. What is Azure Virtual Network?

**Answer:**

A VNet is an isolated network in Azure, with its own address space and subnets. Resources inside it talk to each other and to the outside world through routes, NSGs, peering, gateways, private endpoints, load balancers, and DNS.

I plan non-overlapping address ranges with room to grow, keep workload and security tiers separate, control routing and egress, and connect on-premises networks through VPN or ExpressRoute. Peering gives connectivity between two VNets, but it isn't transitive by default — a third VNet peered to one of them isn't automatically reachable.

When something's broken, I check DNS, effective routes, effective NSG rules, any firewall/NVA, peering/gateway status, service firewalls, and the application port. Network Watcher's connection troubleshoot tool and flow logs help pinpoint exactly where traffic is being dropped.

After any IaC change, I confirm both the traffic that should get through and the traffic that should be blocked behave as expected.

---

### 2. What is Azure Application Gateway?

**Answer:**

Application Gateway is a regional Layer-7 load balancer for HTTP/HTTPS. It handles host/path routing, TLS termination (or end-to-end TLS), health probes, session affinity, redirects, autoscaling, and can add a Web Application Firewall.

**Flow:** client → frontend IP/listener → routing rule → backend pool/HTTP setting → healthy backend. WAF policies inspect requests using managed or custom rules.

For a 502/503, I check the backend's health-check failure reason, DNS/IP, probe path/status, host header, certificate trust, port/protocol, NSG/routes, and whether the backend is actually ready. I compare access, performance, and firewall logs to narrow it down.

Once fixed, I test TLS, the routing paths, health checks, and latency, and confirm WAF is still doing its job — I don't disable protection broadly just to get things working again.

---

### 3. What is Azure DNS?

**Answer:**

Azure DNS hosts public DNS zones and records. Azure Private DNS handles internal resolution for VNets and private endpoints. Hosting DNS for a domain doesn't register that domain for you.

I delegate public zones by pointing the registrar's NS records at Azure, manage records through IaC, use sensible TTLs, and lock down who can change records. Private zones get linked to the VNets that need them, with records or zone groups set up for private endpoints.

A hybrid setup, where on-premises and Azure both need to resolve the same names, may need Azure DNS Private Resolver or DNS forwarders.

To troubleshoot, I use `dig`/`nslookup`, confirm which server is actually authoritative, check the record type, TTL/cache, the VNet link, forwarding rules, and the client's resolver settings. I query from both an internal and an external client, since split-horizon DNS is often deliberately giving different answers to each.

---

### 4. How do you connect Azure services privately?

**Answer:**

I use private endpoints to give supported PaaS services a private IP address inside a VNet, paired with private DNS that maps the service name to that IP. I then disable or restrict public network access, once I've confirmed everything still works.

App Service and Functions use VNet integration for outbound traffic; the private endpoint handles private inbound traffic where that's supported.

Service endpoints are a different, older option for some services and subnets — they still route to the service's public endpoint, so they aren't the same thing as Private Link.

I validate DNS resolution from the actual workload, the route, NSG/firewall rules, endpoint approval, the service's own configuration, and a real TCP/application connection. Hybrid clients also need DNS forwarding and a working VPN/ExpressRoute path. I test that public access is actually denied too, not just that private access works.

---

### 5. How do you secure Azure networking?

**Answer:**

I start by mapping out the data flows and trust boundaries. From there, the usual controls are: subnet segmentation, NSGs, user-defined routes, Azure Firewall or an NVA where traffic needs deep inspection, private endpoints, private DNS, restricted egress, DDoS Protection for exposed critical workloads, a WAF for HTTP applications, and keeping public IPs to a minimum.

Connectivity to on-premises goes over VPN or ExpressRoute, built with redundancy in mind.

I test from the real source, working layer by layer: DNS resolution, routing, effective NSG rules, firewall logs, service firewalls, private endpoint approval, and the application port. Network Watcher's connection troubleshoot tool and flow logs help find exactly where a connection is being denied.

Changes go through IaC and peer review. I turn on diagnostics, alert on unexpected public exposure, review rules regularly, and check both an allowed flow and one that's meant to be denied.
