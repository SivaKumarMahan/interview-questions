# Kubernetes: Networking and Traffic Routing

> Services, Ingress, Gateway API, ALB, API gateways, service mesh, and NetworkPolicies.

## Key Concepts

### Service Types

- **ClusterIP:** A stable internal IP. This is the default Service type.
- **NodePort:** Opens a port on every node and forwards it to the Service.
- **LoadBalancer:** Asks the cloud provider for an external or internal load balancer.
- **ExternalName:** Returns a configured external DNS name.
- **Headless Service:** Uses `clusterIP: None` so clients can discover endpoints directly.

`port` is the Service's own port. `targetPort` is the port on the destination pod. `nodePort` is the optional port exposed on cluster nodes.

### Service Types and External Access

A Service gives a changing set of pods one stable virtual IP and DNS name, and load-balances traffic to whichever pods are ready, based on label selectors.

- `ClusterIP`: an internal-only virtual IP, and the default type.
- `NodePort`: opens a fixed port on every node and forwards it to the Service. Useful for specific integrations or for learning, but exposing nodes directly is rarely the right choice in production.
- `LoadBalancer`: asks the cloud integration to provision or attach an external or internal load balancer to the Service.
- `ExternalName`: returns a DNS CNAME. It doesn't proxy traffic or do any health checking.

Ingress is an HTTP/HTTPS routing API. It needs an Ingress controller such as **NGINX**, **Traefik**, or a cloud-provided controller to actually work. It can bring host/path routing and TLS for many Services together in one place.

Use a LoadBalancer Service for one application or one Layer-4 protocol. Use Ingress when you need shared Layer-7 routing across several Services. When something's wrong, check the controller class, listener, certificate/SNI, host/path rules, Service port, EndpointSlice, readiness, health probes, and network policy.

### Ingress and DNS

Ingress defines HTTP/HTTPS routing rules and needs an Ingress controller to work. CoreDNS provides DNS inside the cluster.

When routing breaks, troubleshoot from the inside out: pod readiness, endpoint slices, Service selectors and ports, DNS, Ingress rules/controller, then the load balancer and firewall.

### NetworkPolicy

`NetworkPolicy` restricts what traffic a pod can send or receive, as long as the CNI plugin supports it.

- With no policy selecting a pod, all traffic is allowed by default.
- A policy isolates a pod only in the directions listed in `policyTypes`, or implied by its rules.
- To block all egress from a pod, select it, include `Egress` in `policyTypes`, and add no allowed egress rules.

Best practice: start with default-deny policies, then add explicit allows for DNS and whatever application traffic is actually needed.

### NetworkPolicy defaults and default-deny

NetworkPolicy restricts Pod ingress and egress when supported by the CNI plugin.

- With no selecting policy, traffic is allowed by default.
- A policy isolates a selected Pod only for the directions listed in `policyTypes` or inferred from its rules.
- To deny all egress, select the Pods, include `Egress` in `policyTypes`, and provide no allowed egress rules.
- Use default-deny policies and add explicit allows for DNS and required application flows.

### Troubleshooting Network and 503 Failures

When you see a network failure or a 503, check in this order: pod readiness, Service selectors, endpoint slices, `port`/`targetPort`, DNS, NetworkPolicies, Ingress controller logs, health probes, load balancer rules, routes, and firewalls.

### Operations Notes

- A Service selects ready Pods by labels. `ClusterIP` is internal-only. `NodePort` exposes a port on every node. A headless Service (`clusterIP: None`) returns Pod endpoints directly instead of a single virtual IP, which is common for StatefulSets. Ingress and Gateway resources define HTTP(S) routing, but they need an installed controller or data plane to actually implement that routing.

### Traffic Routing on EKS: ALB, Ingress, Gateway API, API Gateway, Service Mesh, and Network Policies

ALB, Ingress, Gateway API, API Gateway, Service Mesh, and Network Policies all seem to route traffic, and the features overlap — most can do HTTP routing and TLS termination, and several use Nginx or Envoy as the engine.

The clarity comes not from "what does it do" but from "why does it exist." Each layer was born to solve a production problem the previous setup could not handle.
**2026 context:** In March 2026, Ingress NGINX moved into formal retirement (no more security patches). Kubernetes 1.36 (released April 22, 2026) marks the shift to **Gateway API** as the official successor to Ingress.

Ingress itself is not deprecated, but new investment should go to Gateway API.

#### ALB vs a LoadBalancer Service

Your service runs in a pod. You can hit it from inside the cluster, but nobody outside can reach it.

So you create a **LoadBalancer Service** and Kubernetes provisions a real cloud load balancer with a public URL. It works perfectly — until you have 10 services and 10 cloud load balancers, each on your AWS bill every month. **LoadBalancer Service solved external access, but one per service does not scale.**

So you put one **AWS Application Load Balancer (ALB)** in front of everything. ALB is an AWS-managed load balancer that runs outside your cluster and routes to many services by path or host — `/api/products` to the product service, `/api/orders` to the order service.

One AWS load balancer instead of ten.

The catch: you configure the ALB through the AWS Console or Terraform, so developers cannot ship a new microservice without an infrastructure ticket, and the routing rules (outside the cluster) drift from the cluster's YAML. **ALB cut costs, but it took routing control away from your team.**

#### Kubernetes Ingress and the Ingress Controller

Ingress is a Kubernetes resource that defines routing rules in YAML. Developers commit an Ingress file alongside their service code, so routing lives where the code lives.

But Ingress is just a config file — something has to read and execute it. That something is the **Ingress Controller**: Nginx Ingress, Traefik, or the AWS Load Balancer Controller.

On EKS, most teams use the **AWS Load Balancer Controller**. You write Ingress YAML; the controller talks to AWS and provisions an ALB with the right rules automatically.

You get the cost benefit of one ALB and the YAML-first control of Kubernetes. **ALB without Ingress was unmanageable from the cluster side. Ingress fixed that.**

#### Why Gateway API exists (Ingress limitations)

Ingress was the default for ten years, but it had limits:

- It only handled HTTP and HTTPS. Routing TCP or UDP needed vendor-specific extensions.
- Advanced features (canary deployments, traffic splitting, header-based routing) required many annotations, and each controller had its own syntax — migrating meant rewriting all of them.
- The platform team and application team shared the same Ingress resource, with no clean ownership separation.
- As of March 2026, Ingress NGINX is no longer maintained.

So the Kubernetes community built **Gateway API**.

#### What Gateway API is and how it differs from Ingress

Gateway API is the official successor to Ingress (GA in November 2023, with adoption accelerating through 2025–2026). It splits the old Ingress resource into three role-oriented pieces:

- **GatewayClass** — defines the type of underlying infrastructure. The platform team owns this.
- **Gateway** — the actual entry point; listens on ports and handles TLS. Cluster operators manage these.
- **HTTPRoute** (and **TCPRoute**, **GRPCRoute**) — the actual routing rules. Application developers own these.

Each team manages what it should, with no argument about who owns the Ingress. Gateway API also supports L4 protocols natively (TCP, UDP, gRPC) and has built-in traffic splitting and header-based routing without annotations.

On EKS, the AWS Load Balancer Controller supports Gateway API as of 2026: you write Gateway and HTTPRoute resources, the controller provisions an ALB, and you get the same cost benefits as Ingress with a cleaner model.

