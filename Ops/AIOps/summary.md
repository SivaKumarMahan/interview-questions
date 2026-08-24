# AIOps Interview Summary

**AIOps** applies analytics and machine learning to IT operations data. It helps teams spot unusual behavior, group related events together, prioritize what matters most, assist with diagnosis, forecast capacity, and safely automate repeatable responses.

**Observability** supplies the raw evidence: metrics, logs, traces, service relationships, deployment or configuration events, and who owns each service. AIOps uses those signals — it doesn't replace them.

It also doesn't replace instrumentation, SRE ownership, or having someone lead an incident.

```text
monitoring data and changes -> clean and add context -> group related events and detect unusual behavior
-> rank impact/probable causes -> recommend action
-> approval or bounded runbook -> verify -> learn
```

A useful result looks like real evidence: "latency began after version 42, it affects two regions, traces point to database pool exhaustion, and a rollback fixed this same pattern before." A vague anomaly score on its own isn't useful.

**What automation needs:**

- Confidence thresholds
- An identity with only the access it needs
- Preconditions before it acts
- Rate limits and a capped blast radius
- A dry-run mode
- Approval for anything risky
- A rollback path and a kill switch
- Audit evidence that can't be changed after the fact
- A check against the SLO after the action runs

**What to measure:** detection precision and recall, how much duplicate noise gets reduced, whether alerts are actually actionable, time to detect/acknowledge/restore, whether the top-ranked root cause is usually right, how often the fix actually works, and how often an action turns out to be unsafe.

Feedback has to tell a temporary workaround apart from a real fix — otherwise the system just learns to keep restarting a service instead of ever fixing the underlying leak.
