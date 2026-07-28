## 1. Your Ingress controller crashes repeatedly under heavy load. How do you stabilize it?

**Answer:**

I protect traffic by rollback/config revert, scale healthy replicas, or shift traffic. I inspect current/previous logs, termination/OOM, CPU/memory/throttling, connection/request metrics, reload count, TLS/WAF/log overhead, upstream latency, node pressure and load-balancer health.
I ensure multiple replicas across zones, PDB, realistic resources, HPA on CPU/requests/connections, dedicated nodes if needed, optimized config and controlled reload rate. Large cert/rule sets or excessive access logging/tracing may cause load; backend slowness can accumulate connections.
I load-test peak plus failure, validate P95/error/connection/reset/reload metrics, then add capacity forecast and config validation/canary. Scaling controller does not fix saturated backend.

## 2. During peak traffic, Ingress fails to route requests efficiently. How do you diagnose and scale it?

**Answer:**

I break latency/error into edge/load balancer, Ingress controller, Service/endpoints and backend. I compare request rate, 4xx/5xx, controller vs. upstream latency, active connections/queue, TLS, retries/timeouts, reloads, Pod/node resources, readiness and endpoint count.
I verify routing rule/host/path and test directly to Service. Mitigation may scale controller/backends, add capacity/headroom, rollback route/config, rate limit, or shift traffic.

Tuning buffers/timeouts occurs from evidence because overly long timeout worsens connection exhaustion.

Afterward I load-test, configure HPA/zone spreading/PDB, monitor saturation (how close a resource is to its limit) and ensure cloud LB distributes to ready controller Pods/nodes. Synthetic tests cover key host/path.

## 3. How do you troubleshoot 503 errors from a LoadBalancer?

**Answer:**

503 usually means request reached gateway/LB but no healthy backend or upstream failed. I identify which layer generated response from headers/logs.

Then verify LB provisioning/backend health/probe, Service selector/ports, EndpointSlices, Pod readiness, application listening address/port, Ingress route and network/firewall.

```bash
kubectl get svc,endpointslice,pods -o wide
kubectl describe svc <svc>
kubectl logs <ingress-controller> --since=15m
```

I test Pod IP, Service DNS, Ingress/LB in order. Fix selector/port/probe/network/app or rollback release, then validate external request and metrics. Prevention includes smoke/synthetic test, config validation and alert on healthy backend count.

## 4. Case: Pod is not accessible internally. How do you troubleshoot?

**Answer:**

I clarify access by Pod IP or Service and source namespace. I check Pod Running/Ready, application logs/listening on `0.0.0.0:<targetPort>` not localhost, Service selector/port/targetPort, EndpointSlices and DNS.

From debug Pod I test DNS → Service IP/port → direct Pod IP/port. If direct works but Service fails, inspect selector/endpoints/data plane.

If both fail, inspect app bind, NetworkPolicy, CNI/routes/security group/node firewall. If DNS only fails, inspect CoreDNS/policy.

I capture exact error (timeout/refused/NXDOMAIN), fix one layer, and retest from original source plus readiness/user flow. I remove debug Pods afterward.

## 5. Case: Pod is internally accessible but LoadBalancer fails. What do you check?

**Answer:**

Internal success proves Pod/app partially. I check LoadBalancer Service events/status/external address, cloud LB/backend/target health, probe path/port/protocol/host, Service `port`/`targetPort`/`nodePort`, `externalTrafficPolicy`, node/Pod readiness and cloud security group/firewall/routes.
I test Service from cluster, node/health endpoint as LB sees it, and external path. Controller/cloud-provider logs and cloud activity show provisioning/permission/quota errors.

Source IP preservation can make `Local` policy unhealthy on nodes without local endpoints.

I correct probe/network/ports/annotation or roll back, wait for reconciliation (making actual state match desired state), verify multiple zones/backends, external TLS/request and monitoring. I do not expose broader firewall as a permanent workaround.

## 6. How do you debug DNS failures inside Kubernetes?

**Answer:**

I determine cluster Service name vs. external, one Pod/node/namespace vs. clusterwide, NXDOMAIN vs. timeout. From debug Pod: inspect `/etc/resolv.conf`, `nslookup/dig` short and FQDN, query kube-dns Service IP directly.

Check CoreDNS replicas/readiness/logs/metrics/config, Service/endpoints, NetworkPolicy UDP/TCP 53, CNI and upstream resolver/node DNS.

