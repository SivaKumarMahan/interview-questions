# Observability Networking Scenario Questions

### 1. How do you monitor API performance in Apigee/Azure API Management?

**Answer:** Collect API response time, error rate, and request logs. Add dashboards for the service target, configure useful alerts, and apply rate limiting where needed.

**Mini-case:** Apigee showed a 30% response-time increase for one backend API. The backend Pods were at their resource limit, so scaling them restored normal response times.

**Detailed interview approach:**

I define service indicators first—availability, latency, errors, traffic, saturation (how close a resource is to its limit), and key business outcomes—then collect correlated metrics, structured logs, and traces with consistent service, environment, version, and request IDs.

Dashboards show both symptoms and dependencies; SLO-based alerts route with severity, ownership, and runbooks.

For scale, I combine or downsample old metrics, sample traces intelligently, and apply hot/warm/cold log retention based on debugging and compliance needs. During an incident I follow one request across layers and compare with deployment/config events.

I verify alert delivery and recovery and regularly tune noisy or unactionable signals.

---

### 2. How do you investigate high API latency in GCP/Azure APIs?

**Answer:** Check Cloud Trace / Application Insights → Identify slow endpoints → Scale backend pods → Add caching/CDN.

**Detailed interview approach:**

I define service indicators first—availability, latency, errors, traffic, saturation (how close a resource is to its limit), and key business outcomes—then collect correlated metrics, structured logs, and traces with consistent service, environment, version, and request IDs.

Dashboards show both symptoms and dependencies; SLO-based alerts route with severity, ownership, and runbooks.

For scale, I combine or downsample old metrics, sample traces intelligently, and apply hot/warm/cold log retention based on debugging and compliance needs. During an incident I follow one request across layers and compare with deployment/config events.

I verify alert delivery and recovery and regularly tune noisy or unactionable signals.

---

### 3. How do you handle high latency issues in GCP/Azure services?

**Answer:**

- Check network logs.
- Use Cloud Monitoring (Stackdriver/Azure Monitor).
- Scale infra (VMs, AKS nodes).
- Optimize load balancer & caching.

**Detailed interview approach:**

I define service indicators first—availability, latency, errors, traffic, saturation (how close a resource is to its limit), and key business outcomes—then collect correlated metrics, structured logs, and traces with consistent service, environment, version, and request IDs.

Dashboards show both symptoms and dependencies; SLO-based alerts route with severity, ownership, and runbooks.

For scale, I combine or downsample old metrics, sample traces intelligently, and apply hot/warm/cold log retention based on debugging and compliance needs. During an incident I follow one request across layers and compare with deployment/config events.

I verify alert delivery and recovery and regularly tune noisy or unactionable signals.
