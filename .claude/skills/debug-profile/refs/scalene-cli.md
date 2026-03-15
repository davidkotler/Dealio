# Scalene CLI Reference

> Complete command-line interface, configuration, and environment variable reference for Scalene 2.0+.

---

## Command Structure (Scalene 2.0+)

```bash
scalene run [options] program.py [--- --program-args]   # Profile a program
scalene view [options] [profile.json]                    # View saved profile
```

The `---` triple-dash separator divides Scalene options from program arguments.
Legacy flat syntax (`scalene [options] program.py`) remains supported.

---

## `scalene run` — Core Options

| Flag | Default | Purpose |
|------|---------|---------|
| `-o, --outfile FILE` | `scalene-profile.json` | Output file path |
| `--cpu-only` | `False` | CPU-only mode (fastest, skips memory/GPU) |
| `--cpu` | `True` | Enable CPU profiling |
| `--gpu` | `True` | Enable GPU profiling |
| `--memory` | `True` | Enable memory profiling |
| `--cli` | `False` | Output to terminal only (no web UI) |
| `--html` | `False` | Output as HTML |
| `--json` | `True` | Output as JSON |
| `--reduced-profile` | `False` | Only include lines with significant activity |
| `--profile-all` | `False` | Profile all code including dependencies |
| `--profile-only "pkg1,pkg2"` | — | Only profile files matching these strings |
| `--profile-exclude "pkg1,pkg2"` | — | Exclude files matching these strings |
| `-c, --config FILE` | — | Load options from YAML config file |
| `--profile-interval SECS` | `inf` | Emit intermediate profiles every N seconds |

## `scalene run` — Advanced Options

| Flag | Default | Purpose |
|------|---------|---------|
| `--cpu-percent-threshold PCT` | `1` (%) | Minimum CPU% for a file to appear |
| `--cpu-sampling-rate SECS` | `0.01` (10ms) | CPU sampling interval |
| `--allocation-sampling-window N` | Auto | Memory sampling granularity |
| `--malloc-threshold N` | `100` | Minimum allocations to report a line |
| `--use-virtual-time` | `False` | Measure CPU time only (exclude I/O) |
| `--memory-leak-detector` | `False` | Enable leak detection heuristics |
| `--off` | — | Start with profiling disabled (programmatic control) |
| `--on` | — | Resume profiling for a given PID |
| `--stacks` | `False` | Collect call stacks |
| `--program-path PATH` | Auto | Set program path for file resolution |

## `scalene view` — Viewing Options

| Flag | Purpose |
|------|---------|
| `--cli` | Display in terminal with colored tables |
| `--html` | Save as `scalene-profile.html` |
| `--standalone` | Self-contained HTML with embedded assets |
| `-r, --reduced` | Show only lines with significant activity |
| `-i FILE` | View a specific profile file |

---

## YAML Configuration

All CLI flags (without `--` prefix) are valid YAML keys. Store as `scalene.yaml` in repository root for team consistency.

```yaml
# scalene.yaml — recommended project defaults
outfile: scalene-profile.json
reduced-profile: true
profile-only: "src/"
profile-exclude: "tests/,venv/"
cpu-percent-threshold: 1
cpu-sampling-rate: 0.01
malloc-threshold: 100
```

### Extended configurations

```yaml
# CPU-only (fastest profiling)
cpu-only: true
outfile: cpu-profile.json
profile-only: "src/"
reduced-profile: true
cpu-percent-threshold: 5

# Full with leak detection
memory-leak-detector: true
outfile: leak-profile.json
profile-only: "src/"
reduced-profile: true

# CI pipeline profile
cpu-only: true
outfile: ci-profile.json
profile-only: "src/"
cpu-percent-threshold: 5
reduced-profile: true
```

Usage: `scalene run -c scalene.yaml your_program.py`

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `LD_PRELOAD` / `DYLD_INSERT_LIBRARIES` | Managed automatically for `libscalene` injection |
| `PYTHONMALLOC` | Set to `malloc` automatically during memory profiling |
| `SCALENE_PYTHON_EXECUTABLE` | Override Python executable for MCP server integration |
| `SCALENE_TIMEOUT` | Profiling timeout for MCP server (default: 30s) |
| AI provider API key variables | Prepopulate keys for headless AI suggestion generation (2.1.0+) |

---

## Tuning Guide

| Scenario | Tuning |
|----------|--------|
| **Short-running program** (<5s) | `--cpu-sampling-rate 0.001` `--malloc-threshold 10` |
| **Large codebase** | `--cpu-percent-threshold 5` `--reduced-profile` `--profile-only "src/"` |
| **Fastest possible** | `--cpu-only` (skips memory allocator, near-zero overhead) |
| **Maximum detail** | All defaults + `--memory-leak-detector` + `--stacks` |
| **Long-running server** | `--off` + remote `--on/--off` via PID |

---

## Common Command Recipes

```bash
# Full profile, app code only, save JSON
scalene run --reduced-profile --profile-only "src/" -o profile.json app.py

# CPU-only fast pass
scalene run --cpu-only --reduced-profile -o cpu.json app.py

# Memory leak hunt
scalene run --memory-leak-detector --profile-only "src/" -o leaks.json app.py

# Focus on specific package
scalene run --profile-only "mypackage,utils" -o profile.json app.py

# Before/after comparison
scalene run -o before.json app.py
# ... make changes ...
scalene run -o after.json app.py

# Background profiling (servers)
scalene run --off server.py &
python3 -m scalene.profile --on --pid $(pgrep -f server.py)
# exercise with load test
python3 -m scalene.profile --off --pid $(pgrep -f server.py)

# View in terminal
scalene view --cli -i profile.json

# Self-contained HTML for sharing
scalene view --standalone -i profile.json

# With program arguments
scalene run -o profile.json app.py --- --input data.csv --workers 4

# Use YAML config
scalene run -c scalene.yaml app.py

# Periodic snapshots (every 30s)
scalene run --profile-interval 30.0 -o profile.json long_running.py

# Virtual time (CPU only, ignoring I/O)
scalene run --use-virtual-time -o profile.json compute_heavy.py

# High-frequency sampling for short workloads
scalene run --cpu-sampling-rate 0.001 -o profile.json quick_task.py
```

---

## Platform Notes

| Platform | CPU | Memory | GPU |
|----------|-----|--------|-----|
| Linux (x86_64, ARM) | ✅ | ✅ | ✅ (NVIDIA) |
| macOS (Intel + Apple Silicon) | ✅ | ✅ | ✅ (MPS, v2.1.0+) |
| Windows (native + WSL2) | ✅ | ✅ (v2.0+) | ✅ (NVIDIA) |

- **Python 3.8–3.14** supported; **3.11.0** excluded (CPython bug)
- Windows requires Visual C++ Redistributable for memory profiling
- Django: always pass `--noreload` to prevent auto-reloader interference
- gevent: use `monkey.patch_all(thread=False)`