**Guidance:** For a new EKS project in 2026, use Gateway API. If you run Ingress in production today, you have time — Ingress is stable and not deprecated — but the future investment is Gateway API.

#### Service mesh: service-to-service traffic

Now your microservices talk to each other inside the cluster via ClusterIP Services. It works until something fails, and then you have no idea which call broke or whether pod-to-pod traffic was even encrypted.

Some pods retry forever, some give up immediately, and every team writes retry logic differently. You want mTLS between every service, consistent retries, and distributed tracing.

So you install a **service mesh** — Istio, Linkerd, or Consul. It injects a sidecar proxy into every pod; all pod-to-pod traffic goes through the sidecar, which handles mTLS, retries, timeouts, tracing, and traffic splitting.

Application code stays clean while the mesh handles the plumbing. **Service-to-service traffic was a black box. Service mesh fixed that.**

#### Network Policies: locking down pod-to-pod traffic

By default, any pod can talk to any other pod — your frontend pod can reach your payments database, your build pod can reach your auth service. If one pod is compromised, the attacker can move laterally to anything.

So you use **NetworkPolicies**, which define which Pods may communicate. For example, you can allow only the order service to reach the payments database and allow the frontend to reach only the API service.

**The problem was a flat cluster network. NetworkPolicies limit communication when the installed network plugin enforces them.**

#### API Gateway: managing what your APIs do

Your platform works — internal traffic is meshed, network policies lock things down, external traffic comes in through Gateway API. Then the business launches a mobile app, a partner wants API access, a third-party developer wants to integrate.

Now you need API keys, per-customer rate limits, and centralized JWT validation.

If you add auth and rate-limiting code to every service, six microservices become six different implementations of the same thing, and per-customer limits (Customer A: 1000 req/sec, Customer B: 100, free tier: 10) get scattered everywhere.

So you add an **API Gateway** — Kong, APISIX, AWS API Gateway, or Tyk. It sits between your Gateway/Ingress and your microservices and handles everything that is not business logic: API key validation, JWT validation, per-customer rate limiting, request transformation, response caching, usage analytics.

A request comes in, the gateway checks the API key, sees the customer's plan allows 1000 req/sec, and forwards to the right service. **API-level concerns scattered across services made the platform fragile. API Gateway fixed that.**

#### Gateway API vs API Gateway (do I need both?)

The names are almost identical but they are not the same thing:

- **Gateway API** is a Kubernetes specification for routing traffic. It replaces Ingress and handles north-south routing *into* the cluster.
- **API Gateway** is an architectural pattern for API management — auth, rate limiting, API keys, transformations, analytics.

You can implement an API Gateway *using* Gateway API resources (Kong and Envoy Gateway support both), but Gateway API on its own does not give you API key management or per-customer rate limits — that is API Gateway territory.

The simple rule: **Gateway API gets traffic into the cluster; API Gateway manages what your APIs do once it is in.** In 2026 the line is blurring (Kong, Envoy Gateway, and APISIX do both), but conceptually they solve different problems.

#### Production patterns on EKS

There are three real patterns, each fitting a different stage of your platform.

**Pattern 1 — Internal app or simple frontend.** A React frontend and a few microservices behind it; the frontend is the only client. No third-party API consumers, no API keys.

```text
Internet → AWS ALB → Gateway API (ALB Controller) → Microservices
```

The AWS Load Balancer Controller provisions the ALB from your Gateway and HTTPRoute resources. One YAML, one AWS bill.

This is what ~80% of EKS workloads look like — no API Gateway, no service mesh. **The trap:** engineers add an Nginx "API Gateway" Deployment here because a tutorial said so. It is a reverse proxy with extra steps and a monthly cost.

**Pattern 2 — Public APIs for mobile or third-party clients.** Now you have a mobile app and partners integrating. You need API keys, per-customer rate limits, and centralized JWT validation.

```text
Internet → AWS ALB → Gateway API → API Gateway (Kong / APISIX / Envoy Gateway) → Microservices
```

Gateway API still gets traffic into the cluster; what is new is the API Gateway between it and your services (deployed in-cluster as a Deployment with 2+ replicas). Customer A gets 1000 req/sec, Customer B gets 100, free tier gets 10 — none of that logic touches your microservices.

Most teams skip this until they have already polluted every service with auth code, then spend a quarter ripping it out.

**Pattern 3 — Scale, with internal traffic too.** Mobile clients hit public APIs, the frontend hits internal APIs, and services talk constantly. You need different policies for different traffic and observability across all of it.

```text
Internet
   ↓
AWS ALB (TLS, WAF)
   ↓
Gateway API
   ↓
   ├─→ /api/public/*   → API Gateway → Microservices (with Istio sidecars)
   └─→ /api/internal/* ─────────────→ Microservices (with Istio sidecars)
                                              ↑
                                     Network Policies enforce
                                     pod-to-pod access rules
```

Public traffic goes through the API Gateway (auth, rate limits, transformations). Internal frontend traffic skips the gateway — it is trusted, latency-sensitive, and needs no API key validation.

Service-to-service traffic goes through the service mesh (mTLS, distributed tracing). Network Policies enforce who can talk to whom across the cluster.

Each layer does one job well.

#### How to know which pattern you need

Ask one question: **who is calling your APIs?**

- Only your own frontend → **Pattern 1**.
- A mobile app or third-party clients → **Pattern 2**.
- 50+ services where you care about mTLS, distributed tracing, and zero-trust networking → **Pattern 3**.

Most teams skip Pattern 1 because they read a microservices blog, then over-engineer toward Pattern 3 because they read a Netflix blog. The right answer is almost always one step simpler than what you think you need.

#### Common mistakes (get the names right)

- A Nginx Deployment routing traffic is **not** an API Gateway. It is a reverse proxy.
- An Ingress Controller is **not** a load balancer. It is a router that sits behind one.
- A service mesh is **not** an API Gateway. It handles east-west (service-to-service) traffic; API Gateway handles north-south (internet-to-service) traffic.
- Network Policies are **not** a firewall. They are pod-level traffic rules enforced by your CNI.

#### Should I migrate from Ingress to Gateway API in 2026?

- **New EKS project:** yes — use Gateway API from day one.
- **Running Ingress with the AWS Load Balancer Controller:** you have time. Ingress is stable and not deprecated; AWS supports both.
- **Using Ingress NGINX specifically:** plan your migration — the project is in retirement as of March 2026 with no more security patches.

The migration path is straightforward: Ingress and Gateway API can run side by side. Move new services to Gateway API and migrate old ones one at a time.

#### Frequently asked questions

