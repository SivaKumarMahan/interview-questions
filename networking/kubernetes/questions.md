## 1. Your Ingress controller crashes repeatedly under heavy load. How do you stabilize it?

**Answer:**

First I protect traffic: roll back the last config change, scale up healthy replicas, or shift traffic away. Then I look for the cause. I check current and previous logs, whether pods were OOM-killed or terminated, CPU/memory and throttling, connection and request metrics, how often the config reloads, TLS/WAF/logging overhead, upstream latency, node pressure, and load-balancer health.

Fixes usually involve: running multiple replicas spread across zones, a PodDisruptionBudget, realistic resource requests, autoscaling on CPU/requests/connections, dedicated nodes if needed, a leaner config, and a slower reload rate. A large cert or rule set, or too much access logging/tracing, can also overload the controller. A slow backend can pile up connections and cause the same symptom.

I load-test at peak plus a failure scenario, check p95 latency, error rate, connection resets, and reload metrics, then plan capacity ahead of time and validate config changes with a canary. Scaling the controller alone won't help if the real problem is a saturated backend.

## 2. During peak traffic, Ingress fails to route requests efficiently. How do you diagnose and scale it?

**Answer:**

I split the request path into stages: edge/load balancer, Ingress controller, Service/endpoints, and backend. I compare request rate, 4xx/5xx counts, controller latency versus upstream latency, active connections and queue depth, TLS overhead, retries and timeouts, reload frequency, pod/node resource use, readiness, and endpoint count.

I check the routing rule (host and path) and test the Service directly, bypassing Ingress, to isolate the problem. Depending on what I find, the fix might be scaling the controller or backends, adding capacity headroom, rolling back a recent config change, rate limiting, or shifting traffic elsewhere.

I only tune buffers and timeouts once the evidence points there — a timeout set too long just makes connection exhaustion worse.

Afterward I load-test, set up autoscaling with zone spreading and a PodDisruptionBudget, and monitor saturation — how close a resource is to running out of capacity. I also confirm the cloud load balancer is spreading traffic across healthy controller pods and nodes, and add synthetic tests for the key host/path combinations.

## 3. How do you troubleshoot 503 errors from a LoadBalancer?

**Answer:**

A 503 usually means the request reached the gateway or load balancer, but there was no healthy backend, or the upstream failed. I check the headers and logs to see which layer generated the response.

Then I check load balancer provisioning and backend health, the Service selector and ports, EndpointSlices, pod readiness, whether the app is listening on the right address and port, the Ingress route, and the network/firewall path.

```bash
kubectl get svc,endpointslice,pods -o wide
kubectl describe svc <svc>
kubectl logs <ingress-controller> --since=15m
```

I test in order: the pod IP directly, then the Service DNS name, then the Ingress/load balancer. I fix whatever's broken — selector, port, probe, network, or app — or roll back the release, then confirm the fix with a real external request and by watching metrics. To prevent a repeat, I add smoke/synthetic tests, config validation, and an alert on healthy backend count.

## 4. Case: Pod is not accessible internally. How do you troubleshoot?

**Answer:**

First I clarify what "not accessible" means: by pod IP or by Service, and from which namespace. I check that the pod is Running and Ready, that the app logs show it listening on `0.0.0.0:<targetPort>` (not just `localhost`), that the Service selector, port, and targetPort match, and that EndpointSlices and DNS look correct.

From a debug pod, I test in order: DNS, then Service IP/port, then the pod IP/port directly. If the direct pod IP works but the Service doesn't, the problem is likely the selector, endpoints, or the Service data plane.

If both fail, I check how the app is bound, NetworkPolicy rules, and the CNI/routes/security group/node firewall. If only DNS fails, I check CoreDNS and any DNS-related policy.

I note the exact error — timeout, connection refused, or NXDOMAIN — fix the one layer that's broken, and retest from the original source plus readiness and the real user flow. I clean up any debug pods afterward.

## 5. Case: Pod is internally accessible but LoadBalancer fails. What do you check?

