## 1. How do you design a DevOps platform for 100+ microservices?

**Answer:** Provide standardized CI/CD templates, centralized logging and monitoring, shared Helm charts, self-service infrastructure modules, and enforce guardrails through GitOps. Mini-case: our platform team built a Jenkins shared library, and all 100 services onboarded onto consistent pipelines with the same compliance checks built in.

**Detailed interview approach:**
Instead of a custom pipeline per service, I offer paved-road templates: versioned CI workflows, base images, Helm charts, Terraform modules, observability libraries, security policies, and a self-service catalog.

Teams own their own application configuration, while the platform team owns the supported contracts, upgrades, documentation, examples, and SLOs.

Guardrails run in CI and at admission, with clear error messages and an exception process that expires automatically. I design for tenant isolation, artifact and secret identity, cost attribution, and disaster recovery from day one.

I measure adoption and quality through onboarding time, pipeline reliability, deployment frequency, security findings, and support tickets. That feedback shapes the next version of the platform, rather than teams forking it to work around it.

