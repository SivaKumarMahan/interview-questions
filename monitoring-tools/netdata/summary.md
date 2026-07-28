# Netdata Summary

**Netdata** is a real-time infrastructure monitoring platform centered on the **Netdata Agent**. The Agent automatically collects high-frequency system and application metrics through collectors, stores recent data locally according to configuration, displays dashboards and evaluates health alerts.

It is useful for rapid host/container troubleshooting and can complement Prometheus, cloud-native monitoring data or a larger observability platform.

For multiple systems, **Child Agents** can stream metrics to one or more **Parent Agents** for centralized retention, dashboards and alert processing. Production architecture must size Parent storage and ingestion, protect streaming credentials, use TLS and restrict access.

The Agent's local web/API and streaming service use configurable networking; port `19999` is the documented default, but it should not be exposed broadly to the internet.

Monitor CPU, load, memory, swap, disks, filesystems, network, processes, containers and supported applications. Validate collector status and chart dimensions, alert route and resolution, retention, clock and parent/child connectivity.

An attractive dashboard is not enough: alerts require owners/runbooks and user-facing service SLIs still need application or synthetic instrumentation.
