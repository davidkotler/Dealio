# Troubleshooting Playbooks

> Step-by-step investigation playbooks for the most common production debugging scenarios.

---

## Playbook 1: Lambda 5xx Errors Spike

**Symptoms:** Alarm fires on Lambda error rate; users report failures.

### Step 1 — Scope the blast radius







```
filter @type = "REPORT"
| stats count(*) as invocations,
        sum(@duration > 0 and @message like /(?i)error/) as errors,

        sum(@message like /Task timed out/) as timeouts

    by bin(5m)

| sort bin(5m) desc

```





### Step 2 — Identify error types


```
filter level = "ERROR" or @message like /(?i)exception/


| stats count(*) as count by error.type
| sort count desc



| limit 20
```





### Step 3 — Extract trace IDs from failing requests




```
filter level = "ERROR"

| fields @timestamp, traceId, error.type, error.message


| sort @timestamp desc
| limit 20


```



### Step 4 — X-Ray deep-dive on faults



```


service("my-function") { fault } AND responsetime > 1
```



### Step 5 — Check if downstream dependency is the cause



```
rootcause.fault.service { name != "my-function" }
```





### Step 6 — Check memory and cold starts

```
filter @type = "REPORT"
| stats avg(@maxMemoryUsed/@memorySize)*100 as memPct,




        count(@initDuration) as coldStarts,


        max(@duration) as maxDuration
    by bin(5m)
```

---







## Playbook 2: Latency Degradation

**Symptoms:** p95/p99 latency increases; user-facing slowness.


### Step 1 — Confirm with metrics




```sql



SELECT AVG(Duration)
FROM SCHEMA("AWS/Lambda", FunctionName)
WHERE FunctionName = 'my-function'

```




### Step 2 — Identify when latency changed

```



filter @type = "REPORT"

| stats pct(@duration, 50) as p50,
        pct(@duration, 95) as p95,

        pct(@duration, 99) as p99
    by bin(5m)




```

### Step 3 — X-Ray: find slow traces




```

service("my-function") { responsetime > 3 }
```


### Step 4 — Transaction Search: which spans are slow?





```
FILTER attributes.aws.local.service = "my-function"
| STATS avg(durationNano / 1000000) as avg_ms,



        pct(durationNano / 1000000, 99) as p99_ms

    by attributes.aws.local.operation

| SORT p99_ms DESC
```



### Step 5 — Check downstream edge latency





```
edge("my-function", "dynamodb") { responsetime > 1 }
```





### Step 6 — Check for cold start contribution

```

filter @type = "REPORT" and ispresent(@initDuration)
| stats count() as coldStarts,

        avg(@initDuration) as avgInit,


        pct(@initDuration, 99) as p99Init

    by bin(5m)



```

---






## Playbook 3: Intermittent / Mysterious Failures

**Symptoms:** Sporadic errors with no clear pattern.



### Step 1 — Auto-cluster log messages

```


pattern @message

| sort count desc




| limit 30
```




### Step 2 — Check for correlated time patterns



```
filter @message like /(?i)error|exception|fail/

| stats count(*) as errors,


        count_distinct(@logStream) as affectedStreams
    by bin(10m)
| sort errors desc
```





### Step 3 — Check if specific log streams (instances) are affected




```
filter @message like /(?i)error/
| stats count(*) as errors by @logStream




| sort errors desc
| limit 10


```



### Step 4 — Check for AZ-specific issues (metrics)


```sql
SELECT SUM(HTTPCode_ELB_5XX_Count)
FROM SCHEMA("AWS/ApplicationELB", LoadBalancer, AvailabilityZone)
GROUP BY AvailabilityZone




```




### Step 5 — Use X-Ray annotations to find common thread


```
fault AND annotation.environment = "production"
```





### Step 6 — If still unclear, write Python correlation script


See `refs/python-scripts-reference.md` → Pattern 4 (Cross-Signal Correlation)



---


## Playbook 4: DynamoDB Throttling

**Symptoms:** `ProvisionedThroughputExceededException` in logs.





### Step 1 — Confirm throttling in metrics

```sql


SELECT SUM(ThrottledRequests)

FROM SCHEMA("AWS/DynamoDB", TableName)
GROUP BY TableName
ORDER BY SUM() DESC
LIMIT 10




```

