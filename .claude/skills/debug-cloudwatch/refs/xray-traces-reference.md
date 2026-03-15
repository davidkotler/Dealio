# X-Ray Traces & Transaction Search Reference

> Complete X-Ray filter expression syntax, Transaction Search span queries, annotation patterns, and CLI usage.

---

## X-Ray Filter Expression Syntax

Filter expressions use `keyword operator value` syntax with `AND`, `OR` for compound expressions.

### Boolean Keywords (direct or with `= true`/`= false`)

| Keyword | Meaning |
|---------|---------|
| `ok` | Response 2xx |
| `error` | Response 4xx |
| `fault` | Response 5xx |
| `throttle` | Response 429 |
| `partial` | Incomplete segments |
| `root` | Entry point service |

### Number Keywords (operators: `=`, `!=`, `<`, `<=`, `>`, `>=`)

| Keyword | Meaning |
|---------|---------|
| `responsetime` | Server response time |
| `duration` | Total request duration including downstream |
| `http.status` | HTTP status code |
| `coverage` | Used with rootcause filters |

### String Keywords (operators: `=`, `!=`, `CONTAINS`, `BEGINSWITH`, `ENDSWITH`)

`http.url`, `http.method`, `http.useragent`, `http.clientip`, `http.statuscode`, `user`, `name`, `type`, `message`, `availabilityzone`, `instance.id`, `resource.arn`

### Complex Keywords

```
# Service-scoped filter
service("name") { filter }

# Edge (connection) filter
edge("source", "dest") { filter }

# Annotation query
annotation[key]

# Precise service identification
id(name: "svc", type: "AWS::Lambda::Function")
id(account.id: "123456789012")

# Root cause analysis
rootcause.fault.service { filter }
rootcause.responsetime.entity { filter }

# Group reference
group.name = "group-name"
```

---

## Production Filter Expression Examples

### Basic Filters







```
# All faults
fault

# All errors
error

# Traces without errors
!error

# Slow responses
responsetime > 5



# Duration range

duration >= 5 AND duration <= 8

```



### Service Filters

```
# All traces hitting a service
service("api.example.com")

# Service with errors
service("api.example.com") { error }

# Service with high latency
service("order-service") { responsetime > 3 }


# By service type

service(id(type: "AWS::Lambda::Function")) { error }


# By name AND type (avoids Lambda node duplication)
service(id(name: "my-function", type: "AWS::Lambda::Function")) { error }



# By account ID


service(id(account.id: "123456789012")) { fault }
```



### Edge Filters


```
# Faults between two services
edge("frontend", "payment-service") { fault }


# Edge with latency
edge("api-gateway", "order-service") { responsetime > 2 }

```

### Annotation Filters

```
# Exact string value
annotation.customer_tier = "enterprise"


# Numeric comparison
annotation.order_value > 1000


# Boolean
annotation.is_premium = true

# Annotation existence

annotation.age

# Annotation absence
!annotation.age



# Combined with other filters
annotation.customer_tier = "enterprise" AND responsetime > 2



# Annotation on a specific service
service("checkout") { annotation.order_value > 1000 }


# Environment-specific faults


annotation[environment] = "staging" AND fault = true
```


### HTTP Filters



```
# By URL pattern
http.url CONTAINS "/api/v2/checkout"


# By method


http.method = "POST"

# Combined HTTP + error

http.method = "POST" AND http.statuscode >= 500



# URL present and slow
http.url AND responsetime > 2
```


### Root Cause Analysis



```
# DynamoDB root cause faults
rootcause.fault.service { type = "AWS::DynamoDB" }


# Remote entity responsible for >70% of response time


rootcause.responsetime.entity { remote AND coverage > 0.7 }
```

### User Filters

```
# User experiencing errors


user = "user-123" AND (error OR fault)

# Group + user
group.name = "high_response_time" AND user = "Alice"
```

### Complex Compound


```
# POST checkout with errors

http.method = "POST" AND http.url CONTAINS "/checkout" AND error

# Lambda faults excluding throttles
service(id(name: "process-order", type: "AWS::Lambda::Function")) { fault }
  AND !throttle

```


---


## Annotations vs Metadata

