# Azure Networking Interview Summary

### 4.2 Azure Front Door with a Storage Static Website

Azure Front Door is a global entry point. It routes users through Microsoft's edge network, which improves performance and availability. Depending on how it's configured and which tier you use, it can also add caching, TLS termination, custom domains, health probes, and a Web Application Firewall.

**Typical setup**

1. Enable static website hosting and upload the site.
2. Create an Azure Front Door profile and endpoint.
3. Add the Storage static website endpoint as an origin.
4. Configure the origin group, route, caching, and custom domain.
5. Test both the origin URL and the Front Door URL from a few different locations.
6. Review latency, cache behavior, and health metrics.

Register the required resource provider first if the subscription hasn't used this service before. Test performance from more than one location — a single browser request isn't enough to prove a real improvement.

## 5. Networking

### 5.1 Individual Public IP vs. Public IP Prefix

An **individual public IP address** is one public address assigned to a resource — a load balancer, firewall, application gateway, NAT gateway, or network interface.

A **public IP prefix** is a reserved, contiguous range of static public IP addresses (Standard SKU). You can create individual public IP resources out of that range.

| Feature | Individual public IP | Public IP prefix |
| --- | --- | --- |
| Scope | One address | Contiguous address range |
| Example | `52.160.10.15` | `52.160.10.0/28` |
| Management | Managed separately | Whole range reserved as one resource |
| Best fit | A few endpoints | Larger deployments that need predictable addresses |
| Main benefit | Simple setup | Consistent addresses, easier for partners to allow-list |

**Use an individual IP** for a small number of endpoints. **Use a prefix** when several resources need addresses from a known range — for example outbound NAT, load balancers, or firewalls that external partners need to allow-list.

### 5.2 Azure Network Watcher VM Extension

Network Watcher is Azure's network monitoring and diagnostics service. Some of its VM-based checks — packet capture and certain connection-monitoring scenarios — need the Network Watcher Agent extension installed on the VM first.

If you start one of these diagnostics and the extension is missing, Azure may install the current version for you automatically. If your change-control process requires a specific version, install and validate it yourself before running the diagnostic.

```bash
az vm extension set \
  --resource-group <resource-group> \
  --vm-name <vm-name> \
  --name NetworkWatcherAgentWindows \
  --publisher Microsoft.Azure.NetworkWatcher \
  --version <desired-version>
```

To query the latest version available in a region:

```bash
az vm extension image list \
  --name NetworkWatcherAgentWindows \
  --publisher Microsoft.Azure.NetworkWatcher \
  --latest \
  --location centralindia
```

**Interview summary:** Network Watcher is the service itself. The VM extension is a small in-guest agent that specific diagnostic features need. They're related, but not the same resource.

---

## Azure Landing Zone Hub-and-Spoke Networking

The hub-and-spoke model keeps shared connectivity separate from application workloads:

- A connectivity subscription hosts the hub VNet and shared services: Azure Firewall, VPN or ExpressRoute Gateway, Bastion, private DNS resolver, private endpoints, Route Server, logging, and network monitoring.
- Workload subscriptions host their own spoke VNets and application subnets for VMs, AKS, App Service integration, and databases.
- VNet peering connects the hub to each spoke. User-defined routes in the spokes normally send outbound traffic through Azure Firewall; where needed, route propagation can use BGP and Azure Route Server.
- Internet traffic coming in can pass through Azure Front Door with WAF/DDoS controls before it reaches the regional application. Traffic from on-premises terminates in the hub, over ExpressRoute or a site-to-site VPN.
- Private endpoints give supported PaaS services private IP addresses. Private DNS zones and resolver/forwarding rules need to make the same name resolve correctly from both the spokes and on-premises.

Typical traffic paths are:

- **Spoke to internet:** workload → spoke route table → Azure Firewall/NAT policy → internet.
- **Internet to application:** Front Door/WAF → regional load balancer or application gateway/firewall → spoke application.
- **On-premises to spoke:** ExpressRoute/VPN → hub gateway → approved hub route → spoke.
- **Spoke to PaaS:** workload → private endpoint in the private address space, resolved through private DNS.

