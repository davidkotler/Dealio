# Jinja2 Python Reference

> Environment configuration, custom extensions, performance, async, and testing.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Loaders](#loaders)
3. [Undefined Variable Handling](#undefined-variable-handling)
4. [Custom Filters](#custom-filters)
5. [Custom Tests](#custom-tests)
6. [Global Functions and Variables](#global-functions-and-variables)
7. [Writing Extensions](#writing-extensions)
8. [Performance Optimization](#performance-optimization)
9. [Async Rendering](#async-rendering)
10. [NativeEnvironment](#nativeenvironment)
11. [Custom Delimiters](#custom-delimiters)
12. [Testing Templates](#testing-templates)
13. [Error Handling](#error-handling)

---

## Environment Setup

The `Environment` is the central configuration object. Create one per application and reuse it — it holds the template cache, configuration, filters, tests, and globals.

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "htm", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `loader` | None | How to find templates |
| `autoescape` | False | Enable HTML escaping (always enable for HTML output) |
| `trim_blocks` | False | Remove first newline after block tags |
| `lstrip_blocks` | False | Strip leading whitespace before block tags |
| `undefined` | `Undefined` | How to handle undefined variables |
| `extensions` | `[]` | List of extensions to load |
| `bytecode_cache` | None | Persistent cache for compiled templates |
| `auto_reload` | True | Check for source changes (disable in production) |

Modifying an Environment after loading templates leads to undefined behavior — configure everything at creation time.

---

## Loaders

Loaders locate and read template source code.

| Loader | Use case | Example |
|--------|----------|---------|
| `FileSystemLoader` | Read from directories | `FileSystemLoader("templates")` |
| `PackageLoader` | Read from Python package | `PackageLoader("myapp", "templates")` |
| `DictLoader` | Read from dict (testing) | `DictLoader({"base.html": "..."})` |
| `FunctionLoader` | Call function for source | `FunctionLoader(my_func)` |
| `ChoiceLoader` | Try multiple loaders | See below |
| `PrefixLoader` | Namespace by prefix | `PrefixLoader({"admin": loader1})` |

### ChoiceLoader — Override Pattern

User overrides fall back to defaults:
```python
from jinja2 import ChoiceLoader, FileSystemLoader

loader = ChoiceLoader([
    FileSystemLoader("/user/themes/custom"),   # checked first
    FileSystemLoader("/app/templates/default"), # fallback
])
```

### Custom Loader

For database-backed or API-sourced templates, subclass `BaseLoader`:
```python
from jinja2 import BaseLoader, TemplateNotFound

class DatabaseLoader(BaseLoader):
    def __init__(self, db):
        self.db = db

    def get_source(self, environment, template):
        row = self.db.get_template(template)
        if row is None:
            raise TemplateNotFound(template)
        return row.source, template, lambda: row.updated_at == self.db.get_updated(template)
```

Return `(source_string, filename, uptodate_callable)`. The up-to-date callable returns True if the cached version is still valid.

---

## Undefined Variable Handling

By default, undefined variables silently render as empty strings — a common source of invisible bugs.

| Class | Behavior | Best for |
|-------|----------|----------|
| `Undefined` (default) | Silent empty string | Production (risky) |
| `DebugUndefined` | Renders `{{ variable_name }}` as placeholder | Visual debugging |
| `StrictUndefined` | Raises `UndefinedError` | Development and CI |
| `ChainableUndefined` | Returns self on attribute access | Nested `default` filter chains |

```python
from jinja2 import StrictUndefined, DebugUndefined, make_logging_undefined

# Development — fail fast on typos
env = Environment(undefined=StrictUndefined)

# Production — log undefined access without crashing
LoggingUndefined = make_logging_undefined(logger=logging.getLogger("jinja2"))
env = Environment(undefined=LoggingUndefined)
```

Use `StrictUndefined` during development — it catches typos and missing context variables at render time.

---

## Custom Filters

Register Python functions as template filters. Filters receive the piped value as their first argument:

```python
def datetime_format(value, fmt="%B %d, %Y"):
    """Format a datetime object."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime(fmt)

def pluralize(count, singular, plural=None):
    """Return singular or plural form."""
    if plural is None:
        plural = singular + "s"
    return singular if count == 1 else plural

# Register
env.filters["datetime"] = datetime_format
env.filters["pluralize"] = pluralize
```

```jinja
{{ post.created_at | datetime("%Y-%m-%d") }}
{{ count }} {{ count | pluralize("comment") }}
```

### Context-Aware Filters

Use decorators to access the evaluation context or environment:

```python
from jinja2 import pass_eval_context, pass_environment
from markupsafe import Markup, escape

@pass_eval_context
def nl2br(eval_ctx, value):
    """Convert newlines to <br> tags, respecting autoescaping."""
    result = escape(value).replace("\n", Markup("<br>\n"))
    return Markup(result) if eval_ctx.autoescape else result

@pass_environment
def env_filter(environment, value):
    """Access environment settings."""
    return value

env.filters["nl2br"] = nl2br
```

`@pass_eval_context` is important when your filter produces HTML — it respects the current autoescaping state.

---

## Custom Tests

Tests are used with `is` in conditionals and return booleans:

```python
import re

def is_valid_email(value):
    return bool(re.match(r"^[\w.-]+@[\w.-]+\.\w+$", str(value)))

def is_palindrome(value):
    s = str(value).lower().replace(" ", "")
    return s == s[::-1]

env.tests["valid_email"] = is_valid_email
env.tests["palindrome"] = is_palindrome
```

```jinja
{% if email is valid_email %}OK{% endif %}
```

---

## Global Functions and Variables

Globals are available in every template without being passed in context. They also propagate into `{% import %}`-ed templates (unlike context variables):

```python
from datetime import datetime

env.globals["now"] = datetime.utcnow
env.globals["site_name"] = "My App"
env.globals["url_for"] = url_for_function
```

```jinja
<footer>&copy; {{ now().year }} {{ site_name }}</footer>
```

Use globals for values/functions that truly belong everywhere. For request-specific data, use framework context processors instead.

---

## Writing Extensions

Extensions add custom tags by hooking into the parser. Use when filters, tests, and macros are insufficient.

```python
from jinja2 import nodes
from jinja2.ext import Extension

class CacheExtension(Extension):
    tags = {"cache"}

    def __init__(self, environment):
        super().__init__(environment)
        environment.extend(fragment_cache=None)

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        args = [parser.parse_expression()]
        if parser.stream.current.test("comma"):
            next(parser.stream)
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(300))
        body = parser.parse_statements(["name:endcache"], drop_needle=True)
        return nodes.CallBlock(
            self.call_method("_cache_support", args), [], [], body
        ).set_lineno(lineno)

    def _cache_support(self, name, timeout, caller):
        cache = self.environment.fragment_cache
        if cache is None:
            return caller()
        rv = cache.get(name)
        if rv is not None:
            return rv
        rv = caller()
        cache.set(name, rv, timeout)
        return rv
```

```python
env = Environment(extensions=[CacheExtension])
```

Key parser methods: `parse_expression()`, `parse_statements()`, `parser.stream` for token access. Configure via `environment.extend()` — extension constructors don't accept custom arguments.

### Useful Built-in Extensions

| Extension | Tag | Purpose |
|-----------|-----|---------|
| `jinja2.ext.do` | `{% do %}` | Expression statements (`{% do list.append(x) %}`) |
| `jinja2.ext.loopcontrols` | `{% break %}`, `{% continue %}` | Loop control |
| `jinja2.ext.debug` | `{% debug %}` | Dump current context |
| `jinja2.ext.i18n` | `{% trans %}` | Internationalization |

---

## Performance Optimization

### Three Key Levers

**1. Reuse the Environment** — Creating a new one per render destroys the template cache:

```python
# BAD — ~8x slower
def render(name, ctx):
    env = Environment(loader=FileSystemLoader("templates"))
    return env.get_template(name).render(ctx)

# GOOD — cached
env = Environment(loader=FileSystemLoader("templates"))
def render(name, ctx):
    return env.get_template(name).render(ctx)
```

**2. Bytecode Caching** — Persists compiled templates across process restarts:

```python
from jinja2 import FileSystemBytecodeCache

env = Environment(
    loader=FileSystemLoader("templates"),
    bytecode_cache=FileSystemBytecodeCache("/var/cache/jinja2"),
)
```

Can reduce per-render time from ~50ms to ~6ms. The cache auto-invalidates when template source changes. For distributed environments, use `MemcachedBytecodeCache`.

**3. Disable auto_reload in production:**

```python
env = Environment(
    loader=FileSystemLoader("templates"),
    auto_reload=False,  # skip filesystem stat per render
)
```

### Template-Level Optimization

- Cache expensive filter chains with `{% set %}` instead of repeating them
- Prefer macros over includes in hot loops (includes trigger loader lookups per iteration)
- Use `template.stream()` for large output to yield chunks instead of building everything in memory
- Keep inheritance depth to 3 levels or fewer
- Move complex data transformations to Python — pass pre-computed results

---

## Async Rendering

For async frameworks (FastAPI, Starlette, aiohttp):

```python
env = Environment(
    loader=FileSystemLoader("templates"),
    enable_async=True,
)

async def render():
    template = env.get_template("page.html")
    return await template.render_async(
        user=await get_user(),
        posts=await fetch_posts(),
    )
```

With `enable_async=True`, Jinja2 automatically awaits async functions called in templates and handles async iterables in `for` loops:

```jinja
{{ async_func() }}           {# awaited automatically #}
{% for item in async_iter %} {# async iteration #}
    {{ item }}
{% endfor %}
```

Keep templates free from I/O operations — prepare all data in the handler and pass it as context.

---

## NativeEnvironment

Renders to native Python types instead of strings — useful for configuration generation and data pipelines:

```python
from jinja2.nativetypes import NativeEnvironment

env = NativeEnvironment()

template = env.from_string("{{ x + y }}")
result = template.render(x=1, y=2)
assert result == 3          # int, not "3"
assert type(result) is int
```

Uses `ast.literal_eval()` internally for safe type conversion. Supports async via `render_async()`.

---

## Custom Delimiters

When `{{ }}` conflicts with the target output format (LaTeX, Go templates, etc.):

```python
env = Environment(
    variable_start_string="<<",
    variable_end_string=">>",
    block_start_string="<%",
    block_end_string="%>",
)
```

```
<% for item in items %>
    << item.name >>
<% endfor %>
```

---

## Testing Templates

Test by rendering with known context and asserting on output:

```python
import pytest
from jinja2 import Environment, DictLoader, StrictUndefined

@pytest.fixture
def env():
    return Environment(
        loader=DictLoader({
            "greeting.html": "Hello, {{ name }}!",
            "list.html": "{% for item in items %}{{ item }}{% else %}empty{% endfor %}",
        }),
        undefined=StrictUndefined,
    )

def test_greeting(env):
    result = env.get_template("greeting.html").render(name="World")
    assert result == "Hello, World!"

def test_empty_list_fallback(env):
    result = env.get_template("list.html").render(items=[])
    assert result == "empty"

def test_custom_filter():
    env = Environment()
    env.filters["double"] = lambda v: v * 2
    assert env.from_string("{{ x | double }}").render(x=5) == "10"
```

Use `DictLoader` for isolated tests. Use `StrictUndefined` to catch missing variables. For HTML assertions, parse with BeautifulSoup.

---

## Error Handling

Jinja2 exceptions point to the correct line in the template source:

```python
from jinja2 import TemplateError, TemplateNotFound, UndefinedError

try:
    output = template.render(context)
except UndefinedError as e:
    logger.error(f"Missing template variable: {e}")
except TemplateNotFound as e:
    logger.error(f"Template not found: {e}")
except TemplateError as e:
    logger.error(f"Template error: {e}")
```

| Exception | Cause |
|-----------|-------|
| `UndefinedError` | Accessing undefined variable (with `StrictUndefined`) |
| `TemplateNotFound` | Template file doesn't exist |
| `TemplateSyntaxError` | Invalid template syntax |
| `TemplateRuntimeError` | Runtime error (e.g., required block not overridden) |
| `TemplateAssertionError` | Conflicting extension names or filter registration |

The debug extension (`jinja2.ext.debug`) adds `{% debug %}` which dumps the full template context — useful during development.