- **Is API Gateway the same as Kubernetes Ingress?** No. Ingress (and its successor Gateway API) is a Kubernetes resource for routing external traffic to services. API Gateway is a pattern for API-level concerns like authentication, rate limiting, and API keys. Both can route HTTP, but they solve different problems.
- **Is API Gateway the same as Gateway API?** No, despite the near-identical names. Gateway API is a Kubernetes specification that replaces Ingress. API Gateway is an architectural pattern. You can implement an API Gateway using Gateway API resources, but they are not the same thing.
- **Do I need both ALB and Ingress on EKS?** Yes. ALB is the AWS-managed load balancer; Ingress (or Gateway API) is the Kubernetes resource that tells the AWS Load Balancer Controller how to configure the ALB. They work together.
- **Is Ingress NGINX deprecated?** It entered formal retirement in March 2026. It still works, but no new security patches will be released. Plan migration to Gateway API or another supported Ingress Controller.
- **Can I use AWS API Gateway with EKS?** Yes, via a Network Load Balancer or VPC Link. But most EKS teams prefer in-cluster API Gateways like Kong, APISIX, or Envoy Gateway because they are easier to configure with Kubernetes-native tools.
- **Do I need a service mesh if I have an API Gateway?** They solve different problems. API Gateway handles north-south traffic (internet to your services); service mesh handles east-west traffic (service to service). Most teams need both at scale.
- **What is the difference between Gateway API and API Gateway in Kubernetes?** Gateway API is a Kubernetes specification for routing external traffic into the cluster (it replaces Ingress). API Gateway is a pattern handling authentication, rate limiting, and API management. Some tools (Kong, Envoy Gateway) implement both.

#### Takeaway

Each layer between your user and your pod exists because the previous setup was not enough:

- **ALB** gets traffic to your cluster.
- **Gateway API (or Ingress)** gets traffic into your services.
- **Service Mesh** secures and observes pod-to-pod traffic.
- **Network Policies** enforce who can talk to whom.
- **API Gateway** manages what your public APIs do.

## Interview Questions

### 1. Explain port, targetPort and nodePort in kubernetes?

In Kubernetes, `port` is the port a Service exposes inside the cluster. `targetPort` is the port on the container that traffic actually gets sent to. `nodePort` is the port opened on each worker node so the service can be reached from outside the cluster.

Example: request → `nodePort` (30080) → service `port` (80) → container `targetPort` (8080).

- **`port`:** The port where the Service is exposed inside the cluster. Other pods reach the service through this port.
- **`targetPort`:** The port on the pod's container that the service forwards traffic to. This is where the application actually listens.
- **`nodePort`:** A port opened on every worker node. It lets you reach the service from outside the cluster using `<node-ip>:<nodePort>`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-web-service
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - port: 80           # Service port (cluster-internal)
    targetPort: 8080   # Pod port (container)
    nodePort: 30080    # Node port (external)
```

**NodePort range (by default):** `30000–32767`.

### 2. What are the Kubernetes Service types (ClusterIP, NodePort, LoadBalancer, ExternalName, Headless)?

**Quick definitions:**

- **ClusterIP:** stable internal virtual IP; the default Service type.
- **NodePort:** exposes a port on every node and forwards to the Service.
- **LoadBalancer:** requests an external or internal cloud load balancer.
- **ExternalName:** returns a configured external DNS name.
- **Headless Service:** uses `clusterIP: None` for direct endpoint discovery.
- `port` is the Service port, `targetPort` is the destination Pod port, and `nodePort` is the optional port exposed on cluster nodes.

#### 13.1 ClusterIP Service

> "ClusterIP is the default Kubernetes Service type. It exposes an application only inside the cluster using a stable virtual IP. Other pods can access the application through the Service, but it isn't reachable from outside the cluster."

```
Pod A ----> ClusterIP Service ----> Pod B
```

**Use cases:** database services, internal APIs, backend microservices.

#### 13.2 NodePort Service

> "NodePort exposes the application on a fixed port on every Kubernetes node. Traffic received on that port is forwarded to the Service and then to the target pods."

```
Client
   |
NodeIP:30080
   |
NodePort Service
   |
Pods
```

```yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080
```

**Use cases:** testing, development environments, labs.

#### 13.3 LoadBalancer Service

> "A LoadBalancer Service creates a cloud load balancer in providers like Azure, AWS, or GCP. It exposes the application externally and distributes traffic across healthy pods."

```
Internet
    |
Azure Load Balancer
    |
Kubernetes Service
    |
Pods
```

**Use case:** production web applications and APIs.

#### 13.4 ExternalName Service

> "ExternalName doesn't create a proxy or load balance traffic. Instead, it maps a Kubernetes Service to an external DNS name using a DNS CNAME record."

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  type: ExternalName
  externalName: mysql.company.com
```

Applications connect to:

```
mysql.default.svc.cluster.local
```

which resolves to:

```
mysql.company.com
```

**Use case:** accessing external databases or third-party services without changing application code.

#### 13.5 Headless Service

> "A Headless Service is created by setting `clusterIP: None`. Kubernetes doesn't assign a virtual IP. Instead, DNS returns the IP addresses of the individual pods, allowing clients to communicate directly with them."

```yaml
spec:
  clusterIP: None
```

```
Headless Service
        |
DNS
        |
Pod-0
Pod-1
Pod-2
```

**Use cases:** StatefulSets, databases, Kafka, Cassandra, Elasticsearch.

#### 13.6 Difference between port, targetPort and nodePort

```yaml
ports:
- port: 80
  targetPort: 8080
  nodePort: 30080
```

- **port** -> the port exposed by the Kubernetes Service.
- **targetPort** -> the port on which the container inside the pod is listening.
- **nodePort** -> the port opened on every Kubernetes node (used only with NodePort or LoadBalancer Services).

Flow:

```
Client
   |
NodeIP:30080 (nodePort)
   |
Service:80 (port)
   |
Pod:8080 (targetPort)
```

#### 13.7 Follow-up: which Service type do you use in AKS?

> "For internal communication between microservices, I use ClusterIP because it keeps services accessible only within the cluster. For production applications that need internet access, I use LoadBalancer, which provisions an Azure Load Balancer automatically. I rarely use NodePort in production because it exposes ports directly on every node and is mainly useful for testing or when an external load balancer isn't available."

#### 13.8 Quick comparison

| Service Type | Accessible From | Common Use |
|---|---|---|
| ClusterIP | Inside the cluster only | Internal microservices |
| NodePort | External via NodeIP:Port | Development and testing |
| LoadBalancer | Internet or internal cloud load balancer | Production applications |
| ExternalName | External DNS name | External databases or APIs |
| Headless | Direct pod IPs via DNS | StatefulSets and databases |

#### 13.9 One-line interview summary

- **ClusterIP** -> internal communication within the cluster.
- **NodePort** -> exposes the application on a port of every node.
- **LoadBalancer** -> creates a cloud load balancer for external access.
- **ExternalName** -> maps a Service to an external DNS name.
- **Headless Service** -> no virtual IP; DNS returns individual pod IPs for direct access.

### 3. what is port forwarding in kubernetes?

Port forwarding lets you reach a single pod directly from your local machine. You forward a port on your machine to a port on the pod. It's mainly used for debugging or for reaching an app inside a pod without setting up a full service.

```bash
kubectl port-forward <pod-name> <local-port>:<pod-port>
```

Example:

```bash
kubectl port-forward my-pod 8080:80
```

This forwards local port `8080` to port `80` on the pod named `my-pod`.

You can then reach the app by opening `http://localhost:8080` in a browser, or by using `curl`.

**Use Cases:**

- **Debugging:** Look at logs or interfaces running inside a pod.
- **Testing:** Try out a service without exposing it externally.
- **Accessing Databases:** Connect to a database running in a pod to manage it or run queries.

**Limitations:**

