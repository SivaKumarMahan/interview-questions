# Linux: Disk, Storage, and Filesystems

> Disk and inode usage, full-disk incidents, partitions, mounting, swap, LVM growth, fsck, and file recovery.

## Key Concepts

### File System Usage: Avoiding the Disk Space Disaster

Monitoring disk usage prevents most storage-related incidents.

#### Disk space monitoring

```bash
# Check available space
df -h                     # Human-readable disk usage
df -i                     # Check inode usage (can run out even with space)

# Find what's eating your disk
du -h /var/log            # Directory size
du -sh *                  # Size of each item in current directory
du -h --max-depth=1 /     # Top-level directory sizes
```

#### Finding space hogs

```bash
# Find large files
find / -size +100M -type f 2>/dev/null    # Files larger than 100MB
find /var/log -name "*.log" -size +50M    # Large log files

# Find old files (potential cleanup candidates)
find /tmp -type f -mtime +30              # Files older than 30 days
```

## Interview Questions

### 1. How do you check disk usage?

**Answer:**

`df -hT` shows how full each filesystem is; `df -i` shows inode usage instead of space. Once I know which filesystem is affected, I dig in with `du -xhd1 /path | sort -h` and keep drilling down from there. `find` can list the biggest files, and `lsof +L1` finds files that were deleted but are still open, which `du` won't show.

I compare what `df` and `du` report, and check mount points, reserved blocks, sparse files, and container or log paths.

I never delete files I don't recognize, or system or database files. Instead I stop whatever is generating the growth, rotate or archive the data that's safe to remove, or add storage, then confirm the service can still write, and add alerts based on retention and capacity forecasts.

### 2. How do you check disk partitions and usage?

**Answer:**

I use a different command for each layer: `lsblk -f` shows disks, partitions, filesystems, UUIDs, and mount points. `df -hT` shows how full each mounted filesystem is. `findmnt` shows how things are mounted and with what options. `blkid` confirms filesystem identifiers. `fdisk -l` or `parted -l` shows the partition table.

For LVM, I also run `pvs`, `vgs`, and `lvs -a -o +devices` to see how physical volumes map to volume groups and logical volumes. Before changing anything, I write down this mapping and confirm the exact device by size, serial number, and path.

Cloud disk size, partition size, LVM size, filesystem size, and actual mounted capacity are all separate layers, and growing one doesn't automatically grow the others.

### 3. What happens when `/` is 100% full?

**Answer:**

When root fills up, applications can't write logs, PID files, temp files, package databases, uploads, or database transactions. Services can crash or fail to start, and even logging in can fail if PAM or the shell can't write what it needs.

Running out of inodes causes the exact same symptom even when `df -h` shows free space, so I check both `df -hT` and `df -i`.

I make sure I can still get in, find the filesystem that's growing and the safest large files to deal with, and cut down on writes where I can. I rotate or archive known logs, clear approved caches or temp data, or add storage — I never blindly delete things under `/var/lib`.

Once it's recovered, I restart only the services that were actually affected, check filesystem and application integrity, confirm monitoring is working, and fix retention or capacity so it can't silently happen again.

### 4. The `/` partition is full. How do you find and delete large files safely?

**Answer:**

I confirm the filesystem with `df -hT /` and inodes with `df -i /`, then stay on that same filesystem while I look for usage:

```bash
sudo du -xhd1 / 2>/dev/null | sort -h
sudo find / -xdev -type f -size +500M -printf '%s %p\n' 2>/dev/null | sort -nr | head
```

Before deleting anything, I check who owns it, when it was last modified, whether anything has it open, retention rules, and whether a mount is hiding data underneath it. Logs should normally go through `logrotate` or get safely reopened by the service, and application or database files need to follow the owner's own procedure.

I make the smallest cleanup that actually recovers space, confirm `df`, service health, and logs afterward, then set up rotation, quotas, alerts, or an expansion. I also check `lsof +L1` if `du` can't explain what `df` is reporting.

### 5. A disk is 95% full. How do you find what is consuming space?

**Answer:**

I first identify the full filesystem with `df -hT`, then look only at that mount so another filesystem doesn't skew the result:

```bash
sudo du -xhd1 /var | sort -h
sudo find /var -xdev -type f -size +500M -printf '%s %p\n' | sort -nr | head
sudo lsof +L1
```

The last command finds deleted-but-open files, a common reason `du` and `df` disagree. I check logs, package caches, container images and volumes, temp files, snapshots, and inode usage (`df -i`).

I preserve the evidence and apply retention, rotation, resizing, or a controlled cleanup — I don't delete unknown production data just to make an alert go away.

### 6. How do you handle a disk full issue in Linux? *(scenario)*

**Answer:** Run `df -h` to check usage, clear logs from `/var/log`, remove unused Docker images and containers, and expand the disk if needed.

