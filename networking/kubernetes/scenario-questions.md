## 1. How do you secure Kubernetes Ingress traffic?

**Answer:** Use TLS certificates (Cert-Manager) → Enable WAF/firewall rules → Restrict IP access → Use Istio/NGINX for advanced security.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

## 2. How do you debug Kubernetes DNS issues?

**Answer:** Check CoreDNS logs, verify ConfigMaps, run `nslookup` or `dig` from a Pod with `kubectl exec`, and ensure NetworkPolicies allow DNS traffic. Mini-case: Pods could not resolve Services because of an incorrect CoreDNS `stubDomain`; correcting the ConfigMap restored DNS resolution.

**Detailed interview approach:**
I test from the affected pod using `cat /etc/resolv.conf`, `nslookup kubernetes.default`, and a lookup for the failing Service/FQDN.

I compare against a healthy namespace or node, then check the Service/EndpointSlice records, CoreDNS pods, logs, ConfigMap, resource saturation (how close CoreDNS is to running out of capacity), and the upstream DNS server.

NetworkPolicy and firewall rules need to allow UDP and TCP on port 53 to cluster DNS. I also compare timeouts against `NXDOMAIN`: a timeout points to a path or capacity problem, while a wrong name or search domain gives a valid negative answer instead.

Once I've made the targeted fix — to CoreDNS, a policy, or the upstream resolver — I test both short and full names, run an actual application call, and check DNS latency. If load caused the incident, I also add capacity and alerts.

## 3. How do you debug cross-cluster service communication failures?

**Answer:** Verify DNS resolution, network routes, firewall rules, service mesh mTLS settings, and mutual TLS cert validity; trace requests with distributed tracing (Jaeger) to identify where traffic is dropped.

Mini-case: Tracing showed requests stopping at the ingress of cluster B; firewall rules were blocking healthcheck IP ranges — after opening the range, inter-cluster calls recovered.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

## 4. How do you secure container-to-container communication in Kubernetes?

**Answer:** Use NetworkPolicies → Enable mutual TLS with Istio → Encrypt traffic.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

## 5. How do you debug Kubernetes ingress not routing traffic?

**Answer:** Check ingress controller logs → Validate annotations/paths → Check DNS → Verify backend service health.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

## 6. How do you protect Kubernetes against DDoS attacks?

**Answer:** Use cloud-native DDoS protection (Cloud Armor/Azure DDoS Protection) → Apply rate limiting → Enable WAF on ingress.

**Detailed interview approach:**
I apply defense in depth: a private/restricted API server, SSO, and least-privilege RBAC (giving each identity only the access it needs), separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit/runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect a workload has been exposed, I isolate it, preserve audit and runtime evidence, revoke its tokens or credentials, check for lateral movement, and rebuild it from a trusted image.

I verify both the denied and allowed paths using real service accounts, and periodically review RBAC for unused permissions, rotate certificates and secrets, check patch levels, confirm backup/restore works, and review policy exceptions.

## 7. How do you troubleshoot a Kubernetes service not reachable externally?

**Answer:** Check service type (ClusterIP vs LoadBalancer) → Validate Ingress rules → Ensure firewall/load balancer rules are correct.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

## 8. How do you troubleshoot DNS issues in Kubernetes?

**Answer:** Run kubectl exec into pod → Test DNS resolution → Check CoreDNS logs → Restart CoreDNS pods → Fix network policies if blocking.

**Detailed interview approach:**
I test from the affected pod using `cat /etc/resolv.conf`, `nslookup kubernetes.default`, and a lookup for the failing Service/FQDN.

I compare against a healthy namespace or node, then check the Service/EndpointSlice records, CoreDNS pods, logs, ConfigMap, resource saturation (how close CoreDNS is to running out of capacity), and the upstream DNS server.

NetworkPolicy and firewall rules need to allow UDP and TCP on port 53 to cluster DNS. I also compare timeouts against `NXDOMAIN`: a timeout points to a path or capacity problem, while a wrong name or search domain gives a valid negative answer instead.

Once I've made the targeted fix — to CoreDNS, a policy, or the upstream resolver — I test both short and full names, run an actual application call, and check DNS latency. If load caused the incident, I also add capacity and alerts.

## 9. How do you handle Kubernetes pod networking issues?

**Answer:** Check CNI plugin logs → Validate IP assignment → Restart kube-proxy or CNI → Apply Network Policies correctly.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

## 10. How do you implement Service Mesh in Kubernetes?

**Answer:** Deploy Istio/Linkerd → Enable traffic routing, retries, and observability → Use for canary/blue-green deployments.

**Detailed interview approach:**
I bring in a service mesh for a specific need — workload identity, mTLS, traffic policy, or better telemetry — not just to add proxies for their own sake. I inventory the protocols and ports in use, install the control plane and monitor it, onboard one non-critical namespace first, and check the sidecar or ambient resource overhead.

Identities come from service accounts and short-lived certificates. I move mTLS from permissive to strict only after confirming I've seen every legitimate caller. AuthorizationPolicy then allows the exact service-to-service paths that are needed and denies everything else by default.

I test certificate rotation, retries/timeouts, what happens if the control plane fails, and any way traffic could bypass the proxy — then roll out gradually. Dashboards and tracing confirm latency and error rates are healthy, and I keep clear upgrade and version-skew procedures so the mesh stays supportable.

## 11. How do you troubleshoot network issues in Kubernetes?

**Answer:** • Check kubectl get svc for service mapping.
• Validate Network Policies.
• Run kubectl exec to test connectivity (ping, curl).
• Use kubectl describe svc to verify correct target pods.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.
