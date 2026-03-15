# Patterns Reference — implement-cli

> Advanced patterns for production Typer + Rich CLI applications.

---

## 1. State Management Patterns

### Pattern 1A: Context Object (Recommended for Multi-Command Apps)

Use `typer.Context.obj` with a dataclass for type-safe state passing:

```python
from dataclasses import dataclass

@dataclass
class AppContext:
    verbose: int
    debug: bool
    token: str
    config: dict

@app.callback()
def main(
    ctx: typer.Context,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True,
        help="Increase verbosity (-v, -vv)")] = 0,
    debug: Annotated[bool, typer.Option("--debug")] = False,
    token: Annotated[str, typer.Option(envvar="APP_TOKEN",
        help="Auth token")] = "",
):
    """My CLI — a production-grade developer tool."""
    ctx.obj = AppContext(
        verbose=verbose,
        debug=debug,
        token=token,
        config=load_config(),
    )

@app.command()
def deploy(ctx: typer.Context, service: str):
    """Deploy a service."""
    app_ctx: AppContext = ctx.obj
    if app_ctx.verbose >= 1:
        err_console.print(f"[muted]Token: {app_ctx.token[:8]}...[/]")
```

### Pattern 1B: Simple Module State (Small Apps Only)

For single-file CLIs with few commands:

```python
state = {"verbose": False}

@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False):
    state["verbose"] = verbose
```

**Caveat**: Avoid for multi-module apps — use `ctx.obj` instead.

---

## 2. Version Callback Pattern

```python
from importlib.metadata import version as pkg_version

def version_callback(value: bool):
    if value:
        v = pkg_version("my-cli")
        from rich import print as rprint
        rprint(f"[bold green]my-cli[/] version [cyan]{v}[/]")
        raise typer.Exit()

@app.callback()
def main(
    version: Annotated[Optional[bool], typer.Option(
        "--version", "-V",
        callback=version_callback,
        is_eager=True,  # Process BEFORE all other params
        help="Show version and exit",
    )] = None,
):
    """My CLI application."""
```

**Key**: `is_eager=True` ensures version prints even if required params are missing.

---

## 3. Default Action (No Subcommand Given)

```python
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """My CLI — shows status when no command given."""
    if ctx.invoked_subcommand is None:
        show_status()  # Default behavior
```

---

## 4. Custom Validation Callbacks

```python
import re

def validate_email(ctx: typer.Context, value: str) -> str:
    if ctx.resilient_parsing:  # CRITICAL: skip during shell completion
        return value
    if not re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", value):
        raise typer.BadParameter(f"Invalid email: {value}")
    return value

def validate_port(ctx: typer.Context, value: int) -> int:
    if ctx.resilient_parsing:
        return value
    if not (1 <= value <= 65535):
        raise typer.BadParameter(f"Port must be 1-65535, got {value}")
    return value

@app.command()
def serve(
    email: Annotated[str, typer.Option(callback=validate_email)],
    port: Annotated[int, typer.Option(callback=validate_port)] = 8080,
): ...
```

**Rule**: ALWAYS check `ctx.resilient_parsing` first — shell completion invokes callbacks with this flag.

---

## 5. Confirmation and Interactive Prompts

```python
@app.command()
def destroy(
    env: str,
    force: Annotated[bool, typer.Option("--force", "-f",
        help="Skip confirmation (required in non-interactive mode)")] = False,
):
    """Destroy an environment permanently."""
    if not force:
        if not sys.stdin.isatty():
            err_console.print("[error]Use --force in non-interactive mode[/]")
            raise typer.Exit(code=1)
        typer.confirm(f"Destroy {env}? This cannot be undone", abort=True)
    perform_destroy(env)
```

**Pattern**: Always provide `--force` / `--yes` for CI/CD pipeline compatibility.

---

## 6. Global Error Handling Wrapper

```python
import sys
from functools import wraps

def handle_errors(func):
    """Decorator for consistent error handling across commands."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CLIError as e:
            err_console.print(f"[error]Error:[/] {e.message}")
            if e.hint:
                err_console.print(f"[muted]Hint: {e.hint}[/]")
            raise typer.Exit(code=e.exit_code)
        except KeyboardInterrupt:
            err_console.print("\n[warning]Aborted.[/]")
            raise typer.Exit(code=130)
        except Exception as e:
            err_console.print(f"[error]Unexpected error:[/] {e}")
            err_console.print_exception(show_locals=False)
            raise typer.Exit(code=1)
    return wrapper

@app.command()
@handle_errors
def deploy(service: str): ...
```

### Alternative: Entry-Point Error Handling

```python
# __main__.py
from rich.panel import Panel

def main_entry():
    try:
        app()
    except KeyboardInterrupt:
        err_console.print("\n[warning]Interrupted[/]")
        raise SystemExit(130)
    except CLIError as e:
        err_console.print(Panel(
            f"[error]{e.message}[/]\n\n[muted]Hint: {e.hint}[/]",
            title="[error]Error[/]", border_style="red"
        ))
        raise SystemExit(e.exit_code)
```

---

## 7. Configuration Management