**Detailed interview approach:**
Same investigation pattern as above: confirm scope, preserve access, then check `df -hT`, `df -i`, `du -x`, and `lsof +L1` to see exactly where the space went.

I separate a genuine capacity problem from a leak, an open-deleted file, unrotated logs, or heavy I/O, and I mitigate with the smallest safe step — cutting traffic, a graceful service restart, an approved cleanup, or adding capacity — only after I've collected the evidence.

Afterward I check application health and the resource trend, then put in retention, limits, and alerts rather than relying on manual restarts or deletions going forward.

### 7. How do you troubleshoot high disk usage in Linux servers used for CI/CD? *(scenario)*

**Answer:** Run `du -sh /*` to find the big directories, clear `/var/log`, remove old Docker images, and archive old build artifacts.

**Detailed interview approach:**
I start by confirming the scope of the problem and making sure I still have access before I change anything. For disk usage I check `df -hT`, `df -i`, `du -x`, and `lsof +L1` to see whether space or inodes are the issue and whether a deleted file is still held open.

Then I work out what's actually happening: is it real growth, a leak, an open-but-deleted file, unrotated logs, or just heavy I/O? I fix it with the smallest safe action first — reducing traffic, letting a service shut down cleanly, running an approved cleanup or rotation, or adding capacity — and I only act after I've gathered evidence.

Once things are stable, I check that the application is healthy and look at the resource trend over time. Then I add retention rules, limits, and alerts, or fix the underlying code or config, instead of just scheduling blind restarts or deletions.

### 8. How do you find large unused files across multiple partitions?

**Answer:**

I first list the mounted filesystems with `df -hT`, then search each relevant one separately. For example:

```bash
sudo find /data -xdev -type f -size +1G -mtime +30 \
  -printf '%s %u %TY-%Tm-%Td %p\n' | sort -nr | head -50
```

This finds files bigger than 1 GB that haven't been touched in over 30 days. Modification time alone doesn't prove a file is unused, so I also check access patterns, whether anything has it open with `lsof`, who owns it, retention rules, and who's responsible for it.

I archive or move a small, approved batch first, confirm the service is fine, and only then delete anything. If this keeps happening, I set up retention or log rotation instead of doing manual cleanup over and over.

### 9. How do you list the top 10 largest files anywhere on a Linux system?

**Answer:**

For a quick, system-wide look I can use:

```bash
sudo find / -type f -exec du -h -- {} + 2>/dev/null | sort -hr | head -n 10
```

`find / -type f` walks files starting from root, `du -h` reports how much disk space each one actually uses in human-readable units, `sort -hr` puts the biggest first, and `head -n 10` keeps the top ten.

Redirecting stderr hides permission errors and noise from `/proc`, but during a formal investigation I might want to see those errors, since a path I couldn't read means the search wasn't actually complete.

Scanning all of `/` can be slow and can wander into NFS, container, backup, or other mounted filesystems. I usually start with `df -hT` to find the full filesystem, and search just that mount with `-xdev`, for example:

```bash
sudo find /var -xdev -type f -exec du -h -- {} + 2>/dev/null \
  | sort -hr | head -n 10
```

For the exact logical size with GNU tools, I can use `find ... -printf '%s\t%p\n' | sort -nr`; `du` instead reports allocated blocks, so sparse files can show a different number. Filenames containing newlines need a null-delimited or scripted approach instead.

Once I find a large file, I check it with `stat`, `file`, and `lsof`, and confirm the owner and retention policy. I don't delete it just because it's big.

### 10. Deleted large files but disk space is not freeing up. Why?

**Answer:**

Linux removes the filename right away, but the actual data blocks stay allocated as long as any process still has the file open. I confirm this with:

```bash
sudo lsof +L1
```

The output shows the process, PID, file descriptor, and how much space it's holding onto. The safest fix is to reload or restart that service so it closes and reopens the file — for some daemons, a documented signal like `SIGHUP` is enough.

In an emergency, truncating through `/proc/<pid>/fd/<fd>` is possible but risky, and I'd only do it following an approved procedure. I confirm the space is freed with `df`, then fix the rotation setup so it properly signals the service next time.

### 11. What happens when a file is deleted but still open by a process?

**Answer:**

`unlink()` removes the directory entry, so new commands can't find the file by name anymore, but the inode and its data blocks stay around until the last open file descriptor closes. The process that has it open can keep reading or writing that data, and `df` still counts it as used space even though `du` can't see it.

I demonstrate or diagnose this with `lsof +L1` and by checking `/proc/<pid>/fd/<number>`, which usually shows `(deleted)`. To free it, I get the application to close the descriptor — normally through a graceful reload or restart.

This is also why replacing a deployed binary on disk doesn't automatically change the code a running process already has loaded in memory.

### 12. Why do `df -h` and `du -sh` show different usage?

