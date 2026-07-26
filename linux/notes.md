# Linux Detailed Interview Notes

### Q: How do you attach and detach a file system in Linux?

"In Linux, we attach a file system by mounting it with the `mount` command — for example, `mount /dev/sdb1 /mnt/data`. To detach it, we use `umount /mnt/data`. For persistent mounting, we configure it in `/etc/fstab`. I also check usage with `df -h` and handle busy mounts using `lsof` or `fuser`."

When you "attach" a file system in Linux, you're **mounting** it — linking the file system (from a device, partition, or volume) into your system's directory tree.

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

Now your file system is attached — you can access files under `/mnt/mydata`.

When you "detach" a file system, you're **unmounting** it — safely removing access to that device.

```bash
sudo umount /mnt/mydata
```

If the file system is busy (e.g., some process is using it), you'll get an error like:

```
umount: /mnt/mydata: target is busy
```

You can check which process is using it:

```bash
sudo lsof +f -- /mnt/mydata
# or
sudo fuser -vm /mnt/mydata
```

Then stop/kill the process and try again.

---

## System Logging Notes

Linux log locations vary by distribution and service manager. With systemd, query services and the kernel with `journalctl`; traditional files may be under `/var/log/` such as `syslog`, `messages`, `auth.log` or application-specific logs. `tail -n 4 /var/log/messages` prints the last four lines where that file exists. Centralized logging should preserve timestamps, host/service identity and access controls, and `logrotate` should manage retention, compression and safe rotation of large files.

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

If you want to view the last 15 lines of a command's output:

```bash
dmesg | tail -n 15
```

---

### Q: How would you view the last few lines of a huge log file that's continuously updated?

"I'd use `tail -f logfile.log` to stream the last lines in real-time."

---

### Q: You have hosted an application on a Linux server - how would you migrate it to a serverless architecture in azure?

To migrate an application from a Linux server to a serverless architecture, I would follow these steps:

1. **Assess the Application:** Understand the application architecture, dependencies, and components to identify which parts can be migrated to serverless services.
2. **Choose Azure Serverless Services:** Identify suitable Azure services such as `Azure Functions` for compute, `Azure Logic Apps` for workflows, and `Azure Blob Storage` for static content.
3. **Refactor the Application:** Modify the application code to fit the serverless model, breaking it into smaller functions or services as needed.
4. **Set Up Azure Environment:** Create necessary resources in Azure, including Function Apps, Storage Accounts, and any other required services.
5. **Deploy the Application:** Use Azure DevOps or other CI/CD tools to deploy the refactored application to Azure.
6. **Test and Optimize:** Thoroughly test the application in the serverless environment and optimize for performance and cost.
7. **Monitor and Maintain:** Set up monitoring using `Azure Monitor` and `Application Insights` to ensure the application runs smoothly.

---

### Q: log file processing - using tools like grep to extract IP addresses and count occurrences?

**A:** You can use `grep` along with other command-line tools like `awk`, `sort`, and `uniq` to extract IP addresses from log files and count their occurrences. Here's a step-by-step approach:

1. **Extract IP Addresses:**

   Use `grep` with a regular expression to find IP addresses in the log file.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log
   ```

   Explanation:

   - `grep`
   - `-E` → enables extended regex
   - `-o` → prints only the matching IPs
   - `'([0-9]{1,3}\.){3}[0-9]{1,3}'` → matches IPv4 format (e.g., `10.0.0.5`)

2. **Count Occurrences:**

   Pipe the output to `sort` and `uniq` to count how many times each IP address appears.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log | sort | uniq -c | sort -nr
   ```

   - `sort` → sorts the IPs
   - `uniq -c` → counts occurrences of each unique IP
   - `sort -nr` → sorts the counts in descending order

   This command will give you a list of IP addresses along with their occurrence counts, sorted in descending order.

3. **Save Results to a File:**

   You can redirect the output to a file for further analysis.

   Example:

   ```bash
   grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' logfile.log | sort | uniq -c | sort -nr > ip_counts.txt
   ```

4. **If you know the IP is always the first field:**

   You can simplify the extraction using `awk`.

   Example:

   ```bash
   awk '{print $1}' logfile.log | sort | uniq -c | sort -nr
   ```

---
