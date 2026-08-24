# Infrastructure-as-Code Monitoring Summary

There are two separate things to monitor here: the infrastructure that Terraform creates, and the Terraform pipeline itself. Both need attention.

## Monitor the Infrastructure Terraform Creates

Provision monitoring alongside the infrastructure it watches, not as an afterthought added later. Diagnostic settings or log groups, metric and log alerts, dashboards, notification routing (action groups or topics), retention, and access controls should all live in the same Terraform, Bicep, or CloudFormation resources as the service they belong to — or be enforced through policy so nothing slips through unmonitored.

Reusable modules give every service a safe default. Service owners still decide what a meaningful signal looks like for their own service, and where its alerts should route.

## Monitor the Terraform Pipeline Itself

The delivery pipeline is its own thing to watch, separate from the infrastructure it manages:

- Plan and apply duration and result
- State lock wait time
- Provider and API errors
- Drift detection results
- Policy and security check failures
- Smoke checks run right after apply

Keep a reviewed, access-controlled plan and a full audit trail for every change. Terraform state and full plans can contain secrets, so their content should never be exported into ordinary logs or metrics.

Production applies should be serialized — one at a time — and alerts need to tell the difference between an active, legitimate lock and a stale one left behind by a failed run.

## Validate After Every Apply

An apply that finishes successfully, and creates an alert resource or a diagnostic setting, is not proof the monitoring actually works. Check three things afterward:

1. Monitoring data is actually arriving.
2. Alerts route to the right place.
3. The application transaction being monitored actually works.

## Quick Reference

| What to track | Where | Why it matters |
| --- | --- | --- |
| Format, validation, and policy results | PR pipeline | Catches problems before merge |
| Reviewed plan | PR pipeline, access-controlled | Audit trail, prevents surprise changes |
| Apply result and duration | Production pipeline | Confirms delivery worked |
| State-lock wait | Production pipeline | Flags contention or stuck runs |
| Provider/API failures | Production pipeline | Surfaces upstream issues early |
| Drift | Scheduled plans or platform drift detection | Flags out-of-band changes without silently reverting them |
| Post-apply smoke check | Production pipeline | Confirms the real service works, not just that resources exist |
