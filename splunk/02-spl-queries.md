# Splunk: SPL Queries

> SPL fundamentals and the commands interviewers ask about, search performance best practices, and practical DevOps queries for 5xx rates, latency, error spikes, failed logins, CI/CD failures, and Azure Activity Log and Entra ID sign-in logs.

## Key Concepts

### How a Search Runs

An SPL search is a pipeline. The first part (before the first `|`) is the **base search**: it picks events from indexes using the time range, indexed fields, and keywords. Each command after a `|` works on the output of the one before it.

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog earliest=-60m@m latest=now properties.httpStatus>=500
| stats count by properties.originalHost
| sort - count
```

The Azure examples in this file use data from the Splunk Add-on for Microsoft Cloud Services (Azure diagnostic settings to Event Hubs). Each Azure log record is one JSON event with top-level fields such as `category` and `operationName`, and the details under `properties.*`. Field paths can differ by add-on version and input settings, so I check them first with `| fieldsummary`.

- **Time range:** `earliest=-24h@h` means "24 hours ago, snapped to the start of the hour". Always set it. It is the cheapest filter.
- **Distributed work:** streaming commands (`eval`, `where`, `rex`, `fields`) run on the indexers. The first transforming command (`stats`, `timechart`) runs partly on indexers and finishes on the search head. Commands after that run on the search head only.

### Command Types

| Type | What it does | Examples |
| --- | --- | --- |
| Generating | Creates results without reading events from the pipeline | `search` (implicit), `tstats`, `inputlookup`, `makeresults`, `rest` |
| Distributable streaming | Works one event at a time, can run on indexers | `eval`, `where`, `rex`, `fields`, `rename`, `lookup` |
| Centralized streaming | One event at a time, but in order, on the search head | `streamstats`, `head`, `dedup` (partly), `transaction` |
| Transforming | Turns events into a table of results | `stats`, `chart`, `timechart`, `top`, `rare` |

The lesson: filter and drop fields early, so less data goes to the search head.

### Fields and Extraction

- **Indexed fields:** `index`, `host`, `source`, `sourcetype`, `_time`. Very fast to filter on.
- **Search-time fields:** extracted when you search, from `props.conf` rules, automatic key=value and JSON extraction, or inline with `rex` and `spath`.
- **Calculated fields:** `eval` creates new fields. `where` filters with eval expressions.

```text
index=app_prod sourcetype=myapp:log
| rex field=_raw "user=(?<user>\S+)\s+latency_ms=(?<latency_ms>\d+)"
| eval slow=if(latency_ms>1000, "yes", "no")
```

### stats, transaction, and join

`stats` is the workhorse. It is distributed, memory-efficient, and has no hidden limits for normal use. `transaction` groups events into sessions but runs on the search head and has memory limits. `join` runs a subsearch and is limited to 50,000 rows and 60 seconds by default. Most `transaction` and `join` searches can be rewritten with `stats ... by <key>`.

### tstats and Data Models

`tstats` reads the index files (`tsidx`) instead of the raw events. It works on indexed fields and on **accelerated data models**. It is often 10 to 100 times faster than the same `stats` over raw events. Data models follow the **Common Information Model (CIM)**, for example `Web`, `Authentication`, `Network_Traffic`, and `Change`.

```text
| tstats count where index=web by sourcetype, _time span=5m
| tstats summariesonly=true count from datamodel=Web where Web.status>=500 by Web.dest
```

### Subsearches and Lookups

A subsearch in `[ ]` runs first. Its results become a filter for the outer search. Default limits are 10,000 results and 60 seconds; if a limit is hit, the subsearch is cut off, sometimes with only a warning.

Lookups enrich events from a CSV file or KV store collection, for example service owner by hostname, or a list of known bad IPs.

### Search Performance Rules

- Always use a specific `index=` and `sourcetype=` and the smallest time range you need.
- Put filters in the base search, not in a later `| search` or `| where`.
- Avoid leading wildcards like `*error`. They cannot use the index.
- Use `fields` early to drop columns you do not need.
- Prefer `stats` over `transaction` and `join`.
- Use `tstats` with accelerated data models for dashboards and alerts over large data.
- Use the **Job Inspector** to see where the time goes.

See also: [Splunk: Alerts and Dashboards](03-alerts-and-dashboards.md) and [Splunk: Troubleshooting](04-troubleshooting.md).

## Interview Questions

<details><summary>Q1. [Basic] What does a basic SPL search look like, and how do you control the time range?</summary>

**Answer:**

A search starts with the base search, then pipes into commands:

```text
index=app_prod sourcetype=myapp:log level=ERROR earliest=-4h@h latest=now
| stats count by host
```

- `index` and `sourcetype` narrow the data to scan.
- `level=ERROR` filters on a field. A plain word like `timeout` matches the raw text.
- `earliest` and `latest` override the time picker. `-4h@h` means 4 hours ago, snapped to the hour. `@d` snaps to midnight. `-1d@d` to `@d` means "all of yesterday".
- Boolean operators must be upper case: `AND`, `OR`, `NOT`. `AND` is implied between terms.

**Pitfall:** `NOT status=200` also returns events with no `status` field at all. `status!=200` only returns events that have the field with another value.

</details>

<details><summary>Q2. [Basic] What is the difference between <code>stats</code>, <code>chart</code>, <code>timechart</code>, <code>eventstats</code>, and <code>streamstats</code>?</summary>

**Answer:**

- **stats:** aggregates into a table. Events are replaced by results. `stats count avg(latency_ms) by service`.
- **chart:** like stats, but with two grouping fields shaped as rows and columns. `chart count over host by status`.
- **timechart:** chart with `_time` on the x-axis and a fixed `span`. `timechart span=5m count by status`.
- **eventstats:** calculates an aggregate and **adds it to every event**, without removing events. Good for "compare each value to the average".
- **streamstats:** running calculations in event order, for example a moving average or a running count.

```text
index=app_prod sourcetype=myapp:log
| eventstats avg(latency_ms) as avg_latency by service
| where latency_ms > 3 * avg_latency
```

**Pitfall:** `timechart` limits the number of series to 10 by default and groups the rest into `OTHER`. Use `limit=0` or `useother=false` when you need all of them.

</details>

<details><summary>Q3. [Basic] What is the difference between <code>search</code>, <code>where</code>, and <code>eval</code>?</summary>

**Answer:**

- **search:** filters with search syntax: field=value, wildcards, keywords. Values are case-insensitive. Best in the base search.
- **where:** filters with an eval expression. It can compare two fields, use functions, and is case-sensitive for strings.
- **eval:** creates or changes a field. It does not filter.

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog
| eval is_error=if('properties.httpStatus'>=500, 1, 0)
| where 'properties.timeTaken' > 2 * 'properties.serverResponseLatency'
```

