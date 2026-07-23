# Infrastructure-as-Code Monitoring Summary

Provision monitoring with the infrastructure it observes: diagnostic settings/log groups, metric and log alerts, dashboards, action groups/topics, retention, access controls and service-level probes should be reviewed Terraform/Bicep/CloudFormation resources or enforced policy. Reusable modules provide safe defaults but allow service owners to supply meaningful SLO signals and routing.

Monitor **Terraform delivery** separately: plan/apply duration and result, state lock wait, provider/API errors, drift detection, policy/security failures and post-apply smoke checks. Preserve an access-controlled reviewed plan and audit trail; do not export sensitive plan/state content as ordinary logs or metrics. Production applies are serialized and alerts distinguish an active legitimate lock from a stale failed run.

After apply, validate that telemetry actually arrives, alerts route correctly and the application transaction works. A successfully created alert resource or diagnostic setting is not evidence that the monitoring path works end to end.
