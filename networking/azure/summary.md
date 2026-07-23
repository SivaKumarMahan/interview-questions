# Azure Networking Interview Summary

### 4.2 Azure Front Door with a Storage Static Website

Azure Front Door is a global entry point that can improve performance and availability by routing users through Microsoft's edge network. It can also provide caching, TLS termination, custom domains, health probes, and Web Application Firewall capabilities depending on configuration and tier.

**Typical setup**

1. Enable static website hosting and upload the site.
2. Create an Azure Front Door profile and endpoint.
3. Add the Storage static website endpoint as an origin.
4. Configure the origin group, route, caching, and custom domain.
5. Test both the origin URL and Front Door URL from representative locations.
6. Review latency, cache behavior, and health metrics.

Register the required resource provider if the subscription has not used the service before. Performance measurements should be repeated from multiple locations; a single browser request is not enough to establish a general performance improvement.

## 5. Networking

### 5.1 Individual Public IP vs. Public IP Prefix

An **individual public IP address** is one public address assigned to a resource such as a load balancer, firewall, application gateway, NAT gateway, or network interface.

A **public IP prefix** is a reserved contiguous range of Standard SKU static public IP addresses. Individual public IP resources can be created from that prefix.

| Feature | Individual public IP | Public IP prefix |
| --- | --- | --- |
| Scope | One address | Contiguous address range |
| Example | `52.160.10.15` | `52.160.10.0/28` |
| Management | Managed separately | Range reserved as one prefix resource |
| Best fit | A few endpoints | Scaled deployments needing predictable addresses |
| Main benefit | Simple setup | Address consistency and easier allow-list management |

**Use an individual IP** for a small number of endpoints. **Use a prefix** when multiple resources need addresses from a known range, such as outbound NAT, load balancers, or firewall deployments that external partners must allow-list.

### 5.2 Azure Network Watcher VM Extension

Network Watcher provides network monitoring and diagnostic tools. Some VM-based diagnostic operations require the Network Watcher Agent extension, including packet capture and certain connection-monitoring scenarios.

When a supported diagnostic operation is started and the extension is missing, Azure tooling may install the current extension automatically. If change control requires a particular extension version, install and validate it before running the diagnostic.

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

**Interview summary:** Network Watcher is the service; the VM extension is an in-guest agent needed by specific diagnostic capabilities. They are related but not the same resource.

---

## Azure Landing Zone Hub-and-Spoke Networking

The hub-and-spoke model separates shared connectivity from application workloads:

- A connectivity subscription hosts the hub VNet and shared services such as Azure Firewall, VPN or ExpressRoute Gateway, Bastion, private DNS resolver, private endpoints, Route Server, logging, and network monitoring.
- Workload subscriptions host isolated spoke VNets and application subnets for VMs, AKS, App Service integration, and databases.
- VNet peering connects hub and spokes. User-defined routes in spokes normally send controlled egress through Azure Firewall; route propagation can use BGP and Azure Route Server where the design requires it.
- Internet ingress can use Azure Front Door and WAF/DDoS controls before traffic reaches the regional application entry point. On-premises connectivity terminates in the hub through ExpressRoute or site-to-site VPN.
- Private endpoints expose supported PaaS services through private IP addresses. Private DNS zones and resolver/forwarding rules must make the same name resolve correctly from spokes and on-premises.

Typical traffic paths are:

- **Spoke to internet:** workload → spoke UDR → Azure Firewall/NAT policy → internet.
- **Internet to application:** Front Door/WAF → regional load balancer or application gateway/firewall → spoke application.
- **On-premises to spoke:** ExpressRoute/VPN → hub gateway → inspected/approved hub route → spoke.
- **Spoke to PaaS:** workload → private endpoint in the private address space, with private DNS resolution.

The design centralizes governance, inspection, logging, and hybrid connectivity while keeping workload ownership isolated. Validate non-overlapping CIDRs, forward and return routes, gateway transit, firewall policy, DNS resolution, asymmetric routing, and failure of each shared hub component. The architecture is not complete until routing, DNS, monitoring, and recovery are tested from the real source networks.

## VNet, Subnet, and Application Delivery Patterns

An Azure VNet is a private address and routing boundary. Subnets divide it by trust zone or workload role, for example ingress, web, application, data, private endpoints, and management. Plan non-overlapping CIDRs with growth capacity, then attach resources through NICs or private integration. NSGs filter allowed source, destination, protocol, and port at subnet/NIC scope; UDRs influence routing; peering connects VNets; VPN Gateway or ExpressRoute provides hybrid connectivity; private endpoints give supported PaaS services private addresses with corresponding private DNS design.

Avoid calling Azure subnets inherently "public" or "private." Their effective exposure depends on public IPs, load-balancer or application-gateway frontends, routes, NAT, NSGs, firewall policy, and the service itself.

### Azure Application Gateway request flow

```text
client -> frontend IP -> listener -> routing rule
       -> HTTP settings and health probe -> backend pool
```

Application Gateway is a regional Layer-7 HTTP/HTTPS load balancer. Listeners receive traffic, rules select a backend by host or path, backend settings define protocol, port, TLS and session behavior, and health probes remove unhealthy targets. Backend pools can include supported VM, scale-set, App Service, AKS, or IP/FQDN targets. WAF adds managed/custom web-attack rules; TLS can terminate at the gateway or be re-encrypted to the backend.

Troubleshoot the resolved frontend address, listener/SNI and certificate, WAF logs, rule priority, rewrite/redirect behavior, backend health, probe host/path/status, NSG/UDR/firewall path, backend TLS trust, and application logs. A healthy gateway does not imply a healthy backend.

### Load Balancer and secure administration

Azure Load Balancer distributes Layer-4 TCP/UDP flows using a frontend, rule, backend pool, and health probe. A common path is internet -> public frontend -> load-balancing rule -> healthy VM backend. Use an internal load balancer for private tier-to-tier traffic.

A jump VM is a hardened administrative VM used as an intermediate access point, but it still needs patching, identity controls, logging, and network protection. Azure Bastion is a managed alternative that provides RDP or SSH access to private VMs without assigning each VM a public IP. Whichever pattern is chosen, use least privilege, just-in-time access, session logging, restricted management sources, and a break-glass procedure.

### NSG and Azure Firewall together

NSGs provide distributed stateful Layer-3/4 filtering close to subnets and NICs. Azure Firewall provides centralized inspection and policy, including network/application rules, threat-intelligence capabilities, DNAT/SNAT, and centralized logs according to SKU and configuration. In a hub-and-spoke design, use UDRs to steer required traffic through the firewall and NSGs to restrict each workload boundary. Validate symmetric routing and effective rules; using both products without a deliberate traffic path does not create defense in depth automatically.
