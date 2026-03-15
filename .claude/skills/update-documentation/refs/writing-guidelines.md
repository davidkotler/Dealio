# Writing Guidelines

> Tone, style, and conventions for all documentation written by `/update-documentation`.

---

## Tone and Style

- Write for an audience of engineers who will read this 6 months from now
- Be precise — file paths, class names, configuration keys, not vague descriptions
- Explain the **why**, not just the **what** — future readers need context for decisions
- Use tables for structured data, prose for explanations and context
- Include mermaid diagrams sparingly — only where they communicate something text cannot

---

## Updating vs. Creating

**When updating existing docs:**
- Read the entire existing document first
- Add new content in the appropriate section — don't reorganize
- If the feature changes something already documented, update in place with a note:
  `Updated {date}: {what changed and why, referencing feature design directory}`
- Preserve the existing author's structure and style

**When creating new docs:**
- Follow the templates in the corresponding ref file as a starting structure
- Only include sections relevant to the service or concern — omit empty sections
- Start with what you know from the feature artifacts — don't speculate about future state
- Link to the feature design directory for detailed design rationale

---

## Cross-References

- Link ADRs to the feature design directory: `See [Feature Design](../../designs/YYYY/NNN-{name}/)`
- Link service docs to their OpenAPI/AsyncAPI specs: `See [API Contract](../../../services/{name}/specs/openapi/v1.yaml)`
- Link architecture docs to relevant ADRs: `See [ADR-NNNN](../../adrs/NNNN-{title}.md)`
- Use relative paths for all cross-references within `docs/`
