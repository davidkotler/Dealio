# CloudWatch Logs Insights Reference

> Complete query syntax, functions, and production-tested patterns for every major AWS service.

---

## Syntax Fundamentals

Logs Insights uses a **pipe-delimited command pipeline**. Commands are case-insensitive and chain with `|`.

### Auto-Discovered System Fields

| Field | Description |
|-------|-------------|
| `@message` | Raw log event text |
| `@timestamp` | Event timestamp |
| `@ingestionTime` | CloudWatch receipt time |
| `@logStream` | Log stream name |
| `@log` | `account-id:log-group-name` |

**Lambda-specific:** `@requestId`, `@duration`, `@billedDuration`, `@maxMemoryUsed`, `@memorySize`, `@initDuration`, `@xrayTraceId`

**VPC Flow Logs:** `srcAddr`, `dstAddr`, `srcPort`, `dstPort`, `protocol`, `bytes`, `packets`, `action`

**JSON logs:** Up to 200 fields auto-discovered per event, 1,000 per log group. Access via dot notation (e.g., `error.message`, `requestParameters.userName`).

---

## All Commands

| Command | Purpose | Log Class |
|---------|---------|-----------|
| `fields` | Select/create computed fields | Standard + IA |
| `filter` | Boolean, comparison, regex, `like`, `in` filtering | Standard + IA |
| `stats` | Aggregate with functions; group with `by` | Standard only |
| `sort` | Order results `asc`/`desc` | Standard + IA |
| `limit` | Cap results (default 1,000; max 10,000) | Standard + IA |
| `parse` | Extract fields via glob (`*`) or regex named captures | Standard only |
| `display` | Show only specified fields (use once, at end) | Standard + IA |
| `dedup` | Remove duplicates by field(s) | Standard only |
| `pattern` | Auto-cluster logs into patterns | Standard only |
| `diff` | Compare current vs previous time period | Standard only |
| `unnest` | Flatten arrays into multiple records | Standard only |
| `unmask` | Show unmasked data-protected fields | Standard + IA |

---

## Operators

**Arithmetic:** `+`, `-`, `*`, `/`, `^`, `%`

**Comparison:** `=`, `!=`, `<`, `>`, `<=`, `>=`

**Boolean:** `and`, `or`, `not`

**String matching:**







- `like` with string or regex
- `=~` regex operator
- `in` for set membership
- `not like`



---






## Functions











### String







`strlen`, `toupper`, `tolower`, `trim`, `substr`, `replace`, `concat`, `strcontains`, `isempty`, `isblank`








### Datetime




`bin(period)` — supports `ms`, `s`, `m`, `h`, `d`, `w`, `mo`, `q`, `y`




`datefloor`, `dateceil`, `fromMillis`, `toMillis`, `now()`





### Numeric




`abs`, `ceil`, `floor`, `greatest`, `least`, `log`, `sqrt`





### IP


`isValidIp`, `isIpInSubnet`, `isIpv4InSubnet`, `isValidIpV4`, `isValidIpV6`



### JSON




`jsonParse`, `jsonStringify`, `JSON_EXTRACT()`


### General



`ispresent`, `coalesce`


### Stats Aggregation


`count(*)`, `count(field)`, `count_distinct`, `sum`, `avg`, `min`, `max`, `pct(field, N)`, `stddev`, `median`, `earliest`, `latest`, `sortsFirst`, `sortsLast`



**Critical:** Maximum 2 `stats` commands per query. The second can only reference fields from the first.



---


## Parse Command



### Glob mode (wildcard `*`)


```
parse @message "user=*, method:*, latency := *" as @user, @method, @latency

```



### Regex mode (named capture groups)

```


parse @message /user=(?<user>.*?), method:(?<method>.*?), latency := (?<latency>.*)/
```


**Rule:** Use glob for simple extraction, regex for complex patterns. Skip `parse` entirely when fields are auto-discovered JSON.



---



## Lambda Debugging Queries

### Comprehensive Performance Dashboard


```
filter @type = "REPORT"
| stats count(@type) as invocations,


        count(@initDuration) as coldStarts,

        (count(@initDuration)/count(@type))*100 as pctColdStarts,

        avg(@initDuration) as avgColdStart,

        max(@initDuration) as maxColdStart,


        avg(@duration) as avgDuration,
        max(@duration) as maxDuration,
        avg(@maxMemoryUsed) as avgMemUsed,

        max(@memorySize) as memAllocated,
        (avg(@maxMemoryUsed)/max(@memorySize))*100 as pctMemUsed
    by bin(1h)
```





### Cold Start Analysis by Function

```

filter @type = "REPORT"


| fields @memorySize / 1000000 as memorySize

| filter @message like /(?i)(Init Duration)/
| parse @message /^REPORT.*Init Duration: (?<initDuration>.*) ms.*/

| parse @log /^.*\/aws\/lambda\/(?<functionName>.*)/
| stats count() as coldStarts,
        avg(initDuration) as avgInit,
        max(initDuration) as maxInit




    by functionName, memorySize

```

### Timeout Detection


```


fields @timestamp, @requestId, @message, @logStream

| filter @message like "Task timed out"

| sort @timestamp desc

| limit 100
```

### Memory Utilization (Overprovisioning Check)





