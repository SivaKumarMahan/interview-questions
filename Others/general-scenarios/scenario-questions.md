## 1. How do you design a DevOps platform for 100+ microservices?
**Answer:** Provide standardized CI/CD templates, centralized logging/monitoring, shared Helm charts, self-service infrastructure modules, and enforce guardrails via GitOps. Mini-case: Our platform team built a Jenkins shared library; all 100 services onboarded with consistent pipelines and compliance checks.

**Detailed interview approach:**
I offer paved-road templates rather than one custom pipeline per service: versioned CI workflows, base images, Helm charts, Terraform modules, observability libraries, security policies, and a self-service catalog. Teams own application configuration while the platform owns supported contracts, upgrades, documentation, examples, and SLOs. Guardrails run in CI and admission with clear errors and an expiring exception process. I design tenant isolation, artifact/secret identity, cost attribution, and disaster recovery from the start. Adoption and quality are measured through onboarding time, pipeline reliability, deployment frequency, security findings, and support tickets; feedback drives the next platform version instead of forcing teams to fork it.

