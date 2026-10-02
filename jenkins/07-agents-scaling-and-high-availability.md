# Jenkins: Agents, Scaling, and High Availability

> Agent failures and autoscaling, controller crashes, single points of failure, HA, and disaster recovery.

## Interview Questions

### 1. What if a Jenkins agent node goes offline?

**Answer:**

I check whether it's just one agent, or a whole label or pool, that's affected, and whether the jobs running on it are safe to just retry. In Jenkins, I look at the offline reason and the connection log.

On the agent itself, I check the process or container status, CPU/memory/disk, the Java version, DNS and network access to the controller, certificates, credentials, the clock, and workspace permissions.

For Kubernetes agents, I look at Pod events, image pulls, scheduling, resource quotas, the service account, and container logs. I replace an unhealthy agent rather than trying to fix it in place — but I save the evidence first, before replacing it.

I only reconnect once I've actually fixed the cause. I clean up any workspace that might be corrupted, rerun the stages that are safe to run more than once, and confirm the output is correct. Autoscaling, having more than one agent per label, health checks, and agent images that never change after they're built all stop a single bad host from blocking delivery.

### 2. What if a Jenkins agent node goes offline? *(scenario)*

**Answer:** Check agent logs → Restart service → Verify connectivity with master → Add auto-scaling slaves (Kubernetes or cloud VMs).

**Detailed interview approach:**
I start by checking the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can be stuck waiting because no agent matches its label, every executor is busy, a node has disconnected, a concurrency limit is in effect, or cloud-agent provisioning failed.

I check `Manage Nodes`, queue and build metrics, agent pod or VM events, and network and credential health, then restore or scale the right agent pool. Adding more executors to the controller is not the fix.

To stop this from happening again, I use agents that scale automatically and get created fresh for each job, set up alerts for capacity and queue time, use sensible labels and quotas, add health checks to agent images, apply timeouts, and keep long or privileged workloads separate from everything else.

### 3. How do you implement auto-scaling for Jenkins agents? *(scenario)*

**Answer:** Integrate Jenkins with Kubernetes plugin → Agents spin up as pods on demand → Auto-terminate after job completion.

**Detailed interview approach:**
I start by checking the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can be stuck waiting because no agent matches its label, every executor is busy, a node has disconnected, a concurrency limit is in effect, or cloud-agent provisioning failed.

I check `Manage Nodes`, queue and build metrics, agent pod or VM events, and network and credential health, then restore or scale the right agent pool. Adding more executors to the controller is not the fix.

To stop this from happening again, I use agents that scale automatically and get created fresh for each job, set up alerts for capacity and queue time, use sensible labels and quotas, add health checks to agent images, apply timeouts, and keep long or privileged workloads separate from everything else.

### 4. How do you scale Jenkins dynamically? *(scenario)*

**Answer:** Integrate Jenkins with Kubernetes cloud plugin → Auto-create agents as pods → Terminate when idle.

**Detailed interview approach:**
I start by checking the queue reason, executor usage, node labels, offline status, and the controller and agent logs. A job can be stuck waiting because no agent matches its label, every executor is busy, a node has disconnected, a concurrency limit is in effect, or cloud-agent provisioning failed.

I check `Manage Nodes`, queue and build metrics, agent pod or VM events, and network and credential health, then restore or scale the right agent pool. Adding more executors to the controller is not the fix.

To stop this from happening again, I use agents that scale automatically and get created fresh for each job, set up alerts for capacity and queue time, use sensible labels and quotas, add health checks to agent images, apply timeouts, and keep long or privileged workloads separate from everything else.

### 5. What if a Jenkins controller crashes?

**Answer:**

First I figure out whether it's the process, the host, storage, the database, or the network that failed, and I make sure nobody starts a second, conflicting recovery attempt at the same time.

I save the logs, then restore the controller from a tested `JENKINS_HOME` backup or persistent storage, along with the version-controlled Jenkins Configuration as Code, the plugin version list, and the pipeline definitions.

Artifacts stay safe because they live in an external registry, not on the controller, and agents are disposable anyway. Before I let production deployments run again, I check credentials, plugins, webhooks, agents, the queue, and one non-production pipeline.