In `where` and `eval`, a field name with special characters (like `properties.status.errorCode` in JSON) must be in single quotes: `where 'properties.status.errorCode'!=0`. Double quotes mean a string.

**Pitfall:** in `where`, an unquoted word is read as a field name. `where host=web01` compares the `host` field with a field called `web01`, so it returns nothing. Write `where host="web01"`.

</details>

<details><summary>Q4. [Basic] Explain <code>table</code>, <code>fields</code>, <code>dedup</code>, <code>sort</code>, <code>top</code>, and <code>rare</code>.</summary>

**Answer:**

- **table:** shows the listed fields as columns, in that order. A formatting command, used at the end.
- **fields:** keeps or removes fields (`fields - _raw`). Use it early to make searches faster.
- **dedup:** keeps the first event for each unique value. With default order this is the newest. `dedup host` gives the latest event per host.
- **sort:** sorts results. `sort - count` is descending. By default it returns only 10,000 results; `sort 0 - count` removes the limit.
- **top / rare:** most or least common values, with `count` and `percent` columns. Default limit is 10.

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog properties.httpStatus>=500
| top limit=5 properties.requestUri
```

**Pitfall:** `dedup` on a large data set is slow and keeps raw events. To get "latest value per host" at scale, `stats latest(status) as status by host` is better.

</details>

<details><summary>Q5. [Intermediate] How do you extract a field with <code>rex</code>, and when should the extraction live in <code>props.conf</code> instead?</summary>

**Answer:**

`rex` uses a regex with named groups to create fields at search time:

```text
index=app_prod sourcetype=myapp:log "payment failed"
| rex field=_raw "order_id=(?<order_id>[A-Z0-9-]+)\s+reason=\"(?<reason>[^\"]+)\""
| stats count by reason
```

Useful options:

- `max_match=0` to get all matches as a multivalue field.
- `mode=sed` to change the field text: `rex field=card mode=sed "s/\d{12}(\d{4})/XXXX\1/"`.
- For JSON, use `spath` instead of regex: `spath path=error.code output=error_code`.

When an extraction is used by more than one search or dashboard, I move it to `props.conf` on the search heads (`EXTRACT-reason = reason="(?<reason>[^"]+)"`), so everyone gets the same field name and nobody copies regex around.

