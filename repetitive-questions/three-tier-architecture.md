# 3-Tier Architecture on Azure (End to End)

For an Azure DevOps interview, you should be able to explain the **entire request path**, not just name the services.

A strong 3-tier Azure architecture looks like this.

## 1. High-level architecture

```text
                         INTERNET
                            |
                            v
                    Public IP Address
                            |
                            v
                  Azure Application Gateway
                       + WAF enabled
                            |
                    Web Subnet
                            |
                  +---------+---------+
                  |                   |
                  v                   v
            Web Server 1         Web Server 2
            React/Nginx           React/Nginx
                  |                   |
                  +---------+---------+
                            |
                            | HTTPS / API
                            v
                    Application Subnet
                            |
                  +---------+---------+
                  |                   |
                  v                   v
             App Server 1         App Server 2
             Spring Boot          Spring Boot
                  |                   |
                  +---------+---------+
                            |
                            | DB connection
                            v
                    Database Subnet
                            |
                            v
                   Azure SQL Database
```

The basic idea is:

```text
Internet
   |
Gateway / WAF
   |
Web Tier
   |
Application Tier
   |
Database Tier
```

## 2. Start with the Azure VNet

I create one VNet, for example:

```text
VNet: 10.0.0.0/16
```

Then divide it into separate subnets.

```text
VNet: 10.0.0.0/16
|
+-- AppGatewaySubnet
|      10.0.1.0/24
|
+-- WebSubnet
|      10.0.2.0/24
|
+-- AppSubnet
|      10.0.3.0/24
|
+-- DatabaseSubnet
       10.0.4.0/24
```

The subnet separation gives network isolation.

I don't want users from the Internet directly reaching my application servers or database.

## 3. Internet -> Application Gateway

The user opens:

```text
https://myapp.com
```

DNS resolves the domain to the public IP of Azure Application Gateway.

For example:

```text
myapp.com
     |
     v
Public IP
     |
     v
Application Gateway
```

Application Gateway acts as the Layer 7 entry point.

I can enable WAF on it to protect against common web attacks.

It can also do:

- SSL / TLS termination
- Host-based routing
- Path-based routing
- Load balancing
- Health probes

## 4. Application Gateway subnet

Application Gateway sits in its own dedicated subnet.

For example:

```text
AppGatewaySubnet
10.0.1.0/24
```

I don't deploy normal application workloads into this subnet. This subnet is only for Application Gateway.

## 5. Web tier

The Application Gateway forwards traffic to the web tier.

For example:

```text
Application Gateway
        |
        v
WebSubnet
10.0.2.0/24
        |
   +----+----+
   |         |
   v         v
Web VM 1   Web VM 2
Nginx      Nginx
React      React
```

The web tier might run:

- React
- Nginx
- Angular
- Static web application

In a containerized environment, these would instead be frontend pods running in AKS.

## 6. Why do we need the Web tier?

The web tier handles the user-facing part of the application.

For example:

```text
GET /
GET /login
GET /dashboard
```

The React application is served to the user's browser.

But React should **not** directly access the database. Instead, it talks to the application tier.

## 7. Web tier -> Application tier

Suppose the user clicks **Login**.

React sends:

```text
POST /api/login
```

For example:

```text
https://myapp.com/api/login
```

Application Gateway can use path-based routing:

```text
/              -> Web Tier

/api/*         -> Application Tier
```

So:

```text
User
 |
 | HTTPS
 v
Application Gateway
 |
 +---- / ----------> Web Tier
 |
 +---- /api/* -----> App Tier
```

This is a very important interview concept.

## 8. Application tier

The application tier contains the business logic.

For example:

```text
AppSubnet
10.0.3.0/24

+--------------------+
| Application Server |
| Spring Boot        |
| Port 8080          |
+--------------------+
```

There can be multiple instances:

```text
App Server 1
App Server 2
App Server 3
```

This gives availability and scalability.

The backend could be:

- Java Spring Boot
- .NET
- Node.js
- Python
- Microservices

## 9. How Web -> App communication works

Suppose React sends:

```text
POST /api/orders
```

The request goes:

```text
Browser
   |
   v
Application Gateway
   |
   v
Web/Application routing
   |
   v
Backend Service
   |
   v
Spring Boot
```

The backend processes the request.

For example:

```text
Validate user
      |
Check authorization
      |
Process business logic
      |
Read/write database
```

