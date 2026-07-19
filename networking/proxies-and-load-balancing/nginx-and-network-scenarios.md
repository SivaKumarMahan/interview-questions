# Nginx and Network Troubleshooting Scenarios

Nginx can serve static content, reverse-proxy dynamic requests, balance traffic, terminate TLS, cache responses, compress content, enforce rate limits, add security headers, and operate as a Kubernetes ingress controller. Configuration changes should be validated with `nginx -t` and reloaded gracefully rather than restarting blindly.

## Website works by IP but not by hostname

Compare `dig`/`nslookup` with the expected address, test the FQDN and IP with the same protocol, and check local resolver/search configuration, DNS TTL/cache, split-horizon DNS, virtual-host `Host` routing, TLS SNI/certificate, and proxy configuration. Ping by IP only proves ICMP reachability; it does not validate DNS, TCP, TLS, or HTTP.

## Hosts in the same subnet cannot communicate

Verify address, prefix/mask, interface/link, VLAN, ARP/neighbor entries, host firewall, network ACL, and switch port. Capture ARP and ICMP on both hosts to see whether requests and replies leave. Duplicate addressing or an incorrect mask can make each host choose the wrong on-link behavior.

## Static route does not carry traffic

Check that the next hop is reachable through an active interface, the route is installed, longest-prefix selection chooses it, return routing exists, and no policy route, ACL, NAT, or security group blocks the flow. `ip route get <destination>`, traceroute, device route tables, and packet capture identify the hop where traffic stops.

## Server works on the LAN but not externally

Trace public DNS → public IP/NAT/load balancer → firewall → route → server listener and return path. Confirm health-probe source ranges and ports, default gateway, asymmetric routing, virtual-host/TLS configuration, and application health. Do not expose all sources/ports as a diagnostic shortcut.

## Application is slow: network or server?

Measure end-to-end latency and break it into DNS, connect, TLS, time to first byte, and download. Check loss/retransmission and path latency with `mtr`, interface errors/utilization, and packet capture, then compare server CPU, memory, I/O, connection pools, query and dependency latency, logs, and traces. Correlating one request across the path avoids blaming the network merely because it is between the user and server.

## One company site is down

Confirm scope, power and physical link, WAN circuit and provider status, tunnel/BGP/OSPF/static routes, firewall and DNS, and recent changes. Compare both directions and use the documented backup circuit only after verifying failover will not create loops or asymmetric filtering. Preserve provider and device evidence for the incident review.

## Duplicate IP addresses

Confirm the conflict through ARP/neighbor changes, switch MAC tables, DHCP logs, and packet capture. Isolate or readdress the incorrect device, clear stale neighbor state carefully, and verify the intended owner. DHCP reservations, IP address management, conflict detection, controlled static ranges, and switch security reduce recurrence.

