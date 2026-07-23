# Host Monitoring Summary

**Host monitoring** covers CPU and load, memory/swap, disk capacity/inodes/I/O, network errors and connections, process/service health, filesystem growth, certificate/time health and operating-system logs. `node-exporter` commonly exposes Linux metrics to Prometheus; Windows exporter provides Windows counters. Cloud agents and commercial platforms are alternatives.

Dashboards distinguish resource demand from customer impact:

- **High CPU** investigation compares user/system/steal/I/O wait and responsible processes.
- **Memory** investigation checks working set, cache, swap, OOM and growth.
- **Disk** investigation separates capacity, inode and latency problems.

Service monitoring verifies process, listening port, dependencies and a real health transaction rather than automatically restarting forever.

Centralize Linux journal/application logs and Windows Event channels with synchronized clocks, access controls and retention. Alert on sustained/actionable conditions and forecasted exhaustion. After remediation, confirm application latency/errors as well as host metrics.
