# Proxies and Load Balancing Networking Interview Questions

### 1. A website starts returning HTTP 503. How do you investigate it?

**Answer:**

An HTTP 503 means some HTTP component was reached but is temporarily unable to serve the request. I first capture response headers/body and determine whether CDN, WAF, load balancer, reverse proxy, service mesh, or application generated it.

I compare affected hosts, paths, regions, users, and times and check recent deployments, configuration, certificates, scaling, and dependency incidents.

I trace DNS → frontend listener/TLS → routing rule → target pool → health probe → backend listener/application → dependencies.

I inspect healthy-target count, proxy upstream status and timing, backend readiness, capacity, connection pools, queue depth, timeouts, retry amplification, rate limits, and logs/traces for the same request ID.

A healthy load-balancer resource with zero healthy targets still returns errors.

I restore service through rollback, traffic shift, capacity, or the specific routing/probe/backend/dependency fix. I do not open broad firewall rules or increase every timeout blindly.

I verify sustained real-user-path traffic, p95/p99 latency, 5xx by source/backend, failover, and alerts for target loss, saturation (how close a resource is to its limit), and SLO burn.

### 2. What is an F5 iRule?

**Answer:**

An iRule is event-driven Tcl code attached to BIG-IP traffic processing. It can inspect or modify requests, choose pools, redirect traffic, enforce policy, add headers or make routing decisions at events such as `HTTP_REQUEST`.

I keep iRules small, reviewed, version-controlled and tested in a non-production virtual server because an inefficient or incorrect rule affects the data path. Native BIG-IP policy/profile configuration is preferable when it meets the need; custom code is for behavior the product cannot express declaratively.

### 3. What are Virtual Servers, Pools, Pool Members and Nodes on F5 BIG-IP?

**Answer:**

A Virtual Server is the client-facing listener—virtual IP, port and profiles. It forwards to a Pool, which is a logical set of backend targets and its health/load-balancing policy.

A Pool Member is a specific service endpoint, normally address plus port, such as `10.0.1.20:8443`. A Node is the underlying IP address and may host one or more pool members.

I troubleshoot in that order: listener/TLS/rules, pool availability and monitor result, member port/application health, then node/network reachability.

### 4. Which load-balancing methods would you use and what are their trade-offs?

**Answer:**

Round robin distributes evenly when requests cost about the same. Least connections works better when connection duration varies; weighted variants handle unequal capacity.

Fastest/least response time can adapt to slow backends but depends on trustworthy measurements. Hash or consistent-hash methods provide affinity for caches or state, while source-IP persistence is simpler but can create imbalance behind NAT.

I prefer stateless applications and explicit session storage; persistence is chosen only when required and combined with health checks, slow-start/draining and capacity-aware weights.

### 5. Layer 4 versus Layer 7 load balancers: what is the difference?

**Answer:**

Layer 4 balances TCP or UDP based on IP address and port, usually with lower protocol awareness and latency. Layer 7 understands application protocols such as HTTP and can route by host, path, header, cookie or method; it can also terminate TLS, apply WAF/authentication, rewrite requests and provide richer metrics.

I use L4 for protocol-agnostic or very high-throughput transport needs, and L7 for web/API traffic that needs content-aware routing and policy. Either needs health checks, connection draining, timeouts and observability.