## 10. Application tier -> Database tier

The backend then connects to the database.

For example:

```text
Spring Boot
     |
     | TCP 1433
     v
Azure SQL
```

Or PostgreSQL:

```text
Spring Boot
     |
     | TCP 5432
     v
PostgreSQL
```

The important point:

**The database should not be directly accessible from the Internet.** Only the application tier should be allowed to talk to it.

## 11. Database tier

For Azure, you could use:

- Azure SQL Database
- Azure Database for PostgreSQL
- Azure Database for MySQL

If you use a database server deployed inside the VNet, it can be placed in a dedicated database subnet.

For PaaS databases such as Azure SQL, the networking model is different. You normally use a Private Endpoint / private connectivity instead of simply putting the database resource into your VNet subnet.

For example:

```text
AppSubnet
   |
   | Private connection
   v
Private Endpoint
   |
   v
Azure SQL Database
```

The database has no public exposure.

The full DNS and request flow, with setup commands, is in section 29.

## 12. NSGs

This is very important for interviews.

I use Network Security Groups to control traffic between tiers.

### Web NSG

Allow:

```text
Internet/Application Gateway
        |
TCP 443
        |
Web Tier
```

Don't allow random Internet traffic directly to the web servers.

### Application NSG

Allow:

```text
Web Tier
   |
TCP 8080
   |
Application Tier
```

Block:

```text
Internet -> Application Tier
```

### Database NSG

Allow:

```text
Application Tier
       |
TCP 1433
       |
Database
```

Block:

```text
Internet -> Database
Web Tier -> Database
```

So the idea is:

```text
Internet
   |
   X
   |
Database

Internet
   |
   X
   |
Application Tier

Web Tier
   |
   | Allowed
   v
Application Tier
   |
   | Allowed
   v
Database
```

## 13. Route tables

If needed, I can use User Defined Routes (UDR) with Azure Route Tables.

For example, traffic from private workloads can be forced through Azure Firewall.

```text
Private Subnet
      |
      v
Route Table
      |
      v
Azure Firewall
      |
      v
Internet
```

This gives centralized traffic inspection and control.

## 14. NAT Gateway

Private application servers may need outbound Internet access.

For example, the application server needs to download something from an external API.

I don't want to give the VM a public IP.

Instead:

```text
App Server
   |
   v
NAT Gateway
   |
   v
Internet
```

NAT Gateway gives controlled outbound connectivity.

## 15. Azure Firewall vs NSG

This is another common interview question.

### NSG

Works mainly at the subnet / NIC level.

Used for:

- Allow / Deny
- Source
- Destination
- Port
- Protocol

Example:

```text
WebSubnet -> AppSubnet : 8080 ALLOW
AppSubnet -> DB        : 1433 ALLOW
```

### Azure Firewall

Gives centralized network security and traffic inspection.

For example:

```text
VNet
 |
 +--> Azure Firewall
          |
          +--> Internet
          +--> Other VNet
          +--> On-prem
```

## 16. Where does the VPN / ExpressRoute gateway come in?

If the company has an on-premises data center, we can connect it to Azure using:

### VPN Gateway

```text
On-Prem
   |
   | IPsec VPN
   |
VPN Gateway
   |
   v
Azure VNet
```

### ExpressRoute

```text
On-Prem
   |
   | Private dedicated connection
   |
ExpressRoute
   |
ExpressRoute Gateway
   |
   v
Azure VNet
```

For example, your application might need to access an on-premises payment system.

```text
Application Tier
       |
       v
VPN/ExpressRoute
       |
       v
On-Prem Payment System
```

## 17. How DNS works

Suppose:

```text
www.myapp.com
```

The DNS record points to the Application Gateway public IP.

For internal services, I can use Azure Private DNS.

For example:

```text
myapp.database.windows.net
```

can resolve privately when a private endpoint and private DNS are configured.

This stops internal traffic from going over the public Internet unnecessarily.

## 18. Complete request flow

This is the part you should memorize for the interview.

Suppose the user opens:

```text
https://www.myapp.com
```

Explain:

> "First, the user's DNS request resolves the application domain to the public IP of Azure Application Gateway. The request reaches Application Gateway, where WAF can inspect the traffic and SSL termination can happen. Application Gateway uses health probes and routing rules to forward the request to the healthy web-tier instance in the web subnet."

Then continue:

