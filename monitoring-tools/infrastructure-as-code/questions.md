## 1. How do you implement monitoring for Terraform-managed infrastructure?

**Answer:**

I build monitoring into the same Terraform modules as the service itself. Diagnostic settings or log groups, metric and log alerts, dashboards, notification routing, retention, and access controls all live next to the resource they watch, not bolted on afterward.

Service owners still decide what a meaningful signal looks like for their own service. I push back on generic CPU-only alerts, because they rarely tell you whether users are actually affected.

Policy can enforce a baseline level of logging across the org, so nothing ships unmonitored by accident.

CI validates the code and previews the plan before anything is applied. The apply itself runs with only the permissions it actually needs. Afterward, I generate a known test event or a smoke transaction to prove the whole pipeline works end to end — that data really arrives and a notification really fires.

I also monitor the monitoring resources themselves. That includes cardinality, the number of unique label combinations being produced, since it drives cost and retention just as much as raw data volume does.

## 2. How do you monitor Terraform changes and drift?

**Answer:**

The pull request pipeline records the results of format checks, validation, and policy checks, along with a reviewed and protected plan. Nothing gets applied without going through that review.

In production, I record whether the apply succeeded, how long it took, how long it waited on a state lock, and any provider or API failures. After the apply, I run infrastructure and application checks to confirm the change actually worked.

Scheduled plans, or the platform's own drift-detection feature, catch changes made outside of Terraform. When that happens, I open a ticket or alert for someone to review. I don't let automation silently overwrite an emergency change someone made by hand.

Terraform state and full plans can contain secrets, so I keep them encrypted and access-controlled rather than sending them to ordinary logs. When a run fails, I compare it against the cloud provider's audit logs, and I make sure the state matches the real resources — reconciling the two — before retrying.