# Testing Reference — implement-cli

> Patterns for testing Typer + Rich CLI applications with CliRunner.

---

## Setup

### conftest.py Fixtures

```python
import pytest
from typer.testing import CliRunner
from my_cli.cli import app

@pytest.fixture
def runner():
    """CliRunner with separated stdout/stderr."""
    return CliRunner(mix_stderr=False)

@pytest.fixture
def cli(runner):
    """Shorthand for invoking the app."""
    def invoke(*args, **kwargs):
        return runner.invoke(app, list(args), **kwargs)
    return invoke
```

---

## Core Testing Patterns

### 1. Basic Command Test

```python
def test_deploy_success(runner):
    result = runner.invoke(app, ["deploy", "start", "web-api", "--env", "staging"])
    assert result.exit_code == 0
    assert "Deploying" in result.output
```

**Rule**: ALWAYS assert `result.exit_code` first. This catches errors that produce output but fail silently.

### 2. All Arguments Must Be Strings

```python
# ✅ Correct — all args are strings
result = runner.invoke(app, ["create", "--port", "8080"])

# ❌ Wrong — integers cause errors
result = runner.invoke(app, ["create", "--port", 8080])
```

### 3. Exit Code Assertions

```python
def test_not_found_returns_3(runner):
    result = runner.invoke(app, ["get", "nonexistent-id"])
    assert result.exit_code == 3

def test_bad_input_returns_2(runner):
    result = runner.invoke(app, ["deploy", "--env", "invalid"])
    assert result.exit_code == 2

def test_success_returns_0(runner):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
```

### 4. Stderr vs Stdout Assertions

With `mix_stderr=False`, use `result.output` for stdout and `result.stderr` for stderr:

```python
def test_data_on_stdout_messages_on_stderr(runner):
    result = runner.invoke(app, ["list", "--format", "json"])
    assert result.exit_code == 0

    # Data appears on stdout
    import json
    data = json.loads(result.output)
    assert isinstance(data, list)

    # Status messages appear on stderr
    assert "Fetching" in result.stderr
```

### 5. Interactive Input Simulation

```python
def test_confirm_delete(runner):
    result = runner.invoke(app, ["delete", "my-resource"], input="y\n")
    assert result.exit_code == 0
    assert "Deleted" in result.output

def test_abort_delete(runner):
    result = runner.invoke(app, ["delete", "my-resource"], input="n\n")
    assert result.exit_code == 1
```

### 6. Environment Variable Testing

```python
def test_token_from_env(runner):
    result = runner.invoke(
        app,
        ["deploy", "start", "api"],
        env={"MY_CLI_TOKEN": "test-token-123"},
    )
    assert result.exit_code == 0

def test_missing_token_fails(runner):
    result = runner.invoke(app, ["deploy", "start", "api"])
    assert result.exit_code != 0
```

### 7. Isolated Filesystem

```python
def test_init_creates_config(runner, tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "config.toml").exists()
```

### 8. JSON Output Validation

```python
import json

def test_json_output_structure(runner):
    result = runner.invoke(app, ["list", "--format", "json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert all("name" in item for item in data)
    assert all("status" in item for item in data)
```

### 9. Debugging Failures

```python
def test_debug_mode(runner):
    result = runner.invoke(app, ["failing-command"], catch_exceptions=False)
    # Raises the actual exception instead of capturing it
```

---

## Parametrized Tests

### Cover Multiple Command Variants

```python
@pytest.mark.parametrize("args,expected_code,expected_text", [
    (["list"], 0, "No items"),
    (["list", "--format", "json"], 0, "[]"),
    (["get", "nonexistent"], 3, "Not found"),
    (["deploy", "start", "api", "--env", "staging"], 0, "Deploying"),
])
def test_commands(runner, args, expected_code, expected_text):
    result = runner.invoke(app, args)
    assert result.exit_code == expected_code
    assert expected_text in result.output or expected_text in result.stderr
```

### Cover Output Formats

```python
@pytest.mark.parametrize("fmt", ["table", "json", "csv"])
def test_output_formats(runner, fmt):
    result = runner.invoke(app, ["list", "--format", fmt])
    assert result.exit_code == 0
    assert len(result.output.strip()) > 0
```

---

## Testing Rich Output

### Capture Rich Console Output

Don't assert on ANSI codes. Use Rich's capture mechanism:

```python
from io import StringIO
from rich.console import Console

def test_table_rendering():
    output = StringIO()
    test_console = Console(file=output, force_terminal=True)
    render_status_table(test_console, mock_data)
    rendered = output.getvalue()
    assert "Healthy" in rendered
    assert "my-service" in rendered
```

### Test With Dependency Injection

Design commands to accept a console parameter for testability:

```python
# In production code
def render_status(data, console=None):
    console = console or get_default_console()
    table = Table("Service", "Status")
    for item in data:
        table.add_row(item["name"], item["status"])
    console.print(table)

# In test
def test_render_status():
    output = StringIO()
    test_console = Console(file=output)
    render_status(mock_data, console=test_console)
    assert "my-service" in output.getvalue()
```

---

## Testing Tips Summary

| Tip | Detail |
|-----|--------|
| All args are strings | `["--port", "8080"]` not `["--port", 8080]` |
| Always assert exit_code | Before checking output content |
| `mix_stderr=False` | Separate stdout/stderr for proper assertions |
| `catch_exceptions=False` | For debugging — raises real exceptions |
| `input="y\n"` | Simulate interactive prompts |
| `env={...}` | Test environment variable behavior |
| Don't assert ANSI | Use Rich capture or strip codes |
| Parametrize variants | Cover formats, error cases, edge cases |
| Isolated filesystem | Use `tmp_path` for file operations |
