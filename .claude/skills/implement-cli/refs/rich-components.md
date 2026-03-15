# Rich Components Reference — implement-cli

> Detailed guidance on Rich output components for CLI applications.

---

## Component Selection Guide

| Data Shape | Rich Component | When |
|------------|---------------|------|
| Records / rows | `Table` | Listing items, status dashboards, comparisons |
| Key-value summary | `Panel` | Deployment result, config display, error details |
| Hierarchical data | `Tree` | File trees, dependency graphs, org charts |
| Sequential iteration | `track()` or `Progress` | Downloads, processing, multi-step workflows |
| Real-time updates | `Live` | Monitoring, streaming logs, build status |
| Single line wait | `console.status()` | Database connections, API calls |
| Formatted code | `Syntax` | Config files, generated code, diffs |
| Structured text | `Markdown` | README display, help docs |
| Side-by-side | `Columns` | Multi-panel dashboards |
| Split screen | `Layout` | Complex dashboards with named regions |

---

## 1. Tables

### Full-Featured Table

```python
from rich.table import Table
from rich.box import ROUNDED

table = Table(
    title="[bold]Server Status[/]",
    caption="Last updated: 2025-02-07",
    box=ROUNDED,
    show_header=True,
    header_style="bold cyan",
    title_style="bold magenta",
    show_lines=False,
    expand=False,
    padding=(0, 1),
    row_styles=["", "dim"],  # Zebra striping
)

table.add_column("Host", style="bold white", no_wrap=True, min_width=12)
table.add_column("Status", justify="center")
table.add_column("CPU %", justify="right", style="cyan")
table.add_column("Memory", justify="right")
table.add_column("Uptime", justify="right", style="dim")

for server in servers:
    status = "[green]● UP[/]" if server.healthy else "[red]● DOWN[/]"
    cpu_style = "red" if server.cpu > 90 else "yellow" if server.cpu > 70 else "green"

    table.add_row(
        server.name,
        status,
        f"[{cpu_style}]{server.cpu:.1f}%[/]",
        f"{server.memory_mb:,} MB",
        server.uptime_str,
    )

table.add_section()  # Visual separator between row groups
console.print(table)
```

### Grid Layout (Borderless Table)

```python
grid = Table.grid(expand=True, padding=(0, 2))
grid.add_column(ratio=1)
grid.add_column(ratio=1)
grid.add_row(left_panel, right_panel)  # Side-by-side renderables
console.print(grid)
```

### Box Styles

| Style | Use Case |
|-------|----------|
| `ROUNDED` | Default, clean look |
| `SIMPLE` | Minimal, data-focused |
| `MINIMAL` | Space-efficient |
| `HEAVY_EDGE` | Emphasis, reports |
| `DOUBLE` | Formal output |
| `SQUARE` | Structured data |

---

## 2. Panels

```python
from rich.panel import Panel

# Status panel
panel = Panel(
    "Deployment successful!\nAll 12 services running.",
    title="[success]✓ Status[/]",
    subtitle="v2.3.1",
    border_style="green",
    padding=(1, 2),
    expand=False,
)

# Auto-sized panel
Panel.fit("[bold]Quick Info[/]\nVersion: 1.0", border_style="cyan")

# Error panel
Panel(
    f"[error]{error.message}[/]\n\n[muted]Hint: {error.hint}[/]",
    title="[error]Error[/]",
    border_style="red",
)
```

---

## 3. Trees

```python
from rich.tree import Tree

tree = Tree("[bold]Project Structure[/]", guide_style="dim")
src = tree.add("[bold blue]src/[/]")
src.add("[green]main.py[/]")
src.add("[green]config.py[/]")
commands = src.add("[bold blue]commands/[/]")
commands.add("[green]users.py[/]")
commands.add("[green]projects.py[/]")
console.print(tree)
```

---

## 4. Progress Bars

### Simple — `track()`

```python
from rich.progress import track

for item in track(range(100), description="Processing..."):
    process(item)
```

### Multi-Task Progress