High latency may be ndots/search amplification, overloaded CoreDNS or upstream. I mitigate by scaling/fixing CoreDNS or reverting config, not hardcoded `/etc/hosts`.

I validate internal Service, external name, TCP fallback/large response, and monitor DNS error/latency. NodeLocal DNSCache may help scale after measured analysis.

## 7. How do you troubleshoot Pod-to-Pod networking issues?

**Answer:**

I map source/destination Pods, nodes, IPs, port/protocol and exact failure. Test same-node vs. cross-node direct Pod IP, then Service; use `nc/curl` and packet capture only with approval.

Check app listening, NetworkPolicy both ingress/egress including namespace labels, CNI Pods/logs/IP allocation, node routes/MTU/firewall/security groups, and eBPF/kube-proxy.

Same-node success/cross-node failure points to CNI overlay/routes/MTU/firewall. Direct IP success/Service failure points endpoints/data plane. Timeout vs. refusal provides clues.

After fix I test required allowed flow and denied flow, multiple nodes/zones, and monitor packet drops. Network configuration is codified.

## 8. How do you design and debug NetworkPolicies between namespaces?

**Answer:**

I inventory flows, ensure CNI enforces NetworkPolicy, label namespaces reliably, apply default-deny ingress/egress, then explicit DNS and application allows. A rule may combine `namespaceSelector` and `podSelector` to require both.

I roll out in audit/staging where tooling supports, use connectivity tests from allowed and denied namespaces, and check policy selection (`podSelector` labels), `policyTypes`, port/protocol, namespace labels, return traffic/statefulness and DNS.

For failure I compare direct IP, inspect policies selecting source/destination and CNI policy logs/drop counters. I avoid deleting all policies; add narrow temporary diagnostic allow with expiry if approved.

Validation proves least privilege (only the permissions needed) and required health/monitoring flows.

## 9. How do you restrict communication between two Pods in the same namespace?

**Answer:**

Without policy, Pods are generally non-isolated. I label workloads, apply default deny, then allow target ingress only from approved source label and port; source egress must also allow destination if egress-isolated.

```yaml
spec:
  podSelector: { matchLabels: { app: database } }
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector: { matchLabels: { app: api } }
    ports: [{ protocol: TCP, port: 5432 }]
```

I confirm CNI enforcement and test API→DB allowed, unrelated Pod→DB denied, DNS/monitoring still work. Labels are security inputs and protected by admission/governance. I monitor denied flows where supported and keep policies versioned.

## 10. How would you connect a Kubernetes microservice to an external database through a VPN with high availability and security?

**Answer:**

I design redundant site-to-site VPN tunnels/gateways with BGP/routes, non-overlapping CIDRs, private DNS forwarding and firewall allow only app subnets/Pods to DB port.

Workload uses TLS certificate validation, managed/workload identity or rotated secret, least-privilege (minimum required access) DB account, connection pool with timeout/retry/circuit breaker, and NetworkPolicy egress restriction.
Pods/egress gateways run across zones; DB endpoint/replicas and VPN failover match RTO. I test DNS, route and TCP/TLS from debug Pod, application query, one tunnel failure and zone failure while monitoring latency/errors/connections.

Logs exist at app, VPN/firewall and DB. I avoid retry storms and account for cross-network latency; secrets never appear in manifest/log.

## 11. You need TCP and UDP on the same port. How do you configure it?

**Answer:**

Define two uniquely named Service ports with same number and different protocols, subject to cloud load balancer support:

```yaml
ports:
- name: dns-tcp
  port: 53
  targetPort: 53
  protocol: TCP
- name: dns-udp
  port: 53
  targetPort: 53
  protocol: UDP
```

Container can bind TCP and UDP same numeric port because protocol sockets differ. Standard HTTP Ingress is not suitable for generic UDP; use LoadBalancer Service/Gateway/controller config that supports both.

I verify cloud provider health behavior, firewall/SG for both protocols, endpoints and test `dig` UDP plus TCP. Do not assume one protocol test proves other.

## 12. What happens if the firewall between control plane and worker nodes breaks?

**Answer:**

Nodes cannot heartbeat/watch Pod specs; become NotReady/Unreachable. Existing containers may continue locally, but controllers cannot reliably manage them; exec/logs/port-forward and Secret/config updates fail.

Managed Pods may be recreated elsewhere after tolerations, risking duplicate stateful processes if partitioned node still runs (fencing important). Control plane to kubelet/webhook/node ports may also fail.

