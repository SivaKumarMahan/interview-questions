# Linux: Performance Troubleshooting and Production

> Investigating high CPU, memory, load, and I/O; open-file limits; kernel panics; emergency commands; and moving a server workload to serverless.

## Key Concepts

### Load and performance monitoring

```bash
# System overview
uptime                                # Load average and uptime
w                                     # Who's logged in and doing what
top                                   # Real-time process monitoring
htop                                  # Enhanced process viewer

# Memory analysis
free -h                               # Memory usage summary
cat /proc/meminfo                     # Detailed memory info
vmstat 1 5                            # Virtual memory stats (1 sec intervals, 5 times)

# I/O performance
iostat 1 5                            # Disk I/O statistics
sar 1 5                               # System activity report
```

### Swap usage analysis

```bash
# Check swap status
swapon --show                         # Active swap partitions
cat /proc/swaps                       # Swap usage details
free -h                               # Memory and swap summary
```

High swap usage alone doesn't prove there's memory pressure or a leak. Check swap-in/swap-out activity, available memory, OOM events, page-fault behavior, and per-process growth before deciding whether to tune the workload or add RAM.

### Emergency debugging

```bash
# High CPU investigation
ps aux --sort=-%cpu | head -10        # Top CPU users

# Memory issues
ps aux --sort=-%mem | head -10        # Top memory users
cat /proc/meminfo | grep Available    # Available memory

# Disk space emergency
du -sh /* | sort -hr | head -10       # Largest directories
find /var/log -name "*.log" -size +100M  # Large log files
```

## Interview Questions

<details><summary>Q1. [Intermediate] A service is consuming 100% CPU. How will you find and fix it?</summary>

**Answer:**

First I check whether "100%" means one core or the whole machine, using `top`, `mpstat -P ALL 1`, and `pidstat -u -p ALL 1`. I find the PID and its busiest threads with `top -H -p <pid>`, then compare when it started and when CPU usage rose against traffic, cron jobs, deployments, and the service's own logs.

What I check next depends on the runtime: a Java thread dump (`jstack`), a .NET dump, a Python stack trace, or `strace -p <pid>` for a short, controlled window.

If customers are affected, I rate-limit traffic, pull the unhealthy instance out of the load balancer, scale up healthy replicas, or restart it gracefully after collecting evidence.

The real fix might be correcting an infinite loop, improving a query or index, adding a timeout, setting a resource limit, or adding capacity. Afterward I check CPU, latency, errors, and actual business transactions, and add an alert or regression test for what I found.

</details>

<details><summary>Q2. [Intermediate] How do you troubleshoot high CPU usage on a Linux server? <em>(scenario)</em></summary>

**Answer:** Use `top`, `htop`, `vmstat`, and `iostat` to find the process, then kill or fix it, and scale the infrastructure if needed.

**Detailed interview approach:**
I start the same way: confirm scope, preserve access, then look at CPU with `uptime`, `mpstat`, `pidstat`, and `top`, comparing the busy PID against logs, traffic, and any recent changes.

I work out whether it's a real capacity problem, a stuck process, or I/O wait showing up as load, and I take the smallest safe action — reducing traffic, a graceful restart, or scaling — based on the evidence I've gathered.

I then confirm the application is healthy and check the resource trend, and put in retention, limits, alerts, or a code/config fix so I'm not just restarting things blindly next time.

</details>

<details><summary>Q3. [Basic] How do you find the process using the most CPU right now?</summary>

**Answer:**

I take a snapshot first, then confirm the pattern holds over time:

```bash
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head -n 11
top -o %CPU
pidstat -u 1
```

I check the load average, CPU steal time, I/O wait, recent deployments, and traffic before acting. High load doesn't necessarily mean the CPU itself is saturated — tasks blocked on I/O can drive load up too.

I capture the PID, its service or container owner, and its logs, then mitigate it safely — scaling, rolling back, rate-limiting, or gracefully restarting whichever workload turns out to actually be the problem.

</details>

<details><summary>Q4. [Basic] How do you find the top 5 CPU-consuming and memory-consuming processes?</summary>

**Answer:**

For a snapshot I use:

```bash
ps -eo pid,ppid,user,%cpu,%mem,rss,etime,cmd --sort=-%cpu | head -n 6
ps -eo pid,ppid,user,%cpu,%mem,rss,etime,cmd --sort=-rss  | head -n 6
```

I sort memory by RSS, since `%mem` is derived from it and VSZ can include large chunks of memory that aren't actually resident. A single snapshot can catch a brief spike or miss one entirely, so I confirm with `pidstat 1`, `top`, or historical data from `sar`/`atop`.

I also map each PID back to its service or container and compare it against request rate and any recent changes before deciding a process is actually abnormal.

</details>

<details><summary>Q5. [Basic] Command to show memory usage &amp; CPU / processes <em>(asked in interview round)</em></summary>

```bash
free -h          # memory (human readable)
top / htop       # live CPU + memory + per-process view
vmstat 1         # memory, CPU, IO over time
ps aux --sort=-%mem | head   # top memory consumers
ps aux --sort=-%cpu | head   # top CPU consumers
mpstat -P ALL 1  # per-core CPU
```

