# Networking Fundamentals Interview Questions

## 1. What happens when you enter a URL in a browser?

**Answer:**

The browser parses the URL, checks browser/OS caches and resolves the hostname through the configured resolver. It opens a TCP connection (or QUIC for HTTP/3), performs TLS certificate validation for HTTPS, then sends an HTTP request. DNS/CDN/WAF/load balancer/reverse proxy may route it to an application, which can call caches, databases and other services before a response returns. The browser validates response security policy, fetches referenced resources and renders the page. In troubleshooting I measure each boundary—DNS, connect, TLS, time to first byte and asset loading—rather than assuming “the website” is one step.

## 2. TCP versus UDP: when would you use each?

**Answer:**

TCP is connection-oriented and provides ordered, reliable byte delivery with congestion and flow control; it is the normal choice for HTTP/1.1, HTTP/2, SSH and database protocols. UDP is connectionless and has lower protocol overhead but leaves reliability, ordering and congestion behavior to the application; it suits DNS, voice/video, gaming and QUIC/HTTP/3. UDP is not inherently faster for an application that must rebuild reliability poorly. I choose based on delivery semantics, latency tolerance, network conditions and operational support.

## 3. What is the usual DNS resolution order?

**Answer:**

The application/browser may check its own cache, then the operating-system cache and local mappings such as `/etc/hosts` (exact order is controlled by `nsswitch.conf` on Linux), then query configured recursive resolvers. The resolver checks its cache and, on a miss, walks root, TLD and authoritative servers or uses forwarders. TTL controls caching, and split-horizon DNS can intentionally return different answers inside and outside a network. I verify with `getent hosts`, `dig`, resolver configuration, TTL and the exact client network.

## 4. Forward proxy versus reverse proxy: what is the difference?

**Answer:**

A forward proxy represents clients to the internet, commonly for controlled egress, filtering, authentication and caching; a client is configured to use it. A reverse proxy represents servers to clients, terminating TLS, routing, load balancing, caching and applying WAF/rate limits in front of applications. They can both proxy HTTP, but their trust boundary and ownership differ. I preserve client identity safely using trusted forwarding headers and configure TLS, timeouts and logs deliberately.
