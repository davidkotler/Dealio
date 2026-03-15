# SQL OLAP & Analytics Reference Guide

Condensed reference from industry best practices (dbt Labs, GitLab, Mozilla, Kimball Group) and official
documentation of Snowflake, BigQuery, Redshift, ClickHouse, DuckDB, PostgreSQL, and SQL Server.

## Table of Contents

1. [Naming Conventions](#naming-conventions)
2. [Star Schema Queries](#star-schema-queries)
3. [SCD Type 2 Patterns](#scd-type-2-patterns)
4. [Window Functions Deep Dive](#window-functions-deep-dive)
5. [CTE Patterns](#cte-patterns)
6. [Multi-Dimensional Aggregation](#multi-dimensional-aggregation)
7. [Conditional Aggregation](#conditional-aggregation)
8. [Approximate Functions](#approximate-functions)
9. [Analytical Patterns](#analytical-patterns)
10. [Performance Optimization](#performance-optimization)
11. [Modern SQL Features](#modern-sql-features)
12. [Testing & Quality](#testing--quality)
13. [Cost Optimization](#cost-optimization)

---

## Naming Conventions

### DAG Stage Prefixes (dbt standard)
- `stg_` staging, `int_` intermediate, `fct_` fact, `dim_` dimension, `agg_` aggregation
- Format: `<type>_<source>__<context>` (double underscore before context)
- All snake_case, plural names

### Column Conventions
- PKs: `<object>_id` | FKs: match referenced table's PK name
- Booleans: `is_`, `has_`, `was_` prefix
- Timestamps: `_at` suffix (always UTC) | Dates: `_date` suffix
- Amounts: `_amount`, `_total`, `_count`, `_quantity` suffix
- Metrics: explicit aggregation (`total_revenue` not `revenue`, `avg_order_value` not `aov`)

---

## Star Schema Queries

Canonical pattern: central fact table joined to denormalized dimensions, filter on dimension attributes, aggregate fact measures.

```sql
SELECT
    d.calendar_year,
    p.product_category,
    s.region_name,
    SUM(f.sales_amount) AS total_sales,
    COUNT(*) AS transaction_count
FROM fct_sales AS f
INNER JOIN dim_date    AS d ON f.date_key    = d.date_key
INNER JOIN dim_product AS p ON f.product_key = p.product_key
INNER JOIN dim_store   AS s ON f.store_key   = s.store_key
WHERE d.calendar_year = 2025
  AND p.product_category = 'Electronics'
GROUP BY 1, 2, 3
ORDER BY total_sales DESC;
```

Use surrogate integer keys for fact-dimension joins. Filter on dimension attributes, not fact keys. Pre-filter dimensions in CTEs for readability.

---

## SCD Type 2 Patterns

```sql
-- Current state
SELECT customer_name, city
FROM dim_customer
WHERE customer_id = 1001 AND is_current = 'Y';

-- Point-in-time historical lookup
SELECT customer_name, city
FROM dim_customer
WHERE customer_id = 1001
  AND '2024-06-15' BETWEEN effective_date AND end_date;
```

Always use `'9999-12-31'` as open-ended date (not NULL). Index on `(business_key, is_current)` and `(business_key, effective_date)`.

---

## Window Functions Deep Dive

### Frame Specifications

| Mode | Behavior | Example |
|------|----------|---------|
| ROWS | Physical row count | `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` (7-day MA) |
| RANGE | Value-based range | `RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW` |
| GROUPS | Distinct-value groups | `GROUPS BETWEEN 1 PRECEDING AND 1 FOLLOWING` |

**Critical default**: With ORDER BY, default frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. Without ORDER BY, frame is entire partition. This means `LAST_VALUE` needs explicit `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`.

### Ranking Functions
- `ROW_NUMBER()` — unique sequential, no ties
- `RANK()` — gaps after ties (1, 2, 2, 4)
- `DENSE_RANK()` — no gaps (1, 2, 2, 3)
- `NTILE(n)` — distribute into n buckets
- `PERCENT_RANK()` — (rank-1)/(n-1), range 0-1
- `CUME_DIST()` — fraction of rows <= current

### Period-over-Period with LAG/LEAD

```sql
SELECT period, sales,
    LAG(sales, 1) OVER w AS prev_month,
    (sales - LAG(sales, 1) OVER w) / NULLIF(LAG(sales, 1) OVER w, 0) AS mom_pct,
    LAG(sales, 12) OVER w AS prior_year,
    (sales - LAG(sales, 12) OVER w) / NULLIF(LAG(sales, 12) OVER w, 0) AS yoy_pct
FROM monthly_sales
WINDOW w AS (ORDER BY period);
```

### Named WINDOW Clause
Reduces repetition when multiple functions share the same spec:
```sql
SELECT customer_id, order_date, order_total,
    ROW_NUMBER()     OVER w AS seq,
    SUM(order_total) OVER w AS running_total,
    LAG(order_total) OVER w AS prev_total
FROM fct_orders
WINDOW w AS (PARTITION BY customer_id ORDER BY order_date);
```

---

## CTE Patterns

### Pipeline Architecture: Import -> Filter -> Enrich -> Aggregate -> Output

Each CTE does one logical unit. Last line: `SELECT * FROM final`. Swap which CTE you select from for debugging.

### Recursive CTEs (Hierarchical Data)

```sql
WITH RECURSIVE org_hierarchy AS (
    SELECT employee_id, employee_name, manager_id, 0 AS level,
        CAST(employee_name AS VARCHAR(1000)) AS path
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.employee_name, e.manager_id,
        oh.level + 1, oh.path || ' > ' || e.employee_name
    FROM employees e
    INNER JOIN org_hierarchy oh ON e.manager_id = oh.employee_id
)
SELECT * FROM org_hierarchy ORDER BY path;
```

Always: UNION ALL (not UNION), include termination condition, index join columns.

### CTE Materialization by Platform
- **PostgreSQL 12+**: explicit `MATERIALIZED`/`NOT MATERIALIZED`. Pre-12 always materializes (optimization fence).
- **Snowflake**: single-ref CTEs are pass-through, multi-ref auto-buffer.
- **SQL Server**: optimizer decides, no explicit control.

---

## Multi-Dimensional Aggregation

### ROLLUP — Hierarchical subtotals
```sql
GROUP BY ROLLUP (year, quarter, month)
-- Produces: year+quarter+month, year+quarter, year, grand total
```

### CUBE — All combinations (power set)
```sql
GROUP BY CUBE (category, region)
-- Produces: (cat,region), (cat), (region), ()
```

### GROUPING SETS — Explicit control
```sql
GROUP BY GROUPING SETS (
    (category, region),
    (category),
    ()
)
```

### Distinguish real NULLs from rollup NULLs
```sql
CASE WHEN GROUPING(department) = 1 THEN 'All Departments'
     ELSE department END AS department
```

---

## Conditional Aggregation

### CASE-based (universal)
```sql
SUM(CASE WHEN status = 'completed' THEN amount END) AS completed_revenue
```

### FILTER clause (PostgreSQL, DuckDB, SQLite, Databricks — ~8% faster)
```sql
SUM(amount) FILTER (WHERE status = 'completed') AS completed_revenue
```

---

## Approximate Functions

For millions of rows where interactive speed > precision:

- **APPROX_COUNT_DISTINCT** (HyperLogLog): ~2% error, ~4KB memory, mergeable across partitions
- **APPROX_PERCENTILE** (KLL/t-Digest): ~1.33% error, good for P95/P99 monitoring
- Not suitable for financial/compliance queries

---

## Analytical Patterns

### Sessionization
```sql
WITH lagged AS (
    SELECT *, LAG(event_timestamp) OVER (
        PARTITION BY user_id ORDER BY event_timestamp) AS prev_event
    FROM events
),
flagged AS (
    SELECT *, CASE WHEN prev_event IS NULL
        OR EXTRACT(EPOCH FROM event_timestamp - prev_event) > 1800
        THEN 1 ELSE 0 END AS new_session_flag
    FROM lagged
),
sessioned AS (
    SELECT *, SUM(new_session_flag) OVER (
        PARTITION BY user_id ORDER BY event_timestamp) AS session_id
    FROM flagged
)
SELECT user_id, session_id,
    MIN(event_timestamp) AS session_start,
    MAX(event_timestamp) AS session_end,
    COUNT(*) AS events_in_session
FROM sessioned GROUP BY 1, 2;
```

### Gap and Island Detection
ROW_NUMBER difference method:
```sql
WITH grouped AS (
    SELECT date_col, status,
        date_col - (ROW_NUMBER() OVER (
            PARTITION BY status ORDER BY date_col) * INTERVAL '1 day') AS grp
    FROM events WHERE status = 'active'
)
SELECT MIN(date_col) AS island_start, MAX(date_col) AS island_end,
    COUNT(*) AS length
FROM grouped GROUP BY grp ORDER BY island_start;
```

### Cohort Retention
```sql
WITH user_cohorts AS (
    SELECT user_id, DATE_TRUNC('month', created_at) AS cohort_month FROM users
),
user_activities AS (
    SELECT DISTINCT user_id, DATE_TRUNC('month', activity_date) AS activity_month
    FROM activities
),
retention AS (
    SELECT uc.cohort_month,
        DATE_DIFF(ua.activity_month, uc.cohort_month, MONTH) AS month_num,
        COUNT(DISTINCT uc.user_id) AS active_users
    FROM user_cohorts uc
    JOIN user_activities ua ON uc.user_id = ua.user_id
        AND ua.activity_month >= uc.cohort_month
    GROUP BY 1, 2
),
sizes AS (
    SELECT cohort_month, COUNT(*) AS size FROM user_cohorts GROUP BY 1
)
SELECT r.cohort_month, s.size,
    MAX(CASE WHEN month_num=0 THEN ROUND(active_users*100.0/s.size,1) END) AS "M0",
    MAX(CASE WHEN month_num=1 THEN ROUND(active_users*100.0/s.size,1) END) AS "M1",
    MAX(CASE WHEN month_num=2 THEN ROUND(active_users*100.0/s.size,1) END) AS "M2"
FROM retention r JOIN sizes s ON r.cohort_month = s.cohort_month
GROUP BY 1, 2 ORDER BY 1;
```

### Funnel Analysis
```sql
WITH funnel AS (
    SELECT session_id,
        MAX(CASE WHEN event_name = 'page_view'     THEN 1 ELSE 0 END) AS step_1,
        MAX(CASE WHEN event_name = 'add_to_cart'    THEN 1 ELSE 0 END) AS step_2,
        MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS step_3,
        MAX(CASE WHEN event_name = 'purchase'       THEN 1 ELSE 0 END) AS step_4
    FROM fct_events
    WHERE event_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY 1
)
SELECT COUNT(*) AS total_sessions,
    SUM(step_1) AS viewed,
    SUM(step_2) AS added_to_cart,
    SUM(step_3) AS began_checkout,
    SUM(step_4) AS purchased,
    ROUND(SUM(step_4) * 100.0 / NULLIF(SUM(step_1), 0), 2) AS conversion_pct
FROM funnel;
```

### Pareto / 80-20 Analysis
```sql
WITH ranked AS (
    SELECT product, revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC) AS cum_rev,
        SUM(revenue) OVER () AS total_rev
    FROM product_sales
)
SELECT *, ROUND(cum_rev / total_rev * 100, 1) AS cum_pct,
    CASE WHEN cum_rev / total_rev <= 0.8 THEN 'Top 80%' ELSE 'Bottom 20%' END
FROM ranked;
```

### Market Basket (Association Rules)
Self-join on transaction ID to generate product pairs, compute support, confidence, and lift. Lift > 1 = positive association.

---

## Performance Optimization

### Partition Pruning
```sql
-- GOOD: enables pruning
WHERE sale_date BETWEEN '2025-01-01' AND '2025-03-31'

-- BAD: function prevents pruning
WHERE EXTRACT(YEAR FROM sale_date) = 2025

-- GOOD: rewrite as range
WHERE sale_date >= '2025-01-01' AND sale_date < '2026-01-01'
```

### Join Strategy
- **Hash joins**: optimal for large unsorted analytical tables
- **Merge joins**: pre-sorted inputs
- **Nested loops**: only small outer + indexed inner
- Semi-joins (`EXISTS`) for existence checks instead of JOIN + DISTINCT

### EXPLAIN ANALYZE Red Flags
- Large estimated vs actual row discrepancy → stale statistics, run ANALYZE
- Sequential scan with many filtered rows → missing index
- Sort Method: external merge Disk → increase work_mem
- Nested loops with high loop counts → consider hash join

### Materialized Views
Pre-compute expensive aggregations. BigQuery auto-rewrites queries to matching MVs. Redshift supports incremental refresh for simple patterns.

---

## Modern SQL Features

### LATERAL Joins (per-row dependent subquery)
```sql
SELECT c.id, c.name, o.order_id, o.total
FROM customers c
LEFT JOIN LATERAL (
    SELECT * FROM orders WHERE customer_id = c.id
    ORDER BY placed_at DESC LIMIT 3
) o ON true;
```
SQL Server: `CROSS APPLY` / `OUTER APPLY`.

### QUALIFY (Snowflake, BigQuery, DuckDB, Databricks)
```sql
SELECT * FROM raw_customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;
```

### MATCH_RECOGNIZE (Oracle, Snowflake)
Regex-like pattern detection over ordered rows. V-shape in prices, fraud detection, sessionization.

### Time Travel
- Snowflake: `AT (TIMESTAMP => ...)`, `AT (OFFSET => -3600)` (up to 90 days Enterprise)
- BigQuery: `FOR SYSTEM_TIME AS OF` (7 days)

---

## Testing & Quality

### Essential Quality Checks
- **Freshness**: `MAX(created_at)` vs current time, alert if stale
- **Referential integrity**: LEFT JOIN + WHERE pk IS NULL = 0 rows
- **Uniqueness**: GROUP BY pk HAVING COUNT(*) > 1 = 0 rows
- **Range validation**: no future dates in fact tables

### Idempotency Patterns
- MERGE/UPSERT: same final state on rerun
- DELETE + INSERT in transaction: partition reload
- CREATE OR REPLACE: full rebuild

### Reconciliation
Compare source and target row counts + sums. Hash-based row-level for exact matching.

---

## Cost Optimization

- Require partition filters on all large tables
- Implement query cost budgets and alerts
- Right-size warehouses (start small, scale based on data)
- Use columnar formats (Parquet, ORC) for staging — up to 70% storage reduction
- Auto-expire old partitions, tier to cold storage
- Avoid `SELECT *` — you pay per byte in BigQuery/Snowflake
- Use dry runs for cost estimation before running expensive queries
