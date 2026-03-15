# Interpreting Scalene Output

> How to read, parse, and draw conclusions from Scalene's profiling data.

---

## Output Columns

### CLI / Web UI Columns

| Column                  | Meaning                                              | Optimization Signal                                      |
|-------------------------|------------------------------------------------------|----------------------------------------------------------|
| **Time % Python**       | CPU time in Python bytecode on this line             | Directly optimizable — algorithm, caching, vectorization |
| **Time % native**       | CPU time in C/C++ extensions called from this line   | Change call pattern, batch, or swap library              |
| **Sys %**               | Time in system calls (I/O, sleep, blocking)          | Async I/O, caching, connection pooling                   |
| **GPU %**               | GPU time attributed to this line                     | Check utilization, minimize transfers                    |
| **Mem % Python**        | Memory allocated by Python on this line              | Reduce object creation, use generators                   |
| **Net (MB)**            | Net memory delta — positive = alloc, negative = free | Large positives without negatives = suspect              |
| **Memory timeline / %** | Sparkline trend + share of total memory activity     | Visual leak/spike detector                               |
| **Copy (MB/s)**         | Data copying throughput at Python/native boundary    | Eliminate `.tolist()`, unnecessary conversions           |

### Web UI Color Coding

- **Blue shades** — CPU time (three shades: Python, native, system)
- **Green shades** — Memory allocation (Python vs. native)
- **Red highlighting** — Hotspots (lines consuming significant CPU or memory)
- **Top sparkline** — Overall memory consumption over program lifetime + peak

---

## CPU Time: The Three-Way Split

The Python/native/system split is Scalene's most valuable unique signal. Every CPU hotspot must be classified before
acting.

### Decision Matrix

```
┌────────────────────────┬───────────────────────────────────────────────────┐
│ Dominant Time          │ What It Means → What To Do                       │
├────────────────────────┼───────────────────────────────────────────────────┤
│ Python ≥ 60%           │ Bottleneck is in YOUR code                       │
│                        │ → Optimize: algorithm, vectorize, cache, reduce  │
│                        │   object creation, list comprehension → genexpr  │
│                        │                                                   │
│ Native ≥ 60%           │ Bottleneck is in a C LIBRARY                     │
│                        │ → Cannot optimize Python code here               │
│                        │ → Batch inputs, reduce call count, swap library  │
│                        │ → Check if you're passing data in wrong format   │
│                        │                                                   │
│ System ≥ 40%           │ I/O BOUND (file, network, sleep, lock wait)      │
│                        │ → Async I/O, connection pooling, caching         │
│                        │ → Check for unnecessary sleeps or blocking calls │
│                        │                                                   │
│ Mixed (no dominant)    │ Multiple factors — address largest first          │
│                        │ → Profile with --use-virtual-time to isolate CPU │
│                        │   from I/O and re-assess                         │
└────────────────────────┴───────────────────────────────────────────────────┘
```

### Critical Insight: When NOT to Optimize Python

If a line shows ≥80% native time, rewriting the surrounding Python code will have negligible impact. The time is inside
the C extension. The only productive actions are:

1. Reduce the NUMBER of calls to that native function
2. Batch inputs to reduce per-call overhead
3. Replace with a different library that uses a faster algorithm
4. Check if you're triggering unnecessary copies at the boundary (check copy volume)

---

## Memory Patterns

### Sparkline Pattern Recognition

| Pattern            | Visual       | Diagnosis                         | Severity  |
|--------------------|--------------|-----------------------------------|-----------|
| **Steady growth**  | `▁▂▃▄▅▆▇█`   | Probable memory leak              | 🔴 High   |
| **Spike-and-drop** | `▁▁▇▇▁▁▇▇▁▁` | Normal alloc/dealloc cycle        | 🟢 Normal |
| **Flat-high**      | `▁█████████` | Large persistent allocation       | 🟡 Review |
| **Staircase**      | `▁▁▃▃▅▅▇▇`   | Accumulating without full release | 🔴 High   |
| **Gradual growth** | `▁▁▂▂▃▃▄▄▅`  | Slow leak or cache growth         | 🟡 Medium |

### Python vs. Native Memory

- **High Python memory** from `np.array(python_list)` → accidental copy (passing Python list to NumPy triggers
  conversion)
- **High native memory** from `np.array(...)` → expected NumPy allocation
- Compare the two to determine if unnecessary boundary copies are occurring

### Net (MB) Interpretation

| Net Value                            | Meaning                                         |
|--------------------------------------|-------------------------------------------------|
| Large positive, no matching negative | Memory allocated but not freed — potential leak |
| Large positive with later negative   | Temporary buffer — check if it can be streamed  |
| Small oscillating +/-                | Normal object lifecycle                         |
| Growing positive across iterations   | Accumulating data — verify intentional          |

