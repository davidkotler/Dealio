---
name: implement-jinja2
version: 1.0.0
description: |
  Implement, improve, and optimize Jinja2 templates and the Python code that renders them.
  Use this skill whenever working with Jinja2 — writing new templates, refactoring existing ones,
  building template inheritance hierarchies, creating macro libraries, writing custom filters or tests,
  configuring Environment objects, optimizing rendering performance, or debugging template issues.
  Also use when generating any text output through Jinja2: HTML, emails, config files, YAML, SQL, or code.
  If the task involves .html/.j2/.jinja2 template files or Python code that imports from jinja2, this skill applies.
  Trigger on keywords: jinja, template, macro, filter, block, extends, include, autoescape, Environment.
---

# Jinja2 Implementation

> Templates are code — give them the same rigor as any Python module.

| Aspect | Details |
|--------|---------|
| **Scope** | Jinja2 templates (.html, .j2, .jinja2) + Python rendering code |
| **Framework** | Agnostic — Flask, FastAPI, Ansible, dbt, standalone |
| **References** | [refs/templates.md](refs/templates.md) (syntax, patterns), [refs/python.md](refs/python.md) (Environment, extensions, perf) |

---

## Core Workflow

1. **Understand the output format** — HTML, email, config, SQL? This drives whitespace control, escaping, and delimiter choices.
2. **Read existing templates** — Before writing, understand the inheritance tree, macro libraries, and naming conventions already in place.
3. **Design the composition** — Decide inheritance vs include vs import vs inline. See the decision tree below.
4. **Implement** — Write templates and Python code following the patterns in this skill.
5. **Optimize** — Cache filter results, flatten deep nesting, avoid repeated computation.

---

## Template Composition — Decision Tree

Choosing the right composition mechanism is the most impactful design decision in Jinja2. Each mechanism solves a different problem, and using the wrong one creates coupling, duplication, or invisible bugs.

```
Need to reuse template content?
    │
    ├─► Shared page structure (header, footer, nav)?
    │       └─► Template inheritance (extends + blocks)
    │           Reason: blocks allow child overrides at defined extension points
    │
    ├─► Parameterized component (form field, card, badge)?
    │       └─► Macro (import as namespace)
    │           Reason: macros accept arguments and produce isolated, reusable output
    │
    ├─► Static partial (footer HTML, legal text)?
    │       └─► Include
    │           Reason: embeds rendered output, shares context, no parameters needed
    │
    └─► Wrapper that accepts arbitrary inner content?
            └─► Macro + call block (caller())
                Reason: call blocks pass content *into* the macro, enabling slot patterns
```

### When NOT to use each

- **Don't use inheritance** for small reusable components — macros are lighter.
- **Don't use include** for parameterized content — use macros instead. Includes share the parent context implicitly, creating hidden dependencies.
- **Don't use import with context** unless truly necessary — it creates implicit coupling between templates.

---

## Template Patterns

### Inheritance — The Three-Tier Pattern

Most projects need at most three levels. Going deeper makes debugging painful because block resolution cascades through every level, and finding which template actually defines a block becomes a search problem.

```jinja
{# base.html — Level 1: site-wide skeleton #}
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default{% endblock %} — Site</title>
    {% block head_extra %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock content %}
    {% block scripts %}{% endblock scripts %}
</body>
</html>

{# layouts/two_column.html — Level 2: layout variant #}
{% extends "base.html" %}
{% block content %}
<div class="sidebar">{% block sidebar %}{% endblock sidebar %}</div>
<div class="main">{% block main_content %}{% endblock main_content %}</div>
{% endblock content %}

{# pages/dashboard.html — Level 3: concrete page #}
{% extends "layouts/two_column.html" %}
{% block title %}Dashboard{% endblock %}
{% block main_content %}<h1>Dashboard</h1>{% endblock main_content %}
```

Use `super()` to augment parent blocks instead of replacing them:
```jinja
{% block scripts %}
    {{ super() }}
    <script src="/js/dashboard.js"></script>
{% endblock scripts %}
```

Use named `{% endblock name %}` tags — they cost nothing and prevent mismatched-block bugs in deeply nested templates.

### Macros — Component Pattern

Macros are Jinja2's functions. Organize them in dedicated files and import as namespaces:

```jinja
{# macros/forms.html #}
{% macro input(name, type="text", value="", placeholder="", required=false) -%}
<div class="form-group">
    <label for="{{ name }}">{{ name | replace("_", " ") | title }}</label>
    <input type="{{ type }}" name="{{ name }}" id="{{ name }}"
           value="{{ value }}" placeholder="{{ placeholder }}"
           {{ "required" if required }}>
</div>
{%- endmacro %}
```

```jinja
{# pages/register.html #}
{% from "macros/forms.html" import input, select %}
{{ input("email", type="email", required=true) }}
```

Use `import ... as namespace` for clarity when using multiple macros from the same file. Use `from ... import` for selective access.

### Call Blocks — Slot Pattern

