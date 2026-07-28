# Linux Networking Interview Notes

### 1.9 Investigate intermittent packet loss between containers / nodes

1. **Measure:** `ping`, `mtr <target>` (shows where loss starts hop-by-hop), `iperf3` for throughput.
2. **Interface errors/drops:** `ip -s link`, `ethtool -S eth0`, `netstat -s` (retransmits, drops).
3. **Conntrack exhaustion** (very common on busy nodes): `sysctl net.netfilter.nf_conntrack_count / _max`, check `dmesg` for "nf_conntrack: table full".
4. **CNI / overlay:** MTU mismatch on overlay networks (VXLAN adds ~50 bytes) causes fragmentation/drops — verify pod MTU. Inspect the CNI (Calico/Cilium/Flannel) and `iptables`/`ipvs` rules.
5. **DNS:** intermittent failures often masquerade as packet loss — check CoreDNS, the classic conntrack race on musl/Alpine, `ndots`.
6. **Node/NIC & upstream:** check cloud provider network health, security groups/NACLs, and physical NIC saturation (how close a resource is to its limit).
