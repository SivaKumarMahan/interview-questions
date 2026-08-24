# Linux Networking Interview Questions

### 1. How do you check if a port is open or listening?

**Answer:**

On the server I run `sudo ss -lntp '( sport = :443 )'` to see the listening address, port, PID, and process. `127.0.0.1:443` only accepts local traffic, while `0.0.0.0:443` listens on every IPv4 interface, subject to the firewall.

Then I test each layer separately: `nc -vz host 443` from the real client network to check the TCP connection, `curl -vk https://host/health` to check the application itself, and `nft list ruleset` or the cloud security group to check filtering.

A listening socket doesn't prove the application is healthy, and a failed remote test doesn't prove the service is down — routing, ACLs, NAT, TLS, or the application itself could each be the cause.

---

### 2. You cannot SSH into a remote machine. How do you debug?

**Answer:**

I let the exact client error guide the next step. A timeout points to routing, a firewall, or a security group. "Connection refused" means nothing is listening. "Permission denied" means the connection reached SSH but authentication failed.

I run `ssh -vvv user@host`, check DNS resolves correctly, and test `nc -vz host 22` from the same network the client is on.

Using console or bastion access, I check `ss -lntp`, `systemctl status sshd`, `sshd -t`, the host firewall, disk space, and `/var/log/auth.log` or `/var/log/secure`. For key problems I check the intended user, the ownership of the home directory and `.ssh`, that `.ssh` is mode `700`, that `authorized_keys` is mode `600`, and the server's SSH configuration.

I make one controlled fix at a time and retest. I don't weaken authentication or open port 22 to the whole internet as a shortcut.

---

### 3. Ping works, but SSH fails using hostname. Why?

**Answer:**

Ping only proves an ICMP reply came back — it doesn't prove TCP port 22 or SSH authentication works. I compare `getent ahosts hostname` against the expected IP, test both `ssh -vvv user@hostname` and `ssh user@IP`, and check `nc -vz hostname 22`.

If the IP works but the hostname doesn't, the likely causes are a stale or wrong DNS record, IPv6 being picked when only IPv4 works, an SSH `Host` rule in `~/.ssh/config`, or a host-key mismatch after the address changed.

I fix the DNS or client config, and I verify the host key through a trusted source before updating `known_hosts`. I never just delete a host-key warning, since it can be a sign of a man-in-the-middle attack.

---

### 4. How do you check and configure a static IP address?

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

---

### 5. How do you troubleshoot an NFS mount issue?

**Answer:**

I treat discovery, mounting, and permissions as three separate things to check. From the client I verify DNS and routing and run `showmount -e server` where it's supported, then try a verbose temporary mount like `mount -v -t nfs -o vers=4 server:/export /mnt/test`.

I check `journalctl -k` and the client's NFS logs for timeout, access, or protocol errors.

On the server I check the NFS services, `/etc/exports`, `exportfs -v`, the firewall, and that the exported directory actually exists. If the mount works but access fails, I compare the numeric UID/GID on each side, root-squash behavior, ACLs, and SELinux.

I agree on the NFS version and safe timeout options, test reads and writes with the real service account, and only then make the entry in `/etc/fstab` or the automounter permanent.

---

### 6. A Linux server suddenly becomes unreachable. How do you troubleshoot it?

**Answer:**

First I pin down what "unreachable" actually means: monitoring lost contact, DNS is failing, ping fails, SSH times out, the connection is refused, or only the application is down. I check how much is affected and whether there was a recent network, firewall, DNS, OS, or cloud change, then use the provider's console or out-of-band access if I can't reach it normally.

From a known-good location I check DNS and the IP, the route, the TCP port, and the path using `dig`, `ip route get`, `nc -vz`, `traceroute`/`mtr`, and flow or firewall logs.

On the server itself I check the interface, link, address, and routes, `ss -lntup`, the firewall rules (nftables/iptables/firewalld), the SSH/service state, CPU and memory, disk and inodes, kernel logs, failed logins, and cloud security rules.

A failed ping alone doesn't prove anything, since ICMP is often blocked anyway.

I fix the narrow layer that's actually broken — a route, an address, a firewall rule, a service, capacity, or the host — using a safe rollback where possible.

Then I verify SSH and the real application work from the affected network, remove any temporary access I opened, confirm monitoring recovers, and prevent it happening again with redundant access paths, infrastructure-as-code review, configuration rollback, capacity alerts, and a tested console procedure.
