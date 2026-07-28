# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Process & Tooling

### 13.1 Chaos engineering — what it is and using it in production

- **Chaos engineering** = deliberately injecting failures (kill pods, add latency, drop network, exhaust CPU, simulate AZ loss) to **prove resilience** and find weaknesses **before** real outages do.
- **Practice:** form a hypothesis ("system stays healthy if we kill an AZ"), define a **steady-state metric**, run the experiment starting in **staging**, limit the **scope of impact**, monitor, and roll back automatically if things degrade. Tools: **Chaos Mesh, LitmusChaos, Gremlin, AWS FIS**.
- **In production:** run carefully with small scope of impact, off-peak, strong observability, an abort switch, and stakeholder awareness — GameDays. Goal is confidence in real-world resilience.

### 13.2 Managing ServiceNow tasks — how do you prioritize?

Prioritize by **impact × urgency** (ServiceNow's priority matrix), SLA deadlines, and business criticality: production-impacting incidents (P1/P2) first, then SLA-breach-risk items, then routine changes/requests.

I triage the queue, acknowledge and communicate ETAs, group similar tasks, escalate blockers, follow change-management for prod changes, and document resolutions.

Balance firefighting with reducing recurring tickets through automation.
