# Python Scripts Reference for CloudWatch Debugging

> boto3 patterns for multi-step analysis, cross-signal correlation, automated triage, and report generation.

---

## When to Use Python Scripts

| Scenario | Why Not Direct Query |
|----------|---------------------|
| Multi-step analysis | Query results feed subsequent queries |
| Cross-signal correlation | Combine logs + metrics + traces |
| Large result sets | >10,000 results need pagination |
| Time-series comparison | Compare two time windows programmatically |
| Automated triage | Reusable diagnostic runbooks |
| Report generation | Structured output with data from all signals |

---

## Setup

```python
import boto3
import json
import time
from datetime import datetime, timedelta, timezone

logs_client = boto3.client('logs', region_name='us-east-1')
cw_client = boto3.client('cloudwatch', region_name='us-east-1')
xray_client = boto3.client('xray', region_name='us-east-1')
```

---

## Pattern 1: Logs Insights Query with Wait

```python
def run_logs_query(log_groups: list[str], query: str, hours_back: int = 1) -> list[dict]:
    """Run a Logs Insights query and wait for results."""
    end_time = int(datetime.now(timezone.utc).timestamp())
    start_time = end_time - (hours_back * 3600)

    response = logs_client.start_query(
        logGroupNames=log_groups,
        startTime=start_time,
        endTime=end_time,
        queryString=query,
        limit=10000,
    )
    query_id = response['queryId']

    # Poll for completion
    while True:
        result = logs_client.get_query_results(queryId=query_id)
        if result['status'] in ('Complete', 'Failed', 'Cancelled', 'Timeout'):
            break
        time.sleep(1)

    if result['status'] != 'Complete':
        raise RuntimeError(f"Query {result['status']}: check query syntax and log groups")

    # Convert to list of dicts
    rows = []
    for row in result['results']:
        rows.append({field['field']: field['value'] for field in row})
    return rows
```

---

## Pattern 2: Extract Trace IDs from Logs, Then Fetch Traces

```python
def investigate_errors(log_groups: list[str], hours_back: int = 1) -> dict:
    """Find errors in logs, extract trace IDs, fetch full traces from X-Ray."""

    # Step 1: Query error logs for trace IDs
    error_logs = run_logs_query(
        log_groups=log_groups,
        query="""
            filter level = "ERROR"
            | fields @timestamp, message, traceId, error.type
            | sort @timestamp desc
            | limit 100
        """,
        hours_back=hours_back,
    )

    # Step 2: Extract unique trace IDs
    trace_ids = list({
        row['traceId'] for row in error_logs
        if 'traceId' in row and row['traceId']
    })

    if not trace_ids:
        return {"errors": error_logs, "traces": [], "summary": "No trace IDs found in error logs"}

    # Step 3: Batch-get traces from X-Ray (max 5 per call)
    traces = []
    for i in range(0, len(trace_ids), 5):
        batch = trace_ids[i:i+5]
        response = xray_client.batch_get_traces(TraceIds=batch)
        traces.extend(response.get('Traces', []))

    # Step 4: Analyze traces for root cause
    fault_services = []
    for trace in traces:
        for segment in trace.get('Segments', []):
            doc = json.loads(segment['Document'])
            if doc.get('fault'):
                fault_services.append({
                    'service': doc.get('name'),
                    'trace_id': doc.get('trace_id'),
                    'error': doc.get('cause', {}).get('message', 'Unknown'),
                    'duration': doc.get('end_time', 0) - doc.get('start_time', 0),
                })

    return {
        "error_count": len(error_logs),
        "unique_traces": len(trace_ids),
        "fault_services": fault_services,
        "errors": error_logs[:10],  # Sample
    }
```

---

## Pattern 3: Get Metrics for a Time Window

```python
def get_metric_timeseries(
    namespace: str,
    metric_name: str,
    dimensions: list[dict],
    stat: str = 'Average',
    period: int = 300,
    hours_back: int = 1,
) -> list[dict]:
    """Fetch a metric time series from CloudWatch."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)

    response = cw_client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=[stat],
    )

    datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
    return [
        {'timestamp': dp['Timestamp'].isoformat(), 'value': dp[stat]}
        for dp in datapoints
    ]


# Example: Lambda error rate
errors = get_metric_timeseries(
    namespace='AWS/Lambda',
    metric_name='Errors',
    dimensions=[{'Name': 'FunctionName', 'Value': 'my-function'}],
    stat='Sum',
    hours_back=6,
)
```

---

## Pattern 4: Cross-Signal Correlation

