---
name: implement-cli
version: 1.0.0
description: |
  Implement production-grade Python CLI applications using Typer and Rich with
  modern Annotated syntax, semantic themes, composable command groups, and
  professional terminal UX. Use when building command-line tools, developer
  CLIs, terminal utilities, adding CLI commands/subcommands, wiring Rich output
  (tables, progress bars, panels, trees), or packaging CLI apps for distribution.
  Triggers on "CLI", "command-line", "Typer", "Rich", "terminal tool",
  "developer tool", "shell command", "create a CLI", or when Python files
  contain typer.Typer() or rich.console imports.
  Relevant for Python CLI development, developer experience tooling, terminal
  applications, devtools, and shell utilities.
---

# Implement CLI (Typer + Rich)

> Build developer-grade CLI tools with type-safe commands and beautiful terminal output.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/pydantic`, `implement/python`, `test/unit` |
| **Invoked By** | `implement/python`, `design/code` |
| **Key Tools** | Write, Edit, Bash(pytest), Bash(ruff) |
| **Stack** | Typer 0.15+, Rich 13+, Python 3.11+ |

---

## Core Workflow

1. **Scaffold**: Establish project structure with `console.py`, `cli.py`, `commands/`, `core/`
2. **Theme**: Create shared `Console` + semantic `Theme` in `console.py` (single source of truth for all output)
3. **Root App**: Configure `typer.Typer()` with `rich_markup_mode="rich"`, `no_args_is_help=True`, `-h/--help`
4. **Commands**: Implement command modules using `Annotated` pattern, one module per command group
5. **Output**: Select Rich components by data shape — Table for records, Panel for status, Tree for hierarchy, Progress for iteration
6. **Errors**: Wire `CLIError` hierarchy with typed exit codes, stderr for messages, stdout for data
7. **Validate**: Run `ruff check --fix`, `ruff format`, `pytest`
8. **Chain**: Invoke `test/unit` for CliRunner tests, `review/types` for type safety

---

## Decision Tree

```
User Request
    │
    ├─► New CLI project?
    │     └─► Full scaffold (console.py → cli.py → commands/ → core/)
    │           └─► Invoke: implement/pydantic (for data models)
    │
    ├─► Adding command group?
    │     └─► New module in commands/ → add_typer() in cli.py
    │
    ├─► Adding single command?
    │     └─► @app.command() in existing module
    │
    ├─► Rich output needed?
    │     ├─► Tabular data → Table with semantic column styles
    │     ├─► Status/summary → Panel with border_style
    │     ├─► Hierarchy/tree → Tree with guide_style
    │     ├─► Long iteration → Progress or track()
    │     └─► Real-time update → Live display
    │
    └─► Packaging/distribution?
          └─► pyproject.toml with [project.scripts] entry point
```

---

## Project Structure (Canonical)

```
my_cli/
├── pyproject.toml            # Entry point: [project.scripts]
├── src/
│   └── my_cli/
│       ├── __init__.py       # __version__
│       ├── __main__.py       # python -m support
│       ├── cli.py            # Root Typer app, composes sub-typers
│       ├── console.py        # Shared Console + Theme (SINGLE INSTANCE)
│       ├── config.py         # Config loading (TOML, env vars)
│       ├── commands/         # CLI interface layer (thin wrappers)
│       │   ├── __init__.py
│       │   ├── deploy.py     # One module per command group
│       │   └── auth.py
│       └── core/             # Business logic (ZERO CLI imports)
│           ├── deployer.py
│           └── auth_service.py
└── tests/
    ├── conftest.py           # CliRunner fixture
    └── test_deploy.py
```

**Critical separation**: `commands/` = CLI interface (Typer + Rich imports). `core/` = business logic (no CLI imports). Commands are thin wrappers that call core functions and format output.

---

## Implementation Patterns

### Console Module (Always Create First)

```python
# console.py — SINGLE shared instance for entire app
from rich.console import Console
from rich.theme import Theme

APP_THEME = Theme({
    "info":    "dim cyan",
    "warning": "bold yellow",
    "error":   "bold red",
    "success": "bold green",
    "accent":  "bold magenta",
    "muted":   "dim white",
    "key":     "bold cyan",
})

console = Console(theme=APP_THEME)                # stdout — data output
err_console = Console(stderr=True, theme=APP_THEME)  # stderr — messages/status
```

### Root App Configuration

```python
# cli.py
import typer
from .commands import deploy, auth

app = typer.Typer(
    name="mycli",
    help="My developer tool.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
)

