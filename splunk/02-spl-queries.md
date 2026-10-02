# Splunk: SPL Queries

> SPL fundamentals and the commands interviewers ask about, search performance best practices, and practical DevOps queries for 5xx rates, latency, error spikes, failed logins, CI/CD failures, and AWS CloudTrail.

## Key Concepts

### How a Search Runs

An SPL search is a pipeline. The first part (before the first `|`) is the **base search**: it picks events from indexes using the time range, indexed fields, and keywords. Each command after a `|` works on the output of the one before it.

```text
index=web sourcetype=aws:elb:accesslogs earliest=-60m@m latest=now elb_status_code>=500
| stats count by target_group_arn
| sort - count
```

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
index=web sourcetype=aws:elb:accesslogs
| eval is_error=if(elb_status_code>=500, 1, 0)
| where request_processing_time > target_processing_time
```

In `where` and `eval`, a field name with special characters (like `userIdentity.arn` in JSON) must be in single quotes: `where 'userIdentity.type'="Root"`. Double quotes mean a string.

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
index=web sourcetype=aws:elb:accesslogs elb_status_code>=500
| top limit=5 request_url
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
index=web sourcetype=aws:elb:accesslogs elb_status_code>=500
| lookup service_owners.csv target_group OUTPUT service team oncall
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
(index=app_prod sourcetype=myapp:log) OR (index=aws_cloudtrail sourcetype=aws:cloudtrail)
| eval key=coalesce(request_id, requestID)
| stats values(sourcetype) as sources values(eventName) as api values(level) as level by key
| where mvcount(sources) > 1
```

2. **lookup** when one side is a small, slowly changing list.
3. **join** only when the right side is small and I have checked the counts.

**Pitfall:** `join` defaults to an inner join and `max=1` (only the first match). Use `type=left` and `max=0` if you need all matches.

</details>

<details><summary>Q9. [Intermediate] How does a subsearch work, and what are its limits?</summary>

**Answer:**

The subsearch in square brackets runs first. Its results are turned into a search string (with `format`) and placed into the outer search.

```text
index=app_prod sourcetype=myapp:log level=ERROR
    [ search index=aws_cloudtrail sourcetype=aws:cloudtrail eventName=UpdateService earliest=-1h
      | rename requestParameters.service as service
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

<details><summary>Q12. [Intermediate] Write searches for the ALB 5xx error rate and latency percentiles per target group.</summary>

**Answer:**

Field names below follow the Splunk Add-on for AWS ALB access log sourcetype. I check mine first with `| fieldsummary`.

**5xx rate per target group, every 5 minutes:**

```text
index=web sourcetype=aws:elb:accesslogs earliest=-60m@m
| eval is_5xx=if(elb_status_code>=500, 1, 0)
| timechart span=5m sum(is_5xx) as errors count as total by target_group_arn
```

**Single error-rate table, easy to alert on:**

```text
index=web sourcetype=aws:elb:accesslogs earliest=-15m@m
| stats count as total count(eval(elb_status_code>=500)) as errors by target_group_arn
| eval error_rate_pct=round(errors/total*100, 2)
| where total > 100 AND error_rate_pct > 2
```

**Latency percentiles (seconds):**

```text
index=web sourcetype=aws:elb:accesslogs earliest=-60m@m target_processing_time>=0
| stats perc50(target_processing_time) as p50
        perc95(target_processing_time) as p95
        perc99(target_processing_time) as p99
        count by target_group_arn
```

**Pitfalls:** ALB writes `-1` for processing time when the target did not respond, so filter it out. Always add a minimum request count, or one failed request out of two gives a "50% error rate". `perc95` is an approximation on large data; `exactperc95` is exact but costs more memory.

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

<details><summary>Q15. [Advanced] You suspect AWS credentials were misused. Which searches do you run on CloudTrail and login data? <em>(scenario)</em></summary>

**Answer:**

I work from "who logged in" to "what did they change".

**1. Failed console logins and logins without MFA:**

```text
index=aws_cloudtrail sourcetype=aws:cloudtrail eventName=ConsoleLogin earliest=-24h
| stats count(eval('responseElements.ConsoleLogin'="Failure")) as failures
        count(eval('additionalEventData.MFAUsed'="No")) as no_mfa
        values(sourceIPAddress) as src_ips by userIdentity.arn
| where failures > 5 OR no_mfa > 0
```

**2. SSH brute force on Linux hosts:**

```text
index=os sourcetype=linux_secure "Failed password" earliest=-1h
| rex "Failed password for (invalid user )?(?<user>\S+) from (?<src_ip>\S+)"
| stats count dc(user) as users by src_ip, host
| where count > 20
```

**3. Risky API calls by that identity:**

```text
index=aws_cloudtrail sourcetype=aws:cloudtrail earliest=-7d
    eventName IN (StopLogging, DeleteTrail, CreateAccessKey, CreateUser, AttachUserPolicy,
                  PutUserPolicy, PutBucketPolicy, AuthorizeSecurityGroupIngress, DeleteFlowLogs)
| stats count values(eventName) as actions values(awsRegion) as regions
        min(_time) as first max(_time) as last by userIdentity.arn, sourceIPAddress
| convert ctime(first) ctime(last)
```

**4. Access denied bursts, which often mean someone is probing permissions:**

```text
index=aws_cloudtrail sourcetype=aws:cloudtrail errorCode IN (AccessDenied, UnauthorizedOperation) earliest=-24h
| stats count dc(eventName) as distinct_apis by userIdentity.arn, sourceIPAddress
| where distinct_apis > 10
```

Also check root usage: `'userIdentity.type'="Root"` should almost never appear.

**Next steps:** disable the access key, revoke sessions, and keep the Splunk results as evidence. Make these searches scheduled alerts afterwards.

**Pitfall:** CloudTrail events usually arrive several minutes after the API call, and S3/SQS polling adds more delay. Alert windows must allow for that delay, or events fall between two runs.

</details>
