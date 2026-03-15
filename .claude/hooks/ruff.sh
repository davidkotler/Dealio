#!/usr/bin/env bash
# PostToolUse hook: auto-fix and format Python files with ruff after edits.
# Remaining unfixable issues are reported to Claude via stderr (exit 2).
set -uo pipefail

INPUT=$(cat)

# Extract file path — Edit/Write use "file_path", Serena tools use "relative_path"
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
if [[ -z "$FILE_PATH" ]]; then
  REL_PATH=$(echo "$INPUT" | jq -r '.tool_input.relative_path // empty')
  CWD=$(echo "$INPUT" | jq -r '.cwd // empty')
  if [[ -n "$REL_PATH" && -n "$CWD" ]]; then
    FILE_PATH="$CWD/$REL_PATH"
  fi
fi

# Skip non-Python files or missing paths
if [[ -z "$FILE_PATH" || "$FILE_PATH" != *.py ]]; then
  exit 0
fi

# Skip if file was deleted
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Auto-fix lint issues and format
ruff check --fix --quiet "$FILE_PATH" 2>/dev/null || true
ruff format --quiet "$FILE_PATH" 2>/dev/null || true

# Report remaining unfixable issues to Claude
ISSUES=$(ruff check --no-fix "$FILE_PATH" 2>&1) || true
if [[ -n "$ISSUES" ]]; then
  echo "ruff found issues in $(basename "$FILE_PATH"):" >&2
  echo "$ISSUES" >&2
  exit 2
fi

exit 0
