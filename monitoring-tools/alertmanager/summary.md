# Alertmanager Monitoring Summary

## Role in the Alerting Flow

Prometheus evaluates PromQL alert rules. When a rule becomes firing, Prometheus sends the alert to Alertmanager. Alertmanager does not evaluate PromQL; it manages alert delivery.

```text
Prometheus rule evaluation
        ↓
Alertmanager
        ├── groups related alerts
        ├── deduplicates repeats
        ├── applies inhibition and silences
        └── routes by labels to receivers
```

- **Grouping** combines related alerts into a manageable notification.
- **Deduplication** prevents repeated copies of the same alert.
- **Routing** selects a receiver using labels such as team, service, environment and severity.
- **Inhibition** suppresses symptom alerts when a known parent alert is active.
- **Silence** temporarily suppresses matching notifications, usually for approved maintenance or investigation.

Alertmanager can deliver to email, webhooks, incident-management platforms and controlled chat integrations. Critical alerts should use an on-call system with acknowledgement and escalation rather than relying only on chat.

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

Receiver credentials belong in Kubernetes Secrets or an external secret manager such as Azure Key Vault. Do not commit webhook URLs, API tokens or SMTP passwords.

## Testing and Best Practices

- Alert on sustained, actionable symptoms or SLO burn, not every instantaneous threshold.
- Use stable ownership labels and consistent severity definitions.
- Include observed impact, current value, start time, dashboard and runbook in the notification.
- Test a safe firing condition, the intended route, grouping, template rendering, acknowledgement/escalation and resolved notification.
- Test silences and maintenance processes without leaving broad or permanent suppressions.
- Monitor Alertmanager health, notification errors, queue behavior and configuration reloads.
- For high availability, run supported clustered replicas and test failure of an instance and a notification receiver.

Grafana can add a Prometheus Alertmanager data source to inspect alerts and manage silences. With that integration, Alertmanager contact points, policies and templates remain managed in Alertmanager rather than being edited as Grafana-managed alerting configuration.