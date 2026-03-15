# CloudWatch Metrics Insights Reference

> SQL-based metric queries, Metric Math expressions, EMF patterns, and service-specific debugging queries.

---

## Metrics Insights SQL Syntax

```sql
SELECT FUNCTION(metricName)
FROM namespace | SCHEMA(namespace [, labelKey [, ...]])
[ WHERE labelKey = 'labelValue' [AND ...] ]
[ GROUP BY labelKey [, ...] ]
[ ORDER BY FUNCTION() [DESC | ASC] ]
[ LIMIT number ]
```

### Aggregate Functions

`AVG()`, `COUNT()`, `MAX()`, `MIN()`, `SUM()`, `RATE()`, `RUNNING_SUM()`, `SAMPLE_COUNT()`

### SCHEMA Function

`SCHEMA()` constrains queries to metrics with **exactly** the specified dimensions:

```sql
-- Only metrics with exactly the InstanceId dimension
SELECT AVG(CPUUtilization) FROM SCHEMA("AWS/EC2", InstanceId)

-- Metrics with exactly two dimensions
SELECT SUM(RequestCount) FROM SCHEMA("AWS/ApplicationELB", LoadBalancer, AvailabilityZone)
```

Without `SCHEMA`, queries match all dimension combinations.

### Tag-Based Querying

```sql
SELECT MAX(CPUUtilization) FROM SCHEMA("AWS/EC2") WHERE tag.env='prod'
SELECT MAX(CPUUtilization) FROM SCHEMA("AWS/EC2") GROUP BY tag.env
SELECT AVG(CPUUtilization) FROM "AWS/EC2" GROUP BY tag."aws:cloudformation:stack-name"
```

### Cross-Account Querying

```sql
SELECT AVG(CpuUtilization) FROM "AWS/EC2" WHERE AWS.AccountId = '123456789012'
SELECT AVG(CpuUtilization) FROM "AWS/EC2" GROUP BY AWS.AccountId, InstanceType
SELECT AVG(CpuUtilization) FROM "AWS/EC2" WHERE AWS.AccountId = CURRENT_ACCOUNT_ID()
```

---

## Service-Specific Debugging Queries

### EC2

```sql
-- Top 10 instances by CPU
SELECT MAX(CPUUtilization)
FROM SCHEMA("AWS/EC2", InstanceId)
GROUP BY InstanceId
ORDER BY MAX() DESC
LIMIT 10

-- Filter by production tag
SELECT MAX(CPUUtilization)
FROM SCHEMA("AWS/EC2")
WHERE tag.env='prod'
```

### Lambda

```sql
-- Top functions by errors
SELECT SUM(Errors)
FROM SCHEMA("AWS/Lambda", FunctionName)
GROUP BY FunctionName
ORDER BY SUM() DESC
LIMIT 10

-- Slowest functions
SELECT AVG(Duration)
FROM SCHEMA("AWS/Lambda", FunctionName)
GROUP BY FunctionName
ORDER BY MAX() DESC
LIMIT 10

-- Concurrent executions
SELECT AVG(ConcurrentExecutions) FROM "AWS/Lambda"
```

### ECS / Container Insights

```sql
-- CPU by cluster and service
SELECT AVG(CPUUtilization)
FROM SCHEMA("AWS/ECS", ClusterName, ServiceName)
GROUP BY ClusterName, ServiceName
ORDER BY AVG() DESC
LIMIT 10

-- Running tasks
SELECT AVG(RunningTaskCount)
FROM SCHEMA("ECS/ContainerInsights", ClusterName, ServiceName)
GROUP BY ClusterName, ServiceName
ORDER BY AVG() DESC
```

### Application Load Balancer

```sql
-- Active connections by ALB
SELECT MAX(ActiveConnectionCount)
FROM SCHEMA("AWS/ApplicationELB", LoadBalancer)
GROUP BY LoadBalancer
ORDER BY SUM() DESC
LIMIT 10

-- Request count by AZ
SELECT SUM(RequestCount)
FROM SCHEMA("AWS/ApplicationELB", LoadBalancer, AvailabilityZone)
WHERE LoadBalancer = 'app/load-balancer-1'
GROUP BY AvailabilityZone
```

### DynamoDB

```sql
-- Tables with most user errors
SELECT SUM(UserErrors)
FROM SCHEMA("AWS/DynamoDB", TableName)
GROUP BY TableName
ORDER BY MAX() DESC
LIMIT 10

-- Tables returning most data
SELECT SUM(ReturnedBytes)
FROM SCHEMA("AWS/DynamoDB", TableName)
GROUP BY TableName
ORDER BY MAX() DESC
LIMIT 10
```