> "The React frontend is served from the web tier. When the user performs an operation such as login or retrieving orders, React sends an HTTPS REST API request to the backend. Application Gateway routes `/api/*` traffic to the application tier based on path-based routing."

Then:

> "The application tier contains the backend services, such as Spring Boot microservices. The backend performs authentication, authorization and business logic. When it needs data, it connects privately to the database using the required database port, such as 1433 for Azure SQL."

Then security:

> "NSGs restrict communication between the tiers. The application tier isn't directly accessible from the Internet, and the database isn't accessible from the Internet or directly from the web tier. Private endpoints can be used for PaaS services such as Azure SQL."

Then outbound:

> "If private workloads need outbound Internet access, I use NAT Gateway. If centralized inspection is required, traffic can be routed through Azure Firewall."

## 19. Where CI/CD fits

Now connect this to your Azure DevOps role.

```text
Developer
    |
    v
Azure Repos
    |
    v
Azure DevOps Pipeline
    |
    +--> Build React
    +--> Test
    +--> SonarQube
    +--> Build Docker image
    |
    +--> Build Backend
    +--> Test
    +--> SonarQube
    +--> Build Docker image
    |
    v
Azure Container Registry
    |
    +--> frontend:v1
    +--> backend:v1
    |
    v
AKS
    |
    +--> Web Tier
    +--> Application Tier
```

If using AKS:

```text
Application Gateway
       |
       v
Ingress Controller
       |
       +--------> Frontend Service
       |              |
       |              v
       |         React Pods
       |
       +--------> Backend Service
                      |
                      v
                 Spring Boot Pods
                      |
                      v
                Private Endpoint
                      |
                      v
                  Azure SQL
```

This is a very strong architecture to explain for an Azure DevOps interview.

## 20. How to explain availability

You should also mention:

### Web tier

Multiple instances:

```text
Web 1
Web 2
Web 3
```

Application Gateway distributes traffic.

### Application tier

Multiple backend instances:

```text
App 1
App 2
App 3
```

If one goes down, traffic goes to the healthy instances.

### Database

Use Azure SQL high availability features, zone redundancy where supported, backups and a proper disaster-recovery configuration.

HA inside one region is not DR. Section 33 covers DR across regions.

### Availability Zones

Where supported, spread workloads across zones:

```text
Zone 1       Zone 2       Zone 3
  |            |            |
Web/App      Web/App      Web/App
```

## 21. How to explain security

A good answer includes these points:

```text
Internet
   |
 WAF
   |
Application Gateway
   |
 Web NSG
   |
Web Tier
   |
 App NSG
   |
App Tier
   |
 DB NSG / Private Endpoint
   |
Database
```

And:

- No public IP on application servers where possible
- No public database access
- NSGs between tiers
- WAF at the entry point
- Azure Firewall when centralized inspection is required
- Key Vault for secrets
- Managed Identity instead of hardcoded credentials
- Private Endpoints for PaaS services
- TLS for application communication
- RBAC for Azure access
- Entra ID sign-in in front of the app (see section 32)

## 22. 2-minute interview answer

If the interviewer says *"Explain the 3-tier architecture you have worked on"*, give this:

> "We had a three-tier architecture consisting of web, application and database tiers. We deployed the infrastructure inside an Azure VNet with separate subnets for Application Gateway, web servers, application servers and private connectivity to the database.
>
> The user's request first reaches DNS and resolves to the public IP of Azure Application Gateway. Application Gateway acts as the Layer 7 load balancer and WAF. It performs SSL termination, health probes and routing. Requests for the frontend are routed to the web tier, where our React application is served through Nginx.
>
> When the user performs an operation such as login, React sends an HTTPS REST API request to the backend. Application Gateway routes `/api` traffic to the application tier. The application tier contains our Spring Boot services, which handle authentication, authorization and business logic.
>
> When the backend needs data, it connects to the database over private networking. For example, Azure SQL can be accessed through a Private Endpoint. The database isn't exposed to the Internet.
>
> We use NSGs to control traffic between the tiers. The web tier can receive traffic from the Application Gateway. The application tier accepts only required traffic from the web tier. The database accepts only the required database traffic from the application tier. For outbound connectivity from private resources, we use NAT Gateway, and for centralized network inspection we can use Azure Firewall.
>
> For high availability, we run multiple web and application instances across availability zones where supported. Application Gateway distributes traffic and health probes remove unhealthy instances from rotation.
>
> From the DevOps side, developers push code to Azure Repos. Azure DevOps pipelines build the React frontend and backend, run unit tests and SonarQube analysis, build Docker images and push them to ACR. We then deploy the images to AKS using Helm. In AKS, Ingress routes traffic to frontend and backend services, and the backend communicates privately with Azure SQL. We monitor the application using Azure Monitor, Application Insights, Prometheus and Grafana."

