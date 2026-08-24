# Networking Fundamentals Interview Questions

## 1. What happens when you enter a URL in a browser?

**Answer:**

The browser parses the URL, checks its own and the OS's caches, and resolves the hostname through the configured DNS resolver. It opens a TCP connection (or a QUIC connection for HTTP/3), validates the TLS certificate for HTTPS, then sends the HTTP request.

Along the way, DNS, a CDN, a WAF, a load balancer, or a reverse proxy may route the request to an application. That application may call caches, databases, and other services before it sends back a response. The browser then checks the response's security policy, fetches any resources it references, and renders the page.

When I troubleshoot this, I measure each step separately — DNS, connect, TLS, time to first byte, and asset loading — rather than treating "the website" as one single step.

## 2. TCP versus UDP: when would you use each?

**Answer:**

TCP is connection-oriented. It delivers data in order and reliably, and manages congestion and flow control itself. It's the normal choice for HTTP/1.1, HTTP/2, SSH, and database protocols.

UDP is connectionless and has less overhead, but it leaves reliability, ordering, and congestion handling up to the application. That makes it a good fit for DNS, voice/video, gaming, and QUIC/HTTP/3.

UDP isn't automatically faster — if an application has to rebuild reliability on top of it and does a poor job, it can end up slower. I choose based on what delivery guarantees are needed, how much latency the use case can tolerate, network conditions, and what the team can actually operate.

## 3. What is the usual DNS resolution order?

**Answer:**

The application or browser may check its own cache first, then the OS cache and local entries like `/etc/hosts` (the exact order is controlled by `nsswitch.conf` on Linux), before it queries the configured recursive resolver.

The resolver checks its own cache, and on a miss, walks from the root servers to the TLD servers to the authoritative server — or it hands the query off to a forwarder.

TTL controls how long an answer gets cached, and split-horizon DNS can intentionally return different answers depending on whether you're inside or outside a network. I verify all this with `getent hosts`, `dig`, the resolver configuration, TTL values, and by checking exactly which client network I'm testing from.

## 4. Forward proxy versus reverse proxy: what is the difference?

**Answer:**

A forward proxy sits in front of clients and represents them to the internet — commonly used for controlled egress, filtering, authentication, and caching. The client is explicitly configured to use it.

A reverse proxy sits in front of servers and represents them to clients. It terminates TLS, routes requests, load-balances, caches, and can apply a WAF or rate limits in front of the application.

Both can proxy HTTP, but they sit on opposite sides of the trust boundary and are owned by different parties. I preserve the real client's identity safely, using trusted forwarding headers, and set TLS, timeouts, and logging deliberately rather than by default.
