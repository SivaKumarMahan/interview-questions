# DevOps and Cloud Interview Preparation Roadmap

## 1. Foundations

Be able to explain and troubleshoot Linux processes, `systemd`, memory, disk I/O, permissions, TCP/UDP, DNS, and routing. For Git, explain branching, merge conflicts, rebase, rollback, protected branches, and release tags.

For CI/CD, describe why a stage failed, how you investigated it, and how the fix prevented recurrence.

## 2. Cloud and infrastructure

Think like an architect, not a list of services.

Be ready to compare compute scaling and spot/serverless trade-offs, database failover and cache eviction, how object storage actually behaves, VPC/VNet design, NAT and DNS latency, giving IAM only the access it needs, WAF controls, secret management, availability, disaster recovery, and cost.

Also be ready to map equivalent AWS, Azure, and GCP services and explain the differences that actually matter.

## 3. Kubernetes and containers

Be able to explain the pod lifecycle, `kubelet`, how the scheduler decides, controllers, networking, DNS, Services, Ingress, storage, probes, scaling, and security.

For a scenario like "the pod is Running but the application is unreachable," trace it through: DNS, then ingress/load balancer, then Service, then EndpointSlice, then pod readiness and the listening port.

Compare HPA, VPA, event-driven scaling, and node autoscaling, and know when each one is the wrong choice.

## 4. Microservices on Kubernetes

A production design should think about service boundaries and separate data ownership, small non-root container images, ConfigMaps and external secrets, Deployments, Services, Ingress or the Gateway API, environment overlays, TLS, authentication, autoscaling, probes, RBAC, NetworkPolicies, image signing and scanning, and centralized logs, metrics, and traces. Only add a service mesh once its traffic, identity, or monitoring features are worth the extra operational work.

## 5. Reliability, chaos, and root-cause analysis

Senior interviews test what you do when the dashboards look healthy but users are still failing. Follow one real request end-to-end, and compare logs, metrics, traces, deploy events, dependency health, DNS, identity, and network paths.

A chaos experiment needs a hypothesis, a small blast radius, clear abort conditions, observability, an owner, and a rollback plan. A partial Terraform apply or database replication lag needs a recovery that protects state and data — not a blind retry.

## 6. Storytelling and impact

Use a clear structure: context and scale, your responsibility, the symptoms and evidence, how you investigated, the decision and fix, how you verified it, how you prevented it recurring, and a measurable result. "We restarted it" is a weak answer.

A stronger one sounds like: "We correlated 502 errors with a readiness-probe change, corrected the thresholds, rolled back safely, load-tested the fix, and cut peak error rate by 40%." Be honest about your actual role and only use numbers you can defend if asked.

## 7. Modern operations mindset

- **GitOps and platform engineering** focus on a reviewed desired state, continuously reconciling the live system to match it, safe self-service, and guardrails.
- **Monitoring** reports the signals you already know to watch for. **Observability** helps you investigate failures you didn't anticipate, by correlating metrics, logs, and traces.
- **Deployment engineering** means progressive delivery, health gates, rollback, and database compatibility — not just running `kubectl apply`.
- **Production failures** can come from `kubelet`, CoreDNS, gaps in monitoring data, certificates, identity, or a dependency — even while the high-level dashboard still looks green.

## 8. Introduction, daily work, and technology stack

Do not recite a generic biography. Give a 60–90 second answer tailored to your real experience:

```text
current role and years of relevant experience
-> product/domain and scale
-> cloud and application stack
-> your ownership across CI/CD, IaC, containers, Kubernetes and operations
-> one measurable reliability, delivery, security or cost result
```

A credible day-to-day answer can cover reviewing pull requests and pipeline results, building or promoting artifacts that don't change once built, changing Terraform through reviewed plans, supporting Kubernetes/EC2 deployments, investigating alerts and incidents, improving dashboards and runbooks, patching vulnerabilities, controlling cloud cost, and coordinating releases.

Mention only tools and responsibilities you have actually used, and distinguish personal work from team ownership.
Describe the application stack in layers: client/frontend, API or Java framework, synchronous and asynchronous integration, database/cache, build tool, artifact/container registry, compute platform, CI/CD, IaC, secrets, and observability.

For example, replace placeholders with your real stack rather than claiming all of them:
```text
React -> Java/Spring Boot REST services -> PostgreSQL/Redis/Kafka
Maven -> Docker/ECR -> EC2 or EKS
Jenkins/GitHub Actions -> Terraform -> CloudWatch/Prometheus/Grafana
```

When asked which cloud, CI/CD tool, or services you use, lead with the primary platform and workflow, then name services by purpose. Explain one real deployment or incident to demonstrate depth instead of presenting a long product list.
