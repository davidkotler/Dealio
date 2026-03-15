#!/usr/bin/env bash
# PostToolUse hook: auto-fix and format web files with ESLint + Prettier after edits.
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

# Skip if no path or file was deleted
if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Only process web source files (TS/TSX/JS/JSX/MTS/MJS)
case "$FILE_PATH" in
  */web/src/*.ts | */web/src/*.tsx | */web/src/*.mts | */web/src/*.js | */web/src/*.jsx | */web/src/*.mjs) ;;
  *) exit 0 ;;
esac

# Resolve web/ directory from file path
WEB_DIR="${FILE_PATH%%/src/*}"
BIN_DIR="$WEB_DIR/node_modules/.bin"

# Skip if node_modules not installed
if [[ ! -d "$BIN_DIR" ]]; then
  exit 0
fi

# Auto-fix lint issues
"$BIN_DIR/eslint" --fix "$FILE_PATH" 2>/dev/null || true

# Auto-format with Prettier
"$BIN_DIR/prettier" --write "$FILE_PATH" 2>/dev/null || true

# Report remaining unfixable ESLint issues to Claude
ISSUES=$("$BIN_DIR/eslint" "$FILE_PATH" 2>&1) || true
if echo "$ISSUES" | grep -qE '^\s+[0-9]+:[0-9]+\s+error'; then
  echo "eslint found issues in $(basename "$FILE_PATH"):" >&2
  echo "$ISSUES" >&2
  exit 2
fi

exit 0