**Answer:**

Since internal access works, the pod and app are at least partly healthy. I check the LoadBalancer Service's events, status, and external address, the cloud load balancer's backend/target health, the probe's path/port/protocol/host, the Service's `port`/`targetPort`/`nodePort`, `externalTrafficPolicy`, node and pod readiness, and the cloud security group/firewall/routes.

I test the Service from inside the cluster, the health endpoint the way the load balancer sees it, and the external path. Controller and cloud-provider logs, plus cloud activity logs, usually reveal provisioning, permission, or quota errors.

One thing to watch for: if `externalTrafficPolicy` is set to `Local`, a node with no local endpoints for that Service can fail its health check, even though other nodes are fine.

I fix the probe, network, ports, or annotation — or roll back — then wait for the change to reconcile (for the cluster's actual state to catch up with the desired state). I confirm multiple zones and backends work, check external TLS and requests, and monitor going forward. I never open the firewall wider as a permanent workaround.

## 6. How do you debug DNS failures inside Kubernetes?

**Answer:**

First I narrow down the failure: is it a cluster Service name or an external name, one pod/node/namespace or the whole cluster, and is it NXDOMAIN or a timeout? From a debug pod I check `/etc/resolv.conf`, run `nslookup`/`dig` for both the short name and the FQDN, and query the kube-dns Service IP directly.

I check CoreDNS's replica count, readiness, logs, metrics, and config, the relevant Service/endpoints, NetworkPolicy rules for UDP/TCP port 53, the CNI, and the upstream resolver or node DNS.

High latency is often caused by `ndots` search-domain amplification, an overloaded CoreDNS, or a slow upstream resolver. I fix this by scaling or fixing CoreDNS, or reverting a bad config change — never by hardcoding entries in `/etc/hosts`.

Afterward I confirm both internal Service names and external names resolve, check TCP fallback for large responses, and monitor DNS error rate and latency. NodeLocal DNSCache can help at scale, but only after the data shows it's actually needed.

## 7. How do you troubleshoot Pod-to-Pod networking issues?

**Answer:**

I map out the source pod, destination pod, their nodes, IPs, port/protocol, and the exact failure. I test the direct pod IP first — same node, then across nodes — then the Service, using `nc`/`curl`, and only use packet capture with approval.

I check that the app is actually listening, both ingress and egress NetworkPolicy rules (including namespace labels), CNI pod status/logs/IP allocation, node routes/MTU/firewall/security groups, and kube-proxy or eBPF data-plane state.

If same-node traffic works but cross-node traffic fails, suspect the CNI overlay, routes, MTU, or firewall. If the direct IP works but the Service doesn't, suspect endpoints or the Service data plane. Whether it's a timeout or an outright refusal is also a useful clue.

After the fix, I confirm the traffic that should be allowed works and the traffic that should be blocked stays blocked, test across multiple nodes and zones, and monitor for packet drops. I keep the network config in version control.

## 8. How do you design and debug NetworkPolicies between namespaces?

**Answer:**

I start by listing out the traffic flows that need to exist, then confirm the CNI actually enforces NetworkPolicy, and make sure namespaces are labeled reliably. I apply a default-deny rule for ingress and egress first, then add explicit allows for DNS and the application traffic that's actually needed. A single rule can combine a `namespaceSelector` and a `podSelector` to require both conditions.

I roll this out through an audit or staging mode where the tooling supports it, run connectivity tests from both allowed and denied namespaces, and check policy selection (the `podSelector` labels), `policyTypes`, ports/protocols, namespace labels, return traffic, and DNS.

When something fails, I compare against a direct-IP test, check which policies select the source and destination, and look at CNI policy logs or drop counters. I don't delete all policies to "fix" it — if I need a temporary diagnostic allow rule, I keep it narrow and time-boxed, with approval.

I validate that the result gives least privilege — only the access that's actually needed — while still letting required health checks and monitoring traffic through.

## 9. How do you restrict communication between two Pods in the same namespace?

**Answer:**

Without any policy, pods can generally reach each other freely. I label the workloads, apply a default-deny rule, then allow the target to receive traffic only from the approved source label and port. If egress is also isolated, the source's egress rule needs to allow the destination too.

```yaml
spec:
  podSelector: { matchLabels: { app: database } }
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector: { matchLabels: { app: api } }
    ports: [{ protocol: TCP, port: 5432 }]
```

I confirm the CNI actually enforces this, then test that the API can reach the database, an unrelated pod cannot, and DNS/monitoring still work. Labels are a security-relevant input, so I make sure they're protected by admission control or governance. I monitor denied flows where that's supported, and keep policies in version control.

## 10. How would you connect a Kubernetes microservice to an external database through a VPN with high availability and security?

**Answer:**

I design redundant site-to-site VPN tunnels and gateways with BGP routing, non-overlapping CIDRs, private DNS forwarding, and a firewall that only allows the app's subnets/pods to reach the database port.

The workload validates the database's TLS certificate, authenticates with a managed or workload identity (or a rotated secret if that's not possible), uses a least-privilege database account (one with only the access it actually needs), and connects through a pool with timeouts, retries, and a circuit breaker. NetworkPolicy restricts egress to just the database path.

