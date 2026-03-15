# Packaging Reference — implement-cli

> Packaging, entry points, and distribution for Typer CLI applications.

---

## pyproject.toml (Complete Template)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-cli"
version = "1.0.0"
description = "A production-grade developer CLI tool"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.15.0",   # Includes rich + shellingham
    "rich>=13.0.0",
]

[project.scripts]
mycli = "my_cli.cli:app"    # Entry point: package.module:typer_app

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
    "ty",
]

[tool.hatch.build.targets.wheel]
packages = ["src/my_cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.ty]
strict = true
python_version = "3.11"
```

---

## Entry Points

### __main__.py (Enables `python -m my_cli`)

```python
# src/my_cli/__main__.py
from my_cli.cli import app

if __name__ == "__main__":
    app()
```

### __init__.py (Version)

```python
# src/my_cli/__init__.py
__version__ = "1.0.0"
```

### cli.py (Root App)

```python
# src/my_cli/cli.py
import typer
from .commands import deploy, auth, config

app = typer.Typer(
    name="mycli",
    help="My developer tool.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)

app.add_typer(deploy.app, name="deploy", help="Deployment operations")
app.add_typer(auth.app, name="auth", help="Authentication")
app.add_typer(config.app, name="config", help="Configuration")
```

---

## Shell Completion

Typer generates completions for Bash, Zsh, Fish, and PowerShell:

```bash
# Install completion for current shell
mycli --install-completion

# Show completion script (for manual setup)
mycli --show-completion
```

Users can also set: `export _MYCLI_COMPLETE=bash_source`

---

## Installation Modes

### Development (Editable)

```bash
pip install -e ".[dev]"
```

### Production

```bash
pip install my-cli
```

### From Git

```bash
pip install git+https://github.com/org/my-cli.git
```

---

## Pretty Exceptions Configuration

### Production Settings

```python
app = typer.Typer(
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,  # NEVER show locals in prod
    pretty_exceptions_short=True,         # Suppress Click/Typer internals
)
```

### Debug Mode

Set environment variable to disable Rich tracebacks entirely:

```bash
export _TYPER_STANDARD_TRACEBACK=1
```

---

## Typer CLI API Quick Reference

| API | Purpose |
|-----|---------|
| `typer.Typer()` | Create app/sub-app |
| `@app.command()` | Register a command |
| `@app.callback()` | App-level options & help text |
| `app.add_typer()` | Compose sub-apps |
| `typer.Argument()` | Configure positional args |
| `typer.Option()` | Configure `--options` |
| `typer.Context` | Access Click context |
| `typer.Exit(code=N)` | Exit with code |
| `typer.Abort()` | Abort execution |
| `typer.confirm()` | Y/N confirmation |
| `typer.prompt()` | Interactive prompt |
| `typer.BadParameter()` | Validation error |
| `typer.get_app_dir()` | Platform config dir |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .
      - run: ty src/
      - run: pytest --cov=my_cli --cov-report=xml
```

---

## Distribution Checklist

- [ ] `pyproject.toml` has `[project.scripts]` entry point
- [ ] `__main__.py` enables `python -m` invocation
- [ ] `__init__.py` defines `__version__`
- [ ] `--version` flag reads from `importlib.metadata`
- [ ] `pretty_exceptions_show_locals=False` in production
- [ ] Shell completion works via `--install-completion`
- [ ] README includes installation and usage instructions
- [ ] CI runs ruff, ty, and pytest