Standard Jenkins doesn't normally run as an active-active controller setup. I describe this as backup-and-restore, or a warm standby, with a measured recovery time and recovery point.

To prevent this in the future: monitor controller health, alert on disk space, regularly test that backups actually restore, keep the plugin list small, and keep configuration and pipelines in Git.

### 6. What if Jenkins master crashes? *(scenario)*

**Answer:** I first determine whether only the process failed or the VM, container, disk, or database is also unavailable. I restore the controller on a known-good host from a tested backup of `JENKINS_HOME`, configuration-as-code files, plugin versions, credentials, and job metadata.

Build artifacts should live in an external artifact repository rather than only on the controller.

I reduce recovery time by keeping Jenkins Configuration as Code and pipeline definitions in Git, using persistent and backed-up storage, monitoring controller health, and using ephemeral agents so builds do not depend on the controller host.

Standard Jenkins is not an active-active controller system, so I describe this as disaster recovery or warm standby, not automatic active-active HA.

After recovery, I validate credentials, plugins, agents, webhooks, queued jobs, and one non-production pipeline before enabling production deployments.

**Detailed interview approach:**
I treat recovering the controller as a separate problem from keeping build capacity available. Jenkins controllers normally run active/passive — just running multiple replicas against the same home directory doesn't make them safe on its own.

I keep configuration and pipelines as code, back up `JENKINS_HOME` on a regular schedule, record which plugin versions are running, protect credentials, and actually test restoring to a standby or new controller. Builds run on agents that get created fresh for each job and torn down afterward, so losing one agent isn't a big deal.

If the controller crashes, I preserve the logs first, then restore or fail over using the documented storage or database procedure, reconnect the agents, and check that credentials, jobs, the queue, and webhooks all came back correctly. I keep watching the controller's JVM health, disk space, queue length, backup success, and how long recovery actually takes.

### 7. How do you handle Jenkins master node becoming a single point of failure? *(scenario)*

**Answer:** Run Jenkins in HA (Kubernetes) → Backup Jenkins home → Scale horizontally with agents.

**Detailed interview approach:**
I treat recovering the controller as a separate problem from keeping build capacity available. Jenkins controllers normally run active/passive — just running multiple replicas against the same home directory doesn't make them safe on its own.

I keep configuration and pipelines as code, back up `JENKINS_HOME` on a regular schedule, record which plugin versions are running, protect credentials, and actually test restoring to a standby or new controller. Builds run on agents that get created fresh for each job and torn down afterward, so losing one agent isn't a big deal.

If the controller crashes, I preserve the logs first, then restore or fail over using the documented storage or database procedure, reconnect the agents, and check that credentials, jobs, the queue, and webhooks all came back correctly. I keep watching the controller's JVM health, disk space, queue length, backup success, and how long recovery actually takes.

### 8. How do you implement High Availability (HA) Jenkins? *(scenario)*

**Answer:** Run Jenkins on Kubernetes with persistent volume → Use multiple replicas with HA proxy → Backup Jenkins home regularly.

**Detailed interview approach:**
I treat recovering the controller as a separate problem from keeping build capacity available. Jenkins controllers normally run active/passive — just running multiple replicas against the same home directory doesn't make them safe on its own.

I keep configuration and pipelines as code, back up `JENKINS_HOME` on a regular schedule, record which plugin versions are running, protect credentials, and actually test restoring to a standby or new controller. Builds run on agents that get created fresh for each job and torn down afterward, so losing one agent isn't a big deal.

If the controller crashes, I preserve the logs first, then restore or fail over using the documented storage or database procedure, reconnect the agents, and check that credentials, jobs, the queue, and webhooks all came back correctly. I keep watching the controller's JVM health, disk space, queue length, backup success, and how long recovery actually takes.

### 9. How should you design Jenkins high availability (and what is it not)?

Standard Jenkins does not provide active-active controller clustering like some other clustered platforms. Don't say "run two Jenkins masters against the same `JENKINS_HOME`" - that's not how Jenkins works, and doing it risks corrupting state.

A good Jenkins HA/DR design instead focuses on:

