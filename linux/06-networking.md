# Linux: Networking

> Network interfaces, ports, connectivity troubleshooting, firewalls, time sync, and moving data between servers.

## Key Concepts

### Networking: How Your Services Talk

Services depend on the network to reach each other. When networking breaks, everything built on top of it breaks too.

#### Network interface management

```bash
# Modern way to check network setup
ip addr show              # Show all network interfaces
ip link show              # Show network devices

# The old way (still works)
ifconfig                  # Shows interface configuration
```

#### Port monitoring — the detective work

```bash
# Who's using what port?
netstat -tulpn            # Show all listening ports with processes
ss -tulpn                 # Modern replacement (faster)

# Specific port investigation
lsof -i :80               # What's using port 80?
lsof -i :3306             # Check if MySQL is running
```

#### Network troubleshooting arsenal

```bash
# Is the server reachable?
ping google.com           # Basic connectivity test
ping -c 4 server.com      # Send only 4 packets

# Trace the network path
traceroute google.com     # Show every router hop

# DNS investigation
dig google.com            # Detailed DNS lookup
nslookup google.com       # Simple DNS check
```

#### Firewall management

```bash
# Ubuntu/Debian firewall (UFW - User Friendly Firewall)
sudo ufw status           # Check firewall status
sudo ufw enable           # Turn on firewall
sudo ufw allow 22         # Allow SSH
sudo ufw allow 80/tcp     # Allow HTTP traffic
sudo ufw deny 8080        # Block specific port

# Traditional iptables (more complex but powerful)
sudo iptables -L          # List all rules
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT  # Allow HTTPS
```

## Interview Questions

### 1. How do you check if a port is open or listening?

**Answer:**

On the server I run `sudo ss -lntp '( sport = :443 )'` to see the listening address, port, PID, and process. `127.0.0.1:443` only accepts local traffic, while `0.0.0.0:443` listens on every IPv4 interface, subject to the firewall.

Then I test each layer separately: `nc -vz host 443` from the real client network to check the TCP connection, `curl -vk https://host/health` to check the application itself, and `nft list ruleset` or the cloud security group to check filtering.

A listening socket doesn't prove the application is healthy, and a failed remote test doesn't prove the service is down — routing, ACLs, NAT, TLS, or the application itself could each be the cause.

### 2. How do you find and stop a process listening on port 8080?

**Answer:**

```bash
sudo ss -ltnp '( sport = :8080 )'
sudo lsof -nP -iTCP:8080 -sTCP:LISTEN
sudo systemctl stop <service-name>
```

I identify which service owns the port before stopping it — killing a bare PID can just get it recreated by a supervisor, and can interrupt users unexpectedly. If no service unit owns it, I use `kill -TERM <pid>`, confirm the listener is actually gone, and only escalate to `KILL` if it doesn't respond.

I also check containers (`docker ps` or `crictl ps`) and firewall or proxy configuration, since a port being reachable doesn't prove the application behind it is healthy.

### 3. What is the fastest way to copy huge files across servers?

**Answer:**

The best method depends on the network, how much is changing, how many files there are, and whether any downtime is acceptable. For a large, resumable transfer I usually use:

```bash
rsync -aHAX --info=progress2 --partial source/ user@host:/data/destination/
```

Compression (`-z`) helps on a slower network if the data compresses well, but wastes CPU on data that's already compressed. I run an initial copy while the source is still live, then pause writes or take a snapshot, then run a final delta sync to catch up.

For cloud volumes, a snapshot, replication, or object storage might be faster and safer than a file copy. I estimate the bandwidth and disk space needed, protect any credentials involved, throttle the transfer if it would affect production, and verify file counts and checksums before cutting over.

### 4. How do you fix NTP time sync issues?

**Answer:**

I check `timedatectl`, `chronyc tracking`, and `chronyc sources -v` to see the offset, which source is selected, and whether sources are reachable. Then I confirm the time service is running, its configured sources actually resolve, and UDP port 123 is allowed through.

On virtual machines, I also check whether the hypervisor's own time sync is enabled and conflicting.

