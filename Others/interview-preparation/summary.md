# DevOps and Cloud Interview Preparation Roadmap

## 1. Foundations

Be able to explain and troubleshoot Linux processes, `systemd`, memory, disk I/O, permissions, TCP/UDP, DNS, and routing. For Git, explain branching, merge conflicts, rebase, rollback, protected branches, and release tags. For CI/CD, describe why a stage failed, how you investigated it, and how the fix prevented recurrence.

## 2. Cloud and infrastructure

Think like an architect rather than listing services. Compare compute scaling and spot/serverless trade-offs, database failover and cache eviction, object storage behavior, VPC/VNet design, NAT and DNS latency, IAM least privilege, WAF controls, secret management, availability, disaster recovery, and cost. Be ready to map equivalent AWS, Azure, and GCP services while explaining meaningful differences.

## 3. Kubernetes and containers

Explain the Pod lifecycle, `kubelet`, scheduler decisions, controllers, networking, DNS, Services, Ingress, storage, probes, scaling, and security. For a scenario such as "the Pod is Running but the application is unreachable," trace DNS -> ingress/load balancer -> Service -> EndpointSlice -> Pod readiness and listening port. Compare HPA, VPA, event-driven scaling, and node autoscaling and state when each is inappropriate.

## 4. Microservices on Kubernetes

A production design should consider service boundaries and separate data ownership, small non-root container images, ConfigMaps and external secrets, Deployments/Services/Ingress, environment overlays, TLS, authentication, service mesh only when justified, autoscaling, probes, RBAC, NetworkPolicies, image signing/scanning, centralized logs, metrics, and distributed traces.

## 5. Reliability, chaos, and root-cause analysis

Senior interviews test what happens when normal dashboards look healthy but users still fail. Follow one real request, correlate logs, metrics, traces, deploy events, dependency health, DNS, identity, and network paths. Chaos experiments require a hypothesis, small blast radius, abort conditions, observability, owner, and rollback. Terraform partial applies and database replication lag require state/data-safe recovery rather than blind retries.

## 6. Storytelling and impact

Use a clear structure: context and scale -> responsibility -> symptoms and evidence -> investigation -> decision and fix -> verification -> prevention -> measurable result. "We restarted it" is weak. A stronger answer is: "We correlated 502 errors with a readiness-probe change, corrected thresholds, rolled back safely, load-tested the fix, and reduced peak error rate by 40%." Be honest about your role and the numbers you can defend.

## 7. Modern operations mindset

- **GitOps and platform engineering** focus on reviewed desired state, reconciliation, safe self-service, and guardrails.
- **Monitoring** reports known signals; **observability** helps investigate unknown failures through correlated metrics, logs, and traces.
- **Deployment engineering** includes progressive delivery, health gates, rollback, and database compatibility - not only `kubectl apply`.
- **Production failures** can involve `kubelet`, CoreDNS, telemetry gaps, certificates, identity, or dependencies even when a high-level dashboard remains green.

## 8. Introduction, daily work, and technology stack

Do not recite a generic biography. Give a 60–90 second answer tailored to your real experience:

```text
current role and years of relevant experience
-> product/domain and scale
-> cloud and application stack
-> your ownership across CI/CD, IaC, containers, Kubernetes and operations
-> one measurable reliability, delivery, security or cost result
```

A credible day-to-day answer can cover reviewing pull requests and pipeline results, building or promoting immutable artifacts, changing Terraform through reviewed plans, supporting Kubernetes/EC2 deployments, investigating alerts and incidents, improving dashboards/runbooks, patching vulnerabilities, controlling cloud cost, and coordinating releases. Mention only tools and responsibilities you have actually used, and distinguish personal work from team ownership.

Describe the application stack in layers: client/frontend, API or Java framework, synchronous and asynchronous integration, database/cache, build tool, artifact/container registry, compute platform, CI/CD, IaC, secrets, and observability. For example, replace placeholders with your real stack rather than claiming all of them:

```text
React -> Java/Spring Boot REST services -> PostgreSQL/Redis/Kafka
Maven -> Docker/ECR -> EC2 or EKS
Jenkins/GitHub Actions -> Terraform -> CloudWatch/Prometheus/Grafana
```

When asked which cloud, CI/CD tool, or services you use, lead with the primary platform and workflow, then name services by purpose. Explain one real deployment or incident to demonstrate depth instead of presenting a long product list.
