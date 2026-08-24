# Kubernetes Networking Summary

## 5. Services and Application Networking

### 5.1 Service Types

- **ClusterIP:** A stable internal IP. This is the default Service type.
- **NodePort:** Opens a port on every node and forwards it to the Service.
- **LoadBalancer:** Asks the cloud provider for an external or internal load balancer.
- **ExternalName:** Returns a configured external DNS name.
- **Headless Service:** Uses `clusterIP: None` so clients can discover endpoints directly.

`port` is the Service's own port. `targetPort` is the port on the destination pod. `nodePort` is the optional port exposed on cluster nodes.

### 5.2 Ingress and DNS

Ingress defines HTTP/HTTPS routing rules and needs an Ingress controller to work. CoreDNS provides DNS inside the cluster.

When routing breaks, troubleshoot from the inside out: pod readiness, endpoint slices, Service selectors and ports, DNS, Ingress rules/controller, then the load balancer and firewall.

### 5.3 NetworkPolicy

`NetworkPolicy` restricts what traffic a pod can send or receive, as long as the CNI plugin supports it.

- With no policy selecting a pod, all traffic is allowed by default.
- A policy isolates a pod only in the directions listed in `policyTypes`, or implied by its rules.
- To block all egress from a pod, select it, include `Egress` in `policyTypes`, and add no allowed egress rules.

Best practice: start with default-deny policies, then add explicit allows for DNS and whatever application traffic is actually needed.

## Troubleshooting Network and 503 Failures

When you see a network failure or a 503, check in this order: pod readiness, Service selectors, endpoint slices, `port`/`targetPort`, DNS, NetworkPolicies, Ingress controller logs, health probes, load balancer rules, routes, and firewalls.

## Service Types and External Access

A Service gives a changing set of pods one stable virtual IP and DNS name, and load-balances traffic to whichever pods are ready, based on label selectors.

- `ClusterIP`: an internal-only virtual IP, and the default type.
- `NodePort`: opens a fixed port on every node and forwards it to the Service. Useful for specific integrations or for learning, but exposing nodes directly is rarely the right choice in production.
- `LoadBalancer`: asks the cloud integration to provision or attach an external or internal load balancer to the Service.
- `ExternalName`: returns a DNS CNAME. It doesn't proxy traffic or do any health checking.

Ingress is an HTTP/HTTPS routing API. It needs an Ingress controller such as **NGINX**, **Traefik**, or a cloud-provided controller to actually work. It can bring host/path routing and TLS for many Services together in one place.

Use a LoadBalancer Service for one application or one Layer-4 protocol. Use Ingress when you need shared Layer-7 routing across several Services. When something's wrong, check the controller class, listener, certificate/SNI, host/path rules, Service port, EndpointSlice, readiness, health probes, and network policy.
