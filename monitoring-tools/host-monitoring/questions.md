## 1. What do you monitor on Linux and Windows servers?

**Answer:**

I monitor CPU/load and top processes, memory/swap and OOM, disk capacity/inodes/I/O and growth, network errors/connections, service/process state, ports, certificates/time, updates and OS/application logs. I correlate all of them with request latency, errors and traffic because a healthy host can still serve a broken application.

Linux may use node-exporter, journald and process/service exporters; Windows may use windows_exporter, Performance Monitor counters and Event Viewer forwarding. Cloud-native or commercial agents can replace or complement them. Alerts are sustained, owned and connected to runbooks.

## 2. How do you investigate a high-CPU alert safely?

**Answer:**

I confirm impact and duration, compare traffic and recent changes, then identify user/system/steal/I/O-wait time and the responsible process/thread. I collect application/runtime evidence before restart where possible. I stabilize by shifting traffic, scaling or stopping a proven nonessential runaway task, then fix code, query, configuration, scheduled work or capacity. I validate user latency/errors and CPU under load and improve the alert or regression test.

## 3. How do you monitor disk exhaustion?

**Answer:**

I track filesystem usage, inodes, growth rate and forecasted time to full, plus collector/container disk queues. Investigation identifies the growing directory, open-deleted files, logs, temporary data, package/cache or legitimate application data. I use supported rotation/cleanup and never delete unknown production files. Prevention includes retention, quotas, separate capacity where appropriate and alerts early enough for safe action.

## 4. How do you identify and investigate the ten highest-memory processes?

**Answer:**

For a point-in-time view I run:

```bash
ps -eo pid,ppid,user,%mem,rss,vsz,etime,cmd --sort=-rss | head -n 11
```

The output contains one header plus ten processes. Sorting by RSS is more useful than sorting by VSZ because RSS represents resident physical memory, although shared memory can still make per-process totals imperfect. `ps aux --sort=-%mem | head -n 11` is a shorter alternative.

I do not conclude that the first process is leaking based on one sample. I check `free -h`, `vmstat 1`, swap and OOM logs, then observe the PID with `pidstat -r -p <pid> 1`, application/runtime metrics and historical monitoring. I correlate growth with traffic, deployments and scheduled jobs. If impact is severe, I scale or gracefully restart only after preserving diagnostics; then I fix the leak, cache/heap configuration, workload sizing or resource limit and verify memory, latency and error rate under normal load.
