# Nginx and Network Troubleshooting Scenarios

Nginx can serve static content, reverse-proxy dynamic requests, balance traffic across backends, terminate TLS, cache responses, compress content, enforce rate limits, add security headers, and act as a Kubernetes ingress controller.

Always validate a configuration change with `nginx -t` and reload it gracefully — don't just restart blindly.

## Website works by IP but not by hostname

Compare `dig`/`nslookup` output against the address you expect, test the FQDN and the IP using the same protocol, and check the local resolver/search settings, DNS TTL/cache, split-horizon DNS, the virtual host's `Host`-based routing, TLS SNI/certificate, and the proxy configuration.

Pinging the IP only proves ICMP reachability — it says nothing about DNS, TCP, TLS, or HTTP.

## Hosts in the same subnet cannot communicate

Check the address, prefix/mask, interface/link, VLAN, ARP/neighbor entries, host firewall, network ACL, and switch port. Capture ARP and ICMP traffic on both hosts to see whether requests actually leave and replies actually come back.

A duplicate address or a wrong mask can make a host pick the wrong on-link behavior.

## Static route does not carry traffic

Check that the next hop is reachable through an active interface, that the route is actually installed, that longest-prefix matching picks it over another route, that a return route exists, and that no policy route, ACL, NAT, or security group is blocking the flow.

`ip route get <destination>`, traceroute, the device's route table, and packet capture will show exactly where traffic stops.

## Server works on the LAN but not externally

Trace the path: public DNS → public IP/NAT/load balancer → firewall → route → server listener → return path. Check the health-probe source ranges and ports, the default gateway, asymmetric routing, virtual-host/TLS configuration, and application health.

Don't expose every source or port as a diagnostic shortcut.

## Application is slow: network or server?

Measure end-to-end latency and break it into DNS, connect, TLS, time to first byte, and download. Check for packet loss/retransmission and path latency with `mtr`, look at interface errors/utilization and packet captures, then compare server CPU, memory, I/O, connection pools, query and dependency latency, logs, and traces.

Follow one request across the whole path — don't blame the network just because it sits between the user and the server.

## One company site is down

Confirm the scope of the outage, check power and the physical link, the WAN circuit and provider status, tunnel/BGP/OSPF/static routes, the firewall and DNS, and any recent changes. Compare both directions of traffic, and only use the documented backup circuit after confirming the failover won't create a loop or asymmetric filtering.

Keep provider and device evidence for the incident review.

## Duplicate IP addresses

Confirm the conflict through ARP/neighbor table changes, switch MAC tables, DHCP logs, and packet capture. Isolate or re-address the wrong device, clear stale neighbor entries carefully, and confirm which device should actually own the address.

DHCP reservations, IP address management, conflict detection, controlled static ranges, and switch security all reduce how often this happens.
