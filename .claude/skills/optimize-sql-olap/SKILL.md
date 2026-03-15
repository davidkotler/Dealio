---
name: optimize-sql-olap
description: >
  Optimize SQL queries for OLAP, analytics, and data warehouse workloads. Use this skill whenever the user
  asks to review, optimize, rewrite, or improve SQL that involves analytical patterns — aggregations over
  large datasets, window functions, star/snowflake schema queries, CTEs, ROLLUP/CUBE/GROUPING SETS,
  cohort/funnel/retention analysis, sessionization, or any query running against columnar engines
  (Snowflake, BigQuery, Redshift, ClickHouse, DuckDB, Synapse). Also trigger when a user shares a slow
  OLAP query, asks about SQL best practices for analytics, wants to refactor dbt models, or needs help
  with partition pruning, materialized views, or warehouse cost optimization. Even if the user just says
  "make this query faster" or "this dashboard query is slow" and the SQL involves aggregations or joins
  on fact/dim tables, this skill applies.
---

# SQL OLAP Query Optimizer

You are an expert SQL analytics engineer. When optimizing OLAP queries, work through these phases
systematically. Not every phase applies to every query — use judgment about which are relevant.

For deep reference on any topic below, read the corresponding section in `references/sql_olap_guide.md`.

---

## Phase 1: Understand Context

Before touching the SQL, establish:

1. **Target platform** — Snowflake, BigQuery, Redshift, PostgreSQL, ClickHouse, DuckDB, SQL Server/Synapse, or other. Platform determines which optimizations are available (QUALIFY, FILTER, clustering keys, distribution keys, etc.).
2. **Query purpose** — Dashboard query (latency-sensitive, runs often), ad-hoc analysis (one-off), ETL/dbt model (batch, correctness-first), or real-time pipeline.
3. **Data scale** — Rough row counts for fact tables. This changes whether approximate functions, materialized views, or partition strategies matter.
4. **Schema design** — Star schema, snowflake schema, or flat tables. Look for fact/dim naming patterns.

If the user hasn't provided this context and it would change your recommendations, ask. Otherwise, infer from the SQL and proceed.

---

## Phase 2: Detect Anti-Patterns

Scan the query for these high-impact problems (ordered by typical severity):

### Critical — Almost Always Fix

| Anti-Pattern | Why It Hurts | Fix |
|---|---|---|
| `SELECT *` on columnar tables | Reads every column, defeats columnar storage | Select only needed columns |
| Function on partition/index column in WHERE (`WHERE YEAR(date) = 2025`) | Prevents partition pruning | Rewrite as range predicate: `WHERE date >= '2025-01-01' AND date < '2026-01-01'` |
| `NOT IN` with nullable subquery | Returns zero rows if any NULL in sublist | Use `NOT EXISTS` |
| Correlated subquery in SELECT | Executes inner query per outer row | Replace with JOIN or window function |
| `ORDER BY` in CTEs without LIMIT | Unnecessary sort on intermediate result | Remove unless needed for window function |

### Important — Fix When Relevant

| Anti-Pattern | Why It Hurts | Fix |
|---|---|---|
| `DISTINCT` masking join fan-out | Hides incorrect join logic | Fix the join, don't bandaid with DISTINCT |
| `UNION` instead of `UNION ALL` | Triggers expensive dedup sort | Use `UNION ALL` unless dedup is actually needed |
| `COUNT(DISTINCT x)` on huge datasets | Orders of magnitude slower than COUNT | Consider `APPROX_COUNT_DISTINCT` if ~2% error is acceptable |
| Implicit type conversions in joins/filters | Prevents index/pruning usage | Match types explicitly |
| `HAVING` filter that could be `WHERE` | Filters after aggregation instead of before | Move to WHERE when possible |
| Missing table aliases / ambiguous columns | Readability + potential bugs | Always qualify with table alias |

---

## Phase 3: Apply Structural Improvements

### CTE Pipeline Architecture

Restructure complex queries into the **import -> filter -> enrich -> aggregate -> output** CTE chain.
Each CTE does one logical unit of work. The final line should be `SELECT * FROM final`.

```sql
WITH
-- Import: named after source
orders AS (
    SELECT order_id, customer_id, order_total, order_date
    FROM stg_orders
),
-- Filter/Transform
completed_orders AS (
    SELECT * FROM orders
    WHERE order_date >= '2024-01-01' AND order_total > 0
),
-- Enrich via joins
enriched AS (
    SELECT co.*, c.segment
    FROM completed_orders co
    INNER JOIN dim_customers c ON co.customer_id = c.customer_id
),
-- Aggregate
final AS (
    SELECT segment, DATE_TRUNC('month', order_date) AS month,
        SUM(order_total) AS revenue
    FROM enriched
    GROUP BY 1, 2
)
SELECT * FROM final
```

### Window Function Optimization

- Use **named WINDOW clause** when multiple functions share the same PARTITION BY / ORDER BY.
- Remember the default frame with ORDER BY is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, not the whole partition. This catches people off guard with `LAST_VALUE` — add explicit `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` when needed.
- For top-N per group, prefer `ROW_NUMBER()` in a CTE + filter over self-joins. On Snowflake/BigQuery/DuckDB, use `QUALIFY` to avoid the wrapping CTE entirely.

