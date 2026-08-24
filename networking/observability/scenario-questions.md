# Observability Networking Scenario Questions

### 1. How do you monitor API performance in Apigee/Azure API Management?

**Answer:** Collect API response time, error rate, and request logs. Add dashboards for the service target, configure useful alerts, and apply rate limiting where needed.

**Mini-case:** Apigee showed a 30% response-time increase for one backend API. The backend pods were at their resource limit, so scaling them restored normal response times.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation (how close a resource is to its limit), and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

---

### 2. How do you investigate high API latency in GCP/Azure APIs?

**Answer:** Check Cloud Trace / Application Insights → Identify slow endpoints → Scale backend pods → Add caching/CDN.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation, and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.

---

### 3. How do you handle high latency issues in GCP/Azure services?

**Answer:**

- Check network logs.
- Use Cloud Monitoring (Stackdriver/Azure Monitor).
- Scale infra (VMs, AKS nodes).
- Optimize load balancer & caching.

**Detailed interview approach:**

I start by defining the signals that actually matter: availability, latency, errors, traffic, saturation, and the business outcomes they map to. Then I collect correlated metrics, structured logs, and traces, all tagged consistently with service, environment, version, and request ID.

Dashboards should show both the symptom and the likely dependency behind it. Alerts are tied to SLOs and route with the right severity, owner, and runbook.

At scale, I combine or downsample old metrics, sample traces intelligently, and set hot/warm/cold log retention based on what's actually needed for debugging and compliance. During an incident, I follow a single request across every layer and compare it against recent deployment/config changes.

I regularly check that alerts actually fire and recover as expected, and I tune out noisy or unactionable ones.