### SQS

```sql
-- Queue message age (consumer lag)
SELECT AVG(ApproximateAgeOfOldestMessage)
FROM SCHEMA("AWS/SQS", QueueName)
GROUP BY QueueName
ORDER BY AVG() DESC
LIMIT 10
```

### Kinesis

```sql
-- Iterator age (consumer lag)
SELECT MAX("GetRecords.IteratorAgeMilliseconds")
FROM SCHEMA("AWS/Kinesis", StreamName)
GROUP BY StreamName
ORDER BY MAX() DESC
LIMIT 10
```

---

## Metric Math Expressions

Metric Math operates on: **S** (scalar), **TS** (single time series), **TS[]** (array). Expression IDs must start with a lowercase letter.

### Core Functions

| Function | Description | Example |
|----------|-------------|---------|
| `METRICS()` | All graphed metrics as TS[] | `SUM(METRICS("errors"))` |
| `FILL(m, value)` | Fill missing data (0, REPEAT, LINEAR) | `FILL(m1, 0)` |
| `SEARCH('{ns, dim}', stat, period)` | Dynamic metric discovery | See below |
| `IF(cond, true, false)` | Conditional logic | `IF(m1 > 100, 1, 0)` |
| `ANOMALY_DETECTION_BAND(m, n)` | ML-based expected range | `ANOMALY_DETECTION_BAND(m1, 2)` |
| `TIME_SERIES(scalar)` | Scalar to horizontal line | `TIME_SERIES(99.9)` |
| `RATE(m)` | Per-second rate of change | `RATE(m1)` |
| `DIFF(m)` | Difference from previous value | `DIFF(m1)` |
| `RUNNING_SUM(m)` | Cumulative sum | `RUNNING_SUM(m1)` |
| `PERIOD(m)` | Period in seconds | `m1/PERIOD(m1)` |
| `SORT(arr, func, dir, n)` | Sort and slice | `SORT(METRICS(), AVG, DESC, 10)` |

### Production Metric Math Patterns

```
# Lambda error rate (m1=Errors Sum, m2=Invocations Sum)
(m1/m2)*100

# ALB 5xx error rate (m1=HTTPCode_ELB_5XX_Count, m2=RequestCount)
(m1/m2)*100

# SLA availability with threshold line
e1 = (1 - m1/m2) * 100
e2 = TIME_SERIES(99.9)

# Show only anomalous values
IF(m1 > LAST(ANOMALY_DETECTION_BAND(m1)), m1)
```

### SEARCH Expressions (Dynamic Dashboards)

**Cannot be used in alarms.**

```
-- All EC2 CPU per instance
SEARCH('{AWS/EC2,InstanceId} MetricName="CPUUtilization"', 'Average')

-- All Lambda errors
SEARCH('{AWS/Lambda, FunctionName} MetricName="Errors"', 'Sum')

-- Combine SEARCH with math
SUM(SEARCH('{AWS/Lambda, FunctionName} MetricName="Errors"', 'Sum'))
```

---

## Embedded Metric Format (EMF)

EMF instructs CloudWatch Logs to auto-extract metrics from structured JSON:

```json
{
  "_aws": {
    "Timestamp": 1574109732004,
    "CloudWatchMetrics": [{
      "Namespace": "MyApp/OrderService",
      "Dimensions": [["ServiceName", "Environment"]],
      "Metrics": [
        {"Name": "ProcessingLatency", "Unit": "Milliseconds", "StorageResolution": 60},
        {"Name": "OrderCount", "Unit": "Count"}
      ]
    }]
  },
  "ServiceName": "OrderAPI",
  "Environment": "Production",
  "ProcessingLatency": 157,
  "OrderCount": 1,
  "RequestId": "989ffbf8-9ace-4817-a57c-e4dd734019ee"
}
```

**Critical:** Never use high-cardinality values (requestId, userId) as dimensions — each unique combination creates a separate billable custom metric. Use `setProperty()` for high-cardinality context (queryable via Logs Insights, not billed as dimensions).

### EMF Limits

- Max 100 metric values per key
- Max 30 dimensions per metric
- Max 1 MB document

---

## Metrics Concepts

### Resolution and Retention

| Resolution | Retention |
|-----------|-----------|
| 1-second (high-res) | 3 hours |
| 60-second (standard) | 15 days |
| 5-minute (aggregated) | 63 days |
| 1-hour (aggregated) | 455 days (15 months) |

### Limits

- Query range: most recent 3 hours (extended to 2 weeks with larger periods)
- Max 10,000 metrics per query
- Max 500 time series returned
- Max 30 dimensions per metric
- Console queries are free
