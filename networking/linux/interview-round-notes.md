# Linux Networking Interview Notes

### 1.9 Investigate intermittent packet loss between containers / nodes

1. Measure it: `ping`, `mtr <target>` (shows exactly where the loss starts, hop by hop), and `iperf3` for throughput.
2. Check interface errors and drops: `ip -s link`, `ethtool -S eth0`, `netstat -s` (retransmits, drops).
3. Check for conntrack exhaustion — this is very common on busy nodes. Look at `sysctl net.netfilter.nf_conntrack_count` / `_max`, and check `dmesg` for "nf_conntrack: table full".
4. Check the CNI and overlay network. A MTU mismatch on overlay networks (VXLAN adds about 50 bytes) causes fragmentation and drops, so verify the pod MTU. Also inspect the CNI plugin (Calico, Cilium, or Flannel) and its `iptables`/`ipvs` rules.
5. Check DNS. Intermittent DNS failures often look like packet loss — check CoreDNS, the classic conntrack race on musl/Alpine, and `ndots`.
6. Check the node, NIC, and upstream network: cloud provider network health, security groups/NACLs, and whether the physical NIC is close to saturated.