```

filter @type = "REPORT"
| stats max(@memorySize / 1024 / 1024) as provisioned_MB,
        max(@maxMemoryUsed / 1024 / 1024) as used_MB,

        (1 - max(@maxMemoryUsed) / max(@memorySize)) * 100 as overprovisioned_pct
    by @log


```




### Error Rate Calculation

```
filter @type = "REPORT"

| stats sum(strcontains(@message, "ERROR")) / count(*) * 100 as errorRate
    by bin(1h)


```





---

## API Gateway Debugging Queries


### Error Rate by Endpoint



```


stats count(*) as total,

      sum(status >= 400 and status <= 499) as clientErrors,
      sum(status >= 500) as serverErrors,
      sum(status >= 500) / count(*) * 100 as serverErrorRate
    by path


| sort serverErrorRate desc
```





### Latency by Endpoint



```
filter @message like /HTTP/
| parse @message '"*" * * *ms' as method, path, status, latency

| stats avg(latency) as avgLatency,

        pct(latency, 95) as p95Latency,
        count(*) as requests


    by path


| sort avgLatency desc

```

---



## VPC Flow Logs Queries



### Rejected SSH Traffic by Source


```

filter action = "REJECT" and protocol = 6 and dstPort = 22

| stats sum(bytes) as SSH_Traffic by srcAddr
| sort SSH_Traffic desc
| limit 10

```


### Top Traffic within a Subnet


```


filter isIpv4InSubnet(srcAddr, "192.0.2.0/24")

| stats sum(bytes) as bytesTransferred by dstAddr
| sort bytesTransferred desc
| limit 15
```



### Rejected Connections Summary


```
filter action = "REJECT"

| stats count(*) as rejections by srcAddr, dstAddr, dstPort

| sort rejections desc

| limit 20
```


---


## CloudTrail Debugging Queries


### Unauthorized API Calls


```

filter errorCode = "AccessDenied" or errorCode = "UnauthorizedAccess"
| stats count(*) as deniedCount by userIdentity.arn, eventSource, eventName
| sort deniedCount desc
| limit 20


```

### IAM User Activity

```
filter userIdentity.type = "IAMUser"

| stats count(*) by eventSource, eventName, userIdentity.userName

| sort count(*) desc

```

### Outdated TLS Usage

```

filter tlsDetails.tlsVersion in ["TLSv1", "TLSv1.1"]
| stats count(*) as numOutdatedTlsCalls by eventSource
| sort numOutdatedTlsCalls desc

```


### New IAM Users Created

```
filter eventName="CreateUser"
| fields awsRegion, requestParameters.userName, responseElements.user.arn
```



---

## Advanced Patterns

### Time-Series Binning with Percentiles

```

filter @type = "REPORT"

| stats avg(@duration) as avgDuration,
        pct(@duration, 50) as p50,
        pct(@duration, 90) as p90,
        pct(@duration, 95) as p95,
        pct(@duration, 99) as p99

    by bin(5m)
```


### Error Correlation by Time and Stream

```
filter @message like /ERROR/
| stats count(*) as errors by bin(15m), @logStream
| sort errors desc
```

### Multi-Level Aggregation (Two Stats)


```
FIELDS strlen(@message) AS message_length
| STATS sum(message_length) / 1024 / 1024 as logs_mb BY bin(5m)
| STATS max(logs_mb) AS peak_mb,
        min(logs_mb) AS min_mb,
        avg(logs_mb) AS avg_mb
```


### Regex Parsing of Unstructured Logs

```
parse @message /\[(?<level>\S+)\]\s+(?<config>\{.*\})\s+The error was: (?<exception>\S+)/
| filter level = "ERROR"
| stats count(*) as errorCount by exception
| sort errorCount desc

```

### Composite Error Analysis

```
filter @message like /(?i)error|exception|fail/
| stats count(*) as totalErrors,
        count_distinct(@logStream) as affectedStreams
    by bin(10m)
| sort totalErrors desc
```

### Dedup for Unique Values

```
fields @timestamp, @requestId, @message, @logStream
| filter @type = "REPORT" and @duration > 1000
| sort @timestamp desc
| dedup @requestId
| limit 20
```

### Auto-Cluster with Pattern

```
pattern @message
| sort count desc
| limit 20
```

### Field Existence Check

```
fields @timestamp, @message, errorCode
| filter errorCode != ''
| sort @timestamp desc
```

---

## Efficiency Rules

1. **Select only necessary log groups** — never "all log groups"
2. **Narrow time ranges aggressively** — $0.005/GB scanned
3. **Place `filter` before `stats`** — reduces data processed
4. **Use field indexes** on frequently queried fields (Standard class only)
5. **Always use `limit`** on exploratory queries
6. **Skip `parse` for JSON logs** — fields are auto-discovered
7. **Dashboard widgets trigger queries on refresh** — avoid high-frequency refreshes

---

## Key Limits

| Limit | Value |
|-------|-------|
| Query timeout | 60 minutes |
| Max log groups per query | 50 |
| Max results | 10,000 |
| Max `stats` commands | 2 per query |
| Query results retention | 7 days |
| Max saved queries per region | 1,000 |
| Standard class concurrent queries | 30 |
| Infrequent Access concurrent queries | 5 |
| Auto-discovered fields per event | 200 |
| Auto-discovered fields per log group | 1,000 |
