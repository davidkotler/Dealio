---
name: debug-profile
version: 1.0.0
description: |
  Profile Python applications to identify CPU, memory, GPU, and I/O bottlenecks using Scalene.
  Use when profiling code, finding slow functions, detecting memory leaks, diagnosing high CPU usage,
  investigating memory growth, benchmarking before/after optimization, or when the user says
  "profile this", "why is this slow", "find bottlenecks", "check for memory leaks", "CPU usage",
  "memory profiling", "what's taking so long", or "performance analysis".
  Relevant for Python performance diagnostics, bottleneck identification, memory leak detection,
  CPU/GPU profiling, copy volume analysis, and pre-optimization measurement.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(scalene:*)
  - Bash(python3 -m scalene:*)
  - Bash(pip install scalene:*)
  - Bash(cat:*)
  - Bash(python3 scripts/*:*)
dependencies:
  - scalene
---

# Debug Profile

> Measure before you optimize. Profile Python code with Scalene to pinpoint CPU, memory, GPU, and I/O bottlenecks with
> line-level precision.

## Quick Reference

| Aspect         | Details                                         |
|----------------|-------------------------------------------------|
| **Invokes**    | `optimize/performance`, `implement/*`           |
| **Invoked By** | `review/performance`, `implement/*`             |
| **Key Tools**  | Bash(scalene), Read, Write                      |
| **Profiler**   | Scalene 2.0+ (sampling-based, ~10–20% overhead) |

---

## Core Workflow

1. **Scope**: Identify target code, workload, and profiling goal (CPU, memory, leak, full)
2. **Prepare**: Ensure Scalene is installed, select profiling mode, configure filters
3. **Profile**: Run Scalene with appropriate flags against a realistic workload
4. **Analyze**: Parse JSON output, identify hotspots by category (Python/native/system/memory)
5. **Report**: Produce structured findings with line-level attribution and severity ranking
6. **Chain**: Hand off ranked findings to `optimize/performance` for remediation

---

## Decision Tree

```
Profiling Request
    │
    ├─► "Why is this slow?" / General ──► Full Profile
    │     scalene run --reduced-profile -o profile.json <target>
    │
    ├─► CPU-focused / "high CPU" ──► CPU-Only (fastest)
    │     scalene run --cpu-only --reduced-profile -o profile.json <target>
    │
    ├─► Memory issue / "memory leak" / "OOM" ──► Memory + Leak Detection
    │     scalene run --memory-leak-detector -o profile.json <target>
    │
    ├─► GPU workload / "CUDA slow" ──► Full with GPU focus
    │     scalene run --gpu -o profile.json <target>
    │
    ├─► Long-running server / daemon ──► Background Profiling
    │     scalene run --off <server>.py &
    │     python3 -m scalene.profile --on --pid <PID>
    │     # exercise workload
    │     python3 -m scalene.profile --off --pid <PID>
    │
    └─► Specific function / narrow scope ──► Targeted Profile
          Add @profile decorator to suspect functions
          scalene run --reduced-profile -o profile.json <target>
```

---

## Profiling Modes

| Mode               | Command                                                       | When                         |
|--------------------|---------------------------------------------------------------|------------------------------|
| **Full**           | `scalene run -o profile.json <target>`                        | Default first pass           |
| **CPU-only**       | `scalene run --cpu-only -o profile.json <target>`             | CPU-bound, fastest overhead  |
| **Leak detection** | `scalene run --memory-leak-detector -o profile.json <target>` | Memory growth, OOM           |
| **Focused**        | `--profile-only "src/myapp"`                                  | Large codebase, filter noise |
| **Background**     | `scalene run --off <server>.py`                               | Servers, daemons             |

---

## Analysis Framework

After profiling, classify every hotspot using the three-way CPU split:

### CPU Hotspot Classification

| Dominant Time        | Diagnosis                 | Action                                        |
|----------------------|---------------------------|-----------------------------------------------|
| **High Python time** | Bottleneck in your code   | Optimize algorithm, vectorize, cache          |
| **High native time** | Bottleneck in C extension | Batch calls, reduce invocations, swap library |
| **High system time** | I/O bound                 | Async I/O, caching, connection pooling        |

### Memory Hotspot Classification

| Pattern                         | Diagnosis                   | Action                                    |
|---------------------------------|-----------------------------|-------------------------------------------|
| **Steady growth (↑ sparkline)** | Likely memory leak          | Trace allocation source, check references |
| **Spike-and-drop**              | Normal temp allocation      | Acceptable unless excessive               |
| **Flat-high**                   | Large persistent allocation | Verify intentional (model load, cache)    |
| **High copy volume (MB/s)**     | Silent data conversion      | Eliminate Python↔native boundary copies   |

---

## Output Interpretation

Scalene JSON output key fields to extract:

- `Time % Python` — Pure Python bytecode execution cost (directly optimizable)
- `Time % native` — C/C++ extension cost (change call pattern, not the code)
- `Sys %` — System call / I/O cost (async, batching, pooling)
- `Net (MB)` — Per-line memory delta (positive = alloc, negative = free)
- `Copy (MB/s)` — Data copy throughput at Python/native boundary
- `GPU %` — GPU utilization attributed per line
- Memory sparklines — Trend visualization per line over program lifetime

---

## Skill Chaining

| Condition                                    | Invoke                               | Handoff Context                                |
|----------------------------------------------|--------------------------------------|------------------------------------------------|
| Hotspots identified, optimization needed     | `optimize/performance`               | Ranked findings, file:line, category, severity |
| Algorithmic rewrite required                 | `implement/python`                   | Current code, profiling data, target metric    |
| Async refactor indicated by high system time | `optimize/performance` refs/async.md | I/O-bound lines, blocking call sites           |
| Post-optimization validation                 | `debug-profile` (self)               | Before profile JSON for comparison             |

---

## Patterns & Anti-Patterns

### ✅ Do

- Profile with **realistic workloads** and production-like data sizes
- Ensure workload runs **≥ 5 seconds** for statistically stable sampling
- Use `--profile-only` to **filter to application code**, exclude tests/vendors
- Save JSON output (`-o profile.json`) for **before/after comparison**
- Check the **Python vs. native split** before attempting Python-level optimization
- Run profiling **in a loop** (50–100 iterations) when the hot path is short

### ❌ Don't

- Optimize based on intuition — always measure first
- Attempt Python optimization when native time dominates (≥80%)
- Profile with toy data — small inputs hide O(n²) and allocation patterns
- Run Scalene alongside other profilers (signal handler conflicts)
- Skip memory profiling when investigating "slowness" — memory pressure causes CPU overhead
- Use `--profile-all` by default — it floods output with library internals

---

## Example

**Input:** "This data pipeline is slow, profile it"

**Actions:**

```bash
# 1. Install if needed
pip install -U scalene

# 2. Full profile with application code filter
scalene run --reduced-profile --profile-only "src/" -o profile.json pipeline.py --- --input large_dataset.csv

# 3. View in terminal
scalene view --cli

# 4. Parse JSON for top hotspots
python3 scripts/parse-profile.py profile.json
```

**Report structure:**

```
## Profiling Report: pipeline.py

### Top CPU Hotspots (by total time %)
1. src/transform.py:47  — 34% Python time — list comprehension over 1M rows
2. src/io_handler.py:12 — 22% system time — synchronous file reads

### Memory Concerns
1. src/loader.py:31 — +128 MB net — full dataset materialized into list
2. src/transform.py:52 — 8.2 MB/s copy volume — numpy↔list conversion

### Recommendations (ranked by impact)
1. [HIGH] Vectorize transform at line 47 → est. 5–10x speedup
2. [HIGH] Stream file reads at line 12 → eliminate I/O blocking
3. [MED]  Use generator at line 31 → reduce peak memory by ~128 MB
4. [MED]  Eliminate .tolist() at line 52 → remove copy overhead

→ Invoking: optimize/performance with ranked findings
```

---

## Deep References

For detailed guidance, load these refs on demand:

- **[scalene-cli.md](refs/scalene-cli.md)**: Complete CLI options, config YAML, environment variables
- **[interpreting-output.md](refs/interpreting-output.md)**: Column definitions, JSON schema, sparkline patterns
- **[patterns.md](refs/patterns.md)**: Advanced profiling patterns — servers, multiprocessing, Jupyter, @profile
  decorator, programmatic API, before/after diffing

---

## Quality Gates

Before completing any profiling task:

- [ ] Workload ran for ≥ 5 seconds (statistically meaningful samples)
- [ ] Application code filtered with `--profile-only` (no library noise)
- [ ] JSON output saved for future comparison (`-o profile.json`)
- [ ] Every finding attributed to specific file:line with category and severity
- [ ] Python vs. native vs. system time classified for each CPU hotspot
- [ ] Memory trends checked for leak patterns (steady growth without drops)
- [ ] Copy volume reviewed for hidden Python↔native boundary costs
- [ ] Findings ranked by estimated impact before handoff to optimization