</details>

<details><summary>Q6. [Basic] How do you find free memory?</summary>

**Answer:**

`free -h` — but I look at the `available` column, not `free`, because Linux uses spare RAM for cache that it can reclaim when needed. `vmstat 1` shows swap activity (`si`/`so`) and how many processes are running or blocked. `ps --sort=-%mem`, `smem`, `pmap`, and `pidstat -r` help identify what's using the memory.

I also check the kernel's out-of-memory logs: `journalctl -k | grep -i oom`.

I look at this against the actual workload and its trend over time. High used memory or cache alone is normal. Sustained swapping, allocation failures, OOM kills, or rising latency are the real signs of pressure.

I fix the actual cause — a leak, a cache setting, a config change — or right-size and scale the service based on evidence. Restarting is only a temporary fix, and I preserve diagnostics before doing it.

</details>

<details><summary>Q7. [Basic] How do you find which process is consuming the most memory?</summary>

**Answer:**

For a quick snapshot I use:

```bash
ps aux --sort=-%mem | head -n 11
```

The first line is the header, so `head -n 11` shows ten actual processes. For real investigation I prefer explicit columns sorted by resident memory:

```bash
ps -eo pid,ppid,user,%mem,rss,vsz,etime,cmd --sort=-rss | head -n 11
```

RSS is the physical memory the process actually has resident right now; VSZ includes virtual mappings and can look large without meaning real memory pressure. `%MEM` is fine for a quick comparison, but a single snapshot doesn't tell you if usage is growing.

I confirm system-wide pressure with `free -h`, `vmstat 1`, swap activity, and OOM evidence from `journalctl -k | grep -i oom`. Then I map the PID to its systemd service, container, or application, and watch it with `pidstat -r -p <pid> 1` or a runtime-specific tool.

Before restarting or killing anything, I capture logs and heap or thread diagnostics where relevant, confirm the actual user impact, and try graceful service control first. The permanent fix might be correcting a memory leak, tuning a cache or heap setting, setting resource limits, scaling traffic, or adding capacity.

</details>

<details><summary>Q8. [Intermediate] A process is causing high memory usage. How do you locate and stop it?</summary>

**Answer:**

I check both overall system pressure and the specific process:

```bash
free -m
vmstat 1
ps -eo pid,ppid,user,%mem,rss,vsz,cmd --sort=-rss | head
pmap -x <pid> | tail -1
```

RSS is resident memory; VSZ alone can be misleading. I check swap activity, OOM messages (`journalctl -k | grep -i oom`), container or cgroup limits, the request load, and whether memory keeps climbing, which points to a leak.

Where it's safe, I capture a heap dump or runtime metrics before stopping the process. I use `systemctl stop` or `kill -TERM` first, and only `kill -KILL` if a graceful shutdown fails.

Then I fix the actual leak or cache setting, set realistic limits and alerts, and load-test the fix.

</details>

<details><summary>Q9. [Advanced] Troubleshoot a memory leak on a production Linux server <em>(asked in interview round)</em></summary>