For a large offset, jumping the clock can break databases and authentication, so I follow the application's maintenance procedure. For a small offset, chrony should adjust it gradually and safely. After fixing `/etc/chrony.conf`, I reload or restart chronyd and confirm the offset is shrinking and a source is marked selected (`^*`).

I keep monitoring drift, and use multiple approved internal time sources so a single NTP server isn't a single point of failure.
### 5. How do you check and configure a static IP address?

**Answer:**

I first capture the current address, interface, gateway, routes, DNS, and whether NetworkManager or Netplan owns the config: `ip -br addr`, `ip route`, `resolvectl status`, and `nmcli connection show`. I confirm the new IP is reserved and not already in use.

With NetworkManager, for example:

```bash
sudo nmcli con mod "System eth0" ipv4.method manual \
  ipv4.addresses 10.0.1.20/24 ipv4.gateway 10.0.1.1 \
  ipv4.dns "10.0.0.10 10.0.0.11"
sudo nmcli con up "System eth0"
```

On a remote server I use console access or set up an automatic rollback, since a bad gateway can lock me out. Afterward I verify the address, route, DNS, gateway, and remote connectivity, and update the inventory or DNS documentation.

### 6. A Linux server suddenly becomes unreachable. How do you troubleshoot it?

**Answer:**

First I pin down what "unreachable" actually means: monitoring lost contact, DNS is failing, ping fails, SSH times out, the connection is refused, or only the application is down. I check how much is affected and whether there was a recent network, firewall, DNS, OS, or cloud change, then use the provider's console or out-of-band access if I can't reach it normally.

From a known-good location I check DNS and the IP, the route, the TCP port, and the path using `dig`, `ip route get`, `nc -vz`, `traceroute`/`mtr`, and flow or firewall logs.

On the server itself I check the interface, link, address, and routes, `ss -lntup`, the firewall rules (nftables/iptables/firewalld), the SSH/service state, CPU and memory, disk and inodes, kernel logs, failed logins, and cloud security rules.

A failed ping alone doesn't prove anything, since ICMP is often blocked anyway.

I fix the narrow layer that's actually broken — a route, an address, a firewall rule, a service, capacity, or the host — using a safe rollback where possible.

Then I verify SSH and the real application work from the affected network, remove any temporary access I opened, confirm monitoring recovers, and prevent it happening again with redundant access paths, infrastructure-as-code review, configuration rollback, capacity alerts, and a tested console procedure.

### 7. Investigate intermittent packet loss between containers / nodes *(asked in interview round)*

1. Measure it: `ping`, `mtr <target>` (shows exactly where the loss starts, hop by hop), and `iperf3` for throughput.
2. Check interface errors and drops: `ip -s link`, `ethtool -S eth0`, `netstat -s` (retransmits, drops).
3. Check for conntrack exhaustion — this is very common on busy nodes. Look at `sysctl net.netfilter.nf_conntrack_count` / `_max`, and check `dmesg` for "nf_conntrack: table full".
4. Check the CNI and overlay network. A MTU mismatch on overlay networks (VXLAN adds about 50 bytes) causes fragmentation and drops, so verify the pod MTU. Also inspect the CNI plugin (Calico, Cilium, or Flannel) and its `iptables`/`ipvs` rules.
5. Check DNS. Intermittent DNS failures often look like packet loss — check CoreDNS, the classic conntrack race on musl/Alpine, and `ndots`.
6. Check the node, NIC, and upstream network: cloud provider network health, security groups/NACLs, and whether the physical NIC is close to saturated.

### 8. How do you troubleshoot an NFS mount issue?

**Answer:**

I treat discovery, mounting, and permissions as three separate things to check. From the client I verify DNS and routing and run `showmount -e server` where it's supported, then try a verbose temporary mount like `mount -v -t nfs -o vers=4 server:/export /mnt/test`.

I check `journalctl -k` and the client's NFS logs for timeout, access, or protocol errors.

On the server I check the NFS services, `/etc/exports`, `exportfs -v`, the firewall, and that the exported directory actually exists. If the mount works but access fails, I compare the numeric UID/GID on each side, root-squash behavior, ACLs, and SELinux.

I agree on the NFS version and safe timeout options, test reads and writes with the real service account, and only then make the entry in `/etc/fstab` or the automounter permanent.
