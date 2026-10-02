# Docker: Troubleshooting and Host Maintenance

> Debugging containers that exit or start slowly, common failure scenarios, disk-space cleanup, pruning, and Docker host maintenance.

## Key Concepts

### Scenario Reminders

- **Works locally but not in Docker:** compare configuration, files, CPU architecture, dependencies, the port the app listens on, filesystem permissions, DNS/network setup, and logs.
- **Large image:** check layers, the build context, cache ordering, the base image, leftover package caches, and whether a multi-stage build would help.
- **Frequent restarts:** check the exit code, whether it was OOM-killed, health status, logs, configuration, dependencies, and resource limits.
- **Persistent data:** use a named volume or an external datastore with backups — never rely on the container's writable layer.
- **Multi-container communication:** use a user-defined network and reach other containers by name, not by a fixed IP address.

## Interview Questions

<details><summary>Q1. [Intermediate] What should you do when a Docker container exits immediately after startup?</summary>

**Answer:**

I check `docker ps -a` for the exit code, run `docker logs <container>`, and use `docker inspect` to look at the command, entrypoint, environment, mounts, health status, whether it was OOM-killed, and any runtime errors. Exit code 0 usually just means the main process finished normally — a container only stays running while its main process (PID 1) is still running.

Exit code 1 usually points to an application or config error, 126/127 to a bad command or permissions problem, and 137 usually means it was killed — often by SIGKILL or an out-of-memory kill.

I re-run the exact same image with the intended configuration in a safe environment, only overriding the entrypoint if I need to poke around for diagnosis.

Common causes: a shell-form command that breaks signal handling, a wrong file path, a missing config value or secret, a CPU architecture mismatch, a bind mount accidentally hiding files that should be there, a permissions error, a failed dependency, or the app trying to daemonize itself instead of staying in the foreground.

Once I find the cause, I fix the image or deployment config, rebuild, and re-verify startup, health, logs, clean shutdown, and the restart policy. I never just run `tail -f /dev/null` to paper over a broken main process.

</details>

<details><summary>Q2. [Intermediate] How do you debug slow Docker container startup? <em>(asked in interview round)</em></summary>

**Answer:** Check the image size. Optimize the Dockerfile. Preload dependencies. Monitor entrypoint logs.

**Detailed interview approach:**
I start by measuring rather than guessing. I check the image size and layer count, how much of the build hit cache, and how long the application itself takes to initialize.

Common causes are a bloated image, dependencies being installed at container startup instead of build time, slow registry pulls, or the application doing heavy work (like loading large files or connecting to slow dependencies) before it's ready to serve traffic.

Once I find the bottleneck, I fix the Dockerfile — usually with multi-stage builds and better layer ordering — rebuild, and confirm startup time actually improved.

</details>

<details><summary>Q3. [Intermediate] If Docker containers are consuming too much disk space, how do you fix it?</summary>

**Check disk usage by Docker**

```bash
docker system df
```

This shows how much space is used by:

- Images
- Containers
- Local volumes
- Build cache

**Remove stopped containers**

```bash
docker container prune
```

**Remove unused images, volumes, networks**

```bash
docker image prune
docker volume prune
docker network prune
```

This deletes all unused containers, images, volumes, and networks.

```bash
docker system prune -a --volumes
```

**Check container log size**

```bash
sudo du -sh /var/lib/docker/containers/*/*-json.log | sort -hr | head
```

**Truncate large logs safely:**

```bash
sudo truncate -s 0 /var/lib/docker/containers/<container-id>/<container-id>-json.log
```

</details>

<details><summary>Q4. [Basic] What's the difference between <code>docker system prune</code> and <code>docker system prune -a</code>?</summary>

- `docker system prune` removes unused containers, networks, and dangling images (images with no tag).
- `docker system prune -a` goes further and removes all unused images, even ones that are still tagged.

</details>

<details><summary>Q5. [Intermediate] How do you prevent Docker from filling the disk again?</summary>

- Prune unused images regularly.
- Set logging limits so container logs can't grow forever.
- Store Docker's data on a dedicated volume or partition, separate from the rest of the OS.