Pods and egress gateways run across multiple zones. The database endpoint, its replicas, and the VPN failover setup all need to match the recovery-time target. I test DNS, routing, and TCP/TLS from a debug pod, run an actual application query, and simulate one tunnel failing and one zone failing, while watching latency, errors, and connection counts.

I make sure logs exist at the app, VPN/firewall, and database layers. I avoid retry storms, account for the extra latency of a cross-network path, and make sure secrets never show up in a manifest or log.

## 11. You need TCP and UDP on the same port. How do you configure it?

**Answer:**

Define two Service ports with the same number but different protocols and unique names, as long as your cloud load balancer supports this:

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

A container can bind the same numeric port for TCP and UDP because they're separate sockets under the hood. A standard HTTP Ingress isn't built for generic UDP traffic, so use a LoadBalancer Service or a Gateway/controller that explicitly supports both protocols.

I confirm how the cloud provider handles health checks for this setup, check the firewall/security group covers both protocols, verify endpoints, and test with `dig` over both UDP and TCP. Passing on one protocol doesn't mean the other one works too.

## 12. What happens if the firewall between control plane and worker nodes breaks?

**Answer:**

Nodes can no longer send heartbeats or watch for pod spec changes, so they go NotReady or Unreachable. Containers that are already running may keep running locally, but the control plane can't reliably manage them — `exec`, `logs`, `port-forward`, and Secret/config updates all fail.

The control plane may reschedule managed pods elsewhere once tolerations expire. If the partitioned node is still actually running its pods, this risks two copies of a stateful process running at once — which is why fencing matters. Traffic from the control plane to kubelet or webhook ports can also fail in the same way.

I identify the required direction and port from the provider's docs, test DNS/route/TCP, and check for recent firewall or NSG changes and flow logs, along with node/kubelet and API server logs. I restore only the specific rules that are needed, then confirm nodes go Ready, leases update, scheduling resumes, logs/exec work again, and the CNI and application are consistent.

To prevent this: manage firewall rules through IaC and policy, monitor node heartbeat and connectivity, build redundant network paths, and actually test how the cluster behaves under a network partition.

## 13. Your service mesh sidecar consumes more resources than the app. How do you analyze and optimize it?

**Answer:**

I measure the sidecar's CPU/memory against actual traffic and connection volume, request/response size, TLS handshake rate, retries/timeouts, access log volume, metrics cardinality, trace sampling rate, and the size of its config (clusters, listeners) and control-plane push/reload frequency. Distributed traces often reveal retry amplification or a slow backend as the real driver.

