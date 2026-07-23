# Kubernetes Networking Summary

## 5. Services and Application Networking

### 5.1 Service Types

- **ClusterIP:** Stable internal virtual IP; the default Service type.
- **NodePort:** Exposes a port on every node and forwards to the Service.
- **LoadBalancer:** Requests an external or internal cloud load balancer.
- **ExternalName:** Returns a configured external DNS name.
- **Headless Service:** Uses `clusterIP: None` for direct endpoint discovery.

`port` is the Service port, `targetPort` is the destination Pod port, and `nodePort` is the optional port exposed on cluster nodes.

### 5.2 Ingress and DNS

Ingress defines HTTP/HTTPS routing rules and requires an Ingress controller. CoreDNS provides cluster DNS. Troubleshoot routing from the inside out: Pod readiness, endpoint slices, Service selectors and ports, DNS, Ingress rules/controller, then load balancer and firewall.

### 5.3 NetworkPolicy

`NetworkPolicy` restricts Pod ingress and egress when supported by the CNI plugin.

- With no selecting policy, traffic is allowed by default.
- A policy isolates a selected Pod only for the directions listed in `policyTypes` or inferred from its rules.
- To deny all egress, select the Pods, include `Egress` in `policyTypes`, and provide no allowed egress rules.

Use default-deny policies and add explicit allows for DNS and required application flows.

## Troubleshooting Network and 503 Failures

### Network or 503 Failure

Check Pod readiness, Service selectors, endpoint slices, `port`/`targetPort`, DNS, NetworkPolicies, Ingress controller logs, health probes, load balancer rules, routes, and firewalls.

## Service Types and External Access

A Service gives an ephemeral Pod set a stable virtual IP/DNS name and load-balances to ready endpoints selected by labels.

- `ClusterIP`: internal virtual IP and the default type.
- `NodePort`: exposes a static port on every node and forwards to the Service; useful for specific integrations or learning, but direct node exposure is rarely the preferred production entry point.
- `LoadBalancer`: asks the cloud integration to provision or attach an external/internal load balancer to the Service.
- `ExternalName`: returns a DNS CNAME and does not proxy traffic or perform health checking.

Ingress is an HTTP/HTTPS routing API that requires an Ingress controller such as **NGINX**, **Traefik**, or a cloud controller. It can consolidate host/path routing and TLS for multiple Services. A LoadBalancer Service is suitable for one application or L4 protocol; Ingress is suitable for shared L7 routing. Verify controller class, listener, certificate/SNI, host/path, Service port, EndpointSlice, readiness, health probes, and network policy.