app.add_typer(deploy.app, name="deploy", help="Deployment operations")
app.add_typer(auth.app, name="auth", help="Authentication")
```

### Command Module (Annotated Pattern — Always Use)

```python
# commands/deploy.py
from typing import Annotated, Optional
from enum import StrEnum, auto
import typer
from ..console import console, err_console

class OutputFormat(StrEnum):
    json = auto()
    table = auto()

app = typer.Typer(help="Deployment operations")

@app.command()
def start(
    service: Annotated[str, typer.Argument(help="Service to deploy")],
    env: Annotated[str, typer.Option("--env", "-e", help="Target environment")] = "staging",
    format: Annotated[OutputFormat, typer.Option("--format", "-f", case_sensitive=False)] = OutputFormat.table,
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute", help="Simulate without changes")] = False,
):
    """Deploy a [bold]service[/bold] to the target environment."""
    from ..core.deployer import run_deploy  # Lazy import

    err_console.print(f"[info]Deploying {service} to {env}...[/]")
    result = run_deploy(service, env, dry_run=dry_run)

    if format == OutputFormat.json:
        console.print_json(data=result)
    else:
        _render_table(result)
```

### Error Handling

```python
# errors.py
class CLIError(Exception):
    def __init__(self, message: str, exit_code: int = 1, hint: str = ""):
        self.message = message
        self.exit_code = exit_code
        self.hint = hint
        super().__init__(message)

class AuthenticationError(CLIError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, exit_code=2, hint="Run: mycli auth login")

class NotFoundError(CLIError):
    def __init__(self, resource: str):
        super().__init__(f"Not found: {resource}", exit_code=3)
```

### Exit Codes (Unix Convention)

| Code | Meaning | When |
|------|---------|------|
| 0 | Success | Command completed |
| 1 | General error | Catch-all |
| 2 | Bad input / auth | Invalid args, auth failure |
| 3 | Not found | Resource missing |
| 130 | Interrupted | Ctrl+C / SIGINT |

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Complex data models needed | `implement/pydantic` | Field types, validation rules |
| Business logic module | `implement/python` | Domain concepts, function signatures |
| Implementation complete | `test/unit` | CliRunner patterns, exit code assertions |
| Type annotations review | `review/types` | Python 3.11+ typing conventions |
| Code style review | `review/style` | Ruff rules, naming conventions |

---

## Patterns & Anti-Patterns

### ✅ Do

- **Always** use `Annotated[T, typer.Option(...)]` — never bare defaults
- **Always** create `console.py` with shared `Console` + `Theme` before any commands
- **Always** separate stdout (data) from stderr (messages) — enables clean piping
- **Always** check `ctx.resilient_parsing` in validation callbacks before doing I/O
- **Always** use `StrEnum` for choice parameters, not raw strings
- **Always** support `--format json` for machine-readable output on data commands
- Lazy-import heavy dependencies inside command functions for fast startup
- Use `is_eager=True` on `--version` callback to run before validation

### ❌ Don't

- **Never** put business logic in command functions — commands are thin wrappers
- **Never** use `typer.echo()` — always use `rich.console.Console`
- **Never** print errors to stdout — use `Console(stderr=True)`
- **Never** hardcode colors inline — use Theme styles (`[success]`, `[error]`)
- **Never** skip exit code assertions in tests
- **Never** use module-level mutable dicts for state — use `ctx.obj` with a dataclass
- **Never** ignore `KeyboardInterrupt` — catch and exit with code 130

---

## Deep References

For detailed guidance, load these refs as needed:

- **[patterns.md](refs/patterns.md)**: State management, async, plugins, config, version callbacks, global options
- **[rich-components.md](refs/rich-components.md)**: Tables, panels, trees, progress bars, Live displays, custom renderables
- **[testing.md](refs/testing.md)**: CliRunner patterns, exit code testing, env vars, isolated filesystem, Rich output capture
- **[packaging.md](refs/packaging.md)**: pyproject.toml, entry points, **main**.py, shell completion, distribution

---

## Quality Gates

Before completing any CLI implementation:

- [ ] `console.py` exists with shared Console + semantic Theme
- [ ] All commands use `Annotated` pattern (no bare defaults)
- [ ] Business logic lives in `core/`, not in command functions
- [ ] stdout = data only, stderr = messages/status/errors
- [ ] Error hierarchy with typed exit codes (0, 1, 2, 3, 130)
- [ ] `--format json` supported on data-returning commands
- [ ] `-h/--help` enabled via context_settings
- [ ] `pretty_exceptions_show_locals=False` set on root app
- [ ] Tests assert `result.exit_code` on every test case
- [ ] `ruff check` and `ruff format` pass