| | Annotations | Metadata |
|--|-------------|----------|

| **Indexed** | Yes — searchable via `annotation[key]` | No — not searchable |

| **Types** | String, number, boolean | Any (objects, lists, etc.) |

| **Limit** | 50 per trace | Unlimited |

| **Use for** | Customer IDs, environment, feature flags | Full request bodies, stack traces |

### Promoting OTEL Attributes to Annotations

Three methods:

1. `indexed_attributes` in ADOT collector config


2. `index_all_attributes: true` in collector (expensive)

3. `aws.xray.annotations` attribute on the span itself


```python
span.set_attribute("aws.xray.annotations", ["order.id", "customer.tier", "environment"])
```


---



## Transaction Search (Span Queries)




Transaction Search stores spans in the `aws/spans` log group using OpenTelemetry semantic convention format. Queryable via CloudWatch Logs Insights.

### Key Span Fields

| Field | Description |


|-------|-------------|
| `traceId` | Trace identifier |


| `durationNano` | Span duration in nanoseconds |


| `attributes.aws.local.service` | Service name |

| `attributes.aws.local.operation` | Operation name |
| `attributes.aws.local.environment` | Environment |
| `attributes.http.response.status_code` | HTTP status code |

| `attributes.db.system` | Database type |
| `attributes.db.statement` | Database query |


| `events.name` | Span event name |
| `events.attributes.*` | Span event attributes |






### Slow Database Queries

```
STATS pct(durationNano, 99) as p99 by attributes.db.statement
| SORT p99 ASC

| LIMIT 5
| DISPLAY p99, attributes.db.statement


```



### Top Services with 500 Errors



```
FILTER `attributes.http.response.status_code` >= 500
| STATS count(*) as count by attributes.aws.local.service as service
| SORT count ASC
| LIMIT 5

| DISPLAY count, service
```



### Error Breakdown for a Service


```

FILTER attributes.aws.local.service = "checkout-service"

  and attributes.http.status_code >= 400
| STATS count() as error_count
    by attributes.http.status_code,
       attributes.aws.local.operation
| SORT error_count DESC

| LIMIT 20
```



### Latency Analysis by Operation

```
FILTER attributes.aws.local.service = "order-service"

| STATS avg(durationNano) / 1000000 as avg_ms,

        pct(durationNano / 1000000, 95) as p95_ms,
        pct(durationNano / 1000000, 99) as p99_ms
    by attributes.aws.local.operation
| SORT p99_ms DESC
```


### Custom Business Attribute Search


```
FILTER attributes.order_id = "ORD-12345"
| fields @timestamp, traceId, attributes.aws.local.service, durationNano
```


### Exception Analysis

```
FILTER events.name = "exception"
| STATS count() as exceptions
    by attributes.aws.local.service, events.attributes.exception.type
| SORT exceptions DESC

```

### High-Value Transactions

```
FILTER attributes.order_value > 1000
| STATS count() as count, avg(durationNano / 1000000) as avg_ms
    by attributes.aws.local.service
| SORT count DESC

```

---

## CLI Usage

### Get Trace Summaries with Filter

```bash
EPOCH=$(date +%s)
aws xray get-trace-summaries \
  --start-time $(($EPOCH-3600)) \
  --end-time $EPOCH \
  --filter-expression 'service("my-api") { fault } AND responsetime > 2'
```

### Get Full Trace by ID

```bash
aws xray batch-get-traces \
  --trace-ids "1-67890abc-def012345678901234567890"
```

---

## X-Ray Groups

Groups collect traces matching a filter, generating dedicated service graphs and CloudWatch metrics:

```yaml
Type: AWS::XRay::Group
Properties:
  GroupName: HighLatencyErrors
  FilterExpression: "fault = true AND responsetime >= 5"
  InsightsConfiguration:
    InsightsEnabled: true
    NotificationsEnabled: true
```

---

## Sampling

- **Default:** 1 request/second reservoir + 5% fixed rate
- Use `awsproxy` extension for remote sampling via X-Ray
- **Never** use `TraceIdRatioBased` sampler with X-Ray ID Generator
- Sampling decisions propagate downstream from root service
