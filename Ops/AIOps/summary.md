# AIOps Interview Summary

**AIOps** applies analytics and machine learning to IT operations data. It helps teams detect unusual behavior, group related events, prioritize the most important impact, assist diagnosis, forecast capacity, and safely automate repeatable responses.

**Observability** supplies the evidence: metrics, logs, traces, service relationships, deployment or configuration events, and service ownership. AIOps uses those signals; it does not replace them.

It does **not** replace instrumentation, SRE ownership or incident command.
```text
monitoring data and changes -> clean and add context -> group related events and detect unusual behavior
-> rank impact/probable causes -> recommend action
-> approval or bounded runbook -> verify -> learn
```

A useful result is evidence such as "latency began after version 42, affects two regions, traces point to database pool exhaustion, and rollback previously resolved the same signature," not a vague anomaly score.

**Automation needs:**

- Confidence thresholds
- Least-privilege (minimum required access) identity
- Preconditions
- Rate and blast-radius limits
- Dry run
- Approval for risky actions
- Rollback/kill switch
- Immutable (not changed after creation) audit evidence
- Post-action SLO validation

**Measure:** detection precision/recall, duplicate reduction, alert actionability, time to detect/acknowledge/restore, correct root-cause ranking, fix success and unsafe-action rate.

Feedback must distinguish temporary mitigation from permanent resolution so the system does not learn to restart services endlessly instead of fixing a leak.