I identify direction/port from provider docs, test DNS/route/TCP, inspect firewall/NSG changes/flow logs, node/kubelet and API logs. Restore narrow required rules, verify node Ready, leases, scheduling, logs/exec, CNI and application consistency.

Prevention: IaC/policy, monitoring heartbeat/connectivity, redundant network and tested partition behavior.

## 13. Your service mesh sidecar consumes more resources than the app. How do you analyze and optimize it?

**Answer:**

I measure sidecar CPU/memory vs. traffic/connections, request/response size, TLS handshakes, retries/timeouts, access log volume, monitoring data filters, trace sampling, config size/clusters/listeners and control-plane push/reloads. Distributed traces show retry amplification/backend slowness.
Optimize log/trace sampling, connection pools, retry budget, monitoring data, scope of injected workloads/config and mesh version; right-size from measured peak. Consider ambient/sidecarless mode only after feature/security evaluation, or exclude workloads not needing mesh.
I canary change, load-test mTLS/routing/failure, monitor latency/errors/security plus resource/cost. Removing sidecar blindly may remove identity/policy/observability controls.

## 14. Your Kubernetes cluster is healthy, but requests intermittently return HTTP 503. How do you troubleshoot it?

**Answer:**

I trace one failing request through DNS → external load balancer or ingress → routing rule → Service → EndpointSlice → ready Pod → application dependency. Cluster health alone does not prove that endpoints, readiness, connection pools, or downstream services are healthy.

I compare the time, host, path, zone, Pod, and application version of successful and failed requests.

```bash
kubectl get ingress,svc,endpointslice,pods -A -o wide
kubectl describe ingress <name>
kubectl logs -n <ingress-namespace> deploy/<controller>
kubectl get events --sort-by=.metadata.creationTimestamp
curl -vk https://<host>/<path>
```

I determine whether the 503 is generated by the ingress/proxy or application, then inspect empty or flapping endpoints, readiness failures, selector/port mismatches, rolling-update capacity, zone imbalance, NetworkPolicy, service-mesh retries, upstream timeouts, connection-pool exhaustion, and dependency latency.

Load-balancer and ingress metrics should be split by backend, response code, and upstream timing.
The fix targets the proven layer—for example the health probe, selector, `targetPort`, timeout, readiness, capacity, or dependency. I avoid hiding the problem with unlimited retries.

Afterward I test sustained traffic through the real hostname, verify error and latency SLOs, simulate Pod replacement, and alert on endpoint count, upstream 5xx, readiness churn, and saturation (how close a resource is to its limit).

## 15. Kubernetes Pods look healthy, but users receive HTTP 504 responses. How do you troubleshoot?

**Answer:**

A 504 is a gateway/proxy timeout, so I identify the component that generated it from response headers and logs, then trace ingress/load balancer → Service/EndpointSlice → Pod → downstream dependency.

I compare upstream connect, response and total timings; check endpoint readiness, target ports, DNS, NetworkPolicy, mesh retries, connection pools, queue depth, CPU throttling, GC and database/dependency latency.

A Running Pod can still be slow or unreachable from the proxy. I stabilize by reducing traffic, scaling the proven bottleneck, rolling back a regression or correcting the timeout/dependency issue—never by increasing every timeout blindly—then validate p95/p99 and real-user requests.

## 16. How can workloads in different Kubernetes namespaces communicate securely?

**Answer:**

Expose the destination through a Service and use cluster DNS, for example `api.payments.svc.cluster.local`; clients in another namespace can normally use `api.payments` plus the namespace.

Namespace isolation alone does not block network traffic, so I apply ingress and egress NetworkPolicies enforced by the CNI, allow only the required namespace labels, ports and DNS path, and use workload identity/RBAC for API access.

For an external dependency, an `ExternalName` Service can provide a DNS alias, but it does not create network security or health checking. I test DNS resolution, endpoints, policy enforcement and the full request path.

## 17. What is the difference between a Route and an Ingress?

**Answer:**

Ingress is the standard Kubernetes API for HTTP(S) routing to Services; an Ingress controller implements it. A Route is primarily an OpenShift resource that exposes a Service through the OpenShift router and adds OpenShift-specific TLS/traffic behavior.

They serve a similar north-south routing purpose but are not interchangeable portable APIs. For new portable Kubernetes designs I use the supported Ingress controller or Gateway API, configure TLS, host/path routing, health checks and security policy, and test the external request path.