- Port forwarding only lasts as long as the `kubectl` command keeps running.
- It works only against pods, not directly against services or deployments.
- You need `kubectl` access to the cluster and permission to reach the pod.

**Example Command:**

```bash
kubectl port-forward deployment/my-app 9090:80
```

This forwards local port `9090` to port `80` on the pods managed by the `my-app` deployment.

You can now reach the app at `http://localhost:9090`.

### 4. You need TCP and UDP on the same port. How do you configure it?

**Answer:**

Define two Service ports with the same number but different protocols and unique names, as long as your cloud load balancer supports this:

```yaml
ports:
- name: dns-tcp
  port: 53
  targetPort: 53
  protocol: TCP
- name: dns-udp
  port: 53
  targetPort: 53
  protocol: UDP
```

A container can bind the same numeric port for TCP and UDP because they're separate sockets under the hood. A standard HTTP Ingress isn't built for generic UDP traffic, so use a LoadBalancer Service or a Gateway/controller that explicitly supports both protocols.

I confirm how the cloud provider handles health checks for this setup, check the firewall/security group covers both protocols, verify endpoints, and test with `dig` over both UDP and TCP. Passing on one protocol doesn't mean the other one works too.

### 5. What is the difference between a Route and an Ingress?

**Answer:**

Ingress is the standard Kubernetes API for HTTP(S) routing to Services, implemented by an Ingress controller. A Route is mainly an OpenShift resource that exposes a Service through the OpenShift router and adds some OpenShift-specific TLS/traffic behavior.

They serve a similar purpose — routing traffic into the cluster — but they aren't interchangeable, portable APIs. For a new, portable Kubernetes design, I use a supported Ingress controller or the Gateway API, configure TLS, host/path routing, health checks, and security policy, then test the external request path end to end.

### 6. How do you restrict pod-to-pod communication in a Kubernetes cluster?

To restrict pod-to-pod traffic in a cluster, use **Network Policies**. A Network Policy is a rule that controls which pods can talk to which, based on labels, namespaces, and ports.

Here's how to set one up:

1. **Check that your CNI supports Network Policies.**
   - Your cluster's network plugin needs to enforce them — for example Calico, Cilium, or Weave.
2. **Write the policy.**
   - Create a Network Policy YAML file that spells out the allowed traffic. Here's an example that only lets frontend pods reach backend pods:

   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-frontend-to-backend
     namespace: default
   spec:
     podSelector:
       matchLabels:
         role: backend         # Target backend pods
     policyTypes:
     - Ingress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             role: frontend    # Allow only frontend pods
       ports:
       - protocol: TCP
         port: 80
   ```

   - Here, only pods labeled `role: frontend` can reach pods labeled `role: backend`, and only on port 80.
3. **Apply the policy:**

   ```bash
   kubectl apply -f network-policy.yaml
   ```

4. **Test it.**
   - Confirm that allowed pod-to-pod traffic still works, and that traffic that should be blocked actually is.
5. **Add more policies as needed.**
   - Different pods and namespaces will need their own rules.
6. **Keep reviewing your policies.**
   - Check that they still match how the application works, and update them as the architecture changes.

Network Policies are the main tool for restricting pod-to-pod traffic. Used well, they improve security and give you clear control over how traffic flows between parts of your application.

### 7. How do you restrict communication between two Pods in the same namespace?

**Answer:**

Without any policy, pods can generally reach each other freely. I label the workloads, apply a default-deny rule, then allow the target to receive traffic only from the approved source label and port. If egress is also isolated, the source's egress rule needs to allow the destination too.

```yaml
spec:
  podSelector: { matchLabels: { app: database } }
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector: { matchLabels: { app: api } }
    ports: [{ protocol: TCP, port: 5432 }]
```

I confirm the CNI actually enforces this, then test that the API can reach the database, an unrelated pod cannot, and DNS/monitoring still work. Labels are a security-relevant input, so I make sure they're protected by admission control or governance. I monitor denied flows where that's supported, and keep policies in version control.

### 8. How do you design and debug NetworkPolicies between namespaces?

**Answer:**

I start by listing out the traffic flows that need to exist, then confirm the CNI actually enforces NetworkPolicy, and make sure namespaces are labeled reliably. I apply a default-deny rule for ingress and egress first, then add explicit allows for DNS and the application traffic that's actually needed. A single rule can combine a `namespaceSelector` and a `podSelector` to require both conditions.

I roll this out through an audit or staging mode where the tooling supports it, run connectivity tests from both allowed and denied namespaces, and check policy selection (the `podSelector` labels), `policyTypes`, ports/protocols, namespace labels, return traffic, and DNS.

When something fails, I compare against a direct-IP test, check which policies select the source and destination, and look at CNI policy logs or drop counters. I don't delete all policies to "fix" it — if I need a temporary diagnostic allow rule, I keep it narrow and time-boxed, with approval.

I validate that the result gives least privilege — only the access that's actually needed — while still letting required health checks and monitoring traffic through.

### 9. How can workloads in different Kubernetes namespaces communicate securely?

**Answer:**

Expose the destination through a Service and use cluster DNS — for example `api.payments.svc.cluster.local`. Clients in another namespace can usually just use `api.payments` plus the namespace name.

Being in a different namespace doesn't block traffic on its own, so I add ingress and egress NetworkPolicies (enforced by the CNI) that allow only the required namespace labels, ports, and DNS path, and use workload identity/RBAC for API access.

For an external dependency, an `ExternalName` Service can give it a DNS alias, but it doesn't add network security or health checking on its own. I test DNS resolution, endpoints, policy enforcement, and the full request path before calling it done.

### 10. How do you secure container-to-container communication in Kubernetes? *(scenario)*

**Answer:** Use NetworkPolicies → Enable mutual TLS with Istio → Encrypt traffic.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 11. How do you secure container-to-container communication with layered controls?

Use multiple layers together - no single control is sufficient on its own:

1. **Network Policies** - restrict which Pods can talk to which other Pods (see the NetworkPolicy sections under Key Concepts in this file).
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

#### Short interview answer

I layer several controls: Network Policies to restrict which Pods can reach which, mTLS through a service mesh to encrypt and authenticate the traffic that is allowed, RBAC and Service Accounts to control API access, namespaces for isolation, Key Vault or Kubernetes Secrets for credentials, and hardened Pod security settings - non-root, dropped capabilities - so a compromised container has as little to work with as possible even if it did get network access.

### 12. How can you restrict which pod can access other pods in Kubernetes?

Use Network Policies to control traffic flow between pods:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: allowed-app
```

Network policies work at L3/L4 and require a CNI that supports them (Calico, Cilium, etc.).

### 13. How can you ensure that only pods with a specific label can talk to your backend service?

Use a NetworkPolicy that selects the backend pods and allows ingress only from pods with the required label:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-access-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          access-backend: "true"
    ports:
    - protocol: TCP
      port: 8080
```

Only pods with the label `access-backend: "true"` can reach the backend pods.

### 14. When using network policies, if you don't specify egress rules, are outbound connections blocked by default?

**Answer:**

Yes, when you create a NetworkPolicy that selects Pods but doesn't include egress rules, all outbound traffic from those Pods is blocked by default.

NetworkPolicy behavior:

- **No NetworkPolicy:** All traffic allowed (default).
- **NetworkPolicy with only ingress:** Egress remains open.
- **NetworkPolicy without an egress section:** All egress blocked.
- **Empty egress array:** All egress blocked.

Example blocking all egress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-egress
spec:
  podSelector:
    matchLabels:
      app: secure-app
  policyTypes:
  - Egress
  # No egress rules = deny all egress
```

