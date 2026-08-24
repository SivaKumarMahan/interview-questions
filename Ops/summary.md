# Operations Practices Summary

DevOps, GitOps, MLOps, and AIOps all rely on automation, feedback, measurement, version control, security, and continuous learning. Each one solves a different problem in the lifecycle.

| Practice | Primary focus | Typical work |
| --- | --- | --- |
| **DevOps** | Software delivery and operations | CI/CD, IaC, configuration, observability, collaboration, reliability |
| **GitOps** | Declarative infrastructure/application delivery | Git as the source of truth, pull-based reconciliation (making the live system match Git), drift detection, policy, rollback |
| **MLOps** | Machine-learning lifecycle | Data/versioning, training pipelines, registry, deployment, monitoring, drift and retraining |
| **AIOps** | Intelligent IT operations | Event correlation, anomaly detection, root-cause help, forecasting, noise reduction, safe automated fixes |

DevOps builds reliable delivery. MLOps extends those same practices to data and models: it adds feature and data lineage, experiment tracking, a model registry, serving, drift and bias detection, and retraining.

AIOps applies analytics and machine learning to operational monitoring data so teams can detect and prioritize issues faster. It has to explain its evidence clearly, ask a human before any risky action, take feedback, and limit what it can automate on its own. GitOps keeps the declared state versioned and continuously reconciled against the live system.

A practical learning path: start with Linux, networking, Git, cloud, security, SQL/Python, CI/CD, containers, Kubernetes, and Terraform/Ansible, then add monitoring and logging. From there, add data pipelines and model lifecycle work for MLOps, and statistics, event correlation, and automation guardrails for AIOps.

None of these practices replaces another. Together they cover building, delivering, operating, learning, and improving.

## AIOps Incident Flow: Kubernetes CPU Throttling

AIOps means applying analytics and machine learning to IT operations. Its job is to improve monitoring and response, not to replace the whole software-delivery lifecycle. A practical CPU-throttling flow looks like this:

1. **Prometheus** collects container CPU usage and throttling counters.
2. **Alerting** detects sustained throttling and attaches context: the service, cluster, deployment, and any recent changes.
3. The **AIOps layer** checks the signal against recent deployments, config changes, traffic increases, node pressure, and similar past incidents.
4. It **recommends a limited action**, such as restoring known-good resource requests, scaling replicas, or rolling back a bad release.
5. An **approved runbook** applies the change, watches the rollout, and confirms that throttling, latency, and errors return to normal.
6. The platform **notifies the team** and stores the evidence, decision, action, and result for audit and future learning.

Automatic fixes need confidence thresholds, an identity with only the access it needs, limits on how big a change can be, human approval for risky actions, a rollback path, and a check afterward. Increasing CPU blindly can hide inefficient code or just push the pressure onto another dependency.

Tools like PagerDuty, Datadog, Dynatrace, ManageEngine, Prometheus, Grafana, and various automation platforms can all play a part, but AIOps is an approach to running operations, not one single product.

## AgentOps

Running AI agents in production takes more than just calling an LLM. **AgentOps** covers multi-step and tool-calling workflows, scheduling, retries, state and memory, observability, evaluation, cost, security, and human approval.

An orchestration platform can run branches and retries on Kubernetes and keep track of workflow state, but production also needs prompt and tool versioning, trace correlation, redaction of sensitive data, permission boundaries, quality evaluation, timeout and budget limits, a safe fallback, and an auditable approval path.

Python, Kubernetes, and an orchestrator such as Flyte make a solid open-source learning stack. The architecture matters more than any one tool.

## Managing a Large Kubernetes Fleet

Once you're running tens or hundreds of clusters, treat them as a managed fleet rather than one-off installs:

- **Cluster API** or a cloud fleet service standardizes how clusters get created, upgraded, and retired across accounts, subscriptions, regions, and environments.
- **Terraform** manages cloud and cluster infrastructure through reviewed modules, with separate state per team and blast radius.
- **Argo CD** or **Flux** deploys versioned desired state. **Helm** or **Kustomize** provides reusable application packaging.
- **Vault** or an external-secrets system injects secrets so plaintext values never get committed.
- A **service mesh** is worth adopting only when its mTLS, policy, and traffic-control benefits outweigh the extra operational cost.
- **Central metrics, logs, traces, dashboards, and alert routing** give fleet-wide visibility while still keeping each cluster isolated.

Fleet operations also need a version-skew policy, upgrade rings, admission policy, tenant isolation, capacity and cost reporting, tested backup and restore, and a break-glass process. The goal is repeatable control with a small blast radius per change, not one highly privileged system that can touch every cluster with no safeguards.