**Answer:**

`df` reads the filesystem's own allocation metadata, while `du` walks the visible directory tree and adds up what it finds. The most common cause of a big difference is a deleted-but-open file, which I check with `lsof +L1`.

Other causes: reserved blocks or metadata overhead, files hidden underneath a mount point, not having permission to see everything during the `du` scan, snapshots, or comparing two different filesystems by mistake.

I make sure both commands are looking at the same mount (`findmnt` and `du -x`), run `du` with enough permission, check for open-deleted files and snapshots, and check mount points. Sparse files can go the other way — `ls -l` can show a large size while the file actually takes up little space — and `du --apparent-size` explains that.

I fix whatever the actual cause turns out to be, rather than trusting either number blindly.

### 13. What is inode exhaustion and how do you resolve it?

**Answer:**

Every file and directory needs an inode.

A filesystem full of millions of tiny files can hit 100% inode usage while plenty of data blocks are still free — a new file then fails with "No space left on device." I check `df -i` and narrow down which directories have the most files, for example with `find /var -xdev -type f -printf '%h\n' | sort | uniq -c | sort -nr | head`.

I figure out what actually created all those files — sessions, a mail queue, a cache, container layers, or unrotated temp data — and clean it up using that system's own supported method.

For a lasting fix, I might move the workload, redesign how storage or objects are used, or rebuild the filesystem with an inode density suited to the workload — inode count generally can't be increased in place on ext filesystems.

I add monitoring for file count as well as bytes used.

### 14. The server has high load and an application reports "disk full", but `df -h` shows free space. What do you check?

**Answer:**

I check for inode exhaustion with `df -i`, since millions of small files can use up every inode while data blocks are still free.