### 15. I am getting a 503 error when hitting a load balancer URL that routes traffic to applications deployed in a Kubernetes cluster. How will you troubleshoot this?

Follow this systematic approach:

- **Check service endpoints:** `kubectl get endpoints <service-name>`.
- **Verify pod health:** `kubectl get pods` — check if pods are ready.
- **Check service configuration:** Ensure correct port mapping and selectors.
- **Test internal connectivity:** `kubectl exec` into a pod and test the service.
- **Check ingress/load balancer logs:** Look for backend connection errors.
- **Verify health checks:** Ensure readiness/liveness probes are configured properly.
- **Check resource limits:** Pods might be throttled due to resource constraints.
### 16. How do you troubleshoot 503 errors from a LoadBalancer?

**Answer:**

A 503 usually means the request reached the gateway or load balancer, but there was no healthy backend, or the upstream failed. I check the headers and logs to see which layer generated the response.

Then I check load balancer provisioning and backend health, the Service selector and ports, EndpointSlices, pod readiness, whether the app is listening on the right address and port, the Ingress route, and the network/firewall path.

```bash
kubectl get svc,endpointslice,pods -o wide
kubectl describe svc <svc>
kubectl logs <ingress-controller> --since=15m
```

I test in order: the pod IP directly, then the Service DNS name, then the Ingress/load balancer. I fix whatever's broken — selector, port, probe, network, or app — or roll back the release, then confirm the fix with a real external request and by watching metrics. To prevent a repeat, I add smoke/synthetic tests, config validation, and an alert on healthy backend count.

### 17. Case: Pod is internally accessible but LoadBalancer fails. What do you check?

**Answer:**

Since internal access works, the pod and app are at least partly healthy. I check the LoadBalancer Service's events, status, and external address, the cloud load balancer's backend/target health, the probe's path/port/protocol/host, the Service's `port`/`targetPort`/`nodePort`, `externalTrafficPolicy`, node and pod readiness, and the cloud security group/firewall/routes.

I test the Service from inside the cluster, the health endpoint the way the load balancer sees it, and the external path. Controller and cloud-provider logs, plus cloud activity logs, usually reveal provisioning, permission, or quota errors.

One thing to watch for: if `externalTrafficPolicy` is set to `Local`, a node with no local endpoints for that Service can fail its health check, even though other nodes are fine.

