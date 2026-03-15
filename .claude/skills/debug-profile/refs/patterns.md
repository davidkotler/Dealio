# Profiling Patterns

> Advanced profiling patterns for servers, multiprocessing, targeted profiling, before/after comparison, and CI integration.

---

## Pattern 1: Iterative Narrowing (Recommended Default)

Start broad, then narrow to the bottleneck.

```bash
# Step 1: Full profile, app code only
scalene run --reduced-profile --profile-only "src/" -o full.json app.py

# Step 2: Identify top file (e.g., src/transform.py dominates)
# Step 3: Narrow with @profile decorators on suspect functions
# Step 4: Re-profile for line-level detail on hot functions
scalene run --reduced-profile -o focused.json app.py

# Step 5: Classify each hotspot (Python/native/system/memory)
# Step 6: Hand off classified findings to optimization
```

---

## Pattern 2: Before/After Comparison

Always profile before AND after optimization to validate impact.

```bash
# Baseline
scalene run --reduced-profile --profile-only "src/" -o before.json app.py

# ... apply optimization ...

# Validation
scalene run --reduced-profile --profile-only "src/" -o after.json app.py
```

Compare programmatically:

```python
import json

def load_hotspots(path, threshold=1.0):
    with open(path) as f:
        data = json.load(f)
    hotspots = {}
    for fname, fdata in data.get("files", {}).items():
        for line in fdata.get("lines", []):
            total = (line.get("n_cpu_percent_python", 0)
                   + line.get("n_cpu_percent_c", 0)
                   + line.get("n_sys_percent", 0))
            if total > threshold:
                key = f"{fname}:{line['lineno']}"
                hotspots[key] = {
                    "total_cpu": total,
                    "python": line.get("n_cpu_percent_python", 0),
                    "native": line.get("n_cpu_percent_c", 0),
                    "system": line.get("n_sys_percent", 0),
                    "net_mb": line.get("n_peak_mb", 0),
                }
    return hotspots, data.get("elapsed_time_sec", 0)

before, before_time = load_hotspots("before.json")
after, after_time = load_hotspots("after.json")

print(f"Runtime: {before_time:.2f}s → {after_time:.2f}s "
      f"({(1 - after_time/before_time) * 100:.1f}% improvement)")
```

---

## Pattern 3: @profile Decorator (Targeted Profiling)

Use when you know which functions to investigate.

```python
# IMPORTANT: Do NOT import profile. Scalene injects it automatically.

@profile
def process_batch(items):
    results = []
    for item in items:
        results.append(transform(item))
    return results

@profile
def transform(item):
    return heavy_computation(item)
```

### Making code runnable with and without Scalene

```python
import builtins

if not hasattr(builtins, 'profile'):
    def profile(func):
        return func

@profile
def my_function():
    pass
```

When `@profile` is present, Scalene reports ONLY decorated functions — ideal for cutting noise.

---

## Pattern 4: Programmatic Start/Stop

For programs with long initialization that shouldn't be profiled:

```python
from scalene import scalene_profiler

# Setup (not profiled)
db = connect_database()
model = load_ml_model()

# Profile only the hot path
scalene_profiler.start()
for batch in data_stream:
    process(batch)
scalene_profiler.stop()
```

Context manager form:

```python
from scalene.scalene_profiler import enable_profiling

with enable_profiling():
    expensive_computation()
```

Launch with: `scalene run --off your_program.py`

---

## Pattern 5: Server / Daemon Profiling

Profile a running server during a specific load window.

```bash
# Terminal 1: Start server with profiling disabled
scalene run --off server.py &
# Note: Scalene outputs the PID

# Terminal 2: Warm up the server
curl http://localhost:8000/health

# Terminal 3: Enable profiling
python3 -m scalene.profile --on --pid <PID>

# Terminal 2: Run load test (only THIS window is profiled)
wrk -t4 -c100 -d30s http://localhost:8000/api/endpoint

# Terminal 3: Disable profiling
python3 -m scalene.profile --off --pid <PID>
```

### Framework-specific notes

- **FastAPI/Uvicorn**: Profile the worker process, not the launcher
- **Django**: Pass `--noreload` to prevent auto-reloader interference
- **gevent**: Use `monkey.patch_all(thread=False)` to avoid signal conflicts

---

## Pattern 6: Memory Leak Detection Workflow