## 23. Frontend and backend: what we used and how they connect

**Interviewer:** Which applications did you use in the frontend and backend, and how does the frontend connect to the backend?

**Candidate:** The frontend was **React.js**, served by **Nginx**. The backend was **Java Spring Boot** REST APIs. The data was in **Azure Database for PostgreSQL**. Both apps ran as separate containers in AKS.

The key point: **React runs in the user's browser.** So the browser calls the backend over HTTPS, not the React pod.

```text
Browser (React code)
   |
   | GET https://myapp.com/api/orders
   v
Application Gateway / Ingress
   |
   +-- /       -> frontend-service (ClusterIP) -> Nginx pods (React files)
   |
   +-- /api/*  -> backend-service  (ClusterIP) -> Spring Boot pods :8080
                                                     |
                                                     v
                                               PostgreSQL :5432
```

React calls a relative path:

```javascript
const response = await fetch("/api/orders");
```

Spring Boot exposes it:

```java
@GetMapping("/api/orders")
public List<Order> getOrders() {
    return orderService.findAll();
}
```

Remember:

- React never talks to the database. Only the backend does.
- Same domain for UI and API (`/` and `/api`) means **no CORS problem**. If the API is on another domain, the backend must allow the frontend origin in its CORS settings.
- Values like `VITE_API_URL` or `REACT_APP_API_URL` are baked in at **build time**. A relative `/api` path lets the same image run in every environment.
- `backend-service:8080` works only inside the cluster. The browser cannot resolve it.
- The Dockerfiles for both apps are in [sample-dockerfiles.md](sample-dockerfiles.md).

## 24. Types of load balancers, and which one I used in Azure

**Interviewer:** What types of load balancers are there? Which one have you used in Azure?

**Candidate:** Load balancers are mainly **Layer 4** or **Layer 7**.

| | Layer 4 | Layer 7 |
| --- | --- | --- |
| Works on | TCP / UDP | HTTP / HTTPS |
| Routes by | IP and port | Host, URL path, headers, cookies |
| TLS termination | No (pass-through) | Yes |
| WAF | No | Yes |
| Azure service | Azure Load Balancer | Application Gateway, Front Door |

Azure options:

| Service | Layer | Scope | Use it for |
| --- | --- | --- | --- |
| Azure Load Balancer | L4 | Regional | VMs, VMSS, AKS `LoadBalancer` Services |
| Application Gateway (+ WAF) | L7 | Regional | Web apps, path-based routing, TLS, WAF |
| Azure Front Door (+ WAF) | L7 | Global | Multi-region web apps, CDN, global failover |
| Traffic Manager | DNS | Global | DNS-based failover for any protocol |

Azure Load Balancer comes as **public** (has a public IP) or **internal** (private IP inside the VNet).

**How a Layer 4 load balancer distributes traffic:** it builds a **5-tuple hash** (source IP, source port, destination IP, destination port, protocol) and sends the whole connection to one healthy backend. It is not strict round-robin. If a client must stick to one VM, I set **session persistence** to client IP.

What I used:

> "I mainly used Azure Load Balancer. AKS creates it automatically for a `LoadBalancer` Service, such as the ingress controller. I also used internal load balancers for private services and configured health probes and rules for VM Scale Sets. For web traffic, Application Gateway with WAF was the entry point, because it gives TLS termination and path-based routing."

Remember:

- The **Basic** SKU of Azure Load Balancer was retired in September 2025. Use **Standard**.
- Standard Load Balancer is closed by default. The NSG must allow the traffic.

## 25. Health probes

**Interviewer:** How do you set up health probes in a load balancer?

**Candidate:** A health probe checks each backend regularly. Only healthy backends get **new** connections.

```text
Load Balancer -- probe HTTP :8080 /health every 5s -->  VM1  200  -> healthy
                                                        VM2  200  -> healthy
                                                        VM3  timeout -> removed
```