I fix the probe, network, ports, or annotation — or roll back — then wait for the change to reconcile (for the cluster's actual state to catch up with the desired state). I confirm multiple zones and backends work, check external TLS and requests, and monitor going forward. I never open the firewall wider as a permanent workaround.

### 18. How do you troubleshoot a Kubernetes service not reachable externally? *(scenario)*

**Answer:** Check service type (ClusterIP vs LoadBalancer) → Validate Ingress rules → Ensure firewall/load balancer rules are correct.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 19. Your Kubernetes cluster is healthy, but requests intermittently return HTTP 503. How do you troubleshoot it?

**Answer:**

I trace one failing request through the whole path: DNS → external load balancer or ingress → routing rule → Service → EndpointSlice → ready pod → application dependency. The cluster being "healthy" overall doesn't tell me whether endpoints, readiness, connection pools, or downstream services are actually healthy.

I compare the time, host, path, zone, pod, and application version between successful and failed requests.

```bash
kubectl get ingress,svc,endpointslice,pods -A -o wide
kubectl describe ingress <name>
kubectl logs -n <ingress-namespace> deploy/<controller>
kubectl get events --sort-by=.metadata.creationTimestamp
curl -vk https://<host>/<path>
```

I figure out whether the 503 came from the ingress/proxy or from the application itself, then check for empty or flapping endpoints, readiness failures, selector/port mismatches, insufficient capacity during a rolling update, zone imbalance, NetworkPolicy, service-mesh retries, upstream timeouts, connection-pool exhaustion, and dependency latency.

I split load-balancer and ingress metrics by backend, response code, and upstream timing. The fix targets whichever layer the evidence points to — the health probe, selector, `targetPort`, timeout, readiness, capacity, or a dependency — rather than papering over it with unlimited retries.

Afterward I run sustained traffic through the real hostname, confirm error and latency targets are met, simulate a pod being replaced, and alert on endpoint count, upstream 5xx rate, readiness churn, and saturation — how close a resource is to its limit.

### 20. Pod Running but Application Unavailable (HTTP 503)

#### The situation

All Pods show `Running` and `1/1` ready, but users get HTTP 503.

#### Why "Running" doesn't mean "working"

`Running` only means the container process started — it says nothing about whether the app inside is actually healthy or accepting traffic correctly.

#### Commands to troubleshoot, in order

```bash
# 1. Confirm the Service has real endpoints
kubectl get endpoints payment-service

# 2. Check readiness — Running pods can still be NotReady
kubectl get pods -o wide

# 3. Look at recent events (crashes, probe failures, scheduling issues)
kubectl describe pod payment-api-6d7f8c9d-x1a2

# 4. Check application logs for errors
kubectl logs payment-api-6d7f8c9d-x1a2
kubectl logs payment-api-6d7f8c9d-x1a2 --previous

# 5. Check if the Ingress/Gateway can reach the Service
kubectl describe ingress payment-ingress

# 6. Test directly from inside the cluster, bypassing Ingress
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  wget -qO- http://payment-service
```

503 from an Ingress/Gateway usually means the upstream Service has no healthy backend — even though Pods show `Running`, they might be failing readiness probes, or the app might be throwing errors on every request (e.g., a bad DB connection) while still staying "up."

#### Short interview answer

"Running doesn't mean healthy. I'd check `kubectl get endpoints` first to see if the Service actually has backends, then check readiness state and pod events, then look at application logs, and finally test connectivity directly inside the cluster to isolate whether the problem is the app, the Service, or the Ingress."

### 21. Kubernetes Pods look healthy, but users receive HTTP 504 responses. How do you troubleshoot?

**Answer:**

A 504 means a gateway or proxy timed out waiting for a response, so I check the response headers and logs to identify which component generated it, then trace the path: ingress/load balancer → Service/EndpointSlice → pod → downstream dependency.

I compare connect time, response time, and total time at each hop, and check endpoint readiness, target ports, DNS, NetworkPolicy, mesh retries, connection pools, queue depth, CPU throttling, garbage collection, and database/dependency latency.

A pod that shows as Running can still be slow or unreachable from the proxy's point of view. I stabilize the situation by reducing traffic, scaling the actual bottleneck, rolling back a bad change, or fixing the real timeout/dependency issue — never by just increasing every timeout — then confirm p95/p99 latency and real-user requests look right.

### 22. Application Gateway → AKS → PostgreSQL: HTTP 502/504 with Healthy Pods

#### The architecture

```text
Internet
   |
Azure Application Gateway
   |
AKS Ingress
   |
Service
   |
Pods
   |
PostgreSQL
```

Pods show `1/1 Running`, but users get HTTP 502/504.

#### Why healthy pods don't rule this out

502/504 are gateway-level errors — they mean something *in front of* the app failed to get a valid/timely response, which can happen even if the Pods themselves are running fine. The problem could be at any hop in the chain.

#### Troubleshooting approach, layer by layer

**1. Application Gateway layer**
```bash
az network application-gateway show-backend-health \
  --resource-group <rg> --name <appgw-name>
```
Check if App Gateway considers the backend pool healthy. A 502 often means App Gateway couldn't reach its configured backend (misconfigured health probe path, backend pool pointing to the wrong target, or an expired/mismatched TLS cert on the backend).

**2. Ingress / Service layer**
```bash
kubectl get ingress
kubectl describe ingress payment-ingress
kubectl get endpoints payment-service
kubectl logs -n <ingress-namespace> <ingress-controller-pod>
```
Confirm the Ingress is correctly routing to the Service, and the Service has healthy endpoints.

**3. Pod / application layer**
```bash
kubectl logs <pod> --tail=100
kubectl top pod
```
A 504 (timeout) often means the app is alive but responding too slowly — check CPU throttling (`resources.limits.cpu` too low), thread pool exhaustion, or slow downstream calls.

**4. Database layer**
```bash
kubectl exec -it <pod> -- pg_isready -h <postgres-host>
```
Check PostgreSQL connection pool exhaustion, slow queries, or network latency/connectivity from AKS to PostgreSQL (especially if PostgreSQL is behind a private endpoint/VNet peering — check NSGs and DNS resolution).

**5. Timeouts across layers**
Confirm that App Gateway's request timeout, the Ingress controller's proxy timeout, and any app-level timeout to PostgreSQL are all consistent — a common 504 cause is App Gateway timing out *before* a legitimately slow backend (e.g., a slow DB query) finishes.

#### Short interview answer

"502/504 with healthy pods means the problem isn't the container process itself — it's somewhere in the request path or the app is too slow to respond. I'd work through the chain in order: check Application Gateway's backend health and probe config, confirm the Ingress and Service actually have healthy endpoints, check the pod's CPU/memory and logs for slow responses, and then check PostgreSQL for connection pool exhaustion or slow queries — also comparing timeout settings across App Gateway, Ingress, and the app, since a mismatched timeout is a very common cause of 504s."

### 23. Case: Pod is not accessible internally. How do you troubleshoot?

**Answer:**

First I clarify what "not accessible" means: by pod IP or by Service, and from which namespace. I check that the pod is Running and Ready, that the app logs show it listening on `0.0.0.0:<targetPort>` (not just `localhost`), that the Service selector, port, and targetPort match, and that EndpointSlices and DNS look correct.

From a debug pod, I test in order: DNS, then Service IP/port, then the pod IP/port directly. If the direct pod IP works but the Service doesn't, the problem is likely the selector, endpoints, or the Service data plane.

If both fail, I check how the app is bound, NetworkPolicy rules, and the CNI/routes/security group/node firewall. If only DNS fails, I check CoreDNS and any DNS-related policy.

I note the exact error — timeout, connection refused, or NXDOMAIN — fix the one layer that's broken, and retest from the original source plus readiness and the real user flow. I clean up any debug pods afterward.

### 24. Kubernetes Service Selector Mismatch

#### The setup

Deployment Pods are labeled:

```yaml
labels:
  app: payment-api
```

But the Service selects:

```yaml
selector:
  app: payment
```

#### What is wrong

The Service's `selector` (`app: payment`) does not match the Pod label (`app: payment-api`). A Service only sends traffic to Pods whose labels match its selector exactly (label values, not substrings). Since nothing matches, the Service has **zero endpoints**, so any request to it fails with a connection error.

There's a second issue: `targetPort: 8080` — this only works if the container actually listens on 8080. If the Deployment's container port is different, that's a second reason for failures even after the selector is fixed.

#### How to troubleshoot

```bash
kubectl get pods --show-labels
kubectl describe svc payment-service
kubectl get endpoints payment-service
```

`kubectl get endpoints` is the fastest check — if it shows `<none>`, the selector doesn't match any Pod.

#### Fix

```yaml
spec:
  selector:
    app: payment-api
  ports:
    - port: 80
      targetPort: 8080
```

#### Short interview answer

"Services route traffic based on label selectors, and here the Service selector doesn't match the Pod labels, so it has no endpoints. I'd confirm with `kubectl get endpoints`, then fix the selector to match the actual Pod labels, and double-check `targetPort` matches the port the container listens on."

### 25. How do you troubleshoot Pod-to-Pod networking issues?

**Answer:**

I map out the source pod, destination pod, their nodes, IPs, port/protocol, and the exact failure. I test the direct pod IP first — same node, then across nodes — then the Service, using `nc`/`curl`, and only use packet capture with approval.

I check that the app is actually listening, both ingress and egress NetworkPolicy rules (including namespace labels), CNI pod status/logs/IP allocation, node routes/MTU/firewall/security groups, and kube-proxy or eBPF data-plane state.

If same-node traffic works but cross-node traffic fails, suspect the CNI overlay, routes, MTU, or firewall. If the direct IP works but the Service doesn't, suspect endpoints or the Service data plane. Whether it's a timeout or an outright refusal is also a useful clue.

After the fix, I confirm the traffic that should be allowed works and the traffic that should be blocked stays blocked, test across multiple nodes and zones, and monitor for packet drops. I keep the network config in version control.

### 26. How do you handle Kubernetes pod networking issues? *(scenario)*

**Answer:** Check CNI plugin logs → Validate IP assignment → Restart kube-proxy or CNI → Apply Network Policies correctly.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 27. How do you troubleshoot network issues in Kubernetes? *(scenario)*

**Answer:** • Check kubectl get svc for service mapping.
• Validate Network Policies.
• Run kubectl exec to test connectivity (ping, curl).
• Use kubectl describe svc to verify correct target pods.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 28. How do you debug DNS failures inside Kubernetes?

**Answer:**

First I narrow down the failure: is it a cluster Service name or an external name, one pod/node/namespace or the whole cluster, and is it NXDOMAIN or a timeout? From a debug pod I check `/etc/resolv.conf`, run `nslookup`/`dig` for both the short name and the FQDN, and query the kube-dns Service IP directly.

I check CoreDNS's replica count, readiness, logs, metrics, and config, the relevant Service/endpoints, NetworkPolicy rules for UDP/TCP port 53, the CNI, and the upstream resolver or node DNS.

High latency is often caused by `ndots` search-domain amplification, an overloaded CoreDNS, or a slow upstream resolver. I fix this by scaling or fixing CoreDNS, or reverting a bad config change — never by hardcoding entries in `/etc/hosts`.

Afterward I confirm both internal Service names and external names resolve, check TCP fallback for large responses, and monitor DNS error rate and latency. NodeLocal DNSCache can help at scale, but only after the data shows it's actually needed.

### 29. How do you debug Kubernetes DNS issues? *(scenario)*

**Answer:** Check CoreDNS logs, verify ConfigMaps, run `nslookup` or `dig` from a Pod with `kubectl exec`, and ensure NetworkPolicies allow DNS traffic. Mini-case: Pods could not resolve Services because of an incorrect CoreDNS `stubDomain`; correcting the ConfigMap restored DNS resolution.

**Detailed interview approach:**
I test from the affected pod using `cat /etc/resolv.conf`, `nslookup kubernetes.default`, and a lookup for the failing Service/FQDN.

I compare against a healthy namespace or node, then check the Service/EndpointSlice records, CoreDNS pods, logs, ConfigMap, resource saturation (how close CoreDNS is to running out of capacity), and the upstream DNS server.

NetworkPolicy and firewall rules need to allow UDP and TCP on port 53 to cluster DNS. I also compare timeouts against `NXDOMAIN`: a timeout points to a path or capacity problem, while a wrong name or search domain gives a valid negative answer instead.

Once I've made the targeted fix — to CoreDNS, a policy, or the upstream resolver — I test both short and full names, run an actual application call, and check DNS latency. If load caused the incident, I also add capacity and alerts.

### 30. How do you troubleshoot DNS issues in Kubernetes? *(scenario)*

**Answer:** Run kubectl exec into pod → Test DNS resolution → Check CoreDNS logs → Restart CoreDNS pods → Fix network policies if blocking.

**Detailed interview approach:**
I test from the affected pod using `cat /etc/resolv.conf`, `nslookup kubernetes.default`, and a lookup for the failing Service/FQDN.

I compare against a healthy namespace or node, then check the Service/EndpointSlice records, CoreDNS pods, logs, ConfigMap, resource saturation (how close CoreDNS is to running out of capacity), and the upstream DNS server.

NetworkPolicy and firewall rules need to allow UDP and TCP on port 53 to cluster DNS. I also compare timeouts against `NXDOMAIN`: a timeout points to a path or capacity problem, while a wrong name or search domain gives a valid negative answer instead.

Once I've made the targeted fix — to CoreDNS, a policy, or the upstream resolver — I test both short and full names, run an actual application call, and check DNS latency. If load caused the incident, I also add capacity and alerts.

### 31. Your Ingress controller crashes repeatedly under heavy load. How do you stabilize it?

**Answer:**

First I protect traffic: roll back the last config change, scale up healthy replicas, or shift traffic away. Then I look for the cause. I check current and previous logs, whether pods were OOM-killed or terminated, CPU/memory and throttling, connection and request metrics, how often the config reloads, TLS/WAF/logging overhead, upstream latency, node pressure, and load-balancer health.

Fixes usually involve: running multiple replicas spread across zones, a PodDisruptionBudget, realistic resource requests, autoscaling on CPU/requests/connections, dedicated nodes if needed, a leaner config, and a slower reload rate. A large cert or rule set, or too much access logging/tracing, can also overload the controller. A slow backend can pile up connections and cause the same symptom.

I load-test at peak plus a failure scenario, check p95 latency, error rate, connection resets, and reload metrics, then plan capacity ahead of time and validate config changes with a canary. Scaling the controller alone won't help if the real problem is a saturated backend.

### 32. During peak traffic, Ingress fails to route requests efficiently. How do you diagnose and scale it?

**Answer:**

I split the request path into stages: edge/load balancer, Ingress controller, Service/endpoints, and backend. I compare request rate, 4xx/5xx counts, controller latency versus upstream latency, active connections and queue depth, TLS overhead, retries and timeouts, reload frequency, pod/node resource use, readiness, and endpoint count.

I check the routing rule (host and path) and test the Service directly, bypassing Ingress, to isolate the problem. Depending on what I find, the fix might be scaling the controller or backends, adding capacity headroom, rolling back a recent config change, rate limiting, or shifting traffic elsewhere.

I only tune buffers and timeouts once the evidence points there — a timeout set too long just makes connection exhaustion worse.

Afterward I load-test, set up autoscaling with zone spreading and a PodDisruptionBudget, and monitor saturation — how close a resource is to running out of capacity. I also confirm the cloud load balancer is spreading traffic across healthy controller pods and nodes, and add synthetic tests for the key host/path combinations.

### 33. How do you debug Kubernetes ingress not routing traffic? *(scenario)*

**Answer:** Check ingress controller logs → Validate annotations/paths → Check DNS → Verify backend service health.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 34. What are Ingress and CoreDNS in Kubernetes, and how do you troubleshoot routing issues?

**Key points:**

- Ingress defines HTTP/HTTPS routing rules and requires an Ingress controller.
- CoreDNS provides cluster DNS.
- Troubleshoot routing from the inside out: Pod readiness, endpoint slices, Service selectors and ports, DNS, Ingress rules/controller, then load balancer and firewall.

#### 5.1 What is Ingress?

- Ingress manages external HTTP/HTTPS access to applications running inside the Kubernetes cluster.
- Instead of exposing every application with a separate LoadBalancer, Ingress lets you route traffic based on the host name or URL path.
- Ingress itself is just a set of routing rules. To enforce those rules, you need an **Ingress Controller** such as NGINX Ingress Controller, Azure Application Gateway Ingress Controller (AGIC), or Traefik.

#### 5.2 What is DNS (CoreDNS)?

- Kubernetes uses CoreDNS as its internal DNS server.
- It allows Pods and Services to communicate using names instead of IP addresses.
- For example, a Pod can access a Service using `orders-service.default.svc.cluster.local` instead of remembering its IP.

#### 5.3 How do you troubleshoot routing issues?

I troubleshoot from the inside out, starting with the application and moving toward the user.

**1. Check Pod health** - verify Pods are running and Ready.

```bash
kubectl get pods
```

**2. Check EndpointSlices** - ensure the Service has healthy backend endpoints.

```bash
kubectl get endpointslices
```

**3. Check the Service** - verify the selector matches the Pods, and confirm `port` and `targetPort` are correct.

```bash
kubectl describe svc <service-name>
```

**4. Check DNS** - verify the Service name resolves correctly.

```bash
nslookup <service-name>
dig <service-name>
```

**5. Check Ingress** - verify host, path, and backend Service configuration, and make sure the Ingress Controller is running.

```bash
kubectl describe ingress <ingress-name>
```

**6. Check the external Load Balancer and firewall** - verify the Load Balancer is healthy, and check NSG/firewall rules and DNS records if traffic is coming from outside the cluster.

#### 5.3.1 When the Service specifically isn't reachable from *outside* the cluster

The steps above cover routing in general. When the specific complaint is "works inside the cluster, not from outside," add these:

**Test from inside the cluster first** - before blaming the Ingress/Load Balancer, confirm the Service itself works from inside the cluster using a temporary debug Pod:

```bash
kubectl run test-pod --rm -it --image=curlimages/curl -- sh
curl http://<service-name>:<port>
```

If this fails, the problem is between Service and Pod/Application - the Ingress and Load Balancer aren't the issue yet. If it succeeds, move outward.

**Confirm the Load Balancer actually has an external IP:**

```bash
kubectl get svc <ingress-controller-service> -n ingress-nginx
```

A `<pending>` `EXTERNAL-IP` means the cloud load balancer was never provisioned - that alone explains total external unreachability.

**Confirm the external DNS record points at that Load Balancer IP**, and that the required ports are actually open - normally `80` and `443` - on the NSG/firewall in front of it.

**Finally, review both the application logs and the Ingress Controller logs** - not just its config - since a config that looks correct can still be failing at the connection/upstream level.

#### 5.4 Interview summary

> "Ingress controls external HTTP/HTTPS routing to Kubernetes Services, while CoreDNS provides internal name resolution. When troubleshooting, I start from the application by checking Pod readiness, then EndpointSlices, Service selectors and ports, DNS resolution, Ingress rules and controller, and finally the external Load Balancer and firewall."

### 35. How do you secure Kubernetes Ingress traffic? *(scenario)*

**Answer:** Use TLS certificates (Cert-Manager) → Enable WAF/firewall rules → Restrict IP access → Use Istio/NGINX for advanced security.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 36. How do you protect Kubernetes against DDoS attacks? *(scenario)*

**Answer:** Use cloud-native DDoS protection (Cloud Armor/Azure DDoS Protection) → Apply rate limiting → Enable WAF on ingress.

**Detailed interview approach:**
I apply defense in depth: a private/restricted API server, SSO, and least-privilege RBAC (giving each identity only the access it needs), separate service accounts, Pod Security Admission, non-root and read-only containers, seccomp, admission policy, default-deny NetworkPolicies, encrypted secrets, and audit/runtime monitoring.

Images are pinned, scanned, signed, and only admitted from approved registries.

If I suspect a workload has been exposed, I isolate it, preserve audit and runtime evidence, revoke its tokens or credentials, check for lateral movement, and rebuild it from a trusted image.

I verify both the denied and allowed paths using real service accounts, and periodically review RBAC for unused permissions, rotate certificates and secrets, check patch levels, confirm backup/restore works, and review policy exceptions.

### 37. How do you layer Azure DDoS Protection, rate limiting, and WAF?

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

#### Short interview answer

I use Azure DDoS Protection at the network layer, rate limiting at the Ingress/API Gateway layer, and WAF for application-layer attacks like SQLi and XSS. On top of that, Network Policies, autoscaling, and monitoring/alerting on unusual traffic give defense in depth rather than relying on any single layer.

### 38. Your service mesh sidecar consumes more resources than the app. How do you analyze and optimize it?

**Answer:**

I measure the sidecar's CPU/memory against actual traffic and connection volume, request/response size, TLS handshake rate, retries/timeouts, access log volume, metrics cardinality, trace sampling rate, and the size of its config (clusters, listeners) and control-plane push/reload frequency. Distributed traces often reveal retry amplification or a slow backend as the real driver.

I tune log/trace sampling, connection pool sizes, retry budgets, metrics volume, and which workloads actually need the mesh injected, and check whether the mesh version itself has a known issue. I size resources from a measured peak, not a guess. An ambient or sidecar-less mode is worth considering, but only after checking it covers the features and security controls I actually need — or I simply exclude workloads that don't need the mesh at all.

I roll out any change as a canary, load-test mTLS/routing/failure behavior, and watch latency, errors, security posture, resource use, and cost. Removing the sidecar without this care can quietly remove identity, policy enforcement, or observability along with it.

### 39. How do you implement Service Mesh in Kubernetes? *(scenario)*

**Answer:** Deploy Istio/Linkerd → Enable traffic routing, retries, and observability → Use for canary/blue-green deployments.

**Detailed interview approach:**
I bring in a service mesh for a specific need — workload identity, mTLS, traffic policy, or better telemetry — not just to add proxies for their own sake. I inventory the protocols and ports in use, install the control plane and monitor it, onboard one non-critical namespace first, and check the sidecar or ambient resource overhead.

Identities come from service accounts and short-lived certificates. I move mTLS from permissive to strict only after confirming I've seen every legitimate caller. AuthorizationPolicy then allows the exact service-to-service paths that are needed and denies everything else by default.

I test certificate rotation, retries/timeouts, what happens if the control plane fails, and any way traffic could bypass the proxy — then roll out gradually. Dashboards and tracing confirm latency and error rates are healthy, and I keep clear upgrade and version-skew procedures so the mesh stays supportable.

### 40. What is a Service Mesh?

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

#### Short interview answer

A Service Mesh manages service-to-service communication using sidecar proxies instead of application code. It handles traffic routing, retries, timeouts, mTLS, and observability transparently - the application just makes a normal network call, and the mesh intercepts it to apply policy and collect telemetry.

### 41. How do you debug cross-cluster service communication failures? *(scenario)*

**Answer:** Verify DNS resolution, network routes, firewall rules, service mesh mTLS settings, and mutual TLS cert validity; trace requests with distributed tracing (Jaeger) to identify where traffic is dropped.

Mini-case: Tracing showed requests stopping at the ingress of cluster B; firewall rules were blocking healthcheck IP ranges — after opening the range, inter-cluster calls recovered.

**Detailed interview approach:**
I trace the path layer by layer: DNS → ingress/load balancer → Service → EndpointSlice → pod readiness and listening port. Commands like `kubectl get ingress,svc,endpointslice -o wide`, `kubectl describe`, controller logs, and `curl` from inside and outside the cluster show me where traffic actually stops.

I check selectors, `port` versus `targetPort`, the ingress class/annotations, TLS/SNI, routes, cloud firewall/health probes, NetworkPolicy, and CNI health. I fix the one layer that's actually broken, then confirm the real hostname, status code, latency, and logs all look right.

I avoid opening broad firewall rules as a shortcut. Health endpoints, synthetic tests, and config validation are what actually prevent this from happening again.

### 42. How would you connect a Kubernetes microservice to an external database through a VPN with high availability and security?

**Answer:**

I design redundant site-to-site VPN tunnels and gateways with BGP routing, non-overlapping CIDRs, private DNS forwarding, and a firewall that only allows the app's subnets/pods to reach the database port.

The workload validates the database's TLS certificate, authenticates with a managed or workload identity (or a rotated secret if that's not possible), uses a least-privilege database account (one with only the access it actually needs), and connects through a pool with timeouts, retries, and a circuit breaker. NetworkPolicy restricts egress to just the database path.