**Pitfall:** greedy patterns like `.*` match too much and are slow. Use `[^"]+` or `\S+`.

</details>

<details><summary>Q6. [Intermediate] When would you use <code>transaction</code> and when would you use <code>stats</code> instead?</summary>

**Answer:**

`transaction` groups related events into one result, adds `duration` and `eventcount`, and supports options like `startswith`, `endswith`, `maxspan`, and `maxpause`. It is useful when the grouping depends on event order, or when the same key is reused (for example a session ID that is reused later).

But `transaction` runs on the search head, uses a lot of memory, and silently drops open transactions when limits are reached. If the events share a unique ID, `stats` does the same job much faster:

```text
index=app_prod sourcetype=myapp:log request_id=*
| stats min(_time) as start max(_time) as end count as events values(step) as steps by request_id
| eval duration=end-start
| where duration > 5
```

**Rule I follow:** use `stats` by default. Use `transaction` only when start and end markers or order really matter, and always set `maxspan` to bound it.

</details>

<details><summary>Q7. [Intermediate] How do lookups work in Splunk, and what is the difference between a CSV lookup and a KV store lookup?</summary>

**Answer:**

A lookup adds fields to events by matching a key.

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog properties.httpStatus>=500
| rename properties.originalHost as originalHost
| lookup service_owners.csv originalHost OUTPUT service team oncall
| stats count by service team
```

- `inputlookup` reads a lookup as results. `outputlookup` writes results to a lookup, for example a scheduled search that refreshes a list of known hosts.
- **Automatic lookups** in `props.conf` (`LOOKUP-owners = ...`) run on every search for that sourcetype.
- **CSV lookup:** a file. Simple and good for small, mostly static data. The whole file is replaced on update and replicated to indexers in the knowledge bundle.
- **KV store lookup:** a collection in the KV store on the search head. Supports updates of single records and larger data sets. Good for state that changes often.

**Pitfall:** a large CSV lookup is copied to every indexer in the knowledge bundle. Very large bundles slow down or break distributed search. Use a KV store or set `local=true` where it makes sense.

</details>

<details><summary>Q8. [Intermediate] What are the caveats of <code>join</code>, and how do you avoid it?</summary>

**Answer:**

`join` runs the right side as a subsearch. By default the subsearch returns at most **50,000 rows** and runs for at most **60 seconds** (`[join]` in `limits.conf`). If it hits a limit, results are silently incomplete. It also runs on the search head, so it is slow on large data.

Avoid it in this order:

1. **stats over both data sets** with `OR` in the base search:

```text
(index=app_prod sourcetype=myapp:log level=ERROR) OR (index=cicd sourcetype=azure:devops:pipeline stage=deploy)
| eval key=coalesce(service, pipeline)
| stats values(sourcetype) as sources values(run_id) as deploy_runs count(eval(level="ERROR")) as errors by key
| where mvcount(sources) > 1
```

Here the pipeline name matches the service name, so one `stats` joins deploys and errors. The `azure:devops:pipeline` sourcetype is the example schema from Q14.

2. **lookup** when one side is a small, slowly changing list.
3. **join** only when the right side is small and I have checked the counts.

**Pitfall:** `join` defaults to an inner join and `max=1` (only the first match). Use `type=left` and `max=0` if you need all matches.

</details>

<details><summary>Q9. [Intermediate] How does a subsearch work, and what are its limits?</summary>

**Answer:**

The subsearch in square brackets runs first. Its results are turned into a search string (with `format`) and placed into the outer search.

```text
index=app_prod sourcetype=myapp:log level=ERROR
    [ search index=cicd sourcetype=azure:devops:pipeline stage=deploy result=succeeded earliest=-1h
      | rename pipeline as service
      | fields service ]
