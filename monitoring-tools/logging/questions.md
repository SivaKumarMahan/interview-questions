## 1. How do ELK/OpenSearch and Loki differ?

**Answer:**

An ELK-style setup sends parsed log records through Logstash or Fluent Bit into Elasticsearch or OpenSearch, with Kibana on top. It gives rich full-text and field search, but it takes real effort to manage indices, shards, and lifecycle policies well.

Loki takes a different approach: it indexes only the labels attached to a log stream and stores the actual log lines as compressed chunks. When labels are kept small and controlled, this usually costs less to index. Grafana is the usual way to query it.

Which one I pick depends on the kind of search needed, log volume, retention requirements, how much operational effort the team can spend, tenant and security requirements, and cost.

## 2. How do you handle a sudden log explosion?

**Answer:**

First I find the cause: which service, version, logger, and event pattern is driving the growth. Then I check collector queues, dropped events, backend storage, and ingestion limits, because the real risk is the logging platform itself falling over and taking other services' visibility down with it.

If I need to act fast, I reduce debug verbosity or sample a known repetitive event, but only through a reviewed configuration change, and only after making sure I'm not throwing away anything needed for security or audit purposes. I never just delete logs to make the problem go away.

Once things are stable, I fix the root cause: rate and size limits, structured log levels, buffering with backpressure, and tiered retention. I add alerts on log volume, queue age, dropped records, and forecasted capacity, and I confirm the logs actually needed for troubleshooting and compliance are still available.

## 3. What information should structured logs contain?

**Answer:**

A structured log line should carry a timestamp, severity, event name, service, environment, version, instance or Pod, and a trace or correlation ID, plus whatever limited business or error fields are relevant. It should never contain passwords, tokens, private keys, or unnecessary personal data.

Clock synchronization and the W3C trace context standard are what actually let you correlate these across services. Request IDs belong in logs and traces, not as metric labels — a unique value per request would blow up a metrics system.

## 4. How do you find the ten largest files under `/var/log`?

**Answer:**

First I check which filesystem `/var/log` lives on with `df -hT /var/log`. Then I run a read-only search:

```bash
sudo find /var/log -xdev -type f -exec du -h -- {} + 2>/dev/null \
  | sort -hr | head -n 10
```

`-xdev` stops the search from wandering onto another mounted filesystem by accident. I use `du` because it reports actual disk space used, which is what matters during a capacity incident. If I need the logical byte size instead, GNU `find` can print it directly:

```bash
sudo find /var/log -xdev -type f -printf '%s\t%p\n' 2>/dev/null \
  | sort -nr | head -n 10
```

I compare the `df` and `du` numbers, and I also run `sudo lsof +L1`. A deleted log file that a process still has open keeps using disk space even though `find` can no longer see it. I identify the process writing to it with `lsof` or `fuser`, check its logging configuration, and preserve anything needed for an incident or audit.

The real fix is almost always the log level, rotation, compression, or retention settings — not deleting the largest file and hoping it doesn't come back.

## 5. How do you find all `.log` files larger than 100 MB?

**Answer:**

For `/var/log` specifically:

```bash
sudo find /var/log -xdev -type f -name '*.log' -size +100M -print
```

`-type f` skips directories and devices. `-name '*.log'` matches the suffix case-sensitively — I'd use `-iname` if uppercase extensions matter. `-size +100M` means larger than 100 units of 1,048,576 bytes. To get more detail:

```bash
sudo find /var/log -xdev -type f -name '*.log' -size +100M \
  -printf '%s bytes\t%u:%g\t%TY-%Tm-%Td %TH:%TM\t%p\n' | sort -nr
```

This pattern won't catch rotated files like `app.log.1` or `app.log.2.gz`, so I widen it when I need to see total retention. A large active log file can also be completely normal — I check its growth rate, what's writing to it, its log level, its rotation policy, and how much disk time is left before I touch anything.

## 6. How do you delete `.log` files older than 30 days safely?

**Answer:**

I never start with deletion. First I preview exactly what would match:

```bash
sudo find /var/log -xdev -type f -name '*.log' -mtime +30 -print
```

I confirm the application owner is fine with it, check compliance and incident-retention requirements, make sure a backup or central log copy exists, and check with `lsof` whether any matched file is still open. `-mtime +30` is based on file modification time in full 24-hour periods — it has nothing to do with timestamps written inside the log content, and it won't match common rotated names like `.log.1` or `.gz` unless I explicitly include them.

The real long-term fix is the service's own retention setting, `logrotate`, or journald configuration. I test a logrotate config safely first:

```bash
sudo logrotate -d /etc/logrotate.conf
```

Only after review and approval would I run the same expression with deletion:

```bash
sudo find /var/log -xdev -type f -name '*.log' -mtime +30 -delete
```

I avoid deleting the log a process is actively writing to, since it can keep writing to the old file handle without freeing any disk space. Afterward I check `df -hT`, confirm the service is still logging, confirm rotation works, confirm central logs are still searchable, and make sure alerts and retention policy prevent this from happening again.

## 7. Prometheus versus Splunk, and what is an SPL search?

**Answer:**

Prometheus stores numeric time-series metrics and runs PromQL rules against them. It's built for rates, latency percentiles, capacity planning, and alerting.

Splunk indexes and searches logs and events — some of its products also handle metrics and traces — and it's built for forensic search and correlating events across logs. The two are complementary, not substitutes for each other.

SPL is Splunk's query language, Search Processing Language. A safe investigation narrows the time range and source first, then filters and aggregates — for example:

`index=prod service=payments level=ERROR | stats count by error_code | sort - count`

I avoid unlimited all-time searches, and I make sure sensitive fields are masked before the data is even ingested.