Pods and egress gateways run across multiple zones. The database endpoint, its replicas, and the VPN failover setup all need to match the recovery-time target. I test DNS, routing, and TCP/TLS from a debug pod, run an actual application query, and simulate one tunnel failing and one zone failing, while watching latency, errors, and connection counts.

I make sure logs exist at the app, VPN/firewall, and database layers. I avoid retry storms, account for the extra latency of a cross-network path, and make sure secrets never show up in a manifest or log.

### 43. What happens if the firewall between control plane and worker nodes breaks?

**Answer:**

Nodes can no longer send heartbeats or watch for pod spec changes, so they go NotReady or Unreachable. Containers that are already running may keep running locally, but the control plane can't reliably manage them — `exec`, `logs`, `port-forward`, and Secret/config updates all fail.

The control plane may reschedule managed pods elsewhere once tolerations expire. If the partitioned node is still actually running its pods, this risks two copies of a stateful process running at once — which is why fencing matters. Traffic from the control plane to kubelet or webhook ports can also fail in the same way.

I identify the required direction and port from the provider's docs, test DNS/route/TCP, and check for recent firewall or NSG changes and flow logs, along with node/kubelet and API server logs. I restore only the specific rules that are needed, then confirm nodes go Ready, leases update, scheduling resumes, logs/exec work again, and the CNI and application are consistent.

To prevent this: manage firewall rules through IaC and policy, monitor node heartbeat and connectivity, build redundant network paths, and actually test how the cluster behaves under a network partition.
