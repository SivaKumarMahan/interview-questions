# Windows Networking Interview Questions

### 1. How do you check listening ports on Windows?

**Answer:**

```powershell
Get-NetTCPConnection -State Listen |
  Sort-Object LocalPort |
  Select-Object LocalAddress, LocalPort, OwningProcess

Get-Process -Id <pid>
Test-NetConnection server.example.com -Port 443
```

`netstat -ano` is another option. I verify whether the service listens on the expected interface (`127.0.0.1`, a private IP, or all interfaces), map PID to process/service, and then check Windows Firewall, network security rules, routing, DNS, and upstream load-balancer probes.

A local listening port does not prove remote reachability, so I test from the actual client network and inspect logs on both ends.

---

### 2. How do you manage Windows Firewall rules?

**Answer:**

I create narrowly scoped, documented rules by protocol, port, direction, profile, program/service, and remote address.

```powershell
New-NetFirewallRule -DisplayName 'Allow HTTPS from load balancer' \
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443 \
  -RemoteAddress 10.20.0.0/24 -Profile Domain
```

Before changing production I export/review current policy and confirm the request. I test an allowed source and a denied source. Rules are deployed through Group Policy, configuration management, or IaC where possible, not unmanaged manual changes. Logging and periodic review find unused or overly broad rules.

---

### 3. What is PowerShell remoting?

**Answer:**

PowerShell remoting runs commands on remote systems, commonly through WinRM using Kerberos in a domain or HTTPS/certificate-based configuration where appropriate.

```powershell
Test-WSMan server01
Invoke-Command -ComputerName server01 -ScriptBlock {
    Get-Service W3SVC
}
```

I restrict remoting with firewall scope, least-privilege groups, Just Enough Administration endpoints, logging/transcription, and secure authentication. I avoid TrustedHosts wildcards and plaintext credentials. Troubleshooting covers DNS, time/Kerberos, WinRM listener, firewall, SPNs, user permissions, and the double-hop problem.

---

### 4. How do you troubleshoot RDP connection issues?

**Answer:**

I separate network, service, authentication, and capacity causes:

1. Resolve the correct IP and test TCP 3389 from the client.
2. Check cloud NSG/security group, Windows Firewall, VPN/routes, and NAT.
3. Confirm Remote Desktop Services is running and listening.
4. Verify the user is allowed, account is not locked, and NLA/time/domain trust are healthy.
5. Check TerminalServices and Security event logs and current sessions.
6. Use Bastion or serial/console access for recovery rather than opening RDP broadly.

After fixing, I remove temporary access, verify normal approved connectivity, and keep RDP private behind VPN/Bastion with MFA and monitoring.
