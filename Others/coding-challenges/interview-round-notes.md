# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Coding / Hands-on Challenges

### 11.1 Shell script: log rotation & system cleanup with error handling + notifications
Key elements to demonstrate:
```bash
#!/usr/bin/env bash
set -euo pipefail                      # fail fast, catch undefined vars, pipe failures
LOG_DIR="/var/log/myapp"; RETENTION_DAYS=14; SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

notify() { [[ -n "$SLACK_WEBHOOK" ]] && curl -sf -X POST -d "{\"text\":\"$1\"}" "$SLACK_WEBHOOK" || true; }
trap 'notify "❌ log-cleanup failed at line $LINENO"' ERR

# rotate + compress logs older than 1 day
find "$LOG_DIR" -type f -name '*.log' -mtime +1 -exec gzip {} \;
# delete archives older than retention
deleted=$(find "$LOG_DIR" -type f -name '*.gz' -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
# clean tmp + old cache
find /tmp -type f -atime +7 -delete
notify "✅ log-cleanup done: removed $deleted old archives, disk now $(df -h / | awk 'NR==2{print $5}')"
```
Talk about: `set -euo pipefail`, `trap ... ERR` for error handling, idempotency, using `logrotate` in real setups, and Slack/email notification. Mention scheduling via cron/systemd timer.

### 11.2 Python: parse & analyze AWS CloudWatch metrics with visualization
Key elements:
```python
import boto3, datetime as dt
import matplotlib.pyplot as plt

cw = boto3.client("cloudwatch")
resp = cw.get_metric_statistics(
    Namespace="AWS/EC2", MetricName="CPUUtilization",
    Dimensions=[{"Name": "InstanceId", "Value": "i-0abc123"}],
    StartTime=dt.datetime.utcnow() - dt.timedelta(hours=24),
    EndTime=dt.datetime.utcnow(),
    Period=300, Statistics=["Average", "Maximum"],
)
points = sorted(resp["Datapoints"], key=lambda d: d["Timestamp"])
times = [p["Timestamp"] for p in points]
avg   = [p["Average"] for p in points]

plt.plot(times, avg, label="Avg CPU %")
plt.xlabel("Time"); plt.ylabel("CPU %"); plt.legend(); plt.title("EC2 CPU (24h)")
plt.tight_layout(); plt.savefig("cpu.png")
```
Discuss: boto3 client + credentials (IAM role/OIDC), pagination for large ranges, pandas for analysis (rolling averages, anomaly detection), matplotlib/plotly for viz, and error handling.

### 11.3 Explain list comprehensions in Python & optimize a snippet
- **List comprehension** = concise, faster way to build a list: `[f(x) for x in it if cond]`. It's faster than an equivalent `for`-loop with `.append()` because iteration/append happen in C. Variants: set `{}`, dict `{k:v}`, and **generator** `( … )` (lazy, memory-efficient for large/streamed data).
- **Optimization example:**
  ```python
  # slower
  result = []
  for x in range(1000000):
      if x % 2 == 0:
          result.append(x * x)
  # faster (comprehension)
  result = [x * x for x in range(1000000) if x % 2 == 0]
  # best if you only iterate once (no full list in memory)
  result = (x * x for x in range(1000000) if x % 2 == 0)
  ```
- Other tips: use generators for large data, `sum()`/`any()`/`map` built-ins, avoid repeated attribute lookups in loops, and profile before optimizing.

### 11.4 Terraform multi-tier module (coding round)
See **§6.6** — same question; cover module structure, remote state + locking, layered state, tiered networking, inputs/outputs, and scanning.

---