| stats count by service
```

The subsearch above becomes something like `( service="payments" ) OR ( service="orders" )`.

Default limits (`[subsearch]` in `limits.conf`): **10,000 results** and **60 seconds**. If a limit is hit, the outer search runs with an incomplete filter.

**Good use:** a small list of values that filters a large search.
**Bad use:** a subsearch that returns tens of thousands of values. Use a lookup or `stats` instead.

**How to verify:** check the Job Inspector for a "subsearch was finalized" or "truncated" message.

</details>

<details><summary>Q10. [Advanced] What is <code>tstats</code>, how do data models help, and what does <code>summariesonly</code> do?</summary>

**Answer:**

`tstats` runs statistics over the index files (`tsidx`), not the raw events. It works on:

- indexed fields (`index`, `host`, `source`, `sourcetype`, `_time`, and any custom indexed fields), and
- **accelerated data models**, where Splunk builds and stores summaries in the background.

```text
| tstats count where index=* by index, sourcetype, _time span=1h

| tstats summariesonly=true count from datamodel=Authentication
    where Authentication.action="failure" by Authentication.src, Authentication.user
| where count > 20
```

`summariesonly=true` uses only the accelerated summary. It is fastest but misses data that is not summarized yet (the last few minutes, or data outside the acceleration range). `summariesonly=false` falls back to raw data for those parts: complete, but slower.

For this to work, the data must be **CIM-compliant**: the right tags and field names (for example `action`, `src`, `user`). That is why using the official add-ons matters.

**Pitfall:** data model acceleration uses indexer CPU and disk. Accelerate only the models you use, with a sensible summary range.

</details>

<details><summary>Q11. [Intermediate] A dashboard search takes two minutes. How do you make it faster? <em>(scenario)</em></summary>

**Answer:**

1. **Open the Job Inspector.** Compare scanned events to returned results, and see which command takes the time (`command.search`, `command.stats`, `dispatch.fetch`).
2. **Narrow the base search:** add `index=` and `sourcetype=`, shorten the time range, move `| search` and `| where` filters into the base search, remove leading wildcards.
3. **Drop data early:** `fields` right after the base search.
4. **Replace heavy commands:** `transaction` and `join` become `stats`.
5. **Use accelerated data:** `tstats` on indexed fields or a data model, report acceleration, or a summary index for long time ranges.
6. **Check search mode:** "Fast" mode skips field discovery, which helps interactive searches.

Before and after:

```text
# Before
index=* "error" | search service=payments | transaction request_id | stats count