```python
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TimeElapsedColumn, MofNCompleteColumn,
)

progress = Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
)

with progress:
    download = progress.add_task("[cyan]Downloading...", total=1000)
    extract = progress.add_task("[green]Extracting...", total=500)

    while not progress.finished:
        progress.update(download, advance=5)
        progress.update(extract, advance=2)
```

### Indeterminate Progress

```python
task = progress.add_task("Waiting...", total=None)  # Pulsing animation
```

### Transient Progress (Disappears on Complete)

```python
progress = Progress(transient=True)
```

---

## 5. Status Spinners

```python
with console.status("[bold green]Connecting to database...") as status:
    connect_db()
    status.update("[bold green]Running migrations...")
    run_migrations()
```

Use for short operations where progress percentage is unknown.

---

## 6. Live Displays

```python
from rich.live import Live

def generate_table():
    table = Table()
    table.add_column("Time")
    table.add_column("Value")
    # ... build table from current data
    return table

with Live(generate_table(), refresh_per_second=4, console=console) as live:
    for _ in range(40):
        time.sleep(0.4)
        live.update(generate_table())
```

**Use case**: Real-time monitoring, streaming build output, live dashboards.

---

## 7. Columns

```python
from rich.columns import Columns

items = [Panel(f"Service {i}", expand=True) for i in range(6)]
console.print(Columns(items, equal=True, expand=True))
```

---

## 8. Layout (Split-Screen Dashboards)

```python
from rich.layout import Layout

layout = Layout()
layout.split_column(
    Layout(name="header", size=3),
    Layout(name="body", ratio=1),
    Layout(name="footer", size=5),
)
layout["body"].split_row(
    Layout(name="sidebar", minimum_size=30),
    Layout(name="main", ratio=2),
)
layout["header"].update(Panel("[bold]Dashboard[/]", style="white on blue"))
```

---

## 9. Syntax Highlighting

```python
from rich.syntax import Syntax

code = Syntax.from_path("config.yaml", theme="monokai", line_numbers=True)
console.print(code)

# Or from string
code = Syntax(python_source, "python", theme="monokai", line_numbers=True)
console.print(code)
```

---

## 10. Markdown Rendering

```python
from rich.markdown import Markdown

md = Markdown(readme_text)
console.print(md)
```

---

## 11. Console Markup Quick Reference

```python
# Styles
"[bold]Bold[/]"
"[italic]Italic[/]"
"[underline]Underlined[/]"
"[strike]Strikethrough[/]"

# Colors
"[red]Red[/]"
"[#ff8800]Hex color[/]"
"[bold bright_cyan on dark_blue]Complex[/]"

# Theme styles (preferred — use these over raw colors)
"[success]All good[/]"
"[error]Failed[/]"
"[info]Processing[/]"
"[warning]Caution[/]"

# Links (clickable in supporting terminals)
"[link=https://example.com]Click here[/link]"

# Escaping
"\\[not markup]"
```

---

## 12. Custom Renderables

Implement `__rich_console__` for any Python object:

```python
class ServerStatus:
    def __rich_console__(self, console, options):
        yield "[bold]Server Status Report[/]"
        table = Table("Metric", "Value")
        table.add_row("CPU", "38%")
        table.add_row("Memory", "72%")
        yield table
```

---

## 13. Console Utilities

```python
# JSON pretty-printing
console.print_json(data={"name": "Alice", "role": "admin"})

# Horizontal divider
console.rule("[bold]Results[/]")

# Pager for long output
with console.pager():
    console.print(very_long_text)

# Capture output to string
with console.capture() as capture:
    console.print("[bold]Hello[/]")
text = capture.get()

# Export
html = console.export_html()
svg = console.export_svg(title="My CLI Output")

# Terminal detection
if console.is_terminal:
    console.print("Interactive mode")
```

---

## 14. Logging Integration

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=True,
        markup=True,
    )]
)
log = logging.getLogger("myapp")
```

---

## 15. Combining Components

```python
from rich.console import Group

output = Group(
    Panel("Header Info", border_style="blue"),
    table,
    Panel("Footer: 42 records processed", border_style="dim"),
)
console.print(output)
```

**Pattern**: Use `Group` to vertically stack renderables. Use `Table.grid()` for side-by-side.
