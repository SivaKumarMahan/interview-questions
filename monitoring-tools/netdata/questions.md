## 1. What is Netdata, and when would you use it?

**Answer:**

Netdata runs an Agent on a host. The Agent finds collectors on its own, gathers real-time metrics, shows dashboards and evaluates health alerts.

I use it for fast infrastructure visibility: troubleshooting CPU, memory, disk, network, processes and containers. It gives useful dashboards with almost no setup.

It can sit alongside Prometheus, Grafana or cloud monitoring rather than replace them. I still need to define application SLIs, retention, access control and who owns each incident. Installing a tool by itself does not prove the service is available to customers.

## 2. How would you deploy Netdata securely in production?

**Answer:**

I use a pinned, supported deployment method and give it only the host or container access it actually needs. I restrict the local dashboard and API to localhost or a private management path, require authenticated access, protect configuration and streaming keys, and use TLS between Children and Parents.

I never expose the default port `19999` publicly without a secured proxy and an authorization design in front of it.

For centralized monitoring, Child Agents stream to resilient Parent capacity, or use the approved cloud connection model. Firewall rules allow only the paths that are actually needed.

I also define retention and storage limits, labels, alert receivers and backups, and test agent and parent upgrades in a lower environment first.

## 3. Netdata shows high CPU. How do you investigate?

**Answer:**

First I check whether the CPU spike is sustained, which cores are affected, and whether user, system, iowait or steal time dominates. I compare that against process and cgroup charts, traffic, load, recent deployments and any scheduled jobs.

On the host I confirm with `top`, `pidstat` or an equivalent tool, and look at application or runtime evidence before restarting anything.

To mitigate, I shift traffic, roll back, scale out, or stop a runaway task I've confirmed is nonessential. Then I fix the underlying cause: code, a bad query, configuration or capacity. I check that application latency and errors recover, along with Netdata's own CPU and load charts.

A host-level CPU alert is supporting evidence. It is not the root cause by itself.

## 4. How does Netdata Parent-Child monitoring work?

**Answer:**

Children collect metrics locally and stream them to one or more configured Parent Agents. Parents centralize those metrics and can provide dashboards, retention and health evaluation on behalf of their children.

This means you don't have to browse every node separately. Depending on configuration, buffering and replication can also preserve collection through some network interruptions.

When central monitoring is critical, I plan for more than one parent, or a clear recovery strategy. I size CPU, memory, disk and network from the node count and metric volume, use stable host labels, apply TLS and access controls, and watch for stream disconnects, lag, retention limits and how close the parent is to its own resource limits.

I test what happens on connection loss and reconnection. I don't just assume centralized monitoring is highly available.

## 5. How is Netdata different from Prometheus and Grafana?

**Answer:**

Netdata focuses on an integrated Agent: automatic collectors, real-time dashboards and health alerts with almost no setup. Prometheus is a time-series system built around labeled scraping, querying and rules, and is commonly used for services and Kubernetes. Grafana visualizes data from many different sources.

The three can coexist. Netdata handles rapid diagnosis on a single node, Prometheus handles selected platform and application metrics with a long-term architecture, and Grafana gives you shared dashboards across sources.

I pick between them based on scale, retention needs, query language, how well application instrumentation is exposed, integrations, operational effort, access and data residency requirements, and cost — not by declaring one tool universally better.
