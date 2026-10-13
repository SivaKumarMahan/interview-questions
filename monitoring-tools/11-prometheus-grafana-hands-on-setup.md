# Monitoring Tools: Prometheus and Grafana Hands-On Setup

> Step-by-step setup of a monitoring stack: Prometheus, Node Exporter and Grafana on a Linux VM, then a full Docker Compose stack with cAdvisor, Loki and Grafana Alloy, data sources, imported and custom dashboards, logs, and a first alert.

## Key Concepts

### What You Build

```text
Metrics:
  Linux VM ──► Node Exporter :9100 ──┐
  Containers ──► cAdvisor :8080 ─────┼──► Prometheus :9090 ──► Grafana :3000
                                     │      (pull / scrape)        │
Logs:                                │                             │
  Container logs ──► Grafana Alloy ──► Loki :3100 ─────────────────┘
                        (push)
Alerts:
  Grafana alert rules or Prometheus rules ──► contact point (Slack, Teams, email)
```

| Component | Role | Default port |
| --- | --- | --- |
| Prometheus | Scrapes and stores metrics, runs PromQL and alert rules | 9090 |
| Node Exporter | Exposes Linux host metrics at `/metrics` | 9100 |
| cAdvisor | Exposes per-container CPU, memory, network and filesystem metrics | 8080 |
| Grafana | Dashboards, Explore, and alerting on top of the data sources | 3000 |
| Loki | Stores logs, queried with LogQL | 3100 |
| Grafana Alloy | Collects logs (and metrics or traces) and pushes them to Loki | 12345 (UI) |
| Alertmanager | Groups and routes Prometheus alerts | 9093 |

Prometheus **pulls** metrics: every scrape interval it calls each target's `/metrics` endpoint. Log collectors **push** to Loki. Grafana stores no metrics or logs itself; it queries its data sources.

### Corrections to Common Tutorials

Many beginner guides still show steps that are outdated or wrong. Use these instead:

| Older guide says | Use instead | Why |
| --- | --- | --- |
| Promtail as the log agent | Grafana Alloy | Promtail reached end of life in March 2026 |
| Loki data source URL `http://loki:9090` | `http://loki:3100` | 9090 is Prometheus; Loki listens on 3100 |
| Alert on `avg(node_cpu_seconds_total{mode="idle"})` | `100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))` | The metric is a counter; use `rate()` to get a percentage |
| `google/cadvisor:latest` | `gcr.io/cadvisor/cadvisor:<version>` | The Docker Hub image is no longer maintained |
| `packages.grafana.com` repository | `rpm.grafana.com` / `apt.grafana.com` | Current official Grafana repositories |
| Loki config with `schema: v11` and `store: tsdb`, `enforce_metric_name` | `schema: v13` with `store: tsdb`; remove `enforce_metric_name` | TSDB needs schema v12+; the old option was removed in Loki 3 |
| Open 9090, 9100, 3000 to `0.0.0.0/0` | Allow only your IP, or use an SSH tunnel / VPN | Prometheus and exporters have no authentication by default |
| Images tagged `latest` | Pinned versions | Reproducible, reviewable upgrades |

## Part A: Install on a Linux VM

Example: one Ubuntu or Amazon Linux VM (AWS EC2 or Azure VM) that runs everything. Replace version numbers with the current releases from the project pages.

### Step 1: Install Prometheus as a service

```bash
PROM_VERSION=3.5.0
sudo useradd --system --no-create-home --shell /usr/sbin/nologin prometheus
cd /tmp
curl -LO https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.linux-amd64.tar.gz
tar xzf prometheus-${PROM_VERSION}.linux-amd64.tar.gz
sudo mv prometheus-${PROM_VERSION}.linux-amd64/{prometheus,promtool} /usr/local/bin/
sudo mkdir -p /etc/prometheus /var/lib/prometheus
sudo chown prometheus:prometheus /var/lib/prometheus
```

`/etc/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: node_exporter
    static_configs:
      - targets: ["localhost:9100"]
```

`/etc/systemd/system/prometheus.service`:

