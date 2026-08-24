# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Linux & Troubleshooting

### 1.1 Command to generate an SSH key
```bash
ssh-keygen -t ed25519 -C "you@example.com"      # modern, preferred
ssh-keygen -t rsa -b 4096 -C "you@example.com"  # if ed25519 unsupported
```
This creates a private key at `~/.ssh/id_ed25519` and a public key at `~/.ssh/id_ed25519.pub`. Never share the private key. To copy the public key to a server, run `ssh-copy-id user@host` — it appends the key to `~/.ssh/authorized_keys`.

### 1.2 What if a user loses their SSH key?

You cannot recover the private key. It was never stored on the server, so it is gone for good.

1. Generate a new key pair on the client.
2. Push the new public key to the server. If SSH access is lost entirely, use another path in: the cloud console or a serial connection, an SSM session, a bastion host with a separate credential, or a configuration tool like Ansible to add the new key.
3. Remove the old public key from `~/.ssh/authorized_keys` so it can no longer log in. Rotate anything that key could have reached.

### 1.3 Command to show memory usage & CPU / processes
```bash
free -h          # memory (human readable)
top / htop       # live CPU + memory + per-process view
vmstat 1         # memory, CPU, IO over time
ps aux --sort=-%mem | head   # top memory consumers
ps aux --sort=-%cpu | head   # top CPU consumers
mpstat -P ALL 1  # per-core CPU
```

### 1.4 Command to kill a process
```bash
ps aux | grep <name>     # find PID
kill <PID>               # ask it to stop gracefully
kill -9 <PID>            # force-kill, last resort
pkill -f <pattern>       # kill by command pattern
kill -HUP <PID>          # reload config for many daemons
```
Try a plain `kill` first so the process can clean up after itself. Only use `-9` if it ignores that and refuses to stop.

### 1.5 How do you change user access / privileges?

- Add to a group: `usermod -aG docker alice`.
- Grant sudo: add the user to the `wheel` or `sudo` group, or add a file under `/etc/sudoers.d/` (edit it with `visudo`).
- File permissions: `chmod`, `chown`, and ACLs (`setfacl`).
- Change shell or lock the account: `chsh`, `passwd -l user` to lock it, `usermod -L` or `-U`.
- Best practice: give people only the access they actually need, manage access through groups instead of one-off rules per user, and review `/etc/sudoers` regularly.

### 1.6 Troubleshoot a memory leak on a production Linux server

1. Confirm the trend. Check `free -h`, `vmstat 1`, and your monitoring dashboards. Is memory climbing steadily and never coming back down?
2. Find the process. Use `ps aux --sort=-%rss | head`, `top` (the RES column), or `smem` for a more accurate view. Watch RSS over time, for example with `while true; do ps -o rss= -p <pid>; sleep 5; done`.
3. Check for OOM kills with `dmesg -T | grep -i oom` or `journalctl -k`.
4. Dig into the process using the right tool for its runtime: JVM heap dumps (`jmap`, `jcmd`, then Eclipse MAT), Go's `pprof`, Python's `tracemalloc`/`objgraph`, or native tools like `valgrind`/`heaptrack`.
5. Tell a real leak apart from normal caching. Page cache shows up under `buff/cache` and is reclaimable whenever the kernel needs the space back — that's expected, not a leak.
6. Mitigate now: restart or roll the process, add memory limits (cgroups or systemd's `MemoryMax`), and enable automatic restarts. Then fix the actual bug in the code.

### 1.7 Zombie and orphan processes

A zombie process has already exited, but its parent never called `wait()` to collect its exit status, so its entry lingers in the process table with state `Z`. It uses no memory or CPU, just a slot in the process table. To clear it, get the parent to reap it by handling `SIGCHLD`. If the parent is broken, kill the parent instead — the zombie is re-parented to init and reaped from there. You cannot `kill -9` a zombie; it's already dead.

An orphan is a child process whose parent died first. It gets re-parented to init or systemd (PID 1) right away, and PID 1 reaps it when it exits. This is normally harmless.

In containers, run an init process (`--init` or `tini`) so PID 1 can reap zombies properly.

### 1.8 Debug high I/O latency
```bash
iostat -xz 1        # %util, await, svctm per device
iotop               # per-process IO
dstat / sar -d      # historical
pidstat -d 1        # per-process disk IO
```
Watch `await` (the average I/O wait time in milliseconds) and `%util` — close to 100% means the device is saturated. Also check the `wa` column in `vmstat`, which shows CPU time spent waiting on I/O, and look for processes stuck in uninterruptible sleep (`D` state) with `ps aux | awk '$8 ~ /D/'`.

Common causes are an undersized or degraded disk (for example, EBS gp2 running out of burst credits and getting throttled), a noisy neighbor, swapping, heavy fsync activity, or filesystem fragmentation. Fix it by adding IOPS or throughput, adding caching, batching writes, or moving hot data to faster storage.

### 1.10 Linux server has high load — identify & resolve bottlenecks

Use the USE method across CPU, memory, disk, and network: for each one, check utilization, saturation (how close it is to its limit), and errors.

- Compare `uptime` / load average against the number of cores; watch `top` or `htop`.
- CPU-bound? High `%us`/`%sy` with low idle time points to a specific process — find it and profile it.
- IO-bound? High `wa`, or processes stuck in `D` state — see 1.8 above.
- Memory pressure or swapping? Check `free` and the `si`/`so` columns in `vmstat` — see 1.6 above.
- Too many runnable threads, or a fork bomb? Check the run queue (`r` column) in `vmstat`.

Compare the timing against recent deploys, cron jobs, or traffic spikes. To resolve it: scale out or up, fix the offending process, add resource limits, or tune the workload.

---