When a macro needs to accept arbitrary inner content (like a wrapper or container), use the call block pattern. The `caller()` function renders whatever content is between `{% call %}` and `{% endcall %}`:

```jinja
{% macro card(title, css_class="") %}
<div class="card {{ css_class }}">
    <h3>{{ title }}</h3>
    <div class="card-body">{{ caller() }}</div>
</div>
{% endmacro %}

{% call card("User Profile") %}
    <p>Name: {{ user.name }}</p>
    <p>Email: {{ user.email }}</p>
{% endcall %}
```

### The namespace() Pattern — Loop Scoping

Variables set inside `{% for %}` loops don't propagate outside — this is Jinja2's most common gotcha. The `namespace()` object solves it because attribute mutations on namespace objects survive scope boundaries:

```jinja
{% set ns = namespace(total=0, found=false) %}
{% for item in items %}
    {% set ns.total = ns.total + item.price %}
    {% if item.featured %}{% set ns.found = true %}{% endif %}
{% endfor %}
Total: {{ ns.total }}
```

### Filter Chaining

Chain filters left-to-right. Cache expensive chains with `{% set %}` to avoid recomputation:

```jinja
{# BAD — computed twice #}
{% if items | selectattr("active") | list | length > 0 %}
    {{ items | selectattr("active") | list | length }} active
{% endif %}

{# GOOD — compute once #}
{% set active = items | selectattr("active") | list %}
{% if active %}
    {{ active | length }} active
{% endif %}
```

---

## Anti-Patterns

### Business logic in templates

Templates decide *how* to display data, not *what* data to show. If a conditional involves more than simple display toggling, compute it in Python and pass a clean result:

```jinja
{# BAD — business rule buried in template #}
{% if user.active and user.role != "admin" and user.last_login > cutoff %}

{# GOOD — pre-computed in Python, template just displays #}
{% if show_welcome_banner %}
```

### Deep inheritance chains

More than 3 levels of `{% extends %}` creates a debugging maze. When you can't quickly answer "which template defines block X?", the hierarchy is too deep. Flatten by using includes or macros for shared fragments instead of adding another inheritance level.

### Using include where import belongs

`{% include %}` renders a template and dumps it into the output. `{% import %}` loads macros without rendering. Confusing them leads to either macros being unavailable or templates rendering when you just wanted the functions:

```jinja
{# WRONG — renders the file, macros not available as functions #}
{% include "macros/forms.html" %}

{# RIGHT — loads macros as callable functions #}
{% import "macros/forms.html" as forms %}
```

### Nested {{ }} inside {% %}

Inside statement tags, reference variables directly — don't nest expression delimiters:

```jinja
{# WRONG — syntax error #}
{% if {{ user.active }} %}

{# RIGHT #}
{% if user.active %}
```

### Repeated expensive filter chains

Every `|` filter call in a loop body executes per iteration. Extract invariant computations before the loop.

### New Environment per render

Creating a fresh `Environment()` for each render call destroys the template cache and is roughly 8x slower than reusing one. Create a single `Environment` at module level or app startup and reuse it.

---

## Whitespace Control

Whitespace handling depends entirely on the output format.

**HTML/Email** — Whitespace rarely matters. Prioritize template readability. Enable `trim_blocks=True` and `lstrip_blocks=True` globally for cleaner output without cluttering templates with `-` markers.

**YAML/INI/Config files** — Whitespace is semantic. Always enable `trim_blocks` and `lstrip_blocks`. Use `-` stripping markers (`{%- ... -%}`) for fine-grained control where the global settings aren't enough.

**Code generation** — Use custom delimiters if `{{ }}` conflicts with the target language (e.g., LaTeX, Go templates).

```jinja
{# Fine-grained stripping — strips whitespace on both sides #}
{%- for item in items -%}
    {{ item }}
{%- endfor -%}
```

---

## Style Conventions

These are near-universal across the Jinja2 ecosystem:

| Convention | Example | Why |
|---|---|---|
| Spaces inside delimiters | `{{ var }}`, `{% if %}` | Readability; `{{var}}` is harder to scan |
| Spaces around pipes | `{{ val \| filter }}` | Distinguishes filter from value |
| 4-space indentation | Nested blocks indented 4 spaces | Matches Python convention |
| snake_case variables | `user_name`, `order_total` | Matches Python naming |
| Named end tags | `{% endblock content %}` | Prevents mismatched block bugs |
| Descriptive macro names | `render_field`, `format_price` | Verb-prefixed for clarity |

---

## Reference Files

Read these when you need detailed syntax, filter lists, or Python configuration patterns:

| Reference | When to read | Content |
|-----------|-------------|---------|
| [refs/templates.md](refs/templates.md) | Writing or debugging template syntax | Complete syntax reference, all built-in filters and tests, loop variables, inheritance details, macro internals |
| [refs/python.md](refs/python.md) | Configuring Environment, writing custom filters/tests/extensions, optimizing performance | Loaders, undefined classes, custom filters with context awareness, extensions API, bytecode caching, async rendering, NativeEnvironment, testing templates |