```ini
[Unit]
Description=Prometheus
After=network-online.target
Wants=network-online.target

[Service]
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=15d \
  --web.listen-address=0.0.0.0:9090
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
promtool check config /etc/prometheus/prometheus.yml
sudo systemctl daemon-reload
sudo systemctl enable --now prometheus
systemctl status prometheus
```

### Step 2: Install Node Exporter

```bash
NE_VERSION=1.9.1
sudo useradd --system --no-create-home --shell /usr/sbin/nologin node_exporter
curl -LO https://github.com/prometheus/node_exporter/releases/download/v${NE_VERSION}/node_exporter-${NE_VERSION}.linux-amd64.tar.gz
tar xzf node_exporter-${NE_VERSION}.linux-amd64.tar.gz
sudo mv node_exporter-${NE_VERSION}.linux-amd64/node_exporter /usr/local/bin/
```

`/etc/systemd/system/node_exporter.service`:

```ini
[Unit]
Description=Prometheus Node Exporter
After=network-online.target

[Service]
User=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
curl -s localhost:9100/metrics | grep ^node_cpu_seconds_total | head
```

On other servers, install only Node Exporter and add their `IP:9100` to the `node_exporter` job targets. Allow port 9100 only from the Prometheus server.

### Step 3: Install Grafana

Amazon Linux / RHEL:

```bash
sudo tee /etc/yum.repos.d/grafana.repo <<'EOF'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
sudo dnf install -y grafana
sudo systemctl enable --now grafana-server
```

Ubuntu / Debian:

```bash
sudo apt-get install -y apt-transport-https software-properties-common wget gpg
sudo mkdir -p /etc/apt/keyrings
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update && sudo apt-get install -y grafana
sudo systemctl enable --now grafana-server
```

### Step 4: Open access safely and verify

- In the security group or NSG, allow ports 3000 and 9090 **only from your own IP**. Do not expose 9100 publicly.
- Safer alternative: keep the ports closed and use an SSH tunnel: `ssh -L 3000:localhost:3000 -L 9090:localhost:9090 user@<vm-ip>`.
- Open `http://<vm-ip>:9090` → **Status → Target health**: both jobs must show `UP`.
- In **Query**, run `node_cpu_seconds_total` or `up` to see live data.
- Open `http://<vm-ip>:3000`, log in with `admin` / `admin`, and set a new password when prompted.

## Part B: Full Stack with Docker Compose

This lab runs Prometheus, Grafana, Node Exporter, cAdvisor, Loki and Grafana Alloy on one VM with Docker and the Compose plugin installed (`docker compose version` to check).

### Files

```text
monitoring/
├── docker-compose.yml
├── prometheus.yml
├── loki-config.yml
└── config.alloy
```

`docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.5.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=15d"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:12.1.0
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
      - loki
    restart: unless-stopped

  node_exporter:
    image: prom/node-exporter:v1.9.1
    container_name: node_exporter
    command:
      - "--path.rootfs=/host"
    volumes:
      - /:/host:ro,rslave
    pid: host
    restart: unless-stopped

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.52.1
    container_name: cadvisor
    privileged: true
    devices:
      - /dev/kmsg
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    restart: unless-stopped

  loki:
    image: grafana/loki:3.5.0
    container_name: loki
    command: -config.file=/etc/loki/loki-config.yml
    volumes:
      - ./loki-config.yml:/etc/loki/loki-config.yml:ro
      - loki-data:/loki
    restart: unless-stopped

  alloy:
    image: grafana/alloy:v1.10.0
    container_name: alloy
    command:
      - run
      - --server.http.listen-addr=0.0.0.0:12345
      - --storage.path=/var/lib/alloy/data
      - /etc/alloy/config.alloy
    volumes:
      - ./config.alloy:/etc/alloy/config.alloy:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - loki
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
  loki-data:
```

Only Prometheus and Grafana publish ports. The other containers are reached by service name on the Compose network, so they are not exposed to the internet.

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: node_exporter
    static_configs:
      - targets: ["node_exporter:9100"]

  - job_name: cadvisor
    static_configs:
      - targets: ["cadvisor:8080"]
