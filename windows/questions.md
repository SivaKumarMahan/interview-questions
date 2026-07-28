## 1. What Windows Server tasks have you handled?

**Answer:**

Typical work includes user/group access, services, Event Viewer, IIS, scheduled tasks, patching, Windows Firewall, disks, RDP, certificates, backups, and PowerShell automation. I explain a concrete incident rather than listing tools.

Example: an IIS application returned 503. I confirmed scope from the load balancer, checked application-pool state and Event Viewer, found the service account password had expired, rotated it through the approved process, updated the pool identity, and restarted only that pool.

I validated the health endpoint and a real transaction, monitored errors, and prevented recurrence by using a managed service account and credential-expiry alert.

## 2. How do you check Windows service status?

**Answer:**

```powershell
Get-Service -Name W3SVC
Get-CimInstance Win32_Service -Filter "Name='W3SVC'" |
    Select-Object Name, State, StartMode, StartName, PathName
```

`Get-Service` provides quick status; CIM adds startup account and binary details. If a service is stopped, I do not restart blindly.

I check dependent services, recent changes, System/Application logs, executable path, service account, permissions, ports, and resource pressure.

After a controlled start I verify `Status`, listening port, application health, and monitoring. Repeated failure requires the service-specific log and exit code, not an endless restart loop.

## 3. How do you restart a Windows service with PowerShell?

**Answer:**

```powershell
$service = Get-Service -Name W3SVC -ErrorAction Stop
Restart-Service -InputObject $service -ErrorAction Stop
$service.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
Get-Service -Name W3SVC
```

Before restarting a production service I confirm impact, approval, redundancy, and rollback. I drain the node from a load balancer if necessary and capture relevant logs first because restart can remove evidence.

Afterward I test the port, health endpoint, dependencies, and error rate. If it fails again, I stop retries and investigate configuration, credentials, dependency availability, or resource exhaustion.

## 4. Where do you check Windows logs?

**Answer:**

I use Event Viewer or PowerShell. Main channels include Application, System, Security, Setup, and service-specific logs under Applications and Services Logs.

```powershell
Get-WinEvent -FilterHashtable @{
  LogName='System'
  Level=1,2,3
  StartTime=(Get-Date).AddHours(-2)
} | Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message
```

I filter by incident time, provider, event ID, hostname, and correlation data, then compare recent changes. For multiple servers I centralize logs in a SIEM/Log Analytics platform and synchronize time.

I preserve relevant events before cleanup and avoid treating every warning as the root cause.

## 5. How do you troubleshoot high CPU on Windows?

**Answer:**

I confirm whether CPU is sustained and whether users are affected, then identify the process using Task Manager, Resource Monitor, Performance Monitor, or PowerShell.

```powershell
Get-Process | Sort-Object CPU -Descending |
  Select-Object -First 10 Name, Id, CPU, WorkingSet
```

I compare process CPU with request rate, scheduled tasks, antivirus, updates, application logs, thread count, and recent releases. For IIS I identify the application pool associated with `w3wp.exe`.

I capture a dump or performance trace before restarting when possible.

The fix may be bad code/query correction, configuration change, workload scaling, or stopping a runaway task. I validate response time and CPU after the change and add an alert with a runbook.

## 6. How do you troubleshoot disk-full issues on Windows?

**Answer:**

I identify the full volume and growth source using Storage settings, TreeSize/approved tools, or PowerShell. I check IIS logs, temp directories, crash dumps, Windows Update cache, backups, and application data.

I do not delete unfamiliar files. First I stop or control the producer, archive/rotate supported logs, and clean approved temporary data.

If a large deleted file remains held open, I identify the process. If growth is legitimate, I extend the disk/filesystem after checking backup and platform limits.

After recovery I restart only affected services, verify free space and application writes, and prevent recurrence with retention policies, quotas, capacity alerts, and ownership of high-growth directories.

## 7. How do you schedule tasks in Windows?

**Answer:**

I use Task Scheduler or `Register-ScheduledTask`, define the exact identity, trigger, action, working directory, timeout, retry behavior, and failure logging.

```powershell
$action = New-ScheduledTaskAction -Execute 'PowerShell.exe' \
  -Argument '-NoProfile -File C:\Ops\cleanup.ps1'
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName 'ApprovedCleanup' \
  -Action $action -Trigger $trigger -User 'DOMAIN\svc-ops'
```

The service account has least privilege (only the permissions needed) and managed credentials where possible. I test manually under the same identity because interactive success does not prove scheduled success.

I check history, exit code, logs, overlap behavior, missed-run handling, and alerts.

## 8. How do you patch Windows servers safely?

**Answer:**

My patch process is inventory and risk review → backup/recovery check → test ring → staged production rings → validation. I use WSUS, Configuration Manager, Azure Update Manager, or another governed platform.

Before patching I confirm dependencies, cluster/load-balancer behavior, disk space, pending reboot, maintenance approval, and rollback limitations.

I drain one redundant node, install approved updates, reboot, validate services, ports, application transactions, monitoring, and event logs, then continue to the next node.
For a failure I stop the rollout, preserve evidence, use documented uninstall/restore/failover steps, and communicate impact. Patch compliance, exceptions, reboot status, and post-patch incidents are recorded and reviewed.
