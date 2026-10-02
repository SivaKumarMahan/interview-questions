# Artifact Repositories: Troubleshooting

> Diagnosing failed artifact publishes, failed Docker image pushes, and common Nexus Repository issues.

## Interview Questions

### 1. How would you troubleshoot a pipeline that fails to publish artifacts to Nexus?

**Answer:**

I start with the exact HTTP status and client error.

| Symptom | Likely areas |
| --- | --- |
| `401` | Missing/invalid credential, wrong auth realm/token |
| `403` | Authenticated but missing add/edit privilege, content selector or policy block |
| `404` | Wrong repository URL/name/path or reverse-proxy routing |
| `400/409` | Invalid package metadata, duplicate/redeploy policy or format-specific conflict |
| `5xx` | Nexus/database/blob-store/internal failure |
| Timeout | DNS, TLS, firewall, reverse proxy, saturation (how close a resource is to its limit) or remote storage latency |

Flow:

1. Confirm the failure is publish, not dependency restore.
2. Record pipeline run, package coordinate, target URL, status and Nexus request ID/time.
3. Verify DNS and TLS chain from the same agent.
4. Check the endpoint is a compatible **hosted** repository.
5. Validate credentials without printing them.
6. Verify repository privileges and content selectors for that exact path.
7. Check release/snapshot version policy and redeploy policy.
8. Confirm package metadata and filename/coordinate.
9. Check Nexus status/writable endpoint, logs, database and blob-store capacity.
10. Compare with the last successful run/configuration.
11. Retry only if evidence shows a temporary failure.

For Docker, I additionally verify the Docker Bearer Token Realm, connector/subdomain, TLS certificate and separate login to the correct endpoint.

For Maven, I check that the `distributionManagement` repository ID matches the `<server>` ID in `settings.xml`.

### 2. How do you troubleshoot failed Docker image push to registry? *(scenario)*

**Answer:** Check registry credentials → Validate image name/tag → Ensure repository exists → Retry with correct login.

**Detailed interview approach:**
I look at the image, the runtime configuration, and the host separately. Builds use multi-stage Dockerfiles, small pinned trusted base images, a `.dockerignore` file, dependency layers ordered for caching, and non-root runtime users.

CI scans the dependencies and the image, generates an SBOM, signs the digest so it can't be swapped later, and pushes it over TLS to a registry with tightly scoped write access. Deployment then verifies that same digest before running it.

At runtime I drop unnecessary capabilities, use seccomp, AppArmor, or SELinux, run with a read-only filesystem, set resource limits, avoid exposing the privileged Docker socket, and restrict networking.

If startup is slow or a push fails, I measure layer size and cache hits, check registry DNS, auth, and TLS, and check disk and application initialization, instead of just retrying blindly. Then I rebuild from patched base images and re-verify functionality and security findings.

### 3. What common issues have you encountered while using Nexus Repository, and how would you troubleshoot them?

**Answer:**

#### Authentication and permission failures

Symptoms: `401` or `403`.

I check the credential or token expiry, the auth realm, the anonymous-access policy, the user's role, the repository-view privilege, the content selector, and whether the request even hits the group or goes to a member repository directly.

#### Release cannot be uploaded

I check:

- Snapshot sent to release repository or release sent to snapshot repository.
- Disable-redeploy policy rejecting an existing coordinate.
- Maven server ID mismatch.
- CI user has read but not add/edit.
- Invalid package metadata.

I publish a new version instead of enabling overwrite for an immutable release.

#### Dependency exists remotely but Nexus returns not found

I check the proxy's remote URL, remote availability, routing rule, negative cache, metadata and component cache age, and the repository group's membership and order. I only invalidate a cache when I have evidence it's the cause. I do not repeatedly wipe every cache and hope.

#### Docker login/push fails

I verify Docker Bearer Token Realm, connector/subdomain, TLS/SNI, reverse-proxy headers, registry endpoint, repository write permission and image name.

#### npm scope resolves incorrectly

I check `.npmrc`, scoped-registry mapping, group order, authentication and whether publish is going to hosted rather than the read group.

#### Nexus becomes read-only or returns 5xx

I inspect writable status, disk/blob capacity, PostgreSQL health/latency, JVM pressure, file descriptors and Nexus logs. I stop unsafe cleanup/retry loops and protect evidence.

#### Slow builds

I separate client, Nexus, proxy-remote, database, blob-storage and network latency. I look at cache hits, metadata checks, concurrency, JVM GC and storage I/O rather than assuming the public repository is slow.

#### Cleanup does not free disk

Cleanup may have soft-deleted components without compacting the blob store. I verify policy/task results, recovery-retention settings and schedule safe compaction after backup validation.

#### Artifact is present but cannot be downloaded through a group

I check group member order, group read/browse privilege, content selector and format compatibility. Direct member permission and group permission are separate.

#### General troubleshooting discipline

I collect:

```text
timestamp
pipeline/build ID
client and version
repository URL/type/format
artifact coordinate
HTTP status and request ID
Nexus version
recent configuration/deployment changes
server, database and blob-store health
```

Then I reproduce the problem with the same client, on the same network, using a non-secret verbose mode. I compare Nexus and reverse-proxy logs and fix the root cause. I avoid deleting caches, opening up permissions to a wildcard, or restarting Nexus repeatedly without evidence that any of that will help.