```bash
az network lb probe create -g my-rg --lb-name my-lb -n app-probe \
  --protocol Http --port 8080 --path /health --interval 5 --probe-threshold 2

az network lb rule create -g my-rg --lb-name my-lb -n app-rule \
  --protocol Tcp --frontend-port 80 --backend-port 8080 \
  --frontend-ip-name my-frontend --backend-pool-name my-pool --probe-name app-probe
```

Probe types: **TCP** (port is open), **HTTP** and **HTTPS** (path must return 200).

On **Application Gateway**, I add a custom probe with the host name and path, for example `/actuator/health` for Spring Boot. It accepts 200-399 by default.

If a running VM shows as unhealthy, I check:

- Is the app listening on the probe port, and on `0.0.0.0`, not only `127.0.0.1`? (`ss -lntp`)
- Does `curl -i http://localhost:8080/health` return 200?
- Does the NSG allow the `AzureLoadBalancer` service tag? Probes come from `168.63.129.16`. A custom "deny all inbound" rule blocks them.
- Is the guest OS firewall blocking the port?

Remember:

- Keep the health endpoint light. If it checks the database and the database is slow, every backend can be marked unhealthy at once.
- In AKS, readiness probes decide which pods get traffic. The load balancer probe checks the node or ingress level.

## 26. Exposing the application in AKS: Services, Ingress and NGINX

**Interviewer:** What are the Kubernetes Service types, and how do you expose an application?

**Candidate:** A **Service** gives a stable name and IP to a group of pods, because pod IPs change.

| Type | Reachable from | Use it for |
| --- | --- | --- |
| ClusterIP (default) | Inside the cluster | Backend APIs, internal services |
| NodePort | `NodeIP:30000-32767` | Testing |
| LoadBalancer | Public or private IP (Azure Load Balancer) | Exposing one service, or the ingress controller |
| ExternalName | DNS alias to an outside name | External database or API |
| Headless (`clusterIP: None`) | DNS returns pod IPs | StatefulSets such as Kafka |

For an internal-only load balancer in AKS:

```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
```

**What is an Ingress Controller?** An **Ingress** is only a set of HTTP routing rules. The **Ingress Controller** is the pod that reads those rules and actually routes the traffic. Without a controller, an Ingress does nothing. One controller gives one IP for many apps, instead of one load balancer per app.

```text
Internet
   |
Azure Load Balancer (public IP)
   |
Ingress controller pods (LoadBalancer Service)
   |
   +-- myapp.com/      -> frontend-service (ClusterIP)
   +-- myapp.com/api   -> backend-service  (ClusterIP)
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
spec:
  ingressClassName: nginx
  tls:
    - hosts: [myapp.com]
      secretName: myapp-tls
  rules:
    - host: myapp.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service: { name: backend-service, port: { number: 8080 } }
          - path: /
            pathType: Prefix
            backend:
              service: { name: frontend-service, port: { number: 80 } }
```

**What is NGINX?** NGINX is a fast web server and reverse proxy. I used it in two places:

- **Inside the frontend image:** it serves the React build files and can send `/api` to the backend.
- **As the ingress controller:** it routes HTTP traffic to Services, terminates TLS and load balances across pods.

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;

  location / {
    try_files $uri /index.html;   # React client-side routing
  }

  location /api/ {
    proxy_pass http://backend-service:8080;
  }
}
```

Options for the controller in AKS:

| Option | Note |
| --- | --- |
| Community ingress-nginx | The Kubernetes project retired it in March 2026. No more fixes, so plan a move |
| AKS application routing add-on | Managed NGINX by Microsoft, with a limited support window. Check the current AKS notes |
| AGIC (Application Gateway Ingress Controller) | Uses Application Gateway + WAF as the L7 entry point |
| Application Gateway for Containers | Newer Azure option. Supports the **Gateway API**, the successor to Ingress |

Remember:

- Backend apps stay **ClusterIP**. Only the ingress controller gets a `LoadBalancer` Service.
- `kubectl port-forward` is for debugging only.

## 27. Changing HTTP to HTTPS for frontend and backend

**Interviewer:** Your frontend and backend use HTTP. How do you move them to HTTPS?

**Candidate:** It is more than changing `http` to `https`. I need certificates, HTTPS listeners, a redirect, backend TLS and app config changes.

```text
User --HTTPS 443--> Application Gateway (cert from Key Vault, WAF)
                          |
                          | HTTPS (end-to-end TLS, if required)
                          v
                    Ingress / frontend / backend
                          |
                          | TLS
                          v
                      PostgreSQL (TLS enforced)
