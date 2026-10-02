# Windows: Administration, Services, and Patching

> Day-to-day Windows Server tasks: managing services with PowerShell, scheduled tasks, and safe patching.

## Interview Questions

### 1. What Windows Server tasks have you handled?

**Answer:**

Typical work includes user and group access, services, Event Viewer, IIS, scheduled tasks, patching, Windows Firewall, disks, RDP, certificates, backups, and PowerShell automation. Instead of just listing tools, I like to walk through a real incident.

Example: an IIS application started returning 503 errors. I confirmed the scope from the load balancer, checked the application-pool state and Event Viewer, and found the service account's password had expired. I rotated it through the approved process, updated the pool identity, and restarted only that pool.

I checked the health endpoint and a real transaction worked, watched for errors afterward, and prevented it happening again by switching to a managed service account with a credential-expiry alert.

### 2. How do you check Windows service status?

**Answer:**

```powershell
Get-Service -Name W3SVC
Get-CimInstance Win32_Service -Filter "Name='W3SVC'" |
    Select-Object Name, State, StartMode, StartName, PathName
```

`Get-Service` gives a quick status check; the CIM query adds the startup account and binary path. If a service is stopped, I don't just restart it blindly.

I check dependent services, any recent changes, the System and Application logs, the executable path, the service account, permissions, ports, and whether resources are under pressure.

After a controlled start, I verify the `Status`, the listening port, application health, and monitoring. If it keeps failing, I look at the service-specific log and exit code instead of restarting it over and over.

### 3. How do you restart a Windows service with PowerShell?

**Answer:**

```powershell
$service = Get-Service -Name W3SVC -ErrorAction Stop
Restart-Service -InputObject $service -ErrorAction Stop
$service.WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
Get-Service -Name W3SVC
```

Before restarting a production service, I check the impact, get approval, confirm there's redundancy, and know how I'd roll back. I drain the node from the load balancer if needed and grab the relevant logs first, since a restart can wipe out evidence of what went wrong.

Afterward I test the port, the health endpoint, dependencies, and the error rate. If it fails again, I stop retrying and look into the configuration, credentials, a missing dependency, or resource exhaustion instead.

### 4. How do you schedule tasks in Windows?

**Answer:**

I use Task Scheduler or `Register-ScheduledTask`, and define the exact identity, trigger, action, working directory, timeout, retry behavior, and failure logging.

```powershell
$action = New-ScheduledTaskAction -Execute 'PowerShell.exe' \
  -Argument '-NoProfile -File C:\Ops\cleanup.ps1'
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName 'ApprovedCleanup' \
  -Action $action -Trigger $trigger -User 'DOMAIN\svc-ops'
```

The service account only gets the permissions it actually needs, with managed credentials where possible. I test it manually under the same identity, since it running fine interactively doesn't prove it will run fine on a schedule.

I check the run history, exit code, logs, whether overlapping runs are handled, what happens to a missed run, and that alerts are in place.

### 5. How do you patch Windows servers safely?

**Answer:**

My process is: inventory and risk review, then a backup/recovery check, a test ring, staged production rings, and validation. I use WSUS, Configuration Manager, Azure Update Manager, or another governed platform to run it.

Before patching, I check dependencies, how the cluster or load balancer will behave, disk space, whether a reboot is already pending, maintenance approval, and how hard it would be to roll back.

I drain one redundant node, install the approved updates, reboot it, and check its services, ports, application transactions, monitoring, and event logs before moving on to the next node.

If something fails, I stop the rollout, preserve the evidence, follow the documented uninstall, restore, or failover steps, and communicate the impact. Patch compliance, exceptions, reboot status, and any post-patch incidents all get recorded and reviewed afterward.
