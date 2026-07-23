# Docker Networking Summary

Docker networking connects containers to each other, the host, external networks, and the internet while providing isolation. On a typical Linux host Docker creates a bridge such as `docker0`; containers receive addresses in its subnet and outbound traffic commonly uses host NAT/`iptables` or `nftables` rules.

## Drivers

- **`bridge`:** single-host container networking. Prefer a user-defined bridge because it provides scoped isolation and container-name DNS.
- **`host`:** shares the host network namespace; no port NAT and little isolation. Use only with a measured requirement.
- **`none`:** no normal network interface beyond loopback; useful for isolated work.
- **`overlay`:** multi-host network used with Swarm.
- **`macvlan`:** gives a container a distinct MAC/address on the physical network; requires network-team design and has host-communication caveats.
- **`ipvlan`:** similar L2/L3 integration with different MAC behavior and scaling properties.

`EXPOSE 80` documents the application port.

```bash
docker run -p 8080:80 image
```

The command above publishes host port `8080` to container port `80`. Containers on the same user-defined network communicate using DNS names such as `mysql:3306`; fixed container IPs should not be embedded in configuration.

## Best Practices

Best practices are separate networks per application/trust boundary, publish only required ports on intended interfaces, avoid `--network host` unless necessary, use DNS names, restrict egress/ingress with host/cloud policy, and monitor network and NAT capacity. Troubleshoot with container inspect, namespace routes/listeners, Docker DNS, host firewall/NAT, port mappings, and packet capture on both host and container paths.
