---
name: debug-cloudwatch
version: 1.0.0
description: |
  Investigate and debug production issues using AWS CloudWatch Logs Insights, Metrics Insights,
  X-Ray traces, and Transaction Search. Use when diagnosing errors, latency spikes, timeouts,
  cold starts, 5xx responses, failed requests, capacity exhaustion, or any production anomaly.
  Use when the user says "debug", "investigate", "root cause", "why is this failing", "check logs",
  "query CloudWatch", "find errors", "trace the request", "what happened", "diagnose", "triage",
  or references log groups, metrics, traces, X-Ray, or CloudWatch in a debugging context.
  Generates Logs Insights queries, Metrics Insights SQL, X-Ray filter expressions,
  Transaction Search span queries, and Python boto3 analysis scripts.
  Relevant for AWS production debugging, incident triage, root cause analysis, observability investigation.

---

# Debug CloudWatch

> Investigate production issues by querying CloudWatch Logs, Metrics, X-Ray traces, and Transaction Search — either through direct queries or automated Python analysis scripts.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `observe/logs`, `observe/traces`, `observe/metrics` |
| **Invoked By** | Any agent or human during incident triage or post-mortem |
| **Key Tools** | Bash(aws), Write, Read |
| **Signals** | Logs → Metrics → Traces → Spans (correlate across all four) |

---

## Core Workflow

1. **Scope**: Identify the affected service, time window, and symptom (errors, latency, timeouts, capacity)
2. **Triage**: Start with the broadest signal — Logs Insights error scan or Metrics anomaly — to narrow the blast radius
3. **Correlate**: Cross-reference across signals (log errors → trace IDs → span analysis → metric confirmation)
4. **Deep-dive**: Write targeted queries or Python scripts for complex multi-step analysis
5. **Root-cause**: Isolate the failing component, dependency, or configuration using X-Ray service map and annotations
6. **Document**: Summarize findings with query links, timestamps, and affected resources

---

## Decision Tree

```
User reports issue
    │
    ├─► Error/Exception? ──► Logs Insights: filter errors by time + service
    │                           └──► Extract trace IDs → X-Ray deep-dive
    │
    ├─► Latency spike? ──► Metrics Insights: p95/p99 by service
    │                        └──► X-Ray: responsetime > threshold
    │                              └──► Transaction Search: slow spans
    │
    ├─► Timeout? ──► Logs: "Task timed out" / "timeout" filter
    │                 └──► X-Ray: duration analysis by downstream
    │
    ├─► Capacity/throttle? ──► Metrics: throttle counts, queue depth, connections
    │                           └──► Logs: throttle error patterns
    │
    ├─► Intermittent? ──► Logs: pattern command (auto-cluster)
    │                      └──► Metrics: time-series bin(5m) for anomaly windows
    │
    └─► Complex / multi-service? ──► Write Python script
                                      └──► See refs/python-scripts-reference.md
```

---

## Signal Selection Guide

| Symptom | Start With | Then Correlate |
|---------|-----------|----------------|
| 5xx errors | Logs Insights (error filter) | X-Ray (fault traces) |
| Slow responses | Metrics Insights (latency percentiles) | X-Ray (responsetime filter) |
| Cold starts | Logs Insights (@initDuration) | Metrics (ConcurrentExecutions) |
| Timeouts | Logs Insights ("Task timed out") | X-Ray (duration by edge) |
| Throttling | Metrics (Throttles, 429s) | Logs (throttle messages) |
| Memory issues | Logs (@maxMemoryUsed) | Metrics (MemoryUtilization) |
| Downstream failures | X-Ray (service/edge filters) | Transaction Search (span attributes) |
| Unauthorized access | Logs (CloudTrail errorCode) | X-Ray (error traces) |
| Unknown/intermittent | Logs (`pattern` command) | Metrics (bin time-series) |

---

## Query Templates — Quick Start

### Logs Insights: Error Scan







```

filter @message like /(?i)(error|exception|fail|timeout)/

| stats count(*) as errors by bin(5m)

| sort errors desc

```





### Logs Insights: Specific Service Errors with Trace ID


```
filter level = "ERROR"


| fields @timestamp, message, traceId, error.type, error.message
| sort @timestamp desc


| limit 50

```




### Metrics Insights: Top Erroring Functions


```sql

SELECT SUM(Errors)
FROM SCHEMA("AWS/Lambda", FunctionName)

GROUP BY FunctionName

ORDER BY SUM() DESC
LIMIT 10

```


### X-Ray: Faults on a Service

```

service("order-service") { fault } AND responsetime > 2
```

