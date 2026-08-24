# Linux Detailed Interview Notes

### Q: How do you attach and detach a file system in Linux?

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

---

## System Logging Notes

Log locations vary by Linux distribution and by which service manager it uses. With systemd, you query services and the kernel with `journalctl`. Older-style files usually live under `/var/log/`, such as `syslog`, `messages`, `auth.log`, or logs specific to an application.

`tail -n 4 /var/log/messages` prints the last four lines of that file, if it exists. For centralized logging, keep timestamps, host and service identity, and access controls intact, and let `logrotate` handle retention, compression, and safely rotating large files.

### Q: How do you print the last 15 lines of a file in Linux?

**Using the `tail` command**

The `tail` command prints the last part of a file.

```bash
tail -n <number_of_lines> <filename>
tail -n 15 /var/log/syslog
```

**Continuously monitor file updates (live view)**

```bash
tail -f filename.txt
```

If you want the last 15 lines of a command's output instead of a file:

```bash
dmesg | tail -n 15
```

---

### Q: How would you view the last few lines of a huge log file that's continuously updated?

"I'd use `tail -f logfile.log` to stream the last lines in real time."

---

### Q: You have hosted an application on a Linux server - how would you migrate it to a serverless architecture in azure?

To migrate an application from a Linux server to a serverless setup in Azure, I'd follow these steps:

1. **Assess the application.** Understand its architecture, dependencies, and components to see which parts can move to serverless.
2. **Choose the Azure services.** For example, `Azure Functions` for compute, `Azure Logic Apps` for workflows, and `Azure Blob Storage` for static content.
3. **Refactor the application.** Change the code to fit the serverless model, breaking it into smaller functions where needed.
4. **Set up the Azure environment.** Create the Function Apps, Storage Accounts, and any other resources you need.
5. **Deploy the application.** Use Azure DevOps or another CI/CD tool to deploy the refactored app.
6. **Test and optimize.** Test it thoroughly in the serverless environment and tune it for performance and cost.
7. **Monitor and maintain.** Set up `Azure Monitor` and `Application Insights` so you can see the application is running smoothly.

---

### Q: log file processing - using tools like grep to extract IP addresses and count occurrences?

**A:** You can combine `grep` with `awk`, `sort`, and `uniq` to pull IP addresses out of log files and count how often each one appears. Here's the approach step by step:

1. **Extract the IP addresses.**

   Use `grep` with a regular expression to find IP addresses in the log file.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log
   ```

   What each part does:

   - `grep`
   - `-E` turns on extended regex
   - `-o` prints only the matching text, not the whole line
   - `'([0-9]{1,3}\.){3}[0-9]{1,3}'` matches an IPv4 address (like `10.0.0.5`)

2. **Count how often each one appears.**

   Pipe the output through `sort` and `uniq` to count each unique IP.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log | sort | uniq -c | sort -nr
   ```

   - `sort` puts the IPs in order so identical lines sit next to each other
   - `uniq -c` counts how many times each unique IP shows up
   - `sort -nr` sorts those counts from highest to lowest

   This gives you a list of IP addresses with their occurrence counts, highest first.

3. **Save the results to a file.**

   You can redirect the output to a file for later analysis.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log | sort | uniq -c | sort -nr > ip_counts.txt
   ```

4. **If the IP is always the first field on the line:**

   You can simplify the extraction with `awk` instead.

   Example:

   ```bash
   awk '{print $1}' logfile.log | sort | uniq -c | sort -nr
   ```

---
