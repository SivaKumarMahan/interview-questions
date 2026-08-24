# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Process & Tooling

### 13.1 Chaos engineering — what it is and using it in production

- **Chaos engineering** means deliberately injecting failures — killing pods, adding latency, dropping network traffic, exhausting CPU, simulating the loss of a whole availability zone — to prove the system is resilient and find weaknesses before a real outage does.
- **Practice:** form a hypothesis (like "the system stays healthy if we lose an AZ"), define a metric for normal, healthy behavior, run the experiment starting in staging, keep the blast radius small, monitor closely, and roll back automatically if things get worse. Tools: Chaos Mesh, LitmusChaos, Gremlin, AWS FIS.
- **In production:** run it carefully — small blast radius, off-peak hours, strong observability, an abort switch, and stakeholders who know it's happening (GameDays). The goal is real confidence in how the system holds up.

### 13.2 Managing ServiceNow tasks — how do you prioritize?

Prioritize by impact times urgency (ServiceNow's priority matrix), SLA deadlines, and business criticality: production-impacting incidents (P1/P2) first, then anything at risk of breaching its SLA, then routine changes and requests.

I triage the queue, acknowledge tasks and communicate realistic ETAs, group similar tasks together, escalate blockers, follow change-management for production changes, and document how each one was resolved.

I try to balance firefighting with actually reducing the recurring tickets through automation.