```bash
# Step 1: Profile with leak detector
scalene run --memory-leak-detector --profile-only "src/" -o leaks.json app.py

# Step 2: Examine output
scalene view --cli -i leaks.json
```

### Reliable leak detection requires:

1. **Sufficient iterations** — Run the suspect code path 50–100 times
2. **Realistic data** — Use production-size inputs
3. **Isolation** — Profile the suspect code path specifically, not the entire program
4. **Trend analysis** — Look for lines with steadily increasing sparklines

### Differentiating leaks from intentional accumulation

```python
# LEAK: Unbounded growth
cache = {}
def process(key, value):
    cache[key] = value  # ← grows forever, never evicts

# NOT A LEAK: Bounded cache
from functools import lru_cache
@lru_cache(maxsize=1024)
def process(key):
    return expensive_compute(key)  # ← bounded to 1024 entries
```

---

## Pattern 7: Multiprocessing Profiling

Scalene supports Python's `multiprocessing` — one of few profilers that does.

```bash
scalene run --profile-only "src/" -o mp-profile.json multiprocess_app.py
```

Scalene aggregates results across child processes. No special configuration needed.

**Limitation**: Jupyter on macOS cannot profile child processes. Use CLI instead.

---

## Pattern 8: CI/CD Performance Gate

```yaml
# .github/workflows/profile.yml
name: Performance Gate
on: [pull_request]

jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install scalene -r requirements.txt
      - run: |
          scalene run --cpu-only --reduced-profile \
            --profile-only "src/" \
            -o profile.json \
            benchmarks/perf_test.py
      - run: python scripts/check_perf_gate.py profile.json
      - uses: actions/upload-artifact@v4
        with:
          name: scalene-profile
          path: profile.json
```

### Gate script:

```python
#!/usr/bin/env python3
"""Fail CI if performance exceeds thresholds."""
import json, sys

with open(sys.argv[1]) as f:
    profile = json.load(f)

runtime = profile.get("elapsed_time_sec", 0)
MAX_RUNTIME = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

if runtime > MAX_RUNTIME:
    print(f"FAIL: {runtime:.2f}s > {MAX_RUNTIME}s threshold")
    sys.exit(1)
print(f"PASS: {runtime:.2f}s ≤ {MAX_RUNTIME}s")
```

---

## Pattern 9: Jupyter Notebook Profiling

```python
# Load extension
%load_ext scalene

# Profile a single statement
%scrun my_function()

# Profile an entire cell
%%scalene --reduced-profile
import numpy as np
x = np.array(range(10**7))
result = x ** 2 + x * 3

# CPU-only in Jupyter
%scrun --cpu-only my_function()
```

**Limitations**:
- Jupyter supports CPU + GPU profiling only — full memory requires CLI
- macOS Jupyter cannot profile multiprocessing child processes

---

## Pattern 10: Periodic Snapshots for Long-Running Processes

Monitor how performance characteristics change over time:

```bash
scalene run --profile-interval 30.0 --profile-only "src/" -o periodic.json long_task.py
```

Generates a new profile snapshot every 30 seconds. Useful for:
- Detecting performance degradation over time
- Finding memory growth in long-running batch jobs
- Identifying warm-up effects vs steady-state performance

---

## Anti-Patterns

### ❌ Profiling test code

```bash
# BAD: profiles test framework overhead
scalene run tests/test_pipeline.py

# GOOD: profile the actual application with realistic workload
scalene run --profile-only "src/" -o profile.json benchmarks/benchmark.py
```

### ❌ Toy data profiling

```python
# BAD: 10 items hides O(n²) behavior
data = list(range(10))
process(data)

# GOOD: production-scale input reveals true performance characteristics
data = list(range(1_000_000))
process(data)
```

### ❌ Optimizing native time with Python changes

```python
# Scalene shows: 95% native time on this line
result = np.linalg.solve(A, b)  # ← Rewriting surrounding Python won't help

# PRODUCTIVE: Reduce the NUMBER of calls
# Instead of solving 1000 times in a loop, batch into a single call
results = np.linalg.solve(A_batch, b_batch)
```

### ❌ Running multiple profilers simultaneously

Scalene, cProfile, line_profiler, and py-spy all use signal handling or tracing. Running them together causes interference and corrupted results. Use one at a time.