### Join Optimization

- Filter dimensions in CTEs before joining to fact tables (improves readability; modern optimizers usually achieve the same plan).
- Use `INNER JOIN` when referential integrity is guaranteed; `LEFT JOIN` when late-arriving dimensions are possible.
- For existence checks, prefer `EXISTS` / semi-join over `JOIN` + `DISTINCT`.
- In MPP systems, join on distribution/partition keys to avoid data shuffling.

---

## Phase 4: Platform-Specific Optimization

Apply these only when the target platform is known:

### Snowflake
- Use `QUALIFY` to filter window results inline (no wrapping CTE needed)
- Recommend clustering keys on frequently filtered columns (low-to-medium cardinality)
- Leverage result cache (24h, free) — same query text = instant result
- Auto-suspend warehouses after 1-5 minutes

### BigQuery
- Always include partition filter (`WHERE date BETWEEN ...`). Recommend `require_partition_filter` on large tables.
- Avoid `SELECT *` — billing is per byte scanned at $6.25/TB
- Cluster by up to 4 high-cardinality filter columns
- Use `APPROX_COUNT_DISTINCT` for large cardinality
- Prefer STRUCT/ARRAY for nested data over joins

### Redshift
- Distribution key = most common join key on fact tables
- Use compound sort keys for range-filtered queries
- Run `VACUUM` and `ANALYZE` after bulk loads
- Check `SVL_QUERY_SUMMARY` for broadcast joins on large tables

### ClickHouse
- MergeTree ORDER BY = physical sort order (not a traditional index)
- Use `AggregatingMergeTree` for pre-aggregation
- Materialized views trigger on INSERT for real-time pipelines
- Use `WITH TOTALS` for automatic grand-total rows

### PostgreSQL
- Use `EXPLAIN (ANALYZE, BUFFERS)` to identify issues
- Partial indexes for frequently filtered subsets
- Consider `MATERIALIZED` / `NOT MATERIALIZED` CTE hints (12+)
- Use `FILTER` clause instead of CASE-based conditional aggregation (~8% faster)

### DuckDB
- Queries Parquet/CSV/Arrow directly — no ingestion needed
- In-process columnar engine, ideal for local dev
- Supports `QUALIFY`, `FILTER`, and most modern SQL features

---

## Phase 5: Advanced Pattern Recognition

When you recognize these analytical patterns, apply the canonical implementation:

### Sessionization (event streams)
Three-step pattern: LAG to find previous event time -> flag boundaries exceeding timeout (typically 30 min) -> cumulative SUM for session IDs.

### Gap and Island Detection
ROW_NUMBER difference method: subtract sequence number from value to create constant group key per island.

### Cohort Retention
Assign users to cohorts (signup month) -> compute activity periods -> pivot retention percentages with conditional aggregation.

### Funnel Analysis
Chain CTEs where each step filters from prior step's users. Use MAX(CASE WHEN event = X THEN 1 END) per session for conversion flags.

### Period-over-Period Comparison
Use LAG with appropriate offsets: `LAG(value, 1)` for MoM, `LAG(value, 12)` for YoY. Always protect against division by zero with `NULLIF`.

### Multi-Dimensional Aggregation
- `ROLLUP` for hierarchical subtotals (year -> quarter -> month -> grand total)
- `CUBE` for all dimension combinations
- `GROUPING SETS` for specific combinations
- Always use `GROUPING()` to distinguish real NULLs from rollup NULLs

See `references/sql_olap_guide.md` for production-ready examples of each pattern.

---

## Phase 6: Output the Optimized Query

When presenting the optimized SQL:

1. **Show the optimized query** with clear formatting (uppercase keywords, 4-space indent, trailing commas, explicit aliases, semicolon terminator).
2. **Explain each change** briefly — what was wrong and why the fix helps. Group by impact level.
3. **Flag platform-specific suggestions** separately so the user knows what applies to their engine.
4. **Estimate impact** qualitatively: "This should reduce bytes scanned by ~Nx because..." or "Partition pruning will eliminate scanning months of data."
5. If the query would benefit from **schema changes** (adding a clustering key, creating a materialized view, changing distribution key), mention these as separate recommendations — don't mix DDL advice into the query rewrite.

---

## Style Conventions

When rewriting SQL, follow these formatting standards:

- **Keywords**: UPPERCASE (`SELECT`, `FROM`, `WHERE`, `JOIN`, `GROUP BY`)
- **Identifiers**: snake_case lowercase
- **Indentation**: 4 spaces
- **Commas**: trailing (consistent with dbt Labs style)
- **Aliases**: always use `AS` keyword, short meaningful aliases for tables
- **Joins**: always explicit ANSI syntax (`INNER JOIN`, `LEFT JOIN`, never comma joins)
- **GROUP BY**: column numbers (`GROUP BY 1, 2, 3`) for brevity
- **Line length**: under 120 characters
- **Semicolons**: always terminate statements
