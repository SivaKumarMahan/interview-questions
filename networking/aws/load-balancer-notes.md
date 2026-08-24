# AWS Application Load Balancer vs. Network Load Balancer

An Application Load Balancer works at Layer 7, for HTTP/HTTPS. It understands hosts, paths, headers, methods, redirects, and WebSockets, checks target health, and can integrate with WAF and authentication.

I pick it for web applications, APIs, ingress-style routing, and cases where several services sit behind one endpoint.

A Network Load Balancer works at Layer 4, for TCP, TLS, and UDP. It's built for very high throughput and low latency, preserves the client's source IP in supported modes, and gives you static IP addresses or Elastic IPs.

I pick it for non-HTTP protocols, when clients need a fixed IP to allow-list, or when a workload specifically needs Layer-4 behavior.

Other things that factor into the choice: where TLS terminates, target type, cross-zone load balancing and its cost, health checks, idle connection timeouts, whether clients need to see the real source IP, security groups, whether the load balancer is internal or internet-facing, logging/metrics, and how it behaves if a zone fails.

To troubleshoot, I trace the path in order: DNS → listener → rule → target group → target health and port → security group/NACL/route → application response. A healthy load-balancer resource doesn't mean the application behind it is actually reachable.