### Transaction Search: Slow Spans by Operation

```
FILTER attributes.aws.local.service = "order-service"
| STATS pct(durationNano / 100000, 95) as p95_ms
    by attributes.aws.local.operation
| SORT p95_ms DESC
| LIMIT 20
```

---

## When to Write Python Scripts

Use Python boto3 scripts instead f direct queries when:

- **Multi-step analysis**: Query results feed into subsequent queries (e.g., extract trace IDs from logs, then batch-get traces)
- **Cross-signal correlation**: Combine log, metric, and trace data in a single analysis
- **Time-series aggregation**: Compute rolling averages, detect anomalies, or compare time windows
- **Large result sets**: Process or than 10,000 results (Logs Insights limit) via pagination
- **Automated triage**: Build reusable diagnostic scripts for recurring issue patterns
- **Report generation**: Produce structured incident summaries with data from all signals

**For Python script patterns, load:** `refs/python-scripts-reference.md`

---

## Skill Chaining

### Invoke Downstream Skills When

| Condition | Invoke | Rationale |
|-----------|--------|-----------|
| Need to add missing instrumentation | `observe/logs`, `observe/traces`, `observe/metrics` | Debug reveals observability gaps |
| Root cause is a code defect | `implement/*` (relevant domain) | Fix the identified bug |
| Need to add alerts for this class of failure | `observe/alerts` | Prevent recurrence |

### Chaining Syntax

When chaining is needed, output:
```markdown
**Invoking Sub-Skill:** `observe/traces`
**Reason:** Service lacks trace context — adding spans to isolate downstream latency
**Handoff Context:** Service name, failing endpoint, required span attributes
```

---

## Patterns & Anti-Patterns

### ✅ Do

- Narrow time ranges aggressively — charges are $0.005/GB scanned
- Place `filter` before `stats` to reduce data processed
- Use `limit` on every exploratory query
- Start with `pattern` command to auto-cluster unknown log formats
- Correlate across all signals: logs → traces → metrics → spans
- Use `bin()` for time-series visualization of trends
- Extract trace IDs from logs to pivot into X-Ray for distributed analysis
- Use annotations (`annotation[key]`) in X-Ray for business-context filtering
- Use `SCHEMA()` in Metrics Insights to constrain dimension matching

### ❌ Don't

- Query all log groups when you know the affected service
- Skip time range narrowing (scans entire retention window)
- Use `parse` when fields are auto-discovered JSON (wastes compute)
- Forget the 2-`stats`-command limit in Logs Insights
- Use high-cardinality values as metric dimensions (cost explosion)
- Rely on X-Ray metadata for filtering (only annotations are indexed)
- Write Python scripts when a single direct query suffices

---

## Key Limits to Remember

| System | Limit |
|--------|-------|
| Logs Insights results | 10,000 max |
| Logs Insights log groups per query | 50 max |
| Logs Insights `stats` commands | 2 max per query |
| Logs Insights query timeout | 60 minutes |
| Metrics Insights time range | Most recent 3 hours (standard) |
| Metrics Insights time series returned | 500 max |
| X-Ray annotations per trace | 50 max |
| Infrequent Access log class | No `stats`, `parse`, `dedup`, `pattern` |

---

## Deep References

For detailed query syntax and patterns, load these refs as needed:

- **[logs-insights-reference.md](refs/logs-insights-reference.md)**: Complete Logs Insights syntax, all commands, functions, service-specific query patterns (Lambda, API Gateway, VPC Flow Logs, CloudTrail)
- **[metrics-insights-reference.md](refs/metrics-insights-reference.md)**: Metrics Insights SQL, SCHEMA(), Metric Math, EMF, SEARCH expressions, service-specific metric queries
- **[xray-traces-reference.md](refs/xray-traces-reference.md)**: X-Ray filter expressions, Transaction Search span queries, annotation patterns, service/edge filters, CLI usage
- **[python-scripts-reference.md](refs/python-scripts-reference.md)**: boto3 patterns for multi-step analysis, cross-signal correlation, automated triage scripts, and report generation
- **[troubleshooting.md](refs/troubleshooting.md)**: Common debugging scenarios with step-by-step investigation playbooks

---

## Quality Gates

Before completing any investigation using this skill:

- [ ] Time window is explicitly scoped and as narrow as possible
- [ ] At least two signals were correlated (logs+traces, metrics+logs, etc.)
- [ ] Root cause hypothesis is supported by query evidence, not assumption
- [ ] Queries are cost-efficient (filters before aggregations, limited log groups)
- [ ] Findings include actionable next steps (fix, alert, instrument, or escalate)
