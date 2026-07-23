# AIOps Interview Summary

**AIOps** applies analytics and machine learning to IT operations data so teams can detect unusual behavior, correlate related events, prioritize impact, assist diagnosis, forecast capacity and safely automate repeatable response. **Observability** supplies metrics, logs, traces, topology, deployment/configuration events and service ownership; AIOps reasons over those signals. It does **not** replace instrumentation, SRE ownership or incident command.

```text
telemetry and changes -> normalize/enrich -> correlate and detect
-> rank impact/probable causes -> recommend action
-> approval or bounded runbook -> verify -> learn
```

A useful result is evidence such as "latency began after version 42, affects two regions, traces point to database pool exhaustion, and rollback previously resolved the same signature," not a vague anomaly score.

**Automation needs:**

- Confidence thresholds
- Least-privilege identity
- Preconditions
- Rate and blast-radius limits
- Dry run
- Approval for risky actions
- Rollback/kill switch
- Immutable audit evidence
- Post-action SLO validation

**Measure:** detection precision/recall, duplicate reduction, alert actionability, time to detect/acknowledge/restore, correct root-cause ranking, remediation success and unsafe-action rate. Feedback must distinguish temporary mitigation from permanent resolution so the system does not learn to restart services endlessly instead of fixing a leak.