```

Steps:

1. **Certificate:** from a trusted CA, stored in **Key Vault**. The CN/SAN must match `app.company.com`. Application Gateway reads it through a user-assigned managed identity. In AKS, **cert-manager** can issue and renew certificates automatically.
2. **HTTPS listener** on port 443, plus a **redirect rule** from HTTP 80 to HTTPS 443.
3. **SSL policy:** TLS 1.2 or higher.
4. **Backend:** backend settings on HTTPS 443, with a host name that matches the backend certificate.
5. **App config:** change API URLs to `https://`, so the browser does not block **mixed content**. Mark cookies `Secure`, add HSTS, and update Entra ID redirect URIs.
6. **NSG:** allow 443. Keep 80 only for the redirect.
7. **Test** in Dev and QA first: certificate chain, redirect, API calls, login callback.

Remember:

- Azure Load Balancer is Layer 4 and cannot terminate TLS. Use Application Gateway, Front Door or the ingress controller.
- TLS only up to Application Gateway is enough if policy allows it. If the requirement is end-to-end encryption, the backend must also use HTTPS.
- Add certificate expiry alerts, or use auto-renewal.

## 28. Private AKS cluster

**Interviewer:** Have you created a private Kubernetes cluster? How?

**Candidate:** Yes. In a private AKS cluster, the **API server has only a private IP** in our VNet. `kubectl` works only from a connected network.

```bash
az aks create -g rg-prod -n aks-prod \
  --enable-private-cluster \
  --network-plugin azure \
  --vnet-subnet-id <aks-subnet-id> \
  --enable-managed-identity \
  --enable-aad --enable-azure-rbac \
  --generate-ssh-keys
```

```text
Jumpbox / VPN / self-hosted agent (in VNet or peered VNet)
        |
Private DNS zone (privatelink.<region>.azmk8s.io) -> private IP
        |
AKS API server private endpoint
```

What I set up:

- **Network:** VNet with subnets for nodes, private endpoints and build agents. No overlap with peered or on-premises ranges. Egress through Azure Firewall if needed.
- **DNS:** AKS creates a private DNS zone. In hub-spoke, I link it to the hub VNet or bring my own zone with `--private-dns-zone`.
- **Access:** Entra ID login with Azure RBAC for Kubernetes. Engineers connect through a jumpbox, Bastion or VPN.
- **CI/CD:** a **self-hosted Azure DevOps agent** (VM or VMSS agent pool) inside the VNet. Microsoft-hosted agents cannot reach the private API server.
- **Quick admin command without network access:** `az aks command invoke` runs `kubectl` through Azure.

```bash
az aks command invoke -g rg-prod -n aks-prod --command "kubectl get pods -A"
```

Remember:

- If `kubectl` times out or the name does not resolve, check the private DNS zone link first.
- A private cluster hides the **control plane**. App traffic still comes through the ingress or Application Gateway.

## 29. Private endpoint between the AKS backend and the database

**Interviewer:** How do you connect the AKS backend to the database through a private endpoint? How does the request flow with VNet, subnet and private endpoint?

**Candidate:** A **private endpoint** is a NIC with a private IP in my subnet that connects to one PaaS resource through **Private Link**. The app keeps using the normal host name. **DNS is what changes.**

```text
Spring Boot pod (snet-aks 10.0.1.0/24)
   |
   | 1. connect mydb.postgres.database.azure.com:5432
   v
DNS: CNAME -> mydb.privatelink.postgres.database.azure.com
     Private DNS zone (linked to the VNet) -> A record 10.0.2.5
   |
   | 2. TCP 5432 to 10.0.2.5 (NSG / UDR / firewall checked)
   v
Private endpoint NIC (snet-private-endpoints 10.0.2.5)
   |
   | 3. Private Link over the Microsoft backbone
   v
PostgreSQL (public access disabled)
   |
   | 4. Authentication: Entra ID (workload identity) or password from Key Vault
```

Setup:

```bash
az network private-endpoint create -g my-rg -n pe-postgres \
  --vnet-name aks-vnet --subnet snet-private-endpoints \
  --private-connection-resource-id <postgres-id> \
  --group-id postgresqlServer --connection-name pe-postgres-conn

az network private-dns zone create -g my-rg -n privatelink.postgres.database.azure.com

az network private-dns link vnet create -g my-rg \
  --zone-name privatelink.postgres.database.azure.com \
  --name aks-vnet-link --virtual-network aks-vnet --registration-enabled false

az network private-endpoint dns-zone-group create -g my-rg \
  --endpoint-name pe-postgres --name default \
  --private-dns-zone privatelink.postgres.database.azure.com --zone-name postgres
```