```python
# config.py
from pathlib import Path
from functools import lru_cache
import tomllib  # Python 3.11+

APP_NAME = "mycli"
CONFIG_DIR = Path.home() / f".config/{APP_NAME}"
CONFIG_FILE = CONFIG_DIR / "config.toml"

@lru_cache()
def load_config() -> dict:
    """Load config with environment variable overrides."""
    config = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "rb") as f:
            config = tomllib.load(f)

    # Env var overrides: MYCLI_TOKEN, MYCLI_HOST, etc.
    import os
    prefix = APP_NAME.upper().replace("-", "_")
    for key, value in os.environ.items():
        if key.startswith(f"{prefix}_"):
            config_key = key[len(prefix) + 1:].lower()
            config[config_key] = value

    return config

def save_config(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import tomli_w
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)
```

**Alternative**: Use `typer.get_app_dir("mycli")` for platform-appropriate paths.

---

## 8. Lazy Import Pattern (Fast Startup)

```python
@app.command()
def analyze(path: Path):
    """Analyze a dataset — imports pandas only when called."""
    from rich.progress import track
    import pandas as pd  # Heavy import deferred

    df = pd.read_csv(path)
    for col in track(df.columns, description="Analyzing..."):
        process_column(df[col])
```

**Rule**: Defer heavy imports (`pandas`, `boto3`, `requests`) to command bodies. Startup < 100ms.

---

## 9. Async Command Pattern

Typer does not natively support `async def` commands. Use `asyncio.run()`:

```python
import asyncio

async def _async_deploy(service: str, env: str):
    async with aiohttp.ClientSession() as session:
        await session.post(f"https://api.example.com/deploy/{service}/{env}")

@app.command()
def deploy(service: str, env: str = "staging"):
    """Deploy asynchronously."""
    asyncio.run(_async_deploy(service, env))
```

---

## 10. Plugin / Extension Architecture

```python
# In the main app:
from importlib.metadata import entry_points

def load_plugins(app: typer.Typer):
    for ep in entry_points(group="mycli.plugins"):
        plugin_app = ep.load()
        app.add_typer(plugin_app, name=ep.name)

# In a plugin's pyproject.toml:
# [project.entry-points."mycli.plugins"]
# my-plugin = "mycli_plugin_foo:app"
```

---

## 11. Verbosity / Quiet Pattern

```python
import logging
from rich.logging import RichHandler

def setup_logging(verbosity: int = 0):
    level_map = {-1: logging.WARNING, 0: logging.INFO, 1: logging.DEBUG}
    level = level_map.get(verbosity, logging.DEBUG)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            console=Console(stderr=True),
            rich_tracebacks=True,
            tracebacks_suppress=[typer, click],
            show_path=verbosity >= 1,
            markup=True,
        )],
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

@app.callback()
def main(
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
):
    setup_logging(-1 if quiet else verbose)
```

**Usage**: `-q` = warnings only, default = info, `-v` = debug, `-vv` = debug with locals.

---

## 12. Machine-Readable Output Pattern

```python
import json
import sys

@app.command()
def list_services(
    format: Annotated[str, typer.Option("--format", "-f",
        help="Output format")] = "table",
):
    services = fetch_services()

    # Auto-detect piping → default to JSON
    if not sys.stdout.isatty() and format == "table":
        format = "json"

    if format == "json":
        print(json.dumps(services, indent=2))  # Clean stdout, no Rich
    elif format == "csv":
        for s in services:
            print(f"{s['name']},{s['status']},{s['uptime']}")
    else:
        table = Table("Service", "Status", "Uptime")
        for s in services:
            table.add_row(s["name"], s["status"], s["uptime"])
        console.print(table)
```

**Rule**: Rich auto-strips ANSI when piped. For JSON/CSV, use plain `print()` to avoid any Rich formatting.

---

## 13. File and Path Parameters

```python
from pathlib import Path

@app.command()
def process(
    input_file: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False,
        readable=True, resolve_path=True,
        help="Input file to process",
    )],
    output_dir: Annotated[Path, typer.Option(
        "--output", "-o",
        file_okay=False, dir_okay=True, resolve_path=True,
    )] = Path("."),
):
    output_dir.mkdir(parents=True, exist_ok=True)
    ...
```

---

## 14. Shell Completion

```python
def complete_env(incomplete: str) -> list[tuple[str, str]]:
    envs = [
        ("staging", "The staging environment"),
        ("production", "The production environment"),
        ("development", "Local development"),
    ]
    return [(n, h) for n, h in envs if n.startswith(incomplete)]

@app.command()
def deploy(
    env: Annotated[str, typer.Argument(
        help="Target environment",
        autocompletion=complete_env,
    )],
): ...
```

Install: `mycli --install-completion`. Show: `mycli --show-completion`.

---

## 15. Rich Help Panels (Organize Options)

```python
@app.command(epilog="Made with :heart: by [blue]MyTeam[/]")
def deploy(
    service: Annotated[str, typer.Argument(help="Service name")],
    env: Annotated[str, typer.Option(help="Environment")] = "staging",
    dry_run: Annotated[bool, typer.Option(
        help="Simulate only",
        rich_help_panel="Advanced Options"
    )] = False,
    timeout: Annotated[int, typer.Option(
        help="Timeout seconds",
        rich_help_panel="Advanced Options"
    )] = 60,
):
    """[bold]Deploy[/bold] a service to the target environment."""
```