This design keeps governance, inspection, logging, and hybrid connectivity centralized, while each workload still owns its own spoke. Things worth validating: non-overlapping address ranges, both forward and return routes, gateway transit, firewall policy, DNS resolution, asymmetric routing, and what happens if a shared hub component fails.

The architecture isn't really done until routing, DNS, monitoring, and recovery have all been tested from the real source networks — not just assumed to work.

## VNet, Subnet, and Application Delivery Patterns

An Azure VNet is a private address space and routing boundary. Subnets divide it up by trust zone or role — for example ingress, web, application, data, private endpoints, and management.

Plan non-overlapping address ranges with room to grow, then attach resources through network interfaces or private integration.

NSGs filter traffic by source, destination, protocol, and port at the subnet or NIC level. User-defined routes control where traffic goes. Peering connects VNets to each other. A VPN Gateway or ExpressRoute handles hybrid connectivity. Private endpoints give supported PaaS services their own private addresses, which needs matching private DNS design.

Don't call an Azure subnet inherently "public" or "private" — how exposed it actually is depends on public IPs, load-balancer or application-gateway frontends, routes, NAT, NSGs, firewall policy, and the service running there.

### Azure Application Gateway request flow

```text
client -> frontend IP -> listener -> routing rule
       -> HTTP settings and health probe -> backend pool
```

Application Gateway is a regional Layer-7 load balancer for HTTP/HTTPS. Listeners receive traffic, rules pick a backend by host or path, backend settings define the protocol, port, TLS, and session behavior, and health probes remove any target that isn't healthy.

Backend pools can include VMs, scale sets, App Service, AKS, or plain IP/FQDN targets, depending on what's supported. WAF adds managed or custom rules against common web attacks. TLS can either terminate at the gateway or be re-encrypted on the way to the backend.

Cookie-based affinity can keep a client pinned to the same backend when an application needs session stickiness, but a stateless application is easier to scale and recover. Current v2 SKUs support autoscaling and zone redundancy in regions that have Availability Zones.

For centralized certificate management, Application Gateway can pull TLS certificates from Key Vault using a managed identity that has only the access it needs.

Send access, performance, firewall, and health data through diagnostic settings to Azure Monitor/Log Analytics, and alert on unhealthy backends, failed requests, latency, capacity, and WAF events.

To troubleshoot: check the resolved frontend address, listener/SNI and certificate, WAF logs, rule priority, any rewrite/redirect behavior, backend health, probe host/path/status, the NSG/UDR/firewall path, backend TLS trust, and application logs. A healthy gateway doesn't mean the backend is healthy too.

### Load Balancer and secure administration

Azure Load Balancer distributes Layer-4 TCP/UDP traffic using a frontend, a rule, a backend pool, and a health probe. A common path looks like: internet -> public frontend -> load-balancing rule -> healthy VM backend.

Use an internal load balancer for private, tier-to-tier traffic.

A jump VM is a hardened VM used as a stepping stone for admin access — but it still needs patching, identity controls, logging, and network protection like any other VM. Azure Bastion is a managed alternative: it gives RDP or SSH access to private VMs without giving each one a public IP.

Typically a user starts the session through the Azure portal over HTTPS, and Bastion then reaches the VM over its private address — so inbound TCP 22 or 3389 never has to be exposed to the public internet.

Whichever pattern you use, apply least privilege (give access only where it's needed), just-in-time access, session logging, restricted management sources, and a break-glass procedure for emergencies.

### NSG and Azure Firewall together

NSGs give you distributed, stateful Layer-3/4 filtering close to subnets and NICs. Azure Firewall gives you centralized inspection and policy — network/application rules, threat-intelligence features, DNAT/SNAT, and centralized logs, depending on the SKU and configuration.

In a hub-and-spoke design, use UDRs to steer the traffic that needs inspection through the firewall, and use NSGs to restrict each workload's boundary. Validate that routing is symmetric and check the effective rules — just deploying both products doesn't create defense in depth on its own; you need a deliberate traffic path.
