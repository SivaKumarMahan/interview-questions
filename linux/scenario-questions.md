## 1. How do you troubleshoot high disk usage in Linux servers used for CI/CD?

**Answer:** Run du -sh /* → Clear /var/log → Remove old Docker images → Archive old build artifacts.

**Detailed interview approach:**
I confirm scope and preserve access before changing anything. For disk I check `df -hT`, `df -i`, `du -x`, and `lsof +L1`; for CPU I use `uptime`, `mpstat`, `pidstat`, `top`, and compare the PID with logs, traffic, and recent changes.

I distinguish capacity from leaks, open-deleted files, unrotated logs, I/O wait, or a hot application thread. I mitigate with the smallest safe action—traffic reduction, graceful service handling, approved cleanup/rotation, or capacity—after collecting evidence.

I verify application health and resource trends and then add retention, limits, alerts, or a code/configuration fix rather than scheduling blind restarts or deletions.

## 2. How do you handle a disk full issue in Linux?

**Answer:** Run df -h to check usage → Clear logs from /var/log → Remove unused Docker images/containers → Expand disk if required.

**Detailed interview approach:**
I confirm scope and preserve access before changing anything. For disk I check `df -hT`, `df -i`, `du -x`, and `lsof +L1`; for CPU I use `uptime`, `mpstat`, `pidstat`, `top`, and compare the PID with logs, traffic, and recent changes.

I distinguish capacity from leaks, open-deleted files, unrotated logs, I/O wait, or a hot application thread. I mitigate with the smallest safe action—traffic reduction, graceful service handling, approved cleanup/rotation, or capacity—after collecting evidence.

I verify application health and resource trends and then add retention, limits, alerts, or a code/configuration fix rather than scheduling blind restarts or deletions.

## 3. How do you troubleshoot high CPU usage on a Linux server?

**Answer:** Use top, htop, vmstat, and iostat → Identify process → Kill/fix process → Scale infra if required.

**Detailed interview approach:**
I confirm scope and preserve access before changing anything. For disk I check `df -hT`, `df -i`, `du -x`, and `lsof +L1`; for CPU I use `uptime`, `mpstat`, `pidstat`, `top`, and compare the PID with logs, traffic, and recent changes.

I distinguish capacity from leaks, open-deleted files, unrotated logs, I/O wait, or a hot application thread. I mitigate with the smallest safe action—traffic reduction, graceful service handling, approved cleanup/rotation, or capacity—after collecting evidence.

I verify application health and resource trends and then add retention, limits, alerts, or a code/configuration fix rather than scheduling blind restarts or deletions.

