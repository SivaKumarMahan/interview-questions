# 3-Tier Architecture on Azure (End to End)

For an Azure DevOps interview, you should be able to explain the **entire request path**, not just name the services.

A strong 3-tier Azure architecture looks like this.

## 1. High-level architecture

```
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

```
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

```
VNet: 10.0.0.0/16
```

Then divide it into separate subnets.

```
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

```
https://myapp.com
```

DNS resolves the domain to the public IP of Azure Application Gateway.

For example:

```
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

```
AppGatewaySubnet
10.0.1.0/24
```

I don't deploy normal application workloads into this subnet. This subnet is only for Application Gateway.

## 5. Web tier

The Application Gateway forwards traffic to the web tier.

For example:

```
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

```
GET /
GET /login
GET /dashboard
```

The React application is served to the user's browser.

But React should **not** directly access the database. Instead, it talks to the application tier.

## 7. Web tier -> Application tier

Suppose the user clicks **Login**.

React sends:

```
POST /api/login
```

For example:

```
https://myapp.com/api/login
```

Application Gateway can use path-based routing:

```
/              -> Web Tier

/api/*         -> Application Tier
```

So:

```
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

```
AppSubnet
10.0.3.0/24

+--------------------+
| Application Server |
| Spring Boot        |
| Port 8080          |
+--------------------+
```

There can be multiple instances:

```
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

```
POST /api/orders
```

The request goes:

```
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

```
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

```
Spring Boot
     |
     | TCP 1433
     v
Azure SQL
```

Or PostgreSQL:

```
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

```
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

## 12. NSGs

This is very important for interviews.

I use Network Security Groups to control traffic between tiers.

### Web NSG

Allow:

```
Internet/Application Gateway
        |
TCP 443
        |
Web Tier
```

Don't allow random Internet traffic directly to the web servers.

### Application NSG

Allow:

```
Web Tier
   |
TCP 8080
   |
Application Tier
```

Block:

```
Internet -> Application Tier
```

### Database NSG

Allow:

```
Application Tier
       |
TCP 1433
       |
Database
```

Block:

```
Internet -> Database
Web Tier -> Database
```

So the idea is:

```
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

```
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

```
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

```
WebSubnet -> AppSubnet : 8080 ALLOW
AppSubnet -> DB        : 1433 ALLOW
```

### Azure Firewall

Gives centralized network security and traffic inspection.

For example:

```
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

```
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

```
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

```
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

```
www.myapp.com
```

The DNS record points to the Application Gateway public IP.

For internal services, I can use Azure Private DNS.

For example:

```
myapp.database.windows.net
```

can resolve privately when a private endpoint and private DNS are configured.

This stops internal traffic from going over the public Internet unnecessarily.

## 18. Complete request flow

This is the part you should memorize for the interview.

Suppose the user opens:

```
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

```
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

```
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

```
Web 1
Web 2
Web 3
```

Application Gateway distributes traffic.

### Application tier

Multiple backend instances:

```
App 1
App 2
App 3
```

If one goes down, traffic goes to the healthy instances.

### Database

Use Azure SQL high availability features, zone redundancy where supported, backups and a proper disaster-recovery configuration.

### Availability Zones

Where supported, spread workloads across zones:

```
Zone 1       Zone 2       Zone 3
  |            |            |
Web/App      Web/App      Web/App
```

## 21. How to explain security

A good answer includes these points:

```
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

## One line to remember

```
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
