## 1. What do you monitor on Linux and Windows servers?

**Answer:**

On both platforms I watch CPU and load, plus the top processes. I watch memory and swap usage, and out-of-memory events. I watch disk capacity, inode usage, disk I/O, and how fast disk usage is growing. I watch network errors and connection counts, service and process state, open ports, certificate expiry, time sync, pending updates, and OS and application logs.

I always compare these against request latency, errors, and traffic, because a host can look perfectly healthy while the application running on it is broken.

On Linux I'd typically use node-exporter, journald, and process or service exporters. On Windows I'd use windows_exporter, Performance Monitor counters, and Event Viewer forwarding. Cloud-native or commercial agents can replace or add to any of these.

Alerts should be based on sustained conditions, owned by a specific team, and linked to a runbook.

## 2. How do you investigate a high-CPU alert safely?

**Answer:**

First I confirm the alert is real: how long has it been happening, and is it actually affecting users? I check recent traffic and recent changes, then break the CPU time down into user, system, steal, and I/O-wait time to find the responsible process or thread.

Where I can, I collect application and runtime evidence before restarting anything, since a restart destroys that evidence.

To stabilize things, I shift traffic away, scale out, or stop a task I've confirmed is non-essential and runaway. Then I fix the actual cause: bad code, a slow query, a config issue, a scheduled job, or just not enough capacity.

Afterward I confirm user-facing latency and errors are back to normal, check CPU under real load, and improve the alert or add a regression test so it's caught earlier next time.

## 3. How do you monitor disk exhaustion?

**Answer:**

I track filesystem usage, inode usage, growth rate, and a forecast of when it will hit full, plus disk queue depth on collectors and containers.

When investigating, I look for what's actually growing: a specific directory, files that are open but already deleted, logs, temp data, package caches, or genuine application data.

I clean up using supported rotation and cleanup tools, and I never delete a file in production if I don't know what it is. To prevent this from recurring, I rely on retention policies, quotas, separate capacity where it makes sense, and alerts that fire early enough to act safely.

## 4. How do you identify and investigate the ten highest-memory processes?

**Answer:**

For a point-in-time view I run:

```bash
ps -eo pid,ppid,user,%mem,rss,vsz,etime,cmd --sort=-rss | head -n 11
```

That gives one header line plus the ten highest processes. I sort by RSS rather than VSZ because RSS is the actual resident physical memory in use, though shared memory can still make per-process totals a bit imprecise.

`ps aux --sort=-%mem | head -n 11` works as a shorter alternative.

I don't assume the top process is leaking from a single sample. I check `free -h`, `vmstat 1`, swap usage, and OOM logs. Then I watch that specific PID over time with `pidstat -r -p <pid> 1`, along with application and runtime metrics and historical monitoring data.

I compare the growth pattern against traffic, deployments, and scheduled jobs. If the impact is severe, I scale out or restart gracefully, but only after preserving diagnostics first. Then I fix the actual leak, cache or heap configuration, workload sizing, or resource limit, and confirm memory, latency, and error rate are back to normal under regular load.
