# Windows: Logs and Troubleshooting

> Where to find Windows logs, and how to troubleshoot high CPU and full disks.

## Interview Questions

<details><summary>Q1. [Basic] Where do you check Windows logs?</summary>

**Answer:**

I use Event Viewer or PowerShell. The main channels are Application, System, Security, Setup, and any service-specific logs under Applications and Services Logs.

```powershell
Get-WinEvent -FilterHashtable @{
  LogName='System'
  Level=1,2,3
  StartTime=(Get-Date).AddHours(-2)
} | Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message
```

I filter by the incident time, provider, event ID, hostname, and any correlation data, then compare it against recent changes. Across multiple servers I centralize logs in a SIEM or Log Analytics platform and keep the clocks in sync.

I save the relevant events before any cleanup happens, and I don't treat every warning as the root cause.

</details>

<details><summary>Q2. [Intermediate] How do you troubleshoot high CPU on Windows?</summary>

**Answer:**

I confirm whether the CPU load is sustained and whether users are actually affected, then find the process using Task Manager, Resource Monitor, Performance Monitor, or PowerShell.

```powershell
Get-Process | Sort-Object CPU -Descending |
  Select-Object -First 10 Name, Id, CPU, WorkingSet
```

I compare the process's CPU usage against request rate, scheduled tasks, antivirus activity, updates, application logs, thread count, and any recent releases. For IIS, I identify which application pool `w3wp.exe` belongs to.

Where possible, I capture a dump or performance trace before restarting anything.

The actual fix might be correcting bad code or a slow query, a configuration change, scaling the workload, or stopping a runaway task. Afterward I confirm response time and CPU are back to normal and add an alert with a runbook for next time.

</details>

<details><summary>Q3. [Intermediate] How do you troubleshoot disk-full issues on Windows?</summary>

**Answer:**

I find the full volume and what's filling it using Storage settings, an approved tool like TreeSize, or PowerShell. I check IIS logs, temp directories, crash dumps, the Windows Update cache, backups, and application data.

I don't delete files I don't recognize. First I stop or control whatever is producing the growth, archive or rotate the logs that support it, and clean up approved temporary data.

If a large deleted file is still holding space because a process has it open, I find that process. If the growth is legitimate, I extend the disk or filesystem after checking the backup and platform limits.

After recovering space, I restart only the affected services, confirm there's free space and the application is writing normally, and prevent it recurring with retention policies, quotas, capacity alerts, and clear ownership of directories that tend to grow.

</details>
