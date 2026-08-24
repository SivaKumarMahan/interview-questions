## 1. How do you troubleshoot high disk usage in Linux servers used for CI/CD?

**Answer:** Run `du -sh /*` to find the big directories, clear `/var/log`, remove old Docker images, and archive old build artifacts.

**Detailed interview approach:**
I start by confirming the scope of the problem and making sure I still have access before I change anything. For disk usage I check `df -hT`, `df -i`, `du -x`, and `lsof +L1` to see whether space or inodes are the issue and whether a deleted file is still held open.

Then I work out what's actually happening: is it real growth, a leak, an open-but-deleted file, unrotated logs, or just heavy I/O? I fix it with the smallest safe action first — reducing traffic, letting a service shut down cleanly, running an approved cleanup or rotation, or adding capacity — and I only act after I've gathered evidence.

Once things are stable, I check that the application is healthy and look at the resource trend over time. Then I add retention rules, limits, and alerts, or fix the underlying code or config, instead of just scheduling blind restarts or deletions.

## 2. How do you handle a disk full issue in Linux?

**Answer:** Run `df -h` to check usage, clear logs from `/var/log`, remove unused Docker images and containers, and expand the disk if needed.

**Detailed interview approach:**
Same investigation pattern as above: confirm scope, preserve access, then check `df -hT`, `df -i`, `du -x`, and `lsof +L1` to see exactly where the space went.

I separate a genuine capacity problem from a leak, an open-deleted file, unrotated logs, or heavy I/O, and I mitigate with the smallest safe step — cutting traffic, a graceful service restart, an approved cleanup, or adding capacity — only after I've collected the evidence.

Afterward I check application health and the resource trend, then put in retention, limits, and alerts rather than relying on manual restarts or deletions going forward.

## 3. How do you troubleshoot high CPU usage on a Linux server?

**Answer:** Use `top`, `htop`, `vmstat`, and `iostat` to find the process, then kill or fix it, and scale the infrastructure if needed.

**Detailed interview approach:**
I start the same way: confirm scope, preserve access, then look at CPU with `uptime`, `mpstat`, `pidstat`, and `top`, comparing the busy PID against logs, traffic, and any recent changes.

I work out whether it's a real capacity problem, a stuck process, or I/O wait showing up as load, and I take the smallest safe action — reducing traffic, a graceful restart, or scaling — based on the evidence I've gathered.

I then confirm the application is healthy and check the resource trend, and put in retention, limits, alerts, or a code/config fix so I'm not just restarting things blindly next time.