# After
index=app_prod sourcetype=myapp:log service=payments level=ERROR earliest=-4h@m
| fields request_id
| stats dc(request_id) as failed_requests
```

**Pitfall:** the search may be slow because the indexers are busy (skipped searches, blocked queues). Check the Monitoring Console before you rewrite a good search.

</details>

<details><summary>Q12. [Intermediate] Write searches for the Application Gateway 5xx error rate and latency percentiles per site.</summary>

**Answer:**

The data is the `ApplicationGatewayAccessLog` category, streamed to an Event Hub and read with `sourcetype=azure:monitor:resource`. The useful fields are `httpStatus` (status sent to the client), `serverStatus` (status from the backend), `timeTaken`, `serverResponseLatency`, `originalHost`, `requestUri`, and `clientIP`, all under `properties`. I check mine first with `| fieldsummary`.

**5xx rate per site, every 5 minutes:**

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog earliest=-60m@m
| rename properties.* as *
| eval is_5xx=if(httpStatus>=500, 1, 0)
| timechart span=5m sum(is_5xx) as errors count as total by originalHost
```

**Single error-rate table, easy to alert on:**

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog earliest=-15m@m
| rename properties.* as *
| stats count as total count(eval(httpStatus>=500)) as errors by originalHost
| eval error_rate_pct=round(errors/total*100, 2)
| where total > 100 AND error_rate_pct > 2
```

**Latency percentiles (seconds on the v2 SKU):**

```text
index=web sourcetype=azure:monitor:resource category=ApplicationGatewayAccessLog earliest=-60m@m
| rename properties.* as *
| stats perc50(timeTaken) as p50
        perc95(timeTaken) as p95
        perc99(serverResponseLatency) as backend_p99
        count by originalHost
```

**Pitfalls:**

- `timeTaken` is in seconds on the v2 SKU, but in milliseconds on the old v1 SKU.
- `timeTaken` includes network time to the client. `serverResponseLatency` is the backend only, so compare both before blaming the app.
- A 502 in `httpStatus` with no real `serverStatus` usually means the gateway could not reach a healthy backend. Check backend health, not the app logs.
- Requests from `clientIP=127.0.0.1` come from an internal gateway process. Filter them out.
- Always add a minimum request count, or one failed request out of two gives a "50% error rate". `perc95` is an approximation on large data; `exactperc95` is exact but costs more memory.

</details>

<details><summary>Q13. [Advanced] How do you detect an error spike compared to the normal baseline instead of using a fixed threshold? <em>(scenario)</em></summary>

**Answer:**

A fixed threshold either fires all night or misses problems at peak. I compare the current value with recent history.

**Option 1: moving average and standard deviation:**

```text
index=app_prod sourcetype=myapp:log level=ERROR earliest=-24h@m
| timechart span=5m count as errors
| streamstats window=72 current=false avg(errors) as baseline stdev(errors) as sd
| eval upper=baseline + 3*sd
| where errors > upper AND errors > 20
```

`window=72` with 5-minute buckets is the last 6 hours. `current=false` keeps the current bucket out of its own baseline.

**Option 2: same time last week** with `timewrap`, for traffic with a strong daily or weekly shape:

```text
index=app_prod sourcetype=myapp:log level=ERROR earliest=-14d@h
| timechart span=1h count
| timewrap 1w
```

Other built-in options are the `predict` command and the Machine Learning Toolkit, or ITSI adaptive thresholds.

**Pitfall:** a long outage pulls up the baseline, so the alert stops firing while the problem continues. Pair a baseline alert with an absolute upper limit.

</details>

<details><summary>Q14. [Intermediate] Write a search that shows CI/CD pipeline failures by pipeline and stage.</summary>

**Answer:**

Splunk does not have one standard schema for Azure DevOps or other CI tools. A common way is to send pipeline events to HEC (for example from Azure DevOps service hooks or a final pipeline step). The field names below are an example schema: `pipeline`, `stage`, `result`, `branch`, `run_id`, `duration_sec`.

```text
index=cicd sourcetype=azure:devops:pipeline earliest=-7d@d
| stats count as runs count(eval(result="failed")) as failed
        avg(duration_sec) as avg_duration by pipeline, stage
