# Proxies and Load Balancing Networking Interview Questions

### 1. A website starts returning HTTP 503. How do you investigate it?

**Answer:**

An HTTP 503 means some component in the path was reached, but it couldn't serve the request right now. First I capture the response headers/body to figure out whether the CDN, WAF, load balancer, reverse proxy, service mesh, or the application itself generated it.

I compare which hosts, paths, regions, users, and times are affected, and check for recent deployments, config changes, certificate changes, scaling events, or dependency incidents.

I trace the path: DNS → frontend listener/TLS → routing rule → target pool → health probe → backend listener/application → dependencies.

I look at the healthy-target count, the proxy's upstream status and timing, backend readiness, capacity, connection pools, queue depth, timeouts, retry amplification, rate limits, and logs/traces for the same request ID.

A healthy load-balancer resource with zero healthy targets still returns errors to users.

I restore service through a rollback, a traffic shift, added capacity, or a specific fix to routing/probe/backend/dependency. I don't open broad firewall rules or blindly increase every timeout.

Afterward I confirm sustained real-user traffic works, check p95/p99 latency, 5xx rate by source and backend, and failover behavior, and set up alerts for target loss, saturation (how close a resource is to its limit), and SLO burn.

### 2. What is an F5 iRule?

**Answer:**

An iRule is a small piece of event-driven Tcl code attached to BIG-IP's traffic processing. It can inspect or modify requests, pick a pool, redirect traffic, enforce policy, add headers, or make routing decisions at events like `HTTP_REQUEST`.

I keep iRules small, reviewed, version-controlled, and tested on a non-production virtual server, because a slow or incorrect rule sits directly in the data path. Native BIG-IP policy/profile configuration is preferable whenever it can do the job — custom code is for behavior the product can't express declaratively.

### 3. What are Virtual Servers, Pools, Pool Members and Nodes on F5 BIG-IP?

**Answer:**

A Virtual Server is the client-facing listener — its virtual IP, port, and profiles. It forwards traffic to a Pool, which is a logical set of backend targets plus its health-check and load-balancing policy.

A Pool Member is a specific service endpoint, usually an address plus a port, such as `10.0.1.20:8443`. A Node is the underlying IP address, and it can host more than one pool member.

I troubleshoot in this order: listener/TLS/rules first, then pool availability and monitor results, then member port/application health, and finally node/network reachability.

### 4. Which load-balancing methods would you use and what are their trade-offs?

**Answer:**

Round robin spreads requests evenly, which works well when each request costs about the same. Least connections works better when connection duration varies; weighted versions of either handle backends with unequal capacity.

Fastest/least-response-time methods can adapt to a slow backend, but only if the measurements behind them are trustworthy. Hash or consistent-hash methods give you affinity for caches or session state, while source-IP persistence is simpler but can create imbalance when clients sit behind NAT.

I prefer stateless applications with explicit session storage where possible. I only add persistence when it's genuinely required, and I combine it with health checks, slow-start/connection draining, and capacity-aware weights.

### 5. Layer 4 versus Layer 7 load balancers: what is the difference?

**Answer:**

Layer 4 balances TCP or UDP traffic based on IP address and port. It's less aware of the application, but usually faster and lower-latency. Layer 7 understands application protocols like HTTP, so it can route by host, path, header, cookie, or method. It can also terminate TLS, apply WAF/authentication, rewrite requests, and give you richer metrics.

I use Layer 4 for protocol-agnostic or very high-throughput transport, and Layer 7 for web/API traffic that needs content-aware routing and policy. Either way, you still need health checks, connection draining, timeouts, and good observability.