| Service | Private DNS zone | Port |
| --- | --- | --- |
| Azure SQL | `privatelink.database.windows.net` | 1433 |
| PostgreSQL | `privatelink.postgres.database.azure.com` | 5432 |
| Key Vault | `privatelink.vaultcore.azure.net` | 443 |
| Blob Storage | `privatelink.blob.core.windows.net` | 443 |
| ACR | `privatelink.azurecr.io` | 443 |

Test from inside the cluster:

```bash
kubectl run net-test -it --rm --image=busybox -- sh
nslookup mydb.postgres.database.azure.com   # must return 10.x, not a public IP
nc -zv mydb.postgres.database.azure.com 5432
```

Remember:

- Most failures are DNS. With custom or hub DNS servers, they must forward to Azure DNS `168.63.129.16` or a DNS Private Resolver.
- Use the host name, not the IP. TLS certificates expect the host name.
- NSGs apply to the private endpoint subnet only if network policies are enabled on that subnet.
- Disable public access **after** private connectivity is tested.
- A **service endpoint** is different: the service keeps its public IP, but only allows chosen subnets.
- PostgreSQL Flexible Server has a second model: **VNet integration** in a delegated subnet. You choose it at creation time. The private endpoint model is used with the "public access" networking mode.

## 30. Azure Database for PostgreSQL in the data tier

**Interviewer:** Tell me about the PostgreSQL database in your project.

**Candidate:** We used **Azure Database for PostgreSQL Flexible Server**. (Single Server was retired in March 2025.) I provisioned it with Bicep and handled backups, connectivity and basic performance checks.

| Area | What we did |
| --- | --- |
| Network | Private access only, through a private endpoint or VNet integration. Port 5432 |
| Auth | Entra ID authentication where possible. Otherwise the password is kept in Key Vault |
| HA | Zone-redundant HA in production: a standby in another zone, with automatic failover |
| Backup | Automatic backups, 7-35 days retention, point-in-time restore. Geo-redundant backup for DR |
| Scale | Read replicas for reporting. Compute and storage scaled by tier |
| Monitoring | Azure Monitor metrics: CPU, connections, storage. Alerts through Action Groups |

Useful commands:

```bash
psql "host=mydb.postgres.database.azure.com port=5432 dbname=orders user=appuser sslmode=require"
```

```sql
SELECT count(*) FROM pg_stat_activity;                -- current connections
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity WHERE state = 'active'
ORDER BY duration DESC;                               -- long-running queries
```

```bash
pg_dump -Fc -h <host> -U <user> -d orders -f orders.dump    # logical backup
pg_restore -h <host> -U <user> -d orders orders.dump
```

Remember:

- **Connection pools:** 20 pods x 50 connections = 1000 connections, which can exceed `max_connections`. Size the pool per pod, or use the built-in **PgBouncer** (port 6432).
- For "app cannot connect", check in order: DNS -> `nc` on 5432 -> NSG/firewall -> credentials -> connection limits.

## 31. VNet-to-VNet connectivity

**Interviewer:** How do you connect two VNets?

**Candidate:** I use **VNet peering**. Traffic stays on the Microsoft backbone, and no gateway is needed.

```text
VNet-A 10.0.0.0/16  <--- peering (both directions) --->  VNet-B 10.1.0.0/16
```

```bash
az network vnet peering create -g rg-a --vnet-name vnet-a -n a-to-b \
  --remote-vnet <vnet-b-id> --allow-vnet-access
az network vnet peering create -g rg-b --vnet-name vnet-b -n b-to-a \
  --remote-vnet <vnet-a-id> --allow-vnet-access
```

Steps: address spaces must not overlap -> create both peerings -> status **Connected** -> tighten NSGs (for example, allow only TCP 5432 from the app subnet) -> test with `nc -zv`.

Remember:

- Different regions -> **global VNet peering**. Different subscriptions or tenants also work, with Network Contributor on both sides.
- Peering is **not transitive**. A <-> B <-> C does not let A reach C. Use **hub-and-spoke** with Azure Firewall or an NVA in the hub, or **Virtual WAN**.
- Spokes can share the hub's VPN gateway with **gateway transit** (`--allow-gateway-transit` on the hub, `--use-remote-gateways` on the spoke).
- VNet-to-VNet **VPN** is used only when an IPsec tunnel is required. It is slower and costs more.