I also check the actual mount namespace (`findmnt`, or the container's own namespace), quotas, a separate filesystem like `/tmp` that might be full on its own, filesystem errors or remount-read-only messages in `dmesg`, and deleted-but-open files with `lsof +L1`.

High load can also just be I/O wait from a storage problem rather than actual CPU work, so I check `iostat`, `vmstat`, latency and error metrics, and kernel logs. I fix the specific constraint I find, confirm the application can write again and what actually caused it, then set alerts for both bytes and inode usage.

### 15. How do you extend a partition without unmounting it?

**Answer:**

I first confirm the layout and filesystem with `lsblk -f`, `findmnt`, and the LVM commands, take a backup or snapshot, and check that the filesystem actually supports growing while mounted. After the underlying cloud or virtual disk is expanded, a plain partition can sometimes be grown with `growpart /dev/sda 2`.

For LVM, a typical controlled flow is:

```bash
sudo pvresize /dev/sda2
sudo lvextend -L +10G /dev/vg0/data
sudo xfs_growfs /data              # XFS, use mount point
# or: sudo resize2fs /dev/vg0/data # ext4
```

The exact device names vary every time, so I never just paste commands without checking them against the real layout. I verify each layer afterward with `pvs`/`lvs`, `lsblk`, and `df -hT`. Shrinking is a very different, riskier operation, and XFS can't be shrunk in place at all.

### 16. What steps are needed to add a new disk to a Linux server?

**Answer:**

Once the platform attaches the disk, I identify it by serial number and size with `lsblk -o NAME,SIZE,TYPE,SERIAL,MOUNTPOINTS` — I never just assume it's `/dev/sdb`. I confirm it has no data on it that matters, create a GPT partition if needed, then set up the approved filesystem or add it to LVM.

I create the mount point, mount it temporarily, set ownership, and test that I can read and write to it. For it to survive a reboot, I use the filesystem's UUID from `blkid` in `/etc/fstab` rather than a device name that could change.

I validate with `findmnt --verify` and `mount -a` before actually rebooting, then confirm capacity and permissions. I also update backups, monitoring, and application configuration to cover the new location.

### 17. How do you mount and unmount filesystems in Linux?

**Answer:**

I create an empty mount point and mount it using the UUID with an explicit filesystem type and options, for example `mount -t xfs UUID=<uuid> /data`. I confirm with `findmnt /data`, test permissions, and only add a reviewed entry to `/etc/fstab` once the temporary mount is working.

`findmnt --verify` and `mount -a` catch fstab syntax errors before they cause problems at the next reboot.

Before running `umount /data`, I stop or redirect whatever applications are using it, and check `lsof +f -- /data` or `fuser -vm /data` if it says it's busy. I avoid lazy or forced unmounts unless I fully understand the risk of data loss or stale file handles.

After unmounting, I confirm it's gone from `findmnt` — writing beneath a mount point that isn't actually mounted, or leaving a stray mount point, can quietly fill up the root filesystem.

### 18. How do you attach and detach a file system in Linux?

"In Linux, we attach a file system by mounting it with the `mount` command — for example, `mount /dev/sdb1 /mnt/data`. To detach it, we use `umount /mnt/data`.

For a mount that should survive a reboot, we set it up in `/etc/fstab`. I also check usage with `df -h` and handle busy mounts using `lsof` or `fuser`."

When you "attach" a file system in Linux, you're mounting it — linking a device, partition, or volume into your system's directory tree.

```bash
# 1. Create a directory (mount point)
sudo mkdir /mnt/mydata

# 2. Identify your storage device
sudo fdisk -l    # lists available disks and partitions
# Example device: /dev/sdb1

# 3. Mount it to the directory
sudo mount /dev/sdb1 /mnt/mydata

# 4. Verify
df -h | grep mydata
```

Now the file system is attached, and you can access files under `/mnt/mydata`.

When you "detach" a file system, you're unmounting it — safely removing access to that device.

```bash
sudo umount /mnt/mydata
```

If the file system is busy, for example because a process is using it, you'll get an error like:

```
umount: /mnt/mydata: target is busy
```

You can check which process is using it:

```bash
sudo lsof +f -- /mnt/mydata
# or
sudo fuser -vm /mnt/mydata
```

Then stop or kill that process and try again.

### 19. How do you remount a filesystem read-write without rebooting?

**Answer:**

If it was mounted read-only on purpose and the filesystem is healthy, I use `sudo mount -o remount,rw /mountpoint` and confirm with `findmnt -no OPTIONS /mountpoint`. If this needs to survive a reboot, I update `/etc/fstab` too.

But if the kernel remounted it read-only itself because of I/O or filesystem errors, forcing it back to read-write can make corruption worse. In that case I first check `journalctl -k`, storage or cloud health, and SMART data.

I fail over or stop writes, back up whatever is still readable, unmount or boot into rescue mode, run the proper filesystem repair tool, and only remount once the underlying storage problem is actually fixed.

### 20. How do you create and mount a swap file?

**Answer:**

I first check `free -h`, `swapon --show`, how much disk space is available, and whether the workload or platform even supports a swap file. Then:

Example:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

I confirm it with `swapon --show` and `free -h`, then add `/swapfile none swap sw 0 0` to `/etc/fstab`. Mode `600` matters here, because swap can contain sensitive data that was in memory.

Swap can prevent a sudden OOM kill for some workloads, but it's much slower than RAM and isn't a substitute for fixing a memory leak or sizing memory correctly. I also pick and document an appropriate `vm.swappiness` value rather than changing it without evidence.

### 21. How do you fix a corrupted filesystem using `fsck`?

**Answer:**

I confirm the exact device and filesystem type with `lsblk -f` and protect the data first. `fsck` is really a front end mainly for ext-family filesystems; XFS uses `xfs_repair` instead, and the filesystem normally needs to be unmounted first.

For the root filesystem, I boot into rescue or emergency mode, or attach the disk to a separate recovery host.

For ext4, I might first run a read-only check with `e2fsck -fn /dev/mapper/vg-lv`, review what it finds, then run the actual repair while it's unmounted. I avoid the automatic `-y` flag on valuable data unless the recovery plan is fine with that risk.

Afterward I mount it read-only first if that makes sense, check `lost+found`, validate the application's data, and look into whatever underlying disk, power, or kernel issue caused the corruption in the first place, rather than treating it as a one-off event.

### 22. A Linux server is not booting due to filesystem corruption. How do you recover it?

**Answer:**

I use console access to capture the exact boot error and tell the difference between real filesystem corruption and a bad `/etc/fstab` entry, a missing device, or a bootloader problem. I boot into recovery or rescue media, or attach the root disk to a helper host, map any encrypted or LVM volumes, and take a snapshot before doing any repair.

With the affected filesystems unmounted, I run the right checker — `e2fsck` for ext, `xfs_repair` for XFS — review the UUIDs and options in `/etc/fstab`, and check disk or platform health. I mount it read-only and check the critical files before bringing it back into service.

I only rebuild initramfs or the bootloader if the evidence points there, reboot through console, verify all mounts and services and application consistency, and restore from backup if the repair can't guarantee the data is intact.

### 23. How do you recover a deleted file in Linux?

**Answer:**

I stop or reduce writes right away, since new data can overwrite the blocks the deleted file used. My order of options is: the application's own recycle bin or version history, backups, a storage or LVM snapshot, a replica, and then an open file descriptor (`lsof +L1`) that might still let me copy from `/proc/<pid>/fd/<fd>` to another filesystem.

If none of that works, I unmount or snapshot the filesystem and do any forensic recovery on a copy, using filesystem-specific tools. Recovery isn't guaranteed, especially on SSDs with TRIM enabled, so I set that expectation up front and preserve the evidence.

Once I have a recovered file, I check it with a checksum or against the application, restore the correct owner and permissions, document the incident, and push for better tested backups and deletion controls.
