# Alertmanager Monitoring Summary

## Role in the Alerting Flow

Prometheus evaluates PromQL alert rules. When a rule fires, Prometheus sends the alert to Alertmanager. Alertmanager doesn't evaluate PromQL itself — its job is managing how those alerts get delivered.

```text
Prometheus rule evaluation
        ↓
Alertmanager
        ├── groups related alerts
        ├── deduplicates repeats
        ├── applies inhibition and silences
        └── routes by labels to receivers
```

| Feature | What it does |
| --- | --- |
| Grouping | Combines related alerts into one manageable notification |
| Deduplication | Stops repeated copies of the same alert going out |
| Routing | Picks a receiver based on labels like team, service, environment, and severity |
| Inhibition | Suppresses symptom alerts when a known parent alert is already firing |
| Silence | Temporarily suppresses matching alerts, usually during planned maintenance |

Alertmanager can deliver to email, webhooks, incident-management platforms, and controlled chat integrations. For critical alerts, use an on-call system with acknowledgement and escalation — don't rely on chat alone, since messages can be missed.

## Prometheus Connection

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

The Prometheus rule should include enough context for routing and response:

```yaml
groups:
  - name: application-health
    rules:
      - alert: ApplicationHighErrorRate
        expr: |
          sum by (service) (
            rate(http_requests_total{status=~"5.."}[5m])
          )
          /
          sum by (service) (
            rate(http_requests_total[5m])
          ) > 0.05
        for: 10m
        labels:
          severity: critical
          team: application
        annotations:
          summary: "High error rate for {{ $labels.service }}"
          description: "More than 5% of requests have failed for 10 minutes."
          runbook_url: "https://runbooks.example/application-high-error-rate"
```

## Routing Example

```yaml
route:
  receiver: default-notifications
  group_by: ["alertname", "service", "environment"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers:
        - severity="critical"
      receiver: critical-on-call

receivers:
  - name: default-notifications
    webhook_configs:
      - url_file: /run/secrets/default_webhook_url

  - name: critical-on-call
    webhook_configs:
      - url_file: /run/secrets/on_call_webhook_url
```

Keep receiver credentials in Kubernetes Secrets or an external secret manager such as Azure Key Vault. Never commit webhook URLs, API tokens, or SMTP passwords to the repo.

## Testing and Best Practices

- Alert on sustained, actionable problems or SLO burn — not on every brief threshold breach.
- Use stable ownership labels and consistent severity levels across the board.
- Include the observed impact, current value, start time, a dashboard link, and a runbook link in every notification.
- Test a safe firing condition end to end: the right route, grouping, template rendering, acknowledgement, escalation, and the resolved notification.
- Test silences and maintenance windows, and don't leave broad or permanent suppressions sitting in place afterward.
- Monitor Alertmanager itself: its health, notification failures, queue behavior, and config reloads.
- For high availability, run Alertmanager as a supported cluster, and actually test what happens when one instance or one receiver fails.

## Grafana Integration

Grafana can add Prometheus Alertmanager as a data source to inspect alerts and manage silences from its UI. With that setup, the contact points, policies, and templates stay managed inside Alertmanager itself — they aren't edited as Grafana's own alerting configuration.