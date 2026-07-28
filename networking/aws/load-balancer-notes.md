# AWS Application Load Balancer vs. Network Load Balancer

An Application Load Balancer operates at Layer 7 for HTTP/HTTPS. It understands hosts, paths, headers, methods, redirects, WebSockets, target health, and can integrate with WAF and authentication.

I choose it for web applications, APIs, ingress-style routing, and multiple services behind one endpoint.

A Network Load Balancer operates at Layer 4 for TCP, TLS, and UDP. It is designed for very high throughput and low latency, preserves the source IP in supported modes, and provides static IP addresses or Elastic IPs.

I choose it for non-HTTP protocols, static-IP allowlists, or workloads that need Layer-4 behavior.

The choice also considers TLS termination location, target type, cross-zone behavior and cost, health checks, idle connections, client IP needs, security groups, private versus internet-facing exposure, logging/metrics, and zonal failure.

For troubleshooting I trace DNS → listener → rule → target group → target health and port → security group/NACL/route → application response, rather than assuming a healthy load-balancer resource means the application is reachable.
