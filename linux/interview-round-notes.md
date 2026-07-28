# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Linux & Troubleshooting

### 1.1 Command to generate an SSH key
```bash
ssh-keygen -t ed25519 -C "you@example.com"      # modern, preferred
ssh-keygen -t rsa -b 4096 -C "you@example.com"  # if ed25519 unsupported
```
- Private key → `~/.ssh/id_ed25519` (never share). Public key → `~/.ssh/id_ed25519.pub`.
- Copy public key to a server: `ssh-copy-id user@host` (appends to `~/.ssh/authorized_keys`).

### 1.2 What if a user loses their SSH key?

The private key **cannot be recovered** — it is not stored on the server. You:
1. Generate a **new** key pair on the client.
2. Push the new public key to the server. If SSH access is lost entirely, use an out-of-band path: cloud console/serial connection, an IAM/SSM session (AWS SSM Session Manager), a bastion with a separate credential, or your config-management tool (Ansible) to inject the new key.
3. **Remove the old public key** from `~/.ssh/authorized_keys` so the lost key can no longer authenticate. Rotate anything the compromised key could reach.

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
kill <PID>               # SIGTERM (graceful)
kill -9 <PID>            # SIGKILL (force, last resort)
pkill -f <pattern>       # kill by command pattern
kill -HUP <PID>          # reload config for many daemons
```
Prefer SIGTERM first so the process can clean up; use `-9` only if it ignores TERM.

### 1.5 How do you change user access / privileges?

- **Add to a group:** `usermod -aG docker alice` (add supplementary group).
- **sudo access:** add the user to `wheel`/`sudo` group, or add a file under `/etc/sudoers.d/` (edit with `visudo`).
- **File permissions:** `chmod`, `chown`, and ACLs (`setfacl`).
- **Change shell/lock:** `chsh`, `passwd -l user` (lock), `usermod -L/-U`.
- Best practice: grant least privilege (only the permissions needed), use groups not per-user rules, and audit `/etc/sudoers`.

### 1.6 Troubleshoot a memory leak on a production Linux server

1. **Confirm & trend:** `free -h`, `vmstat 1`, and monitoring dashboards — is memory growing monotonically and not reclaimed?
2. **Isolate the process:** `ps aux --sort=-%rss | head`, `top` (RES column), `smem` for PSS. Watch RSS over time (`while true; do ps -o rss= -p <pid>; sleep 5; done`).
3. **Check for OOM kills:** `dmesg -T | grep -i oom`, `journalctl -k`.
4. **Dig into the process:** language-specific tooling — JVM heap dumps (`jmap`, `jcmd`, then Eclipse MAT), Go `pprof`, Python `tracemalloc`/`objgraph`, native `valgrind`/`heaptrack`.
5. **Cache vs leak:** distinguish real leaks from page cache (page cache is reclaimable and shows under `buff/cache`).
6. **Mitigate now:** restart/roll the process, add memory limits (cgroups/systemd `MemoryMax`), enable automatic restarts. **Fix root cause** in code.

### 1.7 Zombie and orphan processes

- **Zombie (defunct):** a child that exited but the parent hasn't `wait()`ed, so its entry lingers in the process table (state `Z`). It consumes no memory/CPU, only a PID slot. Fix: get the **parent** to reap it (handle `SIGCHLD`); if the parent is broken, kill the parent — the zombie is re-parented to init and reaped. You cannot `kill -9` a zombie (it's already dead).
- **Orphan:** a child whose parent died first. It is immediately **re-parented to init/systemd (PID 1)**, which reaps it on exit — normally harmless.
- In containers, run an init (`--init`, `tini`) so PID 1 reaps zombies.

### 1.8 Debug high I/O latency
```bash
iostat -xz 1        # %util, await, svctm per device
iotop               # per-process IO
dstat / sar -d      # historical
pidstat -d 1        # per-process disk IO
```
- Look at `await` (avg I/O wait ms) and `%util` (≈100% = saturated device).
- Check `vmstat` `wa` column (CPU waiting on IO) and load average driven by `D`-state (uninterruptible) processes: `ps aux | awk '$8 ~ /D/'`.
- Common causes: undersized/degraded disk (EBS gp2 burst credits exhausted, throttling), noisy neighbor, swapping, fsync-heavy workloads, filesystem fragmentation. Resolve by adding IOPS/throughput, adding caching, batching writes, or moving hot data to faster storage.

### 1.10 Linux server has high load — identify & resolve bottlenecks

Use the USE method (Utilization, Saturation (how close a resource is to its limit), Errors) across CPU, memory, disk, network:
- `uptime` / load average vs core count; `top`/`htop`.
- **CPU-bound?** high `%us`/`%sy`, low idle → find the process, profile it.
- **IO-bound?** high `wa`, `D`-state processes → see §1.8.
- **Memory pressure/swap?** `free`, `vmstat` `si/so` → see §1.6.
- **Too many runnable threads / fork bomb?** check run queue in `vmstat` `r`.
Compare with recent deploys, cron jobs, traffic spikes. Resolve: scale out/up, fix the offending process, add limits, tune the workload.

---