## 32. Restricting users before they reach the application

**Interviewer:** How can you restrict users before their requests reach the application?

**Candidate:** I restrict at two levels: **network** (where the request comes from) and **identity** (who the user is).

```text
User
 |
Front Door / Application Gateway + WAF   -> blocks SQL injection, XSS, bots,
 |                                          bad IPs or countries, rate limits
 |
Access restrictions / Private Endpoint   -> app accepts traffic only from the gateway
 |
Entra ID sign-in (Easy Auth)             -> not signed in -> redirect to login
 |                                          not in the allowed group -> denied
Application                              -> checks app roles for admin actions
```

- **WAF:** OWASP rules, plus custom IP, geo and rate-limit rules.
- **Lock the app to the gateway:** App Service access restrictions allow only the Application Gateway subnet, or the `AzureFrontDoor.Backend` service tag plus the `X-Azure-FDID` header check. Otherwise users can bypass the gateway through `*.azurewebsites.net`.
- **Entra ID:** App Service Authentication (Easy Auth) with "Require authentication". In the Enterprise application, set **Assignment required = Yes** and assign only the allowed group.
- **Conditional Access:** require MFA or a compliant device, and block risky locations.
- For internal apps: no public endpoint at all. Users come through VPN and the private network.

Remember:

- WAF stops bad **traffic**. It does not know **who** the user is. Entra ID handles identity, so the two work together.
- The app must still check roles for sensitive operations.

## 33. Environments, subscriptions and disaster recovery

**Interviewer:** Dev, QA and UAT are in one resource group and subscription. Pre-Prod and Prod are in another, but both are in the same region. How do you achieve DR?

**Candidate:** Separate subscriptions give **access and billing isolation**. They do **not** give DR, because one regional outage hits both. For DR, Production needs a **second region**.

```text
Users -> Azure Front Door / Traffic Manager
            |                       |
      Primary region            DR region (paired or chosen region)
      Prod subscription         DR resources (same or separate subscription)
      AKS + App Gateway         AKS (warm standby, or built by IaC on demand)
      PostgreSQL       ---->    geo-redundant backup / cross-region read replica
      ACR Premium      ---->    geo-replicated images
      Key Vault                 Key Vault with the same secrets
```

What I would do:

- Keep Terraform/Bicep and Helm charts ready, so the DR environment can be built the same way.
- Replicate data: PostgreSQL geo-redundant backups or a cross-region read replica, GRS/GZRS storage, ACR geo-replication.
- Put **Front Door** or **Traffic Manager** in front, so traffic can switch regions.
- Write a runbook and run DR drills. Choose the design (active-passive, warm or cold standby) from the agreed **RTO and RPO**.

Remember:

- **HA** = zones in one region (protects against node or zone failure). **DR** = another region (protects against regional failure).
- Dev, QA and UAT usually do not need a DR copy. Production and its dependencies do.

## 34. Where else the tiers can run: App Service, Container Apps, ACI

**Interviewer:** Give a brief on Azure Container Apps and Azure Container Instances.

**Candidate:** The same 3-tier design can run on different compute. I choose by how much control we need.

| Service | What it is | Good for |
| --- | --- | --- |
| AKS | Managed Kubernetes. We manage node pools, ingress and upgrades | Many microservices, full control |
| App Service | Managed web hosting for code or containers | Simple web apps and APIs |
| Azure Container Apps | Serverless containers on managed Kubernetes. KEDA autoscaling (can scale to zero), revisions, traffic splitting, built-in ingress | Microservices without running AKS |
| Azure Container Instances | Run a single container or group quickly. No orchestration | Short jobs, tests, build tasks |

Easy way to remember:

```text
ACI            -> run a container
Container Apps -> run and scale an app made of containers
AKS            -> run your own Kubernetes platform
```

## One line to remember

```text
User
 |
DNS
 |
Application Gateway + WAF
 |
Web Subnet -> React/Nginx
 |
App Subnet -> Spring Boot/API
 |
Private Network
 |
Database -> Azure SQL
```

And the security rule is:

**Internet -> Gateway -> Web -> App -> Database. Never Internet -> Database.**
