# Docker Networking Summary

Docker networking connects containers to each other, to the host, and to the outside world, while still keeping them isolated. On a typical Linux host, Docker creates a bridge interface called `docker0`. Containers get an address on that bridge's subnet, and outbound traffic normally goes through the host's NAT rules (`iptables` or `nftables`).

## Network Drivers

| Driver | What it's for |
| --- | --- |
| `bridge` | Single-host container networking. Prefer a user-defined bridge over the default one — it gives you proper isolation and lets containers find each other by name. |
| `host` | Shares the host's own network stack directly. No port mapping, and almost no isolation. Only use this when you have a specific, measured reason to. |
| `none` | No real network interface beyond loopback. Useful when a container should be fully isolated from the network. |
| `overlay` | Multi-host networking, used with Docker Swarm. |
| `macvlan` | Gives a container its own MAC address and IP on the physical network. Needs sign-off from the network team, and has some quirks around host-to-container communication. |
| `ipvlan` | Similar to macvlan — connects containers at layer 2/3 — but handles MAC addresses differently and scales differently. |

`EXPOSE 80` in a Dockerfile just documents which port the app uses. To actually reach it from outside the container, you publish it:

```bash
docker run -p 8080:80 image
```

This maps host port `8080` to container port `80`. Containers on the same user-defined network can reach each other by name — for example, `mysql:3306` — so avoid hardcoding a container's IP address anywhere in configuration; it can change.

## Best Practices

Give each application (or trust boundary) its own network. Publish only the ports you actually need, on the interfaces you intend. Avoid `--network host` unless you have a real reason. Use DNS names instead of IPs. Restrict inbound and outbound traffic with host or cloud firewall policy. Keep an eye on network and NAT connection capacity.

When troubleshooting, work through: `docker inspect` on the container, its network namespace routes and listening ports, Docker's DNS, the host firewall and NAT rules, port mappings, and — if needed — a packet capture on both the host and container side.