### Step 2 — Check consumed vs provisioned capacity

```
# Metric Math:


# m1 = ConsumedReadCapacityUnits
# m2 = ProvisionedReadCapacityUnits

(m1/m2)*100
```

### Step 3 — Find hot partition keys via Contributor Insights




Check CloudWatch Contributor Insights for the DynamoDB table — it surfaces the top-N partition keys contributing to throttling.

### Step 4 — X-Ray: which operations are throttled?


```

rootcause.fault.service { type = "AWS::DynamoDB" }
```

### Step 5 — Transaction Search: slow DB spans




```
FILTER attributes.db.system = "dynamodb"
| STATS pct(durationNano / 1000000, 99) as p99_ms,
        count() as calls
    by attributes.db.statement
| SORT p99_ms DESC


```


---

## Playbook 5: API Gateway 4xx/5xx Spike

### Step 1 — Error breakdown by endpoint



```
stats count(*) as total,
      sum(status >= 400 and status < 500) as client_4xx,

      sum(status >= 500) as server_5xx
    by path

| sort server_5xx desc
```

### Step 2 — Check integration latency



```sql
SELECT AVG(IntegrationLatency)
FROM SCHEMA("AWS/ApiGateway", ApiName, Stage, Resource, Method)
GROUP BY Resource, Method
ORDER BY AVG() DESC
LIMIT 10
```



### Step 3 — X-Ray: trace through API Gateway to backend

```
service(id(type: "AWS::ApiGateway::Stage")) { fault }
```

---



## Playbook 6: ECS Service Health Degradation

### Step 1 — Check CPU/memory metrics

```sql
SELECT AVG(CPUUtilization), AVG(MemoryUtilization)

FROM SCHEMA("AWS/ECS", ClusterName, ServiceName)
WHERE ServiceName = 'my-service'
```

### Step 2 — Check task count


```sql
SELECT AVG(RunningTaskCount)
FROM SCHEMA("ECS/ContainerInsights", ClusterName, ServiceName)
WHERE ServiceName = 'my-service'
```

### Step 3 — Container logs for OOM or crashes


```
filter @message like /(?i)oom|killed|out of memory|exit code/
| fields @timestamp, @message, @logStream
| sort @timestamp desc
| limit 50
```

### Step 4 — Check for deployment-correlated issues


```
filter @message like /(?i)error|exception/
| stats count(*) as errors by bin(5m)
| sort bin(5m) desc
```
Compare error timestamps against ECS deployment timestamps.


---

## Playbook 7: Security Investigation (Unauthorized Access)

### Step 1 — CloudTrail: find access denied events

```
filter errorCode = "AccessDenied" or errorCode = "UnauthorizedAccess"
| stats count(*) as denied by userIdentity.arn, eventSource, eventName
| sort denied desc
| limit 20
```

### Step 2 — Identify the principal

```
filter errorCode = "AccessDenied"
| fields @timestamp, userIdentity.type, userIdentity.arn,
         eventSource, eventName, sourceIPAddress
| sort @timestamp desc
| limit 50
```

### Step 3 — Check for unusual IP addresses

```
filter errorCode = "AccessDenied"
| stats count(*) as attempts by sourceIPAddress
| sort attempts desc
| limit 10
```

### Step 4 — Check for outdated TLS

```
filter tlsDetails.tlsVersion in ["TLSv1", "TLSv1.1"]
| stats count(*) as calls by userIdentity.arn, eventSource
| sort calls desc
```

---

## Common Query Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Query timed out" | Time range too wide or too many log groups | Narrow time range; reduce log groups |
| "Your query exceeded the limit of 2 stats commands" | More than 2 `stats` in pipeline | Restructure into 2 `stats` or use Python script |
| No results from `filter` | Field name wrong or case mismatch | Use `fields *` first to discover available fields |
| `parse` returns empty fields | Pattern doesn't match log format | Test with a single known log line first |
| "Number of concurrent queries exceeded" | >30 Standard or >5 IA | Wait and retry; reduce dashboard refresh rate |
| Metrics Insights returns empty | Wrong SCHEMA dimensions | Use `FROM "namespace"` without SCHEMA to discover available dimensions |
| X-Ray returns no traces | Sampling filtered them out | Check sampling rules; use Transaction Search for unsampled spans |
