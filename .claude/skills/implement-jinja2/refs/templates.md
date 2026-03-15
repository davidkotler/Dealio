# Jinja2 Template Reference

> Syntax, built-in filters/tests, control structures, composition patterns.

## Table of Contents

1. [Syntax Fundamentals](#syntax-fundamentals)
2. [Variables and Data Access](#variables-and-data-access)
3. [Control Structures](#control-structures)
4. [Loop Variable Reference](#loop-variable-reference)
5. [Template Inheritance](#template-inheritance)
6. [Include and Import](#include-and-import)
7. [Macros](#macros)
8. [Built-in Filters](#built-in-filters)
9. [Built-in Tests](#built-in-tests)
10. [Whitespace Control](#whitespace-control)
11. [Advanced Patterns](#advanced-patterns)

---

## Syntax Fundamentals

Three delimiter pairs:

| Delimiter | Purpose | Example |
|-----------|---------|---------|
| `{{ ... }}` | Expression output | `{{ user.name }}` |
| `{% ... %}` | Statement (control flow, assignments) | `{% if active %}` |
| `{# ... #}` | Comment (stripped at compilation) | `{# TODO: fix this #}` |

Comments produce no output and are stripped during compilation — they're free, use them to document complex logic.

---

## Variables and Data Access

Dot notation tries `getattr` first, then `__getitem__`. Bracket notation does the reverse:

```jinja
{{ user.name }}              {# getattr first #}
{{ user["name"] }}           {# __getitem__ first #}
{{ users[0].email }}         {# chained access #}
{{ data.get("key", "fallback") }}  {# method calls work #}
```

By default, undefined variables render as empty string (falsy). Use `StrictUndefined` in Python to catch typos at render time instead of producing silent empty output.

---

## Control Structures

### Conditionals

```jinja
{% if temperature > 30 %}
    Hot.
{% elif temperature > 15 %}
    Nice.
{% else %}
    Cold.
{% endif %}
```

Inline conditional expression:
```jinja
{{ "active" if user.is_active else "inactive" }}
```

### For Loops

```jinja
{% for user in users %}
    {{ loop.index }}. {{ user.name }}
{% else %}
    No users found.
{% endfor %}
```

The `else` clause executes when the iterable is empty.

**Filtered loops** — filter inline without a separate conditional:
```jinja
{% for user in users if user.is_active %}
    {{ user.name }}
{% endfor %}
```

**Unpacking** — works for dicts and nested structures:
```jinja
{% for key, value in config.items() %}
    {{ key }} = {{ value }}
{% endfor %}
```

### Assignments

```jinja
{% set greeting = "Hello" %}
{% set nav = [("Home", "/"), ("About", "/about")] %}

{# Block assignment — captures rendered content as a string #}
{% set content %}
    <p>This is captured content.</p>
{% endset %}
```

---

## Loop Variable Reference

The `loop` variable is available inside every `{% for %}` block:

| Variable | Type | Description |
|----------|------|-------------|
| `loop.index` | int | 1-based iteration count |
| `loop.index0` | int | 0-based iteration count |
| `loop.first` | bool | True on first iteration |
| `loop.last` | bool | True on last iteration |
| `loop.length` | int | Total number of items |
| `loop.revindex` | int | Reverse count from end (1-based) |
| `loop.revindex0` | int | Reverse count from end (0-based) |
| `loop.cycle(*args)` | any | Cycle through a list of values |
| `loop.previtem` | any | Previous item (Jinja 2.10+) |
| `loop.nextitem` | any | Next item (Jinja 2.10+) |

```jinja
{% for item in items %}
    <tr class="{{ loop.cycle('odd', 'even') }}">
        <td>{{ loop.index }}</td>
        <td>{{ item.name }}</td>
    </tr>
{% endfor %}
```

---

## Template Inheritance

### Core Mechanics

A child template declares `{% extends "parent.html" %}` and overrides named `{% block %}` sections. Everything outside blocks in a child template is ignored.

```jinja
{# base.html #}
<html>
<head><title>{% block title %}Default{% endblock %} — Site</title></head>
<body>{% block content %}{% endblock %}</body>
</html>

{# page.html #}
{% extends "base.html" %}
{% block title %}My Page{% endblock %}
{% block content %}<h1>Hello</h1>{% endblock %}
```

### super()

Renders the parent block's content, enabling additive overrides:
```jinja
{% block scripts %}
    {{ super() }}
    <script src="/js/extra.js"></script>
{% endblock %}
```

### self.block_name()

Reuse a block's content elsewhere in the same template:
```jinja
<title>{% block title %}Page Title{% endblock %}</title>
<h1>{{ self.title() }}</h1>
```

### Scoped Blocks

Blocks inside loops can't access loop variables by default. Add `scoped`:
```jinja
{% for item in items %}
    {% block item_display scoped %}{{ item.name }}{% endblock %}
{% endfor %}
```

### Required Blocks (Jinja 3.1+)

Force child templates to override a block:
```jinja
{% block page_content required %}{% endblock %}
```

### Dynamic Inheritance

The parent template can be a variable:
```jinja
{% extends layout_template %}
```

Where `layout_template` is a string name or template object passed from Python. Enables runtime layout switching (mobile vs desktop, A/B testing).

---

## Include and Import

### Include — Embed Rendered Output

```jinja
{% include "partials/header.html" %}
{% include "partials/sidebar.html" ignore missing %}
{% include ["custom_footer.html", "default_footer.html"] %}
```

- Included templates share the parent's context by default
- `ignore missing` silently skips if the template doesn't exist
- A list tries each template in order, uses the first found
- Use `without context` to isolate the included template

### Import — Load Macros Without Rendering

```jinja
{# Namespace import #}
{% import "macros/forms.html" as forms %}
{{ forms.input("email") }}

{# Selective import #}
{% from "macros/forms.html" import input, textarea %}
{{ input("email") }}
```

Imported templates do NOT have access to the current context by default. Use `with context` only if truly needed — it creates implicit coupling.

### Key Difference

- `include` = render the template, insert the output
- `import` = load the template's macros/variables, don't render

---

## Macros

### Definition

```jinja
{% macro input(name, type="text", value="", required=false) %}
<input type="{{ type }}" name="{{ name }}" value="{{ value }}"
       {{ "required" if required }}>
{% endmacro %}
```

### Special Variables Inside Macros

| Variable | Description |
|----------|-------------|
| `varargs` | Extra positional arguments (list) |
| `kwargs` | Extra keyword arguments (dict) |
| `caller` | Content from a `{% call %}` block |

### Call Blocks

Pass arbitrary content into a macro:

```jinja
{% macro panel(title) %}
<div class="panel">
    <h3>{{ title }}</h3>
    <div class="body">{{ caller() }}</div>
</div>
{% endmacro %}

{% call panel("Details") %}
    <p>Inner content goes here</p>
{% endcall %}
```

Pass arguments back from the macro to the caller:

```jinja
{% macro render_list(items) %}
<ul>
{% for item in items %}
    <li>{{ caller(item) }}</li>
{% endfor %}
</ul>
{% endmacro %}

{% call(item) render_list(products) %}
    <strong>{{ item.name }}</strong> — ${{ item.price }}
{% endcall %}
```

---

## Built-in Filters

Filters transform values using the pipe operator (`|`). Chain left-to-right.

### String Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `upper` | Uppercase | `{{ name \| upper }}` |
| `lower` | Lowercase | `{{ name \| lower }}` |
| `title` | Title Case | `{{ name \| title }}` |
| `capitalize` | First letter uppercase | `{{ name \| capitalize }}` |
| `trim` | Strip leading/trailing whitespace | `{{ input \| trim }}` |
| `striptags` | Remove HTML tags | `{{ html \| striptags }}` |
| `truncate(len, killwords, end)` | Truncate to length | `{{ desc \| truncate(200) }}` |
| `wordwrap(width)` | Wrap at width | `{{ text \| wordwrap(80) }}` |
| `replace(old, new)` | String replace | `{{ name \| replace("_", " ") }}` |
| `indent(width, first)` | Indent lines | `{{ block \| indent(4) }}` |
| `center(width)` | Center in width | `{{ title \| center(40) }}` |
| `format(...)` | printf-style format | `{{ "%.2f" \| format(price) }}` |
| `urlize(trim_url_limit)` | Convert URLs to links | `{{ text \| urlize }}` |

### Collection Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `length` | Collection size | `{{ items \| length }}` |
| `first` / `last` | First/last item | `{{ items \| first }}` |
| `reverse` | Reverse order | `{{ items \| reverse }}` |
| `sort(attribute, reverse)` | Sort | `{{ items \| sort(attribute="name") }}` |
| `unique` | Deduplicate | `{{ tags \| unique }}` |
| `join(sep)` | Join to string | `{{ names \| join(", ") }}` |
| `map(attribute)` | Extract attribute | `{{ users \| map(attribute="name") }}` |
| `select(test)` | Keep matching | `{{ nums \| select("odd") }}` |
| `reject(test)` | Remove matching | `{{ nums \| reject("even") }}` |
| `selectattr(attr, test)` | Keep by attribute | `{{ users \| selectattr("active") }}` |
| `rejectattr(attr, test)` | Remove by attribute | `{{ users \| rejectattr("deleted") }}` |
| `groupby(attribute)` | Group by attribute | `{{ users \| groupby("role") }}` |
| `batch(count, fill)` | Split into batches | `{{ items \| batch(3) }}` |
| `slice(count, fill)` | Split into slices | `{{ items \| slice(3) }}` |
| `list` | Materialize to list | `{{ gen \| list }}` |
| `items` | Dict items (3.1+) | `{{ dict \| items }}` |

### Numeric Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `int` | Convert to int | `{{ val \| int }}` |
| `float` | Convert to float | `{{ val \| float }}` |
| `round(precision, method)` | Round | `{{ price \| round(2) }}` |
| `abs` | Absolute value | `{{ diff \| abs }}` |
| `sum(attribute)` | Sum | `{{ prices \| sum }}` |
| `max` / `min` | Max/min value | `{{ scores \| max }}` |

### Type and Safety Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `default(value, boolean)` | Fallback for undefined/falsy | `{{ x \| default("N/A") }}` |
| `safe` | Mark as safe (bypass escaping) | `{{ html \| safe }}` |
| `escape` / `e` | HTML escape | `{{ input \| e }}` |
| `forceescape` | Force escape (even if safe) | `{{ val \| forceescape }}` |
| `tojson` | Serialize to JSON | `{{ data \| tojson }}` |
| `string` | Convert to string | `{{ num \| string }}` |
| `pprint` | Pretty-print for debugging | `{{ obj \| pprint }}` |

### Formatting Filters

| Filter | Description |
|--------|-------------|
| `xmlattr(autospace)` | Dict to XML attributes |
| `filesizeformat` | Human-readable file size |
| `dictsort(case_sensitive, by)` | Sort dict items |
| `wordcount` | Count words |

### Filter Blocks

Apply a filter to an entire block of content:
```jinja
{% filter upper %}
    This entire block will be uppercased.
{% endfilter %}
```

---

## Built-in Tests

Tests are used with `is` in conditional expressions. They check without modifying:

| Test | Description | Example |
|------|-------------|---------|
| `defined` | Variable exists | `{% if x is defined %}` |
| `undefined` | Variable doesn't exist | `{% if x is undefined %}` |
| `none` | Value is None | `{% if x is none %}` |
| `boolean` | Is a boolean | `{% if x is boolean %}` |
| `integer` | Is an integer | `{% if x is integer %}` |
| `float` | Is a float | `{% if x is float %}` |
| `number` | Is numeric | `{% if x is number %}` |
| `string` | Is a string | `{% if x is string %}` |
| `sequence` | Is a sequence | `{% if x is sequence %}` |
| `iterable` | Is iterable | `{% if x is iterable %}` |
| `mapping` | Is a mapping (dict) | `{% if x is mapping %}` |
| `callable` | Is callable | `{% if x is callable %}` |
| `even` / `odd` | Even/odd number | `{% if n is even %}` |
| `divisibleby(n)` | Divisible by n | `{% if x is divisibleby(3) %}` |
| `sameas(other)` | Identity check (is) | `{% if x is sameas(y) %}` |
| `in(seq)` | Contained in sequence | `{% if x is in(allowed) %}` |
| `eq`, `ne`, `lt`, `le`, `gt`, `ge` | Comparison tests | `{% if age is ge(18) %}` |
| `filter` (3.1+) | Is a registered filter | `{% if "markdown" is filter %}` |
| `test` (3.1+) | Is a registered test | `{% if "prime" is test %}` |

---

## Whitespace Control

### Global Settings (Python)

```python
env = Environment(
    trim_blocks=True,    # Remove first newline after block tags
    lstrip_blocks=True,  # Strip leading whitespace before block tags
)
```

### Per-Tag Control

Add `-` to strip whitespace on that side:
```jinja
{%- for item in items -%}    {# strips both sides #}
    {{ item }}
{%- endfor -%}
```

Add `+` to preserve whitespace (overrides global trim):
```jinja
{%+ if show_space %}         {# preserves leading whitespace #}
```

---

## Advanced Patterns

### Conditional Filter Application

Use the `is filter` test (3.1+) to conditionally apply optional filters:
```jinja
{% if "markdown" is filter %}
    {{ content | markdown }}
{% else %}
    {{ content }}
{% endif %}
```

### Groupby with Nested Loops

```jinja
{% for group in users | groupby("role") %}
<h2>{{ group.grouper }}</h2>
<ul>
    {% for user in group.list %}
    <li>{{ user.name }}</li>
    {% endfor %}
</ul>
{% endfor %}
```

### Batch for Grid Layouts

```jinja
{% for row in items | batch(3, "&nbsp;") %}
<tr>
    {% for col in row %}
    <td>{{ col }}</td>
    {% endfor %}
</tr>
{% endfor %}
```

### Raw Blocks

Disable Jinja processing for a section (useful when outputting template syntax):
```jinja
{% raw %}
    {{ this is not processed }}
{% endraw %}
```

### String Concatenation

Use the `~` operator (converts operands to strings):
```jinja
{% set full_name = first_name ~ " " ~ last_name %}
```
