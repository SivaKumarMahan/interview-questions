# Docker Networking Interview Questions

### 1. How do you troubleshoot container DNS resolution failures?

**Answer:**

First I figure out the scope: is it one container, one network, the whole host, or every destination? Inside the container, I check `/etc/resolv.conf`, run `getent hosts`, look at the application's own error, and test whether connecting by IP works even when connecting by name doesn't.

On the host, I check the Docker network, Docker's embedded DNS server (`127.0.0.11`), the upstream DNS server, routes and firewall rules, any VPN, and the daemon logs.

```bash
docker exec app cat /etc/resolv.conf
docker exec app getent hosts db.internal
docker network inspect appnet
```

I also check the search domain, the DNS record type, whether a stale cache (TTL) is the culprit, and which network the container is actually attached to. I avoid "fixing" this by hardcoding an IP address — that just hides the real problem. Once I fix it, I re-test both the intended hostname and an external one, and keep an eye out for it recurring.

### 2. What strategies do you use for debugging container networking issues?

**Answer:**

I follow the path a packet actually takes: the app binding to a port inside the container → the container's own network namespace and IP → Docker's bridge or overlay network → the host's routes, NAT, and firewall → the remote service or load balancer.

Along the way I check `docker ps` and its port mappings, `docker inspect`, the networks involved, what's actually listening, DNS, routes, firewall rules, and — when it's approved — a packet capture. I test both from inside the source container and from the host, to narrow down which layer is broken.

The usual culprits: the app is bound to `localhost` instead of `0.0.0.0`, the wrong host port was published, the containers are on different networks, DNS isn't resolving, the host firewall is blocking traffic, two networks have overlapping IP ranges, MTU is misconfigured, or a proxy is in the way. I make the smallest fix that addresses the real cause, re-test in both directions, confirm the app is healthy, and write the working network configuration down so it doesn't get lost.
