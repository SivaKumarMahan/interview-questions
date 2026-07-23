# Docker Networking Interview Questions

### 1. How do you troubleshoot container DNS resolution failures?

**Answer:**

I determine whether failure affects one container, network, host, or all destinations. Inside the container I inspect `/etc/resolv.conf`, `getent hosts`, application error, and connectivity by IP vs. name. On host I check Docker network, embedded DNS (`127.0.0.11`), upstream DNS, routes/firewall, VPN, and daemon logs.

```bash
docker exec app cat /etc/resolv.conf
docker exec app getent hosts db.internal
docker network inspect appnet
```

I verify search domain, record type, TTL/stale cache, and network attachment. I avoid "fixing" by hardcoding IP. After correction I test intended and external names and monitor recurrence.

---

### 2. What strategies do you use for debugging container networking issues?

**Answer:**

I follow the packet path: application bind/listen → container network namespace/IP → Docker bridge/overlay → host routes/NAT/firewall → remote service/load balancer.

I inspect `docker ps`, port mappings, `docker inspect`, networks, listening sockets, DNS, routes, firewall, and packet capture when approved. I test from inside the source container and from host to separate layers.

Common causes are app bound to localhost, wrong published port, different networks, DNS, host firewall, overlapping CIDRs, MTU, or proxy. I make the smallest fix, retest both directions, verify application health, and codify network configuration.