- Reliable Jenkins controller infrastructure
- Durable Jenkins state
- Backups
- Multiple build agents
- Monitoring
- Disaster recovery

```
Users
  |
  v
Load Balancer / DNS
  |
  v
Jenkins Controller
  |
  v
Durable Jenkins storage
  |
  v
Jenkins Agents
```

`JENKINS_HOME` contains all the critical Jenkins state:

```
jobs/
plugins/
credentials/
users/
nodes/
secrets/
config.xml
```

Use durable storage for `JENKINS_HOME` and take regular backups. Do **not** run multiple active controllers against the same `JENKINS_HOME` - only one controller process should own it at a time.

Use multiple agents so a single agent failure doesn't stop builds:

```
Controller
  ├── Agent 1
  ├── Agent 2
  └── Agent 3
```

If one agent fails, Jenkins can schedule builds on another. Combine this with Pipeline as Code (Jenkinsfiles stored in Git) so the pipeline definition itself isn't a single point of failure either.

Monitor:

- Jenkins availability
- CPU/memory
- Disk
- Executor utilization
- Queue length
- Agent availability
- Build failures
- Jenkins logs

**Key interview point:** Jenkins HA is not "multiple active controllers." Think controller resilience + durable state + redundant agents + backup/DR.

### 10. How do you design disaster recovery for Jenkins? *(scenario)*

**Answer:** Backup Jenkins home + configs to cloud storage → Use Infrastructure as Code to recreate Jenkins → Run Jenkins on Kubernetes with persistent storage.

**Detailed interview approach:**
I treat recovering the controller as a separate problem from keeping build capacity available. Jenkins controllers normally run active/passive — just running multiple replicas against the same home directory doesn't make them safe on its own.

I keep configuration and pipelines as code, back up `JENKINS_HOME` on a regular schedule, record which plugin versions are running, protect credentials, and actually test restoring to a standby or new controller. Builds run on agents that get created fresh for each job and torn down afterward, so losing one agent isn't a big deal.

If the controller crashes, I preserve the logs first, then restore or fail over using the documented storage or database procedure, reconnect the agents, and check that credentials, jobs, the queue, and webhooks all came back correctly. I keep watching the controller's JVM health, disk space, queue length, backup success, and how long recovery actually takes.
### 11. How do you plan Jenkins disaster recovery (backups, RPO, RTO)?

DR means that if the Jenkins controller or its infrastructure is lost, Jenkins can be restored quickly enough to continue CI/CD. The core principle: **`JENKINS_HOME` is critical state.**

```
Primary Region
  |
  v
Jenkins Controller
  |
  v
JENKINS_HOME
  ├── Backup Storage
  └── Agents
```

Backup storage can be Azure Blob Storage or another durable external store - do **not** keep the only backup on the Jenkins server itself.

What to back up: job configurations, pipeline configurations (if not already in Git), Jenkins configuration, credentials and secrets, plugin information, user configuration, node/agent configuration, and any other required Jenkins metadata.

Use: automated backups, external storage, a separate-region copy where appropriate, retention policies, immutability where required, and periodic restore testing.

**RPO (Recovery Point Objective)** - how much data loss is acceptable. Example: RPO = 1 hour means the recovery point should be no more than roughly an hour old.

**RTO (Recovery Time Objective)** - how quickly Jenkins needs to be restored. Example: RTO = 2 hours means Jenkins should be back up within 2 hours.

Make Jenkins reproducible so recovery isn't just "restore a tarball": Jenkins Configuration as Code, Terraform/Bicep for the infrastructure, Ansible for host configuration, and Jenkinsfiles in Git for the pipelines themselves.

Recovery flow:

```
Jenkins Primary Failed
  |
  v
Declare DR
  |
  v
Provision new Jenkins infrastructure
  |
  v
Install Jenkins
  |
  v
Restore Jenkins data/configuration
  |
  v
Restore required secrets
  |
  v
Connect agents
  |
  v
Run smoke test
  |
  v
Resume CI/CD
```

Test the DR process periodically - an untested backup is not a verified recovery path.

**HA vs DR:** HA minimizes downtime from an infrastructure failure (agents/controller resilience while things are still mostly working). DR restores Jenkins after a major failure or total loss.