```

`loki-config.yml` (single-node, filesystem storage):

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 168h
  max_entries_limit_per_query: 10000
```

`config.alloy` (collect logs from every Docker container and send them to Loki):

```alloy
discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"
}

discovery.relabel "containers" {
  targets = []

  rule {
    source_labels = ["__meta_docker_container_name"]
    regex         = "/(.*)"
    target_label  = "container"
  }
}

loki.source.docker "containers" {
  host          = "unix:///var/run/docker.sock"
  targets       = discovery.docker.containers.targets
  labels        = {"job" = "docker"}
  relabel_rules = discovery.relabel.containers.rules
  forward_to    = [loki.write.local.receiver]
}

loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

### Start and verify

```bash
cd monitoring
docker compose up -d
docker compose ps                      # every service should be "running"
docker compose logs -f alloy loki      # check for push or config errors
```

Open `http://<vm-ip>:9090` → **Status → Target health**: `prometheus`, `node_exporter` and `cadvisor` must be `UP`.

## Part C: Connect Grafana

### Add the data sources

1. Log in to Grafana (`admin` / `admin`) and set a new password.
2. **Connections → Data sources → Add data source → Prometheus.**
3. URL: `http://prometheus:9090` in Docker Compose, or `http://localhost:9090` when both run directly on the same VM.
4. **Save & test** → "Successfully queried the Prometheus API."
5. Add **Loki** the same way with URL `http://loki:3100`.

Inside a container, `localhost` means that container itself, which is the most common reason a data source test fails in Docker.

### Import ready-made dashboards

1. **Dashboards → New → Import.**
2. Enter a dashboard ID from grafana.com and click **Load**:
   - `1860` – Node Exporter Full (host CPU, memory, disk, network).
   - `19908` – cAdvisor Docker Insights (per-container usage).
3. Select the Prometheus data source and click **Import**.

Always check that an imported dashboard's job labels and variables match your setup.

### Build a custom panel

1. **Dashboards → New dashboard → Add visualization**, pick Prometheus.
2. Enter a query, for example:

```promql
# CPU usage % per host
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))

# Memory usage %
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

# CPU used by each container (cores)
sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[5m]))
```

3. Choose a visualization (Time series for trends, Gauge or Stat for current values), set the unit (percent, bytes), thresholds and a title.
4. **Save dashboard**, and add more panels the same way.

### Logs dashboard with Loki

1. Add a visualization, select the **Loki** data source.
2. Query by label, for example `{container="prometheus"}` or `{job="docker"} |= "error"`.
3. Choose the **Logs** visualization, give it a title such as `prometheus-logs`, and turn on timestamps.
4. Repeat for other containers, then save the dashboard.

Use **Explore** to test LogQL queries before adding them to a dashboard.

## Part D: Create a First Alert in Grafana

1. **Alerting → Contact points → Add contact point**: choose Slack, Microsoft Teams, email or a webhook, and test it.
2. **Alerting → Alert rules → New alert rule**:
   - Query: `100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))`
   - Condition: threshold `IS ABOVE 90`.
   - Evaluate every `1m`, pending period `5m`.
   - Labels: `severity=critical`, `team=platform`.
   - Annotations: summary and a runbook link.
3. **Notification policies**: route `severity=critical` to the on-call contact point, group by `instance`, and set the repeat interval (for example 30 minutes).
4. Test it with a CPU stress command (`stress-ng --cpu 2 --timeout 600`) and check both the firing and resolved messages.

For Prometheus-only infrastructure alerts in production, Prometheus rules with Alertmanager are often preferred (see [Grafana and Alertmanager](03-grafana-and-alertmanager.md)).