```python
def correlate_latency_with_errors(
    service_name: str,
    log_groups: list[str],
    hours_back: int = 6,
) -> dict:
    """Correlate latency metrics with error logs for a service."""

    # Step 1: Get latency percentiles from metrics
    latency = get_metric_timeseries(
        namespace='AWS/Lambda',
        metric_name='Duration',
        dimensions=[{'Name': 'FunctionName', 'Value': service_name}],
        stat='p99',
        period=300,
        hours_back=hours_back,
    )

    # Step 2: Get error counts from logs binned by 5 minutes
    error_data = run_logs_query(
        log_groups=log_groups,
        query="""
            filter @message like /(?i)error|exception|fault/
            | stats count(*) as errors by bin(5m) as time_bucket
            | sort time_bucket asc
        """,
        hours_back=hours_back,
    )

    # Step 3: Get X-Ray fault traces for the same window
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)

    trace_summaries = xray_client.get_trace_summaries(
        StartTime=start_time,
        EndTime=end_time,
        FilterExpression=f'service("{service_name}") {{ fault }}',
        Sampling=False,
    )

    faults = trace_summaries.get('TraceSummaries', [])

    return {
        "service": service_name,
        "latency_datapoints": len(latency),
        "error_bins": len(error_data),
        "fault_traces": len(faults),
        "latency_trend": latency,
        "error_trend": error_data,
        "sample_faults": [
            {
                "trace_id": t['Id'],
                "duration": t.get('Duration'),
                "response_time": t.get('ResponseTime'),
                "has_fault": t.get('HasFault'),
            }
            for t in faults[:10]
        ],
    }
```

---

## Pattern 5: Multi-Log-Group Error Aggregation

```python
def aggregate_errors_across_services(
    service_log_groups: dict[str, str],
    hours_back: int = 1,
) -> list[dict]:
    """Aggregate error counts across multiple services for incident triage.

    Args:
        service_log_groups: {"service-name": "/aws/lambda/service-name", ...}
    """
    results = []
    for service, log_group in service_log_groups.items():
        try:
            data = run_logs_query(
                log_groups=[log_group],
                query="""
                    filter @message like /(?i)error|exception|fault/
                    | stats count(*) as error_count,
                            count_distinct(@logStream) as affected_streams
                """,
                hours_back=hours_back,
            )
            if data:
                results.append({
                    "service": service,
                    "error_count": int(data[0].get('error_count', 0)),
                    "affected_streams": int(data[0].get('affected_streams', 0)),
                })
        except Exception as e:
            results.append({"service": service, "error": str(e)})

    return sorted(results, key=lambda x: x.get('error_count', 0), reverse=True)
```

---

## Pattern 6: Time-Window Comparison (Before/After Deploy)

```python
def compare_windows(
    log_groups: list[str],
    query: str,
    before_hours: tuple[int, int],
    after_hours: tuple[int, int],
) -> dict:
    """Compare query results between two time windows.

    Args:
        before_hours: (start_hours_ago, end_hours_ago) e.g., (4, 2) = 4h ago to 2h ago
        after_hours: (start_hours_ago, end_hours_ago) e.g., (2, 0) = 2h ago to now
    """
    now = int(datetime.now(timezone.utc).timestamp())

    def run_window(start_h, end_h, label):
        response = logs_client.start_query(
            logGroupNames=log_groups,
            startTime=now - (start_h * 3600),
            endTime=now - (end_h * 3600),
            queryString=query,
            limit=10000,
        )
        query_id = response['queryId']
        while True:
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] in ('Complete', 'Failed', 'Cancelled', 'Timeout'):
                break
            time.sleep(1)
        return {
            "label": label,
            "status": result['status'],
            "results": [
                {f['field']: f['value'] for f in row}
                for row in result.get('results', [])
            ],
            "stats": result.get('statistics', {}),
        }

    before = run_window(*before_hours, "before")
    after = run_window(*after_hours, "after")

    return {"before": before, "after": after}


# Example: Compare error rates before and after a deployment
result = compare_windows(
    log_groups=["/aws/lambda/order-service"],
    query="""
        filter @message like /(?i)error/
        | stats count(*) as errors, count(*) / 1 as total
    """,
    before_hours=(4, 2),  # 4h ago to 2h ago
    after_hours=(2, 0),   # 2h ago to now
)
```

---

## Pattern 7: Scheduled Queries via CLI

```bash
aws logs create-scheduled-query \
  --name "ErrorAnalysisQuery" \
  --query-language "CWLI" \
  --query-string "fields @timestamp, @message \
    | filter @message like /ERROR/ \
    | stats count() by bin(5m)" \
  --schedule-expression "cron(8 * * * ? *)" \
  --execution-role-arn "arn:aws:iam::123456789012:role/ScheduledQueryRole" \
  --log-group-identifiers "/aws/lambda/my-function" \
  --state "ENABLED"
```

---

## Tips for Python Scripts

1. **Always set a time window** — never query without start/end times
2. **Use pagination** — `get_query_results` returns max 10,000; for more, use multiple narrower time windows
3. **Handle rate limits** — add exponential backoff for `ThrottlingException`
4. **Use `Sampling=False`** in X-Ray `get_trace_summaries` for complete data during incidents
5. **Output structured JSON** — makes results easy to pipe into downstream analysis
6. **Include cost estimates** — log GB scanned from query statistics
7. **Parameterize everything** — service name, log groups, time window, and thresholds should be arguments
