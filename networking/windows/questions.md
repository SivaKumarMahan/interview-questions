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

`netstat -ano` works too. I check whether the service is listening on the interface I expect — `127.0.0.1`, a private IP, or all interfaces — map the PID to its process or service, and then check Windows Firewall, network security rules, routing, DNS, and any load-balancer probes upstream.

A port listening locally doesn't prove it's reachable remotely, so I test from the actual client network and check the logs on both ends.

---

### 2. How do you manage Windows Firewall rules?

**Answer:**

I write narrow, documented rules scoped by protocol, port, direction, profile, program or service, and remote address.

```powershell
New-NetFirewallRule -DisplayName 'Allow HTTPS from load balancer' \
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443 \
  -RemoteAddress 10.20.0.0/24 -Profile Domain
```

Before touching production I export and review the current policy and confirm exactly what was requested. Then I test with both an allowed source and a denied source.

I deploy rules through Group Policy, configuration management, or infrastructure-as-code wherever possible, rather than making unmanaged manual changes. Logging and a periodic review help catch rules that are unused or too broad.

---

### 3. What is PowerShell remoting?

**Answer:**

PowerShell remoting runs commands on a remote system, usually over WinRM — using Kerberos inside a domain, or HTTPS with certificates where that fits better.

```powershell
Test-WSMan server01
Invoke-Command -ComputerName server01 -ScriptBlock {
    Get-Service W3SVC
}
```

I restrict it with firewall scoping, groups that only get the access they need, Just Enough Administration endpoints, logging and transcription, and secure authentication. I avoid TrustedHosts wildcards and plaintext credentials.

When troubleshooting, I look at DNS, time sync and Kerberos, the WinRM listener, the firewall, SPNs, user permissions, and the double-hop problem.

---

### 4. How do you troubleshoot RDP connection issues?

**Answer:**

I treat network, service, authentication, and capacity as separate things to check:

1. Resolve the correct IP and test TCP 3389 from the client.
2. Check the cloud security group, Windows Firewall, VPN/routes, and NAT.
3. Confirm Remote Desktop Services is running and listening.
4. Verify the user is allowed to connect, the account isn't locked, and NLA, time sync, and domain trust are all healthy.
5. Check the TerminalServices and Security event logs, and see who's currently connected.
6. Use Bastion or a serial/console connection for recovery, rather than opening RDP up broadly.

Once it's fixed, I remove any temporary access I opened, confirm normal approved connections still work, and keep RDP private behind a VPN or Bastion with MFA and monitoring.