I tune log/trace sampling, connection pool sizes, retry budgets, metrics volume, and which workloads actually need the mesh injected, and check whether the mesh version itself has a known issue. I size resources from a measured peak, not a guess. An ambient or sidecar-less mode is worth considering, but only after checking it covers the features and security controls I actually need — or I simply exclude workloads that don't need the mesh at all.

I roll out any change as a canary, load-test mTLS/routing/failure behavior, and watch latency, errors, security posture, resource use, and cost. Removing the sidecar without this care can quietly remove identity, policy enforcement, or observability along with it.

## 14. Your Kubernetes cluster is healthy, but requests intermittently return HTTP 503. How do you troubleshoot it?

**Answer:**

I trace one failing request through the whole path: DNS → external load balancer or ingress → routing rule → Service → EndpointSlice → ready pod → application dependency. The cluster being "healthy" overall doesn't tell me whether endpoints, readiness, connection pools, or downstream services are actually healthy.

I compare the time, host, path, zone, pod, and application version between successful and failed requests.

```bash
kubectl get ingress,svc,endpointslice,pods -A -o wide
kubectl describe ingress <name>
kubectl logs -n <ingress-namespace> deploy/<controller>
kubectl get events --sort-by=.metadata.creationTimestamp
curl -vk https://<host>/<path>
```

I figure out whether the 503 came from the ingress/proxy or from the application itself, then check for empty or flapping endpoints, readiness failures, selector/port mismatches, insufficient capacity during a rolling update, zone imbalance, NetworkPolicy, service-mesh retries, upstream timeouts, connection-pool exhaustion, and dependency latency.

I split load-balancer and ingress metrics by backend, response code, and upstream timing. The fix targets whichever layer the evidence points to — the health probe, selector, `targetPort`, timeout, readiness, capacity, or a dependency — rather than papering over it with unlimited retries.

Afterward I run sustained traffic through the real hostname, confirm error and latency targets are met, simulate a pod being replaced, and alert on endpoint count, upstream 5xx rate, readiness churn, and saturation — how close a resource is to its limit.

## 15. Kubernetes Pods look healthy, but users receive HTTP 504 responses. How do you troubleshoot?

**Answer:**

A 504 means a gateway or proxy timed out waiting for a response, so I check the response headers and logs to identify which component generated it, then trace the path: ingress/load balancer → Service/EndpointSlice → pod → downstream dependency.

I compare connect time, response time, and total time at each hop, and check endpoint readiness, target ports, DNS, NetworkPolicy, mesh retries, connection pools, queue depth, CPU throttling, garbage collection, and database/dependency latency.

A pod that shows as Running can still be slow or unreachable from the proxy's point of view. I stabilize the situation by reducing traffic, scaling the actual bottleneck, rolling back a bad change, or fixing the real timeout/dependency issue — never by just increasing every timeout — then confirm p95/p99 latency and real-user requests look right.

## 16. How can workloads in different Kubernetes namespaces communicate securely?

**Answer:**

Expose the destination through a Service and use cluster DNS — for example `api.payments.svc.cluster.local`. Clients in another namespace can usually just use `api.payments` plus the namespace name.

Being in a different namespace doesn't block traffic on its own, so I add ingress and egress NetworkPolicies (enforced by the CNI) that allow only the required namespace labels, ports, and DNS path, and use workload identity/RBAC for API access.

For an external dependency, an `ExternalName` Service can give it a DNS alias, but it doesn't add network security or health checking on its own. I test DNS resolution, endpoints, policy enforcement, and the full request path before calling it done.

## 17. What is the difference between a Route and an Ingress?

**Answer:**

Ingress is the standard Kubernetes API for HTTP(S) routing to Services, implemented by an Ingress controller. A Route is mainly an OpenShift resource that exposes a Service through the OpenShift router and adds some OpenShift-specific TLS/traffic behavior.

They serve a similar purpose — routing traffic into the cluster — but they aren't interchangeable, portable APIs. For a new, portable Kubernetes design, I use a supported Ingress controller or the Gateway API, configure TLS, host/path routing, health checks, and security policy, then test the external request path end to end.
