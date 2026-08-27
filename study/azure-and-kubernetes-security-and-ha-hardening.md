# Azure and Kubernetes Security and HA Hardening

Service mesh, layered container-to-container security, what actually makes a Kubernetes cluster highly available, Azure's DDoS/WAF/rate-limiting stack, Key Vault hardening, and broader Azure HA including storage redundancy tiers.

## Contents

1. [Service Mesh](#1-service-mesh)
2. [Securing container-to-container communication](#2-securing-container-to-container-communication)
3. [Building a highly available Kubernetes cluster](#3-building-a-highly-available-kubernetes-cluster)
4. [Azure DDoS Protection, rate limiting, and WAF](#4-azure-ddos-protection-rate-limiting-and-waf)
5. [Azure Key Vault security](#5-azure-key-vault-security)
6. [High availability in Azure](#6-high-availability-in-azure)

---

## 1. Service Mesh

A Service Mesh is an infrastructure layer that manages communication between microservices without requiring application code changes - the logic lives in a proxy sitting next to each service, not in the service's own code.

**What it provides:**

- **Traffic management** - routing, retries, load balancing, canary releases.
- **Security** - mutual TLS (mTLS), authentication and authorization between services.
- **Observability** - metrics, logs, distributed tracing across service calls.
- **Resilience** - timeouts, circuit breakers, and fault injection for testing failure handling.

**Common solutions:** Istio, Linkerd, Cilium.

**Typical architecture:**

```
Application Pod -> Sidecar Proxy -> Destination Sidecar -> Destination Application
```

Each service gets a sidecar proxy injected alongside it. Traffic between services goes through the proxies rather than directly - which is what lets the mesh apply mTLS, retries, and routing rules uniformly, without every application team implementing that logic themselves.

### Short interview answer

A Service Mesh manages service-to-service communication using sidecar proxies instead of application code. It handles traffic routing, retries, timeouts, mTLS, and observability transparently - the application just makes a normal network call, and the mesh intercepts it to apply policy and collect telemetry.

---

## 2. Securing container-to-container communication

Use multiple layers together - no single control is sufficient on its own:

1. **Network Policies** - restrict which Pods can talk to which other Pods (see NetworkPolicy content in `devops-interview-mixed-topics.md` §6).
2. **mTLS via a Service Mesh** - encrypts and authenticates traffic between services, so even Pods that *can* reach each other over the network still can't impersonate each other or read traffic in transit.
3. **Kubernetes RBAC and Service Accounts** - controls what each workload is allowed to do against the Kubernetes API itself.
4. **Namespaces** - isolate workloads logically, and are the scope boundary for NetworkPolicies and RBAC.
5. **Kubernetes Secrets or Azure Key Vault** - for any credentials the services need to authenticate to each other or to shared dependencies.
6. **Run containers as non-root and drop unnecessary Linux capabilities** - limits the blast radius if a container is compromised, even if network/identity controls are somehow bypassed.

```yaml
securityContext:
  runAsNonRoot: true
  capabilities:
    drop:
      - ALL
```

### Short interview answer

I layer several controls: Network Policies to restrict which Pods can reach which, mTLS through a service mesh to encrypt and authenticate the traffic that is allowed, RBAC and Service Accounts to control API access, namespaces for isolation, Key Vault or Kubernetes Secrets for credentials, and hardened Pod security settings - non-root, dropped capabilities - so a compromised container has as little to work with as possible even if it did get network access.

---

## 3. Building a highly available Kubernetes cluster

- **Multiple control plane nodes** - normally 3 or 5 (odd numbers, for etcd quorum).
- **Distribute nodes across Availability Zones** - both control plane and worker nodes, so a single zone failure doesn't take down the cluster.
- **Highly available etcd** - etcd is the cluster's source of truth; losing quorum on it is losing the cluster's ability to make any changes.
- **Multiple application replicas** - so a single Pod or node failure doesn't cause an outage.
- **Readiness and liveness probes** - so traffic only reaches healthy Pods, and unhealthy containers get restarted automatically.
- **Rolling updates** with suitable `maxUnavailable`/`maxSurge` - see `kubernetes-operations-and-stateful-workloads.md` §6 for the full mechanics.
- **Pod Disruption Budgets (PDBs)** - guarantee a minimum number of replicas stay available during voluntary disruptions like node maintenance.
- **Load Balancer/Ingress** for traffic distribution.
- **HPA and Cluster Autoscaler** - so capacity keeps pace with load.
- **Back up etcd**, and keep the cluster's own definition as infrastructure as code, so the control plane itself is recoverable.

### If a worker node fails

Kubernetes marks the node `NotReady`, removes its Pods' endpoints from any Services routing to them, and schedules replacement Pods on healthy nodes. Because multiple replicas were already spread across nodes, traffic continues flowing through the surviving replicas while the replacements come up.

### Short interview answer

HA in Kubernetes is a stack of measures working together: multiple control plane nodes with HA etcd spread across Availability Zones, multiple Pod replicas backed by readiness/liveness probes and PDBs, rolling updates tuned via `maxSurge`/`maxUnavailable`, HPA plus Cluster Autoscaler for capacity, and regular etcd backups. When a worker node fails, Kubernetes marks it `NotReady`, pulls its Pods out of Service endpoints, and reschedules them elsewhere - the surviving replicas keep serving traffic in the meantime.

---

## 4. Azure DDoS Protection, rate limiting, and WAF

Layered protection, applied in this order:

```
Azure DDoS Protection -> Rate Limiting -> WAF on Ingress
```

- **Azure DDoS Protection** - protects the network against volumetric DDoS attacks, at the network layer.
- **Rate limiting** - limits requests from individual clients; can be implemented at the Ingress Controller or an API Gateway.
- **WAF (Web Application Firewall)** - Azure Application Gateway WAF protects against common web attacks such as SQL Injection and XSS, at the application layer.

**Also layer in:**

- Network Policies (Pod-level restriction).
- HPA / Cluster Autoscaler (absorb legitimate traffic spikes so they aren't mistaken for or compounded by an attack).
- Azure Monitor / Prometheus / Grafana for visibility.
- Alerts for unusual traffic patterns.

### Short interview answer

I use Azure DDoS Protection at the network layer, rate limiting at the Ingress/API Gateway layer, and WAF for application-layer attacks like SQLi and XSS. On top of that, Network Policies, autoscaling, and monitoring/alerting on unusual traffic give defense in depth rather than relying on any single layer.

---

## 5. Azure Key Vault security

- **Enable Soft Delete** - deleted secrets, keys, or certificates are retained and recoverable during the retention period, instead of being gone immediately.
- **Enable Purge Protection** - prevents a *permanent* purge during that retention period, so even someone with delete permissions can't irreversibly destroy a secret before the retention window ends.
- **Use Managed Identity** instead of storing credentials in application code to authenticate to the Vault.
- **Use Azure RBAC with least privilege** - scope access to exactly the secrets/keys a given identity needs.
- **Enable diagnostic logs and monitoring** - so access to secrets is auditable.
- **Restrict network access** using Private Endpoints or firewall rules, rather than leaving the Vault reachable from the public internet.

### Short interview answer

I secure Key Vault with Soft Delete and Purge Protection so secrets can't be irrecoverably destroyed, Managed Identity instead of embedded credentials, least-privilege Azure RBAC, diagnostic logging for auditability, and private network access via Private Endpoints or firewall rules instead of public exposure.

---

## 6. High availability in Azure

Broader than just Kubernetes - applies across VMs, databases, and storage too:

- **Availability Zones**
- **Multiple VM instances / VMSS**
- **Multiple AKS nodes and Pod replicas**
- **Load Balancer / Application Gateway**
- **Autoscaling**
- **Highly available databases**
- **Storage redundancy**
- **Backup and disaster recovery**
- **Monitoring and alerting**

**Storage redundancy tiers:**

| Tier | Meaning |
| --- | --- |
| LRS | Locally Redundant Storage - copies within a single datacenter |
| ZRS | Zone Redundant Storage - copies across Availability Zones in one region |
| GRS | Geo Redundant Storage - copies to a secondary, paired region |
| GZRS | Geo-Zone Redundant Storage - zone redundancy in the primary region, plus geo-replication to a secondary region |

**For AKS specifically:** deploy node pools across Availability Zones, use multiple Pod replicas with readiness probes, HPA, Cluster Autoscaler, an Application Gateway (or other LB) in front, and a highly available database configuration behind it.

### Short interview answer

Azure HA spans compute, data, and storage: Availability Zones and VMSS/multiple AKS nodes for compute, HA database configurations, and a storage redundancy tier chosen for the failure domain that actually matters - LRS for datacenter-local redundancy up through GZRS when both zone and region redundancy are required - backed by autoscaling, load balancing, backup/DR, and monitoring across all of it.
