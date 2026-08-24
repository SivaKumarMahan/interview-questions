# Netdata Summary

## What Netdata Is

Netdata is a real-time infrastructure monitoring platform built around the **Netdata Agent**. The Agent runs on a host, automatically finds collectors, gathers high-frequency system and application metrics, stores recent data locally, shows dashboards and evaluates health alerts.

It's a good fit for fast host and container troubleshooting. It can run alongside Prometheus, cloud-native monitoring, or a larger observability platform instead of replacing them.

## Parent-Child Architecture

For more than a handful of systems, **Child Agents** stream their metrics to one or more **Parent Agents**. The Parent centralizes retention, dashboards and alert processing so you don't have to check every node separately.

When you rely on this for production, plan for:

- Sizing Parent storage and ingestion capacity for the number of nodes and metrics involved.
- Protecting streaming credentials and using TLS between Children and Parents.
- Restricting access to the Parent, and having a recovery plan if it goes down.
- Testing what happens when a Child loses its connection and reconnects.

## Security and Networking

The Agent's local web UI, API and streaming service all use configurable networking. Port `19999` is the documented default, but it should never be exposed broadly to the internet — put it behind authentication and a secured proxy, or restrict it to a private management path.

## What to Monitor

| Area | What to check |
|---|---|
| Host resources | CPU, load, memory, swap, disks, filesystems, network |
| Workloads | Processes, containers, supported applications |
| Netdata itself | Collector status, chart dimensions, clock accuracy |
| Alerting | Alert routing, resolution, and who owns each alert |
| Parent-Child | Retention limits and parent/child connectivity |

## Where It Fits

A good-looking dashboard isn't the whole job. Alerts still need an owner and a runbook, and user-facing service SLIs still need application or synthetic instrumentation on top of what Netdata collects. Netdata is strongest for fast infrastructure visibility; it's not a replacement for defining what "healthy" means for your actual service.