</details>

<details><summary>Q6. [Basic] What are dangling Docker objects?</summary>

**Answer:**

A dangling image is one with no tag pointing to it — usually left behind after you rebuild an image with the same tag as before. Unused containers, networks, volumes, and build cache can also pile up and use disk space, but "dangling" specifically refers to untagged images.

```bash
docker image ls --filter dangling=true
docker system df -v
docker image prune
```

I check what's there before cleaning anything up. A volume might still hold important data, and an old image might be exactly what you'd need to roll back to — so I keep some retention around and treat registry images, not local ones, as the real source of truth.

Any automated cleanup should have filters, disk thresholds, exclusions, logging, and a check that it isn't touching anything a live workload depends on.

</details>

<details><summary>Q7. [Basic] How do you delete all Docker resources in one command?</summary>

**Answer:**

I wouldn't run a broad "delete everything" command on a shared or production host. `docker system prune -a --volumes` removes every unused container, network, image, build cache entry, and unused volume after you confirm — and that can destroy data or images you actually needed for a rollback.

My actual approach: run `docker system df -v` to see what's using space, check what's still in use, back up any volume that matters, and then prune specific object types using age or label filters. In production, I'd rather replace a host outright when it needs cleaning than run an emergency deletion on a live one.

After cleanup, I check that running containers are unaffected, disk and inode usage looks right, the app is healthy, and images can still be pulled. Anything destructive gets logged and approved beforehand.

</details>

<details><summary>Q8. [Basic] How do you remove all containers and images safely?</summary>

**Answer:**

First, I get clear on exactly what needs removing and make sure nothing stateful gets caught up in it. Containers can be stopped and removed explicitly, and an image can only be removed once nothing depends on it:

```bash
docker container ls -aq
docker image ls -q
```

On a disposable lab machine, commands like `docker container prune` and `docker image prune -a` are safer than a broad shell one-liner, because they show you the scope and ask for confirmation.

In production, I never blindly remove every container or run `docker system prune --volumes` — a named volume might hold real application data, running services could get interrupted, and useful evidence could be lost.

Instead, I check `docker system df`, remove only the stopped containers and unused images that are actually approved for removal, confirm the registry still has the images we might need, and keep volume backups. Ongoing cleanup should run on a retention policy with disk alerts, not as an emergency measure — and in production I'd rather replace a host than deep-clean a live one.

</details>

<details><summary>Q9. [Advanced] What happens if you delete <code>/var/lib/docker/overlay</code> on a Docker host?</summary>

**Answer:**

It can corrupt or destroy image data and container writable layers, and containers will start failing. I never manually delete anything inside Docker's internal storage directory while the daemon is using it.

If the real problem is a full disk, the safe path is `docker system df` to see what's using space, then identifying objects, preserving volumes, and using the proper prune or removal commands with approval — not touching the internals directly.

If that directory has already been deleted, I stop making further changes, preserve logs as evidence, check whether any volumes were affected separately, and usually rebuild the host from known-good configuration and re-pull the same fixed images, rather than attempting a risky manual repair.

I then restore any persistent application data from a proper volume backup, validate the workloads, bring the host back into service, and add capacity alerts and automated cleanup so this doesn't happen again. Docker's internal storage directory is not something an operator should ever touch by hand.

</details>

<details><summary>Q10. [Advanced] You need live patching of a Docker host kernel without downtime. How do you achieve it?</summary>

**Answer:**

My default approach is redundancy and rotation: take one host out of scheduling and load balancing, move its containers to healthy hosts, patch and reboot it, verify it's healthy, then bring it back. This handles any patch, including ones that require a reboot, and it also proves your failover actually works.

Kernel live-patching tools — Canonical Livepatch, kpatch, or a cloud provider's own offering — can apply some security fixes without a reboot, but not every patch qualifies for live patching. I check kernel and patch compatibility first, test it on a lower environment, monitor closely, and still schedule a periodic reboot onto a fully updated kernel.

On a single host, you can't truly guarantee zero downtime for the application — the architecture needs another instance to fail over to.

</details>
