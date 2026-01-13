#!/bin/bash
# Post-edit format hook - runs mach format on edited files

# Read the hook input JSON from stdin
file_path=$(jq -r '.tool_input.file_path')

# Check if file should be formatted (using the detection script)
if "$CLAUDE_PROJECT_DIR"/.claude/hooks/should-format-lint.sh "$file_path"; then
    cd "$CLAUDE_PROJECT_DIR" || exit 1
    echo "[Hook] Formatting: $file_path"
    ./mach format "$file_path" 2>&1 | grep -v '^$' | head -30
fi