---

## Copy Volume (MB/s)

Copy volume is unique to Scalene. It measures `memcpy` throughput per line, revealing hidden data conversion costs.

### Common Culprits

| Code Pattern               | Copy Cost                 | Fix                                               |
|----------------------------|---------------------------|---------------------------------------------------|
| `numpy_array.tolist()`     | Full copy NumPy→Python    | Keep in NumPy, iterate with NumPy ops             |
| `np.array(python_list)`    | Full copy Python→NumPy    | Construct NumPy directly, avoid list intermediate |
| `df.values` (pandas)       | May copy entire DataFrame | Use `.to_numpy(copy=False)` where safe            |
| `tensor.cpu()` / `.cuda()` | GPU↔CPU transfer          | Batch transfers, minimize round-trips             |
| Large string encode/decode | Copy + conversion         | Stream processing, avoid full materialization     |

### Rule of Thumb

Any line with copy volume > 1 MB/s warrants investigation. At > 10 MB/s, it's likely a significant performance
bottleneck.

---

## Leak Detection Output

When `--memory-leak-detector` is enabled:

- Lines with high leak probability appear in a **"Potential Leaks"** section
- Leak score uses Laplace's rule of succession: `P(leak) = 1 − (|free| + 1) / (|malloc − free| + 2)`
- Look for lines where:
    - Memory sparkline shows **continuous upward growth**
    - **Net (MB)** is persistently positive with no matching negatives
    - The allocation is inside a **loop or repeated call path**

### Leak vs. Intended Accumulation

Not all growth is a leak. Differentiate:

| Signal                                  | Likely Leak | Likely Intentional             |
|-----------------------------------------|-------------|--------------------------------|
| Grows proportional to input size        | ✅           | —                              |
| Grows proportional to iteration count   | ✅           | —                              |
| Grows once at startup, then flat        | —           | ✅ (model load, cache init)     |
| Grows to a bounded size, then flat      | —           | ✅ (LRU cache, connection pool) |
| Grows indefinitely on repeated requests | ✅           | —                              |

---

## JSON Output Schema (Key Fields)

The Scalene JSON output contains:

```
{
  "elapsed_time_sec": <float>,
  "files": {
    "<filename>": {
      "lines": [
        {
          "lineno": <int>,
          "line": "<source code>",
          "n_cpu_percent_python": <float>,
          "n_cpu_percent_c": <float>,
          "n_sys_percent": <float>,
          "n_gpu_percent": <float>,
          "n_peak_mb": <float>,
          "n_python_fraction": <float>,
          "n_copy_mb_s": <float>,
          "n_usage_fraction": <float>,
          "memory_samples": [<list of memory snapshots>]
        }
      ]
    }
  }
}
```

### Extracting Top Hotspots from JSON

```python
import json

with open("profile.json") as f:
    data = json.load(f)

hotspots = []
for filename, file_data in data.get("files", {}).items():
    for line in file_data.get("lines", []):
        total_cpu = (
                line.get("n_cpu_percent_python", 0)
                + line.get("n_cpu_percent_c", 0)
                + line.get("n_sys_percent", 0)
        )
        if total_cpu > 1.0:  # threshold: 1% total CPU
            hotspots.append({
                "file": filename,
                "line": line["lineno"],
                "source": line.get("line", "").strip(),
                "python_pct": line.get("n_cpu_percent_python", 0),
                "native_pct": line.get("n_cpu_percent_c", 0),
                "system_pct": line.get("n_sys_percent", 0),
                "net_mb": line.get("n_peak_mb", 0),
                "copy_mbs": line.get("n_copy_mb_s", 0),
            })

# Sort by total CPU descending
hotspots.sort(key=lambda h: h["python_pct"] + h["native_pct"] + h["system_pct"], reverse=True)
```

---

## Statistical Reliability

Scalene is a sampling profiler. Results are statistical estimates, not exact counts.

| Runtime      | Confidence       | Guidance                            |
|--------------|------------------|-------------------------------------|
| < 1 second   | ❌ Unreliable     | Use cProfile or increase iterations |
| 1–5 seconds  | 🟡 Directional   | Good for identifying top hotspots   |
| 5–30 seconds | ✅ Stable         | Reliable line-level attribution     |
| > 30 seconds | ✅ High precision | Accurate even for minor hotspots    |

For benchmarking: run the hot path in a loop (50–100+ iterations) to accumulate samples. Always save JSON and compare
before/after quantitatively.
