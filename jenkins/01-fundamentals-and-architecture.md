# Jenkins: Fundamentals and Architecture

> What Jenkins is, the controller-agent model, job types, and plugins.

## Key Concepts

### What Jenkins Is

Jenkins is an automation server used to build CI/CD pipelines. It has two parts:

- **The controller** schedules jobs, stores configuration, and coordinates agents.
- **Agents** are the machines or containers that actually run the build steps.

A `Jenkinsfile` holds the pipeline as code, written in Groovy. It's version-controlled and normally kept at the root of the application repository, so pipeline changes go through the same review and history as any other code change.

There are two pipeline styles:

| Style | When to use it |
| --- | --- |
| Declarative Pipeline | The default choice. Structured, easier to read, has built-in validation. |
| Scripted Pipeline | More flexible, but easier to turn into a mess. Use only when Declarative can't do what you need. |

The main sections in a Declarative Pipeline are `pipeline`, `agent`, `environment`, `options`, `parameters`, `triggers`, `stages`, `stage`, `steps`, `when`, `tools`, and `post`.

Common steps you'll see in almost every pipeline: `checkout`/`git` to pull code, `sh`/`bat` to run shell commands, `withCredentials` to use secrets safely, `junit` to publish test results, `archiveArtifacts` to save build output, `stash`/`unstash` to pass files between stages, and various notification steps.

## Interview Questions

### 1. Explain Jenkins controller-agent architecture and how it enables distributed builds.

**Answer:**

The Jenkins controller holds the configuration, schedules jobs, evaluates pipelines, manages credentials and plugins, records build history, and hands out work. Agents are the machines that actually run the build steps.

An agent can be a static VM or a container/Pod that gets created just for one job and thrown away afterward.

```text
Git webhook → Jenkins controller → queue → labeled agent
                                   → build/test/scan → artifact registry
```

I label agents by what they can do, and use the pipeline `agent` directive so each workload lands on the right kind of machine. Agents that come from Kubernetes are especially clean: each one starts from an approved image, runs exactly one job, and disappears. That cuts down on configuration drift and stops secrets from lingering on disk.

For security, I don't run builds on the controller itself, I give credentials only the access they need, I isolate agents from each other, restrict network access, keep images and plugins patched, and keep trusted and untrusted workloads apart. I also watch queue length, how busy the executors are, agent connection failures, disk space, and overall controller health.

### 2. Freestyle job versus Pipeline: what is the difference?

**Answer:**

A Freestyle job is configured mostly through the Jenkins UI. It's fine for a simple, one-off task, but its configuration is harder to review, version, and reuse.

A Pipeline defines every delivery stage as code in a `Jenkinsfile`. That means code review, durable execution, parallel stages, shared libraries, credential binding, approvals, and a repeatable promotion process.

I prefer Declarative Pipeline for normal CI/CD work because its structure and built-in validation are clearer. Scripted Pipeline is more flexible, but it needs a lot more discipline to keep readable.

### 3. What are Jenkins plugins, and how do you manage them safely?

**Answer:**

Plugins extend Jenkins to work with source control, credentials, agents, pipelines, test reports, artifact repositories, cloud provisioning, and notifications.

Every plugin is code that runs inside Jenkins, so it carries real compatibility and supply-chain risk. I only install supported plugins, pin and test versions on a non-production controller first, watch for security advisories, remove plugins nobody uses, back up configuration, and have a plan to restart or roll back.

I try not to install a plugin just because a pipeline could call it — a CLI, an API, or a shared-library integration is often safer and easier to govern.