| eval failure_rate_pct=round(failed/runs*100, 1)
| sort - failed
```

**Failures on the main branch in the last day, newest first:**

```text
index=cicd sourcetype=azure:devops:pipeline result=failed branch="refs/heads/main" earliest=-24h
| table _time pipeline stage run_id requested_by
| sort - _time
```

**Deploys correlated with errors**, to answer "did the last deploy break it":

```text
(index=cicd sourcetype=azure:devops:pipeline stage=deploy result=succeeded) OR (index=app_prod level=ERROR)
| timechart span=10m count(eval(sourcetype="azure:devops:pipeline")) as deploys count(eval(level="ERROR")) as errors
```

TODO (Siva): replace the example sourcetype and field names with the ones your pipelines really send.

</details>

<details><summary>Q15. [Advanced] You suspect an Azure account or service principal was misused. Which searches do you run on Entra ID and Activity Log data? <em>(scenario)</em></summary>

**Answer:**

I work from "who signed in" to "what did they change". Entra ID logs arrive as `sourcetype=azure:monitor:aad` and the Azure Activity Log as `sourcetype=azure:monitor:activity`, both through Event Hubs.

**1. Failed sign-ins and sign-ins without MFA for a user:**

```text
index=azure_aad sourcetype=azure:monitor:aad category=SignInLogs earliest=-24h
| rename properties.* as *
| stats count(eval('status.errorCode'!=0)) as failures
        count(eval('status.errorCode'=0 AND authenticationRequirement="singleFactorAuthentication")) as no_mfa
        values(ipAddress) as src_ips values(location.countryOrRegion) as countries by userPrincipalName
| where failures > 5 OR no_mfa > 0
```

Error code `0` means success. `50126` means a wrong user name or password. Inside `eval`, the field `status.errorCode` needs single quotes, because a dot is also the string join operator.

**2. Password spray: one IP failing for many users:**

```text
index=azure_aad sourcetype=azure:monitor:aad category=SignInLogs properties.status.errorCode=50126 earliest=-1h
| rename properties.* as *
| bin _time span=10m
| stats dc(userPrincipalName) as users count by ipAddress, _time
| where users > 20
```

**3. Risky control-plane changes in the Activity Log:**

```text
index=azure_activity sourcetype=azure:monitor:activity earliest=-7d
    operationName IN ("Microsoft.Authorization/roleAssignments/write",
                      "Microsoft.Authorization/roleDefinitions/write",
                      "Microsoft.Insights/diagnosticSettings/delete",
                      "Microsoft.Network/networkSecurityGroups/securityRules/write",
                      "Microsoft.Storage/storageAccounts/listKeys/action",
                      "Microsoft.ContainerService/managedClusters/listClusterAdminCredential/action")
| eval caller=coalesce('identity.claims.http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn', 'identity.claims.appid')
| stats count values(operationName) as actions values(resultType) as results
        min(_time) as first max(_time) as last by caller, callerIpAddress
| convert ctime(first) ctime(last)
```

The caller's user name sits in a long claims field. A service principal has no user name, so the search falls back to its app ID. Search terms are not case-sensitive, so this also matches upper-case operation names. A deleted diagnostic setting is the Azure version of "someone turned off the logs".

**4. New credentials on apps and new role members in Entra ID:**

```text
index=azure_aad sourcetype=azure:monitor:aad category=AuditLogs earliest=-7d
    operationName IN ("Add service principal credentials", "Add member to role")
| table _time operationName properties.initiatedBy.user.userPrincipalName properties.targetResources{}.displayName
```

**Next steps:** disable the user or service principal, revoke its sessions, rotate its secrets (or move it to workload identity federation so there is no secret), and keep the Splunk results as evidence. Make these searches scheduled alerts afterwards.

**Pitfall:** Entra ID and Activity Log events reach the Event Hub minutes after the action, and the add-on adds some delay. Alert windows must allow for that delay, or events fall between two runs.

</details>