## Common Problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Target shows `DOWN` with "connection refused" | Exporter not running, wrong port, or firewall | `systemctl status node_exporter`, `curl <target>:9100/metrics`, check NSG / security group |
| Grafana "data source test failed" | `localhost` used inside a container | Use the service name, for example `http://prometheus:9090` |
| No data in an imported dashboard | Job name or labels differ from the dashboard's variables | Edit the variables or the `job_name` |
| Loki shows no logs | Alloy cannot read the Docker socket, or wrong Loki URL | `docker compose logs alloy`; check the socket mount and `http://loki:3100` |
| Loki fails to start | Old schema or removed config options | Use `schema: v13` with TSDB and remove deprecated keys |
| cAdvisor container restarts | Missing privileges or host mounts | Check `privileged`, `/dev/kmsg`, and the read-only host mounts |
| Prometheus disk filling up | Retention too long for the volume | Set `--storage.tsdb.retention.time` or `.size` |

## Interview Questions

<details><summary>Q1. [Basic] Walk me through how you set up Prometheus and Grafana to monitor a Linux server.</summary>

**Answer:**

1. Install Node Exporter on the server as a systemd service; it exposes host metrics on port 9100 at `/metrics`.
2. Install Prometheus and add the server to a scrape job in `prometheus.yml`, then validate with `promtool check config` and restart.
3. Confirm the target is `UP` on the Prometheus **Target health** page and query `node_cpu_seconds_total`.
4. Install Grafana, change the default admin password, and add Prometheus as a data source.
5. Import dashboard 1860 (Node Exporter Full) or build panels with PromQL, then add alerts for CPU, memory and disk with a contact point.

I restrict ports 9090 and 9100 to the monitoring network and put Grafana behind TLS and SSO.

</details>

<details><summary>Q2. [Basic] What are the default ports of Prometheus, Node Exporter, Grafana, Loki, cAdvisor and Alertmanager?</summary>

**Answer:**

Prometheus 9090, Node Exporter 9100, Grafana 3000, Loki 3100, cAdvisor 8080, Alertmanager 9093. Knowing these helps with firewall rules and with spotting misconfigured data source URLs, such as pointing Grafana's Loki data source at 9090, which is Prometheus.

</details>

<details><summary>Q3. [Intermediate] Grafana's Prometheus data source test fails in a Docker Compose setup. Why?</summary>

**Answer:**

Most often the URL is `http://localhost:9090`. Inside the Grafana container, `localhost` is the Grafana container itself, not Prometheus. Use the Compose service name, `http://prometheus:9090`, because both containers share the Compose network.

Other checks: the Prometheus container is running (`docker compose ps`), both services are on the same network, and nothing in front of Prometheus requires authentication.

</details>

<details><summary>Q4. [Intermediate] Why do older guides use Promtail, and what would you use today?</summary>

**Answer:**

Promtail was Loki's original log agent: it tailed log files, added labels and pushed the lines to Loki. It reached end of life in March 2026. Today I use **Grafana Alloy**, which is Grafana's OpenTelemetry-compatible collector. It can collect logs, metrics and traces with one agent, discover Docker or Kubernetes targets, and push logs to Loki. Existing Promtail configs can be converted with `alloy convert --source-format=promtail`.

</details>

<details><summary>Q5. [Intermediate] What is the difference between Node Exporter and cAdvisor?</summary>

**Answer:**

Node Exporter reports **host-level** metrics: CPU, memory, disk, filesystem and network of the whole machine. cAdvisor reports **per-container** metrics: CPU, memory, network and filesystem usage of each container. On a Docker host you usually run both. In Kubernetes, cAdvisor is built into the kubelet, and kube-state-metrics adds object state such as desired vs available replicas.

</details>

<details><summary>Q6. [Intermediate] How would you secure this monitoring stack before using it in production?</summary>

**Answer:**

- Never expose Prometheus, exporters, Loki or Alertmanager to the internet; they have no authentication by default. Keep them on a private network and allow scrapes only from Prometheus.
- Put Grafana behind TLS and SSO, remove the default admin password, and use least-privilege roles.
- Pin image versions, persist data on volumes, set retention, and back up Grafana and the configs in Git.
- Store contact-point credentials (Slack webhooks, SMTP passwords) in a secret manager.
- Review privileged containers such as cAdvisor, and monitor the monitoring stack itself (target health, disk usage, failed notifications).

</details>