1. Confirm the trend. Check `free -h`, `vmstat 1`, and your monitoring dashboards. Is memory climbing steadily and never coming back down?
2. Find the process. Use `ps aux --sort=-%rss | head`, `top` (the RES column), or `smem` for a more accurate view. Watch RSS over time, for example with `while true; do ps -o rss= -p <pid>; sleep 5; done`.
3. Check for OOM kills with `dmesg -T | grep -i oom` or `journalctl -k`.
4. Dig into the process using the right tool for its runtime: JVM heap dumps (`jmap`, `jcmd`, then Eclipse MAT), Go's `pprof`, Python's `tracemalloc`/`objgraph`, or native tools like `valgrind`/`heaptrack`.
5. Tell a real leak apart from normal caching. Page cache shows up under `buff/cache` and is reclaimable whenever the kernel needs the space back — that's expected, not a leak.
6. Mitigate now: restart or roll the process, add memory limits (cgroups or systemd's `MemoryMax`), and enable automatic restarts. Then fix the actual bug in the code.

</details>

<details><summary>Q10. [Intermediate] How do you analyze high system load?</summary>

**Answer:**

Load average counts both runnable tasks and tasks stuck waiting on I/O, so it's not the same thing as CPU percentage. I compare the 1/5/15-minute load numbers against the CPU count, then use `vmstat 1` (looking at run/block queues and swap), `mpstat -P ALL 1`, `iostat -xz 1`, and `pidstat -dur 1` to figure out what the actual bottleneck is.

A high run-queue with busy CPUs points to CPU contention. A high block count, I/O wait, or long disk queues point to storage. Swapping and major page faults point to memory pressure. I also check `ps` for processes stuck in D state and look at NFS or downstream service latency.

I address whatever resource or workload is actually the problem, compare it against the normal baseline and any recent changes, and confirm latency and errors actually recover — not just that the load number dropped.

</details>

<details><summary>Q11. [Intermediate] Linux server has high load — identify &amp; resolve bottlenecks <em>(asked in interview round)</em></summary>

Use the USE method across CPU, memory, disk, and network: for each one, check utilization, saturation (how close it is to its limit), and errors.

- Compare `uptime` / load average against the number of cores; watch `top` or `htop`.
- CPU-bound? High `%us`/`%sy` with low idle time points to a specific process — find it and profile it.
- IO-bound? High `wa`, or processes stuck in `D` state — see 1.8 above.
- Memory pressure or swapping? Check `free` and the `si`/`so` columns in `vmstat` — see 1.6 above.
- Too many runnable threads, or a fork bomb? Check the run queue (`r` column) in `vmstat`.

Compare the timing against recent deploys, cron jobs, or traffic spikes. To resolve it: scale out or up, fix the offending process, add resource limits, or tune the workload.

</details>

<details><summary>Q12. [Basic] How do you check disk I/O performance?</summary>

**Answer:**

I start with `iostat -xz 1`, `vmstat 1`, and `pidstat -d 1`. I compare throughput and IOPS against what the disk is actually rated for, and look at `await`, average queue size, utilization, and how much CPU time is spent waiting on I/O.

`iotop` helps pin down the exact process, and cloud metrics can reveal throttled IOPS or throughput, or exhausted burst credits.

High utilization by itself isn't necessarily bad — the real evidence is rising latency and actual application impact. I compare it against backups, queries, compaction jobs, deployments, and kernel or storage errors happening around the same time.

Fixes can include tuning a query or index, adding caching, moving batch jobs to a quieter time, separating data and log volumes onto different disks, provisioning more IOPS, or scaling up. I take a baseline and remeasure the same workload after making the change.

</details>

<details><summary>Q13. [Intermediate] Debug high I/O latency <em>(asked in interview round)</em></summary>

```bash
iostat -xz 1        # %util, await, svctm per device
iotop               # per-process IO
dstat / sar -d      # historical
pidstat -d 1        # per-process disk IO
```
Watch `await` (the average I/O wait time in milliseconds) and `%util` — close to 100% means the device is saturated. Also check the `wa` column in `vmstat`, which shows CPU time spent waiting on I/O, and look for processes stuck in uninterruptible sleep (`D` state) with `ps aux | awk '$8 ~ /D/'`.

Common causes are an undersized or degraded disk (for example, EBS gp2 running out of burst credits and getting throttled), a noisy neighbor, swapping, heavy fsync activity, or filesystem fragmentation. Fix it by adding IOPS or throughput, adding caching, batching writes, or moving hot data to faster storage.

</details>

<details><summary>Q14. [Intermediate] How do you fix "Too many open files" in Linux?</summary>

**Answer:**

I figure out whether this is a per-process limit or a system-wide one. I check `cat /proc/<pid>/limits`, count descriptors with `ls /proc/<pid>/fd | wc -l`, look at what they are with `lsof -p <pid>`, and check `/proc/sys/fs/file-nr`.

Repeated sockets or files of the same type usually point to a leak somewhere.

For a systemd service, a controlled way to raise the limit is:

```ini
[Service]
LimitNOFILE=65536
```

After `systemctl daemon-reload`, I restart during an approved window and confirm the new limit with `/proc/<new-pid>/limits`. Raising the limit only buys time if the application is leaking connections, so I also fix how it closes or pools connections, tune traffic if needed, and set an alert well before the new limit is hit.

</details>

<details><summary>Q15. [Advanced] How do you debug a kernel panic?</summary>

**Answer:**

My first priority is saving the panic message and getting service back up through the approved failover or reboot procedure. I collect the console or serial output, hypervisor events, the previous boot's journal (`journalctl -k -b -1`), and any crash dump under `/var/crash`.

I note the kernel version and any recent changes to drivers, kernel, firmware, hardware, or workload.

If `kdump` is set up, I analyze the matching unstripped kernel and crash dump with the `crash` tool, or hand them to the vendor. I look for the module that faulted, the stack trace, machine-check errors, OOM or panic settings, and whether it's reproducible.

A temporary fix might be rolling back a kernel or driver, or moving the workload elsewhere. The real fix is a patched kernel, driver, or replacing failed hardware. I make sure `kdump` works and console access is ready before the next incident.

</details>

<details><summary>Q16. [Advanced] You have hosted an application on a Linux server - how would you migrate it to a serverless architecture in azure?</summary>

To migrate an application from a Linux server to a serverless setup in Azure, I'd follow these steps:

1. **Assess the application.** Understand its architecture, dependencies, and components to see which parts can move to serverless.
2. **Choose the Azure services.** For example, `Azure Functions` for compute, `Azure Logic Apps` for workflows, and `Azure Blob Storage` for static content.
3. **Refactor the application.** Change the code to fit the serverless model, breaking it into smaller functions where needed.
4. **Set up the Azure environment.** Create the Function Apps, Storage Accounts, and any other resources you need.
5. **Deploy the application.** Use Azure DevOps or another CI/CD tool to deploy the refactored app.
6. **Test and optimize.** Test it thoroughly in the serverless environment and tune it for performance and cost.
7. **Monitor and maintain.** Set up `Azure Monitor` and `Application Insights` so you can see the application is running smoothly.

</details>
